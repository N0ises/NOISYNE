# NØISYNE V2 Calibrated Loudness Foundation

Version: 1.0

Status: Sprint 3 foundation implemented; psychoacoustic algorithm blocked

Canonical runtime: `noisyne.perception.loudness`

Transport contracts: `noisyne.perception.loudness_contracts`

## Scientific Decision

ISO 532-3:2023, first edition, is the selected future primary method for
general music and time-varying sound. Its scope includes stationary and
time-varying tones, noises, complex sounds, musical sounds, speech and impact
sounds. It also explicitly excludes calculating one overall loudness value for
a time-varying signal longer than five seconds. This matches NØISYNE's need for
time-dependent loudness semantics better than choosing a stationary method
merely because it is easier to implement.

ISO 532-1:2017 (Zwicker) and ISO 532-2:2017 (Moore-Glasberg stationary) remain
comparison methods. ITU-R BS.1770-5 remains the programme-loudness reference,
not the psychoacoustic method. ANSI/ASA S3.4 remains steady-sound and
terminology context.

## Standard Access and Licensing Gate

The repository and development environment contain no licensed copy of ISO
532-3:2023, its informative companion source code, or its verification signals.
The public ISO catalogue confirms that source code accompanies the purchased
standard, but that companion material is not publicly available here. The ISO
catalogue also states that ISO materials are copyright protected. Public
previews are incomplete and are not a lawful or technically adequate basis for
reconstructing normative constants, transfer tables, temporal coefficients, or
reference fixtures.

The 2016 primary paper by Moore, Glasberg, Varathanathan and Schlittenlacher is
open access under CC BY-NC 3.0 and documents the model architecture and
experimental basis. It does not replace the complete 2023 standard, companion
implementation, and verification set for a conformance implementation.

Consequently Sprint 3 does **not** implement ISO 532-3, sones, phons, specific
loudness, binaural inhibition, or temporal loudness. It implements only the
independently justified calibration and evidence boundary needed before those
algorithms can run.

## Quantities Kept Distinct

- **Digital sample amplitude / dBFS** describes an electrical or encoded signal
  relative to a digital reference. It does not establish pressure at a listener.
- **Sound pressure / dB SPL** is an acoustic quantity. This foundation can map
  samples linearly to pressure in pascals when an explicit, traceable calibration
  is supplied. It does not calculate dB SPL.
- **Programme loudness / LUFS** is the existing pyloudnorm-based V1 integrated
  measurement in the ITU-R BS.1770 family. It may be attached as objective
  evidence but is never used as a sone or phon estimate.
- **Loudness** is the auditory sensation ordered from soft to loud; the ASA
  terminology unit is the sone.
- **Loudness level** is defined through equal-loudness comparison with a 1 kHz
  reference under specified listening conditions; its unit is the phon.

The ASA terminology reference defines one sone using a frontally presented
1 kHz plane wave at 40 dB SPL re 20 µPa. This definition is not used as a
shortcut to calculate sones from arbitrary audio.

## Calibration Contract

`LoudnessCalibration` declares:

- a stable calibration identifier and version;
- a finite positive linear scale in pascals per digital sample unit;
- a traceability statement;
- whether the source frequency response has been compensated;
- the declared acoustic presentation path;
- explicit left/right source-channel indexes.

Supported presentation declarations are deliberately limited to input paths
confirmed by accessible ISO 532-3 material:

- free-field single microphone, mapped diotically;
- diffuse-field single microphone, mapped diotically;
- separately calibrated pressure at the left and right eardrum measurement
  points, requiring distinct channels.

The scalar calibration assumes the supplied waveform has already received the
measurement-system frequency-response compensation declared by the caller. An
uncompensated response is retained as context but cannot produce calibrated
pressure input for a future standard method. Earphone electrical sensitivity
and transfer-function processing are not represented; an ordinary stereo file
is not an earphone or binaural measurement.

## Implemented Stages and Provenance

Only these deterministic stages are implemented:

1. Existing `AudioData` validation is reused from the frozen Sprint 2 frontend.
2. Explicit channel mapping follows the declared presentation contract.
3. Digital samples are multiplied by the caller-supplied linear calibration to
   obtain pressure in pascals.
4. Finite, read-only `(frames, 2)` pressure arrays are retained at runtime.
5. Stable RMS pressure in pascals is attached as objective evidence.
6. Existing V1 integrated LUFS may be attached as a separate objective
   programme-loudness measurement.
7. `PerceivedLoudnessResult` is returned with
   `INSUFFICIENT_EVIDENCE`, no estimate, and explicit limitations.

