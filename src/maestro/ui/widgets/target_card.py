import json
from textual.widgets import Static
from maestro.models import TaskPayload


class TargetCard(Static):
    def __init__(self) -> None:
        super().__init__("[bold]CURRENT TARGET[/]\nAwaiting master plan", id="target-card")

    def set_payload(self, payload: TaskPayload | None) -> None:
        if payload is None:
            self.update("[bold]CURRENT TARGET[/]\nAwaiting master plan")
            return
        files = "\n".join(f" • {name}" for name in payload.target_files) or " • (unspecified)"
        override = "[yellow]HUMAN OVERRIDE ACTIVE[/]" if payload.human_override else "[dim]Autonomous plan[/]"
        self.update(f"[bold]TARGET FILES[/]\n{files}\n\n[bold]MASTER RATIONALE[/]\n{payload.rationale}\n\n{override}")
