# PHASENØX V2 Architecture

Version: 2.0

Status: ACTIVE

---

## System Boundary

PHASENØX is an Audio Intelligence System. The V2 workstream adds Perceptual
Intelligence to the frozen V1 Professional Audio Intelligence backend. V2
estimates perception and translation risk, links conclusions to evidence and
returns non-destructive recommendations. Autonomous mixing is V3, not V2.

The canonical codebase is `N0ises/NOISYNE`, distributed as `phasenox` with the
`phasenox` Python namespace. Approved legacy identifiers remain compatibility
contracts and are not alternate implementations.

---

## Layered Architecture

### Layer 0 — Infrastructure

Configuration, logging, dependency injection, model repository, device
selection, lazy loading and runtime cache. Domain layers must not own model
loading or external provider setup.

### Layer 1 — Measurement and Auditory Frontend

V1 audio I/O and deterministic DSP measurements feed a versioned V2 auditory
frontend. Raw audio and objective measurements remain preserved as evidence.

### Layer 2 — Perception and Context Understanding

V2 estimates perceived loudness, frequency masking, perceptual descriptors,
playback-profile effects and translation risk. Listener, genre, artistic intent
and delivery context qualify those estimates; missing context must produce an
explicit fallback or uncertainty, not an invented fact.

### Layer 3 — Reference and Mix Intelligence

Perceptual evidence augments the existing V1 comparison, root-cause, priority
and recommendation contracts. Numerical difference alone is not an error.

### Layer 4 — Reasoning

Deterministic rules, knowledge, memory and optional model-backed reasoning form
an auditable chain:

```text
observation -> evidence -> reasoning -> confidence -> recommendation
```

Optional provider failure must not invalidate deterministic output.

### Layer 5 — Application Boundary

The V2 `PhasenoxV2Service` capability contract was introduced in Sprint 15. The
local API and asynchronous job/progress contract follow in Sprint 16. Domain
models do not depend on API, UI or DAW-specific types.

### Later Action and Creation Layers

DAW session read/control, plugin or automation writes, automatic processing,
generation, voice and autonomous agents are later-version capabilities. Their
conceptual position in the architecture does not imply current implementation
or availability.

---

## Canonical V2 Data Flow

```text
audio + optional references + context
    -> V1 validation and measurements
    -> V2 auditory frontend
    -> perceived loudness / masking / descriptors
    -> playback and translation-risk models
    -> perceptual reference and mix intelligence
    -> evidence-linked reasoning and confidence
    -> non-destructive recommendation/report
```

Each stage uses typed, versioned contracts and records whether it ran, skipped
or failed. Lifecycle status and current-machine availability remain separate.

---

## Desktop Boundary

Desktop V1 is a frozen release candidate on the isolated `desktop-ui` branch.
No tracked Desktop implementation belongs to the V2 backend baseline. Desktop
V2 integration begins only in Sprint 17 and retains this boundary:

```text
PHASENØX Desktop
    -> V2ApplicationAdapter
    -> PHASENØX V2 backend
```

The adapter shields the Desktop from backend domain evolution and binds only to
the stable service/API and async operation contracts established in Sprints
15-16.

---

## DAW and Ableton Boundary

The current `phasenox.integration` package owns implemented deterministic export
contracts. It does not connect to, read from or control any DAW.

Sprint 20 may add only an Ableton launch/connect smoke bridge and a local
health/version/status handshake. It must remain outside Ableton's real-time
audio thread and tolerate PHASENØX start/stop/restart and project save/reopen.
Track manipulation, parameter changes, automation writes, session control and
autonomous mixing are outside V2.

---

## Scientific Architecture Constraints

V2 methodology and evaluation must be anchored in primary research and, at
minimum, ISO 226, ISO 532-1, ITU-R BS.1770 and EBU R128. These references are
validation targets, not claims that the current code conforms.

Perceptual contracts must expose scale/units, valid range, evidence,
uncertainty, required context, model/method version and failure semantics.

---

## Current Capability Boundary

- Production V1 deterministic paths: audio loading, DSP, context, engineering,
  reference comparison, mix/plugin recommendations, reports and service facade.
- Optional/incomplete paths retain their runtime registry states and require
  separate availability checks.
- Planned V2: the validated perceptual core and integrations in the canonical
  Sprint 1-22 sequence.
- Future/V3+: autonomous mixing, deeper DAW control, action and creation.
