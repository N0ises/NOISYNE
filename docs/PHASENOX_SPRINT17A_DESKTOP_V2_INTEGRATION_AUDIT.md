# PHASENOX Sprint 17A Desktop V2 Integration Audit

## Executive verdict

**GO for a constrained Sprint 17B integration. NO-GO for a wholesale branch
merge, an all-features-enabled desktop, or a claim that every Desktop workflow
is scheduler-native.**

The frozen Desktop architecture is worth preserving: its dependency direction,
Qt-free contracts, presentation store, error boundary, worker isolation, and
truthful unavailable states are sound. The correct integration is a selective
semantic replay into `phasenox.ui`, with a new `V2ApplicationAdapter` and a
separate scheduler gateway. It must not merge or copy the frozen backend tree.

The principal gap is contractual, not visual. Frozen Desktop analysis and
reference screens consume the rich output produced by canonical
`PhasenoxService`; `PhasenoxV2Service` currently returns narrower Sprint 15
evidence payloads. Sprint 16 provides real job lifecycle and bounded history,
but no event subscription, incremental service-stage progress, hard
cancellation, live telemetry, or deterministic non-blocking shutdown. A hybrid
is therefore the only truthful Sprint 17B design.

## Audit baseline and method

| Subject | Frozen identity |
| --- | --- |
| Working branch | `v2-development` |
| V2 HEAD | `1aa25ed365d860b0661c2104d5e45336fbc9e351` |
| Desktop branch | `desktop-ui` |
| Desktop HEAD | `e2dd11e4193f32cd4f31cda5bca8cbd322bec3af` |
| Common ancestor | `04b896f151e17e9d4cf35b31afc4e68a254e0306` |
| Desktop-only commits | 24 |
| V2-only commits | 61 |

The Desktop commit was inspected only through `git show`, `git grep`,
`git ls-tree`, and comparisons of immutable Git objects. It was never checked
out, merged, rebased, cherry-picked, or modified. Current production and tests
were read only. This audit document is the sole workspace addition.

## 1. Frozen Desktop architecture

### Inventory

The frozen tree contains 57 files under `brain/ui`, including six design-system
files and six resource files, plus 47 Desktop test files (three under `e2e`) and
four packaging-tool files.

| Layer | Exact files / principal types | Responsibility |
| --- | --- | --- |
| Launch/bootstrap | `brain/ui/__main__.py`, `app.py` | Argument parsing, `QApplication`, theme/icon, session load, exception hook, runtime probe, clean close |
| Product metadata | `branding.py`, `contracts.ProductMetadata` | Installed version, display/title, organization and stable application ID |
| Window/shell | `main_window.py:MainWindow`, `presentation.py:ShellViewState`, `shell_surfaces.py` | Sidebar, workspace, runtime surface, notifications, operation strip, status bar |
| Navigation/workspace | `presentation_state.py:PageId`, `pages.py:PageHost` | Persistent pages and presentation-owned navigation |
| Application state | `state.py:ApplicationStateStore` | Process lifecycle and status message |
| Presentation state | `presentation_state.py`, `presentation_store.py:PresentationStore` | Immutable UI/session/operation/result state and transition enforcement |
| UI contracts | `contracts.py` | Qt-free DTOs, enums, errors and `DesktopApplicationAdapter` protocol |
| Backend adapter | `adapters/v1.py:V1ApplicationAdapter` | Only intended deep-backend import boundary |
| Workers | `workers.py`, `worker_binding.py` | `QThreadPool` wrapper for blocking synchronous adapter calls and ordered UI events |
| Analysis | `analysis_controller.py`, `analyze_page.py`, `analyze_state.py`, `result_view.py`, `result_presentation.py` | Input validation, feature gating, execution and results |
| Reference | `reference_controller.py`, `reference_page.py`, `reference_state.py`, `reference_result_view.py` | Single/multiple-reference workflow and detailed comparison display |
| Intelligence | `intelligence_page.py`, `intelligence_presentation.py` | Retained engineering/mix/plugin/reasoning/reference findings |
| Knowledge | `knowledge_controller.py`, `knowledge_page.py`, `knowledge_state.py` | Capability-gated RAG query surface |
| Reports | `report_controller.py`, `reports_page.py` | Preview, copy/export and open-directory operations |
| Settings/runtime | `settings_controller.py`, `settings_page.py` | Read-only settings and runtime refresh |
| Voice/Agent | `voice_contracts.py`, `agent_contracts.py`, `voice_page.py` | Presentation and safety/permission contracts only; no provider/executor |
| Dashboard | `dashboard.py` | Recent state, runtime and navigation summaries |
| Persistence | `session_persistence.py` | Versioned Desktop session serialization, independent of backend stores |
| Resilience | `errors.py:ExceptionBoundary`, `logging_setup.py` | Safe errors, global exception hook, user-scoped desktop log |
| Paths | `paths.py:DesktopPathLayout` | Qt `AppLocalDataLocation`, session/log/cache/model/report locations |
| Branding | `brand_resources.py` | Package-resource-to-Qt icon/pixmap bridge |
| Packaging | `packaging_probe.py`, `performance_probe.py`, `tools/packaging/noisyne.spec`, build/verify scripts | Frozen one-folder PyInstaller candidate and probes |

