from __future__ import annotations

from dataclasses import dataclass, field
from typing import Self

from .validation_contracts import (
    VALIDATION_SCHEMA_VERSION,
    FixtureKind,
    MethodValidationRecord,
    ToleranceKind,
    ValidationCriterion,
    ValidationStatus,
)

# -----------------------------------------------------------------------------
# Sprint 2 — Auditory Frontend
# -----------------------------------------------------------------------------

_SPRINT2_AUDITORY_FRONTEND = MethodValidationRecord(
    capability_id="auditory_frontend",
    method_id="noisyne.auditory_frontend",
    method_version="1.0.0",
    implementation_status=ValidationStatus.IMPLEMENTED,
    validation_status=ValidationStatus.VERIFIED,
    scientific_basis=[
        "Glasberg and Moore (1990) ERB-rate scale",
        "ISO 226:2023 equal-loudness contours (context only; not used for calibration)",
    ],
    validation_fixture=[
        "silence",
        "zero_energy",
        "single_sine",
        "known_amplitude_sine",
        "two_tone",
        "deterministic_erb_energy",
    ],
    tolerance_policy=[
        "exact_identity: frame_count and band_count must match deterministic derivation",
        "floating_point_numerical: 1e-12 relative tolerance for power spectra of pure tones",
        "dsp_implementation: 1e-9 absolute tolerance for ERB band boundaries versus Glasberg-Moore formula",
    ],
    supported_claims=[
        "Deterministic frame/window/FFT/power/ERB aggregation for finite digital audio",
        "Channel-preserving per-channel analysis",
        "ERB-rate bands are contiguous and non-overlapping in this implementation",
    ],
    prohibited_claims=[
        "No sound-pressure-level calibration is performed",
        "ERB-rate bands aggregate spectral power and are not an auditory-filter model",
        "No loudness, masking, descriptor, or translation estimate is produced",
    ],
    known_limitations=[
        "periodic_hann window only",
        "zero_pad_end boundary policy only",
        "one_sided_window_power spectral representation only",
        "erb_rate_glasberg_moore_1990 scale only",
    ],
    criteria=[
        ValidationCriterion(
            criterion_id="auditory.deterministic_output",
            version="1.0.0",
            description="Same input must produce identical summary output.",
            required_status=ValidationStatus.VERIFIED,
            fixture_kind=FixtureKind.SINGLE_SINE,
            tolerance_kind=ToleranceKind.EXACT_IDENTITY,
            tolerance_value=0.0,
        ),
        ValidationCriterion(
            criterion_id="auditory.serialization_roundtrip",
            version="1.0.0",
            description="Summary must round-trip through JSON without change.",
            required_status=ValidationStatus.VERIFIED,
            fixture_kind=FixtureKind.SINGLE_SINE,
            tolerance_kind=ToleranceKind.SERIALIZATION_IDENTITY,
            tolerance_value=0.0,
        ),
        ValidationCriterion(
            criterion_id="auditory.erb_band_contiguity",
            version="1.0.0",
            description="ERB bands must be contiguous with consecutive zero-based indexes.",
            required_status=ValidationStatus.VERIFIED,
            fixture_kind=FixtureKind.DETERMINISTIC_ERB_ENERGY,
            tolerance_kind=ToleranceKind.EXACT_IDENTITY,
            tolerance_value=0.0,
        ),
    ],
)

# -----------------------------------------------------------------------------
# Sprint 3 — Loudness Foundation
# -----------------------------------------------------------------------------

_SPRINT3_LOUDNESS_FOUNDATION = MethodValidationRecord(
    capability_id="loudness_foundation",
    method_id="noisyne.calibrated_loudness_foundation",
    method_version="1.1.0",
    implementation_status=ValidationStatus.IMPLEMENTED,
    validation_status=ValidationStatus.FOUNDATION_ONLY,
    scientific_basis=[
        "ISO 532-1:2017 (context only; no implementation claim)",
        "ISO 532-3:2023 (context only; no implementation claim)",
        "ITU-R BS.1770-5 (context only; no implementation claim)",
        "EBU R128 v5 (context only; no implementation claim)",
    ],
    validation_fixture=[
        "No normative loudness validation fixtures are available locally.",
    ],
    tolerance_policy=[
        "No calibrated loudness tolerance can be declared without validated reference fixtures.",
    ],
    supported_claims=[
        "Explicit acoustic calibration contract exists with traceable pascals_per_sample mapping",
        "Calibration supports free-field, diffuse-field, and eardrum-pressure presentation declarations",
    ],
    prohibited_claims=[
        "LUFS != COMPLETE PERCEIVED LOUDNESS",
        "No psychoacoustic loudness algorithm is included",
        "No SPL calibration is performed by the auditory frontend",
    ],
    known_limitations=[
        "Only digital_sample_amplitude input quantity is supported",
        "Only sound_pressure_pa output quantity is supported",
        "Frequency response compensation is optional and must be caller-declared",
    ],
)

