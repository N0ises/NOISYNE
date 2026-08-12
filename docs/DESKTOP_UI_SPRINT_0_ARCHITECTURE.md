# Desktop UI Sprint 0 Architecture

Status: Sprint 0 architecture decision record

Baseline: `04b896f151e17e9d4cf35b31afc4e68a254e0306`

Scope: V1 desktop contracts only; no Qt implementation

## 1. Executable boundary and dependency direction

Repository documentation says Desktop consumes `brain/services/`, but the executable CLI
actually constructs `brain.application.soundbrain_service.SoundBrainService`. That class is
the V1 workflow facade. `brain.services.RuntimeService` is a separate runtime facade and is
not registered by `brain.services.registration.register_services()`.

The desktop dependency rule is:

```text
Qt views/widgets
    -> Presentation (view state and user intent)
    -> UI Contracts (immutable DTOs, enums, adapter protocol)
    -> Application Adapter
         -> V1ApplicationAdapter -> V1 application/service facades
         -> V2ApplicationAdapter -> future V2 application facades
```

Only the V1 adapter may import V1 application/domain result types. Qt and Presentation must
not import `brain.audio.*`, `brain.rag.*`, `brain.memory.*`, runtime/model implementations,
provider implementations, NumPy, Torch, or V1 report/reference models.

### Current contract map

| UI use case | Real V1 entry point | Current result/behavior | Desktop decision |
|---|---|---|---|
| Analyze audio | `SoundBrainService.analyze(AnalysisRequest)` | Synchronous `AnalysisResponse`; deterministic core plus optional stages | V1 adapter maps a UI command/result DTO; never expose the response directly |
| Compare references | `SoundBrainService.analyze()` with `reference_path`, internally `ReferencePipeline.run()` | Comparison is optional; failure becomes a warning and `comparison=None` | Same operation, with explicit partial-result/warning mapping; do not call the pipeline from Presentation |
| Export analysis report | `AnalysisRequest.output_path` -> `ReportExporter.save_json()` | JSON only; atomic write | Expose JSON only through an adapter export command |
| Export reference report | `reference_output_directory` -> `ReferenceReportBuilder` | JSON and Markdown | Expose both descriptors when a reference result exists |
| DAW/workflow export | `brain.integration.BaseWorkflowAdapter` | Placeholder JSON/text/Markdown; no DAW communication | Do not present as real DAW integration or general report export |
| Capability status | `RuntimeService.capabilities()` -> static runtime registry | Lifecycle metadata and static explanation only | Adapter must build `CapabilitySnapshot`; current machine availability remains unknown until probed |
| Runtime status | `ModelRuntime`, `DeviceManager`, loaded-model cache, global settings | No aggregate status or provider/model health check | Add an adapter/application-level snapshot query before a status page claims readiness |
| Settings | import-time `brain.infrastructure.config.settings` from packaged YAML | Read only; no validation/update/persistence API | V1 desktop settings are read-only |
| Errors | audio/runtime exception classes, `ValueError`, raw exceptions, warning strings | No common UI error contract | Adapter translates at its boundary and preserves partial results |
| Long work | Synchronous `analyze()`/`review()`/`ReferencePipeline.run()` | No operation ID, callbacks, progress, timeout, or cancellation probe | Run off the GUI thread, but advertise only indeterminate progress and limited cancellation |

## 2. Stable UI contracts

Place future contracts in a UI-owned, Qt-free module. Use frozen dataclasses/enums and plain
scalars/collections. File locations may use `pathlib.Path`; payloads must not contain V1
domain objects or tensors/arrays.

Minimum contracts:

- `DesktopApplicationAdapter`: queries product/capability/runtime/settings snapshots, starts
  analysis/export operations, observes events, and requests cancellation.
- `AnalysisCommand`: source path, optional reference paths and reference intent, optional
  feature flags, human intent, delivery target, and requested export destination.
- `AnalysisViewResult`: stable metadata, normalized metric/value records, engineering issue
  records, optional semantic/reference/mix/plugin sections, report descriptors, status, and
  warnings. The V1 adapter performs all flattening.
- `ReferenceViewResult`: similarity/scores, normalized differences/decisions, summary and
  report descriptors. It contains no `ReferenceComparison`.
- `ReportDescriptor`: report ID, operation ID, kind, format, path, display label, and creation
  time. A descriptor is returned only after the file exists.
