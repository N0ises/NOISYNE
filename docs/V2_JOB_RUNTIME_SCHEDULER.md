# V2 Job Runtime / Scheduler Foundation

Sprint 16 introduces the backend async job runtime that wraps the Sprint 15
`PhasenoxV2Service` operations. It provides queueing, bounded concurrency,
cooperative cancellation, truthful progress, and bounded history without
implementing any Desktop UI, Task Center, or production model changes.

This is a **foundation-only** sprint: the public contracts are stable, but the
scheduler is in-memory and does not yet persist jobs or integrate with the
Desktop V2 adapter.

---

## 1. Architecture

```text
noisyne/runtime/jobs/
    contracts.py   # JobState, JobSnapshot, JobRequest, JobResult, etc.
    registry.py    # in-memory JobRegistry + bounded JobHistory
    executor.py    # JobExecutor: runs one PhasenoxV2Service call
    scheduler.py   # JobScheduler: queue, dispatch, cancel, pause, wait
```

- `JobScheduler` owns a small `ThreadPoolExecutor` and a dedicated dispatcher
  thread.
- The dispatcher maintains a scheduler-level queue so that `QUEUED` reflects
  back-pressure under the configured concurrency policy, not merely the
  internal thread-pool queue.
- `JobExecutor` translates a Sprint 15 `ApplicationRequest` into a `JobResult`
  and records per-stage outcomes.
- Heavy imports (`torch`, `onnxruntime`, Qt, audio devices) are deferred until
  a job actually runs; importing `noisyne.runtime.jobs` remains lightweight.

---

## 2. Job Lifecycle

```text
QUEUED -> RUNNING -> COMPLETED
              \
               -> FAILED
               -> CANCELLED
               -> CANCELLING -> CANCELLED

QUEUED <-> PAUSED
```

| State       | Meaning |
|-------------|---------|
| `QUEUED`    | Submitted, waiting for a concurrency slot. |
| `RUNNING`   | Acquired a slot and the service call is in progress. |
| `PAUSED`    | Queue-only pause; the job will not run until resumed. |
| `COMPLETED` | Service finished successfully (or `PARTIAL` was returned). |
| `FAILED`    | Service reported failure or an unhandled error was caught. |
| `CANCELLED` | Cancelled before start or after cooperative termination. |
| `CANCELLING`| Cooperatively cancelled; waiting for the running stage to observe the event. |

Terminal states: `COMPLETED`, `FAILED`, `CANCELLED`.

---

## 3. Queue & Concurrency

- `JobScheduler.start()` creates the worker pool and dispatcher thread.
- `submit()` returns immediately with a `JobSnapshot` in `QUEUED` state.
- The dispatcher pops one `QUEUED`, non-paused job at a time and submits it to
  the thread pool. The worker then acquires a concurrency slot before marking
  the job `RUNNING`.
- `max_workers` defaults to the active resource profile:
  - `LOW_RESOURCE`: 1 concurrent job.
  - `BALANCED`: 2 concurrent jobs.
  - `PERFORMANCE`: `max(2, cpu_count // 2)`.
- The active-only job list never contains terminal jobs; completed/failed/
  cancelled jobs move to bounded history.

---

## 4. Cancellation Semantics

Cancellation is truthful and stage-aware:

- **Before start (`QUEUED` / `PAUSED`)**: the job becomes `CANCELLED`
  immediately and is removed from the dispatch queue.
- **While running**: the scheduler records `CANCELLING` and sets a
  `threading.Event`. The `JobExecutor` checks the event before and after the
  service call. Sprint 15 operations are treated as atomic/non-checkpointable,
  so the call itself cannot be forcibly interrupted; the job becomes
  `CANCELLED` once the stage exits.
- Jobs in terminal states cannot be cancelled.

`CancellationCapability` values:

- `BEFORE_START` — queued/paused jobs.
- `COOPERATIVE` — running/cancelling jobs.
- `NOT_SUPPORTED` — terminal jobs.

---

## 5. Pause / Resume Truth

Pause is **queue-only** in Sprint 16.

- A `QUEUED` job can be paused; it becomes `PAUSED` and is skipped by the
  dispatcher.
- A `PAUSED` job can be resumed; it returns to `QUEUED` and becomes eligible
  for dispatch.