# -----------------------------------------------------------------------------
# Sprint 4 — Simultaneous Masking
# -----------------------------------------------------------------------------

_SPRINT4_MASKING_FOUNDATION = MethodValidationRecord(
    capability_id="frequency_masking_foundation",
    method_id="noisyne.relative_simultaneous_masking_foundation",
    method_version="1.0.0",
    implementation_status=ValidationStatus.IMPLEMENTED,
    validation_status=ValidationStatus.VERIFIED,
    scientific_basis=[
        "Excitation-pattern models (context only; relative margin evidence only)",
    ],
    validation_fixture=[
        "identical_source_reference",
        "known_digital_gain",
        "exact_policy_boundary",
    ],
    tolerance_policy=[
        "exact_identity: identical masker and target must yield zero relative margin",
        "floating_point_numerical: 1e-12 relative tolerance for power ratio computations",
    ],
    supported_claims=[
        "Deterministic pairwise common-gain relative simultaneous-excitation evidence",
        "Caller-declared sample alignment and common digital gain relationship",
    ],
    prohibited_claims=[
        "RELATIVE MASKING EVIDENCE != AUDIBILITY THRESHOLD",
        "No absolute threshold or full-mix source attribution is performed",
    ],
    known_limitations=[
        "sample_synchronous_equal_length alignment only",
        "matched_channels_independent channel policy only",
        "common_digital_gain_uncalibrated level basis only",
    ],
)

# -----------------------------------------------------------------------------
# Sprint 5 — Brightness Correlate / Descriptor Taxonomy
# -----------------------------------------------------------------------------

_SPRINT5_BRIGHTNESS_CORRELATE = MethodValidationRecord(
    capability_id="brightness_correlate",
    method_id="noisyne.brightness_power_spectral_centroid_correlate",
    method_version="1.0.0",
    implementation_status=ValidationStatus.IMPLEMENTED,
    validation_status=ValidationStatus.VERIFIED,
    scientific_basis=[
        "Saitis and Siedenburg, JASA 148(4), 2020, DOI 10.1121/10.0002275",
        "Marozeau and de Cheveigne, JASA 121(1), 2007, DOI 10.1121/1.2384910",
    ],
    validation_fixture=[
        "single_sine",
        "known_amplitude_sine",
        "known_spectral_shift",
        "identical_source_reference",
    ],
    tolerance_policy=[
        "floating_point_numerical: 1e-9 absolute tolerance for centroid of pure tone at known frequency",
        "dsp_implementation: 1e-6 relative tolerance for centroid versus numpy.average(fft_freq, weights=power)",
    ],
    supported_claims=[
        "Power-spectral-centroid correlate of timbral brightness in hertz",
        "Relative spectral-distribution measurement without SPL calibration",
    ],
    prohibited_claims=[
        "BRIGHTNESS CORRELATE != UNIVERSAL PERCEIVED BRIGHTNESS",
        "Do not call the centroid a universal perceived-brightness scale or normalize it to a score",
        "Do not infer a source within a full mix",
    ],
    known_limitations=[
        "Bandwidth- and sample-rate-dependent",
        "Brightness perception also depends on F0, attack/time behavior, stimulus, and context",
    ],
)

