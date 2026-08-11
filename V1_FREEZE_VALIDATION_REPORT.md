# SoundBrain V1 Freeze — Final Validation Report

**Date:** 2026-08-10
**Baseline release SHA:** `a1946dd838d4918cac5d78f906719e62a9dbcc32`
**Wheel:** `dist/soundbrain-1.0.0-py3-none-any.whl` (215,780 bytes)
**Python:** 3.12.10 (win32)

---

## Executive Summary

All P0 freeze blockers and live P1 correctness issues were confirmed in the current working tree and fixed. Critical integration tests now execute against the committed fixture `tests/assets/test.wav` with **0 skipped**. The full test suite passes, CLI smoke tests pass in both the development and a clean Python 3.12 virtual environment, and the wheel installs normally without `--no-deps` and starts successfully. P3 RAG/Memory issues are documented as explicit V2-preflight blockers and were not fixed during this pass.

| Suite | Passed | Failed | Skipped |
|-------|--------|--------|---------|
| Full pytest suite | 232 | 0 | 0 |
| Targeted edge-case / CLI / integration subset | 33 | 0 | 0 |

---

## A. Findings Disposition

### P0 — Mandatory Freeze Blockers

| ID | Status | Root Cause | Fix | Regression Test |
|----|--------|------------|-----|-----------------|
| **P0.1 Tempo analysis crash** | CONFIRMED / FIXED | `librosa.beat.beat_track()` can return an `ndarray`; `float(tempo)` raised a crash under affected versions/configurations. | `brain/audio/analysis/tempo.py` now normalizes with `float(np.atleast_1d(tempo)[0])` and guards `0.0`. | `tests/test_audio_analysis_edge_cases.py` (real audio) |
| **P0.2 Critical integration tests skipping** | CONFIRMED / FIXED | Tests looked for `tests/audio.wav`; the committed fixture was at `tests/assets/test.wav`. | Standardized every test to `tests/assets/test.wav`; removed the untracked `tests/audio.wav`. | Full suite now shows 0 skipped; integration tests execute |
| **P0.3 Reference comparison crash** | CONFIRMED / FIXED | `ReferenceMetric` lacked `severity`; comparator read it, which would crash on a failed metric. | Added `severity: str` to `brain/reference/models.py` and populated it from `_severity()` in `brain/reference/comparator.py`. | `tests/test_reference_intelligence.py` |
| **P0.4 Wheel dependency resolution** | CONFIRMED / FIXED | `pymupdf`, `marker-pdf`, and `paddleocr` were mandatory, causing backtracking/heavy installs. | Moved PDF/OCR deps into `[project.optional-dependencies] pdf` in `pyproject.toml`; rebuilt wheel. | Clean venv `pip install dist/...whl` + `soundbrain --help` |

### P1 — Live High-Severity Correctness Issues

