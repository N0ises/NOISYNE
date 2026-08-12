"""Presentation-safe settings snapshot and runtime refresh coordinator."""

from __future__ import annotations

from PySide6.QtCore import QObject, Signal

from .contracts import DesktopApplicationAdapter, RuntimeStatus, SettingsSnapshot
from .errors import runtime_refresh_error, settings_error
from .presentation_store import PresentationStore
from .workers import WorkerExecutor, WorkerTask


class SettingsController(QObject):
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

    def refresh_settings(self) -> None:
        """Read the process-global V1 snapshot; this is a trivial in-memory call."""
        self._store.set_settings_loading()
        try:
            snapshot = self._adapter.settings_snapshot()
            if not isinstance(snapshot, SettingsSnapshot):
                raise TypeError("Invalid settings snapshot DTO")
        except Exception as exc:  # noqa: BLE001 - adapter boundary maps safe UI errors
            self._store.set_settings_error(settings_error(exc))
            return
        self._store.set_settings_snapshot(snapshot)

    def refresh_runtime(self) -> WorkerTask:
        self._store.set_runtime_loading()
        task = self._executor.create(
            "runtime_status_refresh",
            self._adapter.runtime_status,
            error_mapper=lambda exc, operation_id: runtime_refresh_error(
                exc, operation_id=operation_id
            ),
        )

        def succeeded(result: object) -> None:
            if isinstance(result, RuntimeStatus):
                self._store.set_runtime_status(result)
            else:
                self._store.set_runtime_unknown()
                self._store.add_error(
                    runtime_refresh_error(
                        TypeError("Invalid runtime status DTO"),
                        operation_id=task.handle.operation_id,
                    )
                )

        def failed(error) -> None:
            self._store.set_runtime_unknown()
            self._store.add_error(error)

        task.signals.succeeded.connect(succeeded)
        task.signals.failed.connect(failed)
        self.task_created.emit(task)
        self._executor.start(task)
        return task
