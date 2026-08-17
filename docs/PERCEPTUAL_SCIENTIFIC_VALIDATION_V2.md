# NØISYNE V2 — Perceptual Scientific Validation

## Sprint 12 — Evaluation / Scientific Validation

**Date:** 2026-08-17  
**Branch:** `v2-development`  
**Schema Version:** `1.0.0`

---

## 1. Purpose

This document establishes the scientific validation framework for the NØISYNE V2 perceptual pipeline (Sprints 2–11).  It is **not** a product feature specification and does **not** add new perceptual capabilities.

The goal is to answer, for each existing V2 perceptual method:

1. What exactly is implemented?
2. What has actually been validated?
3. Against what fixture/reference?
4. What error/tolerance is acceptable?
5. What scientific/product claims are allowed?
6. What claims remain prohibited?

---

## 2. Validation Status Taxonomy

Sprint 12 introduces an explicit validation lifecycle that is **deliberately separate** from runtime `CapabilityStatus` and `ResultStatus`.

| Status | Meaning |
|--------|---------|
| **FOUNDATION_ONLY** | Contracts, taxonomy, and identity exist; no implementation yet. |
| **IMPLEMENTED** | Code executes and produces deterministic output; not yet validated. |
| **VERIFIED** | Implementation correctness confirmed against synthetic/deterministic fixtures. |
| **VALIDATED** | Scientific/perceptual validation completed against normative reference. |
| **UNAVAILABLE** | Blocked: missing standard material, prerequisite, validated model, or fixture. |

### Critical Principle

> **IMPLEMENTED ≠ VALIDATED**  
> **VERIFIED ≠ VALIDATED**  
> Implementation correctness against synthetic fixtures is **not** perceptual validity.

---

## 3. Implementation vs. Scientific Validation

| Aspect | Implementation Correctness | Scientific / Perceptual Validation |
|--------|---------------------------|-----------------------------------|
| Question | Does the code run and produce deterministic output? | Does the output correspond to human perception? |
| Method | Unit tests, synthetic fixtures, round-trip checks | Listening tests, normative reference implementations, calibrated measurements |
| Scope | Code logic, serialization, arithmetic | Psychoacoustic models, SPL calibration, standard conformance |
| Sprint 12 Status | Most V2 methods are VERIFIED | No V2 method is VALIDATED |

---

## 4. Claim Matrix Coverage

The machine-readable claim matrix (`noisyne/perception/validation_matrix.py`) covers:

### Sprint 2 — Auditory Frontend
- **Status:** IMPLEMENTED / VERIFIED
- **Method:** `noisyne.auditory_frontend` v1.0.0
- **Verified against:** Frame/window/FFT/power/ERB aggregation, contiguity, determinism
- **Fixtures:** silence, zero-energy, single sine, two-tone, ERB energy
- **Tolerance:** 1e-12 (FP numerical), 1e-9 (DSP ERB boundaries)

### Sprint 3 — Loudness Foundation
- **Status:** IMPLEMENTED / FOUNDATION_ONLY
- **Method:** `noisyne.calibrated_loudness_foundation` v1.1.0
- **Foundation only:** Calibration contract structure only
- **Blocked:** No local ISO 532-1 / ITU-R BS.1770-5 / EBU R128 validation fixtures
- **Explicit Non-Claim:** `LUFS != COMPLETE PERCEIVED LOUDNESS`

### Sprint 4 — Simultaneous Masking
- **Status:** IMPLEMENTED / VERIFIED
- **Method:** `noisyne.relative_simultaneous_masking_foundation` v1.0.0
- **Verified against:** Pairwise common-gain relative excitation-margin evidence
- **Fixtures:** identical source/reference, known digital gain, policy boundaries
- **Explicit Non-Claim:** `RELATIVE MASKING EVIDENCE != AUDIBILITY THRESHOLD`

### Sprint 5 — Brightness Correlate
- **Status:** IMPLEMENTED / VERIFIED
- **Method:** `noisyne.brightness_power_spectral_centroid_correlate` v1.0.0
- **Verified against:** Power-spectral-centroid computation against known sine inputs
- **Fixtures:** single sine, known amplitude, spectral shift, identical reference
- **Explicit Non-Claim:** `BRIGHTNESS CORRELATE != UNIVERSAL PERCEIVED BRIGHTNESS`

### Sprint 5 — Sharpness (Unavailable)
- **Status:** UNAVAILABLE / UNAVAILABLE
- **Blocked:** DIN 45692:2009 standard material not available; no ISO 532-1 specific-loudness engine

### Sprint 5 — Roughness (Unavailable)
- **Status:** UNAVAILABLE / UNAVAILABLE
- **Blocked:** DIN 38455:2024 supplements not available; no ECMA-418-2 Sottek Hearing Model

### Sprint 6 — Playback Transfer
- **Status:** IMPLEMENTED / VERIFIED
- **Method:** `noisyne.explicit_linear_playback_transfer` v1.0.0
- **Verified against:** FIR convolution against delta impulse and known gain
- **Fixtures:** exact playback transfer, known digital gain
- **Tolerance:** 1e-12 (FP numerical), exact identity for delta impulse

