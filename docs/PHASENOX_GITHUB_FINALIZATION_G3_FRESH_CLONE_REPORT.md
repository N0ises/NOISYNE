# PHASENOX G3 Fresh Clone and Repository Final Verification

## Verdict

| Gate | Result |
| --- | --- |
| G3 fresh-clone verification | **PASS** |
| GitHub repository finalization | **COMPLETE** |
| Public product release | **NO-GO** |

G3 proves the canonical repository, package, CI contract, protected workflow,
and archival history from a new checkout. It does not close the 18 external
Windows acceptance rows or the 3 legal/signing items.

## Canonical repository precheck

- Repository: `N0ises/PHASENOX`
- Repository ID: `1301844155`
- Canonical URL: `https://github.com/N0ises/PHASENOX.git`
- Default branch: `main`
- Verified starting `main`: `db7b7a5450f8a985f8c8a2030d974d5de6719ea9`
- Verified starting `develop`: `db7b7a5450f8a985f8c8a2030d974d5de6719ea9`
- Latest applicable starting-main workflow: `PHASENOX CI`, run
  `32769982344`, conclusion `success`
- Required check: `Windows identity and distribution`

Main protection was active during verification. It required the canonical
strict status check and a pull request, required conversation resolution,
blocked force pushes and deletion, and retained documented administrator
recovery (`enforce_admins=false`). Signed commits and linear history were not
required.

## Fresh workspace and clone

- Disposable workspace:
  `E:\Build\PHASENOX-G3-FRESH-20260824-125545`
- Clone directory:
  `E:\Build\PHASENOX-G3-FRESH-20260824-125545\repo`
- Clone command used only the canonical HTTPS URL.
- Checked-out branch: `main`
- Cloned HEAD: `db7b7a5450f8a985f8c8a2030d974d5de6719ea9`
- Fetch and push URL: `https://github.com/N0ises/PHASENOX.git`
- Initial status: clean
- No old checkout, virtual environment, build output, cache, or developer
  configuration was copied into the workspace.

## Branch, tag, and history integrity

The fresh clone resolved the expected retained remote branches:

| Ref | Verified SHA |
| --- | --- |
| `origin/main` | `db7b7a5450f8a985f8c8a2030d974d5de6719ea9` |
| `origin/develop` | `db7b7a5450f8a985f8c8a2030d974d5de6719ea9` |
| `origin/v2-development` | `3b9272790ad1cbea5b89947761ceecb52a32cb89` |
| `origin/desktop-ui` | `e2dd11e4193f32cd4f31cda5bca8cbd322bec3af` |
| `origin/v1-freeze-candidate` | `04b896f151e17e9d4cf35b31afc4e68a254e0306` |
| `origin/v1-ui-baseline` | `04b896f151e17e9d4cf35b31afc4e68a254e0306` |

Required tags also resolved:

| Tag | Verified target |
| --- | --- |
| `v2-engineering-freeze` | `5a949daff6d679b2c87b24354ce9f9d7f885f585` |
| `archive/main-pre-phasenox` | `a1946dd838d4918cac5d78f906719e62a9dbcc32` |
| `archive/desktop-ui-v1-freeze` | `e2dd11e4193f32cd4f31cda5bca8cbd322bec3af` |
| `archive/v1-freeze-candidate` | `04b896f151e17e9d4cf35b31afc4e68a254e0306` |
| `archive/v1-ui-baseline` | `04b896f151e17e9d4cf35b31afc4e68a254e0306` |
| `archive/develop-pre-v2` | `53bd19802593905ec7ff20144bff0fc35b23d92b` |
| `archive/agent-sprint-1-runtime-stabilization` | `35db097802cd471ff6afcc2265a394c148cdd2e3` |
| `v1.0.0` | `2fed61f38e70f354a5be6b577d5a62f4c69ea626` |

The remote exposed 19 tags. Historical Desktop, V1, old-main, V2 freeze,
and candidate-source commits remained reachable. No history loss was found.

## Old URL independence

- Fresh clone remote URLs containing the old repository: `0`
- Current-facing old repository references: `0`
- Stale old repository references: `0`
- Exact tracked `N0ises/NOISYNE` matches: `25`

The 25 exact matches are confined to historical audits/freeze evidence and
negative regression assertions. They do not configure a current remote,
package URL, workflow, README command, build script, or product-facing link.

## Python environment and source installation

- Interpreter: `Python 3.12.10`
- Source-install pip: `pip 26.2.1`
- Installation method: normal editable install from the fresh source tree,
  including the declared base dependency closure
- `pip check`: `No broken requirements found.`
- Distribution: `phasenox`
- Version: `1.0.0`
- Imported module:
  `E:\Build\PHASENOX-G3-FRESH-20260824-125545\repo\phasenox\__init__.py`
- Old `E:\Build\NOISYNE` path present on the arbitrary-directory probe's
  `sys.path`: no
- `phasenox --help`: exit `0`

An initial provenance probe was invoked while the shell's working directory
was the original checkout and therefore demonstrated Python's ordinary
current-directory precedence. The authoritative rerun was performed from the
dedicated arbitrary directory and resolved only the fresh clone. No installed
path defect was present.

## Canonical CI-equivalent validation

