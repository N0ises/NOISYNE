# PHASENOX Sprint 19C Clean-Machine Certification Report

## Verdict

- Sprint 19C certification: **FAIL — REQUIRED INFRASTRUCTURE UNAVAILABLE**
- Technical RC: **NO-GO**
- Public release: **NO-GO**

This result does not identify a new Desktop Core payload defect. It means the
essential certification criteria were not executed in a genuinely disposable
Windows environment and therefore cannot be marked PASS. Developer-workstation
evidence was deliberately not substituted for clean-machine evidence.

## Candidate identity and integrity

- Tested source identity: `b7908b921a7227d19e85d765588f5375e1b08a34`
- Bundle: `PHASENOX-1.0.0-win-x64`
- Executable SHA-256:
  `5103e8598956c1af40f6f5b8203c5f281872987fcc9b4dca2fb939500c6376df`
- Installer: `PHASENOX-Setup-1.0.0-win-x64.exe`
- Installer SHA-256:
  `1139223984428a875102e5245e099cda043eb2033a6aba32c3f96b14bc61629e`
- Installer AppId: `{A6B2A61D-05B0-4CE7-85A3-C443B36D703B}`
- Profile: `desktop-core / windows-x64`
- Signing: `UNSIGNED`

The executable and installer hashes were checked before and after the Sprint
19C automation work and matched the Sprint 19B checksum evidence exactly. No
bundle, installer, manifest, SBOM, license inventory, or checksum file was
rebuilt or regenerated. The immutable candidate remains the Sprint 19B
artifact.

## Infrastructure audit

Certification-eligible Windows environments used: **0**.

The available host was inspected only to determine infrastructure eligibility:

- OS: Microsoft Windows 11 Pro, version `10.0.26200`, build `26200`, x64
- Environment class: normal developer workstation; not disposable
- Windows Sandbox executable: absent
- Hyper-V cmdlets/hypervisor: absent
- VMware `vmrun`: absent
- VirtualBox `VBoxManage`: absent
- Docker: absent
- Clean Windows CI runner tooling: unavailable
- Optional-feature inspection/provisioning: requires elevation
- Python: installed (`python`, `python3`, and `py` resolve)
- Microsoft VC++ Redistributables: multiple versions installed, including v14

Consequently, this host cannot prove no-Python startup or app-local native
closure without a separately installed VC++ runtime. Enabling a hypervisor or
Sandbox would require elevated system changes and potentially a reboot; those
changes were not silently made.

## Matrix result

The tracked matrix remains evidence-conservative:

- PASS: 0
- FAIL: 0
- BLOCKED: 18
- NOT_EXECUTED: 18

Every row retains `BLOCKED / NOT_EXECUTED`. The matrix now binds those rows to
the exact Git SHA and immutable executable/installer hashes and records the
infrastructure blocker. No row was promoted based on static inspection or
reasoning.

## Certification results

| Area | Result | Evidence / reason |
|---|---|---|
| No-Python launch | BLOCKED | No disposable Windows environment without Python was available. |
| Native DLL / no-VC++ runtime | BLOCKED | Workstation has multiple VC++ redistributables; static Sprint 19B PE closure is not runtime certification. |
| Default per-user install | BLOCKED | Installer was not executed on a clean machine. |
| Custom drive/path with spaces | BLOCKED | No disposable second-drive environment. Harness now preserves native argument boundaries. |
| Clean first-launch Data Root | BLOCKED | No clean user profile was available. UI-automation confirmation is now scripted. |
| Custom Data Root | BLOCKED | Harness now sets and verifies an independent custom/non-ASCII-capable path, but no disposable execution occurred. |
| Unavailable/removable/network root | BLOCKED | No disposable removable/network-root environment. |
| Offline launch / no downloads | BLOCKED | Sprint 19B local frozen probe passed, but no clean-machine network-disabled proof exists. |
| Second launch/state continuity | BLOCKED | Scripted with byte-for-byte pointer comparison; not executed cleanly. |
| Legacy `soundbrain.desktop` target | BLOCKED | Existing unit coverage remains green; no packaged upgrade fixture was exercised. |
| Distinct-version upgrade | BLOCKED | No previous-candidate installer plus disposable snapshot was available. |
| Same-version reinstall/repair | BLOCKED | Harness can remove and repair a deterministic application DLL while preserving the pointer; not executed cleanly. |
| Downgrade | BLOCKED | Source rule exists, but two installed candidate versions were not exercised. |
| App-only uninstall/reinstall | BLOCKED | Harness validates application removal and pointer/state preservation; not executed cleanly. |
| Non-ASCII user/path | BLOCKED | No disposable non-ASCII Windows account/path was exercised. |
| Read-only install payload | BLOCKED | Harness now applies/restores an RX ACL and probes launch; not executed cleanly. |
| Analyze smoke | BLOCKED | Harness accepts a deterministic fixture and records packaged analysis/report evidence; no clean-machine execution. |
| Reference/report workflow | BLOCKED | Requires genuine packaged UI/workflow execution; no clean environment available. |
| Task Center/scheduler | BLOCKED | Requires genuine packaged UI execution; no clean environment available. |
| Defender/SmartScreen | BLOCKED | Unsigned installer was not launched on a clean Defender/SmartScreen-enabled machine. No trust claim is made. |

