from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import numpy as np
from numpy.typing import NDArray

from noisyne.audio.io.models import AudioData

from .auditory import AuditoryFrontend
from .common import MethodMetadata, ResultState, ResultStatus, ScalarValue, UnitBasis
from .descriptor_contracts import (
    BRIGHTNESS_CORRELATE_METHOD_ID,
    BRIGHTNESS_CORRELATE_METHOD_VERSION,
)
from .descriptors import PerceptualDescriptorFoundation
from .reference_contracts import (
    REFERENCE_EMBEDDING_COSINE_METHOD_ID,
    REFERENCE_EMBEDDING_COSINE_METHOD_VERSION,
    REFERENCE_FOUNDATION_METHOD_ID,
    REFERENCE_FOUNDATION_METHOD_VERSION,
    EmbeddingSimilarityMetric,
    ReferenceComparisonConfig,
    ReferenceComparisonMode,
    ReferenceComparisonSummary,
    ReferenceEmbeddingEvidence,
    ReferenceEmbeddingProviderIdentity,
    ReferenceErbPowerSummary,
    ReferenceEvidenceDimensionId,
    ReferenceEvidenceMeasurement,
    ReferenceEvidenceResult,
    ReferenceTrackIdentity,
)

FloatArray = NDArray[np.float64]
BoolArray = NDArray[np.bool_]

_ENERGY_UNIT = "sum_square_digital_sample_amplitude"
_PEAK_UNIT = "digital_sample_amplitude"


class ReferenceEmbeddingProvider(Protocol):
    """Optional provider boundary; Sprint 9 supplies no live CLAP adapter."""

    @property
    def identity(self) -> ReferenceEmbeddingProviderIdentity: ...

    def encode_audio(self, audio: AudioData) -> NDArray[np.floating]: ...


@dataclass(frozen=True, slots=True)
class ReferenceRuntimeResult:
    """Transport evidence plus runtime-only accumulated ERB arrays."""

    evidence: ReferenceEvidenceResult
    source_channel_erb_power: FloatArray
    reference_channel_erb_power: FloatArray
    channel_erb_delta_db: FloatArray
    channel_erb_delta_defined: BoolArray

    def __post_init__(self) -> None:
        if not isinstance(self.evidence, ReferenceEvidenceResult):
            raise TypeError("evidence must be a ReferenceEvidenceResult")
        for array, name, dtype in (
            (self.source_channel_erb_power, "source_channel_erb_power", np.dtype(np.float64)),
            (
                self.reference_channel_erb_power,
                "reference_channel_erb_power",
                np.dtype(np.float64),
            ),
            (self.channel_erb_delta_db, "channel_erb_delta_db", np.dtype(np.float64)),
            (self.channel_erb_delta_defined, "channel_erb_delta_defined", np.dtype(np.bool_)),
        ):
            if not isinstance(array, np.ndarray) or array.ndim != 2 or array.dtype != dtype:
                raise TypeError(f"{name} must be a two-dimensional {dtype} array")
            if dtype == np.dtype(np.float64) and not np.all(np.isfinite(array)):
                raise ValueError(f"{name} must contain finite values")
            if array.flags.writeable:
                raise ValueError(f"{name} must be read-only")
        if self.channel_erb_delta_db.shape != self.channel_erb_delta_defined.shape:
            raise ValueError("ERB delta and definition-mask shapes must match")

        summary = self.evidence.erb_power_distribution
        source_shape = (summary.source_channel_count, summary.source_band_count)
        reference_shape = (summary.reference_channel_count, summary.reference_band_count)
        if self.source_channel_erb_power.shape != source_shape:
            raise ValueError("source ERB power shape must match transport summary")
        if self.reference_channel_erb_power.shape != reference_shape:
            raise ValueError("reference ERB power shape must match transport summary")

        compatible = source_shape == reference_shape
        if summary.state.status is ResultStatus.COMPUTED:
            if not compatible:
                raise ValueError("computed ERB summary requires compatible source/reference shapes")
            delta_shape = source_shape
        elif summary.state.status is ResultStatus.INSUFFICIENT_EVIDENCE:
            delta_shape = source_shape if compatible else (0, 0)
        else:
            raise ValueError("runtime ERB summary must be computed or insufficient evidence")
        if self.channel_erb_delta_db.shape != delta_shape:
            raise ValueError("ERB delta shape must match transport summary semantics")
        if self.channel_erb_delta_defined.shape != delta_shape:
            raise ValueError("ERB definition-mask shape must match transport summary semantics")

        defined_count = int(np.count_nonzero(self.channel_erb_delta_defined))
        if defined_count != summary.defined_value_count:
            raise ValueError("ERB definition-mask count must match transport summary")
        if summary.state.status is ResultStatus.COMPUTED:
            defined_delta = self.channel_erb_delta_db[self.channel_erb_delta_defined]
            extrema = (
                float(np.min(defined_delta)),
                float(np.max(defined_delta)),
                float(np.max(np.abs(defined_delta))),
            )
            expected_extrema = (
                summary.minimum_delta_db,
                summary.maximum_delta_db,
                summary.maximum_absolute_delta_db,
            )
            if extrema != expected_extrema:
                raise ValueError("ERB runtime delta extrema must match transport summary")
        elif np.any(self.channel_erb_delta_db != 0.0):
            raise ValueError("undefined ERB runtime deltas must retain zero placeholders")


