from __future__ import annotations

from dataclasses import dataclass
from math import isfinite

import numpy as np
from numpy.typing import NDArray

from noisyne.audio.analysis.lufs import LUFSAnalyzer
from noisyne.audio.io.models import AudioData

from .auditory import _validated_samples
from .common import (
    Confidence,
    ConfidenceBasis,
    EvidenceSource,
    Measurement,
    MethodMetadata,
    PerceptualEvidence,
    ResultState,
    ResultStatus,
    ScalarValue,
    UnitBasis,
)
from .loudness_contracts import (
    LOUDNESS_FOUNDATION_METHOD_ID,
    LOUDNESS_FOUNDATION_METHOD_VERSION,
    LoudnessCalibration,
)
from .results import PerceivedLoudnessResult

FloatArray = NDArray[np.float64]

_ABSOLUTE_MODEL_UNAVAILABLE = (
    "ISO 532-3:2023 algorithm, companion source code, and verification fixtures are not "
    "available in this development environment; calibrated pressure alone is insufficient "
    "to produce sones or phons."
)
_CALIBRATION_REQUIRED = (
    "Absolute perceived loudness requires explicit digital-to-acoustic calibration and "
    "presentation semantics."
)


@dataclass(frozen=True, slots=True)
class LoudnessFoundationResult:
    """Runtime result for calibration/evidence preparation, not a loudness calculation."""

    perceived_loudness: PerceivedLoudnessResult
    calibration: LoudnessCalibration | None = None
    pressure_by_ear_pa: FloatArray | None = None

    def __post_init__(self) -> None:
        if self.pressure_by_ear_pa is None:
            return
        if self.calibration is None:
            raise ValueError("pressure_by_ear_pa requires calibration")
        if self.pressure_by_ear_pa.ndim != 2 or self.pressure_by_ear_pa.shape[1] != 2:
            raise ValueError("pressure_by_ear_pa must have shape (frames, 2)")
        if not np.all(np.isfinite(self.pressure_by_ear_pa)):
            raise ValueError("pressure_by_ear_pa must contain only finite values")
        if self.pressure_by_ear_pa.flags.writeable:
            raise ValueError("pressure_by_ear_pa must be read-only")


class PerceivedLoudnessFoundation:
    """Prepare calibrated pressure and honest evidence without inventing loudness."""

    def analyze(
        self,
        audio: AudioData,
        *,
        calibration: LoudnessCalibration | None = None,
        include_programme_loudness: bool = True,
    ) -> LoudnessFoundationResult:
        if type(include_programme_loudness) is not bool:
            raise TypeError("include_programme_loudness must be a bool")
        samples, _sample_rate = _validated_samples(audio)
        programme_loudness = (
            _programme_loudness_measurement(audio) if include_programme_loudness else None
        )
        method = MethodMetadata(
            method_id=LOUDNESS_FOUNDATION_METHOD_ID,
            version=LOUDNESS_FOUNDATION_METHOD_VERSION,
            description=(
                "Calibration and evidence foundation only; no psychoacoustic loudness "
                "algorithm is implemented."
            ),
        )

        if calibration is None:
            reason = _CALIBRATION_REQUIRED
            evidence = [
                PerceptualEvidence(
                    evidence_id="absolute_loudness_calibration_missing",
                    source=EvidenceSource.CONTEXT,
                    origin=LOUDNESS_FOUNDATION_METHOD_ID,
                    note="No digital-to-acoustic calibration or presentation mapping was supplied.",
                )
            ]
            pressure_by_ear_pa = None
        elif not calibration.frequency_response_compensated:
            reason = (
                "Calibration does not declare frequency-response compensation; calibrated "
                "pressure input is insufficient for a standard-oriented loudness method."
            )
            evidence = [
                PerceptualEvidence(
                    evidence_id="acoustic_calibration_incomplete",
                    source=EvidenceSource.CONTEXT,
                    origin=calibration.calibration_id,
                    note=reason,
                )
            ]
            pressure_by_ear_pa = None
        else:
            pressure_by_ear_pa = _calibrated_pressure(samples, calibration)
            reason = _ABSOLUTE_MODEL_UNAVAILABLE
            evidence = _pressure_evidence(pressure_by_ear_pa, method, calibration)

        limitations = [
            "No sone or phon estimate is produced.",
            "No ISO 532-3 conformance is claimed.",
            "Programme LUFS is objective supporting evidence, not psychoacoustic loudness.",
            "Ordinary stereo channels are not treated as ear signals without explicit mapping.",
        ]
        result = PerceivedLoudnessResult(
            state=ResultState(status=ResultStatus.INSUFFICIENT_EVIDENCE, reason=reason),
            estimate=None,
            programme_loudness_measurement=programme_loudness,
            evidence=evidence,
            confidence=Confidence(
                score=None,
                basis=ConfidenceBasis.UNKNOWN,
                reason="Absolute psychoacoustic loudness was not computed.",
                limitations=list(limitations),
            ),
            method=method,
            limitations=limitations,
        )
        return LoudnessFoundationResult(
            perceived_loudness=result,
            calibration=calibration,
            pressure_by_ear_pa=pressure_by_ear_pa,
        )


