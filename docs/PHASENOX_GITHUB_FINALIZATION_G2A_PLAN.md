# PHASENOX GitHub Finalization G2-A Migration Plan

## Status and boundary

- Phase: **G2-A preparation only**
- Repository: `N0ises/NOISYNE`
- Working branch: `v2-development`
- Frozen preparation HEAD: `bcb2a6c573d1c25308780696167fc1cf12b92fab`
- Candidate source: `3adfbab5f5dec7e5c2237febb316bc6b89459e5e`
- Repository rename performed: **no**
- Branch migration performed: **no**
- Default branch changed: **no**
- Tags/releases created: **no**
- Public release: **NO-GO**

This document converts the G1 forensic findings into an executable, gated
migration plan. It does not authorize or perform any GitHub mutation beyond a
later, separately approved phase.

## 1. Frozen input verification

Observed after fetching `origin`:

| Ref | Required and observed SHA |
| --- | --- |
| `v2-development` | `bcb2a6c573d1c25308780696167fc1cf12b92fab` |
| `main` | `a1946dd838d4918cac5d78f906719e62a9dbcc32` |
| `develop` | `53bd19802593905ec7ff20144bff0fc35b23d92b` |
| `desktop-ui` | `e2dd11e4193f32cd4f31cda5bca8cbd322bec3af` |
| `v1-freeze-candidate` | `04b896f151e17e9d4cf35b31afc4e68a254e0306` |
| `v1-ui-baseline` | `04b896f151e17e9d4cf35b31afc4e68a254e0306` |
| `agent/sprint-1-runtime-stabilization` | `35db097802cd471ff6afcc2265a394c148cdd2e3` |

Local and remote V2 were synchronized at `0 / 0`; the tracked tree/index was
clean. The only untracked files were the two protected Desktop roadmap files.

Frozen V2 tree at G2-A start:
`63d0e76dbb8f56356097dd834a9afbf34e2a9245`.

## 2. Target state

The recommended final state remains:

1. existing repository renamed in place to `N0ises/PHASENOX`;
2. default branch remains named `main`;
3. canonical `main` contains old `main` history plus the frozen V2 lineage and
   reviewed migration-only metadata/CI commits;
4. `v2-development` remains fixed at `bcb2a6c...` as the preparation freeze;
5. `develop` is normally fast-forwarded to the post-migration development
   baseline;
6. Desktop/V1 evidence branches remain preserved;
7. the fully merged agent branch is only a later deletion candidate;
8. canonical CI and protection exist before migration is declared complete.

No exact final `main` commit can be named before its future preservation merge and
reviewed migration commits exist. The plan therefore freezes its required inputs,
parents, tree checkpoints, and validation gates instead of inventing a SHA.

## 3. Main transition analysis

Current ancestry:

- `origin/main` and `origin/v2-development` are divergent;
- old `main` has 1 commit not reachable from V2;
- V2 has 115 commits not reachable from old `main`;
- merge base: `62a3631db856538484b7ba047769a5b08b0a41c2`;
- neither branch can directly fast-forward the other.

The only `main`-unique commit is `a1946dd...`, a GitHub merge commit. Its tree
`7286640e4a2dbf401dc2f99a885ae8be6bf5a504` exactly equals its second parent
`62a3631...`, which is already an ancestor of V2. It contains historical topology
but no file content unavailable to V2.

### Future safe command sequence

These commands are a G2-B/G2-C plan. They were **not run** in G2-A.

```powershell
git fetch origin
git switch --create g2-main-integration origin/v2-development

# Preserve old main topology while deliberately retaining the frozen V2 tree.
git merge --no-ff --strategy=ours origin/main `
  -m "chore(repository): preserve pre-phasenox main history"

# Both histories must be reachable.
git merge-base --is-ancestor origin/main HEAD
git merge-base --is-ancestor origin/v2-development HEAD

