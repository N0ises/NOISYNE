from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

from phasenox.audio.io.models import AudioData, AudioMetadata
from phasenox.perception import (
    PERCEPTUAL_SCHEMA_VERSION,
    POLICY_CONDITIONED_TRANSLATION_RISK_METHOD_ID,
    TRANSLATION_EVIDENCE_METHOD_ID,
    ConfidenceBasis,
    ExtrapolationPolicy,
    FrequencyRange,
    MagnitudeInterpolationPolicy,
    PlaybackProfileReference,
    PolicyConditionedTranslationRiskResult,
    ResultState,
    ResultStatus,
    ScalarValue,
    TransferAcousticScope,
    TransferChannelTopology,
    TransferGainBasis,
    TransferKind,
    TransferPhaseBasis,
    TransferProvenance,
    TranslationAnalysisSupport,
    TranslationEvidenceDimensionId,
    TranslationEvidenceResult,
    TranslationPolicyProvenance,
    TranslationResult,
    TranslationRiskComparison,
    TranslationRiskCriterion,
    TranslationRiskPolicy,
    UnitBasis,
)
from phasenox.perception.transfer import ImpulseResponseTransfer, MagnitudeResponseEvidence
from phasenox.perception.transfer_contracts import PlaybackTransferProfile
from phasenox.perception.translation import (
    TranslationEvidenceAnalyzer,
    TranslationEvidenceRuntimeResult,
    TranslationRiskEvaluator,
)
from phasenox.runtime.capabilities import CapabilityStatus, registry


def _readonly(values: object) -> np.ndarray:
    result = np.asarray(values, dtype=np.float64)
    result.setflags(write=False)
    return result


def _audio(samples: object, *, sample_rate: int = 48_000) -> AudioData:
    array = np.asarray(samples)
    channels = 1 if array.ndim == 1 else array.shape[1]
    return AudioData(
        samples=array,
        metadata=AudioMetadata(
            path=Path("translation.wav"),
            filename="translation.wav",
            extension=".wav",
            format="WAV",
            codec=None,
            sample_rate=sample_rate,
            channels=channels,
            duration=array.shape[0] / sample_rate,
            bit_depth=24,
            file_size=array.nbytes,
        ),
    )


def _profile(
    *,
    sample_rate: int = 48_000,
    kind: TransferKind = TransferKind.IMPULSE_RESPONSE,
    topology: TransferChannelTopology = TransferChannelTopology.CHANNEL_INDEPENDENT_SHARED,
    channels: int | None = None,
) -> PlaybackTransferProfile:
    magnitude = kind is TransferKind.MAGNITUDE_RESPONSE
    return PlaybackTransferProfile(
        transfer_id="translation.fixture.transfer",
        version="1.0.0",
        profile_reference=PlaybackProfileReference("translation.fixture.target", "1.0.0"),
        provenance=TransferProvenance.ENGINEERING_APPROXIMATION,
        evidence_source="Sprint 7 analytical fixture",
        evidence_version="1.0.0",
        transfer_kind=kind,
        gain_basis=TransferGainBasis.DIGITAL_AMPLITUDE_RATIO,
        phase_basis=(
            TransferPhaseBasis.MAGNITUDE_ONLY
            if magnitude
            else TransferPhaseBasis.IMPULSE_RESPONSE_CONTAINS_PHASE
        ),
        acoustic_scope=TransferAcousticScope.ENGINEERING_TEST_FIXTURE,
        channel_topology=topology,
        measurement_conditions="Deterministic analytical fixture",
        normalization_reference="Digital amplitude ratio; unity is 1.0",
        time_origin_alignment=("Not applicable" if magnitude else "Tap zero at source sample zero"),
        valid_frequency_range=FrequencyRange(100.0, 1000.0) if magnitude else None,
        sample_rate_hz=None if magnitude else sample_rate,
        expected_input_channels=channels,
        interpolation_policy=MagnitudeInterpolationPolicy.LOG_FREQUENCY_DB if magnitude else None,
        extrapolation_policy=ExtrapolationPolicy.REJECT if magnitude else None,
    )


