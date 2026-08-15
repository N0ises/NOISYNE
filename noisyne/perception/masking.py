from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from noisyne.audio.io.models import AudioData

from .auditory import AuditoryFrontend, AuditoryFrontendResult
from .auditory_contracts import AuditoryFrontendConfig, AuditoryFrontendSummary
from .common import (
    AuditoryBand,
    Confidence,
    ConfidenceBasis,
    EvidenceSource,
    MethodMetadata,
    PerceptualEvidence,
    ResultState,
    ResultStatus,
)
from .masking_contracts import (
    SIMULTANEOUS_MASKING_METHOD_ID,
    SIMULTANEOUS_MASKING_METHOD_VERSION,
    RelativeMaskingPairContext,
)
from .results import FrequencyMaskingResult

FloatArray = NDArray[np.float64]
BoolArray = NDArray[np.bool_]

_FILTER_MINIMUM_HZ = 100.0
_FILTER_MAXIMUM_HZ = 6500.0
_MOORE_GLASBERG_1983_DOI = "https://doi.org/10.1121/1.389861"

_PAIR_ASSUMPTIONS = [
    "The caller declares exact sample alignment and a known common digital gain relationship.",
    "Channels are matched by index and analyzed independently without downmixing.",
    (
        "The fixed Moore-Glasberg 1983 moderate-level roex(p) filter is a reference weighting, "
        "not a claim about the actual listener or playback level."
    ),
]
_PAIR_LIMITATIONS = [
    "Relative excitation margin is not an absolute masking threshold or audibility prediction.",
    (
        "No outer/middle-ear transform, absolute threshold, level-dependent filter, or temporal "
        "masking is implemented."
    ),
    (
        "No MaskingEvent is emitted because validated event extraction and a perceptual decision "
        "criterion are unavailable."
    ),
    "The fixed filter reference applies only to center frequencies from 100 Hz to 6.5 kHz.",
    (
        "Comodulation masking release, informational masking, binaural interaction, and listener "
        "variation are not represented."
    ),
]


def moore_glasberg_1983_erb_hz(center_frequency_hz: float | FloatArray) -> float | FloatArray:
    """Return the 1983 auditory-filter ERB for centers within 100 Hz to 6.5 kHz."""
    center = np.asarray(center_frequency_hz, dtype=np.float64)
    if np.any(~np.isfinite(center)) or np.any(
        (center < _FILTER_MINIMUM_HZ) | (center > _FILTER_MAXIMUM_HZ)
    ):
        raise ValueError("center_frequency_hz must be finite and within [100, 6500]")
    center_khz = center / 1000.0
    erb = 6.23 * np.square(center_khz) + 93.39 * center_khz + 28.52
    return float(erb) if center.ndim == 0 else erb


def moore_glasberg_1983_roex_p_weights(
    frequencies_hz: FloatArray, center_frequency_hz: float
) -> FloatArray:
    """Return the fixed moderate-level roex(p) power weighting from Moore-Glasberg 1983."""
    frequencies = np.asarray(frequencies_hz, dtype=np.float64)
    if frequencies.ndim != 1:
        raise ValueError("frequencies_hz must be one-dimensional")
    if np.any(~np.isfinite(frequencies)) or np.any(frequencies < 0.0):
        raise ValueError("frequencies_hz must contain finite non-negative values")
    center = float(center_frequency_hz)
    erb_hz = float(moore_glasberg_1983_erb_hz(center))
    p = 4.0 * center / erb_hz
    g = np.abs(frequencies - center) / center
    pg = p * g
    weights = (1.0 + pg) * np.exp(-pg)
    if not np.all(np.isfinite(weights)):
        raise ValueError("auditory-filter weighting produced non-finite values")
    weights.setflags(write=False)
    return weights


