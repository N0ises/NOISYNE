# PHASENOX Sprint 20 DAW / Ableton Bridge Report

## Executive verdict

| Question | Verdict |
|---|---|
| Sprint 20 implementation | **PASS** |
| PHASENOX-side DAW bridge | **IMPLEMENTED** |
| Real Ableton interoperability | **BLOCKED** |
| `daw_integration` lifecycle | **PLANNED** (unchanged) |
| Desktop exposure | Hidden / unavailable; no Ready or Connected claim |

Sprint 20 establishes a small, truthful PHASENOX-side boundary: an authenticated
loopback protocol handshake and a stable WAV-export intake queue. It does not add
an Ableton-side component, DAW control, project editing, automation, plugin
hosting, or analysis execution. Simulated-client tests prove only the PHASENOX
boundary. They do not prove Ableton compatibility.

Sprint 19C clean-machine execution remains blocked by infrastructure and remains
a mandatory pre-S22 release gate.

## Repository and safety baseline

- Branch at precheck: `v2-development`
- Local and `origin/v2-development` precheck SHA:
  `4bdf2b861e37b23f0d7bc44b346455f56941007a`
- Tracked tree and index were clean at precheck.
- Protected untracked Desktop roadmap files were not touched.
- Local and remote `desktop-ui` remained at
  `e2dd11e4193f32cd4f31cda5bca8cbd322bec3af`.
- No protected branch, persistence contract, packaging identity, brand asset, or
  installer artifact was changed. Nothing was pushed.

## Repository inventory

The search covered tracked production code, tests, scripts, and documentation for
DAW, Ableton, Live, bridge, plugin/VST, Max for Live/M4L, MIDI, OSC, IPC/socket,
transport, session/project/track, and audio import/export concepts. Generic terms
such as `live`, `session`, and `export` produced many unrelated application,
evaluation, report, and release-script matches; those are not DAW integration.

| Classification | Relevant files | Finding |
|---|---|---|
| A — executable production | `phasenox/integration/base.py`, `ableton.py`, `factory.py`, `models.py` | Existing adapters perform deterministic file exports only. They deliberately do not communicate with a DAW, process, API, or socket. |
| A — executable production | `phasenox/integration/ableton_bridge.py` | New PHASENOX-side loopback server with health, version handshake, and bounded stable-WAV queue. No Ableton control. |
| B — application/domain contract | `phasenox/integration/daw_bridge.py` | New Qt-free bridge status, identity, export, import-request, capability, and error contracts. |
| A — capability truth | `phasenox/runtime/capabilities.py` | `daw_integration` is `PLANNED`, not freeze-tested, and reports no runtime DAW integration. Unchanged. |
| A — Desktop presentation | `phasenox/ui/adapters/v2.py` | `daw_integration` is hidden from current capability presentation. Unchanged. |
| C — prototype/foundation | `phasenox/integration/{reaper,cubase,flstudio,studio_one}.py` | Deterministic placeholder/file-export adapters, not vendor connections. |
| D — tests | `tests/test_integration_adapters.py`, `tests/test_integration_factory.py` | Prove deterministic file behavior and adapter selection, not live DAW behavior. |
| D — tests | `tests/test_ableton_bridge.py` | Simulated local client tests for only the new PHASENOX-side boundary. |
| E — current documentation | `docs/ARCHITECTURE_v2.md`, `MODULE_MAP.md`, `CAPABILITY_REGISTRY.md`, `ROADMAP_v2.md`, `EXECUTION_PLAN_v2.md`, `TECHNICAL_DEBT.md` | Describe planned DAW integration or explicitly limited file adapters. |
| E — design/history | `docs/bible/37_DAW_Integration.md`, `docs/bible/05_Roadmap.md`, `docs/bible/06_Sprint_Tracker.md`, `docs/roadmap/*` | Aspirational/historical designs; not executable evidence. |

No tracked production implementation was found for an Ableton `.als` parser,
MIDI Remote Script, Max for Live device, OSC endpoint, named pipe, VST/plugin host,
transport or timeline control, process attach, rendered-stem watcher, or Ableton
project editor. The previous `AbletonAdapter` name did not imply those features.

## Capability registry truth

The registry entry remains:

- lifecycle: `PLANNED`
- requirements: DAW-specific adapters and automation APIs
- unavailable reason: no runtime DAW integration
- freeze tested: false
- machine availability: planned capabilities remain unavailable
- Desktop visibility: hidden

The new bridge foundation does not satisfy the registry's broader DAW automation
acceptance criteria. Consequently, Sprint 20 does not promote the capability to
implemented, verified, Ready, or production.

## Ableton-specific reality check

Ableton Live is installed for the current interactive Windows user:

- product: Ableton Live 11 Suite
- detected version: 11.2.7
- executable: `D:\ProgramData\Ableton\Live 11 Suite\Program\Ableton Live 11 Suite.exe`
- user configuration directory detected for Live 11.2.7
- process state during audit: not running