| ID | Status | Root Cause | Fix | Regression Test |
|----|--------|------------|-----|-----------------|
| **P1.1 Full mix as stem** | CONFIRMED / FIXED | Broad classification rule treated narrow mixes as stems, disabling master loudness validation. | `brain/audio/context/rules.py` now requires strong stem indicators (`onset_count < 40`, `centroid < 1200`, `stereo_width < 0.05` and defined). | `tests/test_audio_analysis_edge_cases.py` |
| **P1.2 Integer PCM clipping detection** | CONFIRMED / FIXED | Old check `analysis.peak > 1.0` missed float values at/near 0 dBFS that map from full-scale int16. | `brain/audio/engineer/rules.py` uses `CLIPPING_THRESHOLD = 0.99997` and checks `>=`; int16 normalization path handled by soundfile loader. | `tests/test_audio_analysis_edge_cases.py` (clipped float + int16) |
| **P1.3 Silence high score** | CONFIRMED / FIXED | Silent audio ran through normal scoring and could receive ~95/100. | Added `_is_silent()` guard in `RuleEngine.evaluate()`: RMS ≤ 1e-6 or non-finite LUFS → high-severity issue and score 5. | `tests/test_audio_analysis_edge_cases.py` |
| **P1.4 Very short audio crashes LUFS** | CONFIRMED / FIXED | BS.1770 needs ~0.4 s of audio; `pyloudnorm` raised `ValueError` on shorter inputs. | `brain/audio/analysis/lufs.py` catches `ValueError` and returns `NaN`; downstream rules handle `NaN`/`Inf` gracefully. | `tests/test_audio_analysis_edge_cases.py` (short audio) |
| **P1.5 Loud master → too quiet** | CONFIRMED / FIXED | Single `else` branch labeled every out-of-range loudness as generic "Loudness", giving wrong direction and advice. | Split into `lufs < -14.5` ("Loudness too quiet" → gain up + limiting) and else ("Loudness too loud" → gain down, no limiting). | `tests/test_audio_analysis_edge_cases.py` (too-loud / too-quiet masters) |
| **P1.6 Unsafe recommendation routing** | CONFIRMED / FIXED | `ProcessingChainRecommender._target()` used raw substring matches, e.g. "Dynamic range is limited" → Limiter because of "limit". | `brain/audio/mix/chains.py` now uses an exact title map plus whole-word matching. | `tests/test_plugin_chain_builder.py` |
| **P1.7 LLM JSON truncated before parsing** | CONFIRMED / FIXED | `OutputGuard` filtered the raw string before JSON parsing, corrupting valid JSON. | `brain/reasoning/engine.py` parses raw answer first, then filters each text field in the structured response; penalizes confidence on `finish_reason=length`. | `tests/test_soundbrain_service_reasoning.py` |
| **P1.8 Dimensionally invalid reference tolerances** | CONFIRMED / FIXED | One `DEFAULT_TOLERANCE = 1.0` was used for LUFS, Hz, BPM, normalized metrics, etc. | `brain/reference/comparator.py` defines `METRIC_TOLERANCES` per metric with units; category-specific scores replace copied global similarity. | `tests/test_reference_intelligence.py` |
| **P1.9 Reference CLI failure returns success** | CONFIRMED / FIXED | Exceptions were caught and printed without a non-zero exit; missing comparison also returned 0. | `main.py` returns `1` on any reference exception and again `1` when `response.comparison is None`. | `soundbrain reference <bad-path>` returns EXIT 1 |

### P2 — Required V1/UI Baseline Issues

All P2 items below were confirmed and fixed; the JSON report now exposes the measurements the Desktop UI needs.

| ID | Status | Summary |
|----|--------|---------|
| **P2.1 JSON report completeness** | FIXED | `brain/report/exporter.py` now includes the full `analysis` object with LUFS, peak, RMS, spectral, tempo, stereo width, phase, MFCC, chroma, onset_count, etc. |
| **P2.2 Dynamic range vs crest factor** | FIXED | `brain/audio/analysis/dynamic_range.py` implements block-based dynamic range; `crest_factor.py` remains the separate crest factor analyzer. |
| **P2.3 Mono stereo metrics** | FIXED | NaN/undefined stereo width and phase are treated as "not applicable" instead of fabricating values. |
| **P2.4 CLAP channel handling** | FIXED | `brain/audio/embeddings/clap.py` resamples to 48 kHz and mixes multi-channel to mono before encoding. |
| **P2.5 Key detection semantics** | FIXED | `brain/audio/analysis/key.py` uses Krumhansl-Kessler/Temperley major/minor profile correlation and returns a real key/mode string. |
| **P2.6 Plugin recommendation routing** | FIXED | See P1.6; taxonomy in `brain/audio/plugin/taxonomy.py` supports explicit categories. |
| **P2.7 Settings wiring** | FIXED | `brain/infrastructure/config/loader.py` loads `llm`, `audio`, `runtime`, and `models` from packaged YAML and passes temperature/top_p/max_tokens to the provider. |
| **P2.8 Reasoning prompt correctness** | FIXED | `brain/reasoning/formatter.py` labels peak as "linear", uses correct field names, and never drops values silently. |
| **P2.9 LLM generation settings** | FIXED | `settings.llm.temperature`, `top_p`, and `max_tokens` are now passed through `ReasoningEngine` to the provider. |
| **P2.10 Multi-reference aggregation** | FIXED | `brain/reference/service.py` selects the closest reference as the primary target and preserves per-reference similarity; no 100% match from averaging. |
| **P2.11 Category scores** | FIXED | `brain/reference/comparator.py` computes per-category scores from mapped metric similarities. |
| **P2.12 Report formatting integrity** | FIXED | `brain/report/exporter.py` uses atomic temp-file writes, `allow_nan=False`, and `_sanitize_floats()` for JSON safety. |

