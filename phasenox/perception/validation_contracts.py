from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Protocol, runtime_checkable

from ._serialization import JsonContract
from .common import (
    _require_identifier,
    _require_non_negative,
    _require_non_negative_integer,
)

VALIDATION_SCHEMA_VERSION = "1.0.0"


class ValidationStatus(str, Enum):
    """Explicit validation lifecycle for a perceptual method.

    These statuses are deliberately separate from runtime CapabilityStatus
    and ResultStatus.  They describe scientific/validation maturity, not
    whether code executes or a capability is advertised.
    """

    FOUNDATION_ONLY = "foundation_only"
    """Contracts, taxonomy, and identity exist; no implementation yet."""

    IMPLEMENTED = "implemented"
    """Code executes and produces deterministic output; not yet validated."""

    VERIFIED = "verified"
    """Implementation correctness confirmed against synthetic/deterministic fixtures."""

    VALIDATED = "validated"
    """Scientific/perceptual validation completed against normative reference."""

    UNAVAILABLE = "unavailable"
    """Blocked: missing standard material, prerequisite, validated model, or fixture."""


class FixtureKind(str, Enum):
    """Category of deterministic synthetic or reference fixture."""

    SILENCE = "silence"
    ZERO_ENERGY = "zero_energy"
    SINGLE_SINE = "single_sine"
    KNOWN_AMPLITUDE_SINE = "known_amplitude_sine"
    TWO_TONE = "two_tone"
    KNOWN_DIGITAL_GAIN = "known_digital_gain"
    KNOWN_SAMPLE_PEAK = "known_sample_peak"
    KNOWN_SPECTRAL_SHIFT = "known_spectral_shift"
    DETERMINISTIC_ERB_ENERGY = "deterministic_erb_energy"
    IDENTICAL_SOURCE_REFERENCE = "identical_source_reference"
    EXACT_PLAYBACK_TRANSFER = "exact_playback_transfer"
    EXACT_POLICY_BOUNDARY = "exact_policy_boundary"


class ToleranceKind(str, Enum):
    """Domain-appropriate tolerance category for numeric comparisons."""

    EXACT_IDENTITY = "exact_identity"
    SERIALIZATION_IDENTITY = "serialization_identity"
    FLOATING_POINT_NUMERICAL = "floating_point_numerical"
    DSP_IMPLEMENTATION = "dsp_implementation"
    REFERENCE_METHOD = "reference_method"


@dataclass(frozen=True, slots=True)
class ValidationCriterion(JsonContract):
    """One auditable criterion that a method must satisfy for a given status."""

    criterion_id: str
    version: str
    description: str
    required_status: ValidationStatus
    fixture_kind: FixtureKind | None = None
    tolerance_kind: ToleranceKind | None = None
    tolerance_value: float | None = None
    assumptions: list[str] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        for field_name in ("criterion_id", "version", "description"):
            _require_identifier(getattr(self, field_name), field_name)
        if not isinstance(self.required_status, ValidationStatus):
            raise TypeError("required_status must be a ValidationStatus")
        if self.fixture_kind is not None and not isinstance(self.fixture_kind, FixtureKind):
            raise TypeError("fixture_kind must be a FixtureKind")
        if self.tolerance_kind is not None and not isinstance(self.tolerance_kind, ToleranceKind):
            raise TypeError("tolerance_kind must be a ToleranceKind")
        if self.tolerance_value is not None:
            _require_non_negative(self.tolerance_value, "tolerance_value")
        for item in self.assumptions:
            _require_identifier(item, "assumptions")
        for item in self.limitations:
            _require_identifier(item, "limitations")


@dataclass(frozen=True, slots=True)
class ValidationEvidence(JsonContract):
    """Recorded evidence that a criterion was evaluated against a fixture."""

    evidence_id: str
    criterion_id: str
    fixture_kind: FixtureKind | None
    passed: bool
    method_id: str
    method_version: str
    fixture_description: str
    result_description: str
    assumptions: list[str] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        for field_name in (
            "evidence_id",
            "criterion_id",
            "method_id",
            "method_version",
            "fixture_description",
            "result_description",
        ):
            _require_identifier(getattr(self, field_name), field_name)
        if self.fixture_kind is not None and not isinstance(self.fixture_kind, FixtureKind):
            raise TypeError("fixture_kind must be a FixtureKind")
        if type(self.passed) is not bool:
            raise TypeError("passed must be a bool")
        for item in self.assumptions:
            _require_identifier(item, "assumptions")
        for item in self.limitations:
            _require_identifier(item, "limitations")


