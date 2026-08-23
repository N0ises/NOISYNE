# PHASENOX R6 Legacy Identity Audit

Status: discovery and classification only

Audit baseline: `v2-development` at `c01bab6c5eac00a5d12296eb07dd87199da9c0b7`

Scope: tracked text in production, tests, documentation, packaging, scripts, and tools; pre-existing untracked desktop-roadmap files were inventoried separately

Implementation changes: none

## 1. Executive summary

The canonical package, distribution, command, and public implementation classes are already PHASENOX identities. The remaining legacy strings are not one uniform cleanup set. They divide into:

- live compatibility contracts that must remain, including Python aliases, the `brain` namespace, root environment fallbacks, engine keys, and persistence collection names;
- serialized method/provider identities that must not be changed without a versioned data-contract migration;
- stale current-facing paths, examples, comments, prompts, cache labels, thread labels, fixture names, and developer documentation that should be updated in a later cleanup sprint;
- historical records that should remain historical rather than be rewritten;
- no production code that this text-only audit can safely prove dead and remove.

R6 must therefore not use a global replacement. In particular, changing an import path and changing a persisted method ID are different operations even when both contain the same lowercase token.

## 2. Method and occurrence totals

The census used case-insensitive literal matching for `noisyne` and `soundbrain`, followed by case-sensitive counts for all observed casing variants. Counts below describe the repository **before this audit document was added**, so the document does not count itself.

### Tracked baseline

| Literal casing | Occurrences |
| --- | ---: |
| `noisyne` | 236 |
| `Noisyne` | 65 |
| `NOISYNE` | 89 |
| `soundbrain` | 180 |
| `SoundBrain` | 189 |
| `SOUNDBRAIN` | 37 |
| **All casing variants** | **796** |

The four exact spellings requested by the R6 brief total 694 occurrences. The remaining 102 are the supplemental `Noisyne` and `SOUNDBRAIN` casing variants, included so the audit is complete.

| Area | Occurrences | Files |
| --- | ---: | ---: |
| Production (`phasenox/`, `brain/`, `main.py`) | 91 | 35 |
| Tests | 207 | 26 |
| Documentation and root Markdown | 486 | 81 |
| Tooling (`.gitignore`, scripts, tools) | 12 | 5 |
| **Total** | **796** | **147** |

### Pre-existing untracked baseline

Two untracked desktop UI roadmaps existed before R6 and are outside this branch's permitted cleanup scope:

| File | Occurrences | Classification |
| --- | ---: | --- |
| `docs/Desktop-Ui-Roadmap-Sprint.md` | 34 | D / out of scope: pre-existing desktop UI roadmap |
| `docs/Desktop-Ui-Roadmap-v1.2.md` | 36 | D / out of scope: pre-existing desktop UI roadmap |

The untracked `assets/` tree contained no matching text. Combining tracked text with the two pre-existing roadmap files gives a worktree baseline of 866 occurrences in 149 files. Neither the roadmaps nor assets were modified.

## 3. Classification rules used

- **A — MUST REMAIN:** compatibility alias/shim, persisted or serialized identifier, legacy engine key, environment compatibility, negative compatibility assertion, repository identity, or migration record needed by a live contract.
- **B — SHOULD UPDATE:** current-facing documentation, import site, filename/module path, comment, prompt, fixture name, cache/thread label, example, or developer-facing identity that is not a persistence contract.
- **C — REMOVE:** code or reference proven dead, obsolete, and unnecessary for compatibility.
- **D — HISTORICAL:** changelog, prior audit, frozen roadmap, archive, release report, or old migration record whose historical wording should remain.

`A/B` and `A/D` mean a file contains occurrences with different semantic roles. Such files require line-level edits; the whole file cannot be replaced or retained as one unit.

## 4. File-by-file classification

### 4.1 Production

