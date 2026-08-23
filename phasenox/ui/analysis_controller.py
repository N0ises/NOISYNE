"""Application-boundary coordinator for asynchronous analysis execution."""

from __future__ import annotations

from PySide6.QtCore import QObject, Signal

from .analyze_state import AnalysisFormState
from .contracts import AnalysisCommand, DesktopApplicationAdapter
from .errors import analysis_error
from .presentation_store import PresentationStore
from .worker_binding import WorkerStateBinding
from .workers import WorkerExecutor, WorkerTask


class AnalysisController(QObject):
    task_created = Signal(object)

    def __init__(
        self,
        adapter: DesktopApplicationAdapter,
        store: PresentationStore,
        executor: WorkerExecutor,
    ) -> None:
        super().__init__()
        self._adapter = adapter
        self._store = store
        self._executor = executor

    def execute(self, form: AnalysisFormState) -> WorkerTask:
        command = form.build_command()
        self._update_selection(command)
        task = self._executor.create(
            "analysis",
            lambda: self._adapter.analyze(command),
            error_mapper=lambda exc, operation_id: analysis_error(
                exc,
                operation_id=operation_id,
            ),
        )
        WorkerStateBinding(self._store).bind(task, capture_analysis_result=True)
        self.task_created.emit(task)
        self._executor.start(task)
        return task

    def _update_selection(self, command: AnalysisCommand) -> None:
        session = self._store.state.session.select_audio(command.source_path)
        session = session.select_references(command.reference_paths)
        self._store.set_session(session)

