# PHASENOX Sprint 19B Packaging / Installer Report

## Decision

Sprint 19B local implementation is **COMPLETE**. The Windows x64 Desktop Core
bundle, fail-closed verifier, per-user installer, Data Root handoff, native
inventory, manifest, hashes, SBOM, and license inventory were produced from a
locked clean build and passed every locally executable release gate.

Public release is **NO-GO**. Disposable clean-machine rows remain
`BLOCKED / NOT_EXECUTED`; legal publisher/copyright identity is unresolved; the
release candidate is unsigned; and the no-preinstalled-VC-runtime case has not
been proven in a disposable machine.

## Local commit chain

The Sprint 19B chain after base `be35389ae0c06aabe795f65f905a0be0062ec2ed`
is:

1. `cfbbc2e` — freeze Desktop Core release profile and locks
2. `fd0fc1c` — add canonical PHASENOX PyInstaller spec and resource generation
3. `258b1fb` — add clean builder and fail-closed bundle verifier
4. `a036168` — add per-user installer and Data Root handoff
5. `c06859d` — add native and clean-machine release probes
6. `2af22b2` — generate installer release evidence
7. `5a51819` — enforce Desktop Core release contract in tests
8. `e532b03` — fix portable single-wheel selection
9. `36beed4` — verify pinned Inno release metadata
10. `fd3eb10` — track the authoritative Sprint 19A audit
11. The commit containing this report records the final Sprint 19B result.

No commit was pushed.

## Desktop Core dependency boundary

The tracked profile is `desktop-core / windows-x64`. It promises shell and
navigation, supported Task Center jobs, deterministic local audio analysis,
deterministic reference comparison, report preview/export, read-only runtime
settings, and deterministic Core intelligence.

Knowledge/RAG, semantic model analysis, LLM reasoning, CPU ML, GPU/CUDA, and
model download capability are unavailable in this profile. The environment and
bundle guards reject Torch, torchaudio, CUDA, ONNX/ONNX Runtime, Chroma,
PyArrow, Transformers, Sentence Transformers, Accelerate, model weights, model
caches, and user/database state.

## Clean build environment and dependency lock

- Source: clean `git archive` of `36beed4132c19bae2721dce8f706000a76e177c3`
- Branch: `v2-development`
- Python: CPython `3.12.10`, fresh venv
- PyInstaller: `6.22.2`
- PySide6 Essentials / Shiboken6: `6.11.2`
- Inno Setup: official `7.1.0-x64`
- Runtime packages: 29 exact Windows wheel requirements with SHA-256 hashes
- Build packages: exact separate hash-locked build closure
- Installation: offline wheelhouses with `--require-hashes`
- `pip check`: PASS, zero broken requirements
- Forbidden distribution/module probe: PASS, all absent
- Global packages: not used

The release locks were generated from clean Windows wheelhouses, not from the
CUDA-heavy development environment or a historical packaging environment.

## Bundle result

- Bundle: `PHASENOX-1.0.0-win-x64/`
- Executable: `PHASENOX.exe`
- Format: PyInstaller one-folder, windowed, `upx=False`, `asInvoker`
- Files: 651
- Unpacked size: 345,783,748 bytes (329.77 MiB)
- Config resources: PASS
- Approved runtime branding set: exact match, PASS
- Qt plugin set: exact six-plugin allowlist, PASS
- Forbidden payload scan: PASS
- Local/repository/user absolute-path scan: PASS
- Secret and state scan: PASS
- Unexpected PyInstaller warnings: zero

The only PyInstaller warnings were the reviewed hook mismatches
`pycparser.lextab`, `pycparser.yacctab`, and `scipy.special._cdflib`. They did
not produce unresolved runtime imports and are explicitly allowlisted.

The largest file is `llvmlite.dll` at 120,369,664 bytes. It was investigated as
the Numba/librosa deterministic Core audio dependency rather than hidden ML
profile contamination. Footprints are: Qt 72,519,728 bytes; NumPy 27,545,871
bytes; SciPy 70,685,184 bytes; and librosa/Numba/llvmlite 121,411,943 bytes.
The bundle is 73.8% smaller than the historical approximately 1.23 GiB
contaminated Desktop artifact and remains below the 700 MiB unpacked RC budget.

## Frozen launch and download safety

The frozen executable returned zero from an arbitrary working directory with
offline environment controls enabled. It loaded the approved resources and
Core scientific stack, found Torch/torchaudio/Transformers unavailable, made no
model-download attempt, created no Hugging Face cache, wrote the canonical Data
Root pointer outside the install directory, emitted no stderr, and left the
bundle byte-for-byte unchanged. The initial shell/probe does not initialize
Chroma, SQLite, models, or remote clients.

## Windows PE metadata and native closure

`PHASENOX.exe` contains:

- ProductName: `PHASENØX`
- FileDescription: `PHASENØX Desktop`
- InternalName: `PHASENOX`
- OriginalFilename: `PHASENOX.exe`
- ProductVersion: `1.0.0`
- FileVersion: `1.0.0.0`
- Icon resource: present
- Manifest resource: present
- SpecialBuild: `UNSIGNED RELEASE CANDIDATE`

`pefile 2024.8.26` inspected all 241 shipped `.exe`, `.dll`, and `.pyd` files.
There were zero parse errors and zero unresolved native imports. CPython, Qt,
Shiboken, OpenSSL, libsndfile, OpenBLAS, and the MSVC runtime imports resolved
app-locally or to Windows system APIs. App-local closure is sufficient on the
build workstation; a machine with no preinstalled VC++ runtime remains a VM
blocker, so no broader VC++ claim is made.

