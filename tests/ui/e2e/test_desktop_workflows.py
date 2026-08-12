from __future__ import annotations

import json
from datetime import UTC, datetime

import pytest
from PySide6.QtWidgets import QLabel, QListWidget, QPushButton, QTableWidget

from brain.ui.agent_contracts import (
    ActionClass,
    AgentPlan,
    ConfirmationDecision,
    ConfirmationOutcome,
    PermissionPolicy,
    PlannedAction,
    VerificationResult,
    VerificationState,
)
from brain.ui.app import build_main_window, create_application
from brain.ui.branding import default_product_metadata
from brain.ui.contracts import (
    AnalysisViewResult,
    Availability,
    KnowledgeSearchResult,
    MetricValue,
    OperationHandle,
    ReferenceViewResult,
    ReportDescriptor,
    ReportExportCommand,
    RuntimeState,
)
from brain.ui.design_system.components import ErrorState, NotificationToast
from brain.ui.intelligence_page import IntelligencePage
from brain.ui.knowledge_page import KnowledgePage
from brain.ui.pages import PageHost
from brain.ui.presentation_state import (
    NAVIGATION_ORDER,
    PageId,
    PresentationState,
    ResultPhase,
)
from brain.ui.presentation_store import PresentationStore
from brain.ui.reference_page import ReferencePage
from brain.ui.reports_page import ReportsPage
from brain.ui.session_persistence import (
    SCHEMA_VERSION,
    SessionPersistenceBinding,
    SessionRepository,
)
from brain.ui.settings_page import SettingsPage
from brain.ui.state import ApplicationStateStore
from brain.ui.voice_contracts import VoiceLifecycle, VoicePresentationState
from brain.ui.voice_page import VoicePage
from brain.ui.workers import WorkerExecutor

from .conftest import DeterministicDesktopAdapter, capability, runtime_status

pytestmark = [pytest.mark.e2e, pytest.mark.integration]


def test_launch_builds_branded_adapter_backed_desktop_without_network_or_models(
    desktop_harness,
) -> None:
    application = create_application(default_product_metadata())
    window = desktop_harness.window
    host = window.findChild(PageHost, "pageHost")

    assert application.applicationDisplayName() == "NØISYNE"
    assert application.applicationName() == "soundbrain.desktop"
    assert window.windowTitle() == "NØISYNE"
    assert host.current_page_id is PageId.OVERVIEW
    assert desktop_harness.store.state.runtime.phase.value == "ready"
    assert desktop_harness.adapter.calls == [("settings_snapshot", None)]
    assert window.statusBar().currentMessage() == "Ready"


def test_navigation_integrates_sidebar_page_host_and_session_for_every_page(
    desktop_harness,
) -> None:
    navigation = desktop_harness.window.findChild(QListWidget, "primaryNavigation")
    host = desktop_harness.window.findChild(PageHost, "pageHost")

    for page_id in NAVIGATION_ORDER:
        navigation.setCurrentRow(NAVIGATION_ORDER.index(page_id))
        assert desktop_harness.store.state.navigation.current_page is page_id
        assert desktop_harness.store.state.session.navigation.current_page is page_id
        assert host.current_page_id is page_id
        assert host.currentWidget() is host.page(page_id)

    voice_before = desktop_harness.store.state.voice
    desktop_harness.store.navigate(PageId.VOICE)
    desktop_harness.store.navigate(PageId.OVERVIEW)
    assert desktop_harness.store.state.voice is voice_before


