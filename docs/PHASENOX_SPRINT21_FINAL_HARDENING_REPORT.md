# PHASENOX Sprint 21 Final Product Closure / Hardening Report

Date: 2026-08-23 (America/Los_Angeles; evidence captured through 2026-08-24 UTC)  
Branch: `v2-development`  
Required base: `d92b08b8f3f800e3df58f91b69e2265751abcb0a`

## Verdict

- Sprint 21: **FAIL** as a final release-closure gate.
- S22: **NOT READY**.
- Ableton installed/running: **YES — Ableton Live 11 Suite 11.2.7 x64**.
- Ableton-side client: **IMPLEMENTED** as an explicit external rendered-export helper.
- Real Ableton end-to-end: **VERIFIED FOR ABLETON LIVE 11.2.7 ONLY**.
- `daw_integration` lifecycle: **VERIFIED**, while Desktop availability remains
  **UNAVAILABLE / NOT EXPOSED**.
- Clean-machine certification: **BLOCKED**.
- Critical blockers: **1** (the grouped, still-unexecuted clean-machine release
  certification gate described below).
- High blockers: **3** (legal publisher identity, third-party license review,
  and authorized production signing/SmartScreen policy).

The technical integration and local regression work passed, but Sprint 19C's
essential clean-machine evidence is still unavailable. A workstation result is
not substituted for that evidence.

## Pre-flight and Sprint 20 review

Pre-flight established the exact required base on local and
`origin/v2-development`, a clean tracked index/worktree, and only the two
protected untracked Desktop roadmap files. Local and remote `desktop-ui` both
remained `e2dd11e4193f32cd4f31cda5bca8cbd322bec3af`.

The full Sprint 20 chain (`9c80cee`, `bc4b86e`, `d92b08b`) and implementation
were reviewed before changes. Its bridge was a Python-side foundation:

- `127.0.0.1` HTTP only, a high-entropy bearer token, and protocol version 1;
- health, handshake, export submission, stable-WAV validation, bounded queue,
  deterministic digest identity, in-memory duplicate rejection, and shutdown;
- no canonical analysis execution, safe result polling, or real Ableton-side
  component.

The Sprint 20 fixture client proved bridge correctness only. It was not treated
as vendor interoperability.

## Running Ableton and installation inventory

Read-only process inspection found:

- process: `Ableton Live 11 Suite.exe`;
- PID: `4868`;
- executable: `D:\ProgramData\Ableton\Live 11 Suite\Program\Ableton Live 11 Suite.exe`;
- product/file version: `11.2.7`;
- architecture: x64;
- interactive session: 5, current user;
- responsive window: `Untitled* - Ableton Live 11 Suite`;
- helper observed during discovery: `Ableton Index.exe`; a plugin scanner was
  transiently present earlier in the audit.

The installation exposes MIDI Remote Scripts, Max for Live, the User Library,
and Ableton's Python control-surface infrastructure. Official documentation
confirms that Live 11 custom remote scripts use Python 3 and that Max for Live
devices are supported in Suite. No preference, Remote Scripts directory, User
Library content, process memory, transport, devices, or project files were
modified by PHASENOX tooling.

References:

- <https://help.ableton.com/hc/en-us/articles/209072009-Installing-third-party-remote-scripts>
- <https://www.ableton.com/en/live-manual/11/max-for-live/>

## Selected architecture and implementation

The selected minimum architecture is an **external, standard-library-only
rendered-WAV helper**. A Remote Script or Max for Live device would require an
Ableton installation/preference change and reload that was unnecessary for the
safe proof available in the running session. There is no DLL injection, debugger,
UI automation, transport control, track/device manipulation, or shell-command
surface.

Implemented boundaries:

- `phasenox.integration.ableton_client`: validates an ephemeral per-user
  handoff, watches only direct children of one explicit export directory,
  performs authenticated handshake/result polling, and detects the actual main
  Ableton process with the Windows Toolhelp API;
- `phasenox.integration.daw_analysis`: a narrow async gateway to the canonical
  `PhasenoxV2Service` `ANALYZE` operation; DSP is not duplicated;
