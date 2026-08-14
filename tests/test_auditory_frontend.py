from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

from noisyne.audio.io.models import AudioData, AudioMetadata
from noisyne.perception import (
    AUDITORY_FRONTEND_METHOD_VERSION,
    AuditoryFrontendConfig,
    AuditoryFrontendSummary,
)
from noisyne.perception.auditory import (
    AuditoryFrontend,
    erb_rate_to_hz,
    hz_to_erb_rate,
)
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
            duration=len(values) / sample_rate if sample_rate else 0.0,
            bit_depth=24,
            file_size=values.size * values.dtype.itemsize,
        ),
    )


def _tone(frequency_hz: float, frames: int = 4096, sample_rate: int = 48_000) -> np.ndarray:
    time = np.arange(frames, dtype=np.float64) / sample_rate
    return np.sin(2.0 * np.pi * frequency_hz * time)


def test_silence_is_finite_and_has_zero_power() -> None:
    result = AuditoryFrontend().analyze(_audio(np.zeros(2048)))

    assert np.all(result.channel_power_spectra == 0.0)
    assert np.all(result.auditory_band_power == 0.0)
    assert np.all(np.isfinite(result.channel_power_spectra))


def test_near_silence_remains_finite_without_floor_or_normalization() -> None:
    samples = np.full(2048, 1e-150)
    result = AuditoryFrontend().analyze(_audio(samples))

    assert np.all(np.isfinite(result.channel_power_spectra))
    assert result.summary.input_peak_absolute == 1e-150


def test_single_bin_tone_has_expected_frequency_peak() -> None:
    sample_rate = 48_000
    bin_frequency = 48 * sample_rate / 2048
    result = AuditoryFrontend().analyze(_audio(_tone(bin_frequency, 2048, sample_rate)))
    peak_index = int(np.argmax(result.channel_power_spectra[0, 0]))

    assert result.linear_frequencies_hz[peak_index] == pytest.approx(bin_frequency)


def test_multiple_tones_produce_peaks_at_known_bins() -> None:
    sample_rate = 48_000
    frequencies = np.array([24, 96, 240]) * sample_rate / 2048
    samples = sum(_tone(float(frequency), 2048, sample_rate) for frequency in frequencies)
    result = AuditoryFrontend().analyze(_audio(samples, sample_rate))
    strongest = np.argsort(result.channel_power_spectra[0, 0])[-12:]

    for frequency in frequencies:
        index = int(np.argmin(np.abs(result.linear_frequencies_hz - frequency)))
        assert index in strongest


def test_seeded_broadband_noise_is_repeatable() -> None:
    samples = np.random.default_rng(20260814).normal(0.0, 0.1, 4097)
    frontend = AuditoryFrontend()

    first = frontend.analyze(_audio(samples))
    second = frontend.analyze(_audio(samples.copy()))

    assert np.array_equal(first.channel_power_spectra, second.channel_power_spectra)
    assert np.array_equal(first.auditory_band_power, second.auditory_band_power)


def test_impulse_spectrum_is_non_negative() -> None:
    samples = np.zeros(2048)
    samples[1024] = 1.0
    result = AuditoryFrontend().analyze(_audio(samples))

    assert np.all(result.channel_power_spectra >= 0.0)
    assert np.all(result.auditory_band_power >= 0.0)


@pytest.mark.parametrize("length", [1, 17, 2047, 2049, 4097])
def test_short_and_odd_sample_counts_have_deterministic_boundary_frames(length: int) -> None:
    result = AuditoryFrontend().analyze(_audio(np.ones(length)))
    expected = 1 + (max(length - 2048, 0) + 511) // 512

    assert result.summary.frame_count == expected
    assert result.channel_power_spectra.shape[1] == expected


def test_mono_shape_is_explicit() -> None:
    result = AuditoryFrontend().analyze(_audio(np.zeros(2048)))

    assert result.summary.channel_count == 1
    assert result.channel_power_spectra.shape[:2] == (1, 1)


def test_identical_stereo_channels_are_preserved() -> None:
    tone = _tone(1125.0, 2048)
    result = AuditoryFrontend().analyze(_audio(np.column_stack((tone, tone))))

    assert result.summary.channel_count == 2
    assert np.array_equal(result.channel_power_spectra[0], result.channel_power_spectra[1])


def test_phase_opposed_stereo_does_not_cancel() -> None:
    tone = _tone(1125.0, 2048)
    result = AuditoryFrontend().analyze(_audio(np.column_stack((tone, -tone))))

    assert np.max(result.channel_power_spectra) > 0.0
    assert np.array_equal(result.channel_power_spectra[0], result.channel_power_spectra[1])
    assert result.summary.config.channel_policy == "per_channel_preserve"


@pytest.mark.parametrize("sample_rate", [100, 8_000, 44_100, 48_000, 96_000])
def test_sample_rate_controls_nyquist_and_metadata(sample_rate: int) -> None:
    result = AuditoryFrontend().analyze(_audio(np.zeros(2048), sample_rate))

    assert result.summary.source_sample_rate_hz == sample_rate
    assert result.linear_frequencies_hz[-1] == pytest.approx(sample_rate / 2.0)
    assert result.summary.auditory_bands[-1].frequency_range.upper_hz == pytest.approx(
        sample_rate / 2.0
    )


def test_custom_odd_frame_and_fft_configuration() -> None:
    config = AuditoryFrontendConfig(
        frame_size_samples=1023,
        hop_size_samples=257,
        fft_size=2049,
    )
    result = AuditoryFrontend(config).analyze(_audio(np.zeros(3001)))

    assert result.summary.config == config
    assert result.linear_frequencies_hz.size == 1025
    assert np.all(np.diff(result.frame_times_seconds) > 0.0)


