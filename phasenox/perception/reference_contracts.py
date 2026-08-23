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

REFERENCE_FOUNDATION_METHOD_ID = "noisyne.perceptual_reference_foundation"
REFERENCE_FOUNDATION_METHOD_VERSION = "1.0.0"
REFERENCE_FOUNDATION_SCHEMA_VERSION = "1.0.0"
REFERENCE_EMBEDDING_COSINE_METHOD_ID = "noisyne.reference_embedding_cosine"
REFERENCE_EMBEDDING_COSINE_METHOD_VERSION = "1.0.0"


class ReferenceProvenance(str, Enum):
    USER_SUPPLIED = "user_supplied"
    PROJECT_SUPPLIED = "project_supplied"
    WORKFLOW_SUPPLIED = "workflow_supplied"
    REFERENCE_LIBRARY = "reference_library"


class ReferenceRole(str, Enum):
    TONAL_REFERENCE = "tonal_reference"
    TRANSLATION_REFERENCE = "translation_reference"
    ARRANGEMENT_REFERENCE = "arrangement_reference"
    MIX_BALANCE_REFERENCE = "mix_balance_reference"
    GENERAL_REFERENCE = "general_reference"


class ReferenceComparisonMode(str, Enum):
    RAW_LEVEL = "raw_level"
    EXPLICIT_DIGITAL_GAIN = "explicit_digital_gain"
    SHAPE_ONLY = "shape_only"


class ReferenceEvidenceDimensionId(str, Enum):
    BRIGHTNESS_CENTROID_DELTA_HZ = "brightness_centroid_delta_hz"
    PROGRAMME_ENERGY_DELTA_DB = "programme_energy_delta_db"
    ERB_POWER_DISTRIBUTION_DELTA_DB = "erb_power_distribution_delta_db"
    SAMPLE_PEAK_DELTA_ABSOLUTE = "sample_peak_delta_absolute"


class EmbeddingSimilarityMetric(str, Enum):
    COSINE_SIMILARITY = "cosine_similarity"


def _validate_strings(values: list[str], field_name: str) -> None:
    if not isinstance(values, list):
        raise TypeError(f"{field_name} must be a list")
    for value in values:
        _require_identifier(value, field_name)


@dataclass(frozen=True, slots=True)
class ReferenceTrackIdentity(JsonContract):
    """Logical reference identity without an absolute local path."""

    reference_id: str
    version: str
    display_name: str
    provenance: ReferenceProvenance
    source: str
    duration_seconds: float
    sample_rate_hz: int
    channel_count: int
    declared_role: ReferenceRole | None = None
    assumptions: list[str] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        for field_name in ("reference_id", "version", "display_name", "source"):
            _require_identifier(getattr(self, field_name), field_name)
        if not isinstance(self.provenance, ReferenceProvenance):
            raise TypeError("provenance must be a ReferenceProvenance")
        if self.declared_role is not None and not isinstance(self.declared_role, ReferenceRole):
            raise TypeError("declared_role must be a ReferenceRole")
        _require_non_negative(self.duration_seconds, "duration_seconds")
        _require_positive_integer(self.sample_rate_hz, "sample_rate_hz")
        _require_positive_integer(self.channel_count, "channel_count")
        _validate_strings(self.assumptions, "assumptions")
        _validate_strings(self.limitations, "limitations")


@dataclass(frozen=True, slots=True)
class ReferenceSet(JsonContract):
    set_id: str
    version: str
    references: list[ReferenceTrackIdentity]
    declared_purpose: str
    provenance: ReferenceProvenance
    source: str
    assumptions: list[str] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        for field_name in ("set_id", "version", "declared_purpose", "source"):
            _require_identifier(getattr(self, field_name), field_name)
        if not isinstance(self.references, list) or not self.references:
            raise ValueError("reference set requires at least one reference")
        if any(not isinstance(item, ReferenceTrackIdentity) for item in self.references):
            raise TypeError("references must contain ReferenceTrackIdentity values")
        reference_ids = [item.reference_id for item in self.references]
        if len(reference_ids) != len(set(reference_ids)):
            raise ValueError("reference set reference_id values must be unique")
        if not isinstance(self.provenance, ReferenceProvenance):
            raise TypeError("provenance must be a ReferenceProvenance")
        _validate_strings(self.assumptions, "assumptions")
        _validate_strings(self.limitations, "limitations")


