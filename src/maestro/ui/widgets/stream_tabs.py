from textual.widgets import RichLog, Static, TabbedContent, TabPane
from rich.syntax import Syntax


class StreamTabs(TabbedContent):
    def __init__(self) -> None:
        super().__init__(
            TabPane("[1] Live Agent Stream", RichLog(id="agent-stream", wrap=True, markup=True), id="tab-agent"),
            TabPane("[2] Live Git Diff", Static("", id="git-diff", markup=False), id="tab-diff"),
            TabPane("[3] Quality Gate Output", RichLog(id="quality-output", wrap=True, markup=False), id="tab-quality"),
            TabPane("[4] Master Brain JSON", Static("{}", id="brain-json", markup=False), id="tab-brain"),
            id="stream-tabs",
        )

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
