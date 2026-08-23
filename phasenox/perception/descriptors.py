from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from phasenox.audio.io.models import AudioData

from .auditory import AuditoryFrontend, AuditoryFrontendResult
from .auditory_contracts import AuditoryFrontendConfig, AuditoryFrontendSummary
from .common import (
    Confidence,
    ConfidenceBasis,
    EvidenceSource,
    FrequencyRange,
    Measurement,
    MethodMetadata,
    PerceptualEvidence,
    ResultState,
    ResultStatus,
    ScalarValue,
    UnitBasis,
)
from .descriptor_contracts import (
    BRIGHTNESS_CORRELATE_METHOD_ID,
    BRIGHTNESS_CORRELATE_METHOD_VERSION,
    DescriptorImplementationState,
    descriptor_taxonomy,
)
from .results import PerceptualDescriptorResult

FloatArray = NDArray[np.float64]
BoolArray = NDArray[np.bool_]

_BRIGHTNESS_LIMITATIONS = [
    "Spectral centroid is a correlate of timbral brightness, not a universal perceptual scale.",
    "Fundamental frequency, attack/time behavior, stimulus set, and listening context can alter brightness judgments.",
    "Values depend on source bandwidth, sample rate, FFT/window settings, and zero-padded boundary frames.",
    "A full-mix result cannot attribute brightness to an instrument or source.",
    "No SPL calibration, equal-loudness correction, or auditory-model transformation is applied.",
]


@dataclass(frozen=True, slots=True)
class PerceptualDescriptorFoundationResult:
    """Transport descriptors plus finite, read-only brightness runtime evidence."""

    descriptors: tuple[PerceptualDescriptorResult, ...]
    auditory_frontend_summary: AuditoryFrontendSummary
    frame_times_seconds: FloatArray
    channel_frame_centroid_hz: FloatArray
    channel_frame_centroid_defined: BoolArray
    channel_programme_centroid_hz: FloatArray
    channel_programme_centroid_defined: BoolArray

    def __post_init__(self) -> None:
        channels = self.auditory_frontend_summary.channel_count
        frames = self.auditory_frontend_summary.frame_count
        expected_descriptor_ids = tuple(
            definition.descriptor_id for definition in descriptor_taxonomy()
        )
        actual_descriptor_ids = tuple(descriptor.descriptor_id for descriptor in self.descriptors)
        if actual_descriptor_ids != expected_descriptor_ids:
            raise ValueError(
                "descriptors must match the complete Sprint 5 taxonomy in stable order"
            )
        _validate_runtime_array(
            self.frame_times_seconds,
            "frame_times_seconds",
            shape=(frames,),
            dtype=np.dtype(np.float64),
            require_finite=True,
        )
        _validate_runtime_array(
            self.channel_frame_centroid_hz,
            "channel_frame_centroid_hz",
            shape=(channels, frames),
            dtype=np.dtype(np.float64),
            require_finite=True,
        )
        _validate_runtime_array(
            self.channel_frame_centroid_defined,
            "channel_frame_centroid_defined",
            shape=(channels, frames),
            dtype=np.dtype(np.bool_),
            require_finite=False,
        )
        _validate_runtime_array(
            self.channel_programme_centroid_hz,
            "channel_programme_centroid_hz",
            shape=(channels,),
            dtype=np.dtype(np.float64),
            require_finite=True,
        )
        _validate_runtime_array(
            self.channel_programme_centroid_defined,
            "channel_programme_centroid_defined",
            shape=(channels,),
            dtype=np.dtype(np.bool_),
            require_finite=False,
        )


def _validate_runtime_array(
    array: np.ndarray,
    name: str,
    *,
    shape: tuple[int, ...],
    dtype: np.dtype,
    require_finite: bool,
) -> None:
    if not isinstance(array, np.ndarray):
        raise TypeError(f"{name} must be a NumPy array")
    if array.shape != shape:
        raise ValueError(f"{name} shape does not match frontend summary")
    if array.dtype != dtype:
        raise ValueError(f"{name} must use {dtype} dtype")
    if require_finite and not np.all(np.isfinite(array)):
        raise ValueError(f"{name} must contain only finite values")
    if array.flags.writeable:
        raise ValueError(f"{name} must be read-only")


