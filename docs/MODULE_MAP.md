# NØISYNE V2 Module Map

Version: 2.0

Status: ACTIVE

Repository: `N0ises/NOISYNE`

Canonical package: `noisyne/`

---

## Identity and Compatibility

All implementation lives under `noisyne`. The top-level `brain` package is a
legacy import shim and must not receive duplicate implementations. The
`soundbrain` CLI, `SoundBrainService`, `SOUNDBRAIN_ROOT`, `soundbrain` engine
alias and `soundbrain` Chroma collection remain approved compatibility
contracts.

---

## Current Backend Modules

| Path | Ownership | Dependency boundary |
| --- | --- | --- |
| `noisyne/runtime/` | Model lifecycle, repository resolution, devices, loading, cache and runtime capability registry | Infrastructure/providers only; domain code does not load models directly |
| `noisyne/infrastructure/` | Configuration, provider plumbing and infrastructure concerns | No UI ownership |
| `noisyne/audio/` | Audio I/O, measurements, context, embeddings, comparison, V1 mix/plugin intelligence and audio-domain models | May use runtime; does not depend on Desktop/DAW protocols |
| `noisyne/engineering/` and `noisyne/audio/engineer/` | Existing rule/engineering analysis paths | Consume audio-domain evidence |
| `noisyne/reference/` | Reference comparison, reasoning, pipeline and reports | Consumes analysis/context; no DAW control |
| `noisyne/knowledge/` | Structured knowledge loading, validation, registry and resolution | Domain knowledge contracts |
| `noisyne/rag/` | Retrieval, ingestion, vector database and reranking | Optional model/data availability |
| `noisyne/memory/` | Memory/profile models, resolution and vector storage | Persistence identifiers remain compatibility-sensitive |
| `noisyne/providers/` | Replaceable AI provider contracts, registry, factory and services | Heavy/remote providers remain optional |
| `noisyne/reasoning/` and `noisyne/prompt/` | Structured reasoning, prompts, parsing and guards | Depend on contracts, not UI |
| `noisyne/report/` | Report models, building, validation and export | Consumes domain results |
| `noisyne/evaluation/` | Metrics, scoring, benchmarks and evaluation reports | Tests domain/application outputs |
| `noisyne/perception/` | V2 perceptual contracts plus the Sprint 2 auditory frontend | Root contracts remain lightweight; `auditory.py` uses NumPy only and has no providers, UI, API or DAW dependencies |
| `noisyne/application/` | Canonical application facade and use-case orchestration | May compose domain modules; no Desktop imports |
| `noisyne/orchestration/` and `noisyne/pipeline/` | Implemented alternate orchestration/stage infrastructure | Not the frozen V1 CLI production path |
| `noisyne/integration/` | Deterministic DAW-named workflow export contracts | No live DAW communication or control |
| `noisyne/cli.py` | Canonical command-line surface | Calls application services |

`noisyne.application.noisyne_service.NoisyneService` is the canonical V1
facade. `noisyne.application.soundbrain_service.SoundBrainService` is retained
as a compatibility alias.

---

## V2 Planned Module Boundaries

Sprint 1 established `noisyne/perception/` as the canonical package for V2
perceptual domain contracts. The first top-level contract schema version is
`1.0.0`. Sprint 2 adds the deterministic, channel-preserving runtime in
`noisyne/perception/auditory.py` and its minimal JSON-safe metadata contracts in
`noisyne/perception/auditory_contracts.py`. The Sprint 1 schema remains
unchanged; loudness, masking, descriptor, playback and translation algorithms
remain unimplemented until their owning sprints.

The package makes no ISO 226, ISO 532-1, ITU-R BS.1770 or EBU R128 conformance
claim. Those standards remain future research and validation anchors. The
runtime registry records the executable auditory frontend as Implemented while
the broader V2 Perceptual Core remains Planned.

The planned ownership boundaries are:

- Perceptual domain contracts — shared types for evidence, confidence,
  uncertainty and versioned model output.
- Auditory frontend — deterministic inputs for perceptual models.
- Loudness, masking and descriptors — independently testable perceptual
  components.
- Playback/translation context — versioned playback profiles and calibrated
  risk output.
- Perceptual reference/mix/reasoning integration — adapters over existing V1
  contracts rather than duplicate pipelines.
- V2 application contract — `NoisyneService` boundary in Sprint 15.
- Local API/async operations — Sprint 16, after the service contract is stable.

No algorithm or integration directories should be created for these areas
before their owning sprint.

---

## Desktop Boundary

The V1 Desktop is frozen on the isolated `desktop-ui` branch. There is no
tracked Desktop implementation in the `v2-development` baseline. Desktop V2
integration starts in Sprint 17:

```text
NØISYNE Desktop -> V2ApplicationAdapter -> NØISYNE V2 backend
```

Desktop code must not be moved into backend domain modules, and backend modules
must not import a UI toolkit.

---

## DAW Boundary

`noisyne/integration` owns file-export contracts only. The Sprint 20 Ableton
launch bridge is a separate planned integration limited to launch/connect and
health/version/status. DAW session read/control, parameter changes, automation
writes and autonomous actions are future capabilities and must not be placed in
the current adapters.

---

## Final Rules

- One canonical implementation per responsibility; compatibility packages only
  delegate.
- Runtime owns model lifecycle; application services orchestrate use cases.
- Domain modules do not depend on Desktop, API transports or DAW protocols.
- Capability lifecycle and machine availability are separate contracts.
- Historical documents may retain former SoundBrain naming; current modules and
  new code use NØISYNE/NOISYNE and `noisyne`.