class ObjectiveReferenceComparator:
    """Whole-programme evidence only; no policy, alignment, quality score, or advice."""

    def compare(
        self,
        source: AudioData,
        reference: AudioData,
        reference_identity: ReferenceTrackIdentity,
        *,
        config: ReferenceComparisonConfig | None = None,
        source_id: str | None = None,
    ) -> ReferenceRuntimeResult:
        if not isinstance(source, AudioData) or not isinstance(reference, AudioData):
            raise TypeError("source and reference must be AudioData")
        if not isinstance(reference_identity, ReferenceTrackIdentity):
            raise TypeError("reference_identity must be a ReferenceTrackIdentity")
        comparison_config = config or ReferenceComparisonConfig()
        if not isinstance(comparison_config, ReferenceComparisonConfig):
            raise TypeError("config must be a ReferenceComparisonConfig")
        self._validate_reference_identity(reference, reference_identity)

        source_audio = _apply_declared_gain(source, comparison_config.source_gain_db)
        reference_audio = _apply_declared_gain(reference, comparison_config.reference_gain_db)

        source_descriptor = PerceptualDescriptorFoundation().analyze(source_audio)
        reference_descriptor = PerceptualDescriptorFoundation().analyze(reference_audio)
        source_frontend = AuditoryFrontend().analyze(source_audio)
        reference_frontend = AuditoryFrontend().analyze(reference_audio)

        source_erb = _accumulate_erb(source_frontend.auditory_band_power)
        reference_erb = _accumulate_erb(reference_frontend.auditory_band_power)
        erb_summary, erb_delta, erb_defined = _compare_erb(
            source_erb,
            reference_erb,
            source_frontend.summary.auditory_bands,
            reference_frontend.summary.auditory_bands,
            comparison_config.mode,
            source_frontend.summary.method,
            reference_frontend.summary.method,
        )

        comparison = ReferenceComparisonSummary(
            method=_reference_method(),
            reference=reference_identity,
            config=comparison_config,
            source_id=source_id,
            source_duration_seconds=source.metadata.duration,
            source_sample_rate_hz=source.metadata.sample_rate,
            source_channel_count=source.metadata.channels,
            temporal_alignment="independent_whole_programme_summaries_no_temporal_alignment",
            channel_policy=(
                "programme scalars sum channel power; ERB comparison requires identical channels "
                "and identical Sprint 2 band definitions"
            ),
            assumptions=[
                "Source and reference are caller-identified programme items.",
                "Different musical content may dominate any reported difference.",
            ],
            limitations=[
                "Reference evidence is not mix quality, mastering quality, or a recommendation.",
                "No sample, beat, section, or time-warp alignment is performed.",
            ],
        )
        evidence = ReferenceEvidenceResult(
            comparison=comparison,
            brightness=_brightness_measurement(
                source_descriptor, reference_descriptor, comparison_config.mode
            ),
            programme_energy=_energy_measurement(
                source_audio, reference_audio, comparison_config.mode
            ),
            erb_power_distribution=erb_summary,
            sample_peak=_peak_measurement(source_audio, reference_audio, comparison_config.mode),
        )
        return ReferenceRuntimeResult(
            evidence=evidence,
            source_channel_erb_power=source_erb,
            reference_channel_erb_power=reference_erb,
            channel_erb_delta_db=erb_delta,
            channel_erb_delta_defined=erb_defined,
        )

    @staticmethod
    def _validate_reference_identity(
        reference: AudioData, identity: ReferenceTrackIdentity
    ) -> None:
        if identity.sample_rate_hz != reference.metadata.sample_rate:
            raise ValueError("reference identity sample rate must match reference audio")
        if identity.channel_count != reference.metadata.channels:
            raise ValueError("reference identity channel count must match reference audio")
        tolerance = 1.0 / reference.metadata.sample_rate
        if abs(identity.duration_seconds - reference.metadata.duration) > tolerance:
            raise ValueError(
                "reference identity duration must match reference audio within one sample"
            )


