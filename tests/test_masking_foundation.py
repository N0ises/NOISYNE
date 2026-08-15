from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

from noisyne.audio.io.models import AudioData, AudioMetadata
from noisyne.perception import (
    FrequencyMaskingResult,
    RelativeMaskingPairContext,
    ResultStatus,
)
from noisyne.perception.masking import (
    SimultaneousMaskingFoundation,
    moore_glasberg_1983_erb_hz,
    moore_glasberg_1983_roex_p_weights,
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
            duration=len(values) / sample_rate,
            bit_depth=24,
            file_size=values.size * values.dtype.itemsize,
        ),
    )


def _tone(
    frequency_hz: float = 1000.0,
    amplitude: float = 0.1,
    duration_seconds: float = 0.1,
    sample_rate: int = 48_000,
) -> np.ndarray:
    time = np.arange(round(duration_seconds * sample_rate), dtype=np.float64) / sample_rate
    return amplitude * np.sin(2.0 * np.pi * frequency_hz * time)


def _context(**changes: object) -> RelativeMaskingPairContext:
    values: dict[str, object] = {
        "gain_relationship_reference": "shared-render-bus-gain-v1",
        "alignment_reference": "sample-zero-aligned-export-v1",
    }
    values.update(changes)
    return RelativeMaskingPairContext(**values)


def _analyze_pair(
    masker: np.ndarray,
    target: np.ndarray,
    *,
    sample_rate: int = 48_000,
    context: RelativeMaskingPairContext | None = None,
):
    return SimultaneousMaskingFoundation().analyze_pair(
        _audio(masker, sample_rate),
        _audio(target, sample_rate),
        context=context or _context(),
    )


def _nearest_filter_index(result, frequency_hz: float) -> int:
    centers = np.array([band.center_hz for band in result.auditory_bands])
    return int(np.argmin(np.abs(centers - frequency_hz)))


def test_1983_erb_reference_value_at_one_kilohertz() -> None:
    assert moore_glasberg_1983_erb_hz(1000.0) == pytest.approx(128.14, abs=1e-12)


@pytest.mark.parametrize("center_hz", [99.0, 6501.0, np.nan, np.inf, -np.inf])
def test_1983_erb_rejects_centers_outside_published_domain(center_hz: float) -> None:
    with pytest.raises(ValueError, match="within"):
        moore_glasberg_1983_erb_hz(center_hz)


def test_roex_p_weight_is_unity_at_center_and_symmetric_in_linear_hz() -> None:
    frequencies = np.array([900.0, 1000.0, 1100.0])
    weights = moore_glasberg_1983_roex_p_weights(frequencies, 1000.0)

    assert weights[1] == pytest.approx(1.0, abs=0.0)
    assert weights[0] == pytest.approx(weights[2], abs=1e-15)
    assert weights.flags.writeable is False


def test_roex_p_numerical_equivalent_rectangular_bandwidth_matches_equation() -> None:
    frequencies = np.linspace(0.0, 6500.0, 260_001)
    weights = moore_glasberg_1983_roex_p_weights(frequencies, 1000.0)

    numerical_erb = np.trapezoid(weights, frequencies)
    assert numerical_erb == pytest.approx(128.14, abs=0.01)


def test_full_mix_returns_insufficient_evidence_without_ordered_events() -> None:
    result = SimultaneousMaskingFoundation().analyze(_audio(_tone()))

    assert result.state.status is ResultStatus.INSUFFICIENT_EVIDENCE
    assert "separate masker and target" in result.state.reason
    assert result.events == []
    assert all("source" not in event.event_id for event in result.events)


def test_identical_pair_has_zero_relative_excitation_margin_and_no_events() -> None:
    tone = _tone()
    output = _analyze_pair(tone, tone.copy())

    assert output.frequency_masking.state.status is ResultStatus.COMPUTED
    assert np.all(output.margin_defined)
    assert np.array_equal(
        output.relative_excitation_margin_db,
        np.zeros_like(output.relative_excitation_margin_db),
    )
    assert output.frequency_masking.events == []


def test_common_gain_ratio_has_exact_power_db_sign_convention() -> None:
    target = _tone(amplitude=0.1)
    output = _analyze_pair(target * 2.0, target)

    expected_db = 10.0 * np.log10(4.0)
    assert np.all(output.relative_excitation_margin_db[output.margin_defined] > 0.0)
    assert np.allclose(
        output.relative_excitation_margin_db[output.margin_defined],
        expected_db,
        rtol=0.0,
        atol=1e-12,
    )


