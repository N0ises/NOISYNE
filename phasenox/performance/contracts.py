from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from phasenox.perception._serialization import JsonContract

from ._common import (
    PERFORMANCE_SCHEMA_VERSION,
    _require_identifier,
    _require_non_negative,
    _require_non_negative_integer,
    _require_string_list,
)


class RuntimeBackend(str, Enum):
    """Known runtime backends that may host a model-backed workload."""

    PYTORCH = "pytorch"
    ONNX_RUNTIME = "onnxruntime"


class DeviceType(str, Enum):
    """Execution device family."""

    CPU = "cpu"
    CUDA = "cuda"


class Precision(str, Enum):
    """Numerical precision declaration for a runtime candidate."""

    FP32 = "fp32"
    FP16 = "fp16"
    BF16 = "bf16"
    INT8 = "int8"


class RuntimeAvailabilityState(str, Enum):
    """Availability outcome for a runtime candidate on this environment."""

    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    INCOMPATIBLE = "incompatible"
    FAILED = "failed"


class EquivalenceStatus(str, Enum):
    """Outcome of comparing a candidate runtime against a canonical reference."""

    EQUIVALENT = "equivalent"
    WITHIN_TOLERANCE = "within_tolerance"
    DIFFERENT = "different"
    FAILED = "failed"
    NOT_EVALUATED = "not_evaluated"


class SelectionStatus(str, Enum):
    """Outcome status for runtime selection."""

    SELECTED = "selected"
    FALLBACK = "fallback"
    REJECTED = "rejected"
    NO_CANDIDATE = "no_candidate"


class PerformanceProfile(str, Enum):
    """Named resource/performance target policy."""

    LOW_RESOURCE = "low_resource"
    BALANCED = "balanced"
    PERFORMANCE = "performance"


class EquivalenceKind(str, Enum):
    """Category of equivalence policy to apply."""

    EXACT = "exact"
    ABSOLUTE_TOLERANCE = "absolute_tolerance"
    RELATIVE_TOLERANCE = "relative_tolerance"
    DOMAIN_SPECIFIC = "domain_specific"


@dataclass(frozen=True, slots=True)
class PerformanceEnvironment(JsonContract):
    """Reproducible snapshot of the benchmarking environment.

    Missing or unmeasurable fields are explicitly ``None`` or ``"unknown"``,
    never fabricated.
    """

    os_name: str
    os_version: str | None
    architecture: str
    python_version: str
    cpu_brand: str
    logical_cores: int | None
    total_ram_bytes: int | None
    gpu_name: str | None
    gpu_total_vram_bytes: int | None
    cuda_available: bool
    cuda_version: str | None
    torch_version: str | None
    onnxruntime_version: str | None
    onnxruntime_providers: list[str]
    benchmark_method_version: str = PERFORMANCE_SCHEMA_VERSION

    def __post_init__(self) -> None:
        _require_identifier(self.os_name, "os_name")
        if self.os_version is not None:
            _require_identifier(self.os_version, "os_version")
        _require_identifier(self.architecture, "architecture")
        _require_identifier(self.python_version, "python_version")
        if self.cpu_brand is not None:
            _require_identifier(self.cpu_brand, "cpu_brand")
        if self.logical_cores is not None:
            _require_non_negative_integer(self.logical_cores, "logical_cores")
        if self.total_ram_bytes is not None:
            _require_non_negative_integer(self.total_ram_bytes, "total_ram_bytes")
        if self.gpu_name is not None:
            _require_identifier(self.gpu_name, "gpu_name")
        if self.gpu_total_vram_bytes is not None:
            _require_non_negative_integer(self.gpu_total_vram_bytes, "gpu_total_vram_bytes")
        if type(self.cuda_available) is not bool:
            raise TypeError("cuda_available must be a bool")
        if self.cuda_version is not None:
            _require_identifier(self.cuda_version, "cuda_version")
        if self.torch_version is not None:
            _require_identifier(self.torch_version, "torch_version")
        if self.onnxruntime_version is not None:
            _require_identifier(self.onnxruntime_version, "onnxruntime_version")
        _require_string_list(self.onnxruntime_providers, "onnxruntime_providers")
        _require_identifier(self.benchmark_method_version, "benchmark_method_version")


