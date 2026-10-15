from textual.app import ComposeResult
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, TextArea


class InterventionModal(ModalScreen[tuple[str, str] | None]):
    BINDINGS = [("escape", "dismiss(None)", "Cancel")]

    def compose(self) -> ComposeResult:
        with Vertical(id="intervention-dialog"):
            yield Label("Human intervention", classes="modal-title")
            yield Label("Target file")
            yield Input(placeholder="relative/path/to/file", id="intervention-file")
            yield Label("Priority directive")
            yield TextArea(id="intervention-directive")
            yield Button("Queue intervention", variant="primary", id="intervention-submit")
            yield Button("Cancel", id="intervention-cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "intervention-cancel":
            self.dismiss(None)
        elif event.button.id == "intervention-submit":
            filename = self.query_one("#intervention-file", Input).value.strip()
            directive = self.query_one("#intervention-directive", TextArea).text.strip()
            if filename and directive:
                self.dismiss((filename, directive))
            else:
                self.notify("Both the target file and directive are required", severity="error")
