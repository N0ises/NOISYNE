# PHASENOX Sprint 18B Desktop Identity and Data Migration Report

## Outcome

Sprint 18B completed the guarded Desktop identity cutover from
`soundbrain.desktop` to `phasenox.desktop` without moving or initializing
backend persistence. Canonical Qt identity, canonical small Desktop state, and
the backend Data Root are now separate contracts.

The mandatory ordering from the Sprint 18A audit is enforced: Desktop state
and Data Root resolution run through Qt-free modules before canonical identity,
logging, the scheduler, backend configuration, or store construction.

## Commit chain

The implementation uses scoped, unsquashed local commits:

1. `400a05d` — `feat(desktop): add data root selection contracts`
2. `17c288b` — `feat(desktop): add guarded session identity migration`
3. `1b92659` — `feat(desktop): guard canonical identity cutover`
4. `d86c989` — `test(desktop): freeze identity migration contract`
5. `9d86aba` — `fix(desktop): bound data root validation`
6. Documentation commit containing this report and the Sprint 18A audit; its
   final SHA is reported in the handoff because a commit cannot contain its own
   hash.

No prior commit was amended, squashed, rebased, or pushed.

## Identity and locations

| Boundary | Final behavior |
| --- | --- |
| Organization | `PHASENOX` |
| Canonical Qt application name / Desktop ID | `phasenox.desktop` |
| Display name | `PHASENØX` |
| Canonical Windows small-state root | `%LOCALAPPDATA%\PHASENOX\phasenox.desktop` |
| Legacy compatibility root | `%LOCALAPPDATA%\PHASENOX\soundbrain.desktop` |
| Package | `phasenox` |

The legacy identity remains only a deterministic discovery/recovery contract.
It is not the effective normal Desktop identity. No legacy directory is
renamed, recursively copied, tombstoned, or deleted.

The canonical small-state root contains only:

- `state/session-v1.json`;
- `state/data-root.json`;
- `state/desktop-state-migration.json`;
- small migration lock/metadata;
- bounded Desktop logs.

It is not a backend-data fallback.

## Data Root contract and precedence

`phasenox.ui.data_location` is Qt-free and exposes normalized selection,
source, availability, conflict, and recovery contracts. Selection precedence
is:

1. non-empty `PHASENOX_ROOT`;
2. valid canonical `state/data-root.json`;
3. the confirmed Sprint 17 packaged legacy-upgrade root;
4. `NOISYNE_ROOT`;
5. `SOUNDBRAIN_ROOT`;
6. explicit first-launch selection or temporary mode.

The schema-1 pointer stores only normalized path, durable selection source,
timestamp, and schema version. Writes use same-directory staging, flush/fsync,
and atomic replacement. Read-only discovery is bounded and never creates or
rewrites the pointer. Environment overrides win for the launch, conflicts are
retained in the resolution, and an environment override does not rewrite the
pointer.

Existing packaged upgrades preserve the exact legacy Qt root as their backend
Data Root and persist it with `selection_source = legacy_upgrade`. Sprint 18B
does not move or rename that path.

Validation checks existence, directory type, readability, required
writeability, symlink/reparse safety, and normalization without creating a
probe file. Removable/network validation has a two-second bound.

## Session migration

Automatic migration covers only `state/session-v1.json`:

1. inspect the legacy and canonical files without mutation;
2. enforce the 1 MiB cap and supported schema 1/2;
3. compute the source SHA-256;
4. acquire the organization-scope exclusive migration lock;
5. atomically write a `started` marker;
6. copy exact bytes to same-directory staging and fsync;
7. reread and validate schema/hash;
8. install only to an absent target using exclusive hard-link semantics;
9. reread and verify the installed target;
10. atomically write the `completed` marker;
11. preserve the source unchanged.

The marker records schema/status, source/target identities and paths, source
and target hashes, start/completion timestamps, and application version. It
contains no session content or credentials. A stale-aware lock is separate
from the R5 backend persistence lock.

Decision behavior:

- legacy valid/canonical absent: copy-first migration;
- canonical valid/legacy absent: canonical session;
- byte-identical dual state: canonical adoption plus completed marker;
- semantic-equal but byte-different or divergent dual state: explicit choice;
- corrupt legacy: preserved without quarantine during discovery;
- corrupt canonical: never overwritten automatically;
- unchanged `started` migration: resumable;
- changed source after `started`: recovery choice required;
- matching `completed` marker: canonical authoritative unless explicit
  recovery.

Missing referenced files remain valid session references. Session content is
never rewritten for branding.

## Split-brain and unavailable-drive behavior

Startup never selects a session merely because a directory exists and never
selects a backend location from the canonical Qt ID.

