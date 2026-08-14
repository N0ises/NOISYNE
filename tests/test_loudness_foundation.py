from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

from noisyne.audio.analysis.lufs import LUFSAnalyzer
from noisyne.audio.io.models import AudioData, AudioMetadata
from noisyne.perception import (
    AcousticPresentation,
    LoudnessCalibration,
    PerceivedLoudnessResult,
    ResultStatus,
)
from noisyne.perception.loudness import PerceivedLoudnessFoundation
from noisyne.runtime.capabilities import CapabilityStatus, registry

ROOT = Path(__file__).resolve().parents[1]


def _audio(samples: np.ndarray, sample_rate: int = 48_000) -> AudioData:
    values = np.asarray(samples)
    channels = values.shape[1] if values.ndim == 2 else 1
    return AudioData(
        samples=values,
        metadata=AudioMetadata(
            path=Path("synthetic.wav"),
            filename="synthetic.wav",
            extension=".wav",
            format="wav",
            codec=None,
            sample_rate=sample_rate,
            channels=channels,
            duration=len(values) / sample_rate,
            bit_depth=24,
            file_size=values.size * values.dtype.itemsize,
        ),
    )


def _tone(
    amplitude: float = 0.1,
    frequency_hz: float = 1000.0,
    duration_seconds: float = 1.0,
    sample_rate: int = 48_000,
) -> np.ndarray:
    time = np.arange(round(duration_seconds * sample_rate), dtype=np.float64) / sample_rate
    return amplitude * np.sin(2.0 * np.pi * frequency_hz * time)


def _free_field_calibration(**changes: object) -> LoudnessCalibration:
    values: dict[str, object] = {
        "calibration_id": "lab-microphone-calibration",
        "version": "2026-08-14",
        "pascals_per_sample": 2.0,
        "presentation": AcousticPresentation.FREE_FIELD_SINGLE_MICROPHONE,
        "left_channel_index": 0,
        "right_channel_index": 0,
        "frequency_response_compensated": True,
        "traceability": "Calibration certificate TEST-001",
    }
    values.update(changes)
    return LoudnessCalibration(**values)


def test_uncalibrated_audio_returns_insufficient_evidence_without_estimate() -> None:
    output = PerceivedLoudnessFoundation().analyze(_audio(_tone()))
    result = output.perceived_loudness

    assert result.state.status is ResultStatus.INSUFFICIENT_EVIDENCE
    assert "calibration" in result.state.reason.lower()
    assert result.estimate is None
    assert output.calibration is None
    assert output.pressure_by_ear_pa is None


def test_uncalibrated_stereo_is_not_assumed_to_be_binaural() -> None:
    tone = _tone()
    output = PerceivedLoudnessFoundation().analyze(_audio(np.column_stack((tone, -tone))))

    assert output.pressure_by_ear_pa is None
    assert output.perceived_loudness.estimate is None
    assert any("stereo" in item.lower() for item in output.perceived_loudness.limitations)


def test_existing_lufs_is_objective_supporting_measurement_only() -> None:
    audio = _audio(_tone())
    output = PerceivedLoudnessFoundation().analyze(audio)
    measurement = output.perceived_loudness.programme_loudness_measurement

    assert measurement is not None
    assert measurement.value.unit == "LUFS"
    assert measurement.value.value == pytest.approx(LUFSAnalyzer().analyze(audio))
    assert output.perceived_loudness.estimate is None
    assert "perceived loudness" in measurement.method.description


def test_programme_loudness_can_be_omitted_explicitly() -> None:
    output = PerceivedLoudnessFoundation().analyze(
        _audio(_tone()), include_programme_loudness=False
    )

    assert output.perceived_loudness.programme_loudness_measurement is None


def test_short_audio_keeps_honest_state_when_lufs_is_unavailable() -> None:
    output = PerceivedLoudnessFoundation().analyze(_audio(np.zeros(100)))

    assert output.perceived_loudness.programme_loudness_measurement is None
    assert output.perceived_loudness.state.status is ResultStatus.INSUFFICIENT_EVIDENCE


def test_calibrated_single_microphone_maps_diotic_pressure_but_not_loudness() -> None:
    samples = np.array([0.0, 0.25, -0.5, 1.0])
    calibration = _free_field_calibration()
    output = PerceivedLoudnessFoundation().analyze(
        _audio(samples), calibration=calibration, include_programme_loudness=False
    )

    expected = samples * 2.0
    assert np.array_equal(output.pressure_by_ear_pa[:, 0], expected)
    assert np.array_equal(output.pressure_by_ear_pa[:, 1], expected)
    assert output.pressure_by_ear_pa.flags.writeable is False
    assert output.perceived_loudness.state.status is ResultStatus.INSUFFICIENT_EVIDENCE
    assert "ISO 532-3:2023" in output.perceived_loudness.state.reason
    assert output.perceived_loudness.estimate is None


def test_calibrated_pressure_evidence_uses_pascal_not_sone_or_phon() -> None:
    output = PerceivedLoudnessFoundation().analyze(
        _audio(np.ones(16) * 0.5),
        calibration=_free_field_calibration(),
        include_programme_loudness=False,
    )
    measurements = [item.measurement for item in output.perceived_loudness.evidence]

    assert len(measurements) == 2
    assert all(measurement.value.unit == "Pa" for measurement in measurements)
    assert all(measurement.value.value == pytest.approx(1.0) for measurement in measurements)
    assert output.perceived_loudness.estimate is None


