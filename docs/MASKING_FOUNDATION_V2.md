# NØISYNE V2 Relative Simultaneous-Masking Foundation

Version: 1.0

Status: Sprint 4 deterministic foundation implemented; masking thresholds and events unavailable

Canonical runtime: `noisyne.perception.masking`

Input contract: `noisyne.perception.masking_contracts`

## Implemented Phenomenon

This sprint implements pairwise, simultaneous, frequency-domain **relative
excitation-margin evidence** for two separate signals whose alignment and common
digital gain relationship are explicitly declared by the caller.

It does not implement an absolute masking threshold, masked audibility, or a
general human masking model. The result indicates how two known signals compare
after the same fixed auditory-filter reference weighting. It does not determine
whether a listener can hear the target.

One full mix does not expose separate masker and target contributions. Full-mix
analysis therefore returns `INSUFFICIENT_EVIDENCE`, no ordered events, and no
source attribution.

## Scientific Decision

The fixed moderate-level roex(p) approximation from Moore and Glasberg (1983)
is used as the narrowest fully traceable auditory-filter reference available for
this sprint. That paper derives auditory-filter shapes from simultaneous-masking
experiments, provides the equations used here, describes excitation as filter
output versus filter center frequency, and requires complex components to be
summed in linear power.

The representation is deliberately labelled a fixed reference. The 1983 paper
states that its estimates apply to young listeners at moderate sound levels and
that filter bandwidth and asymmetry vary with level and listener. Moore and
Glasberg (1987), Glasberg and Moore (1990), and later work further develop
frequency- and level-dependent filters. The complete level-dependent algorithm,
calibrated listener input, and independent validation fixtures needed to apply
those models are not available here. No missing coefficients are guessed.

The 1981 simultaneous-versus-forward study reports materially different filter
shapes between the two paradigms. The 1982 study addresses forward masking as a
function of level. These sources establish that a simultaneous filter must not
be reused as a forward- or backward-masking model. Sprint 4 implements no
temporal masking.

## Equations and Provenance

For auditory-filter center frequency `fc` in hertz, let `fck = fc / 1000`.
Moore and Glasberg (1983), Equation 3, defines:

```text
ERB(fc) = 6.23 * fck^2 + 93.39 * fck + 28.52 Hz
```

For the simplified roex(p) filter in Equation 6:

```text
p = 4 * fc / ERB(fc)
g = abs(f - fc) / fc
W(f, fc) = (1 + p*g) * exp(-p*g)
```

The implemented filter-center domain is the paper's stated 0.1 to 6.5 kHz
range. `W` is a dimensionless power weighting with unity at the center.

For channel `c`, frame `n`, linear FFT bin `b`, and filter center `k`, the
runtime excitation power is:

```text
E_x(c,n,k) = sum_b P_x(c,n,b) * W(f_b, fc_k)
```

`P_x` is Sprint 2's window-normalized one-sided linear power spectrum. The same
weighting is applied independently to masker and target. There is no
outer/middle-ear transform, nonlinear cochlear stage, or level-dependent filter.

Where both excitation powers are strictly positive, the relative excitation
margin is:

```text
M(c,n,k) = 10 * (log10(E_masker(c,n,k)) - log10(E_target(c,n,k))) dB
```

Sign convention:

- positive: masker excitation power exceeds target excitation power;
- zero: equal excitation power;
- negative: target excitation power exceeds masker excitation power.

Larger positive values mean greater **relative excitation dominance** under the
fixed reference weighting. Zero is mathematical equality, not a human masking
threshold. No value has an audibility decision meaning.

If either excitation is zero, the logarithmic margin is undefined. The runtime
stores `0.0` in the finite numerical matrix and marks that cell false in the
separate `margin_defined` matrix. Consumers must never interpret a false cell's
stored numerical placeholder. No epsilon, floor, clipping, or perceptual
threshold is introduced.

## ERB and Bark Decision

Sprint 2's retained linear-Hz spectrum is the input. Its Glasberg-Moore 1990
ERB-rate band centers provide a deterministic sampling grid for filter-center
locations. Sprint 2's `auditory_band_power` is not used as excitation and is not
relabelled as masking.

The filter weights are calculated directly on the linear-Hz FFT bins using the
1983 equations. No Bark representation is added. ITU-R BS.1387-2 uses
Bark-domain structures for its reference/test audio-quality model, but that does
not justify changing NØISYNE's general frontend or importing the PEAQ model.

## ITU-R BS.1387-2 Decision

