"""Qt References page backed only by stable desktop contracts."""

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
from .presentation_state import PageId, PresentationState, ResultPhase
from .reference_result_view import ReferenceResultView
from .reference_state import ReferenceFormState, ReferencePhase

AUDIO_PICKER_FILTER = "Common audio files (*.wav *.mp3 *.flac *.ogg *.m4a *.aac);;All files (*)"


class ReferencePage(QScrollArea):
    comparison_requested = Signal(object)
    current_selected = Signal(object)
    references_selected = Signal(object)
    recovery_requested = Signal(str)
    page_id = PageId.REFERENCES

    def __init__(
        self,
        *,
        tokens: DesignTokens = DEFAULT_TOKENS,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("page-references")
        self.setAccessibleName("Reference Intelligence page")
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setAcceptDrops(True)
        self._tokens = tokens
        self._form = ReferenceFormState.initial()

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(
            tokens.spacing.xl, tokens.spacing.xl, tokens.spacing.xl, tokens.spacing.xl
        )
        layout.setSpacing(tokens.spacing.lg)
        layout.addWidget(
            PageHeader(
                "References",
                "Compare a current track with one or more real V1 reference tracks.",
                tokens=tokens,
            )
        )

        capability_card = Card("Reference comparison availability", tokens=tokens)
        self.capability_badge = StatusBadge("Unknown", VisualState.IDLE)
        self.capability_reason = QLabel(self._form.capability.reason)
        self.capability_reason.setWordWrap(True)
        capability_card.content_layout.addWidget(
            self.capability_badge, 0, Qt.AlignmentFlag.AlignLeft
        )
        capability_card.content_layout.addWidget(self.capability_reason)
        layout.addWidget(capability_card)

        current_card = Card("Current track", tokens=tokens)
        self.current_label = QLabel("No current track selected")
        self.current_label.setObjectName("referenceCurrentPath")
        self.current_label.setWordWrap(True)
        current_actions = QHBoxLayout()
        self.choose_current_button = DesignButton(
            "Choose current track", variant=ButtonVariant.PRIMARY, tokens=tokens
        )
        self.clear_current_button = DesignButton("Clear current track", tokens=tokens)
        current_actions.addWidget(self.choose_current_button)
        current_actions.addWidget(self.clear_current_button)
        current_actions.addStretch(1)
        current_card.content_layout.addWidget(self.current_label)
        current_card.content_layout.addLayout(current_actions)
        layout.addWidget(current_card)

        references_card = Card("Reference tracks", tokens=tokens)
        self.reference_list = QWidget()
        self.reference_list_layout = QVBoxLayout(self.reference_list)
        self.reference_list_layout.setContentsMargins(0, 0, 0, 0)
        self.choose_references_button = DesignButton("Add reference tracks", tokens=tokens)
        references_card.content_layout.addWidget(self.reference_list)
        references_card.content_layout.addWidget(
            self.choose_references_button, 0, Qt.AlignmentFlag.AlignLeft
        )
        layout.addWidget(references_card)

        metadata = Card("Comparison intent", tokens=tokens)
        self.genre_input = TextInput("Genre", accessible_name="Reference genre")
        self.mood_input = TextInput("Mood", accessible_name="Reference mood")
        self.target_input = TextInput("Target", accessible_name="Reference target")
        self.focus_input = TextInput(
            "Focus areas, comma separated", accessible_name="Reference focus areas"
        )
        self.output_label = QLabel("No report output directory selected")
        self.output_label.setObjectName("referenceOutputDirectory")
        output_actions = QHBoxLayout()
        self.choose_output_button = DesignButton("Choose report directory", tokens=tokens)
        self.clear_output_button = DesignButton("Clear report directory", tokens=tokens)
        output_actions.addWidget(self.choose_output_button)
        output_actions.addWidget(self.clear_output_button)
        output_actions.addStretch(1)
        for widget in (
            self.genre_input,
            self.mood_input,
            self.target_input,
            self.focus_input,
            self.output_label,
        ):
            metadata.content_layout.addWidget(widget)
        metadata.content_layout.addLayout(output_actions)
        layout.addWidget(metadata)

        self.validation_label = QLabel(self._form.validation_message)
        self.validation_label.setObjectName("referenceValidation")
        self.validation_label.setWordWrap(True)
        layout.addWidget(self.validation_label)
        self.review_button = DesignButton(
            "Review comparison", variant=ButtonVariant.PRIMARY, tokens=tokens
        )
        layout.addWidget(self.review_button, 0, Qt.AlignmentFlag.AlignLeft)

        self.review_card = Card("Confirm comparison", tokens=tokens)
        self.review_summary = QLabel()
        self.review_summary.setObjectName("referenceReviewSummary")
        self.review_summary.setWordWrap(True)
        review_actions = QHBoxLayout()
        self.compare_button = DesignButton(
            "Run comparison", variant=ButtonVariant.PRIMARY, tokens=tokens
        )
        self.edit_button = DesignButton("Back to configuration", tokens=tokens)
        review_actions.addWidget(self.compare_button)
        review_actions.addWidget(self.edit_button)
        review_actions.addStretch(1)
        self.review_card.content_layout.addWidget(self.review_summary)
        self.review_card.content_layout.addLayout(review_actions)
        layout.addWidget(self.review_card)

        status_card = Card("Comparison status", tokens=tokens)
        self.status_badge = StatusBadge("Idle", VisualState.IDLE)
        self.status_message = QLabel("No comparison has run in this session.")
        self.status_message.setWordWrap(True)
        self.view_result_button = DesignButton(
            "View comparison result", variant=ButtonVariant.PRIMARY, tokens=tokens
        )
        self.view_result_button.setVisible(False)
        status_card.content_layout.addWidget(self.status_badge, 0, Qt.AlignmentFlag.AlignLeft)
        status_card.content_layout.addWidget(self.status_message)
        status_card.content_layout.addWidget(self.view_result_button, 0, Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(status_card)
        self.result_view = ReferenceResultView(tokens=tokens)
        self.result_view.setVisible(False)
        layout.addWidget(self.result_view)
        layout.addStretch(1)
        self.setWidget(content)

        self.choose_current_button.clicked.connect(self._choose_current)
        self.clear_current_button.clicked.connect(lambda: self.select_current(None))
        self.choose_references_button.clicked.connect(self._choose_references)
        self.choose_output_button.clicked.connect(self._choose_output)
        self.clear_output_button.clicked.connect(lambda: self._set_output(None))
        self.review_button.clicked.connect(self.review)
        self.edit_button.clicked.connect(self._edit)
        self.compare_button.clicked.connect(self._confirm)
        self.view_result_button.clicked.connect(self.result_view.show)
        self.result_view.back_requested.connect(self.result_view.hide)
        self.result_view.recovery_requested.connect(self.recovery_requested)
        self._render_form()

    @property
    def form_state(self) -> ReferenceFormState:
        return self._form

    def select_current(self, path: Path | None) -> None:
        self._form = self._form.select_current(path)
        self._render_form()
        self.current_selected.emit(path)

    def add_references(self, paths: tuple[Path, ...]) -> None:
        self._form = self._form.add_references(paths)
        self._render_form()
        self.references_selected.emit(self._form.reference_paths)

    def remove_reference(self, path: Path) -> None:
        self._form = self._form.remove_reference(path)
        self._render_form()
        self.references_selected.emit(self._form.reference_paths)

    def review(self) -> None:
        self._capture_configuration()
        self._form = self._form.review()
        self._render_form()

    def render(self, state: PresentationState) -> None:
        if self._form.current_path is None and state.session.selected_audio is not None:
            self._form = self._form.select_current(state.session.selected_audio)
        if not self._form.reference_paths and state.session.selected_references:
            self._form = self._form.add_references(state.session.selected_references)
        self._form = self._form.with_capabilities(state.runtime.capabilities)
        capability = self._form.capability
        self.capability_badge.setText(capability.availability.value.title())
        self.capability_badge.set_state(availability_visual_state(capability.availability))
        self.capability_reason.setText(capability.reason)
        self._render_form()
        result = state.reference_result
        self.result_view.render(result)
        mapping = {
            ResultPhase.EMPTY: ("Idle", VisualState.IDLE, "No comparison has run in this session."),
            ResultPhase.LOADING: (
                "Running",
                VisualState.RUNNING,
                "Comparison is running. Progress is indeterminate and cancellation is unavailable.",
            ),
            ResultPhase.SUCCESS: ("Result available", VisualState.SUCCESS, "Comparison completed."),
            ResultPhase.WARNING: (
                "Result with warnings",
                VisualState.WARNING,
                "Comparison completed with warnings; returned data remains inspectable.",
            ),
            ResultPhase.FAILURE: (
                "Failed",
                VisualState.ERROR,
                result.error.user_message if result.error else "Comparison failed.",
            ),
            ResultPhase.CANCELLED: (
                "Cancelled",
                VisualState.CANCELLED,
                "Comparison was cancelled.",
            ),
            ResultPhase.UNAVAILABLE: (
                "Unavailable",
                VisualState.UNAVAILABLE,
                "Reference comparison is unavailable.",
            ),
        }
        text, visual, message = mapping[result.phase]
        self.status_badge.setText(text)
        self.status_badge.set_state(visual)
        self.status_message.setText(message)
        available = result.result is not None and result.phase in {
            ResultPhase.SUCCESS,
            ResultPhase.WARNING,
            ResultPhase.FAILURE,
            ResultPhase.CANCELLED,
        }
        self.view_result_button.setVisible(available)
        if not available:
            self.result_view.hide()
        busy = result.phase is ResultPhase.LOADING
        self.compare_button.setEnabled(not busy)
        self.review_button.setEnabled(
            not busy and self._form.validate().phase is ReferencePhase.READY
        )

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if _local_files(event.mimeData()):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event: QDropEvent) -> None:
        paths = _local_files(event.mimeData())
        if not paths:
            event.ignore()
            return
        if self._form.current_path is None:
            self.select_current(paths[0])
            self.add_references(paths[1:])
        else:
            self.add_references(paths)
        event.acceptProposedAction()

    def _choose_current(self) -> None:
        filename, _ = QFileDialog.getOpenFileName(
            self, "Choose current track", "", AUDIO_PICKER_FILTER
        )
        if filename:
            self.select_current(Path(filename))

    def _choose_references(self) -> None:
        filenames, _ = QFileDialog.getOpenFileNames(
            self, "Choose reference tracks", "", AUDIO_PICKER_FILTER
        )
        self.add_references(tuple(Path(item) for item in filenames))

    def _choose_output(self) -> None:
        directory = QFileDialog.getExistingDirectory(self, "Choose reference report directory")
        if directory:
            self._set_output(Path(directory))

    def _set_output(self, path: Path | None) -> None:
        self._form = self._form.configure(
            genre=self.genre_input.text(),
            mood=self.mood_input.text(),
            target=self.target_input.text(),
            focus_areas=tuple(self.focus_input.text().split(",")),
            output_directory=path,
        )
        self._render_form()

    def _capture_configuration(self) -> None:
        self._form = self._form.configure(
            genre=self.genre_input.text(),
            mood=self.mood_input.text(),
            target=self.target_input.text(),
            focus_areas=tuple(self.focus_input.text().split(",")),
            output_directory=self._form.output_directory,
        )

    def _edit(self) -> None:
        self._form = self._form.validate()
        self._render_form()

    def _confirm(self) -> None:
        if self._form.phase is ReferencePhase.REVIEW:
            self.comparison_requested.emit(self._form)

    def _render_form(self) -> None:
        self.current_label.setText(
            str(self._form.current_path) if self._form.current_path else "No current track selected"
        )
        while self.reference_list_layout.count():
            item = self.reference_list_layout.takeAt(0)
            if item.widget() is not None:
                item.widget().deleteLater()
        if not self._form.reference_paths:
            self.reference_list_layout.addWidget(QLabel("No reference tracks selected"))
        for path in self._form.reference_paths:
            row = QWidget()
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(0, 0, 0, 0)
            label = QLabel(str(path))
            label.setObjectName("referenceSelectedPath")
            label.setWordWrap(True)
            remove = DesignButton("Remove", tokens=self._tokens)
            remove.clicked.connect(
                lambda _checked=False, selected=path: self.remove_reference(selected)
            )
            row_layout.addWidget(label, 1)
            row_layout.addWidget(remove)
            self.reference_list_layout.addWidget(row)
        self.output_label.setText(
            str(self._form.output_directory)
            if self._form.output_directory
            else "No report output directory selected"
        )
        self.validation_label.setText(self._form.validation_message)
        self.review_button.setEnabled(self._form.validate().phase is ReferencePhase.READY)
        reviewing = self._form.phase is ReferencePhase.REVIEW
        self.review_card.setVisible(reviewing)
        if reviewing:
            self.review_summary.setText(
                f"Current: {self._form.current_path}\nReferences:\n"
                + "\n".join(str(path) for path in self._form.reference_paths)
                + f"\nGenre: {self._form.genre or 'Not supplied'}"
                + f"\nMood: {self._form.mood or 'Not supplied'}"
                + f"\nTarget: {self._form.target or 'Not supplied'}"
                + f"\nFocus areas: {', '.join(self._form.focus_areas) or 'None'}"
                + f"\nReport directory: {self._form.output_directory or 'None'}"
            )


def _local_files(mime_data) -> tuple[Path, ...]:
    return tuple(Path(url.toLocalFile()) for url in mime_data.urls() if url.isLocalFile())

