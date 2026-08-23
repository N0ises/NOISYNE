# PHASENØX V2 Translation Evidence and Risk Foundation

Version: 1.0.0

Status: Implemented (Sprint 7)

## Scope

Sprint 7 keeps three layers separate:

1. **Objective evidence** records deterministic changes between original audio and the complete
   output of one identified, executable Sprint 6 FIR transfer.
2. **Decision policy** records explicit, versioned, provenance-backed criteria.
3. **Risk result** states only whether each declared criterion was exceeded.

No universal translation score or threshold exists in this foundation. A device-category label is
not executable transfer evidence. Policy-free analysis returns evidence only and emits no risk.

## Standards and research boundary

The following authoritative editions were inspected before implementation:

- ITU-R BS.1387-2 (05/2023), objective measurements of perceived audio quality.
- ITU-R BS.1770-5 (11/2023), programme loudness and true-peak level.
- EBU R 128 v5.0 (November 2023), loudness normalization and permitted maximum level.
- EBU Tech 3341 v4.0 (November 2023), EBU Mode loudness metering.
- EBU Tech 3342 v4.0 (November 2023), Loudness Range.
- ITU-R BS.1534-3 (10/2015, editorial amendments March 2023), MUSHRA subjective assessment.
- AES TD1008.1.21-9 (24 September 2021), streaming/on-demand distribution loudness guidance.

BS.1387 establishes a tightly scoped reference-versus-signal-under-test architecture with explicit
synchronization, perceptual/cognitive model stages, model output variables, validation, conformance,
and application limits. Sprint 7 uses that only as a methodological boundary. It does not implement
PEAQ, ODG, DI, model output variables, trained mappings, disturbance variables, bandwidth penalties,
or BS.1387 conformance.

BS.1770-5, R 128, Tech 3341, and Tech 3342 define programme loudness, true-peak, metering, and LRA
quantities for their stated channel/rendering and distribution contexts. The existing repository LUFS
path is retained unchanged, but it does not have the explicit BS.1770-5/R128 v5 qualification and
reference-fixture record required to add a new Sprint 7 loudness-delta claim. Loudness and LRA
translation evidence are therefore deferred. Distribution loudness guidance is not a universal device
translation model.

BS.1534-3 defines a subjective listening-test method with a hidden reference and anchors. MUSHRA is
a future validation route, not a runtime objective algorithm. No MUSHRA score or anchor is generated.

## Transfer and alignment requirement

`TranslationEvidenceAnalyzer` accepts only `ImpulseResponseTransfer`. Magnitude-only Sprint 6
evidence is rejected because it cannot create before/after audio without invented phase. Profile ID,
profile version, target `PlaybackProfileReference`, transfer provenance, evidence version, transfer
method version, and source analysis method versions remain in the compact result.

Sprint 6 aligns FIR tap zero with source sample zero and produces `N + M - 1` samples. Sprint 7 uses
`FULL_TRANSFER_OUTPUT` support:

- the original is analyzed over all `N` source samples;
- the transferred signal is analyzed over all `N + M - 1` output samples;
- the complete FIR tail is included;
- no signal is silently truncated or padded to match the other support.

This choice retains physical or mathematical transfer decay. It is not a universal assertion that every
future use case should include tails; a future method would require a new support policy and version.

## Objective evidence

### Brightness-correlate centroid shift

Sprint 5's exact power-spectral-centroid correlate and method identity are reused independently over
the original and full transferred signals:

```text
brightness_delta_hz = transferred_centroid_hz - original_centroid_hz
```

Positive means the transferred centroid is higher. Negative means it is lower. This is an objective
spectral-centroid change, not a perceived-brightness failure judgment. If either signal has no positive
analyzed spectral power, the evidence is `INSUFFICIENT_EVIDENCE`.

### Sprint 2 ERB-rate power-distribution change

Sprint 2 frame powers are summed independently for every programme channel and native ERB-rate
band. No waveform downmix or arithmetic channel averaging occurs. Where both powers are positive:

```text
band_delta_db[c,b] = 10 * log10(
    transferred_band_power[c,b] / original_band_power[c,b]
)
```

Positive means greater transferred power in that channel/band; negative means less. This is an
engineering/auditory-frontend power delta, not an audibility threshold, masking result, or bass/mid/high
judgment. The transport summary records defined count and min/max/maximum-absolute delta. Runtime
arrays retain original power, transferred power, dB delta, and a definition mask with shape
`[programme_channels, erb_bands]`.

When either side of a band ratio is zero, the logarithmic delta is undefined. The mask is false and the
finite runtime delta slot is zero solely as an explicitly masked storage placeholder. It must never be
interpreted as a measured zero-dB change.

### Programme energy change

Channels are aggregated by power summation, never waveform downmixing:

```text
E = sum over samples n and programme channels c of x[n,c]^2
programme_energy_delta_db = 10 * log10(E_transferred / E_original)
```