# Before any migration metadata edits, the merge tree must equal frozen V2.
git diff --exit-code origin/v2-development HEAD
git rev-parse 'HEAD^{tree}'
# Required output: 63d0e76dbb8f56356097dd834a9afbf34e2a9245
```

The `ours` strategy is justified only because G1/G2-A proved that old `main`'s
sole unique commit is content-neutral relative to its V2-reachable second parent.
If any ref or relationship changes, stop and repeat the forensic analysis rather
than reusing this command mechanically.

After migration-only files are updated and validated on the integration branch:

```powershell
git push --set-upstream origin g2-main-integration

# Run and review all canonical checks before advancing main.
git fetch origin
git merge-base --is-ancestor origin/main origin/g2-main-integration

# Normal fast-forward only; never add a force option.
git push origin g2-main-integration:main
```

`main` is already the GitHub default branch, so no default-branch setting change
is required if this sequence succeeds. After `main` is proven canonical,
`develop` may be advanced by a separate normal fast-forward because its current
SHA is already an ancestor of V2.

## 4. Future reference-migration inventory

### 4.1 Current-facing repository identity

Update these files in a future scoped migration commit:

| File | Required future change |
| --- | --- |
| `README.md` | Replace repository/origin identity and clone placeholder with canonical URL; remove wording claiming NOISYNE is final repo identity |
| `docs/ARCHITECTURE_v2.md` | Change current canonical repository identity |
| `docs/CAPABILITY_REGISTRY.md` | Change current repository identity only; preserve runtime compatibility names |
| `docs/DECISIONS_v2.md` | Change current canonical repository identity |
| `docs/EXECUTION_PLAN_v2.md` | Update repository header and identity status row |
| `docs/MODULE_MAP.md` | Update repository header only |
| `docs/PHASENOX_TECHNICAL_IDENTITY_FREEZE.md` | Freeze canonical GitHub identity as `N0ises/PHASENOX`; leave runtime compatibility matrix unchanged |
| `docs/ROADMAP_v2.md` | Update the two current repository identity references |

The actionable count remains 11 current-facing occurrences across these 8 files.

### 4.2 Stale repository assertions

Update these tests only to enforce the future canonical repository contract:

| File | Current problem | Future requirement |
| --- | --- | --- |
| `tests/test_noisyne_phase6_repository_freeze.py` | Four assertions require old README/historical repository identity | Stop treating the historical freeze report as current; assert canonical README/origin while preserving the historical file |
| `tests/test_phasenox_technical_identity_freeze.py` | One assertion freezes `N0ises/NOISYNE` as current | Require `N0ises/PHASENOX` after migration |

Do not broaden these edits into runtime identity cleanup. `NOISYNE_ROOT`,
`SOUNDBRAIN_ROOT`, `soundbrain` persistence, serialized `noisyne.*` identifiers,
legacy aliases, and `brain.*` remain separate approved compatibility contracts.

### 4.3 Historical evidence: do not edit

The following classes of files intentionally retain old repository facts:

- `docs/NOISYNE_TECHNICAL_RENAME_FREEZE.md`;
- R4-R10 rename audits and freezes;
- Sprint 17A, 19A, 22, and V2 freeze reports/manifests;
- `docs/PHASENOX_GITHUB_FINALIZATION_G1_AUDIT.md`;
- this G2-A plan after it is committed;
- old release notes, archived roadmaps, and changelogs.

The G1 report adds self-referential old/new repository strings as historical audit
evidence. Do not include those strings in the actionable current-facing count.

### 4.4 Clone URLs and remotes

Current controlled remote:

```text
https://github.com/N0ises/NOISYNE.git
```

Future canonical commands:

```powershell
git remote set-url origin https://github.com/N0ises/PHASENOX.git
git fetch origin
git remote set-head origin -a
```

Fresh clone command:

```powershell
git clone https://github.com/N0ises/PHASENOX.git
```

Update the controlled remote only after the GitHub rename succeeds. Verify the old
URL redirect, but do not rely on it as the permanent configuration. Never create a
new repository at the old slug after rename.

### 4.5 Badges and documentation links

- README contains four generic shields for Python, status, architecture, and MIT;
  none contains an owner/repository or branch name.
- No workflow, coverage, release, or package badge exists.
- Relative README/documentation links are repository-rename safe.
- No tracked `raw.githubusercontent.com` URL exists.
- No tracked repository-specific release, issue, wiki, or package URL exists.
- The LAION-CLAP research link and pre-commit tool-repository URLs are external
  dependency references, not PHASENOX repository references; retain them.

Add canonical workflow badges only after the replacement workflows exist on
`main` and have stable names. Do not add a badge for a planned or failing check.

### 4.6 Package metadata URLs

`pyproject.toml` correctly defines distribution `phasenox`, version `1.0.0`, and
CLI `phasenox`, but has no `[project.urls]` table. A future metadata commit should
add only verified destinations, for example:

```toml
[project.urls]
Repository = "https://github.com/N0ises/PHASENOX"
Issues = "https://github.com/N0ises/PHASENOX/issues"
Documentation = "https://github.com/N0ises/PHASENOX#readme"
Changelog = "https://github.com/N0ises/PHASENOX/blob/main/docs/CHANGELOG_v2.md"
```

Do not invent a Homepage until a real homepage exists. Do not change package name,
namespace, version, CLI, dependency profile, or runtime resources in this
migration.

## 5. CI migration preparation

Frozen V2 and old `main` track no workflow. GitHub's only registered workflow is
`.github/workflows/desktop-ui.yml` on the frozen `desktop-ui` branch. It is
historical, uses old `brain/ui` commands and a contaminated packaging path, and
its latest run failed. Do not merge or copy it into canonical `main`.

### Planned canonical workflow files

Create these files only in a future reviewed integration-branch commit:

1. `.github/workflows/ci-windows.yml`
   - jobs: `windows-core`, `identity-freeze`, `desktop-ui`;
   - Python 3.12 on `windows-latest`;
   - canonical `phasenox` source paths;
   - isolated-process policy for the known native test-order boundary;
   - Desktop smoke with `QT_QPA_PLATFORM=offscreen`.
2. `.github/workflows/ci-package.yml`
   - jobs: `package-build`, `fresh-install`;
   - build wheel and sdist from clean checkout;
   - install wheel in a fresh environment;
   - verify `import phasenox`, metadata `1.0.0`, and `phasenox --help`;
   - assert old CLI commands are not installed.
3. `.github/workflows/ci-release-profile.yml`
   - job: `release-profile`;
   - run identity, branding, resource, manifest, lock, and forbidden-payload
     tests that are executable without release credentials;
   - do not claim a clean-machine, signed-installer, or public-release result.

### Triggers

Preparation rollout:

- `push`: temporary `g2-main-integration`, plus `main` and `develop`;
- `pull_request`: target `main` after canonical workflows are present on `main`;
- `workflow_dispatch`: optional only after the workflow is reachable on default
  branch.

After `main` is canonical, remove the temporary integration-branch trigger through
a normal reviewed PR. Do not require a check until it has produced stable,
uniquely named successful runs.

### Action, cache, and permission policy

- Pin third-party actions to reviewed full commit SHAs, with the release tag in a
  comment for readability.
- Set minimal explicit workflow permissions, normally `contents: read`.
- Do not use repository-name assumptions or hardcoded checkout refs.
- Default checkout must use the event commit; release/provenance jobs must accept
  only an explicitly validated SHA.
- Key caches by OS, Python version, and lockfile hash. Do not reuse the historical
  generic Desktop cache as release evidence.
- Use canonical PHASENOX artifact names. Do not upload old NOISYNE/SoundBrain
  product-facing artifacts.
- Do not add signing secrets or publishing credentials during migration prep.
- Do not make the full PyInstaller/Inno build a required PR check until locked
  wheelhouses/tooling are reproducibly provisioned in CI.

### CODEOWNERS prerequisite

`.github/CODEOWNERS` currently names `@HamidCooper7`, but authenticated GitHub
inspection did not show collaborator permission for that account. Before enabling
required code-owner reviews, change CODEOWNERS in a separately reviewed commit to
an owner/team that GitHub recognizes for this repository. Do not enable a rule
that would make all PRs unmergeable.

## 6. Branch disposition plan

| Branch | Disposition | Planned handling |
| --- | --- | --- |
| `main` | **MIGRATE** | Preserve its unique merge topology, then normally fast-forward to the validated G2 integration SHA |
| `develop` | **MIGRATE** | Normally fast-forward to the post-G2 baseline after `main`; use for post-release development |
| `v2-development` | **KEEP** | Leave fixed at `bcb2a6c...`; protect later against deletion/force push |
| `desktop-ui` | **ARCHIVE** | Retain indefinitely at `e2dd11e...`; 24 unique commits; add an annotated archival tag only in an authorized tag phase |
| `v1-freeze-candidate` | **ARCHIVE** | Retain semantic branch and later annotated tag at `04b896f...` |
| `v1-ui-baseline` | **ARCHIVE** | Retain distinct semantic branch and later annotated tag at `04b896f...` |
| `agent/sprint-1-runtime-stabilization` | **DELETE_LATER** | Fully reachable from V2; retain until tag, reachability, and no-open-PR checks pass in a separate cleanup |

No branch is deleted, renamed, archived, or moved in G2-A.

## 7. Files affected by future phases

### Required edits/additions

- `README.md`
- `docs/ARCHITECTURE_v2.md`
- `docs/CAPABILITY_REGISTRY.md`
- `docs/DECISIONS_v2.md`
- `docs/EXECUTION_PLAN_v2.md`
- `docs/MODULE_MAP.md`
- `docs/PHASENOX_TECHNICAL_IDENTITY_FREEZE.md`
- `docs/ROADMAP_v2.md`
- `tests/test_noisyne_phase6_repository_freeze.py`
- `tests/test_phasenox_technical_identity_freeze.py`
- `pyproject.toml`
- `.github/CODEOWNERS`
- `.github/workflows/ci-windows.yml` (new)
- `.github/workflows/ci-package.yml` (new)
- `.github/workflows/ci-release-profile.yml` (new)

### Explicitly excluded

- production Python under `phasenox/` and compatibility shim `brain/`;
- packaging implementation, installer source, release locks, branding assets, and
  candidate artifacts;
- historical audits, freeze reports, release notes, archived roadmaps, and
  changelogs except where a current canonical link is added outside historical
  prose;
- the two protected untracked Desktop roadmap files;
- persistence, environment fallback, engine, provider, method, and digest
  identities.

## 8. Exact phased migration sequence

### G2-B — integration preparation

1. Fetch and compare every frozen SHA in section 1.
2. Confirm tracked clean state and only the two allowed untracked files.
3. Recheck authenticated availability of `N0ises/PHASENOX`.
4. Manually inspect Packages and installed GitHub Apps, which G1 could not fully
   enumerate.
5. Create local `g2-main-integration` from `origin/v2-development`.
6. Create the documented history-preservation merge and prove its tree.
7. Implement repository references/tests, package URLs, CODEOWNERS, and CI as
   small scoped commits.
8. Run local quality and regression gates.
9. Push only the integration branch; do not push `main`.

### G2-C — CI proof and branch transition

1. Require all new integration-branch workflows to complete successfully.
2. Record exact workflow/job names, run URLs, and SHA.
3. Re-fetch; ensure old `main` remains an ancestor and no remote divergence arose.
4. Advance `main` by a normal fast-forward only.
5. Verify GitHub default remains `main` and its tree/metadata are canonical.
6. Advance `develop` by a separate normal fast-forward to the approved baseline.
7. Leave `v2-development`, Desktop, V1, and agent refs unchanged.

### G2-D — identity/settings migration

1. Recheck target slug and external 18/legal 3 status.
2. Create/push archival tags only if a separately authorized tag phase permits it.
3. Rename the existing repository in place to `N0ises/PHASENOX`.
4. Update controlled remotes and verify old redirect/new canonical URL.
5. Verify issues, PRs, releases, tags, Actions, Packages, Apps, and settings.
6. After stable checks exist, apply default/archive branch rulesets.
7. Remove the temporary integration trigger through normal review.
8. Start G3 from an empty directory.

This sequence does not authorize a public release or binary upload.

## 9. Validation checkpoints

| Checkpoint | Required evidence | Stop condition |
| --- | --- | --- |
| CP0 Freeze | exact refs, clean tracked state, allowed untracked only | any SHA/status mismatch |
| CP1 Slug/integrations | target available; Packages/Apps inspected | conflict or unknown active dependency |
| CP2 Preservation merge | both histories ancestors; tree exactly `63d0e76...` before edits | tree drift or ancestry failure |
| CP3 Reference update | actionable old repo references zero; historical allowlist unchanged | unclassified reference or historical rewrite |
| CP4 Metadata | `phasenox`/`1.0.0`/CLI unchanged; canonical URLs resolve | identity/version drift |
| CP5 Local validation | targeted tests, Ruff, Black, compileall, build/fresh install, diff check | any unexplained failure |
| CP6 CI | all canonical jobs green on exact integration SHA | absent, unstable, skipped, or failed required job |
| CP7 Main transition | old main ancestor; normal fast-forward; default still `main` | divergence or force requirement |
| CP8 Rename | canonical URL works; old URL redirects; settings/refs preserved | missing ref, integration, package, or workflow |
| CP9 G3 | empty canonical clone, clean build/install/test/Desktop smoke | dependency on old URL or existing checkout |

## 10. Local validation commands for future implementation

Run proportionate gates on the migration integration branch:

```powershell
python -m pytest -q `
  tests/test_noisyne_phase6_repository_freeze.py `
  tests/test_phasenox_technical_identity_freeze.py `
  tests/test_phasenox_identity.py `
  tests/test_phasenox_distribution.py `
  tests/test_desktop_core_packaging.py

python -m ruff check tests .github tools
python -m black --check tests tools
python -m compileall -q phasenox brain tests tools
python -m build
git diff --check
```