@dataclass(frozen=True, slots=True)
class ReferenceComparisonConfig(JsonContract):
    mode: ReferenceComparisonMode = ReferenceComparisonMode.RAW_LEVEL
    source_gain_db: float = 0.0
    reference_gain_db: float = 0.0
    gain_method: MethodMetadata | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.mode, ReferenceComparisonMode):
            raise TypeError("mode must be a ReferenceComparisonMode")
        _require_finite_number(self.source_gain_db, "source_gain_db")
        _require_finite_number(self.reference_gain_db, "reference_gain_db")
        explicit = self.mode is ReferenceComparisonMode.EXPLICIT_DIGITAL_GAIN
        if explicit and not isinstance(self.gain_method, MethodMetadata):
            raise ValueError("explicit digital gain mode requires gain_method")
        if not explicit and (
            self.source_gain_db != 0.0
            or self.reference_gain_db != 0.0
            or self.gain_method is not None
        ):
            raise ValueError("raw-level and shape-only modes prohibit applied gains")


@dataclass(frozen=True, slots=True)
class ReferenceEvidenceMeasurement(JsonContract):
    evidence_id: str
    dimension_id: ReferenceEvidenceDimensionId
    state: ResultState
    source_value: ScalarValue | None
    reference_value: ScalarValue | None
    signed_delta: ScalarValue | None
    sign_convention: str
    valid_interpretation: str
    method: MethodMetadata
    source_analysis_method: MethodMetadata
    reference_analysis_method: MethodMetadata
    comparison_mode: ReferenceComparisonMode
    assumptions: list[str] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        for field_name in ("evidence_id", "sign_convention", "valid_interpretation"):
            _require_identifier(getattr(self, field_name), field_name)
        if not isinstance(self.dimension_id, ReferenceEvidenceDimensionId):
            raise TypeError("dimension_id must be a ReferenceEvidenceDimensionId")
        if not isinstance(self.state, ResultState):
            raise TypeError("state must be a ResultState")
        if not isinstance(self.method, MethodMetadata):
            raise TypeError("method must be MethodMetadata")
        if not isinstance(self.source_analysis_method, MethodMetadata) or not isinstance(
            self.reference_analysis_method, MethodMetadata
        ):
            raise TypeError("analysis methods must be MethodMetadata")
        if not isinstance(self.comparison_mode, ReferenceComparisonMode):
            raise TypeError("comparison_mode must be a ReferenceComparisonMode")
        values = (self.source_value, self.reference_value, self.signed_delta)
        if self.state.status is ResultStatus.COMPUTED:
            if any(not isinstance(value, ScalarValue) for value in values):
                raise ValueError("computed reference evidence requires all scalar values")
        elif any(value is not None for value in values):
            raise ValueError("non-computed reference evidence must not carry scalar values")
        _validate_strings(self.assumptions, "assumptions")
        _validate_strings(self.limitations, "limitations")


@dataclass(frozen=True, slots=True)
class ReferenceErbPowerSummary(JsonContract):
    dimension_id: ReferenceEvidenceDimensionId
    state: ResultState
    method: MethodMetadata
    source_analysis_method: MethodMetadata
    reference_analysis_method: MethodMetadata
    comparison_mode: ReferenceComparisonMode
    source_channel_count: int
    reference_channel_count: int
    source_band_count: int
    reference_band_count: int
    defined_value_count: int
    minimum_delta_db: float | None = None
    maximum_delta_db: float | None = None
    maximum_absolute_delta_db: float | None = None
    source_value_unit: str = "accumulated_erb_power"
    reference_value_unit: str = "accumulated_erb_power"
    signed_delta_unit: str = "dB"
    sign_convention: str = "10*log10(source_erb_power/reference_erb_power)"
    arrays_serialized: bool = False
    limitations: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.dimension_id is not ReferenceEvidenceDimensionId.ERB_POWER_DISTRIBUTION_DELTA_DB:
            raise ValueError("ERB summary requires the ERB power distribution dimension")
        if not isinstance(self.state, ResultState):
            raise TypeError("state must be a ResultState")
        if not isinstance(self.method, MethodMetadata):
            raise TypeError("method must be MethodMetadata")
        if not isinstance(self.source_analysis_method, MethodMetadata) or not isinstance(
            self.reference_analysis_method, MethodMetadata
        ):
            raise TypeError("analysis methods must be MethodMetadata")
        if not isinstance(self.comparison_mode, ReferenceComparisonMode):
            raise TypeError("comparison_mode must be a ReferenceComparisonMode")
        for field_name in (
            "source_channel_count",
            "reference_channel_count",
            "source_band_count",
            "reference_band_count",
        ):
            _require_positive_integer(getattr(self, field_name), field_name)
        _require_non_negative_integer(self.defined_value_count, "defined_value_count")
        values = (
            self.minimum_delta_db,
            self.maximum_delta_db,
            self.maximum_absolute_delta_db,
        )
        if self.state.status is ResultStatus.COMPUTED:
            if self.defined_value_count == 0 or any(value is None for value in values):
                raise ValueError("computed ERB summary requires defined delta values")
            for name, value in zip(
                ("minimum_delta_db", "maximum_delta_db", "maximum_absolute_delta_db"),
                values,
                strict=True,
            ):
                _require_finite_number(value, name)
            _require_non_negative(self.maximum_absolute_delta_db, "maximum_absolute_delta_db")
        elif self.defined_value_count or any(value is not None for value in values):
            raise ValueError("non-computed ERB summary must not carry delta values")
        _require_identifier(self.sign_convention, "sign_convention")
        for field_name in ("source_value_unit", "reference_value_unit", "signed_delta_unit"):
            _require_identifier(getattr(self, field_name), field_name)
        if type(self.arrays_serialized) is not bool or self.arrays_serialized:
            raise ValueError("ERB runtime arrays must not be serialized")
        _validate_strings(self.limitations, "limitations")


