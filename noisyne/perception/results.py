from __future__ import annotations

from dataclasses import dataclass, field

from ._serialization import JsonContract
from .common import (
    AuditoryBand,
    ComponentStatus,
    Confidence,
    FrequencyRange,
    Measurement,
    MethodMetadata,
    ObservationCategory,
    PerceptualEvidence,
    PerceptualObservation,
    ResultState,
    ResultStatus,
    ScalarValue,
    TimeRange,
    _require_identifier,
    _require_non_negative,
    _require_positive_integer,
)
from .context import PerceptualContext, PlaybackProfileReference

PERCEPTUAL_SCHEMA_VERSION = "1.0.0"


def _validate_estimate_state(state: ResultState, value: ScalarValue | None, name: str) -> None:
    if state.status is ResultStatus.COMPUTED and value is None:
        raise ValueError(f"computed {name} requires an estimate")
    if state.status is not ResultStatus.COMPUTED and value is not None:
        raise ValueError(f"non-computed {name} must not carry an estimate")


@dataclass(frozen=True, slots=True)
class AnalysisMetadata(JsonContract):
    """Transport metadata for the source analyzed by later perceptual components."""

    source_id: str | None = None
    duration_seconds: float | None = None
    sample_rate_hz: int | None = None
    channel_count: int | None = None
    auditory_frontend: MethodMetadata | None = None

    def __post_init__(self) -> None:
        if self.source_id is not None:
            _require_identifier(self.source_id, "source_id")
        if self.duration_seconds is not None:
            _require_non_negative(self.duration_seconds, "duration_seconds")
        if self.sample_rate_hz is not None:
            _require_positive_integer(self.sample_rate_hz, "sample_rate_hz")
        if self.channel_count is not None:
            _require_positive_integer(self.channel_count, "channel_count")


@dataclass(frozen=True, slots=True)
class PerceivedLoudnessResult(JsonContract):
    """Future perceived-loudness result shape; no methodology is implied."""

    state: ResultState
    estimate: ScalarValue | None = None
    programme_loudness_measurement: Measurement | None = None
    observations: list[PerceptualObservation] = field(default_factory=list)
    evidence: list[PerceptualEvidence] = field(default_factory=list)
    confidence: Confidence = field(default_factory=Confidence)
    method: MethodMetadata | None = None
    limitations: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        _validate_estimate_state(self.state, self.estimate, "perceived loudness result")
        if self.state.status is not ResultStatus.COMPUTED and any(
            observation.state.status is ResultStatus.COMPUTED for observation in self.observations
        ):
            raise ValueError("non-computed perceived loudness result has computed observation")


@dataclass(frozen=True, slots=True)
class MaskingEvent(JsonContract):
    """One future masking observation with optional, evidence-backed attribution."""

    event_id: str
    masker_region: AuditoryBand
    masked_region: AuditoryBand
    strength: ScalarValue
    evidence: list[PerceptualEvidence]
    confidence: Confidence
    time_range: TimeRange | None = None
    source_attribution: str | None = None
    method: MethodMetadata | None = None
    assumptions: list[str] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        _require_identifier(self.event_id, "event_id")
        if self.source_attribution is not None:
            _require_identifier(self.source_attribution, "source_attribution")


@dataclass(frozen=True, slots=True)
class FrequencyMaskingResult(JsonContract):
    """Collection shape; only a computed result may contain masking events."""

    state: ResultState
    events: list[MaskingEvent] = field(default_factory=list)
    evidence: list[PerceptualEvidence] = field(default_factory=list)
    confidence: Confidence = field(default_factory=Confidence)
    method: MethodMetadata | None = None
    assumptions: list[str] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.state.status is not ResultStatus.COMPUTED and self.events:
            raise ValueError("non-computed masking result must not contain events")


@dataclass(frozen=True, slots=True)
class PerceptualDescriptorResult(JsonContract):
    """One independently evolvable descriptor such as brightness, punch, or width."""

    descriptor_id: str
    state: ResultState
    estimate: ScalarValue | None = None
    display_name: str | None = None
    evidence: list[PerceptualEvidence] = field(default_factory=list)
    confidence: Confidence = field(default_factory=Confidence)
    time_range: TimeRange | None = None
    frequency_range: FrequencyRange | None = None
    method: MethodMetadata | None = None
    limitations: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        _require_identifier(self.descriptor_id, "descriptor_id")
        _validate_estimate_state(self.state, self.estimate, "descriptor result")


