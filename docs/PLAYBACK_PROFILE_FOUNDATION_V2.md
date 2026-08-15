# NØISYNE V2 Playback Profile Foundation

Version: 1.0.0
Status: Implemented (Sprint 6)

## Scope and scientific boundary

Sprint 6 separates three concerns:

1. A **reproduction profile** records what is known or declared about a playback path.
2. A **transfer transformation** applies explicit linear evidence to digital audio.
3. A **translation-risk judgment** interprets possible perceptual consequences and belongs to
   Sprint 7.

The frozen Sprint 1 `PlaybackProfile` remains a context-only, versioned description and makes no
emulation claim. `PlaybackTransferProfile` is an adjacent contract for actual evidence. No phone,
laptop, car, Bluetooth speaker, club, headphone, monitor, or room category creates a transfer.

The physical measurement boundaries were checked against IEC 60268-21:2018 (acoustical,
output-based sound-system measurements), IEC 60268-22:2020 (electrical and mechanical transducer
measurements), ANSI/CTA-2034-B (July 2024, in-home loudspeaker response/directivity/maximum output),
AES75-2023 (maximum linear loudspeaker level using Music-Noise), ITU-R BS.775-4 (12/2022,
multichannel layouts/downmix/LFE), ITU-R BS.1116-3 (2015, reference subjective-test reproduction
conditions), ITU-R BS.708 (1990, studio-monitor headphone electro-acoustics), and IEC 60318-1:2009,
IEC 60318-3:2014 and IEC 60318-4:2010 (ear simulators/couplers). This implementation does not
reconstruct paid normative procedures or claim compliance with any of them.

## Evidence and identity

Every transfer has stable `transfer_id` and `version`, a stable Sprint 1
`PlaybackProfileReference`, evidence source/version, schema version, and explicit provenance:

- `MEASURED`: identified physical measurement with caller-supplied metadata.
- `REFERENCE_SPECIFICATION`: a stated reference/target, not an individual measured device.
- `USER_DECLARED`: properties explicitly supplied by the caller.
- `ENGINEERING_APPROXIMATION`: a documented approximation, never measured truth.

Blank provenance metadata is invalid. Runtime application metadata also records transfer-method
identity `noisyne.explicit_linear_playback_transfer` version `1.0.0`. Updating evidence requires a
new evidence/profile version; display names are not identities. The repository ships no mutable
profile catalog and no fictional consumer-device curves. Engineering identity fixtures use the
`engineering_test_fixture` scope.

## Magnitude evidence

`MagnitudeResponseEvidence` accepts caller-supplied, finite, read-only `float64` frequency and dB
arrays. The frequency axis must be positive, strictly increasing, duplicate-free, contain at least
two points, and exactly span the declared validity range. Evaluation uses linear interpolation of
dB on the natural logarithm of frequency (`LOG_FREQUENCY_DB`). Exact anchors remain exact; a
geometric frequency midpoint receives the arithmetic dB midpoint. Queries outside the evidence
range fail (`REJECT`) rather than extrapolating.

Magnitude-only evidence has `MAGNITUDE_ONLY` phase semantics and cannot transform audio. Sprint 6
does **not** synthesize a minimum-phase realization: doing so would introduce derived phase that is
not measured and is unnecessary for the valid minimum scope. No response curve is presented as a
physical impulse response. Validity bounds describe measurement/evidence support, not brick-wall
filters or usable-frequency guarantees.

`NORMALIZED_RELATIVE_RESPONSE` and `DIGITAL_AMPLITUDE_RATIO` may be converted from dB using
`10 ** (dB / 20)`. `ABSOLUTE_ACOUSTIC_OUTPUT` cannot be converted to digital gain. A normalized
curve never establishes sensitivity, listening SPL, or an absolute acoustic level.

## Explicit impulse response and transformation

`ImpulseResponseTransfer` accepts a caller-supplied, real, finite, read-only `float64` FIR with
shape `[transfer_channels, taps]`. Metadata must declare sample rate, provenance, normalization,
measurement conditions, time-origin/alignment convention, acoustic scope, and channel topology.
The scopes distinguish device-only, measured point, device-plus-room, listener-position,
ear-simulator, HATS, real-ear, target, and engineering fixtures. A device/on-axis curve is not
relabelled as what a listener hears in a room.

