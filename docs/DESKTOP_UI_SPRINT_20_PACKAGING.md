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

Read-only resources use `importlib.resources`. Existing V1 writable identity is preserved at
`%LOCALAPPDATA%/SoundBrain/soundbrain.desktop`; Sprint 20 does not migrate it to a NOISYNE
technical path. Frozen startup sets `SOUNDBRAIN_ROOT` to that user root before V1 settings
load, then idempotently creates state, logs, cache, reports, and the compatible sibling
Models directory. Session data is `state/session-v1.json`; desktop diagnostics are
`logs/desktop.log`. Reports remain user-selected; optional models belong in the documented
user Models directory. Initialization failures fall back to safe stderr diagnostics and the
existing UI resilience paths.

## Local candidate validation

- CPU runtime: Torch 2.13.0+cpu, Torchaudio 2.11.0+cpu, CUDA `None`.
- PyInstaller onedir build: passed; icon and version resources embedded.
- Native packaged `--smoke-test` from an unrelated path containing spaces: exit 0 in 2.26 s.
- Static artifact verification: Qt `qwindows.dll`, SVG plugin, five brand assets, YAML,
  NØISYNE 1.0.0 metadata, icon, and unwanted-file scan passed.
- Distribution size: 891,549,317 bytes across 5,591 files. PowerShell and tar ZIP creation
  were stopped after exceeding practical local build time; no completed archive size exists.
- The comprehensive import probe exceeded 120 seconds while importing bundled librosa/Numba;
  it is a known diagnostic limitation, not a shell-startup failure. No model was initialized
  or downloaded.
- PyInstaller reported the known optional Numba TBB pool missing `tbb12.dll`; accepted
  librosa/source regressions do not require that pool.

No Windows Sandbox/VM or installer compiler (Inno Setup, WiX, NSIS) was available. Therefore
the one-folder candidate is the Sprint 20 local package: copy it into any user-writable
directory, launch, replace files to reinstall, and delete that directory to uninstall. This
launch was validated without source/venv dependency by the packaged executable. A separate
copy/reinstall/removal cycle was not completed locally. User data is
outside the bundle and survives replacement/removal. A real Start Menu/uninstall-entry
installer and true clean-machine audio workflow remain Sprint 21 release-candidate risks;
no release, tag, signing, or publishing occurs in Sprint 20.

Final source validation: packaging/adjacent tests 28 passed; full UI 367 passed; E2E 16
passed; stable V1 adapter regressions 18 passed; relevant frozen V1 analyze/reference subset
10 passed; native and offscreen source smoke exited 0; Ruff, Black, compileall, and Git
whitespace checks passed. No backend or V2 file was modified.