### Bootstrap and lifecycle

`app.run()` constructs `V1ApplicationAdapter`, creates the Qt application,
prepares packaged writable directories, configures logging, loads
`session-v1.json`, installs `ExceptionBoundary`, creates a shared
`WorkerExecutor`, launches an asynchronous runtime-status probe, and blocks in
the Qt event loop. On close it waits for the QThreadPool, uninstalls the
exception hook, and saves/closes session persistence.

`MainWindow` owns controllers but not backend models. It renders only from
`ApplicationStateStore` and `PresentationStore`. Its global surfaces are:

- left identity/navigation rail;
- top runtime status linked to Settings;
- notification/recovery surface;
- persistent page host;
- bottom operation status/cancel surface;
- Qt status bar.

Logging writes to `<Qt AppLocalDataLocation>/logs/desktop.log`, falling back to
stderr. `ExceptionBoundary` logs the traceback and presents only a safe
`unexpected_internal_error` DTO.

### Navigation and current frozen truth

`NAVIGATION_ORDER` contains Overview, Analyze, References, Intelligence, Voice,
Knowledge, Reports and Settings. `RUNTIME_STATUS` exists as a page ID but is not
in navigation; runtime details live in Settings and the top bar. There are no
separate Memory, Agent or Plugins pages. Agent presentation is embedded in
Voice; plugin recommendations are a section of Intelligence.

The frozen release record explicitly says Voice has no provider and Agent has
no executor. Knowledge executes only when RAG is reported available. Analysis,
References, Reports and their retained Intelligence results are the supported
workflow.

## 2. Frozen application-adapter contract

`DesktopApplicationAdapter` is a synchronous, runtime-checkable, Qt-free
protocol:

| Method | Input | Output | Frozen behavior |
| --- | --- | --- | --- |
| `product_metadata()` | none | `ProductMetadata` | Static identity plus installed distribution version |
| `capability_snapshots()` | none | tuple of `CapabilitySnapshot` | Lifecycle mapped from registry; planned unavailable; all other machine availability initially unknown |
| `runtime_status()` | none | `RuntimeStatus` | Lightweight paths/config snapshot; device/model/provider readiness deliberately unknown |
| `settings_snapshot()` | none | `SettingsSnapshot` | Effective values, all read-only; API key represented only as configured/not configured |
| `analyze(command)` | `AnalysisCommand` | `AnalysisViewResult` | Calls rich service facade and translates domain models into UI DTOs |
| `compare_references(command)` | `ReferenceComparisonCommand` | `ReferenceViewResult` | Supports one or multiple reference paths and report discovery |
| `search_knowledge(query)` | `KnowledgeQuery` | `KnowledgeSearchResult` | Calls the old RAG facade only after UI capability gating |
| `load_report(descriptor)` | `ReportDescriptor` | `ReportPreview` | UTF-8 preview, 2 MiB limit, JSON formatting |
| `export_report(command)` | `ReportExportCommand` | `ReportExportResult` | Format validation and atomic copy/replace |

All calls are synchronous. Controllers wrap them in `WorkerTask`; the adapter
has no async methods or lifecycle. Exceptions cross only to the worker's error
mapper, which produces `UiError`.

The frozen operation model declares queued/validating/running/cancelling and
terminal states, optional progress, and cancellation. Actual workers emit only
running and terminal signals, never progress, and bind with
`cancellable=False`. `PresentationStore.request_cancellation()` changes state
only when an operation was declared cancellable; it is not connected to
QThreadPool interruption. Frozen cancellation is therefore intentionally not a
backend promise.

Export is adapter-owned file I/O. Backend lifecycle is per-call service
construction, except injected test factories. Shutdown waits for all Qt workers.

## 3. Current V2 application architecture

### Canonical surfaces

| Surface | Current API and truth |
| --- | --- |
| Rich application facade | `phasenox.application.phasenox_service.PhasenoxService.analyze(AnalysisRequest) -> AnalysisResponse` |
| V2 operation facade | `PhasenoxV2Service.execute(ApplicationRequest) -> ApplicationResult` |
| V2 operations | `ANALYZE`, `REFERENCE_COMPARE`, `MIX_EVALUATE`, `REASON`, `CAPABILITY_INSPECT` |
| V2 result | JSON-safe status, payload, stage outcomes, bounded errors and limitations |
| Scheduler | `JobScheduler.start/submit/get_status/list_jobs/wait/cancel/pause/resume/shutdown` |
| Job contracts | `JobRequest`, `JobSnapshot`, `JobProgress`, `JobCapability`, `JobResult`, `JobError`, `ResourceSnapshot` |
| Capabilities | 48 registry entries with lifecycle, dependency list, freeze-test flag and optional reason |
| Reports | `PhasenoxReport`, atomic `ReportExporter`, reference JSON/Markdown builders |
| Config | immutable `AppConfig` loaded from three package YAML resources |
| Root | `PHASENOX_ROOT > NOISYNE_ROOT > SOUNDBRAIN_ROOT > discovery` |
| Branding | `phasenox.resources.branding`, 14 logical assets and Qt-independent byte/materialization APIs |
| Persistence | frozen collection/engine/serialized identities plus separate migration-safety tooling; no Desktop-facing storage facade |

