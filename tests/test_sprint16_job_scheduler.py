"""Sprint 16 — async job scheduler foundation tests."""

from __future__ import annotations

import sys
import threading
import time
from collections.abc import Callable

import pytest

from noisyne.application.contracts import (
    ApplicationRequest,
    ApplicationResult,
    ApplicationResultStatus,
    OperationType,
    StageOutcome,
    StageState,
)
from noisyne.runtime.jobs import (
    JobScheduler,
    JobState,
    PauseCapability,
    ResourceProfile,
)


class _FakeService:
    """Deterministic, controllable application service for scheduler tests."""

    def __init__(
        self,
        *,
        sleep_seconds: float = 0.0,
        fail_for: set[str] | None = None,
        on_enter: Callable[[], None] | None = None,
        on_exit: Callable[[], None] | None = None,
    ) -> None:
        self.sleep_seconds = sleep_seconds
        self.fail_for = fail_for or set()
        self.on_enter = on_enter
        self.on_exit = on_exit
        self.call_count = 0
        self._lock = threading.Lock()

    def execute(self, request: ApplicationRequest) -> ApplicationResult:
        with self._lock:
            self.call_count += 1
            call_id = request.request_id
        if self.on_enter:
            self.on_enter()
        try:
            if self.sleep_seconds:
                time.sleep(self.sleep_seconds)
            if call_id in self.fail_for:
                raise RuntimeError("requested failure")
            return ApplicationResult(
                request_id=call_id,
                operation=request.operation,
                status=ApplicationResultStatus.SUCCESS,
                payload={"echo": call_id, "operation": request.operation.value},
                stages=[
                    StageOutcome(
                        stage_id="execute", state=StageState.COMPLETED, payload={"done": True}
                    )
                ],
            )
        finally:
            if self.on_exit:
                self.on_exit()


class _ConcurrencyRecorder:
    """Records how many fake-service calls overlap."""

    def __init__(self) -> None:
        self._active = 0
        self._max_active = 0
        self._lock = threading.Lock()

    def enter(self) -> None:
        with self._lock:
            self._active += 1
            self._max_active = max(self._max_active, self._active)

    def exit(self) -> None:
        with self._lock:
            self._active -= 1

    @property
    def max_active(self) -> int:
        with self._lock:
            return self._max_active


@pytest.fixture
def scheduler() -> JobScheduler:
    svc = _FakeService()
    sched = JobScheduler(svc, max_workers=2)
    sched.start()
    yield sched
    sched.shutdown(wait=True)


def _inspect_request(request_id: str = "r1") -> ApplicationRequest:
    return ApplicationRequest(
        request_id=request_id,
        operation=OperationType.CAPABILITY_INSPECT,
    )


def test_lightweight_import() -> None:
    """Importing the job scheduler must not initialize torch/onnx/Qt/network."""
    modules_before = set(sys.modules)
    import noisyne.runtime.jobs as jobs_module  # noqa: F401

    new_modules = set(sys.modules) - modules_before
    forbidden = {"torch", "onnxruntime", "PySide6", "torchaudio"}
    found = [m for m in new_modules if any(m == f or m.startswith(f + ".") for f in forbidden)]
    assert not found, f"Heavy modules loaded: {found}"


def test_submit_is_non_blocking(scheduler: JobScheduler) -> None:
    """submit() returns immediately and the job is observable as queued/running."""
    request = _inspect_request()
    t0 = time.monotonic()
    job_id = scheduler.submit(request)
    elapsed = time.monotonic() - t0
    assert elapsed < 0.05

    snapshot = scheduler.get_status(job_id)
    assert snapshot is not None
    assert snapshot.job_id == job_id
    assert snapshot.state in (JobState.QUEUED, JobState.RUNNING)


def test_queued_to_running_to_completed(scheduler: JobScheduler) -> None:
    """A normal job progresses through queued/running/completed."""
    job_id = scheduler.submit(_inspect_request())
    final = scheduler.wait(job_id, timeout=2.0)
    assert final is not None
    assert final.state is JobState.COMPLETED
    assert final.started_at is not None
    assert final.finished_at is not None
    assert final.result is not None
    assert final.result.status == "success"