def test_one_sample_frame_configuration_is_numerically_safe() -> None:
    config = AuditoryFrontendConfig(frame_size_samples=1, hop_size_samples=1, fft_size=1)
    result = AuditoryFrontend(config).analyze(_audio(np.array([0.5]), 100))

    assert result.channel_power_spectra[0, 0, 0] == pytest.approx(0.25)
    assert np.all(np.isfinite(result.auditory_band_power))


def test_multichannel_input_preserves_every_channel() -> None:
    tone = _tone(1125.0, 2048)
    samples = np.column_stack((tone, tone * 0.5, -tone, np.zeros_like(tone)))
    result = AuditoryFrontend().analyze(_audio(samples))

    assert result.summary.channel_count == 4
    assert result.channel_power_spectra.shape[0] == 4
    assert np.all(result.channel_power_spectra[3] == 0.0)


@pytest.mark.parametrize("sample_rate", [0, -1, 48_000.0, True])
def test_invalid_sample_rate_is_rejected(sample_rate: object) -> None:
    audio = _audio(np.zeros(8))
    object.__setattr__(audio.metadata, "sample_rate", sample_rate)

    with pytest.raises(ValueError, match="sample rate"):
        AuditoryFrontend().analyze(audio)


def test_empty_input_is_rejected() -> None:
    with pytest.raises(ValueError, match="empty"):
        AuditoryFrontend().analyze(_audio(np.array([], dtype=np.float64)))


@pytest.mark.parametrize("invalid", [np.nan, np.inf, -np.inf])
def test_non_finite_input_is_rejected(invalid: float) -> None:
    samples = np.zeros(16)
    samples[4] = invalid

    with pytest.raises(ValueError, match="finite"):
        AuditoryFrontend().analyze(_audio(samples))


def test_above_full_scale_input_is_preserved_and_flagged() -> None:
    samples = np.array([0.0, 1.5, -1.25, 0.0])
    original = samples.copy()
    result = AuditoryFrontend().analyze(_audio(samples))

    assert np.array_equal(samples, original)
    assert result.summary.input_peak_absolute == 1.5
    assert result.summary.nominal_full_scale_exceeded is True


def test_non_contiguous_input_is_supported_without_mutation() -> None:
    base = np.arange(8192, dtype=np.float64).reshape(4096, 2)
    samples = base[::2]
    assert not samples.flags.c_contiguous

    result = AuditoryFrontend().analyze(_audio(samples))

    assert result.summary.source_sample_count == 2048
    assert result.summary.channel_count == 2


def test_parseval_like_windowed_power_identity() -> None:
    samples = _tone(1125.0, 2048)
    result = AuditoryFrontend().analyze(_audio(samples))
    indexes = np.arange(2048, dtype=np.float64)
    window = 0.5 - 0.5 * np.cos(2.0 * np.pi * indexes / 2048)
    expected = np.sum(np.square(samples * window)) / np.sum(np.square(window))

    assert np.sum(result.channel_power_spectra[0, 0]) == pytest.approx(expected, rel=1e-12)
    assert np.sum(result.auditory_band_power[0, 0]) == pytest.approx(expected, rel=1e-12)


def test_erb_rate_published_equation_reference_values_and_inverse() -> None:
    assert hz_to_erb_rate(0.0) == 0.0
    assert hz_to_erb_rate(1000.0) == pytest.approx(15.6214497, rel=1e-7)
    frequencies = np.array([0.0, 100.0, 1000.0, 10_000.0, 24_000.0])

    assert np.allclose(erb_rate_to_hz(hz_to_erb_rate(frequencies)), frequencies, rtol=1e-12)


def test_auditory_band_definitions_are_monotonic_and_well_formed() -> None:
    bands = AuditoryFrontend().analyze(_audio(np.zeros(2048))).summary.auditory_bands
    lowers = np.array([band.frequency_range.lower_hz for band in bands])
    uppers = np.array([band.frequency_range.upper_hz for band in bands])
    centers = np.array([band.center_hz for band in bands])

    assert np.all(np.diff(lowers) > 0.0)
    assert np.all(np.diff(uppers) > 0.0)
    assert np.allclose(uppers[:-1], lowers[1:])
    assert np.all((lowers <= centers) & (centers <= uppers))


def test_frame_timestamps_are_monotonic_and_center_referenced() -> None:
    result = AuditoryFrontend().analyze(_audio(np.zeros(5000), 48_000))

    assert result.frame_times_seconds[0] == pytest.approx(1024 / 48_000)
    assert np.all(np.diff(result.frame_times_seconds) > 0.0)


def test_summary_round_trip_is_json_safe_without_runtime_arrays() -> None:
    summary = AuditoryFrontend().analyze(_audio(np.zeros(2048))).summary
    payload = summary.to_dict()

    assert AuditoryFrontendSummary.from_dict(payload) == summary
    assert json.loads(json.dumps(payload, allow_nan=False)) == payload
    assert payload["arrays_serialized"] is False
    assert "channel_power_spectra" not in payload


def test_method_metadata_and_registry_state_are_truthful() -> None:
    summary = AuditoryFrontend().analyze(_audio(np.zeros(2048))).summary
    capability = registry.get("auditory_frontend")

    assert summary.method.version == AUDITORY_FRONTEND_METHOD_VERSION
    assert summary.schema_version == "1.0.0"
    assert summary.spl_calibrated is False
    assert capability is not None
    assert capability.status is CapabilityStatus.IMPLEMENTED
    assert capability.tested_in_freeze is False


def test_perception_root_import_remains_numpy_lightweight() -> None:
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
