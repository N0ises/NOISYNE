# NØISYNE Capability Registry

Version: 2.0

Status: ACTIVE

---

## Purpose and Source of Truth

A capability is a discrete feature that can be discovered, validated, enabled,
disabled, tested and composed. Runtime capability lifecycle truth is defined by
`noisyne/runtime/capabilities.py`; this document explains that registry and
records product-level capabilities that do not yet have runtime entries.

The repository is `N0ises/NOISYNE`; the canonical distribution and Python
namespace are `noisyne`. Compatibility names remain supported where specified
by the technical rename freeze.

---

## Lifecycle Is Not Availability

The runtime lifecycle is:

```text
Planned -> Implemented -> Verified -> Production -> Deprecated
```

Lifecycle describes implementation maturity. Machine availability answers a
different question: whether required dependencies, model assets, services,
configuration and data are usable in the current environment. For example,
CLAP is Verified but its model is not bundled; RAG is Implemented but requires
a configured corpus and model assets. Neither state authorizes a UI to claim
that the capability can run on a particular machine without an availability
check and a reason when unavailable.

A contract or adapter existing also does not imply a live external integration.

---

## Authoritative Runtime Registry Snapshot

This table mirrors the lifecycle states in `noisyne/runtime/capabilities.py` at
the start of V2. Machine availability must be evaluated separately.

| Runtime capability | Lifecycle | Availability constraint / truth |
| --- | --- | --- |
| Runtime | Production | Shared runtime code exists |
| Model Loading | Production | Backend/model requirements still apply |
| Model Cache | Production | Runtime cache exists |
| Model Repository | Production | Repository resolution exists |
| Transformers Backend | Production | Installed dependency and model assets required |
| SentenceTransformers Backend | Production | Installed dependency and model assets required |
| Audio Loading | Production | Requires declared audio dependencies |
| DSP Analysis | Production | Deterministic V1 path; declared DSP dependencies required |
| Auditory Frontend | Implemented | NumPy-only deterministic spectral/ERB-rate inputs; no SPL calibration or perceptual conclusions |
| Loudness Foundation | Implemented | Explicit calibration, pressure mapping and LUFS evidence; no sone/phon or ISO 532-3 algorithm |
| Frequency Masking Foundation | Implemented | Pairwise common-gain relative excitation margin only; no threshold, events, full-mix attribution or temporal masking |
| Perceptual Descriptors Foundation | Implemented | Ten-descriptor scientific taxonomy; unavailable descriptors carry explicit blockers and no substitute values |
| Brightness Correlate | Implemented | Power-spectral centroid in Hz only; no normalized or universal perceived-brightness score |
| Playback Profile Foundation | Implemented | Versioned provenance and bounded transfer-evidence contracts; no generic device presets or inferred room/headphone response |
| Playback Linear Transfer | Implemented | Caller-supplied real FIR, exact-rate full linear convolution; no resampling, downmix, clipping, normalization or nonlinear reproduction model |
| Translation Evidence Foundation | Implemented | Objective brightness-correlate, ERB-power, programme-energy and sample-peak changes for an explicit Sprint 6 FIR; no audibility or quality judgment |
| Policy-Conditioned Translation Risk | Implemented | Boolean evaluation of explicit provenance-backed, dimension- and unit-matched criteria; no universal threshold, normalized score or aggregation |
| Perceptual Context Foundation | Implemented | Provenance-backed literal declarations and deterministic conflicts; no classification, preference prediction or signal evidence |
| Context Policy Binding | Implemented | Exact versioned binding to supplied Sprint 7 policies; no hidden precedence, fallback or policy generation |
| Perceptual Reference Foundation | Implemented | Stable logical reference identity/provenance and compact evidence contracts; a reference is not ground truth |
| Reference Objective Comparison | Implemented | Whole-programme brightness-correlate, ERB-power, sum-square energy and sample-peak deltas; no temporal alignment, policy or quality score |
| Reference Embedding Contract | Implemented | Exact provider/model/checkpoint/preprocessing identity plus raw cosine math; no live model or percentage score |
| Perceptual Mix Intelligence Foundation | Implemented | Structured issues from explicit policy criteria over precomputed Sprint 4/7/8/9 evidence; no quality score or recommendation |
| Mix Policy Evaluation | Implemented | Deterministic source/dimension/unit-safe criteria with policy-declared priority and stable ordering; no DSP or LLM |
| Perceptual Reasoning Foundation | Implemented | Grounded statements rendered from whitelisted Sprint 10 facts; no free-form provider text, quality score or causal diagnosis |
| Grounded Reasoning Validation | Implemented | Exact fact/issue/criterion/template cross-reference validation after provider output; rejected content is not transported as accepted reasoning |
| Deterministic Reasoning | Implemented | Offline canonical explanations and neutral review suggestions; no LLM, RAG, memory or DSP dependency |
| Audio Context | Production | Deterministic rule-based context |
| Engineering Analysis | Production | Deterministic rule engine |
| CLAP Embedding | Verified | Local/downloaded model required; model not bundled |
| Reference Comparison | Production | Deterministic comparator; optional reasoning may be unavailable |
| RAG Retrieval | Implemented | Corpus/models/configuration required; preflight issues remain |
| LLM Reasoning | Implemented | Accessible provider/model required; none is bundled |
| Report Generation | Production | Structured JSON; reference path also supports Markdown |
| Service Facade | Production | V1 `NoisyneService`; `SoundBrainService` is a compatibility alias |
| Engine Registry | Production | In-memory routing registry |
| Orchestration | Implemented | Not exercised by the frozen V1 CLI path |
| Audio Intelligence | Planned | Broader semantic/perceptual intelligence is V2 work |
| Mix Intelligence | Production | Deterministic V1 root-cause/priority/chain recommendations |
| Plugin Intelligence | Production | Deterministic recommendations; no plugin control |
| Memory Learning | Planned | Runtime registry records no V1 learning loop |
| DAW Integration | Planned | No runtime DAW integration exists |

