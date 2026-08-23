from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from phasenox.audio.io.models import AudioData

from .auditory import AuditoryFrontend
from .auditory_contracts import (
    AUDITORY_FRONTEND_METHOD_ID,
    AUDITORY_FRONTEND_METHOD_VERSION,
    AuditoryFrontendConfig,
)
from .common import (
    Confidence,
    ConfidenceBasis,
    EvidenceSource,
    Measurement,
    MethodMetadata,
    PerceptualEvidence,
    ResultState,
    ResultStatus,
    ScalarValue,
    UnitBasis,
)
from .descriptor_contracts import (
    BRIGHTNESS_CORRELATE_METHOD_ID,
    BRIGHTNESS_CORRELATE_METHOD_VERSION,
)
from .descriptors import PerceptualDescriptorFoundation
from .results import TranslationResult, TranslationRiskDimension
from .transfer import ImpulseResponseTransfer, PlaybackTransferEngine
from .translation_contracts import (
    POLICY_CONDITIONED_TRANSLATION_RISK_METHOD_ID,
    POLICY_CONDITIONED_TRANSLATION_RISK_METHOD_VERSION,
    TRANSLATION_EVIDENCE_METHOD_ID,
    TRANSLATION_EVIDENCE_METHOD_VERSION,
    ErbPowerDistributionSummary,
    NominalFullScaleEvidence,
    PolicyConditionedTranslationRiskResult,
    TranslationAnalysisSupport,
    TranslationComparisonSummary,
    TranslationEvidenceDimensionId,
    TranslationEvidenceMeasurement,
    TranslationEvidenceResult,
    TranslationPolicyProvenance,
    TranslationRiskComparison,
    TranslationRiskCriterion,
    TranslationRiskPolicy,
)

FloatArray = NDArray[np.float64]
BoolArray = NDArray[np.bool_]

_PROGRAMME_ENERGY_METHOD_ID = "noisyne.digital_programme_energy_sum"
_PROGRAMME_ENERGY_METHOD_VERSION = "1.0.0"
_ENERGY_UNIT = "digital_sample_squared_sum"
_PEAK_UNIT = "digital_sample_amplitude"


@dataclass(frozen=True, slots=True)
class TranslationEvidenceRuntimeResult:
    """Compact transport evidence plus immutable channel-by-ERB runtime arrays."""

    evidence: TranslationEvidenceResult
    original_channel_erb_power: FloatArray
    transferred_channel_erb_power: FloatArray
    channel_erb_delta_db: FloatArray
    channel_erb_delta_defined: BoolArray

    def __post_init__(self) -> None:
        summary = self.evidence.erb_power_distribution
        shape = (summary.channel_count, summary.band_count)
        for array, name in (
            (self.original_channel_erb_power, "original_channel_erb_power"),
            (self.transferred_channel_erb_power, "transferred_channel_erb_power"),
            (self.channel_erb_delta_db, "channel_erb_delta_db"),
        ):
            _validate_runtime_array(array, name, shape=shape, dtype=np.dtype(np.float64))
        _validate_runtime_array(
            self.channel_erb_delta_defined,
            "channel_erb_delta_defined",
            shape=shape,
            dtype=np.dtype(np.bool_),
        )
        if int(np.count_nonzero(self.channel_erb_delta_defined)) != summary.defined_value_count:
            raise ValueError("ERB definition mask count does not match transport summary")


