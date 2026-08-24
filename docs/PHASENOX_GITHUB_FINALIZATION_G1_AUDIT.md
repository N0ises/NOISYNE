# PHASENOX Post-V2 GitHub Finalization G1 Audit

## Audit verdict

- G1 forensic audit: **PASS**
- Current repository: `N0ises/NOISYNE`
- Recommended repository: `N0ises/PHASENOX`
- Recommended default branch: `main`
- Frozen V2 engineering HEAD: `5a949daff6d679b2c87b24354ce9f9d7f885f585`
- Frozen candidate source: `3adfbab5f5dec7e5c2237febb316bc6b89459e5e`
- Critical migration blockers: **0**
- High migration blockers: **3**
- Public release: **NO-GO**

This was a read-only GitHub and repository audit. No repository, branch, default
branch, protection, workflow, tag, release, remote, or source file was changed.
The only authorized output is this report and its local documentation commit.

## Method and evidence boundary

The audit used:

- fetched Git refs and local Git object/ancestry inspection;
- the authenticated GitHub repository connector;
- authenticated GitHub REST API reads using the configured Git credential;
- tracked-file searches and direct inspection of repository metadata;
- official GitHub documentation for rename and protection behavior.

Credential material and secret values were never printed. Secret and variable
inventories contain names only; all such inventories were empty. GitHub Packages
returned HTTP 403 with the available credential and is explicitly recorded as an
unresolved visibility check rather than inferred to be empty.

## 1. Frozen-state preflight

| Check | Observed | Result |
| --- | --- | --- |
| Branch | `v2-development` | PASS |
| Local HEAD | `5a949daff6d679b2c87b24354ce9f9d7f885f585` | PASS |
| `origin/v2-development` | `5a949daff6d679b2c87b24354ce9f9d7f885f585` | PASS |
| Ahead/behind | `0 / 0` | PASS |
| Tracked tree/index | clean | PASS |
| Untracked | two protected Desktop roadmap files only | PASS |

Protected remote snapshots:

| Branch | SHA |
| --- | --- |
| `desktop-ui` | `e2dd11e4193f32cd4f31cda5bca8cbd322bec3af` |
| `main` | `a1946dd838d4918cac5d78f906719e62a9dbcc32` |
| `develop` | `53bd19802593905ec7ff20144bff0fc35b23d92b` |
| `v1-freeze-candidate` | `04b896f151e17e9d4cf35b31afc4e68a254e0306` |
| `v1-ui-baseline` | `04b896f151e17e9d4cf35b31afc4e68a254e0306` |

## 2. Current GitHub repository settings

Authenticated observation of repository ID `1301844155`:

| Setting | Current state | G2 disposition |
| --- | --- | --- |
| Owner/name | `N0ises/NOISYNE` | Rename to `N0ises/PHASENOX` after canonical `main` is proven |
| Visibility | public | Keep |
| Description | Modular AI audio platform description; no legacy product name | Optionally prefix with PHASENØX |
| Homepage | empty | Decide explicitly; do not invent one |
| Topics | `ai`, `audio`, `audio-analysis`, `audio-intelligence`, `clap`, `llm`, `machine-learning`, `mastering`, `mixing`, `music`, `python`, `qwen`, `rag` | Add `phasenox`; otherwise review semantically |
| Default branch | `main` | Keep name; advance safely to a V2-derived integration commit |
| Archived | false | Keep |
| Issues | enabled; zero issues | Keep enabled |
| Projects | enabled | Review whether needed; no migration change required |
| Wiki | disabled | Keep unless separately requested |
| Discussions | disabled | Keep unless separately requested |
| Pages | disabled; Pages endpoint 404 | No Pages migration |
| Stars/forks/watchers | 2 / 0 / 0 | Preserved by GitHub rename |
| Open pull requests | 0 | No active PR branch dependency |
| Historical pull requests | 1 closed | Preserve through repository rename |
| Merge methods | merge, squash, and rebase enabled | Review after canonical CI exists |
| Auto-merge | disabled | Keep initially |
| Delete branch on merge | disabled | Keep through migration |
| Web commit signoff | not required | Do not change in G1/G2 without policy decision |

### Protection and automation settings

