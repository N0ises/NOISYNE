# PHASENOX R5 Persistence Migration Audit

Status: discovery only

Repository: `N0ises/NOISYNE`

Branch: `v2-development`

Audited HEAD: `e1559f48bb4fd17435dd84ec724b00a1ac345cc3` (R4)

Audit date: 2026-08-23

## Scope and conclusion

This document inventories persistence boundaries before a future R5 migration. No database, collection, schema, path, identifier, file, or production/test source was changed during discovery.

The repository has three application-managed durable stores:

1. a RAG Chroma database at `data/chroma`;
2. an independent memory/audio-vector Chroma database at `data/vector_db`;
3. an audio-index SQLite catalog at `data/index.db`.

It also emits user-owned JSON/Markdown reports and other caller-selected files. Runtime/model caches, logs, and in-memory job/model state are separate concerns and do not require data-schema migration.

The exact persisted compatibility collection is `soundbrain`. The supplied spelling `sounbrain` does not occur in the repository or inspected stores. `soundbrain` must not be renamed in place. If a future product decision requires a canonical collection name, R5 must use a versioned copy plus compatibility lookup and preserve the legacy collection through rollback and deprecation windows.

No persistence identity is technically required to change merely because the Python/runtime identity is now PHASENOX. A future R5 should migrate physical storage only if a new user-data location is approved. Logical identifiers should remain compatible unless each is separately versioned.

## 1. Current persistence architecture

### 1.1 Root selection

R4 established this application-root precedence in `phasenox/infrastructure/config/loader.py`:

1. `PHASENOX_ROOT`
2. `NOISYNE_ROOT`
3. `SOUNDBRAIN_ROOT`
4. automatic source/wheel discovery

All three durable stores are derived from the selected root. Their module constants or settings are evaluated at import time, so changing the environment after import does not redirect an already-created settings object, Chroma client, or SQLite path.

### 1.2 Store overview

| Store | Current default | Owner | Initialization | Workspace status at audit |
| --- | --- | --- | --- | --- |
| RAG Chroma | `<root>/data/chroma` | `phasenox/rag/vectordb.py` | Client and collection created at module import | One `soundbrain` collection, 745 records |
| Memory-vector Chroma | `<root>/data/vector_db` | `phasenox/memory/vector/` | Client created with provider; collection created with manager/collection | Three collections, seven records total |
| Audio catalog SQLite | `<root>/data/index.db` | `phasenox/audio/catalog/` | Directory, connection, and table created by `CatalogDatabase()` | Four catalog rows |
| Primary reports | configured `<root>/reports` or caller path | report/application layers | Created on export | Generated workspace reports exist |
| Reference reports | caller-selected output directory | `phasenox/reference/` | Created on export | JSON and Markdown outputs exist |
| Integration/evaluation files | caller-selected path | `phasenox/integration/`, `phasenox/evaluation/` | Created on export | Not centrally managed |

The live counts above are a read-only snapshot of ignored/tracked workspace artifacts, not a release invariant.

### 1.3 Repository ownership

- `data/chroma/` and `data/vector_db/` are Git-ignored.
- `data/index.db` is currently tracked in Git as a binary file. The audited copy contains four records. This is a source-control/privacy/reproducibility risk and must be addressed deliberately in R5, never by silently deleting it.
- Distribution tests explicitly reject `data/`, `.db`, `.sqlite`, and `.sqlite3` artifacts from wheels and sdists. Installed packages therefore begin without repository persistence contents.
- `reports/.gitkeep` is tracked; generated outputs are not distribution content.

## 2. RAG Chroma audit

### 2.1 Location and configuration

`ChromaConfig` in `phasenox/infrastructure/config/models.py` defaults to:

- path: `data/chroma`;
- collection: `soundbrain`.

`load_settings()` expands the Chroma path against the application root. `phasenox/rag/vectordb.py` then constructs `PersistentClient(path=...)`. Its additional `get_application_root() / settings.chroma.path` join is redundant when the setting is already absolute but currently resolves to the same path.