_SPRINT5_SHARPNESS = MethodValidationRecord(
    capability_id="sharpness",
    method_id="noisyne.descriptor.sharpness",
    method_version="unavailable",
    implementation_status=ValidationStatus.UNAVAILABLE,
    validation_status=ValidationStatus.UNAVAILABLE,
    scientific_basis=[
        "DIN 45692:2009-08",
    ],
    validation_fixture=[
        "No local validation fixtures for DIN 45692 are available.",
    ],
    tolerance_policy=[
        "No tolerance can be declared for an unavailable method.",
    ],
    supported_claims=[
        "Descriptor taxonomy entry exists with explicit authoritative references",
    ],
    prohibited_claims=[
        "Do not label spectral centroid, high-frequency energy, or ERB centroid as sharpness",
        "Do not report acum without the complete validated DIN method",
    ],
    known_limitations=[
        "The complete paid German standard and WAV material are not available locally",
        "NOISYNE has no validated ISO 532-1 specific-loudness engine",
    ],
)

_SPRINT5_ROUGHNESS = MethodValidationRecord(
    capability_id="roughness",
    method_id="noisyne.descriptor.roughness",
    method_version="unavailable",
    implementation_status=ValidationStatus.UNAVAILABLE,
    validation_status=ValidationStatus.UNAVAILABLE,
    scientific_basis=[
        "DIN 38455:2024-11",
        "ECMA-418-2, 4th edition, June 2025, Clause 7",
    ],
    validation_fixture=[
        "No local validation fixtures for DIN 38455 or ECMA-418-2 are available.",
    ],
    tolerance_policy=[
        "No tolerance can be declared for an unavailable method.",
    ],
    supported_claims=[
        "Descriptor taxonomy entry exists with explicit authoritative references",
    ],
    prohibited_claims=[
        "Do not call an envelope FFT with a 70 Hz weighting standardized roughness",
        "Do not conflate DIN 38455 and ECMA-418-2 roughness",
    ],
    known_limitations=[
        "DIN 38455 and its executable supplements are not available locally",
        "The 53-band Sottek Hearing Model and independent ECMA validation fixtures are not implemented",
    ],
)

# -----------------------------------------------------------------------------
# Sprint 6 — Playback Transfer
# -----------------------------------------------------------------------------

_SPRINT6_PLAYBACK_TRANSFER = MethodValidationRecord(
    capability_id="playback_linear_transfer",
    method_id="noisyne.explicit_linear_playback_transfer",
    method_version="1.0.0",
    implementation_status=ValidationStatus.IMPLEMENTED,
    validation_status=ValidationStatus.VERIFIED,
    scientific_basis=[
        "Linear time-invariant system theory (FIR convolution)",
    ],
    validation_fixture=[
        "exact_playback_transfer",
        "known_digital_gain",
        "identical_source_reference",
    ],
    tolerance_policy=[
        "exact_identity: exact FIR delta must yield identical output (modulo tap_count-1 tail)",
        "floating_point_numerical: 1e-12 absolute tolerance for float64 convolution versus scipy.signal.fftconvolve",
        "dsp_implementation: 1e-9 relative tolerance for output_peak_absolute",
    ],
    supported_claims=[
        "Deterministic channel-preserving transfer by explicit real FIR convolution",
        "Validated AudioData and caller-supplied float64 read-only FIR at exact audio sample rate",
    ],
    prohibited_claims=[
        "No clipping, normalization, resampling, downmix, or nonlinear model is applied",
        "Magnitude-response transfer_kind supports shared single response only (no per-channel)",
    ],
    known_limitations=[
        "full_linear convolution boundary policy only",
        "magnitude_response requires explicit interpolation and extrapolation policies",
        "impulse_response requires sample_rate_hz and impulse_response_contains_phase",
    ],
)

# -----------------------------------------------------------------------------
# Sprint 7 — Translation Evidence / Policy
# -----------------------------------------------------------------------------