Recommendation ITU-R BS.1387-2 (05/2023) was inspected for its treatment of
perceptual scales, excitation, masking, playback level, temporal spreading, and
validation. Its detailed model compares a time-aligned Reference Signal with a
Signal Under Test for perceived audio-quality assessment. It includes playback-
level scaling, outer/middle-ear weighting, critical-band grouping, level-
dependent spreading, temporal spreading, masked thresholds, model output
variables, and trained quality mapping.

No BS.1387 equation, constant, table, threshold, spreading function, temporal
stage, or quality mapping is used in Sprint 4. The Recommendation's reference-
test codec/equipment purpose, its fallback playback-level convention, its
temporal stages, and its stated patent/licensing requirements do not establish a
general pairwise mix-masking algorithm. NØISYNE makes no BS.1387 or PEAQ
compliance claim.

## Input Contract and Pairwise Policy

`RelativeMaskingPairContext` requires:

- an auditable common-gain relationship reference;
- an auditable sample-alignment reference;
- optional caller-supplied masker and target source identifiers;
- exact sample-synchronous, equal-length alignment;
- matched channel counts analyzed independently by index;
- an uncalibrated common-digital-gain level basis.

The runtime rejects different sample rates, sample counts, or channel counts.
It performs no resampling, delay estimation, realignment, normalization,
downmixing, or gain matching. Metadata alone does not establish the common gain
relationship; the caller must declare its provenance.

Explicit source identifiers are retained only as caller evidence. No identifier
is inferred. Because this sprint emits no `MaskingEvent`, it emits no
`source_attribution` value.

## Full-Mix Policy

`SimultaneousMaskingFoundation.analyze(audio)` validates the input and returns:

- `ResultStatus.INSUFFICIENT_EVIDENCE`;
- no masking events;
- evidence that source decomposition is unavailable;
- no instrument, stem, or hidden-component identity.

It does not claim that one region masks another inside the sum. Spectral density
or overlap in a full mix is not converted into an ordered masker-to-target
event.

## Channel and Binaural Policy

Matched channels are processed independently by index. Stereo is not downmixed,
phase-opposed channels are not cancelled, and programme channels are not treated
as ears. No binaural masking or cross-channel combination is implemented.

## Time Policy

The model is simultaneous and frame-local. Sprint 2 frame-center timestamps are
retained at runtime and can extend beyond source duration for a final zero-
padded frame. Sprint 4 emits no physical `MaskingEvent` time range. Any future
event extractor must intersect its interval with the source time range and must
not expose padded support after EOF as physical audio.

No forward masking, backward masking, post-masking, pre-masking, temporal decay,
or temporal integration is implemented.

## Runtime and Transport

`RelativeMaskingFoundationResult` retains read-only runtime arrays:

- `frame_times_seconds`: `(frames,)`;
- `masker_excitation_power`: `(channels, frames, filters)`;
- `target_excitation_power`: `(channels, frames, filters)`;
- `relative_excitation_margin_db`: `(channels, frames, filters)`;
- `margin_defined`: `(channels, frames, filters)`.

All numerical arrays are finite. Large matrices are not serialized.

The frozen Sprint 1 `FrequencyMaskingResult` is reused without schema changes.
Pairwise calculations can return `COMPUTED` with evidence and no events. Silence,
one-sided energy, or absence of supported filter centers returns
`INSUFFICIENT_EVIDENCE`. `MaskingEvent.strength` is not populated because no
validated threshold or event-extraction criterion is available.

## Calibration and Level Dependence

No acoustic calibration is required for the relative metric because both
signals must share a known digital gain relationship and the metric is a ratio
after identical linear weighting. This invariance does not make the result an
absolute perceptual prediction.

Absolute masking thresholds, absolute audibility, level-dependent filter
selection, and listener-specific excitation require calibrated acoustic level
and a validated model. Sprint 3 calibration semantics are not changed or
implicitly applied.

## Validation

The authoritative analytical checks are limited to equations actually
implemented:

- Equation 3 gives `ERB(1000 Hz) = 128.14 Hz` exactly to the shown precision.
- Equation 6 gives `W(fc, fc) = 1` and symmetry for equal linear-Hz offsets.
- Numerical integration of the implemented 1 kHz roex(p) weighting agrees with
  the analytical ERB within `0.01 Hz` on the test grid.
- Identical signals produce `0 dB` relative excitation margin wherever defined.
- Doubling masker amplitude at common gain produces
  `10*log10(4) = 6.020599913... dB`; tests use `1e-12 dB` absolute tolerance.
- A 1 kHz masker contributes less excitation to a far 4 kHz filter than to a
  nearby 1.1 kHz filter under the implemented equation.