An unavailable, non-directory, unreadable, read-only, unsafe, or timed-out Data
Root returns `DATA_LOCATION_UNAVAILABLE`. Backend activation then fails closed.
The resolution exposes these presentation-safe recovery intents:

- Retry Data Root;
- Locate Existing Data;
- Choose Another Location;
- Temporary Session Mode;
- Choose Legacy Session;
- Choose Canonical Session.

The current minimal recovery surface is command-line startup selection:
`--data-root`, `--temporary-session`, and `--session-choice`. Full writable
Settings and a graphical storage manager are intentionally deferred.

Temporary mode is explicit. It returns before small-state initialization,
logging, scheduler construction, configuration import, model/download clients,
or backend stores. It does not export a fallback `PHASENOX_ROOT`.

## Bootstrap order

Normal startup is now:

1. parse startup intent and construct only the lightweight adapter metadata;
2. create the minimal Qt runtime without applying product identity;
3. deterministically resolve legacy/canonical roots;
4. resolve and validate the Data Root without creation;
5. persist a durable explicit/legacy-upgrade pointer where appropriate;
6. inspect/migrate/adopt the small session;
7. apply canonical `phasenox.desktop` Qt identity;
8. export the validated selection as `PHASENOX_ROOT`;
9. create canonical small-state directories and bounded logging;
10. bind the selected session;
11. construct/start the scheduler, adapter runtime work, and backend boundary.

Recovery-required startup returns before step 7. Temporary startup applies the
canonical identity but returns before steps 8–11.

## Logging

The Desktop starts a new canonical `logs/desktop.log` only after persistent
startup succeeds. It uses a 5 MiB rotating handler with three backups. The
legacy log is neither opened, copied, merged, nor removed.

## Backend persistence unchanged proof

No production file under RAG, memory, infrastructure persistence, models,
services, runtime persistence, or config loader changed. The implementation
does not invoke Chroma, SQLite, model loaders, Torch, Transformers, or download
clients during discovery/migration.

Regression guards confirm:

- the persisted Chroma collection remains `soundbrain`;
- engine keys remain `noisyne` and `soundbrain`;
- serialized `noisyne.*` identifiers remain unchanged;
- R4 backend environment compatibility remains intact;
- no backend `data/`, model, cache, report, log, audio, or reference content is
  copied or renamed.

The packaged-upgrade test places a sentinel `data/index.db` under a temporary
legacy root and proves its bytes and location remain unchanged while the new
pointer continues selecting that exact root.

## Validation results

| Gate | Result |
| --- | --- |
| Complete Desktop suite | 136 passed |
| Technical identity freeze | 10 passed |
| Application-root suite | 12 passed |
| Persistence safety | 9 passed |
| RAG collection/preflight | 13 passed |
| Sprint 15 application service | 19 passed |
| Sprint 16 scheduler | 27 passed |
| Branding | 6 passed |
| Canonical service RAG/reasoning/reference/semantic regressions | 12 passed |
| Distribution non-packaging checks | 3 passed, 1 deselected |
| Wheel/sdist fresh-install packaging test | 1 passed, 3 deselected |
| Disposable offscreen arbitrary-CWD launch | exit 0 |
| Ruff on all touched Python files | passed |
| Black `--check` on all touched Python files | passed |
| `compileall phasenox brain tests` | passed |
| Base-to-HEAD and worktree `git diff --check` | passed |

One combined Windows pytest process produced two known isolation failures after
RAG had already opened native persistence resources: a retained SQLite handle
prevented a fixture rename, and a module-presence assertion observed the prior
RAG import. The same required suites passed in clean isolated processes (9
persistence and 13 RAG tests). A separate mixed identity/Qt run also triggered
the known native Windows access violation; the identity and Desktop suites each
passed in isolated processes. No assertion failure was hidden.

The offscreen launch used only disposable directories. It created canonical
`logs/desktop.log` and `state/session-v1.json`; the selected disposable Data
Root stayed empty.

## Known limitations and deferred Sprint 19 work

- Full graphical recovery and writable Settings are not part of 18B; the
  contracts and minimal startup options are present.
- A timed-out read-only network validation thread is daemonized and may finish
  later, but it performs no write or store initialization.
- Installer selection, pointer seeding/preservation, repair, update/reinstall,
  and uninstall policy remain Sprint 19.
- **Move PHASENOX Data**, free-space planning, writer shutdown/locking,
  manifests, cross-volume copy/validation, rollback, and cleanup remain later
  storage work.
- Models, downloads, cache/temp, project/results, reference, input/output,
  report, and backup location controls remain later Settings work.

## Scope and safety confirmation

- No real user or backend data was moved.
- Migration tests wrote only temporary fixtures.
- The two protected Desktop roadmap files were not edited or staged.
- No Desktop branch or asset was touched.
- No commit was pushed.
- Sprint 19 was not started.
