from __future__ import annotations

from textual.app import ComposeResult
from textual.widgets import RichLog, Static, TabbedContent, TabPane
from rich.syntax import Syntax


class StreamTabs(TabbedContent):
    def __init__(self) -> None:
        super().__init__(id="stream-tabs")

    def compose(self) -> ComposeResult:
        with TabPane("[1] Live Agent Stream", id="tab-agent"):
            yield RichLog(id="agent-stream", wrap=True, markup=True)
        with TabPane("[2] Live Git Diff", id="tab-diff"):
            yield Static("", id="git-diff", markup=False)
        with TabPane("[3] Quality Gate Output", id="tab-quality"):
            yield RichLog(id="quality-output", wrap=True, markup=False)
        with TabPane("[4] Master Brain JSON", id="tab-brain"):
            yield Static("{}", id="brain-json", markup=False)

    def append_log(self, source: str, text: str) -> None:
        log = self.query_one("#agent-stream", RichLog)
        log.write(f"[{source}] {text}")
        if source == "quality":
            self.query_one("#quality-output", RichLog).write(text)

    def set_diff(self, text: str) -> None:
        self.query_one("#git-diff", Static).update(Syntax(text or "(no diff)", "diff", theme="ansi_dark", line_numbers=True))

    def set_quality(self, text: str) -> None:
        self.query_one("#quality-output", RichLog).write(text)

    def set_brain(self, text: str) -> None:
        self.query_one("#brain-json", Static).update(Syntax(text or "{}", "json", theme="ansi_dark", line_numbers=True))
