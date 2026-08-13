# NØISYNE Desktop V1 Release Candidate

## Candidate boundary

This record freezes the Desktop V1 release-candidate review performed on `desktop-ui`,
starting from approved Sprint 20 HEAD
`d45ea27aeb1a2ae61c09f4855bbd3d7908ac7cc4`. The RC commit is the commit containing
this record. No release, tag, installer publication, signing, or V2 integration is part of
Sprint 21.

The public product identity is **NØISYNE** (`NOISYNE` where ASCII is required), version
1.0.0. The technical `SoundBrain`/`soundbrain`, `brain`, repository, CLI, and application ID
remain unchanged. Qt presentation continues to depend on stable Desktop contracts and the
`DesktopApplicationAdapter`; the V1 backend remains behind `V1ApplicationAdapter`.

## Completed Desktop surface

The eight primary workspaces are Overview, Analyze, References, Intelligence,
Voice / Agent, Knowledge, Reports, and Settings. Runtime status is a global top-bar concern
with its completed detail surface in Settings; the obsolete Runtime placeholder is no
longer exposed in navigation. Native visual review covered every workspace at effective
100% and 125% scaling, keyboard navigation, analysis/reference result detail, window
resizing, scroll behavior, branding, and truthful empty/unavailable states. No clipping or
unintended horizontal scrolling was found after the Overview card-height correction.

The supported GUI workflow was exercised through real page controls, controllers, and the
V1 adapter: launch, inspect runtime/capability truth, choose and analyze supported audio,
review the result, choose and compare a reference, retain Intelligence output, preview and
export the selected report in its declared format, close, and reopen the coherent session.
The fixture analysis completed `ok` with score 95 and a 2,830-byte JSON report; comparison
against the same fixture completed `ok` with similarity 100 and produced JSON and Markdown
reports. The reopened schema-2 session retained valid selected paths, the last result, and
recent reports. Knowledge execution was correctly withheld because RAG availability was
`unknown`, not `available`.

**Definition of Done: yes.** A user can perform the complete supported V1 Desktop workflow
without the CLI: launch, inspect status, select/configure/analyze audio, inspect results,
select/compare references, inspect Intelligence, preview/export reports, close, and reopen
the coherent session. Knowledge participates only when its capability is actually
available; unavailable Voice and Agent execution are not supported V1 workflow steps.

Runtime, capabilities, settings, operations, errors, and report formats remain DTO-driven.
Current-machine availability is not inferred from implementation status. Planned or absent
capabilities remain disabled with a reason. Settings expose 32 packaged-default fields as
read-only. Desktop analysis, comparison, Knowledge, and report operations execute off the
GUI thread; progress, non-cancellability, failures, recovery actions, bounded histories,
and session persistence remain explicit. Voice has no real provider and Agent has no real
executor in V1, so both present truthful safe states and cannot imply execution.

## Responsiveness and regression evidence

Observed source-shell measurements on this Windows host were 18.845 ms for application
creation, 152.466 ms for `MainWindow` construction, 11.187 ms to offscreen ready,
1.335 ms mean selected-page render, 36.874 ms for one eight-page navigation cycle, and
937.161 ms for a cold probe process. Navigation tracing grew 366,080 Python bytes with a
382,644-byte peak; page count remained eight and subscriber count one. Native and offscreen
smoke launches exited 0. These observations are guardrail evidence, not backend performance
claims.

Final source checks:

- full Desktop UI suite: 370 passed;
- Desktop E2E: 16 passed;
- stable V1 adapter regressions: 18 passed;
- packaging tests: 6 passed;
- responsiveness/performance: 8 passed;
- architecture boundary: 5 passed;
- persistence/resilience: 38 passed;
- branding: 9 passed;
- Voice / Agent safety: 94 passed;
- focused frozen V1 audio/service/reference regression: 11 passed;
- native and offscreen source smoke launches: passed.

The complete repository suite was not repeated. It takes about 35 minutes in this
environment and prior broad invocations have a known native RAG/PyArrow termination. The
accepted focused frozen-V1 subset covers deterministic audio review/export, service
analysis and missing-audio behavior, the Torch import guard, single/multiple references,
and graceful reference failure. No backend, native-runtime, dependency declaration, or V2
file changed in this candidate.

## Packaged candidate

