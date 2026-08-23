# PHASENØX V2 — Knowledge / Memory / Personalization Foundation

## Sprint 13

**Date:** 2026-08-17  
**Branch:** `v2-development`  
**Schema Version:** `1.0.0`

---

## 1. Purpose

Sprint 13 establishes the **knowledge / memory / personalization foundation** for PHASENØX V2.

It is **not** an autonomous learning system.  It is **not** a source of scientific truth.  It provides deterministic, provenance-preserving contracts and storage abstractions that future reasoning and product personalization can consume without contaminating Sprint 12 validation truth.

Core principle:

> **SCIENTIFIC FACT ≠ RETRIEVED KNOWLEDGE ≠ PROJECT HISTORY ≠ USER PREFERENCE ≠ MODEL OUTPUT**

These categories remain distinct in contracts, storage, retrieval, and reasoning transport.

---

## 2. Architecture

```
PHASENØX V2 backend
│
├── Sprint 12 perceptual validation truth  (authoritative, immutable)
│
├── Sprint 13 Knowledge / Memory layer
│   ├── MemoryItem contract (identity, type, provenance, scope, trust basis)
│   ├── Storage abstraction (MemoryStore protocol)
│   ├── In-memory deterministic backend (Sprint 13 test/local use)
│   ├── Retrieval contract (KnowledgeQuery / KnowledgeRetrievalResult)
│   ├── User preference model
│   ├── Project history model
│   └── Reference memory model
│
└── Future reasoning consumer
    ├── validated scientific facts  (Sprint 10/11)
    ├── retrieved knowledge         (labeled, not verified)
    ├── user preferences            (labeled, reversible)
    └── project history           (labeled, not current evidence)
```

Memory never overrides the Sprint 12 validation matrix, Sprint 10 source-bound evidence, or Sprint 11 source-truth reasoning facts.

---

## 3. Taxonomy

### 3.1 Knowledge / Memory Type

| Type | Meaning |
|------|---------|
| `SCIENTIFIC_REFERENCE` | Peer-reviewed standards, validated models, or Sprint 12 evidence linked by validation ID. |
| `VERIFIED_PROJECT_KNOWLEDGE` | Project facts verified against deterministic fixtures or explicit project policy. |
| `RETRIEVED_KNOWLEDGE` | Items returned by a retrieval backend; trust is explicitly declared, not assumed. |
| `PROJECT_HISTORY` | Structured events about actions taken in a project. |
| `USER_PREFERENCE` | Explicit, reversible user setting/declaration. |
| `USER_DECLARATION` | One-off user statement that is not a persistent preference. |
| `SYSTEM_OBSERVATION` | Deterministic observation produced by the system. |
| `MODEL_GENERATED_CONTENT` | Output from a model/provider; always unverified in Sprint 13. |

### 3.2 Memory Scope

| Scope | Meaning |
|-------|---------|
| `GLOBAL_USER` | Follows the user across projects (e.g. export defaults). |
| `PROJECT` | Belongs to one project only. |
| `SESSION` | Ephemeral / current-work memory. |
| `REFERENCE_LIBRARY` | Shared reference identities and metadata. |

Rules:

- Project-local data does **not** leak into `GLOBAL_USER` automatically.
- `SESSION` data does **not** promote to persistent memory without explicit policy.

### 3.3 Provenance Kind

| Provenance | Meaning |
|------------|---------|
| `USER_ENTERED` | Typed or imported by the user. |
| `SYSTEM_OBSERVED` | Produced by deterministic system observation. |
| `IMPORTED` | Imported from an external file/corpus. |
| `RETRIEVED` | Returned by a retrieval backend. |
| `DERIVED` | Computed from other memory items (source IDs recorded). |
| `MODEL_GENERATED` | Produced by a model/provider. |

### 3.4 Trust Basis

| Basis | Meaning |
|-------|---------|
| `VALIDATED` | Sprint 12 scientific validation link present.  Only allowed for `SCIENTIFIC_REFERENCE`. |
| `VERIFIED` | Verified against deterministic fixtures or explicit project policy. |
| `DECLARED` | Explicitly declared by user or system; no independent verification. |
| `RETRIEVED` | Provided by retrieval backend; score semantics must be explicit. |
| `UNVERIFIED` | Model-generated or otherwise untrusted content. |

