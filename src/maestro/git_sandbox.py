"""Small, explicit Git boundary used by the cycle orchestrator."""

from __future__ import annotations

import subprocess
from pathlib import Path


class GitSandbox:
    def __init__(self, repository_root: str | Path) -> None:
        self.repository_root = Path(repository_root).resolve()

    def _git(self, *arguments: str, check: bool = True) -> str:
        result = subprocess.run(
            ["git", *arguments],
            cwd=self.repository_root,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        if check and result.returncode != 0:
            detail = result.stderr.strip() or result.stdout.strip()
            raise RuntimeError(f"git {' '.join(arguments)} failed: {detail}")
        return result.stdout

    def checkout_or_create_branch(self, branch: str) -> None:
        if not branch.strip():
            raise ValueError("branch must not be empty")
        exists = self._git("rev-parse", "--verify", "--quiet", f"refs/heads/{branch}", check=False)
        if exists.strip():
            self._git("checkout", branch)
        else:
            self._git("checkout", "-b", branch)

    def is_clean(self) -> bool:
        return not self._git("status", "--porcelain").strip()

    def get_diff(self) -> str:
        return self._git("diff", "--no-ext-diff", "HEAD")

    def get_diff_stat(self) -> str:
        return self._git("diff", "--stat", "HEAD")

    def get_commit_show(self, commit_hash: str) -> str:
        if not commit_hash.strip():
            raise ValueError("commit_hash must not be empty")
        return self._git("show", "--no-ext-diff", "--stat", "--oneline", commit_hash)

    def commit_all(self, message: str) -> str:
        if not message.strip():
            raise ValueError("commit message must not be empty")
        self._git("add", "-A")
        if self.is_clean():
            raise RuntimeError("cannot commit: the working tree has no changes")
        self._git("commit", "-m", message)
        return self._git("rev-parse", "HEAD").strip()

    def rollback_hard(self) -> None:
        self._git("reset", "--hard", "HEAD")
        self._git("clean", "-fd")
