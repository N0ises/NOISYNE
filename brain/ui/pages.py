"""Persistent placeholder page host for the Sprint 4 application shell."""

from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QStackedWidget, QVBoxLayout, QWidget

from .analyze_page import AnalyzePage
from .dashboard import DashboardPage
from .design_system.components import EmptyState, PageHeader
from .design_system.tokens import DEFAULT_TOKENS, DesignTokens
from .presentation_state import NAVIGATION_ORDER, PageId, PresentationState


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

    def render(self, state: PresentationState) -> None:
        dashboard = self._pages[PageId.OVERVIEW]
        if isinstance(dashboard, DashboardPage):
            dashboard.render(state)
        analyze = self._pages[PageId.ANALYZE]
        if isinstance(analyze, AnalyzePage):
            analyze.render(state)
