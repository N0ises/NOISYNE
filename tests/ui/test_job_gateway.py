from __future__ import annotations

import threading
import time

from phasenox.application.contracts import (
    ApplicationResult,
    ApplicationResultStatus,
    OperationType,
)
from phasenox.runtime.jobs import JobScheduler
from phasenox.ui.job_gateway import DesktopJobGateway
from phasenox.ui.task_center import TaskCenterState


class BlockingService:
    def __init__(self, entered: threading.Event, release: threading.Event) -> None:
        self._entered = entered
        self._release = release

    def execute(self, request):
        self._entered.set()
        if not self._release.wait(timeout=5):
            raise TimeoutError("test service was not released")
        return ApplicationResult(
            request_id=request.request_id,
            operation=request.operation,
            status=ApplicationResultStatus.SUCCESS,
            payload={"safe": True},
        )


def _wait_for(gateway: DesktopJobGateway, job_id: str, state: str, timeout: float = 5.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        snapshot = gateway.job_snapshot(job_id)
        if snapshot is not None and snapshot.state == state:
            return snapshot
        time.sleep(0.01)
    raise AssertionError(f"job {job_id} did not reach {state}")


def test_gateway_maps_history_queue_controls_and_cooperative_cancellation() -> None:
    entered = threading.Event()
    release = threading.Event()
    scheduler = JobScheduler(lambda: BlockingService(entered, release), max_workers=1)
    gateway = DesktopJobGateway(scheduler)
    gateway.start()
    try:
        running = gateway.submit(
            OperationType.CAPABILITY_INSPECT.value,
            {},
            request_id="running-request",
        )
        assert entered.wait(timeout=5)
        running_snapshot = _wait_for(gateway, running.job_id, "running")
        assert running_snapshot.cancellation_mode == "cooperative"
        assert not running_snapshot.can_pause
        assert running_snapshot.progress.fraction is None

        queued = gateway.submit(
            OperationType.CAPABILITY_INSPECT.value,
            {},
            request_id="queued-request",
        )
        queued_snapshot = _wait_for(gateway, queued.job_id, "queued")
        assert queued_snapshot.can_pause
        assert queued_snapshot.can_cancel

        paused = gateway.pause_job(queued.job_id)
        assert paused is not None and paused.state == "paused" and paused.can_resume
        resumed = gateway.resume_job(queued.job_id)
        assert resumed is not None and resumed.state == "queued"
        cancelled = gateway.cancel_job(queued.job_id)
        assert cancelled is not None and cancelled.state == "cancelled"

        cancelling = gateway.cancel_job(running.job_id)
        assert cancelling is not None and cancelling.state == "cancelling"
        assert cancelling.cancellation_mode == "cooperative"
        release.set()
        _wait_for(gateway, running.job_id, "cancelled")

        state = TaskCenterState(gateway.list_jobs(include_history=True))
        assert len(state.history) == 2
        assert state.active_jobs == ()
        assert not hasattr(state.jobs[0], "queue_position")
        assert not hasattr(state.jobs[0], "scheduler_capacity")
    finally:
        release.set()
        gateway.shutdown(wait=True)


def test_gateway_shutdown_without_jobs_is_safe_and_idempotent() -> None:
    scheduler = JobScheduler(BlockingService(threading.Event(), threading.Event()))
    gateway = DesktopJobGateway(scheduler)

    gateway.start()
    gateway.shutdown(wait=False)
    gateway.shutdown(wait=False)
