"""Messages emitted by the core without coupling it to a Textual application."""

from __future__ import annotations

from textual.message import Message

from maestro.models import CycleRecord, FSMState, TaskPayload


class StateChanged(Message):
    def __init__(
        self,
        cycle_num: int,
        fsm_state: FSMState,
        task_payload: TaskPayload | None = None,
    ) -> None:
        super().__init__()
        self.cycle_num = cycle_num
        self.fsm_state = fsm_state
        self.task_payload = task_payload


class LogChunkReceived(Message):
    def __init__(self, source: str, text: str) -> None:
        super().__init__()
        self.source = source
        self.text = text


class DiffUpdated(Message):
    def __init__(self, diff_text: str) -> None:
        super().__init__()
        self.diff_text = diff_text


class CycleCompleted(Message):
    def __init__(self, cycle_record: CycleRecord) -> None:
        super().__init__()
        self.cycle_record = cycle_record