| Area | Current state |
| --- | --- |
| Repository rulesets | 0 |
| Branch protection rules | none on all seven branches |
| Actions | enabled; all actions allowed |
| Action SHA-pinning policy | not required |
| Environments | 0 |
| Actions secret names | 0 |
| Actions variable names | 0 |
| Dependabot secret names | 0 |
| Webhooks | 0 |
| Deploy keys | 0 |
| Custom social preview | not configured/endpoint 404 |

### Security and advisory settings

| Setting | Current state |
| --- | --- |
| Automated security fixes | enabled |
| Dependabot security updates | disabled |
| Tracked `.github/dependabot.yml` | absent |
| Dependabot alerts | not observable; API returned 403 |
| Secret scanning | disabled |
| Secret scanning push protection | disabled |
| Non-provider secret patterns | disabled |
| Secret validity checks | disabled |
| Code scanning default setup | not configured; Python detected |
| Private vulnerability reporting | disabled |
| Repository security advisories | 0 |

GitHub Packages could not be inventoried with the current credential (`403` for
container, npm, Maven, RubyGems, and NuGet). G2 must perform a manual authenticated
Packages-tab/API check before the repository rename. This is a known review item,
not evidence that packages exist.

## 3. Complete remote branch inventory

`origin/HEAD` is a symbolic ref and is excluded. There are seven real remote
branches.

| Branch | HEAD | Relationship to frozen V2 | Unique branch / unique V2 commits | Purpose/state | Protection | Disposition |
| --- | --- | --- | ---: | --- | --- | --- |
| `v2-development` | `5a949daff6d679b2c87b24354ce9f9d7f885f585` | exact target | 0 / 0 | Frozen V2 engineering baseline | none | **KEEP** immutable |
| `main` | `a1946dd838d4918cac5d78f906719e62a9dbcc32` | diverged at `62a3631`; neither is ancestor | 1 / 114 | Current default; historical V1 merge | none | **MIGRATE** through preservation merge |
| `develop` | `53bd19802593905ec7ff20144bff0fc35b23d92b` | ancestor of V2 | 0 / 126 | Old development baseline | none | **MIGRATE** by normal fast-forward after `main` |
| `desktop-ui` | `e2dd11e4193f32cd4f31cda5bca8cbd322bec3af` | diverged from `04b896f`; neither is ancestor | 24 / 112 | Frozen V1 Desktop release history | none | **ARCHIVE**; retain branch and add immutable tag |
| `v1-freeze-candidate` | `04b896f151e17e9d4cf35b31afc4e68a254e0306` | ancestor of V2 | 0 / 112 | Semantic V1 freeze reference | none | **ARCHIVE**; retain branch and add tag |
| `v1-ui-baseline` | `04b896f151e17e9d4cf35b31afc4e68a254e0306` | ancestor of V2 | 0 / 112 | Semantic V1 UI baseline reference | none | **ARCHIVE**; retain branch and add tag |
| `agent/sprint-1-runtime-stabilization` | `35db097802cd471ff6afcc2265a394c148cdd2e3` | ancestor of V2 | 0 / 127 | Fully merged agent branch; no open PR | none | **DELETE_LATER** only after tag/reachability verification |

Disposition counts:

- KEEP: **1**
- ARCHIVE: **3**
- MIGRATE: **2**
- DELETE_LATER: **1**
- UNKNOWN_REVIEW_REQUIRED: **0 branches**

## 4. Branch ancestry and history safety

Simplified relationship graph:

```text
agent/sprint-1-runtime-stabilization (35db097)
                |
develop (53bd198)
                |
         ... 62a3631 ...
           |            \
           |             main merge (a1946dd)
           |             tree == 62a3631 tree
           |
v1 freeze/UI baseline (04b896f)
           |\
           | \-- desktop-ui -- 24 unique commits --> e2dd11e
           |
           \-- V2 development -- 112 later commits --> 5a949da
```

The sole `main`-unique commit is GitHub merge commit `a1946dd`. Its tree
`7286640e...` exactly equals its second parent `62a3631`, and that second parent is
already an ancestor of frozen V2. The commit is audit history, not unique file
content. A direct `main -> v2-development` push is nevertheless not a
fast-forward because the merge commit itself is not in V2 ancestry.