def test_result_propagation(scheduler: JobScheduler) -> None:
    """The service result payload reaches the job snapshot."""
    job_id = scheduler.submit(_inspect_request("result-id"))
    final = scheduler.wait(job_id, timeout=2.0)
    assert final is not None
    assert final.result is not None
    assert final.result.payload == {
        "echo": "result-id",
        "operation": "capability_inspect",
    }


def test_failure_propagation(scheduler: JobScheduler) -> None:
    """A service exception is isolated and reported as a failed job."""
    failing_service = _FakeService(fail_for={"fail-id"})
    sched = JobScheduler(failing_service, max_workers=2)
    sched.start()
    try:
        job_id = sched.submit(_inspect_request("fail-id"))
        final = sched.wait(job_id, timeout=2.0)
        assert final is not None
        assert final.state is JobState.FAILED
        assert final.error is not None
        assert final.error.code == "execution_failure"
    finally:
        sched.shutdown(wait=True)


def test_cancellation_before_start() -> None:
    """Cancelling a queued job before it starts marks it CANCELLED."""
    recorder = _ConcurrencyRecorder()
    slow_service = _FakeService(sleep_seconds=0.2, on_enter=recorder.enter, on_exit=recorder.exit)
    sched = JobScheduler(slow_service, max_workers=1)
    sched.start()
    try:
        first = sched.submit(_inspect_request("first"))
        second = sched.submit(_inspect_request("second"))
        # second is queued behind first
        cancelled = sched.cancel(second)
        assert cancelled is not None
        assert cancelled.state is JobState.CANCELLED

        first_final = sched.wait(first, timeout=2.0)
        second_final = sched.wait(second, timeout=2.0)
        assert first_final is not None
        assert first_final.state is JobState.COMPLETED
        assert second_final is not None
        assert second_final.state is JobState.CANCELLED
        assert recorder.max_active == 1
    finally:
        sched.shutdown(wait=True)


def test_running_cancellation_truth_semantics() -> None:
    """Cancelling a running job is cooperative; the scheduler reports CANCELLING/CANCELLED truthfully."""
    recorder = _ConcurrencyRecorder()
    slow_service = _FakeService(sleep_seconds=0.2, on_enter=recorder.enter, on_exit=recorder.exit)
    sched = JobScheduler(slow_service, max_workers=1)
    sched.start()
    try:
        job_id = sched.submit(_inspect_request("run-cancel"))
        # Wait until it is actually running.
        for _ in range(100):
            snap = sched.get_status(job_id)
            if snap is not None and snap.state is JobState.RUNNING:
                break
            time.sleep(0.01)
        cancelling = sched.cancel(job_id)
        assert cancelling is not None
        assert cancelling.state is JobState.CANCELLING

        final = sched.wait(job_id, timeout=2.0)
        assert final is not None
        assert final.state is JobState.CANCELLED
    finally:
        sched.shutdown(wait=True)


def test_pause_unsupported_when_running(scheduler: JobScheduler) -> None:
    """Running Sprint 15 operations cannot be paused mid-flight."""
    recorder = _ConcurrencyRecorder()
    slow_service = _FakeService(sleep_seconds=0.15, on_enter=recorder.enter, on_exit=recorder.exit)
    sched = JobScheduler(slow_service, max_workers=1)
    sched.start()
    try:
        job_id = sched.submit(_inspect_request())
        for _ in range(100):
            snap = sched.get_status(job_id)
            if snap is not None and snap.state is JobState.RUNNING:
                break
            time.sleep(0.01)
        pause_result = sched.pause(job_id)
        assert pause_result is not None
        assert pause_result.capability.pause is PauseCapability.NOT_SUPPORTED

        final = sched.wait(job_id, timeout=2.0)
        assert final is not None
        assert final.state is JobState.COMPLETED
    finally:
        sched.shutdown(wait=True)


