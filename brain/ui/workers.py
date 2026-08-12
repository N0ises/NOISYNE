"""Small QThreadPool foundation for blocking application calls."""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any
from uuid import uuid4

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal, Slot

from .contracts import OperationHandle, OperationState, UiError
from .errors import unexpected_error

logger = logging.getLogger(__name__)
ErrorMapper = Callable[[BaseException, str], UiError]


class WorkerSignals(QObject):
    started = Signal(object)
    succeeded = Signal(object)
    failed = Signal(object)
    finished = Signal(object)


class WorkerTask(QRunnable):
    """Run one callable without claiming in-flight cancellation or progress."""

    def __init__(
        self,
        operation_id: str,
        kind: str,
        function: Callable[[], Any],
        error_mapper: ErrorMapper | None = None,
    ) -> None:
        super().__init__()
        self.handle = OperationHandle(operation_id=operation_id, kind=kind)
        self._function = function
        self._error_mapper = error_mapper
        self.signals = WorkerSignals()

    @Slot()
    def run(self) -> None:
        running = OperationHandle(
            operation_id=self.handle.operation_id,
            kind=self.handle.kind,
            state=OperationState.RUNNING,
        )
        self.signals.started.emit(running)
        try:
            result = self._function()
        except Exception as exc:
            logger.exception("Desktop worker operation %s failed", self.handle.operation_id)
            error = (
                self._error_mapper(exc, self.handle.operation_id)
                if self._error_mapper is not None
                else unexpected_error(exc, operation_id=self.handle.operation_id)
            )
            self.signals.failed.emit(error)
        else:
            self.signals.succeeded.emit(result)
        finally:
            self.signals.finished.emit(self.handle.operation_id)


class WorkerExecutor(QObject):
    def __init__(self, pool: QThreadPool | None = None) -> None:
        super().__init__()
        self._pool = pool or QThreadPool.globalInstance()
        self._active: dict[str, WorkerTask] = {}

    def submit(self, kind: str, function: Callable[[], Any]) -> WorkerTask:
        task = self.create(kind, function)
        self.start(task)
        return task

    def create(
        self,
        kind: str,
        function: Callable[[], Any],
        *,
        error_mapper: ErrorMapper | None = None,
    ) -> WorkerTask:
        """Create and retain a task so UI bindings can be attached before it starts."""
        operation_id = uuid4().hex
        task = WorkerTask(operation_id, kind, function, error_mapper)
        self._active[operation_id] = task
        task.signals.finished.connect(self._active.pop)
        return task

    def start(self, task: WorkerTask) -> None:
        self._pool.start(task)

    def wait_for_done(self, timeout_ms: int = -1) -> bool:
        return self._pool.waitForDone(timeout_ms)