Workflow YAML requires syntax/schema validation. Fresh-install verification must
use the built wheel in a new venv and test `import phasenox`, package metadata,
`phasenox --help`, and absence of legacy console scripts. Do not weaken identity
tests simply to make changed URLs pass.

## 11. Rollback strategy

### Before any remote integration push

- Delete only the local integration branch if a checkpoint fails.
- Return to `v2-development`; verify `bcb2a6c...` and clean tracked state.
- Do not reset or rewrite any published branch.

### After integration-branch push, before `main`

- Leave `main` untouched.
- Correct through additional scoped commits or abandon the integration branch.
- Do not merge a failing branch or convert the failure into a bypass.

### After normal `main` fast-forward, before repository rename

- Preserve published history.
- Fix metadata/CI with forward commits or temporarily choose the frozen V2 ref for
  comparison; do not force-reset `main`.
- Old `main` remains reachable through the preservation merge and archival plan.

### After repository rename

- Use GitHub's old-URL redirect as temporary recovery only.
- If a severe settings/integration defect requires renaming back, first verify the
  old slug has not been reused and record all affected integrations.
- Correct problems with forward commits/settings changes; never replace the
  repository or rewrite release history.
- Keep public release NO-GO until the independent 18 external and 3 legal/signing
  items are closed.

## 12. G2-A completion condition

G2-A is complete when:

- this plan is the only committed file;
- no repository setting or remote URL changed;
- no branch moved, merged, renamed, archived, or deleted;
- no workflow, README, test, package metadata, tag, release, or protection changed;
- nothing was pushed;
- G2-B has not started.