| File | Count | Class | Finding |
| --- | ---: | --- | --- |
| `main.py` | 2 | B | Imports the canonical class through the legacy-named `application.noisyne_service` module. |
| `phasenox/agents/assistant.py` | 1 | B | Current system prompt says `SoundBrain`. |
| `phasenox/agents/base_agent.py` | 1 | B | Current class documentation says `SoundBrain`. |
| `phasenox/application/__init__.py` | 10 | A/B | Public legacy class aliases must remain; lazy loading through legacy-named service modules is cleanup debt. |
| `phasenox/application/noisyne_service.py` | 4 | A/B | `NoisyneService` alias and compatibility documentation remain; canonical implementation living in a legacy-named file should move only with import compatibility preserved. |
| `phasenox/application/service.py` | 2 | A | `NoisyneV2Service` is a single alias to `PhasenoxV2Service`, not a duplicate implementation. |
| `phasenox/application/soundbrain_service.py` | 5 | A | Compatibility module exports aliases to `PhasenoxService`; no duplicate implementation. |
| `phasenox/infrastructure/config/loader.py` | 6 | A/B | `NOISYNE_ROOT` and `SOUNDBRAIN_ROOT` precedence/docs remain; two current error messages saying `NOISYNE configuration` should update. |
| `phasenox/infrastructure/config/models.py` | 1 | A | Persisted Chroma collection default `soundbrain`; do not rename in cleanup. |
| `phasenox/memory/vector/config.py` | 1 | A | Persisted vector collection default `soundbrain`; do not rename in cleanup. |
| `phasenox/orchestration/orchestrator.py` | 1 | B | Internal import uses legacy compatibility module rather than the canonical implementation boundary. |
| `phasenox/perception/auditory_contracts.py` | 1 | A | Serialized method ID. |
| `phasenox/perception/context_contracts.py` | 2 | A | Serialized method IDs. |
| `phasenox/perception/descriptor_contracts.py` | 2 | A/B | Method ID remains; current diagnostic prose should use the current technical identity. |
| `phasenox/perception/knowledge_contracts.py` | 1 | A | Serialized method ID. |
| `phasenox/perception/knowledge_store.py` | 1 | A | Provider identity may be stored or hashed; requires explicit versioning, not cleanup replacement. |
| `phasenox/perception/loudness_contracts.py` | 1 | A | Serialized method ID. |
| `phasenox/perception/loudness.py` | 1 | A | Emitted method ID. |
| `phasenox/perception/masking_contracts.py` | 1 | A | Serialized method ID. |
| `phasenox/perception/mix_intelligence_contracts.py` | 1 | A | Serialized method ID. |
| `phasenox/perception/reasoning_contracts.py` | 2 | A | Serialized method and digest IDs. |
| `phasenox/perception/reasoning.py` | 1 | A | Emitted provider ID. |
| `phasenox/perception/reference_contracts.py` | 2 | A | Serialized method IDs. |
| `phasenox/perception/reference_intelligence.py` | 3 | A | Emitted method IDs. |
| `phasenox/perception/transfer_contracts.py` | 1 | A | Serialized method ID. |
| `phasenox/perception/translation_contracts.py` | 2 | A | Serialized method IDs. |
| `phasenox/perception/translation.py` | 2 | A | Emitted method IDs. |
| `phasenox/perception/validation_fixtures.py` | 2 | B | `NoisyneValidationFixtureProvider` is a current internal/test API name; introduce a canonical name and keep an alias only if external use is supported. |
| `phasenox/perception/validation_matrix.py` | 18 | A/B | Seventeen contract IDs remain; current human-readable `NOISYNE` diagnostic prose should update. |
| `phasenox/performance/benchmark_cli.py` | 1 | B | Disposable default cache directory label; coordinate invalidation/cleanup. |
| `phasenox/performance/fixture_model.py` | 3 | B | Process marker and disposable test-cache labels; update deliberately with cleanup support. |
| `phasenox/report/__init__.py` | 2 | A | `SoundBrainReport` compatibility export remains. |
| `phasenox/report/models.py` | 2 | A | `SoundBrainReport` is a single alias to `PhasenoxReport`. |
| `phasenox/runtime/engine_registry.py` | 3 | A/B | Legacy engine keys `noisyne` and `soundbrain` remain; internal import through `noisyne_service` should update. |
| `phasenox/runtime/jobs/scheduler.py` | 2 | B | Thread names are observability/runtime labels, not persisted job identities; update with monitoring awareness. |

