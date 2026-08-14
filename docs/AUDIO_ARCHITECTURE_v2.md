# NØISYNE V2 Audio Architecture

Version: 2.0

Status: ACTIVE

---

## Purpose

The V2 audio architecture extends NØISYNE's frozen V1 measurement pipeline with
research-anchored perceptual modeling. It predicts how audio may be perceived
and translated across playback contexts, then produces evidence-linked,
non-destructive recommendations. It does not process source audio or control a
DAW.

---

## Processing Pipeline

```text
Audio input
    -> validation and canonical AudioData
    -> deterministic V1 measurement
    -> V2 auditory frontend
    -> perceived loudness and masking
    -> perceptual descriptors
    -> playback/listener/genre/delivery context
    -> translation-risk prediction
    -> perceptual reference and mix intelligence
    -> evidence-linked reasoning
    -> report and recommendation
```

The original measurements, context inputs, method versions and uncertainty must
remain available for audit. A later stage may enrich evidence but must not
silently replace or relabel an objective measurement.

---

## V1 Measurement Baseline

The current backend includes audio loading/validation and metrics such as tempo,
key, pitch, LUFS, peak, RMS, crest factor, dynamic range, stereo width, phase,
MFCC, chroma, spectral centroid/bandwidth/contrast/flatness/rolloff, zero-
crossing rate and onsets.

These are objective or algorithmic measurements. Their existence does not mean
V2 perceptual loudness, masking, descriptor or translation models are already
implemented.

Supported file behavior is determined by the configured SoundFile/librosa
backend and installed codecs. Stems, multitrack sessions, live streams and DAW
sessions must not be claimed as available merely because they appear in a
future architecture.

---

## V2 Perceptual Components

### Auditory Frontend — Sprint 2

Produces stable, versioned inputs for perceptual models from validated audio.
Its sampling, windowing, channel, level and boundary behavior must be explicit.

### Perceived Loudness — Sprint 3

Estimates perceptual loudness without conflating that estimate with the existing
LUFS measurement. Units/scales, calibration, supported signal conditions and
uncertainty must be defined.

### Frequency Masking — Sprint 4

Produces frequency/time-local masking evidence and confidence. It must not label
intentional overlap as a defect without musical and delivery context.

### Perceptual Descriptors — Sprint 5

Defines testable descriptors such as brightness, warmth, harshness, punch and
width perception. Each descriptor needs an operational definition, range,
evidence and validation method before capability promotion.

### Playback Profiles — Sprint 6

Represents versioned reproduction contexts. Profiles are analysis inputs, not
claims that NØISYNE emulates every physical playback system.

### Translation Risk — Sprint 7

Predicts a calibrated risk with contributing evidence, target profile and
uncertainty. It is not a guarantee of listener response.

### Context — Sprint 8

Listener, genre, artistic intent and delivery context qualify perceptual
conclusions. Missing/unknown context must be represented explicitly.

### Reference, Mix and Reasoning — Sprints 9-11

Perceptual evidence augments existing V1 reference/mix contracts and the
observation-to-recommendation trace. Recommendations remain advisory and
non-destructive.

---

## Scientific Validation Anchors

At minimum, future research and validation must consider:

- ISO 226 for equal-loudness contours.
- ISO 532-1 for Zwicker loudness methodology.
- ITU-R BS.1770 for programme loudness and true peak.
- EBU R128 for production/broadcast loudness context.

NØISYNE does not claim present conformance to these standards. A conformance
claim requires reviewed implementation scope, fixtures, tolerances, repeatable
results and recorded limitations.

---

## Real-Time and DAW Safety Boundary

Current workflow adapters only export files. The planned Sprint 20 Ableton
bridge is limited to launch/connect and health/version/status. Heavy ML or audio
analysis must never run on Ableton's real-time audio thread.

V2 excludes track manipulation, plugin/device changes, automation writes,
automatic EQ/compression, automatic mastering, unattended actions and
destructive audio replacement. Deeper DAW-aware action belongs to V3 or later.

---

## Design Rules

1. Preserve objective measurements as evidence.
2. Keep perceptual models versioned, testable and independently replaceable.
3. Separate lifecycle maturity from machine availability.
4. Represent uncertainty and missing context explicitly.
5. Prefer deterministic behavior and graceful optional-provider failure.
6. Keep domain logic independent from UI, API, DAW and provider libraries.
7. Require scientific evaluation before capability promotion or conformance
   language.
