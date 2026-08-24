# PHASENØX Product and V2 Roadmap

Version: 2.0

Status: ACTIVE

Repository: `N0ises/PHASENOX`

Canonical distribution and Python namespace: `phasenox`

---

## Current Baseline

PHASENØX V1 is the frozen Professional Audio Intelligence release candidate.
Its backend and Desktop release-candidate work are complete and remain isolated
from V2 development. The V1 backend provides deterministic audio analysis,
engineering, reference, mix and plugin recommendations, reporting, evaluation,
workflow export contracts, a service facade and the CLI.

The V1 Desktop exists as a frozen release candidate on the isolated
`desktop-ui` branch. It is not a planned-but-unimplemented product surface, and
it is not part of the V2 backend branch.

The repository rename is complete. New code and active documentation use
PHASENØX/PHASENOX, `N0ises/PHASENOX` and `phasenox`. The legacy `brain` namespace,
`SoundBrainService`, `SOUNDBRAIN_ROOT`, `soundbrain` engine
alias and `soundbrain` Chroma collection remain intentional compatibility
contracts.

---

## Product Progression

### V1 — Professional Audio Intelligence

Measure, analyze, explain and recommend. V1 does not modify source audio and
does not control a DAW.

### V2 — Perceptual Intelligence

Move from objective measurement toward research-anchored estimates of human
perception:

```text
measurement
    -> perception
    -> context understanding
    -> translation prediction
    -> perceptual reference and mix intelligence
    -> evidence-linked reasoning
    -> recommendation
```

V2 includes an auditory frontend, perceived loudness, masking, perceptual
descriptors, playback profiles, translation-risk prediction, listener/genre/
delivery context and their integration into reference, mix and reasoning
workflows.

V2 is not an autonomous mixer. It must not perform unattended or destructive
actions.

### V3 — Autonomous Mixing and Deeper DAW-Aware Engineering

V3 may introduce user-approved processing proposals, deeper DAW awareness and
reversible mixing actions only after V2 recommendations are scientifically
validated and trustworthy.

### Later Versions

Advanced action/control, audio foundation-model research, generation and
autonomous-system work remain later-version concerns.

---

## Canonical V2 Sprint Order

| Sprint | Scope |
| ---: | --- |
| 0 | Roadmap / Capability Truth Reconciliation |
| 1 | Perceptual Domain Contracts |
| 2 | Auditory Frontend |
| 3 | Perceived Loudness |
| 4 | Frequency Masking |
| 5 | Perceptual Descriptors |
| 6 | Playback Profiles |
| 7 | Translation Risk Prediction |
| 8 | Listener / Genre / Delivery Context |
| 9 | Perceptual Reference Intelligence |
| 10 | Perceptual Mix Intelligence |
| 11 | Perceptual Reasoning Integration |
| 12 | Evaluation / Scientific Validation |
| 13 | Knowledge / Memory / Personalization Integration |
| 14 | Performance Baseline + ONNX Benchmark Spike |
| 15 | V2 PhasenoxV2Service / Capability Contract |
| 16 | Local API + Async Job / Progress Contract |
| 17 | Desktop V2 Integration |
| 18 | Desktop Identity / User-Data Compatibility |
| 19 | Desktop Packaging / Clean-Machine Candidate |
| 20 | Ableton Launch Bridge Smoke Integration |
| 21 | V2 Regression / Release Hardening |
| 22 | V2 Release Candidate |

Sprint 14 is a benchmark spike, not an authorization to adopt ONNX. Sprint 17
is the first Desktop V2 integration sprint; earlier V2 backend sprints must not
modify the frozen Desktop branch.

---

## V2 DAW and Ableton Boundary

The existing `phasenox.integration` adapters are implemented workflow export
contracts. They create deterministic JSON, text and Markdown files and do not
communicate with a DAW. Contract implementation is not runtime DAW availability.

Sprint 20 is limited to this smoke path:

```text
Ableton Live
    -> PHASENØX Max for Live device/surface
    -> launch or connect
    -> local PHASENØX service
    -> health / version / status handshake
```

Acceptance is limited to loading the surface/device, launch/connect behavior,
visible connection state, stable start/stop/restart behavior, project reopen
stability, and keeping heavy ML/audio analysis off Ableton's real-time audio
thread.

The following are explicitly outside V2: track manipulation, device or plugin
parameter changes, automation writes, session-wide control, automatic EQ,
automatic compression, autonomous mixing, unattended DAW actions and
destructive audio replacement.

---

## Scientific Direction and Validation Gates

V2 research and validation will use, at minimum:

- ISO 226 equal-loudness contours.
- ISO 532-1 Zwicker loudness methodology.
- ITU-R BS.1770 programme loudness and true-peak measurement.
- EBU R128 production and broadcast loudness context.

These are planned research and validation anchors. No current implementation
is claimed to conform to them until code, datasets, methodology and repeatable
acceptance evidence establish that claim.

---

## Definition of Success

- V1: a professional audio intelligence assistant.
- V2: a scientifically evaluated perceptual engineering assistant.
- V3: a human-controlled, reversible autonomous mixing system.
- Later: foundation-model and bounded autonomous audio-intelligence systems.