class EmbeddingCosineComparator:
    """Raw cosine in one exact representation space with scale-stable numerics."""

    def compare(
        self,
        source_embedding: NDArray[np.floating],
        reference_embedding: NDArray[np.floating],
        source_provider: ReferenceEmbeddingProviderIdentity,
        reference_provider: ReferenceEmbeddingProviderIdentity,
        *,
        source_embedding_id: str,
        reference_embedding_id: str,
    ) -> ReferenceEmbeddingEvidence:
        if not isinstance(source_provider, ReferenceEmbeddingProviderIdentity) or not isinstance(
            reference_provider, ReferenceEmbeddingProviderIdentity
        ):
            raise TypeError("provider identities must be ReferenceEmbeddingProviderIdentity")
        if source_provider != reference_provider:
            raise ValueError("embedding comparison requires exact provider representation identity")
        if not source_provider.available:
            raise ValueError("embedding provider must be available to produce comparison evidence")
        source = _embedding_vector(source_embedding, "source_embedding")
        reference = _embedding_vector(reference_embedding, "reference_embedding")
        if source.shape != reference.shape:
            raise ValueError("embedding dimensions must match")
        if source.size != source_provider.embedding_dimension:
            raise ValueError("embedding vectors must match provider embedding_dimension")

        method = MethodMetadata(
            REFERENCE_EMBEDDING_COSINE_METHOD_ID,
            REFERENCE_EMBEDDING_COSINE_METHOD_VERSION,
            "Raw cosine after independent max-absolute scaling for overflow-safe evaluation.",
        )
        limitations = [
            "Model-space similarity is not mix, mastering, tonal, or perceptual quality.",
            "No percentage conversion, ranking-quality claim, or causal interpretation is valid.",
        ]
        similarity = _stable_cosine(source, reference)
        if similarity is None:
            return ReferenceEmbeddingEvidence(
                state=ResultState(
                    ResultStatus.INSUFFICIENT_EVIDENCE,
                    "Cosine similarity is undefined for a zero-norm embedding.",
                ),
                provider=source_provider,
                source_embedding_id=source_embedding_id,
                reference_embedding_id=reference_embedding_id,
                metric=EmbeddingSimilarityMetric.COSINE_SIMILARITY,
                similarity=None,
                formula="dot(source, reference) / (norm(source) * norm(reference))",
                method=method,
                limitations=limitations,
            )
        return ReferenceEmbeddingEvidence(
            state=ResultState(ResultStatus.COMPUTED),
            provider=source_provider,
            source_embedding_id=source_embedding_id,
            reference_embedding_id=reference_embedding_id,
            metric=EmbeddingSimilarityMetric.COSINE_SIMILARITY,
            similarity=ScalarValue(
                similarity,
                UnitBasis.NAMED_SCALE,
                scale="cosine_similarity_-1_to_1",
                normalized=False,
            ),
            formula="dot(source, reference) / (norm(source) * norm(reference))",
            method=method,
            limitations=limitations,
        )