The repository had no code tied to that executable, `.als` format, user library,
temporary/export folders, Remote Scripts, M4L, OSC, or MIDI. Detection was
read-only. No Ableton configuration or project was changed and Ableton was not
launched, because there is no vendor-side component capable of exercising the
new protocol. A launch alone would not constitute interoperability evidence.

## Strategy comparison

| Strategy | Cost/deployment | Access and latency | Security/reliability | Packaging and testability | Decision |
|---|---|---|---|---|---|
| File-based bridge | Low; user renders WAV to an explicit folder | Rendered audio only; non-real-time | Small path/watcher surface if bounded | Stdlib PHASENOX side; easy fixture tests | Useful transport primitive |
| Ableton Remote Script | Medium/high; version-sensitive Ableton installation | Session/track/control access; interactive | Must constrain commands and manage Live API lifecycle | Separate vendor-side install; needs real Live matrix | Future candidate |
| Max for Live | Medium; requires M4L device deployment | Rich session/device messaging | Device lifecycle and localhost authentication required | Separate component; Live edition/version constraints | Roadmap-consistent future client |
| Local IPC | Low/medium on PHASENOX side, but still needs a DAW-side client | Depends on client; low local latency | Loopback, authentication, versioning, limits required | Lightweight and simulation-friendly | Selected protocol boundary |
| Plugin/VST | Very high; native SDK/host and signing burden | Real-time audio/parameter access | Largest crash and compatibility surface | Contaminates release profile and requires DAW matrix | Rejected for Sprint 20 |

The selected scope is an evidence-backed combination of Option 1 and a bounded
part of Option 3: audit plus PHASENOX-side IPC contract smoke. A future separately
shipped Ableton-side M4L or Remote Script component may act as the client. Sprint
20 does not implement or claim that component.

## Selected architecture and protocol

`AbletonBridgeServer` uses Python's standard-library threaded HTTP server and
binds only to `127.0.0.1`. Port `0` (ephemeral selection) is the default. It
exposes:

- authenticated `GET /v1/health`
- authenticated `POST /v1/handshake`
- authenticated `POST /v1/exports`
- protocol version `1`
- expected future client identity `ableton-m4l`

The handshake records bounded client and DAW version strings. A protocol mismatch
sets `VERSION_MISMATCH` and never reports connected. The export endpoint requires
a successful current-process handshake and returns only status/error data.

The Qt-free contract layer contains:

- `DawBridgeStatus`
- `DawConnectionState`
- `DawProjectIdentity`
- `DawTrackIdentity`
- `DawAudioExport`
- `DawImportRequest`
- `DawBridgeCapability`
- `DawBridgeError`

No vendor objects enter UI contracts. No Qt or optional ML/RAG dependency is
imported by this boundary.

## Security and file boundary

- loopback-only bind; no remote-network listener
- generated high-entropy bearer token by default; constant-time comparison
- token is absent from health/status responses
- 64 KiB default request-body limit
- five-second default socket request timeout
- bounded identity fields and JSON-object-only payloads
- explicit export root; it must already exist and be a readable, non-link directory
- relative paths only; traversal, absolute paths, links, and root escape rejected
- WAV extension plus RIFF/RF64 WAVE header validation
- 20 GiB maximum export size
- unchanged size and modification time over a stability interval before enqueue
- content-derived export identity prevents duplicate queueing in the process
- no recursive watcher, arbitrary command execution, process launch, DAW mutation,
  analysis, persistence, or network/model download on request threads
- malformed requests return bounded errors without exposing credentials

The bridge queue is deliberately in-memory. Restart does not claim durable
deduplication or configuration. Persistent configuration would require a separate
approved contract.

## Smoke workflow actually implemented

1. An explicit existing export root is supplied to PHASENOX.
2. The PHASENOX bridge starts on loopback and reports `BRIDGE_AVAILABLE`, not
   connected.
3. A token-authenticated simulated client negotiates protocol version 1.
4. The client supplies bounded project/track identity and a relative WAV path.
5. PHASENOX verifies containment, regular-file type, size, stability, and WAV
   header.
6. A `DawImportRequest` is queued once and can be consumed outside the request
   thread.
7. A repeat submission returns duplicate status and is not requeued.
8. Stop/restart returns to bridge-available/not-connected state.

Analysis execution and result return are not implemented in Sprint 20. The queue
is the explicit gateway for a future application-service handoff; claiming an
analysis PASS would be false.

## Desktop UX boundary

Desktop remains unchanged. It may not display Ready, Connected, Live control, or
full Ableton integration. Truthful future states supported by the contracts are:

- Ableton: not configured
- Ableton: bridge available, DAW not connected
- Ableton: protocol connected (only after a real client handshake)
- Ableton: import/export bridge only

Until a reviewed Desktop adapter is added, `daw_integration` remains hidden and
unavailable. Current plugin intelligence remains recommendations/read-only; it
does not execute plugins, host VSTs, or control a DAW.

## Packaging impact