class TranslationEvidenceAnalyzer:
    """Compare original audio with one explicit Sprint 6 FIR transfer."""

    def __init__(self, frontend_config: AuditoryFrontendConfig | None = None) -> None:
        self._frontend_config = frontend_config or AuditoryFrontendConfig()
        self._transfer_engine = PlaybackTransferEngine()

    def analyze(
        self,
        audio: AudioData,
        transfer: ImpulseResponseTransfer,
        *,
        source_id: str | None = None,
    ) -> TranslationEvidenceRuntimeResult:
        if not isinstance(transfer, ImpulseResponseTransfer):
            raise TypeError(
                "translation comparison requires an executable ImpulseResponseTransfer; "
                "magnitude-only evidence cannot transform audio"
            )
        transferred = self._transfer_engine.apply(audio, transfer)
        original_frontend = AuditoryFrontend(self._frontend_config).analyze(audio)
        transferred_frontend = AuditoryFrontend(self._frontend_config).analyze(transferred.audio)
        original_descriptors = PerceptualDescriptorFoundation(self._frontend_config).analyze(audio)
        transferred_descriptors = PerceptualDescriptorFoundation(self._frontend_config).analyze(
            transferred.audio
        )

        brightness = _brightness_evidence(original_descriptors, transferred_descriptors)
        programme_energy = _programme_energy_evidence(audio, transferred.audio)
        original_band_power, transferred_band_power, delta_db, defined = _erb_evidence(
            original_frontend.auditory_band_power,
            transferred_frontend.auditory_band_power,
        )
        erb_summary = _erb_summary(
            delta_db,
            defined,
            channel_count=original_frontend.summary.channel_count,
            band_count=len(original_frontend.summary.auditory_bands),
        )
        original_peak = float(np.max(np.abs(np.asarray(audio.samples, dtype=np.float64))))
        full_scale = NominalFullScaleEvidence(
            original_peak_absolute=original_peak,
            transferred_peak_absolute=transferred.summary.output_peak_absolute,
            original_nominal_full_scale_exceeded=original_peak > 1.0,
            transferred_nominal_full_scale_exceeded=(
                transferred.summary.nominal_full_scale_exceeded
            ),
            clipping_applied=transferred.summary.clipping_applied,
        )
        evidence_method = MethodMetadata(
            method_id=TRANSLATION_EVIDENCE_METHOD_ID,
            version=TRANSLATION_EVIDENCE_METHOD_VERSION,
            description=(
                "Deterministic objective before/after evidence over the original full support "
                "and the complete Sprint 6 FIR output including its convolution tail."
            ),
        )
        comparison = TranslationComparisonSummary(
            method=evidence_method,
            target_profile=transfer.profile.profile_reference,
            transfer=transferred.summary.transfer,
            transfer_method=transferred.summary.method,
            transfer_provenance=transfer.profile.provenance,
            analysis_methods=[
                _auditory_method(),
                _brightness_method(),
                _programme_energy_method(),
            ],
            support=TranslationAnalysisSupport.FULL_TRANSFER_OUTPUT,
            original_sample_count=transferred.summary.input_sample_count,
            transferred_sample_count=transferred.summary.output_sample_count,
            transfer_tail_sample_count=(
                transferred.summary.output_sample_count - transferred.summary.input_sample_count
            ),
            channel_count=transferred.summary.channel_count,
            alignment="FIR tap zero aligns with source sample zero; full convolution tail included",
            source_id=source_id,
            assumptions=[
                "Input channels are independent programme channels; no ear or layout meaning is inferred.",
                "Programme energy and spectral power aggregate channels by summing power, never waveform downmixing.",
            ],
            limitations=[
                "Objective feature change is not an audible impairment or quality judgment.",
                "The Sprint 2 ERB-rate frontend is an engineering aggregation, not a hearing model.",
                "No source attribution, masking translation, loudness delta, PEAQ, or MUSHRA score is produced.",
            ],
        )
        transport = TranslationEvidenceResult(
            comparison=comparison,
            brightness_centroid=brightness,
            programme_energy=programme_energy,
            erb_power_distribution=erb_summary,
            nominal_full_scale=full_scale,
        )
        return TranslationEvidenceRuntimeResult(
            evidence=transport,
            original_channel_erb_power=original_band_power,
            transferred_channel_erb_power=transferred_band_power,
            channel_erb_delta_db=delta_db,
            channel_erb_delta_defined=defined,
        )