def test_analyze_success_runs_end_to_end_and_renders_retained_result(
    qtbot, desktop_harness, tmp_path
) -> None:
    source = tmp_path / "mix.wav"
    source.write_bytes(b"deterministic-audio-placeholder")
    desktop_harness.adapter.analysis_result = AnalysisViewResult(
        source,
        "ok",
        "mix",
        92.5,
        "Deterministic result summary.",
        metrics=(MetricValue("integrated_loudness", -14.0),),
    )
    desktop_harness.store.navigate(PageId.ANALYZE)
    page = desktop_harness.window._page_host.page(PageId.ANALYZE)

    page.select_source(source)
    page.review_button.click()
    page.confirm_button.click()
    desktop_harness.wait_for_operation(qtbot)

    assert desktop_harness.adapter.calls[-1][0] == "analyze"
    assert desktop_harness.store.state.result.phase is ResultPhase.SUCCESS
    assert desktop_harness.store.state.session.selected_audio == source
    assert desktop_harness.store.state.session.last_analysis_result.score == 92.5
    assert page.completion_badge.text() == "Result available"
    page.view_result_button.click()
    metrics = page.result_view.findChild(QTableWidget, "resultMetrics")
    assert metrics is not None
    assert metrics.rowCount() == 1


def test_analysis_failure_is_structured_visible_recoverable_and_keeps_app_usable(
    qtbot, desktop_harness, tmp_path
) -> None:
    source = tmp_path / "invalid.wav"
    source.write_bytes(b"invalid")
    desktop_harness.adapter.analysis_error = ValueError("secret backend traceback text")
    desktop_harness.store.navigate(PageId.ANALYZE)
    page = desktop_harness.window._page_host.page(PageId.ANALYZE)

    page.select_source(source)
    page.review_button.click()
    page.confirm_button.click()
    desktop_harness.wait_for_operation(qtbot)
    page.view_result_button.click()

    error = desktop_harness.store.state.result.error
    assert error.code == "analysis_input_rejected"
    assert error.result_usability.value == "not_usable"
    assert "secret" not in error.user_message
    assert page.result_view.findChild(ErrorState, "resultErrorState") is not None
    toast = desktop_harness.window.findChild(NotificationToast)
    assert toast is not None
    recovery = next(
        button
        for button in toast.findChildren(QPushButton)
        if button.text() == "Select another file"
    )
    recovery.click()
    assert desktop_harness.store.state.navigation.current_page is PageId.ANALYZE
    desktop_harness.store.navigate(PageId.OVERVIEW)
    assert desktop_harness.window._page_host.current_page_id is PageId.OVERVIEW


def test_reference_comparison_runs_through_main_window_and_updates_session(
    qtbot, desktop_harness, tmp_path
) -> None:
    source = tmp_path / "current.wav"
    references = (tmp_path / "one.wav", tmp_path / "two.wav")
    for path in (source, *references):
        path.write_bytes(b"audio")
    desktop_harness.adapter.reference_result = ReferenceViewResult(
        source, references, "ok", 88.75, 0.9
    )
    desktop_harness.store.navigate(PageId.REFERENCES)
    page: ReferencePage = desktop_harness.window._page_host.page(PageId.REFERENCES)

    page.select_current(source)
    page.add_references(references)
    page.review()
    page.compare_button.click()
    desktop_harness.wait_for_operation(qtbot)

    assert desktop_harness.adapter.calls[-1][0] == "compare_references"
    assert desktop_harness.store.state.reference_result.phase is ResultPhase.SUCCESS
    assert desktop_harness.store.state.session.selected_audio == source
    assert desktop_harness.store.state.session.selected_references == references
    page.view_result_button.click()
    similarity = page.result_view.findChild(QLabel, "referenceResultSimilarity")
    assert similarity.text() == "Similarity (raw): 88.75"


def test_intelligence_page_reports_unavailable_reason_instead_of_fake_readiness(
    desktop_harness,
) -> None:
    capabilities = (
        capability(
            "llm_reasoning",
            Availability.UNAVAILABLE,
            reason="No local reasoning model is configured.",
        ),
    )
    desktop_harness.store.set_runtime_status(
        runtime_status(RuntimeState.DEGRADED, capabilities=capabilities)
    )
    desktop_harness.store.navigate(PageId.INTELLIGENCE)
    page: IntelligencePage = desktop_harness.window._page_host.page(PageId.INTELLIGENCE)

    labels = "\n".join(label.text() for label in page.findChildren(QLabel))
    assert "Unavailable" in labels
    assert "No local reasoning model is configured." in labels
    assert "Ready" not in labels


