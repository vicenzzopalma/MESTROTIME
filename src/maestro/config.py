"""Central configuration and safe defaults for the Maestro engine."""

from __future__ import annotations

import os
import shlex
from pathlib import Path

CODEX_BASE_CMD = [
    "codex",
    "exec",
    "--full-auto",
    "-m",
    "gpt-6-luna",
    "-c",
    'model_reasoning_effort="medium"',
]
AGY_BASE_CMD = ["agy", "-p", "--model", "gemini-3.8-flash-medium"]

STATE_DIRECTORY_NAME = ".maestro_state"
DATABASE_FILENAME = "state.db"

DEFAULT_PRECHECK_TIMEOUT_SEC = 60.0
DEFAULT_PLANNING_TIMEOUT_SEC = 180.0
DEFAULT_CODEX_TIMEOUT_SEC = 1_800.0
DEFAULT_ANTIGRAVITY_TIMEOUT_SEC = 1_800.0
DEFAULT_QUALITY_GATE_TIMEOUT_SEC = 600.0
DEFAULT_GLOBAL_CYCLE_TIMEOUT_SEC = 3_600.0


def resolve_state_dir(repository_root: str | Path) -> Path:
    """Return the state directory for a repository without creating it."""
    return Path(repository_root).resolve() / STATE_DIRECTORY_NAME


def resolve_database_path(repository_root: str | Path) -> Path:
    """Return ``.maestro_state/state.db`` for a repository."""
    return resolve_state_dir(repository_root) / DATABASE_FILENAME


def configured_test_command() -> list[str]:
    """Read the test command from the environment, falling back to compilation."""
    configured = os.environ.get("MAESTRO_TEST_COMMAND", "").strip()
    if configured:
        return shlex.split(configured, posix=os.name != "nt")
    return ["python", "-m", "compileall", "-q", "src"]