### 2.2 Creation and import lifecycle

Importing `phasenox.rag.vectordb` immediately:

1. imports Chroma;
2. opens or creates the persistent database;
3. constructs `QwenEmbeddingFunction`;
4. calls `get_or_create_collection()` for `settings.chroma.collection`;
5. binds the client and collection as module globals.

The embedding model itself is lazy: `QwenEmbeddingFunction.model` imports and resolves it only when embedding is requested. The persistence client and collection are not lazy. This means a seemingly read-only import can create files or mutate Chroma's internal migration state, and the selected root is frozen before application code can redirect it.

### 2.3 Collection contract

Source code requests:

- name: `soundbrain`;
- embedding function: Qwen text embeddings;
- HNSW distance metadata: `{"hnsw:space": "cosine"}`.

RAG records contain:

- deterministic ID: first 16 hexadecimal characters of SHA-256 of the source string, followed by `:<source_chunk_index>`;
- document: chunk text;
- metadata: at least `source` and `chunk_index`, normally also `page`;
- vector: produced by the configured Qwen embedding model.

The source string is normally a path. Moving or normalizing source documents changes both the metadata match and the ID fingerprint. Re-ingestion after such a move can leave the old source records alongside new ones because stale deletion filters on the exact previous source string.

### 2.4 Read/write lifecycle

Writes occur through `ingest_chunks()`:

1. group chunks by exact `source` metadata;
2. query existing records with `where={"source": source}`;
3. delete every returned ID for that source;
4. upsert deterministic IDs, documents, and metadata in batches.

Failure to query/delete stale records raises `IngestionError`; it does not report false success. The source replacement is not transactional across delete and upsert, so a failure after deletion can leave a source partially or completely absent.

Reads occur through the module-global collection in `phasenox/rag/retriever.py`. Query distances are converted with cosine scoring semantics and results are sorted descending.

### 2.5 Read-only live-store observation

The audited workspace's `data/chroma/chroma.sqlite3` and HNSW segment files were inspected in SQLite read-only URI mode; no Chroma client was opened against the store.

Observed:

- Chroma package in the audit virtual environment: `1.5.9`;
- application dependency: unbounded `chromadb` requirement;
- collection: `soundbrain`;
- dimension: 1024;
- records: 745;
- persisted vector distance space: `l2`, not cosine;
- embedding-function descriptor: legacy.

This is a critical pre-migration discrepancy. Fresh-collection tests require cosine, but `get_or_create_collection()` does not retrofit an existing collection's distance configuration. R5 must not silently convert or reinterpret this store. The team must choose separately between preserving existing L2 behavior or intentionally rebuilding/re-embedding into a versioned cosine collection and validating retrieval changes.

### 2.6 Existing RAG coverage

- `tests/test_rag_collection.py`: imports RAG components and the live default collection boundary.
- `tests/test_rag_preflight.py`: fresh temporary Chroma cosine metadata, retrieval score bounds/order, deterministic chunk IDs, idempotent re-ingestion, stale-source replacement, deletion-failure handling, and CWD-independent persistence paths.
- `tests/test_soundbrain_service_rag.py`: service behavior when RAG is empty.
- `tests/test_noisyne_phase4_identity.py`: freezes `ChromaConfig().collection == "soundbrain"`.
- `tests/test_noisyne_phase6_repository_freeze.py`: freezes the persisted `soundbrain` identity in documentation.

Coverage gap: `test_rag_collection.py` imports the production module without isolating its root, so it can open/create the repository store. There is no test for an existing collection whose distance configuration differs from the requested metadata.

## 3. Memory vector-store audit

### 3.1 Independence from RAG

The memory vector store is fully independent of the RAG store:

| Property | RAG | Memory vector |
| --- | --- | --- |
| Directory | `data/chroma` | `data/vector_db` |
| Client construction | module import | `ChromaProvider()` |
| Default collection | `soundbrain` | `soundbrain` |
| Embeddings | collection embedding function can create them | caller supplies embeddings |
| Main consumers | document ingestion/retrieval | audio memory/search and generic vector manager |

Sharing the default collection name does not make these databases interchangeable. They have separate SQLite files, collection UUIDs, HNSW segments, dimensions, and record populations.

### 3.2 Location and creation flow

`phasenox/memory/vector/config.py` defines:

- `DEFAULT_PROVIDER = "chroma"`;
- `DEFAULT_COLLECTION = "soundbrain"`;
- `PERSIST_DIRECTORY = <root>/data/vector_db`.

`PERSIST_DIRECTORY` is calculated at import. `ChromaProvider()` opens a persistent client with anonymized telemetry disabled. `VectorManager()` constructs `VectorDatabase`, selects the registered provider, and constructs `VectorCollection`, whose initializer calls `get_or_create_collection(name)`.

The provider exposes create, get, delete, add, upsert, update, query, and count. `VectorManager.add()` deliberately uses upsert for idempotent record IDs.

### 3.3 Collection and record identities

The default generic collection is `soundbrain`, but callers can provide any collection. `CollectionNames` derives names as:

- `audio_<model-with-slashes-replaced-by-underscores>_<dimension>`;
- `text_<model-with-slashes-replaced-by-underscores>_<dimension>`.

`AudioMemory` selects an audio collection from the actual embedding model name and vector dimension. `AudioSearchService` defaults to `audio_clap_512`.

Vector records contain:

- caller-defined `id`;
- explicit vector;
- arbitrary metadata;
- optional document.

For indexed audio, the ID is the SHA-256 file-content hash. Metadata contains filename, stem, extension, parent directory name, and path. Changing model names, dimensions, collection naming, or path normalization can create parallel collections or stale metadata rather than updating existing records.

### 3.4 Read-only live-store observation

The audited workspace's memory-vector store contains:

| Collection | Dimension | Records | Persisted space |
| --- | ---: | ---: | --- |
| `audio_clap_512` | 512 | 5 | L2 |
| `soundbrain` | 1024 | 1 | L2 |
| `text_bge-m3_1024` | 1024 | 1 | L2 |

R5 must enumerate and migrate every collection. Migrating only `DEFAULT_COLLECTION` would lose the two model-qualified collections.

### 3.5 Existing memory-vector coverage

- `tests/test_vector_preflight.py`: fake-provider proof that repeated `VectorManager.add()` calls use upsert.
- `tests/test_rag_preflight.py`: absolute/CWD-independent `PERSIST_DIRECTORY` checks.
- `tests/test_noisyne_phase4_identity.py`: freezes `DEFAULT_COLLECTION == "soundbrain"`.
- memory loader/registry/resolver/service/preflight tests cover YAML-backed preference/configuration memory, not Chroma persistence.
- Sprint 13 tests cover knowledge/memory contract round trips and supersession, not the Chroma store.

There is no real temporary-Chroma lifecycle test for the memory provider, no all-collection inventory test, and no migration/restore test.

## 4. SQLite and file-storage audit

### 4.1 Audio catalog SQLite

`phasenox/audio/catalog/database.py` owns `data/index.db`. `CatalogDatabase()`:

1. creates the parent directory;
2. opens a default SQLite connection;
3. runs `CREATE TABLE IF NOT EXISTS indexed_audio`;
4. commits.

Schema:

| Column | Type/constraint | Meaning |
| --- | --- | --- |
| `file_hash` | `TEXT PRIMARY KEY` | SHA-256 of audio file contents |
| `path` | `TEXT NOT NULL` | source audio path |
| `modified_time` | `REAL NOT NULL` | file modification time |
| `embedding_model` | `TEXT NOT NULL` | model label, currently `clap` in the live catalog |

