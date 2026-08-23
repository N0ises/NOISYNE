# PHASENOX R9 Full Regression Report

## Verdict

**PASS for the R1-R8 technical rename candidate, with one known inherited
non-rename test mismatch.** No regression attributable to the namespace,
identity, packaging/CLI, runtime-root, persistence-safety, cleanup/freeze, or
brand-resource work was found.

The standard full-suite run completed without a native-process crash and
reported 1,060 passes and three failures. Two failures passed when their
persistence module was rerun in a clean process and are suite-order/Windows
handle-isolation effects. The remaining playback-transfer assertion also fails
in isolation, but both the implementation message and the test expectation are
unchanged from the parent of R1 (`99b1b11de83908723c778538814e130b565d163f`),
so it is not a rename regression. R9 intentionally does not change this
unrelated behavior.

## Scope and pre-flight

- Repository: `N0ises/NOISYNE`
- Branch: `v2-development`
- Validated HEAD: `1cfb1162340fb2334a7774f13e371cc101e4c611`
- Tracked worktree at start: clean
- Known untracked files, left untouched:
  - `docs/Desktop-Ui-Roadmap-Sprint.md`
  - `docs/Desktop-Ui-Roadmap-v1.2.md`
- Protected-roadmap aggregate SHA-256:
  `43194A03474C55B2796923D72C9686AB2BCC0D53AAB078485307ABE32DAC0905`
  (2 files, 83,539 bytes)
- R10 and Desktop Sprint 17 were not started.

## Environment

| Item | Value |
| --- | --- |
| OS | Windows 11 `10.0.26200` |
| Architecture | AMD64, 64-bit; Intel64 Family 6 Model 154 |
| Python | 3.12.10 (`E:\Build\NOISYNE\venv\Scripts\python.exe`) |
| pytest | 9.1.1 |
| chromadb | 1.5.9 |
| setuptools | 81.0.0 |
| wheel | 0.47.0 |
| build | 1.5.0 |
| NumPy | 2.3.5 |
| torch | 2.11.0+cu126 |
| transformers | 4.57.6 |
| PySide6 | 6.11.1 |
| PyYAML | 6.0.3 |
| onnxruntime | Not installed in the validation environment |

The dependency snapshot contained 293 lines. Its SHA-256 was
`9E99CBA5566DE12B4CE070FB1CE57E04556ECD49CE394E594E8224258D6AAC29`.
The repository contained 140 recursively discovered test files.

## Test matrix

### Standard broad suite

`python -m pytest -q` completed normally:

- **1,060 passed**
- **3 failed**
- **0 skipped/deselected reported**
- 2 librosa warnings in `test_key_analysis.py`
- elapsed: 90.17 seconds

Failure disposition:

1. `test_inventory_discovers_fake_stores_without_modifying_them` encountered a
   Windows `PermissionError` while renaming a temporary fake `index.db`.
   `tests/test_persistence_safety.py` passed 9/9 in a clean process.
2. `test_persistence_package_import_does_not_initialize_store_clients` observed
   `phasenox.rag.vectordb` already in `sys.modules` after earlier full-suite
   collection. The same clean-process persistence run passed 9/9.
3. `test_amplitude_conversion_rejects_overflow_and_underflow` expected
   `not representable as a positive float64`, while the current NumPy/platform
   branch raised `magnitude-to-amplitude conversion must produce finite,
   positive values`. It fails independently (29 other playback-transfer tests
   pass). Git history confirms the mismatch predates R1 and R1 only moved the
   package namespace.

### Required logical suites

Each logical group was rerun independently where useful to avoid cross-suite
native-library state:

| Area | Result |
| --- | ---: |
| Identity, release alignment, freeze, compatibility, branding, distribution | 58 passed |
| Application/service including Sprint 15 | 38 passed |
| Sprint 16 scheduler/jobs | 27 passed |
| RAG collection and preflight | 13 passed |
| Memory/vector | 27 passed |
| Persistence safety | 9 passed |
| Audio pipeline/index/search/key/auditory | 94 passed, 2 warnings |
| Reference intelligence/pipeline/reasoning | 60 passed |
| Perception/reasoning excluding the inherited playback assertion | 346 passed |
| Evaluation/scientific validation | 101 passed |
| Playback transfer | 29 passed, 1 inherited non-rename failure |

Named sprint coverage was also confirmed: Sprint 12 (75 passed), Sprint 13
(91 passed), Sprint 14 (29 passed), Sprint 15 application contract (19 passed),
Sprint 15.5 ONNX/GPU boundary (18 passed), and Sprint 16 (27 passed). These
counts overlap the logical groups and are not added to the full-suite total.

### Native crash note

The standard full suite did **not** crash. One combined identity subprocess run
later encountered the known Windows access violation at
`tests/test_phasenox_release_alignment.py:104`, after native dependencies had
already been loaded in the same process. Every identity file passed when run in
its own Python process (58 total assertions). This is recorded separately and
was not treated as a rename assertion failure.

## Imports and compatibility

A fresh source process from an arbitrary temporary working directory verified:

- `import phasenox`
- `import phasenox.application`
- `PhasenoxService` and `PhasenoxV2Service`
- exact `NoisyneService` and `SoundBrainService` aliases
- `import brain`
- representative `brain.reference.models` identity with its canonical module

After these lightweight imports, `torch`, `transformers`, `onnxruntime`, and all
`PySide6` modules were absent from `sys.modules`. The canonical and legacy class
objects were identical; there are no duplicate service implementations.

## Root and configuration validation

Source-checkout and installed-wheel probes confirmed the precedence:

`PHASENOX_ROOT` > `NOISYNE_ROOT` > `SOUNDBRAIN_ROOT` > automatic discovery.

Conflicting canonical and legacy roots produce the existing `RuntimeWarning`
and the canonical root wins. Repository-CWD discovery returned the repository
root. Arbitrary-CWD installed discovery returned the fresh environment's
`site-packages` directory. `audio.yaml`, `models.yaml`, and `runtime.yaml`
resolved through package resources in source and installed contexts, and their
parsed semantics matched. No storage-layout policy changed.

## Persistence safety

- The persistence safety suite passed 9/9 in a clean process using temporary
  fake stores.
- Inventory remained read-only.
- Manifest output remained deterministic.
- Backup remained planning-only.
- Migration locking remained unintegrated from production writers.
- RAG and memory collection defaults remained `soundbrain`.
- Engine compatibility keys `noisyne` and `soundbrain` resolved to the same
  registered engine.
- No production data was moved, migrated, or intentionally opened for mutation.

The tracked repository `data/index.db` remains a repository finding only:
12,288 bytes, SHA-256
`BFBB1FB226EF64092289D000297E2765A55970D74FF292F794919E05FCB7F21D`.
It is absent from both built artifacts.

## Brand resources

Source and installed-package checks resolved all 14 production brand assets
without a repository-CWD or Qt dependency. The frozen constants are:

- `DISPLAY_NAME == "PHASENØX"`
- `ASCII_NAME == "PHASENOX"`
- `WORDMARK_RHYTHM == "PHASE   NØX"`

Raw PNG hashes and newline-normalized SVG hashes matched between source and the
installed package. Root design/source assets were not included in either
distribution artifact.

## Clean build and artifact inspection

The build ran from a clean `git archive` of validated HEAD with
`python -m build --no-isolation --wheel --sdist` and succeeded. Existing
setuptools license-deprecation warnings were informational.

| Artifact | Size | SHA-256 |
| --- | ---: | --- |
| `phasenox-1.0.0-py3-none-any.whl` | 479,496 bytes | `BEE8AA7E30FCB2878D8FF9FACB90107D0642BD04D3CAF55948A18DF4FE842AB2` |
| `phasenox-1.0.0.tar.gz` | 470,604 bytes | `12D3822BEC7066C9F4D043CE4212538F9964C3DAB5AC398D008EE80D6F32C3EE` |