`brain/__init__.py` has no audited token, but is itself an approved legacy namespace shim. It must remain compatibility-only and maps `brain.*` imports to the same `phasenox.*` module objects.

### 4.2 Tests

| File | Count | Class | Finding |
| --- | ---: | --- | --- |
| `tests/test_application_root.py` | 31 | A | Required canonical-first precedence and legacy environment compatibility coverage. |
| `tests/test_audio_pipeline.py` | 1 | B | Arbitrary fixture artist metadata uses a stale identity. |
| `tests/test_engine_registry.py` | 2 | A | Protects approved legacy engine-key lookup. |
| `tests/test_evaluation_metrics.py` | 2 | A | Protects `SoundBrainReport is PhasenoxReport`. |
| `tests/test_noisyne_phase1_compatibility.py` | 41 | A/B | Compatibility proofs remain; stale comments/names describing `noisyne` as canonical should update. |
| `tests/test_noisyne_phase2_distribution.py` | 10 | A | Confirms old commands are absent and legacy import aliases still resolve after wheel installation. |
| `tests/test_noisyne_phase3_namespace.py` | 13 | A/B | Namespace/alias proofs remain; stale test naming should update. |
| `tests/test_noisyne_phase4_identity.py` | 9 | A/B | Persistence and engine assertions remain; stale developer-script/test naming can update. |
| `tests/test_noisyne_phase5_release_alignment.py` | 5 | A | Protects canonical CLI and legacy environment/CLI-negative contracts. |
| `tests/test_noisyne_phase6_repository_freeze.py` | 19 | A/D | Live freeze assertions plus a historical phase filename; retain until superseded by a new canonical contract test. |
| `tests/test_persistence_safety.py` | 5 | A | Fake stores intentionally exercise the persisted `soundbrain` collection. |
| `tests/test_soundbrain_service.py` | 7 | A/B | Canonical behavior is tested through a legacy module; retain a narrow alias/lazy-import proof and move behavior coverage to canonical imports. |
| `tests/test_soundbrain_service_integration.py` | 5 | A/B | Same split: compatibility proof remains, canonical integration coverage should use canonical naming. |
| `tests/test_soundbrain_service_rag.py` | 2 | A/B | Same split; do not weaken RAG behavior coverage. |
| `tests/test_soundbrain_service_reasoning.py` | 3 | A/B | Same split; do not weaken reasoning behavior coverage. |
| `tests/test_soundbrain_service_reference.py` | 4 | A/B | Same split; do not weaken reference behavior coverage. |
| `tests/test_soundbrain_service_semantic.py` | 2 | A/B | Same split; do not weaken semantic behavior coverage. |
| `tests/test_sprint12_validation_framework.py` | 24 | B | Consumers of the noncanonical fixture-provider name; update with its implementation. |
| `tests/test_sprint13_knowledge_memory.py` | 6 | A | Provider identities are serialized contract fixtures/assertions. |
| `tests/test_sprint14_performance_baseline.py` | 1 | B | Disposable performance test-cache label. |
| `tests/test_sprint15_5_onnx_gpu.py` | 5 | B | Disposable fixture cache paths; update with the runtime cache label. |
| `tests/test_sprint15_application_service.py` | 5 | A/B | Alias identity proof remains; lightweight-import assertions expose legacy implementation module naming that should migrate compatibly. |
| `tests/archive/test_full_pipeline.py` | 1 | D | Archived output wording. |
| `tests/archive/test_pymupdf.py` | 1 | D/C candidate | Archived, nonportable hard-coded `E:\SoundBrain` path. Preserve as history or remove the obsolete archived test as a whole; never rewrite it into a live path. |
| `tests/archive/test_reasoning.py` | 1 | D | Archived mock wording. |
| `tests/archive/test_report.py` | 2 | D | Archived report wording. |