The PHASENOX-side implementation adds only standard-library dependencies and is
not wired into Desktop startup or the Desktop Core build. It adds no Torch, ONNX,
Chroma, PyArrow, Qt, model, VST, MIDI, OSC, or download dependency. There is no
installer component or socket permission change in this sprint.

A useful live workflow still requires a separately identifiable Ableton-side M4L
device or Remote Script client, with its own install/uninstall, version matrix,
security review, and artifact verification. It must not be silently folded into
Desktop Core.

## Failure behavior

| Condition | Current safe result |
|---|---|
| Ableton absent or not running | PHASENOX server may be bridge-available; never connected |
| Ableton-side bridge absent | Bridge-available with explicit not-handshaken reason |
| Version mismatch | HTTP conflict and `VERSION_MISMATCH`; no connected claim |
| Export root/path unavailable | Startup/submission rejected; no fallback path |
| Incomplete/changing export | Observed but not queued |
| Unsupported/non-WAV file | Rejected |
| Connection timeout | Socket request bounded; no Desktop crash path introduced |
| Malformed/oversized request | Bounded 4xx error |
| PHASENOX unavailable | Client connection fails; no DAW-side component exists yet |
| Analysis failure | Outside Sprint 20; no analysis is run on bridge threads |
| Shutdown/restart | Clean shutdown; connection identity cleared |

## Test evidence

Tests were run as isolated pytest processes to avoid the known Windows native
test-order issue.

| Suite | Result |
|---|---:|
| New Ableton bridge boundary | 17 passed |
| Existing integration adapters | 27 passed |
| Integration factory | 9 passed |
| Desktop integration | 7 passed |
| Desktop startup/shell smoke | 10 passed |
| Dependency direction | 2 passed |
| Sprint 15 application service | 19 passed |
| Sprint 16 scheduler | 27 passed |
| Desktop Core packaging guard | 8 passed |
| Technical identity freeze | 10 passed |
| PHASENOX identity | 6 passed |
| Branding | 6 passed |
| Distribution/fresh install | 4 passed |
| **Total** | **152 passed** |

The new test matrix covers bridge unavailable/stopped, configured but not
connected, authenticated handshake, version mismatch, unsupported client,
malformed/oversized payload, path traversal and absolute-path rejection, supported
stable WAV, incomplete file observation, duplicate suppression, import-request
identity, unavailable/invalid root, shutdown/restart, capability truth, and the
absence of Torch, ONNX Runtime, Chroma, PyArrow, and PySide6 after a fresh bridge
import.

### Real Ableton matrix

| Evidence | Result |
|---|---|
| Ableton installation/version detection | PASS (read-only, Live 11.2.7) |
| Ableton-side component installation | BLOCKED — component does not exist |
| Real Ableton handshake | BLOCKED |
| Disposable-project export/import | BLOCKED |
| Analysis/result return | BLOCKED — application handoff not implemented |
| Disconnect/no-crash/data-integrity observation | BLOCKED |

No Ableton version range is claimed. Live 11.2.7 is only the locally detected
installation, not a compatibility certification. Live 10, 11, and 12 compatibility
is unverified.

## Repeatable future live validation

1. Build and review a separately packaged protocol-v1 Ableton client.
2. Use a disposable Windows user or VM and a new empty Ableton project.
3. Start PHASENOX with an empty explicit temporary export directory and capture
   its ephemeral endpoint/token through an approved handoff.
4. Confirm bridge-available/not-connected before loading the client.
5. Load the client, confirm exact protocol and version handshake, and verify the
   connected status comes only from that handshake.
6. Generate local synthetic audio, render a WAV into the chosen directory, and
   submit its relative path with project/track identity.
7. Verify one queued import, no duplicate, and no access outside the directory.
8. After an application-service consumer exists, verify analysis/result/error
   return separately.
9. Disconnect, restart both sides, and inspect for crashes, project mutation,
   unexpected network traffic, model downloads, or user-data changes.

## Commits

- `9c80cee` — `feat(integration): add bounded ableton smoke bridge`
- `bc4b86e` — `test(integration): validate ableton bridge boundary`
- Report — the local commit containing this document

No commit was squashed or pushed.

## Known limitations and Sprint 21 implications

- No Ableton-side M4L device or Remote Script exists.
- No live vendor handshake or supported Ableton range is proven.
- No application-service analysis consumer/result channel is connected.
- No persistent configuration or cross-restart deduplication is claimed.
- No Desktop configuration/status UI is exposed.
- No installer or separate Ableton component packaging exists.
- The loopback HTTP protocol needs an end-to-end vendor-client threat review
  before distribution.

Any later sprint must preserve the separation between PHASENOX-side correctness,
real Ableton interoperability, and DAW automation readiness. Sprint 21 was not
started as part of this work.

## Final status

At report preparation, the only expected non-Sprint untracked files were the two
protected Desktop roadmap documents. Final Git status and quality results are
recorded in the task handoff after the report commit. No push was performed.
