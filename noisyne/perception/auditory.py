from __future__ import annotations

from dataclasses import dataclass
from itertools import pairwise

import numpy as np
from numpy.typing import NDArray

from noisyne.audio.io.models import AudioData

from .auditory_contracts import (
    AUDITORY_FRONTEND_METHOD_ID,
    AUDITORY_FRONTEND_METHOD_VERSION,
    AuditoryFrontendConfig,
    AuditoryFrontendSummary,
)
from .common import AuditoryBand, FrequencyRange, MethodMetadata, TimeRange

FloatArray = NDArray[np.float64]


def hz_to_erb_rate(frequency_hz: float | FloatArray) -> float | FloatArray:
    """Glasberg-Moore (1990) ERB-rate mapping for non-negative hertz."""
    values = np.asarray(frequency_hz, dtype=np.float64)
    if np.any(~np.isfinite(values)) or np.any(values < 0.0):
        raise ValueError("frequency_hz must contain only finite non-negative values")
    result = 21.4 * np.log10(1.0 + 4.37 * values / 1000.0)
    return float(result) if values.ndim == 0 else result


def erb_rate_to_hz(erb_rate: float | FloatArray) -> float | FloatArray:
    """Inverse Glasberg-Moore (1990) ERB-rate mapping."""
    values = np.asarray(erb_rate, dtype=np.float64)
    if np.any(~np.isfinite(values)) or np.any(values < 0.0):
        raise ValueError("erb_rate must contain only finite non-negative values")
    result = (np.power(10.0, values / 21.4) - 1.0) * (1000.0 / 4.37)
    return float(result) if values.ndim == 0 else result


@dataclass(frozen=True, slots=True)
class AuditoryFrontendResult:
    """Runtime numerical result with a separate JSON-safe summary."""

    summary: AuditoryFrontendSummary
    linear_frequencies_hz: FloatArray
    frame_times_seconds: FloatArray
    channel_power_spectra: FloatArray
    auditory_band_power: FloatArray

    def __post_init__(self) -> None:
        channels = self.summary.channel_count
        frames = self.summary.frame_count
        bins = self.summary.linear_frequency_bin_count
        bands = len(self.summary.auditory_bands)
        if self.linear_frequencies_hz.shape != (bins,):
            raise ValueError("linear_frequencies_hz shape does not match summary")
        if self.frame_times_seconds.shape != (frames,):
            raise ValueError("frame_times_seconds shape does not match summary")
        if self.channel_power_spectra.shape != (channels, frames, bins):
            raise ValueError("channel_power_spectra shape does not match summary")
        if self.auditory_band_power.shape != (channels, frames, bands):
            raise ValueError("auditory_band_power shape does not match summary")


class AuditoryFrontend:
    """Deterministic channel-preserving spectral frontend for later V2 models."""

    def __init__(self, config: AuditoryFrontendConfig | None = None) -> None:
        self.config = config or AuditoryFrontendConfig()

    def analyze(self, audio: AudioData) -> AuditoryFrontendResult:
        samples, sample_rate = _validated_samples(audio)
        config = self.config
        frame_count = (
            1
            + (max(samples.shape[0] - config.frame_size_samples, 0) + config.hop_size_samples - 1)
            // config.hop_size_samples
        )
        required_samples = (frame_count - 1) * config.hop_size_samples + config.frame_size_samples
        padded = np.zeros((required_samples, samples.shape[1]), dtype=np.float64)
        padded[: samples.shape[0]] = samples

        framed = np.lib.stride_tricks.sliding_window_view(
            padded, config.frame_size_samples, axis=0
        )[:: config.hop_size_samples]
        framed = np.transpose(framed, (1, 0, 2))
        window = _periodic_hann(config.frame_size_samples)
        transformed = np.fft.rfft(framed * window, n=config.fft_size, axis=-1)
        power = np.square(np.abs(transformed)) / (config.fft_size * np.sum(np.square(window)))
        if config.fft_size % 2 == 0:
            power[..., 1:-1] *= 2.0
        else:
            power[..., 1:] *= 2.0

        frequencies = np.fft.rfftfreq(config.fft_size, d=1.0 / sample_rate)
        edges_hz, bands = _erb_bands(sample_rate, config.erb_step)
        band_indexes = np.searchsorted(edges_hz, frequencies, side="right") - 1
        band_indexes = np.clip(band_indexes, 0, len(bands) - 1)
        band_power = np.stack(
            [np.sum(power[..., band_indexes == index], axis=-1) for index in range(len(bands))],
            axis=-1,
        )

        frame_starts = np.arange(frame_count, dtype=np.float64) * config.hop_size_samples
        frame_times = (frame_starts + config.frame_size_samples / 2.0) / sample_rate
        duration = samples.shape[0] / sample_rate
        peak = float(np.max(np.abs(samples)))
        summary = AuditoryFrontendSummary(
            method=MethodMetadata(
                method_id=AUDITORY_FRONTEND_METHOD_ID,
                version=AUDITORY_FRONTEND_METHOD_VERSION,
                description="Deterministic channel-preserving spectral and ERB-rate frontend.",
            ),
            config=config,
            source_sample_rate_hz=sample_rate,
            source_sample_count=samples.shape[0],
            channel_count=samples.shape[1],
            duration_seconds=duration,
            source_time_range=TimeRange(start_seconds=0.0, end_seconds=duration),
            frame_count=frame_count,
            linear_frequency_bin_count=frequencies.size,
            auditory_bands=bands,
            input_peak_absolute=peak,
            nominal_full_scale_exceeded=peak > 1.0,
        )

        arrays = (frequencies, frame_times, power, band_power)
        for array in arrays:
            array.setflags(write=False)
        return AuditoryFrontendResult(summary, frequencies, frame_times, power, band_power)