Frozen V2 tree: `2d8206b8b8902b3ee065f6e361d07c1fac10d1da`.

Final V2 can become canonical `main` without force-pushing or losing history by
creating one explicit integration merge whose first parent is frozen V2 and whose
second-side history contains old `main`. Before repository-metadata updates, the
merge must retain the frozen V2 tree byte-for-byte.

## 5. Branch strategy evaluation

| Option | History safety | Clone/default behavior | CI/protection effect | Verdict |
| --- | --- | --- | --- | --- |
| Directly push V2 to `main` | Not fast-forward; would require force or lose `a1946dd` | Simple only after unsafe rewrite | No V2 CI exists | Reject |
| Change default branch to `v2-development` | Preserves history but leaves noncanonical long-lived default | New clones land on a development-named freeze branch | Existing Desktop workflow still irrelevant | Not preferred |
| Merge old `main` into a V2-derived integration branch, then fast-forward `main` | Preserves every commit; no rewrite; frozen tree can be proven | Canonical clones remain on `main` | Allows new CI to be proven before switch | **Recommended** |
| Replace repository or create a new repo | Risks losing issues, stars, redirects, and audit continuity | New identity but fractured history | Duplicates settings | Reject |

### Recommended final state

1. `main` is the default canonical branch and contains all old `main` and V2
   history through a new preservation merge plus reviewed G2 metadata/CI commits.
2. `v2-development` remains fixed at `5a949da...` as the immutable engineering
   freeze.
3. `develop` is normally fast-forwarded to the post-G2 canonical `main` SHA and
   becomes the post-release development baseline.
4. The repository is renamed in place to `N0ises/PHASENOX` only after canonical
   `main` passes CI.
5. V1/Desktop branches remain available as historical evidence with annotated
   archival tags.

The exact final `main` SHA cannot exist during a read-only G1 audit: it will be the
new G2 integration/metadata SHA. Its frozen content parent must be
`5a949daff6d679b2c87b24354ce9f9d7f885f585`, and its history must include
`a1946dd838d4918cac5d78f906719e62a9dbcc32`. No operation should predeclare a
fabricated commit hash.

## 6. V1 and Desktop history preservation

The frozen `desktop-ui` branch has 24 commits that are not reachable from V2.
Deleting it without another immutable reference would destroy reachability of
real release evidence. Retain it indefinitely and add an annotated archival tag
at `e2dd11e...`.

`v1-freeze-candidate` and `v1-ui-baseline` point to the same SHA but express
different audit meanings. Retain both branch names and add distinct annotated
tags. Do not collapse their semantics merely because their commit IDs match.

Recommended G2 archival tags, subject to explicit G2 authorization:

- `v2-engineering-freeze` -> `5a949da...`
- `archive/main-pre-phasenox` -> `a1946dd...`
- `archive/desktop-ui-v1-freeze` -> `e2dd11e...`
- `archive/v1-freeze-candidate` -> `04b896f...`
- `archive/v1-ui-baseline` -> `04b896f...`
- `archive/develop-pre-v2` -> `53bd198...`
- `archive/agent-sprint-1-runtime-stabilization` -> `35db097...`

No branch deletion belongs in the main migration transaction. The agent branch
may be deleted in a later cleanup only after its tag is pushed, remote reachability
is verified, and open-PR dependency remains zero.

## 7. Repository-name reference inventory

There are **30 exact tracked occurrences** of `N0ises/NOISYNE`.

| Classification | Occurrences | Files | G2 handling |
| --- | ---: | ---: | --- |
| CURRENT_GITHUB_REFERENCE | 11 | 8 | Update to `N0ises/PHASENOX`/canonical URL |
| HISTORICAL_EVIDENCE | 14 | 11 | Preserve unchanged |
| COMPATIBILITY | 0 | 0 | Repository identity is not a runtime compatibility contract |
| STALE | 5 | 2 tests | Replace old repository assertions with canonical migration assertions |

Current-facing files requiring G2 updates:

- `README.md` (2)
- `docs/ARCHITECTURE_v2.md` (1)
- `docs/CAPABILITY_REGISTRY.md` (1)
- `docs/DECISIONS_v2.md` (1)
- `docs/EXECUTION_PLAN_v2.md` (2)
- `docs/MODULE_MAP.md` (1)
- `docs/PHASENOX_TECHNICAL_IDENTITY_FREEZE.md` (1)
- `docs/ROADMAP_v2.md` (2)