There are no application migrations, schema-version table, `PRAGMA user_version` management, secondary indexes, foreign keys, explicit close/context-manager API, WAL policy, or backup API. The audited database reports `user_version = 0`.

`AudioCatalog.exists()` checks only `file_hash`. `AudioCatalog.add()` uses positional `INSERT OR REPLACE` without an explicit column list and commits immediately. A schema column reorder/addition could therefore break writes unless the repository is changed first.

### 4.2 Coupling to audio vectors

`AudioIndexer` computes a file hash, writes the audio vector through `AudioPipeline`/`AudioMemory`, and only then inserts the catalog row. These writes cross two databases and are not transactional.

Consequences:

- a crash after vector upsert but before catalog insert leaves an orphan vector;
- a catalog write failure causes the next run to upsert the vector again, then retry the catalog;
- moving an audio file does not update an existing catalog row because the same content hash is considered already indexed;
- paths are stored both in SQLite and vector metadata.

The live snapshot contains four catalog rows but five records in `audio_clap_512`. This may reflect a crash, test/manual data, or another writer; it proves that migration validation cannot assume one-to-one counts without defining reconciliation rules.

### 4.3 Reports and serialized files

`phasenox/report/exporter.py` creates JSON atomically by writing a temporary file in the target directory and replacing the destination. It serializes stable field names for metadata, analysis, intelligence, engineering, mix intelligence, plugin intelligence, recommendations, and summary.

`phasenox/reference/report_builder.py` writes JSON and Markdown directly after creating parents; those writes are not atomic. Integration adapters and evaluation reports also write directly to caller-selected paths. Performance results can be written as JSON bytes to a caller-selected output.

These files are user-owned artifacts rather than indexed application databases. R5 should leave them in place by default. If a user-data root move includes managed reports, copy files byte-for-byte with hashes; do not rewrite their schemas or embedded identities as part of path migration.

### 4.4 No other application database framework

No other production `sqlite3` usage, `.db` schema owner, pickle/shelve persistence, migration framework, backup command, rollback command, integrity checker, or split-brain detector was found. Chroma's internal `migrations` table belongs to Chroma and is not an application migration system.

Job history and the runtime model cache are in memory only. YAML memory/knowledge bundles are packaged or repository configuration, not a mutable persistence backend.

## 5. User-data locations

### 5.1 Source checkout

With automatic source discovery at this workspace:

| Purpose | Location |
| --- | --- |
| RAG Chroma | `E:\Build\NOISYNE\data\chroma` |
| Memory vector Chroma | `E:\Build\NOISYNE\data\vector_db` |
| Audio catalog | `E:\Build\NOISYNE\data\index.db` |
| General/model cache | `E:\Build\NOISYNE\data\cache` and `data\cache\models` |
| Reports | `E:\Build\NOISYNE\reports` |
| Logs | `E:\Build\NOISYNE\logs` |
| Model root | `E:\Build\Models` because packaged config uses `../Models` |

The `data/` tree also contains audio, courses, documents, knowledge, manuals, and transcripts. Those are input/reference data, not all application-created persistence. R5 inventory must distinguish user sources from generated indexes.

### 5.2 Wheel installation

Without an environment override, the installed package fallback is the parent of `phasenox`, normally `<environment>/Lib/site-packages` on Windows:

- RAG: `<site-packages>/data/chroma`;
- memory vectors: `<site-packages>/data/vector_db`;
- catalog: `<site-packages>/data/index.db`;
- cache/logs/reports: `<site-packages>/data/cache`, `<site-packages>/logs`, and `<site-packages>/reports`;
- models: `<environment>/Lib/Models` because `../Models` escapes `site-packages`.

Fresh distributions contain none of the stores. They are created by later imports/operations. System installations may make these locations unwritable.

### 5.3 Explicit root

For any selected `PHASENOX_ROOT`, `NOISYNE_ROOT`, or `SOUNDBRAIN_ROOT` value `<explicit-root>`:

- RAG: `<explicit-root>/data/chroma`;
- memory vectors: `<explicit-root>/data/vector_db`;
- catalog: `<explicit-root>/data/index.db`;
- caches: `<explicit-root>/data/cache`;
- logs/reports: `<explicit-root>/logs`, `<explicit-root>/reports`;
- models: the normalized result of `<explicit-root>/../Models` under current packaged configuration.

There is still no AppData/LocalAppData platform policy. Multiple environment variables can point at dormant legacy roots even though R4 selects only one winner; a future migration inventory must inspect every distinct configured and automatic root before choosing a source.

## 6. Serialized identity audit

### Classification A — migrate physical data if a new storage root is approved

| Boundary | Migration requirement |
| --- | --- |
| `data/chroma` | Copy/validate the complete Chroma store or logically copy every collection/record; do not copy only SQLite without HNSW segment files |
| `data/vector_db` | Migrate all discovered collections, including model-qualified names |
| `data/index.db` | Snapshot with SQLite-safe tooling, preserve schema/rows, then reconcile with audio vectors |
| Managed report directory | Optional byte-for-byte copy only if R5 adopts a new managed report root |
| Stored source paths | Transform only if the underlying source files also move and an explicit mapping is supplied |

If R5 does not change the physical storage root, none of these stores requires migration solely for branding.

### Classification B — must remain compatible

| Identity | Why it is compatibility-sensitive |
| --- | --- |
| Chroma collection `soundbrain` | Existing collection lookup; present independently in both stores |
| `audio_<model>_<dimension>` / `text_<model>_<dimension>` | Selects model-specific vector spaces; renaming creates parallel empty collections |
| RAG chunk IDs and exact `source` metadata | Drive stale deletion, idempotency, and record identity |
| Audio file SHA-256 IDs | Join concept between catalog and audio vectors |
| Catalog `embedding_model` and vector model/dimension | Determines whether existing embeddings are semantically reusable |
| Engine keys `noisyne` and `soundbrain` | Runtime/API compatibility; not currently a disk-store selector |
| Provider identities such as `noisyne.in_memory_memory_store` and `noisyne.deterministic_reasoning` | Serialized contract provenance |
| `noisyne.*` method IDs | Embedded throughout perception/reference results and validation records |
| Schema versions | Define interpretation of serialized contract payloads |
| Source/fact digests, fact IDs, issue IDs, reasoning request IDs | Hash canonical JSON that includes method/schema identities; renames change hashes |
| JSON field names and pickle compatibility paths | Existing artifacts/consumers depend on them |
| Model IDs/revisions | Define embedding/vector compatibility and runtime model identity |

Legacy identifiers may be presented through canonical aliases in new APIs, but stored historical values must remain readable and comparable. Introducing canonical method/provider IDs requires a new schema/method version and explicit translation rules; overwriting old values would invalidate digests.

### Classification C — safe disposable or rebuildable with policy approval

| Boundary | Treatment |
| --- | --- |
| In-memory `ModelCache` | Process-local; no migration |
| In-memory job active/history state | Process-local; no migration |
| `data/cache` and model download cache | Rebuild/redownload; optionally retain for performance, never treat as authoritative |
| `.noisyne_performance_*` fixture caches | Test/benchmark artifacts; delete/rebuild only in a separately authorized cleanup |
| Atomic report `.tmp` files left after abnormal termination | Disposable after confirming no live writer |
| Logs | No schema migration; retain/archive according to support and privacy policy rather than assuming they are disposable |

The user-managed model root is not a disposable cache by default. It can contain locally supplied weights and should be left or explicitly referenced from the new configuration.

## 7. Migration boundaries and risks

### Hard boundaries

R5 must not combine these independent decisions:

