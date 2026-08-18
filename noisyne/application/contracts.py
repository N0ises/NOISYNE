"""Sprint 15 V2 application service contracts.

Public request/result contracts are deterministic, JSON-safe, and free of Qt,
DAW, prompt, secret, or chain-of-thought types.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from noisyne.perception._serialization import JsonContract

APPLICATION_SCHEMA_VERSION = "1.0.0"


class OperationType(str, Enum):
    """Bounded set of V2 application operations."""

    ANALYZE = "analyze"
    REFERENCE_COMPARE = "reference_compare"
    MIX_EVALUATE = "mix_evaluate"
    REASON = "reason"
    CAPABILITY_INSPECT = "capability_inspect"


class ApplicationResultStatus(str, Enum):
    """Top-level outcome of one application operation."""

    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"


class StageState(str, Enum):
    """Lifecycle state of one stage inside an operation."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    SKIPPED = "skipped"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class StageOutcome(JsonContract):
    """Result of one named processing stage."""

    stage_id: str
    state: StageState
    payload: dict[str, Any] | None = None
    limitations: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not isinstance(self.stage_id, str) or not self.stage_id.strip():
            raise ValueError("stage_id must be a non-empty string")
        if not isinstance(self.state, StageState):
            raise TypeError("state must be a StageState")
        if self.payload is not None and not isinstance(self.payload, dict):
            raise TypeError("payload must be a dict or None")
        if not isinstance(self.limitations, list) or any(
            not isinstance(item, str) for item in self.limitations
        ):
            raise TypeError("limitations must be a list of strings")


@dataclass(frozen=True, slots=True)
class ApplicationRequest(JsonContract):
    """A single V2 application request with operation-specific parameters."""

    request_id: str
    operation: OperationType
    parameters: dict[str, Any] = field(default_factory=dict)
    schema_version: str = APPLICATION_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if not isinstance(self.request_id, str) or not self.request_id.strip():
            raise ValueError("request_id must be a non-empty string")
        if not isinstance(self.operation, OperationType):
            raise TypeError("operation must be an OperationType")
        if not isinstance(self.parameters, dict):
            raise TypeError("parameters must be a dict")
        if not isinstance(self.schema_version, str) or not self.schema_version.strip():
            raise ValueError("schema_version must be a non-empty string")
        self._validate_operation_parameters()

    def _validate_operation_parameters(self) -> None:
        params = self.parameters
        if self.operation is OperationType.ANALYZE:
            if "audio_path" not in params:
                raise ValueError("ANALYZE requires audio_path parameter")
        elif self.operation is OperationType.REFERENCE_COMPARE:
            for required in ("audio_path", "reference_path", "reference_identity"):
                if required not in params:
                    raise ValueError(f"REFERENCE_COMPARE requires {required} parameter")
        elif self.operation is OperationType.MIX_EVALUATE:
            if "mix_policy" not in params:
                raise ValueError("MIX_EVALUATE requires mix_policy parameter")
        elif self.operation is OperationType.REASON:
            if "mix_policy" not in params:
                raise ValueError("REASON requires mix_policy parameter")
        elif self.operation is OperationType.CAPABILITY_INSPECT:
            pass


@dataclass(frozen=True, slots=True)
class ApplicationError(JsonContract):
    """Bounded, transport-safe application error without stack traces or secrets."""

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
class ApplicationResult(JsonContract):
    """Result of one V2 application operation."""

    request_id: str
    operation: OperationType
    status: ApplicationResultStatus
    payload: dict[str, Any] | None = None
    stages: list[StageOutcome] = field(default_factory=list)
    errors: list[ApplicationError] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)
    schema_version: str = APPLICATION_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if not isinstance(self.request_id, str) or not self.request_id.strip():
            raise ValueError("request_id must be a non-empty string")
        if not isinstance(self.operation, OperationType):
            raise TypeError("operation must be an OperationType")
        if not isinstance(self.status, ApplicationResultStatus):
            raise TypeError("status must be an ApplicationResultStatus")
        if self.payload is not None and not isinstance(self.payload, dict):
            raise TypeError("payload must be a dict or None")
        if not isinstance(self.stages, list) or any(
            not isinstance(item, StageOutcome) for item in self.stages
        ):
            raise TypeError("stages must be a list of StageOutcome")
        if not isinstance(self.errors, list) or any(
            not isinstance(item, ApplicationError) for item in self.errors
        ):
            raise TypeError("errors must be a list of ApplicationError")
        if not isinstance(self.limitations, list) or any(
            not isinstance(item, str) for item in self.limitations
        ):
            raise TypeError("limitations must be a list of strings")


class MachineAvailability(str, Enum):
    """Machine-level availability of a declared capability dependency."""

    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class CapabilitySnapshotEntry(JsonContract):
    """One capability plus its machine-level dependency availability."""

    name: str
    lifecycle_status: str
    tested_in_freeze: bool
    dependency_availability: MachineAvailability
    reason_unavailable: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("name must be a non-empty string")
        if not isinstance(self.lifecycle_status, str):
            raise TypeError("lifecycle_status must be a string")
        if type(self.tested_in_freeze) is not bool:
            raise TypeError("tested_in_freeze must be a bool")
        if not isinstance(self.dependency_availability, MachineAvailability):
            raise TypeError("dependency_availability must be a MachineAvailability")
        if self.reason_unavailable is not None and not isinstance(self.reason_unavailable, str):
            raise TypeError("reason_unavailable must be a string or None")


@dataclass(frozen=True, slots=True)
class CapabilitySnapshotResult(JsonContract):
    """Result of CAPABILITY_INSPECT operation."""

    capabilities: list[CapabilitySnapshotEntry]
    count_available: int
    count_unavailable: int
    count_unknown: int

    def __post_init__(self) -> None:
        if not isinstance(self.capabilities, list) or any(
            not isinstance(item, CapabilitySnapshotEntry) for item in self.capabilities
        ):
            raise TypeError("capabilities must be a list of CapabilitySnapshotEntry")
        for name in ("count_available", "count_unavailable", "count_unknown"):
            value = getattr(self, name)
            if not isinstance(value, int) or value < 0:
                raise ValueError(f"{name} must be a non-negative integer")


__all__ = [
    "APPLICATION_SCHEMA_VERSION",
    "ApplicationError",
    "ApplicationRequest",
    "ApplicationResult",
    "ApplicationResultStatus",
    "CapabilitySnapshotEntry",
    "CapabilitySnapshotResult",
    "MachineAvailability",
    "OperationType",
    "StageOutcome",
    "StageState",
]
