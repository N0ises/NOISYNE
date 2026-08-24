# PHASENOX Sprint 18A Desktop Identity and Data Migration Audit

## Executive decision

**GO for a narrowly scoped Sprint 18B, subject to one ordering constraint:**
Sprint 18B must establish a durable Data Root selection contract before changing
the Qt application identifier from `soundbrain.desktop` to
`phasenox.desktop`.

Changing the identifier alone is unsafe. On Windows it changes
`QStandardPaths.AppLocalDataLocation`; in a packaged process Sprint 17 also sets
`PHASENOX_ROOT` to that Qt-derived directory. A naive rename would therefore
fork both the small Desktop session and every relative backend path into a new,
empty root on `C:`. It could create new Chroma/SQLite stores and trigger model
redownloads while the original data remained intact but undiscovered.

The recommended long-term strategy is option **D implemented through C**:
canonical public and Qt identity `phasenox.desktop`, a one-time copy-first
migration of small Desktop state, and a hidden deterministic compatibility
lookup for the old state. Backend data is not moved. A small canonical AppData
pointer preserves the selected backend Data Root, including an existing legacy
root or a user-selected non-system drive.

This document is design only. No identifier, file, directory, environment,
store, installer behavior, production code, or test was changed.

## Audit baseline and observed machine

| Item | Audited value |
| --- | --- |
| Branch | `v2-development` |
| HEAD | `5addaf64055e99faa2584c5f6a4c0c8f9adffc92` |
| Public product | `PHASENØX` |
| ASCII/package identity | `PHASENOX` / `phasenox` |
| Current Desktop application identifier | `soundbrain.desktop` |
| Proposed Desktop application identifier | `phasenox.desktop` |
| Organization | `PHASENOX` |
| Organization domain | empty / not set |
| Frozen Desktop local and remote ref | `e2dd11e4193f32cd4f31cda5bca8cbd322bec3af` |

Read-only Qt probes were run for both application names. The probe called only
`QStandardPaths.writableLocation`; it did not create either directory. The
existing roots were then inventoried without reading personal path values from
the session.

On the audited Windows account:

- `%LOCALAPPDATA%` is `C:\Users\Hamid\AppData\Local`;
- the legacy root exists and contains two files totalling 340 bytes;
- `state/session-v1.json` is schema 2 and 340 bytes;
- `logs/desktop.log` exists and is currently empty;
- the canonical `phasenox.desktop` directory does not exist;
- the legacy Desktop cache, reports, and sibling `Models` paths do not exist.

This observed state is not assumed for other installations; the migration
matrix covers every combination.

## 1. Current Desktop identity and path behavior

### Identity initialization

`phasenox/ui/branding.py` returns:

| Metadata field | Current value |
| --- | --- |
| `display_name` | `PHASENØX` |
| `application_title` | `PHASENØX` |
| `ascii_name` | `PHASENOX` |
| `technical_identity` | `PHASENOX` |
| `organization_name` | `PHASENOX` |
| `organization_domain` | `None` |
| `application_id` | `soundbrain.desktop` |
| version | `importlib.metadata.version("phasenox")` |

`phasenox/ui/app.py:create_application()` then applies:

1. `QCoreApplication.setApplicationName(metadata.application_id)`;
2. `QApplication.setApplicationDisplayName(metadata.display_name)`;
3. `QCoreApplication.setApplicationVersion(metadata.version)`;
4. `QCoreApplication.setOrganizationName(metadata.organization_name)`;
5. organization domain only when non-empty.

Thus the visible name is already PHASENØX, but the filesystem identity remains
legacy. The application ID is not a second Qt property: it is passed as Qt's
application name and is separately frozen in `DESKTOP_APPLICATION_ID`.

### Verified Windows QStandardPaths

