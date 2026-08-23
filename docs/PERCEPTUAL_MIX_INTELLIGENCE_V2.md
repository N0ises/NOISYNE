# PHASENOX V2 Perceptual Mix Intelligence

## Scope

Sprint 10 converts existing, identified evidence into structured issues only when an explicit,
versioned policy criterion is satisfied. It does not analyze audio, infer thresholds, estimate mix
quality, generate recommendations, or modify audio.

The architecture keeps five concepts separate:

1. **Evidence** — precomputed Sprint 4, 7, 8, or 9 results.
2. **Criterion/policy** — a caller-, project-, reference-, or validated-model-supplied rule.
3. **Issue** — a deterministic record that a named criterion was satisfied.
4. **Priority** — an ordinal value declared by that criterion.
5. **Recommendation** — deferred; absent from Sprint 10 transport and runtime behavior.

## Standards and research boundary

The following sources define boundaries, not implemented algorithms:

- [ITU-R BS.1387-2 (05/2023)](https://www.itu.int/rec/R-REC-BS.1387-2-202305-I/en)
  defines objective perceived-audio-quality measurement with specified reference/test relationships,
  model outputs, applications, synchronization, and conformance. Sprint 10 does not implement PEAQ,
  ODG, DI, MOVs, or claim compatibility.
- [ITU-R BS.1116-3](https://www.itu.int/dms_pubrec/itu-r/rec/bs/R-REC-BS.1116-3-201502-I%21%21PDF-E.pdf)
  specifies controlled subjective assessment of small impairments, including hidden-reference test
  design and listening conditions. Sprint 10 does not produce listening-panel or impairment grades.
- [ITU-R BS.1534-3](https://www.itu.int/rec/R-REC-BS.1534-3-201510-I/en) specifies MUSHRA for
  controlled subjective assessment of intermediate audio quality. Sprint 10 does not implement a
  MUSHRA test or infer its scores.
- Torcoli, Kastner, and Herre,
  [Objective Measures of Perceptual Audio Quality Reviewed: An Evaluation of Their Application Domain Dependence](https://doi.org/10.1109/TASLP.2021.3069302),
  compares objective metrics against listening tests in coding and source-separation domains. It
  supports the boundary that validation and training domain matter; a metric is not universal mix
  quality merely because it correlates in another task.

No standard above supplies universal mix thresholds, priority, or a generic mix-quality score.

## Public contracts

The lightweight public surface consists of:

- `MixIssuePriority`
- `MixIssueType`
- `MixEvidenceSourceType`
- `MixEvidenceDimensionId`
- `MixCriterionOperator`
- `MixEvaluationState`
- `MixIssueCriterion`
- `MixIssuePolicy`
- `MixCriterionEvaluation`
- `MixIssue`
- `MixIntelligenceSummary`
- `MixIntelligenceResult`

`TranslationPolicyProvenance` is reused rather than duplicated. Its values are `USER_DECLARED`,
`PROJECT_DECLARED`, `REFERENCE_SPECIFICATION`, and `VALIDATED_MODEL`. The last value is only caller
metadata; the engine does not verify model validation.

Every policy and criterion has an exact ID/version and source. Criteria within a policy must have
unique IDs and matching provenance. Criteria declare their evidence source, canonical dimension,
optional exact evidence identity, operator, threshold with unit/scale, neutral issue type, fixed
priority, and optional non-negative policy rank. No default criteria or thresholds exist.

## Supported evidence and dimensions

The evaluator consumes already-produced evidence objects. It never reruns the auditory frontend,
descriptors, playback transfer, reference analysis, CLAP, source separation, or another signal stage.

### Sprint 9 reference evidence

- `reference.brightness_centroid_delta_hz`
- `reference.programme_energy_delta_db`
- `reference.erb_band_maximum_absolute_delta_db`
- `reference.sample_peak_delta_absolute`

Signed values retain Sprint 9 source-minus-reference semantics. The ERB value is the compact summary's
maximum absolute defined delta; runtime matrices are not copied. A reference deviation is not quality
loss, and no dimensions are aggregated.

### Sprint 7 translation evidence

- `translation.brightness_centroid_shift_hz`
- `translation.programme_energy_delta_db`
- `translation.erb_band_maximum_absolute_delta_db`
- `translation.transferred_peak_absolute`

The existing evidence values and methods are reused without recalculating translation risk.

For `PolicyConditionedTranslationRiskResult`, Sprint 10 exposes only:

- `translation_policy.declared_policy_threshold_exceeded`

Each boolean retains the exact Sprint 7 policy and criterion identity. It is not a probability of
translation failure.

### Sprint 8 context evidence

- `context.resolution_conflict`
- `context.policy_selection_conflict`
- `context.policy_selection_ambiguous`

These can produce `CONTEXT_POLICY_CONFLICT` workflow/configuration issues under explicit boolean
criteria. They are not audio-quality issues.

### Sprint 4 masking evidence

- `masking.maximum_relative_excitation_margin_db`

This adapter is intentionally runtime-only and lazy. It accepts an existing caller-declared,
aligned `RelativeMaskingFoundationResult` and extracts the maximum defined signed relative excitation
margin. It does not analyze audio, serialize matrices, define an absolute threshold, emit masking
events, or claim audibility/inaudibility. Importing or evaluating other precomputed evidence does not
import NumPy or the masking runtime.

Sprint 5 descriptors are not independently adapted in the minimum scope; the exact Sprint 5
brightness correlate is available through Sprint 9 reference evidence.

## Operators, units, and states

Supported numeric operators are `GREATER_THAN`, `GREATER_THAN_OR_EQUAL`, `LESS_THAN`,
`LESS_THAN_OR_EQUAL`, `ABSOLUTE_GREATER_THAN`, and `ABSOLUTE_GREATER_THAN_OR_EQUAL`.
Boolean evidence supports only `BOOLEAN_IS_TRUE` and `BOOLEAN_IS_FALSE`.

Threshold and evidence must match exactly in unit basis, unit, named scale, and normalized flag. There
is no implicit conversion and booleans cannot be compared numerically. Absolute thresholds must be
non-negative.

Criterion evaluations use:

- `TRIGGERED`
- `NOT_TRIGGERED`
- `INSUFFICIENT_EVIDENCE`
- `CONFLICT`

Missing, skipped, unavailable, or insufficient evidence is never replaced by zero. If a criterion
does not specify identity and multiple distinct identities match, the evaluation is `CONFLICT`. If two
supplied values claim the same canonical source/dimension/identity but disagree, evaluation rejects
the evidence set instead of choosing one.

Only triggered evaluations create `MixIssue` objects. Non-triggered and insufficient outcomes remain
auditable through `MixCriterionEvaluation` and summary counts.

## Trigger and exceedance semantics

An issue means only that supplied evidence satisfies a supplied criterion. For triggered numeric
criteria, objective exceedance is retained in the same unit/scale:

- greater-than variants: `actual - threshold`
- less-than variants: `threshold - actual`
- absolute variants: `abs(actual) - threshold`

Equality produces zero exceedance for inclusive operators. Non-triggered evaluations have no issue
and therefore no exceedance. Boolean issues have no numeric exceedance. Exceedance is not normalized
and never determines priority.

## Priority and determinism

Priority is fixed by the criterion as `LOW`, `MEDIUM`, `HIGH`, or `CRITICAL`. It is policy metadata,
not psychoacoustic severity. Issues sort by:

1. declared priority, highest first;
2. optional policy rank, lowest integer first, with unranked issues after ranked issues;
3. criterion ID, lexicographically.

Issue IDs are the first 24 hexadecimal characters of SHA-256 over a separator-delimited exact policy
ID/version, criterion ID/version, and evidence identity, prefixed by `mix_issue.`. No random UUID or
issue text affects identity.

## Confidence and transport invariants

Confidence scores remain `None` with `UNKNOWN` basis. Evaluation is deterministic, but audibility,
perceptual importance, and severity are not validated.

Direct construction and `from_dict()` enforce:

- exact policy-to-criterion provenance and identity;
- unique criterion and issue IDs;
- source/dimension compatibility;
- issue criterion equality with the policy criterion;
- issue evidence equality with its triggered evaluation;
- exact threshold/evidence unit or scale;
- deterministic issue ID and issue ordering;
- policy-declared priority;
- exact objective exceedance arithmetic;
- evaluation coverage in policy order;
- summary counts equal evaluations and issues.

JSON is compact and contains no audio arrays, ERB matrices, embeddings, tensors, aggregate scores, or
recommendation fields.

## V1 migration decision

The V1 reference comparator, engineering engine, knowledge loader, and rule models were inspected.
They contain hard-coded tolerances and ranges, automatic severity mapping, normalized/category and
aggregate scores, fixed confidence values, generated adjustment text, genre/platform expectations,
and recommendations. Their scientific provenance is not transported.

Those numeric values and interpretations remain legacy behavior. Sprint 10 reuses only the structural
idea that explicit rules can produce typed findings; no V1 threshold, severity boundary, category
score, label, or recommendation is migrated as a V2 default.

## Validation fixtures

Analytical coverage includes the `+6.020599913 dB` half-gain reference example, non-triggering larger
thresholds, strict and inclusive equality, exact unit mismatch, true/false Sprint 7 booleans, raw
translation evidence, missing and skipped evidence, context conflict and ambiguity, declared masking
pair evidence, duplicate and conflicting identities, priority/rank ordering, deterministic IDs,
zero-issue results, JSON round-trip, forged issue/summary transport, repeatability, capability truth,
and lightweight imports. Evaluator performance is measured separately with 10, 100, and 1,000
criteria over one precomputed context result; no signal analysis occurs in that benchmark.

## Explicit non-claims and deferred boundary

- **ISSUE TRIGGERED != AUDIBLE DEFECT**
- **POLICY EXCEEDED != MIX FAILURE**
- **REFERENCE DEVIATION != QUALITY LOSS**
- **TRANSLATION RISK BOOLEAN != FAILURE PROBABILITY**
- **MASKING EVIDENCE != INAUDIBILITY**
- **PRIORITY != PSYCHOACOUSTIC SEVERITY**
- **MIX INTELLIGENCE != MIX QUALITY SCORE**
- **ISSUE != RECOMMENDATION**
- **PHASENOX V2 DOES NOT MODIFY AUDIO IN SPRINT 10**

There is no universal severity, subjective label inference, source attribution, recommendation text,
EQ/dynamics/stereo/mastering advice, LLM, RAG, model invocation, autonomous mixing, DAW control, or
audio export. Sprint 11 reasoning integration is not started by this foundation.
