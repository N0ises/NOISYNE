"""DTO-driven Overview Dashboard that emits navigation intent only."""

from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from .contracts import Availability, ProviderStatus
from .design_system.components import (
    CapabilityStatusIndicator,
    Card,
    DesignButton,
    EmptyState,
    PageHeader,
    StatusBadge,
)
from .design_system.semantics import (
    VisualState,
    availability_visual_state,
    runtime_visual_state,
)
from .design_system.tokens import DEFAULT_TOKENS, DesignTokens
from .presentation_state import (
    PageId,
    PresentationState,
    RecentAnalysis,
    RecentPath,
    RecentReport,
    RuntimePresentationPhase,
    RuntimePresentationState,
    SessionState,
)


class DashboardSection(Card):
    def __init__(
        self,
        title: str,
        *,
        object_name: str,
        tokens: DesignTokens,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(title, tokens=tokens, parent=parent)
        self.setObjectName(object_name)
        self._items: list[QWidget] = []

    def replace_items(self, items: tuple[QWidget, ...]) -> None:
        for widget in self._items:
            self.content_layout.removeWidget(widget)
            widget.setParent(None)
            widget.deleteLater()
        self._items = list(items)
        for widget in self._items:
            self.content_layout.addWidget(widget)
        QTimer.singleShot(0, self, self._sync_minimum_height)

    def _sync_minimum_height(self) -> None:
        self.setMinimumHeight(0)
        self.content_layout.invalidate()
        self.content_layout.activate()
        self.setMinimumHeight(self.sizeHint().height())


class DashboardPage(QScrollArea):
    """Render presentation DTOs without owning application or backend lifecycle."""

    navigation_requested = Signal(object)
    page_id = PageId.OVERVIEW

    def __init__(
        self,
        *,
        tokens: DesignTokens = DEFAULT_TOKENS,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("page-overview")
        self.setAccessibleName("Overview Dashboard")
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self._tokens = tokens

        content = QWidget()
        content.setObjectName("dashboardContent")
        layout = QVBoxLayout(content)
        layout.setContentsMargins(
            tokens.spacing.xl,
            tokens.spacing.xl,
            tokens.spacing.xl,
            tokens.spacing.xl,
        )
        layout.setSpacing(tokens.spacing.lg)
        layout.addWidget(
            PageHeader(
                "Overview",
                "Runtime truth, capability status, and recent desktop activity.",
                tokens=tokens,
            )
        )

        self.quick_actions = DashboardSection(
            "Quick actions", object_name="dashboardQuickActions", tokens=tokens
        )
        self.quick_actions.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Minimum)
        actions = QVBoxLayout()
        actions.setSpacing(tokens.spacing.sm)
        for label, page_id in (
            ("Open Analyze", PageId.ANALYZE),
            ("Open References", PageId.REFERENCES),
            ("Open Knowledge", PageId.KNOWLEDGE),
            ("Open Reports", PageId.REPORTS),
        ):
            button = DesignButton(label, tokens=tokens)
            button.setProperty("targetPage", page_id.value)
            button.clicked.connect(
                lambda _checked=False, target=page_id: self.navigation_requested.emit(target)
            )
            actions.addWidget(button)
        self.quick_actions.content_layout.addLayout(actions)
        layout.addWidget(self.quick_actions)

        self.runtime_section = DashboardSection(
            "Runtime status", object_name="dashboardRuntime", tokens=tokens
        )
        self.provider_section = DashboardSection(
            "AI / Provider", object_name="dashboardProvider", tokens=tokens
        )
        self.capabilities_section = DashboardSection(
            "Capabilities", object_name="dashboardCapabilities", tokens=tokens
        )
        self.analyses_section = DashboardSection(
            "Recent analyses", object_name="dashboardRecentAnalyses", tokens=tokens
        )
        self.reports_section = DashboardSection(
            "Recent reports", object_name="dashboardRecentReports", tokens=tokens
        )
        self.references_section = DashboardSection(
            "Recent references", object_name="dashboardRecentReferences", tokens=tokens
        )
        self.session_section = DashboardSection(
            "Current session", object_name="dashboardCurrentSession", tokens=tokens
        )
        for section in (
            self.session_section,
            self.runtime_section,
            self.provider_section,
            self.capabilities_section,
            self.analyses_section,
            self.reports_section,
            self.references_section,
        ):
            section.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Minimum)
            layout.addWidget(section)
        layout.addStretch(1)
        self.setWidget(content)
        self.render(PresentationState())

    def render(self, state: PresentationState) -> None:
        self._render_session(state.session)
        self._render_runtime(state.runtime)
        self._render_provider(state.runtime)
        self._render_capabilities(state.runtime)
        self._render_analyses(state.session.recent_analyses)
        self._render_reports(state.session.recent_reports)
        self._render_references(state.session.recent_references)

    def _render_session(self, session: SessionState) -> None:
        items: list[QWidget] = []
        if session.selected_audio is None:
            items.append(_detail_label("Source audio: None selected"))
        else:
            source_exists = session.selected_audio.exists()
            items.append(_detail_label(f"Source audio: {session.selected_audio}"))
            items.append(
                StatusBadge(
                    "Available" if source_exists else "Source missing",
                    VisualState.READY if source_exists else VisualState.UNAVAILABLE,
                )
            )
        if session.selected_references:
            items.extend(
                _detail_label(f"Reference: {path} ({'available' if path.exists() else 'missing'})")
                for path in session.selected_references
            )
        else:
            items.append(_detail_label("References: None selected"))
        if session.last_knowledge_query:
            items.append(_detail_label(f"Last knowledge query: {session.last_knowledge_query}"))
        self.session_section.replace_items(tuple(items))

    def _render_runtime(self, runtime: RuntimePresentationState) -> None:
        labels = {
            RuntimePresentationPhase.LOADING: "Checking",
            RuntimePresentationPhase.UNKNOWN: "Unknown",
            RuntimePresentationPhase.READY: "Ready",
            RuntimePresentationPhase.DEGRADED: "Degraded",
            RuntimePresentationPhase.UNAVAILABLE: "Unavailable",
        }
        items: list[QWidget] = [
            _status_row(
                "Runtime",
                labels[runtime.phase],
                runtime_visual_state(runtime.phase),
                object_name="dashboardRuntimeState",
            )
        ]
        if runtime.status is not None:
            status = runtime.status
            effective = status.effective_device or "Not determined"
            items.append(_detail_label(f"Requested device: {status.requested_device}"))
            items.append(_detail_label(f"Effective device: {effective}"))
            if status.device_reason:
                items.append(_detail_label(status.device_reason, reason=True))
        else:
            items.append(
                _detail_label(
                    "Runtime details are not available yet.",
                    reason=True,
                )
            )
        self.runtime_section.replace_items(tuple(items))

    def _render_provider(self, runtime: RuntimePresentationState) -> None:
        provider = runtime.status.provider if runtime.status is not None else None
        if provider is None:
            provider = ProviderStatus(
                name="Not reported",
                availability=Availability.UNKNOWN,
                reason="Provider status is not available yet.",
            )
        items: list[QWidget] = [
            _status_row(
                provider.name,
                provider.availability.value.title(),
                availability_visual_state(provider.availability),
                object_name="dashboardProviderState",
            )
        ]
        if provider.reason:
            items.append(_detail_label(provider.reason, reason=True))
        self.provider_section.replace_items(tuple(items))

    def _render_capabilities(self, runtime: RuntimePresentationState) -> None:
        if not runtime.capabilities:
            self.capabilities_section.replace_items(
                (
                    _empty_state(
                        "No capability status",
                        "Capabilities have not been reported.",
                        self._tokens,
                    ),
                )
            )
            return
        indicators = tuple(
            CapabilityStatusIndicator(capability, tokens=self._tokens)
            for capability in runtime.capabilities
        )
        for indicator, capability in zip(indicators, runtime.capabilities, strict=True):
            indicator.setObjectName(f"capability-{capability.id}")
        self.capabilities_section.replace_items(indicators)

    def _render_analyses(self, analyses: tuple[RecentAnalysis, ...]) -> None:
        if not analyses:
            self.analyses_section.replace_items(
                (
                    _empty_state(
                        "No recent analyses",
                        "Completed analyses will appear here.",
                        self._tokens,
                    ),
                )
            )
            return
        self.analyses_section.replace_items(tuple(_analysis_item(item) for item in analyses))

    def _render_reports(self, reports: tuple[RecentReport, ...]) -> None:
        if not reports:
            self.reports_section.replace_items(
                (
                    _empty_state(
                        "No recent reports",
                        "Generated report records will appear here.",
                        self._tokens,
                    ),
                )
            )
            return
        self.reports_section.replace_items(tuple(_report_item(item) for item in reports))

    def _render_references(self, references: tuple[RecentPath, ...]) -> None:
        if not references:
            self.references_section.replace_items(
                (
                    _empty_state(
                        "No recent references",
                        "Selected reference files will appear here.",
                        self._tokens,
                    ),
                )
            )
            return
        self.references_section.replace_items(tuple(_reference_item(item) for item in references))