### Surface mismatch

`PhasenoxService` still supplies the complete existing Desktop result: audio and
DSP analysis, context, engineering score/issues, report, optional multiple
references, RAG/reasoning, mix intelligence and plugin intelligence.

`PhasenoxV2Service.ANALYZE` currently supplies audio metadata, auditory summary
and perceptual descriptors. It does not supply the frozen Desktop score,
engineering issues, complete report, optional reference result, mix/plugin
result or report descriptor. `REFERENCE_COMPARE` accepts one reference plus an
explicit `ReferenceTrackIdentity` and returns objective transport evidence; it
is not the same multi-reference comparison DTO used by the frozen screen.
`MIX_EVALUATE` and `REASON` require caller-supplied policy and evidence.

This is deliberate V2 contract evolution, not a bug. The Desktop adapter must
not pretend the two result shapes are equivalent.

## 4. Contract gap matrix

Categories: A = adapter-only, B = presentation/UI adjustment, C = backend
contract missing, D = already compatible.

| Desktop requirement | Frozen contract | V2 available contract | Category / gap | Required adapter/UI change | Backend change required? | Risk |
| --- | --- | --- | --- | --- | --- | --- |
| Product metadata | `ProductMetadata` with old display/distribution fields | R8 constants plus `phasenox` metadata | A | Construct canonical metadata from branding API and distribution version | No | Low |
| Capability truth | lifecycle plus coarse availability | lifecycle, freeze flag and importability snapshot | B | Preserve lifecycle separately; add readiness source/freeze flag; never equate importable with Ready | Helpful for real probes | High if overstated |
| Runtime status | paths plus unknown device/provider/models | config/runtime modules but no aggregate public status | A/C | Rebuild lightweight snapshot; keep readiness unknown | Yes for authoritative provider/model/device readiness | Medium |
| Settings | read-only flattened snapshot | immutable `AppConfig` | A | Flatten canonical config; redact credential; all values read-only | No for 17B; yes for future editing | Low |
| Rich analysis | `AnalysisViewResult` from full facade | rich `PhasenoxService`; narrow V2 `ANALYZE` | D for canonical rich facade; C for V2 parity | Use canonical rich facade transitionally and label execution boundary | Yes before scheduler-only migration | High |
| Multi-reference workflow | multiple files and rich scores/findings | rich `PhasenoxService`; V2 accepts one identified reference | D/A transitionally; C for V2 parity | Keep canonical facade mapping; do not silently collapse references | Yes before V2-only path | High |
| Mix/plugin intelligence | rich UI items from optional analysis | rich facade plus V2 policy/evidence operations | A | Translate canonical results; V2 policy operations may become separate expert flow later | No for existing workflow | Medium |
| Grounded V2 reasoning | one free-form UI string | structured facts/statements/confidence/limitations | B | Replace string-only presentation contract with structured, provenance-aware items | No | Medium |
| Knowledge search | RAG facade result | no canonical Sprint 15 knowledge-search operation; known RAG blockers | C | Disable surface unless an explicit readiness probe and safe facade are supplied | Yes | High |
| Report preview/export | UI-owned validated file copy | existing atomic exporters | D/A | Retain UI DTO and adapter-owned preview/copy; canonicalize imports | No | Low |
| Job lifecycle | single active presentation operation | multi-job scheduler snapshots/history | B | Add Qt-free Desktop job DTO/store and map scheduler snapshots | No | Medium |
| Job events | Qt worker signals | scheduler polling only | A/C | Poll cheap snapshots with `QTimer`; do not expose backend types | Subscription API desirable, not required | Medium |
| Progress | optional fraction/stage | truthful stage lists; fraction normally `None`; service stages appear only at terminal write | B/C | Show indeterminate/stage state; never synthesize percent | Yes for incremental stage progress | High if faked |
| Cancellation | frozen workers noncancellable | queued immediate; running cooperative before/after service call | B | Enable only from snapshot capability; retain noncancellable state for QThread workers | No | Medium |
| Pause/resume | presentation enum only | queued pause/resume; running pause unsupported | B | Show controls only for `QUEUE_ONLY`; never offer running pause | No | Low |
| Task capacity | none | max workers is private; active/history list public | C | Do not display capacity number in 17B | Yes | Low |
| Resource telemetry | none | start/end optional CPU/RAM/GPU snapshot | B/C | Label as sampled snapshot, not live meter | Yes for live telemetry | Medium |
| Shutdown | QThreadPool waits until done | scheduler cancels queued, lets running finish; no deadline/readiness callback | C | Coordinated closing UI; no claim of immediate cancellation | Yes for deterministic bounded close | High |
| Error model | typed `UiError` with recovery/usability | bounded application/job error code/message/stage | A | Map codes to safe messages; log technical context; never show raw backend message | Taxonomy cleanup helpful | Medium |
| Session state | `session-v1.json` and UI DTOs | no Desktop session contract | B | Version adapter/UI schema deliberately; avoid backend model serialization | No | Medium |
| Desktop writable root | Qt user root sets old env in frozen bundle | canonical root env and installed-package fallback | A/C | Set `PHASENOX_ROOT` only for packaged runtime; keep backend layout unchanged | Storage/app-ID policy decision required | High |
| Desktop launcher | old desktop console entry | only `phasenox` CLI frozen today | C | Choose an explicit GUI launcher without reviving old CLIs | Packaging/freeze contract update required | Medium |
| Installer | old PyInstaller spec | no current Desktop spec/extras | C | Rebuild later against canonical package/resources | Yes, targeted packaging work | High |