def _transfer(
    taps: object,
    *,
    sample_rate: int = 48_000,
    topology: TransferChannelTopology = TransferChannelTopology.CHANNEL_INDEPENDENT_SHARED,
    channels: int | None = None,
) -> ImpulseResponseTransfer:
    array = np.asarray(taps, dtype=np.float64)
    if array.ndim == 1:
        array = array[np.newaxis, :]
    array.setflags(write=False)
    return ImpulseResponseTransfer(
        _profile(
            sample_rate=sample_rate,
            topology=topology,
            channels=channels,
        ),
        array,
    )


def _criterion(
    dimension: TranslationEvidenceDimensionId,
    threshold: float,
    unit: str,
    *,
    comparison: TranslationRiskComparison = TranslationRiskComparison.GREATER_THAN,
    criterion_id: str = "fixture.criterion",
    provenance: TranslationPolicyProvenance = TranslationPolicyProvenance.USER_DECLARED,
) -> TranslationRiskCriterion:
    return TranslationRiskCriterion(
        criterion_id=criterion_id,
        criterion_version="1.0.0",
        evidence_dimension_id=dimension,
        comparison=comparison,
        threshold=ScalarValue(threshold, UnitBasis.DECLARED_UNIT, unit=unit),
        direction_semantics="The named comparison is applied exactly to the signed evidence value.",
        provenance=provenance,
        source="Test caller",
        description="Explicit analytical test criterion",
    )


def _policy(*criteria: TranslationRiskCriterion) -> TranslationRiskPolicy:
    provenance = criteria[0].provenance
    return TranslationRiskPolicy(
        policy_id="fixture.policy",
        version="1.0.0",
        provenance=provenance,
        source="Test caller",
        description="No universal interpretation; deterministic test thresholds only",
        criteria=list(criteria),
    )


@pytest.fixture(scope="module")
def source_audio() -> AudioData:
    indexes = np.arange(12_000, dtype=np.float64)
    signal = 0.35 * np.sin(2.0 * np.pi * 500.0 * indexes / 48_000.0)
    signal += 0.2 * np.sin(2.0 * np.pi * 6_000.0 * indexes / 48_000.0)
    return _audio(signal)


@pytest.fixture(scope="module")
def identity(source_audio: AudioData) -> TranslationEvidenceRuntimeResult:
    return TranslationEvidenceAnalyzer().analyze(
        source_audio, _transfer([1.0]), source_id="fixture.source"
    )


@pytest.fixture(scope="module")
def half_gain(source_audio: AudioData) -> TranslationEvidenceRuntimeResult:
    return TranslationEvidenceAnalyzer().analyze(source_audio, _transfer([0.5]))


@pytest.fixture(scope="module")
def double_gain(source_audio: AudioData) -> TranslationEvidenceRuntimeResult:
    return TranslationEvidenceAnalyzer().analyze(source_audio, _transfer([2.0]))


def test_frozen_sprint_1_translation_contract_and_schema_are_unchanged() -> None:
    result = TranslationResult(
        target_profile=PlaybackProfileReference("target", "1"),
        state=ResultState(
            status=ResultStatus.INSUFFICIENT_EVIDENCE,
            reason="No explicit policy supplied",
        ),
    )
    assert TranslationResult.from_dict(result.to_dict()) == result
    assert PERCEPTUAL_SCHEMA_VERSION == "1.0.0"


def test_identity_evidence_is_exact_and_retains_identity(identity) -> None:
    evidence = identity.evidence
    assert evidence.comparison.method.method_id == TRANSLATION_EVIDENCE_METHOD_ID
    assert evidence.comparison.source_id == "fixture.source"
    assert evidence.comparison.target_profile == PlaybackProfileReference(
        "translation.fixture.target", "1.0.0"
    )
    assert evidence.comparison.transfer.profile.transfer_id == "translation.fixture.transfer"
    assert evidence.comparison.transfer_provenance is TransferProvenance.ENGINEERING_APPROXIMATION
    assert evidence.comparison.support is TranslationAnalysisSupport.FULL_TRANSFER_OUTPUT
    assert evidence.brightness_centroid.signed_delta.value == 0.0
    assert evidence.programme_energy.signed_delta.value == 0.0
    np.testing.assert_array_equal(
        identity.channel_erb_delta_db, np.zeros_like(identity.channel_erb_delta_db)
    )