## Installer and Data Root behavior

- Artifact: `PHASENOX-Setup-1.0.0-win-x64.exe`
- Size: 93,779,700 bytes (89.44 MiB)
- Technology: Inno Setup `7.1.0-x64`
- Stable AppId: `{A6B2A61D-05B0-4CE7-85A3-C443B36D703B}`
- Privilege model: per-user, `PrivilegesRequired=lowest`
- Default install: `%LOCALAPPDATA%\Programs\PHASENOX`
- Upgrade directory: previous directory preserved
- Downgrade: blocked by default
- Signing: `UNSIGNED`

Install Location and Data Location are independent. Setup writes only a bounded
current-user `installer-data-root.json` proposal. It never writes
`data-root.json`, creates backend stores, migrates data, or rewrites environment
variables. Existing pointers are kept by default. PHASENOX starts pre-backend,
validates the suggestion, requires explicit user confirmation, and only then
atomically commits the canonical pointer. Cancel or an unavailable target keeps
the application in recovery with no fallback. Environment-selected unavailable
roots cannot be silently overridden.

Unit and contract tests prove new-root confirmation, source=`installer`, handoff
consumption only after success, byte-for-byte pointer preservation on failure,
environment precedence, no automatic directory creation, and app-only uninstall
configuration. Actual reinstall/upgrade/uninstall execution is deferred to the
disposable-machine matrix; no workstation result is represented as clean-machine
proof.

## Artifact evidence

The ignored local release output at `build/release/desktop-core` contains:

- `evidence/PHASENOX-release-manifest.json`
- `evidence/bundle-verification.json`
- `evidence/release-environment.json`
- `evidence/PHASENOX-desktop-core.cdx.json` (CycloneDX 1.6)
- `evidence/PHASENOX-desktop-core-licenses.json`
- `PHASENOX-1.0.0-win-x64-SHA256SUMS.txt`

The license report covers runtime-locked dependencies only and explicitly makes
no unsupported legal-compliance claim. The release manifest records the full
bundle inventory and hashes, locked dependency hashes, PE/native results,
resource hashes, versions, AppId, privilege/uninstall policy, provenance,
offline probe, signing state, and UTC timestamp.

Canonical SHA-256 values include:

- `PHASENOX.exe`: `5103e8598956c1af40f6f5b8203c5f281872987fcc9b4dca2fb939500c6376df`
- installer: `1139223984428a875102e5245e099cda043eb2033a6aba32c3f96b14bc61629e`
- bundle verification: `89e102164fa8860e77251fc48c1d99a4b9bd899e29e3abdfbd1e05d03ab449b0`
- CycloneDX SBOM: `03557b3521761742f4c8b5fe347ebca0d29093feb2ac4622ddec2d09d30c6224`
- license inventory: `62f33c6ff000d86af5befdea7c8d55d64cacb439da4a587cda060d5fb08e191c`
- release manifest: `0342a4aa0ae0d673942e78f622334428abf8d2282432515b430e4919b6484d73`

## Validation results

- Canonical clean build: PASS
- Bundle verifier, including launch: PASS
- Installer compilation: PASS
- Environment/forbidden-package guard: PASS
- Native closure: PASS
- Desktop/packaging/identity/branding/distribution: 173 passed in isolated processes
- Application service, scheduler, persistence, application-root, service and RAG regressions: 104 passed in isolated processes
- Focused packaging/Data Root set during implementation: 37 passed
- Ruff on 12 touched Python files: PASS
- Black `--check` on 12 touched Python files: PASS
- `compileall phasenox brain tests tools`: PASS
- PowerShell parser on touched scripts: PASS
- Inno compilation: PASS
- `git diff --check`: PASS

A combined desktop run first passed 50 tests and then encountered the known
Windows native test-order access violation while spawning a subprocess. As
required, the files were rerun in separate Python processes; all 173 passed.
No assertion failure was hidden.

## Clean-machine matrix and reproducibility

The tracked matrix and `validate_windows_install.ps1` provide executable proof
steps for no-Python/no-repository machines, default/custom install, pointer
preservation, and app-only uninstall. All 18 VM-only rows are truthfully marked
`BLOCKED / NOT_EXECUTED` because no disposable Windows VM or Sandbox execution
was available. This includes offline first launch, paths with spaces/non-ASCII,
reinstall, upgrade, uninstall, unavailable roots, workflow smoke, and the
no-preinstalled-VC-runtime case.

Several clean local freezer builds produced the same 651-file dependency shape,
but build timestamps changed executable/installer bytes. Bit-for-bit
reproducibility is not claimed. A second independent clean-machine normalized
comparison remains required.

## Remaining public-release blockers

1. Execute and pass all required rows in a disposable Windows x64 environment.
2. Prove the runtime/VC++ strategy on a machine without a preinstalled VC++ runtime.
3. Resolve truthful legal Publisher, CompanyName, and copyright metadata.
4. Complete legal review of the third-party license inventory.
5. Obtain authorized production code-signing identity and sign the artifacts.
6. Perform a second independent normalized reproducibility build.

Final public-release verdict: **NO-GO**.

No persistence identity, environment precedence, frozen branch, Desktop roadmap,
or approved brand source asset was changed. No push occurred, and Sprint 20 was
not started.