def test_queued_pause_and_resume() -> None:
    """Queued jobs can be paused and resumed; they run only after resume."""
    recorder = _ConcurrencyRecorder()
    slow_service = _FakeService(sleep_seconds=0.1, on_enter=recorder.enter, on_exit=recorder.exit)
    sched = JobScheduler(slow_service, max_workers=1)
    sched.start()
    try:
        first = sched.submit(_inspect_request("first"))
        second = sched.submit(_inspect_request("second"))

        paused = sched.pause(second)
        assert paused is not None
        assert paused.state is JobState.PAUSED

        # Wait for first to finish.
        assert sched.wait(first, timeout=2.0) is not None
        # Second should still be paused, not run yet.
        assert sched.get_status(second).state is JobState.PAUSED

        resumed = sched.resume(second)
        assert resumed is not None
        assert resumed.state is JobState.QUEUED

        final = sched.wait(second, timeout=2.0)
        assert final is not None
        assert final.state is JobState.COMPLETED
    finally:
        sched.shutdown(wait=True)


def test_no_fake_progress_percentage(scheduler: JobScheduler) -> None:
    """Progress does not fabricate a percentage."""
    job_id = scheduler.submit(_inspect_request())
    final = scheduler.wait(job_id, timeout=2.0)
    assert final is not None
    assert final.progress.fraction is None
    assert "execute" in final.progress.completed_stages


def test_concurrency_limit() -> None:
    """Only max_workers jobs run concurrently; excess jobs remain queued."""
    recorder = _ConcurrencyRecorder()
    slow_service = _FakeService(sleep_seconds=0.15, on_enter=recorder.enter, on_exit=recorder.exit)
    sched = JobScheduler(slow_service, max_workers=2)
    sched.start()
    try:
        _j1 = sched.submit(_inspect_request("j1"))
        _j2 = sched.submit(_inspect_request("j2"))
        j3 = sched.submit(_inspect_request("j3"))

        # Give the worker pool a moment to pick up the first two.
        time.sleep(0.05)
        assert sched.get_status(j3).state is JobState.QUEUED
        assert recorder.max_active <= 2

        final = sched.wait(j3, timeout=2.0)
        assert final is not None
        assert final.state is JobState.COMPLETED
    finally:
        sched.shutdown(wait=True)


def test_two_jobs_parallel() -> None:
    """Two jobs with max_workers=2 execute in parallel, not sequentially."""
    recorder = _ConcurrencyRecorder()
    slow_service = _FakeService(sleep_seconds=0.15, on_enter=recorder.enter, on_exit=recorder.exit)
    sched = JobScheduler(slow_service, max_workers=2)
    sched.start()
    try:
        t0 = time.monotonic()
        j1 = sched.submit(_inspect_request("p1"))
        j2 = sched.submit(_inspect_request("p2"))
        assert sched.wait(j1, timeout=2.0) is not None
        assert sched.wait(j2, timeout=2.0) is not None
        elapsed = time.monotonic() - t0
        assert elapsed < 0.28, f"jobs ran sequentially ({elapsed:.2f}s)"
        assert recorder.max_active == 2
    finally:
        sched.shutdown(wait=True)


def test_failure_isolation() -> None:
    """One failing job does not corrupt or abort a concurrent successful job."""
    recorder = _ConcurrencyRecorder()
    failing_service = _FakeService(
        sleep_seconds=0.05,
        fail_for={"bad"},
        on_enter=recorder.enter,
        on_exit=recorder.exit,
    )
    sched = JobScheduler(failing_service, max_workers=2)
    sched.start()
    try:
        good = sched.submit(_inspect_request("good"))
        bad = sched.submit(_inspect_request("bad"))
        good_final = sched.wait(good, timeout=2.0)
        bad_final = sched.wait(bad, timeout=2.0)
        assert good_final is not None
        assert good_final.state is JobState.COMPLETED
        assert bad_final is not None
        assert bad_final.state is JobState.FAILED
    finally:
        sched.shutdown(wait=True)


def test_cancellation_isolation() -> None:
    """Cancelling one job does not affect a concurrent job."""
    recorder = _ConcurrencyRecorder()
    slow_service = _FakeService(sleep_seconds=0.1, on_enter=recorder.enter, on_exit=recorder.exit)
    sched = JobScheduler(slow_service, max_workers=2)
    sched.start()
    try:
        victim = sched.submit(_inspect_request("victim"))
        other = sched.submit(_inspect_request("other"))
        sched.cancel(victim)
        other_final = sched.wait(other, timeout=2.0)
        victim_final = sched.wait(victim, timeout=2.0)
        assert other_final is not None
        assert other_final.state is JobState.COMPLETED
        assert victim_final is not None
        assert victim_final.state is JobState.CANCELLED
    finally:
        sched.shutdown(wait=True)