Positive means greater transferred digital energy; negative means less. This quantity uses complete
signal support and is not programme loudness or perceived loudness. If either energy is zero, the dB
ratio is undefined and the evidence is `INSUFFICIENT_EVIDENCE`; no epsilon or finite substitute is
introduced.

### Peak and nominal full scale

The result records original and transferred absolute sample peaks and whether either exceeds nominal
floating full scale (`1.0`). Sprint 6 retains finite samples beyond unity, so exceedance does not mean
that clipping, distortion, or an audible artifact occurred. It is not a BS.1770 true-peak measurement.

## Channel and source policy

Channels remain independent programme channels. Channel count does not identify layout, ears, or a
binaural presentation. Stereo is never summed to mono, so opposite-phase channels do not cancel.
No LFE, layout, rendering, source, stem, instrument, listener, or room meaning is inferred.

Full-mix evidence does not provide source attribution. Sprint 4 masking translation is not run because
one full mix does not establish ordered masker and target sources. No source separation is added.

## Explicit risk policy

`TranslationRiskPolicy` contains a stable policy ID/version, provenance, source, description, and one
or more unique criteria. Every `TranslationRiskCriterion` records its own ID/version, evidence
dimension, operator, numeric threshold, unit/scale, direction semantics, matching provenance, source,
description, assumptions, and limitations.

Policy provenance is one of:

- `USER_DECLARED`
- `PROJECT_DECLARED`
- `REFERENCE_SPECIFICATION`
- `VALIDATED_MODEL`

Missing provenance/source is rejected. A caller must not label a hand-authored threshold as
`VALIDATED_MODEL`.

Supported operators are strictly greater than, greater than or equal, less than, less than or equal,
absolute greater than, and absolute greater than or equal. Equality follows the operator literally:
`GREATER_THAN` excludes equality; `GREATER_THAN_OR_EQUAL` includes it. Threshold units/scales must
exactly match the selected evidence quantity. Hz cannot be compared with dB, and digital sample
amplitude cannot be compared with either.

Supported scalar policy dimensions are:

- signed brightness-centroid shift in Hz;
- signed programme-energy delta in dB;
- maximum absolute defined ERB-band delta in dB;
- transferred absolute sample peak in digital sample amplitude.

Unknown dimensions and unit mismatches are rejected. Undefined evidence cannot produce a risk
value. If every requested dimension is undefined, the frozen Sprint 1 `TranslationResult` is
`INSUFFICIENT_EVIDENCE` and carries no risk dimensions.

## Risk and confidence semantics

A computed Sprint 1 `TranslationRiskDimension.risk` is a boolean `ScalarValue` on the named scale
`declared_policy_threshold_exceeded`:

- `true`: the explicit comparison evaluated true;
- `false`: it evaluated false.

It is not normalized and is not a probability. `aggregate_risk` is always `None`; heterogeneous
criteria are never averaged, weighted, maximized, or converted into a percentage. Confidence carries
no numeric score. It states that comparison is deterministic while making no claim about listener
outcomes, preference, audibility, or mix quality.

## Runtime and transport boundary

All runtime ERB arrays are exact-shape NumPy `float64`/`bool`, finite where represented, and read-only.
Undefined values are governed by the boolean mask. Large arrays are absent from JSON. Transport
contains compact identity, method, support, evidence, policy, summary, assumptions, limitations, and
frozen Sprint 1 risk contracts. `PERCEPTUAL_SCHEMA_VERSION` remains `1.0.0`.

## Validation

Independent fixtures cover identity, half gain, double gain, a known frequency-selective FIR, policy
boundaries below/equal/above, missing provenance, unit mismatch, unknown dimensions, silence,
zero-output energy, mono/stereo, opposite-phase stereo, full FIR tail, magnitude-only rejection,
JSON round-trip, determinism, immutable arrays, and nominal-full-scale evidence.

Expected analytical values include:

- identity: brightness, defined ERB power, and programme energy deltas are zero;
- `[0.5]`: programme energy and every defined band change by
  `10*log10(0.25) = -6.020599913279624 dB`, with unchanged centroid/relative shape;
- `[2.0]`: programme energy changes by `+6.020599913279624 dB`;
- `[1.0, 0.5]` applied to a delta: full output energy changes by `10*log10(1.25)` and the one-sample
  FIR tail is included.

## Explicit non-claims

- **OBJECTIVE CHANGE != AUDIBLE IMPAIRMENT**
- **LOUDNESS CHANGE != TRANSLATION QUALITY**
- **BRIGHTNESS CENTROID SHIFT != PERCEIVED BRIGHTNESS FAILURE**
- **SPECTRAL POWER LOSS != MASKING**
- **FULL-MIX ANALYSIS != SOURCE ATTRIBUTION**
- **POLICY THRESHOLD EXCEEDED != PROBABILITY OF FAILURE**
- **PEAQ != PHASENOX TRANSLATION RISK**
- **DEVICE CATEGORY != TRANSFER EVIDENCE**

Sprint 8 may add explicit listener, genre, delivery, or artistic context. Sprint 7 does not infer those
factors and does not provide recommendations, reasoning prose, ML/LLM inference, or device presets.
