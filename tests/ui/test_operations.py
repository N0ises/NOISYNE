from __future__ import annotations

from phasenox.ui.contracts import OperationEvent, OperationHandle, OperationState
from phasenox.ui.presentation_state import ResultPhase
from phasenox.ui.presentation_store import PresentationStore


def _event(operation_id: str, sequence: int, state: OperationState) -> OperationEvent:
    return OperationEvent(operation_id, sequence, state, state.value)


def test_operation_rejects_wrong_stale_and_late_events() -> None:
    store = PresentationStore()
    store.begin_operation(OperationHandle("op-1", "analysis"))

    assert not store.apply_operation_event(_event("op-2", 1, OperationState.RUNNING))
    assert store.apply_operation_event(_event("op-1", 1, OperationState.RUNNING))
    assert not store.apply_operation_event(_event("op-1", 1, OperationState.FAILED))
    assert store.apply_operation_event(_event("op-1", 2, OperationState.COMPLETED))
    assert not store.apply_operation_event(_event("op-1", 3, OperationState.FAILED))
    assert store.state.operation.state is OperationState.COMPLETED


def test_cancellation_request_is_not_false_completion() -> None:
    store = PresentationStore()
    store.begin_operation(OperationHandle("op-1", "analysis"), cancellable=True)

    assert store.request_cancellation()
    assert store.state.operation.state is OperationState.CANCELLING
    assert store.state.operation.cancel_requested
    assert store.state.result.phase is ResultPhase.LOADING

    assert store.apply_operation_event(_event("op-1", 1, OperationState.CANCELLED))
    assert store.state.result.phase is ResultPhase.CANCELLED


def test_non_cancellable_operation_does_not_claim_cancellation() -> None:
    store = PresentationStore()
    store.begin_operation(OperationHandle("op-1", "analysis"), cancellable=False)

    assert not store.request_cancellation()
    assert store.state.operation.state is OperationState.QUEUED