def _calibrated_pressure(samples: FloatArray, calibration: LoudnessCalibration) -> FloatArray:
    channel_count = samples.shape[1]
    indexes = (calibration.left_channel_index, calibration.right_channel_index)
    if any(index >= channel_count for index in indexes):
        raise ValueError("calibration channel mapping exceeds the audio channel count")
    try:
        with np.errstate(over="raise", invalid="raise"):
            pressure = samples[:, indexes] * calibration.pascals_per_sample
    except FloatingPointError as exc:
        raise ValueError("calibrated pressure conversion overflowed") from exc
    if not np.all(np.isfinite(pressure)):
        raise ValueError("calibrated pressure conversion produced non-finite values")
    pressure.setflags(write=False)
    return pressure


def _pressure_evidence(
    pressure_by_ear_pa: FloatArray,
    method: MethodMetadata,
    calibration: LoudnessCalibration,
) -> list[PerceptualEvidence]:
    evidence = []
    for channel, side in enumerate(("left", "right")):
        rms_pressure = _stable_rms(pressure_by_ear_pa[:, channel])
        measurement = Measurement(
            measurement_id=f"calibrated_{side}_rms_pressure_pa",
            name=f"Calibrated {side} RMS pressure",
            value=ScalarValue(
                value=rms_pressure,
                unit_basis=UnitBasis.DECLARED_UNIT,
                unit="Pa",
            ),
            source=calibration.calibration_id,
            method=method,
            note=(
                "Linear calibrated pressure evidence only; not dB SPL, sone, phon, or "
                "psychoacoustic loudness."
            ),
        )
        evidence.append(
            PerceptualEvidence(
                evidence_id=f"calibrated_{side}_pressure_evidence",
                source=EvidenceSource.MEASUREMENT,
                origin=calibration.traceability,
                measurement=measurement,
            )
        )
    return evidence


def _stable_rms(values: FloatArray) -> float:
    scale = float(np.max(np.abs(values)))
    if scale == 0.0:
        return 0.0
    normalized = values / scale
    return float(scale * np.sqrt(np.mean(np.square(normalized))))


def _programme_loudness_measurement(audio: AudioData) -> Measurement | None:
    try:
        loudness = LUFSAnalyzer().analyze(audio)
    except (FloatingPointError, OverflowError, ValueError):
        return None
    if not isfinite(loudness):
        return None
    return Measurement(
        measurement_id="programme_loudness_lufs",
        name="Integrated programme loudness",
        value=ScalarValue(
            value=loudness,
            unit_basis=UnitBasis.DECLARED_UNIT,
            unit="LUFS",
        ),
        source="noisyne.audio.analysis.lufs.LUFSAnalyzer",
        method=MethodMetadata(
            method_id="noisyne.v1.integrated_programme_loudness",
            version="1.0.0",
            description=(
                "Existing pyloudnorm-based programme loudness measurement; not sone, phon, "
                "or perceived loudness."
            ),
        ),
    )