def _status_row(name: str, status: str, visual_state: VisualState, *, object_name: str) -> QWidget:
    row = QWidget()
    row.setObjectName(object_name)
    layout = QHBoxLayout(row)
    layout.setContentsMargins(0, 0, 0, 0)
    label = QLabel(name)
    label.setProperty("textRole", "secondary")
    badge = StatusBadge(status, visual_state)
    layout.addWidget(label, 1)
    layout.addWidget(badge)
    return row


def _detail_label(text: str, *, reason: bool = False) -> QLabel:
    label = QLabel(text)
    label.setWordWrap(True)
    label.setProperty("textRole", "muted" if reason else "secondary")
    if reason:
        label.setProperty("detailRole", "reason")
    return label


def _empty_state(title: str, message: str, tokens: DesignTokens) -> EmptyState:
    empty = EmptyState(title, message, tokens=tokens)
    empty.setProperty("dashboardEmpty", True)
    return empty


def _analysis_item(item: RecentAnalysis) -> Card:
    card = Card(item.source_path.name)
    card.setProperty("dashboardItem", "analysis")
    card.content_layout.addWidget(_detail_label(f"Status: {item.status}"))
    card.content_layout.addWidget(_detail_label(f"Audio type: {item.audio_type}"))
    card.content_layout.addWidget(_detail_label(f"Score: {item.score:g}"))
    card.content_layout.addWidget(_detail_label(f"Analyzed: {_format_time(item.analyzed_at)}"))
    card.content_layout.addWidget(
        StatusBadge(
            "Available" if item.source_exists else "Source missing",
            VisualState.READY if item.source_exists else VisualState.UNAVAILABLE,
        )
    )
    return card