Stale enforcement appears in:

- `tests/test_noisyne_phase6_repository_freeze.py` (4)
- `tests/test_phasenox_technical_identity_freeze.py` (1)

Historical occurrences are confined to completed rename audits, prior freeze
records, and Sprint reports. They must remain factual snapshots. There is also one
non-hardcoded but stale clone placeholder (`git clone <repository-url>`) in
`README.md`; replace it with the canonical clone URL in G2.

No tracked raw.githubusercontent URL, GitHub Actions URL, release-download URL,
issue URL, wiki URL, package URL, SSH clone URL, submodule, or repository-specific
badge was found. Four README badges are generic shields and need no rename change.

## 8. README and public-document inventory

| Document | Exists | Current assessment |
| --- | --- | --- |
| `README.md` | yes | Current-facing; canonical product naming is good, but repo block and clone command require G2 update |
| `CONTRIBUTING.md` | yes | Current-facing; no hardcoded repo URL |
| `LICENSE` | yes | MIT; no migration change |
| `SECURITY.md` | no | `docs/SECURITY_v2.md` exists; consider canonical root entry point in G2 |
| `CHANGELOG.md` | no | `docs/CHANGELOG_v2.md` exists; preserve history and decide canonical root entry point |
| `CODE_OF_CONDUCT.md` | no | `docs/CODE_OF_CONDUCT_v2.md` exists |
| `SUPPORT.md` | no | `docs/SUPPORT_v2.md` exists |
| Release notes | `docs/RELEASE_NOTES.md` | Historical/current mix; review links, do not rewrite old release facts |
| Architecture | current V2 docs exist | Eight current files contain old repository identity as listed above |

Additional READMEs exist under `assets/brand`, `docs/bible`, `tools`,
`tools/ableton`, and `tools/packaging`. No hardcoded old GitHub URL was found in
them. Historical audits, freeze reports, archived roadmaps, and changelogs should
not be globally rewritten.

## 9. Package metadata and version consistency

`pyproject.toml` is canonical for package identity:

- distribution: `phasenox`;
- version: `1.0.0`;
- CLI: `phasenox`;
- namespace discovery: `phasenox*` plus compatibility package `brain`;
- description: PHASENØX;
- no legacy CLI entry point.

There is no `[project.urls]` table. G2 should add canonical Homepage/Repository,
Issues, Documentation, and Changelog links only after choosing actual destinations.
Do not change the package namespace.

Version `1.0.0` is consistent across the project metadata, PE ProductVersion,
installer version, bundle/installer names, and the frozen evidence. The Windows
FileVersion is the derived numeric `1.0.0.0`. “V2” names the engineering roadmap;
it does not establish a `2.0.0` product version.

## 10. GitHub Actions and `.github` audit

Frozen V2 tracks no workflow. GitHub reports one active workflow because
`.github/workflows/desktop-ui.yml` exists only on `desktop-ui`.

### Existing Desktop UI workflow

- Trigger: push to `desktop-ui`; path-filtered pull requests.
- Runner/jobs: `windows-latest`, Qt tests and a Windows packaging job.
- External actions: `actions/checkout@v4`, `actions/setup-python@v5`; mutable tags,
  not commit-SHA pinned.
- Cache: setup-python `pip` cache with no release-profile-specific key.
- Secrets: none referenced.
- Artifacts/releases: no upload or release logic.
- Stale paths: `brain/ui`, old UI tests, and `python -m brain.ui`.
- Stale packaging: installs heavy optional dependencies and invokes historical
  `build_windows.ps1 -Profile shell`; it is not the locked Desktop Core pipeline.
- Runs: 21 total. The final two runs, including frozen `desktop-ui` HEAD, failed.

### Six migration issues

1. No workflow is tracked on frozen V2 or current `main`.
2. Existing triggers cover only `desktop-ui`, not canonical `main`,
   `v2-development`, or a G2 integration branch.
3. Test/lint/import paths use the old `brain/ui` implementation boundary.
4. The packaging job violates the locked Desktop Core dependency/profile design.
5. Actions are referenced by mutable version tags while repository policy permits
   all actions and does not require SHA pinning.