| Qt location | `soundbrain.desktop` | `phasenox.desktop` |
| --- | --- | --- |
| `AppLocalDataLocation` | `C:\Users\Hamid\AppData\Local\PHASENOX\soundbrain.desktop` | `C:\Users\Hamid\AppData\Local\PHASENOX\phasenox.desktop` |
| `AppDataLocation` | `C:\Users\Hamid\AppData\Roaming\PHASENOX\soundbrain.desktop` | `C:\Users\Hamid\AppData\Roaming\PHASENOX\phasenox.desktop` |
| `CacheLocation` | `C:\Users\Hamid\AppData\Local\PHASENOX\soundbrain.desktop\cache` | `C:\Users\Hamid\AppData\Local\PHASENOX\phasenox.desktop\cache` |
| `ConfigLocation` | `C:\Users\Hamid\AppData\Local\PHASENOX\soundbrain.desktop` | `C:\Users\Hamid\AppData\Local\PHASENOX\phasenox.desktop` |
| `TempLocation` | `C:\Users\Hamid\AppData\Local\Temp` | unchanged |

The Desktop uses only `AppLocalDataLocation` directly. It does not use
`QSettings`, `AppDataLocation`, `CacheLocation`, or a roaming profile.

### Current derived layout

For legacy root `<legacy>` equal to the current `AppLocalDataLocation`:

| Artifact | Current path |
| --- | --- |
| Session | `<legacy>/state/session-v1.json` |
| Corrupt-session quarantine | `<legacy>/state/session-v1.corrupt-<UTC timestamp>.json` |
| Desktop log | `<legacy>/logs/desktop.log` |
| Declared Desktop cache | `<legacy>/data/cache` |
| Declared reports | `<legacy>/reports` |
| Declared models | `<legacy>/../Models` (the organization-level `PHASENOX/Models`) |

`initialize_user_directories()` creates all six layout directories, but it is
called only by `prepare_packaged_runtime()` when `sys.frozen` is true. In a
source checkout, Qt state/logging still use AppLocalData, while backend config
continues to resolve from explicit environment variables or source discovery.

### Current packaged coupling

On a frozen launch, `prepare_packaged_runtime()` currently performs:

```text
PHASENOX_ROOT := <current Qt AppLocalDataLocation>  (setdefault)
```

Relative packaged settings then resolve as:

| Backend artifact | Current packaged path |
| --- | --- |
| RAG Chroma | `<legacy>/data/chroma` |
| Memory vector Chroma | `<legacy>/data/vector_db` |
| SQLite audio catalog | `<legacy>/data/index.db` |
| General cache | `<legacy>/data/cache` |
| Model cache | `<legacy>/data/cache/models` |
| Reports | `<legacy>/reports` |
| Backend logs | `<legacy>/logs` |
| Models | `<legacy>/../Models` |

This is the critical migration boundary. `DesktopPathLayout` currently groups
small UI state and backend-owned paths, but ownership is not actually unified.

## 2. Proposed canonical identity

Sprint 18B should set:

```text
organization name: PHASENOX
Qt application name / Desktop application ID: phasenox.desktop
application display name: PHASENØX
package/distribution: phasenox
```

The resulting canonical Windows small-state root is:

```text
%LOCALAPPDATA%\PHASENOX\phasenox.desktop
```

The new identifier must become active only after pre-bootstrap discovery has
selected a safe Desktop session source and a backend Data Root. This is not a
reason to keep the legacy identifier indefinitely; it is a reason to make the
cutover transactional and compatible.

## 3. Desktop-owned data inventory

Categories: A authoritative user data, B useful user state, C rebuildable
cache, D logs/support data, E transient/disposable.

