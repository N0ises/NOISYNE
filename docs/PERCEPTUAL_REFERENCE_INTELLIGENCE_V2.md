# PHASENOX V2 Perceptual Reference Intelligence

## Scope and scientific boundary

Sprint 9 provides identified comparison evidence. It keeps three categories separate:

1. **Objective reference delta** — differences in named quantities with equations and units.
2. **Representation similarity** — similarity under one exact model/feature representation.
3. **Interpretation or policy** — caller-owned criteria for deciding whether evidence matters.

Only the first category and transport/math foundations for the second are implemented. No policy,
universal threshold, reference aggregation, quality ranking, recommendation, or aggregate match score
is included.

The central constraints are:

- **REFERENCE TRACK != GROUND TRUTH**
- **REFERENCE SIMILARITY != MIX QUALITY**
- **CLAP SIMILARITY != MASTERING SIMILARITY**
- **SPECTRAL DELTA != PERCEPTUAL FAILURE**
- **ENERGY DELTA != LOUDNESS QUALITY**
- **REFERENCE DIFFERENCE MAY REFLECT MUSICAL CONTENT**
- **NEAREST REFERENCE != BEST REFERENCE**
- **REFERENCE COMPARISON != AUTOMATIC MIXING**

Different songs naturally differ in melody, harmony, instrumentation, arrangement, section structure,
dynamics, and duration. Objective or embedding differences can therefore describe content difference
rather than an engineering defect.

## Research reviewed