- `RUNNING` Sprint 15 operations are atomic and cannot be checkpointed.
  Calling `pause()` on a running job returns a snapshot whose capability says
  `NOT_SUPPORTED` while leaving the job running.

No work continues while a job is `PAUSED`.

---

## 6. Progress Semantics

Progress does **not** fabricate a percentage.

`JobProgress` contains:

- `current_stage` — the stage currently in progress, if any.
- `completed_stages` — ordered list of finished stage ids.
- `pending_stages` — stages still to run.
- `stage_states` — per-stage state values from the Sprint 15 service.
- `fraction` — **only populated when mathematically justified**; otherwise
  `None`.

For the Sprint 16 foundation, each job executes a single "execute" stage, so
`fraction` remains `None`. Future long-running workflows may provide stage
counts that allow a fraction to be computed.

---

## 7. Resource Policy

`ResourceProfile` is scheduling metadata, not a guarantee of hardware.

- `LOW_RESOURCE` — CPU-only assumption, conservative concurrency (1), no
  GPU, cold-start sensitive.
- `BALANCED` — default policy, moderate concurrency (2).
- `PERFORMANCE` — higher concurrency, may request GPU unless `device_hint`
  is `cpu`.

GPU jobs acquire a single shared scheduler-level GPU lock, serializing GPU
execution regardless of CPU concurrency. This prevents unsafe unrestricted GPU
concurrency in Sprint 16.

Resource observations (`ResourceSnapshot`) are best-effort readings of process
RSS, total RAM, and GPU memory where `psutil` / `torch` are available. They
are **not** guaranteed peak measurements.

---

## 8. Failure Isolation

- A single job failure is caught by `JobExecutor` and recorded as `FAILED`
  with a bounded `JobError`; it does not crash the scheduler or other jobs.
- Unhandled scheduler errors are logged and the job is marked `FAILED`.
- One job's cancellation does not affect concurrently running jobs.
- Worker pool shutdown waits for running jobs (unless `wait=False`).

---

## 9. History

`JobRegistry` keeps an in-memory, bounded history of terminal jobs (default
100 entries). History is queryable via `list_jobs(include_history=True)`. The
bounded deque evicts oldest entries automatically. There is no persistence in
Sprint 16.

---

## 10. Public API

```python
from noisyne.runtime.jobs import (
    JobScheduler,
    JobState,
    ResourceProfile,
    PauseCapability,
    CancellationCapability,
)
from noisyne.application import PhasenoxV2Service, ApplicationRequest, OperationType

scheduler = JobScheduler(PhasenoxV2Service(), max_workers=2)
scheduler.start()
job_id = scheduler.submit(
    ApplicationRequest(request_id="demo", operation=OperationType.CAPABILITY_INSPECT),
    resource_profile=ResourceProfile.BALANCED,
)
snapshot = scheduler.wait(job_id, timeout=10.0)
print(snapshot.state)  # JobState.COMPLETED
scheduler.shutdown(wait=True)
```

`JobScheduler` also accepts a callable factory instead of a service instance,
which is useful when each worker thread needs its own service instance.

---

## 11. Lightweight Import Guarantee

Importing `noisyne.runtime.jobs` does **not** initialize:

- torch
- onnxruntime sessions
- LLM clients
- Qt
- audio devices
- network

Heavy imports happen only inside the worker when a job actually executes.

---

## 12. Future Desktop Task Center Boundary

Sprint 16 is the **backend foundation**. The following remain future work:

- Desktop Task Center UI.
- Pause/resume UI for atomic operations (requires checkpointable workflows).
- Persistent job store / database.
- Cross-process task distribution.
- Resource monitor UI.
- Automatic model download / installer integration.
- Async I/O scheduler, cancellation of arbitrary blocking DSP/model calls.

The Desktop adapter will consume `JobScheduler` via these contracts without
bypassing the Sprint 15 service boundary.

---

## 13. Non-Goals

Sprint 16 does **not**:

- modify `desktop-ui`.
- add a UI.
- rename the product.
- convert production models to ONNX.
- add live LLM / LM Studio / Qwen integration.
- add generation, voice AI, Ableton bridge, or C++ components.
- implement the model downloader, installer, or path manager.