| Item | Category | Current / proposed path | Expected size | Migration and conflict policy | Rollback importance |
| --- | --- | --- | --- | --- | --- |
| Session JSON | B | `<legacy>/state/session-v1.json` -> `<canonical>/state/session-v1.json` | Usually KiB; bounded recents (20 each) | Eligible for byte-for-byte copy after schema/read/hash validation; never overwrite divergent canonical state | High for continuity, not source media |
| Corrupt session backups | B/D | Legacy `state/*.corrupt-*.json` | Usually KiB | Leave at legacy location; optionally surface path for recovery; do not copy automatically | Medium |
| Desktop log | D | `<legacy>/logs/desktop.log`; new log at `<canonical>/logs/desktop.log` | Currently unbounded | Do not merge/copy an active log; leave legacy log as support archive and start canonical log | Low/medium for diagnostics |
| Session save temporary | E | sibling `.<session>.…tmp` | Session-sized | Ignore stale temp unless an explicit interrupted-migration record owns it; safe cleanup only after age/ownership validation | None |
| In-memory presentation/UI state | E until saved | Process memory | Small | Only allowlisted `SessionState` fields persist | None |
| Current operation and Task Center history | E | Memory only | Bounded memory | Not serialized and not migrated | None |
| Navigation and recent selections | B | Inside session JSON | Small | Migrates with the session | Medium |
| Window geometry/preferences | E/not implemented | None | None | No migration; no `QSettings` or geometry persistence exists | None |
| Desktop-specific cache | C/not currently written | Declared `<legacy>/data/cache` | Potentially large | Do not treat as Desktop state; it is currently the backend cache path | Low, but redownload cost can be high |
| Packaging probe result | A if user retains it | Explicit caller path | Small | External/caller-owned; never migrate automatically | User-dependent |
| Actual analysis/reference reports | A | Caller-selected path or backend Data Root | Small to large | Session stores descriptors only; preserve files in place | High |
| Input/reference audio | A | Arbitrary user paths | Potentially very large | Never copy; session retains absolute references only | Highest |

The only automatic Desktop-owned content migration recommended for 18B is the
valid session file. Logging cutover and the marker/pointer are new small-state
operations, not broad directory migration.

## 4. Backend persistence boundary

Sprint 18B must not copy, rename, initialize, merge, or validate by opening a
write-capable client for:

- RAG Chroma, including collection `soundbrain`;
- memory/vector Chroma and its collection identities;
- `data/index.db` SQLite catalog;
- embeddings, vector IDs, provider IDs, method IDs, or digests;
- models or user-supplied model overrides;
- general/model caches;
- backend reports or logs;
- runtime/engine keys;
- any path selected by `PHASENOX_ROOT`, `NOISYNE_ROOT`, or `SOUNDBRAIN_ROOT`.

The R5.1 inventory/manifest/validation/backup/locking abstractions are useful for
a later full Data Root move, but they are not integrated with writers and are
too broad for a small Desktop session cutover. Sprint 18B may reuse their
principles, not invoke a production persistence migration.

For an upgraded packaged installation whose old Qt root contains backend data,
18B should write a canonical small metadata pointer back to that unchanged
legacy directory and continue setting `PHASENOX_ROOT` to it. The fact that the
path contains `soundbrain.desktop` is a compatibility location, not a license
to rename it.

## 5. Install location versus Data Root policy

### Recommended policy: option 1, explicit hybrid

Use three independent locations:

| Layer | Policy |
| --- | --- |
| Install location | Immutable application binaries/resources; selected by installer; never a writable-data fallback |
| PHASENOX Data Root | Explicit durable pointer to user-managed large/persistent data; may be on `D:`, `E:`, removable media, or a network path |
| Small per-user state | Canonical Qt AppLocalData root for session JSON, Data Root pointer, migration marker/lock, and size-bounded Desktop logs |

Do not use one unified AppData root: it silently consumes `C:` and conflates
small UI state with models/vector stores. Do not default to install-drive-relative
data: Program Files-style locations may be read-only, and application updates
must not own user data. The installer's selected drive can be offered as the
default choice, but the stored Data Root must be explicit.

### Minimum Data Root pointer contract

Recommended canonical file:

```text
<canonical>/state/data-root.json
```

Minimum fields:

```json
{
  "schema_version": 1,
  "path": "E:\\PHASENOX Data",
  "selection_source": "user|legacy_upgrade|environment|installer",
  "selected_at": "UTC ISO-8601"
}
```

It must be written atomically, readable before backend config import, and must
not contain credentials. An optional stable root marker inside a managed Data
Root can identify that root, but 18B must not add markers inside external roots
without explicit ownership/permission.

### Selection precedence

At Desktop startup, before backend writers initialize:

1. non-empty explicit `PHASENOX_ROOT`;
2. valid canonical `data-root.json`;
3. an explicitly confirmed legacy-upgrade Data Root;
4. `NOISYNE_ROOT` legacy environment fallback;
5. `SOUNDBRAIN_ROOT` legacy environment fallback;
6. clean-install selection flow or temporary session mode.

Conflicting environment/pointer values must be reported. Canonical environment
continues to win, consistent with R4, but the Desktop must not silently rewrite
the pointer merely because an environment override is active.

## 6. Legacy discovery

Discovery must inspect only deterministic locations:

- Qt legacy AppLocalData location for organization `PHASENOX`, application
  `soundbrain.desktop`;
- Qt canonical AppLocalData location for `phasenox.desktop`;
- non-empty `PHASENOX_ROOT`, `NOISYNE_ROOT`, `SOUNDBRAIN_ROOT`;
- canonical/legacy Data Root pointer files if defined;
- a known source/install root only when already provided by the running package
  or installer metadata.

Do not recursively scan drives, user profiles, `site-packages`, old virtual
environments, network shares, or removable volumes. Historical roots without a
known pointer are discoverable only through an explicit Locate action.

The pre-bootstrap resolver should obtain both Qt paths before the canonical
application identity becomes authoritative for the process. It must not toggle
Qt identity after windows, logging, or `QSettings` consumers start.

## 7. Migration decision matrix

“Valid” means a readable supported schema and a successful read-only parse.
Identity is not embedded in the current session.

| Legacy state | Canonical state | Marker | Action |
| --- | --- | --- | --- |
| Absent | Absent | Absent | Clean first launch; create canonical small-state root only. Require Data Root selection before large backend use. |
| Valid | Absent | Absent | Auto-eligible for small-state copy after preview/backup manifest; preserve legacy source. Preserve or explicitly select backend Data Root separately. |
| Corrupt/incomplete | Absent | Absent | Do not mutate/quarantine source during discovery. Warn and offer canonical defaults plus Locate/Retry; preserve corrupt source. |
| Absent | Valid | Absent | Use canonical; optionally write an adoption marker. Do not search further. |
| Valid | Valid, byte-identical | Absent | Use canonical and write completed/adopted marker; preserve legacy. |
| Valid | Valid, semantically identical but byte-different | Absent | Prompt or require explicit adoption; hashes alone do not establish which metadata is newer. |
| Valid | Valid, divergent | Any incomplete/absent | Refuse automatic selection. Present safe summary and require explicit legacy/canonical choice; preserve both. |
| Valid | Corrupt/partial | Absent | Refuse overwrite. Offer recovery from legacy only after explicit confirmation; preserve corrupt canonical copy. |
| Corrupt | Valid | Any | Use canonical; retain legacy as diagnostic data. |
| Any | Valid | Completed marker matching hashes/paths | Use canonical. Never silently fall back to legacy on later canonical corruption. Offer explicit recovery. |
| Any | Staging/partial | Started marker | Resume only if source manifest still matches; otherwise stop and require recovery choice. |
| Changed after completed migration | Changed | Completed marker | Canonical remains active. Divergent legacy is historical unless the user explicitly requests rollback/recovery. |

Modification time is secondary evidence only. Clock skew, copy tools, restore
operations, and filesystem precision make it unsuitable as the primary winner.

## 8. Migration mechanics

Recommended 18B sequence:

1. Run before Desktop logging/session autosave and before backend config/writers.
2. Resolve exact legacy/canonical roots and reject symlinks/reparse-point escape
   or path overlap where practical.
3. Acquire an exclusive marker lock in the stable organization parent, for
   example `%LOCALAPPDATA%\PHASENOX\.desktop-state-migration.lock`.
4. Read and validate source session without calling the current loader's corrupt
   quarantine path, because discovery must be read-only.
5. Record source byte size and SHA-256; cap accepted session size to a small,
   documented limit.
6. Copy the session into a same-volume staging directory/file under the
   canonical parent.
7. Flush, reread, revalidate schema, and compare byte hash.
8. Atomically replace only an absent target, or use an explicit user-approved
   recovery path for an existing target.
9. Atomically write the completed migration marker.
10. Select canonical session repository and separately set `PHASENOX_ROOT` from
    the Data Root contract.
