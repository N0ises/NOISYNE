from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

from noisyne.audio.io.models import AudioData, AudioMetadata
from noisyne.perception import (
    DescriptorClass,
    DescriptorDefinition,
    DescriptorImplementationState,
    PerceptualDescriptorResult,
    ResultStatus,
    descriptor_taxonomy,
)
from noisyne.perception.descriptors import PerceptualDescriptorFoundation
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
    frequency_hz: float,
    *,
    amplitude: float = 0.1,
    sample_count: int = 2048,
    sample_rate: int = 48_000,
) -> np.ndarray:
    time = np.arange(sample_count, dtype=np.float64) / sample_rate
    return amplitude * np.sin(2.0 * np.pi * frequency_hz * time)


def _descriptor(output, descriptor_id: str) -> PerceptualDescriptorResult:
    return next(item for item in output.descriptors if item.descriptor_id == descriptor_id)


def test_taxonomy_covers_exact_required_descriptors_in_stable_order() -> None:
    assert [item.descriptor_id for item in descriptor_taxonomy()] == [
        "sharpness",
        "roughness",
        "fluctuation_strength",
        "tonality",
        "brightness",
        "warmth",
        "harshness",
        "punch",
        "density",
        "width",
    ]


def test_taxonomy_classes_are_scientifically_explicit() -> None:
    taxonomy = {item.descriptor_id: item for item in descriptor_taxonomy()}
    for descriptor_id in ("sharpness", "roughness", "fluctuation_strength", "tonality"):
        assert taxonomy[descriptor_id].descriptor_class is DescriptorClass.STANDARDIZED
    assert taxonomy["brightness"].descriptor_class is DescriptorClass.RESEARCH_CORRELATE
    for descriptor_id in ("warmth", "harshness", "punch", "density", "width"):
        assert taxonomy[descriptor_id].descriptor_class is DescriptorClass.INFORMAL_ENGINEERING_TERM


def test_only_brightness_is_implemented_and_no_generic_scale_is_declared() -> None:
    taxonomy = descriptor_taxonomy()
    implemented = [
        item.descriptor_id
        for item in taxonomy
        if item.implementation_state is DescriptorImplementationState.IMPLEMENTED
    ]
    assert implemented == ["brightness"]
    assert all(item.standardized_unit is None for item in taxonomy[4:])
    serialized = json.dumps([item.to_dict() for item in taxonomy]).lower()
    assert "0-100" not in serialized
    assert "0–100" not in serialized


def test_standardized_units_are_owned_by_their_unavailable_methods() -> None:
    taxonomy = {item.descriptor_id: item for item in descriptor_taxonomy()}
    assert taxonomy["sharpness"].standardized_unit == "acum"
    assert taxonomy["roughness"].standardized_unit == "asper"
    assert taxonomy["fluctuation_strength"].standardized_unit == "vacilHMS"
    assert taxonomy["tonality"].standardized_unit == "tuHMS"


def test_taxonomy_contract_round_trip_is_json_safe() -> None:
    for definition in descriptor_taxonomy():
        payload = definition.to_dict()
        assert DescriptorDefinition.from_dict(payload) == definition
        assert json.loads(json.dumps(payload, allow_nan=False)) == payload


def test_unavailable_descriptors_have_no_estimates_or_fake_units() -> None:
    output = PerceptualDescriptorFoundation().analyze(_audio(_tone(1125.0)))
    for result in output.descriptors:
        if result.descriptor_id == "brightness":
            continue
        assert result.state.status is ResultStatus.UNAVAILABLE
        assert result.estimate is None
        assert result.state.reason


def test_silence_makes_brightness_undefined_without_nan_or_zero_estimate() -> None:
    output = PerceptualDescriptorFoundation().analyze(_audio(np.zeros(2048)))
    brightness = _descriptor(output, "brightness")

    assert brightness.state.status is ResultStatus.INSUFFICIENT_EVIDENCE
    assert brightness.estimate is None
    assert not np.any(output.channel_frame_centroid_defined)
    assert not np.any(output.channel_programme_centroid_defined)
    assert np.all(output.channel_frame_centroid_hz == 0.0)


@pytest.mark.parametrize("frequency_hz", [1125.0, 3000.0, 6000.0])
def test_bin_centered_pure_tone_centroid_matches_frequency(frequency_hz: float) -> None:
    output = PerceptualDescriptorFoundation().analyze(_audio(_tone(frequency_hz)))
    brightness = _descriptor(output, "brightness")

    assert brightness.state.status is ResultStatus.COMPUTED
    assert brightness.estimate.unit == "Hz"
    assert brightness.estimate.value == pytest.approx(frequency_hz, abs=1e-10)
    assert output.channel_frame_centroid_hz[0, 0] == pytest.approx(frequency_hz, abs=1e-10)


