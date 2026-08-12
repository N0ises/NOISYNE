from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtWidgets import QDialog, QLabel

from brain.ui.agent_contracts import (
    ActionClass,
    ActionExecution,
    ActionExecutionState,
    AgentPlan,
    Cancellability,
    ConfirmationDecision,
    ConfirmationOutcome,
    ConfirmationScope,
    DenialReason,
    PermissionPolicy,
    PlannedAction,
    PlanStatus,
    VerificationResult,
    VerificationState,
)
from brain.ui.presentation_state import PresentationState
from brain.ui.presentation_store import PresentationStore
from brain.ui.session_persistence import SCHEMA_VERSION, _encode_session
from brain.ui.voice_contracts import (
    ActionResultStatus,
    ActionResultSummary,
    VoiceLifecycle,
    VoicePresentationState,
)
from brain.ui.voice_page import (
    ActionProposalCard,
    AgentPlanConfirmationDialog,
    ResultSummarySurface,
    VerificationSurface,
    VoiceExecutionProgress,
    VoicePage,
)


def _action(
    action_id: str,
    action_class: ActionClass,
    target: str,
    *,
    policy: PermissionPolicy | None = None,
    cancellability: Cancellability = Cancellability.NOT_CANCELLABLE,
) -> PlannedAction:
    selected_policy = policy or PermissionPolicy()
    permission = selected_policy.decide(
        action_class,
        affected_target=target,
        risk_summary=f"Impact on {target}",
        cancellability=cancellability,
    )
    return PlannedAction(
        action_id,
        f"{action_class.value.replace('_', ' ').title()} tool call",
        action_class,
        f"Use a future {action_id} tool.",
        target,
        permission.risk_summary,
        permission,
        f"tool:{action_id}",
    )


def _plan(*actions: PlannedAction) -> AgentPlan:
    return AgentPlan(
        "plan-ui",
        "revision-ui-1",
        "Process the selected audio",
        actions,
        PlanStatus.WAITING_FOR_CONFIRMATION,
        "The following ordered tool calls are proposed.",
    )


def _labels(widget) -> list[str]:
    return [label.text() for label in widget.findChildren(QLabel)]


def test_multi_action_plan_displays_calls_classes_targets_policy_and_risk(qtbot) -> None:
    card = ActionProposalCard()
    qtbot.addWidget(card)
    plan = _plan(
        _action("inspect", ActionClass.READ_ONLY, "C:/Audio/source.wav"),
        _action("render", ActionClass.TRANSFORMATIVE, "C:/Output/render.wav"),
        _action("replace", ActionClass.DESTRUCTIVE, "C:/Audio/source.wav"),
    )

    card.render(None, plan)
    text = "\n".join(_labels(card))

    assert "Plan: Process the selected audio" in text
    assert "Tool: tool:inspect" in text
    assert "Action class: Read Only" in text
    assert "Action class: Transformative" in text
    assert "Action class: Destructive" in text
    assert "Affected target: C:/Output/render.wav" in text
    assert "Risk / impact: Impact on C:/Audio/source.wav" in text
    assert "Reason: Destructive actions always require explicit confirmation." in text
    assert card.review_button.text() == "Review destructive plan"
    assert card.review_button.isEnabled()


def test_plan_confirmation_signal_carries_exact_immutable_snapshot(qtbot) -> None:
    card = ActionProposalCard()
    qtbot.addWidget(card)
    plan = _plan(_action("inspect", ActionClass.READ_ONLY, "mix.wav"))
    card.render(None, plan)

    with qtbot.waitSignal(card.plan_confirmation_requested, timeout=1000) as signal:
        card.review_button.click()

    assert signal.args == [plan]


def test_policy_blocked_plan_is_visible_but_cannot_open_confirmation(qtbot) -> None:
    card = ActionProposalCard()
    qtbot.addWidget(card)
    plan = _plan(
        _action(
            "delete",
            ActionClass.DESTRUCTIVE,
            "source.wav",
            policy=PermissionPolicy(runtime_available=False),
        )
    )

    card.render(None, plan)

    assert plan.actions[0].permission.denial_reason is DenialReason.RUNTIME_UNAVAILABLE
    assert card.review_button.text() == "Plan blocked"
    assert not card.review_button.isEnabled()
    assert "Agent tools are unavailable" in "\n".join(_labels(card))


