"""Qt-free permission and safety contracts for future agent/tool adapters."""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum

from .contracts import UiError


class ActionClass(str, Enum):
    READ_ONLY = "read_only"
    TRANSFORMATIVE = "transformative"
    DESTRUCTIVE = "destructive"


class PermissionDisposition(str, Enum):
    ALLOWED_WITHOUT_CONFIRMATION = "allowed_without_confirmation"
    REQUIRES_CONFIRMATION = "requires_confirmation"
    BLOCKED = "blocked"


class Cancellability(str, Enum):
    NOT_CANCELLABLE = "not_cancellable"
    CANCELLABLE_BEFORE_START = "cancellable_before_start"
    CANCELLABLE_DURING_EXECUTION = "cancellable_during_execution"


class PlanStatus(str, Enum):
    PROPOSED = "proposed"
    WAITING_FOR_CONFIRMATION = "waiting_for_confirmation"
    APPROVED = "approved"
    DECLINED = "declined"
    BLOCKED = "blocked"
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"


class ConfirmationScope(str, Enum):
    ACTION = "action"
    PLAN = "plan"


class ConfirmationOutcome(str, Enum):
    APPROVED = "approved"
    DECLINED = "declined"


class ActionExecutionState(str, Enum):
    PROPOSED = "proposed"
    WAITING_FOR_CONFIRMATION = "waiting_for_confirmation"
    APPROVED = "approved"
    QUEUED = "queued"
    EXECUTING = "executing"
    CANCELLING = "cancelling"
    CANCELLED = "cancelled"
    VERIFYING = "verifying"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"


class VerificationState(str, Enum):
    NOT_STARTED = "not_started"
    VERIFYING = "verifying"
    VERIFIED = "verified"
    FAILED = "failed"
    NOT_APPLICABLE = "not_applicable"


class DenialReason(str, Enum):
    USER_DECLINED = "user_declined"
    POLICY_BLOCKED = "policy_blocked"
    CAPABILITY_UNAVAILABLE = "capability_unavailable"
    TARGET_UNAVAILABLE = "target_unavailable"
    RUNTIME_UNAVAILABLE = "runtime_unavailable"


@dataclass(frozen=True, slots=True)
class PermissionDecision:
    action_class: ActionClass
    disposition: PermissionDisposition
    execution_permitted: bool
    reason: str
    cancellability: Cancellability
    affected_target: str | None
    risk_summary: str
    denial_reason: DenialReason | None = None

    def __post_init__(self) -> None:
        if (
            self.action_class is ActionClass.DESTRUCTIVE
            and self.disposition is PermissionDisposition.ALLOWED_WITHOUT_CONFIRMATION
        ):
            raise ValueError("Destructive actions always require explicit confirmation.")
        if self.disposition is PermissionDisposition.BLOCKED and self.execution_permitted:
            raise ValueError("A blocked action cannot be executable.")
        if (
            self.disposition is PermissionDisposition.REQUIRES_CONFIRMATION
            and self.execution_permitted
        ):
            raise ValueError("Execution is not permitted until confirmation is recorded.")
        if self.disposition is PermissionDisposition.BLOCKED and self.denial_reason is None:
            raise ValueError("A blocked action requires a typed denial reason.")

    @property
    def confirmation_required(self) -> bool:
        return self.disposition is PermissionDisposition.REQUIRES_CONFIRMATION