_SPRINT7_TRANSLATION_EVIDENCE = MethodValidationRecord(
    capability_id="translation_evidence_foundation",
    method_id="noisyne.translation_evidence_foundation",
    method_version="1.0.0",
    implementation_status=ValidationStatus.IMPLEMENTED,
    validation_status=ValidationStatus.VERIFIED,
    scientific_basis=[
        "Brightness correlate (Sprint 5)",
        "Programme-energy (RMS-based)",
        "ERB-power distribution (Sprint 2)",
        "Sample-peak (absolute maximum)",
    ],
    validation_fixture=[
        "exact_playback_transfer",
        "known_digital_gain",
        "known_sample_peak",
    ],
    tolerance_policy=[
        "floating_point_numerical: 1e-12 relative tolerance for delta computations",
        "dsp_implementation: 1e-9 relative tolerance for ERB-band power delta",
    ],
    supported_claims=[
        "Deterministic objective evidence for an explicit playback FIR transfer",
        "Reports brightness-correlate, ERB-power, programme-energy, and sample-peak changes only",
    ],
    prohibited_claims=[
        "POLICY EVALUATION != OBJECTIVE MIX QUALITY",
        "Translation evidence is not a probability of translation failure",
    ],
    known_limitations=[
        "full_transfer_output analysis support only",
        "Brightness centroid shift is a correlate, not a perceptual brightness scale",
    ],
)

_SPRINT7_POLICY_CONDITIONED_RISK = MethodValidationRecord(
    capability_id="policy_conditioned_translation_risk",
    method_id="noisyne.policy_conditioned_translation_risk",
    method_version="1.0.0",
    implementation_status=ValidationStatus.IMPLEMENTED,
    validation_status=ValidationStatus.VERIFIED,
    scientific_basis=[
        "Explicit caller/project/reference/validated-model policy with dimension- and unit-matched thresholds",
    ],
    validation_fixture=[
        "exact_policy_boundary",
        "known_digital_gain",
    ],
    tolerance_policy=[
        "exact_identity: policy evaluation must be deterministic for identical evidence",
        "floating_point_numerical: 1e-15 absolute tolerance for threshold comparisons",
    ],
    supported_claims=[
        "Boolean evaluation of explicit provenance-backed translation criteria",
        "Exact evidence source/dimension and unit or scale match",
    ],
    prohibited_claims=[
        "No universal thresholds, normalized score, or aggregation",
        "A declared translation-policy outcome is not a probability of translation failure",
    ],
    known_limitations=[
        "Policy criteria must use unique criterion_id values",
        "Criterion provenance must match policy provenance",
    ],
)

# -----------------------------------------------------------------------------
# Sprint 8 — Context Resolution
# -----------------------------------------------------------------------------

_SPRINT8_CONTEXT_RESOLUTION = MethodValidationRecord(
    capability_id="perceptual_context_foundation",
    method_id="noisyne.perceptual_context_foundation",
    method_version="1.0.0",
    implementation_status=ValidationStatus.IMPLEMENTED,
    validation_status=ValidationStatus.VERIFIED,
    scientific_basis=[
        "Explicit caller/project/workflow/specification declarations",
        "Deterministic conflict-resolution rules",
    ],
    validation_fixture=[
        "exact_policy_boundary",
        "identical_source_reference",
    ],
    tolerance_policy=[
        "exact_identity: identical context claims must produce identical resolution",
        "serialization_identity: round-trip must preserve resolution result exactly",
    ],
    supported_claims=[
        "Provenance-backed literal context claims and deterministic conflict resolution",
        "Explicit caller/project/workflow/specification declarations or fully described listening-SPL measurements",
    ],
    prohibited_claims=[
        "No classification, inference, profiling, or DSP is performed",
        "Context resolution conflict does not establish an audio-quality finding",
    ],
    known_limitations=[
        "Confidence score must remain unscored with unknown basis in Sprint 8",
        "Only one qualitative listening level per dimension allowed for resolution",
    ],
)

_SPRINT8_CONTEXT_POLICY_BINDING = MethodValidationRecord(
    capability_id="context_policy_binding",
    method_id="noisyne.context_policy_binding",
    method_version="1.0.0",
    implementation_status=ValidationStatus.IMPLEMENTED,
    validation_status=ValidationStatus.VERIFIED,
    scientific_basis=[
        "Exact deterministic selection of supplied translation-risk policies",
    ],
    validation_fixture=[
        "exact_policy_boundary",
    ],
    tolerance_policy=[
        "exact_identity: identical resolved context and binding must produce identical selection",
    ],
    supported_claims=[
        "Exact deterministic selection of supplied translation-risk policies",
        "A resolved conflict-free context, explicit versioned binding, and exact supplied policy identity/version",
    ],
    prohibited_claims=[
        "No policy or threshold generation is performed",
        "Ambiguous or conflict selection must not identify matched bindings incorrectly",
    ],
    known_limitations=[
        "Selected result requires resolved context",
        "Unresolved selection requires exactly one matched binding",
    ],
)

