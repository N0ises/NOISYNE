from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from ._serialization import JsonContract
from .common import (
    FrequencyRange,
    MethodMetadata,
    ScalarValue,
    _require_identifier,
    _require_non_negative,
    _require_positive_integer,
)
from .context import PlaybackProfileReference

PLAYBACK_TRANSFER_METHOD_ID = "noisyne.explicit_linear_playback_transfer"
PLAYBACK_TRANSFER_METHOD_VERSION = "1.0.0"
PLAYBACK_TRANSFER_SCHEMA_VERSION = "1.0.0"


class TransferProvenance(str, Enum):
    """Origin of transfer evidence; category labels are never measurement evidence."""

    MEASURED = "measured"
    REFERENCE_SPECIFICATION = "reference_specification"
    USER_DECLARED = "user_declared"
    ENGINEERING_APPROXIMATION = "engineering_approximation"


class TransferKind(str, Enum):
    MAGNITUDE_RESPONSE = "magnitude_response"
    IMPULSE_RESPONSE = "impulse_response"


class TransferGainBasis(str, Enum):
    """Whether values are relative digital gain or calibrated acoustic evidence."""

    NORMALIZED_RELATIVE_RESPONSE = "normalized_relative_response"
    DIGITAL_AMPLITUDE_RATIO = "digital_amplitude_ratio"
    ABSOLUTE_ACOUSTIC_OUTPUT = "absolute_acoustic_output"


class TransferPhaseBasis(str, Enum):
    MAGNITUDE_ONLY = "magnitude_only"
    IMPULSE_RESPONSE_CONTAINS_PHASE = "impulse_response_contains_phase"


class TransferAcousticScope(str, Enum):
    DEVICE_ONLY = "device_only"
    MEASURED_POINT_RESPONSE = "measured_point_response"
    DEVICE_AND_ROOM = "device_and_room"
    LISTENER_POSITION = "listener_position"
    EAR_SIMULATOR = "ear_simulator"
    HEAD_AND_TORSO_SIMULATOR = "head_and_torso_simulator"
    REAL_EAR = "real_ear"
    REFERENCE_TARGET = "reference_target"
    ENGINEERING_TEST_FIXTURE = "engineering_test_fixture"


class TransferChannelTopology(str, Enum):
    CHANNEL_INDEPENDENT_SHARED = "channel_independent_shared"
    EXPLICIT_PER_CHANNEL = "explicit_per_channel"


class MagnitudeInterpolationPolicy(str, Enum):
    LOG_FREQUENCY_DB = "log_frequency_db"


class ExtrapolationPolicy(str, Enum):
    REJECT = "reject"


class ConvolutionBoundaryPolicy(str, Enum):
    FULL_LINEAR = "full_linear"


