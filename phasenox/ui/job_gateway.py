"""Qt-free scheduler gateway and presentation-safe Desktop job contracts."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class DesktopJobHandle:
    job_id: str


@dataclass(frozen=True, slots=True)
class DesktopJobProgress:
    current_stage: str | None
    completed_stages: tuple[str, ...] = ()
    pending_stages: tuple[str, ...] = ()
    stage_states: tuple[tuple[str, str], ...] = ()
    fraction: float | None = None


@dataclass(frozen=True, slots=True)
class DesktopResourceSnapshot:
    sampled_at: str | None
    cpu_percent: float | None = None
    ram_used_bytes: int | None = None
    ram_total_bytes: int | None = None
    gpu_memory_used_bytes: int | None = None
    gpu_memory_total_bytes: int | None = None


@dataclass(frozen=True, slots=True)
class DesktopJobSnapshot:
    job_id: str
    state: str
    operation: str
    created_at: str
    started_at: str | None
    finished_at: str | None
    progress: DesktopJobProgress
    can_cancel: bool
    cancellation_mode: str | None
    can_pause: bool
    can_resume: bool
    resource: DesktopResourceSnapshot | None = None
    error_code: str | None = None
    error_message: str | None = None


_SAFE_ERROR_MESSAGES = {
    "application_failure": "The operation could not be completed.",
    "cancelled": "The operation was cancelled.",
    "invalid_request": "The operation request is invalid.",
    "scheduler_failure": "The task scheduler could not complete the operation.",
}


class DesktopJobGateway:
    """Translate the Sprint 16 scheduler into stable Desktop-only contracts."""

    def __init__(
        self,
        scheduler: Any | None = None,
        *,
        scheduler_factory: Callable[[], Any] | None = None,
    ) -> None:
        self._scheduler = scheduler
        self._scheduler_factory = scheduler_factory

    def _scheduler_instance(self) -> Any:
        if self._scheduler is None:
            if self._scheduler_factory is not None:
                self._scheduler = self._scheduler_factory()
            else:
                from phasenox.application.service import PhasenoxV2Service
                from phasenox.runtime.jobs import JobScheduler

                self._scheduler = JobScheduler(PhasenoxV2Service)
        return self._scheduler

    def start(self) -> None:
        self._scheduler_instance().start()

    def shutdown(self, *, wait: bool = False) -> None:
        if self._scheduler is not None:
            self._scheduler.shutdown(wait=wait)

    def submit(
        self,
        operation: str,
        parameters: Mapping[str, Any],
        *,
        request_id: str,
        resource_profile: str = "balanced",
        device_hint: str | None = None,
        job_id: str | None = None,
    ) -> DesktopJobHandle:
        from phasenox.application.contracts import ApplicationRequest, OperationType
        from phasenox.runtime.jobs import ResourceProfile

        request = ApplicationRequest(
            request_id=request_id,
            operation=OperationType(operation),
            parameters=dict(parameters),
        )
        assigned_id = self._scheduler_instance().submit(
            request,
            resource_profile=ResourceProfile(resource_profile),
            device_hint=device_hint,
            job_id=job_id,
        )
        return DesktopJobHandle(assigned_id)

    def job_snapshot(self, job_id: str) -> DesktopJobSnapshot | None:
        return self._translate(self._scheduler_instance().get_status(job_id))

    def list_jobs(self, *, include_history: bool = False) -> tuple[DesktopJobSnapshot, ...]:
        snapshots = self._scheduler_instance().list_jobs(include_history=include_history)
        return tuple(self._translate(item) for item in snapshots if item is not None)

    def cancel_job(self, job_id: str) -> DesktopJobSnapshot | None:
        return self._translate(self._scheduler_instance().cancel(job_id))

    def pause_job(self, job_id: str) -> DesktopJobSnapshot | None:
        return self._translate(self._scheduler_instance().pause(job_id))

    def resume_job(self, job_id: str) -> DesktopJobSnapshot | None:
        return self._translate(self._scheduler_instance().resume(job_id))

    @classmethod
    def _translate(cls, snapshot: Any | None) -> DesktopJobSnapshot | None:
        if snapshot is None:
            return None
        progress = snapshot.progress
        fraction = getattr(progress, "fraction", None)
        mapped_progress = DesktopJobProgress(
            current_stage=progress.current_stage,
            completed_stages=tuple(progress.completed_stages),
            pending_stages=tuple(progress.pending_stages),
            stage_states=tuple(
                sorted((str(key), cls._value(value)) for key, value in progress.stage_states.items())
            ),
            fraction=float(fraction) if fraction is not None else None,
        )
        sampled_at = snapshot.finished_at or snapshot.started_at
        resource = cls._resource(
            getattr(snapshot, "resource_snapshot", None),
            sampled_at=str(sampled_at) if sampled_at is not None else None,
        )
        state = cls._value(snapshot.state)
        pause_mode = cls._value(snapshot.capability.pause)
        cancellation_mode = cls._value(snapshot.capability.cancellation)
        error = snapshot.error or getattr(snapshot.result, "error", None)
        error_code = str(error.code) if error is not None else None
        return DesktopJobSnapshot(
            job_id=str(snapshot.job_id),
            state=state,
            operation=str(snapshot.request.operation),
            created_at=str(snapshot.created_at),
            started_at=(str(snapshot.started_at) if snapshot.started_at is not None else None),
            finished_at=(str(snapshot.finished_at) if snapshot.finished_at is not None else None),
            progress=mapped_progress,
            can_cancel=cancellation_mode != "not_supported",
            cancellation_mode=(
                cancellation_mode if cancellation_mode != "not_supported" else None
            ),
            can_pause=state == "queued" and pause_mode == "queue_only",
            can_resume=state == "paused" and pause_mode == "queue_only",
            resource=resource,
            error_code=error_code,
            error_message=(cls._safe_error_message(error_code) if error_code else None),
        )

    @staticmethod
    def _resource(
        resource: Any | None,
        *,
        sampled_at: str | None,
    ) -> DesktopResourceSnapshot | None:
        if resource is None:
            return None
        return DesktopResourceSnapshot(
            sampled_at=sampled_at,
            cpu_percent=resource.cpu_percent,
            ram_used_bytes=resource.ram_used_bytes,
            ram_total_bytes=resource.ram_total_bytes,
            gpu_memory_used_bytes=resource.gpu_memory_used_bytes,
            gpu_memory_total_bytes=resource.gpu_memory_total_bytes,
        )

    @staticmethod
    def _safe_error_message(code: str) -> str:
        return _SAFE_ERROR_MESSAGES.get(code, "The task ended with a backend error.")

    @staticmethod
    def _value(value: Any) -> str:
        return str(getattr(value, "value", value))


__all__ = [
    "DesktopJobGateway",
    "DesktopJobHandle",
    "DesktopJobProgress",
    "DesktopJobSnapshot",
    "DesktopResourceSnapshot",
]
