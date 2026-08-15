# NØISYNE V2 Perceptual Descriptor Foundation

Version: 1.0.0
Status: Sprint 5 implemented foundation

## Scientific boundary

This sprint separates standardized psychoacoustic quantities, research-backed
correlates, and informal mix-engineering terms. It does not create a universal
descriptor scale. An unavailable descriptor has no numeric value; zero never
means unavailable. Standard units are named below only to document their owning
method and are emitted only when that complete method is implemented.

## Descriptor taxonomy

| ID | Class | Reference | Correlates / dependency | Unit | Calibration and valid input | State | Prohibited claim |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `sharpness` | Standardized | DIN 45692:2009-08 | Weighted first moment of Zwicker specific loudness on critical-band rate; requires complete DIN method and validated DIN 45631 / ISO 532-1-style loudness | acum | Standard input/listening conditions and validated specific loudness | Unavailable: paid standard/WAV and specific-loudness engine absent | Spectral centroid, HF ratio, or ERB centroid is not DIN sharpness |
| `roughness` | Standardized | DIN 38455:2024-11; ECMA-418-2:2025 Clause 7 | Method-specific rapid envelope modulation plus auditory filtering and specific loudness | asper | Calibrated pressure and all conditions of the selected, explicitly identified method | Unavailable: DIN method/supplements absent; Sottek model and independent fixtures absent | A 70 Hz-weighted envelope FFT is not standardized roughness; DIN and ECMA are not interchangeable |
| `fluctuation_strength` | Standardized | ECMA-418-2 4th ed., Clause 9 | Slow modulation, envelope-dependent windows, HSA, and Sottek specific loudness | vacilHMS | Calibrated pressure, 48 kHz processing, declared ECMA-74 compliance | Unavailable: prerequisite model and validation absent | A standalone 4 Hz detector is not fluctuation strength |
| `tonality` | Standardized | ECMA-418-2 4th ed., Clause 6 | Autocorrelation separation of tonal/noise partial loudness | tuHMS | Calibrated pressure, 48 kHz processing, declared ECMA-74 compliance | Unavailable: prerequisite model and validation absent | Do not merge ECMA tonality, TNR, prominence ratio, and ISO/TS 20065 into a score |
| `brightness` | Research correlate | Saitis & Siedenburg 2020; Marozeau & de Cheveigné 2007 | Linear-frequency power spectral centroid | Hz measurement, not a standardized psychoacoustic unit | Finite digital audio and positive power; no SPL calibration | Implemented | Centroid is not a universal perceived-brightness scale or source attribution |
| `warmth` | Informal engineering term | No general validated operational definition selected | Spectral balance may provide later evidence | none | Not established | Unavailable | Low-mid/high ratio is not perceptual warmth |
| `harshness` | Informal engineering term | No general validated operational definition selected | Sharpness, roughness, spectrum, distortion, level, and context may interact | none | Not established | Unavailable | Harshness is not sharpness or fixed 2-5 kHz energy |
| `punch` | Informal engineering term | No general validated operational definition selected | Transient, envelope, low-frequency, and dynamics evidence may interact | none | Not established | Unavailable | Crest factor, peak, bass energy, or attack alone is not punch |
| `density` | Informal engineering term | No general validated operational definition selected | Occupancy, event rate, masking, polyphony, and compression may interact | none | Not established | Unavailable | RMS, occupancy, masking, polyphony, or compression is not density |
| `width` | Informal engineering term | No general validated operational definition selected | Spatial hearing and presentation; inter-channel metrics may support later evidence | none | Requires a defined presentation/listening model | Unavailable | Stereo correlation or side/mid energy is not perceived width |

The executable taxonomy, including limitations and prohibited claims, is the
`descriptor_taxonomy()` contract in `noisyne/perception/descriptor_contracts.py`.

## Standards research and implementation gate

DIN Media lists DIN 45692:2009-08 as a current, 14-page German standard with WAV
material, available only by purchase. Its public description identifies a
weighted first moment of a DIN 45631 loudness-tonality pattern. The complete
method and supplied WAV material were not available. NOISYNE also lacks the
validated Zwicker specific-loudness prerequisite. No acum output is implemented.

DIN Media lists DIN 38455:2024-11 as a current, 44-page German standard with EXE
and further digital supplements, available only by purchase. The complete method
and supplements were not available. It is not reconstructed from secondary
sources and is not conflated with ECMA roughness.

