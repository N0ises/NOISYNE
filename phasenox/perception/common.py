from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from math import isfinite

from ._serialization import JsonContract


class ResultStatus(str, Enum):
    """Execution outcome for one perceptual result, not capability lifecycle."""

    COMPUTED = "computed"
    UNAVAILABLE = "unavailable"
    SKIPPED = "skipped"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"


class EvidenceSource(str, Enum):
    """Origin of evidence supporting a perceptual estimate."""

    MEASUREMENT = "measurement"
    CONTEXT = "context"
    REFERENCE = "reference"
    MODEL_ESTIMATE = "model_estimate"
    USER_INPUT = "user_input"


class ConfidenceBasis(str, Enum):
    """Non-probabilistic basis used to derive a normalized confidence score."""

    MEASUREMENT_QUALITY = "measurement_quality"
    MODEL_OUTPUT = "model_output"
    HEURISTIC = "heuristic"
    USER_PROVIDED = "user_provided"
    COMBINED = "combined"
    UNKNOWN = "unknown"


class UnitBasis(str, Enum):
    """How the meaning of a scalar's unit or scale is declared."""

    DECLARED_UNIT = "declared_unit"
    NAMED_SCALE = "named_scale"
    UNDEFINED = "undefined"


class ObservationCategory(str, Enum):
    """Broad category for a perceptual observation."""

    LOUDNESS = "loudness"
    MASKING = "masking"
    DESCRIPTOR = "descriptor"
    TRANSLATION_RISK = "translation_risk"
    CONTEXT = "context"


