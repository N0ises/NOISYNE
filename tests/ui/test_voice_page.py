from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

import pytest
from PySide6.QtCore import Qt

from brain.ui.contracts import (
    Availability,
    OperationState,
    ResultUsability,
    UiError,
    UiErrorCategory,
)
from brain.ui.design_system.semantics import VisualState
from brain.ui.pages import PageHost
from brain.ui.presentation_state import (
    OperationPresentationState,
    PageId,
    PresentationState,
)
from brain.ui.session_persistence import SCHEMA_VERSION, _encode_session
from brain.ui.voice_contracts import (
    ActionProposal,
    ActionResultStatus,
    ActionResultSummary,
    ConversationHistory,
    MicrophonePermission,
    MicrophoneStatus,
    TranscriptItem,
    TranscriptRole,
    VoiceAvailability,
    VoiceLifecycle,
    VoicePresentationState,
)
from brain.ui.voice_page import (
    ActionConfirmationDialog,
    ActionProposalCard,
    ResultSummarySurface,
    TranscriptSurface,
    VoiceExecutionProgress,
    VoiceInputControl,
    VoicePage,
)


def _available() -> VoiceAvailability:
    return VoiceAvailability(
        engine=Availability.AVAILABLE,
        microphone=MicrophoneStatus(
            MicrophonePermission.GRANTED,
            Availability.AVAILABLE,
            "Granted by fake test boundary.",
        ),
        provider=Availability.AVAILABLE,
        model=Availability.AVAILABLE,
        reason="Available through fake presentation data.",
    )


def _proposal() -> ActionProposal:
    return ActionProposal(
        "proposal-1",
        "Open analysis report",
        "Review the retained deterministic analysis report.",
        ("Locate the report", "Open a read-only preview"),
        "No audio or report files will be changed.",
        affected_target="C:/reports/analysis.html",
    )


def _item(message_id: str, role: TranscriptRole, text: str) -> TranscriptItem:
    return TranscriptItem(
        message_id,
        role,
        text,
        datetime(2026, 1, 1, tzinfo=UTC),
    )


def test_voice_page_is_a_stable_navigation_destination(qtbot) -> None:
    host = PageHost()
    qtbot.addWidget(host)

    page = host.page(PageId.VOICE)
    host.show_page(PageId.VOICE)

    assert isinstance(page, VoicePage)
    assert host.current_page_id is PageId.VOICE
    assert page.accessibleName() == "Voice and agent workspace"


def test_unavailable_engine_is_truthful_and_disables_voice_input(qtbot) -> None:
    page = VoicePage()
    qtbot.addWidget(page)
    page.render(PresentationState())

    assert page.availability.ui_badge.text() == "UI available"
    assert page.availability.engine_badge.text() == "Engine unavailable"
    assert page.availability.permission_badge.text() == "Permission unknown"
    assert page.availability.provider_badge.text() == "Provider unavailable"
    assert page.availability.model_badge.text() == "Model unavailable"
    assert page.agent_status.badge.text() == "Unavailable"
    assert not page.input_control.action_button.isEnabled()
    assert page.input_control.action_button.text() == "Voice unavailable"
    assert "not available" in page.input_control.state_label.text()


@pytest.mark.parametrize(
    ("lifecycle", "label", "processing"),
    [
        (VoiceLifecycle.IDLE, "Idle", False),
        (VoiceLifecycle.LISTENING, "Listening", False),
        (VoiceLifecycle.TRANSCRIBING, "Transcribing", True),
        (VoiceLifecycle.UNDERSTANDING, "Understanding", True),
        (VoiceLifecycle.PLANNING, "Planning", True),
        (
            VoiceLifecycle.WAITING_FOR_CONFIRMATION,
            "Waiting for confirmation",
            False,
        ),
        (VoiceLifecycle.EXECUTING, "Executing", True),
        (VoiceLifecycle.VERIFYING, "Verifying", True),
        (VoiceLifecycle.RESPONDING, "Response ready", False),
    ],
)
def test_all_voice_lifecycle_states_render_explicit_text(
    qtbot, lifecycle, label, processing
) -> None:
    control = VoiceInputControl()
    qtbot.addWidget(control)
    state = VoicePresentationState(lifecycle=lifecycle, availability=_available())

    control.render(state)

    assert control.state_badge.text() == label
    assert bool(control.processing.isHidden()) is not processing
    assert control.state_label.text()


def test_listening_state_is_static_and_does_not_fabricate_waveform(qtbot) -> None:
    control = VoiceInputControl()
    qtbot.addWidget(control)
    control.render(
        VoicePresentationState(
            lifecycle=VoiceLifecycle.LISTENING,
            availability=_available(),
        )
    )

    assert control.action_button.text() == "Stop listening"
    assert "No audio level is fabricated" in control.state_label.text()
    assert control.findChildren(type(control.processing)) == [control.processing]


def test_interruption_control_emits_intent_without_backend_claim(qtbot) -> None:
    control = VoiceInputControl()
    qtbot.addWidget(control)
    control.render(
        VoicePresentationState(
            lifecycle=VoiceLifecycle.PLANNING,
            availability=_available(),
        )
    )

    with qtbot.waitSignal(control.interruption_requested, timeout=1000):
        control.action_button.click()

    assert control.state_badge.text() == "Planning"
    assert control.action_button.text() == "Interrupt"


