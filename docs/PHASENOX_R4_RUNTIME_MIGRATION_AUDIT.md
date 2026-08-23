# PHASENOX R4 Runtime Migration Audit

Status: discovery only

Repository: `N0ises/NOISYNE`

Branch: `v2-development`

Audited HEAD: `09d20b7c1c16145521538a600849d3e26b551df4` (R3)

Audit date: 2026-08-23

## Scope and conclusion

This document maps the runtime identity dependencies that must be understood before an R4 migration. It does not authorize or implement a rename, path relocation, persistence migration, or compatibility decision.

The current root identity is resolved by one production function, `get_application_root()` in `phasenox/infrastructure/config/loader.py`. Its precedence is:

1. `NOISYNE_ROOT`
2. `SOUNDBRAIN_ROOT`
3. the nearest ancestor of the config package containing `pyproject.toml` or `configs/`
4. the parent of the installed `phasenox` package (normally `site-packages`)

`PHASENOX_ROOT` is not currently read or documented by production code. There is no Windows per-user application-data policy. In a wheel installation, cache, logs, reports, SQLite, and Chroma paths consequently resolve under the Python installation's `site-packages` directory unless a legacy root variable is set.

The safest future change is therefore not a text rename. R4 should introduce a canonical root variable with explicit precedence and legacy fallbacks, while leaving existing data locations and persistence identifiers untouched. Any move from the current root to a per-user directory changes persistence location and should be designed and executed as an R5 data migration, with discovery, validation, rollback, and split-brain protection.

## 1. Current architecture

### 1.1 Application-root resolution

The only authoritative production resolver is `phasenox/infrastructure/config/loader.py`:

- `_ENV_ROOT = "NOISYNE_ROOT"`
- `_LEGACY_ENV_ROOT = "SOUNDBRAIN_ROOT"`
- `get_application_root()` reads the two variables using `os.environ.get(...)` and the `or` operator.
- A selected environment value is processed with `Path(value).expanduser().resolve()`.
- If neither value is truthy, the function walks upward from `phasenox.infrastructure.config.__file__` and returns the first parent containing either `pyproject.toml` or `configs/`.
- If no source marker is found, it returns `config_dir.parents[2]`, the parent of the installed `phasenox` package.

Consequences:

- `NOISYNE_ROOT` wins whenever it is a non-empty string.
- `SOUNDBRAIN_ROOT` is only consulted when `NOISYNE_ROOT` is absent or empty.
- Whitespace is truthy and resolves as a path; it is not treated as unset.
- Relative environment values resolve against the process current working directory.
- `~` is expanded.
- The selected root is not checked for existence, directory type, or writability.
- The nearest source marker wins; an unexpected ancestor containing `configs/` can change discovery.
- Existing exceptions and guidance still name `NOISYNE_ROOT`.

`phasenox/infrastructure/config/__init__.py` creates the module-level `settings` object by calling `load_settings()` during import. Consumers that import this singleton capture path settings at that time. Changing an environment variable later does not mutate the existing object; callers must explicitly call the loader again or reload the module. This import-time snapshot is an important compatibility and test-order risk.

### 1.2 Environment-loading inventory

| Area | File/function | Behavior | R4 relevance |
| --- | --- | --- | --- |
| Application root | `phasenox/infrastructure/config/loader.py` — `get_application_root()` | Direct `os.environ` lookup with legacy precedence | Primary R4 boundary |
| Settings | `phasenox/infrastructure/config/loader.py` — `load_settings()` | Resolves configured relative paths against the selected root | Primary R4 consumer |
| Config singleton | `phasenox/infrastructure/config/__init__.py` | Loads settings at import time | Import-order compatibility risk |
| CUDA test setup | `tests/performance/conftest.py` and ONNX tests | Reads/updates `PATH` for CUDA DLL discovery | Unrelated to root identity |
| Installer script | `install.ps1` | Uses `KIMI_INSTALL_DIR` and `USERPROFILE` | Separate installer behavior; not the application-root resolver |

No production `os.getenv(...)`, dotenv loader, `APPDATA`, `LOCALAPPDATA`, `Path.home()`, or platform-specific user-data helper was found. `PHASENOX_ROOT` has no current references.

