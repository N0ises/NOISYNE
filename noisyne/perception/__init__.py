"""Lightweight V2 perceptual domain contracts.

This package defines transport-safe value objects only. It does not implement
auditory, loudness, masking, descriptor, playback, or translation algorithms.
"""

from .common import (
    AuditoryBand,
    ComponentStatus,
    Confidence,
    ConfidenceBasis,
    EvidenceSource,
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
    UnitBasis,
)
from .context import (
    ListeningLevel,
    MonoCompatibility,
    PerceptualContext,
    PlaybackConstraint,
    PlaybackProfile,
    PlaybackProfileReference,
)
from .results import (
    PERCEPTUAL_SCHEMA_VERSION,
    AnalysisMetadata,
    FrequencyMaskingResult,
    MaskingEvent,
    PerceivedLoudnessResult,
    PerceptualAnalysisResult,
    PerceptualDescriptorResult,
    TranslationResult,
    TranslationRiskDimension,
    descriptor_observation,
)

__all__ = [
    "PERCEPTUAL_SCHEMA_VERSION",
    "AnalysisMetadata",
    "AuditoryBand",
    "ComponentStatus",
    "Confidence",
    "ConfidenceBasis",
    "EvidenceSource",
    "FrequencyMaskingResult",
    "FrequencyRange",
    "ListeningLevel",
    "MaskingEvent",
    "Measurement",
    "MethodMetadata",
    "MonoCompatibility",
    "ObservationCategory",
    "PerceivedLoudnessResult",
    "PerceptualAnalysisResult",
    "PerceptualContext",
    "PerceptualDescriptorResult",
    "PerceptualEvidence",
    "PerceptualObservation",
    "PlaybackConstraint",
    "PlaybackProfile",
    "PlaybackProfileReference",
    "ResultState",
    "ResultStatus",
    "ScalarValue",
    "TimeRange",
    "TranslationResult",
    "TranslationRiskDimension",
    "UnitBasis",
    "descriptor_observation",
]
