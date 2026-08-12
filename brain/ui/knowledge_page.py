"""Persistent Knowledge / RAG page backed only by stable desktop contracts."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from .design_system.components import (
    ButtonVariant,
    Card,
    DesignButton,
    PageHeader,
    StatusBadge,
    TextInput,
)
from .design_system.semantics import VisualState, availability_visual_state
from .design_system.tokens import DEFAULT_TOKENS, DesignTokens
from .knowledge_state import KnowledgeQueryState
from .presentation_state import PageId, PresentationState, ResultPhase


class KnowledgePage(QScrollArea):
    search_requested = Signal(object)
    page_id = PageId.KNOWLEDGE

    def __init__(
        self,
        *,
        tokens: DesignTokens = DEFAULT_TOKENS,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("page-knowledge")
        self.setAccessibleName("Knowledge search page")
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self._tokens = tokens
        self._query = KnowledgeQueryState()

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(
            tokens.spacing.xl, tokens.spacing.xl, tokens.spacing.xl, tokens.spacing.xl
        )
        layout.setSpacing(tokens.spacing.lg)
        layout.addWidget(
            PageHeader(
                "Knowledge",
                "Search the configured V1 knowledge service without exposing vector-store internals.",
                tokens=tokens,
            )
        )

        capability_card = Card("Knowledge status", tokens=tokens)
        self.capability_badge = StatusBadge("Unknown", VisualState.IDLE)
        self.capability_reason = QLabel(self._query.capability.reason)
        self.capability_reason.setWordWrap(True)
        capability_card.content_layout.addWidget(
            self.capability_badge, 0, Qt.AlignmentFlag.AlignLeft
        )
        capability_card.content_layout.addWidget(self.capability_reason)
        layout.addWidget(capability_card)

        query_card = Card("Search knowledge", tokens=tokens)
        self.query_input = TextInput("Enter a knowledge query", accessible_name="Knowledge query")
        actions = QHBoxLayout()
        self.search_button = DesignButton("Search", variant=ButtonVariant.PRIMARY, tokens=tokens)
        self.clear_button = DesignButton("Clear query", tokens=tokens)
        actions.addWidget(self.search_button)
        actions.addWidget(self.clear_button)
        actions.addStretch(1)
        self.validation_label = QLabel(self._query.validation_message)
        self.validation_label.setObjectName("knowledgeValidation")
        self.validation_label.setWordWrap(True)
        query_card.content_layout.addWidget(self.query_input)
        query_card.content_layout.addLayout(actions)
        query_card.content_layout.addWidget(self.validation_label)
        layout.addWidget(query_card)

        status_card = Card("Search status", tokens=tokens)
        self.status_badge = StatusBadge("No query", VisualState.IDLE)
        self.status_message = QLabel("No knowledge search has run in this session.")
        self.status_message.setObjectName("knowledgeStatusMessage")
        self.status_message.setWordWrap(True)
        self.progress = QProgressBar()
        self.progress.setObjectName("knowledgeProgress")
        self.progress.setRange(0, 0)
        self.progress.setVisible(False)
        status_card.content_layout.addWidget(self.status_badge, 0, Qt.AlignmentFlag.AlignLeft)
        status_card.content_layout.addWidget(self.status_message)
        status_card.content_layout.addWidget(self.progress)
        layout.addWidget(status_card)

        self.warnings_card = Card("Warnings", tokens=tokens)
        self.warnings_layout = self.warnings_card.content_layout
        self.warnings_card.setVisible(False)
        layout.addWidget(self.warnings_card)

        self.context_card = Card("Context used by reasoning", tokens=tokens)
        self.context_label = QLabel()
        self.context_label.setObjectName("knowledgeReasoningContext")
        self.context_label.setWordWrap(True)
        self.context_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.context_card.content_layout.addWidget(self.context_label)
        self.context_card.setVisible(False)
        layout.addWidget(self.context_card)

        self.results_card = Card("Retrieved results", tokens=tokens)
        self.results_container = QWidget()
        self.results_layout = QVBoxLayout(self.results_container)
        self.results_layout.setContentsMargins(0, 0, 0, 0)
        self.results_card.content_layout.addWidget(self.results_container)
        layout.addWidget(self.results_card)
        layout.addStretch(1)
        self.setWidget(content)

        self.query_input.textChanged.connect(self._query_changed)
        self.query_input.returnPressed.connect(self._search)
        self.search_button.clicked.connect(self._search)
        self.clear_button.clicked.connect(self.query_input.clear)
        self._render_query()
        self._show_empty_results("Run a search to retrieve knowledge results.")

    def render(self, state: PresentationState) -> None:
        self._query = self._query.with_capabilities(state.runtime.capabilities)
        capability = self._query.capability
        self.capability_badge.setText(capability.availability.value.title())
        self.capability_badge.set_state(availability_visual_state(capability.availability))
        self.capability_reason.setText(capability.reason)
        if not self.query_input.text() and state.session.last_knowledge_query:
            self.query_input.setText(state.session.last_knowledge_query)
        self._render_query()

        result_state = state.knowledge_result
        busy = result_state.phase is ResultPhase.LOADING
        self.progress.setVisible(busy)
        self.search_button.setEnabled(self._query.can_search and not busy)
        self.query_input.setEnabled(not busy)
        self.clear_button.setEnabled(not busy)

        mapping = {
            ResultPhase.EMPTY: (
                "No query",
                VisualState.IDLE,
                "No knowledge search has run in this session.",
            ),
            ResultPhase.LOADING: (
                "Searching",
                VisualState.RUNNING,
                "Searching knowledge. Progress is indeterminate and cancellation is unavailable.",
            ),
            ResultPhase.SUCCESS: ("Complete", VisualState.SUCCESS, "Knowledge search completed."),
            ResultPhase.WARNING: (
                "Complete with warnings",
                VisualState.WARNING,
                "Search returned usable results with warnings.",
            ),
            ResultPhase.FAILURE: (
                "Failed",
                VisualState.ERROR,
                (
                    result_state.error.user_message
                    if result_state.error
                    else "Knowledge search failed."
                ),
            ),
            ResultPhase.CANCELLED: (
                "Cancelled",
                VisualState.CANCELLED,
                "Knowledge search was cancelled.",
            ),
            ResultPhase.UNAVAILABLE: (
                "Unavailable",
                VisualState.UNAVAILABLE,
                "Knowledge search is unavailable.",
            ),
        }
        badge, visual, message = mapping[result_state.phase]
        self.status_badge.setText(badge)
        self.status_badge.set_state(visual)
        self.status_message.setText(message)

        result = result_state.result
        self._clear_layout(self.warnings_layout)
        warnings = result.warnings if result else ()
        for warning in warnings:
            label = QLabel(warning)
            label.setWordWrap(True)
            self.warnings_layout.addWidget(label)
        self.warnings_card.setVisible(bool(warnings))

        context = result.reasoning_context if result else None
        self.context_label.setText(context or "")
        self.context_card.setVisible(bool(context))

        if result is not None:
            if result.items:
                self._render_results(result.items)
            else:
                self._show_empty_results("No results were found for this query.")
        elif result_state.phase is ResultPhase.FAILURE:
            self._show_empty_results("No results are available from the failed search.")

    def _query_changed(self, text: str) -> None:
        self._query = self._query.set_text(text)
        self._render_query()

    def _search(self) -> None:
        self._query = self._query.set_text(self.query_input.text())
        self._render_query()
        if self._query.can_search:
            self.search_requested.emit(self._query.build_query())

    def _render_query(self) -> None:
        self.validation_label.setText(self._query.validation_message)
        self.search_button.setEnabled(self._query.can_search)

    def _render_results(self, items: tuple) -> None:
        self._clear_layout(self.results_layout)
        for index, item in enumerate(items, start=1):
            card = Card(f"Result {index}", tokens=self._tokens)
            source = QLabel(f"Source: {item.source}" if item.source else "Source: not supplied")
            source.setObjectName("knowledgeResultSource")
            content = QLabel(item.content)
            content.setObjectName("knowledgeResultContent")
            content.setWordWrap(True)
            content.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            card.content_layout.addWidget(source)
            if item.page is not None:
                page = QLabel(f"Page: {item.page}")
                page.setObjectName("knowledgeResultPage")
                card.content_layout.addWidget(page)
            score_parts = []
            if item.raw_score is not None:
                score_parts.append(f"Raw retrieval score: {item.raw_score:g}")
            if item.raw_rerank_score is not None:
                score_parts.append(f"Raw reranker score: {item.raw_rerank_score:g}")
            if score_parts:
                relevance = QLabel(" | ".join(score_parts))
                relevance.setObjectName("knowledgeResultRelevance")
                card.content_layout.addWidget(relevance)
            card.content_layout.addWidget(content)
            self.results_layout.addWidget(card)

    def _show_empty_results(self, message: str) -> None:
        self._clear_layout(self.results_layout)
        label = QLabel(message)
        label.setObjectName("knowledgeEmptyResults")
        label.setWordWrap(True)
        self.results_layout.addWidget(label)

    @staticmethod
    def _clear_layout(layout: QVBoxLayout) -> None:
        while layout.count():
            item = layout.takeAt(0)
            if item.widget() is not None:
                item.widget().deleteLater()