### 1.3 Runtime configuration model

`load_settings()` always loads these package resources, in order, and recursively merges their dictionaries:

1. `phasenox/infrastructure/config/resources/runtime.yaml`
2. `phasenox/infrastructure/config/resources/models.yaml`
3. `phasenox/infrastructure/config/resources/audio.yaml`

They are included in distributions by the `pyproject.toml` package-data declaration for `phasenox.infrastructure.config`. Loading uses `importlib.resources.files("phasenox.infrastructure.config")`; source checkouts and wheels therefore follow the same resource API.

The root-level `configs/runtime.yaml`, `configs/models.yaml`, and `configs/audio.yaml` are mirrors, not runtime overlays. The loader does not read them. Setting a root environment variable changes the base used for relative paths but does not select different YAML content. There is no general user YAML/JSON/TOML override mechanism.

Path expansion rules are:

- `~` is expanded.
- Absolute paths are preserved.
- Other paths are joined to the application root.
- `EmbeddingConfig.model_path` is derived from a model entry name and is handled later by the model repository rather than by the general path expander.

### 1.4 Other configuration loaders

| Loader | Default | Resolution behavior | Wheel implication |
| --- | --- | --- | --- |
| `phasenox/memory/loader.py` — `MemoryLoader` | `configs/memory` | Relative default is joined to `get_application_root()` | Root configs are not packaged, so the default is unavailable in a normal wheel |
| `phasenox/knowledge/loader.py` — `KnowledgeLoader` | `configs/knowledge` | Remains current-working-directory relative | Works in repository-root tests but is fragile outside the checkout |
| `phasenox/audio/plugin/registry.py` — `PluginRegistry` | `configs/plugin_registry.json` | Remains current-working-directory relative | Default registry is not a packaged resource |

The root `configs/` tree also contains memory profiles, knowledge bundles, and `plugin_registry.json`. These files require an explicit packaging/configuration decision if they are intended to function from an installed wheel.

## 2. Legacy runtime identities

### 2.1 Root and path identities

| Identity | Current role | Persistence impact | Proposed phase |
| --- | --- | --- | --- |
| `NOISYNE_ROOT` | Primary application-root override | Redirects all root-relative paths | R4 compatibility boundary |
| `SOUNDBRAIN_ROOT` | Secondary legacy root override | Redirects all root-relative paths | R4 compatibility boundary |
| `PHASENOX_ROOT` | Not implemented | None today | Candidate canonical R4 identity |
| `.noisyne_performance_cache` | Performance CLI's CWD-relative cache | Disposable cache artifacts | Evaluate in R4 only if cache labels are in scope |
| `.noisyne_performance_test_cache` | Performance fixture cache | Disposable test artifacts | Test-only; evaluate with cache-label scope |
| `noisyne_job_` / `noisyne_job_dispatcher` | Scheduler thread names | No durable data | Observability identity, not root resolution |

### 2.2 Runtime and serialized identities outside root scope

The repository also contains legacy engine keys, service compatibility modules, provider identities, method identifiers, documentation, and test fixtures containing `noisyne` or `soundbrain`. These are not equivalent to application-root variables. Several can appear in result payloads, validation matrices, digests, logs, or stored records. They must not be changed as collateral work in a root migration.

Notable examples include:

- engine registry keys `"noisyne"` and `"soundbrain"`;
- the Chroma collection identifier `"soundbrain"`;
- provider identity `"noisyne.in_memory_memory_store"`;
- perception/reference method identifiers beginning with `noisyne.`;
- compatibility module filenames such as `noisyne_service.py` and `soundbrain_service.py`.

These require separate API, schema, or persistence compatibility decisions. A global replacement would break established contracts.

## 3. Runtime path layout

### 3.1 Configured paths

The packaged `runtime.yaml` currently declares:

| Purpose | Configured value | Source-checkout result at the audited workspace |
| --- | --- | --- |
| Model root | `../Models` | `E:\Build\Models` |
| Model cache | `data/cache/models` | `E:\Build\NOISYNE\data\cache\models` |
| General cache | `data/cache` | `E:\Build\NOISYNE\data\cache` |
| Logs | `logs` | `E:\Build\NOISYNE\logs` |
| Reports | `reports` | `E:\Build\NOISYNE\reports` |
| RAG Chroma | default `data/chroma` | `E:\Build\NOISYNE\data\chroma` |

