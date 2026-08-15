# NOISYNE V2 Perceptual Reasoning Integration

## Scope and architecture

Sprint 11 adds a grounded explanation layer inside the existing NOISYNE V2 backend:

`MixIntelligenceResult -> fact extraction -> constrained provider selection -> grounding validator
-> canonical renderer -> PerceptualReasoningResult`

The Sprint 10 result, its exact policy and criteria, issue evidence, assumptions, limitations, and
evidence references remain authoritative. A provider can select approved statement templates and
fact IDs. It cannot supply accepted prose or change transported facts. NOISYNE validates every
selection and renders the final text deterministically.

Explicit boundaries:

- **LLM OUTPUT != SOURCE OF TRUTH**
- **VALID JSON != GROUNDED FACT**
- **GROUNDED EXPLANATION != PERCEPTUAL CERTAINTY**
- **ISSUE != AUDIBLE DEFECT**
- **PRIORITY != SEVERITY**
- **REVIEW SUGGESTION != DSP INSTRUCTION**
- **NOISYNE DOES NOT MODIFY AUDIO IN SPRINT 11**

## Research and safety boundary

The [NIST AI Risk Management Framework](https://airc.nist.gov/airmf-resources/airmf/) treats
trustworthiness as a lifecycle concern rather than a property established by one model response.
The [AI RMF Core](https://airc.nist.gov/airmf-resources/airmf/5-sec-core/) calls for documented
scope, human oversight, contextual interpretation, validation, and limitations on generalization.
The [AI RMF Playbook](https://airc.nist.gov/airmf-resources/playbook/) further recommends testing
explanations and documenting models, thresholds, evaluation, and oversight. The
[NIST Generative AI Profile](https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.600-1.pdf) identifies
confabulation as a generative-AI risk.

[JSON Schema](https://json-schema.org/specification) distinguishes structural/schema validation
from the meaning or truth of field values. Sprint 11 therefore uses two independent controls:

1. strict typed provider-response and public transport contracts;
2. deterministic validation against a machine-checkable fact whitelist.

Schema-valid content with unsupported facts is rejected. Prompting alone is not a grounding
control.

## V1 inspection and reuse decision

The V1 reasoning engine, models, parser, prompt builder, LM Studio client, provider adapters,
output guards, and RAG query/retrieval paths were inspected. V1 can request JSON, but it also accepts
free-form fallback text, transports model-generated recommendations, assigns numeric confidence,
records raw answers in reasoning diagnostics, and uses broad audio-engineering prompts. Its LM
Studio client is directly configured around an OpenAI-compatible endpoint and does not provide the
Sprint 11 fact/template grounding boundary. The V1 RAG path injects retrieved knowledge and query
rewriting, which is outside Sprint 11.

V1 remains unchanged. Sprint 11 reuses only structural lessons: provider abstraction, typed
responses, bounded failures, and deterministic formatting. It does not reuse V1 prompts, raw-text
fallback, recommendation generation, numeric confidence, endpoint assumptions, RAG, or memory.

## Public contracts

The lightweight public surface includes:

- `GroundingFactType` and `GroundingFact`
- `ReasoningStatementKind` and `ReasoningGroundingStatus`
- `ReasoningEvidenceReference` and `ReasoningStatement`
- `ReasoningProviderType`, `ReasoningProviderAvailability`, and `ReasoningProviderIdentity`
- `ReasoningRequest`
- `ProviderReasoningStatement` and `ProviderReasoningResponse`
- `PerceptualReasoningProvider`
- `PerceptualReasoningState`, `ReasoningErrorCode`, and `ReasoningError`
- `PerceptualReasoningSummary` and `PerceptualReasoningResult`

All public result statements have `GROUNDED` status. Rejected provider candidates contribute only
to counts and a bounded result state; unsupported text is never serialized as an accepted
statement.

## Deterministic fact whitelist

Each triggered Sprint 10 issue produces identified facts for:

- issue type and policy-supplied title;
- policy-declared priority;
- evidence identity, canonical evidence dimension, and exact `ScalarValue`;
- criterion identity, exact threshold, and operator;
- deterministic triggered state;
- exact exceedance when present;
- transported assumptions and limitations.

Result-level facts separately retain exact policy identity, all Sprint 10 summary counts, and the
source result's unscored/unknown confidence semantics. They are available to providers as data but
are not authorized by any Sprint 11 statement template.

Fact IDs use `fact.<issue_id>.<semantic-suffix>`. Assumption and limitation facts also include a
short content hash. Every fact retains `source_contract`, `source_identity`, `issue_id`, and
`criterion_id`. Provider-selected facts must exist exactly and must all belong to the selected
issue and criterion. Another issue's evidence cannot be borrowed.

Policy titles, descriptions, sources, assumptions, and limitations are data. They do not become
instructions and cannot authorize a template, fact, action, or final rendered phrase.

## Providers and structured output

`PerceptualReasoningProvider` exposes safe provider identity and one `generate(ReasoningRequest)`
operation. `ReasoningRequest` contains only policy identity, issue IDs, and typed allowed facts. It
contains no raw audio, arrays, embeddings, repository context, conversation history, prompt, API
key, header, or credential.

Provider responses may contain only:

- statement kind;
- approved template ID;
- whitelisted fact IDs;
- exact issue and criterion IDs;
- an optional text field that is deliberately rejected if present.

Thus free-form provider text is not accepted. A future model adapter may serialize the request as
clearly delimited data and request this schema, but it must still pass the same validator. A valid
JSON response alone is insufficient.

## Deterministic provider and optional local model

`DeterministicReasoningProvider` is the default and offline test oracle. For every triggered issue,
it selects, in order:

1. observation;
2. policy interpretation;
3. limitation;
4. review suggestion.

Sprint 11 does not implement a live LM Studio adapter. The existing V1 adapter remains unchanged.
The V2 provider protocol and structured-model identity make a future adapter possible without
binding public contracts to LM Studio. No model, endpoint, network, model download, or cloud key is
required by Sprint 11 or its tests.

## Grounding validation and canonical rendering

The validator requires:

- an allowed statement kind;
- an approved template for that kind and issue type;
- an existing issue and its exact criterion ID;
- only existing fact IDs;
- exact same-issue and same-criterion references;
- the exact fact-type set required by the template;
- absence of provider-authored text.

Unknown facts, unknown issues, cross-issue references, kind/template mismatches, changed threshold
or priority claims, free numeric claims, quality language, audibility claims, causal diagnoses, and
DSP instructions are rejected rather than repaired. This avoids pretending to be a general
natural-language theorem prover.

The renderer, not the provider, inserts values. Exact `ScalarValue` transport is preserved. Numeric
presentation uses two decimal places; observations show an explicit sign. For example,
`6.020599913279624 dB` renders as `+6.02 dB`, while a `3 dB` threshold renders as `3.00 dB`.
Boolean values render as `true` or `false`.

## Review suggestions

Review suggestions come from a closed deterministic registry keyed by neutral Sprint 10 issue type:

- reference deviation: review the declared reference relationship;
- translation policy: review the declared criterion and evidence;
- relative masking margin: review the declared masker-target relationship and criterion;
- context conflict: resolve conflicting or ambiguous declarations;
- level or spectral condition: review the declared criterion and evidence.

They contain no gain, frequency, ratio, ceiling, plugin, mastering, automation, or DAW instruction.
They do not diagnose causes or infer vocals, bass, drums, instruments, buses, or stems.

## Ordering and deterministic identity

The source issue order from Sprint 10 is authoritative. Within each issue, statements sort by
observation, policy interpretation, limitation, and review suggestion, then deterministic statement
ID. Statement IDs are SHA-256-derived from provider ID, issue ID, statement kind, template ID, and
sorted fact IDs. Request identity derives from exact policy/method identity and issue IDs. Random
UUIDs are not used.

## Confidence, errors, timeout, and cancellation

Confidence remains `score=None`, `basis=UNKNOWN`. Passing grounding checks does not imply 100%
confidence or perceptual certainty.

Structured states distinguish:

- `PROVIDER_UNAVAILABLE`
- `TIMEOUT`
- `INVALID_PROVIDER_RESPONSE`
- `GROUNDING_REJECTED`
- `NO_GROUNDED_STATEMENTS`

Errors contain fixed safe messages rather than raw exception strings. A provider declaring no
structured-output support is not called. `TimeoutError` maps to `TIMEOUT`; future live providers
must enforce their configured timeout. Sprint 11 makes no cancellation claim because its provider
protocol is synchronous and does not expose cancellation.

## Prompt injection, privacy, logging, and serialization

There is no Sprint 11 model prompt or live network adapter. Untrusted policy/reference metadata
remains typed fact data and is never rendered by templates that could turn it into an action.
Provider-authored free text is rejected even if it references valid facts.

Public JSON excludes prompts, hidden reasoning, chain-of-thought, raw audio, arrays, embeddings,
endpoint URLs, authorization headers, API keys, credentials, and rejected text. Sprint 11 emits no
provider prompt or metadata logs. Future operational logging is limited to safe provider/request
identity, duration, validation counts, and error category; full prompts and raw metadata remain
prohibited by default.

## Validation and explicit limitations

Fixtures cover reference energy, zero and multiple issues, context conflicts, translation policy,
relative masking margins, priority semantics, unknown/cross-issue facts, malformed responses,
timeouts, unavailable providers, empty responses, prompt injection strings, canonical numeric
rendering, deterministic IDs, forged transport, JSON round trips, capability truth, and lightweight
imports. Fake providers require no model or network.

Sprint 11 does not use RAG, memory, personalization, conversational history, chain-of-thought,
free-form accepted model text, causal diagnosis, source inference, aggregate scores, audibility or
quality claims, executable DSP, audio mutation, automation, DAW control, or model confidence.

Sprint 12 is not started. Any later orchestration must consume this bounded result without weakening
its fact, template, issue, criterion, privacy, or human-review boundaries.