@dataclass(frozen=True, slots=True)
class PermissionPolicy:
    allow_read_only_without_confirmation: bool = False
    runtime_available: bool = True

    def decide(
        self,
        action_class: ActionClass,
        *,
        affected_target: str | None,
        risk_summary: str,
        cancellability: Cancellability = Cancellability.NOT_CANCELLABLE,
        available: bool = True,
        denial_reason: DenialReason | None = None,
    ) -> PermissionDecision:
        if denial_reason is not None:
            reason = {
                DenialReason.USER_DECLINED: "The user declined this proposed action.",
                DenialReason.POLICY_BLOCKED: "Current policy blocks this action.",
                DenialReason.CAPABILITY_UNAVAILABLE: "The required capability is unavailable.",
                DenialReason.TARGET_UNAVAILABLE: "The affected target is unavailable.",
                DenialReason.RUNTIME_UNAVAILABLE: (
                    "Agent tools are unavailable in the current runtime."
                ),
            }[denial_reason]
            return PermissionDecision(
                action_class,
                PermissionDisposition.BLOCKED,
                False,
                reason,
                cancellability,
                affected_target,
                risk_summary,
                denial_reason,
            )
        if not self.runtime_available:
            return PermissionDecision(
                action_class,
                PermissionDisposition.BLOCKED,
                False,
                "Agent tools are unavailable in the current runtime.",
                cancellability,
                affected_target,
                risk_summary,
                DenialReason.RUNTIME_UNAVAILABLE,
            )
        if not available:
            return PermissionDecision(
                action_class,
                PermissionDisposition.BLOCKED,
                False,
                "The required capability is unavailable.",
                cancellability,
                affected_target,
                risk_summary,
                DenialReason.CAPABILITY_UNAVAILABLE,
            )
        if action_class is ActionClass.READ_ONLY and self.allow_read_only_without_confirmation:
            return PermissionDecision(
                action_class,
                PermissionDisposition.ALLOWED_WITHOUT_CONFIRMATION,
                True,
                "Read-only inspection is explicitly permitted by policy.",
                cancellability,
                affected_target,
                risk_summary,
            )
        reason = {
            ActionClass.READ_ONLY: "Read-only execution requires confirmation under current policy.",
            ActionClass.TRANSFORMATIVE: "This action creates or modifies an output.",
            ActionClass.DESTRUCTIVE: "Destructive actions always require explicit confirmation.",
        }[action_class]
        return PermissionDecision(
            action_class,
            PermissionDisposition.REQUIRES_CONFIRMATION,
            False,
            reason,
            cancellability,
            affected_target,
            risk_summary,
        )


@dataclass(frozen=True, slots=True)
class PlannedAction:
    action_id: str
    title: str
    action_class: ActionClass
    summary: str
    affected_target: str | None
    risk_summary: str
    permission: PermissionDecision
    tool_label: str

    def __post_init__(self) -> None:
        if self.permission.action_class is not self.action_class:
            raise ValueError("Permission decision must describe the planned action class.")
        if self.permission.affected_target != self.affected_target:
            raise ValueError("Permission decision must describe the same affected target.")


@dataclass(frozen=True, slots=True)
class AgentPlan:
    plan_id: str
    revision: str
    intent_summary: str
    actions: tuple[PlannedAction, ...]
    status: PlanStatus = PlanStatus.PROPOSED
    rationale: str | None = None

    def __post_init__(self) -> None:
        if not self.actions:
            raise ValueError("An agent plan must contain at least one proposed action.")
        action_ids = tuple(action.action_id for action in self.actions)
        if len(set(action_ids)) != len(action_ids):
            raise ValueError("Planned action identifiers must be unique within a plan.")

    @property
    def confirmation_pending(self) -> bool:
        return any(action.permission.confirmation_required for action in self.actions)

    @property
    def blocked(self) -> bool:
        return any(
            action.permission.disposition is PermissionDisposition.BLOCKED
            for action in self.actions
        )

    @property
    def confirmable_action_ids(self) -> tuple[str, ...]:
        if self.blocked:
            return ()
        return tuple(
            action.action_id for action in self.actions if action.permission.confirmation_required
        )


@dataclass(frozen=True, slots=True)
class ConfirmationDecision:
    plan_id: str
    plan_revision: str
    scope: ConfirmationScope
    action_ids: tuple[str, ...]
    outcome: ConfirmationOutcome

    def __post_init__(self) -> None:
        if not self.action_ids:
            raise ValueError("A confirmation must reference at least one exact action.")
        if len(set(self.action_ids)) != len(self.action_ids):
            raise ValueError("A confirmation cannot contain duplicate action identifiers.")
        if self.scope is ConfirmationScope.ACTION and len(self.action_ids) != 1:
            raise ValueError("Action-level confirmation must reference exactly one action.")

    @classmethod
    def for_plan(cls, plan: AgentPlan, outcome: ConfirmationOutcome) -> ConfirmationDecision:
        if plan.blocked and outcome is ConfirmationOutcome.APPROVED:
            raise ValueError("A blocked plan cannot be approved.")
        return cls(
            plan.plan_id,
            plan.revision,
            ConfirmationScope.PLAN,
            tuple(action.action_id for action in plan.actions),
            outcome,
        )

    @classmethod
    def for_action(
        cls,
        plan: AgentPlan,
        action_id: str,
        outcome: ConfirmationOutcome,
    ) -> ConfirmationDecision:
        action = next(
            (item for item in plan.actions if item.action_id == action_id),
            None,
        )
        if action is None:
            raise ValueError("Confirmation references an action outside the plan.")
        if (
            action.permission.disposition is PermissionDisposition.BLOCKED
            and outcome is ConfirmationOutcome.APPROVED
        ):
            raise ValueError("A blocked action cannot be approved.")
        return cls(
            plan.plan_id,
            plan.revision,
            ConfirmationScope.ACTION,
            (action_id,),
            outcome,
        )

    def authorizes(self, plan: AgentPlan, action_id: str) -> bool:
        return (
            self.outcome is ConfirmationOutcome.APPROVED
            and self.plan_id == plan.plan_id
            and self.plan_revision == plan.revision
            and action_id in self.action_ids
            and any(action.action_id == action_id for action in plan.actions)
        )


