# NØISYNE Architecture Decisions

Version: 2.1

Status: ACTIVE

---

## Purpose

This document records accepted long-term architectural decisions for NØISYNE.
Historical compatibility identifiers remain governed by the technical rename
freeze.

---

## Decision 001 — Project Identity

NØISYNE is an Audio Intelligence System, distributed as `phasenox` from
`N0ises/NOISYNE`. It is not merely an audio analyzer or mixing assistant.

Status: Accepted

## Decision 002 — Perception Before Measurement Alone

Recommendations must account for human perception; objective measurements
remain preserved as auditable evidence and are never silently replaced.

Status: Accepted

## Decision 003 — Understanding Before Recommendation

Recommendations consider available audio context, genre, artistic intent,
references, perceptual evidence and engineering knowledge. Missing context is
reported rather than invented.

Status: Accepted

## Decision 004 — Explainable AI

Every recommendation follows observation -> evidence -> reasoning -> confidence
-> recommendation.

Status: Accepted

## Decision 005 — Clean Architecture

Business and perceptual domain logic remain independent from providers,
libraries, UI frameworks and DAW-specific protocols.

Status: Accepted

## Decision 006 — Provider Pattern

Providers are replaceable and optional. Business logic depends on provider
contracts, and provider/model unavailability degrades gracefully.

Status: Accepted

## Decision 007 — Dependency Injection

Dependencies are injected. Hidden dependencies are forbidden.

Status: Accepted

## Decision 008 — Generic Reasoning Engine

There is one reasoning architecture. Different workflows use different prompt
builders and typed contexts rather than duplicate reasoning engines.

Status: Accepted

## Decision 009 — Multimodal Direction

Audio and text are current architectural inputs. Images, voice, MIDI and DAW
sessions are long-term target modalities; listing them does not claim a current
runtime capability.

Status: Accepted

## Decision 010 — Trusted Knowledge

Engineering intelligence should use trusted, attributable professional
knowledge and primary standards/research where applicable.

Status: Accepted

## Decision 011 — Agent Architecture

Specialized agents are a later-version direction. Agent classes or concepts in
the repository do not make autonomous agents a V2 product capability.

Status: Planned

## Decision 012 — Audio Memory

Persistent memory is a first-class architectural component. Personalization
must use explicit provenance and controlled override rules.

Status: Accepted

## Decision 013 — Automation

Reasoning and safety validation precede automation. V2 recommendations are
non-destructive; deeper action/control belongs to later versions.

Status: Accepted

## Decision 014 — Human-Centered AI

Humans remain in control of creative decisions. Unattended destructive actions
are forbidden.

Status: Accepted

## Decision 015 — Product Progression

```text
V1 -> Professional Audio Intelligence
V2 -> Perceptual Intelligence
V3 -> Autonomous Mixing / deeper DAW-aware engineering
V4+ -> Foundation-model, advanced action/control and autonomous-system work
```

Status: Accepted

## Decision 016 — Capability Truth

Actual runtime code and `noisyne/runtime/capabilities.py` determine present
capability truth. Lifecycle state and current-machine availability are separate.
A module, adapter or contract does not by itself establish runtime availability.

Status: Accepted

## Decision 017 — Desktop Isolation

The frozen V1 Desktop remains isolated from V2 backend development. Desktop V2
integrates only after stable V2 service and async-operation contracts through:

```text
NØISYNE Desktop -> V2ApplicationAdapter -> NØISYNE V2 backend
```

Status: Accepted

## Decision 018 — V2 DAW Boundary

Existing DAW-named adapters are deterministic export contracts, not live DAW
integrations. V2 permits only a late Ableton launch/connect smoke bridge with a
health/version/status handshake. Session read/control, parameter or automation
writes and autonomous mixing are outside V2.

Status: Accepted

## Decision 019 — Scientific Claims

ISO 226, ISO 532-1, ITU-R BS.1770 and EBU R128 are minimum planned validation
anchors for relevant V2 work. Referencing them is not a conformance claim;
conformance requires reviewed scope, implementation, fixtures, tolerances and
repeatable evidence.

Status: Accepted

---

## Final Rule

Architecture defines intended boundaries; repository code and runtime metadata
define current capability truth. A conflict must be documented and reviewed
before either architecture or implementation is changed.