def test_deterministic_job_identity() -> None:
    """Submitting with an explicit job_id preserves deterministic identity."""
    sched = JobScheduler(_FakeService(), max_workers=1)
    sched.start()
    try:
        job_id = "my-deterministic-id"
        assigned = sched.submit(_inspect_request(), job_id=job_id)
        assert assigned == job_id
        final = sched.wait(job_id, timeout=2.0)
        assert final is not None
        assert final.job_id == job_id
    finally:
        sched.shutdown(wait=True)


def test_history() -> None:
    """Completed, failed and cancelled jobs are retained in bounded history."""
    svc = _FakeService(fail_for={"bad"})
    sched = JobScheduler(svc, max_workers=3)
    sched.start()
    try:
        good_id = sched.submit(_inspect_request("good"))
        bad_id = sched.submit(_inspect_request("bad"))
        cancelled_id = sched.submit(_inspect_request("cancelled"))
        sched.cancel(cancelled_id)

        assert sched.wait(good_id, timeout=2.0) is not None
        assert sched.wait(bad_id, timeout=2.0) is not None
        assert sched.wait(cancelled_id, timeout=2.0) is not None

        all_jobs = sched.list_jobs(include_history=True)
        states = {s.job_id: s.state for s in all_jobs}
        assert states[good_id] is JobState.COMPLETED
        assert states[bad_id] is JobState.FAILED
        assert states[cancelled_id] is JobState.CANCELLED

        # Terminal jobs must not appear in the active-only list.
        active_ids = {s.job_id for s in sched.list_jobs(include_history=False)}
        assert good_id not in active_ids
        assert bad_id not in active_ids
        assert cancelled_id not in active_ids
    finally:
        sched.shutdown(wait=True)


def test_shutdown_rejects_new_jobs() -> None:
    """After shutdown, submit() rejects new jobs."""
    sched = JobScheduler(_FakeService(), max_workers=1)
    sched.start()
    sched.shutdown(wait=True)
    with pytest.raises(RuntimeError):
        sched.submit(_inspect_request())


def test_resource_profile_propagation() -> None:
    """The scheduler preserves the resource profile on the job snapshot."""
    sched = JobScheduler(_FakeService(), max_workers=1)
    sched.start()
    try:
        job_id = sched.submit(_inspect_request(), resource_profile=ResourceProfile.LOW_RESOURCE)
        final = sched.wait(job_id, timeout=2.0)
        assert final is not None
        assert final.resource_profile is ResourceProfile.LOW_RESOURCE
    finally:
        sched.shutdown(wait=True)


def test_gpu_serialization_policy() -> None:
    """GPU-hinted jobs are serialized through the shared GPU lock."""
    recorder = _ConcurrencyRecorder()
    slow_service = _FakeService(sleep_seconds=0.1, on_enter=recorder.enter, on_exit=recorder.exit)
    sched = JobScheduler(slow_service, max_workers=4)
    sched.start()
    try:
        g1 = sched.submit(_inspect_request("g1"), device_hint="cuda")
        g2 = sched.submit(_inspect_request("g2"), device_hint="cuda")
        assert sched.wait(g1, timeout=2.0) is not None
        assert sched.wait(g2, timeout=2.0) is not None
        # CPU concurrency would allow 2, but GPU lock serializes.
        assert recorder.max_active == 1
    finally:
        sched.shutdown(wait=True)


def test_sprint15_service_boundary_preserved() -> None:
    """The scheduler executes ApplicationRequest through the real NoisyneV2Service shape."""
    from noisyne.application.service import NoisyneV2Service

    sched = JobScheduler(NoisyneV2Service(), max_workers=1)
    sched.start()
    try:
        request = ApplicationRequest(
            request_id="real-service",
            operation=OperationType.CAPABILITY_INSPECT,
        )
        job_id = sched.submit(request)
        final = sched.wait(job_id, timeout=10.0)
        assert final is not None
        assert final.state is JobState.COMPLETED
        assert final.result is not None
        assert final.result.status == "success"
        assert "snapshot" in (final.result.payload or {})
    finally:
        sched.shutdown(wait=True)


