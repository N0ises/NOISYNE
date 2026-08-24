# PHASENOX Sprint 19A Packaging / Installer Audit

Status: discovery and design only

Repository: `N0ises/NOISYNE`

Branch audited: `v2-development`

Baseline: `be35389ae0c06aabe795f65f905a0be0062ec2ed`
Target platform: Windows x64

## Executive decision

The recommended Sprint 19B release candidate is a **PyInstaller one-folder,
windowed Desktop Core bundle wrapped by a per-user Inno Setup installer**.
The installed GUI is `PHASENOX.exe`; the existing Python distribution and
console-script contract remain `phasenox` and are not renamed by the freezer.

The binary install location and PHASENOX Data Root remain independent. The
installer may suggest a Data Root, but the Desktop must confirm and commit the
choice in the current user's context before any persistent backend starts.
Existing canonical pointers, including pointers whose target contains a legacy
`soundbrain.desktop` path, are preserved unless the user explicitly approves a
change. No model is bundled or downloaded during build, install, or shell
startup.

Decision: **GO for a bounded Sprint 19B implementation and release-candidate
validation; NO-GO for public distribution today.** The blockers are listed in
Section 20.

## 1. Current packaging inventory

### Current tracked configuration

- `pyproject.toml` declares distribution `phasenox`, version `1.0.0`, and
  Python `>=3.12`. Setuptools discovers `phasenox*` and `brain*`.
- The only console script is `phasenox = phasenox.cli:main`.
- Desktop development launch is `python -m phasenox.ui`, implemented by
  `phasenox/ui/__main__.py`.
- The `desktop` extra adds PySide6. The main dependency set is currently
  monolithic and includes DSP, ML, RAG, and network packages. The
  `performance` extra adds ONNX Runtime, ONNX, and psutil.
- Packaged resources are configuration YAML files and approved runtime brand
  PNG/SVG files under `phasenox/resources/`.
- The packaging probe checks representative DSP imports, optional ML imports,
  configuration and branding resources, writable directories outside the
  install payload, and the Qt Windows platform plugin.
- There is no current tracked PyInstaller spec, Inno/WiX/NSIS/MSIX source,
  canonical Windows build script, release workflow, constraints file, or
  hash-locked dependency file.
- Root `install.ps1` installs Kimi Code and is unrelated to PHASENOX. It must
  not be reused or presented as the product installer. `validate.ps1` contains
  a developer-machine path and is not release automation.

### Historical Desktop freezer inspection

The frozen `desktop-ui` branch was inspected read-only. Its historical
`tools/packaging/noisyne.spec` and packaging tests provide useful patterns, but
not an acceptable specification.

Reusable concepts:

- PyInstaller one-folder, windowed output with UPX disabled.
- A clean CPU-only build environment and a guard against accidental CUDA
  inclusion.
- Generated ICO and Windows version resources.
- Explicit resource collection, packaging probes, and artifact assertions.
- Launch testing from an arbitrary working directory with downloads disabled.
- Separate shell/core and heavier feature profiles.

Obsolete concepts that must not be copied:

- `NOISYNE`, NØISYNE, `soundbrain`, `brain` entry/resource, or
  `soundbrain.desktop` identities as canonical release metadata.
- A combined install/AppData/backend root.
- Broad hidden-import and Qt-plugin collection without profile evidence.
- Old dependency assumptions or local verification paths.

The locally retained historical `dist/NOISYNE` is about 1.23 GiB unpacked and
contains 10,185 files. It includes a nested 319 MiB archive, a 291 MiB
`torch_cpu.dll`, unused Qt QML/Quick/PDF/VirtualKeyboard material, tests, and
legacy metadata. It is diagnostic evidence only, not a release candidate.

### Resources and brand sources

- Approved source artwork is under `assets/brand/`.
- Runtime-approved copies are under `phasenox/resources/branding/`.
- Approved raster exports include 16, 32, 64, 128, 256, 512, and 1024 pixel
  sizes, including `assets/brand/exports/phasenox-logo-1024x1024.png`.
- No models, databases, logs, reports, user audio, or developer documents are
  runtime resources.