class PerceptualDescriptorFoundation:
    """Truthful Sprint 5 taxonomy with one signal-level brightness correlate."""

    def __init__(self, frontend_config: AuditoryFrontendConfig | None = None) -> None:
        self._frontend = AuditoryFrontend(frontend_config)

    def analyze(self, audio: AudioData) -> PerceptualDescriptorFoundationResult:
        frontend = self._frontend.analyze(audio)
        (
            frame_centroids,
            frame_defined,
            channel_centroids,
            channel_defined,
            programme_centroid,
            programme_defined,
        ) = _power_spectral_centroids(frontend)

        brightness = _brightness_result(
            frontend,
            programme_centroid=programme_centroid,
            programme_defined=programme_defined,
        )
        descriptors = tuple(
            (
                brightness
                if definition.descriptor_id == "brightness"
                else _unavailable_result(definition)
            )
            for definition in descriptor_taxonomy()
        )
        arrays = (frame_centroids, frame_defined, channel_centroids, channel_defined)
        for array in arrays:
            array.setflags(write=False)
        return PerceptualDescriptorFoundationResult(
            descriptors=descriptors,
            auditory_frontend_summary=frontend.summary,
            frame_times_seconds=frontend.frame_times_seconds,
            channel_frame_centroid_hz=frame_centroids,
            channel_frame_centroid_defined=frame_defined,
            channel_programme_centroid_hz=channel_centroids,
            channel_programme_centroid_defined=channel_defined,
        )


def _power_spectral_centroids(
    frontend: AuditoryFrontendResult,
) -> tuple[FloatArray, BoolArray, FloatArray, BoolArray, float, bool]:
    """Centroids over the exact one-sided Sprint 2 power spectrum, including DC/Nyquist."""

    power = frontend.channel_power_spectra
    frequencies = frontend.linear_frequencies_hz
    try:
        with np.errstate(over="raise", invalid="raise", divide="raise", under="ignore"):
            frame_power = np.sum(power, axis=-1)
            frame_moment = np.einsum("cfk,k->cf", power, frequencies, optimize=True)
            frame_defined = frame_power > 0.0
            frame_centroids = np.zeros_like(frame_power)
            frame_centroids[frame_defined] = (
                frame_moment[frame_defined] / frame_power[frame_defined]
            )

            channel_power = np.sum(frame_power, axis=-1)
            channel_moment = np.sum(frame_moment, axis=-1)
            channel_defined = channel_power > 0.0
            channel_centroids = np.zeros_like(channel_power)
            channel_centroids[channel_defined] = (
                channel_moment[channel_defined] / channel_power[channel_defined]
            )

            total_power = float(np.sum(channel_power))
            total_moment = float(np.sum(channel_moment))
            programme_defined = total_power > 0.0
            programme_centroid = total_moment / total_power if programme_defined else 0.0
    except FloatingPointError as exc:
        raise ValueError("brightness centroid calculation overflowed") from exc

    for values in (frame_centroids, channel_centroids):
        if not np.all(np.isfinite(values)):
            raise ValueError("brightness centroid calculation produced non-finite values")
    return (
        frame_centroids,
        frame_defined,
        channel_centroids,
        channel_defined,
        programme_centroid,
        programme_defined,
    )


