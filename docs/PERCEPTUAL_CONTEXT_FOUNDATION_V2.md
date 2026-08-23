# PHASENØX V2 Perceptual Context Foundation

Status: Sprint 8 implemented foundation. This is not a verification, production,
standard-conformance, recommendation, or intelligence claim.

## Scope and separation

Sprint 8 stores explicit listener, programme-intent, delivery, playback, and listening-condition
context; resolves literal agreement or conflict; and selects an already-authored Sprint 7
`TranslationRiskPolicy` through an explicit versioned binding. It is lightweight and deterministic.

The architecture keeps four categories separate:

1. Signal/perceptual evidence is produced by Sprint 2–7 measurement paths.
2. Context consists of caller-, project-, workflow-, reference-, or measurement-supplied facts and
   assumptions.
3. Policy consists of explicit criteria and thresholds.
4. Reasoning and recommendations are future work.

Context resolution never reads audio, calculates a metric, runs a playback transfer, changes signal
evidence, or invokes a model. Policy selection does not run the selected policy; a caller may later
pass that policy and appropriate Sprint 7 evidence to the unchanged `TranslationRiskEvaluator`.

## Standards reviewed and bounded use

- **ITU-R BS.1116-3 (02/2015), in force:** reviewed for the fact that rigorous subjective
  assessment explicitly controls programme material, reproduction devices, monitors/headphones,
  listening rooms and fields, listening levels, arrangements, and listener panels. PHASENØX does
  not implement its grading, listener selection, statistical procedure, reference level, or claim
  BS.1116 conformance.
- **EBU Tech 3276, 2nd edition (May 1998):** reviewed as critical-listening and control-room
  context for mono and two-channel stereo. Its room, reproduction, and listening-level conditions
  are not treated as universal home or consumer conditions, room correction, or playback
  simulation.
- **EBU Tech 3276 Supplement 1 (2004):** reviewed for the corresponding multichannel
  critical-listening context boundary. It supplies no automatic transfer or consumer default.
- **EBU R 022 (1999):** reviewed for its recommendation to use Tech 3276 conditions in critical
  operational/technical assessment. It supplies no consumer preference or engineering rule.
- **ITU-R BS.1534-3 (10/2015), MUSHRA, in force:** reviewed only for explicit listener, programme
  material, experimental, and listening-condition context and the boundary between objective
  code and subjective validation. PHASENØX implements no MUSHRA scores, anchors, hidden
  references, panels, or quality prediction.
- **ITU-R BS.1770-5 (11/2023):** reviewed only to distinguish an identified programme-loudness
  measurement specification from a free-text delivery label. Sprint 8 adds no loudness algorithm,
  threshold, or target.
- **EBU R 128 v5.0 (November 2023), EBU Tech 3341 v4.0 (November 2023), EBU Tech
  3342 v4.0 (November 2023), and EBU Tech 3343 v4.1 (November 2023):** reviewed only as
  explicitly identified broadcast/loudness workflows. Their operational values are not generalized
  into streaming or artistic mastering targets, and Sprint 8 implements none of their calculations.

These references justify treating listening, reproduction, programme, and delivery conditions as
explicit context variables. A reference claim preserves what the caller asserted; it does not prove
that a room, device, listener, workflow, or programme conforms.

## Sprint 1 compatibility

The frozen `PerceptualContext` class and `PERCEPTUAL_SCHEMA_VERSION = "1.0.0"` are unchanged.
Its fields remain declarations. `PerceptualContextResolver` adapts populated fields into adjacent
claims without changing their values. Its `assumptions` are copied to those generated claims.
Listener-preference order and exact spelling are preserved.

The default provenance for a directly supplied `PerceptualContext` is `USER_DECLARED`, with an
explicit source description. Callers may identify it as project- or workflow-declared. Using
reference-specification provenance requires a version. A frozen numeric listening-level field
cannot be relabelled as measured through this adapter because measured claims require dedicated
measurement metadata; callers must supply a typed claim instead.

## Public contracts

`ContextClaim` records a stable claim ID, dimension, typed literal value, provenance, source,
optional source version, optional listening-measurement metadata, assumptions, and limitations.
It deliberately has no inferred/predicted class. Its existing `Confidence` transport remains
unscored (`score=None`, `basis=UNKNOWN`) because Sprint 8 has no validated scoring method.

Supported dimensions are:

- genre, style, artistic intent, delivery target;
- playback expectation (`PlaybackProfileReference` only);
- qualitative listening level (`LOW`, `MODERATE`, or `HIGH`);
- numeric listening level in dB SPL;
- mono compatibility (`NOT_REQUIRED`, `PREFERRED`, or `REQUIRED`);
- listener use case and individual listener preferences.

The foundation does not add an ontology. Text is exact caller text. Genre and style are metadata,
not classes or engineering instructions. Artistic intent is descriptive and is never interpreted
numerically. Delivery target is a declaration, not a platform rule. Listener use case and
preferences are session/project declarations, not a psychoacoustic, demographic, health, or
behavioral profile.

`ContextResolutionResult` contains dimension results and their source claims. A dimension is
`RESOLVED` when all supplied claims have one exactly equal JSON literal and `CONFLICT` when two
or more distinct literals exist. Listener preference is the deliberate multi-valued exception:
distinct declared preferences remain an ordered resolved collection, while exact duplicates collapse
in the resolved value list and retain every source claim. An empty input is `INSUFFICIENT_EVIDENCE`.
The overall result is `CONFLICT` if any dimension conflicts. Equal declarations retain all
provenance-bearing claims. No source wins: Sprint 8 has **no precedence rule**.

