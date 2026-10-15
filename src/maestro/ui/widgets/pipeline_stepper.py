from textual.widgets import Static
import time


class PipelineStepper(Static):
    STEPS = ["PRE_CHECK", "PLANNING", "EXECUTING_CODEX", "EXECUTING_ANTIGRAVITY", "QUALITY_GATE", "AUTO_HEAL", "COMMIT_OR_ROLLBACK"]

    def __init__(self) -> None:
        self.current = None
        self.started = 0.0
        self.completed: set[str] = set()
        self.failed: set[str] = set()
        super().__init__(self._build_text(), id="pipeline-stepper")

    def set_state(self, state: str) -> None:
        if self.current and self.current != state:
            self.completed.add(self.current)
        self.current, self.started = state, time.monotonic()
        if state in self.completed:
            self.completed.remove(state)
        self.update(self._build_text())

    def _build_text(self) -> str:
        lines = ["[bold]PIPELINE[/]"]
        for step in self.STEPS:
            if step in self.completed:
                icon = "[green][OK][/]"
            elif step == self.current:
                icon = "[cyan][>>][/]"
            elif step in self.failed:
                icon = "[red][ X][/]"
            else:
                icon = "[dim][  ][/]"
            elapsed = f"  {int(time.monotonic()-self.started)}s" if step == self.current and self.started > 0 else ""
            lines.append(f"{icon} {step.replace('_', ' ').title()}{elapsed}")
        return "\n".join(lines)
