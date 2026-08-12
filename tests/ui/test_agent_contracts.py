from __future__ import annotations

from dataclasses import FrozenInstanceError, replace

import pytest

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
    PermissionDecision,
    PermissionDisposition,
    PermissionPolicy,
    PlannedAction,
    VerificationResult,
    VerificationState,
)


def _action(
    action_id: str = "action-1",
    action_class: ActionClass = ActionClass.READ_ONLY,
    *,
    policy: PermissionPolicy | None = None,
    available: bool = True,
    target: str = "mix.wav",
    cancellability: Cancellability = Cancellability.NOT_CANCELLABLE,
) -> PlannedAction:
    selected_policy = policy or PermissionPolicy()
    decision = selected_policy.decide(
        action_class,
        affected_target=target,
        risk_summary="Reads or changes the explicitly displayed target.",
        cancellability=cancellability,
        available=available,
    )
    return PlannedAction(
        action_id,
        f"Action {action_id}",
        action_class,
        "A stable proposed action.",
        target,
        decision.risk_summary,
        decision,
        "future_tool",
    )


def _plan(*actions: PlannedAction, revision: str = "revision-1") -> AgentPlan:
    return AgentPlan(
        "plan-1",
        revision,
        "Inspect or process selected audio",
        actions or (_action(),),
        rationale="Ordered actions proposed by a future adapter.",
    )


def test_action_classes_are_stable_and_explicit() -> None:
    assert tuple(ActionClass) == (
        ActionClass.READ_ONLY,
        ActionClass.TRANSFORMATIVE,
        ActionClass.DESTRUCTIVE,
    )


def test_read_only_policy_can_explicitly_permit_without_confirmation() -> None:
    decision = PermissionPolicy(allow_read_only_without_confirmation=True).decide(
        ActionClass.READ_ONLY,
        affected_target="mix.wav",
        risk_summary="Reads the source without modifying it.",
    )

    assert decision.disposition is PermissionDisposition.ALLOWED_WITHOUT_CONFIRMATION
    assert decision.execution_permitted
    assert not decision.confirmation_required
    assert "explicitly permitted" in decision.reason


def test_read_only_policy_can_still_require_confirmation() -> None:
    decision = PermissionPolicy().decide(
        ActionClass.READ_ONLY,
        affected_target="private-project",
        risk_summary="Inspects private project metadata.",
    )

    assert decision.disposition is PermissionDisposition.REQUIRES_CONFIRMATION
    assert decision.confirmation_required
    assert not decision.execution_permitted


def test_transformative_defaults_to_confirmation_required() -> None:
    decision = PermissionPolicy(allow_read_only_without_confirmation=True).decide(
        ActionClass.TRANSFORMATIVE,
        affected_target="render.wav",
        risk_summary="Creates an output file.",
    )

    assert decision.confirmation_required
    assert not decision.execution_permitted
    assert "creates or modifies" in decision.reason


def test_destructive_always_requires_confirmation_even_with_read_only_trust() -> None:
    decision = PermissionPolicy(allow_read_only_without_confirmation=True).decide(
        ActionClass.DESTRUCTIVE,
        affected_target="source.wav",
        risk_summary="Overwrites the source audio.",
    )

    assert decision.confirmation_required
    assert not decision.execution_permitted
    assert "always require" in decision.reason


def test_destructive_cannot_be_constructed_as_auto_approved() -> None:
    with pytest.raises(ValueError, match="always require"):
        PermissionDecision(
            ActionClass.DESTRUCTIVE,
            PermissionDisposition.ALLOWED_WITHOUT_CONFIRMATION,
            True,
            "Unsafe override",
            Cancellability.NOT_CANCELLABLE,
            "source.wav",
            "Overwrites source.",
        )


@pytest.mark.parametrize(
    ("policy", "available", "reason"),
    [
        (PermissionPolicy(runtime_available=False), True, DenialReason.RUNTIME_UNAVAILABLE),
        (PermissionPolicy(), False, DenialReason.CAPABILITY_UNAVAILABLE),
    ],
)
def test_runtime_and_capability_denial_are_typed(policy, available, reason) -> None:
    decision = policy.decide(
        ActionClass.READ_ONLY,
        affected_target="mix.wav",
        risk_summary="Read-only inspection.",
        available=available,
    )

    assert decision.disposition is PermissionDisposition.BLOCKED
    assert not decision.execution_permitted
    assert decision.denial_reason is reason


