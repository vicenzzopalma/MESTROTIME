from textual.app import ComposeResult
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Label, RichLog, Static
from maestro.models import CycleRecord


class CycleDetailModal(ModalScreen[None]):
    BINDINGS = [("escape", "dismiss", "Close")]

    def __init__(self, record: CycleRecord, commit_show: str = "") -> None:
        super().__init__()
        self.record, self.commit_show = record, commit_show

    def compose(self) -> ComposeResult:
        record = self.record
        with Vertical(id="cycle-detail-dialog"):
            yield Label(f"Cycle {record.cycle_number} · {record.status}", classes="modal-title")
            yield Static(f"File: {record.target_file}\nDuration: {record.duration_sec:.1f}s\nRationale: {record.rationale}", id="cycle-summary")
            yield Label("Codex prompt")
            yield Static(record.codex_prompt or "(not recorded)", classes="prompt-view")
            yield Label("Antigravity prompt")
            yield Static(record.agy_prompt or "(not recorded)", classes="prompt-view")
            yield Label("Error or commit details")
            yield RichLog(id="cycle-output", wrap=True, markup=False)
            yield Button("Close", variant="primary", id="cycle-close")

    def on_mount(self) -> None:
        log = self.query_one("#cycle-output", RichLog)
        log.write(self.record.error_summary or self.commit_show or "No error or commit details recorded.")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cycle-close":
            self.dismiss()