### 4.3 Current-facing and mixed documentation

| File | Count | Class | Finding |
| --- | ---: | --- | --- |
| `CONTRIBUTING.md` | 2 | A | Correctly records removal of the two former CLI commands. |
| `README.md` | 12 | A/B | Repository URL, env fallbacks, and legacy alias remain; stale package trees, ASCII identity, canonical-service declaration, and example import should update. |
| `docs/AI_AGENT_RULES.md` | 1 | B | Current title uses the former identity. |
| `docs/ARCHITECTURE_v2.md` | 2 | A/B | Repository name remains; stale package path updates. |
| `docs/AUDIO_ADR_v2.md` | 1 | B | Current product prose uses the former identity. |
| `docs/AUDITORY_FRONTEND_V2.md` | 4 | A/B | Serialized method ID remains; three stale module/package references update. |
| `docs/CAPABILITY_REGISTRY.md` | 10 | A/B | Repository, aliases, and removed-CLI history remain; stale source paths update. |
| `docs/CODE_OF_CONDUCT_v2.md` | 2 | B | Current project wording uses the former identity. |
| `docs/CONTRIBUTING_v2.md` | 4 | B | Current contributor-facing branding uses the former identity. |
| `docs/DECISIONS_v2.md` | 2 | A/B | Repository identity remains; stale runtime path updates. |
| `docs/DEPENDENCY_GRAPH.md` | 2 | B | Current title/prose uses the former identity. |
| `docs/DESCRIPTOR_FOUNDATION_V2.md` | 2 | B | Stale source path and current technical prose. |
| `docs/DESIGN_PATTERNS_v2.md` | 2 | B | Current title/prose uses the former identity. |
| `docs/ENGINEERING_v2.md` | 1 | B | Current title uses the former identity. |
| `docs/EXECUTION_PLAN_v2.md` | 7 | A | Correct current repository and compatibility-boundary record. |
| `docs/KNOWLEDGE_MEMORY_PERSONALIZATION_V2.md` | 6 | B | Stale package/source paths. |
| `docs/LOUDNESS_FOUNDATION_V2.md` | 2 | B | Stale module paths. |
| `docs/MASKING_FOUNDATION_V2.md` | 2 | B | Stale module paths. |
| `docs/MODEL_REGISTRY.md` | 2 | B | Current title/prose uses the former identity. |
| `docs/MODULE_MAP.md` | 49 | A/B | Compatibility identities and repository remain; canonical package declaration and extensive source paths are stale. Highest-priority documentation cleanup. |
| `docs/PERCEPTUAL_MIX_INTELLIGENCE_V2.md` | 2 | B | Current technical headings/prose use the prior ASCII identity. |
| `docs/PERCEPTUAL_REASONING_INTEGRATION_V2.md` | 5 | A/B | Serialized digest ID remains; current prose uses the prior identity. |
| `docs/PERCEPTUAL_REFERENCE_INTELLIGENCE_V2.md` | 1 | B | Current heading uses the prior ASCII identity. |
| `docs/PERCEPTUAL_SCIENTIFIC_VALIDATION_V2.md` | 17 | A/B | Thirteen serialized method IDs remain; source paths update. |
| `docs/PERFORMANCE_ONNX_BENCHMARK_V2.md` | 7 | B | Stale import commands, module paths, and cache examples. |
| `docs/PHILOSOPHY_v2.md` | 5 | B | Current project philosophy uses the former identity. |
| `docs/PLAYBACK_PROFILE_FOUNDATION_V2.md` | 1 | A | Serialized method identity. |
| `docs/PROJECT_MANIFEST.md` | 2 | B/D | Stale package tree should update; link to historical rename freeze remains. |
| `docs/README_v2.md` | 6 | A/B | Compatibility aliases, removed CLI commands, and env fallbacks remain; canonical service example should use `PhasenoxService`. |
| `docs/ROADMAP_v2.md` | 8 | A/B | Repository and compatibility boundary remain; stale `noisyne.integration` path updates. |
| `docs/SECURITY_v2.md` | 2 | B | Current security policy uses the former identity. |
| `docs/SUPPORT_v2.md` | 4 | B | Current support text uses the former identity. |
| `docs/TRANSLATION_RISK_FOUNDATION_V2.md` | 1 | B | Current comparison label uses the prior ASCII identity. |
| `docs/V2_APPLICATION_SERVICE_INTEGRATION.md` | 5 | A/B | Alias names remain as compatibility documentation; stale canonical package paths update. |
| `docs/V2_JOB_RUNTIME_SCHEDULER.md` | 5 | B | Stale package paths and import example. |
| `docs/VISION_v2.md` | 2 | B | Current title/prose uses the former identity. |