### Sprint 7 — Translation Evidence
- **Status:** IMPLEMENTED / VERIFIED
- **Method:** `noisyne.translation_evidence_foundation` v1.0.0
- **Verified against:** Before/after/delta evidence for brightness, ERB, energy, peak
- **Explicit Non-Claim:** `POLICY EVALUATION != OBJECTIVE MIX QUALITY`

### Sprint 7 — Policy-Conditioned Translation Risk
- **Status:** IMPLEMENTED / VERIFIED
- **Method:** `noisyne.policy_conditioned_translation_risk` v1.0.0
- **Verified against:** Boolean threshold evaluation determinism
- **Explicit Non-Claim:** No universal thresholds or normalized scores

### Sprint 8 — Context Resolution
- **Status:** IMPLEMENTED / VERIFIED
- **Method:** `noisyne.perceptual_context_foundation` v1.0.0
- **Verified against:** Deterministic conflict resolution, round-trip stability
- **Explicit Non-Claim:** No classification, inference, profiling, or DSP

### Sprint 8 — Context Policy Binding
- **Status:** IMPLEMENTED / VERIFIED
- **Method:** `noisyne.context_policy_binding` v1.0.0
- **Verified against:** Exact deterministic policy selection

### Sprint 9 — Reference Comparison
- **Status:** IMPLEMENTED / VERIFIED
- **Method:** `noisyne.perceptual_reference_foundation` v1.0.0
- **Verified against:** Whole-programme objective deltas for brightness, energy, ERB, peak
- **Fixtures:** identical source/reference, known spectral shift

### Sprint 9 — Reference Embedding (Contract Only)
- **Status:** IMPLEMENTED / FOUNDATION_ONLY
- **Method:** `noisyne.reference_embedding_cosine` v1.0.0
- **Foundation only:** Transport contract only; no live CLAP model bundled
- **Blocked:** Model asset not available locally

### Sprint 10 — Mix Intelligence
- **Status:** IMPLEMENTED / VERIFIED
- **Method:** `noisyne.perceptual_mix_intelligence_foundation` v1.0.0
- **Verified against:** Policy-criteria evaluation, issue derivation, count balancing
- **Explicit Non-Claim:** `POLICY EVALUATION != OBJECTIVE MIX QUALITY`

### Sprint 11 — Grounded Reasoning
- **Status:** IMPLEMENTED / VERIFIED
- **Method:** `noisyne.grounded_perceptual_reasoning_foundation` v1.0.0
- **Verified against:** Fact extraction, canonical rendering, deterministic statement generation
- **Explicit Non-Claim:** `STRUCTURED REASONING != SCIENTIFIC TRUTH`

---

## 5. Fixture Strategy

All fixtures are:
- **Deterministic:** Same parameters always produce identical signals
- **Offline:** No network or model downloads required
- **Synthetic:** Do not represent real audio content
- **Referenceable:** Parameters are explicit and auditable

### Fixture Catalogue

| Fixture | Purpose | Used By |
|---------|---------|---------|
| silence | Baseline zero-input behavior | Sprint 2, general boundary |
| zero_energy | Explicit energy-zero signal | Sprint 2, boundary |
| single_sine | Known-frequency pure tone | Sprint 2, 5, 6 |
| known_amplitude_sine | Calibrated amplitude verification | Sprint 2, 5 |
| two_tone | Multi-tone spectral interaction | Sprint 2 |
| known_digital_gain | Exact linear gain relationship | Sprint 4, 6, 7, 9 |
| known_sample_peak | Exact peak verification | Sprint 7, 9 |
| known_spectral_shift | Centroid/bandshift validation | Sprint 5, 9 |
| deterministic_erb_energy | ERB band placement verification | Sprint 2 |
| identical_source_reference | Zero-delta reference sanity check | Sprint 4, 6, 7, 8, 9, 10 |
| exact_playback_transfer | FIR convolution identity | Sprint 6, 7 |
| exact_policy_boundary | Threshold edge-case testing | Sprint 7, 8, 10 |

### Critical Principle

> **SYNTHETIC FIXTURE PASS ≠ HUMAN PERCEPTUAL VALIDATION**

---

## 6. Tolerance Policy

Explicit domain-appropriate tolerances are defined per method.  No global epsilon is used.

| Tolerance Kind | When Used | Typical Value |
|----------------|-----------|---------------|
| **exact_identity** | Deterministic counts, IDs, serialization | 0.0 |
| **serialization_identity** | JSON round-trip, dict ordering | 0.0 |
| **floating_point_numerical** | Pure math operations, scalar deltas | 1e-12 to 1e-15 |
| **dsp_implementation** | FFT, convolution, ERB aggregation | 1e-6 to 1e-9 |
| **reference_method** | Comparison against external reference | Not yet declared (blocked) |

Each tolerance in the claim matrix includes a documented reason.

---

## 7. Standards Boundaries

The following standards are referenced in the V2 perceptual pipeline.  **No standard conformance is claimed** unless the implementation has been validated against the required normative material.

