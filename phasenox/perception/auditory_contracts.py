from __future__ import annotations

from dataclasses import dataclass, field

from ._serialization import JsonContract
from .common import (
    AuditoryBand,
    MethodMetadata,
    TimeRange,
    _require_finite_number,
    _require_identifier,
    _require_non_negative,
    _require_positive_integer,
)

AUDITORY_FRONTEND_METHOD_ID = "noisyne.auditory_frontend"
AUDITORY_FRONTEND_METHOD_VERSION = "1.0.0"
AUDITORY_FRONTEND_SCHEMA_VERSION = "1.0.0"


@dataclass(frozen=True, slots=True)
class AuditoryFrontendConfig(JsonContract):
    """Small, versioned configuration for deterministic spectral preparation."""

    frame_size_samples: int = 2048
    hop_size_samples: int = 512
    fft_size: int = 2048
    window_id: str = "periodic_hann"
    boundary_policy: str = "zero_pad_end"
    channel_policy: str = "per_channel_preserve"
    spectral_representation_id: str = "one_sided_window_power"
    auditory_scale_id: str = "erb_rate_glasberg_moore_1990"
    erb_step: float = 1.0

    def __post_init__(self) -> None:
        _require_positive_integer(self.frame_size_samples, "frame_size_samples")
        _require_positive_integer(self.hop_size_samples, "hop_size_samples")
        _require_positive_integer(self.fft_size, "fft_size")
        if self.hop_size_samples > self.frame_size_samples:
            raise ValueError("hop_size_samples must not exceed frame_size_samples")
        if self.fft_size < self.frame_size_samples:
            raise ValueError("fft_size must be greater than or equal to frame_size_samples")
        if self.window_id != "periodic_hann":
            raise ValueError("only the periodic_hann window is supported in method version 1.0.0")
        if self.boundary_policy != "zero_pad_end":
            raise ValueError("only zero_pad_end is supported in method version 1.0.0")
        if self.channel_policy != "per_channel_preserve":
            raise ValueError("only per_channel_preserve is supported in method version 1.0.0")
        if self.spectral_representation_id != "one_sided_window_power":
            raise ValueError("only one_sided_window_power is supported in method version 1.0.0")
        if self.auditory_scale_id != "erb_rate_glasberg_moore_1990":
            raise ValueError(
                "only erb_rate_glasberg_moore_1990 is supported in method version 1.0.0"
            )
        _require_finite_number(self.erb_step, "erb_step")
        if not 0.25 <= float(self.erb_step) <= 4.0:
            raise ValueError("erb_step must be within [0.25, 4.0]")


@dataclass(frozen=True, slots=True)
class AuditoryFrontendSummary(JsonContract):
    """Transport-safe audit metadata; numerical frame matrices remain runtime-only."""

    method: MethodMetadata
    config: AuditoryFrontendConfig
    source_sample_rate_hz: int
    source_sample_count: int
    channel_count: int
    duration_seconds: float
    source_time_range: TimeRange
    frame_count: int
    linear_frequency_bin_count: int
    auditory_bands: list[AuditoryBand]
    input_peak_absolute: float
    nominal_full_scale_exceeded: bool
    level_reference: str = "digital_sample_amplitude_uncalibrated"
    spl_calibrated: bool = False
    arrays_serialized: bool = False
    schema_version: str = AUDITORY_FRONTEND_SCHEMA_VERSION
    limitations: list[str] = field(
        default_factory=lambda: [
            "No sound-pressure-level calibration is available.",
            "ERB-rate bands aggregate spectral power and are not an auditory-filter model.",
            "No loudness, masking, descriptor, or translation estimate is produced.",
        ]
    )

    def __post_init__(self) -> None:
        _require_identifier(self.schema_version, "schema_version")
        _require_positive_integer(self.source_sample_rate_hz, "source_sample_rate_hz")
        _require_positive_integer(self.source_sample_count, "source_sample_count")
        _require_positive_integer(self.channel_count, "channel_count")
        _require_non_negative(self.duration_seconds, "duration_seconds")
        _require_positive_integer(self.frame_count, "frame_count")
        _require_positive_integer(self.linear_frequency_bin_count, "linear_frequency_bin_count")
        if not self.auditory_bands:
            raise ValueError("auditory_bands must not be empty")
        for index, band in enumerate(self.auditory_bands):
            if band.band_index != index:
                raise ValueError("auditory_bands must use consecutive zero-based indexes")
            if index and (
                self.auditory_bands[index - 1].frequency_range.upper_hz
                != band.frequency_range.lower_hz
            ):
                raise ValueError("auditory_bands must have contiguous boundaries")
        _require_non_negative(self.input_peak_absolute, "input_peak_absolute")
        _require_identifier(self.level_reference, "level_reference")
        if type(self.nominal_full_scale_exceeded) is not bool:
            raise TypeError("nominal_full_scale_exceeded must be a bool")
        if type(self.spl_calibrated) is not bool:
            raise TypeError("spl_calibrated must be a bool")
        if type(self.arrays_serialized) is not bool:
            raise TypeError("arrays_serialized must be a bool")
        if self.spl_calibrated:
            raise ValueError("method version 1.0.0 does not accept SPL calibration")
        if self.arrays_serialized:
            raise ValueError("runtime frame matrices are not part of the transport summary")
