"""Application-boundary coordinator for report preview, export, and folder opening."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from PySide6.QtCore import QObject, QUrl, Signal
from PySide6.QtGui import QDesktopServices

from .contracts import DesktopApplicationAdapter, ReportDescriptor, ReportExportCommand
from .errors import report_error, report_open_error
from .presentation_store import PresentationStore
from .worker_binding import WorkerStateBinding
from .workers import WorkerExecutor, WorkerTask

DirectoryOpener = Callable[[Path], bool]


def _open_directory(path: Path) -> bool:
    return QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))


class ReportController(QObject):
    task_created = Signal(object)

    def __init__(
        self,
        adapter: DesktopApplicationAdapter,
        store: PresentationStore,
        executor: WorkerExecutor,
        *,
        directory_opener: DirectoryOpener = _open_directory,
    ) -> None:
        super().__init__()
        self._adapter = adapter
        self._store = store
        self._executor = executor
        self._directory_opener = directory_opener

    def preview(self, descriptor: ReportDescriptor) -> WorkerTask:
        task = self._executor.create(
            "report_preview",
            lambda: self._adapter.load_report(descriptor),
            error_mapper=lambda exc, operation_id: report_error(
                exc, operation_id=operation_id, action="preview"
            ),
        )
        WorkerStateBinding(self._store).bind(task, capture_report_preview=True)
        self.task_created.emit(task)
        self._executor.start(task)
        return task

    def export(self, command: ReportExportCommand) -> WorkerTask:
        task = self._executor.create(
            "report_export",
            lambda: self._adapter.export_report(command),
            error_mapper=lambda exc, operation_id: report_error(
                exc, operation_id=operation_id, action="export"
            ),
        )
        WorkerStateBinding(self._store).bind(task, capture_report_export=True)
        self.task_created.emit(task)
        self._executor.start(task)
        return task

    def open_directory(self, path: Path) -> bool:
        if not path.exists() or not path.is_dir() or not self._directory_opener(path):
            self._store.add_error(report_open_error())
            return False
        return True
