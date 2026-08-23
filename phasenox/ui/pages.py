"""Persistent placeholder page host for the Sprint 4 application shell."""

from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QStackedWidget, QVBoxLayout, QWidget

from .analyze_page import AnalyzePage
from .dashboard import DashboardPage
from .design_system.components import EmptyState, PageHeader
from .design_system.tokens import DEFAULT_TOKENS, DesignTokens
from .intelligence_page import IntelligencePage
from .knowledge_page import KnowledgePage
from .presentation_state import NAVIGATION_ORDER, PageId, PresentationState
from .reference_page import ReferencePage
from .reports_page import ReportsPage
from .settings_page import SettingsPage


@dataclass(frozen=True, slots=True)
class PageDefinition:
    page_id: PageId
    title: str
    description: str


PAGE_DEFINITIONS = {
    PageId.ANALYZE: PageDefinition(
        PageId.ANALYZE,
        "Analyze",
        "Audio analysis workflow is not part of this shell sprint.",
    ),
    PageId.REFERENCES: PageDefinition(
        PageId.REFERENCES,
        "References",
        "Reference comparison tools will be added in a later sprint.",
    ),
    PageId.INTELLIGENCE: PageDefinition(
        PageId.INTELLIGENCE,
        "Intelligence",
        "Intelligence tools will be composed here in a later sprint.",
    ),
    PageId.KNOWLEDGE: PageDefinition(
        PageId.KNOWLEDGE,
        "Knowledge",
        "Knowledge features are intentionally not included in this shell sprint.",
    ),
    PageId.REPORTS: PageDefinition(
        PageId.REPORTS,
        "Reports",
        "Report browsing and export controls will be added in a later sprint.",
    ),
    PageId.SETTINGS: PageDefinition(
        PageId.SETTINGS,
        "Settings",
        "Settings remain read-only until their contract-backed workflow is implemented.",
    ),
    PageId.RUNTIME_STATUS: PageDefinition(
        PageId.RUNTIME_STATUS,
        "Runtime / Status",
        "Detailed runtime diagnostics will be added in a later sprint.",
    ),
}