def test_explicit_eardrum_pressure_mapping_preserves_two_ear_channels() -> None:
    samples = np.column_stack((np.array([1.0, 2.0]), np.array([-3.0, -4.0])))
    calibration = _free_field_calibration(
        presentation=AcousticPresentation.EARDRUM_PRESSURE,
        left_channel_index=0,
        right_channel_index=1,
        pascals_per_sample=0.25,
    )
    output = PerceivedLoudnessFoundation().analyze(
        _audio(samples), calibration=calibration, include_programme_loudness=False
    )

    assert np.array_equal(output.pressure_by_ear_pa[:, 0], samples[:, 0] * 0.25)
    assert np.array_equal(output.pressure_by_ear_pa[:, 1], samples[:, 1] * 0.25)


def test_single_microphone_requires_one_diotic_channel_mapping() -> None:
    with pytest.raises(ValueError, match="diotically"):
        _free_field_calibration(right_channel_index=1)


def test_eardrum_pressure_requires_distinct_ear_channels() -> None:
    with pytest.raises(ValueError, match="distinct"):
        _free_field_calibration(presentation=AcousticPresentation.EARDRUM_PRESSURE)


def test_channel_mapping_must_exist_in_audio() -> None:
    calibration = _free_field_calibration(
        presentation=AcousticPresentation.EARDRUM_PRESSURE,
        left_channel_index=0,
        right_channel_index=2,
    )

    with pytest.raises(ValueError, match="channel mapping"):
        PerceivedLoudnessFoundation().analyze(
            _audio(np.zeros((32, 2))),
            calibration=calibration,
            include_programme_loudness=False,
        )


@pytest.mark.parametrize("scale", [0.0, -1.0, np.nan, np.inf, -np.inf])
def test_invalid_pressure_scale_is_rejected(scale: float) -> None:
    with pytest.raises((TypeError, ValueError)):
        _free_field_calibration(pascals_per_sample=scale)


def test_uncompensated_frequency_response_is_insufficient_for_pressure_input() -> None:
    calibration = _free_field_calibration(frequency_response_compensated=False)
    output = PerceivedLoudnessFoundation().analyze(
        _audio(np.ones(32)), calibration=calibration, include_programme_loudness=False
    )

    assert output.pressure_by_ear_pa is None
    assert output.perceived_loudness.state.status is ResultStatus.INSUFFICIENT_EVIDENCE
    assert "frequency-response" in output.perceived_loudness.state.reason


def test_calibrated_pressure_overflow_is_rejected_without_clipping() -> None:
    calibration = _free_field_calibration(pascals_per_sample=2.0)

    with pytest.raises(ValueError, match="overflowed"):
        PerceivedLoudnessFoundation().analyze(
            _audio(np.full(16, np.finfo(np.float64).max)),
            calibration=calibration,
            include_programme_loudness=False,
        )


def test_large_finite_calibrated_pressure_uses_overflow_safe_rms() -> None:
    value = np.finfo(np.float64).max / 2.0
    output = PerceivedLoudnessFoundation().analyze(
        _audio(np.full(16, value)),
        calibration=_free_field_calibration(pascals_per_sample=1.0),
        include_programme_loudness=False,
    )

    assert np.all(np.isfinite(output.pressure_by_ear_pa))
    for evidence in output.perceived_loudness.evidence:
        assert evidence.measurement.value.value == pytest.approx(value)


@pytest.mark.parametrize("invalid", [np.nan, np.inf, -np.inf])
def test_non_finite_audio_is_rejected(invalid: float) -> None:
    samples = np.zeros(16)
    samples[3] = invalid

    with pytest.raises(ValueError, match="finite"):
        PerceivedLoudnessFoundation().analyze(_audio(samples), include_programme_loudness=False)


def test_calibration_contract_round_trip_is_json_safe() -> None:
    calibration = _free_field_calibration()
    payload = calibration.to_dict()

    assert LoudnessCalibration.from_dict(payload) == calibration
    assert json.loads(json.dumps(payload, allow_nan=False)) == payload


def test_loudness_transport_result_round_trip_contains_no_runtime_pressure_array() -> None:
    output = PerceivedLoudnessFoundation().analyze(
        _audio(np.ones(32) * 0.25),
        calibration=_free_field_calibration(),
        include_programme_loudness=False,
    )
    payload = output.perceived_loudness.to_dict()

    assert PerceivedLoudnessResult.from_dict(payload) == output.perceived_loudness
    assert json.loads(json.dumps(payload, allow_nan=False)) == payload
    assert "pressure_by_ear_pa" not in payload


def test_loudness_foundation_capability_is_implemented_but_not_verified() -> None:
    capability = registry.get("loudness_foundation")

    assert capability is not None
    assert capability.status is CapabilityStatus.IMPLEMENTED
    assert capability.tested_in_freeze is False


def test_perception_root_import_remains_numpy_lightweight_with_loudness_contracts() -> None:
    script = """
import sys
import noisyne.perception
print('numpy' in sys.modules)
"""
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "False"
