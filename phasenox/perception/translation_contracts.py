from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from ._serialization import JsonContract
from .common import (
    MethodMetadata,
    ResultState,
    ResultStatus,
    ScalarValue,
    _require_finite_number,
    _require_identifier,
    _require_non_negative,
    _require_non_negative_integer,
    _require_positive_integer,
)
from .context import PlaybackProfileReference
from .results import TranslationResult
from .transfer_contracts import (
    ImpulseResponseSummary,
    TransferProvenance,
)

TRANSLATION_EVIDENCE_METHOD_ID = "noisyne.translation_evidence_foundation"
TRANSLATION_EVIDENCE_METHOD_VERSION = "1.0.0"
TRANSLATION_EVIDENCE_SCHEMA_VERSION = "1.0.0"
POLICY_CONDITIONED_TRANSLATION_RISK_METHOD_ID = "noisyne.policy_conditioned_translation_risk"
POLICY_CONDITIONED_TRANSLATION_RISK_METHOD_VERSION = "1.0.0"


class TranslationAnalysisSupport(str, Enum):
    """Which signal support is included by every global Sprint 7 quantity."""

    FULL_TRANSFER_OUTPUT = "full_transfer_output"


class TranslationEvidenceDimensionId(str, Enum):
    BRIGHTNESS_CENTROID_SHIFT_HZ = "brightness_centroid_shift_hz"
    PROGRAMME_ENERGY_DELTA_DB = "programme_energy_delta_db"
    ERB_BAND_MAXIMUM_ABSOLUTE_DELTA_DB = "erb_band_maximum_absolute_delta_db"
    TRANSFERRED_PEAK_ABSOLUTE = "transferred_peak_absolute"


class TranslationPolicyProvenance(str, Enum):
    USER_DECLARED = "user_declared"
    PROJECT_DECLARED = "project_declared"
    REFERENCE_SPECIFICATION = "reference_specification"
    VALIDATED_MODEL = "validated_model"


class TranslationRiskComparison(str, Enum):
    GREATER_THAN = "greater_than"
    GREATER_THAN_OR_EQUAL = "greater_than_or_equal"
    LESS_THAN = "less_than"
    LESS_THAN_OR_EQUAL = "less_than_or_equal"
    ABSOLUTE_GREATER_THAN = "absolute_greater_than"
    ABSOLUTE_GREATER_THAN_OR_EQUAL = "absolute_greater_than_or_equal"


def _validate_strings(values: list[str], field_name: str) -> None:
    if not isinstance(values, list):
        raise TypeError(f"{field_name} must be a list")
    for value in values:
        _require_identifier(value, field_name)


@dataclass(frozen=True, slots=True)
class TranslationEvidenceMeasurement(JsonContract):
    """Compact before/after/delta evidence; it is not a risk judgment."""

    evidence_id: str
    quantity_id: str
    state: ResultState
    original_value: ScalarValue | None
    transferred_value: ScalarValue | None
    signed_delta: ScalarValue | None
    sign_convention: str
    valid_interpretation: str
    method: MethodMetadata
    assumptions: list[str] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not isinstance(self.state, ResultState):
            raise TypeError("state must be a ResultState")
        if not isinstance(self.method, MethodMetadata):
            raise TypeError("method must be MethodMetadata")
        for field_name in (
            "evidence_id",
            "quantity_id",
            "sign_convention",
            "valid_interpretation",
        ):
            _require_identifier(getattr(self, field_name), field_name)
        values = (self.original_value, self.transferred_value, self.signed_delta)
        if self.state.status is ResultStatus.COMPUTED:
            if any(value is None for value in values):
                raise ValueError("computed translation evidence requires before, after, and delta")
            if any(not isinstance(value, ScalarValue) for value in values):
                raise TypeError("translation evidence values must be ScalarValue instances")
        elif any(value is not None for value in values):
            raise ValueError("non-computed translation evidence must not carry values")
        _validate_strings(self.assumptions, "assumptions")
        _validate_strings(self.limitations, "limitations")


