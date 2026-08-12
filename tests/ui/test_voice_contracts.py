from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime

import pytest

from brain.ui.contracts import Availability, ResultUsability
from brain.ui.presentation_state import PresentationState
from brain.ui.presentation_store import PresentationStore
from brain.ui.voice_contracts import (
    ActionProposal,
    ActionResultStatus,
    ActionResultSummary,
    ConversationHistory,
    MicrophonePermission,
    MicrophoneStatus,
    TranscriptItem,
    TranscriptRole,
    TranscriptStatus,
    VoiceAvailability,
    VoiceLifecycle,
    VoicePresentationState,
)

ROADMAP_FLOW = (
    VoiceLifecycle.IDLE,
    VoiceLifecycle.LISTENING,
    VoiceLifecycle.TRANSCRIBING,
    VoiceLifecycle.UNDERSTANDING,
    VoiceLifecycle.PLANNING,
    VoiceLifecycle.WAITING_FOR_CONFIRMATION,
    VoiceLifecycle.EXECUTING,
    VoiceLifecycle.VERIFYING,
    VoiceLifecycle.RESPONDING,
    VoiceLifecycle.IDLE,
)


def _message(index: int, role: TranscriptRole = TranscriptRole.USER) -> TranscriptItem:
    return TranscriptItem(
        message_id=f"message-{index}",
        role=role,
        text=f"Message {index}",
        created_at=datetime(2026, 1, 1, 0, 0, index, tzinfo=UTC),
    )


def test_voice_lifecycle_has_exact_roadmap_states_and_idle_default() -> None:
    assert tuple(VoiceLifecycle) == ROADMAP_FLOW[:-1]
    assert VoicePresentationState().lifecycle is VoiceLifecycle.IDLE


def test_complete_roadmap_transition_path_is_valid() -> None:
    state = VoicePresentationState()

    for next_state in ROADMAP_FLOW[1:]:
        state = state.transition(next_state)

    assert state.lifecycle is VoiceLifecycle.IDLE
    assert not state.interruption_requested


def test_invalid_voice_transition_is_rejected_without_state_mutation() -> None:
    state = VoicePresentationState()

    with pytest.raises(ValueError, match="idle -> planning"):
        state.transition(VoiceLifecycle.PLANNING)

    assert state.lifecycle is VoiceLifecycle.IDLE


@pytest.mark.parametrize("lifecycle", tuple(VoiceLifecycle)[1:])
def test_active_voice_states_have_safe_ui_interruption_path(lifecycle) -> None:
    state = replace(VoicePresentationState(), lifecycle=lifecycle)

    interrupted = state.request_interruption()

    assert interrupted.lifecycle is VoiceLifecycle.IDLE
    assert interrupted.interruption_requested


def test_idle_interruption_is_safely_ignored() -> None:
    state = VoicePresentationState()
    assert state.request_interruption() is state


def test_microphone_and_voice_availability_are_separate_truths() -> None:
    default = VoiceAvailability()

    assert default.ui_available
    assert default.engine is Availability.UNAVAILABLE
    assert default.microphone.permission is MicrophonePermission.UNKNOWN
    assert default.microphone.availability is Availability.UNKNOWN
    assert default.provider is Availability.UNAVAILABLE
    assert default.model is Availability.UNAVAILABLE
    assert not default.can_listen

    available = VoiceAvailability(
        engine=Availability.AVAILABLE,
        microphone=MicrophoneStatus(
            MicrophonePermission.GRANTED,
            Availability.AVAILABLE,
            "Permission supplied by a future platform boundary.",
        ),
        provider=Availability.AVAILABLE,
        model=Availability.AVAILABLE,
        reason="Future fake adapter reports availability.",
    )
    assert available.can_listen


def test_all_microphone_permission_states_are_stable_values() -> None:
    assert {item.value for item in MicrophonePermission} == {
        "unknown",
        "granted",
        "denied",
        "unavailable",
        "not_applicable",
    }


def test_transcript_roles_status_and_order_are_stable() -> None:
    roles = tuple(TranscriptRole)
    history = ConversationHistory()
    for index, role in enumerate(roles):
        history = history.append(_message(index, role))

    assert tuple(item.role for item in history.items) == roles
    assert all(item.status is TranscriptStatus.FINAL for item in history.items)


def test_conversation_history_is_bounded_in_memory() -> None:
    history = ConversationHistory(limit=3)
    for index in range(5):
        history = history.append(_message(index))

    assert tuple(item.message_id for item in history.items) == (
        "message-2",
        "message-3",
        "message-4",
    )


def test_presentation_store_owns_ephemeral_voice_updates() -> None:
    store = PresentationStore()
    observed = []
    store.subscribe(observed.append)

    store.transition_voice(VoiceLifecycle.LISTENING)
    store.append_voice_transcript(_message(1))
    proposal = ActionProposal(
        "proposal-1",
        "Inspect report",
        "Open the retained report for review.",
        ("Locate report", "Open read-only preview"),
        "No file changes are proposed.",
        affected_target="report.html",
    )
    store.set_voice_proposal(proposal)
    result = ActionResultSummary(
        ActionResultStatus.AVAILABLE,
        "Preview available",
        "A stable result is ready.",
        ResultUsability.USABLE,
    )
    store.set_voice_result(result)

    assert store.state.voice.lifecycle is VoiceLifecycle.LISTENING
    assert store.state.voice.conversation.items[-1].message_id == "message-1"
    assert store.state.voice.proposal is proposal
    assert store.state.voice.result is result
    assert len(observed) == 5


def test_store_interruption_records_intent_without_claiming_backend_cancellation() -> None:
    store = PresentationStore(
        PresentationState(
            voice=replace(
                VoicePresentationState(),
                lifecycle=VoiceLifecycle.EXECUTING,
            )
        )
    )

    assert store.request_voice_interruption()
    assert store.state.voice.lifecycle is VoiceLifecycle.IDLE
    assert store.state.voice.interruption_requested
    assert store.state.operation.is_idle