The engine performs deterministic NumPy full linear convolution. Input and IR sample rates must
match exactly; there is no resampling. With `N` input samples and `M` taps, output length is
`N + M - 1`. Sample zero of the supplied FIR aligns with sample zero of the input; any physical
delay is retained in the caller-supplied FIR under its declared time-origin convention. A one-tap
unity FIR is therefore zero-latency identity.

`CHANNEL_INDEPENDENT_SHARED` applies one FIR independently to every channel.
`EXPLICIT_PER_CHANNEL` requires one FIR per declared input channel. Channel count/order alone does
not establish a layout. There is no transfer matrix, channel remapping, stereo-to-mono downmix,
bass management, or LFE reconstruction. BS.775-4 informs these boundaries only; no BS.775 downmix
is implemented.

The engine copies input samples to contiguous `float64`, never mutates the input, and emits a new
`AudioData` whose samples are read-only. Duration and in-memory sample-byte size are updated. It
rejects nonnumeric, complex, empty, shape-inconsistent, NaN/Inf, or convolution-overflow inputs.
Finite samples beyond nominal digital full scale are preserved and reported; output is never
silently clipped, limited, or normalized.

## Loudspeakers, rooms, and headphones

A loudspeaker response can describe device-only/free-field evidence, a measured point, or a
device/room/listener-position path only when explicitly labelled. Directivity and room simulation
are not implemented. An on-axis loudspeaker response is not a listener in-room response.

Headphone evidence uses separate scopes for electrical/device, coupler/ear simulator, HATS,
real-ear, and target response. Ear-simulator response is not an individual's real-ear response.
There is no individualized HRTF, binaural renderer, target personalization, or invented headphone
correction.

## Headroom, nonlinear behavior, and listening level

`MaximumLinearOutputEvidence` can carry a measured, referenced, declared, or approximate scalar,
its units/scale, method reference, conditions, optional frequency range and distance, and
limitations. It is separate from frequency response. Merely citing AES75 does not assert
AES75-compatible measurement; the caller must supply actual evidence and method metadata.

No limiter, compression, clipping, amplifier protection, thermal compression, excursion limit,
distortion, codec, or generic small-speaker effect is simulated. Dynamic-range numbers are not
invented. Playback metadata does not infer acoustic listening SPL; the existing explicit
calibration/listening-level contracts remain authoritative.

## Validation and transport

Analytical fixtures cover identity, half gain (`-6.020599913279624 dB` = amplitude `0.5`), exact
and interpolated magnitude anchors, known FIR convolution, delta response, silence, independent
opposite-phase stereo, explicit per-channel gains, multichannel rejection, overflow, immutable
arrays, missing provenance, and rejected extrapolation. Comparisons use exact equality where the
operation is exactly representable and tight floating tolerances otherwise.

Large frequency/IR arrays are runtime-only and explicitly absent from JSON. Compact JSON-safe
summaries contain identity, provenance, semantics, dimensions, method version, output size, peak,
and flags proving that clipping and normalization were not applied.

## Explicit non-claims

- **FREQUENCY RESPONSE != PERCEIVED SOUND QUALITY**
- **NORMALIZED RESPONSE != ABSOLUTE SPL**
- **ON-AXIS SPEAKER RESPONSE != LISTENER IN-ROOM RESPONSE**
- **EAR-SIMULATOR RESPONSE != INDIVIDUAL REAL-EAR RESPONSE**
- **DEVICE CATEGORY != A UNIQUE TRANSFER FUNCTION**
- **MAXIMUM OUTPUT != FREQUENCY RESPONSE**
- **PLAYBACK TRANSFORMATION != TRANSLATION-RISK JUDGMENT**

Sprint 7 may compare perceptual evidence before and after an explicit transfer. Sprint 6 itself
does not produce compatibility percentages, risk, masking, descriptor, or sound-quality judgments.
