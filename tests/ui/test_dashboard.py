from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime

import pytest
from PySide6.QtWidgets import QLabel, QPushButton

from brain.ui.analyze_page import AnalyzePage
from brain.ui.app import build_main_window
from brain.ui.contracts import (
    Availability,
    CapabilityLifecycle,
    CapabilitySnapshot,
    ProviderStatus,
    ReportDescriptor,
    RuntimeState,
    RuntimeStatus,
)
from brain.ui.dashboard import DashboardPage, DashboardSection
from brain.ui.design_system.components import (
    CapabilityStatusIndicator,
    Card,
    EmptyState,
    StatusBadge,
)
from brain.ui.design_system.semantics import VisualState
from brain.ui.intelligence_page import IntelligencePage
from brain.ui.knowledge_page import KnowledgePage
from brain.ui.pages import PageHost, PlaceholderPage
from brain.ui.presentation_state import (
    NAVIGATION_ORDER,
    PageId,
    PresentationState,
    RecentAnalysis,
    RecentPath,
    RecentReport,
    RuntimePresentationState,
    SessionState,
)
from brain.ui.presentation_store import PresentationStore
from brain.ui.reference_page import ReferencePage
from brain.ui.state import ApplicationStateStore


def _runtime(
    *,
    runtime_state: RuntimeState = RuntimeState.UNKNOWN,
    provider: ProviderStatus | None = None,
    capabilities: tuple[CapabilitySnapshot, ...] = (),
    device_reason: str | None = None,
) -> RuntimePresentationState:
    status = RuntimeStatus(
        state=runtime_state,
        requested_device="cuda",
        effective_device="cpu" if runtime_state is RuntimeState.DEGRADED else None,
        device_reason=device_reason,
        loaded_models=(),
        provider=provider or ProviderStatus("local", Availability.UNKNOWN),
        paths=(),
        configuration_source="test",
        capabilities=capabilities,
        checked_at=datetime.now(UTC),
    )
    return RuntimePresentationState.from_status(status)


def _labels(widget) -> list[str]:
    return [label.text() for label in widget.findChildren(QLabel)]


def _dashboard(qtbot, state: PresentationState | None = None) -> DashboardPage:
    dashboard = DashboardPage()
    qtbot.addWidget(dashboard)
    dashboard.render(state or PresentationState())
    return dashboard


def test_implemented_pages_are_real_while_later_pages_are_placeholders(qtbot) -> None:
    host = PageHost()
    qtbot.addWidget(host)

    assert isinstance(host.page(PageId.OVERVIEW), DashboardPage)
    assert isinstance(host.page(PageId.ANALYZE), AnalyzePage)
    assert isinstance(host.page(PageId.REFERENCES), ReferencePage)
    assert isinstance(host.page(PageId.INTELLIGENCE), IntelligencePage)
    assert isinstance(host.page(PageId.KNOWLEDGE), KnowledgePage)
    assert all(
        isinstance(host.page(page_id), PlaceholderPage)
        for page_id in NAVIGATION_ORDER
        if page_id
        not in {
            PageId.OVERVIEW,
            PageId.ANALYZE,
            PageId.REFERENCES,
            PageId.INTELLIGENCE,
            PageId.KNOWLEDGE,
        }
    )


