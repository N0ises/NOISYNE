# PHASENOX V2 Engineering Freeze Manifest

## Freeze status

- Engineering freeze: **READY**
- Technical Desktop Core RC: **PASS**
- Public release: **NO-GO**
- External Windows acceptance: **PENDING — 18**
- Legal/signing items: **3**
- Signing status: **UNSIGNED**

This manifest freezes the V2 engineering and candidate-source identity. It is not
a public-release authorization and does not initiate repository migration.

## Source and artifact provenance

| Field | Frozen value |
| --- | --- |
| Repository | `N0ises/NOISYNE` |
| Branch | `v2-development` |
| Final V2 shipping-source SHA | `3adfbab5f5dec7e5c2237febb316bc6b89459e5e` |
| Candidate source SHA | `3adfbab5f5dec7e5c2237febb316bc6b89459e5e` |
| Version | `1.0.0` |
| Profile | `desktop-core / windows-x64` |
| Bundle | `PHASENOX-1.0.0-win-x64/` |
| Executable | `PHASENOX.exe` |
| Executable SHA-256 | `753da4c1336467b8a8fca6d7eb9ee9b7b2cbe1b3045466e1dafdd09e8fa80c48` |
| Installer | `PHASENOX-Setup-1.0.0-win-x64.exe` |
| Installer SHA-256 | `a30d30a4b92b7060c9e93a230c4bb291e46168b70f5379e8dbeeb3370b2e59c0` |
| Installer AppId | `{A6B2A61D-05B0-4CE7-85A3-C443B36D703B}` |
| Desktop application ID | `phasenox.desktop` |

Evidence/report-only commits after the shipping-source SHA do not change the
candidate payload. Any later shipping-code, runtime, dependency-profile,
packaging, installer-source, or application-resource change invalidates this
candidate and requires a rebuild with new hashes.

## Canonical technical identities

- Public brand: `PHASENØX`.
- ASCII product identity: `PHASENOX`.
- Distribution and Python namespace: `phasenox`.
- Canonical service module: `phasenox.application.phasenox_service`.
- Canonical public classes: `PhasenoxService`, `PhasenoxV2Service`,
  `PhasenoxReport`, and `PhasenoxValidationFixtureProvider`.
- CLI: `phasenox`.
- Canonical runtime-root environment variable: `PHASENOX_ROOT`.
- Desktop application ID: `phasenox.desktop`.
- Windows executable: `PHASENOX.exe`.

## Frozen compatibility and persistence contracts

The following identities must not be removed or renamed without a separately
designed compatibility/migration program:

- Python aliases: `NoisyneService`, `SoundBrainService`, `NoisyneV2Service`,
  `SoundBrainReport`, and `NoisyneValidationFixtureProvider`.
- Compatibility modules: `phasenox.application.noisyne_service` and
  `phasenox.application.soundbrain_service`.
- Compatibility namespace: `brain.*`.
- Environment fallbacks: `NOISYNE_ROOT`, then `SOUNDBRAIN_ROOT`.
- Persisted collection identity: `soundbrain`.
- Engine keys: `noisyne` and `soundbrain`.
- Existing serialized `noisyne.*` method/provider/digest identifiers.
- Repository identity: `N0ises/NOISYNE`.
- Approved Category D historical records.

`PHASENOX_ROOT` remains first in root precedence. No persistence data, collection,
schema, path layout, cache identity, engine key, or serialized identifier was
migrated in Sprint 22.

## Frozen release boundary

The standard artifact is PHASENOX Desktop Core for Windows x64. It does not ship
Torch, CUDA, torchaudio, ONNX Runtime, Chroma, PyArrow, model weights, RAG/GPU
profiles, bundled models, or implicit model downloads. Capabilities requiring
those payloads remain unavailable.

The DAW interoperability claim is limited to **Ableton Live 11.2.7**. No broader
Ableton, DAW, host, or plugin-format support is implied by this freeze.

## Validation baseline

- Full regression: 1,253 passed, 1 expected Windows symlink-permission skip,
  0 failed, across 101 isolated files.
- Focused Data Root/persistence/bridge batch: 82 passed.
- Candidate/bridge tests: 26 passed, 1 expected skip.
- Bridge lifecycle: 100 post-fix lifecycle cycles passed.
- Bundle verifier: PASS, 651 files, 345,784,067 bytes.
- Native closure: 241 PE files, 0 unresolved imports, 0 parse errors.
- Packaged arbitrary-CWD/offline analysis: PASS, exit 0, score 95,
  report export 2,830 bytes, no model download.
- Installer compilation: PASS with Inno Setup 7.1.0 x64.
- Legacy census: Category B = 0; Category C = 0.
- Critical/High open local code, security, packaging, persistence defects: 0.

## Protected branch provenance

These fetched remote SHAs were recorded during the freeze and were not modified:

- `origin/desktop-ui`:
  `e2dd11e4193f32cd4f31cda5bca8cbd322bec3af`
- `origin/main`:
  `a1946dd838d4918cac5d78f906719e62a9dbcc32`
- `origin/develop`:
  `53bd19802593905ec7ff20144bff0fc35b23d92b`
- `origin/v1-freeze-candidate`:
  `04b896f151e17e9d4cf35b31afc4e68a254e0306`
- `origin/v1-ui-baseline`:
  `04b896f151e17e9d4cf35b31afc4e68a254e0306`

## Gates that remain outside the engineering freeze

Public release remains NO-GO pending:

1. all 18 immutable-candidate external Windows acceptance rows;
2. publisher/legal identity resolution;
3. third-party license inventory legal review; and
4. authorized production signing and SmartScreen/reputation policy.

## Post-freeze task boundary

The following are separate, explicitly authorized tasks only:

1. push the frozen V2 baseline;
2. run the immutable candidate on the external Windows acceptance host;
3. resolve publisher/legal identity;
4. complete third-party license legal review;
5. sign authorized final artifacts and record SmartScreen/Defender results;
6. make the public-release GO/NO-GO decision from completed evidence; and
7. plan any GitHub/repository identity migration separately.

No push, public release, GitHub repository migration, branch rewrite, or new
development sprint is part of this manifest.
