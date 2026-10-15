from textual.widgets import Static


class PipelineStepper(Static):
    STEPS = ["PRE_CHECK", "PLANNING", "EXECUTING_CODEX", "EXECUTING_ANTIGRAVITY", "QUALITY_GATE", "AUTO_HEAL", "COMMIT_OR_ROLLBACK"]

    def __init__(self) -> None:
        self.current = None
        self.started = 0.0
        self.completed: set[str] = set()
        self.failed: set[str] = set()
        super().__init__(id="pipeline-stepper")
        self.refresh_view()

    def set_state(self, state: str) -> None:
        import time
        if self.current and self.current != state:
            self.completed.add(self.current)
        self.current, self.started = state, time.monotonic()
        if state in self.completed:
            self.completed.remove(state)
        self.refresh_view()

    def refresh_view(self) -> None:
        import time
        lines = ["[bold]PIPELINE[/]"]
        for step in self.STEPS:
            icon = "[✔]" if step in self.completed else "[⏳]" if step == self.current else "[✖]" if step in self.failed else "[ ]"
            elapsed = f"  {int(time.monotonic()-self.started)}s" if step == self.current else ""
            lines.append(f"{icon} {step.replace('_', ' ').title()}{elapsed}")
        self.update("\n".join(lines))