@dataclass(frozen=True, slots=True)
class RelativeMaskingFoundationResult:
    """Runtime-only pairwise excitation evidence; large matrices are not serialized."""

    frequency_masking: FrequencyMaskingResult
    context: RelativeMaskingPairContext
    masker_summary: AuditoryFrontendSummary
    target_summary: AuditoryFrontendSummary
    auditory_bands: tuple[AuditoryBand, ...]
    frame_times_seconds: FloatArray
    masker_excitation_power: FloatArray
    target_excitation_power: FloatArray
    relative_excitation_margin_db: FloatArray
    margin_defined: BoolArray

    def __post_init__(self) -> None:
        channels = self.masker_summary.channel_count
        frames = self.masker_summary.frame_count
        filters = len(self.auditory_bands)
        if self.target_summary.channel_count != channels:
            raise ValueError("target summary channel count does not match masker summary")
        if self.target_summary.frame_count != frames:
            raise ValueError("target summary frame count does not match masker summary")
        if self.frame_times_seconds.shape != (frames,):
            raise ValueError("frame_times_seconds shape does not match summaries")
        expected = (channels, frames, filters)
        matrices = (
            (self.masker_excitation_power, "masker_excitation_power"),
            (self.target_excitation_power, "target_excitation_power"),
            (self.relative_excitation_margin_db, "relative_excitation_margin_db"),
        )
        for matrix, name in matrices:
            if matrix.shape != expected:
                raise ValueError(f"{name} shape must be {expected}")
            if not np.all(np.isfinite(matrix)):
                raise ValueError(f"{name} must contain only finite values")
            if matrix.flags.writeable:
                raise ValueError(f"{name} must be read-only")
        if self.margin_defined.shape != expected or self.margin_defined.dtype != np.bool_:
            raise ValueError("margin_defined must be a boolean matrix matching excitation shape")
        if self.margin_defined.flags.writeable:
            raise ValueError("margin_defined must be read-only")
        if self.frame_times_seconds.flags.writeable:
            raise ValueError("frame_times_seconds must be read-only")


class SimultaneousMaskingFoundation:
    """Prepare honest simultaneous-masking evidence without inventing thresholds or events."""

    def __init__(self, frontend_config: AuditoryFrontendConfig | None = None) -> None:
        self._frontend = AuditoryFrontend(frontend_config)

    def analyze(self, audio: AudioData) -> FrequencyMaskingResult:
        """Validate one full mix and explain why ordered masking is unavailable."""
        self._frontend.analyze(audio)
        method = _method_metadata()
        reason = (
            "A single summed mix does not identify separate masker and target signals; ordered "
            "simultaneous masking evidence cannot be computed without source decomposition."
        )
        return FrequencyMaskingResult(
            state=ResultState(status=ResultStatus.INSUFFICIENT_EVIDENCE, reason=reason),
            evidence=[
                PerceptualEvidence(
                    evidence_id="full_mix_source_decomposition_unavailable",
                    source=EvidenceSource.CONTEXT,
                    origin=SIMULTANEOUS_MASKING_METHOD_ID,
                    note=reason,
                )
            ],
            confidence=Confidence(
                score=None,
                basis=ConfidenceBasis.UNKNOWN,
                reason="No evidence identifies an ordered masker and target inside the mix.",
            ),
            method=method,
            limitations=[
                (
                    "No source attribution, hidden-component audibility, or ordered masking event "
                    "is inferred from a full mix."
                )
            ],
        )

    def analyze_pair(
        self,
        masker: AudioData,
        target: AudioData,
        *,
        context: RelativeMaskingPairContext,
    ) -> RelativeMaskingFoundationResult:
        """Compare explicitly aligned sources using a common uncalibrated digital gain basis."""
        if not isinstance(context, RelativeMaskingPairContext):
            raise TypeError("context must be a RelativeMaskingPairContext")
        masker_frontend = self._frontend.analyze(masker)
        target_frontend = self._frontend.analyze(target)
        _validate_pair_compatibility(masker_frontend, target_frontend)

        bands = tuple(
            band
            for band in masker_frontend.summary.auditory_bands
            if band.center_hz is not None
            and _FILTER_MINIMUM_HZ <= band.center_hz <= _FILTER_MAXIMUM_HZ
        )
        frequencies = masker_frontend.linear_frequencies_hz
        if bands:
            weights = np.stack(
                [moore_glasberg_1983_roex_p_weights(frequencies, band.center_hz) for band in bands]
            )
            try:
                with np.errstate(over="raise", invalid="raise"):
                    masker_excitation = np.einsum(
                        "cfb,kb->cfk",
                        masker_frontend.channel_power_spectra,
                        weights,
                        optimize=True,
                    )
                    target_excitation = np.einsum(
                        "cfb,kb->cfk",
                        target_frontend.channel_power_spectra,
                        weights,
                        optimize=True,
                    )
            except FloatingPointError as exc:
                raise ValueError("relative excitation calculation overflowed") from exc
        else:
            shape = (
                masker_frontend.summary.channel_count,
                masker_frontend.summary.frame_count,
                0,
            )
            masker_excitation = np.empty(shape, dtype=np.float64)
            target_excitation = np.empty(shape, dtype=np.float64)

        if not np.all(np.isfinite(masker_excitation)) or not np.all(np.isfinite(target_excitation)):
            raise ValueError("relative excitation calculation produced non-finite values")
        margin_defined = (masker_excitation > 0.0) & (target_excitation > 0.0)
        margin_db = np.zeros_like(masker_excitation)
        try:
            with np.errstate(over="raise", invalid="raise", divide="raise"):
                margin_db[margin_defined] = 10.0 * (
                    np.log10(masker_excitation[margin_defined])
                    - np.log10(target_excitation[margin_defined])
                )
        except FloatingPointError as exc:
            raise ValueError("relative excitation margin calculation overflowed") from exc
        if not np.all(np.isfinite(margin_db)):
            raise ValueError("relative excitation margin produced non-finite values")

        method = _method_metadata()
        if not bands:
            state = ResultState(
                status=ResultStatus.INSUFFICIENT_EVIDENCE,
                reason="No auditory-filter center lies within the supported 100 Hz to 6.5 kHz domain.",
            )
        elif not np.any(margin_defined):
            state = ResultState(
                status=ResultStatus.INSUFFICIENT_EVIDENCE,
                reason=(
                    "Relative excitation margin is undefined because masker and target do not "
                    "both have positive excitation in any analyzed cell."
                ),
            )
        else:
            state = ResultState(status=ResultStatus.COMPUTED)

        result = FrequencyMaskingResult(
            state=state,
            events=[],
            evidence=_pair_evidence(context, method),
            confidence=Confidence(
                score=None,
                basis=ConfidenceBasis.MEASUREMENT_QUALITY,
                reason=(
                    "The relative excitation calculation is deterministic, but no validated "
                    "perceptual decision threshold is available."
                ),
                limitations=list(_PAIR_LIMITATIONS),
            ),
            method=method,
            assumptions=list(_PAIR_ASSUMPTIONS),
            limitations=list(_PAIR_LIMITATIONS),
        )
        arrays = (
            masker_excitation,
            target_excitation,
            margin_db,
            margin_defined,
        )
        for array in arrays:
            array.setflags(write=False)
        return RelativeMaskingFoundationResult(
            frequency_masking=result,
            context=context,
            masker_summary=masker_frontend.summary,
            target_summary=target_frontend.summary,
            auditory_bands=bands,
            frame_times_seconds=masker_frontend.frame_times_seconds,
            masker_excitation_power=masker_excitation,
            target_excitation_power=target_excitation,
            relative_excitation_margin_db=margin_db,
            margin_defined=margin_defined,
        )


