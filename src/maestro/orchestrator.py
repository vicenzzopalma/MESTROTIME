"""Asynchronous finite-state orchestration for a Maestro engineering cycle."""

from __future__ import annotations

import asyncio
import inspect
import json
import time
from collections.abc import Callable
from pathlib import Path

from maestro.config import (
    CODEX_BASE_CMD, DEFAULT_ANTIGRAVITY_TIMEOUT_SEC, DEFAULT_CODEX_TIMEOUT_SEC,
    DEFAULT_GLOBAL_CYCLE_TIMEOUT_SEC, DEFAULT_PRECHECK_TIMEOUT_SEC,
)
from maestro.git_sandbox import GitSandbox
from maestro.master_brain import MasterBrain
from maestro.models import CycleRecord, FSMState, TaskPayload
from maestro.process_watchdog import ProcessWatchdog
from maestro.quality_gate import QualityGate
from maestro.repo_context import RepoContext
from maestro.state_store import StateStore
from maestro.ui.events import CycleCompleted, DiffUpdated, LogChunkReceived, StateChanged, TimerUpdated


class MaestroOrchestrator:
    """Runs cycles independently of Textual and posts typed UI messages."""

    def __init__(self, repository_root: str | Path, state_store: StateStore,
                 git_sandbox: GitSandbox, post_message: Callable,
                 duration_seconds: int = 3600, test_command: list[str] | None = None,
                 branch: str = "maestro-refine") -> None:
        if duration_seconds <= 0:
            raise ValueError("duration_seconds must be positive")
        self.repository_root = Path(repository_root).resolve()
        self.state_store, self.git = state_store, git_sandbox
        self.post_message = post_message
        self.duration_seconds = int(duration_seconds)
        self.remaining_seconds = int(duration_seconds)
        self.branch = branch
        self.watchdog = ProcessWatchdog()
        self.brain = MasterBrain(RepoContext(self.repository_root), state_store, self.watchdog)
        self.quality_gate = QualityGate(self.repository_root, self.watchdog, test_command)
        self.state = FSMState.PRE_CHECK
        self.cycle_number = state_store.get_stats()["last_cycle_number"] + 1
        self.task_payload: TaskPayload | None = None
        self.paused = False
        self.stopped = False
        self._skip = False
        self._rollback = False
        self._lock = asyncio.Lock()
        self._loop_task: asyncio.Task | None = None
        self._stage_started = time.monotonic()
        self.latest_diff = ""
        self.latest_brain_json = "{}"
        self.latest_quality_output = ""
        self.latest_codex_prompt = ""
        self.latest_agy_prompt = ""

    async def _post(self, message) -> None:
        result = self.post_message(message)
        if inspect.isawaitable(result):
            await result

    async def _set_state(self, state: FSMState) -> None:
        self.state = state
        self._stage_started = time.monotonic()
        await self._post(StateChanged(self.cycle_number, state, self.task_payload))

    async def _log(self, source: str, text: str) -> None:
        if text:
            await self._post(LogChunkReceived(source, text))

    async def _process_log(self, source: str):
        async def emit(chunk: str) -> None:
            await self._log(source, chunk)
        return emit

    async def adjust_timer(self, delta_minutes: int) -> None:
        async with self._lock:
            self.remaining_seconds = max(0, self.remaining_seconds + int(delta_minutes) * 60)
            self.duration_seconds = max(0, self.duration_seconds + int(delta_minutes) * 60)
        await self._emit_timer()

    async def toggle_pause(self) -> None:
        self.paused = not self.paused
        if self.paused:
            await self._set_state(FSMState.PAUSED)
        else:
            await self._set_state(FSMState.PRE_CHECK)

    async def skip_current_step(self) -> None:
        self._skip = True
        await self._log("system", "Skip solicitado; etapa atual será interrompida.")
        await self.watchdog.kill_active_process()

    async def force_rollback(self) -> None:
        self._rollback = True
        await self.watchdog.kill_active_process()
        await self._log("system", "Rollback imediato solicitado.")

    async def stop(self) -> None:
        self.stopped = True
        await self.watchdog.kill_active_process()
        if self._loop_task and self._loop_task is not asyncio.current_task():
            self._loop_task.cancel()
        await self._set_state(FSMState.STOPPED)

    async def kill_current_stage(self) -> None:
        await self.skip_current_step()

    async def submit_intervention(self, target_file: str, directive: str) -> None:
        self.brain.set_human_override(target_file, directive)
        self._skip = False

    async def _emit_timer(self) -> None:
        await self._post(TimerUpdated(self.remaining_seconds, self.duration_seconds, self.paused))

    async def _timer(self) -> None:
        while not self.stopped:
            await asyncio.sleep(1)
            if not self.paused and self.remaining_seconds > 0:
                self.remaining_seconds -= 1
            await self._emit_timer()
            if self.remaining_seconds <= 0:
                await self.stop()
                return

    async def run(self) -> None:
        if self._loop_task is not None:
            raise RuntimeError("orchestrator is already running")
        self._loop_task = asyncio.current_task()
        timer_task = asyncio.create_task(self._timer(), name="maestro-global-timer")
        try:
            await self._run_cycles()
        except asyncio.CancelledError:
            pass
        finally:
            self.stopped = True
            timer_task.cancel()
            await asyncio.gather(timer_task, return_exceptions=True)
            if self.state != FSMState.STOPPED:
                await self._set_state(FSMState.STOPPED)

    async def _run_cycles(self) -> None:
        while not self.stopped and self.remaining_seconds > 0:
            while self.paused and not self.stopped:
                await asyncio.sleep(0.2)
            if self.stopped:
                break
            await self._run_cycle()
            self.cycle_number += 1

    async def _run_cycle(self) -> None:
        started = time.monotonic()
        status = "ROLLBACK"
        error: str | None = None
        commit_hash: str | None = None
        try:
            await self._set_state(FSMState.PRE_CHECK)
            if not self.repository_root.is_dir():
                raise RuntimeError(f"Repository does not exist: {self.repository_root}")
            await asyncio.to_thread(self.git.checkout_or_create_branch, self.branch)
            clean = await asyncio.to_thread(self.git.is_clean)
            if not clean:
                raise RuntimeError("Working tree is not clean; refusing to overwrite uncommitted changes")
            await self._set_state(FSMState.PLANNING)
            self.task_payload = await self.brain.plan(await self._process_log("master"))
            self.latest_brain_json = self.task_payload.model_dump_json(indent=2)
            self.latest_agy_prompt = self.task_payload.agy_instruction
            await self._post(StateChanged(self.cycle_number, FSMState.PLANNING, self.task_payload))
            await self._set_state(FSMState.EXECUTING_CODEX)
            self.latest_codex_prompt = self.task_payload.codex_instruction
            result = await self.watchdog.run(
                [*CODEX_BASE_CMD, self.task_payload.codex_instruction], DEFAULT_CODEX_TIMEOUT_SEC,
                await self._process_log("codex"), cwd=self.repository_root)
            if result.returncode != 0 or result.timed_out:
                raise RuntimeError(f"Codex failed (exit={result.returncode}, timeout={result.timed_out})\n{result.stderr[-3000:]}")
            self.latest_diff = await asyncio.to_thread(self.git.get_diff)
            await self._post(DiffUpdated(self.latest_diff))
            if self._rollback:
                raise RuntimeError("Rollback requested")
            await self._set_state(FSMState.EXECUTING_ANTIGRAVITY)
            review = await self.watchdog.run(
                ["agy", "-p", "--model", "gemini-3.8-flash-medium", self.task_payload.agy_instruction],
                DEFAULT_ANTIGRAVITY_TIMEOUT_SEC, await self._process_log("antigravity"), cwd=self.repository_root)
            if review.returncode != 0 or review.timed_out:
                raise RuntimeError(f"Antigravity failed (exit={review.returncode}, timeout={review.timed_out})")
            await self._set_state(FSMState.QUALITY_GATE)
            passed, output = await self.quality_gate.run(await self._process_log("quality"))
            self.latest_quality_output = output
            healed = 0
            while not passed and healed < 2 and not self._rollback and not self.stopped:
                healed += 1
                await self._set_state(FSMState.AUTO_HEAL)
                fix = f"Fix these quality gate failures, preserving the task scope:\n{output[-6000:]}"
                repair = await self.watchdog.run([*CODEX_BASE_CMD, fix], DEFAULT_CODEX_TIMEOUT_SEC,
                    await self._process_log("auto-heal"), cwd=self.repository_root)
                if repair.returncode != 0 or repair.timed_out:
                    break
                await self._set_state(FSMState.QUALITY_GATE)
                passed, output = await self.quality_gate.run(await self._process_log("quality"))
                self.latest_quality_output = output
            if not passed:
                raise RuntimeError(f"Quality gate failed after {healed} repair attempt(s):\n{output[-3000:]}")
            if self._rollback or self.stopped:
                raise RuntimeError("Rollback requested")
            await self._set_state(FSMState.COMMIT_OR_ROLLBACK)
            commit_hash = await asyncio.to_thread(self.git.commit_all,
                f"maestro cycle {self.cycle_number}: {self.task_payload.rationale[:72]}")
            status = "COMMIT"
        except asyncio.CancelledError:
            error = "Orchestration stopped"
            raise
        except Exception as exc:
            error = str(exc)
            await self._log("system", f"Cycle {self.cycle_number} failed: {error}\n")
            try:
                await asyncio.to_thread(self.git.rollback_hard)
            except Exception as rollback_exc:
                error += f"; rollback failed: {rollback_exc}"
        finally:
            self._rollback = False
            payload = self.task_payload or TaskPayload(rationale="Cycle failed before planning",
                codex_instruction="", agy_instruction="")
            record = CycleRecord(cycle_number=self.cycle_number, status=status,
                target_file=", ".join(payload.target_files) or "(none)", rationale=payload.rationale,
                duration_sec=time.monotonic()-started, commit_hash=commit_hash, error_summary=error,
                codex_prompt=self.latest_codex_prompt, agy_prompt=self.latest_agy_prompt)
            await asyncio.to_thread(self.state_store.save_cycle, record)
            await self._post(CycleCompleted(record))
            self.latest_diff = await asyncio.to_thread(self.git.get_diff)
            await self._post(DiffUpdated(self.latest_diff))
            self.task_payload = None
