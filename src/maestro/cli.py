"""Typer command line interface for Chronos Maestro."""

from __future__ import annotations

import re
import shlex
from pathlib import Path

import typer

from maestro import __version__
from maestro.git_sandbox import GitSandbox
from maestro.state_store import StateStore
from maestro.ui.app import MaestroApp

app = typer.Typer(help="Chronos Maestro autonomous engineering orchestrator.")


def parse_duration(value: str) -> int:
    match = re.fullmatch(r"\s*(\d+)\s*([mh])?\s*", value, flags=re.I)
    if not match or int(match.group(1)) <= 0:
        raise typer.BadParameter("duration must look like 60m, 2h, 45m, or just numbers in minutes (e.g. 90 or 420)")
    unit = (match.group(2) or "m").lower()
    multiplier = 3600 if unit == "h" else 60
    return int(match.group(1)) * multiplier


@app.command()
def run(
    duration: str = typer.Option("60m", "--duration", help="Global timer, for example 60m, 2h, or 45m."),
    repo: Path = typer.Option(Path("."), "--repo", exists=True, file_okay=False, dir_okay=True,
                              resolve_path=True, help="Repository root."),
    test_cmd: str = typer.Option("pytest", "--test-cmd", help="Quality gate command."),
    branch: str = typer.Option("maestro-refine", "--branch", help="Branch for autonomous work."),
) -> None:
    """Run the interactive autonomous engineering dashboard."""
    seconds = parse_duration(duration)
    command = shlex.split(test_cmd, posix=False)
    if not command:
        raise typer.BadParameter("test-cmd must not be empty")
    root = repo.resolve()
    store = StateStore(root)
    sandbox = GitSandbox(root)
    MaestroApp(root, seconds, command, branch, store, sandbox).run()


@app.command()
def version() -> None:
    """Print the installed Chronos Maestro version."""
    typer.echo(__version__)