# -----------------------------------------------------------------------------
# Sprint 9 — Reference Comparison
# -----------------------------------------------------------------------------

_SPRINT9_REFERENCE_COMPARISON = MethodValidationRecord(
    capability_id="reference_objective_comparison",
    method_id="noisyne.perceptual_reference_foundation",
    method_version="1.0.0",
    implementation_status=ValidationStatus.IMPLEMENTED,
    validation_status=ValidationStatus.VERIFIED,
    scientific_basis=[
        "Brightness correlate (Sprint 5)",
        "Programme-energy (RMS-based)",
        "ERB-power distribution (Sprint 2)",
        "Sample-peak (absolute maximum)",
    ],
    validation_fixture=[
        "identical_source_reference",
        "known_digital_gain",
        "known_sample_peak",
        "known_spectral_shift",
    ],
    tolerance_policy=[
        "exact_identity: identical source and reference must yield zero delta for all dimensions",
        "floating_point_numerical: 1e-12 relative tolerance for delta computations",
        "dsp_implementation: 1e-9 relative tolerance for ERB-band comparison",
    ],
    supported_claims=[
        "Whole-programme objective source-minus-reference evidence",
        "Validated AudioData and existing Sprint 2/5 analysis",
    ],
    prohibited_claims=[
        "References are examples, not ground truth or quality targets",
        "No temporal alignment or aggregate match score is produced",
    ],
    known_limitations=[
        "ERB comparison requires exact channel and band compatibility",
        "shape-only mode skips programme_energy and sample_peak",
    ],
)

_SPRINT9_REFERENCE_EMBEDDING = MethodValidationRecord(
    capability_id="reference_embedding_contract",
    method_id="noisyne.reference_embedding_cosine",
    method_version="1.0.0",
    implementation_status=ValidationStatus.IMPLEMENTED,
    validation_status=ValidationStatus.FOUNDATION_ONLY,
    scientific_basis=[
        "CLAP/laion-clap model architecture (contract only; no live model bundled)",
    ],
    validation_fixture=[
        "No live CLAP model is bundled; contract-only validation.",
    ],
    tolerance_policy=[
        "No runtime tolerance can be validated without bundled model assets.",
    ],
    supported_claims=[
        "Identified embedding-provider transport and raw cosine comparison contract",
        "Exact provider/model/checkpoint/preprocessing identity and finite runtime vectors",
    ],
    prohibited_claims=[
        "No live provider, model asset, or embedding is bundled by this capability",
        "Cosine similarity alone does not establish perceptual similarity",
    ],
    known_limitations=[
        "Contract-only; runtime requires external model download or local model_root",
        "Sprint 9 supports cosine_similarity metric only",
    ],
)

# -----------------------------------------------------------------------------
# Sprint 10 — Mix Intelligence
# -----------------------------------------------------------------------------

_SPRINT10_MIX_INTELLIGENCE = MethodValidationRecord(
    capability_id="perceptual_mix_intelligence_foundation",
    method_id="noisyne.perceptual_mix_intelligence_foundation",
    method_version="1.0.0",
    implementation_status=ValidationStatus.IMPLEMENTED,
    validation_status=ValidationStatus.VERIFIED,
    scientific_basis=[
        "Explicit policy criteria with dimension- and unit-matched thresholds",
        "Deterministic priority and issue derivation",
    ],
    validation_fixture=[
        "exact_policy_boundary",
        "known_digital_gain",
        "identical_source_reference",
    ],
    tolerance_policy=[
        "exact_identity: identical evidence and policy must produce identical issues",
        "serialization_identity: MixIntelligenceResult must round-trip exactly",
        "floating_point_numerical: 1e-15 absolute tolerance for threshold comparisons",
    ],
    supported_claims=[
        "Structured issues from explicit policy criteria and precomputed evidence",
        "Caller-supplied versioned policy, declared priorities, and supported Sprint 4/7/8/9 evidence",
    ],
    prohibited_claims=[
        "POLICY EVALUATION != OBJECTIVE MIX QUALITY",
        "No universal thresholds, quality score, recommendations, DSP, or LLM",
        "A declared translation-policy outcome is not a probability of translation failure",
    ],
    known_limitations=[
        "Mix issue confidence must remain unscored with unknown basis",
        "Issues must correspond exactly to triggered evaluations",
    ],
)

