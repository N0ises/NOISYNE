"""Qt-free Task Center presentation state."""

from __future__ import annotations

from dataclasses import dataclass

from .job_gateway import DesktopJobSnapshot

_ACTIVE_STATES = frozenset({"queued", "paused", "running", "cancelling"})


@dataclass(frozen=True, slots=True)
class TaskCenterState:
    jobs: tuple[DesktopJobSnapshot, ...] = ()

    @property
    def active_jobs(self) -> tuple[DesktopJobSnapshot, ...]:
        return tuple(job for job in self.jobs if job.state in _ACTIVE_STATES)

    @property
    def history(self) -> tuple[DesktopJobSnapshot, ...]:
        return tuple(job for job in self.jobs if job.state not in _ACTIVE_STATES)

    @property
    def summary(self) -> str:
        count = len(self.active_jobs)
        return "No active tasks" if count == 0 else f"{count} active task{'s' if count != 1 else ''}"

    def find(self, job_id: str) -> DesktopJobSnapshot | None:
        return next((job for job in self.jobs if job.job_id == job_id), None)


__all__ = ["TaskCenterState"]