- `CapabilitySnapshot`, `RuntimeStatus`, `SettingsSnapshot`, `OperationHandle`,
  `OperationEvent`, `UiError`, and `ProductMetadata` as defined below.

Do not create UI copies of stable scalar input concepts merely for symmetry. DTOs are needed
where they prevent imports of V1 types, hide secrets/runtime objects, normalize inconsistent
errors, or provide V2-stable result shapes.

## 3. Capability truth

```text
CapabilitySnapshot
  id: str
  display_name: str
  lifecycle: planned | implemented | verified | production | deprecated
  availability: available | unavailable | degraded | unknown
  reason_code: str | null
  reason: str | null
  checked_at: datetime | null
  dependencies: tuple[str, ...]
```

Lifecycle and availability are independent. `reason_unavailable` in the V1 registry is static
release metadata, not proof that a dependency is missing on this machine. `has_capability()`
only means a registry key exists. A Ready label requires an executable availability probe (or
a successful recent operation), not `lifecycle == production`.

| User-facing capability | Registry lifecycle | Availability truth at Sprint 0 |
|---|---|---|
| Audio loading, DSP, context, engineering | Production | Unknown until lightweight dependency/path probe; operation failure remains authoritative |
| Reference comparison | Production | Unknown until deterministic audio path can initialize/run |
| CLAP embedding | Verified | Unknown; model is not bundled and may require download/local assets |
| RAG retrieval | Implemented | Unknown; configured corpus and models are not probed |
| LLM reasoning | Implemented | Unknown; default local endpoint/model is not health-checked |
| Report generation | Production | Unknown until destination writability is checked |
| Mix intelligence | Production | Unknown; available only with a successful deterministic analysis result |
| Plugin intelligence | Production | Unknown; depends on successful mix intelligence |
| Audio intelligence | Planned | Unavailable: broader feature is not V1 implementation |
| Memory/learning | Planned | Unavailable: no V1 persistent learning contract |
| DAW integration | Planned | Unavailable: workflow adapters are export placeholders only |

Probe failures must be isolated. For example, unavailable CLAP disables semantic analysis but
does not disable deterministic analysis. Cached snapshots may initially be `unknown`; probes
must run outside the GUI thread and include a timestamp.

## 4. Operations, progress, and cancellation

```text
OperationHandle
  operation_id: str
  kind: analyze | reference | export | runtime_probe
  state: queued | validating | running | cancelling | completed | failed | cancelled
  cancel_requested: bool

OperationEvent
  operation_id: str
  sequence: int
  state: OperationState
  stage: str
  progress: float | null       # 0..1; null means indeterminate
  message: str | null
  cancellable: bool
  result: UI DTO | null
  error: UiError | null
```

Events are ordered by `sequence`; exactly one terminal event is emitted. Completion may carry
warnings and partial results. Failure may also identify a usable partial result. A cancel
request is idempotent and means requested, not completed.

### Honest V1 execution matrix

| Work/stage | Work type | Progress now | Cancellable now |
|---|---|---|---|
| Validate command before dispatch | UI/adapter | Determinate | Yes, while queued |
| Audio load/validation | Blocking I/O + decode | Indeterminate | No after V1 call starts |
| DSP/context/engineering | CPU | Indeterminate | No |
| CLAP/model load/inference | I/O + CPU/GPU | Indeterminate | No |
| Reference comparison | I/O + CPU/model | Indeterminate | No |
| RAG/provider reasoning | I/O/model | Indeterminate | No timeout/cancel contract |
| Mix/plugin enrichment | CPU | Indeterminate | No |
| Report/export write | File I/O | Indeterminate | No; analysis JSON write is atomic |
| Runtime/model service | Long-lived shared service/cache | Snapshot events only | Cache unload is a separate command, not operation cancellation |

Sprint 1 may cancel a queued executor job. Once `SoundBrainService.analyze()` begins, the UI
must disable Cancel or label it as unavailable. A worker thread keeps Qt responsive but does
not improve these semantics.

The smallest later V1 application change is an optional stage observer plus cancellation
probe at safe boundaries between existing stages. It must be added at the application layer,
not by reaching into DSP/model code from Qt. Do not emit fabricated percentage progress.

## 5. Settings contract and policy

`load_settings()` merges packaged `runtime.yaml`, `models.yaml`, and `audio.yaml`, resolves
paths against an application root, and constructs a process-global settings object at import.
There is no user override, schema version, update validation, atomic persistence, rollback,
reload notification, or restart policy. The loaded `api_key` must never appear in a UI DTO,
log, error detail, or diagnostic export.

