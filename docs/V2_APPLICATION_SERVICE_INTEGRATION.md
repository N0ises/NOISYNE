# NØISYNE V2 — Application Service Integration Foundation

Sprint 15 introduces the first public V2 application/service integration layer.
It does **not** add new perception science, new DSP, a live LLM, RAG, memory
reasoning, scheduling, UI, or installers. It wraps frozen Sprint 2–14 components
behind a deterministic, JSON-safe request/result contract.

---

## 1. Purpose

`PhasenoxV2Service` exposes a single entry point for V2 workflows:

- `ANALYZE` — load audio and run the auditory frontend + descriptor foundation.
- `REFERENCE_COMPARE` — compare source and reference audio using Sprint 9
  reference intelligence.
- `MIX_EVALUATE` — evaluate a `MixIssuePolicy` against supplied evidence using
  Sprint 10 mix intelligence.
- `REASON` — run deterministic grounded reasoning over a Sprint 10 mix result
  using Sprint 11 reasoning.
- `CAPABILITY_INSPECT` — report capability lifecycle state and machine-level
  dependency availability.

---

## 2. Architecture

```
Desktop / CLI / future adapter
      |
      v
PhasenoxV2Service
      |
      +-- ANALYZE --------------> AudioIOService + AuditoryFrontend + PerceptualDescriptorFoundation
      +-- REFERENCE_COMPARE ------> ObjectiveReferenceComparator
      +-- MIX_EVALUATE -----------> PerceptualMixIntelligenceEngine
      +-- REASON -----------------> PerceptualMixIntelligenceEngine + PerceptualReasoningEngine
      +-- CAPABILITY_INSPECT -----> CapabilityRegistry + optional import checks
```

All heavy modules are imported lazily inside methods. Importing
`noisyne.application` does not initialize torch, ONNX sessions, LLM clients,
network connections, Qt, or audio devices.

---

## 3. Public contracts

Contracts live in `noisyne.application.contracts`:

| Contract | Purpose |
|----------|---------|
| `ApplicationRequest` | Operation + parameters + deterministic request ID. |
| `ApplicationResult` | Status + payload + stages + bounded errors + limitations. |
| `ApplicationError` | Stable error code + message; no stack traces or secrets. |
| `StageOutcome` | Per-stage completion state with optional payload. |
| `CapabilitySnapshotEntry` | One capability with lifecycle and machine availability. |
| `CapabilitySnapshotResult` | Aggregated capability snapshot. |
| `OperationType`, `ApplicationResultStatus`, `StageState`, `MachineAvailability` | Bounded enums. |

Nested domain payloads are `dict[str, Any] | None` so that the service layer
remains independent of V2 contract versioning while remaining JSON-safe.

---

## 4. Operations

### 4.1 ANALYZE

Required parameters:

- `audio_path`: path to the audio file

Stages:

- `audio_io`
- `auditory_frontend`
- `descriptor_foundation`

Returns:

- `audio_metadata`
- `auditory_summary`
- `descriptors`

Does not run reasoning, reference comparison, or mix intelligence.

### 4.2 REFERENCE_COMPARE

Required parameters:

- `audio_path`: source audio path
- `reference_path`: reference audio path
- `reference_identity`: serialized `ReferenceTrackIdentity`
- optional `config`: serialized `ReferenceComparisonConfig`

Stages:

- `audio_io`
- `reference_identity_rehydration`
- `reference_compare`

Returns `comparison` evidence.

### 4.3 MIX_EVALUATE

Required parameters:

- `mix_policy`: serialized `MixIssuePolicy`
- optional `evidence`: list of evidence wrappers

Evidence wrapper format:

```json
{"contract_type": "reference_evidence", "data": {...}}
{"contract_type": "translation_evidence", "data": {...}}
```

Stages:

- `policy_rehydration`
- optional `evidence_rehydration`
- `mix_evaluate`

Returns the full `MixIntelligenceResult`. Insufficient evidence is a valid,
truthful result, not a failure.

### 4.4 REASON

Required parameters:

- `mix_policy`: serialized `MixIssuePolicy`
- optional `evidence`

Stages:

- `policy_rehydration`
- optional `evidence_rehydration`
- `mix_evaluate`
- `reasoning`

Maps deterministic reasoning states to application status:

- `COMPLETED` -> `SUCCESS`
- `NO_GROUNDED_STATEMENTS` -> `SUCCESS` with limitation
- any other non-completion state -> `PARTIAL` with bounded `REASONING_FAILURE`
- exceptions -> `FAILED`

Source-truth digests and grounding fact identities are preserved unchanged.

### 4.5 CAPABILITY_INSPECT

No required parameters.

Returns a snapshot of every registered capability:

- lifecycle status
- `tested_in_freeze`
- machine-level dependency availability
- `reason_unavailable`

Dependency availability rules:

- package dependency present -> `AVAILABLE` (import-level only)
- package dependency missing -> `UNAVAILABLE`
- non-package/model dependency -> `UNKNOWN`
- no dependencies -> `AVAILABLE`

Availability is **not** model, hardware, or runtime compatibility attestation.

---

## 5. Error semantics

All public errors are `ApplicationError` instances:

- bounded `code` string
- human-readable `message`
- optional `stage_id`

No stack traces, credentials, endpoint URLs, prompts, secrets, or chain-of-thought
are serialized. Internal exceptions are logged server-side at debug level.

Result status mapping:

| Situation | Status |
|-----------|--------|
| All stages succeed | `SUCCESS` |
| Non-fatal bounded problem (e.g. reasoning non-completion) | `PARTIAL` |
| Validation or capability problem | `FAILED` |
| Unhandled exception | `FAILED` |

---

## 6. V1 separation

The canonical V1 `PhasenoxService` export and compatibility aliases
(`NoisyneService`, `SoundBrainService`, `AnalysisRequest`, `AnalysisResponse`)
remain available through `noisyne.application.__getattr__`
but are not imported by default. New V2 code should use `PhasenoxV2Service` and
the Sprint 15 contracts.

Sprint 15 does not migrate `V2ApplicationAdapter` or any Desktop UI code.

---

## 7. Memory / knowledge boundary

Sprint 15 does not consume Sprint 13 memory or RAG. The service layer keeps
memory/knowledge separate from scientific truth:

- `ANALYZE`, `REFERENCE_COMPARE`, `MIX_EVALUATE`, and `REASON` use only
  validated Sprint 10 evidence and Sprint 11 source-truth binding.
- `CAPABILITY_INSPECT` reports validation status from the capability registry;
  it does not promote memory, preference, or history into scientific evidence.

---

## 8. Runtime / ONNX boundary

Sprint 15 does not change Sprint 14 runtime selection. `CAPABILITY_INSPECT`
treats `onnx_runtime_optimization` as an implemented foundation only. Its
dependency availability reflects whether `onnxruntime` can be imported, not
whether a production ONNX model is validated or faster.

---

## 9. Explicit non-goals

Sprint 15 does **not** implement:

- async scheduler
- Task Center
- pause/resume
- cancellation
- multi-tasking
- Desktop UI / V2ApplicationAdapter migration
- resource monitor UI
- model downloader
- installer / path manager
- Ableton bridge
- C++ integration
- Voice AI
- generation
- live LM Studio / Qwen
- memory-driven reasoning
- autonomous agent behavior

---

## 10. Handoff to future sprints

- Sprint 15.5: memory-aware reasoning boundary, retrieval context integration,
  preference influence.
- Sprint 16: async job scheduling, pause/resume, resource profiles, runtime
  selection at the service layer.