11. Start logging, scheduler, adapter runtime probes, and backend writers.
12. Preserve the legacy source until a later explicit cleanup operation.

No destructive move comes first. Rerunning after success is idempotent because
the completed marker and target hash match. Rerunning after interruption resumes
only when the recorded source hash is unchanged; otherwise it refuses.

Rollback does not delete either copy. A recovery command can explicitly select
the preserved legacy session while keeping the canonical Qt identity. Backend
rollback is solely a Data Root pointer selection; no stores are moved.

## 9. Session compatibility

The filename is `session-v1.json`, but the current payload schema is version 2
and versions 1 and 2 are accepted. The filename need not change in 18B.

Persisted top-level fields are:

- `schema_version`, `navigation`;
- selected audio, references, and report path;
- bounded recent audio/reference/report/analysis lists;
- last/recent knowledge query strings;
- a deliberately reduced last-analysis record.

Not persisted:

- product/application/brand identity;
- API keys or credential flags;
- operation IDs/current operation;
- Task Center history;
- free-text analysis, issues, metrics, warnings;
- backend/domain models;
- window geometry or Qt preferences.

Absolute input/reference/report paths can be present and reveal personal
filenames. They remain references, not migration sources. Missing referenced
files are already restored safely with `exists=False`; they do not invalidate a
session. The session can therefore be copied byte-for-byte without a schema or
branding rewrite. Valid content should not be normalized merely to update the
product name.

Current corrupt-session handling atomically renames the invalid file to a
timestamped `.corrupt` backup and starts defaults. That behavior is appropriate
after the active canonical repository is selected, but migration discovery must
not invoke it against the legacy source.

## 10. Cache, log, and report policy

### Logs

- Leave legacy `desktop.log` in place as a diagnostic archive.
- Start a fresh canonical Desktop log after cutover.
- Do not concatenate logs or hash-validate a file that may be active.
- Sprint 18B should introduce bounded rotation (recommended small cap such as
  5 MiB with three backups) or explicitly defer it with a documented `C:` risk;
  the current `FileHandler` is unbounded.
- Redact secrets and avoid logging complete provider URLs containing credentials.

### Cache

No distinct Desktop cache writer exists. `<legacy>/data/cache` is the backend
general/model cache because of the packaged-root coupling. Do not copy, purge,
or recreate it as part of Desktop-state migration. Preserve its Data Root.
Rebuild/purge may be offered later with explicit user approval.

### Reports and outputs

Analysis uses a user-selected save path; reference comparison uses a
user-selected output directory; report export uses a user-selected destination.
The session stores descriptors to those files but not their contents.

Configured `<Data Root>/reports` and any legacy-root report files are
authoritative user output, not disposable Desktop state. Sprint 18B leaves them
in place and preserves the Data Root pointer. Any later Data Root move must copy
reports byte-for-byte, verify size/hash, refuse unapproved overwrite, and retain
the source until confirmation.

## 11. Models and data-drive policy

Current config exposes one root-derived model root (`../Models`), model cache,
general cache, Chroma, reports, and logs. Runtime strategies may call
`from_pretrained`, so an accidental new root can cause downloads. Existing APIs
do not provide a public aggregate Data Root availability state, durable pointer,
free-space check, managed/external model distinction, or no-fallback guard.

`get_application_root()` normalizes environment paths but does not require them
to exist, be mounted, readable, or writable. Some downstream clients create
directories/stores, which makes silent split-brain possible.

Sprint 18B foundation must provide:

- a Qt-free `DataRootSelection` contract;
- pre-backend validation of existence, type, accessibility, and intended root;
- a durable pointer stored in small canonical AppData;
- an explicit `DATA_LOCATION_UNAVAILABLE` state;
- no fallback to another drive/root;
- delayed backend initialization until the selected root is valid;
- temporary session mode that disables backend persistence/downloads rather
  than inventing an empty root.

Later Settings/installer work should add separate managed model location,
external model overrides, download/cache/temp policies, input/output/reference
defaults, project/results layout, backup, free-space planning, and an actual
data-move workflow.