def test_blocked_permission_cannot_claim_execution_is_permitted() -> None:
    with pytest.raises(ValueError, match="blocked action"):
        PermissionDecision(
            ActionClass.READ_ONLY,
            PermissionDisposition.BLOCKED,
            True,
            "Blocked",
            Cancellability.NOT_CANCELLABLE,
            "mix.wav",
            "Read only.",
            DenialReason.POLICY_BLOCKED,
        )


@pytest.mark.parametrize(
    ("denial_reason", "expected"),
    [
        (DenialReason.POLICY_BLOCKED, "policy blocks"),
        (DenialReason.TARGET_UNAVAILABLE, "target is unavailable"),
    ],
)
def test_policy_and_target_denials_are_typed_non_exceptional_outcomes(
    denial_reason, expected
) -> None:
    decision = PermissionPolicy().decide(
        ActionClass.TRANSFORMATIVE,
        affected_target="output.wav",
        risk_summary="Would create an output.",
        denial_reason=denial_reason,
    )

    assert decision.disposition is PermissionDisposition.BLOCKED
    assert decision.denial_reason is denial_reason
    assert expected in decision.reason


def test_planned_action_permission_must_match_class_and_target() -> None:
    permission = PermissionPolicy().decide(
        ActionClass.READ_ONLY,
        affected_target="one.wav",
        risk_summary="Read only.",
    )
    with pytest.raises(ValueError, match="same affected target"):
        PlannedAction(
            "action-1",
            "Inspect",
            ActionClass.READ_ONLY,
            "Inspect audio.",
            "two.wav",
            "Read only.",
            permission,
            "inspect_audio",
        )


def test_multi_action_plan_preserves_order_and_confirmation_truth() -> None:
    actions = (
        _action("read", ActionClass.READ_ONLY),
        _action("render", ActionClass.TRANSFORMATIVE, target="output.wav"),
        _action("delete", ActionClass.DESTRUCTIVE, target="source.wav"),
    )
    plan = _plan(*actions)

    assert tuple(item.action_id for item in plan.actions) == ("read", "render", "delete")
    assert plan.confirmation_pending
    assert plan.confirmable_action_ids == ("read", "render", "delete")
    assert not plan.blocked


def test_blocked_plan_cannot_be_confirmed_into_execution() -> None:
    plan = _plan(
        _action(
            "blocked",
            ActionClass.DESTRUCTIVE,
            policy=PermissionPolicy(runtime_available=False),
            target="source.wav",
        )
    )

    assert plan.blocked
    assert plan.confirmable_action_ids == ()
    with pytest.raises(ValueError, match="blocked plan"):
        ConfirmationDecision.for_plan(plan, ConfirmationOutcome.APPROVED)


def test_confirmation_references_exact_plan_revision_and_actions() -> None:
    plan = _plan(
        _action("inspect"),
        _action("render", ActionClass.TRANSFORMATIVE, target="output.wav"),
    )
    decision = ConfirmationDecision.for_plan(plan, ConfirmationOutcome.APPROVED)

    assert decision.scope is ConfirmationScope.PLAN
    assert decision.plan_id == plan.plan_id
    assert decision.plan_revision == plan.revision
    assert decision.action_ids == ("inspect", "render")
    assert decision.authorizes(plan, "render")
    assert not decision.authorizes(replace(plan, revision="revision-2"), "render")


def test_action_level_confirmation_authorizes_only_selected_action() -> None:
    plan = _plan(_action("inspect"), _action("compare"))
    decision = ConfirmationDecision.for_action(plan, "inspect", ConfirmationOutcome.APPROVED)

    assert decision.scope is ConfirmationScope.ACTION
    assert decision.authorizes(plan, "inspect")
    assert not decision.authorizes(plan, "compare")


def test_confirmation_cancellation_is_normal_declined_outcome() -> None:
    plan = _plan()
    decision = ConfirmationDecision.for_plan(plan, ConfirmationOutcome.DECLINED)

    assert decision.outcome is ConfirmationOutcome.DECLINED
    assert not decision.authorizes(plan, "action-1")


