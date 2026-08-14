# NØISYNE V2 Execution Plan

Version: 2.0

Status: ACTIVE

Repository: `N0ises/NOISYNE`

---

## Purpose

This plan governs the V2 Perceptual Intelligence workstream. It extends the
frozen V1 backend without reopening the completed technical rename or allowing
Desktop, DAW-control, agent, voice or foundation-model work to drift into early
V2 sprints.

Actual code and the runtime capability registry are the source of capability
truth. Documentation lifecycle state and machine availability are separate:
implemented code may still be unavailable on a machine because a model,
service, corpus or dependency is absent.

---

## Verified Starting Point

| Area | Repository truth | Lifecycle note |
| --- | --- | --- |
| Identity | Distribution/namespace `noisyne`; repository `N0ises/NOISYNE` | Rename complete |
| V1 application | `noisyne.application.NoisyneService`; compatibility `SoundBrainService` | Production V1 facade |
| Product surface | `noisyne/cli.py`; canonical `noisyne` and legacy `soundbrain` commands | CLI production |
| Runtime capabilities | `noisyne/runtime/capabilities.py` | Authoritative runtime lifecycle metadata |
| Audio/DSP/engineering | Deterministic V1 analysis and recommendations | Production where registered |
| Optional CLAP | Implemented and verified; model is not bundled | Availability depends on local assets |
| RAG | Implemented with documented preflight issues | Not Production |
| LLM reasoning | Implemented; external/local endpoint required | Not Production by default |
| Workflow adapters | `noisyne/integration` deterministic file-export contracts | Implemented contracts; no DAW communication |
| Local API | No tracked `noisyne/api` package | Planned for Sprint 16 |
| Desktop V1 | Frozen release candidate on isolated `desktop-ui` branch | Exists; not part of this branch |
| V2 perceptual core | No validated V2 perceptual implementation | Planned |

Compatibility identifiers such as `brain`, `soundbrain`, `SoundBrainService`,
`SOUNDBRAIN_ROOT`, the `soundbrain` engine key and Chroma collection are retained
deliberately and are not rename debt.

---

## V2 Product Contract

V2 transforms measurements into perception-aware, context-aware, evidence-
linked recommendations:

```text
source audio + optional references + listener/genre/delivery context
    -> validated V1 measurements
    -> auditory/perceptual features
    -> perceived loudness and masking
    -> perceptual descriptors and playback profiles
    -> translation-risk prediction
    -> perceptual reference and mix intelligence
    -> evidence-linked reasoning with confidence
    -> non-destructive recommendation
```

Providers, UI frameworks and DAW-specific protocols must not leak into the
perceptual domain contracts. Deterministic outputs must remain available when
optional model-backed reasoning is unavailable.

V2 does not authorize automatic mixing, audio replacement, DAW session control,
plugin parameter writes, automation writes, voice functionality, agent
autonomy, or production ONNX adoption.

---

## Sprint Execution Order

| Sprint | Deliverable | Gate |
| ---: | --- | --- |
| 0 | Reconciled live roadmap, capability and architecture truth | Documentation matches code; no runtime changes |
| 1 | Perceptual domain contracts | Stable typed inputs, outputs, evidence and uncertainty |
| 2 | Auditory frontend | Deterministic, tested perceptual feature inputs |
| 3 | Perceived loudness | Validated loudness-perception output |
| 4 | Frequency masking | Validated masking evidence |
| 5 | Perceptual descriptors | Defined and evaluated descriptors |
| 6 | Playback profiles | Versioned reproduction profiles |
| 7 | Translation risk prediction | Evidence-linked risk output and calibration |
| 8 | Listener / genre / delivery context | Explicit context contracts and fallbacks |
| 9 | Perceptual reference intelligence | Perceptual comparisons without unsupported error claims |
| 10 | Perceptual mix intelligence | Perception-aware, non-destructive recommendations |
| 11 | Perceptual reasoning integration | Traceable observation-to-recommendation reasoning |
| 12 | Evaluation / scientific validation | Versioned dataset, metrics, baselines and limitations |
| 13 | Knowledge / memory / personalization integration | Controlled overrides with provenance |
| 14 | Performance baseline + ONNX benchmark spike | Evidence for adopt/defer decision; no assumed adoption |
| 15 | V2 NoisyneService / capability contract | Stable V2 application boundary |
| 16 | Local API + async job/progress contract | Versioned local API and cancellation/progress semantics |
| 17 | Desktop V2 integration | `NØISYNE Desktop -> V2ApplicationAdapter -> V2 backend` |
| 18 | Desktop identity / user-data compatibility | Migration-safe identity and paths |
| 19 | Desktop packaging / clean-machine candidate | Repeatable packaged candidate |
| 20 | Ableton launch bridge smoke integration | Launch/connect and health/version/status only |
| 21 | V2 regression / release hardening | Full deterministic regression and known limitations |
| 22 | V2 release candidate | Recorded validation evidence and release decision |

Do not start a later sprint before the current sprint's gate is met.

---

## Scientific Validation Requirements

Research design for perceptual capabilities must reference appropriate primary
standards and literature. The minimum anchors are:

| Anchor | Planned use |
| --- | --- |
| ISO 226 | Equal-loudness contour research and validation context |
| ISO 532-1 | Zwicker loudness methodology research and comparison |
| ITU-R BS.1770 | Programme loudness and true-peak measurement baseline |
| EBU R128 | Production/broadcast loudness and delivery context |

Referencing a standard is not a conformance claim. Conformance may be stated
only after the implementation, supported parameter range, fixtures, tolerance,
methodology and repeatable results have been reviewed and recorded.

Every new perceptual output must define units or scale, valid range, required
inputs, uncertainty/confidence semantics, failure behavior, versioning and an
evaluation method. Recommendations must preserve the evidence chain:
observation -> evidence -> reasoning -> confidence -> recommendation.

---

## Desktop and Ableton Integration Gates

Desktop V1 remains frozen and isolated until Sprint 17. V2 backend modules do
not import Desktop code. Desktop V2 consumes the backend through
`V2ApplicationAdapter`, after the V2 service and async operation contracts are
stable.

The Sprint 20 Ableton bridge is a late smoke integration only. It may load a
Max for Live surface/device, launch or connect to the local NØISYNE service and
show health/version/status. It must tolerate NØISYNE restarts and project
save/reopen and must never run heavy analysis on Ableton's real-time thread.

Full DAW read/control and user-confirmed or unattended actions belong to later
versions. Existing workflow adapters remain deterministic export contracts.

---

## Sprint 0 Completion Gate

- Live V2 roadmap, execution, capability, architecture, audio architecture and
  module-map documents agree with repository truth.
- V2 is Perceptual Intelligence and V3 is Autonomous Mixing.
- Desktop V1 is recorded as a frozen release candidate.
- DAW contracts are not presented as runtime DAW control.
- The canonical Sprint 0-22 order is recorded.
- Scientific anchors are recorded as future validation requirements only.
- No backend, persistence, Desktop or compatibility identifier changes occur.
