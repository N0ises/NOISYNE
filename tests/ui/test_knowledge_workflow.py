from __future__ import annotations

import threading
import time
from pathlib import Path

from PySide6.QtCore import QThreadPool, QTimer
from PySide6.QtWidgets import QLabel

from brain.ui.contracts import (
    AnalysisViewResult,
    Availability,
    CapabilityLifecycle,
    CapabilitySnapshot,
    IntelligenceSnapshot,
    KnowledgeQuery,
    KnowledgeResultItem,
    KnowledgeSearchResult,
    ReferenceViewResult,
    UiErrorCategory,
)
from brain.ui.knowledge_controller import KnowledgeController
from brain.ui.knowledge_page import KnowledgePage
from brain.ui.pages import PageHost, PlaceholderPage
from brain.ui.presentation_state import (
    PageId,
    PresentationState,
    ResultPhase,
    RuntimePresentationState,
)
from brain.ui.presentation_store import PresentationStore
from brain.ui.workers import WorkerExecutor


class FakeKnowledgeAdapter:
    def __init__(self, result=None, error=None, delay=0.0) -> None:
        self.result = result
        self.error = error
        self.delay = delay
        self.query = None
        self.thread_id = None

    def search_knowledge(self, query):
        self.query = query
        self.thread_id = threading.get_ident()
        if self.delay:
            time.sleep(self.delay)
        if self.error:
            raise self.error
        return self.result


def _capability(availability=Availability.AVAILABLE) -> CapabilitySnapshot:
    return CapabilitySnapshot(
        "rag_retrieval",
        "RAG retrieval",
        CapabilityLifecycle.IMPLEMENTED,
        availability,
        reason="Knowledge runtime status.",
    )


def _result(**changes) -> KnowledgeSearchResult:
    values = {
        "query": "headroom",
        "items": (
            KnowledgeResultItem(
                "Keep headroom before limiting.",
                "mastering-guide.pdf",
                12,
                0.8123,
                -1.25,
            ),
        ),
        "warnings": (),
        "reasoning_context": None,
    }
    values.update(changes)
    return KnowledgeSearchResult(**values)


def test_knowledge_placeholder_is_replaced_and_page_is_persistent(qtbot) -> None:
    host = PageHost()
    qtbot.addWidget(host)

    page = host.page(PageId.KNOWLEDGE)
    assert isinstance(page, KnowledgePage)
    assert not isinstance(page, PlaceholderPage)

    page.query_input.setText("retained query")
    host.show_page(PageId.ANALYZE)
    host.show_page(PageId.KNOWLEDGE)
    assert host.page(PageId.KNOWLEDGE) is page
    assert page.query_input.text() == "retained query"


def test_empty_query_does_not_emit_and_enter_builds_query_dto(qtbot) -> None:
    page = KnowledgePage()
    qtbot.addWidget(page)
    page.render(PresentationState(runtime=RuntimePresentationState(capabilities=(_capability(),))))
    emitted = []
    page.search_requested.connect(emitted.append)

    page.search_button.click()
    assert emitted == []
    assert "Enter a query" in page.validation_label.text()

    page.query_input.setText("  headroom  ")
    page.query_input.returnPressed.emit()
    assert emitted == [KnowledgeQuery("headroom")]


def test_worker_is_bound_before_start_off_gui_and_is_truthfully_indeterminate(qtbot) -> None:
    adapter = FakeKnowledgeAdapter(result=_result(), delay=0.15)
    store = PresentationStore()
    executor = WorkerExecutor(QThreadPool())
    controller = KnowledgeController(adapter, store, executor)
    state_at_creation = []
    controller.task_created.connect(
        lambda _task: state_at_creation.append(store.state.operation.state)
    )
    timer_fired = []
    QTimer.singleShot(20, lambda: timer_fired.append(True))
    gui_thread = threading.get_ident()

    controller.execute(KnowledgeQuery("headroom"))
    qtbot.waitUntil(lambda: store.state.operation.state.value == "running", timeout=1000)

    assert state_at_creation[0].value == "queued"
    assert store.state.operation.progress is None
    assert not store.state.operation.cancellable
    assert not store.request_cancellation()
    qtbot.waitUntil(lambda: bool(timer_fired), timeout=1000)
    qtbot.waitUntil(lambda: store.state.operation.is_terminal, timeout=3000)
    executor.wait_for_done()
    assert adapter.thread_id != gui_thread
    assert store.state.knowledge_result.result == adapter.result
    assert store.state.session.last_knowledge_query == "headroom"
    assert store.state.session.recent_knowledge_queries == ("headroom",)


