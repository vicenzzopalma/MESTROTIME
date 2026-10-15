"""Typed contracts exchanged by the orchestration engine and its UI."""

from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class FSMState(str, Enum):
    PRE_CHECK = "PRE_CHECK"
    PLANNING = "PLANNING"
    EXECUTING_CODEX = "EXECUTING_CODEX"
    EXECUTING_ANTIGRAVITY = "EXECUTING_ANTIGRAVITY"
    QUALITY_GATE = "QUALITY_GATE"
    AUTO_HEAL = "AUTO_HEAL"
    COMMIT_OR_ROLLBACK = "COMMIT_OR_ROLLBACK"
    PAUSED = "PAUSED"
    STOPPED = "STOPPED"


class TaskPayload(BaseModel):
    target_files: list[str] = Field(default_factory=list)
    rationale: str
    codex_instruction: str
    agy_instruction: str
    human_override: bool = False


class CycleRecord(BaseModel):
    cycle_number: int
    status: Literal["COMMIT", "ROLLBACK"]
    target_file: str
    rationale: str
    duration_sec: float
    commit_hash: str | None = None
    error_summary: str | None = None
    codex_prompt: str = ""
    agy_prompt: str = ""