@dataclass(frozen=True, slots=True)
class ErbPowerDistributionSummary(JsonContract):
    """Compact summary; channel-by-band powers, deltas, and masks remain runtime-only."""

    state: ResultState
    method: MethodMetadata
    channel_count: int
    band_count: int
    defined_value_count: int
    minimum_delta_db: float | None = None
    maximum_delta_db: float | None = None
    maximum_absolute_delta_db: float | None = None
    sign_convention: str = "10*log10(transferred_band_power/original_band_power)"
    arrays_serialized: bool = False
    limitations: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not isinstance(self.state, ResultState):
            raise TypeError("state must be a ResultState")
        if not isinstance(self.method, MethodMetadata):
            raise TypeError("method must be MethodMetadata")
        _require_positive_integer(self.channel_count, "channel_count")
        _require_positive_integer(self.band_count, "band_count")
        _require_non_negative_integer(self.defined_value_count, "defined_value_count")
        if self.defined_value_count > self.channel_count * self.band_count:
            raise ValueError("defined_value_count exceeds the channel-by-band shape")
        values = (
            self.minimum_delta_db,
            self.maximum_delta_db,
            self.maximum_absolute_delta_db,
        )
        if self.state.status is ResultStatus.COMPUTED:
            if self.defined_value_count == 0 or any(value is None for value in values):
                raise ValueError("computed ERB summary requires defined finite delta values")
            for name, value in zip(
                ("minimum_delta_db", "maximum_delta_db", "maximum_absolute_delta_db"),
                values,
                strict=True,
            ):
                _require_finite_number(value, name)
            if self.maximum_delta_db < self.minimum_delta_db:
                raise ValueError("maximum_delta_db must not be below minimum_delta_db")
            _require_non_negative(self.maximum_absolute_delta_db, "maximum_absolute_delta_db")
        elif self.defined_value_count or any(value is not None for value in values):
            raise ValueError("non-computed ERB summary must not carry defined delta values")
        _require_identifier(self.sign_convention, "sign_convention")
        if type(self.arrays_serialized) is not bool:
            raise TypeError("arrays_serialized must be a bool")
        if self.arrays_serialized:
            raise ValueError("ERB runtime arrays must not be serialized")
        _validate_strings(self.limitations, "limitations")


@dataclass(frozen=True, slots=True)
class NominalFullScaleEvidence(JsonContract):
    """Sample-peak evidence; exceeding unity does not imply clipping occurred."""

    original_peak_absolute: float
    transferred_peak_absolute: float
    original_nominal_full_scale_exceeded: bool
    transferred_nominal_full_scale_exceeded: bool
    clipping_applied: bool = False
    interpretation: str = (
        "Finite floating samples beyond unity are retained; exceedance is not audible clipping."
    )

    def __post_init__(self) -> None:
        _require_non_negative(self.original_peak_absolute, "original_peak_absolute")
        _require_non_negative(self.transferred_peak_absolute, "transferred_peak_absolute")
        for field_name in (
            "original_nominal_full_scale_exceeded",
            "transferred_nominal_full_scale_exceeded",
            "clipping_applied",
        ):
            if type(getattr(self, field_name)) is not bool:
                raise TypeError(f"{field_name} must be a bool")
        if self.clipping_applied:
            raise ValueError("Sprint 6/7 never clips transfer output")
        _require_identifier(self.interpretation, "interpretation")


