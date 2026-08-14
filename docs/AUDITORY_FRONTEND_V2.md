# NØISYNE V2 Auditory Frontend

Version: 1.0

Status: Sprint 2 implemented

Canonical runtime: `noisyne.perception.auditory`

Transport contracts: `noisyne.perception.auditory_contracts`

## Decision

Sprint 2 retains a neutral, one-sided linear-Hz power spectrum and adds one
canonical auditory coordinate: the Glasberg-Moore (1990) ERB-rate scale. It
does not also implement Bark.

ERB was selected because it is tied to measured equivalent rectangular
bandwidths of auditory filters, has a mature closed-form rate equation and
inverse, behaves continuously from zero to Nyquist, and can support later
filter-bank or loudness research without discarding the neutral spectrum. Bark
and the critical-band organization behind the Zwicker method remain relevant
research inputs for later loudness and masking sprints. Implementing both now
would create two competing frontend truths without a Sprint 2 consumer that
requires Bark.

The ERB-rate mapping is:

```text
E(f) = 21.4 log10(1 + 4.37 f / 1000)
f(E) = (10^(E / 21.4) - 1) 1000 / 4.37
```

where `f` is in hertz. Version 1.0.0 partitions the interval from zero to
Nyquist into adjacent 1-ERB-rate regions by default. Each linear FFT bin is
assigned to exactly one region and its power contribution is summed. This is a
deterministic band aggregation, not a gammatone filterbank, cochlear model,
critical-masking threshold, or loudness method.

## Input and Level Policy

The frontend accepts the existing `noisyne.audio.io.models.AudioData`; it does
not load files and does not introduce another audio-data abstraction. The
canonical shape is `(frames,)` for mono or `(frames, channels)` for
multichannel audio. Samples must be finite, real numeric values, and metadata
must report the matching positive channel count and integer sample rate.
Non-contiguous input is copied into an internal float64 working buffer. The
source object is never mutated.

Sample amplitude is preserved. No normalization, limiting, clipping, or
resampling occurs. Values outside nominal digital full scale are accepted and
reported by `nominal_full_scale_exceeded`. Digital sample amplitude and dBFS
are not physical sound-pressure level. Version 1.0.0 accepts no microphone,
loudspeaker, gain, or SPL calibration and explicitly reports
`spl_calibrated = false`.

## Channel Policy

All channels are analyzed independently and retained in arrays shaped
`(channels, frames, bins)` and `(channels, frames, auditory_bands)`. No mono
downmix is produced. Identical and phase-opposed stereo therefore have equal
per-channel energy and cannot disappear through phase cancellation. A future
consumer may derive a documented combination from these channels, but Sprint 2
does not score stereo width or select a loudness channel weighting.

This differs intentionally from several V1 feature analyzers that average
channels for an objective scalar. The V1 implementations remain unchanged.

## Framing and Spectrum

Method `noisyne.auditory_frontend`, version `1.0.0`, defaults to:

| Property | Value |
| --- | --- |
| Window | Periodic Hann |
| Frame size | 2048 samples |
| Hop size | 512 samples (75% overlap) |
| FFT size | 2048 samples |
| Alignment | Frames start at source sample zero; timestamps identify frame centres |
| Boundary | The final incomplete frame is zero-padded; at least one frame is emitted |
| Resampling | None |
| Spectrum | One-sided, window-energy-normalized power |
| Precision | NumPy float64 working and result arrays |

At 48 kHz these defaults provide a 42.7 ms frame, 10.7 ms hop, and 23.4 Hz bin
spacing; at 44.1 kHz they provide 46.4 ms, 11.6 ms, and 21.5 Hz. The explicit,
serialized configuration permits later algorithms to select a different
frame/hop/FFT tradeoff without changing method 1.0.0 defaults or introducing a
general DSP framework. FFT sizes may exceed frame sizes for explicit
zero-padding; they may not be smaller.

`frame_times_seconds` identifies the center of each complete analysis frame,
including its zero-padded support. A padded frame center can therefore fall
after the physical end of a short source and is not guaranteed to lie inside
`source_time_range`. A downstream consumer that reports physical source events
or intervals must clip or intersect analysis-frame support with
`source_time_range`; the frontend intentionally does not clamp timestamps.

For a windowed frame `x[n] w[n]` and FFT size `Nfft`, the one-sided bin
contributions are based on:

```text
P[k] = |FFT{x w}[k]|² / (Nfft sum(w²))
```

Interior one-sided bins are doubled, excluding DC and an even-length Nyquist
bin. Summing bins therefore equals `sum((x w)²) / sum(w²)` within floating-point
tolerance, including when the FFT is zero-padded.

## Runtime and Transport Boundary

`AuditoryFrontendResult` is runtime-only and contains read-only NumPy arrays for
linear frequencies, frame-centre times, channel power spectra, and auditory
band power. `AuditoryFrontendSummary` is the JSON-safe audit contract. It
contains method/configuration identity, source facts, time coverage, band
definitions, level assumptions, limitations, and matrix dimensions, but never
serializes frame matrices. Its independent schema version is `1.0.0`.

All runtime arrays must contain finite values. Input samples are not clipped or
normalized; if a finite but extreme amplitude overflows the FFT, power
calculation, or band aggregation, analysis raises `ValueError` instead of
returning NaN or infinity. NumPy overflow/invalid handling is scoped only to
these numerical operations.

The Sprint 1 aggregate perceptual schema remains `1.0.0` and is unchanged.

## Capability Truth

The runtime registry adds `auditory_frontend` as **Implemented**, not Verified
or Production. It is deterministic and executable with the existing NumPy
dependency, but it is not part of the frozen V1 path and has not passed a later
perceptual-model validation programme. Machine availability remains separate
from lifecycle state.

## Research Anchors

- B. R. Glasberg and B. C. J. Moore, “Derivation of auditory filter shapes from
  notched-noise data,” *Hearing Research* 47 (1990), 103–138,
  <https://doi.org/10.1016/0378-5955(90)90170-T>.
- E. Zwicker, “Subdivision of the Audible Frequency Range into Critical Bands,”
  *Journal of the Acoustical Society of America* 33 (1961), 248,
  <https://doi.org/10.1121/1.1908630>.
- F. J. Harris, “On the Use of Windows for Harmonic Analysis with the Discrete
  Fourier Transform,” *Proceedings of the IEEE* 66 (1978), 51–83,
  <https://doi.org/10.1109/PROC.1978.10837>.
- ISO 226:2023, *Acoustics — Normal equal-loudness-level contours*,
  <https://www.iso.org/standard/83117.html>.
- ISO 532-1:2017, *Acoustics — Methods for calculating loudness — Part 1:
  Zwicker method*, <https://www.iso.org/standard/63077.html>.
- ITU-R BS.1770-5 (2023), *Algorithms to measure audio programme loudness and
  true-peak audio level*,
  <https://www.itu.int/rec/R-REC-BS.1770-5-202311-I/en>.

The ISO and ITU documents are context for level, channel, and future loudness
work. Sprint 2 does not implement or claim compliance with ISO 226, ISO 532-1,
ITU-R BS.1770, or EBU R128.

## Explicit Non-Claims and Limitations

Sprint 2 produces auditory-analysis inputs only. It does not claim or produce:

- a human-hearing or cochlear model;
- calibrated SPL or equal-loudness compensation;
- ISO-compliant or perceived loudness;
- Zwicker loudness;
- critical masking thresholds;
- brightness, warmth, harshness, punch, or width scores;
- playback simulation or translation risk;
- recommendations, DAW control, or autonomous mixing.
