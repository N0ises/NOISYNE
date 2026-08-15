from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from ._serialization import JsonContract, JsonValue
from .common import Confidence, ConfidenceBasis, _require_identifier, _require_non_negative
from .context import ListeningLevel, MonoCompatibility, PlaybackProfileReference
from .translation_contracts import TranslationRiskPolicy

CONTEXT_FOUNDATION_METHOD_ID = "noisyne.perceptual_context_foundation"
CONTEXT_FOUNDATION_METHOD_VERSION = "1.0.0"
CONTEXT_FOUNDATION_SCHEMA_VERSION = "1.0.0"
CONTEXT_POLICY_BINDING_METHOD_ID = "noisyne.context_policy_binding"
CONTEXT_POLICY_BINDING_METHOD_VERSION = "1.0.0"


class ContextProvenance(str, Enum):
    """Explicit origin of a context declaration; no inference classes exist."""

    USER_DECLARED = "user_declared"
    PROJECT_DECLARED = "project_declared"
    WORKFLOW_DECLARED = "workflow_declared"
    REFERENCE_SPECIFICATION = "reference_specification"
    MEASURED_LISTENING_CONDITION = "measured_listening_condition"


class ContextDimension(str, Enum):
    GENRE = "genre"
    STYLE = "style"
    ARTISTIC_INTENT = "artistic_intent"
    DELIVERY_TARGET = "delivery_target"
    PLAYBACK_EXPECTATION = "playback_expectation"
    LISTENING_LEVEL_QUALITATIVE = "listening_level_qualitative"
    LISTENING_LEVEL_DB_SPL = "listening_level_db_spl"
    MONO_COMPATIBILITY = "mono_compatibility"
    LISTENER_USE_CASE = "listener_use_case"
    LISTENER_PREFERENCE = "listener_preference"


class ContextResolutionStatus(str, Enum):
    RESOLVED = "resolved"
    CONFLICT = "conflict"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"


class ContextRequirementOperator(str, Enum):
    EQUALS = "equals"
    PRESENT = "present"
    ABSENT = "absent"


class ContextPolicySelectionStatus(str, Enum):
    SELECTED = "selected"
    CONFLICT = "conflict"
    AMBIGUOUS = "ambiguous"
    NO_MATCH = "no_match"
    UNRESOLVED = "unresolved"


ContextValue = str | float | ListeningLevel | MonoCompatibility | PlaybackProfileReference


def _prepare_context_value(dimension: ContextDimension, value: object) -> object:
    if dimension is ContextDimension.LISTENING_LEVEL_QUALITATIVE and isinstance(value, str):
        return ListeningLevel(value)
    if dimension is ContextDimension.MONO_COMPATIBILITY and isinstance(value, str):
        return MonoCompatibility(value)
    return value


def _validate_strings(values: list[str], field_name: str) -> None:
    if not isinstance(values, list):
        raise TypeError(f"{field_name} must be a list")
    for value in values:
        _require_identifier(value, field_name)


@dataclass(frozen=True, slots=True)
class ListeningConditionMeasurement(JsonContract):
    """Metadata required to identify an acoustic listening-level measurement."""

    measurement_method: str
    weighting: str
    time_basis: str
    acoustic_reference: str
    measurement_position_context: str

    def __post_init__(self) -> None:
        for field_name in (
            "measurement_method",
            "weighting",
            "time_basis",
            "acoustic_reference",
            "measurement_position_context",
        ):
            _require_identifier(getattr(self, field_name), field_name)