## 5. Adapter migration design

Create `phasenox.ui.adapters.v2.V2ApplicationAdapter`; do not rename the frozen
class in place and do not retain `V1ApplicationAdapter` as the canonical
implementation.

Recommended composition:

1. `PhasenoxService` for the existing rich Analyze and References workflows.
   This is canonical, not a legacy alias, and preserves the tested user contract.
2. `PhasenoxV2Service` for V2-native application requests and capability
   inspection.
3. `JobScheduler` for V2-native asynchronous jobs.
4. Adapter-owned Qt-free translation to Desktop DTOs.
5. Adapter-owned report preview/export file operations.
6. Canonical config and branding APIs for metadata/status/settings.

Keep `DesktopApplicationAdapter` for synchronous queries and rich transitional
workflows. Add a separate `DesktopJobGateway` protocol rather than bloating the
adapter:

- `start()` / `shutdown()`;
- `submit(request) -> DesktopJobHandle`;
- `job_snapshot(job_id) -> DesktopJobSnapshot | None`;
- `list_jobs(include_history=False)`;
- `cancel_job(job_id)`;
- `pause_job(job_id)` / `resume_job(job_id)`.

`DesktopJobSnapshot` must copy only presentation-safe fields. `ApplicationResult`,
`JobSnapshot`, `PhasenoxReport`, audio/domain objects, perception contracts and
runtime registry objects must never leak into Qt or presentation.

## 6. Scheduler/job integration design

### Recommendation: C — hybrid

- Continue `QThreadPool` wrapping for synchronous rich `PhasenoxService`, report
  preview/export, settings and any file-only operation.
- Consume `JobScheduler` directly for operations represented honestly by
  `ApplicationRequest`.
- Poll `get_status/list_jobs` from a short Qt timer or a dedicated bridge; never
  wrap a scheduler job in another long-running QThread task.
- Translate snapshots at the adapter boundary and publish them to a multi-job
  presentation store.

### Current scheduler truth

| Concern | Truth |
| --- | --- |
| Submit | Requires started scheduler and validated `ApplicationRequest`; immediately returns job ID |
| States | queued, paused, running, cancelling, completed, failed, cancelled |
| Progress | `execute` while running; final service stages only after execution; no trustworthy percentage |
| Cancellation | immediate before start; cooperative checkpoint before/after the monolithic service call |
| Pause/resume | queued jobs only; running pause explicitly unsupported |
| History | bounded, in memory, terminal jobs retained; not durable |
| Resources | optional CPU/RAM/GPU snapshots at run/finish, not continuous |
| Concurrency | profile-derived internally; no public capacity/status DTO |
| Thread safety | registry and scheduler operations are lock-protected and tested for isolation/races |
| Shutdown | rejects new jobs, cancels queued/paused, running calls finish; waiting may block |

Sprint 17B must show indeterminate execution for monolithic calls, disable pause
while running, and describe running cancellation as requested/cooperative—not
instantaneous.

## 7. Capability truth mapping

The current-machine Sprint 15 probe reported 45 importable, three unavailable
and zero unknown dependencies. This is only package importability; it is not
model, endpoint, corpus, hardware, calibration or production-readiness proof.
The UI decision below combines lifecycle, freeze evidence and explicit reasons.