# -----------------------------------------------------------------------------
# Sprint 11 — Grounded Reasoning
# -----------------------------------------------------------------------------

_SPRINT11_GROUNDED_REASONING = MethodValidationRecord(
    capability_id="perceptual_reasoning_foundation",
    method_id="noisyne.grounded_perceptual_reasoning_foundation",
    method_version="1.0.0",
    implementation_status=ValidationStatus.IMPLEMENTED,
    validation_status=ValidationStatus.VERIFIED,
    scientific_basis=[
        "Deterministic fact extraction from Sprint 10 results",
        "Canonical statement rendering with whitelisted templates",
    ],
    validation_fixture=[
        "exact_policy_boundary",
        "identical_source_reference",
    ],
    tolerance_policy=[
        "exact_identity: identical source result and provider must produce identical grounded statements",
        "serialization_identity: PerceptualReasoningResult must round-trip exactly",
    ],
    supported_claims=[
        "Grounded explanations rendered from validated Sprint 10 facts",
        "Deterministic provider is offline; no live model is required",
    ],
    prohibited_claims=[
        "STRUCTURED REASONING != SCIENTIFIC TRUTH",
        "Provider output must select whitelisted fact IDs and approved templates; free-form provider text is rejected",
    ],
    known_limitations=[
        "Only deterministic_template provider type is fully validated",
        "Reasoning confidence must remain unscored with unknown basis",
    ],
)


# -----------------------------------------------------------------------------
# Aggregate matrix
# -----------------------------------------------------------------------------

_ALL_RECORDS: tuple[MethodValidationRecord, ...] = (
    _SPRINT2_AUDITORY_FRONTEND,
    _SPRINT3_LOUDNESS_FOUNDATION,
    _SPRINT4_MASKING_FOUNDATION,
    _SPRINT5_BRIGHTNESS_CORRELATE,
    _SPRINT5_SHARPNESS,
    _SPRINT5_ROUGHNESS,
    _SPRINT6_PLAYBACK_TRANSFER,
    _SPRINT7_TRANSLATION_EVIDENCE,
    _SPRINT7_POLICY_CONDITIONED_RISK,
    _SPRINT8_CONTEXT_RESOLUTION,
    _SPRINT8_CONTEXT_POLICY_BINDING,
    _SPRINT9_REFERENCE_COMPARISON,
    _SPRINT9_REFERENCE_EMBEDDING,
    _SPRINT10_MIX_INTELLIGENCE,
    _SPRINT11_GROUNDED_REASONING,
)


@dataclass(frozen=True, slots=True)
class PerceptualValidationMatrix:
    """Machine-readable and documented claim matrix for V2 perceptual capabilities."""

    records: tuple[MethodValidationRecord, ...] = field(default=_ALL_RECORDS)
    schema_version: str = VALIDATION_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if not isinstance(self.records, tuple) or any(
            not isinstance(item, MethodValidationRecord) for item in self.records
        ):
            raise TypeError("records must be a tuple of MethodValidationRecord values")
        ids = [(r.capability_id, r.method_id, r.method_version) for r in self.records]
        if len(ids) != len(set(ids)):
            raise ValueError("records must have unique capability_id + method_id + method_version")

    @classmethod
    def build(cls) -> Self:
        return cls()

    def by_capability(self, capability_id: str) -> MethodValidationRecord | None:
        for record in self.records:
            if record.capability_id == capability_id:
                return record
        return None

    def by_status(self, status: ValidationStatus) -> tuple[MethodValidationRecord, ...]:
        return tuple(r for r in self.records if r.validation_status is status)

    def summary(self) -> dict[str, int]:
        counts: dict[str, int] = {
            "foundation_only": 0,
            "implemented": 0,
            "verified": 0,
            "validated": 0,
            "unavailable": 0,
        }
        for record in self.records:
            counts[record.validation_status.value] += 1
        counts["total"] = len(self.records)
        return counts


__all__ = [
    "PerceptualValidationMatrix",
]
