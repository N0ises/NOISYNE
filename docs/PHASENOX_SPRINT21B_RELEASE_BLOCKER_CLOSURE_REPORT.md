# PHASENOX Sprint 21B Release Blocker Closure Report

Date: 2026-08-24 (America/Los_Angeles)
Branch: `v2-development`

## Verdict

- Local code completeness: **PASS**.
- Local technical RC: **PASS**.
- External Windows acceptance: **PENDING**.
- Public release: **NO-GO**.
- Critical local blockers: **0**.
- High local blockers: **0**.
- External acceptance rows: **18 `EXTERNAL_ACCEPTANCE_PENDING / NOT_EXECUTED`**.
- Release-governance High items: **3**.

Sprint 21B found and fixed one real packaged-analysis defect, rebuilt the
Desktop Core candidate from the fixed source, and completed all locally
executable release gates. No clean-machine claim is made. Public distribution
remains prohibited until the separate Windows acceptance checklist passes and
the legal/signing items below are resolved.

## Baseline and local commits

The reviewed Sprint 21 baseline `7123116aa0d5f48adcbaa671b91d6530db2d3a34`
was pushed to `origin/v2-development` by normal fast-forward before Sprint 21B
work began. Local and remote were then `0 / 0` ahead/behind. No Sprint 21B commit
has been pushed.

Scoped Sprint 21B commits before this report:

1. `f8f0394` — `fix(desktop): keep core analysis independent of semantic runtime`
2. `72954ad` — `test(release): defer external windows acceptance`

The second commit is the exact source/provenance SHA of the final candidate:
`72954adb2347a94b602198e3f4f252ea2a05a24b`. Changes after that SHA update only
the candidate-bound checklist, matrix assertions, and this evidence report;
they do not change shipping code or payload inputs.

The temporary workstation cleanup script was absent at final audit and was not
committed. The two protected Desktop roadmap files were never edited or staged.

## Candidate and provenance

The Sprint 21 candidate initially rebuilt from `7123116…` was not accepted as
final after its real frozen analysis probe exposed the defect described below.
The final candidate was rebuilt from clean Git source `72954ad…` with `git
archive`, Python 3.12.10, the hash-locked offline Desktop Core wheelhouses,
PyInstaller 6.22.2, PySide6 Essentials/Shiboken 6.11.2, and Inno Setup
7.1.0-x64. `pip check` reported zero broken requirements.

| Artifact | Final value |
|---|---|
| Profile | `desktop-core / windows-x64` |
| Bundle | `PHASENOX-1.0.0-win-x64` |
| Bundle files | 651 |
| Bundle bytes | 345,784,067 |
| `PHASENOX.exe` SHA-256 | `763ce5ad34dfdafb97bffd6252aa8419760fae0f1f514b5014611ba70e3fc7b2` |
| Installer | `PHASENOX-Setup-1.0.0-win-x64.exe` |
| Installer bytes | 93,774,691 |
| Installer SHA-256 | `30d6fbb0bc9548c045e549589db38dea981c92270aaa5c5d888cb2f0e94f617b` |
| SBOM SHA-256 | `2b2013d91b961609a565a4ea1e7a92f5b7c4f723d708dbc396295aafa604764a` |
| License inventory SHA-256 | `62f33c6ff000d86af5befdea7c8d55d64cacb439da4a587cda060d5fb08e191c` |
| Release manifest SHA-256 | `20d90db8dfacf586b0ba78b05e74e50111342dcb815dda9136d48ce991c699db` |
| Signing state | `UNSIGNED` |

Manifest, executable, installer, SBOM, and license hashes were recomputed and
matched internally. The installer was compiled from the verified final bundle.
No rebuild is required after this report because no shipping input changed.

## Packaged-analysis defect and closure

The pre-fix frozen executable failed a real deterministic analysis probe with:

`ModuleNotFoundError: No module named 'torch'`

`AudioContextDetector` eagerly imported and constructed the optional CLAP
semantic analyzer even when `include_semantic_analysis` was false. That made a
promised Desktop Core workflow depend on a deliberately excluded runtime.

Commit `f8f0394` moved semantic analyzer import/construction behind the explicit
audio/semantic path. The deterministic path no longer imports Torch,
torchaudio, or Transformers. The optional semantic behavior and public method
contract remain unchanged.

Proof after the final rebuild:

- final frozen executable returned exit code 0 from an arbitrary CWD;
- deterministic local WAV analysis returned `status=ok`, score 95;
- a 2,830-byte report was created in 16.311 seconds;
- Torch was unavailable and not imported;
- no model download was attempted;
- no Hugging Face cache was created;
- all writable state resolved outside the install directory.

This is host-local packaged execution, not clean-machine certification.

## Exact Sprint 21 Critical/High classification