def _report_item(item: RecentReport) -> Card:
    descriptor = item.descriptor
    card = Card(descriptor.display_label or descriptor.path.name)
    card.setProperty("dashboardItem", "report")
    card.content_layout.addWidget(_detail_label(f"Format: {descriptor.format}"))
    card.content_layout.addWidget(_detail_label(str(descriptor.path)))
    card.content_layout.addWidget(_detail_label(f"Created: {_format_time(item.created_at)}"))
    card.content_layout.addWidget(
        StatusBadge(
            "Available" if item.exists else "File missing",
            VisualState.READY if item.exists else VisualState.UNAVAILABLE,
        )
    )
    return card


def _reference_item(item: RecentPath) -> Card:
    card = Card(item.path.name)
    card.setProperty("dashboardItem", "reference")
    card.content_layout.addWidget(_detail_label(str(item.path)))
    card.content_layout.addWidget(_detail_label(f"Last used: {_format_time(item.last_used_at)}"))
    card.content_layout.addWidget(
        StatusBadge(
            "Available" if item.exists else "File missing",
            VisualState.READY if item.exists else VisualState.UNAVAILABLE,
        )
    )
    return card


def _format_time(value: datetime) -> str:
    return value.astimezone().strftime("%Y-%m-%d %H:%M")