### 4.4 Historical documentation

These files are historical records. Their legacy wording is evidence of the state they recorded, not current API guidance.

| File | Count | Class |
| --- | ---: | --- |
| `docs/CHANGELOG_v2.md` | 6 | D |
| `docs/NOISYNE_TECHNICAL_RENAME_FREEZE.md` | 17 | A/D |
| `docs/PHASENOX_R4_RUNTIME_MIGRATION_AUDIT.md` | 55 | D |
| `docs/PHASENOX_R5_PERSISTENCE_MIGRATION_AUDIT.md` | 46 | D |
| `docs/RELEASE_NOTES.md` | 2 | D |
| `docs/TECHNICAL_DEBT.md` | 49 | D |
| `V1_FREEZE_VALIDATION_REPORT.md` | 26 | D |
| `V2_RAG_MEMORY_PREFLIGHT_REPORT.md` | 2 | D |
| `docs/roadmap/SoundBrain_Living_Roadmap_v2.md` | 1 | D |
| `docs/roadmap/SoundBrain_Living_Roadmap_v3.md` | 1 | D |
| `docs/roadmap/SoundBrain_Living_Roadmap_v3_Final.md` | 1 | D |
| `docs/roadmap/SoundBrain_Living_Roadmap_v4.md` | 1 | D |
| `docs/roadmap/SoundBrain_Living_Roadmap_v5_Architecture_Freeze.md` | 2 | D |
| `docs/roadmap/SoundBrain_Living_Roadmap_v6_Ultimate.md` | 1 | D |
| `docs/roadmap/SoundBrain_Living_Roadmap_v7_Platform_Extended.md` | 1 | D |
| `docs/roadmap/SoundBrain_Master_Roadmap.md` | 4 | D |

All matching Bible files are historical design records:

| File | Count | Class |
| --- | ---: | --- |
| `docs/bible/README.md` | 1 | D |
| `docs/bible/01_Vision_&_Mission.md` | 5 | D |
| `docs/bible/02_Architecture.md` | 1 | D |
| `docs/bible/03_Runtime.md` | 2 | D |
| `docs/bible/04_AI_Stack.md` | 2 | D |
| `docs/bible/05_Roadmap.md` | 1 | D |
| `docs/bible/06_Sprint_Tracker.md` | 13 | D |
| `docs/bible/07_Technical_Debt.md` | 28 | D |
| `docs/bible/08_Validation_Gates.md` | 1 | D |
| `docs/bible/09_Release_Guide.md` | 1 | D |
| `docs/bible/10_Testing_Strategy.md` | 1 | D |
| `docs/bible/11_Backlog.md` | 1 | D |
| `docs/bible/12_Project_Rules.md` | 2 | D |
| `docs/bible/13_System_Architecture.md` | 2 | D |
| `docs/bible/14_Data_Flow.md` | 1 | D |
| `docs/bible/15_Folder_Structure.md` | 3 | D |
| `docs/bible/16_Model_Registry.md` | 2 | D |
| `docs/bible/17_Knowledge_Layer.md` | 1 | D |
| `docs/bible/18_RAG_Architecture.md` | 1 | D |
| `docs/bible/19_Reasoning_Engine.md` | 1 | D |
| `docs/bible/20_Engineering_Intelligence.md` | 1 | D |
| `docs/bible/21_Report_Generator.md` | 1 | D |
| `docs/bible/22_Memory_System.md` | 2 | D |
| `docs/bible/23_API_Design.md` | 2 | D |
| `docs/bible/24_Configuration_System.md` | 2 | D |
| `docs/bible/25_Dependency_Injection.md` | 1 | D |
| `docs/bible/26_Error_Handling_Strategy.md` | 2 | D |
| `docs/bible/27_Logging_Strategy.md` | 1 | D |
| `docs/bible/39_Audio_Foundation_Model_V4.md` | 1 | D |

