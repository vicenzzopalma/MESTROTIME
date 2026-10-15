"""Interactive Textual dashboard for Chronos Maestro."""

from __future__ import annotations

from pathlib import Path
from textual.app import App, ComposeResult
from textual.containers import Vertical
from textual.binding import Binding
from textual import on

from maestro.models import FSMState
from maestro.state_store import StateStore
from maestro.git_sandbox import GitSandbox
from maestro.orchestrator import MaestroOrchestrator
from maestro.ui.events import CycleCompleted, DiffUpdated, LogChunkReceived, StateChanged, TimerUpdated
from maestro.ui.modals import CycleDetailModal, InterventionModal
from maestro.ui.widgets import HeaderHud, PipelineStepper, TargetCard, CycleTable, StreamTabs, StatsBar


class MaestroApp(App):
    """Textual front end; all repository work remains in MaestroOrchestrator."""

    TITLE = "Chronos Maestro"
    CSS_PATH = "theme.tcss"
    BINDINGS = [
        Binding("space", "toggle_pause", "Pause / Resume", priority=True),
        Binding("1", "tab(0)", "Agent stream"), Binding("2", "tab(1)", "Git diff"),
        Binding("3", "tab(2)", "Quality gate"), Binding("4", "tab(3)", "Master Brain"),
        Binding("i", "intervention", "Intervention"), Binding("+", "add_time", "+15 min"),
        Binding("-", "remove_time", "-15 min"), Binding("k", "kill_stage", "Kill stage"),
        Binding("r", "rollback", "Rollback"), Binding("q", "quit_maestro", "Quit", priority=True),
    ]

    def __init__(self, repository_root: str | Path = ".", duration_seconds: int = 3600,
                 test_command: list[str] | None = None, branch: str = "maestro-refine",
                 state_store: StateStore | None = None, git_sandbox: GitSandbox | None = None) -> None:
        super().__init__()
        self.repository_root = Path(repository_root).resolve()
        self.store = state_store or StateStore(self.repository_root)
        self.git = git_sandbox or GitSandbox(self.repository_root)
        self.duration_seconds = duration_seconds
        self.test_command, self.branch = test_command, branch
        self.orchestrator: MaestroOrchestrator | None = None
        self._orchestrator_task = None

    def compose(self) -> ComposeResult:
        yield HeaderHud(self.branch)
        with Vertical(id="left-column"):
            yield PipelineStepper()
            yield TargetCard()
            yield CycleTable()
        yield StreamTabs()
        yield StatsBar()

    async def on_mount(self) -> None:
        self.query_one(CycleTable).focus()
        for record in reversed(self.store.get_recent_cycles(100)):
            self.query_one(CycleTable).add_record(record)
        self.query_one(StatsBar).set_stats(self.store.get_stats())
        self.orchestrator = MaestroOrchestrator(
            self.repository_root, self.store, self.git, self.post_message,
            self.duration_seconds, self.test_command, self.branch,
        )
        self._orchestrator_task = self.run_worker(self.orchestrator.run(), name="maestro-orchestrator", exclusive=True)

    @on(StateChanged)
    def handle_state_changed(self, message: StateChanged) -> None:
        self.query_one(HeaderHud).update_state(message.fsm_state.value)
        self.query_one(PipelineStepper).set_state(message.fsm_state.value)
        self.query_one(TargetCard).set_payload(message.task_payload)
        if message.fsm_state == FSMState.PLANNING and self.orchestrator:
            self.query_one(StreamTabs).set_brain(self.orchestrator.latest_brain_json)

    @on(LogChunkReceived)
    def handle_log(self, message: LogChunkReceived) -> None:
        self.query_one(StreamTabs).append_log(message.source, message.text)
        if message.source == "quality" and self.orchestrator:
            self.orchestrator.latest_quality_output += message.text

    @on(DiffUpdated)
    def handle_diff(self, message: DiffUpdated) -> None:
        self.query_one(StreamTabs).set_diff(message.diff_text)

    @on(CycleCompleted)
    def handle_cycle(self, message: CycleCompleted) -> None:
        self.query_one(CycleTable).add_record(message.cycle_record)
        self.query_one(StatsBar).set_stats(self.store.get_stats())
        self.notify(f"Cycle {message.cycle_record.cycle_number}: {message.cycle_record.status}")

    @on(TimerUpdated)
    def handle_timer(self, message: TimerUpdated) -> None:
        self.query_one(HeaderHud).update_timer(message.remaining_seconds, message.paused)

    def action_tab(self, index: int) -> None:
        self.query_one(StreamTabs).active = ["tab-agent", "tab-diff", "tab-quality", "tab-brain"][index]

    async def action_toggle_pause(self) -> None:
        if self.orchestrator:
            await self.orchestrator.toggle_pause()

    async def action_add_time(self) -> None:
        if self.orchestrator:
            await self.orchestrator.adjust_timer(15)

    async def action_remove_time(self) -> None:
        if self.orchestrator:
            await self.orchestrator.adjust_timer(-15)

    async def action_kill_stage(self) -> None:
        if self.orchestrator:
            await self.orchestrator.kill_current_stage()

    async def action_rollback(self) -> None:
        if self.orchestrator:
            await self.orchestrator.force_rollback()

    async def action_intervention(self) -> None:
        result = await self.push_screen_wait(InterventionModal())
        if result and self.orchestrator:
            try:
                await self.orchestrator.submit_intervention(*result)
                self.notify("Human intervention queued for the next cycle")
            except ValueError as exc:
                self.notify(str(exc), severity="error")

    @on(CycleTable.RowSelected)
    async def handle_cycle_selected(self, event: CycleTable.RowSelected) -> None:
        record = self.query_one(CycleTable).selected_record()
        if record is None:
            return
        commit_show = ""
        if record.commit_hash:
            try:
                import asyncio
                commit_show = await asyncio.to_thread(self.git.get_commit_show, record.commit_hash)
            except Exception as exc:
                commit_show = f"Unable to load git show: {exc}"
        await self.push_screen(CycleDetailModal(record, commit_show))

    async def action_quit_maestro(self) -> None:
        if self.orchestrator:
            await self.orchestrator.stop()
        self.exit()