### P3 — V2 Preflight Findings (Deferred)

| Finding | Disposition | Code Location | Justification |
|---------|-------------|---------------|---------------|
| Duplicate vector IDs / stale `add()` | **Deferred to V2** | `brain/memory/vector/manager.py:27-39`, `brain/memory/vector/providers/chroma.py:38-45`, `brain/rag/builder.py:36,45-51`, `brain/rag/pipeline.py:29,35-41` | Fixing requires new idempotency/upsert strategy and a broader RAG redesign; not safe for a freeze pass. |
| CWD-relative persistence | **Deferred to V2** | `brain/memory/vector/config.py:7`, `brain/memory/vector/providers/chroma.py:16-17`, `brain/audio/catalog/database.py:7` | Correct fix is to resolve persistence against the stable application root; tied to V2 RAG persistence work. |
| `score = 1 - distance` under default squared-L2 | **Deferred to V2** | `brain/rag/retriever.py:25`, `brain/rag/vectordb.py:55-59` | Must switch to cosine-normalized embeddings or use Chroma's distance-to-score API; scope is V2 retrieval. |
| Re-ingestion duplicates corpus | **Deferred to V2** | `brain/rag/builder.py:10-58`, `brain/rag/pipeline.py:17-45` | Needs upsert/delete-by-source and content hashing; not V1 release-critical. |
| Redundant retrieve/rerank calls | **Deferred to V2** | `brain/services/rag_service.py:105-119` | Structural refactor of `RagService.ask()`; safe to defer. |
| Missing memory config → empty profile | **Deferred to V2** | `brain/memory/loader.py:53-83` | Empty-profile fallback is a known UX bug but not a freeze blocker for deterministic analysis. |

---

## B. Files Changed

### Core fixes

- `brain/audio/analysis/tempo.py`
- `brain/audio/analysis/lufs.py`
- `brain/audio/analysis/dynamic_range.py`
- `brain/audio/analysis/key.py`
- `brain/audio/context/rules.py`
- `brain/audio/engineer/rules.py`
- `brain/audio/embeddings/clap.py`
- `brain/audio/mix/chains.py`
- `brain/audio/plugin/taxonomy.py`

### Reference / reasoning / report

- `brain/reference/comparator.py`
- `brain/reference/models.py`
- `brain/reference/report_builder.py`
- `brain/reference/service.py`
- `brain/reasoning/engine.py`
- `brain/reasoning/formatter.py`
- `brain/reasoning/models.py`
- `brain/report/builder.py`
- `brain/report/exporter.py`
- `brain/report/models.py`
- `brain/report/validator.py`

### Config / packaging / CLI

- `brain/infrastructure/config/loader.py`
- `brain/infrastructure/config/models.py`
- `brain/infrastructure/config/resources/audio.yaml` (new, packaged)
- `brain/infrastructure/config/resources/models.yaml` (new, packaged)
- `brain/infrastructure/config/resources/runtime.yaml` (new, packaged)
- `brain/providers/qwen.py`
- `brain/llm/qwen.py`
- `brain/text/embeddings/bge.py`
- `brain/application/audio_review_service.py`
- `brain/cli.py` (new)
- `main.py`
- `pyproject.toml`
- `configs/models.yaml`
- `brain/runtime/capabilities.py`

### Tests / fixtures