def _require_identifier(value: str, field_name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string")


def _require_finite_number(value: float, field_name: str) -> None:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise TypeError(f"{field_name} must be a number")
    if isinstance(value, float) and not isfinite(value):
        raise ValueError(f"{field_name} must be a finite number")


def _require_non_negative(value: float, field_name: str) -> None:
    _require_finite_number(value, field_name)
    if value < 0:
        raise ValueError(f"{field_name} must be a non-negative number")


def _require_non_negative_integer(value: int, field_name: str) -> None:
    if type(value) is not int or value < 0:
        raise ValueError(f"{field_name} must be a non-negative integer")


def _require_positive_integer(value: int, field_name: str) -> None:
    if type(value) is not int or value <= 0:
        raise ValueError(f"{field_name} must be a positive integer")


@dataclass(frozen=True, slots=True)
class TimeRange(JsonContract):
    """Half-open or closed interval semantics are method-defined; values use seconds."""

    start_seconds: float
    end_seconds: float

    def __post_init__(self) -> None:
        _require_non_negative(self.start_seconds, "start_seconds")
        _require_non_negative(self.end_seconds, "end_seconds")
        if self.end_seconds < self.start_seconds:
            raise ValueError("end_seconds must be greater than or equal to start_seconds")


@dataclass(frozen=True, slots=True)
class FrequencyRange(JsonContract):
    """Frequency interval in hertz with no fixed upper-frequency assumption."""

    lower_hz: float
    upper_hz: float

    def __post_init__(self) -> None:
        _require_non_negative(self.lower_hz, "lower_hz")
        _require_non_negative(self.upper_hz, "upper_hz")
        if self.upper_hz < self.lower_hz:
            raise ValueError("upper_hz must be greater than or equal to lower_hz")


@dataclass(frozen=True, slots=True)
class MethodMetadata(JsonContract):
    """Identity and version of a measurement or future perceptual method."""

    method_id: str
    version: str
    description: str | None = None

    def __post_init__(self) -> None:
        _require_identifier(self.method_id, "method_id")
        _require_identifier(self.version, "version")


@dataclass(frozen=True, slots=True)
class ScalarValue(JsonContract):
    """Transport-safe value with an explicit physical, named-scale, or undefined basis."""

    value: float | int | str | bool
    unit_basis: UnitBasis
    unit: str | None = None
    scale: str | None = None
    normalized: bool = False

    def __post_init__(self) -> None:
        if type(self.value) not in (float, int, str, bool):
            raise ValueError("value must be a float, int, string, or bool")
        if type(self.value) in (float, int):
            _require_finite_number(self.value, "value")
        if self.unit is not None:
            _require_identifier(self.unit, "unit")
        if self.scale is not None:
            _require_identifier(self.scale, "scale")

        if self.unit_basis is UnitBasis.DECLARED_UNIT:
            if self.unit is None or self.scale is not None:
                raise ValueError("declared_unit values require unit and prohibit scale")
        elif self.unit_basis is UnitBasis.NAMED_SCALE:
            if self.scale is None or self.unit is not None:
                raise ValueError("named_scale values require scale and prohibit unit")
        elif self.unit is not None or self.scale is not None:
            raise ValueError("undefined values must not declare unit or scale")

        if self.normalized:
            if self.unit_basis is not UnitBasis.NAMED_SCALE:
                raise ValueError("normalized values must use a named scale")
            if isinstance(self.value, bool) or not isinstance(self.value, int | float):
                raise ValueError("normalized values must be numeric")
            if not 0.0 <= float(self.value) <= 1.0:
                raise ValueError("normalized value must be within [0, 1]")


@dataclass(frozen=True, slots=True)
class Confidence(JsonContract):
    """Support strength; score is normalized but is not a probability claim."""

    score: float | None = None
    basis: ConfidenceBasis = ConfidenceBasis.UNKNOWN
    reason: str | None = None
    limitations: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.score is not None:
            _require_finite_number(self.score, "confidence score")
            if not 0.0 <= float(self.score) <= 1.0:
                raise ValueError("confidence score must be within [0, 1]")
        if self.reason is not None:
            _require_identifier(self.reason, "confidence reason")


@dataclass(frozen=True, slots=True)
class ResultState(JsonContract):
    """Outcome and explanation for a component execution attempt."""

    status: ResultStatus
    reason: str | None = None

    def __post_init__(self) -> None:
        if self.status is not ResultStatus.COMPUTED and not self.reason:
            raise ValueError(f"{self.status.value} state requires a reason")
        if self.reason is not None:
            _require_identifier(self.reason, "state reason")


@dataclass(frozen=True, slots=True)
class Measurement(JsonContract):
    """Objective or deterministic source value, distinct from a perceptual estimate."""

    measurement_id: str
    name: str
    value: ScalarValue
    source: str
    method: MethodMetadata | None = None
    time_range: TimeRange | None = None
    frequency_range: FrequencyRange | None = None
    note: str | None = None

    def __post_init__(self) -> None:
        _require_identifier(self.measurement_id, "measurement_id")
        _require_identifier(self.name, "measurement name")
        _require_identifier(self.source, "measurement source")


@dataclass(frozen=True, slots=True)
class PerceptualEvidence(JsonContract):
    """Evidence supporting an estimate without binding to one future algorithm."""

    evidence_id: str
    source: EvidenceSource
    origin: str | None = None
    measurement: Measurement | None = None
    reference: str | None = None
    method: MethodMetadata | None = None
    time_range: TimeRange | None = None
    frequency_range: FrequencyRange | None = None
    note: str | None = None

    def __post_init__(self) -> None:
        _require_identifier(self.evidence_id, "evidence_id")
        if self.origin is not None:
            _require_identifier(self.origin, "evidence origin")
        if self.reference is not None:
            _require_identifier(self.reference, "evidence reference")
        if self.source is EvidenceSource.MEASUREMENT and self.measurement is None:
            raise ValueError("measurement evidence requires a measurement")
        if self.measurement is None and self.reference is None and not self.note:
            raise ValueError("evidence requires a measurement, reference, or note")


@dataclass(frozen=True, slots=True)
class AuditoryBand(JsonContract):
    """Transport-safe auditory region without selecting Bark, ERB, or another scale."""

    frequency_range: FrequencyRange
    center_hz: float | None = None
    band_index: int | None = None
    scale_id: str | None = None
    method: MethodMetadata | None = None

    def __post_init__(self) -> None:
        if self.center_hz is not None:
            _require_non_negative(self.center_hz, "center_hz")
            if not self.frequency_range.lower_hz <= self.center_hz <= self.frequency_range.upper_hz:
                raise ValueError("center_hz must fall within frequency_range")
        if self.band_index is not None:
            _require_non_negative_integer(self.band_index, "band_index")
        if self.scale_id is not None:
            _require_identifier(self.scale_id, "scale_id")


@dataclass(frozen=True, slots=True)
class PerceptualObservation(JsonContract):
    """Generic, scoped perceptual estimate with structured evidence and confidence."""

    observation_id: str
    category: ObservationCategory
    kind: str
    state: ResultState
    value: ScalarValue | None = None
    evidence: list[PerceptualEvidence] = field(default_factory=list)
    confidence: Confidence = field(default_factory=Confidence)
    time_range: TimeRange | None = None
    frequency_range: FrequencyRange | None = None
    method: MethodMetadata | None = None
    limitations: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        _require_identifier(self.observation_id, "observation_id")
        _require_identifier(self.kind, "observation kind")
        if self.state.status is ResultStatus.COMPUTED and self.value is None:
            raise ValueError("computed observation requires a value")
        if self.state.status is not ResultStatus.COMPUTED and self.value is not None:
            raise ValueError("non-computed observation must not carry a value")


@dataclass(frozen=True, slots=True)
class ComponentStatus(JsonContract):
    """Named component outcome for the aggregate perceptual result."""

    component_id: str
    state: ResultState

    def __post_init__(self) -> None:
        _require_identifier(self.component_id, "component_id")
