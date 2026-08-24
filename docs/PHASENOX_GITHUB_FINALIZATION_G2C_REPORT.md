# PHASENOX GitHub Finalization G2-C Report

## Phase status

- Phase: **G2-C canonicalization and repository rename**
- Pre-rename migration readiness: **PASS**
- Repository rename: **PENDING**
- Public release: **NO-GO**
- External Windows acceptance: **18 PENDING**
- Legal/signing items: **3 PENDING**

This report records the validated migration commits before their first remote
publication. It will be updated with final remote and rename evidence after the
canonical `main` advance and in-place repository rename.

## Repository identities

| Boundary | Value |
| --- | --- |
| Old repository | `N0ises/NOISYNE` |
| Canonical target | `N0ises/PHASENOX` |
| Default branch | `main` |
| Distribution | `phasenox` |
| Product version | `1.0.0` |

The target slug returned HTTP 404 immediately before G2-C work began, confirming
that no unexpected replacement repository occupied it. The current authenticated
operator is `N0ises` with repository admin permission. G2-C will rename repository
ID `1301844155` in place; it will not create, transfer, delete, or recreate a
repository.

## Scoped commits

1. `3938191f401874eb85a88cb22e209c8cf1bdfb5a` — canonical repository references
   and package metadata.
2. `705f82f5ceaa5aca73513e43f17be9a8b99dd5c2` — canonical Windows CI,
   CODEOWNERS, and workflow guard.
3. This report commit — pending at the time this section was authored.

The reference/metadata commit changes:

- `README.md`;
- `pyproject.toml`;
- `docs/ARCHITECTURE_v2.md`;
- `docs/CAPABILITY_REGISTRY.md`;
- `docs/DECISIONS_v2.md`;
- `docs/EXECUTION_PLAN_v2.md`;
- `docs/MODULE_MAP.md`;
- `docs/PHASENOX_TECHNICAL_IDENTITY_FREEZE.md`;
- `docs/ROADMAP_v2.md`;
- `tests/test_noisyne_phase6_repository_freeze.py`;
- `tests/test_phasenox_release_alignment.py`;
- `tests/test_phasenox_technical_identity_freeze.py`.

The CI commit changes only:

- `.github/CODEOWNERS`;
- `.github/workflows/phasenox-ci.yml`;
- `tests/test_github_configuration.py`.

No PHASENOX runtime/source module, persistence contract, shipping resource,
branding artwork, version, serialized identity, engine key, or CLI behavior was
changed.

## Current-facing reference cleanup

Canonical references now use `N0ises/PHASENOX` and its HTTPS URL in the README,
active architecture/capability/decision/execution/module/freeze/roadmap documents,
package metadata, and regression guards. The README clone command accepts an
arbitrary checkout directory while using the real canonical URL.

`pyproject.toml` retains distribution `phasenox` and version `1.0.0` and now
defines only the appropriate project links:

- Repository: `https://github.com/N0ises/PHASENOX`;
- Issues: `https://github.com/N0ises/PHASENOX/issues`.

No company, publisher, legal identity, homepage, or unrelated URL was invented.

Pre-rename census after the committed migration changes:

| Classification | Count |
| --- | ---: |
| Current-facing old repository references | 0 |
| Stale old repository references | 0 |
| Historical evidence occurrences retained | 22 |
| Negative regression-guard literals | 2 |

The 22 historical occurrences remain in 13 completed audits, freezes, plans, and
reports. They retain factual repository identity at the time each artifact was
written. The two test literals prohibit the old slug from returning to the
explicit active-document allowlist; they are enforcement data, not current links.

## Canonical CI design

The frozen V2-derived branch contained no workflow. The only registered workflow
was the stale `Desktop UI` workflow stored on the frozen `desktop-ui` branch; its
commands and dependency profile do not describe canonical PHASENOX.

`.github/workflows/phasenox-ci.yml` introduces one truthful Windows job for:

- pushes to `main`;
- pull requests targeting `main`;
- Python 3.12 on `windows-latest`;
- read-only repository permissions;
- focused repository identity, release-alignment, Desktop Core contract, and
  distribution/fresh-install validation;
- canonical wheel and source-distribution builds.

It does not depend on secrets, LM Studio, model downloads, external Windows
acceptance, PyInstaller/Inno compilation, or the excluded Desktop Core heavy
profiles. Import-heavy compatibility suites remain part of the established local
matrix because their collection path requires Chroma, NumPy, and network-client
runtime dependencies. The CI matrix was proven from a clean Python 3.12.10 venv
with only `build`, `pytest`, and `PyYAML` plus their installer dependencies.

CODEOWNERS now assigns `*` to `@N0ises`, the authenticated repository owner/admin.
The prior `@HamidCooper7` assignment had no observable collaborator permission and
was removed rather than used as misleading ownership evidence. No fabricated
team or account was introduced.

## Validation results

| Gate | Result |
| --- | --- |
| Full focused local identity/compatibility/distribution/freeze suite | PASS — 63 tests |
| Clean minimal CI identity/release/Desktop Core subset | PASS — 22 tests |
| Clean minimal CI distribution/fresh-install suite | PASS — 4 tests |
| Clean Python 3.12 wheel/sdist build | PASS |
| Artifacts | `phasenox-1.0.0-py3-none-any.whl`, `phasenox-1.0.0.tar.gz` |
| Ruff on touched Python | PASS |
| Black check on touched Python | PASS |
| Compileall on touched Python | PASS |
| TOML metadata validation | PASS |
| Workflow YAML parse and trigger assertions | PASS |
| `git diff --check` | PASS |

The build emitted existing setuptools license-metadata deprecation warnings; it
completed successfully. G2-C did not change the license metadata because that is
not required for repository migration correctness.

## Pre-rename remote snapshot

| Ref | SHA |
| --- | --- |
| `main` | `ea5d93043a5ecf679744ab662167cc3926a191d0` |
| `g2-main-integration` | `b6a40ccf464f1bda15fd9fe9e547e85c912fc3b0` |
| `v2-development` | `3b9272790ad1cbea5b89947761ceecb52a32cb89` |
| `desktop-ui` | `e2dd11e4193f32cd4f31cda5bca8cbd322bec3af` |
| `develop` | `53bd19802593905ec7ff20144bff0fc35b23d92b` |
| `v1-freeze-candidate` | `04b896f151e17e9d4cf35b31afc4e68a254e0306` |
| `v1-ui-baseline` | `04b896f151e17e9d4cf35b31afc4e68a254e0306` |

Additional server state before rename:

- visibility: public;
- issues: enabled, zero open;
- branches: 8;
- tags: 12;
- releases: 1 historical release;
- Actions: enabled, all actions allowed, SHA pinning not required;
- registered workflows: 1 historical Desktop workflow;
- rulesets: 0;
- `main` branch protection: absent.

Protection/ruleset changes and branch cleanup remain G2-D work.

## Rollback plan

Before `main` advances, a failed migration branch or CI gate leaves canonical
remote refs unchanged; stop without merging, rebasing, or force pushing. After a
published `main` advance, use reviewed forward corrections rather than resetting
published history. After the in-place rename, GitHub's old-slug redirect is a
recovery aid but not canonical configuration; controlled remotes must use the new
URL. A severe post-rename settings problem requires a separately audited rename-
back operation, never creation of a replacement repository.

No rollback path changes shipping data, releases artifacts, tags, frozen branches,
or the public-release NO-GO verdict.