### 4.5 Packaging, scripts, and tools

`pyproject.toml` has zero audited legacy occurrences. Its only console script is `phasenox = "phasenox.cli:main"`.

| File | Count | Class | Finding |
| --- | ---: | --- | --- |
| `.gitignore` | 3 | B | Stale header and disposable performance-cache directory names. Coordinate with cache default changes. |
| `scripts/export_project.py` | 1 | B | Current generated export header uses prior ASCII identity. |
| `scripts/generate_v1_release_validation.py` | 5 | A/B | Compatibility module/test paths remain while those tests exist; generated purpose text should update. |
| `tools/exporter/bundle.py` | 1 | B | Current bundle metadata emits prior ASCII product identity. |
| `tools/README.md` | 2 | B | Developer examples describe stale package paths. |

## 5. Must-remain identities

### Python compatibility

- `NoisyneService` -> `PhasenoxService`
- `SoundBrainService` -> `PhasenoxService`
- `NoisyneV2Service` -> `PhasenoxV2Service`
- `SoundBrainReport` -> `PhasenoxReport`
- legacy `phasenox.application.noisyne_service` and `phasenox.application.soundbrain_service` import paths while compatibility is promised
- `brain.*` -> the same canonical `phasenox.*` module objects

Each legacy class is an alias, not a second implementation.

### Environment compatibility

The live order is:

1. `PHASENOX_ROOT`
2. `NOISYNE_ROOT`
3. `SOUNDBRAIN_ROOT`
4. automatic discovery

Empty values remain unset; resolved-path conflict diagnostics remain. The two legacy variables must not be removed in a documentation cleanup.

### Persistence and serialized contracts

- Chroma/vector collection `soundbrain`
- engine registry keys `noisyne` and `soundbrain`
- all `noisyne.*` method IDs, provider IDs, and digest IDs currently emitted or validated by perceptual contracts

The exact misspelling `sounbrain` has no live repository occurrence; its only mention is the R5 audit explaining that absence.

### Repository and migration history

The repository name and origin `N0ises/NOISYNE` remain factual until a separately authorized repository migration. Prior audit, freeze, changelog, report, and roadmap wording should remain intact or be clearly archived, not silently rewritten.

## 6. Safe cleanup candidates

No Category C production deletion is established by this audit. The following Category B work is safe only when performed semantically and with focused tests:

1. Update current-facing docs and examples to `phasenox` paths and `Phasenox*` canonical imports, led by `docs/MODULE_MAP.md`, `README.md`, and `docs/README_v2.md`.
2. Move the canonical V1 implementation out of `application/noisyne_service.py` to a canonical-named module, leaving the old module as a thin alias shim; update internal imports in `main.py`, the orchestrator, and engine registry.
3. Move canonical behavior tests away from `test_soundbrain_service*` imports while retaining a compact compatibility suite proving old paths and aliases.
4. Canonicalize `NoisyneValidationFixtureProvider`, retaining an alias only if it is an intentionally public surface.
5. Update live prompt/prose strings and diagnostic messages.
6. Rename disposable performance caches and scheduler thread names with explicit cleanup and observability notes; do not treat them as persisted business data.
7. Update exporter metadata/header text and tool documentation.
8. Either retain `tests/archive/test_pymupdf.py` as historical evidence or remove the obsolete archived test; never repoint its hard-coded local path.

