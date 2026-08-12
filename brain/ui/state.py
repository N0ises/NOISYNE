"""Minimal application-level state foundation for the desktop shell."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, replace
from enum import Enum


class ApplicationLifecycle(str, Enum):
    STARTING = "starting"
    READY = "ready"
    STOPPING = "stopping"
    STOPPED = "stopped"


@dataclass(frozen=True, slots=True)
class ApplicationState:
    lifecycle: ApplicationLifecycle = ApplicationLifecycle.STARTING
    status_message: str = "Starting"


class ApplicationStateStore:
    """Small observable store; feature state belongs to later sprints."""

    def __init__(self, initial: ApplicationState | None = None) -> None:
        self._state = initial or ApplicationState()
        self._subscribers: list[Callable[[ApplicationState], None]] = []

    @property
    def state(self) -> ApplicationState:
        return self._state

    def subscribe(self, callback: Callable[[ApplicationState], None]) -> None:
        self._subscribers.append(callback)

    def set_lifecycle(self, lifecycle: ApplicationLifecycle, message: str) -> None:
        self._state = replace(self._state, lifecycle=lifecycle, status_message=message)
        for callback in tuple(self._subscribers):
            callback(self._state)