@dataclass(frozen=True, slots=True)
class PerformanceWorkload(JsonContract):
    """Declaration of a workload that can be benchmarked."""

    workload_id: str
    workload_type: str
    description: str
    duration_seconds: float
    sample_count: int
    deterministic: bool
    limitations: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        _require_identifier(self.workload_id, "workload_id")
        _require_identifier(self.workload_type, "workload_type")
        _require_identifier(self.description, "description")
        _require_non_negative(self.duration_seconds, "duration_seconds")
        _require_non_negative_integer(self.sample_count, "sample_count")
        if type(self.deterministic) is not bool:
            raise TypeError("deterministic must be a bool")
        _require_string_list(self.limitations, "limitations")


@dataclass(frozen=True, slots=True)
class LatencyStatistics(JsonContract):
    """Aggregated timing from repeated measurements."""

    mean_seconds: float
    median_seconds: float
    min_seconds: float
    max_seconds: float
    p95_seconds: float | None
    sample_count: int

    def __post_init__(self) -> None:
        for name in ("mean_seconds", "median_seconds", "min_seconds", "max_seconds"):
            _require_non_negative(getattr(self, name), name)
        if self.p95_seconds is not None:
            _require_non_negative(self.p95_seconds, "p95_seconds")
        _require_non_negative_integer(self.sample_count, "sample_count")


@dataclass(frozen=True, slots=True)
class RawLatencySample(JsonContract):
    """One timed measurement with its phase label."""

    phase: str
    elapsed_seconds: float

    def __post_init__(self) -> None:
        _require_identifier(self.phase, "phase")
        _require_non_negative(self.elapsed_seconds, "elapsed_seconds")


@dataclass(frozen=True, slots=True)
class MemoryMeasurement(JsonContract):
    """Observed memory usage with explicit availability state."""

    ram_bytes: int | None
    gpu_allocated_bytes: int | None
    gpu_reserved_bytes: int | None

    def __post_init__(self) -> None:
        if self.ram_bytes is not None:
            _require_non_negative_integer(self.ram_bytes, "ram_bytes")
        if self.gpu_allocated_bytes is not None:
            _require_non_negative_integer(self.gpu_allocated_bytes, "gpu_allocated_bytes")
        if self.gpu_reserved_bytes is not None:
            _require_non_negative_integer(self.gpu_reserved_bytes, "gpu_reserved_bytes")


@dataclass(frozen=True, slots=True)
class PerformanceBenchmarkResult(JsonContract):
    """Result of benchmarking one workload on one runtime candidate."""

    benchmark_id: str
    workload_id: str
    runtime_identity: str
    device: DeviceType
    precision: Precision
    environment: PerformanceEnvironment
    warmup_iterations: int
    timed_iterations: int
    peak_memory: MemoryMeasurement = field(
        default_factory=lambda: MemoryMeasurement(None, None, None)
    )
    startup_load_time_seconds: float | None = None
    cold_latency_seconds: float | None = None
    warm_statistics: LatencyStatistics | None = None
    throughput_per_second: float | None = None
    limitations: list[str] = field(default_factory=list)
    timestamp_iso: str | None = None
    raw_samples: list[RawLatencySample] = field(default_factory=list)

    def __post_init__(self) -> None:
        _require_identifier(self.benchmark_id, "benchmark_id")
        _require_identifier(self.workload_id, "workload_id")
        _require_identifier(self.runtime_identity, "runtime_identity")
        if not isinstance(self.device, DeviceType):
            raise TypeError("device must be a DeviceType")
        if not isinstance(self.precision, Precision):
            raise TypeError("precision must be a Precision")
        if not isinstance(self.environment, PerformanceEnvironment):
            raise TypeError("environment must be a PerformanceEnvironment")
        _require_non_negative_integer(self.warmup_iterations, "warmup_iterations")
        _require_non_negative_integer(self.timed_iterations, "timed_iterations")
        if not isinstance(self.peak_memory, MemoryMeasurement):
            raise TypeError("peak_memory must be a MemoryMeasurement")
        if self.startup_load_time_seconds is not None:
            _require_non_negative(self.startup_load_time_seconds, "startup_load_time_seconds")
        if self.cold_latency_seconds is not None:
            _require_non_negative(self.cold_latency_seconds, "cold_latency_seconds")
        if self.warm_statistics is not None and not isinstance(
            self.warm_statistics, LatencyStatistics
        ):
            raise TypeError("warm_statistics must be a LatencyStatistics")
        if self.throughput_per_second is not None:
            _require_non_negative(self.throughput_per_second, "throughput_per_second")
        _require_string_list(self.limitations, "limitations")
        if self.timestamp_iso is not None:
            _require_identifier(self.timestamp_iso, "timestamp_iso")
        if not isinstance(self.raw_samples, list) or any(
            not isinstance(item, RawLatencySample) for item in self.raw_samples
        ):
            raise TypeError("raw_samples must be a list of RawLatencySample")