### Unavailable drive behavior

If `D:`, `E:`, removable media, or a network location is unavailable:

```text
Selected Data Root
  -> validate without creating
  -> unavailable
  -> block persistent backend initialization
  -> show Data location unavailable
       Retry
       Locate existing data
       Choose another location (explicit rebind; no implicit copy)
       Temporary session mode
```

The pointer remains unchanged until the user explicitly confirms a replacement.
Do not create an empty `C:` root, download models, initialize Chroma/SQLite, or
write a new marker that masks the unavailable root. Network timeouts must be
bounded and must not freeze the Qt thread.

## 12. Split-brain prevention

Startup must never choose based only on directory existence. The resolver uses:

1. a completed marker whose paths and hashes still validate;
2. supported session schema and byte/semantic comparison;
3. explicit Data Root pointer/environment precedence;
4. timestamps only as secondary display evidence;
5. explicit user choice for divergent state.

The canonical path is not automatically “newer” merely because it exists. A
partial installer run, crash, antivirus restore, cloud synchronization, or
manual copy can create it.

Once migration is completed, canonical small state is authoritative. Legacy is
a preserved recovery source, not a live dual-write or automatic read fallback.
Never write both sessions. Never merge recent lists automatically: that can
reintroduce private paths the user deliberately removed.

### Minimal migration marker

Recommended path:

```text
<canonical>/state/desktop-state-migration.json
```

Recommended fields:

```json
{
  "schema_version": 1,
  "status": "started|completed",
  "source_identity": "soundbrain.desktop",
  "target_identity": "phasenox.desktop",
  "source_path": "…",
  "target_path": "…",
  "source_session_sha256": "…",
  "target_session_sha256": "… or null",
  "started_at": "UTC ISO-8601",
  "completed_at": "UTC ISO-8601 or null",
  "application_version": "…"
}
```

This is sufficient; a general file-by-file database manifest is unnecessary for
one small session file. Writes must be atomic and the marker must never contain
credentials or session contents.

## 13. Security and privacy

The Desktop session is credential-free by design but can contain absolute paths,
personal filenames, recent knowledge queries, provider-independent analysis
metadata, and report locations. Logs may contain technical exception context,
paths, endpoints, and filenames. The Data Root pointer and migration marker also
contain absolute paths.

Requirements:

- inherit/create per-user Windows AppData ACLs; do not grant broad write access;
- use owner-only semantics where supported and document that POSIX-style mode
  bits alone do not establish Windows ACLs;
- reject unsafe source/target overlap and avoid following unexpected symlink or
  reparse-point escapes;
- bound file sizes and JSON nesting before parsing untrusted/corrupt state;
- never copy API key values into session, marker, pointer, or logs;
- present paths only where useful and avoid telemetry upload;
- log safe error codes and technical context without secrets;
- make migration choices accessible without revealing file contents.

Migration does not broaden access: source and target stay within the same user
context. A Data Root on a shared/network drive requires an explicit warning that
its ACL/privacy policy is external to AppData.

## 14. Required Sprint 18B tests

### Identity and Qt path

1. Current legacy path probe remains reproducible.
2. Successful cutover sets Qt application name to `phasenox.desktop`, display
   name to PHASENØX, and resolves the canonical AppLocalData path.
3. Organization remains `PHASENOX`; no domain-dependent surprise.
4. Arbitrary-CWD behavior.
5. Clean-machine first launch.

### Migration matrix

6. Legacy-only valid state copies byte-for-byte and remains visible.
7. Canonical-only valid state is adopted without legacy mutation.
8. Neither location exists.
9. Identical dual locations complete deterministically.
10. Divergent dual locations refuse automatic selection.
11. Corrupt legacy session is preserved and does not get quarantined during
    discovery.
12. Corrupt/partial canonical state is not overwritten silently.
13. Interrupted staging/started marker resumes when source hash is unchanged.
14. Interrupted migration refuses when source changed.
15. Completed migration rerun is idempotent.
16. Copy size/SHA-256/schema validation.
17. Existing target uses exclusive/no-overwrite semantics.
18. Failure before marker leaves legacy source usable.
19. Explicit rollback selects preserved legacy state without reverting public
    identity.