def test_half_gain_expected_values_and_shape_invariance(half_gain) -> None:
    expected = 10.0 * np.log10(0.25)
    assert half_gain.evidence.programme_energy.signed_delta.value == pytest.approx(
        expected, abs=1e-12
    )
    assert half_gain.evidence.brightness_centroid.signed_delta.value == pytest.approx(
        0.0, abs=1e-10
    )
    np.testing.assert_allclose(
        half_gain.channel_erb_delta_db[half_gain.channel_erb_delta_defined],
        expected,
        atol=1e-11,
    )
    summary = half_gain.evidence.erb_power_distribution
    assert summary.maximum_delta_db - summary.minimum_delta_db == pytest.approx(0.0, abs=1e-11)


def test_double_gain_expected_energy(double_gain) -> None:
    assert double_gain.evidence.programme_energy.signed_delta.value == pytest.approx(
        10.0 * np.log10(4.0), abs=1e-12
    )


def test_frequency_selective_fir_changes_distribution_and_centroid(source_audio) -> None:
    result = TranslationEvidenceAnalyzer().analyze(source_audio, _transfer([0.5, -0.5]))
    assert result.evidence.brightness_centroid.signed_delta.value > 0.0
    summary = result.evidence.erb_power_distribution
    assert summary.maximum_delta_db > summary.minimum_delta_db
    assert summary.maximum_absolute_delta_db > 0.0


def test_identity_positive_threshold_is_not_exceeded(identity) -> None:
    criterion = _criterion(
        TranslationEvidenceDimensionId.BRIGHTNESS_CENTROID_SHIFT_HZ,
        1.0,
        "Hz",
        comparison=TranslationRiskComparison.ABSOLUTE_GREATER_THAN,
    )
    evaluated = TranslationRiskEvaluator().evaluate(identity.evidence, _policy(criterion))
    assert evaluated.translation.dimensions[0].risk.value is False
    assert evaluated.translation.aggregate_risk is None
    assert evaluated.translation.method.method_id == POLICY_CONDITIONED_TRANSLATION_RISK_METHOD_ID


def test_threshold_boundary_operators_are_explicit(double_gain) -> None:
    actual = float(double_gain.evidence.programme_energy.signed_delta.value)
    cases = (
        (TranslationRiskComparison.GREATER_THAN, actual - 0.1, True),
        (TranslationRiskComparison.GREATER_THAN, actual, False),
        (TranslationRiskComparison.GREATER_THAN, actual + 0.1, False),
        (TranslationRiskComparison.GREATER_THAN_OR_EQUAL, actual, True),
        (TranslationRiskComparison.LESS_THAN_OR_EQUAL, actual, True),
    )
    for index, (operator, threshold, expected) in enumerate(cases):
        criterion = _criterion(
            TranslationEvidenceDimensionId.PROGRAMME_ENERGY_DELTA_DB,
            threshold,
            "dB",
            comparison=operator,
            criterion_id=f"boundary.{index}",
        )
        result = TranslationRiskEvaluator().evaluate(double_gain.evidence, _policy(criterion))
        assert result.translation.dimensions[0].risk.value is expected


def test_absolute_operator_uses_signed_delta_magnitude(half_gain) -> None:
    criterion = _criterion(
        TranslationEvidenceDimensionId.PROGRAMME_ENERGY_DELTA_DB,
        6.0,
        "dB",
        comparison=TranslationRiskComparison.ABSOLUTE_GREATER_THAN,
    )
    result = TranslationRiskEvaluator().evaluate(half_gain.evidence, _policy(criterion))
    assert result.translation.dimensions[0].risk.value is True


def test_missing_or_mismatched_policy_provenance_is_rejected() -> None:
    criterion = _criterion(TranslationEvidenceDimensionId.PROGRAMME_ENERGY_DELTA_DB, 1.0, "dB")
    with pytest.raises(ValueError, match="source"):
        replace(criterion, source=" ")
    with pytest.raises(TypeError, match="provenance"):
        replace(criterion, provenance=None)
    with pytest.raises(ValueError, match="provenance"):
        replace(
            _policy(criterion),
            provenance=TranslationPolicyProvenance.PROJECT_DECLARED,
        )


def test_unit_mismatch_is_rejected(identity) -> None:
    criterion = _criterion(TranslationEvidenceDimensionId.BRIGHTNESS_CENTROID_SHIFT_HZ, 1.0, "dB")
    with pytest.raises(ValueError, match="unit/scale"):
        TranslationRiskEvaluator().evaluate(identity.evidence, _policy(criterion))


