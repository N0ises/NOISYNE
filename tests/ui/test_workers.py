from __future__ import annotations

from PySide6.QtCore import QThreadPool

from phasenox.ui.contracts import UiError, UiErrorCategory
from phasenox.ui.workers import WorkerTask


def test_worker_emits_success(qtbot) -> None:
    task = WorkerTask("success-id", "test", lambda: 42)

    with qtbot.waitSignal(task.signals.succeeded, timeout=3000) as signal:
        QThreadPool.globalInstance().start(task)

    assert signal.args == [42]


def test_worker_translates_failure(qtbot) -> None:
    def fail() -> None:
        raise RuntimeError("worker failed")

    task = WorkerTask("failure-id", "test", fail)

    with qtbot.waitSignal(task.signals.failed, timeout=3000) as signal:
        QThreadPool.globalInstance().start(task)

    error = signal.args[0]
    assert isinstance(error, UiError)
    assert error.category is UiErrorCategory.INTERNAL
    assert error.operation_id == "failure-id"
    assert error.technical_detail == "RuntimeError"