@dataclass(frozen=True, slots=True)
class CompatibilityResult(JsonContract):
    """Compatibility of a runtime candidate with the current environment."""

    runtime_identity: str
    backend: RuntimeBackend
    device: DeviceType
    precision: Precision
    state: RuntimeAvailabilityState
    reason: str | None

    def __post_init__(self) -> None:
        _require_identifier(self.runtime_identity, "runtime_identity")
        if not isinstance(self.backend, RuntimeBackend):
            raise TypeError("backend must be a RuntimeBackend")
        if not isinstance(self.device, DeviceType):
            raise TypeError("device must be a DeviceType")
        if not isinstance(self.precision, Precision):
            raise TypeError("precision must be a Precision")
        if not isinstance(self.state, RuntimeAvailabilityState):
            raise TypeError("state must be a RuntimeAvailabilityState")
        if self.reason is not None:
            _require_identifier(self.reason, "reason")


@dataclass(frozen=True, slots=True)
class EquivalenceResult(JsonContract):
    """Output-equivalence outcome against a canonical reference runtime."""

    runtime_identity: str
    canonical_identity: str
    status: EquivalenceStatus
    policy: EquivalenceKind
    tolerance_value: float | None
    max_absolute_difference: float | None
    max_relative_difference: float | None
    reason: str | None

    def __post_init__(self) -> None:
        _require_identifier(self.runtime_identity, "runtime_identity")
        _require_identifier(self.canonical_identity, "canonical_identity")
        if not isinstance(self.status, EquivalenceStatus):
            raise TypeError("status must be an EquivalenceStatus")
        if not isinstance(self.policy, EquivalenceKind):
            raise TypeError("policy must be an EquivalenceKind")
        for name in (
            "tolerance_value",
            "max_absolute_difference",
            "max_relative_difference",
        ):
            value = getattr(self, name)
            if value is not None:
                _require_non_negative(value, name)
        if self.reason is not None:
            _require_identifier(self.reason, "reason")


@dataclass(frozen=True, slots=True)
class RuntimeCandidate(JsonContract):
    """One candidate runtime with its measured and validated properties."""

    runtime_identity: str
    backend: RuntimeBackend
    device: DeviceType
    precision: Precision
    compatibility: CompatibilityResult
    equivalence: EquivalenceResult | None
    benchmark: PerformanceBenchmarkResult | None
    is_canonical: bool

    def __post_init__(self) -> None:
        _require_identifier(self.runtime_identity, "runtime_identity")
        if not isinstance(self.backend, RuntimeBackend):
            raise TypeError("backend must be a RuntimeBackend")
        if not isinstance(self.device, DeviceType):
            raise TypeError("device must be a DeviceType")
        if not isinstance(self.precision, Precision):
            raise TypeError("precision must be a Precision")
        if not isinstance(self.compatibility, CompatibilityResult):
            raise TypeError("compatibility must be a CompatibilityResult")
        if self.equivalence is not None and not isinstance(self.equivalence, EquivalenceResult):
            raise TypeError("equivalence must be an EquivalenceResult or None")
        if self.benchmark is not None and not isinstance(
            self.benchmark, PerformanceBenchmarkResult
        ):
            raise TypeError("benchmark must be a PerformanceBenchmarkResult or None")
        if type(self.is_canonical) is not bool:
            raise TypeError("is_canonical must be a bool")


@dataclass(frozen=True, slots=True)
class RejectedCandidate(JsonContract):
    """Record of why a candidate was not selected."""

    runtime_identity: str
    reason: str

    def __post_init__(self) -> None:
        _require_identifier(self.runtime_identity, "runtime_identity")
        _require_identifier(self.reason, "reason")


@dataclass(frozen=True, slots=True)
class RuntimeSelectionResult(JsonContract):
    """Deterministic outcome of selecting the fastest validated runtime."""

    selection_status: SelectionStatus
    selected_candidate: RuntimeCandidate | None
    canonical_candidate: RuntimeCandidate | None
    rejected_candidates: list[RejectedCandidate]
    reason: str
    evidence_ids: list[str]

    def __post_init__(self) -> None:
        if not isinstance(self.selection_status, SelectionStatus):
            raise TypeError("selection_status must be a SelectionStatus")
        if self.selected_candidate is not None and not isinstance(
            self.selected_candidate, RuntimeCandidate
        ):
            raise TypeError("selected_candidate must be a RuntimeCandidate or None")
        if self.canonical_candidate is not None and not isinstance(
            self.canonical_candidate, RuntimeCandidate
        ):
            raise TypeError("canonical_candidate must be a RuntimeCandidate or None")
        if not isinstance(self.rejected_candidates, list) or any(
            not isinstance(item, RejectedCandidate) for item in self.rejected_candidates
        ):
            raise TypeError("rejected_candidates must be a list of RejectedCandidate")
        _require_identifier(self.reason, "reason")
        _require_string_list(self.evidence_ids, "evidence_ids")


