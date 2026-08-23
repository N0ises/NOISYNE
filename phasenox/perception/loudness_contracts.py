from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from ._serialization import JsonContract
from .common import (
    _require_finite_number,
    _require_identifier,
    _require_non_negative_integer,
)

LOUDNESS_FOUNDATION_METHOD_ID = "noisyne.calibrated_loudness_foundation"
LOUDNESS_FOUNDATION_METHOD_VERSION = "1.1.0"


class AcousticPresentation(str, Enum):
    """Declared measurement path for calibrated pressure supplied to a future model."""

    FREE_FIELD_SINGLE_MICROPHONE = "free_field_single_microphone"
    DIFFUSE_FIELD_SINGLE_MICROPHONE = "diffuse_field_single_microphone"
    EARDRUM_PRESSURE = "eardrum_pressure"


@dataclass(frozen=True, slots=True)
class FrequencyResponseCompensation(JsonContract):
    """Identity and traceability for compensation already applied upstream."""

    method_reference: str
    version: str
    traceability: str

    def __post_init__(self) -> None:
        _require_identifier(self.method_reference, "method_reference")
        _require_identifier(self.version, "version")
        _require_identifier(self.traceability, "traceability")


@dataclass(frozen=True, slots=True)
class LoudnessCalibration(JsonContract):
    """Auditable linear mapping from digital samples to pressure in pascals."""

    calibration_id: str
    version: str
    pascals_per_sample: float
    presentation: AcousticPresentation
    left_channel_index: int
    right_channel_index: int
    frequency_response_compensated: bool
    traceability: str
    frequency_response_compensation: FrequencyResponseCompensation | None = None
    input_quantity: str = "digital_sample_amplitude"
    output_quantity: str = "sound_pressure_pa"

    def __post_init__(self) -> None:
        _require_identifier(self.calibration_id, "calibration_id")
        _require_identifier(self.version, "version")
        _require_finite_number(self.pascals_per_sample, "pascals_per_sample")
        if self.pascals_per_sample <= 0.0:
            raise ValueError("pascals_per_sample must be positive")
        _require_non_negative_integer(self.left_channel_index, "left_channel_index")
        _require_non_negative_integer(self.right_channel_index, "right_channel_index")
        if type(self.frequency_response_compensated) is not bool:
            raise TypeError("frequency_response_compensated must be a bool")
        _require_identifier(self.traceability, "traceability")
        if self.frequency_response_compensated:
            if self.frequency_response_compensation is None:
                raise ValueError(
                    "frequency_response_compensation is required when "
                    "frequency_response_compensated is true"
                )
            if not isinstance(self.frequency_response_compensation, FrequencyResponseCompensation):
                raise TypeError(
                    "frequency_response_compensation must be a " "FrequencyResponseCompensation"
                )
        elif self.frequency_response_compensation is not None:
            raise ValueError(
                "frequency_response_compensation must be omitted when "
                "frequency_response_compensated is false"
            )
        if self.input_quantity != "digital_sample_amplitude":
            raise ValueError("input_quantity must be digital_sample_amplitude")
        if self.output_quantity != "sound_pressure_pa":
            raise ValueError("output_quantity must be sound_pressure_pa")

        single_microphone = self.presentation in (
            AcousticPresentation.FREE_FIELD_SINGLE_MICROPHONE,
            AcousticPresentation.DIFFUSE_FIELD_SINGLE_MICROPHONE,
        )
        if single_microphone and self.left_channel_index != self.right_channel_index:
            raise ValueError("single-microphone presentation must map one channel diotically")
        if (
            self.presentation is AcousticPresentation.EARDRUM_PRESSURE
            and self.left_channel_index == self.right_channel_index
        ):
            raise ValueError("eardrum-pressure presentation requires distinct left/right channels")