def _apply_declared_gain(audio: AudioData, gain_db: float) -> AudioData:
    try:
        with np.errstate(over="raise", under="raise", invalid="raise"):
            factor = float(np.power(10.0, gain_db / 20.0))
    except FloatingPointError as exc:
        raise ValueError("declared digital gain is not representable") from exc
    if not np.isfinite(factor) or factor == 0.0:
        raise ValueError("declared digital gain is not representable")
    values = np.asarray(audio.samples, dtype=np.float64)
    try:
        with np.errstate(over="raise", invalid="raise"):
            samples = np.array(values * factor, dtype=np.float64, copy=True)
    except FloatingPointError as exc:
        raise ValueError("gain-applied audio is not representable") from exc
    if not np.all(np.isfinite(samples)):
        raise ValueError("gain-applied audio must remain finite")
    return AudioData(samples=samples, metadata=audio.metadata)


def _stable_cosine(source: FloatArray, reference: FloatArray) -> float | None:
    """Compute cosine after positive max-absolute scaling; return None for zero norm."""
    source_scale = float(np.max(np.abs(source)))
    reference_scale = float(np.max(np.abs(reference)))
    if source_scale == 0.0 or reference_scale == 0.0:
        return None

    try:
        with np.errstate(over="raise", invalid="raise", divide="raise", under="ignore"):
            source_scaled = source / source_scale
            reference_scaled = reference / reference_scale
            source_norm = float(np.linalg.norm(source_scaled))
            reference_norm = float(np.linalg.norm(reference_scaled))
            if (
                not np.isfinite(source_norm)
                or not np.isfinite(reference_norm)
                or source_norm <= 0.0
                or reference_norm <= 0.0
            ):
                raise ValueError("cosine similarity requires finite positive norms")
            denominator = source_norm * reference_norm
            if not np.isfinite(denominator) or denominator <= 0.0:
                raise ValueError("cosine similarity requires a finite positive denominator")
            dot_product = float(np.dot(source_scaled, reference_scaled))
            if not np.isfinite(dot_product):
                raise ValueError("cosine similarity requires a finite dot product")
            similarity = dot_product / denominator
    except (FloatingPointError, OverflowError, ZeroDivisionError) as exc:
        raise ValueError("cosine similarity intermediate is not representable") from exc

    intermediates = (source_norm, reference_norm, denominator, dot_product, similarity)
    if not all(np.isfinite(value) for value in intermediates):
        raise ValueError("cosine similarity requires finite intermediates and positive norms")

    roundoff_tolerance = 8.0 * np.finfo(np.float64).eps
    if similarity < -1.0 or similarity > 1.0:
        if similarity < -1.0 - roundoff_tolerance or similarity > 1.0 + roundoff_tolerance:
            raise ValueError("cosine similarity lies outside its mathematical interval")
        similarity = min(1.0, max(-1.0, similarity))
    return similarity