@dataclass(frozen=True, slots=True)
class RuntimeSelectionPolicy(JsonContract):
    """Policy governing runtime selection priority."""

    policy_id: str
    profile: PerformanceProfile
    require_equivalence: bool
    fallback_to_canonical: bool
    preferred_device: DeviceType | None = None
    max_acceptable_latency_seconds: float | None = None
    min_acceptable_throughput_per_second: float | None = None
    prohibited_backends: list[RuntimeBackend] = field(default_factory=list)
    prohibited_precisions: list[Precision] = field(default_factory=list)

    def __post_init__(self) -> None:
        _require_identifier(self.policy_id, "policy_id")
        if not isinstance(self.profile, PerformanceProfile):
            raise TypeError("profile must be a PerformanceProfile")
        if type(self.require_equivalence) is not bool:
            raise TypeError("require_equivalence must be a bool")
        if self.preferred_device is not None and not isinstance(self.preferred_device, DeviceType):
            raise TypeError("preferred_device must be a DeviceType or None")
        if self.max_acceptable_latency_seconds is not None:
            _require_non_negative(
                self.max_acceptable_latency_seconds, "max_acceptable_latency_seconds"
            )
        if self.min_acceptable_throughput_per_second is not None:
            _require_non_negative(
                self.min_acceptable_throughput_per_second,
                "min_acceptable_throughput_per_second",
            )
        if type(self.fallback_to_canonical) is not bool:
            raise TypeError("fallback_to_canonical must be a bool")
        if not isinstance(self.prohibited_backends, list) or any(
            not isinstance(item, RuntimeBackend) for item in self.prohibited_backends
        ):
            raise TypeError("prohibited_backends must be a list of RuntimeBackend")
        if not isinstance(self.prohibited_precisions, list) or any(
            not isinstance(item, Precision) for item in self.prohibited_precisions
        ):
            raise TypeError("prohibited_precisions must be a list of Precision")


@dataclass(frozen=True, slots=True)
class BenchmarkFingerprint(JsonContract):
    """Stable identity for invalidating cached benchmark results."""

    os_name: str
    architecture: str
    python_version: str
    cpu_brand: str
    logical_cores: int | None
    total_ram_bytes: int | None
    gpu_name: str | None
    torch_version: str | None
    onnxruntime_version: str | None
    runtime_identity: str
    precision: Precision
    workload_id: str
    benchmark_method_version: str

    def __post_init__(self) -> None:
        _require_identifier(self.os_name, "os_name")
        _require_identifier(self.architecture, "architecture")
        _require_identifier(self.python_version, "python_version")
        if self.cpu_brand is not None:
            _require_identifier(self.cpu_brand, "cpu_brand")
        if self.logical_cores is not None:
            _require_non_negative_integer(self.logical_cores, "logical_cores")
        if self.total_ram_bytes is not None:
            _require_non_negative_integer(self.total_ram_bytes, "total_ram_bytes")
        if self.gpu_name is not None:
            _require_identifier(self.gpu_name, "gpu_name")
        if self.torch_version is not None:
            _require_identifier(self.torch_version, "torch_version")
        if self.onnxruntime_version is not None:
            _require_identifier(self.onnxruntime_version, "onnxruntime_version")
        _require_identifier(self.runtime_identity, "runtime_identity")
        if not isinstance(self.precision, Precision):
            raise TypeError("precision must be a Precision")
        _require_identifier(self.workload_id, "workload_id")
        _require_identifier(self.benchmark_method_version, "benchmark_method_version")


__all__ = [
    "BenchmarkFingerprint",
    "CompatibilityResult",
    "DeviceType",
    "EquivalenceKind",
    "EquivalenceResult",
    "EquivalenceStatus",
    "LatencyStatistics",
    "MemoryMeasurement",
    "PerformanceBenchmarkResult",
    "PerformanceEnvironment",
    "PerformanceProfile",
    "PerformanceWorkload",
    "Precision",
    "RawLatencySample",
    "RejectedCandidate",
    "RuntimeAvailabilityState",
    "RuntimeBackend",
    "RuntimeCandidate",
    "RuntimeSelectionPolicy",
    "RuntimeSelectionResult",
    "SelectionStatus",
]
