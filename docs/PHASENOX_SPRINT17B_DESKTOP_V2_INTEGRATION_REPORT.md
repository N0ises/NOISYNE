# PHASENOX Sprint 17B Desktop V2 Integration Report

## Outcome

Sprint 17B completed the constrained Desktop integration authorized by the
Sprint 17A audit. The frozen Desktop architecture was replayed semantically into
`phasenox/ui/`; the `desktop-ui` branch was not merged, rebased, cherry-picked,
checked out, or modified.

The delivered boundary remains:

```text
Qt -> Presentation -> UI contracts -> V2ApplicationAdapter / DesktopJobGateway -> Backend
```

No production persistence, RAG storage, engine key, serialized identifier,
environment compatibility name, or canonical CLI contract changed.

## Exact implementation commits

| Commit | Layer |
| --- | --- |
| `a3d07d8ab92444361d675ff53e09662878514499` | Qt-free presentation/contracts/design/session foundation |
| `e157cafc0a1003a52c9c508d284a4a4645104fca` | Shell, pages, feature gating, brand/config/path/error integration |
| `230b26ce35f752afb913f534ef312bd74fa64c18` | Canonical `V2ApplicationAdapter` |
| `74dd1af7531ad9246537f82eb13491ce0bc815b8` | Scheduler gateway and constrained Task Center |
| `5c0bc55f2a02298d97e4830b2ad38e9307b2a9b9` | Lightweight capability probing |
| `57a34909beb91a2166f3ac115ad56dfeef353c32` | Desktop tests and optional dependency groups |

Commits were intentionally kept scoped and were not squashed.

## Files replayed and adapted

### Application and shell

- `phasenox/ui/__init__.py`, `phasenox/ui/__main__.py`, `phasenox/ui/app.py`
- `phasenox/ui/main_window.py`, `phasenox/ui/pages.py`, `phasenox/ui/dashboard.py`
- `phasenox/ui/shell_surfaces.py`, `phasenox/ui/state.py`
- `phasenox/ui/logging_setup.py`, `phasenox/ui/paths.py`
- `phasenox/ui/packaging_probe.py`, `phasenox/ui/performance_probe.py`

### Qt-free contracts and presentation

- `phasenox/ui/contracts.py`, `phasenox/ui/presentation.py`
- `phasenox/ui/presentation_state.py`, `phasenox/ui/presentation_store.py`
- `phasenox/ui/session_persistence.py`
- `phasenox/ui/errors.py`
- `phasenox/ui/workers.py`, `phasenox/ui/worker_binding.py`
- `phasenox/ui/agent_contracts.py`, `phasenox/ui/voice_contracts.py`

Voice and Agent contracts were retained only as Qt-free session/presentation
compatibility. No provider, capture flow, or executor was integrated, and these
features are absent from active navigation.

### Workflow surfaces

- Analysis: `analysis_controller.py`, `analyze_page.py`, `analyze_state.py`,
  `result_presentation.py`, `result_view.py`
- References: `reference_controller.py`, `reference_page.py`,
  `reference_result_view.py`, `reference_state.py`
- Intelligence: `intelligence_page.py`, `intelligence_presentation.py`
- Knowledge: `knowledge_controller.py`, `knowledge_page.py`, `knowledge_state.py`
- Reports: `report_controller.py`, `reports_page.py`
- Settings: `settings_controller.py`, `settings_page.py`

### Design system

- `phasenox/ui/design_system/__init__.py`
- `components.py`, `gallery.py`, `semantics.py`, `theme.py`, `tokens.py`

### New V2 integration boundaries

- `phasenox/ui/adapters/__init__.py`
- `phasenox/ui/adapters/v2.py`
- `phasenox/ui/job_gateway.py`
- `phasenox/ui/task_center.py`
- `phasenox/ui/task_center_surface.py`

### Packaging metadata and tests

