# NØISYNE Technical Rename Freeze

Status: Final technical rename freeze
Approved pre-Phase 6 baseline: `bf5ac42128ded14159b7952d916729206c3d3174`
Approved Phase 6 freeze commit: `eb3d7ce7c5044b82b92fc5a1a8bda84df56bb9ce`

## Technical identity matrix

| Contract | Canonical identity | Retained compatibility |
|---|---|---|
| Display | NØISYNE | — |
| ASCII | NOISYNE | — |
| Distribution | `phasenox` | — |
| Python namespace | `phasenox` | `brain` |
| CLI | `phasenox` | — |
| Service | `PhasenoxService` | `NoisyneService`, `SoundBrainService` |
| Application root environment | `NOISYNE_ROOT` | `SOUNDBRAIN_ROOT` |
| Engine key | `noisyne` | `soundbrain` |
| Persisted Chroma collection | `soundbrain` | Stable; intentionally unchanged |
| Repository | `N0ises/NOISYNE` | Rename complete |

Environment precedence is `NOISYNE_ROOT` → `SOUNDBRAIN_ROOT` → automatic
structural detection.

## Phase record

- Phase 0: preflight and rename inventory
- Phase 1: compatibility infrastructure
- Phase 2: distribution identity
- Phase 3: Python namespace migration
- Phase 4: technical IDs and persistence compatibility
- Phase 5: packaging, documentation, and CI alignment
- Phase 6: repository readiness and final technical-identity freeze

Technical Rename Phases 0–6: **COMPLETE**

## Repository status

- Repository rename: **COMPLETE**
- Canonical repository: `N0ises/NOISYNE`
- Canonical origin: `https://github.com/N0ises/NOISYNE.git`
- Default branch: `main`

The canonical origin resolves directly to the renamed repository and no longer
relies on the legacy repository redirect.

## Intentional freezes and exclusions

- `brain`, `NoisyneService`, `SoundBrainService`, and `SOUNDBRAIN_ROOT` remain
  supported compatibility contracts.
- The persisted Chroma collection remains `soundbrain`; no data migration or
  collection rename is authorized.
- Desktop code, application ID, and Desktop user-data paths remain frozen.
- Historical reports, archived roadmaps, artifact names, and prior URLs remain
  unchanged.
- No release, tag, package publication, ownership transfer, or repository
  creation was performed.
- No ONNX, Voice, Agent behavior, or V2 feature work is included.

## Validation note

Windows test runs can terminate natively while importing PyArrow through the
scientific/transformer dependency chain. Affected tail suites must be rerun in
isolated processes and reported; the native termination must not be hidden.
