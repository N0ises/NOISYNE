"""Qt-free contracts for the future voice and conversational UI boundary."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from enum import Enum

from .agent_contracts import (
    ActionExecution,
    AgentPlan,
    ConfirmationDecision,
    VerificationResult,
)
from .contracts import Availability, ResultUsability, UiError


class VoiceLifecycle(str, Enum):
    IDLE = "idle"
    LISTENING = "listening"
    TRANSCRIBING = "transcribing"
    UNDERSTANDING = "understanding"
    PLANNING = "planning"
    WAITING_FOR_CONFIRMATION = "waiting_for_confirmation"
    EXECUTING = "executing"
    VERIFYING = "verifying"
    RESPONDING = "responding"


_ROADMAP_TRANSITIONS = {
    VoiceLifecycle.IDLE: frozenset({VoiceLifecycle.LISTENING}),
    VoiceLifecycle.LISTENING: frozenset({VoiceLifecycle.TRANSCRIBING, VoiceLifecycle.IDLE}),
    VoiceLifecycle.TRANSCRIBING: frozenset({VoiceLifecycle.UNDERSTANDING, VoiceLifecycle.IDLE}),
    VoiceLifecycle.UNDERSTANDING: frozenset({VoiceLifecycle.PLANNING, VoiceLifecycle.IDLE}),
    VoiceLifecycle.PLANNING: frozenset(
        {VoiceLifecycle.WAITING_FOR_CONFIRMATION, VoiceLifecycle.IDLE}
    ),
    VoiceLifecycle.WAITING_FOR_CONFIRMATION: frozenset(
        {VoiceLifecycle.EXECUTING, VoiceLifecycle.IDLE}
    ),
    VoiceLifecycle.EXECUTING: frozenset({VoiceLifecycle.VERIFYING, VoiceLifecycle.IDLE}),
    VoiceLifecycle.VERIFYING: frozenset({VoiceLifecycle.RESPONDING, VoiceLifecycle.IDLE}),
    VoiceLifecycle.RESPONDING: frozenset({VoiceLifecycle.IDLE}),
}


class MicrophonePermission(str, Enum):
    UNKNOWN = "unknown"
    GRANTED = "granted"
    DENIED = "denied"
    UNAVAILABLE = "unavailable"
    NOT_APPLICABLE = "not_applicable"


@dataclass(frozen=True, slots=True)
class MicrophoneStatus:
    permission: MicrophonePermission = MicrophonePermission.UNKNOWN
    availability: Availability = Availability.UNKNOWN
    reason: str = "Microphone permission has not been checked."


@dataclass(frozen=True, slots=True)
class VoiceAvailability:
    """Availability truth, deliberately separate from lifecycle."""

    ui_available: bool = True
    engine: Availability = Availability.UNAVAILABLE
    microphone: MicrophoneStatus = MicrophoneStatus()
    provider: Availability = Availability.UNAVAILABLE
    model: Availability = Availability.UNAVAILABLE
    reason: str = "Voice engine is not available in the V1 desktop runtime."

    @property
    def can_listen(self) -> bool:
        return (
            self.ui_available
            and self.engine is Availability.AVAILABLE
            and self.microphone.availability is Availability.AVAILABLE
            and self.microphone.permission is MicrophonePermission.GRANTED
        )


class TranscriptRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    AGENT = "agent"
    SYSTEM = "system"


class TranscriptStatus(str, Enum):
    PENDING = "pending"
    FINAL = "final"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class TranscriptItem:
    message_id: str
    role: TranscriptRole
    text: str
    created_at: datetime
    status: TranscriptStatus = TranscriptStatus.FINAL
    source: str | None = None


@dataclass(frozen=True, slots=True)
class ConversationHistory:
    items: tuple[TranscriptItem, ...] = ()
    limit: int = 50

    def append(self, item: TranscriptItem) -> ConversationHistory:
        if self.limit < 1:
            raise ValueError("Conversation history limit must be positive.")
        return replace(self, items=(*self.items, item)[-self.limit :])


@dataclass(frozen=True, slots=True)
class ActionProposal:
    proposal_id: str
    title: str
    summary: str
    proposed_actions: tuple[str, ...]
    impact_summary: str
    confirmation_required: bool = True
    affected_target: str | None = None


class ActionResultStatus(str, Enum):
    COMPLETED = "completed"
    AVAILABLE = "available"
    PARTIALLY_AVAILABLE = "partially_available"
    FAILED = "failed"
    BLOCKED = "blocked"
    CANCELLED = "cancelled"


@dataclass(frozen=True, slots=True)
class ActionResultSummary:
    status: ActionResultStatus
    title: str
    detail: str
    usability: ResultUsability = ResultUsability.NOT_APPLICABLE
    error: UiError | None = None


@dataclass(frozen=True, slots=True)
class VoicePresentationState:
    lifecycle: VoiceLifecycle = VoiceLifecycle.IDLE
    availability: VoiceAvailability = VoiceAvailability()
    conversation: ConversationHistory = ConversationHistory()
    proposal: ActionProposal | None = None
    result: ActionResultSummary | None = None
    agent_plan: AgentPlan | None = None
    confirmation: ConfirmationDecision | None = None
    executions: tuple[ActionExecution, ...] = ()
    verification: VerificationResult = field(default_factory=VerificationResult)
    interruption_requested: bool = False

    def transition(self, next_state: VoiceLifecycle) -> VoicePresentationState:
        if next_state is self.lifecycle:
            return self
        if next_state not in _ROADMAP_TRANSITIONS[self.lifecycle]:
            raise ValueError(
                f"Invalid voice transition: {self.lifecycle.value} -> {next_state.value}"
            )
        return replace(self, lifecycle=next_state, interruption_requested=False)

    def request_interruption(self) -> VoicePresentationState:
        if self.lifecycle is VoiceLifecycle.IDLE:
            return self
        return replace(
            self,
            lifecycle=VoiceLifecycle.IDLE,
            interruption_requested=True,
        )

    def append_transcript(self, item: TranscriptItem) -> VoicePresentationState:
        return replace(self, conversation=self.conversation.append(item))


def transcript_item(
    message_id: str,
    role: TranscriptRole,
    text: str,
    *,
    status: TranscriptStatus = TranscriptStatus.FINAL,
    source: str | None = None,
    created_at: datetime | None = None,
) -> TranscriptItem:
    """Convenience constructor for adapters that do not own a clock abstraction."""
    return TranscriptItem(
        message_id=message_id,
        role=role,
        text=text,
        created_at=created_at or datetime.now(UTC),
        status=status,
        source=source,
    )