@dataclass(frozen=True, slots=True)
class ReferenceComparisonSummary(JsonContract):
    method: MethodMetadata
    reference: ReferenceTrackIdentity
    config: ReferenceComparisonConfig
    source_id: str | None
    source_duration_seconds: float
    source_sample_rate_hz: int
    source_channel_count: int
    temporal_alignment: str
    channel_policy: str
    assumptions: list[str] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not isinstance(self.method, MethodMetadata):
            raise TypeError("method must be MethodMetadata")
        if not isinstance(self.reference, ReferenceTrackIdentity):
            raise TypeError("reference must be a ReferenceTrackIdentity")
        if not isinstance(self.config, ReferenceComparisonConfig):
            raise TypeError("config must be a ReferenceComparisonConfig")
        if self.source_id is not None:
            _require_identifier(self.source_id, "source_id")
        _require_non_negative(self.source_duration_seconds, "source_duration_seconds")
        _require_positive_integer(self.source_sample_rate_hz, "source_sample_rate_hz")
        _require_positive_integer(self.source_channel_count, "source_channel_count")
        _require_identifier(self.temporal_alignment, "temporal_alignment")
        _require_identifier(self.channel_policy, "channel_policy")
        _validate_strings(self.assumptions, "assumptions")
        _validate_strings(self.limitations, "limitations")


@dataclass(frozen=True, slots=True)
class ReferenceEvidenceResult(JsonContract):
    comparison: ReferenceComparisonSummary
    brightness: ReferenceEvidenceMeasurement
    programme_energy: ReferenceEvidenceMeasurement
    erb_power_distribution: ReferenceErbPowerSummary
    sample_peak: ReferenceEvidenceMeasurement
    schema_version: str = REFERENCE_FOUNDATION_SCHEMA_VERSION

    def __post_init__(self) -> None:
        expected = (
            (self.comparison, ReferenceComparisonSummary, "comparison"),
            (self.brightness, ReferenceEvidenceMeasurement, "brightness"),
            (self.programme_energy, ReferenceEvidenceMeasurement, "programme_energy"),
            (self.erb_power_distribution, ReferenceErbPowerSummary, "erb_power_distribution"),
            (self.sample_peak, ReferenceEvidenceMeasurement, "sample_peak"),
        )
        for value, contract, field_name in expected:
            if not isinstance(value, contract):
                raise TypeError(f"{field_name} must be a {contract.__name__}")

        dimensions = (
            (
                self.brightness,
                ReferenceEvidenceDimensionId.BRIGHTNESS_CENTROID_DELTA_HZ,
                "brightness",
            ),
            (
                self.programme_energy,
                ReferenceEvidenceDimensionId.PROGRAMME_ENERGY_DELTA_DB,
                "programme_energy",
            ),
            (
                self.erb_power_distribution,
                ReferenceEvidenceDimensionId.ERB_POWER_DISTRIBUTION_DELTA_DB,
                "erb_power_distribution",
            ),
            (
                self.sample_peak,
                ReferenceEvidenceDimensionId.SAMPLE_PEAK_DELTA_ABSOLUTE,
                "sample_peak",
            ),
        )
        comparison_mode = self.comparison.config.mode
        for component, dimension_id, field_name in dimensions:
            if component.dimension_id is not dimension_id:
                raise ValueError(f"{field_name} has the wrong reference evidence dimension")
            if component.comparison_mode is not comparison_mode:
                raise ValueError(f"{field_name} comparison_mode must match comparison config")

        if comparison_mode is ReferenceComparisonMode.SHAPE_ONLY:
            for component, field_name in (
                (self.programme_energy, "programme_energy"),
                (self.sample_peak, "sample_peak"),
            ):
                if component.state.status is not ResultStatus.SKIPPED:
                    raise ValueError(f"shape-only {field_name} must be skipped")
        _require_identifier(self.schema_version, "schema_version")