@dataclass(frozen=True, slots=True)
class PlaybackTransferProfile(JsonContract):
    """Compact identity and evidence semantics; large transfer arrays remain runtime-only."""

    transfer_id: str
    version: str
    profile_reference: PlaybackProfileReference
    provenance: TransferProvenance
    evidence_source: str
    evidence_version: str
    transfer_kind: TransferKind
    gain_basis: TransferGainBasis
    phase_basis: TransferPhaseBasis
    acoustic_scope: TransferAcousticScope
    channel_topology: TransferChannelTopology
    measurement_conditions: str
    normalization_reference: str
    time_origin_alignment: str
    valid_frequency_range: FrequencyRange | None = None
    sample_rate_hz: int | None = None
    expected_input_channels: int | None = None
    interpolation_policy: MagnitudeInterpolationPolicy | None = None
    extrapolation_policy: ExtrapolationPolicy | None = None
    limitations: list[str] = field(default_factory=list)
    schema_version: str = PLAYBACK_TRANSFER_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if not isinstance(self.profile_reference, PlaybackProfileReference):
            raise TypeError("profile_reference must be a PlaybackProfileReference")
        for field_name, enum_type in (
            ("provenance", TransferProvenance),
            ("transfer_kind", TransferKind),
            ("gain_basis", TransferGainBasis),
            ("phase_basis", TransferPhaseBasis),
            ("acoustic_scope", TransferAcousticScope),
            ("channel_topology", TransferChannelTopology),
        ):
            if not isinstance(getattr(self, field_name), enum_type):
                raise TypeError(f"{field_name} must be a {enum_type.__name__}")
        for field_name in (
            "transfer_id",
            "version",
            "evidence_source",
            "evidence_version",
            "measurement_conditions",
            "normalization_reference",
            "time_origin_alignment",
            "schema_version",
        ):
            _require_identifier(getattr(self, field_name), field_name)
        if not isinstance(self.limitations, list):
            raise TypeError("limitations must be a list")
        for limitation in self.limitations:
            _require_identifier(limitation, "limitations")
        if self.sample_rate_hz is not None:
            _require_positive_integer(self.sample_rate_hz, "sample_rate_hz")
        if self.expected_input_channels is not None:
            _require_positive_integer(self.expected_input_channels, "expected_input_channels")
        if self.channel_topology is TransferChannelTopology.EXPLICIT_PER_CHANNEL:
            if self.expected_input_channels is None:
                raise ValueError("explicit_per_channel topology requires expected_input_channels")
        elif self.expected_input_channels is not None:
            raise ValueError(
                "channel_independent_shared topology must not constrain input channel count"
            )

        if self.transfer_kind is TransferKind.MAGNITUDE_RESPONSE:
            if self.channel_topology is not TransferChannelTopology.CHANNEL_INDEPENDENT_SHARED:
                raise ValueError(
                    "Sprint 6 magnitude evidence is a shared single response only; "
                    "explicit_per_channel is unsupported"
                )
            if self.valid_frequency_range is None:
                raise ValueError("magnitude_response requires valid_frequency_range")
            if not isinstance(self.valid_frequency_range, FrequencyRange):
                raise TypeError("valid_frequency_range must be a FrequencyRange")
            if self.phase_basis is not TransferPhaseBasis.MAGNITUDE_ONLY:
                raise ValueError("magnitude_response supports magnitude_only phase basis")
            if self.interpolation_policy is None or self.extrapolation_policy is None:
                raise ValueError(
                    "magnitude_response requires explicit interpolation and extrapolation policies"
                )
            if not isinstance(self.interpolation_policy, MagnitudeInterpolationPolicy):
                raise TypeError("interpolation_policy must be a MagnitudeInterpolationPolicy")
            if not isinstance(self.extrapolation_policy, ExtrapolationPolicy):
                raise TypeError("extrapolation_policy must be an ExtrapolationPolicy")
            if self.sample_rate_hz is not None:
                raise ValueError("magnitude evidence does not require a processing sample rate")
        else:
            if self.sample_rate_hz is None:
                raise ValueError("impulse_response requires sample_rate_hz")
            if self.phase_basis is not TransferPhaseBasis.IMPULSE_RESPONSE_CONTAINS_PHASE:
                raise ValueError(
                    "impulse_response requires impulse_response_contains_phase phase basis"
                )
            if self.interpolation_policy is not None or self.extrapolation_policy is not None:
                raise ValueError("impulse_response must not declare interpolation policies")
            if self.gain_basis is TransferGainBasis.ABSOLUTE_ACOUSTIC_OUTPUT:
                raise ValueError(
                    "absolute acoustic evidence cannot be used as a digital impulse response"
                )


@dataclass(frozen=True, slots=True)
class MagnitudeResponseSummary(JsonContract):
    profile: PlaybackTransferProfile
    point_count: int
    minimum_frequency_hz: float
    maximum_frequency_hz: float
    arrays_serialized: bool = False

    def __post_init__(self) -> None:
        _require_positive_integer(self.point_count, "point_count")
        _require_non_negative(self.minimum_frequency_hz, "minimum_frequency_hz")
        _require_non_negative(self.maximum_frequency_hz, "maximum_frequency_hz")
        if self.maximum_frequency_hz <= self.minimum_frequency_hz:
            raise ValueError("maximum_frequency_hz must exceed minimum_frequency_hz")
        if self.profile.transfer_kind is not TransferKind.MAGNITUDE_RESPONSE:
            raise ValueError("summary profile must describe magnitude_response")
        if type(self.arrays_serialized) is not bool:
            raise TypeError("arrays_serialized must be a bool")
        if self.arrays_serialized:
            raise ValueError("magnitude response arrays are runtime-only")


