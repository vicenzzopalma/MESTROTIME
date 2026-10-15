from textual.widgets import Static


class HeaderHud(Static):
    DEFAULT_CSS = "HeaderHud { height: 3; padding: 0 1; content-align: left middle; }"

    def __init__(self, branch: str = "maestro-refine") -> None:
        self.branch = branch
        self.state = "STARTING"
        self.remaining = 0
        self.paused = False
        super().__init__(self._get_text(), id="header-hud")

    @staticmethod
    def format_time(seconds: int) -> str:
        hours, remainder = divmod(max(0, seconds), 3600)
        minutes, secs = divmod(remainder, 60)
        return f"{hours:02}:{minutes:02}:{secs:02}"

    def update_state(self, state: str) -> None:
        self.state = state
        self.update(self._get_text())

    def update_timer(self, remaining: int, paused: bool) -> None:
        self.remaining, self.paused = remaining, paused
        self.update(self._get_text())

    def _get_text(self) -> str:
        css = "timer-critical" if self.remaining <= 300 else "timer-warning" if self.remaining <= 900 else "timer-normal"
        badge = "PAUSED" if self.paused else self.state
        return f"[bold]CHRONOS MAESTRO[/]   Branch: [cyan]{self.branch}[/]   Status: [bold]{badge}[/]   Timer: [{css}]{self.format_time(self.remaining)}[/]"
