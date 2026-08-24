# PHASENOX External Windows Acceptance Checklist

Use this checklist on a separate Windows x64 laptop before public distribution.
It is external acceptance evidence, not a source-development sprint.

## Immutable candidate

- Source Git SHA: `3adfbab5f5dec7e5c2237febb316bc6b89459e5e`
- Version: `1.0.0`
- Installer: `PHASENOX-Setup-1.0.0-win-x64.exe`
- Installer SHA-256:
  `a30d30a4b92b7060c9e93a230c4bb291e46168b70f5379e8dbeeb3370b2e59c0`
- Installed executable SHA-256:
  `753da4c1336467b8a8fca6d7eb9ee9b7b2cbe1b3045466e1dafdd09e8fa80c48`
- Signing state: `UNSIGNED`

Stop if either hash differs. Do not substitute another artifact while recording
results against this candidate.

## Before installation

1. Record Windows edition, version/build, architecture, hostname, username,
   locale, drive inventory, free space, network state, date, and time.
2. Record whether the account is an administrator.
3. Run and save the output:

   ```powershell
   Get-FileHash .\PHASENOX-Setup-1.0.0-win-x64.exe -Algorithm SHA256
   Get-Command python,python3,py,pip,git -ErrorAction SilentlyContinue
   $env:Path
   $uninstallKeys = @(
     'HKLM:\Software\Microsoft\Windows\CurrentVersion\Uninstall\*'
     'HKLM:\Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\*'
   )
   Get-ItemProperty -Path $uninstallKeys -ErrorAction SilentlyContinue |
     Where-Object DisplayName -Match 'Microsoft Visual C\+\+.*Redistributable' |
     Select-Object DisplayName,DisplayVersion,Publisher
   ```

4. Confirm or record any pre-existing PHASENOX state, Python, VC++ runtime,
   developer tooling, Torch/CUDA/ONNX/Chroma/PyArrow, and Ableton installation.
5. Keep Microsoft Defender and SmartScreen enabled. Record warnings, detections,
   quarantine, or no observation; do not bypass or disable protection to pass.

## Installation and first launch

1. Install per-user to the default location. Record installer result and log.
2. Confirm no Python prerequisite or PATH change is requested.
3. Before first launch, confirm that no canonical pointer existed unless this is
   intentionally an upgrade test:

   `%LOCALAPPDATA%\PHASENOX\phasenox.desktop\state\data-root.json`

4. Launch PHASENOX. Confirm the Data Location dialog appears before persistent
   backend initialization.
5. Select an explicit custom Data Root independent of the install directory.
   Prefer a non-C drive and a path containing spaces if available.
6. Confirm the pointer is committed only after confirmation, and inspect C: for
   unintended Chroma, SQLite, model, or duplicate Data Root creation.
7. Hash or copy the pointer bytes for later comparison.

## Runtime acceptance

1. Close and relaunch. Confirm the same pointer is reused without a duplicate
   root or unnecessary prompt.
2. Disconnect networking and launch again. Confirm shell startup, no download,
   no model-cache creation, and truthful Desktop Core capability availability.
3. Analyze the supplied deterministic local WAV and save the result.
4. Run the supported local Reference comparison and save its visible result.
5. Export a report to a user-selected folder whose path contains spaces. Confirm
   no report or log is written into the install directory.
6. If practical, make the selected Data Root unavailable, relaunch, and confirm
   truthful recovery with an unchanged pointer and no silent C: fallback. Restore
   the root and confirm recovery.

## Reinstall and uninstall

1. Run the same installer again. Confirm application repair/reinstall succeeds
   and the pointer and user data remain byte-for-byte unchanged.
2. Uninstall PHASENOX. Confirm application files, shortcuts, and registration are
   removed while AppData, the pointer, backend data, reports, and user outputs
   remain.
3. Reinstall and confirm preserved state is reused without a duplicate root.

## Evidence record

For every result record the environment ID, Windows build, installer hash,
source SHA, UTC timestamp, command/log/screenshot path, and one of `PASS`,
`FAIL`, or `NOT_EXECUTED`. A PASS requires direct observation on this external
host. Return the evidence without secrets or personal file contents for entry
in `tools/packaging/clean-machine-matrix.json`.

Public distribution remains NO-GO until required external rows pass and the
separate legal publisher, license-review, and authorized signing policies are
resolved.