20. Upgrade from the Sprint 17 `session-v1.json` schema 2 layout.
21. Supported schema 1 upgrade.
22. Missing referenced audio/report files remain safe.

### Data Root and backend isolation

23. Existing packaged legacy Data Root remains selected after Qt ID cutover.
24. RAG Chroma, memory Chroma, SQLite, models, cache, reports, and logs are not
    copied, renamed, initialized, or opened by migration discovery.
25. Collection `soundbrain` and serialized identities remain unchanged.
26. `PHASENOX_ROOT > pointer > NOISYNE_ROOT > SOUNDBRAIN_ROOT` selection and
    conflict diagnostics.
27. Unavailable external/removable/network root produces
    `DATA_LOCATION_UNAVAILABLE` and never falls back to `C:`.
28. Unavailable root does not create directories, initialize stores, or download
    models.
29. Locate/choose action changes selection only after explicit confirmation.
30. Temporary session mode performs no persistent backend writes.
31. Read-only/unwritable root and file-vs-directory failures.
32. Path normalization, UNC paths, drive-letter case, and symlink/reparse safety.

### Operations and lifecycle

33. Migration runs before logging, session autosave, scheduler, config, or store
    initialization.
34. Exclusive migration lock and stale-lock recovery policy.
35. Atomic pointer and marker writes.
36. Desktop log starts at canonical root; legacy log remains byte-identical.
37. Log rotation/retention if included.
38. Update/reinstall preserves pointer; uninstall policy is represented as an
    installer contract test later.

All migration tests must use temporary directories and fake stores. Tests must
prove absence of writes to backend paths, not merely lack of assertion errors.

## 15. Exact Sprint 18B implementation scope

### Must implement in 18B

1. Change canonical Desktop application ID constant to `phasenox.desktop` only
   as part of the complete guarded cutover.
2. Add a Qt-free small-state location/discovery contract that resolves exact
   legacy and canonical AppLocalData paths before normal startup.
3. Split `DesktopPathLayout` into small Desktop-state paths and an explicit Data
   Root selection; stop deriving backend root blindly from the new Qt identity.
4. Add atomic `data-root.json` read/write and validation.
5. Preserve an existing explicit environment root; for upgraded packaged users,
   bind unchanged legacy backend data as the selected Data Root without moving it.
6. Add read-only migration eligibility inspection and the full dual-location
   decision matrix.
7. Implement copy-first migration for valid `session-v1.json` only, with size,
   schema, SHA-256, exclusive target, staging, fsync/replace, marker, lock,
   idempotency, and rollback metadata.
8. Preserve legacy session and log files; never delete or tombstone them.
9. Add `DATA_LOCATION_UNAVAILABLE` startup state and block backend initialization
   when the selected Data Root is unavailable.
10. Provide Retry, Locate existing data, Choose another location, and temporary
    session-mode intents. A minimal pre-shell dialog is acceptable; do not build
    full writable Settings.
11. Reorder bootstrap so migration/Data Root resolution precedes logging,
    session binding, scheduler start, config import, and backend writers.
12. Start canonical Desktop logging after cutover; preferably add bounded
    rotation.
13. Update focused identity/freeze tests and add the complete temporary-directory
    migration/Data Root suite above.
14. Document the temporary legacy Data Root path as an approved compatibility
    location where applicable.

Expected implementation files:

- `phasenox/ui/branding.py`
- `phasenox/ui/app.py`
- `phasenox/ui/paths.py`
- `phasenox/ui/session_persistence.py` (validation reuse only; avoid content rewrite)
- `phasenox/ui/logging_setup.py`
- new `phasenox/ui/data_location.py`
- new `phasenox/ui/identity_migration.py`
- relevant Qt-free contracts/error/recovery DTOs
- focused files under `tests/ui/`
- identity freeze documentation/tests only where the approved application-ID
  compatibility contract changes.

No backend store implementation needs to change if the Desktop resolves and
sets the selected `PHASENOX_ROOT` before importing/initializing backend config.
If that cannot be achieved without materially changing backend root semantics,
Sprint 18B must stop and report the blocker.

