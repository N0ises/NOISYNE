from __future__ import annotations

import gc
import threading
import time
import tracemalloc
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

import pytest
from PySide6.QtCore import QThreadPool, QTimer

from brain.ui.analyze_state import AnalysisFormState
from brain.ui.app import build_main_window
from brain.ui.contracts import (
    AnalysisViewResult,
    Availability,
    CapabilityLifecycle,
    CapabilitySnapshot,
    KnowledgeQuery,
    KnowledgeResultItem,
    KnowledgeSearchResult,
    OperationState,
    ReferenceSimilarity,
    ReferenceViewResult,
    ReportDescriptor,
    ReportPreview,
    RuntimeState,
)
from brain.ui.performance_probe import collect_desktop_metrics
from brain.ui.presentation_state import (
    NAVIGATION_ORDER,
    PageId,
    PresentationState,
    ResultPhase,
    RuntimePresentationState,
)
from brain.ui.presentation_store import PresentationStore
from brain.ui.reference_state import ReferenceFormState
from brain.ui.state import ApplicationStateStore
from brain.ui.voice_contracts import (
    ConversationHistory,
    TranscriptRole,
    VoicePresentationState,
    transcript_item,
)
from brain.ui.workers import WorkerExecutor


def _analysis_form(source: Path) -> AnalysisFormState:
    return AnalysisFormState.initial().select_source(source).review()


def _reference_form(current: Path, references: tuple[Path, ...]) -> ReferenceFormState:
    capability = CapabilitySnapshot(
        "reference_comparison",
        "Reference comparison",
        CapabilityLifecycle.IMPLEMENTED,
        Availability.AVAILABLE,
    )
    return (
        ReferenceFormState.initial((capability,))
        .select_current(current)
        .add_references(references)
        .review()
    )


def _wait_for_task(qtbot, store: PresentationStore, executor: WorkerExecutor, task) -> None:
    qtbot.waitUntil(
        lambda: store.state.operation.operation_id == task.handle.operation_id
        and store.state.operation.is_terminal,
        timeout=3000,
    )
    qtbot.waitUntil(lambda: task.handle.operation_id not in executor._active, timeout=3000)


@pytest.mark.performance
def test_heavy_adapter_calls_run_off_gui_and_publish_back_on_gui_thread(
    qtbot, fake_adapter, tmp_path
) -> None:
    source = tmp_path / "source.wav"
    reference = tmp_path / "reference.wav"
    report_path = tmp_path / "report.json"
    for path in (source, reference):
        path.write_bytes(b"audio")
    report_path.write_text("{}", encoding="utf-8")

    results = {
        "analysis": AnalysisViewResult(source, "ok", "mix", 90.0, "measured"),
        "reference": ReferenceViewResult(source, (reference,), "ok", 90.0, 0.9),
        "knowledge": KnowledgeSearchResult(
            "headroom",
            (KnowledgeResultItem("Keep headroom.", "guide.md", 1, 0.9, 0.8),),
        ),
    }
    descriptor = ReportDescriptor("analysis", "json", report_path, "Analysis JSON")
    results["report"] = ReportPreview(descriptor, "{}", 2, datetime(2026, 1, 1, tzinfo=UTC))
    adapter_threads: dict[str, int] = {}

    def recorded(name: str):
        def call(_argument):
            adapter_threads[name] = threading.get_ident()
            return results[name]

        return call

    fake_adapter.analyze = recorded("analysis")
    fake_adapter.compare_references = recorded("reference")
    fake_adapter.search_knowledge = recorded("knowledge")
    fake_adapter.load_report = recorded("report")

    store = PresentationStore()
    executor = WorkerExecutor(QThreadPool())
    window = build_main_window(fake_adapter, ApplicationStateStore(), store, executor)
    qtbot.addWidget(window)
    gui_thread = threading.get_ident()
    publication_threads: list[int] = []
    store.subscribe(lambda _state: publication_threads.append(threading.get_ident()))
    publication_threads.clear()

    operations = (
        lambda: window._analysis_controller.execute(_analysis_form(source)),
        lambda: window._reference_controller.execute(_reference_form(source, (reference,))),
        lambda: window._knowledge_controller.execute(KnowledgeQuery("headroom")),
        lambda: window._report_controller.preview(descriptor),
    )
    for operation in operations:
        task = operation()
        _wait_for_task(qtbot, store, executor, task)

    assert set(adapter_threads) == {"analysis", "reference", "knowledge", "report"}
    assert all(thread_id != gui_thread for thread_id in adapter_threads.values())
    assert publication_threads
    assert set(publication_threads) == {gui_thread}
    assert executor._active == {}


