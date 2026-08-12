"""Qt result view for retained analysis DTOs."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QGridLayout,
    QHeaderView,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QToolBox,
    QVBoxLayout,
    QWidget,
)

from .contracts import AnalysisIssue, ReportDescriptor
from .design_system.components import Card, DesignButton, ErrorState, PageHeader, StatusBadge
from .design_system.semantics import result_visual_state
from .design_system.tokens import DEFAULT_TOKENS, DesignTokens
from .presentation_state import ResultPhase, ResultPresentationState
from .result_presentation import AnalysisResultViewState, build_result_view_state, raw_value_text


class AnalysisResultView(QWidget):
    """Render stable result contracts without backend calls or domain interpretation."""

    back_requested = Signal()

    def __init__(
        self,
        *,
        tokens: DesignTokens = DEFAULT_TOKENS,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("analysisResultView")
        self.setAccessibleName("Analysis result")
        self._tokens = tokens
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(tokens.spacing.lg)
        header = PageHeader(
            "Analysis result",
            "Measured values, findings, and interpretation are presented separately.",
            tokens=tokens,
        )
        self.back_button = DesignButton("Back to analysis", tokens=tokens)
        header.add_action(self.back_button)
        self.back_button.clicked.connect(self.back_requested)
        self._layout.addWidget(header)
        self._body: QWidget | None = None
        self.render(ResultPresentationState())

    def render(self, state: ResultPresentationState) -> None:
        view_state = build_result_view_state(state)
        body = (
            self._build_available_result(view_state)
            if view_state.header is not None
            else self._build_state_message(view_state)
        )
        if self._body is not None:
            self._layout.removeWidget(self._body)
            self._body.setParent(None)
            self._body.deleteLater()
        self._body = body
        self._layout.addWidget(body)

    def _build_state_message(self, state: AnalysisResultViewState) -> QWidget:
        if state.phase is ResultPhase.FAILURE and state.error is not None:
            error = ErrorState(state.error, tokens=self._tokens)
            error.setObjectName("resultErrorState")
            return error
        card = Card("Result status", tokens=self._tokens)
        card.setObjectName("resultStateCard")
        badge = StatusBadge(state.phase.value.title(), result_visual_state(state.phase))
        message = QLabel(state.message)
        message.setObjectName("resultStateMessage")
        message.setWordWrap(True)
        card.content_layout.addWidget(badge, 0, Qt.AlignmentFlag.AlignLeft)
        card.content_layout.addWidget(message)
        return card

    def _build_available_result(self, state: AnalysisResultViewState) -> QWidget:
        assert state.header is not None
        root = QWidget()
        layout = QVBoxLayout(root)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(self._tokens.spacing.lg)

        header_card = Card("Result overview", tokens=self._tokens)
        header_card.setObjectName("resultOverview")
        phase_badge = StatusBadge(state.phase.value.title(), result_visual_state(state.phase))
        header_card.content_layout.addWidget(phase_badge, 0, Qt.AlignmentFlag.AlignLeft)
        grid = QGridLayout()
        grid.setHorizontalSpacing(self._tokens.spacing.xl)
        grid.setVerticalSpacing(self._tokens.spacing.sm)
        self._add_header_value(grid, 0, "Source", state.header.source_path.name, "resultSource")
        self._add_header_value(grid, 1, "Status", state.header.status, "resultStatus")
        self._add_header_value(grid, 2, "Score", raw_value_text(state.header.score), "resultScore")
        self._add_header_value(grid, 3, "Audio type", state.header.audio_type, "resultAudioType")
        header_card.content_layout.addLayout(grid)
        source_path = QLabel(str(state.header.source_path))
        source_path.setObjectName("resultSourcePath")
        source_path.setProperty("textRole", "caption")
        source_path.setWordWrap(True)
        header_card.content_layout.addWidget(source_path)
        layout.addWidget(header_card)

        if state.phase is ResultPhase.WARNING:
            warning_status = Card("Partial result", tokens=self._tokens)
            warning_status.setProperty("semantic", "warning")
            warning_status.content_layout.addWidget(QLabel(state.message))
            layout.addWidget(warning_status)

        details = QToolBox()
        details.setObjectName("resultTechnicalDetails")
        details.setAccessibleName("Expandable analysis result details")
        if state.metrics:
            details.addItem(self._metrics_widget(state), "Measured / deterministic")
        if state.issues:
            details.addItem(self._issues_widget(state.issues), "Engineering findings")
        else:
            no_issues = QLabel("No engineering findings were returned.")
            no_issues.setObjectName("resultNoIssues")
            no_issues.setProperty("textRole", "secondary")
            no_issues.setWordWrap(True)
            layout.addWidget(no_issues)
        if state.summary:
            details.addItem(
                self._text_section("resultInterpretation", state.summary),
                "AI / interpretation",
            )
        if state.warnings:
            details.addItem(self._warnings_widget(state.warnings), "Warnings")
        if state.reference_similarity is not None:
            details.addItem(
                self._text_section(
                    "resultReferenceSimilarity",
                    raw_value_text(state.reference_similarity),
                    prefix="Reference similarity: ",
                ),
                "Reference",
            )
        if state.reports:
            details.addItem(self._reports_widget(state.reports), "Generated reports")
        if details.count():
            layout.addWidget(details)
        layout.addStretch(1)
        return root

    @staticmethod
    def _add_header_value(
        grid: QGridLayout,
        column: int,
        label: str,
        value: str,
        object_name: str,
    ) -> None:
        title = QLabel(label)
        title.setProperty("textRole", "secondary")
        text = QLabel(value)
        text.setObjectName(object_name)
        text.setProperty("textRole", "metric")
        text.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        grid.addWidget(title, 0, column)
        grid.addWidget(text, 1, column)

    def _metrics_widget(self, state: AnalysisResultViewState) -> QWidget:
        table = QTableWidget(len(state.metrics), 2)
        table.setObjectName("resultMetrics")
        table.setHorizontalHeaderLabels(("Metric", "Raw value"))
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.verticalHeader().setVisible(False)
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        for row, metric in enumerate(state.metrics):
            table.setItem(row, 0, QTableWidgetItem(metric.name))
            table.setItem(row, 1, QTableWidgetItem(raw_value_text(metric.value)))
        table.setMinimumHeight(min(320, 72 + len(state.metrics) * 30))
        return table

    def _issues_widget(self, issues: tuple[AnalysisIssue, ...]) -> QWidget:
        widget = QWidget()
        widget.setObjectName("resultIssues")
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        for issue in issues:
            card = Card(issue.title, tokens=self._tokens)
            severity = QLabel(f"Severity: {issue.severity}")
            severity.setObjectName("resultIssueSeverity")
            severity.setProperty("textRole", "secondary")
            description = QLabel(issue.description)
            description.setObjectName("resultIssueDescription")
            description.setWordWrap(True)
            card.content_layout.addWidget(severity)
            card.content_layout.addWidget(description)
            if issue.recommendation:
                recommendation = QLabel(f"Recommendation: {issue.recommendation}")
                recommendation.setObjectName("resultIssueRecommendation")
                recommendation.setWordWrap(True)
                card.content_layout.addWidget(recommendation)
            layout.addWidget(card)
        return widget

    @staticmethod
    def _text_section(object_name: str, text: str, *, prefix: str = "") -> QWidget:
        label = QLabel(f"{prefix}{text}")
        label.setObjectName(object_name)
        label.setWordWrap(True)
        label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        return label

    def _warnings_widget(self, warnings: tuple[str, ...]) -> QWidget:
        widget = QWidget()
        widget.setObjectName("resultWarnings")
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        for warning in warnings:
            label = QLabel(warning)
            label.setProperty("semantic", "warning")
            label.setWordWrap(True)
            layout.addWidget(label)
        return widget

    def _reports_widget(self, reports: tuple[ReportDescriptor, ...]) -> QWidget:
        widget = QWidget()
        widget.setObjectName("resultReports")
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        for report in reports:
            card = Card(report.display_label, tokens=self._tokens)
            details = QLabel(f"Kind: {report.kind}\nFormat: {report.format}\nPath: {report.path}")
            details.setObjectName("resultReportDetails")
            details.setWordWrap(True)
            details.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            card.content_layout.addWidget(details)
            layout.addWidget(card)
        return widget