- `pyproject.toml`
- `tests/ui/conftest.py`
- `tests/ui/test_dependency_direction.py`
- `tests/ui/test_design_components.py`
- `tests/ui/test_design_resize.py`
- `tests/ui/test_design_semantics.py`
- `tests/ui/test_design_tokens.py`
- `tests/ui/test_desktop_integration.py`
- `tests/ui/test_error_resilience.py`
- `tests/ui/test_intelligence_adapter.py`
- `tests/ui/test_job_gateway.py`
- `tests/ui/test_operations.py`
- `tests/ui/test_presentation_state.py`
- `tests/ui/test_reference_adapter.py`
- `tests/ui/test_report_adapter.py`
- `tests/ui/test_session_persistence.py`
- `tests/ui/test_session_state.py`
- `tests/ui/test_settings_adapter.py`
- `tests/ui/test_state.py`
- `tests/ui/test_worker_binding.py`
- `tests/ui/test_workers.py`

No frozen `brain/ui` file, old Desktop brand asset, backend implementation, or
PyInstaller specification was copied into the current tree.

## Adapter architecture

`V2ApplicationAdapter` is Qt-free and is the only rich synchronous backend
translation boundary.

- Canonical `PhasenoxService` supplies the existing rich Analyze and
  multi-reference workflows.
- Domain results are copied into Desktop DTOs; domain/report/reference objects
  do not cross into presentation.
- Report preview and export remain adapter-owned, bounded, UTF-8 file operations.
- Settings and runtime snapshots use canonical config APIs.
- Knowledge has no default RAG service construction because package presence is
  not corpus/model readiness. An explicit ready test/application boundary may be
  injected.
- Capability inspection uses package-spec presence rather than importing heavy
  dependencies. Lifecycle, freeze evidence, and readiness source remain separate.

Structured Intelligence DTOs now have statement/source identity, category,
severity, confidence meaning, grounding/validation state, assumptions,
limitations, and warnings. Primary UI output does not expose raw method,
provider, digest, fixture, or array internals.

## Scheduler integration and Task Center

`DesktopJobGateway` is separate from `DesktopApplicationAdapter`. It lazily
constructs `PhasenoxV2Service` plus `JobScheduler`, accepts JSON-safe operation
inputs, and returns only:

- `DesktopJobHandle`
- `DesktopJobSnapshot`
- `DesktopJobProgress`
- `DesktopResourceSnapshot`

The Task Center polls bounded scheduler history with `QTimer`; it does not fake
an event subscription.

Available presentation:

- queued, paused, running, cancelling, completed, failed, cancelled;
- created/start/finish timestamps;
- current and known completed/pending stages;
- bounded in-memory history;
- safe error categories/messages;
- sampled CPU/RAM/GPU/VRAM values only when present;
- queued pause/resume and cancellation according to the current capability;
- cooperative running cancellation labelled as non-instantaneous.

Intentionally absent:

- fabricated percentage, queue position, scheduler capacity;
- live resource meters;
- durable-history claim;
- running pause or hard-cancel claim.

QThreadPool remains responsible for rich synchronous analysis/reference,
settings/runtime, report, and file-only work. Scheduler jobs are not wrapped in
long-running Qt workers.

## Visible, hidden, and disabled feature matrix

| Surface | Sprint 17B state | Basis |
| --- | --- | --- |
| Overview | Visible | Presentation/session/runtime summary |
| Analysis | Visible and enabled | Freeze-tested canonical rich service |
| References | Visible and enabled | Canonical rich multi-reference service |
| Intelligence | Visible and section-gated | Real retained engineering/mix/plugin/reference outputs |
| Reports | Visible and enabled | Bounded preview/export operations |
| Settings | Visible, read-only | Immutable canonical configuration |
| Knowledge | Visible but disabled without readiness | RAG corpus/model readiness is not validated |
| Voice | Hidden from active navigation | No capture/provider pipeline |
| Agent | Hidden | No executor |
| Memory | No page | No approved user-facing contract |
| Plugins | Intelligence recommendations only | No execution surface |
| Runtime | Global and Settings status | No separate navigation page |

Planned capabilities and importable-only optional capabilities are never shown
as Ready.

## Brand integration

The Qt bridge reads only the approved package API in
`phasenox.resources.branding`:

- `DISPLAY_NAME = PHASENØX`
- `ASCII_NAME = PHASENOX`
- `WORDMARK_RHYTHM = PHASE   NØX`
- packaged 256 px application icon;
- approved light/dark master lockups and symbols.

The main window, application display name, icon, sidebar identity, and product
metadata use these resources. Version resolution is
`importlib.metadata.version("phasenox")`. No artwork or splash behavior was
generated.

## Settings behavior

Settings are read-only and include effective provider/model/base URL,
generation values, device/dtype/lazy loading, application/model/cache/log/report
paths, model identities, audio values, embedding identity/device, Chroma path
and collection, and logging values.

API key contents and the key name are not exposed. Empty values and known
sentinels such as the default `lm-studio` value do not count as a configured
credential. There is no write, reload, model download, or storage migration.

## Application identity and user-data continuity

The public product identity is PHASENØX, but the Qt application identifier
remains temporarily `soundbrain.desktop`. This deliberate compatibility choice
preserves the existing `QStandardPaths.AppLocalDataLocation` and therefore
Desktop session/log/cache/report continuity. Changing that identifier and
migrating Desktop state requires a separate approved migration sprint.

Packaged-runtime backend redirection uses canonical `PHASENOX_ROOT`; legacy
root fallback behavior in the backend is untouched. The Desktop session remains
Desktop-owned and uses the existing versioned schema. Invalid/old data fails
safely and no backend models are serialized.

## Dependencies and launcher

`pyproject.toml` now exposes optional `desktop` and `desktop-test` groups for
PySide6 and pytest-qt. The frozen CLI contract remains unchanged: the only
console script is `phasenox`. Developer launch is:

```console
python -m phasenox.ui
```

No installer, final PyInstaller specification, signing, updater, model bundle,
or GUI console entry point was added.

## Validation results

| Validation | Result |
| --- | --- |
| Focused offscreen Desktop suite | 95 passed |
| Identity, branding, application service, rich service, Sprint 16 scheduler | 79 passed |
| Distribution, wheel/sdist identity, fresh install and release alignment | 12 passed |
| Application root, RAG collection/preflight, reasoning/RAG/semantic regressions | 29 passed |
| Direct `python -m phasenox.ui --smoke-test` with offscreen Qt | Passed |
| Real gateway `capability_inspect` scheduler smoke | Passed |
| Heavy-import proof | Torch, Transformers, ONNX Runtime and Chroma absent after Desktop adapter import/capability snapshot |

The first combined pytest run encountered the documented Windows native
PyArrow/pytest-Qt subprocess access violation while starting a subprocess. It
did not report an assertion failure. Suites were rerun in isolated processes
with unrelated third-party pytest plugin autoload disabled; all assertions then
passed as recorded above.

Final quality gates run after this report:

- Ruff on all changed Python files;
- Black `--check` on all changed Python files;
- `compileall phasenox brain tests`;
- `git diff --check`.

## Known limitations and deferred packaging work

- V2 scheduler-native Analyze/Reference result parity is still narrower than
  the rich canonical service, so the hybrid boundary remains necessary.
- Knowledge remains unavailable until a real RAG readiness contract exists.
- Voice and Agent have no provider/executor.
- Settings remain immutable.
- Scheduler progress is stage/indeterminate; cancellation is cooperative;
  resource snapshots are not live; history is not durable.
- Deterministic bounded shutdown of already-running backend calls is not
  provided by Sprint 16.
- Application-ID migration is deferred.
- Final PyInstaller configuration, ICO generation, installer, signing, update
  channel, model packaging, and GPU-provider packaging remain Sprint 19 work.

No RAG redesign, persistence migration, writable settings, data-root redesign,
voice/speech pipeline, Agent executor, plugin execution, model download,
installer work, or broad visual redesign was started.

## Frozen branch confirmation

The local and remote `desktop-ui` refs remained
`e2dd11e4193f32cd4f31cda5bca8cbd322bec3af` throughout Sprint 17B. This work
was implemented exclusively on `v2-development` and was not pushed.