@pytest.mark.performance
def test_slow_analysis_keeps_event_loop_progress_and_cancellation_truthful(
    qtbot, fake_adapter, tmp_path
) -> None:
    source = tmp_path / "slow.wav"
    source.write_bytes(b"audio")
    gate = threading.Event()
    adapter_started = threading.Event()
    adapter_times: dict[str, float] = {}

    def slow_analysis(_command):
        adapter_times["start"] = time.perf_counter()
        adapter_started.set()
        assert gate.wait(2.0)
        adapter_times["end"] = time.perf_counter()
        return AnalysisViewResult(source, "ok", "mix", 91.0, "slow fixture")

    fake_adapter.analyze = slow_analysis
    store = PresentationStore()
    executor = WorkerExecutor(QThreadPool())
    window = build_main_window(fake_adapter, ApplicationStateStore(), store, executor)
    qtbot.addWidget(window)
    window.show()
    ticks: list[float] = []
    timer = QTimer(window)
    timer.setInterval(5)

    def tick() -> None:
        ticks.append(time.perf_counter())
        if len(ticks) >= 3:
            gate.set()

    timer.timeout.connect(tick)
    timer.start()
    issued = time.perf_counter()
    task = window._analysis_controller.execute(_analysis_form(source))
    queued = time.perf_counter()

    assert store.state.operation.state is OperationState.QUEUED
    assert store.state.result.phase is ResultPhase.LOADING
    assert not store.state.operation.cancellable
    cancel_started = time.perf_counter()
    assert not store.request_cancellation()
    cancellation_latency_ms = (time.perf_counter() - cancel_started) * 1000
    qtbot.waitUntil(adapter_started.is_set, timeout=1000)
    qtbot.waitUntil(lambda: len(ticks) >= 3, timeout=1000)
    _wait_for_task(qtbot, store, executor, task)
    finished = time.perf_counter()
    timer.stop()

    assert window._operation_surface.progress.isHidden()
    assert len(ticks) >= 3
    assert queued - issued < 0.5
    assert adapter_times["start"] >= issued
    assert adapter_times["end"] <= finished
    assert cancellation_latency_ms < 100.0
    assert store.state.result.phase is ResultPhase.SUCCESS


@pytest.mark.performance
def test_local_probe_has_broad_regression_budgets() -> None:
    report = collect_desktop_metrics(render_iterations=5, navigation_cycles=3)

    assert report.application_creation_ms < 5_000
    assert report.main_window_construction_ms < 5_000
    assert report.initial_render_ms < 1_000
    assert report.offscreen_ready_ms < 1_000
    assert report.mean_current_page_render_ms < 500
    assert report.navigation_cycle_ms < 2_000
    assert report.navigation_python_growth_bytes < 10 * 1024 * 1024
    assert report.page_count == len(NAVIGATION_ORDER)
    assert report.subscriber_count == 1


@pytest.mark.performance
@pytest.mark.stress
def test_navigation_stress_keeps_pages_subscribers_and_memory_bounded(qtbot, fake_adapter) -> None:
    store = PresentationStore()
    window = build_main_window(fake_adapter, ApplicationStateStore(), store)
    qtbot.addWidget(window)
    pages = {page: window._page_host.page(page) for page in NAVIGATION_ORDER}
    subscribers = len(store._subscribers)
    tracemalloc.start()
    gc.collect()
    before = tracemalloc.get_traced_memory()[0]
    started = time.perf_counter()

    for _ in range(60):
        for page in NAVIGATION_ORDER:
            store.navigate(page)
    qtbot.wait(1)
    elapsed = time.perf_counter() - started
    gc.collect()
    after = tracemalloc.get_traced_memory()[0]
    tracemalloc.stop()

    assert elapsed < 20.0
    assert {page: window._page_host.page(page) for page in NAVIGATION_ORDER} == pages
    assert len(store._subscribers) == subscribers
    assert len(window._page_host._pages) == len(NAVIGATION_ORDER)
    assert after - before < 10 * 1024 * 1024


@pytest.mark.performance
@pytest.mark.stress
def test_repeated_analysis_and_knowledge_release_workers_and_bound_history(
    qtbot, fake_adapter, tmp_path
) -> None:
    source = tmp_path / "repeat.wav"
    source.write_bytes(b"audio")
    fake_adapter.analyze = lambda _command: AnalysisViewResult(source, "ok", "mix", 90.0, "repeat")
    fake_adapter.search_knowledge = lambda query: KnowledgeSearchResult(
        query.text,
        (KnowledgeResultItem("bounded", "guide.md", 1, 0.8, None),),
    )
    store = PresentationStore()
    executor = WorkerExecutor(QThreadPool())
    window = build_main_window(fake_adapter, ApplicationStateStore(), store, executor)
    qtbot.addWidget(window)

    for _ in range(25):
        task = window._analysis_controller.execute(_analysis_form(source))
        _wait_for_task(qtbot, store, executor, task)
    for index in range(25):
        task = window._knowledge_controller.execute(KnowledgeQuery(f"query {index}"))
        _wait_for_task(qtbot, store, executor, task)

    assert executor._active == {}
    assert len(store.state.session.recent_analyses) <= store.state.session.recent_limit
    assert len(store.state.session.recent_knowledge_queries) == store.state.session.recent_limit
    assert len(store.state.notifications.active) == 0


