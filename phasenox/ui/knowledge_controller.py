"""Application-boundary coordinator for Knowledge search."""

from __future__ import annotations

from PySide6.QtCore import QObject, Signal

from .contracts import DesktopApplicationAdapter, KnowledgeQuery
from .errors import knowledge_error
from .presentation_store import PresentationStore
from .worker_binding import WorkerStateBinding
from .workers import WorkerExecutor, WorkerTask


class KnowledgeController(QObject):
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

    def execute(self, query: KnowledgeQuery) -> WorkerTask:
        task = self._executor.create(
            "knowledge_search",
            lambda: self._adapter.search_knowledge(query),
            error_mapper=lambda exc, operation_id: knowledge_error(exc, operation_id=operation_id),
        )
        WorkerStateBinding(self._store).bind(task, capture_knowledge_result=True)
        self.task_created.emit(task)
        self._executor.start(task)
        return task

