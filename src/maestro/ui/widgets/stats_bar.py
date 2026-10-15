from textual.widgets import Static


class StatsBar(Static):
    def __init__(self) -> None:
        super().__init__(id="stats-bar")
        self.commits = self.rollbacks = 0
        self._render()

    def set_stats(self, stats: dict) -> None:
        self.commits = int(stats.get("commits", 0))
        self.rollbacks = int(stats.get("rollbacks", 0))
        self._render()

    def _render(self) -> None:
        total = self.commits + self.rollbacks
        rate = 100 * self.commits / total if total else 0
        self.update(f"Commits: [green]{self.commits}[/]   Rollbacks: [red]{self.rollbacks}[/]   Success: {rate:.1f}%")