@dataclass(frozen=True, slots=True)
class TranslationComparisonSummary(JsonContract):
    """Reproducible identity, alignment, and method metadata for one comparison."""

    method: MethodMetadata
    target_profile: PlaybackProfileReference
    transfer: ImpulseResponseSummary
    transfer_method: MethodMetadata
    transfer_provenance: TransferProvenance
    analysis_methods: list[MethodMetadata]
    support: TranslationAnalysisSupport
    original_sample_count: int
    transferred_sample_count: int
    transfer_tail_sample_count: int
    channel_count: int
    alignment: str
    source_id: str | None = None
    assumptions: list[str] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not isinstance(self.method, MethodMetadata):
            raise TypeError("method must be MethodMetadata")
        if not isinstance(self.target_profile, PlaybackProfileReference):
            raise TypeError("target_profile must be a PlaybackProfileReference")
        if not isinstance(self.transfer, ImpulseResponseSummary):
            raise TypeError("transfer must be an ImpulseResponseSummary")
        if not isinstance(self.transfer_method, MethodMetadata):
            raise TypeError("transfer_method must be MethodMetadata")
        if self.method.method_id != TRANSLATION_EVIDENCE_METHOD_ID or (
            self.method.version != TRANSLATION_EVIDENCE_METHOD_VERSION
        ):
            raise ValueError("translation evidence method metadata is unsupported")
        if self.target_profile != self.transfer.profile.profile_reference:
            raise ValueError("target_profile must match the executable transfer profile")
        if self.transfer_provenance is not self.transfer.profile.provenance:
            raise ValueError("transfer_provenance must match the executable transfer profile")
        if self.support is not TranslationAnalysisSupport.FULL_TRANSFER_OUTPUT:
            raise ValueError("Sprint 7 supports full_transfer_output analysis only")
        _require_positive_integer(self.original_sample_count, "original_sample_count")
        _require_positive_integer(self.transferred_sample_count, "transferred_sample_count")
        _require_non_negative_integer(self.transfer_tail_sample_count, "transfer_tail_sample_count")
        _require_positive_integer(self.channel_count, "channel_count")
        if self.transferred_sample_count != (
            self.original_sample_count + self.transfer_tail_sample_count
        ):
            raise ValueError("transferred support must equal source support plus FIR tail")
        if self.transfer_tail_sample_count != self.transfer.tap_count - 1:
            raise ValueError("transfer_tail_sample_count must equal FIR tap_count minus one")
        _require_identifier(self.alignment, "alignment")
        if self.source_id is not None:
            _require_identifier(self.source_id, "source_id")
        if not self.analysis_methods:
            raise ValueError("analysis_methods must identify the reused analysis methods")
        if any(not isinstance(method, MethodMetadata) for method in self.analysis_methods):
            raise TypeError("analysis_methods must contain MethodMetadata values")
        _validate_strings(self.assumptions, "assumptions")
        _validate_strings(self.limitations, "limitations")


@dataclass(frozen=True, slots=True)
class TranslationEvidenceResult(JsonContract):
    comparison: TranslationComparisonSummary
    brightness_centroid: TranslationEvidenceMeasurement
    programme_energy: TranslationEvidenceMeasurement
    erb_power_distribution: ErbPowerDistributionSummary
    nominal_full_scale: NominalFullScaleEvidence
    schema_version: str = TRANSLATION_EVIDENCE_SCHEMA_VERSION

    def __post_init__(self) -> None:
        for value, expected, field_name in (
            (self.comparison, TranslationComparisonSummary, "comparison"),
            (
                self.brightness_centroid,
                TranslationEvidenceMeasurement,
                "brightness_centroid",
            ),
            (self.programme_energy, TranslationEvidenceMeasurement, "programme_energy"),
            (
                self.erb_power_distribution,
                ErbPowerDistributionSummary,
                "erb_power_distribution",
            ),
            (self.nominal_full_scale, NominalFullScaleEvidence, "nominal_full_scale"),
        ):
            if not isinstance(value, expected):
                raise TypeError(f"{field_name} must be a {expected.__name__}")
        _require_identifier(self.schema_version, "schema_version")