| Capability | Lifecycle | Machine probe | Desktop disposition |
| --- | --- | --- | --- |
| audio_context | production/tested | available | Expose through Analysis |
| audio_intelligence | planned | available | Hide; lifecycle overrides empty dependency list |
| audio_loading | production/tested | available | Expose |
| auditory_frontend | implemented/not freeze-tested | available | Diagnostics/evidence only |
| brightness_correlate | implemented/not freeze-tested | available | Diagnostics/evidence only |
| clap_embedding | verified/tested | unavailable | Show disabled optional Semantic control with model/dependency reason |
| context_policy_binding | implemented/not freeze-tested | available | Internal/expert contract; hide |
| daw_integration | planned | available | Hide |
| deterministic_reasoning | implemented/not freeze-tested | available | Expose only as bounded V2 intelligence when a valid policy/evidence request exists |
| dsp_analysis | production/tested | available | Expose |
| engine_registry | production/tested | available | Internal diagnostics only |
| engineering_analysis | production/tested | available | Expose in Analysis/Intelligence |
| frequency_masking_foundation | implemented/not freeze-tested | available | Internal evidence; no top-level feature |
| grounded_reasoning_validation | implemented/not freeze-tested | available | Internal validation badge/data only |
| knowledge_memory_foundation | implemented/not freeze-tested | available | Hide; contract foundation is not a user store |
| knowledge_retrieval_contract | implemented/not freeze-tested | available | Hide until an executable service/readiness boundary exists |
| llm_reasoning | implemented/tested | unavailable | Disabled; no bundled model/provider readiness |
| loudness_foundation | implemented/not freeze-tested | available | Internal evidence only |
| memory_learning | planned | available | Hide |
| mix_intelligence | production/tested | available | Expose after successful rich analysis |
| mix_policy_evaluation | implemented/not freeze-tested | available | Expert/internal until policy authoring contract exists |
| model_cache | production/not freeze-tested | available | Runtime diagnostics only |
| model_loading | production/not freeze-tested | available | Runtime diagnostics only; do not claim models loaded |
| onnx_runtime_optimization | implemented/not freeze-tested | available (`onnxruntime 1.19.2`) | Hide; only fixture optimization exists |
| orchestration | implemented/not freeze-tested | available | Hide; no Desktop application boundary |
| perceptual_context_foundation | implemented/not freeze-tested | available | Internal evidence only |
| perceptual_descriptors_foundation | implemented/not freeze-tested | available | Internal evidence only |
| perceptual_mix_intelligence_foundation | implemented/not freeze-tested | available | Internal structured result only |
| perceptual_reasoning_foundation | implemented/not freeze-tested | available | Internal structured result only |
| perceptual_reference_foundation | implemented/not freeze-tested | available | Internal evidence only |
| performance_benchmark_foundation | implemented/not freeze-tested | available | Developer diagnostics only |
| personalization_foundation | implemented/not freeze-tested | available | Hide; no user persistence/editing contract |
| playback_linear_transfer | implemented/not freeze-tested | available | Hide; requires explicit supplied transfer |
| playback_profile_foundation | implemented/not freeze-tested | available | Hide; no profile-management UI contract |
| plugin_intelligence | production/tested | available | Expose read-only recommendations; never imply plugin execution |
| policy_conditioned_translation_risk | implemented/not freeze-tested | available | Internal/expert evidence only |
| rag_retrieval | implemented/tested | unavailable | Disable Knowledge with explicit preflight reason |
| reference_comparison | production/tested | available | Expose rich canonical workflow |
| reference_embedding_contract | implemented/not freeze-tested | available | Internal evidence; no live provider implied |
| reference_objective_comparison | implemented/not freeze-tested | available | May appear inside V2 reference evidence, not as separate page |
| report_generation | production/tested | available | Expose Reports/export |
| repository | production/not freeze-tested | available | Runtime diagnostics only |
| runtime | production/not freeze-tested | available | Show runtime as unknown/degraded until probed |
| runtime_selection_foundation | implemented/not freeze-tested | available | Internal policy result only |
| sentence_transformers_backend | production/not freeze-tested | available | Package presence only; no Ready state |
| service_facade | production/tested | available | Expose through adapter |
| transformers_backend | production/not freeze-tested | available | Package presence only; no Ready state |
| translation_evidence_foundation | implemented/not freeze-tested | available | Internal evidence only |

Required UI rule: planned is always hidden/disabled; unavailable is disabled;
implemented plus importable is not automatically user-visible; production or
verified still needs current-machine assets/provider readiness for optional
features.

## 8. Settings/config mapping

### Truthfully readable now

- provider/model/base URL and generation parameters;
- requested runtime device/dtype/lazy loading;
- resolved model root/model cache/cache/log/report paths;
- configured CLAP, Qwen, reranker and text-embedding identities;
- audio sample rate, CLAP target rate, duration and transform parameters;
- embedding identity/device;
- Chroma path and frozen collection identity;
- logging level/format;
- active application root and configuration source.

Every value must remain read-only in Sprint 17B. There is no validated settings
write/persistence/reload API. Do not infer restart behavior for an operation the
application cannot perform. If future editing is added, root, runtime/device,
model/provider and storage changes should be treated as restart-required until
proved otherwise.

Never return `llm.api_key`. `credential_configured` should distinguish a real
configured credential from packaged placeholder/local-provider sentinel values;
the frozen `bool(api_key)` rule is insufficient. Base URLs may be displayed but
must not be logged with query credentials.

`PHASENOX_ROOT` is the canonical process contract, not a normal Settings text
field. Legacy root names remain backend fallbacks and should not appear as
editable product identity.

## 9. Brand/product integration

| Desktop surface | Sprint 17B mapping |
| --- | --- |
| Window/title/display | `DISPLAY_NAME` (`PHASENØX`) |
| ASCII metadata | `ASCII_NAME` (`PHASENOX`) |
| Wordmark rhythm | `WORDMARK_RHYTHM` (`PHASE   NØX`) where a textual fallback is needed |
| Installed version | `importlib.metadata.version("phasenox")` |
| Qt app icon | `BrandAssetName.APP_ICON_256` (or size-appropriate icon assets) via bytes/materialization |
| Sidebar lockup | primary light/dark logo or wordmark selected by theme |
| Splash | Asset exists, but frozen bootstrap has no splash lifecycle; defer rather than add layout behavior |
| About/product metadata | canonical display/ASCII/version; repository may remain `N0ises/NOISYNE` |
| PyInstaller icon | generate an `.ico` at build time from approved packaged PNG source; no root concept art |

