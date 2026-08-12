from __future__ import annotations

from PySide6.QtCore import QThreadPool

from brain.ui.contracts import AnalysisViewResult, OperationHandle, OperationState, UiErrorCategory
from brain.ui.presentation_state import ResultPhase
from brain.ui.presentation_store import PresentationStore
from brain.ui.worker_binding import WorkerStateBinding
from brain.ui.workers import WorkerTask


def test_worker_success_drives_ordered_analysis_state(qtbot, tmp_path) -> None:
    result = AnalysisViewResult(tmp_path / "audio.wav", "ok", "mix", 90.0, "summary")
    task = WorkerTask("success-id", "analysis", lambda: result)
    store = PresentationStore()
    WorkerStateBinding(store).bind(task, capture_analysis_result=True)

    with qtbot.waitSignal(task.signals.finished, timeout=3000):
        QThreadPool.globalInstance().start(task)

    assert store.state.operation.state is OperationState.COMPLETED
    assert store.state.operation.last_sequence == 2
    assert store.state.result.phase is ResultPhase.SUCCESS
    assert store.state.result.result == result


def test_worker_failure_drives_error_and_notification(qtbot) -> None:
    def fail() -> None:
        raise RuntimeError("failed")

    task = WorkerTask("failure-id", "analysis", fail)
    store = PresentationStore()
    WorkerStateBinding(store).bind(task, capture_analysis_result=True)

    with qtbot.waitSignal(task.signals.finished, timeout=3000):
        QThreadPool.globalInstance().start(task)

    assert store.state.operation.state is OperationState.FAILED
    assert store.state.result.error is not None
    assert store.state.result.error.category is UiErrorCategory.INTERNAL
    assert store.state.notifications.active[-1].operation_id == "failure-id"


def test_worker_binding_ignores_mismatched_started_handle() -> None:
    task = WorkerTask("expected-id", "analysis", lambda: None)
    store = PresentationStore()
    WorkerStateBinding(store).bind(task)

    task.signals.started.emit(OperationHandle("different-id", "analysis", OperationState.RUNNING))

    assert store.state.operation.state is OperationState.QUEUED
    assert store.state.result.phase is ResultPhase.EMPTY