@pytest.mark.parametrize(
    ("result", "error", "phase", "visible_text"),
    [
        (KnowledgeSearchResult("headroom"), None, ResultPhase.SUCCESS, "No results were found"),
        (
            KnowledgeSearchResult("headroom", warnings=("Reranker unavailable.",)),
            None,
            ResultPhase.WARNING,
            "Reranker unavailable.",
        ),
        (None, ImportError("rag internals"), ResultPhase.FAILURE, "unavailable"),
    ],
)
def test_knowledge_empty_warning_and_unavailable_flows_are_deterministic(
    qtbot, desktop_harness, result, error, phase, visible_text
) -> None:
    desktop_harness.adapter.knowledge_result = result
    desktop_harness.adapter.knowledge_error = error
    desktop_harness.store.navigate(PageId.KNOWLEDGE)
    page: KnowledgePage = desktop_harness.window._page_host.page(PageId.KNOWLEDGE)
    page.query_input.setText("headroom")
    page.search_button.click()
    desktop_harness.wait_for_operation(qtbot)

    assert desktop_harness.store.state.knowledge_result.phase is phase
    labels = "\n".join(label.text() for label in page.findChildren(QLabel))
    assert visible_text.casefold() in labels.casefold()
    if error is not None:
        ui_error = desktop_harness.store.state.knowledge_result.error
        assert ui_error.code == "knowledge_runtime_unavailable"
        assert "rag internals" not in ui_error.user_message


def test_knowledge_success_renders_adapter_chunks_without_rag_or_network(
    qtbot, desktop_harness
) -> None:
    desktop_harness.store.navigate(PageId.KNOWLEDGE)
    page: KnowledgePage = desktop_harness.window._page_host.page(PageId.KNOWLEDGE)
    page.query_input.setText("headroom")
    page.search_button.click()
    desktop_harness.wait_for_operation(qtbot)

    assert desktop_harness.store.state.knowledge_result.phase is ResultPhase.SUCCESS
    assert desktop_harness.adapter.calls[-1][0] == "search_knowledge"
    content = page.findChild(QLabel, "knowledgeResultContent")
    assert content.text() == "Keep headroom before limiting."
    assert page.findChild(QLabel, "knowledgeResultSource").text() == "Source: fixture-guide.md"


def test_report_preview_and_export_flow_updates_visible_state_and_session(
    qtbot, desktop_harness, tmp_path
) -> None:
    source = tmp_path / "analysis.json"
    source.write_text('{"score": 92.5}', encoding="utf-8")
    descriptor = ReportDescriptor("analysis", "json", source, "Analysis JSON")
    desktop_harness.store.set_session(
        desktop_harness.store.state.session.record_report(
            descriptor, created_at=datetime(2026, 1, 1, tzinfo=UTC)
        )
    )
    desktop_harness.store.navigate(PageId.REPORTS)
    page: ReportsPage = desktop_harness.window._page_host.page(PageId.REPORTS)
    desktop_harness.wait_for_operation(qtbot)

    assert desktop_harness.adapter.calls[-1][0] == "load_report"
    assert desktop_harness.store.state.report_preview.phase is ResultPhase.SUCCESS
    assert page.viewer.toPlainText() == '{"score": 92.5}'
    destination = tmp_path / "exported.json"
    page.export_requested.emit(ReportExportCommand(descriptor, destination))
    desktop_harness.wait_for_operation(qtbot)

    assert any(name == "export_report" for name, _payload in desktop_harness.adapter.calls)
    assert desktop_harness.store.state.report_export.phase is ResultPhase.SUCCESS
    assert desktop_harness.store.state.session.recent_reports[0].descriptor.path == destination
    assert page.status_badge.text() == "Export complete"