@dataclass(frozen=True, slots=True)
class ContextClaim(JsonContract):
    """One literal context declaration with explicit provenance and limitations."""

    claim_id: str
    context_dimension: ContextDimension
    value: ContextValue
    provenance: ContextProvenance
    source: str
    source_version: str | None = None
    measurement: ListeningConditionMeasurement | None = None
    confidence: Confidence = field(
        default_factory=lambda: Confidence(
            reason="No validated Sprint 8 confidence method; provenance is retained instead."
        )
    )
    assumptions: list[str] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)

    @staticmethod
    def _prepare_dict(data: dict[str, object]) -> dict[str, object]:
        if "context_dimension" in data and "value" in data:
            dimension = ContextDimension(data["context_dimension"])
            data["value"] = _prepare_context_value(dimension, data["value"])
        return data

    def __post_init__(self) -> None:
        _require_identifier(self.claim_id, "claim_id")
        _require_identifier(self.source, "source")
        if not isinstance(self.context_dimension, ContextDimension):
            raise TypeError("context_dimension must be a ContextDimension")
        if not isinstance(self.provenance, ContextProvenance):
            raise TypeError("provenance must be a ContextProvenance")
        if not isinstance(self.confidence, Confidence):
            raise TypeError("confidence must be a Confidence")
        if (
            self.confidence.score is not None
            or self.confidence.basis is not ConfidenceBasis.UNKNOWN
        ):
            raise ValueError("Sprint 8 context confidence must remain unscored with unknown basis")
        if self.source_version is not None:
            _require_identifier(self.source_version, "source_version")
        if (
            self.provenance is ContextProvenance.REFERENCE_SPECIFICATION
            and self.source_version is None
        ):
            raise ValueError("reference specification claims require source_version")
        if self.provenance is ContextProvenance.MEASURED_LISTENING_CONDITION:
            if self.context_dimension is not ContextDimension.LISTENING_LEVEL_DB_SPL:
                raise ValueError(
                    "measured listening condition provenance is supported only for numeric dB SPL"
                )
            if not isinstance(self.measurement, ListeningConditionMeasurement):
                raise ValueError("measured listening SPL requires measurement metadata")
        elif self.measurement is not None:
            raise ValueError(
                "measurement metadata requires measured listening condition provenance"
            )
        self._validate_value()
        _validate_strings(self.assumptions, "assumptions")
        _validate_strings(self.limitations, "limitations")

    def _validate_value(self) -> None:
        dimension = self.context_dimension
        if dimension in (
            ContextDimension.GENRE,
            ContextDimension.STYLE,
            ContextDimension.ARTISTIC_INTENT,
            ContextDimension.DELIVERY_TARGET,
            ContextDimension.LISTENER_USE_CASE,
            ContextDimension.LISTENER_PREFERENCE,
        ):
            if type(self.value) is not str:
                raise TypeError(f"{dimension.value} value must be a string")
            _require_identifier(self.value, f"{dimension.value} value")
        elif dimension is ContextDimension.PLAYBACK_EXPECTATION:
            if not isinstance(self.value, PlaybackProfileReference):
                raise TypeError("playback_expectation value must be a PlaybackProfileReference")
        elif dimension is ContextDimension.LISTENING_LEVEL_QUALITATIVE:
            if not isinstance(self.value, ListeningLevel):
                raise TypeError("qualitative listening level value must be a ListeningLevel")
        elif dimension is ContextDimension.LISTENING_LEVEL_DB_SPL:
            if isinstance(self.value, bool) or not isinstance(self.value, int | float):
                raise TypeError("numeric listening level value must be a float")
            _require_non_negative(float(self.value), "listening_level_db_spl")
        elif dimension is ContextDimension.MONO_COMPATIBILITY:
            if not isinstance(self.value, MonoCompatibility):
                raise TypeError("mono_compatibility value must be a MonoCompatibility")


