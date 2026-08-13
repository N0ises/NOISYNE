# NØISYNE Windows Packaging — Sprint 20

## Strategy

The first Windows candidate is a PyInstaller **one-folder** application named
`NOISYNE.exe`. One-folder keeps Qt/native libraries auditable, avoids one-file extraction
startup and antivirus risk, and is suitable for a later installer. Public identity is
NØISYNE/NOISYNE; the technical `soundbrain`, `brain`, repository, CLI, and application ID
remain unchanged.

The normal `cpu` profile requires CPU-only Torch/Torchaudio and refuses a CUDA environment.
The `shell` profile excludes Torch solely for the fast non-release CI packaging gate. GPU is
a separate future distribution. Models are not bundled or downloaded.

## Build

Use Windows, Python 3.12, and a clean venv. Install the project plus
`soundbrain[desktop-package]`; install CPU Torch/Torchaudio from the official CPU wheel
index. Then run:

```powershell
tools/packaging/build_windows.ps1 -Profile cpu
```

This generates icon/version inputs from the approved packaged PNG and `pyproject.toml`,
builds `dist/NOISYNE/`, verifies required Qt/config/brand files and Windows resources,
and creates `dist/NOISYNE-windows-x64-1.0.0.zip`. Generated binaries,
build work, and archives remain ignored and are not committed.

The spec explicitly includes Qt, the Windows platform and SVG/image plugins, packaged YAML,
brand assets, and installed distribution metadata. It excludes dev tools, optional RAG/data
stacks, and known dependency test trees. Source `.py`, PDBs, repository docs, local state,
models, `.env`, credentials, and unrelated workspace `assets/` are not shipped.

## Runtime locations and first run

Read-only resources use `importlib.resources`. The stable application ID remains
`soundbrain.desktop`; desktop user data resolves under
`%LOCALAPPDATA%/NOISYNE/soundbrain.desktop`. Frozen startup sets `SOUNDBRAIN_ROOT` to that
user root before V1 settings load, then idempotently creates state, logs, cache, reports, and
the compatible sibling Models directory. Session data is `state/session-v1.json`; desktop
diagnostics are `logs/desktop.log`. Reports remain user-selected; optional models belong in
the documented user Models directory. Initialization failures fall back to safe stderr
diagnostics and the existing UI resilience paths.

## Local candidate validation

- CPU runtime: Torch 2.13.0+cpu, Torchaudio 2.11.0+cpu, CUDA `None`.
- PyInstaller onedir build: passed; icon and version resources embedded.
- Native packaged `--smoke-test` from an unrelated path containing spaces: exit 0 in 2.26 s.
- Static artifact verification: Qt `qwindows.dll`, SVG plugin, five brand assets, YAML,
  NØISYNE 1.0.0 metadata, icon, and unwanted-file scan passed.
- Distribution size: 891,550,244 bytes across 5,591 files. PowerShell and tar ZIP creation
  were stopped after exceeding practical local build time; no completed archive size exists.
- A real packaged V1 analysis of the 8,629,040-byte `tests/assets/test.wav` fixture completed
  from a relocated bundle in 29.053 s, returned `ok` with score 95.0, and exported a
  2,830-byte JSON report. The command used the bundled runtime only:

  ```powershell
  & 'E:\Build\NOISYNE Sprint20 Validation\Bundle A\NOISYNE.exe' `
    --packaging-probe 'E:\Build\NOISYNE Sprint20 Validation\Results\probe.json' `
    --packaged-analysis 'E:\Build\NOISYNE Sprint20 Validation\Inputs\supported-test.wav' `
    --packaged-analysis-report 'E:\Build\NOISYNE Sprint20 Validation\Results\analysis-report.json'
  ```

  No model was initialized or downloaded.
- PyInstaller's missing `tbb12.dll` message is non-blocking for the supported deterministic
  V1 analysis path. The warning originates from Numba's optional TBB threading pool; the
  packaged librosa import and real analysis/report workflow above completed without it.

No Windows Sandbox, disposable VM, usable clean local account, or installer compiler (Inno
Setup, WiX, NSIS) was available. The strongest available isolation was a fresh temporary
workspace outside the repository, with a relocated bundle and audio input, an unrelated
working directory containing spaces, and no development `PYTHONPATH` or active virtual
environment. This is not a true clean-machine test. Windows resolved the external user-data
location to `%LOCALAPPDATA%/NOISYNE/soundbrain.desktop`; that path was outside the bundle.

The relocated bundle launched successfully and the probe found all five brand assets,
`runtime.yaml`, and Qt's native `qwindows.dll`. Two close/reopen smoke runs exited 0 in
9.149 s and 3.035 s. For the reinstall-equivalent, the original bundle was moved aside and
replaced with the same 5,591-file, 891,550,244-byte build; relaunch exited 0 in 15.467 s and
the session SHA-256 remained
`1670CA79D7E9F8D82F55A4381211AACC0C303FB3EDC65481BACA7BC0885B5EB0`. For the
uninstall-equivalent, both validation bundle copies were sent to the Recycle Bin. The copied
install path was absent afterward while the external session, reports, and model directories
remained. These are bundle replacement/removal tests, not installer tests.

A real Start Menu/uninstall-entry installer build/test and true clean-machine audio workflow
remain environment-blocked release-candidate risks. No release, tag, signing, or publishing
occurs in Sprint 20.

Completion-pass source validation: packaging tests 6 passed; full UI 368 passed; E2E 16
passed; stable V1 adapter regressions 18 passed; Ruff, Black, compileall, and Git whitespace
checks passed. No backend or V2 file was modified.