class PlaceholderPage(QWidget):
    def __init__(
        self,
        definition: PageDefinition,
        *,
        tokens: DesignTokens = DEFAULT_TOKENS,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.page_id = definition.page_id
        self.setObjectName(f"page-{definition.page_id.value}")
        self.setAccessibleName(f"{definition.title} page")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(
            tokens.spacing.xl,
            tokens.spacing.xl,
            tokens.spacing.xl,
            tokens.spacing.xl,
        )
        layout.setSpacing(tokens.spacing.lg)
        layout.addWidget(PageHeader(definition.title, definition.description, tokens=tokens))
        layout.addWidget(
            EmptyState(
                f"{definition.title} is ready for future content",
                "This placeholder proves stable navigation and page lifecycle only.",
                tokens=tokens,
            )
        )
        layout.addStretch(1)


class PageHost(QStackedWidget):
    navigation_requested = Signal(object)
    analysis_requested = Signal(object)
    reference_comparison_requested = Signal(object)
    knowledge_search_requested = Signal(object)
    report_preview_requested = Signal(object)
    report_export_requested = Signal(object)
    report_open_directory_requested = Signal(object)
    settings_refresh_requested = Signal()
    runtime_refresh_requested = Signal()
    session_audio_selected = Signal(object)
    session_references_selected = Signal(object)
    session_report_selected = Signal(object)
    recovery_requested = Signal(str)
    voice_start_listening_requested = Signal()
    voice_stop_listening_requested = Signal()
    voice_interruption_requested = Signal()
    voice_proposal_confirmed = Signal(str)
    voice_proposal_cancelled = Signal(str)
    voice_plan_confirmation_recorded = Signal(object)
    voice_action_cancellation_requested = Signal(str)

    def __init__(
        self,
        *,
        tokens: DesignTokens = DEFAULT_TOKENS,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("pageHost")
        self.setAccessibleName("Page workspace")
        self._pages: dict[PageId, QWidget] = {}
        for page_id in NAVIGATION_ORDER:
            if page_id is PageId.OVERVIEW:
                page = DashboardPage(tokens=tokens)
                page.navigation_requested.connect(self.navigation_requested)
            elif page_id is PageId.ANALYZE:
                page = AnalyzePage(tokens=tokens)
                page.analysis_requested.connect(self.analysis_requested)
                page.source_selected.connect(self.session_audio_selected)
                page.references_selected.connect(self.session_references_selected)
                page.recovery_requested.connect(self.recovery_requested)
            elif page_id is PageId.REFERENCES:
                page = ReferencePage(tokens=tokens)
                page.comparison_requested.connect(self.reference_comparison_requested)
                page.current_selected.connect(self.session_audio_selected)
                page.references_selected.connect(self.session_references_selected)
                page.recovery_requested.connect(self.recovery_requested)
            elif page_id is PageId.INTELLIGENCE:
                page = IntelligencePage(tokens=tokens)
            elif page_id is PageId.KNOWLEDGE:
                page = KnowledgePage(tokens=tokens)
                page.search_requested.connect(self.knowledge_search_requested)
            elif page_id is PageId.REPORTS:
                page = ReportsPage(tokens=tokens)
                page.preview_requested.connect(self.report_preview_requested)
                page.export_requested.connect(self.report_export_requested)
                page.open_directory_requested.connect(self.report_open_directory_requested)
                page.report_selected.connect(self.session_report_selected)
            elif page_id is PageId.SETTINGS:
                page = SettingsPage(tokens=tokens)
                page.refresh_settings_requested.connect(self.settings_refresh_requested)
                page.refresh_runtime_requested.connect(self.runtime_refresh_requested)
            else:
                page = PlaceholderPage(PAGE_DEFINITIONS[page_id], tokens=tokens)
            self._pages[page_id] = page
            self.addWidget(page)

    @property
    def current_page_id(self) -> PageId:
        page = self.currentWidget()
        page_id = getattr(page, "page_id", None)
        if not isinstance(page_id, PageId):
            raise TypeError("Page host contains an unexpected widget.")
        return page_id

    def page(self, page_id: PageId) -> QWidget:
        return self._pages[page_id]

    def show_page(self, page_id: PageId) -> None:
        self.setCurrentWidget(self._pages[page_id])

    def render_current(self, state: PresentationState) -> None:
        """Render only the page selected by presentation state.

        Inactive pages are persistent and receive the latest state when they are
        selected.  Avoiding eight unnecessary page renders on every publication
        keeps navigation and operation updates lightweight.
        """
        page_id = state.navigation.current_page
        self.show_page(page_id)
        page = self._pages[page_id]
        render = getattr(page, "render", None)
        if callable(render) and type(page).render is not QWidget.render:
            render(state)

    def render(self, state: PresentationState) -> None:
        """Synchronize every state-aware page, primarily for explicit test use."""
        dashboard = self._pages[PageId.OVERVIEW]
        if isinstance(dashboard, DashboardPage):
            dashboard.render(state)
        analyze = self._pages[PageId.ANALYZE]
        if isinstance(analyze, AnalyzePage):
            analyze.render(state)
        references = self._pages[PageId.REFERENCES]
        if isinstance(references, ReferencePage):
            references.render(state)
        intelligence = self._pages[PageId.INTELLIGENCE]
        if isinstance(intelligence, IntelligencePage):
            intelligence.render(state)
        knowledge = self._pages[PageId.KNOWLEDGE]
        if isinstance(knowledge, KnowledgePage):
            knowledge.render(state)
        reports = self._pages[PageId.REPORTS]
        if isinstance(reports, ReportsPage):
            reports.render(state)
        settings = self._pages[PageId.SETTINGS]
        if isinstance(settings, SettingsPage):
            settings.render(state)