@dataclass(frozen=True, slots=True)
class TranslationRiskCriterion(JsonContract):
    criterion_id: str
    criterion_version: str
    evidence_dimension_id: TranslationEvidenceDimensionId
    comparison: TranslationRiskComparison
    threshold: ScalarValue
    direction_semantics: str
    provenance: TranslationPolicyProvenance
    source: str
    description: str
    assumptions: list[str] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        for field_name in (
            "criterion_id",
            "criterion_version",
            "direction_semantics",
            "source",
            "description",
        ):
            _require_identifier(getattr(self, field_name), field_name)
        if not isinstance(self.evidence_dimension_id, TranslationEvidenceDimensionId):
            raise TypeError("evidence_dimension_id must be a TranslationEvidenceDimensionId")
        if not isinstance(self.comparison, TranslationRiskComparison):
            raise TypeError("comparison must be a TranslationRiskComparison")
        if not isinstance(self.provenance, TranslationPolicyProvenance):
            raise TypeError("provenance must be a TranslationPolicyProvenance")
        if not isinstance(self.threshold, ScalarValue):
            raise TypeError("threshold must be a ScalarValue")
        if isinstance(self.threshold.value, bool) or not isinstance(
            self.threshold.value, int | float
        ):
            raise TypeError("translation risk thresholds must be numeric")
        if self.threshold.normalized:
            raise ValueError("Sprint 7 risk thresholds must not be normalized")
        if (
            self.comparison
            in (
                TranslationRiskComparison.ABSOLUTE_GREATER_THAN,
                TranslationRiskComparison.ABSOLUTE_GREATER_THAN_OR_EQUAL,
            )
            and float(self.threshold.value) < 0.0
        ):
            raise ValueError("absolute comparison thresholds must be non-negative")
        _validate_strings(self.assumptions, "assumptions")
        _validate_strings(self.limitations, "limitations")


@dataclass(frozen=True, slots=True)
class TranslationRiskPolicy(JsonContract):
    policy_id: str
    version: str
    provenance: TranslationPolicyProvenance
    source: str
    description: str
    criteria: list[TranslationRiskCriterion]
    assumptions: list[str] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        for field_name in ("policy_id", "version", "source", "description"):
            _require_identifier(getattr(self, field_name), field_name)
        if not isinstance(self.provenance, TranslationPolicyProvenance):
            raise TypeError("provenance must be a TranslationPolicyProvenance")
        if not isinstance(self.criteria, list) or not self.criteria:
            raise ValueError("criteria must be a non-empty list")
        if any(not isinstance(criterion, TranslationRiskCriterion) for criterion in self.criteria):
            raise TypeError("criteria must contain TranslationRiskCriterion values")
        criterion_ids = [criterion.criterion_id for criterion in self.criteria]
        if len(criterion_ids) != len(set(criterion_ids)):
            raise ValueError("criteria must use unique criterion_id values")
        if any(criterion.provenance is not self.provenance for criterion in self.criteria):
            raise ValueError("criterion provenance must match policy provenance")
        _validate_strings(self.assumptions, "assumptions")
        _validate_strings(self.limitations, "limitations")


@dataclass(frozen=True, slots=True)
class PolicyConditionedTranslationRiskResult(JsonContract):
    """Frozen Sprint 1 risk result plus the explicit policy and evidence that condition it."""

    policy: TranslationRiskPolicy
    evidence: TranslationEvidenceResult
    translation: TranslationResult

    def __post_init__(self) -> None:
        if not isinstance(self.policy, TranslationRiskPolicy):
            raise TypeError("policy must be a TranslationRiskPolicy")
        if not isinstance(self.evidence, TranslationEvidenceResult):
            raise TypeError("evidence must be a TranslationEvidenceResult")
        if not isinstance(self.translation, TranslationResult):
            raise TypeError("translation must be a TranslationResult")
        if self.translation.target_profile != self.evidence.comparison.target_profile:
            raise ValueError("translation target must match the evidence target profile")


__all__ = [
    "POLICY_CONDITIONED_TRANSLATION_RISK_METHOD_ID",
    "POLICY_CONDITIONED_TRANSLATION_RISK_METHOD_VERSION",
    "TRANSLATION_EVIDENCE_METHOD_ID",
    "TRANSLATION_EVIDENCE_METHOD_VERSION",
    "TRANSLATION_EVIDENCE_SCHEMA_VERSION",
    "ErbPowerDistributionSummary",
    "NominalFullScaleEvidence",
    "PolicyConditionedTranslationRiskResult",
    "TranslationAnalysisSupport",
    "TranslationComparisonSummary",
    "TranslationEvidenceDimensionId",
    "TranslationEvidenceMeasurement",
    "TranslationEvidenceResult",
    "TranslationPolicyProvenance",
    "TranslationRiskComparison",
    "TranslationRiskCriterion",
    "TranslationRiskPolicy",
]
