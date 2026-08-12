from __future__ import annotations

import threading
import time
from pathlib import Path

from PySide6.QtCore import QThreadPool, QTimer

from brain.ui.analysis_controller import AnalysisController
from brain.ui.analyze_page import AnalyzePage
from brain.ui.analyze_state import AnalysisFormState
from brain.ui.contracts import (
    AnalysisCommand,
    AnalysisViewResult,
    OperationState,
    ReportDescriptor,
    UiErrorCategory,
)
from brain.ui.presentation_state import ResultPhase
from brain.ui.presentation_store import PresentationStore
from brain.ui.workers import WorkerExecutor


class FakeAnalysisAdapter:
    def __init__(self, result=None, error: Exception | None = None, delay: float = 0.0) -> None:
        self.result = result
        self.error = error
        self.delay = delay
        self.command: AnalysisCommand | None = None
        self.thread_id: int | None = None

    def analyze(self, command: AnalysisCommand):
        self.command = command
        self.thread_id = threading.get_ident()
        if self.delay:
            time.sleep(self.delay)
        if self.error:
            raise self.error
        return self.result


def _review(source: Path, reference: Path | None = None) -> AnalysisFormState:
    return AnalysisFormState.initial().select_source(source).select_reference(reference).review()


def _controller(adapter, store, pool) -> tuple[AnalysisController, WorkerExecutor]:
    executor = WorkerExecutor(pool)
    return AnalysisController(adapter, store, executor), executor


def test_success_runs_off_gui_thread_and_updates_session(qtbot, tmp_path) -> None:
    source = tmp_path / "source.wav"
    reference = tmp_path / "reference.wav"
    report_path = tmp_path / "report.json"
    source.write_bytes(b"source")
    reference.write_bytes(b"reference")
    report_path.write_text("{}", encoding="utf-8")
    result = AnalysisViewResult(
        source,
        "ok",
        "mix",
        92.0,
        "summary",
        reports=(ReportDescriptor("analysis", "json", report_path, "Analysis JSON"),),
    )
    adapter = FakeAnalysisAdapter(result)
    store = PresentationStore()
    pool = QThreadPool()
    controller, executor = _controller(adapter, store, pool)
    main_thread = threading.get_ident()

    controller.execute(_review(source, reference))
    qtbot.waitUntil(lambda: store.state.operation.is_terminal, timeout=3000)
    executor.wait_for_done()

    assert adapter.thread_id != main_thread
    assert adapter.command.source_path == source
    assert adapter.command.reference_paths == (reference,)
    assert store.state.operation.state is OperationState.COMPLETED
    assert store.state.result.phase is ResultPhase.SUCCESS
    assert store.state.result.result == result
    assert store.state.session.selected_audio == source
    assert store.state.session.selected_references == (reference,)
    assert store.state.session.last_analysis_result == result
    assert store.state.session.recent_analyses[0].source_path == source
    assert store.state.session.recent_reports[0].descriptor.path == report_path


def test_warning_result_is_retained_as_partial_success(qtbot, tmp_path) -> None:
    source = tmp_path / "source.wav"
    source.write_bytes(b"source")
    result = AnalysisViewResult(
        source,
        "degraded",
        "mix",
        80.0,
        "partial",
        warnings=("Optional reasoning was unavailable.",),
    )
    adapter = FakeAnalysisAdapter(result)
    store = PresentationStore()
    controller, executor = _controller(adapter, store, QThreadPool())

    controller.execute(_review(source))
    qtbot.waitUntil(lambda: store.state.operation.is_terminal, timeout=3000)
    executor.wait_for_done()

    assert store.state.result.phase is ResultPhase.WARNING
    assert store.state.result.result == result
    assert store.state.session.last_analysis_result == result
    assert store.state.notifications.active[-1].message == result.warnings[0]


def test_failure_produces_structured_error_state(qtbot, tmp_path) -> None:
    source = tmp_path / "source.wav"
    source.write_bytes(b"source")
    adapter = FakeAnalysisAdapter(error=ValueError("backend rejected audio"))
    store = PresentationStore()
    controller, executor = _controller(adapter, store, QThreadPool())

    controller.execute(_review(source))
    qtbot.waitUntil(lambda: store.state.operation.is_terminal, timeout=3000)
    executor.wait_for_done()

    assert store.state.operation.state is OperationState.FAILED
    assert store.state.result.phase is ResultPhase.FAILURE
    assert store.state.result.error is not None
    assert store.state.result.error.category is UiErrorCategory.VALIDATION
    assert store.state.notifications.active[-1].error is store.state.result.error


def test_running_analysis_is_indeterminate_non_cancellable_and_gui_responsive(
    qtbot, tmp_path
) -> None:
    source = tmp_path / "source.wav"
    source.write_bytes(b"source")
    result = AnalysisViewResult(source, "ok", "mix", 90.0, "summary")
    adapter = FakeAnalysisAdapter(result=result, delay=0.2)
    store = PresentationStore()
    controller, executor = _controller(adapter, store, QThreadPool())
    timer_fired = []
    QTimer.singleShot(20, lambda: timer_fired.append(True))

    controller.execute(_review(source))
    qtbot.waitUntil(
        lambda: store.state.operation.state is OperationState.RUNNING,
        timeout=1000,
    )

    assert store.state.operation.progress is None
    assert not store.state.operation.cancellable
    assert not store.request_cancellation()
    qtbot.waitUntil(lambda: bool(timer_fired), timeout=1000)
    qtbot.waitUntil(lambda: store.state.operation.is_terminal, timeout=3000)
    executor.wait_for_done()


def test_fake_adapter_completes_confirmed_page_workflow(qtbot, tmp_path) -> None:
    source = tmp_path / "source.wav"
    source.write_bytes(b"source")
    result = AnalysisViewResult(source, "ok", "mix", 90.0, "summary")
    adapter = FakeAnalysisAdapter(result=result, delay=0.02)
    store = PresentationStore()
    controller, executor = _controller(adapter, store, QThreadPool())
    page = AnalyzePage()
    qtbot.addWidget(page)
    page.analysis_requested.connect(controller.execute)
    observed_states = []
    store.subscribe(lambda state: observed_states.append(state.operation.state))

    page.select_source(source)
    page.review()
    page.confirm_button.click()
    qtbot.waitUntil(lambda: store.state.operation.is_terminal, timeout=3000)
    executor.wait_for_done()

    assert OperationState.QUEUED in observed_states
    assert OperationState.RUNNING in observed_states
    assert observed_states[-1] is OperationState.COMPLETED
    assert adapter.command == page.form_state.build_command()
    assert store.state.session.last_analysis_result == result