The final artifact is `dist/NOISYNE/NOISYNE.exe`: version 1.0.0, Windows x64, `cpu`
one-folder profile, 5,591 files, and 891,550,542 bytes. It embeds NØISYNE metadata, icon,
Qt `qwindows.dll`, SVG/image plugins, five approved brand assets, packaged runtime YAML,
and installed distribution metadata. The verifier found no source, credentials, `.env`,
workspace data/models, unrelated assets, or development payload.

The bundle uses Torch 2.13.0+cpu and Torchaudio 2.11.0+cpu; CUDA is unavailable by design.
From a relocated path containing spaces, with an unrelated working directory and no
development `PYTHONPATH` or active virtual environment, the frozen executable loaded Qt,
NumPy, SciPy, SoundFile, librosa, Torch, Torchaudio, and Transformers, then completed the
supported audio analysis `ok` with score 95 in 45.132 seconds and wrote the expected
2,830-byte report. It performed no model download. Two close/reopen packaged smoke runs
exited 0, and the external session hash remained unchanged. User state resolved outside the
bundle under `%LOCALAPPDATA%/NOISYNE/soundbrain.desktop`.

The PyInstaller warning for missing `tbb12.dll` belongs to Numba's optional TBB pool and is
non-blocking for the demonstrated deterministic path. No installer compiler, Windows
Sandbox, disposable VM, or suitable clean local account was available. Relocation and the
Sprint 20 bundle replacement/removal checks therefore remain the strongest available
installation evidence; they are not a real installer or clean-machine test.

## Release checklist

| Gate | Status | Evidence / limitation |
|---|---|---|
| All V1 screens complete | PASS | Eight completed workspaces; obsolete placeholder hidden |
| Supported V1 workflows integrated | PASS WITH LIMITATION | Analyze, References, Intelligence, Reports, persistence pass; Knowledge requires an actually available RAG capability |
| Backend regression suite | PASS WITH LIMITATION | Accepted 11-test frozen-V1 subset passed; full repository suite not repeated |
| Desktop integration | PASS | Real controls/controllers/V1 adapter workflow and reopen passed |
| Packaging | PASS | Verified CPU-only Windows x64 bundle and real frozen analysis passed |
| Clean install | PASS WITH LIMITATION | Relocation/replacement/removal passed; no installer or true clean-machine environment |
| Error handling | PASS | Structured failure, recovery, and truthful availability paths covered |
| No critical UI freezes | PASS | Worker/thread-affinity, timer responsiveness, smoke, and performance gates passed |
| No UI-domain coupling | PASS | Architecture tests preserve UI contracts and adapter direction |
| Documentation | PASS | This RC record and prior Sprint records describe the tested boundary |
| Brand | PASS | NØISYNE public identity and unchanged technical identity verified |
| Known limitations recorded | PASS | See below |

There are no known failing RC gates. The candidate is ready for review subject to the
explicit limitations below.

## Known limitations and deferred work

- Voice has no production provider, and Agent has no production executor in V1.
- Optional provider/model/RAG capabilities may be `unknown` or unavailable and remain
  disabled until the adapter reports actual availability.
- The normal package is CPU-only. No GPU/CUDA package was produced or validated.
- No signed installer, installer lifecycle, or true clean-machine run was available.
- The package is large, and the optional Numba TBB warning remains.
- Technical names and the stable application ID intentionally remain unchanged.
- ONNX is absent and deferred to V2; no V2 adapter or migration work was performed.
- Troubleshooting remains capability-led: inspect the runtime/availability reason in
  Settings, verify the selected path still exists, and use the offered recovery action.
  Packaged diagnostics remain in the documented external user-data log directory; normal UI
  errors do not expose raw tracebacks.

The next planned phase is explicitly deferred and requires separate approval:

- NOISYNE Technical Rename Preflight;
- controlled SoundBrain → NOISYNE V2 migration;
- V2 backend development;
- ONNX benchmark spike;
- real Voice engine integration;
- Voicebox/local voice benchmark;
- cloud voice providers;
- autonomous Agent/tool execution;
- installer/signing improvements;
- auto-update;
- GPU-specific package.

The package/build mechanics remain documented in
`docs/DESKTOP_UI_SPRINT_20_PACKAGING.md`; performance methodology and guardrails remain in
`docs/DESKTOP_UI_SPRINT_19_PERFORMANCE.md`.