---

## 4. Truth / Trust Boundary

Sprint 13 memory **must not** override:

- Sprint 12 validation status or claim matrix.
- Sprint 10 source-bound evidence.
- Sprint 11 source-truth reasoning facts.
- Explicit capability truth.

### Allowed examples

- "User prefers brighter masters."
- "User usually exports at -9 LUFS target."
- "Previous project used Reference X."
- "Retrieved document Y section Z suggests technique W."

### Prohibited examples

- "Brighter masters are objectively better."
- "-9 LUFS is scientifically optimal."
- "Reference X proves the current mix is correct."
- "Retrieval score 0.9 means the claim is true."

---

## 5. Storage Abstraction

`MemoryStore` is a backend-neutral protocol:

- `put(item) -> MemoryItem`
- `get(memory_id) -> MemoryItem | None`
- `search(query) -> KnowledgeRetrievalResult`
- `list(scope=..., project_id=..., user_id=...) -> tuple[MemoryItem, ...]`
- `delete(memory_id) -> bool`
- `clear_scope(scope, project_id=..., user_id=...) -> int`

Sprint 13 provides `InMemoryMemoryStore`, a deterministic local backend for tests and lightweight local use.  It does **not** require ChromaDB or any vector database.

Future persistent backends can implement `MemoryStore` without changing consumers.

---

## 6. Retrieval Contract

`KnowledgeQuery` and `KnowledgeRetrievalResult` provide a deterministic, provider-agnostic retrieval contract.

- `KnowledgeQuery` carries explicit `provider_identity`, `query_id`, and deterministic filters.
- `RetrievedKnowledgeItem` carries the source `MemoryItem`, rank, and an optional `retrieval_score`.
- If `retrieval_score` is present, `score_semantics` is **required** and must describe what the score means.
- `retrieval_score` is provider-specific; Sprint 13 does **not** impose a universal normalized scale such as `[0, 1]`.
- Retrieval score is **not** confidence, truth, probability, or a percentage.
- Scores from different providers must not be compared unless their `score_semantics` are explicitly compatible.

Sprint 13 retrieval is deterministic filtering/sorting only.  Vector similarity search is deferred.

---

## 7. User Preference Model

`UserPreferenceItem` captures explicit, reversible user preferences:

- Preferred analysis mode.
- Preferred reference workflow.
- Genre/style declaration.
- Playback targets.
- Export preferences.
- UI/display preferences.
- Optional mix-review tendencies.

Rules:

- Preferences are explicit and reversible by default.
- No arbitrary psychological profiling.
- No inference of sensitive personal attributes.
- A user preference is **never** scientific validation.

---

## 8. Project History Model

`ProjectHistoryEvent` records structured project events:

- Analysis performed.
- Reference selected.
- Policy used.
- Reasoning result generated.
- User accepted/dismissed finding.
- Export created.

History is append-oriented with deterministic ordering.  It does not duplicate full analysis payloads when stable references/IDs are sufficient.

---

## 9. Reference Memory Model

`ReferenceMemoryItem` tracks safe reference metadata:

- Reference identity.
- Source path/identity.
- Comparison mode.
- Prior project associations.
- User annotations.
- Tags.

Rules:

- Historical similarity is **not** a universal quality score.
- No "best reference" inference without explicit policy.

---

## 10. RAG Integration Boundary

Sprint 13 establishes a safe boundary around retrieval:

RAG may:
- Retrieve relevant documents, notes, or project history.
- Supply explicitly labeled context.

RAG must not:
- Become source of scientific truth automatically.
- Override the Sprint 12 validation matrix.
- Alter Sprint 10 evidence.
- Fabricate grounding facts.
- Bypass Sprint 11 source-truth validation.
- Create final scientific claims without provenance.

Existing RAG infrastructure (`phasenox/rag/`) is **not** rewritten.  Sprint 13 contracts provide a clean integration surface for future safe consumption.