@dataclass(frozen=True, slots=True)
class MethodValidationRecord(JsonContract):
    """Complete validation record for one perceptual method."""

    capability_id: str
    method_id: str
    method_version: str
    implementation_status: ValidationStatus
    validation_status: ValidationStatus
    scientific_basis: list[str]
    validation_fixture: list[str]
    tolerance_policy: list[str]
    supported_claims: list[str]
    prohibited_claims: list[str]
    known_limitations: list[str]
    criteria: list[ValidationCriterion] = field(default_factory=list)
    evidence: list[ValidationEvidence] = field(default_factory=list)
    schema_version: str = VALIDATION_SCHEMA_VERSION

    def __post_init__(self) -> None:
        for field_name in ("capability_id", "method_id", "method_version"):
            _require_identifier(getattr(self, field_name), field_name)
        if not isinstance(self.implementation_status, ValidationStatus):
            raise TypeError("implementation_status must be a ValidationStatus")
        if not isinstance(self.validation_status, ValidationStatus):
            raise TypeError("validation_status must be a ValidationStatus")
        if any(not isinstance(item, ValidationCriterion) for item in self.criteria):
            raise TypeError("criteria must contain ValidationCriterion values")
        if any(not isinstance(item, ValidationEvidence) for item in self.evidence):
            raise TypeError("evidence must contain ValidationEvidence values")
        _require_identifier(self.schema_version, "schema_version")
        for lst_name in (
            "scientific_basis",
            "validation_fixture",
            "tolerance_policy",
            "supported_claims",
            "prohibited_claims",
            "known_limitations",
        ):
            values = getattr(self, lst_name)
            if not isinstance(values, list):
                raise TypeError(f"{lst_name} must be a list")
            for value in values:
                _require_identifier(value, lst_name)


@dataclass(frozen=True, slots=True)
class ValidationSummary(JsonContract):
    """Aggregate validation state across the V2 perceptual pipeline."""

    record_count: int
    foundation_only_count: int
    implemented_count: int
    verified_count: int
    validated_count: int
    unavailable_count: int
    records: list[MethodValidationRecord]
    schema_version: str = VALIDATION_SCHEMA_VERSION

    def __post_init__(self) -> None:
        _require_non_negative_integer(self.record_count, "record_count")
        _require_non_negative_integer(self.foundation_only_count, "foundation_only_count")
        _require_non_negative_integer(self.implemented_count, "implemented_count")
        _require_non_negative_integer(self.verified_count, "verified_count")
        _require_non_negative_integer(self.validated_count, "validated_count")
        _require_non_negative_integer(self.unavailable_count, "unavailable_count")
        if not isinstance(self.records, list) or any(
            not isinstance(item, MethodValidationRecord) for item in self.records
        ):
            raise TypeError("records must contain MethodValidationRecord values")
        expected = (
            self.foundation_only_count
            + self.implemented_count
            + self.verified_count
            + self.validated_count
            + self.unavailable_count
        )
        if expected != self.record_count:
            raise ValueError("status counts must sum to record_count")
        if len(self.records) != self.record_count:
            raise ValueError("records length must match record_count")
        _require_identifier(self.schema_version, "schema_version")


@runtime_checkable
class ValidationFixtureProvider(Protocol):
    """Protocol for deterministic fixture generation."""

    def generate(
        self,
        kind: FixtureKind,
        sample_rate_hz: int,
        duration_seconds: float,
        channel_count: int,
        **kwargs: object,
    ) -> dict[str, object]:
        """Return fixture data and metadata for the given kind."""
        ...


__all__ = [
    "VALIDATION_SCHEMA_VERSION",
    "FixtureKind",
    "MethodValidationRecord",
    "ToleranceKind",
    "ValidationCriterion",
    "ValidationEvidence",
    "ValidationFixtureProvider",
    "ValidationStatus",
    "ValidationSummary",
]
