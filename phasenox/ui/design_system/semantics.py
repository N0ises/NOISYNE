"""Semantic visual roles mapped from stable UI contracts and presentation state."""

from __future__ import annotations

from enum import Enum

from ..contracts import Availability, OperationState
from ..presentation_state import ResultPhase, RuntimePresentationPhase


class VisualState(str, Enum):
    IDLE = "idle"
    LOADING = "loading"
    READY = "ready"
    RUNNING = "running"
    SUCCESS = "success"
    WARNING = "warning"
    DEGRADED = "degraded"
    ERROR = "error"
    CANCELLED = "cancelled"
    UNAVAILABLE = "unavailable"
    DISABLED = "disabled"
    INFO = "info"
    UNKNOWN = "unknown"
    INTELLIGENCE = "intelligence"


def operation_visual_state(state: OperationState | None) -> VisualState:
    return {
        None: VisualState.IDLE,
        OperationState.QUEUED: VisualState.LOADING,
        OperationState.VALIDATING: VisualState.LOADING,
        OperationState.RUNNING: VisualState.RUNNING,
        OperationState.CANCELLING: VisualState.WARNING,
        OperationState.COMPLETED: VisualState.SUCCESS,
        OperationState.FAILED: VisualState.ERROR,
        OperationState.CANCELLED: VisualState.CANCELLED,
    }[state]


def result_visual_state(phase: ResultPhase) -> VisualState:
    return {
        ResultPhase.EMPTY: VisualState.IDLE,
        ResultPhase.LOADING: VisualState.LOADING,
        ResultPhase.SUCCESS: VisualState.SUCCESS,
        ResultPhase.WARNING: VisualState.WARNING,
        ResultPhase.FAILURE: VisualState.ERROR,
        ResultPhase.CANCELLED: VisualState.CANCELLED,
        ResultPhase.UNAVAILABLE: VisualState.UNAVAILABLE,
    }[phase]


def runtime_visual_state(phase: RuntimePresentationPhase) -> VisualState:
    return {
        RuntimePresentationPhase.LOADING: VisualState.LOADING,
        RuntimePresentationPhase.UNKNOWN: VisualState.UNKNOWN,
        RuntimePresentationPhase.READY: VisualState.READY,
        RuntimePresentationPhase.DEGRADED: VisualState.DEGRADED,
        RuntimePresentationPhase.UNAVAILABLE: VisualState.UNAVAILABLE,
    }[phase]


def availability_visual_state(availability: Availability) -> VisualState:
    return {
        Availability.AVAILABLE: VisualState.READY,
        Availability.DEGRADED: VisualState.DEGRADED,
        Availability.UNAVAILABLE: VisualState.UNAVAILABLE,
        Availability.UNKNOWN: VisualState.UNKNOWN,
    }[availability]