- `phasenox.integration.ableton_bridge`: safe result endpoint and disconnect,
  bounded results, queue/race hardening, and connection-close semantics;
- `tools.ableton.bridge_host` and `tools.ableton.export_client`: explicit
  operator-run host/client entry points.

The helper is not installed by Desktop Core and is not a standard Desktop Core
payload. A future release must make it a separately selected optional component
or package. Installation must be user-visible; uninstall removes only
PHASENOX-owned helper files and never Ableton projects, exports, preferences, or
unrelated settings.

## Security and privacy model

- Literal `127.0.0.1` is required; `localhost`, wildcard, credential-bearing,
  HTTPS, and non-v1 endpoints are rejected.
- The bridge token is high entropy, bounded, short lived, stored in an atomic
  per-user handoff, removed by normal host shutdown, and never printed by the
  client or ordinary bridge output.
- Request bodies, tokens, project strings, paths, handoffs, result fields, and
  polling time are bounded.
- Only direct `.wav` children of the explicitly selected export folder are
  eligible. Absolute paths, traversal, missing paths, directory masquerades,
  unsupported content, and symlink/reparse escapes are rejected.
- Results contain only request/analysis IDs, state, source basename, bounded
  summary/counts/limitations, availability, and safe error codes/messages.
  Credentials, private exceptions, internal paths, model objects, and raw
  analysis arrays are not returned.
- No eval, arbitrary Python, subprocess command, remote binding, or arbitrary
  filesystem API is exposed.

The real evidence directory is outside the repository and remains preserved for
review. It contains the WAV plus Ableton's `.asd` sidecar; neither is tracked or
packaged. The report records a SHA-256 digest, not media contents.

## Real Ableton interoperability evidence

The operator rendered from the open, disposable `Untitled` Ableton workflow into
the explicit temporary export directory while the helper was connected. This
was not a developer-side file copy. Evidence:

- detected Ableton process/version in helper output: PID 4868, version 11.2.7;
- export: `Ableton-Render.wav`, 22,556,332 bytes;
- Ableton-created sidecar: `Ableton-Render.wav.asd`, 198,098 bytes;
- WAV SHA-256:
  `8B1B225B3BEFD150881FEF1A64637209313E8A750F27C9B54007C36F00011AB7`;
- audio result: stereo, 44,100 Hz, 63.9350566893424 seconds, WAV;
- deterministic request/export ID:
  `dc6db04428e9fe65ae5eec21c18752c8dd90c82485372f84031b712e93567438`;
- analysis ID: `analysis-dc6db04428e9fe65`;
- result: `completed`, 10 descriptors, zero issues, bounded limitation text;
- disconnect completed; reconnect returned `connected` with the same real
  Ableton PID/version;
- duplicate submission on the live host returned `duplicate` without a second
  job;
- after a complete bridge restart on a new port/new token, the genuine rendered
  file was reaccepted and produced the same deterministic result identity;
- both bridge processes released their ports and were stopped without touching
  Ableton.

This proves the tested rendered-export workflow with **Ableton Live 11.2.7**.
It does not claim control-surface integration, automatic rendering, other Live
11 builds, Live 10, or Live 12. One distinct Ableton render was produced; a
second distinct operator render was requested but was not required to fabricate
the result. Repeatability is supported by reconnect, duplicate, and full bridge
restart/reanalysis evidence, but multi-render coverage remains a limitation.

## Failure and concurrency matrix

Automated tests passed for bridge unavailable, wrong token, malformed/expired
handoff, protocol mismatch, unsupported client, malformed JSON, oversized body,
nonexistent path, directory named `.wav`, traversal/absolute path, incomplete
WAV, unsupported/non-WAV content, duplicate/concurrent duplicate submission,
client timeout, bounded analysis failure, disconnect during active analysis,
shutdown ordering, reconnect, bridge restart, and helper process detection.

