# PHASENOX R6.3 Final Legacy Identity Census

## Scope and method

This is the read-only final census performed at commit
`33625370428d81ab38f64a468e73e80181ddc51d` on branch
`v2-development`. It searched every tracked text file for the exact case variants
`noisyne`, `NOISYNE`, `Noisyne`, `soundbrain`, `SoundBrain`, and `SOUNDBRAIN`,
then inspected every tracked filename case-insensitively for `noisyne` or
`soundbrain`.

Counts below describe the repository before this report was added. The report is
excluded from its own census so that its explanatory text does not recursively
inflate the result. Matching is occurrence-based, not line-based: multiple
matches on one line count separately.

## Executive result

There are **604** remaining text occurrences in **112 tracked files**.

| Category | Meaning | Occurrences |
| --- | --- | ---: |
| A | Must remain: live compatibility, persisted/serialized contract, or active migration/freeze reference | 284 |
| B | Should still update: active disposable/current-facing naming | 17 |
| C | Remove: proven dead and unnecessary | 0 |
| D | Historical record | 303 |
| **Total** |  | **604** |

The R6 close condition is **not met**. Category B is 17 rather than zero.
Category C is zero. The residual B items are enumerated exactly below; this
sprint does not change them.

### Exact-case totals

| Search token | Occurrences |
| --- | ---: |
| `noisyne` | 139 |
| `Noisyne` | 42 |
| `NOISYNE` | 69 |
| `soundbrain` | 155 |
| `SoundBrain` | 162 |
| `SOUNDBRAIN` | 37 |
| **Total** | **604** |

### Counts by area and category

| Area | Files | A | B | C | D | Total |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Production (`phasenox/`, `brain/`, production scripts) | 32 | 72 | 6 | 0 | 0 | 78 |
| Tests | 18 | 145 | 8 | 0 | 5 | 158 |
| Documentation and repository-root reports | 60 | 66 | 0 | 0 | 298 | 364 |
| Tooling/configuration | 2 | 1 | 3 | 0 | 0 | 4 |
| **Total** | **112** | **284** | **17** | **0** | **303** | **604** |

## Category B residuals

These are active, disposable identifiers or stale current-facing wording. They
are not persistence names, engine keys, serialized IDs, compatibility aliases,
or environment-variable fallbacks.

| File and line | Count | Residual identity | Reason for B classification |
| --- | ---: | --- | --- |
| `.gitignore:2` | 1 | `# SoundBrain` | Current-facing repository heading. |
| `.gitignore:53-54` | 2 | `.noisyne_performance_test_cache/`, `.noisyne_performance_cache/` | Active disposable cache-directory names. |
| `phasenox/performance/benchmark_cli.py:285` | 1 | `.noisyne_performance_cache` | Active disposable benchmark cache default. |
| `phasenox/performance/fixture_model.py:213,276,312` | 3 | `_noisyne_fixture_process` and `.noisyne_performance_test_cache` | Active process marker and disposable test cache identity. |
| `phasenox/runtime/jobs/scheduler.py:118,123` | 2 | `noisyne-job-scheduler`, `noisyne-job-worker` | Active diagnostic thread names; not serialized contracts. |
| `tests/test_audio_pipeline.py:25` | 1 | artist value `SoundBrain` | Current test fixture label without a compatibility purpose. |
| `tests/test_sprint14_performance_baseline.py:555` | 1 | `.noisyne_performance_test_cache` | Active disposable test cache expectation. |
| `tests/test_sprint15_5_onnx_gpu.py:64,141,171,210,230` | 5 | `.noisyne_performance_test_cache` | Active disposable test cache setup/expectations. |
| `tests/test_sprint15_application_service.py:100` | 1 | `test_import_noisyne_application_is_lightweight` | Stale current-facing test function name; behavior already targets `phasenox`. |
| **Total** | **17** |  |  |

No Category C occurrence was found.

## Remaining production occurrences

All production occurrences not identified as B are Category A compatibility,
persistence, engine, serialized, or environment contracts.