| Standard | Context | Validation Status |
|----------|---------|-------------------|
| ISO 226:2023 | Equal-loudness contours (context only) | Referenced, not validated |
| ISO 532-1:2017 | Loudness (Zwicker) | Not implemented |
| ISO 532-2:2017 | Loudness (Moore-Glasberg) | Not implemented |
| ISO 532-3:2023 | Moore-Glasberg-Schlittenlacher loudness method | Not implemented |
| ITU-R BS.1770-5 | Programme loudness | Not implemented |
| EBU R128 v5 | Loudness normalisation | Not implemented |
| EBU Tech 3341–3344 | Loudness measurement | Not implemented |
| DIN 45692:2009 | Sharpness | Blocked (no standard material) |
| DIN 38455:2024 | Roughness | Blocked (no supplements) |
| ECMA-418-2 4th ed 2025 | Sottek Hearing Model | Blocked (no model implementation) |
| ITU-R BS.1387-2 | PEQ (Perceptual Evaluation) | Not implemented |
| ITU-R BS.1116-3 | Subjective listening tests | Not implemented |
| ITU-R BS.1534-3 | MUSHRA | Not implemented |

---

## 8. What Is NOT Validated

The following remain **explicitly unvalidated** in Sprint 12:

- **Perceptual loudness:** No ISO 532 or ITU-R BS.1770 implementation exists.
- **Sharpness:** Blocked by missing DIN 45692 standard material and prerequisite loudness engine.
- **Roughness:** Blocked by missing DIN 38455 supplements and ECMA-418-2 model.
- **Fluctuation strength:** Blocked by missing ECMA-418-2 Clause 9 implementation.
- **Tonality:** Blocked by missing ECMA-418-2 Clause 6 implementation.
- **Live CLAP embedding:** Contract only; no bundled model.
- **Live LLM reasoning:** Deterministic template provider only; no structured model validated.
- **RAG/memory:** Separate preflight issues documented in V2_RAG_MEMORY_PREFLIGHT_REPORT.md.

---

## 9. Blocked Validation

| Blocker | Affected Methods | Resolution Path |
|---------|-----------------|----------------|
| Missing DIN 45692:2009 standard material | sharpness | Acquire standard + validation WAVs |
| Missing DIN 38455:2024 supplements | roughness | Acquire supplements + executable model |
| Missing ECMA-418-2 Sottek model | roughness, fluctuation, tonality | Implement 53-band model + validation |
| Missing ISO 532-1 specific-loudness engine | sharpness | Implement or integrate validated engine |
| Missing ITU-R BS.1770-5 reference fixtures | loudness_foundation | Acquire reference test vectors |
| No bundled CLAP model | reference_embedding_contract | Bundle or validate model download |

---

## 10. How Sprint 13+ Must Consume Validation Truth

Future sprints **must**:

1. **Read** the validation status before adding new capabilities.
2. **Respect** prohibited claims; do not widen them to make features pass.
3. **Update** the claim matrix when a method advances in validation status.
4. **Add** fixtures and evidence before claiming a method is VERIFIED or VALIDATED.
5. **Keep** lifecycle state, runtime availability, and validation status separate.

Future sprints **must not**:

1. Conflate implementation with validation.
2. Present synthetic fixture passes as perceptual proof.
3. Claim standards conformance without normative validation.
4. Add hidden confidence scores or fake percentages.

---

## 11. Explicit Non-Claims Summary

| Non-Claim | Meaning |
|-----------|---------|
| `IMPLEMENTED != VALIDATED` | Code running does not mean it is scientifically correct. |
| `SYNTHETIC FIXTURE PASS != HUMAN PERCEPTUAL VALIDATION` | Sine waves are not listeners. |
| `POLICY EVALUATION != OBJECTIVE MIX QUALITY` | Threshold triggers are not quality judgments. |
| `BRIGHTNESS CORRELATE != UNIVERSAL PERCEIVED BRIGHTNESS` | Spectral centroid is a correlate only. |
| `RELATIVE MASKING EVIDENCE != AUDIBILITY THRESHOLD` | Margin evidence is not audibility. |
| `LUFS != COMPLETE PERCEIVED LOUDNESS` | Programme loudness / LUFS is not a complete model of perceived loudness. |
| `STRUCTURED REASONING != SCIENTIFIC TRUTH` | Templates render facts; they do not discover truth. |

---

## 12. Files Added / Modified

### New Files

- `noisyne/perception/validation_contracts.py` — Validation contracts and API
- `noisyne/perception/validation_matrix.py` — Machine-readable claim matrix
- `noisyne/perception/validation_fixtures.py` — Deterministic fixture provider
- `tests/test_sprint12_validation_framework.py` — Sprint 12 validation tests
- `docs/PERCEPTUAL_SCIENTIFIC_VALIDATION_V2.md` — This document

### Unmodified

All existing Sprint 2–11 source files remain unmodified.  Sprint 12 is additive only.

---

*End of Sprint 12 Scientific Validation Framework.*