## 7. Risk analysis

| Risk | Consequence | Control |
| --- | --- | --- |
| Global replacement changes `soundbrain` collections | Existing RAG/memory data becomes invisible or split across stores. | Exclude persistence constants and assert collection identity. |
| Rewriting `noisyne.*` method/provider IDs | Stored results, digests, fixtures, and comparison logic lose identity continuity. | Freeze IDs or introduce explicitly versioned aliases/migrations. |
| Removing aliases or legacy modules | Existing Python consumers and installed-wheel compatibility break. | Keep one canonical implementation plus thin aliases and identity tests. |
| Removing legacy root variables | Existing deployments resolve a different application root. | Preserve precedence and conflict tests. |
| Removing engine keys | Serialized selections/configuration fail at runtime. | Retain registry aliases until a separate migration contract exists. |
| Renaming cache paths blindly | Orphaned files and confusing benchmark behavior. | Treat as disposable state but add cleanup/fallback handling. |
| Updating historical records | Audit trail becomes inaccurate. | Leave D files unchanged; add superseding current docs instead. |
| Editing pre-existing desktop UI or assets | Cross-branch/scope contamination. | Keep those paths untouched. |

## 8. Recommended cleanup order

1. Freeze must-remain identities in a small explicit compatibility matrix and tests.
2. Update current architecture/docs/examples without touching historical records.
3. Introduce canonical internal module and fixture names, leaving aliases at legacy import boundaries.
4. Shift behavior tests to canonical imports; retain focused compatibility tests.
5. Update current prompts, diagnostics, scripts, and generated metadata.
6. Change disposable cache/thread labels with cleanup and monitoring notes.
7. Re-run an exact census and review every remaining occurrence against the A/D inventory.
8. Consider removal only after usage/dependency evidence proves a candidate dead; do not infer deadness from naming alone.

## 9. Special-check results

- **Package:** `phasenox` exists as canonical package. No production `import noisyne`, `from noisyne...`, or matching dynamic module load was found under `phasenox/`, `brain/`, `scripts/`, `tools/`, or `main.py`.
- **CLI:** `pyproject.toml` exposes only `phasenox`; no `noisyne` or `soundbrain` console entry point remains. Tests intentionally mention old commands to assert they are absent.
- **Classes:** canonical `PhasenoxService`, `PhasenoxV2Service`, and `PhasenoxReport` definitions exist. Legacy names are aliases to those objects; there are no duplicate service/report implementations.
- **Persistence:** live collection defaults remain exactly `soundbrain` in RAG/config and memory-vector boundaries. No persistence path, schema, or data was changed.
- **Environment:** `PHASENOX_ROOT > NOISYNE_ROOT > SOUNDBRAIN_ROOT > auto discovery` remains implemented and covered.
- **Compatibility:** `brain/` remains a compatibility-only import hook targeting `phasenox.*`; it contains no canonical implementation.

## 10. Final rename completion checklist

- [x] Canonical package is `phasenox`; no production dependency imports `noisyne.*`.
- [x] Distribution and sole CLI entry point are `phasenox`.
- [x] Canonical public implementation classes are `Phasenox*`; old names are aliases only.
- [x] Runtime root is canonical-first with both legacy fallbacks preserved.
- [x] `brain` is compatibility-only.
- [x] `soundbrain` persistence identity is unchanged.
- [ ] Current-facing package trees, module paths, examples, and architecture docs use `phasenox` consistently.
- [ ] Canonical V1 implementation and behavior tests no longer depend internally on legacy-named service modules.
- [ ] Internal fixture, cache, thread, prompt, diagnostic, script, and exporter identities are canonicalized where safe.
- [ ] A post-cleanup census contains only approved A and D occurrences.
- [ ] Any future removal has separate dependency proof and deprecation authorization.

This audit authorizes no cleanup, persistence migration, commit, or push.
