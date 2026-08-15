from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

from noisyne.audio.io.models import AudioData, AudioMetadata
from noisyne.perception import (
    PLAYBACK_TRANSFER_METHOD_ID,
    PLAYBACK_TRANSFER_METHOD_VERSION,
    ExtrapolationPolicy,
    FrequencyRange,
    MagnitudeInterpolationPolicy,
    MaximumLinearOutputEvidence,
    PlaybackProfile,
    PlaybackProfileReference,
    PlaybackTransferApplicationSummary,
    PlaybackTransferProfile,
    ScalarValue,
    TransferAcousticScope,
    TransferChannelTopology,
    TransferGainBasis,
    TransferKind,
    TransferPhaseBasis,
    TransferProvenance,
    UnitBasis,
)
from noisyne.perception.transfer import (
    ImpulseResponseTransfer,
    MagnitudeResponseEvidence,
    PlaybackTransferEngine,
)
from noisyne.runtime.capabilities import CapabilityStatus, registry


def _readonly(values: object) -> np.ndarray:
    result = np.asarray(values, dtype=np.float64)
    result.setflags(write=False)
    return result


def _profile(
    kind: TransferKind = TransferKind.IMPULSE_RESPONSE,
    *,
    topology: TransferChannelTopology = TransferChannelTopology.CHANNEL_INDEPENDENT_SHARED,
    channels: int | None = None,
    gain_basis: TransferGainBasis = TransferGainBasis.DIGITAL_AMPLITUDE_RATIO,
    provenance: TransferProvenance = TransferProvenance.USER_DECLARED,
) -> PlaybackTransferProfile:
    magnitude = kind is TransferKind.MAGNITUDE_RESPONSE
    return PlaybackTransferProfile(
        transfer_id="fixture.linear.v1",
        version="1.0.0",
        profile_reference=PlaybackProfileReference("fixture", "1.0.0"),
        provenance=provenance,
        evidence_source="Sprint 6 analytical fixture",
        evidence_version="1.0.0",
        transfer_kind=kind,
        gain_basis=gain_basis,
        phase_basis=(
            TransferPhaseBasis.MAGNITUDE_ONLY
            if magnitude
            else TransferPhaseBasis.IMPULSE_RESPONSE_CONTAINS_PHASE
        ),
        acoustic_scope=TransferAcousticScope.ENGINEERING_TEST_FIXTURE,
        channel_topology=topology,
        measurement_conditions="Deterministic unit-test conditions",
        normalization_reference="Digital amplitude ratio; unity is 1.0",
        time_origin_alignment=(
            "Not applicable to magnitude evidence" if magnitude else "Tap zero at input sample zero"
        ),
        valid_frequency_range=FrequencyRange(100.0, 1000.0) if magnitude else None,
        sample_rate_hz=None if magnitude else 48_000,
        expected_input_channels=channels,
        interpolation_policy=MagnitudeInterpolationPolicy.LOG_FREQUENCY_DB if magnitude else None,
        extrapolation_policy=ExtrapolationPolicy.REJECT if magnitude else None,
        limitations=["Engineering fixture, not a consumer playback target"],
    )