def test_increasing_masker_level_does_not_reduce_relative_margin() -> None:
    target = _tone(amplitude=0.1)
    lower = _analyze_pair(target, target)
    higher = _analyze_pair(target * 4.0, target)

    valid = lower.margin_defined & higher.margin_defined
    assert np.all(
        higher.relative_excitation_margin_db[valid] >= lower.relative_excitation_margin_db[valid]
    )


def test_masker_excitation_is_lower_at_a_far_filter_than_a_near_filter() -> None:
    masker = _tone(frequency_hz=1000.0)
    target = _tone(frequency_hz=1100.0)
    output = _analyze_pair(masker, target)
    near = _nearest_filter_index(output, 1100.0)
    far = _nearest_filter_index(output, 4000.0)

    assert np.max(output.masker_excitation_power[..., near]) > np.max(
        output.masker_excitation_power[..., far]
    )


def test_swapping_masker_and_target_reverses_defined_margin() -> None:
    low = _tone(frequency_hz=500.0, amplitude=0.2)
    high = _tone(frequency_hz=2000.0, amplitude=0.1)
    forward = _analyze_pair(low, high)
    reverse = _analyze_pair(high, low)
    valid = forward.margin_defined & reverse.margin_defined

    assert np.allclose(
        forward.relative_excitation_margin_db[valid],
        -reverse.relative_excitation_margin_db[valid],
        rtol=0.0,
        atol=1e-12,
    )


def test_pair_context_with_explicit_source_ids_round_trips_through_json() -> None:
    context = _context(masker_source_id="explicit-masker", target_source_id="explicit-target")
    payload = context.to_dict()

    assert RelativeMaskingPairContext.from_dict(payload) == context
    assert json.loads(json.dumps(payload, allow_nan=False)) == payload


def test_only_caller_supplied_source_ids_appear_in_pair_evidence() -> None:
    context = _context(masker_source_id="explicit-masker", target_source_id="explicit-target")
    output = _analyze_pair(_tone(), _tone(), context=context)

    assert output.frequency_masking.evidence[0].origin == "explicit-masker -> explicit-target"
    assert output.frequency_masking.events == []


def test_missing_source_ids_are_not_fabricated() -> None:
    output = _analyze_pair(_tone(), _tone())

    assert output.frequency_masking.evidence[0].origin is None
    assert output.frequency_masking.events == []


@pytest.mark.parametrize("field", ["gain_relationship_reference", "alignment_reference"])
def test_pair_context_requires_auditable_alignment_and_gain_references(field: str) -> None:
    with pytest.raises(ValueError, match=field):
        _context(**{field: " "})


def test_incompatible_sample_rates_are_rejected_without_resampling() -> None:
    with pytest.raises(ValueError, match="sample rates must match"):
        SimultaneousMaskingFoundation().analyze_pair(
            _audio(_tone(sample_rate=44_100), 44_100),
            _audio(_tone(sample_rate=48_000), 48_000),
            context=_context(),
        )


def test_duration_mismatch_is_rejected_without_realignment() -> None:
    with pytest.raises(ValueError, match="sample counts must match"):
        _analyze_pair(_tone(duration_seconds=0.1), _tone(duration_seconds=0.2))


def test_channel_mismatch_is_rejected_without_downmixing() -> None:
    mono = _tone()
    stereo = np.column_stack((mono, mono))

    with pytest.raises(ValueError, match="channel counts must match"):
        _analyze_pair(mono, stereo)


def test_stereo_channels_are_preserved_and_phase_opposition_does_not_cancel() -> None:
    tone = _tone()
    masker = np.column_stack((tone, -tone))
    target = np.column_stack((tone * 0.5, tone * 0.5))
    output = _analyze_pair(masker, target)

    assert output.masker_excitation_power.shape[0] == 2
    assert np.array_equal(output.masker_excitation_power[0], output.masker_excitation_power[1])


