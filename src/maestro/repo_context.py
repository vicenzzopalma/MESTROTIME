"""Repository information made available to the planning agent."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path


class RepoContext:
    IGNORED_DIRECTORIES = {
        ".git",
        ".venv",
        "venv",
        "node_modules",
        "__pycache__",
        ".maestro_state",
        ".maestri",
    }

    def __init__(self, repository_root: str | Path) -> None:
        self.repository_root = Path(repository_root).resolve()

    def file_tree(self) -> str:
        """Return a deterministic, repository-relative list of files."""
        entries: list[str] = []
        for current, directory_names, filenames in os.walk(self.repository_root):
            directory_names[:] = sorted(
                name for name in directory_names if name not in self.IGNORED_DIRECTORIES
            )
            relative_dir = Path(current).relative_to(self.repository_root)
            for filename in sorted(filenames):
                relative_path = relative_dir / filename
                entries.append(relative_path.as_posix())
        return "\n".join(entries)

    def git_log(self) -> str:
        result = subprocess.run(
            ["git", "log", "-n", "10", "--oneline"],
            cwd=self.repository_root,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        if result.returncode != 0:
            return "(no Git history available)"
        return result.stdout.strip() or "(no commits yet)"

    def snapshot(self) -> str:
        return f"FILES:\n{self.file_tree()}\n\nRECENT GIT HISTORY:\n{self.git_log()}"
