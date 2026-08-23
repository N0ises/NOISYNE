"""Observable, Qt-free coordinator for desktop presentation state."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from pathlib import Path

from .agent_contracts import (
    ActionExecution,
    AgentPlan,
    ConfirmationDecision,
    ConfirmationOutcome,
    ConfirmationScope,
    PermissionDisposition,
    VerificationResult,
)
from .contracts import (
    AnalysisViewResult,
    KnowledgeSearchResult,
    OperationEvent,
    OperationHandle,
    OperationState,
    ReferenceViewResult,
    ReportExportResult,
    ReportPreview,
    RuntimeStatus,
    SettingsSnapshot,
    UiError,
)
from .presentation_state import (
    KnowledgeResultPresentationState,
    NotificationLevel,
    PageId,
    PresentationState,
    ReferenceResultPresentationState,
    ReportExportPresentationState,
    ReportPreviewPresentationState,
    ResultPhase,
    ResultPresentationState,
    RuntimePresentationState,
    SessionState,
    SettingsPresentationPhase,
    SettingsPresentationState,
)
from .voice_contracts import (
    ActionProposal,
    ActionResultSummary,
    TranscriptItem,
    VoiceAvailability,
    VoiceLifecycle,
    VoicePresentationState,
)

Subscriber = Callable[[PresentationState], None]


class PresentationStore:
    def __init__(self, state: PresentationState | None = None) -> None:
        self._state = state or PresentationState()
        self._subscribers: list[Subscriber] = []

    @property
    def state(self) -> PresentationState:
        return self._state

    def subscribe(self, subscriber: Subscriber) -> Callable[[], None]:
        self._subscribers.append(subscriber)
        subscriber(self._state)

        def unsubscribe() -> None:
            if subscriber in self._subscribers:
                self._subscribers.remove(subscriber)

        return unsubscribe

    def navigate(self, page: PageId) -> None:
        self._publish(
            replace(
                self._state,
                navigation=self._state.navigation.navigate(page),
                session=self._state.session.navigate(page),
            )
        )

    def set_session(self, session: SessionState) -> None:
        self._publish(replace(self._state, session=session, navigation=session.navigation))

    def select_audio(self, path: Path | None) -> None:
        self.set_session(self._state.session.select_audio(path))

    def select_references(self, paths: tuple[Path, ...]) -> None:
        self.set_session(self._state.session.select_references(paths))

    def select_report(self, path: Path | None) -> None:
        self.set_session(self._state.session.select_report(path))

    def set_voice_state(self, voice: VoicePresentationState) -> None:
        """Accept state from a future voice adapter without coupling Qt to it."""
        self._publish(replace(self._state, voice=voice))

    def set_voice_availability(self, availability: VoiceAvailability) -> None:
        self._publish(
            replace(
                self._state,
                voice=replace(self._state.voice, availability=availability),
            )
        )

    def transition_voice(self, lifecycle: VoiceLifecycle) -> None:
        self._publish(
            replace(
                self._state,
                voice=self._state.voice.transition(lifecycle),
            )
        )

    def request_voice_interruption(self) -> bool:
        voice = self._state.voice.request_interruption()
        if voice is self._state.voice:
            return False
        self._publish(replace(self._state, voice=voice))
        return True

    def append_voice_transcript(self, item: TranscriptItem) -> None:
        self._publish(
            replace(
                self._state,
                voice=self._state.voice.append_transcript(item),
            )
        )

    def set_voice_proposal(self, proposal: ActionProposal | None) -> None:
        self._publish(
            replace(
                self._state,
                voice=replace(self._state.voice, proposal=proposal),
            )
        )

    def set_voice_result(self, result: ActionResultSummary | None) -> None:
        self._publish(
            replace(
                self._state,
                voice=replace(self._state.voice, result=result),
            )
        )

    def set_agent_plan(self, plan: AgentPlan | None) -> None:
        """Publish an immutable proposal snapshot; this does not execute any action."""
        self._publish(
            replace(
                self._state,
                voice=replace(
                    self._state.voice,
                    agent_plan=plan,
                    confirmation=None,
                    executions=(),
                    verification=VerificationResult(),
                ),
            )
        )

    def record_agent_confirmation(self, decision: ConfirmationDecision) -> bool:
        plan = self._state.voice.agent_plan
        if plan is None:
            return False
        if decision.plan_id != plan.plan_id or decision.plan_revision != plan.revision:
            return False
        plan_action_ids = tuple(item.action_id for item in plan.actions)
        if any(action_id not in plan_action_ids for action_id in decision.action_ids):
            return False
        if decision.scope is ConfirmationScope.PLAN and decision.action_ids != plan_action_ids:
            return False
        if decision.outcome is ConfirmationOutcome.APPROVED and plan.blocked:
            return False
        selected = tuple(
            action for action in plan.actions if action.action_id in decision.action_ids
        )
        if decision.outcome is ConfirmationOutcome.APPROVED and any(
            action.permission.disposition is PermissionDisposition.BLOCKED for action in selected
        ):
            return False
        self._publish(
            replace(
                self._state,
                voice=replace(self._state.voice, confirmation=decision),
            )
        )
        return True

    def set_agent_execution(self, execution: ActionExecution) -> None:
        executions = tuple(
            item for item in self._state.voice.executions if item.action_id != execution.action_id
        )
        self._publish(
            replace(
                self._state,
                voice=replace(
                    self._state.voice,
                    executions=(*executions, execution),
                ),
            )
        )

    def set_agent_verification(self, verification: VerificationResult) -> None:
        self._publish(
            replace(
                self._state,
                voice=replace(self._state.voice, verification=verification),
            )
        )

    def begin_operation(
        self,
        handle: OperationHandle,
        *,
        cancellable: bool = False,
        tracks_result: bool = True,
        tracks_reference_result: bool = False,
        tracks_knowledge_result: bool = False,
        tracks_report_preview: bool = False,
        tracks_report_export: bool = False,
    ) -> None:
        operation = self._state.operation.begin(handle, cancellable=cancellable)
        self._publish(
            replace(
                self._state,
                operation=operation,
                result=(
                    ResultPresentationState.loading(
                        handle.operation_id,
                        self._state.result.result,
                    )
                    if tracks_result
                    else self._state.result
                ),
                reference_result=(
                    ReferenceResultPresentationState.loading(
                        handle.operation_id,
                        self._state.reference_result.result,
                    )
                    if tracks_reference_result
                    else self._state.reference_result
                ),
                knowledge_result=(
                    KnowledgeResultPresentationState.loading(
                        handle.operation_id,
                        self._state.knowledge_result.result,
                    )
                    if tracks_knowledge_result
                    else self._state.knowledge_result
                ),
                report_preview=(
                    ReportPreviewPresentationState.loading(handle.operation_id)
                    if tracks_report_preview
                    else self._state.report_preview
                ),
                report_export=(
                    ReportExportPresentationState.loading(handle.operation_id)
                    if tracks_report_export
                    else self._state.report_export
                ),
                session=self._state.session.with_operation(handle),
            )
        )

    def request_cancellation(self) -> bool:
        operation = self._state.operation.request_cancel()
        if operation is self._state.operation:
            return False
        handle = OperationHandle(
            operation_id=operation.operation_id or "",
            kind=operation.kind or "",
            state=OperationState.CANCELLING,
            cancel_requested=True,
        )
        self._publish(
            replace(
                self._state,
                operation=operation,
                session=self._state.session.with_operation(handle),
            )
        )
        return True

    def apply_operation_event(self, event: OperationEvent) -> bool:
        operation, accepted = self._state.operation.apply(event)
        if not accepted:
            return False

        result_state = self._state.result
        session = self._state.session.with_operation(
            OperationHandle(
                operation_id=event.operation_id,
                kind=operation.kind or "",
                state=event.state,
                cancel_requested=operation.cancel_requested,
            )
        )
        notifications = self._state.notifications
        tracks_result = result_state.operation_id == event.operation_id
        reference_result = self._state.reference_result
        tracks_reference_result = reference_result.operation_id == event.operation_id
        knowledge_result = self._state.knowledge_result
        tracks_knowledge_result = knowledge_result.operation_id == event.operation_id
        report_preview = self._state.report_preview
        tracks_report_preview = report_preview.operation_id == event.operation_id
        report_export = self._state.report_export
        tracks_report_export = report_export.operation_id == event.operation_id

        if event.state is OperationState.COMPLETED:
            if event.result is not None and not isinstance(
                event.result,
                (
                    AnalysisViewResult,
                    ReferenceViewResult,
                    KnowledgeSearchResult,
                    ReportPreview,
                    ReportExportResult,
                ),
            ):
                raise TypeError("Completed UI operations must carry stable result DTOs.")
            if tracks_result and isinstance(event.result, AnalysisViewResult):
                phase = (
                    ResultPhase.WARNING
                    if event.result.warnings or event.result.status.casefold() == "degraded"
                    else ResultPhase.SUCCESS
                )
                result_state = ResultPresentationState(
                    phase=phase,
                    operation_id=event.operation_id,
                    result=event.result,
                )
                session = session.record_analysis(event.result)
                for warning in event.result.warnings:
                    notifications = notifications.add(
                        level=NotificationLevel.WARNING,
                        message=warning,
                        operation_id=event.operation_id,
                    )
            elif tracks_reference_result and isinstance(event.result, ReferenceViewResult):
                phase = (
                    ResultPhase.WARNING
                    if event.result.warnings or event.result.status.casefold() == "degraded"
                    else ResultPhase.SUCCESS
                )
                reference_result = ReferenceResultPresentationState(
                    phase=phase,
                    operation_id=event.operation_id,
                    result=event.result,
                )
                session = session.record_reference_result(event.result)
                for warning in event.result.warnings:
                    notifications = notifications.add(
                        level=NotificationLevel.WARNING,
                        message=warning,
                        operation_id=event.operation_id,
                    )
            elif tracks_knowledge_result and isinstance(event.result, KnowledgeSearchResult):
                phase = ResultPhase.WARNING if event.result.warnings else ResultPhase.SUCCESS
                knowledge_result = KnowledgeResultPresentationState(
                    phase=phase,
                    operation_id=event.operation_id,
                    result=event.result,
                )
                session = session.record_knowledge_result(event.result)
                for warning in event.result.warnings:
                    notifications = notifications.add(
                        level=NotificationLevel.WARNING,
                        message=warning,
                        operation_id=event.operation_id,
                    )
            elif tracks_report_preview and isinstance(event.result, ReportPreview):
                phase = (
                    ResultPhase.WARNING
                    if event.result.warnings or event.result.unavailable_reason
                    else ResultPhase.SUCCESS
                )
                report_preview = ReportPreviewPresentationState(
                    phase=phase,
                    operation_id=event.operation_id,
                    preview=event.result,
                )
                for warning in event.result.warnings:
                    notifications = notifications.add(
                        level=NotificationLevel.WARNING,
                        message=warning,
                        operation_id=event.operation_id,
                    )
            elif tracks_report_export and isinstance(event.result, ReportExportResult):
                phase = ResultPhase.WARNING if event.result.warnings else ResultPhase.SUCCESS
                report_export = ReportExportPresentationState(
                    phase=phase,
                    operation_id=event.operation_id,
                    result=event.result,
                )
                session = session.record_report(event.result.exported)
                for warning in event.result.warnings:
                    notifications = notifications.add(
                        level=NotificationLevel.WARNING,
                        message=warning,
                        operation_id=event.operation_id,
                    )
        elif event.state is OperationState.FAILED and tracks_result:
            result_state = ResultPresentationState(
                phase=ResultPhase.FAILURE,
                operation_id=event.operation_id,
                result=result_state.result,
                error=event.error,
            )
        elif event.state is OperationState.CANCELLED and tracks_result:
            result_state = ResultPresentationState(
                phase=ResultPhase.CANCELLED,
                operation_id=event.operation_id,
                result=result_state.result,
                error=event.error,
            )
        elif event.state is OperationState.FAILED and tracks_reference_result:
            reference_result = ReferenceResultPresentationState(
                phase=ResultPhase.FAILURE,
                operation_id=event.operation_id,
                result=reference_result.result,
                error=event.error,
            )
        elif event.state is OperationState.CANCELLED and tracks_reference_result:
            reference_result = ReferenceResultPresentationState(
                phase=ResultPhase.CANCELLED,
                operation_id=event.operation_id,
                result=reference_result.result,
                error=event.error,
            )
        elif event.state is OperationState.FAILED and tracks_knowledge_result:
            knowledge_result = KnowledgeResultPresentationState(
                phase=ResultPhase.FAILURE,
                operation_id=event.operation_id,
                result=knowledge_result.result,
                error=event.error,
            )
        elif event.state is OperationState.CANCELLED and tracks_knowledge_result:
            knowledge_result = KnowledgeResultPresentationState(
                phase=ResultPhase.CANCELLED,
                operation_id=event.operation_id,
                result=knowledge_result.result,
                error=event.error,
            )
        elif event.state is OperationState.FAILED and tracks_report_preview:
            report_preview = ReportPreviewPresentationState(
                phase=ResultPhase.FAILURE,
                operation_id=event.operation_id,
                error=event.error,
            )
        elif event.state is OperationState.CANCELLED and tracks_report_preview:
            report_preview = ReportPreviewPresentationState(
                phase=ResultPhase.CANCELLED,
                operation_id=event.operation_id,
                error=event.error,
            )
        elif event.state is OperationState.FAILED and tracks_report_export:
            report_export = ReportExportPresentationState(
                phase=ResultPhase.FAILURE,
                operation_id=event.operation_id,
                error=event.error,
            )
        elif event.state is OperationState.CANCELLED and tracks_report_export:
            report_export = ReportExportPresentationState(
                phase=ResultPhase.CANCELLED,
                operation_id=event.operation_id,
                error=event.error,
            )

        if event.state is OperationState.FAILED and event.error is not None:
            notifications = notifications.add(
                level=NotificationLevel.ERROR,
                message=event.error.user_message,
                operation_id=event.operation_id,
                error=event.error,
                recovery_actions=event.error.recovery_actions,
            )

        self._publish(
            replace(
                self._state,
                operation=operation,
                result=result_state,
                reference_result=reference_result,
                knowledge_result=knowledge_result,
                report_preview=report_preview,
                report_export=report_export,
                notifications=notifications,
                session=session,
            )
        )
        return True

    def set_runtime_loading(self) -> None:
        self._publish(replace(self._state, runtime=RuntimePresentationState.loading()))

    def set_runtime_unknown(self) -> None:
        self._publish(replace(self._state, runtime=RuntimePresentationState()))

    def set_runtime_status(self, status: RuntimeStatus) -> None:
        self._publish(replace(self._state, runtime=RuntimePresentationState.from_status(status)))

    def set_settings_loading(self) -> None:
        self._publish(
            replace(
                self._state,
                settings=SettingsPresentationState(
                    phase=SettingsPresentationPhase.LOADING,
                    snapshot=self._state.settings.snapshot,
                ),
            )
        )

    def set_settings_snapshot(self, snapshot: SettingsSnapshot) -> None:
        self._publish(
            replace(
                self._state,
                settings=SettingsPresentationState(
                    phase=SettingsPresentationPhase.READY,
                    snapshot=snapshot,
                ),
            )
        )

    def set_settings_error(self, error: UiError) -> None:
        self._publish(
            replace(
                self._state,
                settings=SettingsPresentationState(
                    phase=SettingsPresentationPhase.FAILURE,
                    snapshot=self._state.settings.snapshot,
                    error=error,
                ),
            )
        )
        self.add_error(error)

    def add_notification(
        self,
        level: NotificationLevel,
        message: str,
        *,
        operation_id: str | None = None,
    ) -> str:
        notifications = self._state.notifications.add(
            level=level,
            message=message,
            operation_id=operation_id,
        )
        notification_id = notifications.active[-1].notification_id
        self._publish(replace(self._state, notifications=notifications))
        return notification_id

    def add_error(self, error: UiError) -> str:
        """Add a structured global or operation-linked error without parsing exceptions."""
        existing_id = self._state.notifications.active_error_id(error)
        if existing_id is not None:
            return existing_id
        notifications = self._state.notifications.add(
            level=NotificationLevel.ERROR,
            message=error.user_message,
            operation_id=error.operation_id,
            error=error,
            recovery_actions=error.recovery_actions,
        )
        notification_id = notifications.active[-1].notification_id
        self._publish(replace(self._state, notifications=notifications))
        return notification_id

    def dismiss_notification(self, notification_id: str) -> None:
        self._publish(
            replace(
                self._state,
                notifications=self._state.notifications.dismiss(notification_id),
            )
        )

    def _publish(self, state: PresentationState) -> None:
        self._state = state
        for subscriber in tuple(self._subscribers):
            subscriber(state)

