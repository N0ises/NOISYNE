from __future__ import annotations

import threading
import time

from PySide6.QtCore import QThreadPool, QTimer
from PySide6.QtWidgets import QLabel

from brain.ui.contracts import (
    Availability,
    CapabilityLifecycle,
    CapabilitySnapshot,
    OperationState,
    ReferenceViewResult,
    ReportDescriptor,
    UiErrorCategory,
)
from brain.ui.presentation_state import PresentationState, ResultPhase, RuntimePresentationState
from brain.ui.presentation_store import PresentationStore
from brain.ui.reference_controller import ReferenceController
from brain.ui.reference_page import ReferencePage
from brain.ui.reference_state import ReferenceFormState
from brain.ui.workers import WorkerExecutor


class FakeReferenceAdapter:
    def __init__(self, result=None, error=None, delay=0.0) -> None:
        self.result = result
        self.error = error
        self.delay = delay
        self.command = None
        self.thread_id = None

    def compare_references(self, command):
        self.command = command
        self.thread_id = threading.get_ident()
        if self.delay:
            time.sleep(self.delay)
        if self.error:
            raise self.error
        return self.result


def _review(tmp_path) -> ReferenceFormState:
    current = tmp_path / "current.wav"
    first = tmp_path / "first.wav"
    second = tmp_path / "second.wav"
    for path in (current, first, second):
        path.write_bytes(b"audio")
    capability = CapabilitySnapshot(
        "reference_comparison",
        "Reference comparison",
        CapabilityLifecycle.PRODUCTION,
        Availability.AVAILABLE,
    )
    return (
        ReferenceFormState.initial((capability,))
        .select_current(current)
        .add_references((first, second))
        .review()
    )


def test_reference_worker_binds_before_start_runs_off_gui_and_retains_result(
    qtbot, tmp_path
) -> None:
    form = _review(tmp_path)
    report_path = tmp_path / "reference_report.json"
    report_path.write_text("{}", encoding="utf-8")
    result = ReferenceViewResult(
        form.current_path,
        form.reference_paths,
        "ok",
        88.0,
        0.9,
        reports=(ReportDescriptor("reference_comparison", "json", report_path, "JSON"),),
    )
    adapter = FakeReferenceAdapter(result=result, delay=0.02)
    store = PresentationStore()
    executor = WorkerExecutor(QThreadPool())
    controller = ReferenceController(adapter, store, executor)
    state_at_creation = []
    controller.task_created.connect(
        lambda _task: state_at_creation.append(store.state.operation.state)
    )
    gui_thread = threading.get_ident()

    controller.execute(form)
    qtbot.waitUntil(lambda: store.state.operation.is_terminal, timeout=3000)
    executor.wait_for_done()

    assert state_at_creation == [OperationState.QUEUED]
    assert adapter.thread_id != gui_thread
    assert store.state.operation.state is OperationState.COMPLETED
    assert store.state.reference_result.phase is ResultPhase.SUCCESS
    assert store.state.reference_result.result is result
    assert store.state.session.last_reference_result is result
    assert store.state.session.selected_audio == form.current_path
    assert store.state.session.selected_references == form.reference_paths
    assert store.state.session.recent_reports[0].descriptor.path == report_path


def test_reference_warning_is_partial_success_and_failure_is_structured(qtbot, tmp_path) -> None:
    form = _review(tmp_path)
    warning_result = ReferenceViewResult(
        form.current_path,
        form.reference_paths,
        "degraded",
        None,
        None,
        warnings=("Reference comparison returned partial data.",),
    )
    store = PresentationStore()
    warning_executor = WorkerExecutor(QThreadPool())
    warning_controller = ReferenceController(
        FakeReferenceAdapter(result=warning_result), store, warning_executor
    )

    warning_controller.execute(form)
    qtbot.waitUntil(lambda: store.state.operation.is_terminal, timeout=3000)
    warning_executor.wait_for_done()

    assert store.state.reference_result.phase is ResultPhase.WARNING
    assert store.state.reference_result.result is warning_result
    assert store.state.notifications.active[-1].message == warning_result.warnings[0]

    failure_store = PresentationStore()
    failure_executor = WorkerExecutor(QThreadPool())
    failure_controller = ReferenceController(
        FakeReferenceAdapter(error=ValueError("backend rejected tracks")),
        failure_store,
        failure_executor,
    )
    failure_controller.execute(form)
    qtbot.waitUntil(lambda: failure_store.state.operation.is_terminal, timeout=3000)
    failure_executor.wait_for_done()

    assert failure_store.state.reference_result.phase is ResultPhase.FAILURE
    assert failure_store.state.reference_result.error.category is UiErrorCategory.VALIDATION


def test_reference_progress_is_indeterminate_noncancellable_and_gui_responsive(
    qtbot, tmp_path
) -> None:
    form = _review(tmp_path)
    result = ReferenceViewResult(form.current_path, form.reference_paths, "ok", 88.0, 0.9)
    store = PresentationStore()
    executor = WorkerExecutor(QThreadPool())
    controller = ReferenceController(
        FakeReferenceAdapter(result=result, delay=0.2),
        store,
        executor,
    )
    timer_fired = []
    QTimer.singleShot(20, lambda: timer_fired.append(True))

    controller.execute(form)
    qtbot.waitUntil(lambda: store.state.operation.state is OperationState.RUNNING, timeout=1000)

    assert store.state.operation.progress is None
    assert not store.state.operation.cancellable
    assert not store.request_cancellation()
    qtbot.waitUntil(lambda: bool(timer_fired), timeout=1000)
    qtbot.waitUntil(lambda: store.state.operation.is_terminal, timeout=3000)
    executor.wait_for_done()


def test_fake_adapter_completes_full_reference_page_workflow(qtbot, tmp_path) -> None:
    form = _review(tmp_path)
    result = ReferenceViewResult(form.current_path, form.reference_paths, "ok", 91.25, 0.95)
    capability = CapabilitySnapshot(
        "reference_comparison",
        "Reference comparison",
        CapabilityLifecycle.PRODUCTION,
        Availability.AVAILABLE,
    )
    store = PresentationStore(
        PresentationState(runtime=RuntimePresentationState(capabilities=(capability,)))
    )
    executor = WorkerExecutor(QThreadPool())
    controller = ReferenceController(FakeReferenceAdapter(result=result), store, executor)
    page = ReferencePage()
    qtbot.addWidget(page)
    store.subscribe(page.render)
    page.select_current(form.current_path)
    page.add_references(form.reference_paths)
    page.comparison_requested.connect(controller.execute)

    page.review()
    page.compare_button.click()
    qtbot.waitUntil(lambda: store.state.operation.is_terminal, timeout=3000)
    executor.wait_for_done()

    assert store.state.reference_result.result is result
    assert page.view_result_button.isVisible() or not page.isVisible()
    page.view_result_button.click()
    similarity = page.result_view.findChild(QLabel, "referenceResultSimilarity")
    assert similarity is not None
    assert similarity.text() == "Similarity (raw): 91.25"