def _brightness_measurement(source, reference, mode) -> ReferenceEvidenceMeasurement:
    source_result = next(item for item in source.descriptors if item.descriptor_id == "brightness")
    reference_result = next(
        item for item in reference.descriptors if item.descriptor_id == "brightness"
    )
    method = MethodMetadata(
        BRIGHTNESS_CORRELATE_METHOD_ID,
        BRIGHTNESS_CORRELATE_METHOD_VERSION,
        "Sprint 5 power-spectral-centroid brightness correlate compared source minus reference.",
    )
    if (
        source_result.state.status is ResultStatus.COMPUTED
        and reference_result.state.status is ResultStatus.COMPUTED
    ):
        source_value = float(source_result.estimate.value)
        reference_value = float(reference_result.estimate.value)
        state = ResultState(ResultStatus.COMPUTED)
        before = ScalarValue(source_value, UnitBasis.DECLARED_UNIT, unit="Hz")
        after = ScalarValue(reference_value, UnitBasis.DECLARED_UNIT, unit="Hz")
        delta = ScalarValue(source_value - reference_value, UnitBasis.DECLARED_UNIT, unit="Hz")
    else:
        state = ResultState(
            ResultStatus.INSUFFICIENT_EVIDENCE,
            "Brightness centroid requires positive analyzed spectral power in both programmes.",
        )
        before = after = delta = None
    return ReferenceEvidenceMeasurement(
        evidence_id="reference_brightness_centroid_delta",
        dimension_id=ReferenceEvidenceDimensionId.BRIGHTNESS_CENTROID_DELTA_HZ,
        state=state,
        source_value=before,
        reference_value=after,
        signed_delta=delta,
        sign_convention="source_centroid_hz - reference_centroid_hz",
        valid_interpretation="Difference in the Sprint 5 brightness correlate only.",
        method=method,
        source_analysis_method=method,
        reference_analysis_method=method,
        comparison_mode=mode,
        limitations=["Brightness-correlate delta is not brightness quality or perceptual failure."],
    )


def _energy_measurement(
    source: AudioData, reference: AudioData, mode
) -> ReferenceEvidenceMeasurement:
    method = MethodMetadata(
        "noisyne.reference_programme_energy_delta",
        "1.0.0",
        "Sum-square programme energy ratio across all samples and channels.",
    )
    if mode is ReferenceComparisonMode.SHAPE_ONLY:
        state = ResultState(
            ResultStatus.SKIPPED,
            "Shape-only mode intentionally excludes level-dependent programme energy.",
        )
        source_value = reference_value = delta = None
    else:
        source_energy = _sum_square(source.samples)
        reference_energy = _sum_square(reference.samples)
        if source_energy > 0.0 and reference_energy > 0.0:
            delta_db = float(10.0 * np.log10(source_energy / reference_energy))
            state = ResultState(ResultStatus.COMPUTED)
            source_value = ScalarValue(source_energy, UnitBasis.DECLARED_UNIT, unit=_ENERGY_UNIT)
            reference_value = ScalarValue(
                reference_energy, UnitBasis.DECLARED_UNIT, unit=_ENERGY_UNIT
            )
            delta = ScalarValue(delta_db, UnitBasis.DECLARED_UNIT, unit="dB")
        else:
            state = ResultState(
                ResultStatus.INSUFFICIENT_EVIDENCE,
                "Energy dB ratio requires positive source and reference programme energy.",
            )
            source_value = reference_value = delta = None
    return ReferenceEvidenceMeasurement(
        evidence_id="reference_programme_energy_delta",
        dimension_id=ReferenceEvidenceDimensionId.PROGRAMME_ENERGY_DELTA_DB,
        state=state,
        source_value=source_value,
        reference_value=reference_value,
        signed_delta=delta,
        sign_convention="10*log10(source_sum_square_energy/reference_sum_square_energy)",
        valid_interpretation="Digital sum-square programme energy difference only.",
        method=method,
        source_analysis_method=method,
        reference_analysis_method=method,
        comparison_mode=mode,
        assumptions=["Channels contribute by power summation without waveform downmix."],
        limitations=["Programme energy is not perceived loudness or loudness quality."],
    )