| File | A | B | Classification note |
| --- | ---: | ---: | --- |
| `phasenox/application/__init__.py` | 8 | 0 | Legacy public aliases. |
| `phasenox/application/noisyne_service.py` | 2 | 0 | Compatibility-only module and alias. |
| `phasenox/application/phasenox_service.py` | 2 | 0 | Legacy serialized/compatibility references. |
| `phasenox/application/service.py` | 2 | 0 | Legacy V2 service alias. |
| `phasenox/application/soundbrain_service.py` | 4 | 0 | Compatibility-only aliases. |
| `phasenox/infrastructure/config/loader.py` | 4 | 0 | Legacy environment fallbacks. |
| `phasenox/infrastructure/config/models.py` | 1 | 0 | Protected runtime/engine identity. |
| `phasenox/memory/vector/config.py` | 1 | 0 | Persisted collection name. |
| `phasenox/perception/auditory_contracts.py` | 1 | 0 | Serialized `noisyne.*` identifier. |
| `phasenox/perception/context_contracts.py` | 2 | 0 | Serialized `noisyne.*` identifiers. |
| `phasenox/perception/descriptor_contracts.py` | 1 | 0 | Serialized `noisyne.*` identifier. |
| `phasenox/perception/knowledge_contracts.py` | 1 | 0 | Serialized `noisyne.*` identifier. |
| `phasenox/perception/knowledge_store.py` | 1 | 0 | Serialized `noisyne.*` identifier. |
| `phasenox/perception/loudness_contracts.py` | 1 | 0 | Serialized `noisyne.*` identifier. |
| `phasenox/perception/loudness.py` | 1 | 0 | Serialized `noisyne.*` identifier. |
| `phasenox/perception/masking_contracts.py` | 1 | 0 | Serialized `noisyne.*` identifier. |
| `phasenox/perception/mix_intelligence_contracts.py` | 1 | 0 | Serialized `noisyne.*` identifier. |
| `phasenox/perception/reasoning_contracts.py` | 2 | 0 | Serialized `noisyne.*` identifiers. |
| `phasenox/perception/reasoning.py` | 1 | 0 | Serialized `noisyne.*` identifier. |
| `phasenox/perception/reference_contracts.py` | 2 | 0 | Serialized `noisyne.*` identifiers. |
| `phasenox/perception/reference_intelligence.py` | 3 | 0 | Serialized `noisyne.*` identifiers. |
| `phasenox/perception/transfer_contracts.py` | 1 | 0 | Serialized `noisyne.*` identifier. |
| `phasenox/perception/translation_contracts.py` | 2 | 0 | Serialized `noisyne.*` identifiers. |
| `phasenox/perception/translation.py` | 2 | 0 | Serialized `noisyne.*` identifiers. |
| `phasenox/perception/validation_fixtures.py` | 2 | 0 | Legacy validation fixture aliases. |
| `phasenox/perception/validation_matrix.py` | 17 | 0 | Serialized method/provider/digest IDs. |
| `phasenox/performance/benchmark_cli.py` | 0 | 1 | Disposable cache path. |
| `phasenox/performance/fixture_model.py` | 0 | 3 | Disposable cache/process marker. |
| `phasenox/report/__init__.py` | 2 | 0 | Legacy report alias. |
| `phasenox/report/models.py` | 2 | 0 | Legacy report alias. |
| `phasenox/runtime/engine_registry.py` | 2 | 0 | Protected engine keys. |
| `phasenox/runtime/jobs/scheduler.py` | 0 | 2 | Diagnostic thread names. |
| **Total** | **72** | **6** |  |

No matching occurrence remains in tracked `brain/` source; the namespace itself
continues to provide compatibility through its generic redirect mechanism.

## Remaining test occurrences

