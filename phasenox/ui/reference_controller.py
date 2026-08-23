"""Application-boundary coordinator for reference comparison."""

from __future__ import annotations

from PySide6.QtCore import QObject, Signal

from .contracts import DesktopApplicationAdapter, ReferenceComparisonCommand
from .errors import reference_error
from .presentation_store import PresentationStore
from .reference_state import ReferenceFormState
from .worker_binding import WorkerStateBinding
from .workers import WorkerExecutor, WorkerTask


class ReferenceController(QObject):
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

    def execute(self, form: ReferenceFormState) -> WorkerTask:
        command = form.build_command()
        self._update_selection(command)
        task = self._executor.create(
            "reference_comparison",
            lambda: self._adapter.compare_references(command),
            error_mapper=lambda exc, operation_id: reference_error(
                exc,
                operation_id=operation_id,
            ),
        )
        WorkerStateBinding(self._store).bind(task, capture_reference_result=True)
        self.task_created.emit(task)
        self._executor.start(task)
        return task

    def _update_selection(self, command: ReferenceComparisonCommand) -> None:
        session = self._store.state.session.select_audio(command.current_path)
        session = session.select_references(command.reference_paths)
        self._store.set_session(session)