def test_confirmed_snapshot_is_immutable_and_does_not_authorize_mutation() -> None:
    plan = _plan()
    decision = ConfirmationDecision.for_plan(plan, ConfirmationOutcome.APPROVED)

    with pytest.raises(FrozenInstanceError):
        plan.revision = "changed"
    mutated = replace(plan, revision="changed")
    assert not decision.authorizes(mutated, "action-1")


def test_execution_lifecycle_rejects_invalid_transition() -> None:
    execution = ActionExecution("action-1")
    with pytest.raises(ValueError, match="proposed -> completed"):
        execution.transition(ActionExecutionState.COMPLETED)


def test_execution_lifecycle_includes_blocked_cancelled_and_failure_outcomes() -> None:
    assert tuple(ActionExecutionState) == (
        ActionExecutionState.PROPOSED,
        ActionExecutionState.WAITING_FOR_CONFIRMATION,
        ActionExecutionState.APPROVED,
        ActionExecutionState.QUEUED,
        ActionExecutionState.EXECUTING,
        ActionExecutionState.CANCELLING,
        ActionExecutionState.CANCELLED,
        ActionExecutionState.VERIFYING,
        ActionExecutionState.COMPLETED,
        ActionExecutionState.FAILED,
        ActionExecutionState.BLOCKED,
    )


def test_execution_lifecycle_supports_proposal_through_verification() -> None:
    execution = ActionExecution("action-1")
    for state in (
        ActionExecutionState.WAITING_FOR_CONFIRMATION,
        ActionExecutionState.APPROVED,
        ActionExecutionState.QUEUED,
        ActionExecutionState.EXECUTING,
        ActionExecutionState.VERIFYING,
        ActionExecutionState.COMPLETED,
    ):
        execution = execution.transition(state)

    assert execution.state is ActionExecutionState.COMPLETED


@pytest.mark.parametrize(
    ("cancellability", "state", "expected"),
    [
        (Cancellability.NOT_CANCELLABLE, ActionExecutionState.QUEUED, False),
        (Cancellability.CANCELLABLE_BEFORE_START, ActionExecutionState.QUEUED, True),
        (Cancellability.CANCELLABLE_BEFORE_START, ActionExecutionState.EXECUTING, False),
        (Cancellability.CANCELLABLE_DURING_EXECUTION, ActionExecutionState.EXECUTING, True),
    ],
)
def test_cancellability_is_explicit_and_state_sensitive(cancellability, state, expected) -> None:
    execution = ActionExecution("action-1", state, cancellability)
    assert execution.can_cancel is expected


def test_safe_cancellation_before_start_is_terminal_without_backend_claim() -> None:
    execution = ActionExecution(
        "action-1",
        ActionExecutionState.QUEUED,
        Cancellability.CANCELLABLE_BEFORE_START,
    )
    cancelled = execution.request_cancellation()

    assert cancelled.state is ActionExecutionState.CANCELLED
    assert "before execution" in cancelled.message


def test_during_execution_cancellation_only_records_request() -> None:
    execution = ActionExecution(
        "action-1",
        ActionExecutionState.EXECUTING,
        Cancellability.CANCELLABLE_DURING_EXECUTION,
    )
    cancelling = execution.request_cancellation()

    assert cancelling.state is ActionExecutionState.CANCELLING
    assert "awaiting" in cancelling.message


def test_verification_is_distinct_from_execution_success() -> None:
    execution = ActionExecution(
        "action-1",
        ActionExecutionState.COMPLETED,
    )
    verification = VerificationResult(
        VerificationState.FAILED,
        "Output exists, but validation did not pass.",
        ("Checksum did not match expected output.",),
    )

    assert execution.state is ActionExecutionState.COMPLETED
    assert verification.state is VerificationState.FAILED


def test_verification_lifecycle_values_are_stable() -> None:
    assert tuple(VerificationState) == (
        VerificationState.NOT_STARTED,
        VerificationState.VERIFYING,
        VerificationState.VERIFIED,
        VerificationState.FAILED,
        VerificationState.NOT_APPLICABLE,
    )