1. physical root relocation;
2. Chroma library/database-format upgrade;
3. collection rename;
4. distance-metric correction;
5. embedding-model change/re-embedding;
6. serialized method/provider/schema rename;
7. source-file path relocation.

Each changes different compatibility properties. Combining them makes validation and rollback ambiguous.

### Principal risks

1. **Import-time writes.** Importing RAG persistence can create/open/migrate the source before backup or root selection is finalized.
2. **Split-brain roots.** Canonical, two legacy variables, checkout defaults, and old wheel `site-packages` roots can all contain different stores.
3. **Partial Chroma copy.** Chroma uses SQLite plus UUID-named HNSW segment files; copying only one component corrupts the logical store.
4. **Unpinned Chroma format.** `chromadb` is unbounded, so source and target tools may run different internal migrations.
5. **Distance mismatch.** Live RAG uses L2 while source/tests expect cosine; an unnoticed rebuild changes ranking and score meaning.
6. **Embedding mismatch.** RAG does not persist a clear application-level embedding model/revision manifest. Same-dimensional vectors from different models are not interchangeable.
7. **Non-transactional RAG replacement.** Delete-before-upsert can lose source records on interruption.
8. **Non-transactional catalog/vector writes.** SQLite and vector data can diverge; the live counts already differ.
9. **Path-bearing identities.** RAG IDs and stale filters derive from source strings; audio metadata/catalog rows also store paths.
10. **Digest invalidation.** Renaming method/provider IDs changes canonical JSON hashes and downstream IDs.
11. **Tracked live database.** `data/index.db` in Git can leak workstation paths and can be overwritten by checkout/merge operations.
12. **Open Windows handles.** Global Chroma clients and unclosed SQLite connections can prevent atomic directory/file replacement.
13. **Cross-volume switching.** Filesystem rename is not atomic across volumes; staging must occur on the target volume.
14. **No migration journal.** The application has no lock, manifest, checkpoint, dual-write, or resume mechanism.
15. **Report overwrite.** Reference/integration/evaluation writers are not uniformly atomic.

## 8. Recommended R5 strategy

This is a recommendation for a future implementation, not a migration performed by this audit.

### Phase 0 — decisions and freeze

1. Decide whether a physical user-data root is actually changing. If not, preserve all stores and identities.
2. Freeze Chroma version and embedding model/revision for the migration.
3. Decide the L2-versus-cosine discrepancy separately. A metric correction is a rebuild, not a path migration.
4. Define whether reports and local models are managed data or external/user-owned files.
5. Require a maintenance window. Existing code cannot provide safe zero-downtime dual writes.

### Phase 1 — read-only inventory

Build a migration command that does not import `phasenox.rag.vectordb`. It should:

- resolve and enumerate every distinct canonical, legacy, automatic-checkout, and known wheel root;
- identify both Chroma directories, catalog SQLite, reports, caches, and model root;
- record application/Chroma/Python versions;
- inventory every Chroma collection, dimension, distance space, embedding descriptor, record count, IDs, documents, metadata, and vector dimensions;
- record SQLite schema SQL, `user_version`, integrity result, row count, key set, and embedding-model distribution;
- reconcile catalog file hashes with audio collection IDs;
- emit a signed/hashed manifest without opening stores for writing.

### Phase 2 — backup

1. Stop all application writers and acquire an exclusive migration lock.
2. Close Chroma clients and SQLite connections.
3. Use a cold, complete directory copy for each Chroma store, including SQLite and every segment directory. Hash every file into the manifest.
4. Use SQLite's backup API or `VACUUM INTO` for `index.db`; do not raw-copy a live database.
5. Copy user-managed report files only if they are in scope, preserving relative paths and hashes.
6. Store backups outside both source and target roots and mark them read-only where practical.

### Phase 3 — staged migration

Stage on the target filesystem under a unique temporary directory. Prefer a same-version cold copy for a pure path relocation. If logical copying is required:

- use public Chroma APIs in bounded batches;
- create collections with the exact source dimension and distance configuration;
- preserve names, IDs, embeddings, documents, metadata, and model identity;
- migrate all collections, not just `soundbrain`;
- never mutate Chroma's internal SQLite tables directly;
- copy SQLite with its existing schema before introducing any versioned schema evolution;
- apply explicit path mappings only where users approved source-file moves.

Do not create a new canonical collection name during the same operation. Chroma has no native collection alias; an application compatibility locator can prefer a future canonical collection and fall back read-only to `soundbrain`, but exactly one location must be writable.

### Phase 4 — validation

Before switching:

- verify backup hashes and target file hashes;
- run Chroma collection count and exact ID-set comparisons;
- verify vector dimensions, documents, metadata, and sampled/full vector equality as scale permits;
- run fixed-query parity tests with distance/ranking tolerances appropriate to the preserved metric;
- run `PRAGMA integrity_check` for SQLite;
- compare SQLite schema, `user_version`, row count, file-hash set, model labels, and mapped paths;
- reconcile catalog rows with the appropriate audio-vector collection and report every orphan;
- load representative historical JSON/pickle artifacts and recompute frozen digests;
- confirm `soundbrain` remains readable in both independent databases;
- test from a fresh process rooted only at the staged target.

### Phase 5 — atomic switch and split-brain prevention

1. Keep writers stopped and stage on the target volume.
2. Atomically rename a completed target directory into place or atomically replace a small root-pointer/configuration file.
3. Write a completion marker containing the source/target manifest hashes and migration version.
4. Make the old root read-only or place a redirect/tombstone that refuses writes and names the active root.
5. Start exactly one writer and verify it reports the active root/manifest.
6. Scan known roots on every startup during the compatibility window; refuse writes when divergent active stores are detected.

### Rollback

Before writes resume, rollback is an atomic pointer/directory switch back to the validated source. Keep the source and backups untouched.

After writes resume, switching back would discard new data. Safe rollback then requires either:

- a write journal/dual-write mechanism implemented and tested before cutover; or
- stopping writers and reverse-migrating the new records into a restored source.

Because neither mechanism exists today, the recommended first R5 uses a maintenance window and completes full validation before releasing writes. Preserve old stores for a defined rollback period; delete nothing automatically.

## 9. Required implementation files for future R5

Final scope depends on whether R5 relocates the physical root. The minimum recommended implementation surface is:

### New migration boundary

- `phasenox/infrastructure/persistence/__init__.py`
- `phasenox/infrastructure/persistence/inventory.py`
- `phasenox/infrastructure/persistence/manifest.py`
- `phasenox/infrastructure/persistence/locking.py`
- `phasenox/infrastructure/persistence/backup.py`
- `phasenox/infrastructure/persistence/migrate.py`
- `phasenox/infrastructure/persistence/validate.py`

These proposed modules keep migration tooling independent from import-time production clients.

### Existing production boundaries requiring controlled changes

- `phasenox/infrastructure/config/loader.py`
- `phasenox/infrastructure/config/models.py`
- `phasenox/infrastructure/config/resources/runtime.yaml` only if explicit persistence paths are added
- `phasenox/rag/vectordb.py`
- `phasenox/rag/ingestion.py`
- `phasenox/memory/vector/config.py`
- `phasenox/memory/vector/providers/chroma.py`
- `phasenox/memory/vector/collection.py`
- `phasenox/memory/vector/manager.py`
- `phasenox/memory/vector/naming.py`
- `phasenox/audio/catalog/database.py`
- `phasenox/audio/catalog/repository.py`
- `phasenox/audio/indexer/indexer.py`
- `phasenox/audio/memory.py`
- `phasenox/audio/search/service.py`
- `pyproject.toml` if the Chroma version is constrained for migration safety

Conditional only if reports move:

- `phasenox/report/exporter.py`
- `phasenox/reference/report_builder.py`
- `phasenox/reference/pipeline.py`
- `phasenox/integration/base.py`
- `phasenox/evaluation/report.py`