class TranslationRiskEvaluator:
    """Evaluate explicit criteria as booleans; no score, probability, or aggregation."""

    def evaluate(
        self,
        evidence: TranslationEvidenceResult,
        policy: TranslationRiskPolicy,
    ) -> PolicyConditionedTranslationRiskResult:
        if not isinstance(evidence, TranslationEvidenceResult):
            raise TypeError("evidence must be a TranslationEvidenceResult")
        if not isinstance(policy, TranslationRiskPolicy):
            raise TypeError("policy must be a TranslationRiskPolicy")

        dimensions = []
        computed_count = 0
        for criterion in policy.criteria:
            actual, method = _criterion_evidence(evidence, criterion.evidence_dimension_id)
            if actual is None:
                dimensions.append(
                    TranslationRiskDimension(
                        dimension_id=criterion.criterion_id,
                        display_name=criterion.description,
                        state=ResultState(
                            status=ResultStatus.INSUFFICIENT_EVIDENCE,
                            reason=(
                                f"{criterion.evidence_dimension_id.value} is undefined for this "
                                "before/after signal pair."
                            ),
                        ),
                        risk=None,
                        confidence=Confidence(
                            score=None,
                            basis=ConfidenceBasis.UNKNOWN,
                            reason="No policy decision is possible without defined objective evidence.",
                        ),
                        limitations=[
                            "Undefined logarithmic ratios are not replaced with finite placeholders."
                        ],
                    )
                )
                continue
            _validate_matching_unit(actual, criterion.threshold)
            exceeded = _compare(actual, criterion)
            computed_count += 1
            dimensions.append(_risk_dimension(criterion, actual, method, exceeded))

        method = MethodMetadata(
            method_id=POLICY_CONDITIONED_TRANSLATION_RISK_METHOD_ID,
            version=POLICY_CONDITIONED_TRANSLATION_RISK_METHOD_VERSION,
            description=(
                "Boolean evaluation of explicit provenance-backed criteria; not a probability, "
                "normalized score, or aggregate quality judgment."
            ),
        )
        if computed_count:
            state = ResultState(status=ResultStatus.COMPUTED)
            result_dimensions = dimensions
        else:
            state = ResultState(
                status=ResultStatus.INSUFFICIENT_EVIDENCE,
                reason="No policy criterion had defined, unit-compatible objective evidence.",
            )
            result_dimensions = []
        transfer_profile = evidence.comparison.transfer.profile
        result = TranslationResult(
            target_profile=evidence.comparison.target_profile,
            state=state,
            dimensions=result_dimensions,
            aggregate_risk=None,
            evidence=[
                PerceptualEvidence(
                    evidence_id="translation_policy_identity",
                    source=_policy_evidence_source(policy.provenance),
                    origin=policy.source,
                    reference=f"{policy.policy_id}@{policy.version}",
                    method=method,
                    note=(
                        f"Policy evaluated against transfer {transfer_profile.transfer_id}@"
                        f"{transfer_profile.version}; boolean threshold outcomes only."
                    ),
                )
            ],
            confidence=Confidence(
                score=None,
                basis=ConfidenceBasis.UNKNOWN,
                reason=(
                    "Evaluation is deterministic, but no probability or universal confidence "
                    "about listener outcomes is claimed."
                ),
            ),
            method=method,
            limitations=[
                "Policy threshold exceeded does not mean probability of translation failure.",
                "Independent dimensions are not aggregated.",
            ],
        )
        return PolicyConditionedTranslationRiskResult(
            policy=policy,
            evidence=evidence,
            translation=result,
        )


def _brightness_evidence(original, transferred) -> TranslationEvidenceMeasurement:
    original_result = next(
        item for item in original.descriptors if item.descriptor_id == "brightness"
    )
    transferred_result = next(
        item for item in transferred.descriptors if item.descriptor_id == "brightness"
    )
    method = _brightness_method()
    if (
        original_result.state.status is ResultStatus.COMPUTED
        and transferred_result.state.status is ResultStatus.COMPUTED
    ):
        original_value = float(original_result.estimate.value)
        transferred_value = float(transferred_result.estimate.value)
        delta = transferred_value - original_value
        state = ResultState(status=ResultStatus.COMPUTED)
        before = ScalarValue(original_value, UnitBasis.DECLARED_UNIT, unit="Hz")
        after = ScalarValue(transferred_value, UnitBasis.DECLARED_UNIT, unit="Hz")
        signed = ScalarValue(delta, UnitBasis.DECLARED_UNIT, unit="Hz")
    else:
        state = ResultState(
            status=ResultStatus.INSUFFICIENT_EVIDENCE,
            reason="Brightness centroid requires positive analyzed spectral power in both signals.",
        )
        before = after = signed = None
    return TranslationEvidenceMeasurement(
        evidence_id="brightness_centroid_before_after",
        quantity_id=TranslationEvidenceDimensionId.BRIGHTNESS_CENTROID_SHIFT_HZ.value,
        state=state,
        original_value=before,
        transferred_value=after,
        signed_delta=signed,
        sign_convention="transferred_centroid_hz - original_centroid_hz",
        valid_interpretation="Change in the Sprint 5 power-spectral-centroid brightness correlate.",
        method=method,
        assumptions=[
            "Original and full transfer output use the same Sprint 2 frontend configuration."
        ],
        limitations=[
            "Spectral centroid shift is not perceived-brightness failure or audible impairment."
        ],
    )