def test_destructive_confirmation_uses_explicit_strong_language(qtbot) -> None:
    plan = _plan(_action("delete", ActionClass.DESTRUCTIVE, "source.wav"))
    dialog = AgentPlanConfirmationDialog(plan)
    qtbot.addWidget(dialog)

    text = "\n".join(_labels(dialog))
    assert "This plan contains a destructive action" in text
    assert "Action class: Destructive" in text
    assert "Affected target: source.wav" in text
    assert dialog.confirm_button.text() == "Confirm destructive plan"
    assert dialog.confirm_button.accessibleName() == "Confirm exact destructive plan"
    assert dialog.cancel_button.accessibleName() == "Decline proposed agent plan"


@pytest.mark.parametrize(
    ("dialog_code", "expected"),
    [
        (QDialog.DialogCode.Accepted, ConfirmationOutcome.APPROVED),
        (QDialog.DialogCode.Rejected, ConfirmationOutcome.DECLINED),
    ],
)
def test_voice_page_confirmation_and_decline_emit_exact_plan_decision(
    qtbot, monkeypatch, dialog_code, expected
) -> None:
    page = VoicePage()
    qtbot.addWidget(page)
    plan = _plan(_action("render", ActionClass.TRANSFORMATIVE, "output.wav"))
    monkeypatch.setattr(AgentPlanConfirmationDialog, "exec", lambda _dialog: dialog_code)

    with qtbot.waitSignal(page.plan_confirmation_recorded, timeout=1000) as signal:
        page._confirm_plan(plan)

    decision = signal.args[0]
    assert decision.outcome is expected
    assert decision.plan_id == plan.plan_id
    assert decision.plan_revision == plan.revision
    assert decision.action_ids == ("render",)


@pytest.mark.parametrize(
    ("execution", "cancel_visible"),
    [
        (
            ActionExecution(
                "unsafe",
                ActionExecutionState.EXECUTING,
                Cancellability.NOT_CANCELLABLE,
                "Unsafe to cancel after start.",
            ),
            False,
        ),
        (
            ActionExecution(
                "safe",
                ActionExecutionState.EXECUTING,
                Cancellability.CANCELLABLE_DURING_EXECUTION,
                "Safe cancellation is supported.",
            ),
            True,
        ),
    ],
)
def test_cancel_control_only_appears_when_contract_permits(
    qtbot, execution, cancel_visible
) -> None:
    surface = VoiceExecutionProgress()
    qtbot.addWidget(surface)
    surface.show()
    surface.render_agent_execution(execution)

    assert surface.cancel_button.isVisible() is cancel_visible
    assert surface.cancel_button.isEnabled() is cancel_visible


def test_safe_cancel_button_emits_action_identity_without_execution_claim(qtbot) -> None:
    surface = VoiceExecutionProgress()
    qtbot.addWidget(surface)
    execution = ActionExecution(
        "safe-action",
        ActionExecutionState.EXECUTING,
        Cancellability.CANCELLABLE_DURING_EXECUTION,
        "Executing through a fake presentation fixture.",
    )
    surface.render_agent_execution(execution)

    with qtbot.waitSignal(surface.cancellation_requested, timeout=1000) as signal:
        surface.cancel_button.click()

    assert signal.args == ["safe-action"]
    assert execution.state is ActionExecutionState.EXECUTING


@pytest.mark.parametrize(
    ("verification_state", "expected"),
    [
        (VerificationState.NOT_STARTED, "Not Started"),
        (VerificationState.VERIFYING, "Verifying"),
        (VerificationState.VERIFIED, "Verified"),
        (VerificationState.FAILED, "Failed"),
        (VerificationState.NOT_APPLICABLE, "Not Applicable"),
    ],
)
def test_verification_surface_exposes_all_states(qtbot, verification_state, expected) -> None:
    surface = VerificationSurface()
    qtbot.addWidget(surface)
    surface.render(
        VerificationResult(
            verification_state,
            f"Verification state: {expected}",
            ("Evidence remains separate from execution status.",),
        )
    )

    assert surface.badge.text() == expected
    assert surface.summary.text() == f"Verification state: {expected}"
    assert "Evidence remains separate" in surface.evidence.text()


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        (ActionResultStatus.BLOCKED, "Blocked"),
        (ActionResultStatus.CANCELLED, "Cancelled"),
    ],
)
def test_result_summary_distinguishes_blocked_and_cancelled_outcomes(
    qtbot, status, expected
) -> None:
    surface = ResultSummarySurface()
    qtbot.addWidget(surface)
    surface.render(ActionResultSummary(status, f"Action {expected.lower()}", "Normal outcome."))

    assert surface.badge.text() == expected
    assert surface.title_label.text() == f"Action {expected.lower()}"