---

## 11. Reasoning Integration Boundary

Future reasoning may consume:

- Validated scientific facts (Sprint 10/11).
- Retrieved knowledge (labeled `RETRIEVED_KNOWLEDGE`).
- User preferences (labeled `USER_PREFERENCE`).
- Project history (labeled `PROJECT_HISTORY`).

Every consumed item must keep its category label.  Memory does **not** become a `GroundingFact` unless it satisfies the existing Sprint 11 source-truth rules.

---

## 12. Deletion / Forget Semantics

Memory supports explicit deletion:

- Delete one item by `memory_id`.
- Clear all items in a scope, optionally filtered by `project_id` or `user_id`.

Deletion removes the record.  It does **not** soft-delete while pretending to forget.  It does **not** delete user files, models, or audio.

---

## 13. Staleness / Versioning

Memory items support explicit staleness/version semantics:

- `schema_version` for contract schema.
- `created_at` / `updated_at` ISO timestamps.
- `expiration` optional ISO timestamp.
- `superseded_by` optional link to a newer memory ID.

Stale or superseded memory must not be used as current authoritative scientific truth.

---

## 14. Model-Generated Memory

Model-generated content is stored only with:

- `memory_type = MODEL_GENERATED_CONTENT`.
- `provenance = MODEL_GENERATED`.
- `trust_basis = UNVERIFIED`.
- Provider/model identity where available.
- Source context IDs where available.

Sprint 13 does **not** implement a live model.  These are contract/policy rules only.

---

## 15. Personalization Policy

`PersonalizationPolicy` defines allowed and prohibited effects.

Allowed effects:
- `PRESENTATION` — ordering, display.
- `DEFAULTS` — suggested defaults.
- `WORKFLOW_FOCUS` — suggested review focus.

Prohibited effects (always enforced):
- `scientific_evidence` — personalization must never modify scientific evidence, validation status, source-bound facts, criterion arithmetic, or hide contradictory evidence.

User consent is required by default.

---

## 16. Files Added

- `phasenox/perception/knowledge_contracts.py` — Sprint 13 public contracts.
- `phasenox/perception/knowledge_store.py` — `MemoryStore` protocol and `InMemoryMemoryStore` backend.
- `tests/test_sprint13_knowledge_memory.py` — Sprint 13 focused tests.
- `docs/KNOWLEDGE_MEMORY_PERSONALIZATION_V2.md` — This document.

### Modified files

- `phasenox/perception/__init__.py` — exports new Sprint 13 contracts and fills in missing Sprint 12 exports.
- `phasenox/perception/validation_matrix.py` — adds Sprint 13 claim-matrix records.
- `phasenox/runtime/capabilities.py` — registers new Sprint 13 capabilities.

No frozen Sprint 0–12 runtime logic was modified.

---

## 17. Explicit Non-Claims

| Non-Claim | Meaning |
|-----------|---------|
| `MEMORY != SCIENTIFIC TRUTH` | Stored items are not automatically true. |
| `USER PREFERENCE != OBJECTIVE QUALITY` | Preferences are subjective. |
| `RETRIEVAL SCORE != CONFIDENCE` | A similarity score is not a confidence or truth claim. |
| `RAG CONTEXT != VERIFIED FACT` | Retrieved context must be separately verified. |
| `MODEL OUTPUT != VERIFIED KNOWLEDGE` | Model output is unverified unless independently validated. |
| `PROJECT HISTORY != CURRENT EVIDENCE` | Past events do not prove current state. |
| `PERSONALIZATION != SCIENTIFIC VALIDATION` | Personalization cannot validate a method. |

---

## 18. What Remains Deferred

- Persistent backend integration (ChromaDB, SQL, etc.) behind `MemoryStore`.
- Vector similarity retrieval.
- Live model integration for model-generated memory.
- Runtime application of personalization to analysis workflows.
- Desktop UI integration (knowledge page, settings, task center, model manager).
- Long-term learning loop (`memory_learning` capability remains `PLANNED`).
- Automated ingestion of external knowledge corpora beyond existing RAG scope.