Do not copy the five frozen `brain.ui.resources/brand/noisyne` assets. Replace
`brand_resources.py` with a small Qt bridge over
`phasenox.resources.branding`; the branding package remains Qt-independent.

The Desktop application ID/user-data directory requires an explicit decision.
Changing frozen `soundbrain.desktop` to `phasenox.desktop` changes Qt's
`AppLocalDataLocation`. Sprint 17B must either retain the hidden compatibility
ID temporarily or approve a separate Desktop state-location transition. It must
not silently split or relocate user state during UI integration.

## 10. Navigation and feature visibility

| Surface | Real backing | Sprint 17B decision |
| --- | --- | --- |
| Overview | session, runtime and recent-result presentation | Show |
| Analysis | canonical rich service; optional subfeatures capability-gated | Show; deterministic baseline enabled |
| Reference | canonical rich service and report builders | Show |
| Intelligence | retained analysis/reference plus structured V2 contracts | Show; section-level gating and provenance |
| Knowledge | legacy RAG facade only; current probe unavailable and known correctness blockers | Disable with reason, or hide if no preflight is implemented |
| Memory | foundations only; no user-facing persistence/learning service | Hide; no new page |
| Voice | presentation contracts only; no provider | Remove from available navigation or visibly disable; no controls implying capture |
| Agent | permission/plan presentation only; no executor/application boundary | Hide; no autonomous action claims |
| Plugins | real read-only recommendation data after rich analysis; no execution | Keep as Intelligence section, not standalone functional tool |
| Reports | real preview/export files | Show |
| Settings | effective read-only config/runtime | Show read-only |
| Runtime/Status | partial snapshot only | Keep global/Settings surface; use Unknown/Unavailable truthfully |

## 11. Recommended Intelligence contract

Retain a Qt-free `IntelligenceSnapshot`, but evolve it from loosely formatted
strings toward explicit presentation records:

- stable item/issue/statement ID;
- section and source operation;
- observation/finding/recommendation separated;
- severity/category where defined;
- confidence value plus confidence meaning/source;
- evidence items with value, unit, source contract and identity;
- reasoning grounding state, fact references and validation state;
- assumptions, limitations and warnings;
- optional proposed action clearly labelled as a recommendation, never executed.

Actual user-facing intelligence now includes deterministic engineering issues,
mix root causes/priorities/chain, read-only plugin suggestions, reference
findings/evidence and grounded reasoning statements. Method metadata, digests,
provider IDs, raw arrays and complete validation fixtures belong in expandable
technical details or diagnostics, not the primary UI. Free-form chain-of-thought
must never be requested or shown.

## 12. Task Center feasibility

### Available now

- active jobs and bounded terminal history;
- job/request/operation/profile/device IDs;
- queued, paused, running, cancelling and terminal states;
- created/started/finished timestamps;
- truthful stage lists at current/final snapshots;
- queued cancellation and queue-only pause/resume;
- cooperative running cancellation request;
- terminal payload/error code/stage;
- optional start/end CPU, RAM, GPU name and VRAM snapshots.

### Requires backend work

- public scheduler capacity, queue position and occupied-slot snapshot;
- subscription/event stream or version counter to avoid polling;
- incremental application stage publication during execution;
- continuous resource sampling if live meters are desired;
- durable history across restarts, retry/clone and history clearing;
- bounded asynchronous shutdown/readiness contract;
- richer mapping from application partial results into job errors/limitations.

### Not supported

- pause/resume of a running service call;
- hard interruption of an in-flight Python/native/model call;
- a trustworthy percent-complete value for monolithic calls;
- live CPU/RAM/GPU/VRAM telemetry;
- persisted job history;
- claiming a cancellation request has already stopped work.

Sprint 17B Task Center should show state/stage/time and only controls authorized
by `JobCapability`. Resource values must be labelled snapshots. Unsupported
fields are omitted, not zero-filled.

## 13. Error and exception mapping

Preserve the frozen `UiError` boundary. Map backend codes, never exception text:

| Backend condition | UI category | User treatment |
| --- | --- | --- |
| invalid request / bad path | validation | Correct input, choose another file/path |
| capability/dependency unavailable | capability or provider/model | Disabled feature, runtime/settings recovery link |
| audio decode/analysis/reference failure | validation or internal according to code | Safe operation-specific message; retain prior usable result |
| reasoning failure/partial | provider/model | Preserve deterministic/mix result as partially usable |
| job cancelled | cancelled | State requested/confirmed cancellation accurately |
| timeout | timeout | Retry only when operation is idempotent |
| report/file permission/format | report export | Choose path/format; preserve source result |
| session/persistence failure | persistence | Warn that session was not saved; do not imply backend-store corruption |
| scheduler/internal failure | internal | Generic message, operation ID, technical log only |

`ApplicationResult` usually returns failures instead of raising, so the adapter
must inspect status/errors/limitations and translate them. Raw messages may
contain exception text and must not be placed directly in user labels.
`ExceptionBoundary` remains the last-resort process hook, not normal control
flow.