The wheel contains 417 entries: 409 under `phasenox`, all 14 production brand
assets, all three YAML configurations, and only `brain/__init__.py` for the
compatibility namespace. The sdist contains 498 entries with the same 409
package entries, 14 production assets, three configurations, and the same
single `brain` shim. Neither contains a `noisyne` package tree, databases,
Chroma/vector data, caches, logs, reports, Desktop UI source, root design
sources, secrets, tokens, or current-workstation absolute paths.

The sdist contains one intentional historical-looking drive literal in a
negative test assertion:
`tests/test_phasenox_identity.py` asserts that `E:\SoundBrain` is absent from
current-facing source. It is test text, not a path to this checkout or embedded
workstation data.

## Isolated installation and CLI

A brand-new temporary venv received the wheel with `--no-deps`, followed by the
cached PyYAML dependency needed for configuration parsing. From an arbitrary
directory outside the repository, with no repository path on `sys.path`, it
verified canonical imports, `brain`, service aliases, config resources, brand
resources, automatic root discovery, and semantic source/install parity.

A second temporary environment installed the wheel and reused the already
recorded project dependency set solely for dependency-backed engine/persistence
imports. `phasenox` itself was confirmed to load from that temporary
environment's `site-packages`, not the checkout.

Console-script metadata and executable inspection showed exactly one project
entry point: `phasenox`. `phasenox --help` returned zero and contained
`PHASENØX`; `noisyne` and `soundbrain` executables were absent. On Windows the
help bytes use the active CP1252 console encoding; source and installed output
were byte-identical.

## Source/install parity

The following contracts matched semantically:

- distribution name/version and canonical modules
- canonical service classes and all approved aliases
- `brain` module-object compatibility
- only the `phasenox` CLI entry point
- parsed YAML configuration
- all 14 production brand resources and identity constants
- `soundbrain` persistence defaults
- `noisyne`/`soundbrain` engine aliases
- frozen serialized `noisyne.*` identifier allowlist

Raw text hashes for YAML/SVG files differed only because the clean archive used
LF while the Windows checkout used CRLF. Parsed YAML and normalized SVG content
matched, so there was no semantic drift.

## Quality gates

The 12 Python files touched from R6.4 through R8 were used as the relevant
baseline-delta set:

- Ruff: passed
- Black `--check`: passed; 12 files unchanged
- `compileall phasenox brain tests`: passed
- `git diff --check`: passed

No new formatting or lint debt was introduced by the rename/brand sequence.

## Final legacy census

The tracked-text census (excluding this report from self-counting) contains 868
approved legacy-token occurrences:

| Token | Count |
| --- | ---: |
| `noisyne` | 257 |
| `NOISYNE` | 89 |
| `Noisyne` | 66 |
| `soundbrain` | 198 |
| `SoundBrain` | 209 |
| `SOUNDBRAIN` | 49 |
| **Total** | **868** |

Classification remains **A = 405, B = 0, C = 0, D = 463**. The 12 tracked
legacy filenames are the two live service compatibility modules, one focused
freeze test, and nine approved historical documents. No stale current-facing or
dead identity reappeared.

## Repository hygiene and final scope

- No persistence database or user data leaked into wheel/sdist.
- No current local absolute checkout path, secret, token, cache, log, report,
  Desktop UI source, or unintended workstation data leaked into artifacts.
- No production, test, persistence, Desktop UI, or asset file was changed by
  R9.
- The two pre-existing untracked Desktop UI roadmaps remain untouched.
- R10 was not started.

R9 therefore validates the PHASENOX rename candidate while preserving the
pre-existing playback assertion mismatch as an explicit, non-rename baseline
finding rather than expanding this sprint's scope.