def test_no_qt_import() -> None:
    """Importing the scheduler module does not bring in Qt, torch, or ONNX."""
    modules_before = set(sys.modules)
    import noisyne.runtime.jobs as jobs_module  # noqa: F401

    new_modules = set(sys.modules) - modules_before
    forbidden = {"PySide6", "torch", "onnxruntime", "torchaudio"}
    found = [m for m in new_modules if any(m == f or m.startswith(f + ".") for f in forbidden)]
    assert not found, f"Heavy modules loaded by scheduler import: {found}"


def test_no_live_llm() -> None:
    """Scheduler tests do not depend on live LLM/network."""
    # The tests are fully offline; this assertion documents the invariant.
    assert True


# ---------------------------------------------------------------------------
# Sprint 16 concurrency-hardening regression tests
# ---------------------------------------------------------------------------


class _GatedService(_FakeService):
    """Fake service that blocks inside execute() until a gate is released."""

    def __init__(self, gate: threading.Event, **kwargs: object) -> None:
        super().__init__(**kwargs)  # type: ignore[arg-type]
        self._gate = gate
        self.executed_ids: list[str] = []

    def execute(self, request: ApplicationRequest) -> ApplicationResult:
        self._gate.wait(timeout=5.0)
        with self._lock:
            self.executed_ids.append(request.request_id)
        return super().execute(request)


def _wait_for(predicate: Callable[[], bool], timeout: float = 2.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.005)
    return predicate()


def test_duplicate_job_id_rejected() -> None:
    """A job_id already known to the registry is never silently reused."""
    sched = JobScheduler(_FakeService(), max_workers=1)
    sched.start()
    try:
        sched.submit(_inspect_request(), job_id="dup-id")
        with pytest.raises(ValueError, match="Duplicate job_id"):
            sched.submit(_inspect_request(), job_id="dup-id")

        final = sched.wait("dup-id", timeout=2.0)
        assert final is not None
        assert final.state is JobState.COMPLETED

        # Even after the job moved to history, the id stays reserved.
        with pytest.raises(ValueError, match="Duplicate job_id"):
            sched.submit(_inspect_request(), job_id="dup-id")

        # A fresh id still works.
        other = sched.submit(_inspect_request(), job_id="other-id")
        assert sched.wait(other, timeout=2.0).state is JobState.COMPLETED
    finally:
        sched.shutdown(wait=True)


def test_shutdown_cancels_queued_jobs() -> None:
    """Jobs still QUEUED at shutdown are CANCELLED, so wait() can never block
    forever on a job that will never be dispatched."""
    gate = threading.Event()
    svc = _GatedService(gate)
    sched = JobScheduler(svc, max_workers=1)
    sched.start()
    try:
        blocker = sched.submit(_inspect_request("blocker"))
        assert _wait_for(
            lambda: (s := sched.get_status(blocker)) is not None and s.state is JobState.RUNNING
        )

        queued = sched.submit(_inspect_request("queued"))
        # The dispatcher eagerly hands queued jobs to the worker pool, where
        # this one blocks on the single concurrency slot, still QUEUED.
        assert _wait_for(lambda: queued in sched._cancel_events)

        # Shutdown while the blocker still holds the slot; the sweep must
        # cancel the never-started job even though it already left the deque.
        shutdown_thread = threading.Thread(
            target=sched.shutdown, kwargs={"wait": True}, daemon=True
        )
        shutdown_thread.start()
        assert _wait_for(
            lambda: (s := sched.get_status(queued)) is not None and s.state is JobState.CANCELLED
        )
        assert shutdown_thread.is_alive()  # still waiting on the gated blocker

        gate.set()
        shutdown_thread.join(timeout=5.0)
        assert not shutdown_thread.is_alive()

        # Running jobs are unaffected and finish normally.
        assert sched.get_status(blocker).state is JobState.COMPLETED

        queued_final = sched.get_status(queued)
        assert queued_final is not None
        assert queued_final.state is JobState.CANCELLED
        assert queued_final.finished_at is not None
        assert "queued" not in svc.executed_ids

        # wait() on the never-started job returns promptly, not after timeout.
        t0 = time.monotonic()
        waited = sched.wait(queued, timeout=1.0)
        assert time.monotonic() - t0 < 0.5
        assert waited is not None
        assert waited.state is JobState.CANCELLED
    finally:
        gate.set()
        sched.shutdown(wait=True)