def test_voice_page_integrates_plan_execution_verification_and_result_independently(
    qtbot,
) -> None:
    page = VoicePage()
    qtbot.addWidget(page)
    plan = _plan(_action("render", ActionClass.TRANSFORMATIVE, "output.wav"))
    execution = ActionExecution(
        "render",
        ActionExecutionState.COMPLETED,
        Cancellability.NOT_CANCELLABLE,
        "Execution completed.",
    )
    verification = VerificationResult(
        VerificationState.FAILED,
        "Execution completed, but output verification failed.",
    )
    state = PresentationState(
        voice=VoicePresentationState(
            lifecycle=VoiceLifecycle.VERIFYING,
            agent_plan=plan,
            executions=(execution,),
            verification=verification,
        )
    )

    page.render(state)

    assert page.execution.badge.text() == "Completed"
    assert page.verification.badge.text() == "Failed"
    assert "verification failed" in page.verification.summary.text()


def test_store_rejects_stale_confirmation_and_accepts_exact_snapshot() -> None:
    plan = _plan(_action("inspect", ActionClass.READ_ONLY, "mix.wav"))
    store = PresentationStore()
    store.set_agent_plan(plan)
    stale = ConfirmationDecision.for_plan(
        replace_plan_revision(plan, "old-revision"),
        ConfirmationOutcome.APPROVED,
    )
    exact = ConfirmationDecision.for_plan(plan, ConfirmationOutcome.APPROVED)

    assert not store.record_agent_confirmation(stale)
    assert store.state.voice.confirmation is None
    assert store.record_agent_confirmation(exact)
    assert store.state.voice.confirmation is exact


def test_store_rejects_forged_approval_for_blocked_plan() -> None:
    plan = _plan(
        _action(
            "delete",
            ActionClass.DESTRUCTIVE,
            "source.wav",
            policy=PermissionPolicy(runtime_available=False),
        )
    )
    store = PresentationStore()
    store.set_agent_plan(plan)
    forged = ConfirmationDecision(
        plan.plan_id,
        plan.revision,
        ConfirmationScope.PLAN,
        ("delete",),
        ConfirmationOutcome.APPROVED,
    )

    assert not store.record_agent_confirmation(forged)
    assert store.state.voice.confirmation is None


def replace_plan_revision(plan: AgentPlan, revision: str) -> AgentPlan:
    return AgentPlan(
        plan.plan_id,
        revision,
        plan.intent_summary,
        plan.actions,
        plan.status,
        plan.rationale,
    )


def test_user_decline_is_recorded_as_normal_non_error_decision() -> None:
    plan = _plan(_action("render", ActionClass.TRANSFORMATIVE, "output.wav"))
    store = PresentationStore()
    store.set_agent_plan(plan)
    declined = ConfirmationDecision.for_plan(plan, ConfirmationOutcome.DECLINED)

    assert store.record_agent_confirmation(declined)
    assert store.state.voice.confirmation.outcome is ConfirmationOutcome.DECLINED
    assert store.state.notifications.active == ()


def test_agent_permission_state_is_not_persisted_and_schema_remains_v2() -> None:
    plan = _plan(_action("delete", ActionClass.DESTRUCTIVE, "source.wav"))
    decision = ConfirmationDecision.for_plan(plan, ConfirmationOutcome.APPROVED)
    state = PresentationState(voice=VoicePresentationState(agent_plan=plan, confirmation=decision))

    payload = _encode_session(state.session)

    assert payload["schema_version"] == SCHEMA_VERSION == 2
    serialized = repr(payload)
    assert "plan-ui" not in serialized
    assert "revision-ui-1" not in serialized
    assert "source.wav" not in serialized
    assert "confirmation" not in serialized


def test_production_agent_modules_have_no_executor_or_mutation_boundary() -> None:
    repository = Path(__file__).resolve().parents[2]
    sources = {
        relative: (repository / relative).read_text(encoding="utf-8")
        for relative in (
            "brain/ui/agent_contracts.py",
            "brain/ui/voice_contracts.py",
            "brain/ui/voice_page.py",
        )
    }
    combined = "\n".join(sources.values())

    for forbidden in (
        "subprocess",
        "os.remove",
        "unlink(",
        "write_bytes",
        "write_text",
        "brain.audio",
        "brain.rag",
        "brain.v2",
        "v2-development",
    ):
        assert forbidden not in combined
    assert "execute_tool" not in combined
    assert "auto_confirm" not in combined


def test_agent_permission_ui_has_no_page_local_brand_colors() -> None:
    repository = Path(__file__).resolve().parents[2]
    source = (repository / "brain/ui/voice_page.py").read_text(encoding="utf-8")

    assert "#6366F1" not in source
    assert "linear-gradient" not in source