## 16. Deferred Sprint 19 and later responsibilities

### Sprint 19 installer/packaging

- install-location UI and permissions;
- seed/preserve Data Root pointer from installer choice;
- update/reinstall discovery and repair;
- uninstall checkbox/policy, defaulting to preserve all user data;
- final PyInstaller spec, launcher, ICO, signing, updater;
- installer drive changes must not relocate data implicitly.

### Later Settings/storage work

- writable Data Root and per-category location management;
- full **Move PHASENOX Data** operation;
- required free-space calculation and same-volume/cross-volume planning;
- copy/validate/switch/rollback for live backend stores under writer locks;
- managed versus external model locations and overrides;
- model downloads and cache/temp policies;
- project/results/reference/input/output defaults;
- backups and retention/cleanup UI;
- explicit legacy Desktop-state cleanup after user confirmation.

Sprint 18B should establish interfaces that a future Move operation can consume,
but must not implement the move. A correct future operation requires source and
target manifests, writer shutdown/lock, space checks, copy, per-store validation,
atomic pointer switch, rollback, and cleanup only after confirmation.

## 17. Risk and blocker matrix

| Risk/blocker | Severity | Evidence | 18B mitigation |
| --- | --- | --- | --- |
| Qt ID change forks Desktop state | High | Verified distinct AppLocalData paths | Copy-first small-state migration before cutover |
| Qt ID change forks backend stores | Critical | Packaged startup sets `PHASENOX_ROOT` from Qt root | Decouple and persist Data Root before identity switch |
| Unavailable external root creates empty `C:` store | Critical | Root resolver does not require existence; clients may create | Validate without creating and block backend initialization; no fallback |
| Dual valid sessions diverge | High | No current marker/authority record | Hash/schema/marker plus explicit choice; no merge/overwrite |
| Corrupt discovery mutates source | High | Current loader quarantines via rename | Add separate read-only validator for eligibility |
| Absolute personal paths leak | Medium | Session stores recent/selected paths | Same-user ACL, no telemetry, no content logging |
| Unbounded Desktop log consumes AppData | Medium | Plain `FileHandler` | Add bounded rotation or explicit near-term follow-up |
| Reports mistaken for disposable cache | High | Root layout groups reports/cache/session | Classify reports as authoritative; preserve Data Root |
| Models mistaken for cache | Critical | Model root may contain user assets | Never move/purge automatically; explicit managed/external policy later |
| Network/removable root stalls UI | High | No current availability abstraction | Bounded asynchronous validation and explicit unavailable state |
| Config imported before root choice | High | `phasenox.infrastructure.config` loads settings at import | Bootstrap ordering/dependency tests; set root before backend boundary |
| Windows ACL/reparse behavior | Medium | POSIX modes are insufficient | Inherited per-user ACL, path containment/reparse checks |
| Marker becomes a second source of truth | Medium | Pointer, env, and marker may conflict | Clear precedence; marker records migration, pointer selects Data Root |
| Installer later overwrites pointer | High | Installer contract not implemented | Freeze preserve-by-default contract for Sprint 19 |

## 18. Final GO/NO-GO verdict

### GO

Proceed with Sprint 18B only as the bounded identity and small-state migration
described here:

- canonical `phasenox.desktop` identity;
- byte-preserving session migration;
- canonical small AppData state;
- explicit Data Root pointer and availability guard;
- unchanged backend stores and legacy compatibility source;
- split-brain refusal and recovery choices;
- comprehensive temporary-directory tests.

### NO-GO conditions

Do not start or continue an implementation that:

- changes the Qt ID before selecting the backend Data Root;
- recursively moves the legacy AppData tree;
- opens or initializes Chroma/SQLite during discovery;
- silently defaults large data to `C:` or the install directory;
- deletes/tombstones legacy state;
- merges divergent sessions automatically;
- implements the full Move Data/installer/settings redesign;
- requires a material backend persistence-contract change without a new review.

With the Data Root ordering constraint honored, Sprint 18B is technically ready
to begin. Sprint 18B was not started during this audit.