def test_report_preview_failure_is_visible_structured_and_does_not_break_navigation(
    qtbot, desktop_harness, tmp_path
) -> None:
    source = tmp_path / "analysis.json"
    source.write_text("{}", encoding="utf-8")
    descriptor = ReportDescriptor("analysis", "json", source, "Analysis JSON")
    desktop_harness.adapter.preview_error = ValueError("private parser detail")
    desktop_harness.store.set_session(desktop_harness.store.state.session.record_report(descriptor))
    desktop_harness.store.navigate(PageId.REPORTS)
    page: ReportsPage = desktop_harness.window._page_host.page(PageId.REPORTS)
    desktop_harness.wait_for_operation(qtbot)

    error = desktop_harness.store.state.report_preview.error
    assert error.code == "report_format_unsupported"
    assert "private parser detail" not in page.status_message.text()
    assert page.status_badge.text() == "Preview failed"
    desktop_harness.store.navigate(PageId.SETTINGS)
    assert desktop_harness.window._page_host.current_page_id is PageId.SETTINGS


def test_settings_load_refresh_and_runtime_unavailable_remain_read_only(
    qtbot, desktop_harness
) -> None:
    desktop_harness.store.navigate(PageId.SETTINGS)
    page: SettingsPage = desktop_harness.window._page_host.page(PageId.SETTINGS)

    assert "e2e-revision" in page.settings_status.text()
    assert page.policy_badge.text() == "Read-only"
    assert page.findChild(QLabel, "setting-device").text() == "cpu"
    desktop_harness.adapter.runtime = runtime_status(RuntimeState.UNAVAILABLE)
    page.refresh_runtime_button.click()
    qtbot.waitUntil(
        lambda: desktop_harness.store.state.runtime.phase.value == "unavailable",
        timeout=3000,
    )
    assert desktop_harness.executor.wait_for_done(3000)
    assert page.runtime_badge.text() == "Unavailable"
    assert "Deterministic test runtime status" in page.runtime_summary.text()
    page.reload_settings_button.click()
    assert [name for name, _ in desktop_harness.adapter.calls].count("settings_snapshot") == 2


def test_restart_restores_allowlisted_session_and_drops_all_transient_state(
    qtbot, tmp_path
) -> None:
    repository = SessionRepository(tmp_path / "desktop-session.json")
    adapter = DeterministicDesktopAdapter()
    source = tmp_path / "mix.wav"
    reference = tmp_path / "reference.wav"
    report_path = tmp_path / "report.json"
    for path in (source, reference, report_path):
        path.write_bytes(b"fixture")
    descriptor = ReportDescriptor("analysis", "json", report_path, "Report", source)
    store = PresentationStore()
    binding = SessionPersistenceBinding(repository, store)
    window = build_main_window(adapter, ApplicationStateStore(), store, WorkerExecutor())
    qtbot.addWidget(window)
    window._page_host.page(PageId.ANALYZE).select_source(source)
    window._page_host.page(PageId.REFERENCES).add_references((reference,))
    store.select_report(report_path)
    store.set_session(store.state.session.record_report(descriptor))
    permission = PermissionPolicy().decide(
        ActionClass.DESTRUCTIVE,
        affected_target=str(source),
        risk_summary="Would overwrite source.",
    )
    action = PlannedAction(
        "delete",
        "Delete source",
        ActionClass.DESTRUCTIVE,
        "Future action only.",
        str(source),
        permission.risk_summary,
        permission,
        "tool:delete",
    )
    plan = AgentPlan("restart-plan", "revision-1", "Delete source", (action,))
    store.set_voice_state(
        VoicePresentationState(
            lifecycle=VoiceLifecycle.WAITING_FOR_CONFIRMATION,
            agent_plan=plan,
            confirmation=ConfirmationDecision.for_plan(plan, ConfirmationOutcome.APPROVED),
            verification=VerificationResult(VerificationState.VERIFYING),
        )
    )
    store.begin_operation(OperationHandle("transient-operation", "analysis"))
    store.add_notification(
        __import__(
            "brain.ui.presentation_state", fromlist=["NotificationLevel"]
        ).NotificationLevel.WARNING,
        "Transient warning",
    )
    binding.save_current()
    binding.close()
    window.close()

    payload = json.loads(repository.path.read_text(encoding="utf-8"))
    restored = repository.load().session
    restarted_store = PresentationStore(PresentationState.from_session(restored))
    restarted = build_main_window(
        DeterministicDesktopAdapter(),
        ApplicationStateStore(),
        restarted_store,
        WorkerExecutor(),
    )
    qtbot.addWidget(restarted)

    assert payload["schema_version"] == SCHEMA_VERSION == 2
    assert restored.selected_audio == source
    assert restored.selected_references == (reference,)
    assert restored.selected_report_path == report_path
    assert restarted_store.state.voice == VoicePresentationState()
    assert restarted_store.state.notifications.active == ()
    assert restarted_store.state.operation.is_idle
    serialized = repository.path.read_text(encoding="utf-8")
    assert "restart-plan" not in serialized
    assert "Transient warning" not in serialized
    assert "transient-operation" not in serialized