The meaningful steps in `.github/workflows/phasenox-ci.yml` were reproduced
with a separate Python 3.12 environment containing `build`, `pytest`, and
`PyYAML`.

| Test group | Result |
| --- | --- |
| `test_github_configuration.py`, repository freeze, release alignment, Desktop Core packaging | **22 passed** in 0.44 s |
| `test_phasenox_distribution.py` | **4 passed** in 40.82 s |

Total CI-equivalent result: **26 passed**. The workflow triggers on pushes to
`main` and pull requests targeting `main`, uses read-only contents permission,
and contains no stale repository-name assumption.

## Wheel and source distribution

`python -m build` completed successfully from the fresh clone.

- Wheel: `phasenox-1.0.0-py3-none-any.whl`
- Source distribution: `phasenox-1.0.0.tar.gz`
- Wheel inventory: 478 files
- Source-distribution inventory: 633 entries
- Build warnings: setuptools warned that the table-form license and license
  classifier are deprecated for a future setuptools release; these warnings
  did not fail the current build.

Built metadata verified:

- `Name: phasenox`
- `Version: 1.0.0`
- Repository: `https://github.com/N0ises/PHASENOX`
- Issues: `https://github.com/N0ises/PHASENOX/issues`
- Console entry point: `phasenox`

The only `noisyne`/`SoundBrain` terms in expanded wheel metadata occur in the
packaged compatibility paragraph documenting the supported aliases, removed
old CLI commands, and legacy environment fallback. They are approved
compatibility content, not distribution identity.

## Fresh wheel installation and path-leak audit

A second disposable environment installed the freshly built wheel through a
normal dependency-resolving pip operation. The first attempt exhausted the
host's E: drive while extracting dependencies. After clearing only completed
or partial disposable G3 environments, a newly reset wheel environment
completed normally.

- Wheel installation: **PASS**
- `pip check`: **PASS**
- Arbitrary-CWD import: **PASS**
- Imported module location:
  `E:\Build\PHASENOX-G3-FRESH-20260824-125545\venv-wheel\Lib\site-packages\phasenox\__init__.py`
- CLI from arbitrary CWD: **PASS**, exit `0`
- Lightweight application/runtime imports: **PASS**
- Old checkout on `sys.path`: no
- Absolute source/user path leaks in expanded wheel or sdist: `0`

The capacity event was an environmental retry condition, not a resolver,
metadata, package, or test failure.

## Desktop developer launch

Desktop dependencies were installed from the pinned Desktop Core input,
including `PySide6-Essentials==6.11.2` and `shiboken6==6.11.2`. The application
was launched from the fresh clone with:

- the Qt offscreen platform;
- `--smoke-test`;
- a disposable explicit Data Root;
- isolated disposable `APPDATA` and `LOCALAPPDATA`.

The shell started and closed cleanly with exit code `0`. Canonical PHASENOX
AppData state was created only inside the disposable profile, the fresh source
tree stayed clean, and no old checkout path was required. This is a developer
launch check, not clean-machine installer acceptance.

## Build and release script discovery

- `tools/release/validate_release_environment.py --help`: PASS
- `tools/release/generate_release_artifacts.py --help`: PASS
- `tools/packaging/verify_desktop_core_bundle.py --help`: PASS with its pinned
  `pefile` build dependency
- `tools/packaging/generate_windows_assets.py --help`: PASS with its pinned
  `Pillow` build dependency
- `tools/packaging/phasenox_desktop_core.spec`: present
- `tools/packaging/installer/PHASENOX.iss`: present
- PowerShell syntax checks for the build, installer-validation, install, and
  repository-validation scripts: no parser errors
- Hard-coded old/new local checkout paths in active build/configuration files:
  `0`

The immutable Sprint 22 executable and installer were not rebuilt.

## README command validation

The documented canonical clone URL produced this fresh clone. The documented
source-install pattern and `phasenox --help` command both worked. No README
repository-finalization defect was found.

## Frozen candidate provenance

- Candidate source:
  `3adfbab5f5dec7e5c2237febb316bc6b89459e5e`
- PHASENOX executable SHA-256:
  `753da4c1336467b8a8fca6d7eb9ee9b7b2cbe1b3045466e1dafdd09e8fa80c48`
- Installer SHA-256:
  `a30d30a4b92b7060c9e93a230c4bb291e46168b70f5379e8dbeeb3370b2e59c0`

The candidate source remains an ancestor of canonical `main`. Post-candidate
changes are repository canonicalization, CI, tests, documentation, and
evidence metadata; no `phasenox/` shipping implementation, release dependency
profile, PyInstaller spec, installer source, or runtime resource changed.
Freeze and acceptance documents continue to reference the exact candidate
source and artifact hashes. Provenance is **VALID**.

## Remaining release boundary

- External Windows acceptance: **18 PENDING**
- Legal/signing: **3 PENDING**
- Public release: **NO-GO**
- GitHub migration blockers: **0**

G3 closes GitHub/repository finalization only. Public release remains blocked
by the explicitly separate external and legal/signing gates.

## Final conclusion

The canonical repository works from a fresh clone without the old repository
URL or checkout. Package installation, canonical CI-equivalent validation,
wheel and sdist creation, wheel isolation, Desktop developer startup,
protection, archive integrity, and frozen-candidate provenance all pass.

**GitHub finalization is complete and ready to close.**