## 14. DTO/presentation migration

### Retain with canonical defaults

Product metadata, UI errors/recovery actions, report descriptors/preview/export,
analysis/reference command DTOs, reference display DTOs, settings/path/provider
snapshots, session/recent-item state, notifications and navigation state.

### Extend

- `CapabilitySnapshot`: add freeze/test evidence and readiness source; retain
  lifecycle and availability separately.
- `RuntimeStatus`: add only probed scheduler/runtime facts; never default to
  Ready.
- `IntelligenceItem`: add IDs, provenance, units, grounding/validation,
  assumptions and limitations.
- operation presentation: support multiple job summaries instead of only one
  active operation.
- new `DesktopJobHandle`, `DesktopJobSnapshot`, `DesktopJobProgress`,
  `DesktopResourceSnapshot` and scheduler-status DTOs.

### Replace

- `V1ApplicationAdapter` with `V2ApplicationAdapter`;
- old product identity/resource bridge;
- old package/version lookup;
- old packaged-runtime root environment variable;
- old PyInstaller metadata/spec expectations.

### Never leak across the adapter

Qt and presentation must not import `ApplicationResult`, `StageOutcome`,
`JobSnapshot`, `PhasenoxReport`, `AnalysisResponse`, `AudioData`, reference
domain models, perception contracts, config dataclasses, registries, Chroma
clients, model runtime objects, Torch tensors or provider clients.

Required direction remains:

`Qt -> Presentation -> UI contracts -> Application adapter/job gateway -> Backend`

## 15. Packaging/runtime implications

Current V2 has no PySide6 extra, Desktop entry point or PyInstaller spec.
`pyproject.toml` exposes only `phasenox` and its core dependency list remains
heavy. Frozen packaging targets old package/resource/metadata names and must not
be reused unchanged.

Sprint 17B developer/runtime requirements:

- introduce a deliberate `desktop`/`desktop-test` optional dependency group for
  PySide6 and pytest-qt;
- decide whether a new GUI launcher such as `phasenox-desktop` is allowed by the
  R7 CLI freeze, or use `python -m phasenox.ui` until packaging scope approves
  it;
- package `phasenox.ui` and use existing branding/config resource packages;
- keep imports lazy so opening the shell does not load Torch, Transformers,
  ONNX, model clients or Chroma;
- set only canonical `PHASENOX_ROOT` for packaged writable runtime when the
  Desktop path policy is explicitly selected;
- keep session/logs in a writable Qt user location and backend models/cache/data
  outside a read-only bundle;
- do not bundle models or trigger downloads at startup.

Sprint 19 packaging blockers:

- rewrite the spec, asset/version generator, verifier and build script for
  `phasenox` and R8 assets;
- choose CPU/GPU/ONNX profiles deliberately;
- audit mandatory heavy dependencies versus excludes;
- generate and verify Windows icon/version resources;
- settle application ID/user-data continuity;
- test clean-machine install, relocation, update/removal, signing and installer
  lifecycle.

## 16. Test migration plan

### Reusable architecture tests after namespace-only import updates

`test_agent_contracts.py`, `test_agent_permission_ui.py`,
`test_analyze_page.py`, `test_analyze_state.py`, `test_design_components.py`,
`test_design_resize.py`, `test_design_semantics.py`, `test_design_tokens.py`,
`test_intelligence_page.py`, `test_knowledge_state.py`,
`test_presentation_state.py`, `test_reference_page.py`,
`test_reference_results.py`, `test_reference_state.py`,
`test_session_persistence.py`, `test_session_state.py`, `test_state.py`,
`test_voice_contracts.py`, `test_voice_page.py` and the synchronous
`test_workers.py` cases.

Voice/Agent component tests prove safe presentation contracts only; they must
not make those capabilities visible.

### Adapter fixture/result updates required

`e2e/conftest.py`, `e2e/test_desktop_workflows.py`, `test_app.py`,
`test_analysis_results.py`, `test_analysis_workflow.py`, `test_dashboard.py`,
`test_error_resilience.py`, `test_intelligence_adapter.py`,
`test_knowledge_adapter.py`, `test_knowledge_workflow.py`,
`test_operations.py`, `test_performance_responsiveness.py`,
`test_reference_adapter.py`, `test_reference_workflow.py`,
`test_report_adapter.py`, `test_reports_workflow.py`,
`test_settings_adapter.py`, `test_settings_workflow.py`,
`test_worker_binding.py` and `test_shell.py`.

### Canonical identity/packaging expectations required

`test_brand_integration.py`, `test_branding.py`,
`test_packaging_release.py`, plus identity assertions in `test_app.py`,
`test_shell.py`, settings tests and the E2E workflow.

### Replace/retire

- Replace `test_v1_adapter.py` with `test_v2_desktop_adapter.py` while retaining
  equivalent rich-workflow regression coverage.
- Rewrite old brand-resource tests against `phasenox.resources.branding`.
- Defer frozen executable-size/file-count and old spec tests to the new packaging
  sprint; do not weaken them into meaningless assertions.