| ID | Origin | Severity | Type | Status | Evidence | Release impact |
|---|---|---:|---|---|---|---|
| S21-C1 | Sprint 21 grouped clean-machine gate | Critical | EXTERNAL_ACCEPTANCE | EXTERNAL_ACCEPTANCE_PENDING | `clean-machine-matrix.json`; external checklist | Public distribution NO-GO; not a known product defect |
| S21-H1 | Sprint 21 | High | LEGAL_SIGNING | PENDING | Publisher fields remain intentionally unresolved | Public distribution NO-GO |
| S21-H2 | Sprint 21 | High | LEGAL_SIGNING | PENDING | Generated license inventory exists; legal review is not claimed | Public distribution NO-GO |
| S21-H3 | Sprint 21 | High | LEGAL_SIGNING | PENDING | Candidate is unsigned; authorized signing/SmartScreen policy unresolved | Public distribution NO-GO |

S21-C1 is missing external execution evidence (Category B under the revised
blocker taxonomy), not a local code defect. S21-H1 through S21-H3 are
release-governance/legal/signing items (Category C). No Sprint 21 Critical/High
item disappeared or was silently downgraded.

## Final local Critical/High gate table

| ID | Origin | Severity | Type | Status | Evidence | Release impact |
|---|---|---:|---|---|---|---|
| S21B-PKG-1 | Frozen deterministic analysis | Critical | PACKAGING | PASS | final packaged analysis probe and `f8f0394` | Closed |
| S21B-PKG-2 | Desktop Core payload | Critical | PACKAGING | PASS | fail-closed verifier: 651 files, zero failures | Closed |
| S21B-NATIVE-1 | PE/DLL closure | Critical | PACKAGING | PASS (static/local) | 241 PE files, zero unresolved imports, zero parse errors | External no-VC runtime execution remains pending |
| S21B-DATA-1 | Data Root authority | Critical | PERSISTENCE | PASS | 83 focused tests plus full regression | Closed locally |
| S21B-NET-1 | Startup/model cache | High | SECURITY | PASS | frozen offline probe, cache forwarding tests, no cache/download evidence | Closed locally |
| S21B-DAW-1 | Ableton bridge boundary | High | SECURITY | PASS | bridge/client security and soak tests | Closed locally |
| S21B-ID-1 | Current-facing identity | High | CODE | PASS | identity freeze/branding/distribution tests; B=0, C=0 | Closed |
| S21B-UX-1 | Capability/action truth | High | CODE | PASS | all 23 Desktop UI files; DAW remains unavailable/not exposed | Closed |

Final local counts by type are zero Critical and zero High for CODE, SECURITY,
PACKAGING, and PERSISTENCE.

## Regression results

The authoritative post-fix regression executed every current top-level and
Desktop UI test file in a separate Python process:

- **1,252 passed**;
- **1 skipped**;
- **0 assertion failures**;
- 101 isolated test files.

The sole skip is Windows symlink creation privilege; the real junction/reparse
guard remains covered and passed. One RAG file reproduced the documented
Windows native pytest-plugin/PyArrow teardown access violation. The same test
passed with plugin autoload disabled, and the identical service request passed
in a plain fresh Python process. This isolated invocation is the authoritative
result for that non-UI file; no product assertion was suppressed.

Additional focused results:

- post-fix service/Desktop boundary: 40 passed;
- Data Root/session/persistence boundary: 83 passed;
- runtime/application/scheduler/package alignment: 69 passed;
- final Desktop Core packaging contract: 8 passed;
- Ableton bridge/client: 37 passed, 1 privilege-dependent skip;
- all 23 Desktop UI files: 140 passed.

An earlier release-alignment failure was traced to two concurrently launched
pytest processes sharing the configured `tmp` base directory. It passed 8/8
when rerun alone, and the final authoritative regression was strictly serial.

## Stress gates

| Gate | Result |
|---|---|
| Desktop construct/open/close | 10/10 PASS |
| Scheduler submit/wait/shutdown | 10/10 PASS |
| Bridge start/stop plus connect/disconnect | 10/10 PASS |
| Concurrent duplicate DAW request guard | PASS |
| Deterministic analysis | 10/10 PASS |
| Exact-byte report export | 10/10 PASS |

No zombie process, held bridge port, duplicate request, stale scheduler task,
duplicate logging handler, or report mismatch was observed in these gates.

## Data Root, network, and persistence

Focused tests covered canonical and custom roots, environment precedence,
conflict diagnostics, atomic pointer writes, unavailable/invalid/read-only
paths, existing pointer preservation, legacy-named target preservation, no
migration, temporary mode, first-launch and installer handoff boundaries,
session migration, and persistence safety.

The unavailable-root path remains truthful and never creates a fallback or
replacement store. No test or packaged probe created unintended `data/`,
`chroma/`, `vector_db/`, `index.db`, `models/`, or cache state outside its
isolated authoritative location. Persistence identities and schemas were not
changed.

