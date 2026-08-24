# PHASENOX Sprint 22 Final Release Candidate Report

## Verdict

- Sprint 22 local engineering gate: **PASS**
- Desktop Core technical release candidate: **PASS**
- V2 engineering freeze readiness: **READY**
- Public release: **NO-GO**
- Candidate signing state: **UNSIGNED**

The public-release verdict remains NO-GO because 18 external Windows acceptance
rows have not been executed on a separate clean host and three legal/signing
items remain unresolved. No local result in this report substitutes for those
acceptance decisions.

## Candidate identity

| Field | Frozen value |
| --- | --- |
| Repository | `N0ises/NOISYNE` |
| Branch | `v2-development` |
| Application version | `1.0.0` |
| Profile | `desktop-core / windows-x64` |
| Candidate source SHA | `3adfbab5f5dec7e5c2237febb316bc6b89459e5e` |
| Executable | `PHASENOX-1.0.0-win-x64/PHASENOX.exe` |
| Executable SHA-256 | `753da4c1336467b8a8fca6d7eb9ee9b7b2cbe1b3045466e1dafdd09e8fa80c48` |
| Installer | `PHASENOX-Setup-1.0.0-win-x64.exe` |
| Installer SHA-256 | `a30d30a4b92b7060c9e93a230c4bb291e46168b70f5379e8dbeeb3370b2e59c0` |
| Installer AppId | `{A6B2A61D-05B0-4CE7-85A3-C443B36D703B}` |
| Desktop application ID | `phasenox.desktop` |
| Signing | `UNSIGNED` |

The candidate was rebuilt after the loopback retry fix. The acceptance checklist,
machine matrix, and packaging regression test are bound to the source and hashes
above. Older Sprint 21B artifact hashes are superseded and must not be used to
record Sprint 22 acceptance results.

## Master release gate

| Component | Current state | Evidence | Release-supported claim | Blocker | Severity | Disposition |
| --- | --- | --- | --- | --- | --- | --- |
| Source provenance | PASS | Clean Git archive of candidate source SHA | Exact-source build | None | — | Frozen |
| Locked build environment | PASS | Python 3.12.10, PyInstaller 6.22.2, PySide6 Essentials/Shiboken 6.11.2, offline wheelhouses | Windows x64 Desktop Core | None | — | Frozen |
| Desktop Core bundle | PASS | Canonical verifier: 651 files, 345,784,067 bytes | One-folder windowed app | None | — | Frozen |
| Forbidden payload guard | PASS | Verifier failures empty | No Torch, CUDA, ONNX Runtime, Chroma, PyArrow, weights, or user state | None | — | Frozen |
| Native PE closure | PASS | 241 PE files, zero unresolved imports, zero parse errors | App-local VC runtime closure | Clean-host confirmation pending | External | Pending externally |
| Installer | PASS | Inno Setup 7.1.0 x64 compiled and verified | Per-user install, app-only uninstall | External install matrix pending | External | Pending externally |
| Packaged analysis | PASS | Offline arbitrary-CWD probe, exit 0, score 95, 2,830-byte report | Deterministic local analysis/report | Clean-host execution pending | External | Pending externally |
| Data Root contract | PASS | 82-test focused boundary run plus full regression | Explicit handoff, no silent fallback, pointer preservation | Clean-host scenarios pending | External | Pending externally |
| DAW bridge | PASS | Replay-safe bounded transport retry; duplicate and restart soak green | Ableton Live 11.2.7 bridge contract only | Real external DAW acceptance remains outside local certification | External | Pending externally |
| Full regression | PASS | 1,253 passed, 1 skipped, 0 failed across 101 isolated files | Repository-wide local behavior | None | — | Frozen |
| Identity/persistence freeze | PASS | Freeze tests and census | Approved aliases and persisted identities preserved | None | — | Frozen |
| Security/artifact hygiene | PASS locally | Forbidden payload, secret/path, download, and repository-state scans | Local candidate hygiene | Defender/SmartScreen and signing policy unresolved | Legal/external | Pending |
| Legal/license/signing | OPEN | Sprint 19-21 reports and acceptance contract | No public-release claim | Three unresolved items | Release | NO-GO |
| External Windows acceptance | NOT EXECUTED | Clean-machine matrix | No clean-host claim | 18 pending rows | Release | NO-GO |

## Defect found and closed

The final soak reproduced an intermittent Windows loopback transport abort in the
Ableton bridge client (`ConnectionAbortedError`, WinError 10053). It was not
waived. The canonical client now retries transport-level `TimeoutError`,
`URLError`, and `OSError` failures with a bounded three-attempt sequence and
50/100 ms backoff. HTTP, authentication, and protocol failures are not retried.

The bridge protocol operations are replay-safe: export requests use deterministic
content identity and duplicate suppression, while handshake, disconnect, and
result operations are idempotent. There is one implementation, not a parallel
compatibility path.

Implementation commits:

- `ee43cf0568e2390f42d9b61602e9d4205b14c445` — retry transient loopback requests.
- `3adfbab5f5dec7e5c2237febb316bc6b89459e5e` — harden bounded retry backoff.

## Build and artifact verification

The release orchestrator created a fresh isolated environment from the locked
offline wheelhouses and built from the exact candidate source SHA.

- `pip check`: zero dependency errors.
- Bundle verifier: PASS.
- File inventory: 651 files.
- Unpacked size: 345,784,067 bytes.
- PE inventory: 241 files.
- Unresolved native imports: 0.
- Native parse errors: 0.
- Unexpected PyInstaller warnings: 0 after policy filtering.
- PE ProductName: `PHASENØX`.
- PE OriginalFilename: `PHASENOX.exe`.
- PE ProductVersion: `1.0.0`.
- Qt Windows platform plugin: present.
- Installer compilation: PASS.
- SBOM, license inventory, release manifest, and SHA-256 output: generated.
- Signing state: `UNSIGNED`.