def test_page_renders_real_fields_raw_scores_warnings_and_explicit_context(qtbot) -> None:
    page = KnowledgePage()
    qtbot.addWidget(page)
    result = _result(
        warnings=("Optional reranker was degraded.",),
        reasoning_context="Explicit context supplied by the adapter.",
    )
    state = PresentationState(
        runtime=RuntimePresentationState(capabilities=(_capability(Availability.DEGRADED),))
    )
    store = PresentationStore(state)
    executor = WorkerExecutor(QThreadPool())
    controller = KnowledgeController(FakeKnowledgeAdapter(result=result), store, executor)
    store.subscribe(page.render)

    controller.execute(KnowledgeQuery("headroom"))
    qtbot.waitUntil(lambda: store.state.operation.is_terminal, timeout=3000)
    executor.wait_for_done()

    source = page.findChild(QLabel, "knowledgeResultSource")
    page_label = page.findChild(QLabel, "knowledgeResultPage")
    relevance = page.findChild(QLabel, "knowledgeResultRelevance")
    assert source.text() == "Source: mastering-guide.pdf"
    assert page_label.text() == "Page: 12"
    assert relevance.text() == "Raw retrieval score: 0.8123 | Raw reranker score: -1.25"
    assert "%" not in relevance.text()
    assert page.warnings_card.isVisible() or not page.isVisible()
    assert page.context_label.text() == "Explicit context supplied by the adapter."


def test_no_results_is_success_and_reasoning_context_is_absent_when_not_returned(qtbot) -> None:
    page = KnowledgePage()
    qtbot.addWidget(page)
    store = PresentationStore(
        PresentationState(runtime=RuntimePresentationState(capabilities=(_capability(),)))
    )
    executor = WorkerExecutor(QThreadPool())
    controller = KnowledgeController(
        FakeKnowledgeAdapter(result=_result(items=())), store, executor
    )
    store.subscribe(page.render)

    controller.execute(KnowledgeQuery("nothing"))
    qtbot.waitUntil(lambda: store.state.operation.is_terminal, timeout=3000)
    executor.wait_for_done()

    assert store.state.knowledge_result.phase is ResultPhase.SUCCESS
    assert "No results" in page.findChild(QLabel, "knowledgeEmptyResults").text()
    assert not page.context_card.isVisible()


def test_absent_source_page_and_relevance_are_not_invented(qtbot) -> None:
    page = KnowledgePage()
    qtbot.addWidget(page)
    result = _result(items=(KnowledgeResultItem("Unattributed content", "", None, None, None),))
    state = PresentationState(
        runtime=RuntimePresentationState(capabilities=(_capability(),)),
        knowledge_result=PresentationState().knowledge_result.__class__(
            phase=ResultPhase.SUCCESS, result=result
        ),
    )

    page.render(state)

    assert page.findChild(QLabel, "knowledgeResultSource").text() == "Source: not supplied"
    assert page.findChild(QLabel, "knowledgeResultPage") is None
    assert page.findChild(QLabel, "knowledgeResultRelevance") is None


def test_failure_is_structured_and_does_not_erase_unrelated_results(qtbot) -> None:
    analysis = AnalysisViewResult(
        Path("mix.wav"),
        "ok",
        "mix",
        90.0,
        "summary",
        intelligence=IntelligenceSnapshot(reasoning="retained reasoning"),
    )
    reference = ReferenceViewResult(Path("mix.wav"), (Path("reference.wav"),), "ok", 90.0, 0.9)
    initial = PresentationState(
        result=PresentationState().result.__class__(phase=ResultPhase.SUCCESS, result=analysis),
        reference_result=PresentationState().reference_result.__class__(
            phase=ResultPhase.SUCCESS, result=reference
        ),
    )
    store = PresentationStore(initial)
    executor = WorkerExecutor(QThreadPool())
    controller = KnowledgeController(
        FakeKnowledgeAdapter(error=RuntimeError("native store failure")), store, executor
    )

    controller.execute(KnowledgeQuery("headroom"))
    qtbot.waitUntil(lambda: store.state.operation.is_terminal, timeout=3000)
    executor.wait_for_done()

    assert store.state.knowledge_result.phase is ResultPhase.FAILURE
    assert store.state.knowledge_result.error.category is UiErrorCategory.INTERNAL
    assert store.state.knowledge_result.error.technical_detail == "RuntimeError"
    assert store.state.result.result is analysis
    assert store.state.result.result.intelligence.reasoning == "retained reasoning"
    assert store.state.reference_result.result is reference


def test_missing_knowledge_runtime_maps_to_capability_unavailable(qtbot) -> None:
    store = PresentationStore()
    executor = WorkerExecutor(QThreadPool())
    controller = KnowledgeController(
        FakeKnowledgeAdapter(error=ModuleNotFoundError("optional runtime")), store, executor
    )

    controller.execute(KnowledgeQuery("headroom"))
    qtbot.waitUntil(lambda: store.state.operation.is_terminal, timeout=3000)
    executor.wait_for_done()

    assert store.state.knowledge_result.error.category is UiErrorCategory.CAPABILITY_UNAVAILABLE
    assert store.state.knowledge_result.error.capability_id == "rag_retrieval"


def test_unknown_and_unavailable_disable_search_while_degraded_allows_it(qtbot) -> None:
    page = KnowledgePage()
    qtbot.addWidget(page)
    page.query_input.setText("headroom")

    for availability in (Availability.UNKNOWN, Availability.UNAVAILABLE):
        page.render(
            PresentationState(
                runtime=RuntimePresentationState(capabilities=(_capability(availability),))
            )
        )
        assert not page.search_button.isEnabled()
        assert page.capability_reason.text() == "Knowledge runtime status."

    page.render(
        PresentationState(
            runtime=RuntimePresentationState(capabilities=(_capability(Availability.DEGRADED),))
        )
    )
    assert page.search_button.isEnabled()
