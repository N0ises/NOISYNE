"""Qt presentation for stable reference comparison result DTOs."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHeaderView,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QToolBox,
    QVBoxLayout,
    QWidget,
)

from .contracts import ReferenceViewResult, UiError
from .design_system.components import Card, DesignButton, ErrorState, PageHeader, StatusBadge
from .design_system.semantics import result_visual_state
from .design_system.tokens import DEFAULT_TOKENS, DesignTokens
from .presentation_state import ReferenceResultPresentationState, ResultPhase
from .result_presentation import raw_value_text


class ReferenceResultView(QWidget):
    back_requested = Signal()
    recovery_requested = Signal(str)

    def __init__(
        self,
        *,
        tokens: DesignTokens = DEFAULT_TOKENS,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("referenceResultView")
        self._tokens = tokens
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(tokens.spacing.lg)
        header = PageHeader(
            "Reference comparison result",
            "Backend measurements, differences, and recommendations remain distinct.",
            tokens=tokens,
        )
        back = DesignButton("Back to comparison", tokens=tokens)
        back.clicked.connect(self.back_requested)
        header.add_action(back)
        self._layout.addWidget(header)
        self._body: QWidget | None = None
        self.render(ReferenceResultPresentationState())

    def render(self, state: ReferenceResultPresentationState) -> None:
        if state.result is not None and state.phase in {
            ResultPhase.SUCCESS,
            ResultPhase.WARNING,
            ResultPhase.FAILURE,
            ResultPhase.CANCELLED,
        }:
            body = self._result_widget(state.result, state.phase, state.error)
        elif state.phase is ResultPhase.FAILURE and state.error is not None:
            body = ErrorState(state.error, tokens=self._tokens)
            body.setObjectName("referenceResultError")
            body.recovery_requested.connect(self.recovery_requested)
        else:
            body = Card("Comparison status", tokens=self._tokens)
            message = QLabel(_state_message(state.phase))
            message.setObjectName("referenceResultStateMessage")
            message.setWordWrap(True)
            body.content_layout.addWidget(
                StatusBadge(state.phase.value.title(), result_visual_state(state.phase)),
                0,
                Qt.AlignmentFlag.AlignLeft,
            )
            body.content_layout.addWidget(message)
        if self._body is not None:
            self._layout.removeWidget(self._body)
            self._body.setParent(None)
            self._body.deleteLater()
        self._body = body
        self._layout.addWidget(body)

    def _result_widget(
        self,
        result: ReferenceViewResult,
        phase: ResultPhase,
        error: UiError | None = None,
    ) -> QWidget:
        root = QWidget()
        layout = QVBoxLayout(root)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(self._tokens.spacing.lg)
        if error is not None:
            failure = ErrorState(error, tokens=self._tokens)
            failure.setObjectName("referenceResultError")
            failure.recovery_requested.connect(self.recovery_requested)
            layout.addWidget(failure)
        elif phase is ResultPhase.CANCELLED:
            retained = Card("Previous result retained", tokens=self._tokens)
            retained.content_layout.addWidget(
                QLabel("The latest comparison was cancelled; the previous result remains usable.")
            )
            layout.addWidget(retained)
        overview = Card("Comparison overview", tokens=self._tokens)
        overview.content_layout.addWidget(
            StatusBadge(phase.value.title(), result_visual_state(phase)),
            0,
            Qt.AlignmentFlag.AlignLeft,
        )
        for name, value, object_name in (
            ("Current track", result.current_path.name, "referenceResultCurrent"),
            ("Status", result.status, "referenceResultStatus"),
            (
                "Similarity (raw)",
                raw_value_text(result.similarity),
                "referenceResultSimilarity",
            ),
            (
                "Confidence (raw)",
                raw_value_text(result.confidence),
                "referenceResultConfidence",
            ),
        ):
            label = QLabel(f"{name}: {value}")
            label.setObjectName(object_name)
            label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            overview.content_layout.addWidget(label)
        references = QLabel(
            "References:\n" + "\n".join(str(path) for path in result.reference_paths)
        )
        references.setObjectName("referenceResultReferences")
        references.setWordWrap(True)
        overview.content_layout.addWidget(references)
        layout.addWidget(overview)

        details = QToolBox()
        details.setObjectName("referenceResultDetails")
        if result.scores:
            details.addItem(
                _simple_metrics_table(result.scores, "referenceScores"),
                "Backend comparison scores",
            )
        if result.metrics:
            details.addItem(self._metrics_table(result), "Side-by-side metrics")
        if result.metric_variances:
            details.addItem(
                _simple_metrics_table(result.metric_variances, "referenceVariances"),
                "Backend metric variance",
            )
        if result.band_differences:
            details.addItem(self._band_table(result), "Band differences")
        if result.reference_similarities:
            details.addItem(self._similarities_table(result), "Per-reference similarity")
        if result.findings:
            details.addItem(self._findings_widget(result), "Reference findings")
        if result.segment_deviations:
            details.addItem(self._segments_table(result), "Backend segment deviations")
        if result.warnings:
            details.addItem(self._text_list(result.warnings, "referenceWarnings"), "Warnings")
        if result.reports:
            reports = tuple(
                f"{item.display_label}\nKind: {item.kind}\nFormat: {item.format}\nPath: {item.path}"
                for item in result.reports
            )
            details.addItem(self._text_list(reports, "referenceReports"), "Generated reports")
        if details.count():
            layout.addWidget(details)
        layout.addStretch(1)
        return root

    def _metrics_table(self, result: ReferenceViewResult) -> QTableWidget:
        headers = (
            "Metric",
            "Current",
            "Reference",
            "Difference",
            "Unit",
            "Tolerance",
            "Passed",
            "Severity",
            "Similarity",
        )
        rows = tuple(
            (
                item.name,
                raw_value_text(item.current),
                raw_value_text(item.reference),
                raw_value_text(item.difference),
                item.unit,
                raw_value_text(item.tolerance),
                raw_value_text(item.passed),
                item.severity,
                raw_value_text(item.similarity),
            )
            for item in result.metrics
        )
        return _table(headers, rows, "referenceMetrics")

    def _band_table(self, result: ReferenceViewResult) -> QTableWidget:
        rows = tuple(
            tuple(
                map(
                    raw_value_text,
                    (
                        item.band,
                        item.start_hz,
                        item.end_hz,
                        item.current_energy,
                        item.reference_energy,
                        item.difference_db,
                        item.severity,
                    ),
                )
            )
            for item in result.band_differences
        )
        return _table(
            ("Band", "Start Hz", "End Hz", "Current", "Reference", "Difference dB", "Severity"),
            rows,
            "referenceBandDifferences",
        )

    def _similarities_table(self, result: ReferenceViewResult) -> QTableWidget:
        return _table(
            ("Reference", "Similarity (raw)"),
            tuple(
                (str(item.reference_path), raw_value_text(item.similarity))
                for item in result.reference_similarities
            ),
            "referenceSimilarities",
        )

    def _findings_widget(self, result: ReferenceViewResult) -> QWidget:
        widget = QWidget()
        widget.setObjectName("referenceFindings")
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        for finding in result.findings:
            card = Card(finding.title, tokens=self._tokens)
            for text in (
                f"Category: {finding.category}",
                f"Severity: {finding.severity}",
                f"Confidence: {raw_value_text(finding.confidence)}",
                finding.description,
            ):
                label = QLabel(text)
                label.setWordWrap(True)
                card.content_layout.addWidget(label)
            if finding.recommendation:
                recommendation = QLabel(f"Recommendation: {finding.recommendation}")
                recommendation.setObjectName("referenceRecommendation")
                recommendation.setWordWrap(True)
                card.content_layout.addWidget(recommendation)
            layout.addWidget(card)
        return widget

    def _segments_table(self, result: ReferenceViewResult) -> QTableWidget:
        return _table(
            ("Start", "End", "Metric", "Current", "Reference", "Severity"),
            tuple(
                (
                    raw_value_text(item.start_time),
                    raw_value_text(item.end_time),
                    item.metric,
                    raw_value_text(item.current_value),
                    raw_value_text(item.reference_value),
                    item.severity,
                )
                for item in result.segment_deviations
            ),
            "referenceSegments",
        )

    @staticmethod
    def _text_list(items: tuple[str, ...], object_name: str) -> QWidget:
        widget = QWidget()
        widget.setObjectName(object_name)
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        for item in items:
            label = QLabel(item)
            label.setWordWrap(True)
            label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            layout.addWidget(label)
        return widget


def _simple_metrics_table(metrics, object_name: str) -> QTableWidget:
    return _table(
        ("Name", "Raw value"),
        tuple((item.name, raw_value_text(item.value)) for item in metrics),
        object_name,
    )


def _table(headers: tuple[str, ...], rows: tuple[tuple[str, ...], ...], name: str) -> QTableWidget:
    table = QTableWidget(len(rows), len(headers))
    table.setObjectName(name)
    table.setHorizontalHeaderLabels(headers)
    table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
    table.verticalHeader().setVisible(False)
    for row_index, row in enumerate(rows):
        for column_index, value in enumerate(row):
            table.setItem(row_index, column_index, QTableWidgetItem(value))
    table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
    table.horizontalHeader().setStretchLastSection(True)
    table.setMinimumHeight(min(320, 72 + len(rows) * 30))
    return table


def _state_message(phase: ResultPhase) -> str:
    return {
        ResultPhase.EMPTY: "No reference comparison result is available.",
        ResultPhase.LOADING: "Reference comparison is running with indeterminate progress.",
        ResultPhase.SUCCESS: "The operation did not return a comparison result.",
        ResultPhase.WARNING: "The partial operation did not return a comparison result.",
        ResultPhase.FAILURE: "Reference comparison failed.",
        ResultPhase.CANCELLED: "Reference comparison was cancelled before completion.",
        ResultPhase.UNAVAILABLE: "Reference comparison is unavailable.",
    }[phase]