Sprint 1 policy: expose a sanitized, read-only `SettingsSnapshot`. All `writable` flags are
false. It may show effective non-secret values and the source (`packaged_default`). It must
show credential presence as a boolean only.

A future write contract, before any field becomes editable, must provide:

```text
read_effective() -> SettingsSnapshot
validate(SettingsUpdate) -> ValidationResult
persist(SettingsUpdate, expected_revision) -> SettingsSnapshot
```

It must use a versioned user-scoped location supplied by a platform path resolver, atomic
replace plus recoverable backup, optimistic revision checking, secret references rather than
secret values, and per-field `hot_apply | restart_required`. Install/package directories and
the current working directory are not valid user-write locations. Until this exists, Settings
is status-only.

## 6. Report/export truth

| Output | Format | Implemented V1 path | UI claim |
|---|---|---|---|
| Analysis report | JSON | `ReportExporter.save_json()` | Supported |
| Analysis report | Markdown/PDF/HTML/CSV | None | Unsupported |
| Reference report | JSON | `ReferenceReportBuilder.save_json()` | Supported |
| Reference report | Markdown | `ReferenceReportBuilder.save_markdown()` | Supported |
| Workflow analysis/plugin export | JSON | Placeholder workflow adapters | Experimental placeholder; not DAW integration |
| Workflow processing chain | JSON + text | Placeholder workflow adapters | Experimental placeholder; not DAW integration |
| Workflow report | JSON + Markdown | Placeholder workflow adapters | Experimental placeholder; not the general analysis reporter |

The adapter should expose an allow-list per result type. It must validate the destination,
return only created file descriptors, and map write/serialization failures to `report_export`.
Reference JSON writes are not atomic today; this is a documented gap, not a UI workaround.

## 7. Runtime status

```text
RuntimeStatus
  state: ready | degraded | unavailable | unknown
  requested_device: str
  effective_device: str | null
  device_reason: str | null
  loaded_models: tuple[ModelStatus, ...]
  provider: ProviderStatus          # name, availability, reason, checked_at; no credentials
  paths: tuple[PathStatus, ...]     # kind, resolved path, exists, readable, writable
  configuration_source: str
  capabilities: tuple[CapabilitySnapshot, ...]
  checked_at: datetime
```

`DeviceManager.detect()` currently reports CUDA/MPS/CPU and `available_models()` reports only
loaded cache entries. Neither proves a configured model or provider can initialize. Runtime
status therefore needs lightweight, independently failing probes. Importing the status
contract must not import Torch or initialize models; the V1 adapter performs those probes
lazily on a worker.

## 8. Structured UI errors

```text
UiError
  code: str
  category: validation | capability_unavailable | configuration | provider_model |
            cancelled | timeout | report_export | internal
  user_message: str
  technical_detail: str | null
  retryable: bool
  recovery_actions: tuple[RecoveryAction, ...]
  partial_result_usable: bool
  capability_id: str | null
  operation_id: str | null
```

| Source/condition | Category | Typical recovery |
|---|---|---|
| Bad/missing/unsupported/over-duration audio | Validation | Choose another file or correct input |
| Planned feature or failed availability probe | Capability unavailable | Continue without optional feature; open Runtime status |
| Invalid/missing packaged config or unwritable path | Configuration | Show effective source/path; repair configuration |
| Model load, provider endpoint, inference failure | Provider/model | Retry, configure dependency, or continue with deterministic result |
| Cooperative cancellation completed | Cancelled | Start again; never display as failure |
| Explicit application timeout | Timeout | Retry or adjust supported timeout; V1 has no timeout contract yet |
| Serialization or destination write failure | Report/export | Choose writable destination; analysis result remains usable |
| Unexpected exception | Internal | Preserve operation ID, log details, show safe message |

The V1 adapter maps `Audio*Error`, runtime errors, selected `ValueError`/filesystem failures,
and optional-stage warning strings. Tracebacks and secrets remain in protected logs only.

## 9. Known contract gaps and required APIs

Required before a UI can claim the corresponding behavior:

1. A Qt-free `DesktopApplicationAdapter` protocol and V1 DTO mapper.
2. `capability_snapshot()` with real availability probes and reason codes.
3. `runtime_status()` with lazy device/model/provider/path health.
4. Operation IDs/events and an executor boundary. V1 analysis remains non-cancellable after
   dispatch until application-level safe-point hooks exist.