| File | A | B | D | Classification note |
| --- | ---: | ---: | ---: | --- |
| `tests/archive/test_full_pipeline_integration.py` | 0 | 0 | 1 | Archived test. |
| `tests/archive/test_pymupdf_runtime_policy.py` | 0 | 0 | 1 | Archived test. |
| `tests/archive/test_reasoning.py` | 0 | 0 | 1 | Archived test. |
| `tests/archive/test_report.py` | 0 | 0 | 2 | Archived test. |
| `tests/test_application_root.py` | 31 | 0 | 0 | Canonical/legacy root precedence coverage. |
| `tests/test_audio_pipeline.py` | 0 | 1 | 0 | Stale fixture label. |
| `tests/test_engine_registry.py` | 2 | 0 | 0 | Protected engine-key coverage. |
| `tests/test_noisyne_phase6_repository_freeze.py` | 19 | 0 | 0 | Active legacy freeze/compatibility contract; filename is historical. |
| `tests/test_persistence_safety.py` | 5 | 0 | 0 | Persisted collection/legacy inventory contract. |
| `tests/test_phasenox_compatibility.py` | 48 | 0 | 0 | Focused public alias/module compatibility. |
| `tests/test_phasenox_distribution.py` | 10 | 0 | 0 | Negative legacy CLI/distribution assertions. |
| `tests/test_phasenox_identity.py` | 7 | 0 | 0 | Canonical identity and protected legacy contract assertions. |
| `tests/test_phasenox_namespace_compatibility.py` | 13 | 0 | 0 | Focused `brain.*` compatibility. |
| `tests/test_phasenox_release_alignment.py` | 4 | 0 | 0 | Protected compatibility/release assertions. |
| `tests/test_sprint13_knowledge_memory.py` | 6 | 0 | 0 | Serialized/persisted identity coverage. |
| `tests/test_sprint14_performance_baseline.py` | 0 | 1 | 0 | Disposable cache path. |
| `tests/test_sprint15_5_onnx_gpu.py` | 0 | 5 | 0 | Disposable test cache paths. |
| `tests/test_sprint15_application_service.py` | 0 | 1 | 0 | Stale test function name. |
| **Total** | **145** | **8** | **5** |  |

The six current behavior suites—`test_phasenox_service.py` plus its integration,
RAG, reasoning, reference, and semantic variants—contain no legacy occurrence
and import `PhasenoxService` from
`phasenox.application.phasenox_service`. Compatibility coverage remains
concentrated in the two explicit PHASENOX compatibility suites and active
freeze-contract tests rather than duplicating normal service behavior.

## Remaining documentation and tooling occurrences

### Current files: Category A

All matches in these files describe a live compatibility/persistence contract,
a negative legacy CLI assertion, or an active migration/freeze reference.

| File | A |
| --- | ---: |
| `CONTRIBUTING.md` | 2 |
| `README.md` | 8 |
| `docs/ARCHITECTURE_v2.md` | 1 |
| `docs/AUDITORY_FRONTEND.md` | 1 |
| `docs/CAPABILITY_REGISTRY.md` | 7 |
| `docs/DECISIONS.md` | 1 |
| `docs/EXECUTION_PLAN.md` | 7 |
| `docs/MODULE_MAP.md` | 10 |
| `docs/PERCEPTUAL_REASONING_ARCHITECTURE.md` | 1 |
| `docs/PERCEPTUAL_SCIENTIFIC_REVIEW.md` | 13 |
| `docs/PLAYBACK_PROFILE.md` | 1 |
| `docs/PROJECT_MANIFEST.md` | 1 |
| `docs/README_v2.md` | 5 |
| `docs/ROADMAP_v2.md` | 6 |
| `docs/V2_APPLICATION_SERVICE.md` | 2 |
| **Total** | **66** |

### Historical files: Category D