@dataclass(frozen=True, slots=True)
class ResolvedContextDimension(JsonContract):
    context_dimension: ContextDimension
    status: ContextResolutionStatus
    values: list[ContextValue]
    claims: list[ContextClaim]

    @staticmethod
    def _prepare_dict(data: dict[str, object]) -> dict[str, object]:
        if "context_dimension" in data and "values" in data:
            dimension = ContextDimension(data["context_dimension"])
            values = data["values"]
            if isinstance(values, list):
                data["values"] = [_prepare_context_value(dimension, value) for value in values]
        return data

    def __post_init__(self) -> None:
        if not isinstance(self.context_dimension, ContextDimension):
            raise TypeError("context_dimension must be a ContextDimension")
        if self.status not in (ContextResolutionStatus.RESOLVED, ContextResolutionStatus.CONFLICT):
            raise ValueError("resolved dimension status must be resolved or conflict")
        if not isinstance(self.values, list) or not self.values:
            raise ValueError("resolved context dimension requires values")
        if not isinstance(self.claims, list) or not self.claims:
            raise ValueError("resolved context dimension requires claims")
        if any(claim.context_dimension is not self.context_dimension for claim in self.claims):
            raise ValueError("all claims must match the resolved context dimension")
        expected = (
            ContextResolutionStatus.RESOLVED
            if len(self.values) == 1
            or self.context_dimension is ContextDimension.LISTENER_PREFERENCE
            else ContextResolutionStatus.CONFLICT
        )
        if self.status is not expected:
            raise ValueError("dimension status must reflect the number of distinct literal values")


@dataclass(frozen=True, slots=True)
class ContextResolutionResult(JsonContract):
    status: ContextResolutionStatus
    dimensions: list[ResolvedContextDimension]
    method_id: str = CONTEXT_FOUNDATION_METHOD_ID
    method_version: str = CONTEXT_FOUNDATION_METHOD_VERSION
    schema_version: str = CONTEXT_FOUNDATION_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if not isinstance(self.status, ContextResolutionStatus):
            raise TypeError("status must be a ContextResolutionStatus")
        if not isinstance(self.dimensions, list):
            raise TypeError("dimensions must be a list")
        if any(not isinstance(item, ResolvedContextDimension) for item in self.dimensions):
            raise TypeError("dimensions must contain ResolvedContextDimension values")
        identifiers = [item.context_dimension for item in self.dimensions]
        if len(identifiers) != len(set(identifiers)):
            raise ValueError("context dimensions must be unique")
        expected = ContextResolutionStatus.INSUFFICIENT_EVIDENCE
        if self.dimensions:
            expected = (
                ContextResolutionStatus.CONFLICT
                if any(item.status is ContextResolutionStatus.CONFLICT for item in self.dimensions)
                else ContextResolutionStatus.RESOLVED
            )
        if self.status is not expected:
            raise ValueError("resolution status must reflect resolved dimensions")
        for field_name in ("method_id", "method_version", "schema_version"):
            _require_identifier(getattr(self, field_name), field_name)

    def dimension(self, dimension: ContextDimension) -> ResolvedContextDimension | None:
        return next((item for item in self.dimensions if item.context_dimension is dimension), None)


@dataclass(frozen=True, slots=True)
class ContextRequirement(JsonContract):
    context_dimension: ContextDimension
    operator: ContextRequirementOperator
    expected_value: ContextValue | None = None

    @staticmethod
    def _prepare_dict(data: dict[str, object]) -> dict[str, object]:
        if "context_dimension" in data and data.get("expected_value") is not None:
            dimension = ContextDimension(data["context_dimension"])
            data["expected_value"] = _prepare_context_value(dimension, data["expected_value"])
        return data

    def __post_init__(self) -> None:
        if not isinstance(self.context_dimension, ContextDimension):
            raise TypeError("context_dimension must be a ContextDimension")
        if not isinstance(self.operator, ContextRequirementOperator):
            raise TypeError("operator must be a ContextRequirementOperator")
        if self.operator is ContextRequirementOperator.EQUALS:
            if self.expected_value is None:
                raise ValueError("equals requirement requires expected_value")
            ContextClaim(
                claim_id="requirement.value.validation",
                context_dimension=self.context_dimension,
                value=self.expected_value,
                provenance=ContextProvenance.WORKFLOW_DECLARED,
                source="ContextRequirement type validation",
            )
        elif self.expected_value is not None:
            raise ValueError("present/absent requirements must not carry expected_value")