6. The last frozen Desktop workflow run failed, so it cannot be made a required
   status check or treated as current evidence.

A repository rename itself does not introduce a hardcoded repo-name failure in
this workflow. Replacing `main` with V2-derived content does: the workflow file
would disappear and its commands do not describe the canonical codebase.

### Other `.github` configuration

Only `.github/CODEOWNERS` is tracked on V2. It maps all files to
`@HamidCooper7`, but the collaborator-permission endpoint returns 404 for that
account in this repository. Resolve the owner to an account/team with repository
permission before requiring code-owner review.

Absent: Dependabot configuration, issue templates, pull-request template,
FUNDING, release configuration, and local composite actions.

## 11. Canonical repository slug decision

Recommended slug: **`N0ises/PHASENOX`**.

- `PHASENOX` uses valid ASCII slug characters.
- GitHub repository name matching is case-insensitive; use uppercase spelling as
  display convention, not as a separate identity.
- An authenticated API lookup returned 404 for `N0ises/PHASENOX`, so the slug was
  available at audit time.
- Recheck immediately before rename because availability is time-sensitive.

Do not create a second repository. Rename the existing repository in place to
retain its issues, stars, watchers, releases, tags, and audit continuity.

## 12. Rename and redirect risk

GitHub documents that repository renames redirect web information and old
`clone`/`fetch`/`push` locations, but recommends updating local remotes. Project
site URLs are an exception, and calls to an action hosted in a renamed repository
do not redirect. GitHub also warns not to reuse the old slug, because doing so
breaks the redirect. See [Renaming a repository](https://docs.github.com/en/enterprise-cloud@latest/repositories/creating-and-managing-repositories/renaming-a-repository)
and [Managing remote repositories](https://docs.github.com/en/get-started/git-basics/managing-remote-repositories).

Project-specific impact:

| Surface | Current evidence | Migration action |
| --- | --- | --- |
| Clone/fetch/push URLs | one HTTPS origin and README URL | Update to canonical URL; verify old redirect, do not rely on it indefinitely |
| Forks | 0 | No fork coordination currently required |
| Stars/watchers | 2 / 0 | GitHub rename retains them |
| Issues/PRs | 0 issues, 1 closed PR | Rename retains history |
| Actions | one stale branch-only workflow | Replace before main switch; repository does not publish an `action.yml` action |
| Releases/tags | 1 release, 12 tags | Retain; do not reinterpret old SoundBrain release |
| Webhooks/deploy keys | 0 / 0 | No endpoint/key migration |
| Pages | disabled | No Pages URL risk |
| Raw URLs | none tracked | No tracked raw-link rewrite |
| Submodules/LFS | none | No URL migration |
| Packages | API visibility denied | Manually verify before rename and validate linkage afterward |
| GitHub Apps | repository-wide installation inventory not exposed by this credential | Review installed-app settings before rename |
| Badges | generic only | Add canonical CI badges only after workflows exist and pass |

## 13. Releases, tags, and artifact policy

Current GitHub state:

- one public release: `SoundBrain v1.0.0`, tag `v1.0.0`, wheel asset
  `soundbrain-1.0.0-py3-none-any.whl`;
- 12 tags total, including the old `v1.0.0`, `v1.0.0-rc1`, roadmap/sprint tags,
  and `runtime-v1-stable`;
- no current GitHub Actions artifacts.

Do not reuse or move the existing `v1.0.0` tag. Recommended separation:

1. G2 archival engineering tag `v2-engineering-freeze` at `5a949da...`; this is
   not a product-version claim.
2. If external acceptance and legal/signing later pass, use namespaced product
   tags such as `phasenox-v1.0.0-rc.1` and `phasenox-v1.0.0`, pointing to the
   exact authorized release source. Do not invent `v2.0.0` from roadmap naming.

An eventual PHASENØX GitHub Release should include:

- the signed/authorized installer;
- canonical SHA256SUMS;
- CycloneDX SBOM;
- third-party license inventory;
- release manifest.

Do not publish `PHASENOX.exe` alone; it belongs to the one-folder bundle. Do not
publish the whole one-folder bundle by default unless a portable distribution is
explicitly supported and the verified directory is archived with its manifest.
The installer remains the canonical end-user artifact.

Frozen unsigned RC hashes, for provenance only:

- `PHASENOX.exe`:
  `753da4c1336467b8a8fca6d7eb9ee9b7b2cbe1b3045466e1dafdd09e8fa80c48`
- installer:
  `a30d30a4b92b7060c9e93a230c4bb291e46168b70f5379e8dbeeb3370b2e59c0`

## 14. Recommended branch protection

There is nothing to “migrate”; protections are absent. Establish protection only
after canonical workflows have produced stable, uniquely named checks. GitHub
warns that required checks must actually exist and that check names must be
unambiguous. See [About protected branches](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches)
and [Creating rulesets](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/creating-rulesets-for-a-repository).

Recommended minimum default-branch ruleset:

- target the default branch (`main`);
- block force pushes;
- block deletion;
- require pull requests for normal development;
- require conversation resolution;
- require only checks that have passed repeatedly on the canonical workflow;
- initially require one approval only if a valid reviewer/owner exists;
- define administrator bypass as an explicit emergency policy, not a silent
  permanent bypass;
- do not require signed commits until the project makes and validates that policy.

Protect frozen/archive branches against force push and deletion. They do not need
the same PR/status-check policy as active `main`.

## 15. Exact G2 operation sequence

G2 must be separately authorized. Execute it as staged, stop-on-failure work:

1. Re-fetch and prove every SHA, clean tracked state, target-slug availability,
   zero open PR dependencies, and the 18/3 public-release NO-GO status.
2. Manually verify Packages and installed GitHub Apps, which G1 could not fully
   enumerate.
3. Create and locally verify the seven annotated archival/freeze tags listed in
   section 6; do not push them until their target SHAs are rechecked.
4. Create `g2-main-integration` from frozen `5a949da...`.
5. Merge old `origin/main` with an explicit no-fast-forward history-preservation
   merge that retains the V2 tree (for example, a documented `ours` strategy
   merge). Verify:
   - old `main` is an ancestor of the result;
   - frozen V2 is an ancestor of the result;
   - before metadata edits, the result tree equals
     `2d8206b8b8902b3ee065f6e361d07c1fac10d1da`.
6. On the integration branch, make scoped G2 commits for:
   - eight current-facing repository references and the README clone command;
   - the two stale identity test files while preserving historical documents;
   - canonical `[project.urls]` metadata;
   - a valid CODEOWNERS principal;
   - new canonical workflows.
7. New workflows must provide distinct checks for Windows/core tests, identity
   freeze, Desktop tests/smoke, wheel build plus fresh-install import/CLI, and
   release-profile/forbidden-payload validation. Use canonical `phasenox` paths,
   pin third-party actions to reviewed commit SHAs, and avoid the historical
   heavy packaging job.
8. Push only the integration branch and run all new checks. Do not advance `main`
   while any check is absent, unstable, or failing.
9. Push the integration SHA to `main` as a **normal fast-forward**. No force,
   rebase, squash, or history rewrite. The default branch name already is `main`,
   so no default-branch switch should be needed.
10. Verify canonical `main`, then fast-forward `develop` normally to the same
    post-G2 baseline. Keep `v2-development` fixed at `5a949da...`.
11. Push verified archival tags. Retain Desktop/V1 branches; defer any agent-branch
    deletion to a later cleanup.
12. Recheck `N0ises/PHASENOX` availability and rename the existing repository in
    place. Never create/reuse `N0ises/NOISYNE` afterward.
13. Update the local remote:

    ```powershell
    git remote set-url origin https://github.com/N0ises/PHASENOX.git
    git fetch origin
    git remote set-head origin -a
    ```

14. Verify the canonical URL, old-URL redirect, refs, release/tag history,
    settings, Pages-disabled state, packages/apps, and workflow runs.
15. After stable check names exist, activate the `main` and archive protection
    rulesets described above.
16. Run G3 from an empty directory. Do not claim migration complete until it
    passes.

## 16. G3 fresh-clone verification plan

From a newly created empty directory on a clean validation host:

1. `git clone https://github.com/N0ises/PHASENOX.git` without using the old URL.
2. Verify clean status, branch `main`, canonical origin, expected final G2 SHA,
   default remote HEAD, and full `git fsck`.
3. Verify `v2-development` and every archival tag resolve to their recorded SHAs,
   especially `desktop-ui` evidence `e2dd11e...`.
4. Search the fresh checkout for current-facing old repository URLs; permit only
   classified historical evidence.
5. With Python 3.12, create a fresh build venv and run `python -m build`.
6. In a second clean venv, install the generated `phasenox` wheel and verify:
   - `import phasenox`;
   - `importlib.metadata.version("phasenox") == "1.0.0"`;
   - `phasenox --help`;
   - no `noisyne` or `soundbrain` console scripts.
7. Run identity freeze, compatibility, application-root, persistence safety,
   Desktop, application-service, scheduler, packaging/distribution, and relevant
   full regression tests using the established isolated-process policy.
8. Launch the developer Desktop smoke path with
   `python -m phasenox.ui --smoke-test` from an arbitrary working directory.
9. Confirm all canonical CI checks run from zero on `main` and pass on Windows;
   do not count the old Desktop UI workflow.
10. Confirm no test/build command depends on the old repository URL, local build
    paths, existing venv, untracked roadmap files, or redirected origin.

## 17. CI-from-zero target

The current repository does **not** provide this coverage. G2 must create it; G3
must prove it. Minimum distinct checks:

1. Windows Python/core regression.
2. PHASENOX identity and compatibility freeze.
3. Desktop UI tests and smoke launch.
4. Wheel/sdist build and fresh-install import/CLI verification.
5. Desktop Core profile, resource, manifest, and forbidden-dependency guard tests.

Do not make a full PyInstaller/Inno release build a required PR check unless its
locked wheelhouses and licensed tooling are reproducibly provisioned in CI.
Static/profile validation may be required while signed/final packaging remains a
controlled release workflow.

## 18. Rollback strategy

- Before `main` advancement: delete only the unmerged integration branch if G2
  fails; all published refs remain unchanged.
- If the preservation merge does not keep the frozen tree: discard the local
  integration branch and investigate. Never repair with force push.
- If canonical CI fails: do not advance `main` or rename the repository.
- After `main` fast-forward but before rename: retain `v2-development` and archival
  tags; correct metadata through new forward commits or temporarily select the
  frozen branch as default. Do not reset published history.
- After repository rename: old URLs provide a temporary redirect, but update all
  controlled remotes immediately. If a severe settings/integration issue requires
  renaming back, preserve the new slug and audit redirects before doing so; never
  create a replacement repository at the old slug.
- If a ruleset blocks recovery: use only the documented administrator emergency
  bypass, record the operation, make a forward fix, and restore enforcement.
- No rollback step changes candidate data, releases binaries, or alters the
  public-release verdict.

## 19. Migration blockers and decisions

### High migration blockers: 3

1. `main` diverges by one unique historical merge commit, so a direct fast-forward
   is impossible until the preservation merge is created.
2. Frozen V2 has no CI workflow; the only registered workflow is stale and its
   latest frozen run failed.
3. No branch is protected, and CODEOWNERS names an account without observable
   collaborator permission; protection cannot safely require current checks or
   owners until G2 repairs both.

### Medium/required review items

- GitHub Packages inventory unavailable with the current API scope.
- Installed GitHub Apps are not completely enumerable with the available
  credential.
- Actions permits all actions without SHA-pinning enforcement.
- Secret scanning, push protection, code scanning, and private vulnerability
  reporting are disabled.
- Root-standard community-health files are incomplete even though equivalent V2
  documents exist under `docs/`.

### Critical migration blockers: 0

The canonical slug was available at audit time, the operator has repository admin
permission, no open PR depends on a branch, the V2 remote is synchronized, and a
non-rewriting branch strategy exists. High items must still be closed in G2 before
the rename transaction.

## 20. Public-release boundary

- External Windows acceptance: **18 PENDING**
- Legal/signing: **3 PENDING**
- Public release: **NO-GO**
- Candidate signing status: **UNSIGNED**

Repository/branch migration can proceed independently after G2 authorization, but
must not create a final public release, upload binaries, move the old `v1.0.0`
tag, or imply that acceptance/signing gates have passed.