def test_unknown_evidence_dimension_is_rejected() -> None:
    criterion = _criterion(TranslationEvidenceDimensionId.PROGRAMME_ENERGY_DELTA_DB, 1.0, "dB")
    with pytest.raises(TypeError, match="TranslationEvidenceDimensionId"):
        replace(criterion, evidence_dimension_id="unknown")


def test_silence_has_truthful_undefined_ratios_and_defined_zero_peak() -> None:
    result = TranslationEvidenceAnalyzer().analyze(_audio(np.zeros(4096)), _transfer([1.0]))
    evidence = result.evidence
    assert evidence.brightness_centroid.state.status is ResultStatus.INSUFFICIENT_EVIDENCE
    assert evidence.programme_energy.state.status is ResultStatus.INSUFFICIENT_EVIDENCE
    assert evidence.erb_power_distribution.state.status is ResultStatus.INSUFFICIENT_EVIDENCE
    assert not np.any(result.channel_erb_delta_defined)
    np.testing.assert_array_equal(
        result.channel_erb_delta_db, np.zeros_like(result.channel_erb_delta_db)
    )
    assert evidence.nominal_full_scale.original_peak_absolute == 0.0
    assert evidence.nominal_full_scale.transferred_peak_absolute == 0.0


def test_zero_output_ratio_is_undefined_without_infinity(source_audio) -> None:
    result = TranslationEvidenceAnalyzer().analyze(source_audio, _transfer([0.0]))
    assert result.evidence.programme_energy.state.status is ResultStatus.INSUFFICIENT_EVIDENCE
    assert result.evidence.programme_energy.signed_delta is None
    assert not np.any(result.channel_erb_delta_defined)
    assert np.all(np.isfinite(result.channel_erb_delta_db))


def test_all_undefined_policy_evidence_returns_insufficient_without_risk_dimensions() -> None:
    silence = TranslationEvidenceAnalyzer().analyze(_audio(np.zeros(4096)), _transfer([1.0]))
    criterion = _criterion(TranslationEvidenceDimensionId.PROGRAMME_ENERGY_DELTA_DB, 1.0, "dB")
    result = TranslationRiskEvaluator().evaluate(silence.evidence, _policy(criterion))
    assert result.translation.state.status is ResultStatus.INSUFFICIENT_EVIDENCE
    assert result.translation.dimensions == []
    assert result.translation.aggregate_risk is None


@pytest.mark.parametrize("channels", [1, 2])
def test_mono_and_stereo_channel_shapes_are_preserved(channels: int) -> None:
    base = np.sin(2.0 * np.pi * 1000.0 * np.arange(8192) / 48_000.0)
    samples = base if channels == 1 else np.column_stack((base, 0.5 * base))
    result = TranslationEvidenceAnalyzer().analyze(_audio(samples), _transfer([1.0]))
    assert result.original_channel_erb_power.shape[0] == channels
    assert result.evidence.comparison.channel_count == channels


def test_opposite_phase_stereo_does_not_cancel() -> None:
    base = np.sin(2.0 * np.pi * 1000.0 * np.arange(8192) / 48_000.0)
    result = TranslationEvidenceAnalyzer().analyze(
        _audio(np.column_stack((base, -base))), _transfer([1.0])
    )
    assert result.evidence.programme_energy.original_value.value > 0.0
    assert result.evidence.programme_energy.signed_delta.value == 0.0
    assert result.original_channel_erb_power.shape[0] == 2


def test_full_fir_tail_is_included_and_never_silently_truncated() -> None:
    result = TranslationEvidenceAnalyzer().analyze(_audio([1.0]), _transfer([1.0, 0.5]))
    comparison = result.evidence.comparison
    assert comparison.original_sample_count == 1
    assert comparison.transferred_sample_count == 2
    assert comparison.transfer_tail_sample_count == 1
    assert result.evidence.programme_energy.signed_delta.value == pytest.approx(
        10.0 * np.log10(1.25), abs=1e-12
    )


def test_magnitude_only_evidence_cannot_enter_executable_path(source_audio) -> None:
    magnitude = MagnitudeResponseEvidence(
        _profile(kind=TransferKind.MAGNITUDE_RESPONSE),
        _readonly([100.0, 1000.0]),
        _readonly([0.0, -3.0]),
    )
    with pytest.raises(TypeError, match="magnitude-only"):
        TranslationEvidenceAnalyzer().analyze(source_audio, magnitude)