def _peak_measurement(
    source: AudioData, reference: AudioData, mode
) -> ReferenceEvidenceMeasurement:
    method = MethodMetadata(
        "noisyne.reference_sample_peak_delta",
        "1.0.0",
        "Maximum absolute floating sample amplitude; not reconstructed true peak.",
    )
    if mode is ReferenceComparisonMode.SHAPE_ONLY:
        state = ResultState(
            ResultStatus.SKIPPED,
            "Shape-only mode intentionally excludes level-dependent sample peak.",
        )
        source_value = reference_value = delta = None
    else:
        source_peak = float(np.max(np.abs(np.asarray(source.samples, dtype=np.float64))))
        reference_peak = float(np.max(np.abs(np.asarray(reference.samples, dtype=np.float64))))
        state = ResultState(ResultStatus.COMPUTED)
        source_value = ScalarValue(source_peak, UnitBasis.DECLARED_UNIT, unit=_PEAK_UNIT)
        reference_value = ScalarValue(reference_peak, UnitBasis.DECLARED_UNIT, unit=_PEAK_UNIT)
        delta = ScalarValue(source_peak - reference_peak, UnitBasis.DECLARED_UNIT, unit=_PEAK_UNIT)
    return ReferenceEvidenceMeasurement(
        evidence_id="reference_sample_peak_delta",
        dimension_id=ReferenceEvidenceDimensionId.SAMPLE_PEAK_DELTA_ABSOLUTE,
        state=state,
        source_value=source_value,
        reference_value=reference_value,
        signed_delta=delta,
        sign_convention="source_sample_peak_absolute - reference_sample_peak_absolute",
        valid_interpretation="Difference in maximum absolute sample value only.",
        method=method,
        source_analysis_method=method,
        reference_analysis_method=method,
        comparison_mode=mode,
        limitations=["Sample peak is not true peak, loudness, clipping, or quality."],
    )


def _accumulate_erb(frame_power: np.ndarray) -> FloatArray:
    values = np.sum(frame_power, axis=1, dtype=np.float64)
    if not np.all(np.isfinite(values)):
        raise ValueError("accumulated ERB power must be finite")
    values.setflags(write=False)
    return values