`../Models` intentionally escapes the application root. In a source checkout it points beside the repository; in a wheel it points above `site-packages`, typically into the environment's `Lib/Models` directory on Windows.

### 3.2 Development checkout

With neither legacy environment variable set and the process importing the source package:

- the repository root is discovered through `pyproject.toml` or `configs/`;
- data, cache, logs, reports, SQLite, and vector stores are repository-relative;
- the model root is one directory above the repository because of `../Models`;
- knowledge/plugin defaults additionally depend on the process being launched from the repository root.

### 3.3 Installed wheel

A fresh isolated Windows virtual environment was created during this audit. The existing R3 wheel `dist/phasenox-1.0.0-py3-none-any.whl` and PyYAML were installed without dependencies, and configuration was imported from a working directory outside the repository. Observed resolution was:

| Purpose | Fresh-wheel resolution |
| --- | --- |
| Package | `<venv>\Lib\site-packages\phasenox` |
| Application root | `<venv>\Lib\site-packages` |
| Model root | `<venv>\Lib\Models` |
| Model cache | `<venv>\Lib\site-packages\data\cache\models` |
| General cache | `<venv>\Lib\site-packages\data\cache` |
| Logs | `<venv>\Lib\site-packages\logs` |
| Reports | `<venv>\Lib\site-packages\reports` |
| RAG Chroma | `<venv>\Lib\site-packages\data\chroma` |

All three packaged YAML resources were present. Importing configuration did not create the cache, log, report, model, or Chroma directories. They are created later by individual consumers. A system-wide or otherwise protected Python installation may make these locations unwritable.

### 3.4 Windows user layout

There is no built-in Windows user layout. The application does not consult `%APPDATA%`, `%LOCALAPPDATA%`, `Path.home()`, or a platform-directory library. A user path exists only when the operator explicitly supplies one through `NOISYNE_ROOT` or `SOUNDBRAIN_ROOT`.

Therefore the current layouts are:

- source execution: checkout-relative;
- virtual-environment installation: environment `site-packages`-relative;
- system installation: system `site-packages`-relative and potentially unwritable;
- explicit override: entirely relative to the selected legacy root, except for absolute config values and `../Models` traversal.

### 3.5 Path consumers and temporary files

| Boundary | File | Current behavior |
| --- | --- | --- |
| Reports | `main.py`, reference/report pipeline modules | Uses configured or caller-supplied report directory and creates parents |
| Model loading | `phasenox/runtime/runtime.py`, `phasenox/runtime/repository.py` | Reads model root; repository does not persist model state |
| Declared cache/log paths | config models/resources | `model_cache_dir`, `cache_dir`, and `log_dir` have no general production writer discovered; logging has no file handler |
| Audio catalog | `phasenox/audio/catalog/database.py` | Creates `data/index.db` under the root |
| Report atomic write | `phasenox/report/exporter.py` | Uses `NamedTemporaryFile` in the destination directory and atomically replaces the target; cleans up on failure |
| Integration/evaluation output | adapter and evaluation modules | Writes to caller-supplied target paths |
| Performance artifacts | `phasenox/performance/benchmark_cli.py`, `fixture_model.py` | Creates CWD-relative `.noisyne_*` cache directories |

There is no centralized temporary-directory or runtime-directory manager.

## 4. Configuration resolution by execution mode

### Source checkout

- Python resources are loaded from `phasenox/infrastructure/config/resources/` through `importlib.resources`.
- The source root is discovered by markers.
- Relative runtime paths are expanded against that root.
- Root `configs/runtime.yaml`, `models.yaml`, and `audio.yaml` do not override packaged resources.
- Memory config is root-relative; knowledge and plugin registry defaults are CWD-relative.

### Wheel installation

- The same three YAML resources are loaded from the installed package.
- The fallback root is `site-packages`.
- Relative runtime paths target `site-packages`.
- Root-level memory, knowledge, and plugin registry configs are not present in the wheel under their current defaults.

### User override