@pytest.mark.performance
@pytest.mark.stress
def test_repeated_failures_reference_and_report_preview_bound_retained_resources(
    qtbot, fake_adapter, tmp_path
) -> None:
    source = tmp_path / "workflow.wav"
    reference = tmp_path / "reference.wav"
    report_path = tmp_path / "report.json"
    source.write_bytes(b"audio")
    reference.write_bytes(b"audio")
    report_path.write_text("{}", encoding="utf-8")
    reference_form = _reference_form(source, (reference,))
    descriptor = ReportDescriptor("analysis", "json", report_path, "Analysis JSON")
    fake_adapter.compare_references = lambda command: ReferenceViewResult(
        command.current_path, command.reference_paths, "ok", 88.0, 0.8
    )
    fake_adapter.load_report = lambda item: ReportPreview(
        item, "{}", 2, datetime(2026, 1, 1, tzinfo=UTC)
    )

    def fail_analysis(_command):
        raise ValueError("deterministic repeated failure")

    fake_adapter.analyze = fail_analysis
    store = PresentationStore()
    executor = WorkerExecutor(QThreadPool())
    window = build_main_window(fake_adapter, ApplicationStateStore(), store, executor)
    qtbot.addWidget(window)
    tracemalloc.start()
    gc.collect()
    before = tracemalloc.get_traced_memory()[0]

    for _ in range(15):
        task = window._analysis_controller.execute(_analysis_form(source))
        _wait_for_task(qtbot, store, executor, task)
    for _ in range(15):
        task = window._reference_controller.execute(reference_form)
        _wait_for_task(qtbot, store, executor, task)
    for _ in range(15):
        task = window._report_controller.preview(descriptor)
        _wait_for_task(qtbot, store, executor, task)

    gc.collect()
    after = tracemalloc.get_traced_memory()[0]
    tracemalloc.stop()

    assert executor._active == {}
    assert len(store.state.notifications.active) == store.state.notifications.active_limit
    assert len(store.state.notifications.history) <= store.state.notifications.history_limit
    assert after - before < 10 * 1024 * 1024


@pytest.mark.performance
@pytest.mark.stress
def test_many_references_and_long_transcript_remain_bounded_and_renderable(
    qtbot, fake_adapter, tmp_path
) -> None:
    current = tmp_path / "current.wav"
    current.write_bytes(b"audio")
    references = tuple(tmp_path / f"reference-{index}.wav" for index in range(75))
    for path in references:
        path.write_bytes(b"audio")
    captured: list[tuple[Path, ...]] = []

    def compare(command):
        captured.append(command.reference_paths)
        return ReferenceViewResult(
            command.current_path,
            command.reference_paths,
            "ok",
            85.0,
            0.8,
            reference_similarities=tuple(
                ReferenceSimilarity(path, 0.75) for path in command.reference_paths
            ),
        )

    fake_adapter.compare_references = compare
    store = PresentationStore()
    executor = WorkerExecutor(QThreadPool())
    window = build_main_window(fake_adapter, ApplicationStateStore(), store, executor)
    qtbot.addWidget(window)
    task = window._reference_controller.execute(_reference_form(current, references))
    _wait_for_task(qtbot, store, executor, task)

    long_text = "Measured long response. " * 200
    items = tuple(
        transcript_item(str(index), TranscriptRole.ASSISTANT, long_text) for index in range(60)
    )
    bounded = ConversationHistory(limit=50)
    for item in items:
        bounded = bounded.append(item)
    store.navigate(PageId.VOICE)
    render_started = time.perf_counter()
    store.set_voice_state(VoicePresentationState(conversation=bounded))
    qtbot.wait(1)
    render_elapsed = time.perf_counter() - render_started

    assert captured == [references]
    assert len(store.state.voice.conversation.items) == 50
    assert render_elapsed < 5.0
    assert window._page_host.current_page_id is PageId.VOICE


@pytest.mark.performance
def test_unavailable_accelerator_status_does_not_probe_or_block_other_pages(
    qtbot, fake_adapter
) -> None:
    status = replace(
        fake_adapter.runtime_status(),
        state=RuntimeState.DEGRADED,
        requested_device="cuda",
        effective_device="cpu",
        device_reason="Requested accelerator is unavailable; CPU remains usable.",
    )
    calls = 0

    def runtime_status():
        nonlocal calls
        calls += 1
        return status

    fake_adapter.runtime_status = runtime_status
    store = PresentationStore(
        PresentationState(runtime=RuntimePresentationState.from_status(status))
    )
    window = build_main_window(fake_adapter, ApplicationStateStore(), store)
    qtbot.addWidget(window)
    started = time.perf_counter()
    for page in NAVIGATION_ORDER:
        store.navigate(page)
    qtbot.wait(1)

    assert time.perf_counter() - started < 2.0
    assert calls == 0
    assert store.state.runtime.phase.value == "degraded"
    assert window._page_host.current_page_id is PageId.RUNTIME_STATUS