@pytest.mark.parametrize(
    ("lifecycle", "availability", "lifecycle_text", "availability_text"),
    [
        (CapabilityLifecycle.PLANNED, Availability.AVAILABLE, "Lifecycle: planned", "available"),
        (
            CapabilityLifecycle.IMPLEMENTED,
            Availability.UNKNOWN,
            "Lifecycle: implemented",
            "unknown",
        ),
        (
            CapabilityLifecycle.PRODUCTION,
            Availability.UNAVAILABLE,
            "Lifecycle: production",
            "unavailable",
        ),
        (
            CapabilityLifecycle.PRODUCTION,
            Availability.DEGRADED,
            "Lifecycle: production",
            "degraded",
        ),
    ],
)
def test_capability_lifecycle_and_availability_remain_separate(
    qtbot, lifecycle, availability, lifecycle_text, availability_text
) -> None:
    capability = CapabilitySnapshot(
        id="capability",
        display_name="Capability",
        lifecycle=lifecycle,
        availability=availability,
        reason="Machine-specific reason",
    )
    state = replace(PresentationState(), runtime=_runtime(capabilities=(capability,)))
    indicator = _dashboard(qtbot, state).findChild(
        CapabilityStatusIndicator, "capability-capability"
    )
    labels = _labels(indicator)
    badge = indicator.findChild(StatusBadge)

    assert lifecycle_text in labels
    assert badge.text() == availability_text
    assert "Machine-specific reason" in labels
    if lifecycle is CapabilityLifecycle.PLANNED:
        assert "Ready" not in labels
    if lifecycle is CapabilityLifecycle.IMPLEMENTED:
        assert all("production" not in text.casefold() for text in labels)
    if availability is Availability.UNAVAILABLE:
        assert badge.visual_state is VisualState.UNAVAILABLE
    if availability is Availability.DEGRADED:
        assert badge.visual_state is VisualState.WARNING


def test_unknown_capability_remains_unknown_with_reason(qtbot) -> None:
    capability = CapabilitySnapshot(
        id="unknown",
        display_name="Unknown capability",
        lifecycle=CapabilityLifecycle.PRODUCTION,
        availability=Availability.UNKNOWN,
        reason="Not checked",
    )
    state = replace(PresentationState(), runtime=_runtime(capabilities=(capability,)))
    dashboard = _dashboard(qtbot, state)
    badge = dashboard.findChild(CapabilityStatusIndicator).findChild(StatusBadge)

    assert badge.text() == "unknown"
    assert badge.visual_state is VisualState.IDLE
    assert "Not checked" in _labels(dashboard)


@pytest.mark.parametrize(
    ("availability", "visual_state"),
    [
        (Availability.UNAVAILABLE, VisualState.UNAVAILABLE),
        (Availability.UNKNOWN, VisualState.IDLE),
    ],
)
def test_provider_name_does_not_imply_availability(qtbot, availability, visual_state) -> None:
    provider = ProviderStatus(
        "configured-provider", availability, reason="Provider has not been verified."
    )
    state = replace(PresentationState(), runtime=_runtime(provider=provider))
    section = _dashboard(qtbot, state).findChild(DashboardSection, "dashboardProvider")
    badge = section.findChild(StatusBadge)

    assert badge.text() == availability.value.title()
    assert badge.visual_state is visual_state
    assert "Provider has not been verified." in _labels(section)


def test_dashboard_does_not_render_secret_values(qtbot) -> None:
    secret = "sk-private-value"
    provider = ProviderStatus("provider", Availability.UNKNOWN, reason="Credential configured")
    state = replace(PresentationState(), runtime=_runtime(provider=provider))
    labels = _labels(_dashboard(qtbot, state))

    assert secret not in " ".join(labels)
    assert "Credential configured" in labels


def test_runtime_renders_devices_reason_and_degraded_truth(qtbot) -> None:
    state = replace(
        PresentationState(),
        runtime=_runtime(
            runtime_state=RuntimeState.DEGRADED,
            device_reason="CUDA is unavailable; CPU selected.",
        ),
    )
    section = _dashboard(qtbot, state).findChild(DashboardSection, "dashboardRuntime")

    assert section.findChild(StatusBadge).text() == "Degraded"
    assert "Requested device: cuda" in _labels(section)
    assert "Effective device: cpu" in _labels(section)
    assert "CUDA is unavailable; CPU selected." in _labels(section)


def test_empty_dashboard_has_unknown_and_real_empty_states(qtbot) -> None:
    dashboard = _dashboard(qtbot)

    runtime = dashboard.findChild(DashboardSection, "dashboardRuntime")
    assert runtime.findChild(StatusBadge).text() == "Unknown"
    assert len(dashboard.findChildren(EmptyState)) == 4
    assert "No recent analyses" in _labels(dashboard)
    assert "No recent reports" in _labels(dashboard)
    assert "No recent references" in _labels(dashboard)