def _programme_energy_evidence(
    original_audio: AudioData, transferred_audio: AudioData
) -> TranslationEvidenceMeasurement:
    original_energy = _sum_square_energy(original_audio.samples)
    transferred_energy = _sum_square_energy(transferred_audio.samples)
    method = _programme_energy_method()
    if original_energy > 0.0 and transferred_energy > 0.0:
        try:
            with np.errstate(over="raise", under="raise", invalid="raise", divide="raise"):
                delta_db = float(
                    (10.0 / np.log(10.0)) * (np.log(transferred_energy) - np.log(original_energy))
                )
        except FloatingPointError as exc:
            raise ValueError("programme energy ratio is not representable") from exc
        state = ResultState(status=ResultStatus.COMPUTED)
        before = ScalarValue(original_energy, UnitBasis.DECLARED_UNIT, unit=_ENERGY_UNIT)
        after = ScalarValue(transferred_energy, UnitBasis.DECLARED_UNIT, unit=_ENERGY_UNIT)
        signed = ScalarValue(delta_db, UnitBasis.DECLARED_UNIT, unit="dB")
    else:
        state = ResultState(
            status=ResultStatus.INSUFFICIENT_EVIDENCE,
            reason=(
                "Programme energy dB ratio is undefined unless both original and transferred "
                "energies are strictly positive."
            ),
        )
        before = after = signed = None
    return TranslationEvidenceMeasurement(
        evidence_id="programme_energy_before_after",
        quantity_id=TranslationEvidenceDimensionId.PROGRAMME_ENERGY_DELTA_DB.value,
        state=state,
        original_value=before,
        transferred_value=after,
        signed_delta=signed,
        sign_convention="10*log10(transferred_sum_square_energy/original_sum_square_energy)",
        valid_interpretation="Digital programme energy change across all samples and channels.",
        method=method,
        assumptions=[
            "Channels are aggregated by summing squared sample amplitudes without downmix."
        ],
        limitations=["Digital programme energy change is not perceived loudness change."],
    )


def _sum_square_energy(samples) -> float:
    values = np.asarray(samples, dtype=np.float64)
    try:
        with np.errstate(over="raise", under="raise", invalid="raise"):
            energy = float(np.sum(np.square(values), dtype=np.float64))
    except FloatingPointError as exc:
        raise ValueError("programme energy is not representable as float64") from exc
    if not np.isfinite(energy) or energy < 0.0:
        raise ValueError("programme energy must be finite and non-negative")
    return energy


def _erb_evidence(
    original_frame_power: FloatArray,
    transferred_frame_power: FloatArray,
) -> tuple[FloatArray, FloatArray, FloatArray, BoolArray]:
    if original_frame_power.shape[0] != transferred_frame_power.shape[0] or (
        original_frame_power.shape[2] != transferred_frame_power.shape[2]
    ):
        raise ValueError("original and transferred ERB channel/band shapes must match")
    try:
        with np.errstate(over="raise", under="raise", invalid="raise"):
            original = np.sum(original_frame_power, axis=1, dtype=np.float64)
            transferred = np.sum(transferred_frame_power, axis=1, dtype=np.float64)
        defined = (original > 0.0) & (transferred > 0.0)
        delta = np.zeros_like(original)
        with np.errstate(over="raise", under="raise", invalid="raise", divide="raise"):
            delta[defined] = (10.0 / np.log(10.0)) * (
                np.log(transferred[defined]) - np.log(original[defined])
            )
    except FloatingPointError as exc:
        raise ValueError("ERB power comparison is not representable") from exc
    for array in (original, transferred, delta):
        if not np.all(np.isfinite(array)):
            raise ValueError("ERB power comparison produced non-finite values")
        array.setflags(write=False)
    defined.setflags(write=False)
    return original, transferred, delta, defined