Remote model strategies continue to forward the configured PHASENOX model
cache. Desktop Core excludes the model runtimes and disables the corresponding
capabilities. Frozen startup and real packaged analysis created no default Hugging
Face cache and attempted no download.

## Installer, package hygiene, and native closure

The final Inno source compiled successfully with the pinned 7.1.0-x64 compiler.
Static and test inspection reconfirmed:

- stable AppId `{A6B2A61D-05B0-4CE7-85A3-C443B36D703B}`;
- `PrivilegesRequired=lowest`;
- `%LOCALAPPDATA%\Programs\PHASENOX` default with selectable install path;
- previous application directory preservation and downgrade guard;
- independent Data Location proposal/handoff;
- no direct installer write to `data-root.json`;
- no environment rewriting;
- application-only uninstall and no data deletion rule.

The fail-closed bundle verifier re-passed the final artifact. It found no Torch,
torchaudio, CUDA, ONNX, Chroma, PyArrow, model weights/cache, tests, docs,
roadmaps, source concepts, databases, user state, credentials, private keys,
repository paths, personal paths, or unexpected Qt payload. Secret hit counts
were empty.

Static native closure inspected 241 shipped `.exe`, `.dll`, and `.pyd` files:
zero unresolved imports and zero parse errors. CPython, Qt/qwindows, shiboken,
NumPy, SciPy, SoundFile/libsndfile, and MSVC files resolve through app-local or
Windows-system classification. The local strategy is app-local closure; proof
on a Windows host without a separately installed VC++ runtime remains external
acceptance.

PyInstaller emitted only the reviewed optional/generated-table warnings for
`pycparser.lextab`, `pycparser.yacctab`, and `scipy.special._cdflib`. The final
frozen deterministic analysis exercised the shipping SciPy/librosa/SoundFile
path successfully. Setuptools license metadata deprecations do not affect the
current payload but reinforce the separate license/governance review item.

## Ableton, capability truth, and security

Sprint 21's real Ableton Live 11.2.7 rendered-export evidence remains valid.
Final PHASENOX-side tests reconfirmed literal loopback binding, authenticated
protocol v1, bounded tokens/bodies/paths/results, traversal and reparse/junction
protection, duplicate suppression, safe reconnect/restart, no arbitrary command
surface, and clean shutdown.

The helper remains outside Desktop Core. `daw_integration` is lifecycle
`VERIFIED` for the explicitly tested Ableton 11.2.7 rendered-export boundary,
but Desktop availability remains `UNAVAILABLE / not_exposed_in_desktop`. No
automatic Ableton control or broader-version support is claimed.

Focused review of the DAW bridge, installer handoff, Data Root, report export,
session state, logging, and model configuration found zero Critical/High local
security findings. Tokens and sensitive values are not logged, writes remain
bounded to authoritative/user-selected destinations, and visible capability
states remain truthful.

## Identity census

The R10-style tracked-text census, excluding this self-referential report,
returned:

| Token | Count |
|---|---:|
| `noisyne` | 290 |
| `NOISYNE` | 123 |
| `Noisyne` | 74 |
| `soundbrain` | 256 |
| `SoundBrain` | 219 |
| `SOUNDBRAIN` | 72 |
| **Total** | **1,034** |

Identity freeze tests and the approved compatibility/history allowlists confirm
Category **B=0** and **C=0**. All live occurrences remain approved compatibility,
persistence, engine, serialized-ID, environment, or repository contracts; all
non-live occurrences remain historical. The count increase since the Sprint 21
audit is historical report text, not current-facing drift.

## External acceptance

`tools/packaging/clean-machine-matrix.json` is bound to the final source and
artifact hashes. All 18 rows are explicitly
`EXTERNAL_ACCEPTANCE_PENDING / NOT_EXECUTED`; none is called PASS, FAIL, or a
product blocker without external evidence.

The deterministic separate-host procedure is
`docs/PHASENOX_EXTERNAL_WINDOWS_ACCEPTANCE_CHECKLIST.md`. It covers hash
verification, no-Python launch, installer and virgin first launch, custom Data
Root, restart, offline startup, Analyze, Reference, report export,
unavailable-root behavior where practical, reinstall, uninstall, preserved
data, and Defender/SmartScreen observation.

## Quality gates

- Ruff on touched Python: PASS.
- Black check on touched Python: PASS.
- `compileall phasenox brain tests tools`: PASS.
- PowerShell parser validation: PASS (2 tracked scripts).
- Final Inno compile: PASS.
- JSON parse and candidate contract assertions: PASS.
- `git diff --check`: PASS.

## Final release statement

Sprint 21B local closure and the local technical RC are **PASS**. There are no
known Critical/High local CODE, SECURITY, PACKAGING, or PERSISTENCE blockers.
External Windows acceptance is **PENDING**, and the three legal/signing High
items remain explicit. Therefore public release is **NO-GO**.

Sprint 22 was not started. No Sprint 21B commit was pushed.
