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
| `noisyne/perception/` | V2 perceptual contracts, auditory frontend, calibrated loudness, relative simultaneous masking, descriptors, explicit playback transfer, and policy-conditioned translation evidence | Root contracts remain lightweight; numerical runtimes use existing audio/NumPy dependencies and have no providers, UI, API or DAW dependencies |
| `noisyne/application/` | Canonical application facade and use-case orchestration | May compose domain modules; no Desktop imports |
| `noisyne/orchestration/` and `noisyne/pipeline/` | Implemented alternate orchestration/stage infrastructure | Not the frozen V1 CLI production path |
| `noisyne/integration/` | Deterministic DAW-named workflow export contracts | No live DAW communication or control |
| `noisyne/cli.py` | Canonical command-line surface | Calls application services |

`noisyne.application.noisyne_service.PhasenoxService` is the canonical V1
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

Sprint 3 adds `noisyne/perception/loudness_contracts.py` and
`noisyne/perception/loudness.py`. This is an explicit digital-to-pascal
calibration, channel/presentation and evidence foundation only. The complete
ISO 532-3:2023 algorithm, companion source and verification fixtures are not
available in the development environment, so the runtime returns
`INSUFFICIENT_EVIDENCE` and produces no sones, phons or psychoacoustic loudness.
The frozen Sprint 1 schema and Sprint 2 frontend behavior remain unchanged.

Sprint 4 adds `noisyne/perception/masking_contracts.py` and
`noisyne/perception/masking.py`. It computes pairwise, common-gain relative
excitation-margin evidence using a fixed Moore-Glasberg 1983 moderate-level
roex(p) reference over Sprint 2's linear-Hz spectra. It produces no absolute
masking threshold or `MaskingEvent`; full mixes return `INSUFFICIENT_EVIDENCE`
because source decomposition is unavailable. Sprint 1 transport, Sprint 2
frontend and Sprint 3 calibration behavior remain unchanged.

Sprint 5 adds `noisyne/perception/descriptor_contracts.py` and
`noisyne/perception/descriptors.py`. The contracts classify standardized
psychoacoustic quantities, research correlates and informal engineering terms.
Only an uncalibrated power-spectral-centroid brightness correlate is executable;
sharpness, roughness, fluctuation strength and tonality remain unavailable until
their complete standard prerequisites and independent validation exist, while
warmth, harshness, punch, density and width receive no invented scores. Runtime
curves remain outside transport contracts. Sprint 1-4 behavior is unchanged.

Sprint 6 adds `noisyne/perception/transfer_contracts.py` and
`noisyne/perception/transfer.py`. It separates playback context from explicit,
versioned transfer evidence. Tabulated magnitude evidence supports bounded
log-frequency/linear-dB interpolation but cannot be transformed into audio or
used to invent phase. Executable transfer requires a caller-supplied real FIR
at the exact audio sample rate and performs channel-preserving full linear
convolution without resampling, clipping, normalization, downmix or nonlinear
device simulation. No generic phone, laptop, speaker, headphone or room preset
is claimed. Sprint 1-5 behavior is unchanged.

Sprint 7 adds `noisyne/perception/translation_contracts.py` and
`noisyne/perception/translation.py`. It compares an original signal with the
complete output of an explicit Sprint 6 FIR, including its convolution tail.
Objective evidence covers the Sprint 5 brightness correlate, Sprint 2
channel-by-ERB power, summed digital programme energy, and sample-peak/full-
scale state. Risk is emitted only when a versioned, provenance-backed policy
provides dimension- and unit-matched criteria; each result is a boolean
threshold outcome, never a probability, normalized score or aggregate risk.
No PEAQ, loudness/LRA delta, full-mix masking attribution, source separation or
device-category inference is implemented. Sprint 1-6 behavior is unchanged.

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
- V2 application contract — `PhasenoxV2Service` boundary in Sprint 15.
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
