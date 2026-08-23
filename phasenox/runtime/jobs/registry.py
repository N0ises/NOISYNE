"""In-memory job registry with bounded history for Sprint 16."""

from __future__ import annotations

import threading
from collections import deque

from .contracts import JobSnapshot


class JobHistory:
    """Bounded, ordered view of completed job snapshots."""

    def __init__(self, max_size: int = 100) -> None:
        if not isinstance(max_size, int) or max_size < 1:
            raise ValueError("max_size must be a positive integer")
        self._max_size = max_size
        self._order: deque[str] = deque(maxlen=max_size)
        self._entries: dict[str, JobSnapshot] = {}
        self._lock = threading.Lock()

    def append(self, snapshot: JobSnapshot) -> None:
        with self._lock:
            if snapshot.job_id in self._entries:
                self._order.remove(snapshot.job_id)
            elif len(self._order) == self._max_size:
                oldest = self._order.popleft()
                self._entries.pop(oldest, None)
            self._order.append(snapshot.job_id)
            self._entries[snapshot.job_id] = snapshot

    def list(self) -> list[JobSnapshot]:
        with self._lock:
            return [self._entries[job_id] for job_id in self._order]

    def get(self, job_id: str) -> JobSnapshot | None:
        with self._lock:
            return self._entries.get(job_id)


class JobRegistry:
    """Thread-safe in-memory store for active and historical jobs."""

    def __init__(self, max_history: int = 100) -> None:
        self._jobs: dict[str, JobSnapshot] = {}
        self._history = JobHistory(max_size=max_history)
        self._lock = threading.RLock()

    def put(self, snapshot: JobSnapshot) -> None:
        with self._lock:
            self._jobs[snapshot.job_id] = snapshot
            if snapshot.state.value in {"completed", "failed", "cancelled"}:
                self._history.append(snapshot)
                # Terminal snapshots live only in history so that the active
                # list does not report completed work as still active.
                self._jobs.pop(snapshot.job_id, None)

    def get(self, job_id: str) -> JobSnapshot | None:
        with self._lock:
            active = self._jobs.get(job_id)
            if active is not None:
                return active
            return self._history.get(job_id)

    def list_active(self) -> list[JobSnapshot]:
        with self._lock:
            return list(self._jobs.values())

    def list_all(self) -> list[JobSnapshot]:
        with self._lock:
            active = list(self._jobs.values())
            historical = self._history.list()
            active_ids = {s.job_id for s in active}
            return active + [s for s in historical if s.job_id not in active_ids]

    def list_history(self) -> list[JobSnapshot]:
        with self._lock:
            return self._history.list()

    def pop_active(self, job_id: str) -> JobSnapshot | None:
        with self._lock:
            return self._jobs.pop(job_id, None)
