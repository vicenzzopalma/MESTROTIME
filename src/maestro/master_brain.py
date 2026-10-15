"""Planner that turns repository state into tightly validated agent work."""

from __future__ import annotations

import json
import re
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass

from maestro.config import AGY_BASE_CMD, DEFAULT_PLANNING_TIMEOUT_SEC
from maestro.models import TaskPayload
from maestro.process_watchdog import LogCallback, ProcessWatchdog
from maestro.repo_context import RepoContext
from maestro.state_store import StateStore


class PlanningError(RuntimeError):
    """Raised when AGY cannot provide a valid plan."""


@dataclass(frozen=True, slots=True)
class HumanOverride:
    target_file: str
    directive: str


class MasterBrain:
    def __init__(
        self,
        repo_context: RepoContext,
        state_store: StateStore,
        watchdog: ProcessWatchdog | None = None,
        agy_base_command: list[str] | None = None,
        planning_timeout_sec: float = DEFAULT_PLANNING_TIMEOUT_SEC,
    ) -> None:
        self.repo_context = repo_context
        self.state_store = state_store
        self.watchdog = watchdog or ProcessWatchdog()
        self.agy_base_command = list(agy_base_command or AGY_BASE_CMD)
        self.planning_timeout_sec = planning_timeout_sec
        self._human_overrides: deque[HumanOverride] = deque()

    def set_human_override(self, target_file: str, directive: str) -> None:
        """Queue a focused instruction; the next plan consumes it before AGY."""
        if not target_file.strip() or not directive.strip():
            raise ValueError("target_file and directive must not be empty")
        self._human_overrides.append(HumanOverride(target_file, directive))

    def _build_prompt(self) -> str:
        recent_cycles = [record.model_dump() for record in self.state_store.get_recent_cycles()]
        return (
            "You are the planning brain for an autonomous repository engineer. "
            "Select one small, high-value, safe change. Reply with ONLY a strict JSON object, "
            "without Markdown or commentary, matching exactly this schema: "
            '{"target_files":["relative/path.py"],"rationale":"why",'
            '"codex_instruction":"precise implementation instruction",'
            '"agy_instruction":"precise verification/review instruction",'
            '"human_override":false}.\n\n'
            f"Repository context:\n{self.repo_context.snapshot()}\n\n"
            f"Most recent cycles (newest first):\n{json.dumps(recent_cycles, ensure_ascii=False)}"
        )

    @staticmethod
    def _extract_json(text: str) -> dict:
        fenced = re.sub(r"^\s*```(?:json)?\s*|\s*```\s*$", "", text.strip(), flags=re.I)
        decoder = json.JSONDecoder()
        for match in re.finditer(r"\{", fenced):
            try:
                value, _ = decoder.raw_decode(fenced[match.start() :])
            except json.JSONDecodeError:
                continue
            if isinstance(value, dict):
                return value
        candidate = re.search(r"\{[\s\S]*\}", fenced)
        if candidate:
            try:
                value = json.loads(candidate.group(0))
            except json.JSONDecodeError as exc:
                raise PlanningError(f"planner returned malformed JSON: {exc}") from exc
            if isinstance(value, dict):
                return value
        raise PlanningError("planner output did not contain a JSON object")

    @classmethod
    def _parse_payload(cls, text: str) -> TaskPayload:
        try:
            return TaskPayload.model_validate(cls._extract_json(text))
        except Exception as exc:
            if isinstance(exc, PlanningError):
                raise
            raise PlanningError(f"planner output did not match TaskPayload: {exc}") from exc

    async def plan(self, on_log: LogCallback | None = None) -> TaskPayload:
        if self._human_overrides:
            override = self._human_overrides.popleft()
            return TaskPayload(
                target_files=[override.target_file],
                rationale="Human-directed override",
                codex_instruction=override.directive,
                agy_instruction=f"Review whether this directive was correctly applied: {override.directive}",
                human_override=True,
            )

        prompt = self._build_prompt()
        result = await self.watchdog.run(
            [*self.agy_base_command, prompt],
            timeout_sec=self.planning_timeout_sec,
            on_log=on_log,
            cwd=self.repo_context.repository_root,
        )
        output = f"{result.stdout}\n{result.stderr}".strip()
        if result.timed_out:
            raise PlanningError(f"AGY planning timed out after {result.duration_sec:.1f}s")
        if result.returncode != 0:
            raise PlanningError(f"AGY planning failed ({result.returncode}): {output[-2000:]}")
        return self._parse_payload(output)