def test_runtime_arrays_are_float64_bool_finite_and_read_only(identity) -> None:
    for array in (
        identity.original_channel_erb_power,
        identity.transferred_channel_erb_power,
        identity.channel_erb_delta_db,
    ):
        assert array.dtype == np.float64
        assert np.all(np.isfinite(array))
        assert not array.flags.writeable
    assert identity.channel_erb_delta_defined.dtype == np.bool_
    assert not identity.channel_erb_delta_defined.flags.writeable


def test_json_round_trip_excludes_runtime_arrays(identity) -> None:
    payload = identity.evidence.to_dict()
    assert TranslationEvidenceResult.from_dict(payload) == identity.evidence
    serialized = json.dumps(payload)
    for name in (
        "original_channel_erb_power",
        "transferred_channel_erb_power",
        "channel_erb_delta_db",
        "channel_erb_delta_defined",
    ):
        assert name not in serialized
    assert payload["erb_power_distribution"]["arrays_serialized"] is False


def test_policy_result_round_trip_is_boolean_non_normalized_and_non_aggregate(identity) -> None:
    criterion = _criterion(
        TranslationEvidenceDimensionId.TRANSFERRED_PEAK_ABSOLUTE,
        0.1,
        "digital_sample_amplitude",
    )
    result = TranslationRiskEvaluator().evaluate(identity.evidence, _policy(criterion))
    payload = result.to_dict()
    assert PolicyConditionedTranslationRiskResult.from_dict(payload) == result
    risk = result.translation.dimensions[0].risk
    assert type(risk.value) is bool
    assert risk.scale == "declared_policy_threshold_exceeded"
    assert not risk.normalized
    assert result.translation.aggregate_risk is None
    assert result.translation.confidence.score is None
    assert result.translation.confidence.basis is ConfidenceBasis.UNKNOWN


def test_policy_free_analysis_emits_evidence_and_no_risk(identity) -> None:
    assert isinstance(identity.evidence, TranslationEvidenceResult)
    assert not hasattr(identity, "translation")
    assert not hasattr(identity.evidence, "risk")


def test_nominal_full_scale_exceedance_is_not_clipping(source_audio) -> None:
    result = TranslationEvidenceAnalyzer().analyze(source_audio, _transfer([4.0]))
    full_scale = result.evidence.nominal_full_scale
    assert full_scale.transferred_nominal_full_scale_exceeded
    assert not full_scale.clipping_applied


def test_policy_and_evidence_are_deterministic(source_audio) -> None:
    analyzer = TranslationEvidenceAnalyzer()
    first = analyzer.analyze(source_audio, _transfer([0.5]))
    second = analyzer.analyze(source_audio, _transfer([0.5]))
    assert first.evidence == second.evidence
    np.testing.assert_array_equal(first.channel_erb_delta_db, second.channel_erb_delta_db)
    criterion = _criterion(
        TranslationEvidenceDimensionId.PROGRAMME_ENERGY_DELTA_DB,
        -3.0,
        "dB",
        comparison=TranslationRiskComparison.LESS_THAN,
    )
    evaluator = TranslationRiskEvaluator()
    assert evaluator.evaluate(first.evidence, _policy(criterion)) == evaluator.evaluate(
        second.evidence, _policy(criterion)
    )


def test_capabilities_are_narrow_and_implemented() -> None:
    assert registry.get("translation_evidence_foundation").status is CapabilityStatus.IMPLEMENTED
    assert (
        registry.get("policy_conditioned_translation_risk").status is CapabilityStatus.IMPLEMENTED
    )
    assert registry.get("universal_translation_prediction") is None
    assert registry.get("phone_compatibility") is None


def test_lightweight_perception_import_still_avoids_numpy() -> None:
    repository = Path(__file__).resolve().parents[1]
    program = (
        "import sys; "
        f"sys.path.insert(0, {str(repository)!r}); "
        "import phasenox.perception; "
        "assert 'numpy' not in sys.modules"
    )
    completed = subprocess.run(
        [sys.executable, "-I", "-c", program], capture_output=True, text=True, check=False
    )
    assert completed.returncode == 0, completed.stderr
