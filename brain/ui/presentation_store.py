"""Observable, Qt-free coordinator for desktop presentation state."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace

from .contracts import (
    AnalysisViewResult,
    OperationEvent,
    OperationHandle,
    OperationState,
    RuntimeStatus,
    UiError,
)
from .presentation_state import (
    NotificationLevel,
    PageId,
    PresentationState,
    ResultPhase,
    ResultPresentationState,
    RuntimePresentationState,
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

    def begin_operation(
        self,
        handle: OperationHandle,
        *,
        cancellable: bool = False,
        tracks_result: bool = True,
    ) -> None:
        operation = self._state.operation.begin(handle, cancellable=cancellable)
        self._publish(
            replace(
                self._state,
                operation=operation,
                result=(
                    ResultPresentationState.loading(handle.operation_id)
                    if tracks_result
                    else self._state.result
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

        if event.state is OperationState.COMPLETED:
            if event.result is not None and not isinstance(event.result, AnalysisViewResult):
                raise TypeError("Completed analysis events must carry AnalysisViewResult DTOs.")
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
        elif event.state is OperationState.FAILED and tracks_result:
            result_state = ResultPresentationState(
                phase=ResultPhase.FAILURE,
                operation_id=event.operation_id,
                error=event.error,
            )
        elif event.state is OperationState.CANCELLED and tracks_result:
            result_state = ResultPresentationState(
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