_EXECUTION_TRANSITIONS = {
    ActionExecutionState.PROPOSED: frozenset(
        {
            ActionExecutionState.WAITING_FOR_CONFIRMATION,
            ActionExecutionState.APPROVED,
            ActionExecutionState.BLOCKED,
            ActionExecutionState.CANCELLED,
        }
    ),
    ActionExecutionState.WAITING_FOR_CONFIRMATION: frozenset(
        {
            ActionExecutionState.APPROVED,
            ActionExecutionState.BLOCKED,
            ActionExecutionState.CANCELLED,
        }
    ),
    ActionExecutionState.APPROVED: frozenset(
        {ActionExecutionState.QUEUED, ActionExecutionState.CANCELLED}
    ),
    ActionExecutionState.QUEUED: frozenset(
        {
            ActionExecutionState.EXECUTING,
            ActionExecutionState.CANCELLED,
            ActionExecutionState.FAILED,
        }
    ),
    ActionExecutionState.EXECUTING: frozenset(
        {
            ActionExecutionState.CANCELLING,
            ActionExecutionState.VERIFYING,
            ActionExecutionState.COMPLETED,
            ActionExecutionState.FAILED,
        }
    ),
    ActionExecutionState.CANCELLING: frozenset(
        {ActionExecutionState.CANCELLED, ActionExecutionState.FAILED}
    ),
    ActionExecutionState.VERIFYING: frozenset(
        {ActionExecutionState.COMPLETED, ActionExecutionState.FAILED}
    ),
    ActionExecutionState.CANCELLED: frozenset(),
    ActionExecutionState.COMPLETED: frozenset(),
    ActionExecutionState.FAILED: frozenset(),
    ActionExecutionState.BLOCKED: frozenset(),
}


@dataclass(frozen=True, slots=True)
class ActionExecution:
    action_id: str
    state: ActionExecutionState = ActionExecutionState.PROPOSED
    cancellability: Cancellability = Cancellability.NOT_CANCELLABLE
    message: str = "Proposed action has not started."
    error: UiError | None = None

    @property
    def can_cancel(self) -> bool:
        if self.cancellability is Cancellability.NOT_CANCELLABLE:
            return False
        if self.state in {
            ActionExecutionState.PROPOSED,
            ActionExecutionState.WAITING_FOR_CONFIRMATION,
            ActionExecutionState.APPROVED,
            ActionExecutionState.QUEUED,
        }:
            return True
        return (
            self.cancellability is Cancellability.CANCELLABLE_DURING_EXECUTION
            and self.state is ActionExecutionState.EXECUTING
        )

    def transition(
        self,
        state: ActionExecutionState,
        *,
        message: str | None = None,
        error: UiError | None = None,
    ) -> ActionExecution:
        if state is self.state:
            return self
        if state not in _EXECUTION_TRANSITIONS[self.state]:
            raise ValueError(f"Invalid action transition: {self.state.value} -> {state.value}")
        return replace(
            self,
            state=state,
            message=message if message is not None else self.message,
            error=error,
        )

    def request_cancellation(self) -> ActionExecution:
        if not self.can_cancel:
            return self
        if self.state is ActionExecutionState.EXECUTING:
            return self.transition(
                ActionExecutionState.CANCELLING,
                message="Cancellation requested; awaiting the future tool adapter.",
            )
        return self.transition(
            ActionExecutionState.CANCELLED,
            message="Action cancelled before execution.",
        )


@dataclass(frozen=True, slots=True)
class VerificationResult:
    state: VerificationState = VerificationState.NOT_STARTED
    summary: str = "Verification has not started."
    evidence: tuple[str, ...] = ()
    error: UiError | None = None