The three PyInstaller discovery warnings for optional internal tables are known
hook-discovery messages and did not become verifier failures or unresolved native
imports.

## Runtime and workflow validation

### Packaged offline analysis

The frozen executable was launched from an arbitrary temporary working directory
with isolated `APPDATA`/`LOCALAPPDATA`, an explicit temporary Data Root, and
Hugging Face/Transformers offline flags.

- Process exit: 0.
- Frozen runtime: true.
- Analysis status: `ok`.
- Score: 95.0.
- Report size: 2,830 bytes.
- Model download attempted: false.
- Torch, torchaudio, and transformers: unavailable as required by Desktop Core.
- Unexpected files in the explicit Data Root: none.
- User state remained outside the install directory.

### Regression and soak

- Full isolated regression: **1,253 passed, 1 skipped, 0 failed** across 101
  files. The skip is the expected Windows symlink-permission test.
- Focused candidate/bridge regression: **26 passed, 1 skipped**.
- Focused Data Root, persistence, duplicate submission, and bridge soak batch:
  **82 passed**.
- Bridge lifecycle soak after the final retry policy: 10 executions of the
  10-cycle test, **100 lifecycle cycles passed**.
- Desktop open/close soak: 10/10 passed.
- Scheduler submit/wait/shutdown soak: 10/10 passed.
- Deterministic local analysis soak: 10/10 passed.
- Exact-byte report export soak: 10/10 passed.

### Capability truth

Desktop Core continues to expose only capabilities backed by its locked payload.
ML/RAG/GPU capabilities requiring excluded runtimes remain unavailable rather
than silently downloading dependencies or models. Current navigation is backed by
real adapters; the non-navigation runtime-status fallback is not represented as a
shipping workflow. Task pause remains queue-only and is enabled only for queued
jobs.

The Ableton interoperability claim remains deliberately narrow: **Ableton Live
11.2.7 only**. This report does not broaden the claim to other Ableton versions,
DAWs, hosts, or plugin formats.

## Data, persistence, and identity audit

- `PHASENOX_ROOT` remains canonical-first.
- `NOISYNE_ROOT` and `SOUNDBRAIN_ROOT` remain supported fallbacks.
- Canonical pointer preservation and unavailable-root no-fallback behavior pass.
- Installer handoff remains a proposal validated and committed by Desktop before
  persistent backend initialization.
- The persisted collection identity `soundbrain` is unchanged.
- Existing serialized `noisyne.*` method/provider/digest identifiers are
  unchanged.
- Engine keys `noisyne` and `soundbrain` are unchanged.
- The `brain.*` namespace and approved Python aliases remain compatibility-only.
- No persistence migration, collection rename, schema change, or data movement
  occurred.

The tracked-text census before adding this report contained 1,040 case-specific
legacy-token matches (`noisyne` 291, `NOISYNE` 124, `Noisyne` 75, `soundbrain`
257, `SoundBrain` 220, `SOUNDBRAIN` 73). The identity allowlist and freeze tests
classify all live matches as approved compatibility/persistence contracts and all
non-live matches as historical evidence: **Category B = 0; Category C = 0**.

## Security review

The bridge remains loopback-only and retains authentication, bounded request-body,
path containment, reparse-point, duplicate-request, and clean-shutdown controls.
The packaging verifier rejects forbidden heavy runtimes, model data, databases,
user state, secrets, repository paths, developer paths, and legacy-facing product
artifacts. Offline initial shell and packaged analysis did not attempt a model
download.

No Critical or High local code, security, packaging, or persistence defect remains
open. This statement does not claim external antivirus reputation or code-signing
acceptance.

## External Windows acceptance: 18 pending

All rows remain `EXTERNAL_ACCEPTANCE_PENDING / NOT_EXECUTED` and must be run
against the immutable hashes in this report on a separate Windows x64 host:

1. no Python installed;
2. no repository state;
3. default install;
4. custom install path with spaces;
5. custom Data Root;
6. non-ASCII user or path;
7. offline first launch;
8. no model download;
9. second launch;
10. same-version reinstall;
11. upgrade preserves pointer;
12. uninstall preserves user data;
13. unavailable Data Root with no fallback;
14. deterministic analysis;
15. reference workflow;
16. report export;
17. Task Center/shell;
18. no preinstalled VC++ runtime.

Defender/SmartScreen observation belongs to the external acceptance record and is
not represented as a local PASS.

## Legal and signing: 3 open items

1. Resolve the publisher/legal identity used by release metadata.
2. Complete legal review of the generated third-party license inventory.
3. Approve and execute the production code-signing and SmartScreen reputation
   policy with an authorized certificate.

No company name, certificate subject, or compliance conclusion was fabricated.

## Final blocker accounting

| Class | Critical | High | Open release item |
| --- | ---: | ---: | --- |
| Code | 0 | 0 | None |
| Security (local) | 0 | 0 | External Defender/SmartScreen observation pending |
| Packaging | 0 | 0 | External install matrix pending |
| Persistence | 0 | 0 | None; no migration performed |
| External acceptance | — | — | 18 rows pending |
| Legal/signing | — | — | 3 items pending |

## Final disposition

The Desktop Core candidate is a **technical RC PASS**, and the V2 engineering
baseline is **READY to freeze locally**. Public release remains **NO-GO** until
all 18 external Windows rows pass and all three legal/signing items are resolved.
No push or GitHub migration is authorized by Sprint 22.