## Listening conditions

Qualitative listening level and numeric dB SPL are different dimensions. Neither is inferred from
digital amplitude, LUFS, playback profile, a volume control, use case, or audio samples. A finite,
non-negative number may be explicitly declared as dB SPL without receiving a label such as safe,
loud, quiet, optimal, or reference.

`MEASURED_LISTENING_CONDITION` is permitted only for numeric dB SPL and requires a measurement
method/source description, weighting, time basis, acoustic reference/unit, and measurement
position/context. These fields identify the assertion; they do not establish calibration quality,
hearing exposure, safety duration, audibility, or medical meaning.

## Playback and mono context

A playback expectation reuses the frozen `PlaybackProfileReference`. It does not prove that a
Sprint 6 executable transfer exists. Policy selection does not load or synthesize a transfer.

Mono `REQUIRED`, `PREFERRED`, and `NOT_REQUIRED` are production/delivery expectations only.
Resolution performs no downmix and says nothing about whether the current mix passes a mono
check.

## Provenance

- `USER_DECLARED`: supplied explicitly by the caller/user.
- `PROJECT_DECLARED`: supplied by project or session metadata.
- `WORKFLOW_DECLARED`: supplied by a production/export workflow.
- `REFERENCE_SPECIFICATION`: tied to an identified source and mandatory version/edition.
- `MEASURED_LISTENING_CONDITION`: numeric dB SPL with mandatory measurement metadata.

Provenance does not imply accuracy or assign numeric confidence. No provenance class outranks
another. Confidence remains unscored because Sprint 8 has no justified scoring method.

## Exact context-policy binding

`ContextRequirement` supports only `EQUALS`, `PRESENT`, and `ABSENT`. Equality compares the
JSON-safe literal exactly. There is no lowercasing, aliasing, ontology normalization, fuzzy match,
regular expression, NLP, embedding, or semantic similarity.

`ContextPolicyBinding` identifies its own ID/version, one or more exact requirements, an exact
Sprint 7 policy ID/version, provenance/source, assumptions, and limitations. A reference-sourced
binding requires a source version. The binding contains no risk criterion and creates no threshold.

`ContextPolicySelector` behaves as follows:

- any resolved context conflict returns `CONFLICT` and selects nothing;
- zero matching bindings returns `NO_MATCH`; there is no universal fallback;
- multiple matching bindings return `AMBIGUOUS`; there is no hidden ranking;
- one matching binding whose exact policy ID/version is absent returns `UNRESOLVED`;
- one matching binding plus that exact supplied policy returns `SELECTED`.

The selected object is the existing `TranslationRiskPolicy` itself. Policy contents remain owned by
Sprint 7 and `TranslationRiskEvaluator` is unchanged. This is selection, not generation.

## Transport and determinism

All public contracts follow the repository's frozen, slotted dataclass and `JsonContract`
conventions. Transport is compact and JSON-safe. It contains no audio samples, spectral/ERB
arrays, embeddings, or runtime state. Exact enum decoding, finite numeric validation, stable
identities, and unknown-field rejection apply. Repeated resolution and selection over identical
ordered inputs produce identical results.

## Privacy and data minimization

Sprint 8 retains only declarations needed for the supplied project/session operation. It performs no
demographic or age inference, health inference, identity profiling, preference learning, behavioral
tracking, or persistent personalization. Long-term user memory belongs to a separately designed
later sprint.

## Explicit non-claims and boundaries

**GENRE LABEL != ENGINEERING TARGET**

**DELIVERY TARGET != MASTERING LOUDNESS TARGET**

**LISTENER PREFERENCE != PSYCHOACOUSTIC MODEL**

**LISTENING LEVEL DECLARATION != HEARING-SAFETY ASSESSMENT**

**REFERENCE SPECIFICATION != CONFORMANCE**

**PLAYBACK EXPECTATION != EXECUTABLE TRANSFER**

**ARTISTIC INTENT != NUMERICAL POLICY**

**CONTEXT != OBJECTIVE SIGNAL EVIDENCE**

**POLICY SELECTION != POLICY GENERATION**

Sprint 8 is not a genre classifier, listener-preference predictor, mastering-target recommender,
platform policy database, hearing-health model, room/headphone correction engine, DSP path, audio
metric engine, ML model, LLM/RAG feature, or persistent personalization system. It does not scrape
platforms or contain platform constants or genre stereotypes.

Sprint 9 reference-track similarity, ranking, embeddings, genre inference, and reference
recommendations are not implemented. Sprint 11 reasoning and Sprint 13 memory/personalization are
also outside this foundation.

## Authoritative references

- [ITU-R BS.1116-3 (02/2015)](https://www.itu.int/rec/R-REC-BS.1116-3-201502-I/en)
- [EBU Tech 3276 (May 1998)](https://tech.ebu.ch/publications/tech3276)
- [EBU Tech 3276 Supplement 1 (2004)](https://tech.ebu.ch/docs/tech/tech3276s1.pdf)
- [EBU R 022 (1999)](https://tech.ebu.ch/publications/r022)
- [ITU-R BS.1534-3 (10/2015)](https://www.itu.int/rec/R-REC-BS.1534-3-201510-I/en)
- [ITU-R BS.1770-5 (11/2023)](https://www.itu.int/rec/R-REC-BS.1770-5-202311-I/en)
- [EBU loudness publications, including R 128 v5.0 and Tech 3341–3343](https://tech.ebu.ch/loudness/)