| File or file group | Files | D |
| --- | ---: | ---: |
| `docs/bible/01_SYSTEM_OVERVIEW.md` | 1 | 5 |
| `docs/bible/02_ARCHITECTURE.md` | 1 | 1 |
| `docs/bible/03_DATA_FLOW.md` | 1 | 2 |
| `docs/bible/04_UI_SPEC.md` | 1 | 2 |
| `docs/bible/05_STATE_MANAGEMENT.md` | 1 | 1 |
| `docs/bible/06_API_REFERENCE.md` | 1 | 13 |
| `docs/bible/07_MODULE_REFERENCE.md` | 1 | 28 |
| `docs/bible/08_PLUGIN_SYSTEM.md` | 1 | 1 |
| `docs/bible/09_RETRIEVAL_SUBSYSTEM.md` | 1 | 1 |
| `docs/bible/10_AUDIO_SUBSYSTEM.md` | 1 | 1 |
| `docs/bible/11_DSP_SUBSYSTEM.md` | 1 | 1 |
| `docs/bible/12_ML_SUBSYSTEM.md` | 1 | 2 |
| `docs/bible/13_PROJECT_SUBSYSTEM.md` | 1 | 2 |
| `docs/bible/14_WORKSPACE_FORMAT.md` | 1 | 1 |
| `docs/bible/15_ERROR_HANDLING.md` | 1 | 3 |
| `docs/bible/16_LOGGING_AND_DIAGNOSTICS.md` | 1 | 2 |
| `docs/bible/17_CRASH_RECOVERY.md` | 1 | 1 |
| `docs/bible/18_UPDATE_SYSTEM.md` | 1 | 1 |
| `docs/bible/19_SECURITY_MODEL.md` | 1 | 1 |
| `docs/bible/20_PERFORMANCE_BUDGETS.md` | 1 | 1 |
| `docs/bible/21_THREADING_MODEL.md` | 1 | 1 |
| `docs/bible/22_BUILD_AND_RELEASE.md` | 1 | 2 |
| `docs/bible/23_TEST_STRATEGY.md` | 1 | 2 |
| `docs/bible/24_REPOSITORY_CONVENTIONS.md` | 1 | 2 |
| `docs/bible/25_ONBOARDING.md` | 1 | 1 |
| `docs/bible/26_GLOSSARY.md` | 1 | 2 |
| `docs/bible/27_DECISION_LOG.md` | 1 | 1 |
| `docs/bible/39_GOVERNANCE_POLICY.md` | 1 | 1 |
| `docs/bible/README.md` | 1 | 1 |
| `docs/CHANGELOG_v2.md` | 1 | 6 |
| `docs/NOISYNE_TECHNICAL_RENAME_FREEZE.md` | 1 | 17 |
| `docs/PHASENOX_R4_RUNTIME_MIGRATION_AUDIT.md` | 1 | 55 |
| `docs/PHASENOX_R5_PERSISTENCE_MIGRATION_AUDIT.md` | 1 | 46 |
| `docs/RELEASE_NOTES.md` | 1 | 2 |
| `docs/roadmap/SoundBrain_Living_Roadmap_v2.md` | 1 | 1 |
| `docs/roadmap/SoundBrain_Living_Roadmap_v3.md` | 1 | 1 |
| `docs/roadmap/SoundBrain_Living_Roadmap_v3_Final.md` | 1 | 1 |
| `docs/roadmap/SoundBrain_Living_Roadmap_v4.md` | 1 | 1 |
| `docs/roadmap/SoundBrain_Living_Roadmap_v5_Architecture_Freeze.md` | 1 | 2 |
| `docs/roadmap/SoundBrain_Living_Roadmap_v6_Ultimate.md` | 1 | 1 |
| `docs/roadmap/SoundBrain_Living_Roadmap_v7_Platform_Extended.md` | 1 | 1 |
| `docs/roadmap/SoundBrain_Master_Roadmap.md` | 1 | 4 |
| `docs/TECHNICAL_DEBT.md` | 1 | 49 |
| `V1_FREEZE_VALIDATION_REPORT.md` | 1 | 26 |
| `V2_RAG_MEMORY_PREFLIGHT_REPORT.md` | 1 | 2 |
| **Documentation/root subtotal** | **45** | **298** |
| Archived tests (listed in the test table) | **4** | **5** |
| **Category D total** | **49** | **303** |

The historical set has no changes between R5.1 commit
`c01bab6c5eac00a5d12296eb07dd87199da9c0b7` and the census HEAD.

### Tooling/configuration