def _brightness_result(
    frontend: AuditoryFrontendResult,
    *,
    programme_centroid: float,
    programme_defined: bool,
) -> PerceptualDescriptorResult:
    method = MethodMetadata(
        method_id=BRIGHTNESS_CORRELATE_METHOD_ID,
        version=BRIGHTNESS_CORRELATE_METHOD_VERSION,
        description=(
            "Energy-combined, time-energy-weighted linear-frequency centroid of Sprint 2 "
            "one-sided window-power spectra; a timbral-brightness correlate only."
        ),
    )
    frequency_range = FrequencyRange(
        lower_hz=0.0,
        upper_hz=frontend.summary.source_sample_rate_hz / 2.0,
    )
    if programme_defined:
        estimate = ScalarValue(
            value=programme_centroid,
            unit_basis=UnitBasis.DECLARED_UNIT,
            unit="Hz",
        )
        state = ResultState(status=ResultStatus.COMPUTED)
        measurement = Measurement(
            measurement_id="brightness_power_spectral_centroid_hz",
            name="Timbral brightness power-spectral-centroid correlate",
            value=estimate,
            source="Sprint 2 channel-preserving one-sided window-power spectra",
            method=method,
            time_range=frontend.summary.source_time_range,
            frequency_range=frequency_range,
            note=(
                "DC and Nyquist are included. Channel and time contributions are combined by "
                "spectral power, without waveform downmixing or arithmetic channel averaging."
            ),
        )
        evidence = [
            PerceptualEvidence(
                evidence_id="brightness_centroid_measurement",
                source=EvidenceSource.MEASUREMENT,
                measurement=measurement,
                method=method,
                frequency_range=frequency_range,
            ),
            PerceptualEvidence(
                evidence_id="brightness_timbre_research_basis",
                source=EvidenceSource.REFERENCE,
                reference="Saitis and Siedenburg 2020, DOI 10.1121/10.0002275",
                method=method,
                note=(
                    "Spectral centroid is a robust acoustical correlate of timbral brightness, "
                    "with documented attack-time and context interactions."
                ),
            ),
        ]
    else:
        estimate = None
        state = ResultState(
            status=ResultStatus.INSUFFICIENT_EVIDENCE,
            reason="Brightness spectral centroid is undefined because analyzed spectral power is zero.",
        )
        evidence = [
            PerceptualEvidence(
                evidence_id="brightness_zero_energy_observation",
                source=EvidenceSource.MEASUREMENT,
                measurement=Measurement(
                    measurement_id="brightness_analyzed_spectral_power_present",
                    name="Positive analyzed spectral power present",
                    value=ScalarValue(
                        value=False,
                        unit_basis=UnitBasis.UNDEFINED,
                    ),
                    source="Sprint 2 channel-preserving one-sided window-power spectra",
                    method=method,
                    frequency_range=frequency_range,
                ),
                method=method,
            )
        ]
    return PerceptualDescriptorResult(
        descriptor_id="brightness",
        display_name="Timbral brightness spectral-centroid correlate",
        state=state,
        estimate=estimate,
        evidence=evidence,
        confidence=Confidence(
            score=None,
            basis=ConfidenceBasis.MEASUREMENT_QUALITY,
            reason=(
                "The spectral measurement is deterministic; no universal perceptual brightness "
                "confidence score is claimed."
            ),
            limitations=list(_BRIGHTNESS_LIMITATIONS),
        ),
        time_range=frontend.summary.source_time_range,
        frequency_range=frequency_range,
        method=method,
        limitations=list(_BRIGHTNESS_LIMITATIONS),
    )


def _unavailable_result(definition) -> PerceptualDescriptorResult:
    if definition.implementation_state is DescriptorImplementationState.IMPLEMENTED:
        raise ValueError("implemented taxonomy entries require an executable descriptor result")
    blockers = "; ".join(definition.limitations)
    return PerceptualDescriptorResult(
        descriptor_id=definition.descriptor_id,
        display_name=definition.descriptor_id.replace("_", " ").title(),
        state=ResultState(status=ResultStatus.UNAVAILABLE, reason=blockers),
        estimate=None,
        evidence=[
            PerceptualEvidence(
                evidence_id=f"{definition.descriptor_id}_taxonomy_reference",
                source=EvidenceSource.REFERENCE,
                reference="; ".join(definition.authoritative_references),
                note="Taxonomy/reference evidence only; no numerical descriptor was computed.",
            )
        ],
        confidence=Confidence(
            score=None,
            basis=ConfidenceBasis.UNKNOWN,
            reason="No validated executable model is available for this descriptor.",
            limitations=list(definition.limitations),
        ),
        limitations=list(definition.limitations) + list(definition.prohibited_claims),
    )


__all__ = ["PerceptualDescriptorFoundation", "PerceptualDescriptorFoundationResult"]