The complete official ECMA-418-2, 4th edition (June 2025), was reviewed under
its implementation-permitting copyright notice. Clauses 5-9 require much more
than modulation weighting: 48 kHz preprocessing; outer/middle/inner-ear filters;
a 53-band modified-Bark auditory bank; method-specific padding, segmentation,
rectification and RMS; a calibrated nonlinear transform and threshold in quiet;
then ACF or envelope/HSA processing, noise reduction, temporal aggregation,
calibration, and binaural rules. Annexes A-C provide evaluation plots and study
summaries but no machine-readable conformance fixtures sufficient for an
independent implementation gate. No Sottek hearing-model stage was added.

ECMA algorithm identity, ECMA-74-compliant measurement, and applying an
ECMA-derived algorithm to music are separate claims. This sprint claims none of
them. Ordinary music files do not automatically meet ECMA-74 conditions.

## Brightness quantity definition

For channel `c`, frame `n`, and one-sided FFT bin `k`, Sprint 2 supplies window
power `P[c,n,k]` and linear frequency `f[k]`. The runtime computes:

```text
C[c,n] = sum_k(f[k] * P[c,n,k]) / sum_k(P[c,n,k])
```

when the denominator is positive. The per-channel programme value is:

```text
C_channel[c] = sum_n,k(f[k] * P[c,n,k]) / sum_n,k(P[c,n,k])
```

and the transported programme estimate is:

```text
C_programme = sum_c,n,k(f[k] * P[c,n,k]) / sum_c,n,k(P[c,n,k])
```

Thus temporal and channel aggregation are explicitly power weighted. Channels
are not waveform-downmixed, treated as ears, or arithmetically averaged; a
silent channel cannot dilute an active channel, and opposite-phase channels do
not cancel. Both DC and the available Nyquist bin are included. The unit is Hz.
No normalization, clipping, epsilon, perceptual weighting, SPL calibration, or
equal-loudness correction is applied.

Frame curves and per-channel programme values remain finite, read-only runtime
arrays. Undefined zero-power cells use a finite zero storage value paired with
an explicit boolean definition mask. If all analyzed power is zero, transport
state is `INSUFFICIENT_EVIDENCE` and the estimate is absent. The final Sprint 2
frame is zero padded; it participates in the same power-weighted programme
summary and the boundary policy is exposed in frontend metadata.

## Literature and limitations

Saitis and Siedenburg, *JASA* 148(4), 2020,
DOI `10.1121/10.0002275`, support spectral centroid as a robust acoustical
correlate of timbral brightness while also reporting interaction with attack
time. Marozeau and de Cheveigné, *JASA* 121(1), 2007,
DOI `10.1121/1.2384910`, show systematic fundamental-frequency influence on the
brightness dimension. Consequently the result is named a **timbral brightness
spectral-centroid correlate**, not perceived brightness.

It depends on sample rate, source bandwidth, window/FFT configuration, F0,
attack/time behavior, stimulus set, and context. A full-mix measurement cannot
identify a hi-hat, vocal, or other source as its cause.

## Validation and contracts

Validation uses analytical single- and two-tone cases, amplitude-scale
invariance, ordering, channel invariants, silence, unusual lengths/sample rates,
non-contiguous and non-finite inputs, deterministic repetition, read-only array
checks, and JSON transport checks. These are validation of the centroid
measurement, not standard validation for sharpness, roughness, fluctuation
strength, or tonality.

`PerceptualDescriptorResult`, `PerceptualEvidence`, `Measurement`, `Confidence`,
`ResultState`, and `ScalarValue` are reused unchanged. `PERCEPTUAL_SCHEMA_VERSION`
remains `1.0.0`. Only compact descriptor results cross the transport boundary;
large runtime arrays do not.

## Explicit non-equivalences and future path

- SHARPNESS != BRIGHTNESS
- ROUGHNESS != HARSHNESS
- LUFS != PERCEIVED LOUDNESS
- STEREO CORRELATION != PERCEIVED WIDTH

Future standardized engines require lawful complete source material, all
prerequisite hearing-model stages, calibrated input-condition contracts, and
independent official fixtures. Future informal descriptors require their own
validated operational models. UI normalization, playback/translation profiles,
recommendations, source separation, ML models, API, Desktop, and DAW integration
are outside Sprint 5.