- There is no general user configuration file override.
- A legacy environment root changes relative filesystem bases only.
- Absolute YAML paths remain absolute.
- Environment changes made after importing the settings singleton do not update existing consumers.

## 5. Persistence boundaries

No persistence identity or data was changed during this audit.

### 5.1 Durable and semi-durable stores

| Store | Code boundary | Current location/identity | Classification recommendation |
| --- | --- | --- | --- |
| RAG Chroma | `phasenox/rag/vectordb.py` | root + `data/chroma`; collection `soundbrain` | R5: path/data/collection migration |
| Memory vector Chroma | `phasenox/memory/vector/config.py`, `providers/chroma.py` | root + `data/vector_db`; default collection `soundbrain` | R5: separate store requiring separate discovery/migration |
| Audio catalog SQLite | `phasenox/audio/catalog/database.py` | root + `data/index.db` | R5 if root storage moves |
| Reports/reference artifacts | report/reference modules | configured `reports` or caller-supplied paths | R5 if user-data layout moves; format IDs may need schema policy |
| Integration/evaluation artifacts | adapter/evaluation modules | caller-supplied JSON/text/Markdown paths | Future schema compatibility if embedded IDs change |
| Performance caches | performance modules | CWD-relative `.noisyne_*` directories | Disposable; may be invalidated rather than migrated if explicitly scoped |

There are two independent Chroma persistence directories. They share a default collection name but are not the same database. Treating them as one store would risk partial migration or data loss.

`phasenox/rag/vectordb.py` creates a persistent client and collection as module globals. Root selection and storage access therefore occur at import time, which amplifies environment-order and migration risks.

### 5.2 Non-persistent runtime state

- `phasenox/runtime/jobs/registry.py` keeps active jobs and bounded history in memory. Job state is lost at process exit; no serialized job-state migration exists today.
- `phasenox/runtime/cache.py` is an in-memory model-object cache.
- `phasenox/perception/knowledge_store.py` currently provides an in-memory memory store despite its legacy provider identity.

These do not need data migration today. If persistence is later added, its location and identifier scheme should begin with the canonical policy rather than inheriting accidental `site-packages` paths.

### 5.3 Proposed R4 versus R5 boundary

The following is a recommendation for planning, not a decision made by this audit.

Proposed R4 scope:

- recognize a canonical root environment variable;
- preserve and explicitly test legacy root fallbacks;
- update root-resolution diagnostics and narrowly related technical documentation;
- validate root selection before settings and persistent clients are imported;
- decide whether disposable cache/thread labels are in R4 or a later observability cleanup;
- do not relocate existing storage.

Future R5 scope:

- choose a canonical Windows/macOS/Linux user-data layout;
- discover existing legacy roots and stores;
- migrate or dual-read both Chroma directories independently;
- preserve the `soundbrain` collection until an explicit collection migration is approved;
- migrate/validate SQLite and other durable artifacts;
- handle rollback, interrupted migration, locking, duplicates, and split-brain roots;
- version any change to serialized method/provider identifiers.

## 6. Migration risks

1. **Silent precedence inversion.** Adding a canonical variable without a documented precedence rule could select a different data root on machines that define multiple variables.
2. **Import-time capture.** The settings singleton and global RAG client can bind to a root before an application or test modifies its environment.
3. **Split-brain storage.** Switching the default from `site-packages` or a checkout to a user directory without migration can make existing Chroma and SQLite data appear lost while writes begin elsewhere.
4. **Installed-directory permissions.** Current wheel defaults can fail only when a late writer attempts to create a directory or database.
5. **Two Chroma stores.** `data/chroma` and `data/vector_db` require independent inventory and validation despite sharing `soundbrain` as a default collection name.
6. **Persistence identity coupling.** Renaming `soundbrain`, engine keys, method IDs, or provider IDs during a root change can invalidate lookups, digests, comparisons, and serialized records.
7. **Source-marker ambiguity.** The nearest ancestor containing `configs/` can be selected even when it is not the intended project root.
8. **Escaping model path.** `../Models` is outside the selected root, so a root policy alone does not fully control runtime storage.
9. **Resource/config divergence.** Root YAML mirrors can drift from packaged resources even though they look like overrides.
10. **CWD-dependent loaders.** Knowledge and plugin registry defaults can resolve differently from the main settings root.
11. **Relative/invalid overrides.** Relative, whitespace, nonexistent, file, and unwritable environment values are accepted without clear validation.
12. **Concurrent migration.** Chroma and SQLite need locking and atomic migration semantics; a root rename alone provides neither.