The symlink test is skipped when the Windows user lacks symlink privilege. A
separate real Windows junction/reparse probe passed with `unsafe_path`, proving
the platform guard. Ableton itself was not terminated or restarted because the
task explicitly protected the running process and open user session; that row is
not represented as a PASS.

## Capability and Desktop truth

The real workflow justifies moving `daw_integration` from `PLANNED` to
`VERIFIED`, not `PRODUCTION`. The registry now states the exact rendered-export
boundary and tested-version evidence. Desktop Core still marks it unavailable
with `not_exposed_in_desktop`; there is no fake Ready state, installer component,
or DAW workspace. `rag_retrieval`, `llm_reasoning`, `audio_intelligence`, and
`memory_learning` retain distinct lifecycle, dependency, readiness, and Desktop
policy states. Importability is not treated as readiness.

## Model/cache, persistence, Data Root, and packaging audits

Every nonlocal Transformers/SentenceTransformers load now receives the explicit
configured PHASENOX model cache directory; local assets remain local-only. The
Desktop Core optional model controls stay unavailable, so no release-visible
action can silently download into a default Hugging Face cache. The configured
runtime cache is not yet automatically derived from Sprint 18's Desktop pointer;
future ML profiles must bind that contract before becoming available.

No Data Root selection, pointer, installer handoff, persistence path, schema, or
identity changed. The `soundbrain` collection, compatibility engine keys,
serialized `noisyne.*` IDs, `brain.*` shim, `NOISYNE_ROOT`, and
`SOUNDBRAIN_ROOT` remain frozen. `PHASENOX_ROOT` remains canonical-first.

Desktop Core package/profile guards passed. Sprint 21 did not add Torch, CUDA,
ONNX, Chroma, PyArrow, models, tests, audits, Ableton development state, or user
media to the standard bundle. The helper remains source-only and optional.

## Shutdown, resources, and soak

- Desktop open/close: 10/10 PASS. Scheduler shutdown now waits before Qt worker
  teardown.
- Bridge start/stop: 10/10 PASS; ports released and relaunches succeeded.
- Connect/disconnect/reconnect: 10/10 PASS.
- Core analysis fixture: 10/10 PASS.
- Exact-byte report export: 10/10 PASS.
- Job submit/cancel/shutdown subset: 10/10 iterations (40 assertions) PASS after
  hardening.
- Persistence safety: four runs, 36/36 PASS. Fake SQLite fixtures now explicitly
  close handles, fixing the Windows rename/cleanup lock without changing
  production persistence.

The scheduler soak exposed that resource snapshots imported Torch merely to
observe GPU state, causing unpredictable multi-second startup and a timeout.
Resource probing now observes Torch only when a caller already loaded it. A
fresh-process execution guard proves the scheduler does not initialize Torch.

An unrelated full-regression edge case was also closed: extreme dB conversion
already raised `ValueError`, but NumPy could select a different error-message
branch. Both overflow and underflow now preserve the established
`not representable as a positive float64` contract.

No orphan bridge process, client process, server thread, locked WAV, duplicate
job, stale port, or duplicate Desktop log handler remained in the tested paths.

## Regression and quality results

Current test collection is 1,252 tests. All current top-level and Desktop UI
test files were executed in isolated Python processes to avoid the known native
Windows order interaction: **1,251 passed, 1 skipped**. The sole skip is Windows
symlink creation privilege; the junction/reparse equivalent passed separately.

Focused/repeated results include:

- Ableton bridge/client: 37 passed, 1 skipped before the capability assertion;
  the final bridge plus Desktop capability run passed 27/27;
- Sprint 15 application service: 19 passed;
- Sprint 15.5 ONNX/GPU: 18 passed;
- Sprint 16 scheduler final: 28 passed;
- Sprint 14 performance: 29 passed;
- all 23 Desktop UI files: 140 passed;
- identity, branding, distribution, packaging, RAG, reference, persistence,
  runtime, application-root, analysis, and service families: PASS.

Ruff, Black check, compileall, and `git diff --check` are final commit gates and
are recorded with the final handoff. PowerShell/Inno/payload sources were not
changed, so no installer or bundle rebuild was warranted.