def _erb_summary(
    delta: FloatArray,
    defined: BoolArray,
    *,
    channel_count: int,
    band_count: int,
) -> ErbPowerDistributionSummary:
    defined_count = int(np.count_nonzero(defined))
    method = MethodMetadata(
        method_id="noisyne.sprint2_erb_programme_power_delta",
        version="1.0.0",
        description=(
            "Per-channel Sprint 2 ERB-band frame-power sums compared in dB; no hearing, "
            "masking, or audibility model."
        ),
    )
    limitations = [
        "Undefined band ratios use a false definition mask and a runtime-only zero placeholder.",
        "ERB power delta is not audibility loss, masking, or source attribution.",
    ]
    if defined_count:
        values = delta[defined]
        return ErbPowerDistributionSummary(
            state=ResultState(status=ResultStatus.COMPUTED),
            method=method,
            channel_count=channel_count,
            band_count=band_count,
            defined_value_count=defined_count,
            minimum_delta_db=float(np.min(values)),
            maximum_delta_db=float(np.max(values)),
            maximum_absolute_delta_db=float(np.max(np.abs(values))),
            limitations=limitations,
        )
    return ErbPowerDistributionSummary(
        state=ResultState(
            status=ResultStatus.INSUFFICIENT_EVIDENCE,
            reason="No channel-by-ERB band had positive power in both signals.",
        ),
        method=method,
        channel_count=channel_count,
        band_count=band_count,
        defined_value_count=0,
        limitations=limitations,
    )


def _criterion_evidence(
    evidence: TranslationEvidenceResult,
    dimension_id: TranslationEvidenceDimensionId,
) -> tuple[ScalarValue | None, MethodMetadata]:
    if dimension_id is TranslationEvidenceDimensionId.BRIGHTNESS_CENTROID_SHIFT_HZ:
        return evidence.brightness_centroid.signed_delta, evidence.brightness_centroid.method
    if dimension_id is TranslationEvidenceDimensionId.PROGRAMME_ENERGY_DELTA_DB:
        return evidence.programme_energy.signed_delta, evidence.programme_energy.method
    if dimension_id is TranslationEvidenceDimensionId.ERB_BAND_MAXIMUM_ABSOLUTE_DELTA_DB:
        summary = evidence.erb_power_distribution
        value = (
            ScalarValue(
                summary.maximum_absolute_delta_db,
                UnitBasis.DECLARED_UNIT,
                unit="dB",
            )
            if summary.state.status is ResultStatus.COMPUTED
            else None
        )
        return value, summary.method
    if dimension_id is TranslationEvidenceDimensionId.TRANSFERRED_PEAK_ABSOLUTE:
        return (
            ScalarValue(
                evidence.nominal_full_scale.transferred_peak_absolute,
                UnitBasis.DECLARED_UNIT,
                unit=_PEAK_UNIT,
            ),
            evidence.comparison.transfer_method,
        )
    raise ValueError(f"unknown evidence dimension: {dimension_id!r}")


def _validate_matching_unit(actual: ScalarValue, threshold: ScalarValue) -> None:
    if (
        actual.unit_basis is not threshold.unit_basis
        or actual.unit != threshold.unit
        or actual.scale != threshold.scale
        or actual.normalized != threshold.normalized
    ):
        raise ValueError("criterion threshold unit/scale does not match its evidence dimension")


def _compare(actual: ScalarValue, criterion: TranslationRiskCriterion) -> bool:
    value = float(actual.value)
    threshold = float(criterion.threshold.value)
    operator = criterion.comparison
    if operator is TranslationRiskComparison.GREATER_THAN:
        return value > threshold
    if operator is TranslationRiskComparison.GREATER_THAN_OR_EQUAL:
        return value >= threshold
    if operator is TranslationRiskComparison.LESS_THAN:
        return value < threshold
    if operator is TranslationRiskComparison.LESS_THAN_OR_EQUAL:
        return value <= threshold
    if operator is TranslationRiskComparison.ABSOLUTE_GREATER_THAN:
        return abs(value) > threshold
    if operator is TranslationRiskComparison.ABSOLUTE_GREATER_THAN_OR_EQUAL:
        return abs(value) >= threshold
    raise ValueError(f"unsupported comparison operator: {operator!r}")