def test_two_tone_power_weighted_centroid_matches_analytical_value() -> None:
    first_frequency = 1125.0
    second_frequency = 3000.0
    first_amplitude = 0.2
    second_amplitude = 0.1
    samples = _tone(first_frequency, amplitude=first_amplitude) + _tone(
        second_frequency, amplitude=second_amplitude
    )
    expected = (
        first_frequency * first_amplitude**2 + second_frequency * second_amplitude**2
    ) / (first_amplitude**2 + second_amplitude**2)

    brightness = _descriptor(
        PerceptualDescriptorFoundation().analyze(_audio(samples)), "brightness"
    )

    assert brightness.estimate.value == pytest.approx(expected, abs=1e-10)


def test_higher_frequency_signal_has_higher_centroid() -> None:
    foundation = PerceptualDescriptorFoundation()
    low = _descriptor(foundation.analyze(_audio(_tone(1125.0))), "brightness")
    high = _descriptor(foundation.analyze(_audio(_tone(6000.0))), "brightness")
    assert high.estimate.value > low.estimate.value


@pytest.mark.parametrize("scale", [0.5, 2.0, 10.0])
def test_centroid_is_amplitude_scale_invariant(scale: float) -> None:
    foundation = PerceptualDescriptorFoundation()
    samples = _tone(1125.0) + 0.3 * _tone(3000.0)
    reference = _descriptor(foundation.analyze(_audio(samples)), "brightness")
    scaled = _descriptor(foundation.analyze(_audio(samples * scale)), "brightness")
    assert scaled.estimate.value == pytest.approx(reference.estimate.value, abs=1e-10)


def test_channels_are_power_combined_not_arithmetically_averaged() -> None:
    low = _tone(1125.0, amplitude=0.2)
    high = _tone(3000.0, amplitude=0.1)
    output = PerceptualDescriptorFoundation().analyze(_audio(np.column_stack((low, high))))
    brightness = _descriptor(output, "brightness")
    expected = (1125.0 * 0.2**2 + 3000.0 * 0.1**2) / (0.2**2 + 0.1**2)

    assert output.channel_programme_centroid_hz == pytest.approx([1125.0, 3000.0], abs=1e-10)
    assert brightness.estimate.value == pytest.approx(expected, abs=1e-10)
    assert brightness.estimate.value != pytest.approx((1125.0 + 3000.0) / 2.0)


def test_silent_channel_does_not_dilute_active_channel() -> None:
    tone = _tone(3000.0)
    output = PerceptualDescriptorFoundation().analyze(
        _audio(np.column_stack((tone, np.zeros_like(tone))))
    )
    brightness = _descriptor(output, "brightness")

    assert brightness.estimate.value == pytest.approx(3000.0, abs=1e-10)
    assert np.array_equal(output.channel_programme_centroid_defined, [True, False])


def test_opposite_phase_stereo_does_not_cancel() -> None:
    tone = _tone(3000.0)
    output = PerceptualDescriptorFoundation().analyze(_audio(np.column_stack((tone, -tone))))
    brightness = _descriptor(output, "brightness")

    assert brightness.estimate.value == pytest.approx(3000.0, abs=1e-10)
    assert output.channel_programme_centroid_hz == pytest.approx([3000.0, 3000.0], abs=1e-10)


def test_multichannel_audio_is_preserved() -> None:
    samples = np.column_stack((_tone(1125.0), _tone(3000.0), _tone(6000.0)))
    output = PerceptualDescriptorFoundation().analyze(_audio(samples))

    assert output.channel_frame_centroid_hz.shape == (3, 1)
    assert output.channel_programme_centroid_hz == pytest.approx(
        [1125.0, 3000.0, 6000.0], abs=1e-10
    )


@pytest.mark.parametrize("sample_rate,frequency_hz", [(44_100, 1102.5), (48_000, 1125.0)])
def test_sample_rates_use_their_actual_linear_frequency_axis(
    sample_rate: int, frequency_hz: float
) -> None:
    output = PerceptualDescriptorFoundation().analyze(
        _audio(_tone(frequency_hz, sample_rate=sample_rate), sample_rate)
    )
    brightness = _descriptor(output, "brightness")
    assert brightness.estimate.value == pytest.approx(frequency_hz, abs=1e-7)
    assert brightness.frequency_range.upper_hz == sample_rate / 2.0


