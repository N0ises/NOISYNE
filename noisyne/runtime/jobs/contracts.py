"""Typed/versioned contracts for the Sprint 16 async job runtime."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from noisyne.perception._serialization import JsonContract

JOB_SCHEMA_VERSION = "1.0.0"


class JobState(str, Enum):
    """Public lifecycle state of one job."""

    QUEUED = "queued"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    CANCELLING = "cancelling"


class PauseCapability(str, Enum):
    """What level of pause/resume the current job stage supports."""

    SUPPORTED = "supported"
    QUEUE_ONLY = "queue_only"
    NOT_SUPPORTED = "not_supported"


class CancellationCapability(str, Enum):
    """What level of cancellation the current job stage supports."""

    BEFORE_START = "before_start"
    COOPERATIVE = "cooperative"
    NOT_SUPPORTED = "not_supported"


class ResourceProfile(str, Enum):
    """Named resource/performance target policy for a job."""

    LOW_RESOURCE = "low_resource"
    BALANCED = "balanced"
    PERFORMANCE = "performance"


JobId = str


@dataclass(frozen=True, slots=True)
class JobError(JsonContract):
    """Bounded, transport-safe job error without stack traces or secrets."""

    code: str
    message: str
    stage_id: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.code, str) or not self.code.strip():
            raise ValueError("code must be a non-empty string")
        if not isinstance(self.message, str) or not self.message.strip():
            raise ValueError("message must be a non-empty string")
        if self.stage_id is not None and (
            not isinstance(self.stage_id, str) or not self.stage_id.strip()
        ):
            raise ValueError("stage_id must be a non-empty string or None")


@dataclass(frozen=True, slots=True)
class JobProgress(JsonContract):
    """Truthful progress: no fake percentage."""

    current_stage: str | None
    completed_stages: list[str] = field(default_factory=list)
    pending_stages: list[str] = field(default_factory=list)
    stage_states: dict[str, str] = field(default_factory=dict)
    fraction: float | None = None

    def __post_init__(self) -> None:
        if self.current_stage is not None and (
            not isinstance(self.current_stage, str) or not self.current_stage.strip()
        ):
            raise ValueError("current_stage must be a non-empty string or None")
        if not isinstance(self.completed_stages, list) or any(
            not isinstance(item, str) for item in self.completed_stages
        ):
            raise TypeError("completed_stages must be a list of strings")
        if not isinstance(self.pending_stages, list) or any(
            not isinstance(item, str) for item in self.pending_stages
        ):
            raise TypeError("pending_stages must be a list of strings")
        if not isinstance(self.stage_states, dict) or any(
            not isinstance(key, str) or not isinstance(value, str)
            for key, value in self.stage_states.items()
        ):
            raise TypeError("stage_states must be a dict of strings")
        if self.fraction is not None:
            if not isinstance(self.fraction, int | float):
                raise TypeError("fraction must be a number or None")
            if not 0.0 <= self.fraction <= 1.0:
                raise ValueError("fraction must be between 0.0 and 1.0")


@dataclass(frozen=True, slots=True)
class JobCapability(JsonContract):
    """Capabilities of the current job execution boundary."""

    pause: PauseCapability
    cancellation: CancellationCapability

    def __post_init__(self) -> None:
        if not isinstance(self.pause, PauseCapability):
            raise TypeError("pause must be a PauseCapability")
        if not isinstance(self.cancellation, CancellationCapability):
            raise TypeError("cancellation must be a CancellationCapability")


@dataclass(frozen=True, slots=True)
class ResourceSnapshot(JsonContract):
    """Optional resource observation snapshot; missing values are explicit."""

    cpu_percent: float | None = None
    ram_used_bytes: int | None = None
    ram_total_bytes: int | None = None
    gpu_name: str | None = None
    gpu_memory_used_bytes: int | None = None
    gpu_memory_total_bytes: int | None = None

    def __post_init__(self) -> None:
        for name in ("cpu_percent",):
            value = getattr(self, name)
            if value is not None:
                if not isinstance(value, int | float):
                    raise TypeError(f"{name} must be a number or None")
                if value < 0.0:
                    raise ValueError(f"{name} must be non-negative")
        for name in (
            "ram_used_bytes",
            "ram_total_bytes",
            "gpu_memory_used_bytes",
            "gpu_memory_total_bytes",
        ):
            value = getattr(self, name)
            if value is not None and not isinstance(value, int):
                raise TypeError(f"{name} must be an int or None")


@dataclass(frozen=True, slots=True)
class JobRequest(JsonContract):
    """A job-bound copy of a Sprint 15 application request plus scheduling metadata."""

    request_id: str
    operation: str
    parameters: dict[str, Any] = field(default_factory=dict)
    resource_profile: ResourceProfile = ResourceProfile.BALANCED
    device_hint: str | None = None
    schema_version: str = JOB_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if not isinstance(self.request_id, str) or not self.request_id.strip():
            raise ValueError("request_id must be a non-empty string")
        if not isinstance(self.operation, str) or not self.operation.strip():
            raise ValueError("operation must be a non-empty string")
        if not isinstance(self.parameters, dict):
            raise TypeError("parameters must be a dict")
        if not isinstance(self.resource_profile, ResourceProfile):
            raise TypeError("resource_profile must be a ResourceProfile")
        if self.device_hint is not None and (
            not isinstance(self.device_hint, str) or not self.device_hint.strip()
        ):
            raise ValueError("device_hint must be a non-empty string or None")
        if not isinstance(self.schema_version, str) or not self.schema_version.strip():
            raise ValueError("schema_version must be a non-empty string")


@dataclass(frozen=True, slots=True)
class JobResult(JsonContract):
    """Result or cancellation/failure outcome of a job."""

    status: str
    payload: dict[str, Any] | None = None
    error: JobError | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.status, str) or not self.status.strip():
            raise ValueError("status must be a non-empty string")
        if self.payload is not None and not isinstance(self.payload, dict):
            raise TypeError("payload must be a dict or None")
        if self.error is not None and not isinstance(self.error, JobError):
            raise TypeError("error must be a JobError or None")


@dataclass(frozen=True, slots=True)
class JobSnapshot(JsonContract):
    """Observable, immutable state of one job at one moment."""

    job_id: JobId
    state: JobState
    request: JobRequest
    progress: JobProgress
    capability: JobCapability
    created_at: str
    started_at: str | None = None
    finished_at: str | None = None
    result: JobResult | None = None
    error: JobError | None = None
    resource_profile: ResourceProfile = ResourceProfile.BALANCED
    resource_snapshot: ResourceSnapshot | None = None
    execution_metadata: dict[str, Any] = field(default_factory=dict)
    schema_version: str = JOB_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if not isinstance(self.job_id, str) or not self.job_id.strip():
            raise ValueError("job_id must be a non-empty string")
        if not isinstance(self.state, JobState):
            raise TypeError("state must be a JobState")
        if not isinstance(self.request, JobRequest):
            raise TypeError("request must be a JobRequest")
        if not isinstance(self.progress, JobProgress):
            raise TypeError("progress must be a JobProgress")
        if not isinstance(self.capability, JobCapability):
            raise TypeError("capability must be a JobCapability")
        if not isinstance(self.created_at, str) or not self.created_at.strip():
            raise ValueError("created_at must be a non-empty string")
        if self.started_at is not None and (
            not isinstance(self.started_at, str) or not self.started_at.strip()
        ):
            raise ValueError("started_at must be a non-empty string or None")
        if self.finished_at is not None and (
            not isinstance(self.finished_at, str) or not self.finished_at.strip()
        ):
            raise ValueError("finished_at must be a non-empty string or None")
        if self.result is not None and not isinstance(self.result, JobResult):
            raise TypeError("result must be a JobResult or None")
        if self.error is not None and not isinstance(self.error, JobError):
            raise TypeError("error must be a JobError or None")
        if not isinstance(self.resource_profile, ResourceProfile):
            raise TypeError("resource_profile must be a ResourceProfile")
        if self.resource_snapshot is not None and not isinstance(
            self.resource_snapshot, ResourceSnapshot
        ):
            raise TypeError("resource_snapshot must be a ResourceSnapshot or None")
        if not isinstance(self.execution_metadata, dict):
            raise TypeError("execution_metadata must be a dict")
        if not isinstance(self.schema_version, str) or not self.schema_version.strip():
            raise ValueError("schema_version must be a non-empty string")


__all__ = [
    "JOB_SCHEMA_VERSION",
    "CancellationCapability",
    "JobCapability",
    "JobError",
    "JobId",
    "JobProgress",
    "JobRequest",
    "JobResult",
    "JobSnapshot",
    "JobState",
    "PauseCapability",
    "ResourceProfile",
    "ResourceSnapshot",
]
