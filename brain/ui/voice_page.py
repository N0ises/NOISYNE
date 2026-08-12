"""Voice-ready workspace built only from stable presentation contracts."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from .contracts import Availability, ResultUsability
from .design_system.components import (
    ButtonVariant,
    Card,
    ConfirmationDialog,
    DesignButton,
    PageHeader,
    ProgressIndicator,
    StatusBadge,
)
from .design_system.semantics import (
    VisualState,
    availability_visual_state,
    operation_visual_state,
)
from .design_system.tokens import DEFAULT_TOKENS, DesignTokens
from .presentation_state import OperationPresentationState, PageId, PresentationState
from .voice_contracts import (
    ActionProposal,
    ActionResultStatus,
    ActionResultSummary,
    MicrophonePermission,
    TranscriptItem,
    VoiceAvailability,
    VoiceLifecycle,
    VoicePresentationState,
)

_LIFECYCLE_LABELS = {
    VoiceLifecycle.IDLE: "Idle",
    VoiceLifecycle.LISTENING: "Listening",
    VoiceLifecycle.TRANSCRIBING: "Transcribing",
    VoiceLifecycle.UNDERSTANDING: "Understanding",
    VoiceLifecycle.PLANNING: "Planning",
    VoiceLifecycle.WAITING_FOR_CONFIRMATION: "Waiting for confirmation",
    VoiceLifecycle.EXECUTING: "Executing",
    VoiceLifecycle.VERIFYING: "Verifying",
    VoiceLifecycle.RESPONDING: "Response ready",
}

_LIFECYCLE_VISUALS = {
    VoiceLifecycle.IDLE: VisualState.IDLE,
    VoiceLifecycle.LISTENING: VisualState.RUNNING,
    VoiceLifecycle.TRANSCRIBING: VisualState.RUNNING,
    VoiceLifecycle.UNDERSTANDING: VisualState.INTELLIGENCE,
    VoiceLifecycle.PLANNING: VisualState.INTELLIGENCE,
    VoiceLifecycle.WAITING_FOR_CONFIRMATION: VisualState.WARNING,
    VoiceLifecycle.EXECUTING: VisualState.RUNNING,
    VoiceLifecycle.VERIFYING: VisualState.INFO,
    VoiceLifecycle.RESPONDING: VisualState.INTELLIGENCE,
}

_PROCESSING_STATES = frozenset(
    {
        VoiceLifecycle.TRANSCRIBING,
        VoiceLifecycle.UNDERSTANDING,
        VoiceLifecycle.PLANNING,
        VoiceLifecycle.EXECUTING,
        VoiceLifecycle.VERIFYING,
    }
)


class VoiceInputControl(Card):
    start_listening_requested = Signal()
    stop_listening_requested = Signal()
    interruption_requested = Signal()

    def __init__(
        self,
        *,
        tokens: DesignTokens = DEFAULT_TOKENS,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__("Voice input", tokens=tokens, parent=parent)
        self.setObjectName("voiceInputControl")
        self.setAccessibleName("Voice input control")
        self.state_label = QLabel()
        self.state_label.setObjectName("voiceInputState")
        self.state_label.setWordWrap(True)
        self.state_badge = StatusBadge("Idle", VisualState.IDLE)
        self.processing = ProgressIndicator(
            None,
            accessible_name="Voice processing activity",
        )
        self.action_button = DesignButton(
            "Start listening",
            variant=ButtonVariant.PRIMARY,
            tokens=tokens,
        )
        self.action_button.setObjectName("voiceInputAction")
        self.action_button.clicked.connect(self._emit_current_intent)
        self.content_layout.addWidget(self.state_badge, 0, Qt.AlignmentFlag.AlignLeft)
        self.content_layout.addWidget(self.state_label)
        self.content_layout.addWidget(self.processing)
        self.content_layout.addWidget(
            self.action_button,
            0,
            Qt.AlignmentFlag.AlignLeft,
        )
        self._state = VoicePresentationState()
        self.render(self._state)

    def render(self, state: VoicePresentationState) -> None:
        self._state = state
        lifecycle = state.lifecycle
        self.state_badge.setText(_LIFECYCLE_LABELS[lifecycle])
        self.state_badge.set_state(_LIFECYCLE_VISUALS[lifecycle])
        self.processing.setVisible(lifecycle in _PROCESSING_STATES)

        if lifecycle is VoiceLifecycle.IDLE:
            if state.availability.can_listen:
                self.action_button.setText("Start listening")
                self.action_button.setAccessibleName("Start voice listening")
                self.action_button.setEnabled(True)
                self.state_label.setText("Voice input is available.")
            else:
                self.action_button.setText("Voice unavailable")
                self.action_button.setAccessibleName("Voice input unavailable")
                self.action_button.setEnabled(False)
                self.state_label.setText(state.availability.reason)
        elif lifecycle is VoiceLifecycle.LISTENING:
            self.action_button.setText("Stop listening")
            self.action_button.setAccessibleName("Stop voice listening")
            self.action_button.setEnabled(True)
            self.state_label.setText("Listening. No audio level is fabricated by this UI.")
        else:
            self.action_button.setText("Interrupt")
            self.action_button.setAccessibleName("Request voice interaction interruption")
            self.action_button.setEnabled(True)
            self.state_label.setText(_state_description(lifecycle))

    def _emit_current_intent(self) -> None:
        if self._state.lifecycle is VoiceLifecycle.IDLE:
            self.start_listening_requested.emit()
        elif self._state.lifecycle is VoiceLifecycle.LISTENING:
            self.stop_listening_requested.emit()
        else:
            self.interruption_requested.emit()


class VoiceAvailabilitySurface(Card):
    def __init__(
        self,
        *,
        tokens: DesignTokens = DEFAULT_TOKENS,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__("Availability truth", tokens=tokens, parent=parent)
        self.setObjectName("voiceAvailability")
        self.ui_badge = StatusBadge("UI available", VisualState.READY)
        self.engine_badge = StatusBadge("Engine unavailable", VisualState.UNAVAILABLE)
        self.permission_badge = StatusBadge("Permission unknown", VisualState.UNKNOWN)
        self.provider_badge = StatusBadge("Provider unavailable", VisualState.UNAVAILABLE)
        self.model_badge = StatusBadge("Model unavailable", VisualState.UNAVAILABLE)
        badges = QHBoxLayout()
        badges.setSpacing(tokens.spacing.sm)
        for badge in (
            self.ui_badge,
            self.engine_badge,
            self.permission_badge,
            self.provider_badge,
            self.model_badge,
        ):
            badges.addWidget(badge)
        badges.addStretch(1)
        self.reason_label = QLabel()
        self.reason_label.setProperty("textRole", "secondary")
        self.reason_label.setWordWrap(True)
        self.content_layout.addLayout(badges)
        self.content_layout.addWidget(self.reason_label)

    def render(self, availability: VoiceAvailability) -> None:
        self.ui_badge.setText("UI available" if availability.ui_available else "UI unavailable")
        self.ui_badge.set_state(
            VisualState.READY if availability.ui_available else VisualState.UNAVAILABLE
        )
        _set_availability_badge(self.engine_badge, "Engine", availability.engine)
        _set_availability_badge(self.provider_badge, "Provider", availability.provider)
        _set_availability_badge(self.model_badge, "Model", availability.model)
        permission = availability.microphone.permission
        self.permission_badge.setText(f"Permission {permission.value.replace('_', ' ')}")
        self.permission_badge.set_state(_permission_visual(permission))
        self.reason_label.setText(availability.reason)


class AgentStatusSurface(Card):
    def __init__(
        self,
        *,
        tokens: DesignTokens = DEFAULT_TOKENS,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__("Agent status", component="panel", tokens=tokens, parent=parent)
        self.setProperty("semantic", "intelligence")
        self.setObjectName("voiceAgentStatus")
        self.badge = StatusBadge("Idle", VisualState.IDLE)
        self.detail = QLabel("No voice or agent engine is active.")
        self.detail.setWordWrap(True)
        self.content_layout.addWidget(self.badge, 0, Qt.AlignmentFlag.AlignLeft)
        self.content_layout.addWidget(self.detail)

    def render(self, state: VoicePresentationState) -> None:
        if (
            state.lifecycle is VoiceLifecycle.IDLE
            and state.availability.engine is not Availability.AVAILABLE
        ):
            self.badge.setText(
                "Unknown" if state.availability.engine is Availability.UNKNOWN else "Unavailable"
            )
            self.badge.set_state(availability_visual_state(state.availability.engine))
            self.detail.setText(state.availability.reason)
            return
        self.badge.setText(_LIFECYCLE_LABELS[state.lifecycle])
        self.badge.set_state(_LIFECYCLE_VISUALS[state.lifecycle])
        self.detail.setText(_state_description(state.lifecycle))


class TranscriptSurface(Card):
    def __init__(
        self,
        *,
        tokens: DesignTokens = DEFAULT_TOKENS,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__("Conversation transcript", tokens=tokens, parent=parent)
        self.setObjectName("voiceTranscript")
        self.setAccessibleName("Conversation transcript")
        self._tokens = tokens
        self._message_widgets: list[QWidget] = []
        self.empty_label = QLabel("No conversation has started.")
        self.empty_label.setObjectName("voiceTranscriptEmpty")
        self.empty_label.setProperty("textRole", "secondary")
        self.content_layout.addWidget(self.empty_label)

    def render(self, items: tuple[TranscriptItem, ...]) -> None:
        for widget in self._message_widgets:
            self.content_layout.removeWidget(widget)
            widget.setParent(None)
            widget.deleteLater()
        self._message_widgets.clear()
        self.empty_label.setVisible(not items)
        for item in items:
            frame = QFrame()
            frame.setObjectName(f"transcript-{item.message_id}")
            frame.setProperty("component", "panel")
            frame.setAccessibleName(f"{item.role.value} transcript message")
            layout = QVBoxLayout(frame)
            layout.setContentsMargins(
                self._tokens.spacing.md,
                self._tokens.spacing.sm,
                self._tokens.spacing.md,
                self._tokens.spacing.sm,
            )
            meta = QLabel(
                f"{item.role.value.title()} · {item.status.value.replace('_', ' ').title()}"
            )
            meta.setProperty("textRole", "caption")
            text = QLabel(item.text)
            text.setWordWrap(True)
            text.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            layout.addWidget(meta)
            layout.addWidget(text)
            self.content_layout.addWidget(frame)
            self._message_widgets.append(frame)


class ActionProposalCard(Card):
    confirmation_requested = Signal(str)

    def __init__(
        self,
        *,
        tokens: DesignTokens = DEFAULT_TOKENS,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__("Proposed action", component="panel", tokens=tokens, parent=parent)
        self.setProperty("semantic", "intelligence")
        self.setObjectName("voiceActionProposal")
        self._proposal: ActionProposal | None = None
        self.title_label = QLabel()
        self.title_label.setProperty("textRole", "title")
        self.summary_label = QLabel()
        self.summary_label.setWordWrap(True)
        self.actions_label = QLabel()
        self.actions_label.setWordWrap(True)
        self.impact_label = QLabel()
        self.impact_label.setWordWrap(True)
        self.target_label = QLabel()
        self.target_label.setProperty("textRole", "technical")
        self.target_label.setWordWrap(True)
        self.review_button = DesignButton(
            "Review and confirm",
            variant=ButtonVariant.PRIMARY,
            tokens=tokens,
        )
        self.review_button.setAccessibleName("Review proposed action")
        self.review_button.clicked.connect(self._request_confirmation)
        for widget in (
            self.title_label,
            self.summary_label,
            self.actions_label,
            self.impact_label,
            self.target_label,
            self.review_button,
        ):
            self.content_layout.addWidget(widget)
        self.setVisible(False)

    def render(self, proposal: ActionProposal | None) -> None:
        self._proposal = proposal
        self.setVisible(proposal is not None)
        if proposal is None:
            return
        self.title_label.setText(proposal.title)
        self.summary_label.setText(proposal.summary)
        self.actions_label.setText(
            "Proposed steps\n" + "\n".join(f"• {item}" for item in proposal.proposed_actions)
        )
        self.impact_label.setText(f"Impact\n{proposal.impact_summary}")
        self.target_label.setText(
            f"Affected target: {proposal.affected_target}"
            if proposal.affected_target
            else "Affected target: not specified"
        )
        self.review_button.setVisible(proposal.confirmation_required)

    def _request_confirmation(self) -> None:
        if self._proposal is not None:
            self.confirmation_requested.emit(self._proposal.proposal_id)


class ActionConfirmationDialog(ConfirmationDialog):
    def __init__(
        self,
        proposal: ActionProposal,
        *,
        tokens: DesignTokens = DEFAULT_TOKENS,
        parent: QWidget | None = None,
    ) -> None:
        target = proposal.affected_target or "No target was specified."
        actions = "\n".join(f"• {item}" for item in proposal.proposed_actions)
        super().__init__(
            "Confirm proposed action",
            (
                f"{proposal.title}\n\n{proposal.summary}\n\n"
                f"Proposed steps:\n{actions}\n\n"
                f"Affected target: {target}\n\nImpact: {proposal.impact_summary}"
            ),
            confirm_label="Confirm action",
            tokens=tokens,
            parent=parent,
        )
        self.setObjectName("voiceActionConfirmation")
        self.setAccessibleName("Confirm proposed voice agent action")


class VoiceExecutionProgress(Card):
    def __init__(
        self,
        *,
        tokens: DesignTokens = DEFAULT_TOKENS,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__("Execution progress", tokens=tokens, parent=parent)
        self.setObjectName("voiceExecutionProgress")
        self.badge = StatusBadge("Idle", VisualState.IDLE)
        self.message = QLabel("No proposed action is executing.")
        self.message.setWordWrap(True)
        self.progress = ProgressIndicator(None, accessible_name="Agent action progress")
        self.content_layout.addWidget(self.badge, 0, Qt.AlignmentFlag.AlignLeft)
        self.content_layout.addWidget(self.message)
        self.content_layout.addWidget(self.progress)
        self.render(OperationPresentationState())

    def render(self, operation: OperationPresentationState) -> None:
        state_text = operation.state.value if operation.state else "idle"
        self.badge.setText(state_text.replace("_", " ").title())
        self.badge.set_state(operation_visual_state(operation.state))
        active = not operation.is_idle and not operation.is_terminal
        self.progress.setVisible(active)
        if active:
            self.progress.set_progress(operation.progress)
        self.message.setText(
            operation.message or operation.kind or "No proposed action is executing."
        )


class ResultSummarySurface(Card):
    def __init__(
        self,
        *,
        tokens: DesignTokens = DEFAULT_TOKENS,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__("Result summary", tokens=tokens, parent=parent)
        self.setObjectName("voiceResultSummary")
        self.badge = StatusBadge("No result", VisualState.IDLE)
        self.title_label = QLabel("No conversational action result is available.")
        self.title_label.setProperty("textRole", "title")
        self.detail_label = QLabel()
        self.detail_label.setWordWrap(True)
        self.content_layout.addWidget(self.badge, 0, Qt.AlignmentFlag.AlignLeft)
        self.content_layout.addWidget(self.title_label)
        self.content_layout.addWidget(self.detail_label)

    def render(self, result: ActionResultSummary | None) -> None:
        if result is None:
            self.badge.setText("No result")
            self.badge.set_state(VisualState.IDLE)
            self.title_label.setText("No conversational action result is available.")
            self.detail_label.clear()
            return
        visual = {
            ActionResultStatus.COMPLETED: VisualState.SUCCESS,
            ActionResultStatus.AVAILABLE: VisualState.READY,
            ActionResultStatus.PARTIALLY_AVAILABLE: VisualState.WARNING,
            ActionResultStatus.FAILED: VisualState.ERROR,
        }[result.status]
        self.badge.setText(result.status.value.replace("_", " ").title())
        self.badge.set_state(visual)
        self.title_label.setText(result.title)
        detail = result.error.user_message if result.error is not None else result.detail
        if result.usability is not ResultUsability.NOT_APPLICABLE:
            detail = f"{detail}\n{result.usability.value.replace('_', ' ').title()} result."
        self.detail_label.setText(detail)


class VoicePage(QScrollArea):
    page_id = PageId.VOICE
    start_listening_requested = Signal()
    stop_listening_requested = Signal()
    interruption_requested = Signal()
    proposal_confirmed = Signal(str)
    proposal_cancelled = Signal(str)

    def __init__(
        self,
        *,
        tokens: DesignTokens = DEFAULT_TOKENS,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("page-voice")
        self.setAccessibleName("Voice and agent workspace")
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._tokens = tokens
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
                "Voice / Agent",
                "Voice-ready presentation infrastructure. No V1 voice engine is configured.",
                tokens=tokens,
            )
        )
        self.availability = VoiceAvailabilitySurface(tokens=tokens)
        self.agent_status = AgentStatusSurface(tokens=tokens)
        self.input_control = VoiceInputControl(tokens=tokens)
        self.transcript = TranscriptSurface(tokens=tokens)
        self.proposal = ActionProposalCard(tokens=tokens)
        self.execution = VoiceExecutionProgress(tokens=tokens)
        self.result = ResultSummarySurface(tokens=tokens)
        for widget in (
            self.availability,
            self.agent_status,
            self.input_control,
            self.transcript,
            self.proposal,
            self.execution,
            self.result,
        ):
            layout.addWidget(widget)
        layout.addStretch(1)
        self.setWidget(content)
        self.input_control.start_listening_requested.connect(self.start_listening_requested)
        self.input_control.stop_listening_requested.connect(self.stop_listening_requested)
        self.input_control.interruption_requested.connect(self.interruption_requested)
        self.proposal.confirmation_requested.connect(self._confirm_proposal)
        self._current_state = VoicePresentationState()
        self.render(PresentationState())

    def render(self, state: PresentationState) -> None:
        self._current_state = state.voice
        self.availability.render(state.voice.availability)
        self.agent_status.render(state.voice)
        self.input_control.render(state.voice)
        self.transcript.render(state.voice.conversation.items)
        self.proposal.render(state.voice.proposal)
        self.execution.render(state.operation)
        self.result.render(state.voice.result)

    def _confirm_proposal(self, proposal_id: str) -> None:
        proposal = self._current_state.proposal
        if proposal is None or proposal.proposal_id != proposal_id:
            return
        dialog = ActionConfirmationDialog(proposal, tokens=self._tokens, parent=self)
        if dialog.exec() == ConfirmationDialog.DialogCode.Accepted:
            self.proposal_confirmed.emit(proposal_id)
        else:
            self.proposal_cancelled.emit(proposal_id)


def _set_availability_badge(
    badge: StatusBadge,
    label: str,
    availability: Availability,
) -> None:
    badge.setText(f"{label} {availability.value}")
    badge.set_state(availability_visual_state(availability))


def _permission_visual(permission: MicrophonePermission) -> VisualState:
    return {
        MicrophonePermission.UNKNOWN: VisualState.UNKNOWN,
        MicrophonePermission.GRANTED: VisualState.READY,
        MicrophonePermission.DENIED: VisualState.ERROR,
        MicrophonePermission.UNAVAILABLE: VisualState.UNAVAILABLE,
        MicrophonePermission.NOT_APPLICABLE: VisualState.DISABLED,
    }[permission]


def _state_description(lifecycle: VoiceLifecycle) -> str:
    return {
        VoiceLifecycle.IDLE: "No voice or agent engine is active.",
        VoiceLifecycle.LISTENING: "Listening state reported by the future voice boundary.",
        VoiceLifecycle.TRANSCRIBING: "Transcribing input. Progress is indeterminate.",
        VoiceLifecycle.UNDERSTANDING: "Interpreting the transcript.",
        VoiceLifecycle.PLANNING: "Preparing a proposed action for review.",
        VoiceLifecycle.WAITING_FOR_CONFIRMATION: "Waiting for explicit user confirmation.",
        VoiceLifecycle.EXECUTING: "Executing a confirmed operation through shared operation state.",
        VoiceLifecycle.VERIFYING: "Verifying the reported operation result.",
        VoiceLifecycle.RESPONDING: (
            "A response is ready. Speech output is unavailable until a voice engine reports it."
        ),
    }[lifecycle]