Additional tests cover masker-level monotonicity for linear scaling, swapped
pair direction, pure tones, broadband and narrowband noise, impulse input,
silence, near-silence, mono, stereo, phase opposition, 44.1 and 48 kHz sample
rates, low sample rate, odd/short final frames, incompatible pairs, JSON
round-trips, determinism, finite/read-only matrices, source-ID policy, and
lightweight package import.

These are equation, numerical, and software-contract checks. They are not
psychoacoustic threshold validation. No published masked-threshold fixture is
claimed because the required acoustic conditions and complete level-dependent
model are outside the implemented quantity.

## Numerical Safeguards

- Existing Sprint 2 validation rejects malformed, empty, non-finite, or
  incompatible audio metadata and arrays.
- FFT and excitation overflow raise errors; values are not clipped.
- Margin uses a difference of base-10 logarithms to avoid ratio overflow.
- Zero excitation uses an explicit validity mask rather than an arbitrary
  epsilon.
- Outputs are finite and read-only.

## Baseline Performance

Local development-environment timings for `analyze_pair`, including both Sprint
2 frontend passes and Sprint 4 excitation/margin calculation, used two aligned
10-second sinusoidal inputs. Each case ran three times with no model warm-up or
excluded setup pass:

| Sample rate | Channels | Frames | Filters | Minimum | Median | Maximum |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 44.1 kHz | 1 | 859 | 28 | 0.060222 s | 0.060589 s | 0.064139 s |
| 44.1 kHz | 2 | 859 | 28 | 0.193055 s | 0.197649 s | 0.198634 s |
| 48 kHz | 1 | 935 | 28 | 0.068898 s | 0.069562 s | 0.070230 s |
| 48 kHz | 2 | 935 | 28 | 0.210250 s | 0.211746 s | 0.214229 s |

These are baseline wall-clock observations, not cross-machine performance
guarantees. The runtime computes two `(channels, frames, filters)` excitation
matrices and one margin matrix without constructing a
`frames × filters × filters` influence tensor.

## Limitations and Non-Claims

This foundation does not claim:

- an exact human masking threshold or audibility prediction;
- a cochlear or full psychoacoustic hearing simulation;
- source separation or identification of kick, bass, vocal, or instruments;
- ordered masking events from a full mix;
- binaural masking or stereo-to-ear equivalence;
- forward, backward, informational, or temporal masking;
- comodulation masking release;
- tonal/noise masker offsets or MPEG psychoacoustic behavior;
- absolute threshold of hearing;
- hearing-loss or listener-specific prediction;
- ISO, ITU-R BS.1387, PEAQ, or MPEG compliance.

A static, independent-filter representation cannot model comodulation masking
release or across-band spectro-temporal detection cues. Listener variation,
level-dependent asymmetry, suppression, outer/middle-ear transmission, and
nonlinear combination remain unresolved.

## Sources

- B. C. J. Moore and B. R. Glasberg, “Suggested formulae for calculating
  auditory-filter bandwidths and excitation patterns,” *JASA* 74(3), 750–753
  (1983), <https://doi.org/10.1121/1.389861>.
- B. R. Glasberg and B. C. J. Moore, “Derivation of auditory filter shapes from
  notched-noise data,” *Hearing Research* 47, 103–138 (1990),
  <https://doi.org/10.1016/0378-5955(90)90170-T>.
- B. C. J. Moore and B. R. Glasberg, “Auditory filter shapes derived in
  simultaneous and forward masking,” *JASA* 70, 1003–1014 (1981),
  <https://doi.org/10.1121/1.386950>.
- B. R. Glasberg and B. C. J. Moore, “Auditory filter shapes in forward masking
  as a function of level,” *JASA* 71, 946–949 (1982),
  <https://doi.org/10.1121/1.387575>.
- B. C. J. Moore and B. R. Glasberg, “Formulae describing frequency selectivity
  as a function of frequency and level, and their use in calculating excitation
  patterns,” *Hearing Research* 28, 209–225 (1987),
  <https://doi.org/10.1016/0378-5955(87)90050-5>.
- Recommendation ITU-R BS.1387-2 (05/2023), “Method for objective measurements
  of perceived audio quality,”
  <https://www.itu.int/rec/R-REC-BS.1387-2-202305-I/en>.

## Deferred Work

Before producing masking thresholds or events, future work needs a selected
level-dependent model, explicit acoustic/presentation calibration, lawful and
complete algorithm access, independent reference fixtures with expected
thresholds, a validated decision criterion, and an event aggregation policy.
Temporal masking, CMR, binaural processing, and source decomposition require
separate scopes and evidence.
