from __future__ import annotations

import math
from typing import Any

import numpy as np

from .validation_contracts import FixtureKind, ValidationFixtureProvider


class PhasenoxValidationFixtureProvider(ValidationFixtureProvider):
    """Deterministic, offline fixture generator for Sprint 12 validation."""

    def generate(
        self,
        kind: FixtureKind,
        sample_rate_hz: int,
        duration_seconds: float,
        channel_count: int,
        **kwargs: Any,
    ) -> dict[str, Any]:
        if sample_rate_hz <= 0:
            raise ValueError("sample_rate_hz must be positive")
        if duration_seconds < 0:
            raise ValueError("duration_seconds must be non-negative")
        if channel_count <= 0:
            raise ValueError("channel_count must be positive")

        sample_count = round(sample_rate_hz * duration_seconds)

        if kind is FixtureKind.SILENCE:
            return self._silence(sample_rate_hz, sample_count, channel_count)
        if kind is FixtureKind.ZERO_ENERGY:
            return self._zero_energy(sample_rate_hz, sample_count, channel_count)
        if kind is FixtureKind.SINGLE_SINE:
            frequency_hz = float(kwargs.get("frequency_hz", 1000.0))
            return self._single_sine(sample_rate_hz, sample_count, channel_count, frequency_hz)
        if kind is FixtureKind.KNOWN_AMPLITUDE_SINE:
            frequency_hz = float(kwargs.get("frequency_hz", 1000.0))
            amplitude = float(kwargs.get("amplitude", 0.5))
            return self._known_amplitude_sine(
                sample_rate_hz, sample_count, channel_count, frequency_hz, amplitude
            )
        if kind is FixtureKind.TWO_TONE:
            frequency_a_hz = float(kwargs.get("frequency_a_hz", 1000.0))
            frequency_b_hz = float(kwargs.get("frequency_b_hz", 2000.0))
            amplitude_a = float(kwargs.get("amplitude_a", 0.5))
            amplitude_b = float(kwargs.get("amplitude_b", 0.5))
            return self._two_tone(
                sample_rate_hz,
                sample_count,
                channel_count,
                frequency_a_hz,
                frequency_b_hz,
                amplitude_a,
                amplitude_b,
            )
        if kind is FixtureKind.KNOWN_DIGITAL_GAIN:
            gain_db = float(kwargs.get("gain_db", 6.0))
            return self._known_digital_gain(sample_rate_hz, sample_count, channel_count, gain_db)
        if kind is FixtureKind.KNOWN_SAMPLE_PEAK:
            peak = float(kwargs.get("peak", 0.8))
            return self._known_sample_peak(sample_rate_hz, sample_count, channel_count, peak)
        if kind is FixtureKind.KNOWN_SPECTRAL_SHIFT:
            source_frequency_hz = float(kwargs.get("source_frequency_hz", 1000.0))
            target_frequency_hz = float(kwargs.get("target_frequency_hz", 2000.0))
            return self._known_spectral_shift(
                sample_rate_hz,
                sample_count,
                channel_count,
                source_frequency_hz,
                target_frequency_hz,
            )
        if kind is FixtureKind.DETERMINISTIC_ERB_ENERGY:
            frequency_hz = float(kwargs.get("frequency_hz", 1000.0))
            return self._deterministic_erb_energy(
                sample_rate_hz, sample_count, channel_count, frequency_hz
            )
        if kind is FixtureKind.IDENTICAL_SOURCE_REFERENCE:
            return self._identical_source_reference(sample_rate_hz, sample_count, channel_count)
        if kind is FixtureKind.EXACT_PLAYBACK_TRANSFER:
            return self._exact_playback_transfer(
                sample_rate_hz, sample_count, channel_count, kwargs
            )
        if kind is FixtureKind.EXACT_POLICY_BOUNDARY:
            return self._exact_policy_boundary(sample_rate_hz, sample_count, channel_count, kwargs)

        raise ValueError(f"unsupported fixture kind: {kind.value}")

    def _silence(
        self, sample_rate_hz: int, sample_count: int, channel_count: int
    ) -> dict[str, Any]:
        array = np.zeros((sample_count, channel_count), dtype=np.float64)
        return {
            "kind": FixtureKind.SILENCE.value,
            "sample_rate_hz": sample_rate_hz,
            "sample_count": sample_count,
            "channel_count": channel_count,
            "array": array,
            "expected_peak_absolute": 0.0,
            "expected_rms": 0.0,
        }

    def _zero_energy(
        self, sample_rate_hz: int, sample_count: int, channel_count: int
    ) -> dict[str, Any]:
        # Semantically identical to silence for digital signals, but distinct fixture
        array = np.zeros((sample_count, channel_count), dtype=np.float64)
        return {
            "kind": FixtureKind.ZERO_ENERGY.value,
            "sample_rate_hz": sample_rate_hz,
            "sample_count": sample_count,
            "channel_count": channel_count,
            "array": array,
            "expected_total_energy": 0.0,
            "expected_power": 0.0,
        }

    def _single_sine(
        self,
        sample_rate_hz: int,
        sample_count: int,
        channel_count: int,
        frequency_hz: float,
    ) -> dict[str, Any]:
        t = np.arange(sample_count, dtype=np.float64) / sample_rate_hz
        samples = np.sin(2.0 * math.pi * frequency_hz * t)
        array = np.stack([samples] * channel_count, axis=1)
        return {
            "kind": FixtureKind.SINGLE_SINE.value,
            "sample_rate_hz": sample_rate_hz,
            "sample_count": sample_count,
            "channel_count": channel_count,
            "frequency_hz": frequency_hz,
            "array": array,
            "expected_peak_absolute": 1.0,
            "expected_rms": 1.0 / math.sqrt(2.0),
        }

    def _known_amplitude_sine(
        self,
        sample_rate_hz: int,
        sample_count: int,
        channel_count: int,
        frequency_hz: float,
        amplitude: float,
    ) -> dict[str, Any]:
        t = np.arange(sample_count, dtype=np.float64) / sample_rate_hz
        samples = amplitude * np.sin(2.0 * math.pi * frequency_hz * t)
        array = np.stack([samples] * channel_count, axis=1)
        return {
            "kind": FixtureKind.KNOWN_AMPLITUDE_SINE.value,
            "sample_rate_hz": sample_rate_hz,
            "sample_count": sample_count,
            "channel_count": channel_count,
            "frequency_hz": frequency_hz,
            "amplitude": amplitude,
            "array": array,
            "expected_peak_absolute": amplitude,
            "expected_rms": amplitude / math.sqrt(2.0),
        }

    def _two_tone(
        self,
        sample_rate_hz: int,
        sample_count: int,
        channel_count: int,
        frequency_a_hz: float,
        frequency_b_hz: float,
        amplitude_a: float,
        amplitude_b: float,
    ) -> dict[str, Any]:
        t = np.arange(sample_count, dtype=np.float64) / sample_rate_hz
        samples = amplitude_a * np.sin(2.0 * math.pi * frequency_a_hz * t)
        samples += amplitude_b * np.sin(2.0 * math.pi * frequency_b_hz * t)
        array = np.stack([samples] * channel_count, axis=1)
        return {
            "kind": FixtureKind.TWO_TONE.value,
            "sample_rate_hz": sample_rate_hz,
            "sample_count": sample_count,
            "channel_count": channel_count,
            "frequency_a_hz": frequency_a_hz,
            "frequency_b_hz": frequency_b_hz,
            "amplitude_a": amplitude_a,
            "amplitude_b": amplitude_b,
            "array": array,
            "expected_peak_absolute": amplitude_a + amplitude_b,
        }

    def _known_digital_gain(
        self,
        sample_rate_hz: int,
        sample_count: int,
        channel_count: int,
        gain_db: float,
    ) -> dict[str, Any]:
        # Generate a sine, then apply known digital gain
        t = np.arange(sample_count, dtype=np.float64) / sample_rate_hz
        frequency_hz = 1000.0
        samples = np.sin(2.0 * math.pi * frequency_hz * t)
        linear_gain = 10.0 ** (gain_db / 20.0)
        array = np.stack([samples * linear_gain] * channel_count, axis=1)
        return {
            "kind": FixtureKind.KNOWN_DIGITAL_GAIN.value,
            "sample_rate_hz": sample_rate_hz,
            "sample_count": sample_count,
            "channel_count": channel_count,
            "gain_db": gain_db,
            "linear_gain": linear_gain,
            "array": array,
            "expected_peak_absolute": linear_gain,
        }

    def _known_sample_peak(
        self,
        sample_rate_hz: int,
        sample_count: int,
        channel_count: int,
        peak: float,
    ) -> dict[str, Any]:
        # Constant DC at known peak (not musically meaningful but deterministic)
        array = np.full((sample_count, channel_count), peak, dtype=np.float64)
        return {
            "kind": FixtureKind.KNOWN_SAMPLE_PEAK.value,
            "sample_rate_hz": sample_rate_hz,
            "sample_count": sample_count,
            "channel_count": channel_count,
            "peak": peak,
            "array": array,
            "expected_peak_absolute": abs(peak),
        }

    def _known_spectral_shift(
        self,
        sample_rate_hz: int,
        sample_count: int,
        channel_count: int,
        source_frequency_hz: float,
        target_frequency_hz: float,
    ) -> dict[str, Any]:
        t = np.arange(sample_count, dtype=np.float64) / sample_rate_hz
        source = np.sin(2.0 * math.pi * source_frequency_hz * t)
        target = np.sin(2.0 * math.pi * target_frequency_hz * t)
        source_array = np.stack([source] * channel_count, axis=1)
        target_array = np.stack([target] * channel_count, axis=1)
        return {
            "kind": FixtureKind.KNOWN_SPECTRAL_SHIFT.value,
            "sample_rate_hz": sample_rate_hz,
            "sample_count": sample_count,
            "channel_count": channel_count,
            "source_frequency_hz": source_frequency_hz,
            "target_frequency_hz": target_frequency_hz,
            "source_array": source_array,
            "target_array": target_array,
            "expected_centroid_delta_hz": target_frequency_hz - source_frequency_hz,
        }

    def _deterministic_erb_energy(
        self,
        sample_rate_hz: int,
        sample_count: int,
        channel_count: int,
        frequency_hz: float,
    ) -> dict[str, Any]:
        # Single sine at known frequency to validate ERB energy placement
        t = np.arange(sample_count, dtype=np.float64) / sample_rate_hz
        samples = np.sin(2.0 * math.pi * frequency_hz * t)
        array = np.stack([samples] * channel_count, axis=1)
        return {
            "kind": FixtureKind.DETERMINISTIC_ERB_ENERGY.value,
            "sample_rate_hz": sample_rate_hz,
            "sample_count": sample_count,
            "channel_count": channel_count,
            "frequency_hz": frequency_hz,
            "array": array,
            "expected_dominant_erb_band_contains_hz": frequency_hz,
        }

    def _identical_source_reference(
        self, sample_rate_hz: int, sample_count: int, channel_count: int
    ) -> dict[str, Any]:
        t = np.arange(sample_count, dtype=np.float64) / sample_rate_hz
        frequency_hz = 1000.0
        samples = np.sin(2.0 * math.pi * frequency_hz * t)
        array = np.stack([samples] * channel_count, axis=1)
        return {
            "kind": FixtureKind.IDENTICAL_SOURCE_REFERENCE.value,
            "sample_rate_hz": sample_rate_hz,
            "sample_count": sample_count,
            "channel_count": channel_count,
            "array": array,
            "expected_all_deltas_zero": True,
        }

    def _exact_playback_transfer(
        self,
        sample_rate_hz: int,
        sample_count: int,
        channel_count: int,
        kwargs: dict[str, Any],
    ) -> dict[str, Any]:
        # Delta impulse: output must equal input (plus tail)
        fir_taps = np.array([1.0], dtype=np.float64)
        t = np.arange(sample_count, dtype=np.float64) / sample_rate_hz
        frequency_hz = 1000.0
        samples = np.sin(2.0 * math.pi * frequency_hz * t)
        array = np.stack([samples] * channel_count, axis=1)
        return {
            "kind": FixtureKind.EXACT_PLAYBACK_TRANSFER.value,
            "sample_rate_hz": sample_rate_hz,
            "sample_count": sample_count,
            "channel_count": channel_count,
            "fir_taps": fir_taps,
            "array": array,
            "expected_output_peak_match": True,
        }

    def _exact_policy_boundary(
        self,
        sample_rate_hz: int,
        sample_count: int,
        channel_count: int,
        kwargs: dict[str, Any],
    ) -> dict[str, Any]:
        # Generate a signal with exact properties for policy boundary testing
        threshold = float(kwargs.get("threshold", 0.5))
        operator = str(kwargs.get("operator", "greater_than"))
        # Use a value just above or below threshold for boundary testing
        value = threshold + 1e-6 if operator.startswith("greater") else threshold - 1e-6
        samples = np.full(sample_count, value, dtype=np.float64)
        array = np.stack([samples] * channel_count, axis=1)
        return {
            "kind": FixtureKind.EXACT_POLICY_BOUNDARY.value,
            "sample_rate_hz": sample_rate_hz,
            "sample_count": sample_count,
            "channel_count": channel_count,
            "threshold": threshold,
            "operator": operator,
            "value": value,
            "array": array,
        }


NoisyneValidationFixtureProvider = PhasenoxValidationFixtureProvider

__all__ = [
    "NoisyneValidationFixtureProvider",
    "PhasenoxValidationFixtureProvider",
]