@dataclass(frozen=True, slots=True)
class ReferenceEmbeddingProviderIdentity(JsonContract):
    provider_id: str
    implementation: str
    model_id: str
    model_version_or_checkpoint: str
    preprocessing_id: str
    preprocessing_version: str
    embedding_dimension: int
    input_sample_rate_hz: int
    clip_window_policy: str
    aggregation_policy: str
    backend: str
    device: str
    available: bool
    unavailable_reason: str | None = None

    def __post_init__(self) -> None:
        for field_name in (
            "provider_id",
            "implementation",
            "model_id",
            "model_version_or_checkpoint",
            "preprocessing_id",
            "preprocessing_version",
            "clip_window_policy",
            "aggregation_policy",
            "backend",
            "device",
        ):
            _require_identifier(getattr(self, field_name), field_name)
        _require_positive_integer(self.embedding_dimension, "embedding_dimension")
        _require_positive_integer(self.input_sample_rate_hz, "input_sample_rate_hz")
        if type(self.available) is not bool:
            raise TypeError("available must be a bool")
        if self.available and self.unavailable_reason is not None:
            raise ValueError("available provider must not carry unavailable_reason")
        if not self.available:
            _require_identifier(self.unavailable_reason, "unavailable_reason")


@dataclass(frozen=True, slots=True)
class ReferenceEmbeddingEvidence(JsonContract):
    state: ResultState
    provider: ReferenceEmbeddingProviderIdentity
    source_embedding_id: str
    reference_embedding_id: str
    metric: EmbeddingSimilarityMetric
    similarity: ScalarValue | None
    formula: str
    method: MethodMetadata
    assumptions: list[str] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not isinstance(self.state, ResultState):
            raise TypeError("state must be a ResultState")
        if not isinstance(self.provider, ReferenceEmbeddingProviderIdentity):
            raise TypeError("provider must be a ReferenceEmbeddingProviderIdentity")
        for field_name in ("source_embedding_id", "reference_embedding_id", "formula"):
            _require_identifier(getattr(self, field_name), field_name)
        if self.metric is not EmbeddingSimilarityMetric.COSINE_SIMILARITY:
            raise ValueError("Sprint 9 supports cosine_similarity only")
        if not isinstance(self.method, MethodMetadata):
            raise TypeError("method must be MethodMetadata")
        if self.state.status is ResultStatus.COMPUTED:
            if not isinstance(self.similarity, ScalarValue):
                raise ValueError("computed embedding evidence requires similarity")
            if self.similarity.unit_basis.value != "named_scale" or (
                self.similarity.scale != "cosine_similarity_-1_to_1"
            ):
                raise ValueError("cosine similarity must use its named unnormalized scale")
            value = float(self.similarity.value)
            if not -1.0 <= value <= 1.0:
                raise ValueError("cosine similarity must be within [-1, 1]")
        elif self.similarity is not None:
            raise ValueError("non-computed embedding evidence must not carry similarity")
        _validate_strings(self.assumptions, "assumptions")
        _validate_strings(self.limitations, "limitations")


__all__ = [
    "REFERENCE_EMBEDDING_COSINE_METHOD_ID",
    "REFERENCE_EMBEDDING_COSINE_METHOD_VERSION",
    "REFERENCE_FOUNDATION_METHOD_ID",
    "REFERENCE_FOUNDATION_METHOD_VERSION",
    "REFERENCE_FOUNDATION_SCHEMA_VERSION",
    "EmbeddingSimilarityMetric",
    "ReferenceComparisonConfig",
    "ReferenceComparisonMode",
    "ReferenceComparisonSummary",
    "ReferenceEmbeddingEvidence",
    "ReferenceEmbeddingProviderIdentity",
    "ReferenceErbPowerSummary",
    "ReferenceEvidenceDimensionId",
    "ReferenceEvidenceMeasurement",
    "ReferenceEvidenceResult",
    "ReferenceProvenance",
    "ReferenceRole",
    "ReferenceSet",
    "ReferenceTrackIdentity",
]