The pressure conversion is a unit/calibration operation, not an ISO 532-3
algorithm stage. No Sprint 2 ERB band power is converted to loudness.

## Uncalibrated and Calibrated Behavior

Ordinary `AudioData` loaded from a music file contains no acoustic calibration
or listening condition. The result therefore has no pressure array, sone, phon,
or absolute perceived-loudness estimate. A finite V1 LUFS value may still be
reported as supporting evidence.

With a complete calibration declaration, the foundation may produce left/right
pressure arrays and Pa measurements. The loudness result still remains
`INSUFFICIENT_EVIDENCE` because the authoritative ISO 532-3 algorithm and
verification materials are unavailable. Calibration alone never authorizes a
sone or phon estimate.

## Monaural, Stereo and Binaural Semantics

A single calibrated free-field or diffuse-field microphone is mapped to equal
left/right pressure inputs (diotic), matching the declared single-microphone
presentation. Separately measured eardrum pressure requires two distinct mapped
channels. Stereo programme channels without calibration and measurement-path
semantics are not treated as left-ear/right-ear signals. No binaural
interaction or inhibition is implemented.

## Temporal Semantics and Runtime Data

No instantaneous, short-term, long-term, percentile, or overall
psychoacoustic-loudness quantity is implemented. The only new runtime array is
the optional calibrated pressure array `(frames, 2)` in pascals. It is finite,
read-only, and not part of JSON transport. Existing Sprint 2 arrays and behavior
are unchanged.

## Validation

No ISO reference fixture or expected sone/phon value is used because the
official verification package is unavailable. Tests validate only implemented
foundation invariants:

- missing calibration produces `INSUFFICIENT_EVIDENCE` and no estimate;
- LUFS remains a separately labelled supporting measurement;
- scalar pressure conversion and channel mapping use analytical exact values;
- single-microphone mapping is diotic and eardrum mapping is two-channel;
- malformed mappings and calibrations are rejected;
- non-finite input and pressure overflow are rejected without clipping;
- pressure arrays are finite and read-only;
- calibration contracts round-trip through strict JSON serialization;
- package-root import remains NumPy-lightweight.

Exact linear mapping assertions use exact array equality where values are
binary-exact. RMS and existing LUFS comparisons use `pytest.approx` at its
default numerical tolerance. These are software-contract tests, not
psychoacoustic conformance tolerances.

## Sources

- ISO 532-3:2023, *Acoustics — Methods for calculating loudness — Part 3:
  Moore-Glasberg-Schlittenlacher method*,
  <https://www.iso.org/standard/69856.html>.
- B. C. J. Moore, B. R. Glasberg, A. Varathanathan and J. Schlittenlacher,
  “A Loudness Model for Time-Varying Sounds Incorporating Binaural
  Inhibition,” *Trends in Hearing* 20 (2016),
  <https://doi.org/10.1177/2331216516682698>.
- J. Schlittenlacher et al., “Testing and refining a loudness model for
  time-varying sounds incorporating binaural inhibition,” *JASA* 143 (2018),
  <https://doi.org/10.1121/1.5027246>.
- ISO 532-1:2017, Zwicker method,
  <https://www.iso.org/standard/63077.html>.
- ISO 532-2:2017, Moore-Glasberg stationary method,
  <https://www.iso.org/standard/63078.html>.
- ISO 226:2023, equal-loudness-level contours,
  <https://www.iso.org/standard/83117.html>.
- ITU-R BS.1770-5, programme loudness and true peak,
  <https://www.itu.int/rec/R-REC-BS.1770-5-202311-I/en>.
- ASA Standards terminology: loudness, loudness level, sone and phon,
  <https://asastandards.org/asa-standard-term-database/>.

## Non-Claims and Remaining Work

This foundation does not claim:

- ISO 532-3, ISO 532-2, ISO 532-1 or ANSI/ASA S3.4 compliance;
- a human-hearing simulation or exact subjective loudness;
- sone, phon, specific-loudness or loudness-level output;
- instantaneous, short-term, long-term or overall perceived loudness;
- binaural loudness from ordinary stereo;
- headphone, room, listener-specific or hearing-loss prediction;
- that LUFS equals psychoacoustic loudness.

Before implementing the selected method, development requires lawful access to
the complete ISO 532-3:2023 text, companion source code, verification signals,
expected results, licensing terms suitable for the repository, and validation
tolerances. The method must then be implemented and cross-checked against those
materials before any conformance or lifecycle promotion.