## Legacy identity census

Tracked literal counts at audit time:

- `noisyne`: 287
- `NOISYNE`: 121
- `Noisyne`: 73
- `soundbrain`: 254
- `SoundBrain`: 218
- `SOUNDBRAIN`: 70
- total: 1,023

Sprint 21 introduced zero added lines containing those tokens. The R10
allowlist/classification remains applicable: all live occurrences are approved
compatibility/persistence contracts (A), and all non-live occurrences are
historical records (D). **B = 0, C = 0**. No production import depends on
`noisyne.*`.

## Sprint 19C status and master open-item inventory

No eligible disposable Windows environment was found. Windows Sandbox and
Hyper-V remain unavailable without an elevated feature change/reboot; VMware,
VirtualBox, Docker, clean Windows CI, and a cloud/secondary clean machine were
not available. No elevation, provisioning, reboot, or fabricated clean-machine
PASS was attempted. The Sprint 19C matrix remains 18 `BLOCKED / NOT_EXECUTED`
rows and technical/public release remains NO-GO.

### CRITICAL (1)

1. **Genuine disposable Windows release certification is unexecuted.** This
   grouped gate includes no-Python/no-VC++ native closure; default/custom install;
   first-launch, custom, legacy and unavailable Data Root with no silent C:
   fallback; offline/no-download proof; restart; upgrade/repair/downgrade;
   app-only uninstall/reinstall; non-ASCII/space/read-only paths; packaged
   Analyze, Reference/report and Task Center smoke; and Defender/SmartScreen
   observation. It may not be decomposed to make any essential row disappear.

### HIGH (3)

1. Legal publisher/copyright identity is unresolved.
2. Third-party license review is unresolved; generated inventory is not legal
   approval.
3. Authorized production signing and SmartScreen reputation policy are
   unresolved. The RC remains intentionally unsigned.

### MEDIUM

1. The Ableton helper has verified source/runtime evidence but no release-owned
   optional installer/package or multi-version support claim. It remains outside
   Desktop Core and hidden.
2. A future ML profile must bind runtime model/cache paths to the selected
   Desktop Data Root contract before enabling downloads. Desktop Core remains
   correctly gated today.
3. Full-suite same-process native ordering remains a Windows test-runner risk;
   the authoritative release regression uses per-file process isolation and all
   isolated files pass.

### LOW

1. A second distinct operator-rendered Ableton export and an intentional Ableton
   application restart would strengthen repeatability. Neither justifies
   destructive automation of the protected running session.

Resolved in Sprint 21: canonical analysis handoff, safe result return, path and
handoff hardening, active-analysis shutdown ordering, Desktop scheduler wait,
SQLite test-handle ownership, remote model cache forwarding, scheduler Torch
initialization, amplitude error-contract drift, capability truth, and B/C
identity drift.

## Local commit chain

1. `e8d6aa5` — `feat(integration): add ableton export analysis client`
2. `682a0f3` — `test(integration): harden ableton export workflow`
3. `9e1a774` — `fix(runtime): bind remote models to phasenox cache`
4. `34dd160` — `fix(integration): harden ableton client lifecycle`
5. `6d84fd2` — `fix(desktop): await scheduler shutdown`
6. `44311fd` — `test(integration): expand ableton failure and soak matrix`
7. `e4c150a` — `test(persistence): close sqlite fixture handles`
8. `19c0c65` — `refactor(capability): verify optional ableton integration`
9. `aa6f617` — `fix(perception): stabilize amplitude range errors`
10. `6448a44` — `fix(scheduler): keep resource probes lightweight`
11. final report commit — this document and final validation record

## Final readiness statement

The optional Ableton rendered-export workflow is genuinely verified on the
detected Ableton Live 11.2.7 installation and is truthfully excluded from
Desktop Core availability and production claims. The repository is locally
hardened and regression-green, but the unresolved critical clean-machine gate
and three high public-release governance gates make Sprint 21 **FAIL** as final
product closure and S22 **NOT READY**.

No push occurred. Sprint 22 was not started.