def test_transcript_surface_renders_roles_in_contract_order(qtbot) -> None:
    surface = TranscriptSurface()
    qtbot.addWidget(surface)
    items = (
        _item("user-1", TranscriptRole.USER, "Analyze the selected audio."),
        _item("agent-1", TranscriptRole.AGENT, "Proposed a deterministic analysis."),
        _item("assistant-1", TranscriptRole.ASSISTANT, "Result is available."),
    )

    surface.render(items)

    assert surface.empty_label.isHidden()
    assert [widget.objectName() for widget in surface._message_widgets] == [
        "transcript-user-1",
        "transcript-agent-1",
        "transcript-assistant-1",
    ]
    assert [widget.accessibleName() for widget in surface._message_widgets] == [
        "user transcript message",
        "agent transcript message",
        "assistant transcript message",
    ]


def test_action_proposal_card_renders_target_impact_and_confirmation_intent(qtbot) -> None:
    card = ActionProposalCard()
    qtbot.addWidget(card)
    proposal = _proposal()
    card.render(proposal)

    with qtbot.waitSignal(card.confirmation_requested, timeout=1000) as signal:
        card.review_button.click()

    assert signal.args == [proposal.proposal_id]
    assert proposal.affected_target in card.target_label.text()
    assert proposal.impact_summary in card.impact_label.text()
    assert not card.isHidden()


def test_confirmation_dialog_exposes_keyboard_operable_confirm_and_cancel(qtbot) -> None:
    confirm = ActionConfirmationDialog(_proposal())
    qtbot.addWidget(confirm)
    with qtbot.waitSignal(confirm.accepted, timeout=1000):
        qtbot.mouseClick(confirm.confirm_button, Qt.MouseButton.LeftButton)

    cancel = ActionConfirmationDialog(_proposal())
    qtbot.addWidget(cancel)
    with qtbot.waitSignal(cancel.rejected, timeout=1000):
        qtbot.mouseClick(cancel.cancel_button, Qt.MouseButton.LeftButton)

    assert confirm.accessibleName() == "Confirm proposed voice agent action"
    assert confirm.confirm_button.text() == "Confirm action"
    assert cancel.cancel_button.text() == "Cancel"


def test_execution_progress_reuses_operation_presentation_semantics(qtbot) -> None:
    surface = VoiceExecutionProgress()
    qtbot.addWidget(surface)
    operation = OperationPresentationState(
        operation_id="operation-1",
        kind="future agent action",
        state=OperationState.RUNNING,
        message="Executing confirmed action",
    )

    surface.render(operation)

    assert surface.badge.text() == "Running"
    assert surface.badge.visual_state is VisualState.RUNNING
    assert surface.progress.minimum() == 0
    assert surface.progress.maximum() == 0
    assert surface.message.text() == "Executing confirmed action"


@pytest.mark.parametrize(
    ("status", "visual"),
    [
        (ActionResultStatus.COMPLETED, VisualState.SUCCESS),
        (ActionResultStatus.AVAILABLE, VisualState.READY),
        (ActionResultStatus.PARTIALLY_AVAILABLE, VisualState.WARNING),
        (ActionResultStatus.FAILED, VisualState.ERROR),
    ],
)
def test_result_summary_renders_stable_status_and_usability(qtbot, status, visual) -> None:
    surface = ResultSummarySurface()
    qtbot.addWidget(surface)
    error = (
        UiError(
            "voice_action_failed",
            UiErrorCategory.INTERNAL,
            "The proposed action could not be completed.",
            result_usability=ResultUsability.NOT_USABLE,
        )
        if status is ActionResultStatus.FAILED
        else None
    )
    result = ActionResultSummary(
        status,
        "Action result",
        "Stable result detail.",
        ResultUsability.NOT_USABLE if error else ResultUsability.USABLE,
        error,
    )

    surface.render(result)

    assert surface.badge.visual_state is visual
    assert surface.title_label.text() == "Action result"
    assert surface.detail_label.text()


def test_voice_state_is_not_serialized_and_session_schema_is_unchanged() -> None:
    history = ConversationHistory().append(
        _item("private-voice-message", TranscriptRole.USER, "Do not persist me.")
    )
    state = PresentationState(voice=replace(VoicePresentationState(), conversation=history))

    payload = _encode_session(state.session)

    assert payload["schema_version"] == SCHEMA_VERSION == 2
    assert "voice" not in payload
    assert "transcript" not in payload
    assert "private-voice-message" not in repr(payload)


def test_voice_modules_have_no_backend_voice_v2_or_provider_imports() -> None:
    repository = Path(__file__).resolve().parents[2]
    sources = "\n".join(
        (repository / relative).read_text(encoding="utf-8")
        for relative in (
            "brain/ui/voice_contracts.py",
            "brain/ui/voice_page.py",
        )
    )

    for forbidden in (
        "brain.audio",
        "brain.rag",
        "v2-development",
        "brain.v2",
        "speech_recognition",
        "pyaudio",
        "transformers",
        "torch",
    ):
        assert forbidden not in sources


def test_voice_page_uses_intelligence_semantic_without_raw_brand_colors() -> None:
    repository = Path(__file__).resolve().parents[2]
    source = (repository / "brain/ui/voice_page.py").read_text(encoding="utf-8")

    assert 'setProperty("semantic", "intelligence")' in source
    assert "#6366F1" not in source
    assert "linear-gradient" not in source
