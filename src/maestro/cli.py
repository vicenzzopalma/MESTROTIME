"""Command-line entry point for basic package introspection."""

from __future__ import annotations

import typer

from maestro import __version__

app = typer.Typer(help="Chronos Maestro autonomous engineering orchestrator.")


@app.command()
def version() -> None:
    """Print the installed Chronos Maestro version."""
    typer.echo(__version__)