- Split worker tests into synchronous noncancellable operations and
  scheduler-backed cancellable/queue-pausable jobs.

### New Sprint 17B tests

- shell start/close and headless/offscreen Qt smoke;
- adapter construction imports no heavy backend/Qt dependencies prematurely;
- canonical display/ASCII/version/icon/wordmark metadata;
- 48-capability lifecycle/readiness mapping with no fake Ready states;
- settings flattening and credential redaction;
- canonical rich analysis/reference translation;
- V2 job queued/running/terminal mapping and bounded history;
- queued cancellation, cooperative running cancellation and queue-only pause;
- close/shutdown behavior with queued and running jobs;
- backend application/job error to safe `UiError` mapping;
- disabled Knowledge/Voice/Agent and conditional Semantic/Reasoning states;
- Task Center omission of unsupported percentage/live telemetry;
- dependency rule proving Qt/presentation do not import deep backend modules;
- session compatibility/schema handling;
- package-resource use from an unrelated CWD.

## 17. Git integration strategy

| Option | Assessment |
| --- | --- |
| A. Merge `desktop-ui` | Reject. It would combine 24 Desktop-only and 61 V2-only commits and reintroduce the old canonical backend/package tree, data and identity conflicts. |
| B. Cherry-pick Desktop commits | Reject as the primary method. The 22 UI-affecting commits are incremental and include old backend imports, identity, resources and packaging assumptions; conflict resolution would obscure semantics. |
| C. Manual copy/replay | Recommended foundation. Select only UI architecture/tests, place them under canonical paths, and adapt each boundary deliberately. |
| D. Controlled semantic replay in scoped commits | **Recommended implementation form.** Start a Sprint 17B integration branch from `v2-development`; extract selected frozen files read-only, then apply reviewed patches by layer. |

Recommended commit sequence for 17B:

1. Qt-free contracts, presentation state/store and design system.
2. Shell/pages/controllers with unsupported navigation gated.
3. canonical brand/config/path/error integration.
4. `V2ApplicationAdapter` rich canonical workflow mapping.
5. scheduler gateway and Task Center DTO/state mapping.
6. migrated headless/adapter/compatibility tests.
7. developer desktop extra/launcher only if the R7 freeze is deliberately
   updated; installer work remains later.

Never copy `brain/`, frozen data/manuals, old UI assets, old spec, distribution
metadata, generated reports, or frozen backend code into V2.

## 18. Exact Sprint 17B implementation scope

### Port/replay

- `brain/ui` architecture into `phasenox/ui`, including contracts,
  presentation, shell, design system, supported workflow pages/controllers,
  session/error/logging/path foundations and dormant Voice/Agent presentation
  contracts only where needed to avoid a rewrite.
- All imports become canonical `phasenox.ui`; only adapter modules may import
  application/runtime/config/report backends.
- Port the 47 Desktop tests selectively according to the matrix above.

### Implement

- `phasenox/ui/adapters/v2.py` and a Qt-free `DesktopJobGateway`;
- canonical brand bridge over the R8 API;
- truthful capability/config/runtime mapping;
- hybrid worker/scheduler operation binding;
- multi-job Task Center presentation model using only currently available data;
- safe backend-result/error translation;
- navigation gating and canonical product metadata;
- packaged-runtime canonical root mapping only after the user-data-ID decision.

### Do not implement in 17B

- RAG/persistence redesign or migration;
- writable settings;
- Voice provider, speech pipeline or Agent executor;
- autonomous plugin actions;
- running-job pause, hard cancellation, fake progress/live telemetry;
- model download/bundling;
- final PyInstaller/installer/signing/update work;
- broad UI redesign.

## 19. Risks and blockers

### Blocking for unrestricted feature parity

1. V2 `ANALYZE`/`REFERENCE_COMPARE` do not match rich Desktop results.
2. RAG/Knowledge lacks a production-ready application boundary and truthful
   corpus/provider readiness probe.
3. Scheduler lacks incremental events/progress, public capacity and bounded
   shutdown readiness.
4. Provider/model/device readiness is not represented by capability importability.
5. Desktop application ID/user-data continuity is undecided.
6. Current packaging has no Desktop extras, launcher or canonical spec.

### Manageable in constrained 17B

- retain canonical `PhasenoxService` for rich workflows;
- keep unsupported features hidden/disabled;
- use polling and indeterminate stage presentation;
- keep settings read-only and credentials redacted;
- defer installer and storage-policy changes;
- preserve the adapter boundary so later backend contracts replace composition
  without rewriting Qt.

## Final Go/No-Go

**GO** for Sprint 17B only under the constrained scope above: selective semantic
replay, canonical PHASENOX identity, rich canonical service compatibility,
hybrid scheduler integration, truthful capability gating, and no storage or
installer redesign.

**NO-GO** if Sprint 17B is defined as a direct branch merge, scheduler-only
replacement of the rich UI workflow, enabling Knowledge/Voice/Agent without
real readiness, or claiming unsupported progress/cancellation/telemetry.

No implementation, merge, cherry-pick, rebase, packaging build, test migration,
or Sprint 17B work was performed during this audit.
