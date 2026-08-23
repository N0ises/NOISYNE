# PHASENOX Technical Identity Freeze

Status: **FROZEN**

Effective after: R7

Baseline commit: `8f7830c37f2b8b48e38f7506b82a42eb33a22cff`

## Purpose

This document freezes the technical identity established by rename sprints
R1–R6. Future work must use the canonical PHASENOX identities below while
preserving the explicitly approved compatibility and historical contracts.
This freeze does not authorize further rename cleanup, persistence migration,
brand integration, or removal of compatibility boundaries.

## Canonical identity matrix

| Boundary | Frozen canonical identity |
| --- | --- |
| Public brand | PHASENØX |
| ASCII product identity | PHASENOX |
| Distribution | `phasenox` |
| Python namespace | `phasenox` |
| Canonical service module | `phasenox.application.phasenox_service` |
| Primary service class | `PhasenoxService` |
| V2 service class | `PhasenoxV2Service` |
| Report class | `PhasenoxReport` |
| Validation fixture provider | `PhasenoxValidationFixtureProvider` |
| CLI | `phasenox` |
| Canonical application-root environment variable | `PHASENOX_ROOT` |

New production code must not import a `noisyne` Python package. The distribution
must expose only the `phasenox` CLI entry point. The canonical service
implementation must remain in `phasenox.application.phasenox_service`; legacy
service modules remain forwarding boundaries only.

## Approved live compatibility contracts

The following identities are Category A and must remain compatible until an
explicitly scoped future compatibility-removal decision changes the contract.

### Python aliases

- `NoisyneService` is an alias of `PhasenoxService`.
- `SoundBrainService` is an alias of `PhasenoxService`.
- `NoisyneV2Service` is an alias of `PhasenoxV2Service`.
- `SoundBrainReport` is an alias of `PhasenoxReport`.
- `NoisyneValidationFixtureProvider` is an alias of
  `PhasenoxValidationFixtureProvider`.

### Modules and namespace

- `phasenox.application.noisyne_service`
- `phasenox.application.soundbrain_service`
- `brain.*`, resolving to the same canonical `phasenox.*` module objects

These are compatibility boundaries, not alternate implementations.

### Runtime and storage contracts

| Boundary | Approved legacy identity |
| --- | --- |
| Application-root environment fallback | `NOISYNE_ROOT`, then `SOUNDBRAIN_ROOT` |
| Persisted vector collection | `soundbrain` |
| Engine compatibility keys | `noisyne`, `soundbrain` |
| Repository identity | `N0ises/NOISYNE` |

Application-root precedence is frozen as `PHASENOX_ROOT`, `NOISYNE_ROOT`,
`SOUNDBRAIN_ROOT`, then automatic discovery.

### Serialized identifier allowlist

The following existing `noisyne.*` method, provider, and digest identifiers are
serialized compatibility contracts. Their spelling must not change without a
separate versioned data-contract migration:

- `noisyne.auditory_frontend`
- `noisyne.brightness_power_spectral_centroid_correlate`
- `noisyne.calibrated_loudness_foundation`
- `noisyne.context_policy_binding`
- `noisyne.descriptor.roughness`
- `noisyne.descriptor.sharpness`
- `noisyne.deterministic_reasoning`
- `noisyne.digital_programme_energy_sum`
- `noisyne.explicit_linear_playback_transfer`
- `noisyne.grounded_perceptual_reasoning_foundation`
- `noisyne.in_memory_memory_store`
- `noisyne.knowledge_memory_foundation`
- `noisyne.knowledge_retrieval_contract`
- `noisyne.mix_intelligence_canonical_json_sha256`
- `noisyne.perceptual_context_foundation`
- `noisyne.perceptual_mix_intelligence_foundation`
- `noisyne.perceptual_reference_foundation`
- `noisyne.personalization_foundation`
- `noisyne.policy_conditioned_translation_risk`
- `noisyne.reference_embedding_cosine`
- `noisyne.reference_erb_programme_power_delta`
- `noisyne.reference_programme_energy_delta`
- `noisyne.reference_sample_peak_delta`
- `noisyne.relative_simultaneous_masking_foundation`
- `noisyne.sprint2_erb_programme_power_delta`
- `noisyne.translation_evidence_foundation`
- `noisyne.v1.integrated_programme_loudness`

This is an allowlist, not permission to create new serialized identifiers under
the legacy prefix.

## Approved historical records

Category D content remains historical evidence and must not be rewritten merely
to satisfy current naming. The authoritative occurrence-level classification is
the R6.3 final census. Its historical file groups are frozen as:

- `docs/bible/**`
- `docs/roadmap/SoundBrain_*.md`
- `docs/CHANGELOG_v2.md`
- `docs/NOISYNE_TECHNICAL_RENAME_FREEZE.md`
- `docs/PHASENOX_R4_RUNTIME_MIGRATION_AUDIT.md`
- `docs/PHASENOX_R5_PERSISTENCE_MIGRATION_AUDIT.md`
- `docs/PHASENOX_R6_LEGACY_IDENTITY_AUDIT.md`
- `docs/PHASENOX_R6_FINAL_LEGACY_CENSUS.md`
- `docs/RELEASE_NOTES.md`
- `docs/TECHNICAL_DEBT.md`
- `V1_FREEZE_VALIDATION_REPORT.md`
- `V2_RAG_MEMORY_PREFLIGHT_REPORT.md`
- `tests/archive/**`
- `tests/test_noisyne_phase6_repository_freeze.py`

References to these records from current governance documentation are approved
migration/freeze references, not active product identities.

## Regression guard

`tests/test_phasenox_technical_identity_freeze.py` enforces this freeze through
an explicit matrix. It checks production import syntax and dynamic import
literals, the exact console-script mapping, canonical class locations and
aliases, environment precedence, persistence and engine identities, the
serialized-ID allowlist, representative `brain.*` module identity, and selected
current-facing product surfaces.

The guard intentionally does not ban legacy strings across the entire
repository. Such a ban would reject the approved Category A compatibility
contracts and Category D historical evidence frozen above.

## Change control

Any proposal to alter an approved compatibility identity requires its own
explicitly authorized sprint, migration and rollback analysis where data is
involved, focused regression updates, and a revised freeze decision. Incidental
feature work must not weaken or silently expand this contract.