## 7. Recommended migration strategy

This strategy should be reviewed and approved before implementation:

1. Freeze the R4 boundary to root identity and compatibility. Do not combine it with storage relocation, collection rename, engine-key rename, or serialized-schema changes.
2. Introduce `PHASENOX_ROOT` as the canonical read path with proposed precedence `PHASENOX_ROOT` > `NOISYNE_ROOT` > `SOUNDBRAIN_ROOT` > automatic discovery.
3. Retain both legacy variables for at least one deprecation window. When multiple variables are set to different resolved paths, emit an actionable warning or error rather than silently merging data.
4. Normalize and validate the selected root consistently. Specify handling for empty/whitespace values, relative paths, `~`, nonexistent roots, files, symlinks, and unwritable directories.
5. Keep the automatic fallback unchanged during R4 unless the team explicitly accepts a persistence migration. A user-data fallback is architecturally preferable, but adopting it is a storage move and belongs with R5 migration controls.
6. Make initialization order explicit: root selection must be final before importing the settings singleton or RAG persistence module.
7. Add diagnostics that report which variable/source selected the root without exposing unrelated environment values.
8. In R5, implement read-only discovery first, then copy/validate/switch/rollback. Never rename or delete the old store in place as the first step.
9. Treat the two Chroma stores and SQLite catalog as separate migration units. Preserve `soundbrain` until its own migration is designed.
10. Resolve the packaged-resource versus root-config contract and the CWD-dependent loader behavior as explicit configuration work, not incidental replacements.

## 8. Backward compatibility recommendation

Recommended future behavior:

- Canonical: `PHASENOX_ROOT`.
- Compatibility aliases: continue reading `NOISYNE_ROOT` and `SOUNDBRAIN_ROOT`.
- Proposed precedence: canonical first, then the current primary legacy name, then the older legacy name.
- Do not write environment variables on behalf of the user.
- Do not automatically move or delete legacy data in R4.
- If only a legacy variable is set, preserve today's resolved path exactly and optionally issue a targeted deprecation warning.
- If canonical and legacy variables resolve to the same normalized path, proceed without treating it as a conflict.
- If they resolve to different paths, report the selected source and the ignored conflicting values; consider a hard failure for commands that can write persistent state.
- Retain legacy support until telemetry/documented release policy shows it can be removed safely.

This approach preserves current deployments while making the canonical identity unambiguous. The precise warning and removal timeline remains a product decision.

## 9. Exact files for a future R4

### 9.1 Confirmed minimum for an environment-identity-only R4

Production:

- `phasenox/infrastructure/config/loader.py`

Tests:

- `tests/test_application_root.py`
- `tests/test_noisyne_phase5_release_alignment.py`
- `tests/test_noisyne_phase6_repository_freeze.py`

Technical documentation that currently states the legacy root contract:

- `README.md`
- `docs/README_v2.md`
- `docs/NOISYNE_TECHNICAL_RENAME_FREEZE.md`
- `docs/EXECUTION_PLAN_v2.md`
- `docs/ROADMAP_v2.md`
- `docs/MODULE_MAP.md`

The documentation set must be filtered to runtime/configuration guidance only; marketing/display branding remains out of scope.

### 9.2 Conditional files if R4 also changes initialization or runtime path policy

These files are not automatically in scope. They become affected only if R4 is approved to change path layout, validation, loader consistency, or disposable runtime labels:

- `phasenox/infrastructure/config/__init__.py`
- `phasenox/infrastructure/config/models.py`
- `phasenox/infrastructure/config/resources/runtime.yaml`
- `configs/runtime.yaml`
- `main.py`
- `phasenox/runtime/runtime.py`
- `phasenox/rag/vectordb.py`
- `phasenox/memory/vector/config.py`
- `phasenox/memory/vector/providers/chroma.py`
- `phasenox/audio/catalog/database.py`
- `phasenox/memory/loader.py`
- `phasenox/knowledge/loader.py`
- `phasenox/audio/plugin/registry.py`
- `phasenox/performance/benchmark_cli.py`
- `phasenox/performance/fixture_model.py`
- directly corresponding RAG, memory, config, packaging, performance, and application tests.