@dataclass(frozen=True, slots=True)
class ImpulseResponseSummary(JsonContract):
    profile: PlaybackTransferProfile
    transfer_channel_count: int
    tap_count: int
    boundary_policy: ConvolutionBoundaryPolicy = ConvolutionBoundaryPolicy.FULL_LINEAR
    arrays_serialized: bool = False

    def __post_init__(self) -> None:
        _require_positive_integer(self.transfer_channel_count, "transfer_channel_count")
        _require_positive_integer(self.tap_count, "tap_count")
        if self.profile.transfer_kind is not TransferKind.IMPULSE_RESPONSE:
            raise ValueError("summary profile must describe impulse_response")
        if self.boundary_policy is not ConvolutionBoundaryPolicy.FULL_LINEAR:
            raise ValueError("only full_linear convolution is supported")
        if type(self.arrays_serialized) is not bool:
            raise TypeError("arrays_serialized must be a bool")
        if self.arrays_serialized:
            raise ValueError("impulse response arrays are runtime-only")


@dataclass(frozen=True, slots=True)
class MaximumLinearOutputEvidence(JsonContract):
    """Optional measured/declared headroom evidence; it never creates nonlinear DSP."""

    evidence_id: str
    provenance: TransferProvenance
    source: str
    evidence_version: str
    measurement_method_reference: str
    value: ScalarValue
    measurement_conditions: str
    frequency_range: FrequencyRange | None = None
    measurement_distance_m: float | None = None
    limitations: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not isinstance(self.provenance, TransferProvenance):
            raise TypeError("provenance must be a TransferProvenance")
        if not isinstance(self.value, ScalarValue):
            raise TypeError("value must be a ScalarValue")
        for field_name in (
            "evidence_id",
            "source",
            "evidence_version",
            "measurement_method_reference",
            "measurement_conditions",
        ):
            _require_identifier(getattr(self, field_name), field_name)
        if not isinstance(self.limitations, list):
            raise TypeError("limitations must be a list")
        for limitation in self.limitations:
            _require_identifier(limitation, "limitations")
        if self.frequency_range is not None and not isinstance(
            self.frequency_range, FrequencyRange
        ):
            raise TypeError("frequency_range must be a FrequencyRange")
        if self.measurement_distance_m is not None:
            _require_non_negative(self.measurement_distance_m, "measurement_distance_m")
            if self.measurement_distance_m == 0.0:
                raise ValueError("measurement_distance_m must be positive")


@dataclass(frozen=True, slots=True)
class PlaybackTransferApplicationSummary(JsonContract):
    method: MethodMetadata
    transfer: ImpulseResponseSummary
    input_sample_count: int
    output_sample_count: int
    channel_count: int
    output_peak_absolute: float
    nominal_full_scale_exceeded: bool
    clipping_applied: bool = False
    normalization_applied: bool = False

    def __post_init__(self) -> None:
        if (
            self.method.method_id != PLAYBACK_TRANSFER_METHOD_ID
            or self.method.version != PLAYBACK_TRANSFER_METHOD_VERSION
        ):
            raise ValueError("playback transfer method metadata does not match this implementation")
        _require_positive_integer(self.input_sample_count, "input_sample_count")
        _require_positive_integer(self.output_sample_count, "output_sample_count")
        _require_positive_integer(self.channel_count, "channel_count")
        _require_non_negative(self.output_peak_absolute, "output_peak_absolute")
        if type(self.nominal_full_scale_exceeded) is not bool:
            raise TypeError("nominal_full_scale_exceeded must be a bool")
        if type(self.clipping_applied) is not bool:
            raise TypeError("clipping_applied must be a bool")
        if type(self.normalization_applied) is not bool:
            raise TypeError("normalization_applied must be a bool")
        if self.clipping_applied or self.normalization_applied:
            raise ValueError("method version 1.0.0 never clips or normalizes")


__all__ = [
    "PLAYBACK_TRANSFER_METHOD_ID",
    "PLAYBACK_TRANSFER_METHOD_VERSION",
    "PLAYBACK_TRANSFER_SCHEMA_VERSION",
    "ConvolutionBoundaryPolicy",
    "ExtrapolationPolicy",
    "ImpulseResponseSummary",
    "MagnitudeInterpolationPolicy",
    "MagnitudeResponseSummary",
    "MaximumLinearOutputEvidence",
    "PlaybackTransferApplicationSummary",
    "PlaybackTransferProfile",
    "TransferAcousticScope",
    "TransferChannelTopology",
    "TransferGainBasis",
    "TransferKind",
    "TransferPhaseBasis",
    "TransferProvenance",
]