| File | A | B | Note |
| --- | ---: | ---: | --- |
| `.gitignore` | 0 | 3 | Stale heading and disposable cache names. |
| `scripts/generate_v1_release_validation.py` | 1 | 0 | Deliberate legacy compatibility-module validation. |
| **Total** | **1** | **3** |  |

## Legacy filename inventory

Twelve tracked filenames contain `noisyne` or `soundbrain` case-insensitively.

### Live compatibility: Category A

- `phasenox/application/noisyne_service.py` — compatibility-only import boundary.
- `phasenox/application/soundbrain_service.py` — compatibility-only import boundary.

### Historical: Category D

- `docs/NOISYNE_TECHNICAL_RENAME_FREEZE.md`
- `docs/roadmap/SoundBrain_Living_Roadmap_v2.md`
- `docs/roadmap/SoundBrain_Living_Roadmap_v3.md`
- `docs/roadmap/SoundBrain_Living_Roadmap_v3_Final.md`
- `docs/roadmap/SoundBrain_Living_Roadmap_v4.md`
- `docs/roadmap/SoundBrain_Living_Roadmap_v5_Architecture_Freeze.md`
- `docs/roadmap/SoundBrain_Living_Roadmap_v6_Ultimate.md`
- `docs/roadmap/SoundBrain_Living_Roadmap_v7_Platform_Extended.md`
- `docs/roadmap/SoundBrain_Master_Roadmap.md`
- `tests/test_noisyne_phase6_repository_freeze.py` — historical filename retained
  by an active freeze/compatibility contract.

No filename is Category B or C.

## Special-check results

1. **Production imports:** no tracked production Python import or dynamic-import
   expression depends on `noisyne` or `noisyne.*`.
2. **CLI:** `pyproject.toml` exposes only
   `phasenox = "phasenox.cli:main"`; there is no `noisyne` or `soundbrain`
   console entry point.
3. **Canonical service:** `PhasenoxService` is implemented in
   `phasenox/application/phasenox_service.py`; `PhasenoxV2Service` remains in the
   canonical application service boundary.
4. **Legacy modules:** `phasenox/application/noisyne_service.py` and
   `phasenox/application/soundbrain_service.py` import the canonical class and
   expose aliases only. Neither contains a duplicate implementation.
5. **Behavior tests:** all six current service behavior families use
   `PhasenoxService` from `phasenox.application.phasenox_service`; none imports a
   legacy module or class name.
6. **Compatibility tests:** focused identity assertions prove the legacy class
   aliases and `brain.*` redirect behavior without duplicating the service
   behavior suites.
7. **Persistence:** `phasenox/memory/vector/config.py` still defines
   `DEFAULT_COLLECTION = "soundbrain"`. It was not renamed.
8. **Serialized identities:** the production multiset of `noisyne.*` tokens is
   unchanged from R5.1: 40 tokens at R5.1 and 40 at the census HEAD, with an
   identical value/count comparison.
9. **Runtime root:** `phasenox/infrastructure/config/loader.py` keeps precedence
   `PHASENOX_ROOT`, then `NOISYNE_ROOT`, then `SOUNDBRAIN_ROOT`, then automatic
   discovery.
10. **Historical records:** the designated historical documents and archived
    tests remain historical and were not rewritten after R5.1.

## Risk and required follow-up

The 17 Category B occurrences do not block canonical imports, CLI behavior,
compatibility, persistence, serialized data, or environment fallback. They do
block the stricter R6 completion rule because they are active identifiers that
could continue surfacing legacy naming in cache directories, process/thread
diagnostics, test output, and repository metadata.

A future explicitly authorized cleanup should change the production B items and
their paired test/config expectations together, verify cache behavior remains
disposable, and rerun this census. It must not reinterpret the Category A
engine, persistence, serialized, environment, class-alias, module-alias, or
`brain.*` contracts as cleanup candidates.

## Final rename readiness verdict

**R6 is not ready to close.** All protected live legacy identities are correctly
Category A and all archival identities are Category D, but 17 Category B
occurrences remain. Category C is zero. No changes are made here; this report is
the sole R6.3 deliverable.