def test_short_one_sample_input_is_finite_and_truthfully_undefined() -> None:
    output = PerceptualDescriptorFoundation().analyze(_audio(np.array([1.0])))
    assert _descriptor(output, "brightness").state.status is ResultStatus.INSUFFICIENT_EVIDENCE
    assert np.all(np.isfinite(output.channel_frame_centroid_hz))


def test_zero_padded_final_frame_is_exposed_and_finite() -> None:
    samples = _tone(1125.0, sample_count=2501)
    output = PerceptualDescriptorFoundation().analyze(_audio(samples))

    assert output.auditory_frontend_summary.config.boundary_policy == "zero_pad_end"
    half_frame_seconds = output.auditory_frontend_summary.config.frame_size_samples / 2.0 / 48_000
    assert output.frame_times_seconds[-1] + half_frame_seconds > len(samples) / 48_000
    assert np.all(np.isfinite(output.channel_frame_centroid_hz))
    assert np.all(output.channel_frame_centroid_defined)


def test_non_contiguous_input_is_supported_without_mutation() -> None:
    base = _tone(1125.0, sample_count=4096)
    samples = base[::2]
    original = samples.copy()
    assert not samples.flags.c_contiguous

    output = PerceptualDescriptorFoundation().analyze(_audio(samples))

    assert np.array_equal(samples, original)
    assert _descriptor(output, "brightness").state.status is ResultStatus.COMPUTED


@pytest.mark.parametrize("invalid", [np.nan, np.inf, -np.inf])
def test_non_finite_input_is_rejected(invalid: float) -> None:
    samples = _tone(1125.0)
    samples[10] = invalid
    with pytest.raises(ValueError, match="finite"):
        PerceptualDescriptorFoundation().analyze(_audio(samples))


def test_extreme_finite_input_fails_without_clipping_or_nan_transport() -> None:
    samples = np.full(2048, np.finfo(np.float64).max)
    with pytest.raises(ValueError, match="overflowed"):
        PerceptualDescriptorFoundation().analyze(_audio(samples))


def test_repeatability_is_bitwise_deterministic() -> None:
    samples = _tone(1125.0) + 0.25 * _tone(3000.0)
    foundation = PerceptualDescriptorFoundation()
    first = foundation.analyze(_audio(samples))
    second = foundation.analyze(_audio(samples.copy()))

    assert first.descriptors == second.descriptors
    assert np.array_equal(first.channel_frame_centroid_hz, second.channel_frame_centroid_hz)
    assert np.array_equal(first.channel_programme_centroid_hz, second.channel_programme_centroid_hz)


def test_runtime_arrays_are_finite_and_read_only() -> None:
    output = PerceptualDescriptorFoundation().analyze(_audio(_tone(1125.0)))
    for array in (
        output.frame_times_seconds,
        output.channel_frame_centroid_hz,
        output.channel_frame_centroid_defined,
        output.channel_programme_centroid_hz,
        output.channel_programme_centroid_defined,
    ):
        assert np.all(np.isfinite(array))
        assert array.flags.writeable is False


def test_transport_results_are_json_safe_and_exclude_runtime_arrays() -> None:
    output = PerceptualDescriptorFoundation().analyze(_audio(_tone(1125.0)))
    payload = [item.to_dict() for item in output.descriptors]

    assert [PerceptualDescriptorResult.from_dict(item) for item in payload] == list(
        output.descriptors
    )
    assert json.loads(json.dumps(payload, allow_nan=False)) == payload
    serialized = json.dumps(payload)
    assert "channel_frame_centroid_hz" not in serialized
    assert "channel_programme_centroid_hz" not in serialized


def test_full_mix_has_no_source_attribution_claim() -> None:
    brightness = _descriptor(
        PerceptualDescriptorFoundation().analyze(_audio(_tone(1125.0))), "brightness"
    )
    text = json.dumps(brightness.to_dict()).lower()
    assert "hi-hat" not in text
    assert "vocal" not in text
    assert any("full-mix" in item for item in brightness.limitations)


def test_descriptor_capabilities_are_implemented_not_verified() -> None:
    for name in ("perceptual_descriptors_foundation", "brightness_correlate"):
        capability = registry.get(name)
        assert capability is not None
        assert capability.status is CapabilityStatus.IMPLEMENTED
        assert capability.tested_in_freeze is False
    for name in ("sharpness", "roughness", "fluctuation_strength", "tonality"):
        assert registry.get(name) is None


def test_perception_root_import_remains_numpy_lightweight_with_descriptor_contracts() -> None:
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