def _audio(samples: object, *, sample_rate: int = 48_000) -> AudioData:
    array = np.asarray(samples)
    channels = 1 if array.ndim == 1 else array.shape[1]
    return AudioData(
        samples=array,
        metadata=AudioMetadata(
            path=Path("fixture.wav"),
            filename="fixture.wav",
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


def _transfer(
    taps: object,
    *,
    topology: TransferChannelTopology = TransferChannelTopology.CHANNEL_INDEPENDENT_SHARED,
    channels: int | None = None,
) -> ImpulseResponseTransfer:
    values = np.asarray(taps, dtype=np.float64)
    if values.ndim == 1:
        values = values[np.newaxis, :]
    values.setflags(write=False)
    return ImpulseResponseTransfer(
        profile=_profile(topology=topology, channels=channels), impulse_response=values
    )


def test_sprint_1_playback_profile_remains_context_only_and_round_trips() -> None:
    profile = PlaybackProfile(
        profile_id="headphones.context",
        display_name="Declared headphone context",
        version="1",
        description="Context only; no response data",
    )
    assert PlaybackProfile.from_dict(profile.to_dict()) == profile
    assert not hasattr(profile, "frequency_hz")
    assert not hasattr(profile, "impulse_response")


@pytest.mark.parametrize("provenance", list(TransferProvenance))
def test_every_provenance_class_round_trips(provenance: TransferProvenance) -> None:
    profile = _profile(provenance=provenance)
    assert PlaybackTransferProfile.from_dict(profile.to_dict()) == profile


@pytest.mark.parametrize("field", ["evidence_source", "evidence_version", "transfer_id"])
def test_missing_provenance_identity_is_rejected(field: str) -> None:
    with pytest.raises((TypeError, ValueError)):
        replace(_profile(), **{field: " "})


def test_magnitude_arrays_are_strict_finite_read_only_float64() -> None:
    evidence = MagnitudeResponseEvidence(
        _profile(TransferKind.MAGNITUDE_RESPONSE),
        _readonly([100.0, 1000.0]),
        _readonly([0.0, -20.0]),
    )
    assert not evidence.frequency_hz.flags.writeable
    assert evidence.summary.point_count == 2
    for invalid in (
        np.array([100.0, 1000.0]),
        _readonly([100.0, 100.0]),
        _readonly([1000.0, 100.0]),
        _readonly([100.0, np.nan]),
        _readonly([0.0, 1000.0]),
    ):
        with pytest.raises(ValueError):
            MagnitudeResponseEvidence(
                _profile(TransferKind.MAGNITUDE_RESPONSE), invalid, _readonly([0.0, -20.0])
            )


def test_magnitude_bounds_must_exactly_match_evidence() -> None:
    profile = replace(
        _profile(TransferKind.MAGNITUDE_RESPONSE),
        valid_frequency_range=FrequencyRange(99.0, 1000.0),
    )
    with pytest.raises(ValueError, match="bounds"):
        MagnitudeResponseEvidence(profile, _readonly([100.0, 1000.0]), _readonly([0.0, -20.0]))


def test_log_frequency_linear_db_interpolation_and_gain_convention() -> None:
    evidence = MagnitudeResponseEvidence(
        _profile(TransferKind.MAGNITUDE_RESPONSE),
        _readonly([100.0, 1000.0]),
        _readonly([0.0, -20.0]),
    )
    assert evidence.magnitude_at(100.0) == 0.0
    assert evidence.magnitude_at(1000.0) == -20.0
    assert evidence.magnitude_at(np.sqrt(100.0 * 1000.0)) == pytest.approx(-10.0, abs=1e-12)
    assert evidence.amplitude_ratio_at(np.sqrt(100.0 * 1000.0)) == pytest.approx(
        10.0 ** (-10.0 / 20.0), rel=1e-15
    )
    half_gain_db = 20.0 * np.log10(0.5)
    half_gain = MagnitudeResponseEvidence(
        _profile(TransferKind.MAGNITUDE_RESPONSE),
        _readonly([100.0, 1000.0]),
        _readonly([half_gain_db, half_gain_db]),
    )
    assert half_gain.amplitude_ratio_at(440.0) == pytest.approx(0.5, rel=1e-15)


@pytest.mark.parametrize("query", [99.0, 1001.0])
def test_magnitude_extrapolation_is_rejected(query: float) -> None:
    evidence = MagnitudeResponseEvidence(
        _profile(TransferKind.MAGNITUDE_RESPONSE),
        _readonly([100.0, 1000.0]),
        _readonly([0.0, 0.0]),
    )
    with pytest.raises(ValueError, match="extrapolation"):
        evidence.magnitude_at(query)


def test_absolute_acoustic_evidence_is_not_digital_gain() -> None:
    evidence = MagnitudeResponseEvidence(
        _profile(
            TransferKind.MAGNITUDE_RESPONSE,
            gain_basis=TransferGainBasis.ABSOLUTE_ACOUSTIC_OUTPUT,
        ),
        _readonly([100.0, 1000.0]),
        _readonly([70.0, 72.0]),
    )
    with pytest.raises(ValueError, match="not an amplitude ratio"):
        evidence.amplitude_ratio_at(200.0)
    assert not hasattr(evidence, "minimum_phase")
    assert not hasattr(evidence, "apply")


def test_magnitude_response_requires_shared_channel_topology() -> None:
    shared = _profile(TransferKind.MAGNITUDE_RESPONSE)
    assert shared.channel_topology is TransferChannelTopology.CHANNEL_INDEPENDENT_SHARED
    assert shared.expected_input_channels is None

    with pytest.raises(ValueError, match="shared single response only"):
        _profile(
            TransferKind.MAGNITUDE_RESPONSE,
            topology=TransferChannelTopology.EXPLICIT_PER_CHANNEL,
            channels=2,
        )


def test_amplitude_conversion_rejects_overflow_and_underflow() -> None:
    for magnitude_db in (10_000.0, -10_000.0):
        evidence = MagnitudeResponseEvidence(
            _profile(TransferKind.MAGNITUDE_RESPONSE),
            _readonly([100.0, 1000.0]),
            _readonly([magnitude_db, magnitude_db]),
        )
        with pytest.raises(ValueError, match="not representable as a positive float64"):
            evidence.amplitude_ratio_at(440.0)


def test_successful_amplitude_vectors_are_finite_positive_and_read_only() -> None:
    evidence = MagnitudeResponseEvidence(
        _profile(TransferKind.MAGNITUDE_RESPONSE),
        _readonly([100.0, 1000.0]),
        _readonly([-6.020599913279624, 6.020599913279624]),
    )
    result = evidence.amplitude_ratio_at(_readonly([100.0, 316.22776601683796, 1000.0]))
    assert result[0] == pytest.approx(0.5, rel=1e-15)
    assert np.all(np.isfinite(result))
    assert np.all(result > 0.0)
    assert not result.flags.writeable


def test_impulse_response_validation_and_topology() -> None:
    with pytest.raises(ValueError, match="read-only"):
        ImpulseResponseTransfer(_profile(), np.array([[1.0]], dtype=np.float64))
    with pytest.raises(ValueError, match="one transfer channel"):
        ImpulseResponseTransfer(_profile(), _readonly([[1.0], [1.0]]))
    explicit = _transfer(
        [[1.0], [0.5]],
        topology=TransferChannelTopology.EXPLICIT_PER_CHANNEL,
        channels=2,
    )
    assert explicit.summary.transfer_channel_count == 2


def test_identity_is_exact_zero_latency_and_does_not_mutate_input() -> None:
    samples = np.array([0.25, -0.5, 1.25], dtype=np.float32)
    original = samples.copy()
    result = PlaybackTransferEngine().apply(_audio(samples), _transfer([1.0]))
    np.testing.assert_array_equal(result.audio.samples, original.astype(np.float64))
    np.testing.assert_array_equal(samples, original)
    assert result.summary.input_sample_count == result.summary.output_sample_count == 3
    assert result.summary.transfer.profile.time_origin_alignment == "Tap zero at input sample zero"
    assert result.summary.method.method_id == PLAYBACK_TRANSFER_METHOD_ID
    assert result.summary.method.version == PLAYBACK_TRANSFER_METHOD_VERSION
    assert result.summary.nominal_full_scale_exceeded
    assert not result.summary.clipping_applied
    assert not result.summary.normalization_applied
    assert not result.audio.samples.flags.writeable


def test_constant_gain_and_known_fir_are_analytically_correct() -> None:
    engine = PlaybackTransferEngine()
    half = engine.apply(_audio([1.0, -0.5]), _transfer([0.5]))
    np.testing.assert_array_equal(half.audio.samples, [0.5, -0.25])
    known = engine.apply(_audio([1.0, 2.0, 3.0]), _transfer([0.5, -0.25]))
    np.testing.assert_array_equal(known.audio.samples, [0.5, 0.75, 1.0, -0.75])
    assert known.audio.metadata.duration == 4 / 48_000
    assert known.audio.metadata.file_size == known.audio.samples.nbytes


def test_delta_reproduces_fir_and_silence_stays_silent() -> None:
    engine = PlaybackTransferEngine()
    fir = [0.25, -0.5, 0.125]
    np.testing.assert_array_equal(engine.apply(_audio([1.0]), _transfer(fir)).audio.samples, fir)
    np.testing.assert_array_equal(
        engine.apply(_audio(np.zeros(4)), _transfer(fir)).audio.samples, np.zeros(6)
    )


def test_opposite_phase_stereo_is_processed_independently() -> None:
    stereo = np.column_stack(([1.0, -0.5], [-1.0, 0.5]))
    result = PlaybackTransferEngine().apply(_audio(stereo), _transfer([0.5]))
    np.testing.assert_array_equal(result.audio.samples[:, 0], [0.5, -0.25])
    np.testing.assert_array_equal(result.audio.samples[:, 1], [-0.5, 0.25])
    assert result.audio.metadata.channels == 2


def test_explicit_per_channel_gain_and_channel_mismatch() -> None:
    transfer = _transfer(
        [[1.0], [0.5]],
        topology=TransferChannelTopology.EXPLICIT_PER_CHANNEL,
        channels=2,
    )
    result = PlaybackTransferEngine().apply(_audio([[1.0, 1.0], [-1.0, -1.0]]), transfer)
    np.testing.assert_array_equal(result.audio.samples, [[1.0, 0.5], [-1.0, -0.5]])
    with pytest.raises(ValueError, match="channel count"):
        PlaybackTransferEngine().apply(_audio([1.0]), transfer)


def test_sample_rate_mismatch_and_invalid_audio_are_rejected() -> None:
    engine = PlaybackTransferEngine()
    with pytest.raises(ValueError, match="sample rates"):
        engine.apply(_audio([1.0], sample_rate=44_100), _transfer([1.0]))
    for invalid in ([np.nan], [np.inf]):
        with pytest.raises(ValueError, match="finite"):
            engine.apply(_audio(invalid), _transfer([1.0]))
    with pytest.raises(TypeError, match="real numeric"):
        engine.apply(_audio(np.array([1.0 + 1.0j])), _transfer([1.0]))


def test_noncontiguous_audio_is_supported_and_extreme_overflow_is_rejected() -> None:
    source = np.arange(12.0).reshape(6, 2)
    view = source[::2]
    assert not view.flags.c_contiguous
    result = PlaybackTransferEngine().apply(_audio(view), _transfer([1.0]))
    np.testing.assert_array_equal(result.audio.samples, view)
    with pytest.raises(ValueError, match="overflowed|non-finite"):
        PlaybackTransferEngine().apply(_audio([np.finfo(np.float64).max]), _transfer([2.0]))


def test_application_summary_round_trips_without_runtime_arrays() -> None:
    result = PlaybackTransferEngine().apply(_audio([1.0, 0.0]), _transfer([1.0, 0.5]))
    payload = result.summary.to_dict()
    assert PlaybackTransferApplicationSummary.from_dict(payload) == result.summary
    assert '"impulse_response":' not in json.dumps(payload)
    assert payload["transfer"]["arrays_serialized"] is False


def test_maximum_linear_output_evidence_is_separate_transport_metadata() -> None:
    evidence = MaximumLinearOutputEvidence(
        evidence_id="speaker.max-linear.2026",
        provenance=TransferProvenance.MEASURED,
        source="Identified laboratory report",
        evidence_version="2026-01",
        measurement_method_reference="AES75-2023-compatible report supplied by caller",
        value=ScalarValue(101.5, UnitBasis.DECLARED_UNIT, unit="dB SPL"),
        measurement_conditions="Music-Noise, one metre; see source report",
        frequency_range=FrequencyRange(100.0, 10_000.0),
        measurement_distance_m=1.0,
    )
    assert MaximumLinearOutputEvidence.from_dict(evidence.to_dict()) == evidence
    assert not hasattr(evidence, "limiter")


def test_transfer_contract_rejects_semantic_category_errors() -> None:
    with pytest.raises(ValueError, match="sample_rate_hz"):
        replace(_profile(), sample_rate_hz=None)
    with pytest.raises(ValueError, match="absolute acoustic"):
        replace(_profile(), gain_basis=TransferGainBasis.ABSOLUTE_ACOUSTIC_OUTPUT)
    with pytest.raises(ValueError, match="expected_input_channels"):
        _profile(topology=TransferChannelTopology.EXPLICIT_PER_CHANNEL)


def test_capability_registry_uses_narrow_implemented_claims() -> None:
    assert registry.get("playback_profile_foundation").status is CapabilityStatus.IMPLEMENTED
    assert registry.get("playback_linear_transfer").status is CapabilityStatus.IMPLEMENTED
    assert registry.get("playback_simulation") is None
    assert registry.get("phone_simulation") is None


def test_lightweight_perception_import_does_not_import_numpy_runtime() -> None:
    repository = Path(__file__).resolve().parents[1]
    program = (
        "import sys; "
        f"sys.path.insert(0, {str(repository)!r}); "
        "import noisyne.perception; "
        "assert 'numpy' not in sys.modules"
    )
    completed = subprocess.run(
        [sys.executable, "-I", "-c", program], capture_output=True, text=True, check=False
    )
    assert completed.returncode == 0, completed.stderr