@pytest.mark.parametrize("which", ["target", "masker", "both"])
def test_zero_energy_pairs_have_no_fabricated_finite_margin(which: str) -> None:
    tone = _tone()
    silence = np.zeros_like(tone)
    masker = silence if which in ("masker", "both") else tone
    target = silence if which in ("target", "both") else tone
    output = _analyze_pair(masker, target)

    assert output.frequency_masking.state.status is ResultStatus.INSUFFICIENT_EVIDENCE
    assert not np.any(output.margin_defined)
    assert np.all(np.isfinite(output.relative_excitation_margin_db))


def test_near_silence_remains_finite_without_a_perceptual_epsilon() -> None:
    tiny = _tone(amplitude=np.finfo(np.float64).tiny)
    output = _analyze_pair(tiny, tiny)

    assert np.all(np.isfinite(output.masker_excitation_power))
    assert np.all(np.isfinite(output.target_excitation_power))
    assert np.all(np.isfinite(output.relative_excitation_margin_db))


@pytest.mark.parametrize("sample_rate", [44_100, 48_000])
def test_valid_common_sample_rates_produce_finite_results(sample_rate: int) -> None:
    tone = _tone(sample_rate=sample_rate)
    output = _analyze_pair(tone, tone, sample_rate=sample_rate)

    assert np.all(np.isfinite(output.masker_excitation_power))
    assert output.frequency_masking.state.status is ResultStatus.COMPUTED


def test_low_sample_rate_without_supported_filter_centers_is_insufficient() -> None:
    samples = np.ones(100, dtype=np.float64)
    output = _analyze_pair(samples, samples, sample_rate=100)

    assert output.frequency_masking.state.status is ResultStatus.INSUFFICIENT_EVIDENCE
    assert output.masker_excitation_power.shape[-1] == 0


def test_short_odd_pair_and_zero_padded_final_frame_remain_finite() -> None:
    samples = np.linspace(-0.25, 0.25, 1001)
    output = _analyze_pair(samples, samples)

    assert output.frame_times_seconds[-1] > len(samples) / 48_000
    assert output.frequency_masking.events == []
    assert np.all(np.isfinite(output.masker_excitation_power))


def test_seeded_broadband_and_narrowband_noise_are_finite() -> None:
    rng = np.random.default_rng(42)
    broadband = rng.normal(0.0, 0.05, 4800)
    narrowband = _tone(1200.0) + _tone(1250.0)
    output = _analyze_pair(broadband, narrowband)

    assert np.all(np.isfinite(output.masker_excitation_power))
    assert np.all(np.isfinite(output.target_excitation_power))


def test_impulse_pair_is_deterministic_and_finite() -> None:
    impulse = np.zeros(3001)
    impulse[100] = 1.0
    first = _analyze_pair(impulse, impulse)
    second = _analyze_pair(impulse.copy(), impulse.copy())

    assert np.array_equal(first.masker_excitation_power, second.masker_excitation_power)
    assert np.array_equal(first.relative_excitation_margin_db, second.relative_excitation_margin_db)


def test_runtime_matrices_are_finite_and_read_only() -> None:
    output = _analyze_pair(_tone(), _tone())

    for matrix in (
        output.masker_excitation_power,
        output.target_excitation_power,
        output.relative_excitation_margin_db,
        output.margin_defined,
    ):
        assert np.all(np.isfinite(matrix))
        assert matrix.flags.writeable is False


def test_transport_round_trip_contains_no_runtime_matrices_or_events() -> None:
    output = _analyze_pair(_tone(), _tone())
    payload = output.frequency_masking.to_dict()

    assert FrequencyMaskingResult.from_dict(payload) == output.frequency_masking
    assert json.loads(json.dumps(payload, allow_nan=False)) == payload
    assert payload["events"] == []
    assert "masker_excitation_power" not in payload
    assert "relative_excitation_margin_db" not in payload


@pytest.mark.parametrize("invalid", [np.nan, np.inf, -np.inf])
def test_non_finite_audio_is_rejected(invalid: float) -> None:
    samples = _tone()
    samples[3] = invalid

    with pytest.raises(ValueError, match="finite"):
        _analyze_pair(samples, _tone())


def test_frequency_masking_foundation_capability_is_implemented_not_verified() -> None:
    capability = registry.get("frequency_masking_foundation")

    assert capability is not None
    assert capability.status is CapabilityStatus.IMPLEMENTED
    assert capability.tested_in_freeze is False


def test_perception_root_import_remains_numpy_lightweight_with_masking_contract() -> None:
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
