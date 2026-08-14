# NØISYNE Technical Rename Freeze

Status: Phase 6 review candidate
Approved pre-Phase 6 baseline: `bf5ac42128ded14159b7952d916729206c3d3174`

## Technical identity matrix

| Contract | Canonical identity | Retained compatibility |
|---|---|---|
| Display | NØISYNE | — |
| ASCII | NOISYNE | — |
| Distribution | `noisyne` | — |
| Python namespace | `noisyne` | `brain` |
| CLI | `noisyne` | `soundbrain` |
| Service | `NoisyneService` | `SoundBrainService` |
| Application root environment | `NOISYNE_ROOT` | `SOUNDBRAIN_ROOT` |
| Engine key | `noisyne` | `soundbrain` |
| Persisted Chroma collection | `soundbrain` | Stable; intentionally unchanged |
| Repository | Target: `N0ises/NOISYNE` | Current: `N0ises/SoundBrain` |

Environment precedence is `NOISYNE_ROOT` → `SOUNDBRAIN_ROOT` → automatic
structural detection.

## Phase record

- Phase 0: preflight and rename inventory
- Phase 1: compatibility infrastructure
- Phase 2: distribution identity
- Phase 3: Python namespace migration
- Phase 4: technical IDs and persistence compatibility
- Phase 5: packaging, documentation, and CI alignment
- Phase 6: repository readiness and final technical-identity freeze candidate

The Phase 6 commit is the commit containing this document; its final SHA is
reported with the review candidate because a commit cannot contain its own SHA.

## Repository status

The GitHub repository has **not** been renamed. The configured local `origin`
remains `https://github.com/HamidCooper7/SoundBrain.git`, which GitHub currently
redirects to `N0ises/SoundBrain`. Redirect behavior is transitional and is not
the intended permanent configuration.

After explicit Phase 6 approval, the repository owner should:

1. Reconfirm permissions and that `N0ises/NOISYNE` is available.
2. Rename `N0ises/SoundBrain` to `N0ises/NOISYNE` in GitHub.
3. Verify the canonical URL and the default and protected branches immediately.
4. Update `origin` to `https://github.com/N0ises/NOISYNE.git`.
5. Update only current repository links/status text; preserve historical URLs.
6. Rerun package, fresh-install, CLI, exporter, and regression validation.

## Intentional freezes and exclusions

- `brain`, `soundbrain`, `SoundBrainService`, and `SOUNDBRAIN_ROOT` remain
  supported compatibility contracts.
- The persisted Chroma collection remains `soundbrain`; no data migration or
  collection rename is authorized.
- Desktop code, application ID, and Desktop user-data paths remain frozen.
- Historical reports, archived roadmaps, artifact names, and prior URLs remain
  unchanged.
- No repository rename, remote change, release, tag, or package publication is
  part of this candidate.
- No ONNX, Voice, Agent behavior, or V2 feature work is included.

## Validation note

Windows test runs can terminate natively while importing PyArrow through the
scientific/transformer dependency chain. Affected tail suites must be rerun in
isolated processes and reported; the native termination must not be hidden.