def _compare_erb(
    source,
    reference,
    source_bands,
    reference_bands,
    mode,
    source_analysis_method,
    reference_analysis_method,
):
    method = MethodMetadata(
        "noisyne.reference_erb_programme_power_delta",
        "1.0.0",
        "Per-channel accumulated Sprint 2 ERB power compared source minus reference in dB.",
    )
    compatible = source.shape == reference.shape and source_bands == reference_bands
    if not compatible:
        delta = np.empty((0, 0), dtype=np.float64)
        defined = np.empty((0, 0), dtype=np.bool_)
        delta.setflags(write=False)
        defined.setflags(write=False)
        summary = ReferenceErbPowerSummary(
            dimension_id=ReferenceEvidenceDimensionId.ERB_POWER_DISTRIBUTION_DELTA_DB,
            state=ResultState(
                ResultStatus.INSUFFICIENT_EVIDENCE,
                "ERB comparison requires identical channel count and Sprint 2 band definitions.",
            ),
            method=method,
            source_analysis_method=source_analysis_method,
            reference_analysis_method=reference_analysis_method,
            comparison_mode=mode,
            source_channel_count=source.shape[0],
            reference_channel_count=reference.shape[0],
            source_band_count=source.shape[1],
            reference_band_count=reference.shape[1],
            defined_value_count=0,
            limitations=[
                "No channel duplication, collapse, downmix, or band remapping is applied."
            ],
        )
        return summary, delta, defined

    source_values = np.array(source, copy=True)
    reference_values = np.array(reference, copy=True)
    sign_convention = "10*log10(source_erb_power/reference_erb_power)"
    if mode is ReferenceComparisonMode.SHAPE_ONLY:
        source_total = np.sum(source_values, axis=1, keepdims=True)
        reference_total = np.sum(reference_values, axis=1, keepdims=True)
        valid_channels = (source_total > 0.0) & (reference_total > 0.0)
        source_values = np.divide(
            source_values,
            source_total,
            out=np.zeros_like(source_values),
            where=source_total > 0.0,
        )
        reference_values = np.divide(
            reference_values,
            reference_total,
            out=np.zeros_like(reference_values),
            where=reference_total > 0.0,
        )
        defined = (source_values > 0.0) & (reference_values > 0.0) & valid_channels
        sign_convention = "10*log10(source_erb_power_fraction/reference_erb_power_fraction)"
    else:
        defined = (source_values > 0.0) & (reference_values > 0.0)
    delta = np.zeros_like(source_values)
    delta[defined] = 10.0 * np.log10(source_values[defined] / reference_values[defined])
    defined_count = int(np.count_nonzero(defined))
    limitations = [
        "ERB deltas are not masking, audibility, source attribution, or quality judgments.",
        "Undefined ratios retain a false runtime mask and zero placeholder.",
    ]
    if defined_count:
        defined_deltas = delta[defined]
        summary = ReferenceErbPowerSummary(
            dimension_id=ReferenceEvidenceDimensionId.ERB_POWER_DISTRIBUTION_DELTA_DB,
            state=ResultState(ResultStatus.COMPUTED),
            method=method,
            source_analysis_method=source_analysis_method,
            reference_analysis_method=reference_analysis_method,
            comparison_mode=mode,
            source_channel_count=source.shape[0],
            reference_channel_count=reference.shape[0],
            source_band_count=source.shape[1],
            reference_band_count=reference.shape[1],
            defined_value_count=defined_count,
            minimum_delta_db=float(np.min(defined_deltas)),
            maximum_delta_db=float(np.max(defined_deltas)),
            maximum_absolute_delta_db=float(np.max(np.abs(defined_deltas))),
            sign_convention=sign_convention,
            limitations=limitations,
        )
    else:
        summary = ReferenceErbPowerSummary(
            dimension_id=ReferenceEvidenceDimensionId.ERB_POWER_DISTRIBUTION_DELTA_DB,
            state=ResultState(
                ResultStatus.INSUFFICIENT_EVIDENCE,
                "No channel-by-band ratio had positive power in both programmes.",
            ),
            method=method,
            source_analysis_method=source_analysis_method,
            reference_analysis_method=reference_analysis_method,
            comparison_mode=mode,
            source_channel_count=source.shape[0],
            reference_channel_count=reference.shape[0],
            source_band_count=source.shape[1],
            reference_band_count=reference.shape[1],
            defined_value_count=0,
            sign_convention=sign_convention,
            limitations=limitations,
        )
    delta.setflags(write=False)
    defined.setflags(write=False)
    return summary, delta, defined


def _sum_square(samples) -> float:
    values = np.asarray(samples, dtype=np.float64)
    try:
        with np.errstate(over="raise", invalid="raise"):
            result = float(np.sum(np.square(values), dtype=np.float64))
    except FloatingPointError as exc:
        raise ValueError("programme energy is not representable") from exc
    if not np.isfinite(result) or result < 0.0:
        raise ValueError("programme energy must be finite and non-negative")
    return result


def _embedding_vector(values, name: str) -> FloatArray:
    array = np.asarray(values)
    if array.ndim != 1 or array.size == 0:
        raise ValueError(f"{name} must be a non-empty one-dimensional vector")
    if not np.issubdtype(array.dtype, np.number) or np.issubdtype(array.dtype, np.complexfloating):
        raise TypeError(f"{name} must contain real numeric values")
    result = np.asarray(array, dtype=np.float64)
    if not np.all(np.isfinite(result)):
        raise ValueError(f"{name} must contain finite values")
    return result


def _reference_method() -> MethodMetadata:
    return MethodMetadata(
        REFERENCE_FOUNDATION_METHOD_ID,
        REFERENCE_FOUNDATION_METHOD_VERSION,
        "Independent whole-programme objective evidence; no quality or recommendation score.",
    )


__all__ = [
    "EmbeddingCosineComparator",
    "ObjectiveReferenceComparator",
    "ReferenceEmbeddingProvider",
    "ReferenceRuntimeResult",
]