def test_missing_runtime_capability_shows_reason_recovery_and_keeps_other_pages_usable(
    qtbot, desktop_harness
) -> None:
    unavailable = capability(
        "rag_retrieval",
        Availability.UNAVAILABLE,
        reason="Knowledge index is not installed.",
    )
    desktop_harness.store.set_runtime_status(
        runtime_status(RuntimeState.DEGRADED, capabilities=(unavailable,))
    )
    desktop_harness.store.navigate(PageId.KNOWLEDGE)
    knowledge: KnowledgePage = desktop_harness.window._page_host.page(PageId.KNOWLEDGE)

    assert knowledge.capability_badge.text() == "Unavailable"
    assert "Knowledge index is not installed." in knowledge.capability_reason.text()
    assert not knowledge.search_button.isEnabled()
    desktop_harness.adapter.runtime = runtime_status(RuntimeState.DEGRADED)
    desktop_harness.adapter.runtime_status = lambda: (_ for _ in ()).throw(
        ImportError("native runtime detail")
    )
    desktop_harness.store.navigate(PageId.SETTINGS)
    settings: SettingsPage = desktop_harness.window._page_host.page(PageId.SETTINGS)
    settings.refresh_runtime_button.click()
    qtbot.waitUntil(lambda: bool(desktop_harness.store.state.notifications.active), timeout=3000)
    assert desktop_harness.executor.wait_for_done(3000)
    toast = desktop_harness.window.findChild(NotificationToast)
    assert toast is not None
    assert any(
        button.text() == "Refresh runtime status" for button in toast.findChildren(QPushButton)
    )
    desktop_harness.store.navigate(PageId.ANALYZE)
    assert desktop_harness.window._page_host.current_page_id is PageId.ANALYZE


def test_voice_and_agent_remain_disabled_presentation_only_safety_surfaces(
    desktop_harness,
) -> None:
    desktop_harness.store.navigate(PageId.VOICE)
    page: VoicePage = desktop_harness.window._page_host.page(PageId.VOICE)

    assert page.availability.engine_badge.text() == "Engine unavailable"
    assert page.input_control.action_button.text() == "Voice unavailable"
    assert not page.input_control.action_button.isEnabled()
    state = desktop_harness.store.state.voice
    for lifecycle in (
        VoiceLifecycle.LISTENING,
        VoiceLifecycle.TRANSCRIBING,
        VoiceLifecycle.UNDERSTANDING,
        VoiceLifecycle.PLANNING,
        VoiceLifecycle.WAITING_FOR_CONFIRMATION,
    ):
        state = state.transition(lifecycle)
        desktop_harness.store.set_voice_state(state)
        assert (
            page.input_control.state_badge.text()
            == {
                VoiceLifecycle.LISTENING: "Listening",
                VoiceLifecycle.TRANSCRIBING: "Transcribing",
                VoiceLifecycle.UNDERSTANDING: "Understanding",
                VoiceLifecycle.PLANNING: "Planning",
                VoiceLifecycle.WAITING_FOR_CONFIRMATION: "Waiting for confirmation",
            }[lifecycle]
        )
    assert all(name not in {"execute", "execute_tool"} for name, _ in desktop_harness.adapter.calls)