5. Sanitized `settings_snapshot()`. Settings update remains intentionally absent/read-only.
6. Application-level `export_report()` with a truthful per-result format allow-list.
7. Central exception/warning-to-`UiError` translation.
8. `ProductMetadata` supplied once at desktop bootstrap.

Do not modify `SoundBrainService` merely to satisfy UI naming. If stage observation or
cancellation is later approved, make the smallest backward-compatible application-level
addition and retain the existing synchronous call for CLI/tests.

## 10. Sprint 1 packaging risks and environment decision

- The repository requires Python 3.12+. `venv` is healthy on Python 3.12.10; the ambient
  `python` is 3.11.15 and is unsupported for this project. Sprint 1 commands/CI must use a
  reproducible Python 3.12 environment.
- Requirements are not locked. PySide6, `pytest-qt`, and PyInstaller are absent from both
  project metadata and the checked V1 environment. Add desktop/test/packaging dependencies
  through project metadata and lock the supported environment in Sprint 1.
- Torch, torchaudio, transformers, sentence-transformers, librosa, soundfile, ChromaDB and
  SciPy introduce large native binaries and dynamic imports. The packaging walking skeleton
  must test representative imports outside the checkout and record hooks/hidden imports.
- Qt platform plugins, TLS/image plugins, application icons, and future UI resources need
  explicit packaging verification.
- Packaged YAML via `importlib.resources` is wheel-safe, but effective model/cache/log/report
  paths are currently derived from the application root. A frozen/install directory may be
  read-only or ephemeral. The adapter/platform-path boundary must supply writable user data
  paths before packaging depends on them.
- Models are not bundled. First-run/missing-model behavior and offline behavior must remain
  explicit; no startup model download.
- Runtime status must remain lazy so showing the shell does not import/load every ML backend.
- `ReportExporter` is atomic; reference export is not. Interrupted reference export can leave
  a partial file pair.

Sprint 0 feasibility result: no architectural blocker was proven, but packaging is unverified
because no Qt or packager dependency exists. The Sprint 1 Windows walking-skeleton gate is a
release blocker, not a deferred release task.

## 11. Sprint 1 desktop testing strategy

- Unit-test DTO construction, enum/state transitions, error mapping, format allow-lists,
  capability readiness rules, settings redaction, and branding fallback without importing Qt
  or V1 domain modules.
- Test `V1ApplicationAdapter` with injected fake `SoundBrainService`/runtime/config/export
  facades. Assert domain objects are flattened and optional failure produces degraded partial
  results.
- With `pytest-qt`, test launch/close, navigation shell, queued/running/terminal signal
  delivery, duplicate/late event rejection, and an indeterminate non-cancellable V1 operation
  using `QT_QPA_PLATFORM=offscreen` where supported.
- Add integration tests with the committed small WAV fixture for deterministic analysis,
  missing/invalid audio, optional reference failure, JSON export, and reference JSON/Markdown.
- Add deterministic fault injection for provider/model/config/export failures. Do not require
  network access or model downloads in the default desktop suite.
- Keep existing V1 service/runtime/reference tests green. Run a separate Windows packaged
  smoke test from outside the checkout for startup, representative native imports, lightweight
  runtime initialization, writable paths, and clean shutdown.

## 12. Product identity and branding

```text
ProductMetadata
  display_name: str
  application_title: str
  version: str
  organization_name: str
  organization_domain: str | null
  application_id: str              # stable internal ID for OS integration/storage
```

Desktop bootstrap supplies one immutable instance. Views obtain labels/titles from
Presentation, never string literals. `display_name` and `application_title` may later change
without changing the repository, Python package, CLI command, backend namespaces, stable
`application_id`, or existing user-data location. Version should come from installed package
metadata with a development fallback. Brand assets/tokens remain a separate central design
system concern for the later brand sprint.

## 13. V1 to V2 migration seam

When `V1ApplicationAdapter` is replaced by `V2ApplicationAdapter`, these remain unchanged:

- Qt pages/widgets and their signals;
- Presentation state, commands, and reducers/view-models;
- all UI DTOs, operation events, capability/runtime/settings/error contracts;
- product metadata consumption and display-name behavior;
- report format negotiation and descriptor rendering;
- desktop unit/component tests and adapter conformance tests.

Only adapter construction, V2 request/result mapping, capability/runtime probes, and backend
error translation change. Any V2-only feature must appear as a new capability/contract version,
not as an `isinstance(V1Type)` or provider-specific branch in Presentation.
