from __future__ import annotations

from dataclasses import dataclass, replace

import numpy as np
from numpy.typing import NDArray

from noisyne.audio.io.models import AudioData

from .common import MethodMetadata
from .transfer_contracts import (
    PLAYBACK_TRANSFER_METHOD_ID,
    PLAYBACK_TRANSFER_METHOD_VERSION,
    ImpulseResponseSummary,
    MagnitudeInterpolationPolicy,
    MagnitudeResponseSummary,
    PlaybackTransferApplicationSummary,
    PlaybackTransferProfile,
    TransferChannelTopology,
    TransferGainBasis,
    TransferKind,
)

FloatArray = NDArray[np.float64]


@dataclass(frozen=True, slots=True)
class MagnitudeResponseEvidence:
    """Tabulated magnitude evidence; it is not a complete time-domain transfer."""

    profile: PlaybackTransferProfile
    frequency_hz: FloatArray
    magnitude_db: FloatArray

    def __post_init__(self) -> None:
        if self.profile.transfer_kind is not TransferKind.MAGNITUDE_RESPONSE:
            raise ValueError("profile must describe magnitude_response")
        _validate_read_only_float_array(self.frequency_hz, "frequency_hz", dimensions=1)
        _validate_read_only_float_array(self.magnitude_db, "magnitude_db", dimensions=1)
        if self.frequency_hz.size < 2:
            raise ValueError("magnitude response requires at least two points")
        if self.frequency_hz.shape != self.magnitude_db.shape:
            raise ValueError("frequency_hz and magnitude_db shapes must match")
        if np.any(self.frequency_hz <= 0.0):
            raise ValueError("frequency_hz values must be positive for log-frequency interpolation")
        if np.any(np.diff(self.frequency_hz) <= 0.0):
            raise ValueError("frequency_hz must be strictly increasing without duplicates")
        valid_range = self.profile.valid_frequency_range
        if valid_range is None:  # pragma: no cover - profile contract guard
            raise ValueError("magnitude profile requires valid_frequency_range")
        if (
            float(self.frequency_hz[0]) != valid_range.lower_hz
            or float(self.frequency_hz[-1]) != valid_range.upper_hz
        ):
            raise ValueError("valid_frequency_range must equal the tabulated response bounds")

    @property
    def summary(self) -> MagnitudeResponseSummary:
        return MagnitudeResponseSummary(
            profile=self.profile,
            point_count=self.frequency_hz.size,
            minimum_frequency_hz=float(self.frequency_hz[0]),
            maximum_frequency_hz=float(self.frequency_hz[-1]),
        )

    def magnitude_at(self, frequency_hz: float | FloatArray) -> float | FloatArray:
        """Evaluate log-frequency/linear-dB interpolation; extrapolation is rejected."""

        query = np.asarray(frequency_hz, dtype=np.float64)
        if np.any(~np.isfinite(query)) or np.any(query <= 0.0):
            raise ValueError("frequency_hz queries must be finite and positive")
        if np.any(query < self.frequency_hz[0]) or np.any(query > self.frequency_hz[-1]):
            raise ValueError(
                "frequency_hz query is outside the valid range; extrapolation is rejected"
            )
        if self.profile.interpolation_policy is not MagnitudeInterpolationPolicy.LOG_FREQUENCY_DB:
            raise ValueError("unsupported magnitude interpolation policy")
        result = np.interp(
            np.log(query),
            np.log(self.frequency_hz),
            self.magnitude_db,
        )
        if query.ndim == 0:
            return float(result)
        result.setflags(write=False)
        return result

    def amplitude_ratio_at(self, frequency_hz: float | FloatArray) -> float | FloatArray:
        """Convert interpolated dB to an amplitude ratio for relative/digital gain evidence."""

        if self.profile.gain_basis is TransferGainBasis.ABSOLUTE_ACOUSTIC_OUTPUT:
            raise ValueError("absolute acoustic output evidence is not an amplitude ratio")
        magnitude_db = self.magnitude_at(frequency_hz)
        try:
            with np.errstate(over="raise", under="raise", invalid="raise"):
                result = np.power(10.0, np.asarray(magnitude_db) / 20.0)
        except FloatingPointError as exc:
            raise ValueError(
                "magnitude-to-amplitude conversion is not representable as a positive float64"
            ) from exc
        if np.any(~np.isfinite(result)) or np.any(result <= 0.0):
            raise ValueError(
                "magnitude-to-amplitude conversion must produce finite, positive values"
            )
        if np.asarray(frequency_hz).ndim == 0:
            return float(result)
        result.setflags(write=False)
        return result


@dataclass(frozen=True, slots=True)
class ImpulseResponseTransfer:
    """Explicit real FIR, including its supplied phase and declared time origin."""

    profile: PlaybackTransferProfile
    impulse_response: FloatArray

    def __post_init__(self) -> None:
        if self.profile.transfer_kind is not TransferKind.IMPULSE_RESPONSE:
            raise ValueError("profile must describe impulse_response")
        _validate_read_only_float_array(self.impulse_response, "impulse_response", dimensions=2)
        transfer_channels, tap_count = self.impulse_response.shape
        if transfer_channels == 0 or tap_count == 0:
            raise ValueError("impulse_response must contain channels and taps")
        if self.profile.channel_topology is TransferChannelTopology.CHANNEL_INDEPENDENT_SHARED:
            if transfer_channels != 1:
                raise ValueError(
                    "channel_independent_shared impulse response requires one transfer channel"
                )
        elif transfer_channels != self.profile.expected_input_channels:
            raise ValueError(
                "explicit_per_channel impulse response must match expected_input_channels"
            )

    @property
    def summary(self) -> ImpulseResponseSummary:
        return ImpulseResponseSummary(
            profile=self.profile,
            transfer_channel_count=self.impulse_response.shape[0],
            tap_count=self.impulse_response.shape[1],
        )