def _validated_samples(audio: AudioData) -> tuple[FloatArray, int]:
    sample_rate = audio.metadata.sample_rate
    if type(sample_rate) is not int or sample_rate <= 0:
        raise ValueError("audio sample rate must be a positive integer")
    if type(audio.metadata.channels) is not int or audio.metadata.channels <= 0:
        raise ValueError("audio metadata channels must be a positive integer")
    raw = np.asarray(audio.samples)
    if raw.ndim not in (1, 2):
        raise ValueError("audio samples must have shape (frames,) or (frames, channels)")
    if raw.shape[0] == 0:
        raise ValueError("audio samples must not be empty")
    if raw.ndim == 2 and raw.shape[1] == 0:
        raise ValueError("audio samples must contain at least one channel")
    if not np.issubdtype(raw.dtype, np.number) or np.issubdtype(raw.dtype, np.complexfloating):
        raise TypeError("audio samples must be real numeric values")
    values = np.array(raw, dtype=np.float64, order="C", copy=True)
    if values.ndim == 1:
        values = values[:, np.newaxis]
    if not np.all(np.isfinite(values)):
        raise ValueError("audio samples must contain only finite values")
    if audio.metadata.channels != values.shape[1]:
        raise ValueError("audio metadata channel count does not match sample shape")
    return values, sample_rate


def _periodic_hann(length: int) -> FloatArray:
    if length == 1:
        return np.ones(1, dtype=np.float64)
    indexes = np.arange(length, dtype=np.float64)
    return 0.5 - 0.5 * np.cos(2.0 * np.pi * indexes / length)


def _erb_bands(sample_rate: int, erb_step: float) -> tuple[FloatArray, list[AuditoryBand]]:
    nyquist_hz = sample_rate / 2.0
    maximum_rate = float(hz_to_erb_rate(nyquist_hz))
    interior_rates = np.arange(0.0, maximum_rate, erb_step, dtype=np.float64)
    edge_rates = np.append(interior_rates, maximum_rate)
    if edge_rates.size < 2:
        edge_rates = np.array([0.0, maximum_rate], dtype=np.float64)
    edges_hz = np.asarray(erb_rate_to_hz(edge_rates), dtype=np.float64)
    edges_hz[0] = 0.0
    edges_hz[-1] = nyquist_hz
    scale_method = MethodMetadata(
        method_id="glasberg_moore_erb_rate",
        version="1990-equation",
        description="Equal ERB-rate intervals over the retained linear-Hz spectrum.",
    )
    bands = []
    for index, (lower_rate, upper_rate) in enumerate(pairwise(edge_rates)):
        lower_hz = float(edges_hz[index])
        upper_hz = float(edges_hz[index + 1])
        center_hz = float(erb_rate_to_hz((lower_rate + upper_rate) / 2.0))
        bands.append(
            AuditoryBand(
                frequency_range=FrequencyRange(lower_hz=lower_hz, upper_hz=upper_hz),
                center_hz=center_hz,
                band_index=index,
                scale_id="erb_rate_glasberg_moore_1990",
                method=scale_method,
            )
        )
    return edges_hz, bands