def _risk_dimension(
    criterion: TranslationRiskCriterion,
    actual: ScalarValue,
    method: MethodMetadata,
    exceeded: bool,
) -> TranslationRiskDimension:
    measurement = Measurement(
        measurement_id=f"{criterion.criterion_id}_actual_value",
        name=f"Actual value for {criterion.evidence_dimension_id.value}",
        value=actual,
        source=TRANSLATION_EVIDENCE_METHOD_ID,
        method=method,
        note=criterion.direction_semantics,
    )
    return TranslationRiskDimension(
        dimension_id=criterion.criterion_id,
        display_name=criterion.description,
        state=ResultState(status=ResultStatus.COMPUTED),
        risk=ScalarValue(
            value=exceeded,
            unit_basis=UnitBasis.NAMED_SCALE,
            scale="declared_policy_threshold_exceeded",
        ),
        evidence=[
            PerceptualEvidence(
                evidence_id=f"{criterion.criterion_id}_objective_evidence",
                source=EvidenceSource.MEASUREMENT,
                measurement=measurement,
                method=method,
            ),
            PerceptualEvidence(
                evidence_id=f"{criterion.criterion_id}_policy_criterion",
                source=_policy_evidence_source(criterion.provenance),
                origin=criterion.source,
                reference=f"{criterion.criterion_id}@{criterion.criterion_version}",
                note=(
                    f"Operator {criterion.comparison.value}; threshold "
                    f"{criterion.threshold.value} {criterion.threshold.unit or criterion.threshold.scale}."
                ),
            ),
        ],
        confidence=Confidence(
            score=None,
            basis=ConfidenceBasis.UNKNOWN,
            reason=(
                "The comparison is deterministic; no probability of audible or translation "
                "failure is estimated."
            ),
        ),
        limitations=[
            "Boolean means only that the declared criterion was exceeded.",
            *criterion.limitations,
        ],
    )


def _policy_evidence_source(provenance: TranslationPolicyProvenance) -> EvidenceSource:
    if provenance in (
        TranslationPolicyProvenance.USER_DECLARED,
        TranslationPolicyProvenance.PROJECT_DECLARED,
    ):
        return EvidenceSource.USER_INPUT
    return EvidenceSource.REFERENCE


def _auditory_method() -> MethodMetadata:
    return MethodMetadata(
        method_id=AUDITORY_FRONTEND_METHOD_ID,
        version=AUDITORY_FRONTEND_METHOD_VERSION,
        description="Sprint 2 channel-preserving spectral and ERB-rate frontend.",
    )


def _brightness_method() -> MethodMetadata:
    return MethodMetadata(
        method_id=BRIGHTNESS_CORRELATE_METHOD_ID,
        version=BRIGHTNESS_CORRELATE_METHOD_VERSION,
        description="Sprint 5 power-spectral-centroid brightness correlate.",
    )


def _programme_energy_method() -> MethodMetadata:
    return MethodMetadata(
        method_id=_PROGRAMME_ENERGY_METHOD_ID,
        version=_PROGRAMME_ENERGY_METHOD_VERSION,
        description="Sum of squared floating sample amplitudes across all samples and channels.",
    )


def _validate_runtime_array(
    array: np.ndarray,
    name: str,
    *,
    shape: tuple[int, int],
    dtype: np.dtype,
) -> None:
    if not isinstance(array, np.ndarray):
        raise TypeError(f"{name} must be a NumPy array")
    if array.shape != shape:
        raise ValueError(f"{name} must have shape {shape}")
    if array.dtype != dtype:
        raise ValueError(f"{name} must use {dtype} dtype")
    if dtype == np.dtype(np.float64) and not np.all(np.isfinite(array)):
        raise ValueError(f"{name} must contain only finite values")
    if array.flags.writeable:
        raise ValueError(f"{name} must be read-only")


__all__ = [
    "TranslationEvidenceAnalyzer",
    "TranslationEvidenceRuntimeResult",
    "TranslationRiskEvaluator",
]