## Hardened repeatable command

`tools/release/validate_windows_install.ps1` now provides a fail-closed clean
machine harness that:

- requires the expected installer SHA-256 before execution;
- records Windows build, architecture, user privilege, Python commands,
  installed VC++ redistributables, network state, locations, and timestamp;
- can require no Python, no separately installed VC++ runtime, offline network,
  and absent canonical user state;
- uses `.NET ProcessStartInfo.ArgumentList` so spaces and non-ASCII argument
  boundaries are preserved;
- installs to a caller-selected destination without elevation;
- uses Windows UI Automation to confirm the real first-launch Data Location
  dialog and optionally set an independent custom Data Root;
- validates installer handoff consumption and atomic pointer creation;
- runs first- and second-launch frozen probes and optional deterministic Analyze
  plus report output;
- asserts pointer byte preservation on restart, repair, and uninstall;
- can test read-only install ACL behavior, same-version repair, a controlled
  previous installer, and application-only uninstall;
- blocks if a forbidden model cache appears;
- writes structured JSON evidence suitable for matrix promotion.

The command is intentionally not run on the developer workstation because it
installs, changes ACLs, can remove an application DLL for repair testing, and
can uninstall the application. It is designed for an interactive disposable
Windows desktop or equivalent clean runner.

## Example disposable-machine invocation

```powershell
.\validate_windows_install.ps1 `
  -Installer 'D:\Candidate\PHASENOX-Setup-1.0.0-win-x64.exe' `
  -ExpectedVersion '1.0.0' `
  -ExpectedInstallerSha256 '1139223984428a875102e5245e099cda043eb2033a6aba32c3f96b14bc61629e' `
  -InstallRoot 'D:\PHASENOX Test\App' `
  -DataRoot 'D:\PHASENOX Data\Tést Root' `
  -AudioFixture 'D:\Fixtures\test.wav' `
  -EvidenceDirectory 'D:\Evidence\PHASENOX-19C' `
  -RequireCleanUserState -RequireNoPython -RequireNoVCRedist -RequireOffline `
  -Repair -ReadOnlyInstallProbe -Uninstall
```

The disposable environment must have an interactive desktop for UI Automation.
Network isolation must be established by the VM/Sandbox/runner configuration;
the harness verifies the reported network profile but does not weaken Defender
or mutate firewall policy to manufacture an offline result.

## Changes and validation

No product, persistence, Data Root, identity, branding, installer, or bundle
contract was changed. No artifact fix was made.

Sprint 19C commits before this report:

1. `cf4e2d6` — harden the clean-machine certification harness and bind matrix evidence
2. `a36c614` — support custom Data Root certification through the real first-launch UI
3. The commit containing this report records the blocked certification result.

Local validation:

- Packaging contract tests: 8 passed
- PowerShell parser: PASS
- Matrix JSON parse: PASS
- Ruff touched Python: PASS
- Black `--check` touched Python: PASS
- `compileall tests tools`: PASS
- `git diff --check`: PASS

No Inno or payload source changed, so the installer was not recompiled and the
expensive release build was not rerun.

## Remaining blockers

Technical RC remains NO-GO until a genuinely disposable Windows environment
proves all essential criteria:

1. no-Python installation and launch;
2. native runtime closure without a separately installed VC++ redistributable,
   or an evidence-based official redistributable strategy;
3. first-launch/custom/unavailable Data Root behavior and no silent C: fallback;
4. offline launch with monitored absence of downloads/cache fallback;
5. distinct-version upgrade, repair, downgrade, and app-only uninstall/reinstall;
6. deterministic Analyze and Reference/report smoke;
7. Task Center/scheduler and clean shutdown;
8. paths with spaces, non-ASCII paths/user, and read-only install payload;
9. Defender/SmartScreen observation on the unchanged unsigned artifacts.

Public release additionally remains NO-GO because legal publisher/copyright
identity, license review, authorized production signing, and SmartScreen
reputation policy remain unresolved.

No push occurred. Sprint 20 was not started.
