"""Job executor: runs one NoisyneV2Service operation inside a worker thread."""

from __future__ import annotations

import datetime
import threading
from dataclasses import replace
from typing import Any

from .contracts import (
    JobError,
    JobProgress,
    JobResult,
    JobSnapshot,
    JobState,
    ResourceSnapshot,
)
from .registry import JobRegistry


class JobCancelled(Exception):
    """Raised when a job is cancelled before or during a checkpoint."""


class JobExecutor:
    """Executes one ApplicationRequest via a supplied NoisyneV2Service."""

    def __init__(self, service: Any) -> None:
        self._service = service

    def run_job(
        self, job_id: str, cancel_event: threading.Event, registry: JobRegistry
    ) -> JobSnapshot:
        """Run the job to completion, failure, or cancellation.

        The service call itself is treated as a single non-checkpointable stage:
        cooperative cancellation is honoured immediately before the call and after
        it returns, but the call cannot be forcibly interrupted mid-flight.
        """
        snapshot = registry.get(job_id)
        if snapshot is None:
            raise RuntimeError(f"Job {job_id} not found in registry")

        if cancel_event.is_set():
            return self._finish(snapshot, JobState.CANCELLED, registry)

        running = replace(
            snapshot,
            state=JobState.RUNNING,
            started_at=snapshot.started_at or _now_iso(),
            resource_snapshot=_capture_resource_snapshot(),
            progress=JobProgress(
                current_stage="execute",
                completed_stages=[],
                pending_stages=["execute"],
                stage_states={"execute": "running"},
            ),
        )
        registry.put(running)
        snapshot = running

        try:
            if cancel_event.is_set():
                raise JobCancelled()

            # Heavy application contract import is deferred to execution time.
            from noisyne.application.contracts import ApplicationRequest, OperationType

            operation = OperationType(snapshot.request.operation)
            app_request = ApplicationRequest(
                request_id=snapshot.request.request_id,
                operation=operation,
                parameters=dict(snapshot.request.parameters),
            )
            app_result = self._service.execute(app_request)

            # Build truthful progress from service stage outcomes.
            completed_stages: list[str] = []
            stage_states: dict[str, str] = {}
            for stage in app_result.stages:
                completed_stages.append(stage.stage_id)
                stage_states[stage.stage_id] = stage.state.value

            if cancel_event.is_set():
                return self._finish(snapshot, JobState.CANCELLED, registry)

            status = app_result.status.value
            result = JobResult(
                status=status,
                payload=app_result.payload,
            )
            error: JobError | None = None
            if status == "failed" and app_result.errors:
                first = app_result.errors[0]
                error = JobError(
                    code=first.code,
                    message=first.message,
                    stage_id=first.stage_id,
                )
                state = JobState.FAILED
            elif status == "failed":
                error = JobError(code="execution_failed", message="Service reported failure")
                state = JobState.FAILED
            else:
                # success / partial both map to COMPLETED; result.status carries the nuance.
                state = JobState.COMPLETED

            progress = JobProgress(
                current_stage=completed_stages[-1] if completed_stages else None,
                completed_stages=completed_stages,
                pending_stages=[],
                stage_states=stage_states,
            )
            return self._finish(
                snapshot, state, registry, result=result, error=error, progress=progress
            )
        except JobCancelled:
            return self._finish(snapshot, JobState.CANCELLED, registry)
        except Exception as exc:  # noqa: BLE001
            error = JobError(
                code="execution_failure",
                message=f"Unhandled job execution error: {exc}",
            )
            return self._finish(snapshot, JobState.FAILED, registry, error=error)

    def _finish(
        self,
        snapshot: JobSnapshot,
        state: JobState,
        registry: JobRegistry,
        result: JobResult | None = None,
        error: JobError | None = None,
        progress: JobProgress | None = None,
    ) -> JobSnapshot:
        final = replace(
            snapshot,
            state=state,
            finished_at=_now_iso(),
            result=result,
            error=error,
            progress=(
                progress
                if progress is not None
                else JobProgress(
                    current_stage=None,
                    completed_stages=snapshot.progress.completed_stages,
                    pending_stages=[],
                    stage_states=snapshot.progress.stage_states,
                )
            ),
            capability=_terminal_capability(state),
            resource_snapshot=_capture_resource_snapshot(),
        )
        registry.put(final)
        return final


def _now_iso() -> str:
    return datetime.datetime.now(datetime.UTC).isoformat()


def _terminal_capability(state: JobState) -> Any:
    """Capabilities are meaningless once a job is terminal."""
    from .contracts import CancellationCapability, JobCapability, PauseCapability

    return JobCapability(
        pause=PauseCapability.NOT_SUPPORTED,
        cancellation=CancellationCapability.NOT_SUPPORTED,
    )


def _capture_resource_snapshot() -> ResourceSnapshot:
    """Return a lightweight, truthful resource observation if psutil/torch are available."""
    cpu_percent: float | None = None
    ram_used: int | None = None
    ram_total: int | None = None
    gpu_name: str | None = None
    gpu_used: int | None = None
    gpu_total: int | None = None

    try:
        import psutil

        cpu_percent = float(psutil.cpu_percent(interval=None))
        mem = psutil.virtual_memory()
        ram_used = int(mem.used)
        ram_total = int(mem.total)
    except Exception:  # noqa: BLE001, S110
        pass

    try:
        import torch

        if torch.cuda.is_available():
            gpu_name = str(torch.cuda.get_device_name(0))
            gpu_total = int(torch.cuda.get_device_properties(0).total_memory)
            gpu_used = int(torch.cuda.memory_allocated(0))
    except Exception:  # noqa: BLE001, S110
        pass

    return ResourceSnapshot(
        cpu_percent=cpu_percent,
        ram_used_bytes=ram_used,
        ram_total_bytes=ram_total,
        gpu_name=gpu_name,
        gpu_memory_used_bytes=gpu_used,
        gpu_memory_total_bytes=gpu_total,
    )