@dataclass(frozen=True, slots=True)
class TranslationRiskDimension(JsonContract):
    """One explicit translation-risk dimension for a target playback profile."""

    dimension_id: str
    state: ResultState
    risk: ScalarValue | None = None
    display_name: str | None = None
    evidence: list[PerceptualEvidence] = field(default_factory=list)
    confidence: Confidence = field(default_factory=Confidence)
    observations: list[PerceptualObservation] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        _require_identifier(self.dimension_id, "dimension_id")
        _validate_estimate_state(self.state, self.risk, "translation-risk dimension")
        if self.state.status is not ResultStatus.COMPUTED and any(
            observation.state.status is ResultStatus.COMPUTED for observation in self.observations
        ):
            raise ValueError("non-computed translation-risk dimension has computed observation")


@dataclass(frozen=True, slots=True)
class TranslationResult(JsonContract):
    """Translation-risk result for one playback target with multiple dimensions."""

    target_profile: PlaybackProfileReference
    state: ResultState
    dimensions: list[TranslationRiskDimension] = field(default_factory=list)
    aggregate_risk: ScalarValue | None = None
    evidence: list[PerceptualEvidence] = field(default_factory=list)
    confidence: Confidence = field(default_factory=Confidence)
    method: MethodMetadata | None = None
    limitations: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.state.status is ResultStatus.COMPUTED:
            if not self.dimensions and self.aggregate_risk is None:
                raise ValueError(
                    "computed translation result requires dimensions or aggregate risk"
                )
        elif self.dimensions or self.aggregate_risk is not None:
            raise ValueError("non-computed translation result must not carry risks")


@dataclass(frozen=True, slots=True)
class PerceptualAnalysisResult(JsonContract):
    """Versioned aggregate transport contract for all future V2 perceptual outputs."""

    state: ResultState
    schema_version: str = PERCEPTUAL_SCHEMA_VERSION
    analysis_id: str | None = None
    metadata: AnalysisMetadata | None = None
    context: PerceptualContext | None = None
    perceived_loudness: PerceivedLoudnessResult | None = None
    frequency_masking: FrequencyMaskingResult | None = None
    descriptors: list[PerceptualDescriptorResult] = field(default_factory=list)
    translations: list[TranslationResult] = field(default_factory=list)
    observations: list[PerceptualObservation] = field(default_factory=list)
    evidence: list[PerceptualEvidence] = field(default_factory=list)
    component_statuses: list[ComponentStatus] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        _require_identifier(self.schema_version, "schema_version")
        if self.analysis_id is not None:
            _require_identifier(self.analysis_id, "analysis_id")

        component_ids = [item.component_id for item in self.component_statuses]
        if len(component_ids) != len(set(component_ids)):
            raise ValueError("component_statuses must use unique component_id values")

        has_results = any(
            (
                self.perceived_loudness is not None,
                self.frequency_masking is not None,
                bool(self.descriptors),
                bool(self.translations),
                bool(self.observations),
            )
        )
        if self.state.status is ResultStatus.COMPUTED and not has_results:
            raise ValueError("computed analysis requires at least one result component")
        if self.state.status in (ResultStatus.UNAVAILABLE, ResultStatus.SKIPPED) and has_results:
            raise ValueError("unavailable or skipped analysis must not contain result components")
        if self.state.status is ResultStatus.INSUFFICIENT_EVIDENCE:
            computed_components = any(
                (
                    self.perceived_loudness is not None
                    and self.perceived_loudness.state.status is ResultStatus.COMPUTED,
                    self.frequency_masking is not None
                    and self.frequency_masking.state.status is ResultStatus.COMPUTED,
                    any(item.state.status is ResultStatus.COMPUTED for item in self.descriptors),
                    any(item.state.status is ResultStatus.COMPUTED for item in self.translations),
                    any(item.state.status is ResultStatus.COMPUTED for item in self.observations),
                    any(
                        item.state.status is ResultStatus.COMPUTED
                        for item in self.component_statuses
                    ),
                )
            )
            if computed_components:
                raise ValueError(
                    "insufficient-evidence analysis must not contain computed components"
                )


def descriptor_observation(
    *,
    observation_id: str,
    descriptor_id: str,
    state: ResultState,
    value: ScalarValue | None,
    evidence: list[PerceptualEvidence] | None = None,
    confidence: Confidence | None = None,
) -> PerceptualObservation:
    """Create a typed descriptor observation without an unstructured catch-all mapping."""
    return PerceptualObservation(
        observation_id=observation_id,
        category=ObservationCategory.DESCRIPTOR,
        kind=descriptor_id,
        state=state,
        value=value,
        evidence=list(evidence or []),
        confidence=confidence or Confidence(),
    )
