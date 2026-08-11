# SoundBrain V2 RAG/Memory Preflight Stabilization Report

**Branch:** `v2-development`  
**Baseline:** `04b896f151e17e9d4cf35b31afc4e68a254e0306`  
**Date:** 2026-08-11

---

## Executive Summary

All six deferred P3 RAG/Memory findings were confirmed in the `v2-development` working tree and fixed in a narrowly scoped preflight pass. The fixes preserve the approved V1 deterministic audio-analysis pipeline and only touch RAG/Memory infrastructure. The full test suite passes, including new regression tests for idempotent ingestion, cosine distance scoring, CWD-independent persistence, and structured memory-configuration failures.

| Suite | Passed | Failed | Skipped |
|-------|--------|--------|---------|
| Full pytest suite | 281 | 0 | 0 |
| Targeted RAG/Memory preflight tests | 19 | 0 | 0 |

A deterministic ingest → retrieve → re-ingest → retrieve cycle was run against a real temporary Chroma collection and confirmed that no duplicate documents are created, stale chunks are replaced, and retrieval ordering is preserved under the cosine-distance metric.

---

## Findings Disposition

| # | Original Deferred Finding | Status | Root Cause | Fix |
|---|---------------------------|--------|------------|-----|
| 1 | **Duplicate vector IDs / stale Chroma `add()`** | **FIXED** | `VectorManager.add()` forwarded records to `collection.add()`. Chroma `add()` either fails or silently no-ops on duplicate ids depending on the version, and never updates stale vectors. | `VectorManager.add()` now uses `ChromaProvider.upsert()` so repeated adds of the same id update the existing record. `ChromaProvider` exposes an `upsert()` method. |
| 2 | **CWD-relative persistence paths** | **FIXED** | `brain/memory/vector/config.py` used `PERSIST_DIRECTORY = "data/vector_db"`; `brain/audio/catalog/database.py` used `Path("data/index.db")`; `MemoryLoader` default root was `"configs/memory"`. All were relative to the process CWD. | Added exported `get_application_root()` to `brain.infrastructure.config`. All persistence paths now resolve against the stable application root (package root / `SOUNDBRAIN_ROOT` env). |
| 3 | **Invalid `score = 1 - distance` semantics** | **FIXED** | `brain/rag/retriever.py` blindly computed `1 - distance`, assuming cosine. The default Chroma collection was created without `hnsw:space`, which defaults to squared-L2. | New `brain/rag/scoring.py::score_from_distance()` validates the configured metric. The shared Chroma collection is now created with `metadata={"hnsw:space": "cosine"}` and normalized embeddings. |
| 4 | **Re-ingestion duplicates corpus** | **FIXED** | `brain/rag/builder.py` and `pipeline.py` minted fresh `uuid4` ids on every run and used `collection.add()`, appending duplicates and never removing stale chunks. | New `brain/rag/ingestion.py::ingest_chunks()` groups chunks by source, deletes existing chunks for each source, and upserts new chunks with deterministic per-source ids derived from `sha256(source):source_index`. Both builder and pipeline now use `ingest_chunks()`. |
| 5 | **Redundant retrieve/rerank execution** | **FIXED** | `RAGService.ask()` called `self.search()` then `self.build_context()`, which internally called `self.search()` again. | `build_context()` now accepts an optional `results` argument; `ask()` passes the results from the single `search()` call to `build_context()`. |
| 6 | **Missing memory config → empty profile** | **FIXED** | `MemoryLoader._load_section()` returned `{}` when a referenced section file did not exist, silently converting a missing required config into a valid empty profile. | New `brain/memory/errors.py::MemoryConfigurationError` provides a structured failure state. Missing files, invalid YAML, and non-mapping bundles now raise `MemoryConfigurationError` with `reason="missing"` or `"invalid"`. Inline `{}` sections remain valid intentionally empty profiles. |

---

## Files Changed

### Core RAG/Memory fixes