The previous broad claims that Audio Intelligence, Memory & Personalization and
DAW Integration were all Production did not match this runtime registry.

---

## Product and Contract Capability Truth

These states describe product surfaces or contracts and must not be confused
with a successful runtime availability probe.

| Capability | State | Exact boundary |
| --- | --- | --- |
| V1 CLI | Production | Canonical `noisyne`; legacy `soundbrain` alias retained |
| V1 NoisyneService | Production | Canonical facade; `SoundBrainService` retained for compatibility |
| Workflow Integration Contracts | Implemented | Deterministic JSON/text/Markdown exports only |
| DAW Integration Contracts | Implemented | Adapter interfaces and file exports; no DAW communication |
| Ableton Launch Bridge | Planned (Sprint 20) | Launch/connect plus health/version/status smoke handshake only |
| DAW Session Read/Control | Future | Outside V2 |
| User-Confirmed DAW Actions | Future | Outside V2; later-version safety/action work |
| Autonomous Mixing | Future / V3 | Not a V2 capability |
| Local API | Planned (Sprint 16) | No tracked API implementation at V2 baseline |
| Desktop V1 | Frozen release candidate | Exists on isolated `desktop-ui`; not runtime-registered here |
| Desktop V2 Integration | Planned (Sprint 17) | Through `V2ApplicationAdapter` after service/API contracts |
| V2 Perceptual Core | Planned | Auditory, loudness-calibration, relative-masking, descriptor-taxonomy, playback-transfer and policy-conditioned translation foundations plus a brightness correlate are Implemented; standardized descriptor engines and absolute masking remain planned |
| ONNX | Benchmark spike (Sprint 14) | No adoption or runtime availability claim |
| Voice / Agent Functionality | Future | Outside V2 |

---

## Workflow Integration Contract Detail

`noisyne/integration` contains placeholder adapters for Ableton Live, REAPER,
Cubase, FL Studio and Studio One. Their supported operations write deterministic
files:

- `export_analysis`
- `export_processing_chain`
- `export_plugin_recommendations`
- `export_report`

They perform no OSC, MIDI, ReaScript, remote API, process launch, socket, DAW
session, plugin-control or automation operation. Their use of DAW names is
contract metadata, not external-system availability.

---

## V1 Release-Candidate Qualification

NØISYNE V1.0.0-rc1 completed release hardening for its supported deterministic
paths. Optional or incomplete capabilities retain their actual registry states;
the release-candidate designation does not promote every registry entry to
Production.

Known constraints include provider/model availability, RAG preflight issues,
thin reference segmentation and legacy repository-wide formatting debt.

---

## Final Rule

Every new runtime feature must receive lifecycle metadata before Production.
Every client must combine lifecycle metadata with a separate machine-
availability result and explanatory reason. No capability may be presented as
available merely because a contract, module or roadmap entry exists.