def test_recent_analysis_uses_session_metadata_and_missing_state(qtbot, tmp_path) -> None:
    analysis = RecentAnalysis(
        source_path=tmp_path / "missing.wav",
        analyzed_at=datetime(2026, 8, 12, 12, 0, tzinfo=UTC),
        status="warning",
        audio_type="mix",
        score=87.5,
        source_exists=False,
    )
    state = replace(
        PresentationState(), session=replace(SessionState(), recent_analyses=(analysis,))
    )
    dashboard = _dashboard(qtbot, state)
    card = next(
        item
        for item in dashboard.findChildren(Card)
        if item.property("dashboardItem") == "analysis"
    )

    assert analysis.source_path.name in _labels(card)
    assert "Status: warning" in _labels(card)
    assert "Audio type: mix" in _labels(card)
    assert "Score: 87.5" in _labels(card)
    assert card.findChild(StatusBadge).text() == "Source missing"


def test_recent_report_uses_only_session_descriptor_and_missing_state(qtbot, tmp_path) -> None:
    descriptor = ReportDescriptor(
        "analysis", "json", tmp_path / "missing-report.json", "Analysis JSON"
    )
    report = RecentReport(descriptor, datetime.now(UTC), exists=False)
    state = replace(PresentationState(), session=replace(SessionState(), recent_reports=(report,)))
    dashboard = _dashboard(qtbot, state)
    card = next(
        item for item in dashboard.findChildren(Card) if item.property("dashboardItem") == "report"
    )
    labels = _labels(card)

    assert "Analysis JSON" in labels
    assert "Format: json" in labels
    assert str(descriptor.path) in labels
    assert card.findChild(StatusBadge).text() == "File missing"
    assert "markdown" not in " ".join(labels).casefold()


def test_recent_reference_uses_session_path_and_missing_state(qtbot, tmp_path) -> None:
    reference = RecentPath(tmp_path / "missing-reference.wav", datetime.now(UTC), False)
    state = replace(
        PresentationState(), session=replace(SessionState(), recent_references=(reference,))
    )
    dashboard = _dashboard(qtbot, state)
    card = next(
        item
        for item in dashboard.findChildren(Card)
        if item.property("dashboardItem") == "reference"
    )

    assert reference.path.name in _labels(card)
    assert str(reference.path) in _labels(card)
    assert card.findChild(StatusBadge).text() == "File missing"


@pytest.mark.parametrize(
    ("label", "target"),
    [
        ("Open Analyze", PageId.ANALYZE),
        ("Open References", PageId.REFERENCES),
        ("Open Knowledge", PageId.KNOWLEDGE),
        ("Open Reports", PageId.REPORTS),
    ],
)
def test_quick_actions_emit_navigation_intent(qtbot, label, target) -> None:
    dashboard = _dashboard(qtbot)
    button = next(item for item in dashboard.findChildren(QPushButton) if item.text() == label)

    with qtbot.waitSignal(dashboard.navigation_requested, timeout=1000) as signal:
        button.click()

    assert signal.args == [target]


def test_quick_action_navigates_store_without_resetting_session(
    qtbot, fake_adapter, tmp_path
) -> None:
    selected = tmp_path / "selected.wav"
    selected.write_bytes(b"audio")
    store = PresentationStore(PresentationState.from_session(SessionState().select_audio(selected)))
    window = build_main_window(fake_adapter, ApplicationStateStore(), store)
    qtbot.addWidget(window)
    window.show()
    dashboard = window.findChild(DashboardPage, "page-overview")
    button = next(
        item for item in dashboard.findChildren(QPushButton) if item.text() == "Open Analyze"
    )

    button.click()

    assert store.state.navigation.current_page is PageId.ANALYZE
    assert store.state.session.navigation.current_page is PageId.ANALYZE
    assert store.state.session.selected_audio == selected


def test_dashboard_resizes_without_horizontal_overflow(qtbot) -> None:
    dashboard = _dashboard(qtbot)
    dashboard.show()

    dashboard.resize(500, 500)
    qtbot.wait(10)
    assert dashboard.horizontalScrollBar().maximum() == 0

    dashboard.resize(1200, 900)
    qtbot.wait(10)
    assert dashboard.horizontalScrollBar().maximum() == 0
