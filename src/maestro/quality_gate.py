"""Quality-gate execution independent from any specific test framework."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from maestro.config import DEFAULT_QUALITY_GATE_TIMEOUT_SEC, configured_test_command
from maestro.process_watchdog import LogCallback, ProcessWatchdog


class QualityGate:
    def __init__(
        self,
        repository_root: str | Path,
        watchdog: ProcessWatchdog | None = None,
        test_command: Sequence[str] | None = None,
        timeout_sec: float = DEFAULT_QUALITY_GATE_TIMEOUT_SEC,
    ) -> None:
        self.repository_root = Path(repository_root).resolve()
        self.watchdog = watchdog or ProcessWatchdog()
        self.test_command = list(test_command) if test_command is not None else configured_test_command()
        self.timeout_sec = timeout_sec

    async def run(self, on_log: LogCallback | None = None) -> tuple[bool, str]:
        result = await self.watchdog.run(
            self.test_command,
            timeout_sec=self.timeout_sec,
            on_log=on_log,
            cwd=self.repository_root,
        )
        output = f"{result.stdout}{result.stderr}"
        if result.timed_out:
            output = f"Quality gate timed out after {result.duration_sec:.1f}s\n{output}"
        return (not result.timed_out and result.returncode == 0, output)