- `tests/test_audio_analysis_edge_cases.py` (new)
- `tests/test_audio_pipeline.py`
- `tests/test_audio_review_service.py`
- `tests/test_plugin_chain_builder.py`
- `tests/test_reference_cli.py`
- `tests/test_reference_intelligence.py`
- `tests/test_soundbrain_service.py`
- `tests/test_soundbrain_service_integration.py`
- `tests/test_soundbrain_service_rag.py`
- `tests/test_soundbrain_service_reasoning.py`
- `tests/test_soundbrain_service_reference.py`
- `tests/test_soundbrain_service_semantic.py`
- `tests/assets/reference_eval/reference_eval_manifest.json`
- `tests/archive/*.py` — all archive fixture paths updated to `tests/assets/test.wav`

---

## C. Test Results

### Full suite

```text
$ ./venv/Scripts/python -m pytest -q --tb=short
232 passed in 40.54s
```

**Executed:** 232  
**Passed:** 232  
**Failed:** 0  
**Skipped:** 0

### Targeted regression subset

```text
$ ./venv/Scripts/python -m pytest -q --tb=short \
    tests/test_audio_analysis_edge_cases.py \
    tests/test_reference_cli.py \
    tests/test_soundbrain_service_integration.py \
    tests/test_audio_review_service.py
33 passed in 23.65s
```

### Critical integration groups (now actually executing)

- `tests/test_soundbrain_service_integration.py` — 4/4 passed
- `tests/test_soundbrain_service_reference.py` — 3/3 passed
- `tests/test_reference_cli.py` — passed (including deliberate failure exit-code test)
- `tests/test_audio_analysis_edge_cases.py` — covers silence, near-silence, very short audio, mono, stereo, int16 PCM, clipped audio, too-loud/too-quiet masters

---

## D. Runtime Smoke Tests

### Development venv

| Command | Result |
|---------|--------|
| `python main.py --help` | ✅ |
| `python main.py analyze tests/assets/test.wav --output reports/smoke_analyze.json` | ✅ |
| `python main.py reference tests/assets/test.wav tests/assets/test.wav --output reports/smoke_reference` | ✅ |
| `python main.py reference tests/assets/test.wav tests/assets/does_not_exist.wav --output reports/smoke_reference_fail` | ✅ EXIT 1 |

### Clean Python 3.12 venv (`venv/fresh_py312`)

| Command | Result |
|---------|--------|
| `pip install dist/soundbrain-1.0.0-py3-none-any.whl` | ✅ dependency resolution succeeded, no `--no-deps` |
| `soundbrain --help` | ✅ |
| `soundbrain analyze <absolute-path>/tests/assets/test.wav --output <absolute-path>/reports/fresh_analyze.json` | ✅ produced valid JSON |
| `soundbrain reference <absolute-path>/tests/assets/test.wav <absolute-path>/tests/assets/test.wav --output <absolute-path>/reports/fresh_reference.json` | ✅ produced reference reports |
| `soundbrain reference <good> <bad-path>` | ✅ EXIT 1 with error on stderr |

**Dependency-resolution result:** SUCCESS  
**Environmental storage limitation:** None observed; install completed from cache/download.

---

## E. Wheel Validation

- **Build command:** `python -m build --wheel` (or equivalent) produced `dist/soundbrain-1.0.0-py3-none-any.whl`.
- **Size:** 215,780 bytes.
- **Clean install:** succeeded without `--no-deps` into a fresh Python 3.12 venv.
- **CLI startup from wheel:** `soundbrain --help` works.
- **Real analysis from wheel:** works on `tests/assets/test.wav`.
- **No external `SOUNDBRAIN_ROOT` required** for startup.
- **Packaged resources:** YAML configs are included via `[tool.setuptools.package-data]`.

---

## F. Capability Truth Audit (Runtime Reality)

The canonical registry is `brain/runtime/capabilities.py`. A JSON dump of the freeze-audit state was written to `reports/capability_inventory.json`.