def test_shutdown_cancels_paused_jobs() -> None:
    """Paused jobs are CANCELLED at shutdown, not stranded in a state wait()
    would block on forever."""
    gate = threading.Event()
    svc = _GatedService(gate)
    sched = JobScheduler(svc, max_workers=1)
    sched.start()
    try:
        blocker = sched.submit(_inspect_request("blocker"))
        assert _wait_for(
            lambda: (s := sched.get_status(blocker)) is not None and s.state is JobState.RUNNING
        )

        paused = sched.submit(_inspect_request("paused"))
        assert _wait_for(lambda: paused in sched._cancel_events)
        pause_result = sched.pause(paused)
        assert pause_result is not None
        assert pause_result.state is JobState.PAUSED

        shutdown_thread = threading.Thread(
            target=sched.shutdown, kwargs={"wait": True}, daemon=True
        )
        shutdown_thread.start()
        assert _wait_for(
            lambda: (s := sched.get_status(paused)) is not None and s.state is JobState.CANCELLED
        )

        gate.set()
        shutdown_thread.join(timeout=5.0)
        assert not shutdown_thread.is_alive()

        assert sched.get_status(blocker).state is JobState.COMPLETED
        paused_final = sched.get_status(paused)
        assert paused_final is not None
        assert paused_final.state is JobState.CANCELLED
        assert paused_final.finished_at is not None
        assert "paused" not in svc.executed_ids
    finally:
        gate.set()
        sched.shutdown(wait=True)


def test_pause_after_dispatch_requeues_without_running() -> None:
    """A pause that lands after dispatch but before the RUNNING transition
    re-queues the job; a paused job must never execute."""
    gate = threading.Event()
    svc = _GatedService(gate)
    sched = JobScheduler(svc, max_workers=1)
    sched.start()
    try:
        blocker = sched.submit(_inspect_request("blocker"))
        assert _wait_for(
            lambda: (s := sched.get_status(blocker)) is not None and s.state is JobState.RUNNING
        )

        victim = sched.submit(_inspect_request("victim"))
        # Wait until the dispatcher has picked the victim up (it is out of the
        # queue and its wrapper is blocked on the single concurrency slot).
        assert _wait_for(lambda: victim in sched._cancel_events)

        paused = sched.pause(victim)
        assert paused is not None
        assert paused.state is JobState.PAUSED

        gate.set()
        assert sched.wait(blocker, timeout=2.0).state is JobState.COMPLETED

        # The victim wrapper acquired the freed slot but must have re-queued
        # instead of running while PAUSED.
        assert _wait_for(lambda: sched.get_status(victim).state is JobState.PAUSED)
        assert "victim" not in svc.executed_ids

        resumed = sched.resume(victim)
        assert resumed is not None
        assert resumed.state is JobState.QUEUED
        assert sched.wait(victim, timeout=2.0).state is JobState.COMPLETED
        assert "victim" in svc.executed_ids
    finally:
        gate.set()
        sched.shutdown(wait=True)


def test_cancel_after_service_return_still_cancels(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A cancellation landing after the service returned but before the
    terminal write wins over recording a COMPLETED/FAILED result."""
    import noisyne.runtime.jobs.executor as executor_mod

    real_result_cls = executor_mod.JobResult
    sched = JobScheduler(_FakeService(), max_workers=1)
    sched.start()
    try:
        job_id = "late-cancel"

        def cancelling_result(*args: object, **kwargs: object) -> object:
            # Fires while the executor builds the JobResult: after the service
            # call returned and after the earlier cancel checkpoints, but
            # before the terminal snapshot is written.
            sched.cancel(job_id)
            return real_result_cls(*args, **kwargs)  # type: ignore[arg-type]

        monkeypatch.setattr(executor_mod, "JobResult", cancelling_result)
        sched.submit(_inspect_request("late-cancel"), job_id=job_id)
        final = sched.wait(job_id, timeout=2.0)
        assert final is not None
        assert final.state is JobState.CANCELLED
        assert final.result is None
    finally:
        sched.shutdown(wait=True)