## 2. Recommended bundle format

| Option | Assessment |
|---|---|
| PyInstaller one-folder | Recommended. Predictable DLL layout, faster startup, inspectable support surface, straightforward resource verification, and practical incremental installer upgrades. |
| PyInstaller one-file | Rejected for the baseline. It extracts at runtime, duplicates disk activity, complicates native-DLL diagnostics and signing inspection, and is a poor fit for a large PySide/native stack. |
| Nuitka / `pyside6-deploy` | Worth a later measured spike, but switching build systems now adds compiler and deployment uncertainty without evidence of a release benefit. |
| Installer wrapping one-folder | Recommended final format. It adds stable application identity, selectable destinations, upgrade/uninstall behavior, shortcuts, and future signing hooks. |

PyInstaller documents one-folder/one-file behavior and the one-file bootloader's
two-process extraction model in its [usage documentation](https://pyinstaller.org/en/stable/usage.html)
and [feature notes](https://pyinstaller.org/en/stable/feature-notes.html).
Qt supports PyInstaller for PySide applications, while noting that deployment
must include the required Qt libraries and plugins; see the official
[PySide deployment overview](https://doc.qt.io/qtforpython-6/deployment/index.html),
[PyInstaller guidance](https://doc.qt.io/qtforpython-6/deployment/deployment-pyinstaller.html),
and [Windows deployment guidance](https://doc.qt.io/qt-6/windows-deployment.html).

Target artifacts:

- Bundle directory: `PHASENOX-1.0.0-win-x64/`
- GUI: `PHASENOX.exe` (windowed)
- Installer: `PHASENOX-Setup-1.0.0-win-x64.exe`
- Hashes: `PHASENOX-1.0.0-win-x64-SHA256SUMS.txt`
- Manifest/SBOM: versioned JSON plus CycloneDX or SPDX output

## 3. Install location policy

Use a **current-user installation** for the Sprint 19B baseline:

- Default: `%LOCALAPPDATA%\Programs\PHASENOX`.
- The user may select another drive or folder.
- The bundle remains Program Files-compatible: it treats its directory as
  read-only and never derives writable state or Data Root from it.
- Changing the binary destination never moves, clones, repairs, or rewrites
  Data Root.
- Use `asInvoker` application execution and an Inno
  `PrivilegesRequired=lowest` baseline. This prevents an elevated installer
  from accidentally writing another security principal's per-user AppData.
- An all-users Program Files mode is deferred until the original-user Data
  Root handoff and permissions model have explicit implementation and tests.

## 4. Data Root installer policy

The installer UI has separate **Install Location** and **Data Location**
steps. “Use the same drive as installation” computes a suggestion only; it
does not couple the paths after installation.

Precedence and preservation rules:

1. `PHASENOX_ROOT`, then approved legacy environment fallbacks, remain runtime
   authorities exactly as established by Sprint 18. The installer does not
   rewrite environment variables.
2. If a valid canonical `data-root.json` exists, preserve it byte-for-byte by
   default and show “keep existing Data Location.” Do not overwrite it without
   explicit approval.
3. Preserve a valid pointer even when its target path contains the approved
   legacy `soundbrain.desktop` identity.
4. For a clean user, show an explicit Data Location suggestion and require
   confirmation. Never silently fall back large data to C:.
5. A custom local, removable, or network path is accepted only after path,
   access, capacity, and expected-store checks. A network/removable target must
   be labelled as availability-dependent.
6. If an existing target is unavailable, installation/update of binaries may
   continue, but the pointer is unchanged and persistent backend startup stays
   blocked. Recovery choices are retry, select an existing location, choose a
   new empty root, or temporary/non-persistent operation where supported.
7. Selecting a new empty root does not migrate or merge old stores. Migration
   remains a separate explicit operation outside Sprint 19.

The installer should pass a pending selection to a current-user first-launch
handoff. The Desktop validates and commits it before backend initialization.
This avoids making the installer a second implementation of Sprint 18's root
contract.

## 5. First-launch behavior

Recommended model: **installer suggests, Desktop confirms**.

On a clean machine with no canonical small state, pointer, or root environment:

1. The shell starts without importing or initializing persistent backends.
2. It presents the installer suggestion and a browse/select-existing choice.
3. It validates identity, writability, free space, availability, and whether
   the folder is empty or an identifiable existing PHASENOX root.
4. The user confirms the choice.
5. Only then does the Desktop write canonical small state under
   `%LOCALAPPDATA%\PHASENOX\phasenox.desktop`, commit `data-root.json`, create
   an empty root where explicitly approved, and allow backend initialization.

Cancel keeps the shell in a non-persistent/recovery state. It must not create a
replacement Chroma store, redownload models, or synthesize a fallback root.

## 6. Upgrade, reinstall, and repair behavior

- A stable opaque installer AppId must be generated once in 19B and frozen.
  It must not reuse the historical NOISYNE/SoundBrain identifier. Inno uses
  AppId to associate uninstall entries and previous settings; see
  [AppId](https://jrsoftware.org/ishelp/topic_setup_appid.htm) and
  [UsePreviousAppDir](https://jrsoftware.org/ishelp/topic_setup_usepreviousappdir.htm).
- Same-version reinstall and repair replace verified application payload,
  shortcuts, and registration only.
- Upgrade replaces the bundle while preserving install choice, canonical
  AppData, the exact Data Root pointer, and all backend data.
- A changed binary install drive does not move Data Root.
- Missing/corrupt binaries are repaired from installer payload. User state is
  neither diagnosed as application payload nor deleted.
- An unavailable Data Root remains unavailable after repair; the pointer is
  preserved and Desktop recovery remains the authority.
- Downgrade is blocked by default. A diagnostic override, if ever added, must
  first prove configuration and store schema compatibility.
- Installer version comparison, application display version, wheel version,
  and PE metadata come from one version source.

## 7. Uninstall policy

Sprint 19B implements **Remove application only**:

- Remove installed binaries, shortcuts, and installer registration.
- Preserve canonical Desktop small state, `data-root.json`, caches, models,
  reports, projects, references, output, and backend stores.
- Display a final summary naming the preserved locations where safely known.

The following are deferred: remove small Desktop state, remove disposable
cache, and remove all PHASENOX data. A future current-user cleanup helper must
inventory exact targets, distinguish cache from durable output, handle offline
roots, require explicit confirmation, and provide a reviewable deletion
summary. “Remove all” must never be a default checkbox.

## 8. Branding and version resources

Freeze these Windows fields for 19B, subject to the legal-identity blocker:

| Field | Value/source |
|---|---|
| ProductName | `PHASENØX` |
| FileDescription | `PHASENØX Desktop` |
| OriginalFilename | `PHASENOX.exe` |
| Internal/ASCII identity | `PHASENOX` |
| ProductVersion | `1.0.0` from project metadata |
| FileVersion | Numeric Windows form derived from the same source, initially `1.0.0.0` |
| CompanyName | Proposed `PHASENOX`; legal owner must be confirmed |
| Publisher | Must exactly match the future certificate subject |
| Copyright | Blocked pending authoritative legal holder/year |

Generate a multi-resolution ICO in a disposable build directory from the
approved 1024px raster and approved exports (at least 16, 24, 32, 48, 64, 128,
and 256 where source quality permits). Use it for EXE and installer. Do not
create or modify source artwork. Verify the About display against the same
version and approved runtime logo.

## 9. Canonical PyInstaller design

The canonical spec/profile should:

- Start at `phasenox/ui/__main__.py`; output windowed `PHASENOX.exe` in a
  one-folder bundle; use `upx=False`.
- Use the repository only as build `pathex`; ensure no absolute checkout path
  is serialized into the distribution or diagnostics.
- Copy an explicit allowlist of configuration YAMLs and runtime-approved
  branding. Include distribution metadata required at runtime.
- Collect only the Qt modules in use (`QtCore`, `QtGui`, `QtWidgets`) and the
  proven plugins (`platforms/qwindows` plus required image formats). Exclude
  Qt Quick/QML/PDF/WebEngine/VirtualKeyboard unless a traced shipping feature
  proves a requirement.
- Derive hidden imports from isolated trace/probe evidence. Explicitly include
  profile-selected dynamic strategies; do not use an unbounded collect-all.
- Exclude tests, tooling, docs, source brand concepts, build systems, and every
  dependency outside the selected profile.
- Keep runtime hooks minimal. A hook may repair frozen DLL/plugin lookup, but
  must not set Data Root, create stores, or download models.
- Embed version resources and a manifest with `asInvoker`; add DPI/long-path
  declarations only after compatibility tests.
- Generate icon/version/spec inputs without editing source assets.
- Fail on unexpected PyInstaller warnings, missing native libraries, forbidden
  identities, unexpected Qt modules, model files, or CUDA DLLs.
- Maintain a single canonical spec generator/profile definition rather than
  divergent hand-edited specs.

## 10. Dependency profiles

| Profile | Contents | Release position |
|---|---|---|
| Desktop Shell | PySide6 essentials, UI/application boundaries, config and branding | Diagnostic minimum, not sufficient for promised workflows |
| Desktop Core | Shell plus NumPy, SciPy, librosa, SoundFile/libsndfile, pyloudnorm and proven transitive DSP dependencies | **Standard 19B baseline** |
| CPU ML | Desktop Core plus matched CPU-only Torch/torchaudio, Transformers, sentence-transformers and required local-model support | Separate candidate after clean lock and model policy pass |
| RAG/Knowledge | Chroma, its ONNX CPU dependency, PyArrow/ecosystem dependencies, RAG clients | Separate optional profile after native/storage proof |
| GPU/CUDA | Matched CUDA Torch/torchaudio and/or ONNX GPU stack for a documented driver/CUDA matrix | Separate later distribution only |
| Development/testing | pytest, Ruff, Black, build tools, source tests, notebook/docs tooling | Never shipped |

The main project dependency declaration does not currently express these
shipping boundaries. Sprint 19B needs release-specific, hash-locked profile
inputs; it should not redefine runtime feature behavior merely to make a small
bundle.

## 11. Torch and CUDA policy

The active developer environment contains Torch/torchaudio `2.11.0+cu126` and
a CUDA-capable build. The historical packaging environment contains CPU Torch
`2.13.0` with torchaudio `2.11.0`, an unacceptable mismatch. A historical
`torch_cpu.dll` alone is about 291 MiB; CUDA payloads can be much larger.

Recommendation:

- Exclude Torch and every CUDA DLL from the standard Desktop Core installer.
- Do not freeze from the developer CUDA environment.
- Build any CPU ML artifact in a new environment with exactly matched,
  supported CPU-only Torch and torchaudio wheels and a zero-error `pip check`.
- Publish GPU/CUDA only as a separately named profile after testing a declared
  Windows/GPU driver/CUDA/cuDNN matrix, hardware fallback, installer size,
  signing, and clean uninstall.
- Optional ML invocation with no installed profile/model must fail with a clear
  capability message, not trigger an uncontrolled install or Data Root bypass.

## 12. ONNX Runtime policy

ONNX Runtime is used by performance/benchmark paths and is not required for
the current Desktop Core workflows. The developer environment has
`onnxruntime-gpu 1.19.2` with TensorRT, CUDA, and CPU providers, while project
metadata also permits CPU ONNX via an optional extra. Chroma independently
declares an ONNX Runtime dependency, so a RAG profile must reconcile package
metadata and provider selection.

- Standard Desktop Core: exclude ONNX Runtime.
- RAG/Knowledge: use a separately locked CPU ONNX package unless a real GPU
  requirement is approved.
- GPU ONNX: separate profile; probe available providers and DLL load failure
  without crashing shell startup.
- Record actual providers in diagnostics, but never initialize ONNX on shell
  import.

Official ONNX Runtime [installation requirements](https://onnxruntime.ai/docs/install/)
and [CUDA provider compatibility](https://onnxruntime.ai/docs/execution-providers/CUDA-ExecutionProvider.html)
must be the source of the profile matrix.

## 13. Models and native dependencies

### External models

Current resolution first accepts a local/explicit model and otherwise passes a
Hugging Face model ID to Transformers. `from_pretrained` can download a remote
ID on feature invocation, and the configured `model_cache` is not visibly
passed as `cache_dir` at that boundary. Therefore:

- No model or model cache enters the bundle or installer.
- Build, install, packaging probes, and initial shell launch run offline with
  download calls blocked.
- Sprint 19B must route approved first-use downloads to the selected Data Root,
  or keep such features blocked until that integration exists.
- An unavailable Data Root cannot cause cache fallback or redownload.

### Native inventory

| Component | Native concern / likely failure |
|---|---|
| PySide6 | `qwindows.dll`, image plugins, shiboken, Qt DLL closure; excessive plugin collection materially increases size |
| NumPy/SciPy | Many `.pyd`/DLL files and optimized math runtimes; imports must be tested on machines without developer runtimes |
| SoundFile | `_soundfile_data/libsndfile_x64.dll`; verify supported formats and loading from frozen location |
| librosa | Transitive numba/llvmlite, scikit-learn, joblib and soxr behavior; do not assume ffmpeg is installed |
| Torch | Large CPU DLL and strict Torch/torchaudio pairing; CUDA contamination risk |
| ONNX | CPU or CUDA/TensorRT provider DLL closure and VC++ prerequisite |
| Chroma/PyArrow | Native ecosystem and package-metadata compatibility; Windows file-handle/store lifecycle tests |
| CPython | PyInstaller must include Python 3.12 runtime; users must not install Python separately |

The current machine lacks `dumpbin`, `llvm-readobj`, `objdump`, and Sigcheck,
so native dependency closure has not been proven. The historical bundle
contains app-local `vcruntime`/`msvcp` files, but their presence is not proof
that every binary dependency is satisfied.

For 19B, inspect every shipped PE import in the clean bundle using an approved
dependency tool and test a VM with no separately installed runtime. ONNX
documents a Windows Visual C++ runtime requirement. Microsoft recommends the
current compatible v14 redistributable and central deployment for servicing;
see [latest supported downloads](https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist?view=msvc-170)
and [redistribution guidance](https://learn.microsoft.com/en-us/cpp/windows/redistributing-visual-cpp-files?view=msvc-170).
Only after the PE inventory may 19B choose either a detected/bootstrapped
official x64 redistributable or a demonstrably complete licensed app-local
closure. Do not guess from the developer machine.

## 14. Installer technology decision

| Technology | Result |
|---|---|
| Inno Setup | **Recommended.** Compact script, custom Install/Data Location pages, current-user mode, stable AppId and previous-directory support, upgrade/uninstall scripting, signing hooks, and command-line CI compilation. |
| WiX/MSI | Strong future enterprise option, but more ceremony and major-upgrade sequencing risk for the first Desktop candidate. |
| NSIS | Flexible, but lower-level custom logic and greater maintenance burden for this lifecycle contract. |
| MSIX | Not selected. Container/VFS behavior, signing requirements, and custom external Data Root/install semantics do not fit the initial support model. |

Use Inno's documented [Setup section](https://jrsoftware.org/ishelp/topic_setupsection.htm),
[custom directory page](https://jrsoftware.org/ishelp/topic_isxfunc_createinputdirpage.htm),
[privilege model](https://jrsoftware.org/ishelp/topic_setup_privilegesrequired.htm),
[non-administrative mode](https://jrsoftware.org/ishelp/topic_admininstallmode.htm),
and [compiler command line](https://jrsoftware.org/ishelp/topic_compilercmdline.htm).
WiX [major-upgrade behavior](https://docs.firegiant.com/wix3/howtos/updates/major_upgrade/)
would require careful sequencing. MSIX [VFS redirection behavior](https://learn.microsoft.com/en-us/windows/msix/msix-troubleshooting-guide)
adds complexity to the required location contract.

Inno Setup is not installed on the audited machine. Sprint 19B must pin and
provision its build-tool version in the clean release environment.

The Python console script remains `phasenox` for wheel users. Do not freeze a
second `phasenox.exe` beside `PHASENOX.exe`: Windows filenames are
case-insensitive. If a packaged console tool is approved later, use a distinct
identity such as `PHASENOX-CLI.exe`.

## 15. Clean-machine matrix

Every row is required for Desktop Core x64. Run installer cases in disposable
Windows VMs/snapshots, not a developer workstation.

| # | Scenario | Required result |
|---:|---|---|
| 1 | Clean supported Windows x64 | Installer and app run with no repository state |
| 2 | No Python installed/on PATH | GUI launches; bundled CPython is sufficient |
| 3 | Default binary destination | Per-user install succeeds without elevation |
| 4 | Custom drive/folder | Bundle runs; no paths point to the build checkout |
| 5 | New custom Data Root | Explicit confirmation precedes pointer/store creation |
| 6 | Same-drive suggestion | Suggestion is independent; later install movement does not move data |
| 7 | Existing valid Data Root | Existing data is recognized without mutation or merge |
| 8 | External Data Root disconnected | Pointer preserved; persistent backend blocked with recovery UI |
| 9 | Network Data Root online/offline | Clear availability handling; never local fallback or split-brain creation |
| 10 | First launch, no state/pointer/env | Shell opens chooser; no persistent backend starts |
| 11 | Second launch | Confirmed pointer/state survives exactly |
| 12 | Existing canonical AppData | State is preserved by installation and launch |
| 13 | Legacy-named backend target | Pointer target remains byte-for-byte unchanged |
| 14 | Environment override present | Runtime precedence remains authoritative; installer does not rewrite it |
| 15 | Same-version reinstall | Application repaired; AppData, pointer, and backend preserved |
| 16 | Upgrade over previous build | Stable AppId upgrades payload and preserves all state/data |
| 17 | Downgrade attempt | Blocked with explicit version message |
| 18 | Repair missing/corrupt binary | Payload restored; user data untouched |
| 19 | Uninstall | Binaries removed; all user state/data retained by default |
| 20 | Reinstall after uninstall | Preserved pointer/state reused; no duplicate backend |
| 21 | Arbitrary working directory | Resources/config resolve from frozen package, not CWD |
| 22 | Paths with spaces | Install, Data Root, DSP, report export, and uninstall work |
| 23 | Non-ASCII username and path | Same operations work without encoding/path corruption |
| 24 | Offline build/install/startup | No dependency/model/network request is made |
| 25 | Missing optional model | Shell remains healthy; feature gives explicit capability/recovery result |
| 26 | Read-only/unavailable chosen root | Validation rejects or blocks; no alternate store is created |
| 27 | Non-admin daily user | Launch, small state, chosen root, logs, and outputs work |
| 28 | Shell/Task Center smoke | Open, navigate, task lifecycle, cancel/restart, close cleanly |
| 29 | Analyze minimal local fixture | Deterministic Desktop Core analysis succeeds |
| 30 | Reference workflow | Local reference path/selection and result succeed |
| 31 | Report export | User-selected writable output succeeds; install folder remains unchanged |
| 32 | Crash/log behavior | Diagnostics go to canonical small state or selected data policy, never install dir |
| 33 | No VC++ redistributable preinstalled | Either app-local closure works or official prerequisite is installed/detected |
| 34 | AV/Defender and SmartScreen | Unsigned candidate behavior recorded; no false one-file extraction pattern |
| 35 | Two install destinations across upgrade | Old payload is handled deterministically; Data Root is unchanged |
| 36 | Low disk space | Installer/root validation fails before partial persistent initialization |

Repeat applicable cases for any future CPU ML, RAG, and GPU profiles, adding
hardware/provider/model and payload-size assertions.

## 16. Artifact hygiene

The bundle verifier uses an explicit allowlist plus targeted deny rules. It
must reject:

- `tests/`, developer tools, caches, bytecode outside frozen needs, coverage,
  notebooks, roadmap/audit documents, and source-control metadata;
- absolute repository/user paths and build-environment names;
- databases, Chroma directories, `index.db`, manifests of real user stores,
  canonical or legacy Desktop state, logs, reports, personal audio, projects,
  references, and model caches/weights;
- `.env`, credentials, tokens, certificates/private keys, CI secrets, and
  local environment configuration;
- unapproved brand concepts/source working files;
- legacy product-facing metadata or filenames except explicitly approved
  compatibility code/resources required by runtime tests;
- CUDA/ONNX/Torch/RAG/PyArrow or unused Qt modules in Desktop Core;
- nested bundle archives and source distributions.

Verify file inventory, size budget, PE metadata, resource hashes, import smoke,
arbitrary-CWD launch, write locations, no-download behavior, and clean shutdown.
Treat unexpected additions as review failures, not harmless freezer noise.

## 17. Reproducibility and release manifest

Sprint 19B should build only from a clean commit in a fresh Windows x64
environment using:

- A pinned Python 3.12 patch release.
- Per-profile constraints/lock files with hashes, including PyInstaller,
  PySide6/shiboken, native scientific wheels, and Inno Setup version.
- A clean virtual environment and private wheelhouse/cache; `pip check` must
  return zero errors.
- A recorded OS/SDK/toolchain architecture and native-runtime decision.
- Clean output directories and no dependency on global Python or the current
  developer environment.

Release manifest fields:

- canonical product/distribution/profile/platform/architecture;
- semantic, PE file, and installer versions;
- Git SHA, branch/tag, and clean-worktree assertion;
- Python, PyInstaller, Qt/PySide, installer, and build-host versions;
- complete locked dependency inventory with wheel origins/hashes;
- bundle file paths, SHA-256 hashes, sizes, and aggregate size;
- approved resource names/hashes and Windows metadata;
- native DLL/provider inventory and VC++ strategy;
- test/probe matrix identifiers and results;
- installer AppId, requested privilege, destinations, and uninstall policy;
- SBOM and license-report hashes;
- signing state, certificate identity/thumbprint, and timestamp authority when
  signing is later enabled;
- UTC build time and reproducibility inputs.

PE/installer timestamps and future signatures may prevent bit-for-bit equality.
Record reproducible inputs and an unsigned-payload hash first; claim binary
reproducibility only after a controlled `SOURCE_DATE_EPOCH` experiment proves
it. Produce CycloneDX or SPDX SBOM and a license notice/report before release.

## 18. CI and release path

Future Windows release automation:

1. Checkout an exact clean commit/tag.
2. Provision pinned Python/build tools and a profile-specific clean venv.
3. Install hash-locked wheels; run `pip check`, license, and vulnerability
   inventory gates.
4. Run unit/application/Desktop contract tests.
5. Build and test the `phasenox` wheel/sdist.
6. Generate approved ICO/version resources into build output.
7. Build the PyInstaller one-folder profile.
8. Run bundle verifier, frozen probes, no-download checks, and SBOM generation.
9. Compile the Inno installer from the verified payload.
10. Install/test/uninstall on clean Windows VM snapshots across the matrix.
11. Emit hashes, manifest, logs, size diff, and release-candidate provenance.
12. Later, sign individual executable/DLL payload where required, then the
    installer, using protected CI secrets and a trusted timestamp service.
13. Promote only the tested immutable artifacts; do not rebuild after testing.

Signing is not implemented in 19A/19B unless credentials are separately
authorized. Unsigned builds will have poorer SmartScreen reputation. Certificate
private keys must use a managed signing service/HSM or protected CI secret,
never the repository or bundle.

## 19. Exact Sprint 19B scope

### Must implement

1. Freeze the Windows x64 Desktop Core feature/dependency boundary.
2. Add hash-locked clean-build inputs and enforce CPU/CUDA/profile guards and
   zero-error `pip check`.
3. Add a canonical PyInstaller one-folder/windowed spec generator or profile
   rooted at `phasenox/ui/__main__.py`.
4. Generate ICO and PE version metadata from approved assets and the single
   project version source, without changing artwork.
5. Add a clean PowerShell build orchestrator with isolated output and recorded
   provenance.
6. Add a bundle verifier for identity, allowed resources, Qt/native closure,
   forbidden payload, sizes, arbitrary CWD, read-only install behavior, and no
   model/network activity.
7. Freeze GUI identity as `PHASENOX.exe` while leaving the Python `phasenox`
   console-script contract unchanged.
8. Add a current-user Inno Setup baseline with a new stable AppId, selectable
   binary directory, canonical metadata, repair/upgrade rules, and app-only
   uninstall.
9. Implement the independent Data Location page and current-user Desktop
   handoff. Preserve any existing pointer/state byte-for-byte unless change is
   explicitly approved.
10. Complete clean first-launch confirmation/recovery so no persistent backend
    initializes before root selection and no unavailable root falls back.
11. Add packaging probes for canonical AppData, Data Root preservation,
    arbitrary CWD, offline startup, no downloads, and clean shutdown.
12. Automate disposable clean-VM install/launch/workflow/upgrade/uninstall
    cases, including no Python and no preinstalled VC runtime.
13. Prove native PE/DLL closure and select/document the VC++ redistribution
    strategy from evidence.
14. Generate artifact manifest, SHA-256 file, SBOM, license report, and
    allowlist inventory; enforce artifact hygiene and size budgets.
15. Document supported Windows versions, Desktop Core features, offline/model
    behavior, install/Data Root semantics, recovery, upgrade, and uninstall.

### Explicitly defer

- Online updater or update service.
- Production certificate signing if identity/credentials are unavailable
  (hooks and unsigned diagnostics may be added).
- CUDA/GPU distribution and multi-profile public release.
- CPU ML/RAG/PDF profiles unless separately locked and accepted after the Core
  candidate; they must not delay or contaminate Desktop Core.
- Model bundling or implicit first-launch downloads.
- Full “Move PHASENOX Data” operation or storage migration.
- General writable Settings redesign.
- All-users Program Files install until user-context handoff is proven.
- Destructive uninstall choices and user-data deletion helper.

## 20. Risks and blockers

### Release-blocking

- No per-profile hash lock/constraints or reproducible clean environment.
- Neither inspected Python environment is valid release evidence: the developer
  environment is CUDA-heavy and has a Chroma/ONNX metadata conflict; the old
  freezer environment has mismatched Torch/torchaudio and stale distributions.
- Desktop Core's exact promised feature boundary and size budget are not yet
  frozen.
- Remote model resolution can download and does not visibly bind its cache to
  the authoritative Data Root.
- Clean first-launch Data Root selection/confirmation and unavailable-root
  recovery need packaged end-to-end proof.
- Native DLL/VC++ closure has not been inspected with a PE dependency tool or
  tested on a clean VM.
- New stable installer AppId, legal Company/Publisher/copyright identity, and
  future certificate subject are unresolved.
- No clean Windows snapshot matrix has passed.

### High risk

- Historical freezer output demonstrates severe size and stale-resource
  contamination if broad hooks are reused.
- Chroma's ONNX dependency and PyArrow/native lifecycle complicate a future RAG
  profile.
- Qt plugins, scientific libraries, and audio format support can pass locally
  while failing on a clean machine.
- Unsigned artifacts can trigger SmartScreen/antivirus warnings.
- Upgrade, repair, external/network roots, non-ASCII paths, and interrupted
  installs need destructive-failure testing.

### Medium risk

- ICO intermediate sizes and Windows high-DPI display need visual QA.
- Version/SBOM/license metadata can drift unless generated from one manifest.
- Session/report/log privacy and support bundles require an explicit inventory.

## 21. GO / NO-GO

**GO:** begin Sprint 19B as the bounded implementation above: Windows x64,
Desktop Core, PyInstaller one-folder, per-user Inno Setup, independent Data
Location handoff, app-only uninstall, and rigorous clean-machine verification.

**NO-GO:** do not publish a final installer until all release-blocking items in
Section 20 are closed and the full applicable matrix is green. Do not ship the
historical bundle, a build made from the active CUDA environment, a monolithic
all-dependency installer, bundled models, a silent C: Data Root fallback, or a
GPU/RAG profile under the Desktop Core name.

This audit changes no production/test contract, builds no installer, migrates
no data, modifies no approved artwork, and does not start Sprint 19B.