| Capability | Status | Runtime Reality | Tested in Freeze |
|------------|--------|-----------------|------------------|
| `audio_loading` | PRODUCTION | Works for WAV/FLAC/etc. via soundfile/librosa. | ✅ |
| `dsp_analysis` | PRODUCTION | Deterministic LUFS, peaks, spectrum, dynamics, stereo, tempo, key all wired and tested. | ✅ |
| `audio_context` | PRODUCTION | Full-mix vs stem classification now correct. | ✅ |
| `engineering_analysis` | PRODUCTION | Rule engine with silence/loudness/clipping/stereo guards. | ✅ |
| `clap_embedding` | VERIFIED | Works when the local CLAP model is present; model is **not** bundled. | ✅ |
| `reference_comparison` | PRODUCTION | Per-metric tolerances, category scores, non-zero CLI exit on failure. | ✅ |
| `rag_retrieval` | IMPLEMENTED | Chroma/BGE wired but has known V2-preflight correctness issues. | ✅ (empty-collection smoke) |
| `llm_reasoning` | IMPLEMENTED | Wired to OpenAI-compatible provider; default points to local LM Studio, no bundled LLM. | ✅ (fake-engine wiring) |
| `report_generation` | PRODUCTION | JSON export includes full `analysis`; formatting validated. | ✅ |
| `service_facade` | PRODUCTION | `SoundBrainService` entry point passes all integration tests. | ✅ |
| `engine_registry` | PRODUCTION | No external deps. | ✅ |
| `orchestration` | IMPLEMENTED | Available but not exercised by V1 CLI freeze path. | ❌ |
| `audio_intelligence` | PLANNED | CLAP semantic labels work, but broader audio intelligence is V2 scope. | ✅ |
| `mix_intelligence` | PRODUCTION | Root cause, priority, processing chain, explanations all tested. | ✅ |
| `plugin_intelligence` | PRODUCTION | Taxonomy and parameter generation tested. | ✅ |
| `memory_learning` | PLANNED | Not implemented; empty-profile fallback bug is a V2 blocker. | ❌ |
| `daw_integration` | PLANNED | No runtime DAW integration in V1. | ❌ |

---

## G. Remaining Known Limitations

1. **CLAP model not bundled.** Semantic analysis requires a local CLAP folder under the configured `model_root`; it will not work out-of-the-box from a clean install without downloading/providing the model.
2. **LLM provider external.** Reasoning requires an OpenAI-compatible endpoint (default LM Studio at `127.0.0.1:1234/v1`); no LLM is bundled.
3. **RAG retrieval not production-ready.** The empty-collection smoke test passes, but P3 items (duplicate IDs, CWD-relative persistence, distance-to-score conversion, re-ingestion duplication, redundant calls) are deferred to V2.
4. **Memory learning not implemented.** Missing memory config falls back to an empty profile; this is a known V2-preflight blocker.
5. **DAW integration not implemented.** It remains a planned V2 capability.

---

## H. Architecture / Public-Contract Changes

- **New console script:** `soundbrain = "brain.cli:main"` in `pyproject.toml`. The CLI is now the supported entry point.
- **Packaged configuration:** `brain/infrastructure/config/resources/*.yaml` are now the canonical config source; `SOUNDBRAIN_ROOT` is optional and CWD-independent.
- **Optional extras:** PDF/OCR ingestion moved to `soundbrain[pdf]`; core analysis does not require it.
- **JSON report contract:** The exported JSON now contains an `analysis` object with all deterministic measurements. Existing fields are preserved.
- **Reference metric contract:** `ReferenceMetric` now exposes `severity` and `unit`; category scores are real category-specific values.
- **Capability registry contract:** `Capability` gained optional fields (`requirements`, `dependencies`, `reason_unavailable`, `tested_in_freeze`) for the V1 freeze audit; existing callers are unaffected.

---

## Sign-Off

- All confirmed P0/P1 blockers are fixed and regression-tested.
- Critical integration tests execute (0 skipped).
- CLI smoke tests pass in both dev and clean venvs.
- Wheel builds, installs cleanly, and runs.
- No release-critical hidden issues remain.

**This working tree is ready to be committed as the V1 freeze baseline.**
