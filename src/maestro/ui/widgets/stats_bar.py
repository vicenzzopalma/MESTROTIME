from textual.widgets import Static


class StatsBar(Static):
    def __init__(self) -> None:
        self.commits = self.rollbacks = 0
        super().__init__(self._build_text(), id="stats-bar")

    def set_stats(self, stats: dict) -> None:
        self.commits = int(stats.get("commits", 0))
        self.rollbacks = int(stats.get("rollbacks", 0))
        self.update(self._build_text())

    def _build_text(self) -> str:
        total = self.commits + self.rollbacks
        rate = 100 * self.commits / total if total else 0
        return f"Commits: [green]{self.commits}[/]   Rollbacks: [red]{self.rollbacks}[/]   Success: {rate:.1f}%"
