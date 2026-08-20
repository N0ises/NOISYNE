"""Async job scheduler for Sprint 16."""

from __future__ import annotations

import datetime
import logging
import os
import threading
import uuid
from collections import deque
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import replace
from typing import Any

from .contracts import (
    CancellationCapability,
    JobCapability,
    JobError,
    JobProgress,
    JobRequest,
    JobSnapshot,
    JobState,
    PauseCapability,
    ResourceProfile,
)
from .executor import JobExecutor, _now_iso
from .registry import JobRegistry

logger = logging.getLogger(__name__)


_TERMINAL_STATES = {"completed", "failed", "cancelled"}


def _concurrency_for_profile(profile: ResourceProfile) -> int:
    if profile is ResourceProfile.LOW_RESOURCE:
        return 1
    if profile is ResourceProfile.PERFORMANCE:
        return max(2, (os.cpu_count() or 2) // 2)
    return 2


def _terminal_capability() -> JobCapability:
    return JobCapability(
        pause=PauseCapability.NOT_SUPPORTED,
        cancellation=CancellationCapability.NOT_SUPPORTED,
    )


def _running_capability() -> JobCapability:
    return JobCapability(
        pause=PauseCapability.NOT_SUPPORTED,
        cancellation=CancellationCapability.COOPERATIVE,
    )


def _queued_capability() -> JobCapability:
    return JobCapability(
        pause=PauseCapability.QUEUE_ONLY,
        cancellation=CancellationCapability.BEFORE_START,
    )


class JobScheduler:
    """Bounded, asynchronous job scheduler wrapping NoisyneV2Service operations.

    The scheduler maintains its own dispatch queue on top of a thread pool so
    that ``QUEUED`` reflects scheduler-level back-pressure, not merely the
    internal ThreadPoolExecutor work queue.
    """

    def __init__(
        self,
        service: Any,
        *,
        max_workers: int | None = None,
        default_profile: ResourceProfile = ResourceProfile.BALANCED,
        max_history: int = 100,
    ) -> None:
        """Construct a scheduler.

        *service* may be a ``NoisyneV2Service`` instance or a callable factory
        that returns one.  A factory is useful when each worker thread needs
        its own service instance, though the default instance is shared by
        callers that pass an instance directly.
        """
        self._service_factory = service if callable(service) else lambda: service
        self._service: Any = service if not callable(service) else None
        self._default_profile = default_profile
        self._registry = JobRegistry(max_history=max_history)
        self._executor: ThreadPoolExecutor | None = None
        self._dispatcher: threading.Thread | None = None
        self._running = False
        self._lock = threading.RLock()
        self._condition = threading.Condition(self._lock)
        self._queue: deque[str] = deque()
        self._paused_ids: set[str] = set()
        self._cancel_events: dict[str, threading.Event] = {}
        self._futures: dict[str, Future[Any]] = {}
        self._gpu_lock = threading.Lock()
        self._slots: threading.Semaphore | None = None
        self._max_workers = max_workers or _concurrency_for_profile(default_profile)

    @property
    def _service_instance(self) -> Any:
        if self._service is None:
            self._service = self._service_factory()
        return self._service

    def start(self) -> None:
        """Start the scheduler, worker pool, and dispatcher thread."""
        with self._lock:
            if self._running:
                return
            self._slots = threading.Semaphore(self._max_workers)
            self._executor = ThreadPoolExecutor(
                max_workers=self._max_workers,
                thread_name_prefix="noisyne_job_",
            )
            self._running = True
            self._dispatcher = threading.Thread(
                target=self._dispatch_loop,
                name="noisyne_job_dispatcher",
                daemon=True,
            )
            self._dispatcher.start()

    def shutdown(self, wait: bool = True) -> None:
        """Stop accepting new jobs and shut down the worker pool."""
        with self._lock:
            self._running = False
            self._condition.notify_all()
            executor = self._executor
            self._executor = None
            self._slots = None
        if executor is not None:
            executor.shutdown(wait=wait)
        dispatcher = self._dispatcher
        self._dispatcher = None
        if dispatcher is not None and dispatcher.is_alive():
            dispatcher.join(timeout=5.0)

    def submit(
        self,
        application_request: Any,
        *,
        resource_profile: ResourceProfile | None = None,
        device_hint: str | None = None,
        job_id: str | None = None,
    ) -> str:
        """Submit a Sprint 15 ApplicationRequest as an asynchronous job.

        Returns the assigned job_id.  The caller receives a snapshot in
        ``QUEUED`` state immediately; heavy execution happens on a worker
        thread only when a concurrency slot is available.
        """
        if resource_profile is None:
            resource_profile = self._default_profile

        # Deferred import keeps the scheduler module lightweight.
        from noisyne.application.contracts import ApplicationRequest

        if not isinstance(application_request, ApplicationRequest):
            raise TypeError("application_request must be an ApplicationRequest")

        assigned_id = job_id or str(uuid.uuid4())
        job_request = JobRequest(
            request_id=application_request.request_id,
            operation=application_request.operation.value,
            parameters=dict(application_request.parameters),
            resource_profile=resource_profile,
            device_hint=device_hint,
        )
        snapshot = JobSnapshot(
            job_id=assigned_id,
            state=JobState.QUEUED,
            request=job_request,
            progress=JobProgress(
                current_stage=None,
                completed_stages=[],
                pending_stages=["execute"],
                stage_states={},
            ),
            capability=_queued_capability(),
            created_at=_now_iso(),
            resource_profile=resource_profile,
        )
        with self._lock:
            if not self._running or self._executor is None or self._slots is None:
                raise RuntimeError("Scheduler is not running")
            self._registry.put(snapshot)
            self._queue.append(assigned_id)
            self._condition.notify()
        return assigned_id

    def _dispatch_loop(self) -> None:
        """Background thread that moves queued jobs into the worker pool."""
        while True:
            with self._lock:
                if not self._running:
                    break
                job_id = self._next_dispatchable_job()
                if job_id is None:
                    self._condition.wait(timeout=0.1)
                    continue
                slots = self._slots
                executor = self._executor
                if slots is None or executor is None:
                    # Scheduler is shutting down; re-queue the job so history
                    # records it rather than silently dropping it.
                    self._queue.appendleft(job_id)
                    break
                cancel_event = threading.Event()
                self._cancel_events[job_id] = cancel_event
                future = executor.submit(self._run_job_wrapper, job_id, cancel_event)
                self._futures[job_id] = future

    def _next_dispatchable_job(self) -> str | None:
        """Return the next QUEUED, non-paused job id and remove it from queue."""
        for jid in list(self._queue):
            snapshot = self._registry.get(jid)
            if snapshot is None:
                self._queue.remove(jid)
                continue
            if snapshot.state is JobState.QUEUED:
                self._queue.remove(jid)
                return jid
        return None

    def _run_job_wrapper(self, job_id: str, cancel_event: threading.Event) -> None:
        """Worker entry point: acquire resources, then run the job."""
        slots = self._slots
        slot_acquired = False
        try:
            if slots is None:
                return
            slots.acquire()
            slot_acquired = True

            snapshot = self._registry.get(job_id)
            if snapshot is None:
                return
            if snapshot.state.value in _TERMINAL_STATES:
                return
            if snapshot.state is JobState.PAUSED:
                # Re-queue paused jobs; the dispatcher skips them until resumed.
                with self._lock:
                    self._queue.appendleft(job_id)
                return

            use_gpu = snapshot.request.device_hint == "cuda" or (
                snapshot.request.resource_profile is ResourceProfile.PERFORMANCE
                and snapshot.request.device_hint != "cpu"
            )

            if use_gpu:
                self._gpu_lock.acquire()
            try:
                with self._lock:
                    snap = self._registry.get(job_id)
                    if snap is None or snap.state.value in _TERMINAL_STATES:
                        return
                    running = replace(
                        snap,
                        state=JobState.RUNNING,
                        started_at=snap.started_at or _now_iso(),
                        capability=_running_capability(),
                        resource_snapshot=_capture_resource_snapshot(),
                    )
                    self._registry.put(running)

                if cancel_event.is_set():
                    self._finish_cancelled(job_id)
                    return

                JobExecutor(self._service_instance).run_job(job_id, cancel_event, self._registry)
            finally:
                if use_gpu:
                    self._gpu_lock.release()
        except Exception:
            logger.exception("Unhandled scheduler error running job %s", job_id)
            # Try to leave the job in a terminal failed state rather than
            # disappearing.
            try:
                snapshot = self._registry.get(job_id)
                if snapshot is not None and snapshot.state.value not in _TERMINAL_STATES:
                    final = replace(
                        snapshot,
                        state=JobState.FAILED,
                        finished_at=_now_iso(),
                        error=JobError(
                            code="scheduler_failure",
                            message="Unhandled scheduler error",
                        ),
                        capability=_terminal_capability(),
                    )
                    self._registry.put(final)
            except Exception:  # noqa: BLE001, S110
                pass
        finally:
            if slot_acquired and slots is not None:
                try:
                    slots.release()
                except ValueError:
                    pass
            with self._lock:
                self._futures.pop(job_id, None)
                self._cancel_events.pop(job_id, None)
                self._condition.notify()

    def _finish_cancelled(self, job_id: str) -> None:
        snapshot = self._registry.get(job_id)
        if snapshot is None or snapshot.state.value in _TERMINAL_STATES:
            return
        final = replace(
            snapshot,
            state=JobState.CANCELLED,
            finished_at=_now_iso(),
            capability=_terminal_capability(),
        )
        self._registry.put(final)

    def get_status(self, job_id: str) -> JobSnapshot | None:
        """Return the current snapshot for one job."""
        return self._registry.get(job_id)

    def list_jobs(self, *, include_history: bool = False) -> list[JobSnapshot]:
        """Return all active jobs, optionally including bounded history."""
        if include_history:
            return self._registry.list_all()
        return self._registry.list_active()

    def wait(
        self,
        job_id: str,
        timeout: float | None = None,
        poll_interval: float = 0.01,
    ) -> JobSnapshot | None:
        """Block until the job reaches a terminal state or the timeout expires."""
        deadline = (
            None if timeout is None else (datetime.datetime.now(datetime.UTC).timestamp() + timeout)
        )
        while True:
            snapshot = self._registry.get(job_id)
            if snapshot is None:
                return None
            if snapshot.state.value in _TERMINAL_STATES:
                return snapshot
            if deadline is not None and datetime.datetime.now(datetime.UTC).timestamp() >= deadline:
                return snapshot
            threading.Event().wait(poll_interval)

    def cancel(self, job_id: str) -> JobSnapshot | None:
        """Request cancellation of a queued or running job.

        Queued jobs become ``CANCELLED`` immediately.  Running jobs are
        cooperatively cancelled at the next checkpoint; if the underlying
        operation cannot be interrupted, the job continues and is marked
        ``CANCELLED`` once it finishes or reaches a checkpoint.
        """
        with self._lock:
            snapshot = self._registry.get(job_id)
            if snapshot is None:
                return None

            if snapshot.state is JobState.QUEUED or snapshot.state is JobState.PAUSED:
                self._paused_ids.discard(job_id)
                self._remove_from_queue(job_id)
                final = replace(
                    snapshot,
                    state=JobState.CANCELLED,
                    finished_at=_now_iso(),
                    capability=_terminal_capability(),
                )
                self._registry.put(final)
                self._condition.notify()
                return final

            if snapshot.state in (JobState.RUNNING, JobState.CANCELLING):
                event = self._cancel_events.get(job_id)
                if event is not None:
                    event.set()
                cancelling = replace(
                    snapshot,
                    state=JobState.CANCELLING,
                    capability=_running_capability(),
                )
                self._registry.put(cancelling)
                return cancelling

            return snapshot

    def pause(self, job_id: str) -> JobSnapshot | None:
        """Pause a queued job.  Running jobs cannot be paused in Sprint 16."""
        with self._lock:
            snapshot = self._registry.get(job_id)
            if snapshot is None:
                return None
            if snapshot.state is JobState.QUEUED:
                self._paused_ids.add(job_id)
                paused = replace(
                    snapshot,
                    state=JobState.PAUSED,
                    capability=_queued_capability(),
                )
                self._registry.put(paused)
                return paused
            if snapshot.state is JobState.PAUSED:
                return snapshot
            # RUNNING, CANCELLING, or terminal.
            return replace(
                snapshot,
                capability=JobCapability(
                    pause=PauseCapability.NOT_SUPPORTED,
                    cancellation=_current_cancel_capability(snapshot),
                ),
            )

    def resume(self, job_id: str) -> JobSnapshot | None:
        """Resume a paused queued job."""
        with self._lock:
            snapshot = self._registry.get(job_id)
            if snapshot is None:
                return None
            if snapshot.state is not JobState.PAUSED:
                return snapshot
            self._paused_ids.discard(job_id)
            queued = replace(
                snapshot,
                state=JobState.QUEUED,
                capability=_queued_capability(),
            )
            self._registry.put(queued)
            self._condition.notify()
            return self._registry.get(job_id)

    def _remove_from_queue(self, job_id: str) -> None:
        try:
            self._queue.remove(job_id)
        except ValueError:
            pass


def _current_cancel_capability(snapshot: JobSnapshot) -> CancellationCapability:
    if snapshot.state.value in {"queued", "paused"}:
        return CancellationCapability.BEFORE_START
    if snapshot.state.value in {"running", "cancelling"}:
        return CancellationCapability.COOPERATIVE
    return CancellationCapability.NOT_SUPPORTED


def _capture_resource_snapshot():
    """Import local helper to keep scheduler top-level lightweight."""
    from .executor import _capture_resource_snapshot as capture

    return capture()
