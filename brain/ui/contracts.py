"""Qt-free contracts shared by desktop presentation and application adapters."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Protocol, runtime_checkable


class CapabilityLifecycle(str, Enum):
    PLANNED = "planned"
    IMPLEMENTED = "implemented"
    VERIFIED = "verified"
    PRODUCTION = "production"
    DEPRECATED = "deprecated"


class Availability(str, Enum):
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    DEGRADED = "degraded"
    UNKNOWN = "unknown"


class RuntimeState(str, Enum):
    READY = "ready"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"
    UNKNOWN = "unknown"


class OperationState(str, Enum):
    QUEUED = "queued"
    VALIDATING = "validating"
    RUNNING = "running"
    CANCELLING = "cancelling"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class UiErrorCategory(str, Enum):
    VALIDATION = "validation"
    CAPABILITY_UNAVAILABLE = "capability_unavailable"
    CONFIGURATION = "configuration"
    PROVIDER_MODEL = "provider_model"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"
    REPORT_EXPORT = "report_export"
    INTERNAL = "internal"


@dataclass(frozen=True, slots=True)
class ProductMetadata:
    display_name: str
    application_title: str
    version: str
    organization_name: str
    organization_domain: str | None
    application_id: str


@dataclass(frozen=True, slots=True)
class CapabilitySnapshot:
    id: str
    display_name: str
    lifecycle: CapabilityLifecycle
    availability: Availability
    reason_code: str | None = None
    reason: str | None = None
    checked_at: datetime | None = None
    dependencies: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ModelStatus:
    name: str
    availability: Availability
    reason: str | None = None


@dataclass(frozen=True, slots=True)
class ProviderStatus:
    name: str
    availability: Availability
    reason: str | None = None
    checked_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class PathStatus:
    kind: str
    path: Path
    exists: bool
    readable: bool
    writable: bool


@dataclass(frozen=True, slots=True)
class RuntimeStatus:
    state: RuntimeState
    requested_device: str
    effective_device: str | None
    device_reason: str | None
    loaded_models: tuple[ModelStatus, ...]
    provider: ProviderStatus
    paths: tuple[PathStatus, ...]
    configuration_source: str
    capabilities: tuple[CapabilitySnapshot, ...]
    checked_at: datetime


@dataclass(frozen=True, slots=True)
class SettingValue:
    key: str
    value: str | int | float | bool
    writable: bool = False
    restart_required: bool = False


@dataclass(frozen=True, slots=True)
class SettingsSnapshot:
    revision: str
    source: str
    values: tuple[SettingValue, ...]
    credential_configured: bool


@dataclass(frozen=True, slots=True)
class RecoveryAction:
    id: str
    label: str


@dataclass(frozen=True, slots=True)
class UiError:
    code: str
    category: UiErrorCategory
    user_message: str
    technical_detail: str | None = None
    retryable: bool = False
    recovery_actions: tuple[RecoveryAction, ...] = ()
    partial_result_usable: bool = False
    capability_id: str | None = None
    operation_id: str | None = None


@dataclass(frozen=True, slots=True)
class OperationHandle:
    operation_id: str
    kind: str
    state: OperationState = OperationState.QUEUED
    cancel_requested: bool = False


@dataclass(frozen=True, slots=True)
class OperationEvent:
    operation_id: str
    sequence: int
    state: OperationState
    stage: str
    progress: float | None = None
    message: str | None = None
    cancellable: bool = False
    result: object | None = None
    error: UiError | None = None


@dataclass(frozen=True, slots=True)
class AnalysisCommand:
    source_path: Path
    reference_paths: tuple[Path, ...] = ()
    intent: str = ""
    delivery_target: str = ""
    include_semantic_analysis: bool = False
    include_reasoning: bool = False
    include_rag: bool = False
    include_mix_intelligence: bool = False
    include_plugin_intelligence: bool = False
    output_path: Path | None = None


@dataclass(frozen=True, slots=True)
class AnalysisIssue:
    title: str
    severity: str
    description: str
    recommendation: str


@dataclass(frozen=True, slots=True)
class MetricValue:
    name: str
    value: str | int | float | bool | None


@dataclass(frozen=True, slots=True)
class ReportDescriptor:
    kind: str
    format: str
    path: Path
    display_label: str


@dataclass(frozen=True, slots=True)
class AnalysisViewResult:
    source_path: Path
    status: str
    audio_type: str
    score: float
    summary: str
    issues: tuple[AnalysisIssue, ...] = ()
    metrics: tuple[MetricValue, ...] = ()
    warnings: tuple[str, ...] = ()
    reference_similarity: float | None = None
    reports: tuple[ReportDescriptor, ...] = ()


@runtime_checkable
class DesktopApplicationAdapter(Protocol):
    def product_metadata(self) -> ProductMetadata: ...

    def capability_snapshots(self) -> tuple[CapabilitySnapshot, ...]: ...

    def runtime_status(self) -> RuntimeStatus: ...

    def settings_snapshot(self) -> SettingsSnapshot: ...

    def analyze(self, command: AnalysisCommand) -> AnalysisViewResult: ...