def _validate_pair_compatibility(
    masker: AuditoryFrontendResult, target: AuditoryFrontendResult
) -> None:
    masker_summary = masker.summary
    target_summary = target.summary
    if masker_summary.source_sample_rate_hz != target_summary.source_sample_rate_hz:
        raise ValueError("masker and target sample rates must match; no resampling is performed")
    if masker_summary.source_sample_count != target_summary.source_sample_count:
        raise ValueError("masker and target sample counts must match; no realignment is performed")
    if masker_summary.channel_count != target_summary.channel_count:
        raise ValueError("masker and target channel counts must match")
    if masker_summary.config != target_summary.config:
        raise ValueError("masker and target auditory frontend configurations must match")


def _method_metadata() -> MethodMetadata:
    return MethodMetadata(
        method_id=SIMULTANEOUS_MASKING_METHOD_ID,
        version=SIMULTANEOUS_MASKING_METHOD_VERSION,
        description=(
            "Pairwise common-gain relative excitation margin using the fixed moderate-level "
            "Moore-Glasberg 1983 roex(p) reference; not an absolute masking threshold."
        ),
    )


def _pair_evidence(
    context: RelativeMaskingPairContext, method: MethodMetadata
) -> list[PerceptualEvidence]:
    identities = [
        identity
        for identity in (context.masker_source_id, context.target_source_id)
        if identity is not None
    ]
    origin = " -> ".join(identities) if identities else None
    return [
        PerceptualEvidence(
            evidence_id="moore_glasberg_1983_fixed_roex_reference",
            source=EvidenceSource.REFERENCE,
            origin=origin,
            reference=_MOORE_GLASBERG_1983_DOI,
            method=method,
            note=(
                "Equation-derived moderate-level auditory-filter weighting; used only for "
                "relative excitation evidence."
            ),
        ),
        PerceptualEvidence(
            evidence_id="pair_alignment_and_gain_declaration",
            source=EvidenceSource.CONTEXT,
            origin=context.gain_relationship_reference,
            note=(
                f"Alignment reference: {context.alignment_reference}. No normalization, "
                "resampling, or realignment was performed."
            ),
        ),
    ]
