"""Async process supervision with bounded time and complete child-tree termination."""

from __future__ import annotations

import asyncio
import inspect
import os
import signal
import subprocess
import time
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

LogCallback = Callable[[str], None | Awaitable[None]]


@dataclass(frozen=True, slots=True)
class ProcessResult:
    command: tuple[str, ...]
    returncode: int | None
    stdout: str
    stderr: str
    timed_out: bool
    duration_sec: float


class ProcessWatchdog:
    """Run one child process at a time and enforce per-stage/global deadlines."""

    def __init__(self, global_timeout_sec: float | None = None) -> None:
        self._global_deadline = (
            time.monotonic() + global_timeout_sec
            if global_timeout_sec is not None
            else None
        )
        self._active_process: asyncio.subprocess.Process | None = None
        self._active_lock = asyncio.Lock()

    def remaining_global_time(self) -> float | None:
        if self._global_deadline is None:
            return None
        return max(0.0, self._global_deadline - time.monotonic())

    async def _emit(self, callback: LogCallback | None, line: str) -> None:
        if callback is None:
            return
        result = callback(line)
        if inspect.isawaitable(result):
            await result

    async def _terminate_process(self, process: asyncio.subprocess.Process) -> None:
        if process.returncode is not None:
            return
        if os.name == "nt":
            killer = await asyncio.create_subprocess_exec(
                "taskkill", "/F", "/T", "/PID", str(process.pid),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            await killer.wait()
            return
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            return
        try:
            await asyncio.wait_for(process.wait(), timeout=3.0)
        except TimeoutError:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                return

    async def kill_active_process(self) -> None:
        """Terminate the active command and every process it spawned."""
        async with self._active_lock:
            process = self._active_process
        if process is not None:
            await self._terminate_process(process)

    async def run(
        self,
        command: Sequence[str],
        timeout_sec: float,
        on_log: LogCallback | None = None,
        cwd: str | Path | None = None,
        env: dict[str, str] | None = None,
    ) -> ProcessResult:
        if not command:
            raise ValueError("command must contain at least one argument")
        if timeout_sec <= 0:
            raise ValueError("timeout_sec must be positive")

        remaining = self.remaining_global_time()
        effective_timeout = min(timeout_sec, remaining) if remaining is not None else timeout_sec
        if effective_timeout <= 0:
            return ProcessResult(tuple(command), None, "", "global timeout exhausted", True, 0.0)

        creationflags = subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0
        started = time.monotonic()
        process = await asyncio.create_subprocess_exec(
            *command,
            cwd=str(cwd) if cwd is not None else None,
            env=env,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            creationflags=creationflags,
            start_new_session=os.name != "nt",
        )
        async with self._active_lock:
            self._active_process = process

        stdout_lines: list[str] = []
        stderr_lines: list[str] = []

        async def pump(stream: asyncio.StreamReader, sink: list[str]) -> None:
            while True:
                data = await stream.readline()
                if not data:
                    break
                line = data.decode(errors="replace")
                sink.append(line)
                await self._emit(on_log, line)

        stdout_task = asyncio.create_task(pump(process.stdout, stdout_lines))
        stderr_task = asyncio.create_task(pump(process.stderr, stderr_lines))
        timed_out = False
        try:
            await asyncio.wait_for(process.wait(), timeout=effective_timeout)
        except TimeoutError:
            timed_out = True
            await self._terminate_process(process)
            await process.wait()
        finally:
            await asyncio.gather(stdout_task, stderr_task)
            async with self._active_lock:
                if self._active_process is process:
                    self._active_process = None

        return ProcessResult(
            command=tuple(command),
            returncode=process.returncode,
            stdout="".join(stdout_lines),
            stderr="".join(stderr_lines),
            timed_out=timed_out,
            duration_sec=time.monotonic() - started,
        )