@dataclass(frozen=True, slots=True)
class ContextPolicyBinding(JsonContract):
    binding_id: str
    version: str
    requirements: list[ContextRequirement]
    policy_id: str
    policy_version: str
    provenance: ContextProvenance
    source: str
    source_version: str | None = None
    assumptions: list[str] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        for field_name in ("binding_id", "version", "policy_id", "policy_version", "source"):
            _require_identifier(getattr(self, field_name), field_name)
        if not isinstance(self.requirements, list) or not self.requirements:
            raise ValueError("binding requirements must be a non-empty list")
        if any(not isinstance(item, ContextRequirement) for item in self.requirements):
            raise TypeError("requirements must contain ContextRequirement values")
        if not isinstance(self.provenance, ContextProvenance):
            raise TypeError("provenance must be a ContextProvenance")
        if self.source_version is not None:
            _require_identifier(self.source_version, "source_version")
        if (
            self.provenance is ContextProvenance.REFERENCE_SPECIFICATION
            and self.source_version is None
        ):
            raise ValueError("reference specification bindings require source_version")
        _validate_strings(self.assumptions, "assumptions")
        _validate_strings(self.limitations, "limitations")


@dataclass(frozen=True, slots=True)
class ContextPolicySelectionResult(JsonContract):
    status: ContextPolicySelectionStatus
    resolution: ContextResolutionResult
    matched_binding_ids: list[str] = field(default_factory=list)
    selected_binding: ContextPolicyBinding | None = None
    selected_policy: TranslationRiskPolicy | None = None
    reason: str | None = None
    method_id: str = CONTEXT_POLICY_BINDING_METHOD_ID
    method_version: str = CONTEXT_POLICY_BINDING_METHOD_VERSION

    def __post_init__(self) -> None:
        if not isinstance(self.status, ContextPolicySelectionStatus):
            raise TypeError("status must be a ContextPolicySelectionStatus")
        if not isinstance(self.resolution, ContextResolutionResult):
            raise TypeError("resolution must be a ContextResolutionResult")
        _validate_strings(self.matched_binding_ids, "matched_binding_ids")
        if self.reason is not None:
            _require_identifier(self.reason, "reason")
        for field_name in ("method_id", "method_version"):
            _require_identifier(getattr(self, field_name), field_name)
        selected = self.status is ContextPolicySelectionStatus.SELECTED
        if selected:
            if not isinstance(self.selected_binding, ContextPolicyBinding) or not isinstance(
                self.selected_policy, TranslationRiskPolicy
            ):
                raise ValueError("selected result requires a binding and policy")
            if self.matched_binding_ids != [self.selected_binding.binding_id]:
                raise ValueError("selected result must identify exactly its selected binding")
            if (
                self.selected_policy.policy_id != self.selected_binding.policy_id
                or self.selected_policy.version != self.selected_binding.policy_version
            ):
                raise ValueError("selected policy identity must exactly match the binding")
        elif self.selected_binding is not None or self.selected_policy is not None:
            raise ValueError("non-selected result must not carry a selected binding or policy")


def context_value_key(value: ContextValue) -> JsonValue:
    """Return the JSON-safe literal used for exact equality and conflict detection."""
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, PlaybackProfileReference):
        return value.to_dict()
    return value


__all__ = [
    "CONTEXT_FOUNDATION_METHOD_ID",
    "CONTEXT_FOUNDATION_METHOD_VERSION",
    "CONTEXT_FOUNDATION_SCHEMA_VERSION",
    "CONTEXT_POLICY_BINDING_METHOD_ID",
    "CONTEXT_POLICY_BINDING_METHOD_VERSION",
    "ContextClaim",
    "ContextDimension",
    "ContextPolicyBinding",
    "ContextPolicySelectionResult",
    "ContextPolicySelectionStatus",
    "ContextProvenance",
    "ContextRequirement",
    "ContextRequirementOperator",
    "ContextResolutionResult",
    "ContextResolutionStatus",
    "ContextValue",
    "ListeningConditionMeasurement",
    "ResolvedContextDimension",
]