If the canonical installed default becomes a user directory, all persistence consumers in this conditional list must be treated as an R5-coordinated change rather than a simple R4 rename.

## 10. Test inventory

### 10.1 Existing coverage

`tests/test_application_root.py` covers:

- `NOISYNE_ROOT` override;
- `SOUNDBRAIN_ROOT` fallback;
- current precedence of `NOISYNE_ROOT` over `SOUNDBRAIN_ROOT`;
- source discovery through `pyproject.toml`;
- source discovery through `configs/`;
- synthetic installed-package fallback to `site-packages`.

Additional relevant coverage:

- `tests/test_noisyne_phase6_repository_freeze.py` verifies arbitrary checkout-directory behavior and clears both legacy variables.
- `tests/test_noisyne_phase5_release_alignment.py` freezes the documented legacy environment names.
- `tests/test_noisyne_phase3_namespace.py` checks packaged namespace/resources.
- `tests/test_noisyne_phase2_distribution.py` checks wheel contents and installed package behavior.
- `tests/test_memory_preflight.py` and memory loader/resolver tests cover memory bundle loading and preflight behavior.
- Knowledge loader tests cover bundle parsing but generally rely on repository-root current working directory.
- Plugin registry tests primarily use injected dictionaries or explicit paths.
- RAG/preflight tests cover the existing collection and client contract.
- Performance tests cover their fixture cache and CUDA environment manipulation.

### 10.2 Missing coverage

The following tests are required before or during R4:

1. Canonical `PHASENOX_ROOT` selection.
2. Full three-variable precedence matrix, including same-path and conflicting-path cases.
3. Empty and whitespace-only values.
4. Relative value/CWD behavior and the intended policy for it.
5. `~` expansion.
6. Nonexistent roots, regular-file roots, symlink roots, and unwritable roots.
7. Windows path case/normalization behavior.
8. Import-before-environment-change behavior for the settings singleton.
9. Root selection before importing the global RAG client.
10. Exact expanded values for model, cache, log, report, SQLite, and both Chroma paths.
11. Source-checkout and fresh-wheel parity for resource loading.
12. Fresh-wheel behavior from a non-repository CWD.
13. Clear failure behavior for writes under protected `site-packages`.
14. Legacy fallback warnings and any agreed deprecation policy.
15. Confirmation that `soundbrain` collections, engine keys, and persisted data remain unchanged in R4.
16. Confirmation that root-level YAML files are not treated as overrides unless a new override feature is explicitly designed.
17. Wheel tests for default memory, knowledge, and plugin registry resources, or explicit tests documenting that these defaults are unavailable.
18. No-creation-on-config-import and expected creation-on-first-writer tests.

### 10.3 Required R4 regression suites

At minimum, future R4 validation should include:

- application-root/config loader tests;
- package resource and distribution/fresh-install tests;
- application service and scheduler tests;
- RAG collection/preflight tests with the collection identity frozen;
- memory loader/vector-provider tests;
- audio catalog path tests;
- report output/atomic-write tests;
- performance cache tests if disposable cache identities are changed;
- a subprocess test that imports from a clean environment and reports the selected root before any persistent client is imported.

## 11. R4 guardrails

The future R4 implementation should explicitly prove:

- no Chroma collection rename;
- no Chroma, SQLite, model, report, or user-data migration;
- no engine-key or runtime-cache-key collateral rename unless separately approved;
- no package, distribution, CLI, public-class, desktop UI, asset, or display-branding changes;
- no duplicate configuration implementation;
- legacy variables continue to resolve the same paths during the compatibility window;
- no R5 work is bundled into the R4 commit.

## Audit disposition

Discovery found a small environment-variable entry point but a broad downstream path and persistence surface. The canonical variable can be introduced narrowly; changing the default storage root cannot. R4 should establish identity and precedence only. A per-user storage layout and existing-data transition require a separately designed R5 migration.