@dataclass(frozen=True, slots=True)
class PlaybackTransferResult:
    """Transformed AudioData plus compact JSON-safe audit metadata."""

    audio: AudioData
    summary: PlaybackTransferApplicationSummary


class PlaybackTransferEngine:
    """Deterministic full linear convolution for explicit real FIR evidence only."""

    def apply(self, audio: AudioData, transfer: ImpulseResponseTransfer) -> PlaybackTransferResult:
        samples, was_mono = _validated_samples(audio)
        profile = transfer.profile
        if audio.metadata.sample_rate != profile.sample_rate_hz:
            raise ValueError("audio and impulse-response sample rates must match")
        if (
            profile.channel_topology is TransferChannelTopology.EXPLICIT_PER_CHANNEL
            and samples.shape[1] != profile.expected_input_channels
        ):
            raise ValueError("audio channel count does not match explicit transfer topology")

        tap_count = transfer.impulse_response.shape[1]
        output = np.empty((samples.shape[0] + tap_count - 1, samples.shape[1]), dtype=np.float64)
        try:
            with np.errstate(over="raise", invalid="raise", divide="raise"):
                for channel in range(samples.shape[1]):
                    transfer_channel = (
                        0
                        if profile.channel_topology
                        is TransferChannelTopology.CHANNEL_INDEPENDENT_SHARED
                        else channel
                    )
                    output[:, channel] = np.convolve(
                        samples[:, channel],
                        transfer.impulse_response[transfer_channel],
                        mode="full",
                    )
        except FloatingPointError as exc:
            raise ValueError("playback transfer convolution overflowed") from exc
        if not np.all(np.isfinite(output)):
            raise ValueError("playback transfer convolution produced non-finite output")

        output_samples = output[:, 0] if was_mono else output
        output_samples.setflags(write=False)
        output_metadata = replace(
            audio.metadata,
            duration=output.shape[0] / audio.metadata.sample_rate,
            file_size=output_samples.nbytes,
        )
        peak = float(np.max(np.abs(output)))
        summary = PlaybackTransferApplicationSummary(
            method=MethodMetadata(
                method_id=PLAYBACK_TRANSFER_METHOD_ID,
                version=PLAYBACK_TRANSFER_METHOD_VERSION,
                description="Explicit real-FIR full linear convolution",
            ),
            transfer=transfer.summary,
            input_sample_count=samples.shape[0],
            output_sample_count=output.shape[0],
            channel_count=samples.shape[1],
            output_peak_absolute=peak,
            nominal_full_scale_exceeded=peak > 1.0,
        )
        return PlaybackTransferResult(
            audio=AudioData(samples=output_samples, metadata=output_metadata),
            summary=summary,
        )


def _validated_samples(audio: AudioData) -> tuple[FloatArray, bool]:
    sample_rate = audio.metadata.sample_rate
    if type(sample_rate) is not int or sample_rate <= 0:
        raise ValueError("audio sample rate must be a positive integer")
    raw = np.asarray(audio.samples)
    if raw.ndim not in (1, 2) or raw.shape[0] == 0:
        raise ValueError("audio samples must be non-empty mono or channel-last audio")
    if raw.ndim == 2 and raw.shape[1] == 0:
        raise ValueError("audio samples must contain at least one channel")
    if not np.issubdtype(raw.dtype, np.number) or np.issubdtype(raw.dtype, np.complexfloating):
        raise TypeError("audio samples must be real numeric values")
    values = np.array(raw, dtype=np.float64, order="C", copy=True)
    was_mono = values.ndim == 1
    if was_mono:
        values = values[:, np.newaxis]
    if not np.all(np.isfinite(values)):
        raise ValueError("audio samples must contain only finite values")
    if audio.metadata.channels != values.shape[1]:
        raise ValueError("audio metadata channel count does not match sample shape")
    return values, was_mono


def _validate_read_only_float_array(array: np.ndarray, name: str, *, dimensions: int) -> None:
    if not isinstance(array, np.ndarray):
        raise TypeError(f"{name} must be a NumPy array")
    if array.ndim != dimensions:
        raise ValueError(f"{name} must have {dimensions} dimensions")
    if array.dtype != np.dtype(np.float64):
        raise ValueError(f"{name} must use float64 dtype")
    if not np.all(np.isfinite(array)):
        raise ValueError(f"{name} must contain only finite values")
    if array.flags.writeable:
        raise ValueError(f"{name} must be read-only")


__all__ = [
    "ImpulseResponseTransfer",
    "MagnitudeResponseEvidence",
    "PlaybackTransferEngine",
    "PlaybackTransferResult",
]