- Elizalde et al., [CLAP: Learning Audio Concepts From Natural Language Supervision](https://arxiv.org/abs/2206.04769).
- Wu et al., [Large-scale Contrastive Language-Audio Pretraining with Feature Fusion and Keyword-to-Caption Augmentation](https://arxiv.org/abs/2211.06687), and the [official LAION-CLAP implementation](https://github.com/LAION-AI/CLAP).
- Huang et al., [MuLan: A Joint Embedding of Music Audio and Natural Language](https://arxiv.org/abs/2208.12415).
- Goto, [Music Information Retrieval: Recent Developments and Applications](https://staff.aist.go.jp/m.goto/PAPER/IEEEPROC200804goto.pdf).
- Casey et al., [Content-Based Music Information Retrieval: Current Directions and Future Challenges](https://drops.dagstuhl.de/entities/document/10.4230/DFU.Vol3.11041.157).
- Essentia documentation for [CrossSimilarityMatrix](https://essentia.upf.edu/reference/std_CrossSimilarityMatrix.html) and [CoverSongSimilarity](https://essentia.upf.edu/reference/std_CoverSongSimilarity.html).
- Won et al., [Towards Perceptually-Aligned Music Similarity](https://arxiv.org/abs/2601.19109).

The conclusion is deliberately narrow: similarity means whatever the selected representation,
training objective, preprocessing, and metric operationally define. Contrastively trained audio/text
embeddings can support retrieval and classification, but a cosine value does not become mix balance,
mastering quality, tonal equality, listener preference, or production correctness.

MuLan and Essentia are research context only. Sprint 9 adds neither dependency. No source separation,
LLM, RAG, or heavy model was added.

## Reference identity, provenance, and role

`ReferenceTrackIdentity` carries a logical `reference_id`, version, display name, provenance, source,
duration, sample rate, channel count, optional caller-declared role, assumptions, and limitations. It
does not transport a filesystem path or infer a role.

Provenance is one of `USER_SUPPLIED`, `PROJECT_SUPPLIED`, `WORKFLOW_SUPPLIED`, or
`REFERENCE_LIBRARY`. None means curated, professional, correct, or industry-standard.

Roles are optional caller declarations: tonal, translation, arrangement, mix-balance, or general
reference. Audio content never infers them. Sprint 8 context is not required and is unchanged; a future
adapter may attach an explicit declared purpose or role without adding genre inference, listener-based
ranking, or automatic thresholds.

`ReferenceSet` is a transport collection with stable set identity and unique reference IDs. It is not a
hidden library and performs no downloading, averaging, target construction, ranking, or comparison.
Each reference must be compared independently. Heterogeneous references are never averaged into a
pseudo-mastering target.

## Objective comparison

`ObjectiveReferenceComparator` produces independent whole-programme evidence for a source and one
identified reference. Every signed delta follows **source minus reference** semantics.

### Brightness correlate

The exact Sprint 5 power-spectral-centroid correlate is reused:

`delta_hz = source_centroid_hz - reference_centroid_hz`

This is a correlate difference, not brightness quality.

### ERB power distribution

The exact Sprint 2 channel-preserving ERB frontend is reused. Frame powers are summed independently
for each programme and channel. For raw or explicitly gain-adjusted evidence:

`delta_db[c,b] = 10 log10(source_power[c,b] / reference_power[c,b])`

For shape-only evidence, each channel's band powers are divided by that channel's positive total power
before the same ratio. Only ratios with positive numerator and denominator are defined. Undefined
cells have a false runtime mask and a zero placeholder; they are not silently floored. ERB evidence is
not masking, audibility, source attribution, or a bass/mid/high judgment.

Channel-by-band comparison requires identical channel counts and identical Sprint 2 band definitions.
Otherwise it returns insufficient evidence and empty runtime delta arrays. Channels are never copied,
collapsed, downmixed, labeled as ears, or inferred as stereo/LFE. Programme scalar energy sums power
across channels without waveform downmix.

### Programme energy

The engineering quantity is sum-square digital sample amplitude across all samples and channels:

`delta_db = 10 log10(source_sum_square / reference_sum_square)`

Both energies must be positive. It is not LUFS, SPL, or perceived loudness.

### Sample peak

The quantity is maximum absolute sample amplitude:

`delta = source_sample_peak_absolute - reference_sample_peak_absolute`

It is sample peak, not reconstructed true peak, loudness, or a clipping judgment.

## Comparison and gain modes

- `RAW_LEVEL` compares samples exactly as supplied. No normalization is performed.
- `EXPLICIT_DIGITAL_GAIN` applies caller-declared source/reference gains using
  `amplitude * 10^(gain_db/20)`. It requires a transported gain method ID/version. The system does not
  choose gains or imply loudness matching.
- `SHAPE_ONLY` excludes programme energy and sample peak. Brightness is inherently invariant to a
  common positive gain, and ERB power is normalized per channel only for this explicit mode.

Raw and shape-only modes prohibit nonzero applied gains and gain metadata. There is no peak matching,
automatic loudness matching, or hidden normalization.

## Duration and temporal alignment

Different durations are accepted because every programme is summarized independently. There is no
sample, frame, beat, section, dynamic-time-warp, tempo-stretch, or learned alignment. Sprint 9 does not
make framewise cross-programme claims.

## Embedding provider and cosine evidence

Sprint 9 chooses the contract-only provider option. `ReferenceEmbeddingProvider` defines a narrow
runtime boundary, while `ReferenceEmbeddingProviderIdentity` transports provider, implementation,
model/checkpoint, preprocessing, dimension, sample rate, clip/window policy, aggregation policy,
backend, device, and availability. Raw embeddings remain runtime-only.

Direct comparison requires exact provider identity equality. Cosine is computed without assuming
normalized inputs:

`cosine_similarity = dot(x, y) / (norm(x) * norm(y))`

Inputs must be one-dimensional, real, finite, nonempty, and match the declared dimension. Zero-norm
input returns insufficient evidence; no epsilon is introduced. The result uses the named raw interval
`[-1, 1]`, is not normalized, and is never converted to a percentage.

No live CLAP adapter is wired. Existing `clap_embedding` capability truth remains `VERIFIED`: a local
or downloaded model is required and is not bundled. The current provider does not expose a sufficiently
complete stable checkpoint/preprocessing/clip/aggregation identity for Sprint 9 transport evidence.
Consequently arbitrary long-audio segmentation and aggregation are deferred rather than guessed.
There is no network access or model download in tests or benchmarks.

CLAP, if later stabilized, would provide model-space semantic evidence only. It would not provide mix,
mastering, tonal, loudness, production-quality, genre, or preference evidence. MuLan is not used.

## Transport/runtime boundary

JSON contracts retain method and schema versions, reference identity, comparison mode and gains,
source/reference values, signed deltas, units, state, sign convention, assumptions, and limitations.
They round-trip with finite JSON numbers.

Large ERB arrays and their definition mask stay in `ReferenceRuntimeResult`, are finite/read-only, and
are explicitly absent from JSON. The transport summary exposes their dimensions, count of defined
values, extrema, sign convention, and `arrays_serialized=false`. Embedding vectors likewise are not
transported.

## V1 migration decision

The V1 `ReferenceComparator` was inspected. It uses metric-specific hard-coded tolerances,
tolerance-normalized error, pass/fail and severity, a 100/50/0-oriented similarity mapping, category
scores, aggregate similarity, reference selection, and recommendations. Its metrics have heterogeneous
units and the tolerance values do not carry scientific provenance.

Those behaviors remain legacy V1/UI engineering semantics. Sprint 9 does not relabel or migrate them
as scientific V2 truth. V2 emits explicit evidence; any future threshold/policy contract must be
caller/project supplied with provenance. No policy contract or default thresholds are introduced here.

## Validation and capability truth

Analytical fixtures cover identity, half gain (`6.020599913279624 dB`), explicit inverse gain,
frequency-selective direction, silence, mono/stereo channel mismatch, duration mismatch,
determinism, JSON round-trip, immutable runtime arrays, duplicate identities, and logical identity
without path leakage. Cosine fixtures cover identical, orthogonal, opposite, positive scaling, zero,
nonfinite values, dimension mismatch, and exact representation-identity mismatch using analytical
vectors only.

The narrow implemented capabilities are `perceptual_reference_foundation`,
`reference_objective_comparison`, and `reference_embedding_contract`. There is no
`reference_clap_similarity`, `professional_match`, `mastering_match`, or reference quality score.

## Deferred boundary

Sprint 9 provides evidence only. Mix issue prioritization, EQ/dynamics/stereo/mastering advice,
automatic tonal matching, transfer-function estimation between songs, and any “fix this” behavior are
outside scope. They are not implemented in anticipation of Sprint 10. Natural-language reasoning is
also excluded and remains a later integration concern.