Required operational documentation:

- an R5 migration runbook covering discovery, backup, dry run, cutover, rollback, and support diagnostics;
- a persistence compatibility matrix for roots, collection names, store versions, schema versions, and supported rollback paths.

## 10. Test coverage audit

### Existing coverage

| Area | Existing tests | What is covered |
| --- | --- | --- |
| RAG collection/import | `test_rag_collection.py` | Import boundary and callable access |
| RAG behavior | `test_rag_preflight.py` | Fresh cosine collection, scoring, ingestion idempotency, stale cleanup, path stability |
| Persisted identity | `test_noisyne_phase4_identity.py`, `test_noisyne_phase6_repository_freeze.py` | `soundbrain` default frozen |
| Memory vectors | `test_vector_preflight.py` | Fake-provider upsert behavior |
| Memory YAML/contracts | memory tests, Sprint 13 | Config-backed profiles, resolution, serialization/supersession |
| Root selection | `test_application_root.py` | Canonical/legacy precedence and discovery |
| Distribution | `test_noisyne_phase2_distribution.py` | Persistence artifacts excluded from wheel/sdist; fresh installation |
| Serialized contracts | perception/application/Sprint 12–16 tests | JSON-safe serialization, schema/method constraints, deterministic digests/round trips |
| Reports | reference/integration/application tests | Output creation and selected JSON content |
| Legacy pickle | `test_noisyne_phase3_namespace.py` | One legacy module-path pickle compatibility case |

### Missing tests required before R5

1. Read-only inventory across canonical, both legacy, automatic source, and simulated wheel roots.
2. No-write proof for inventory/dry-run, including file hashes and modification timestamps.
3. Isolated RAG import test proving no production-root database is touched.
4. Existing-collection configuration test showing requested metadata does not silently change L2/cosine behavior.
5. Migration policy test for the observed L2-versus-cosine discrepancy.
6. RAG cold backup/restore and logical copy with exact IDs, embeddings, documents, metadata, dimension, and collection configuration.
7. Interrupted RAG delete/upsert recovery.
8. Memory-provider tests using a real temporary Chroma store.
9. All-collection memory migration, including `soundbrain`, audio, text, and arbitrary custom collections.
10. Model-name/dimension compatibility and re-embedding rejection tests.
11. SQLite schema, CRUD, close, concurrent access, `integrity_check`, backup/restore, and `user_version` tests.
12. Catalog/vector reconciliation tests for missing rows, orphan vectors, stale paths, changed mtimes, and model changes.
13. Tracked `data/index.db` removal/ignore policy test once an approved safe migration exists.
14. Migration manifest determinism and file-hash verification.
15. Resume behavior after interruption at every migration checkpoint.
16. Same-volume atomic switch and explicit cross-volume refusal/staging behavior.
17. Split-brain detection and single-writer enforcement.
18. Rollback before writes and rollback/reverse-migration after new writes.
19. Legacy `soundbrain` lookup after cutover and throughout the compatibility window.
20. Historical JSON/pickle golden fixtures across schema/method/provider aliases.
21. Frozen digest equality for all historical schemas and deliberate inequality only for new versioned schemas.
22. Source-path mapping tests ensuring RAG stale records and audio metadata are not duplicated.
23. Report byte-copy/hash validation if reports are included.
24. Fresh-wheel migration from an old `site-packages` root into the approved target root.
25. Chroma-version compatibility matrix tests using the exact supported source and target versions.

## Audit disposition

The persistence surface is small in number of stores but tightly coupled through import-time initialization, path-derived identities, embedding semantics, and non-transactional cross-store writes. The safest future R5 is a physical relocation with frozen logical identities, a cold backup, a manifest-driven staged copy, and one atomic single-writer cutover. Collection, metric, model, and serialized-identity changes must remain separate versioned migrations.
