"""Qt Analyze workflow page that renders state and emits confirmed intent."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from .analyze_state import AnalysisFormState, AnalyzePhase
from .design_system.components import (
    ButtonVariant,
    Card,
    DesignButton,
    PageHeader,
    StatusBadge,
    TextInput,
    ToggleSwitch,
)
from .design_system.semantics import VisualState
from .design_system.tokens import DEFAULT_TOKENS, DesignTokens
from .presentation_state import PageId, PresentationState, ResultPhase
from .result_view import AnalysisResultView

AUDIO_PICKER_FILTER = "Common audio files (*.wav *.mp3 *.flac *.ogg *.m4a *.aac);;All files (*)"


class AnalyzePage(QScrollArea):
    analysis_requested = Signal(object)
    source_selected = Signal(object)
    references_selected = Signal(object)
    recovery_requested = Signal(str)
    page_id = PageId.ANALYZE

    def __init__(
        self,
        *,
        tokens: DesignTokens = DEFAULT_TOKENS,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("page-analyze")
        self.setAccessibleName("Analyze audio page")
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setAcceptDrops(True)
        self._tokens = tokens
        self._form = AnalysisFormState.initial()

        content = QWidget()
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
                "Analyze",
                "Select, configure, review, and run audio analysis.",
                tokens=tokens,
            )
        )

        self.file_card = Card("Audio file", tokens=tokens)
        self.source_label = QLabel("No file selected")
        self.source_label.setObjectName("selectedAudioPath")
        self.source_label.setWordWrap(True)
        self.source_status = StatusBadge("Required", VisualState.IDLE)
        source_actions = QHBoxLayout()
        self.choose_source_button = DesignButton(
            "Choose audio file", variant=ButtonVariant.PRIMARY, tokens=tokens
        )
        self.clear_source_button = DesignButton("Clear", tokens=tokens)
        source_actions.addWidget(self.choose_source_button)
        source_actions.addWidget(self.clear_source_button)
        source_actions.addStretch(1)
        self.file_card.content_layout.addWidget(self.source_label)
        self.file_card.content_layout.addWidget(self.source_status, 0, Qt.AlignmentFlag.AlignLeft)
        self.file_card.content_layout.addLayout(source_actions)
        layout.addWidget(self.file_card)

        self.reference_card = Card("Optional reference", tokens=tokens)
        self.reference_label = QLabel("No reference selected")
        self.reference_label.setObjectName("selectedReferencePath")
        self.reference_label.setWordWrap(True)
        reference_actions = QHBoxLayout()
        self.choose_reference_button = DesignButton("Choose reference", tokens=tokens)
        self.clear_reference_button = DesignButton("Clear reference", tokens=tokens)
        reference_actions.addWidget(self.choose_reference_button)
        reference_actions.addWidget(self.clear_reference_button)
        reference_actions.addStretch(1)
        self.reference_card.content_layout.addWidget(self.reference_label)
        self.reference_card.content_layout.addLayout(reference_actions)
        layout.addWidget(self.reference_card)

        self.configuration_card = Card("Configuration", tokens=tokens)
        self.intent_input = TextInput("Intent", accessible_name="Analysis intent")
        self.delivery_input = TextInput("Delivery target", accessible_name="Delivery target")
        self.output_label = QLabel("No JSON output path selected")
        self.output_label.setObjectName("analysisOutputPath")
        output_actions = QHBoxLayout()
        self.choose_output_button = DesignButton("Choose JSON output", tokens=tokens)
        self.clear_output_button = DesignButton("Clear output", tokens=tokens)
        output_actions.addWidget(self.choose_output_button)
        output_actions.addWidget(self.clear_output_button)
        output_actions.addStretch(1)
        self.configuration_card.content_layout.addWidget(self.intent_input)
        self.configuration_card.content_layout.addWidget(self.delivery_input)
        self.configuration_card.content_layout.addWidget(self.output_label)
        self.configuration_card.content_layout.addLayout(output_actions)
        self.feature_toggles: dict[str, ToggleSwitch] = {}
        self.feature_reasons: dict[str, QLabel] = {}
        for feature in self._form.features:
            toggle = ToggleSwitch(feature.label)
            toggle.setObjectName(feature.field)
            reason = QLabel(feature.reason or "")
            reason.setProperty("textRole", "caption")
            reason.setWordWrap(True)
            self.feature_toggles[feature.field] = toggle
            self.feature_reasons[feature.field] = reason
            self.configuration_card.content_layout.addWidget(toggle)
            self.configuration_card.content_layout.addWidget(reason)
        layout.addWidget(self.configuration_card)

        self.validation_label = QLabel("Choose an audio file to continue.")
        self.validation_label.setObjectName("analysisValidation")
        self.validation_label.setWordWrap(True)
        self.validation_label.setProperty("textRole", "secondary")
        layout.addWidget(self.validation_label)

        self.review_button = DesignButton(
            "Review analysis", variant=ButtonVariant.PRIMARY, tokens=tokens
        )
        layout.addWidget(self.review_button, 0, Qt.AlignmentFlag.AlignLeft)

        self.review_card = Card("Confirm analysis", tokens=tokens)
        self.review_card.setObjectName("analysisConfirmation")
        self.review_summary = QLabel()
        self.review_summary.setWordWrap(True)
        self.confirm_button = DesignButton(
            "Run analysis", variant=ButtonVariant.PRIMARY, tokens=tokens
        )
        self.edit_button = DesignButton("Back to configuration", tokens=tokens)
        review_actions = QHBoxLayout()
        review_actions.addWidget(self.confirm_button)
        review_actions.addWidget(self.edit_button)
        review_actions.addStretch(1)
        self.review_card.content_layout.addWidget(self.review_summary)
        self.review_card.content_layout.addLayout(review_actions)
        layout.addWidget(self.review_card)

        self.completion_card = Card("Analysis status", tokens=tokens)
        self.completion_card.setObjectName("analysisCompletion")
        self.completion_badge = StatusBadge("Idle", VisualState.IDLE)
        self.completion_message = QLabel("No analysis has run in this session.")
        self.completion_message.setWordWrap(True)
        self.view_result_button = DesignButton(
            "View analysis result", variant=ButtonVariant.PRIMARY, tokens=tokens
        )
        self.view_result_button.setVisible(False)
        self.completion_card.content_layout.addWidget(self.completion_badge)
        self.completion_card.content_layout.addWidget(self.completion_message)
        self.completion_card.content_layout.addWidget(
            self.view_result_button,
            0,
            Qt.AlignmentFlag.AlignLeft,
        )
        layout.addWidget(self.completion_card)
        self.result_view = AnalysisResultView(tokens=tokens)
        self.result_view.setVisible(False)
        layout.addWidget(self.result_view)
        layout.addStretch(1)
        self.setWidget(content)

        self.choose_source_button.clicked.connect(self._choose_source)
        self.clear_source_button.clicked.connect(lambda: self.select_source(None))
        self.choose_reference_button.clicked.connect(self._choose_reference)
        self.clear_reference_button.clicked.connect(lambda: self.select_reference(None))
        self.choose_output_button.clicked.connect(self._choose_output)
        self.clear_output_button.clicked.connect(lambda: self._set_output(None))
        self.review_button.clicked.connect(self.review)
        self.edit_button.clicked.connect(self._edit)
        self.confirm_button.clicked.connect(self._confirm)
        self.view_result_button.clicked.connect(self.result_view.show)
        self.result_view.back_requested.connect(self.result_view.hide)
        self.result_view.recovery_requested.connect(self.recovery_requested)
        self._render_form()

    @property
    def form_state(self) -> AnalysisFormState:
        return self._form

    def select_source(self, path: Path | None) -> None:
        self._form = self._form.select_source(path)
        self._render_form()
        self.source_selected.emit(path)

    def select_reference(self, path: Path | None) -> None:
        self._form = self._form.select_reference(path).validate()
        self._render_form()
        self.references_selected.emit((path,) if path is not None else ())

    def review(self) -> None:
        selected = frozenset(
            field for field, toggle in self.feature_toggles.items() if toggle.isChecked()
        )
        self._form = self._form.configure(
            intent=self.intent_input.text(),
            delivery_target=self.delivery_input.text(),
            output_path=self._form.output_path,
            selected_features=selected,
        ).review()
        self._render_form()

    def render(self, state: PresentationState) -> None:
        if self._form.source_path is None and state.session.selected_audio is not None:
            self._form = self._form.select_source(state.session.selected_audio)
        if self._form.reference_path is None and state.session.selected_references:
            self._form = self._form.select_reference(
                state.session.selected_references[0]
            ).validate()
        self._form = self._form.with_capabilities(state.runtime.capabilities)
        self._render_features()
        result = state.result
        self.result_view.render(result)
        phase_map = {
            ResultPhase.EMPTY: ("Idle", VisualState.IDLE, "No analysis has run in this session."),
            ResultPhase.LOADING: (
                "Running",
                VisualState.RUNNING,
                "Analysis is running. Progress is indeterminate.",
            ),
            ResultPhase.SUCCESS: (
                "Result available",
                VisualState.SUCCESS,
                "Analysis completed. The retained result is ready to inspect.",
            ),
            ResultPhase.WARNING: (
                "Result available with warnings",
                VisualState.WARNING,
                "Analysis completed with warnings. The partial result is retained.",
            ),
            ResultPhase.FAILURE: (
                "Failed",
                VisualState.ERROR,
                result.error.user_message if result.error else "Analysis failed.",
            ),
            ResultPhase.CANCELLED: (
                "Cancelled",
                VisualState.CANCELLED,
                "Analysis was cancelled before completion.",
            ),
            ResultPhase.UNAVAILABLE: (
                "Unavailable",
                VisualState.UNAVAILABLE,
                "Analysis is unavailable.",
            ),
        }
        text, visual, message = phase_map[result.phase]
        self.completion_badge.setText(text)
        self.completion_badge.set_state(visual)
        self.completion_message.setText(message)
        result_available = result.result is not None and result.phase in {
            ResultPhase.SUCCESS,
            ResultPhase.WARNING,
            ResultPhase.FAILURE,
            ResultPhase.CANCELLED,
        }
        self.view_result_button.setVisible(result_available)
        if not result_available:
            self.result_view.setVisible(False)
        busy = result.phase is ResultPhase.LOADING
        self.confirm_button.setEnabled(not busy)
        self.review_button.setEnabled(
            not busy and self._form.validate().phase is AnalyzePhase.READY
        )

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if _first_local_file(event.mimeData()) is not None:
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event: QDropEvent) -> None:
        path = _first_local_file(event.mimeData())
        if path is None:
            event.ignore()
            return
        self.select_source(path)
        event.acceptProposedAction()

    def _choose_source(self) -> None:
        filename, _filter = QFileDialog.getOpenFileName(
            self, "Choose audio file", "", AUDIO_PICKER_FILTER
        )
        if filename:
            self.select_source(Path(filename))

    def _choose_reference(self) -> None:
        filename, _filter = QFileDialog.getOpenFileName(
            self, "Choose optional reference", "", AUDIO_PICKER_FILTER
        )
        if filename:
            self.select_reference(Path(filename))

    def _choose_output(self) -> None:
        filename, _filter = QFileDialog.getSaveFileName(
            self, "Choose JSON analysis output", "", "JSON files (*.json)"
        )
        if filename:
            path = Path(filename)
            self._set_output(
                path if path.suffix.casefold() == ".json" else path.with_suffix(".json")
            )

    def _set_output(self, path: Path | None) -> None:
        self._form = self._form.configure(
            intent=self.intent_input.text(),
            delivery_target=self.delivery_input.text(),
            output_path=path,
            selected_features=frozenset(
                field for field, toggle in self.feature_toggles.items() if toggle.isChecked()
            ),
        )
        self._render_form()

    def _edit(self) -> None:
        self._form = self._form.validate()
        self._render_form()

    def _confirm(self) -> None:
        if self._form.phase is AnalyzePhase.REVIEW:
            self.analysis_requested.emit(self._form)

    def _render_form(self) -> None:
        source = self._form.source_path
        self.source_label.setText(str(source) if source else "No file selected")
        if self._form.phase is AnalyzePhase.INVALID:
            self.source_status.setText("Invalid")
            self.source_status.set_state(VisualState.ERROR)
        elif source is not None:
            self.source_status.setText("Selected")
            self.source_status.set_state(VisualState.READY)
        else:
            self.source_status.setText("Required")
            self.source_status.set_state(VisualState.IDLE)
        reference = self._form.reference_path
        self.reference_label.setText(str(reference) if reference else "No reference selected")
        output = self._form.output_path
        self.output_label.setText(str(output) if output else "No JSON output path selected")
        self.validation_label.setText(self._form.validation_message or "Ready to review.")
        self.review_button.setEnabled(self._form.validate().phase is AnalyzePhase.READY)
        reviewing = self._form.phase is AnalyzePhase.REVIEW
        self.review_card.setVisible(reviewing)
        if reviewing:
            features = ", ".join(item.label for item in self._form.selected_features) or "None"
            reference_text = str(reference) if reference else "None"
            output_text = str(output) if output else "None"
            self.review_summary.setText(
                f"Audio: {source}\nReference: {reference_text}\n"
                f"Optional features: {features}\nJSON output: {output_text}"
            )
        self._render_features()

    def _render_features(self) -> None:
        for feature in self._form.features:
            toggle = self.feature_toggles[feature.field]
            toggle.setEnabled(feature.enabled)
            toggle.setChecked(feature.checked)
            state_text = feature.availability.value
            lifecycle = feature.lifecycle.value if feature.lifecycle else "unknown"
            reason = feature.reason or ""
            self.feature_reasons[feature.field].setText(
                f"Lifecycle: {lifecycle}; availability: {state_text}. {reason}".strip()
            )


def _first_local_file(mime_data) -> Path | None:
    for url in mime_data.urls():
        if url.isLocalFile():
            return Path(url.toLocalFile())
    return None