- `brain/infrastructure/config/loader.py` — exported `get_application_root()`
- `brain/infrastructure/config/__init__.py` — re-exported `get_application_root`
- `brain/memory/vector/config.py` — absolute `PERSIST_DIRECTORY`
- `brain/memory/vector/manager.py` — use `upsert` instead of raw `add`
- `brain/memory/vector/providers/chroma.py` — added `upsert()`
- `brain/audio/catalog/database.py` — absolute `DATABASE_PATH`
- `brain/memory/loader.py` — structured errors, absolute root resolution
- `brain/memory/errors.py` — new structured `MemoryConfigurationError`
- `brain/rag/vectordb.py` — absolute Chroma path, cosine distance metadata
- `brain/rag/retriever.py` — use `score_from_distance()`
- `brain/rag/scoring.py` — new metric-aware distance-to-score helper
- `brain/rag/ingestion.py` — new idempotent source-scoped ingestion helper
- `brain/rag/builder.py` — use `ingest_chunks()`
- `brain/rag/pipeline.py` — use `ingest_chunks()`
- `brain/services/rag_service.py` — pass search results to `build_context()`

### Regression tests

- `tests/test_rag_preflight.py`
- `tests/test_memory_preflight.py`
- `tests/test_vector_preflight.py`

---

## Public Contract / Schema Changes

| Change | Migration Impact |
|--------|------------------|
| `brain.infrastructure.config.get_application_root()` is now public. | New API; no existing callers affected. |
| `ReferenceMetric` gained `similarity: float = 0.0` in prior follow-up commit; not part of this pass. | N/A for this pass. |
| `VectorManager.add()` semantics changed from insert-only to upsert. | Consumers relying on duplicate-id errors must now handle updates; no V1 consumer does. |
| `brain/memory/errors.MemoryConfigurationError` raised instead of `FileNotFoundError`/`TypeError` for memory config problems. | UI and CLI can now catch `MemoryConfigurationError` and present structured messages; old broad `FileNotFoundError` catches will still catch it because it subclasses `Exception` but not `OSError`. |
| `RAGService.build_context(query, *, results=None)` signature changed (keyword-only optional arg). | Backward-compatible for positional callers. |
| `brain.rag.builder.build_database` no longer prints the misleading "CLEARING DATABASE" banner; it now idempotently ingests. | Behavior improved; any scripts parsing the old banner will need minor adjustment. |

---

## Test Results

### Full suite

```text
$ ./venv/Scripts/python -m pytest -q --tb=short
281 passed in 51.50s
```

**Passed:** 281  
**Failed:** 0  
**Skipped:** 0

### Targeted RAG/Memory preflight tests

```text
$ ./venv/Scripts/python -m pytest -q --tb=short tests/test_rag_preflight.py tests/test_memory_preflight.py tests/test_vector_preflight.py
19 passed in 3.39s
```

**Passed:** 19  
**Failed:** 0  
**Skipped:** 0

---

## Deterministic Ingest/Retrieve/Re-ingest Cycle

Ran a manual real-Chroma cycle with a temporary `hnsw:space=cosine` collection:

1. Ingest source `s1` (2 chunks) and `s2` (1 chunk) → 3 documents.
2. Re-ingest `s1` with 1 updated chunk, keep `s2`, add `s3` → still 3 documents.
3. Verified `s1`, `s2`, `s3` each have exactly 1 chunk; stale `s1`/`s2` chunks were removed.
4. Queried `alpha` → top result was `alpha updated` with distance `0.0`.
5. Scores stayed bounded in `[0.0, 1.0]` and results were ordered highest-first.

Result: **CYCLE OK**

---

## Known Limitations Remaining

- Existing collections created before this fix may still use `l2` distance. New collections will use `cosine`. A future migration may drop/recreate old collections if strict cosine semantics are required.
- The RAG builder still only supports PDF sources via `load_documents()`. That is outside the preflight scope.
- Memory loader now raises structured errors, but does not yet fall back to a default bundle for missing configs. Callers must handle `MemoryConfigurationError`.

---

## Sign-Off

- All six deferred RAG/Memory findings are fixed and regression-tested.
- V1 deterministic audio behavior is preserved (full suite passes, no V1 contracts broken).
- No Desktop UI code was modified.
- No broader V2 roadmap features were started.

**Ready for local commit.**
