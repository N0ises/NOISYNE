# Desktop UI Sprint 19 Performance Record

## Scope and measurement boundary

Sprint 19 measures the NØISYNE desktop shell through the stable
`DesktopApplicationAdapter` seam. It does not optimize or benchmark DSP, RAG, ML,
provider, or V2 internals. The optional local command is:

```powershell
python -m brain.ui.performance_probe --cold-process
```

It uses a deterministic construction-only adapter, imports no V1 backend, writes no
telemetry, and reports JSON. Timings below are observations from the Windows offscreen
runtime, not product performance claims. Regression tests use generous semantic budgets.

## Baseline and final measurements

| Metric | Baseline | Final | Boundary / interpretation |
|---|---:|---:|---|
| Application creation | 18.21 ms | 18.67 ms | Qt/UI only |
| MainWindow construction | 163.89 ms | 145.46 ms | Pages, controllers, initial store render |
| Offscreen-ready after `show()` | 11.98 ms | 10.26 ms | Qt event processing |
| Cold-ish Python/Qt child process | not captured | 891.26 ms | Process + imports + deterministic probe |
| Initial current-page render | not separated | 1.20 ms | Presentation/UI only |
| Mean current-page render | not separated | 1.20 ms | 20 repeated renders |
| Five full navigation cycles | 529.43 ms | about 176.87 ms | Final derived from 35.37 ms/cycle |
| Sixty full navigation cycles | probe did not complete cleanly | 30.51 ms/cycle | 540 navigations, post-change |
| Navigation traced growth | unavailable | 2,180,776 bytes | 60 cycles; 2,206,872-byte traced peak |
| Pages / subscribers | 9 / 1 | 9 / 1 | Stable after stress |

The demonstrated bottleneck was render work for all nine persistent pages on every state
publication. Normal shell updates now render only the selected page;
an explicit all-page `render()` remains available for synchronization tests. Five-cycle
navigation time improved by about 67% on the observed runs. Brand assets are loaded during
application/window construction, not in ordinary presentation render loops, so no resource
cache change was justified.

## Operation and responsiveness measurements

A controlled 25 ms analysis adapter call measured 34.94 ms from command issue to visible
terminal publication: 5.77 ms scheduling delay, 25.38 ms adapter duration, and 9.02 ms
combined command/presentation/UI overhead. A controlled JSON report adapter measured
19.11 ms user-visible: 11.20 ms adapter/file work and 7.84 ms UI/scheduling overhead.
Separately, a 30-byte local JSON preview through the real `V1ApplicationAdapter` measured
17.30 ms user-visible end to end. These figures do not claim backend analysis speed.

The deterministic slow-analysis test uses a worker gate and repeating Qt timer. At least
three GUI callbacks fire while the adapter is blocked, queued/loading state is published
before completion, indeterminate progress is visible while active, the result is rendered,
and the worker registry returns to zero. Analysis, reference comparison, Knowledge search,
and report preview adapter calls execute away from the GUI thread; state publication and UI
render callbacks execute on the GUI thread.

Desktop V1 analysis/reference/Knowledge/report operations remain non-cancellable once
submitted. The measured unsupported-cancellation truth check returned `false` in 0.003 ms;
no backend preemption is claimed. Agent actions retain their separately declared
before-start/during-execution cancellation contracts.

## Runtime, model, and memory truth

- First model load: **not measurable in the current runtime**. The stable desktop adapter
  has no model-load or model-reload operation, and no model is configured or downloaded.
- Subsequent model reuse/reload: **not implemented/currently not measurable**.
- GPU memory: **not measurable** without an enabled local model/GPU runtime. No CUDA probe
  was added. A requested-CUDA/effective-CPU degraded DTO renders without blocking or repeated
  probing, and unrelated pages remain usable.
- Real backend analysis latency: **not measured** because no representative user audio and
  configured optional model runtime were available. Fake-adapter timing is reported only as
  UI overhead.
- Process RSS: not asserted because Sprint 19 adds no platform-specific dependency. Python
  allocation trends are measured with `tracemalloc`; thresholds detect gross growth rather
  than platform allocator noise.

Stress coverage includes 25 analyses, 25 Knowledge queries, 15 failures, 15 reference
comparisons, 15 report previews, 75 simultaneous references, 60 navigation cycles, and a
50-item bounded transcript containing long text. Active workers return to zero; recent
session lists remain capped at 20; transcript and notification history remain capped at 50.
The leak audit found one unbounded surface: distinct operation failures accumulated active
notifications indefinitely. Active notifications are now capped at 10 while the 50-entry
history remains available. No orphaned workers, subscriber growth, page recreation, repeated
signal connections, or thread-pool accumulation was observed.

## Regression and CI impact

Fast checks are marked `performance`; repetition-heavy checks are also marked `stress`.
Markers are registered. The focused suite adds seconds, not minutes, to the existing UI run.
Budgets are intentionally broad: semantic timer progress, correct thread affinity, startup
and render ceilings, stable object counts, zero active workers, and less than 10 MiB traced
growth. Critical responsiveness tests must pass three consecutive runs before approval.

Final validation on the Sprint 19 worktree:

- critical responsiveness/stress file: 8 passed in each of three consecutive runs
  (24 passed, 0 failed, 0 skipped total);
- full Desktop UI suite: 362 passed, 0 failed, 0 skipped in 43.82 seconds (the pre-change
  baseline was 354 passed in 21.80 seconds);
- Desktop E2E suite separately: 16 passed, 0 failed, 0 skipped;
- stable V1 adapter regressions: 18 passed, 0 failed, 0 skipped;
- relevant frozen V1 analyze/reference service subset: 10 passed, 0 failed, 0 skipped;
- native and offscreen smoke launches: both exited 0;
- Ruff, Black check, compileall, and Git whitespace check: passed.

No backend or V2 file was modified. The CI wall-time impact of executing the marked stress
tests in the normal UI suite was about 22 seconds on this machine, keeping the complete UI
job under one minute.

Sprint 20 packaging, PyInstaller, installer, release directories, runtime bundling, signing,
and clean-machine release validation are explicitly deferred.
