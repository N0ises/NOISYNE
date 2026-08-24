# PHASENOX GitHub Finalization G2-D Report

## Finalization status

- G2-D repository finalization: **PASS pending this report PR**
- Canonical repository: `N0ises/PHASENOX`
- Default branch: `main`
- Public release: **NO-GO**
- External Windows acceptance: **18 PENDING**
- Legal/signing items: **3 PENDING**

G2-D preserves historical evidence, removes only proven-redundant operational
branches, establishes practical canonical-main protection, and prepares the
repository for G3 fresh-clone verification. It does not alter PHASENOX shipping
source, publish a product release, or rewrite history.

## Branch inventory and disposition

The post-G2-C inventory contained nine remote branches. Every branch was checked
against `main` for ancestry, unique commits, open pull-request dependency, and
protection state.

| Branch | Audited SHA | Relationship at inventory | Unique branch commits | Final disposition |
| --- | --- | --- | ---: | --- |
| `main` | `8d6a3a96fe94ae45a0c7d68173e0b09ae178d942` | canonical | 0 | KEEP_ACTIVE |
| `develop` | `53bd19802593905ec7ff20144bff0fc35b23d92b` | ancestor of main | 0 | KEEP_ACTIVE; fast-forwarded to canonical main |
| `v2-development` | `3b9272790ad1cbea5b89947761ceecb52a32cb89` | ancestor of main | 0 | KEEP_ARCHIVAL through G3 |
| `desktop-ui` | `e2dd11e4193f32cd4f31cda5bca8cbd322bec3af` | diverged; 24 unique commits | 24 | KEEP_ARCHIVAL plus immutable tag |
| `v1-freeze-candidate` | `04b896f151e17e9d4cf35b31afc4e68a254e0306` | ancestor of main | 0 | KEEP_ARCHIVAL plus immutable tag |
| `v1-ui-baseline` | `04b896f151e17e9d4cf35b31afc4e68a254e0306` | ancestor of main | 0 | KEEP_ARCHIVAL plus immutable tag |
| `g2-main-integration` | `b6a40ccf464f1bda15fd9fe9e547e85c912fc3b0` | one unique evidence commit | 1 | MERGE_EVIDENCE_THEN_DELETE |
| `g2-repo-migration` | `0e925f5208a392ea424c5879c12d322805d0cb75` | one unique evidence commit | 1 | MERGE_EVIDENCE_THEN_DELETE |
| `agent/sprint-1-runtime-stabilization` | `35db097802cd471ff6afcc2265a394c148cdd2e3` | ancestor of main | 0 | TAG_THEN_DELETE |

No branch had an open PR dependency at inventory time. All branches were
unprotected before G2-D.

The two unique G2 report commits were merged through
`g2-repo-finalization`. PR #2 passed canonical CI and merged normally as
`3285a9ab21854c911a1e1fa93d7c6454399fb70e`. Both former G2 tips are ancestors of
that main commit, and their report files are reachable from canonical history.

Deleted after reachability proof:

- `g2-main-integration`;
- `g2-repo-migration`;
- `agent/sprint-1-runtime-stabilization`.

The report branch `g2-repo-finalization` is temporary and must be deleted only
after this report reaches protected `main`. Final intended branch count: six.

## Archival and engineering-freeze tags

Seven annotated, non-product tags were created and independently verified by
their peeled remote targets:

| Tag | Target |
| --- | --- |
| `v2-engineering-freeze` | `5a949daff6d679b2c87b24354ce9f9d7f885f585` |
| `archive/main-pre-phasenox` | `a1946dd838d4918cac5d78f906719e62a9dbcc32` |
| `archive/desktop-ui-v1-freeze` | `e2dd11e4193f32cd4f31cda5bca8cbd322bec3af` |
| `archive/v1-freeze-candidate` | `04b896f151e17e9d4cf35b31afc4e68a254e0306` |
| `archive/v1-ui-baseline` | `04b896f151e17e9d4cf35b31afc4e68a254e0306` |
| `archive/develop-pre-v2` | `53bd19802593905ec7ff20144bff0fc35b23d92b` |
| `archive/agent-sprint-1-runtime-stabilization` | `35db097802cd471ff6afcc2265a394c148cdd2e3` |

The engineering-freeze target is the exact baseline specified by both the V2
freeze manifest and G1 audit. It is not the later migration/report SHA and is not
a product-version claim. Existing tags, especially `v1.0.0`, were not moved.
Remote tag count is 19; GitHub release count remains one historical release. No
GitHub Release or product release tag was created.

## Main protection

Canonical `main` protection is enabled with:

- strict required status check `Windows identity and distribution`, bound to
  GitHub Actions app ID `15368`;
- pull requests required before merging;
- zero mandatory approvals, avoiding an impossible self-approval policy;
- stale approvals dismissed after changes;
- code-owner review not required;
- conversation resolution required;
- force pushes blocked;
- branch deletion blocked;
- signed commits not required;
- linear history not required, preserving reviewed merge history;
- no user/team push restriction, which is unsupported for this user-owned repo.

`enforce_admins` is false. The repository owner/admin therefore retains an
emergency recovery bypass. Normal work must use PRs and the required check; an
admin bypass is reserved for documented recovery and must be followed by a
forward fix and audit record.

The protection API initially rejected organization-only empty restriction fields.
No partial policy was applied. The final accepted policy uses `restrictions: null`
and omits review dismissal/bypass user/team lists, while preserving all required
safety controls above.

## Actions settings and CI

Actions remain enabled but are narrowed from `all` actions to selected actions:

- GitHub-owned actions allowed;
- verified Marketplace actions not broadly allowed;
- no additional patterns allowed;
- default workflow token permission: read;
- workflows cannot approve pull requests;
- no secrets introduced.

The canonical workflow uses only `actions/checkout` and `actions/setup-python`, so
this restriction does not make the required check impossible.

CI evidence:

| Run | Event / SHA | Result |
| --- | --- | --- |
| `32749199431` | G2-C main push / `8d6a3a9...` | PASS |
| `32768789804` | G2 evidence-preservation PR / `14f9214...` | PASS |
| `32769027502` | evidence merge on main / `3285a9a...` | PASS |

The report PR must also pass the same required check before merge. External clean-
machine Windows acceptance is not represented by this CI and remains pending.

## Repository metadata

- Repository name: `PHASENOX`;
- repository ID: `1301844155`;
- visibility: public;
- default branch: `main`;
- description: canonical modular audio-platform description with no legacy name;
- homepage: intentionally empty;
- topics: existing audio/AI topics plus canonical `phasenox`;
- issues: enabled;
- origin: `https://github.com/N0ises/PHASENOX.git`.

No stale repository identity remains in current GitHub metadata, and no marketing,
company, publisher, or legal identity was invented.

## Reference census and historical preservation

Canonical main census before this report:

| Classification | Count |
| --- | ---: |
| Current-facing old repository references | 0 |
| Stale old repository references | 0 |
| Exact old-slug literals across all tracked historical/guard files | 25 |
| Canonical references in the active allowlist | 14 |

The remaining old-slug literals are factual historical evidence or negative
regression guards. No current-facing URL depends on the rename redirect.

History preservation checks confirm canonical main contains:

- old-main merge history;
- authoritative V2 engineering freeze;
- final shipping candidate source;
- G2-A, G2-B, and G2-C migration evidence;
- both unique temporary-branch report commits.

Desktop/V1 auditability is retained by both archival branches and verified
annotated tags. The agent branch is retained by main ancestry and its archival
tag after branch deletion.

## Remaining G3 work

G3 must perform fresh-clone verification from the canonical URL in a new empty
directory, verify default `main`, refs/tags/history, run clean package build and
fresh-wheel acceptance, repeat the current-reference census, and confirm the
required canonical CI/protection behavior from zero. G3 must not reinterpret
engineering tags as product releases.

External Windows acceptance remains **18 PENDING**, legal/signing remains
**3 PENDING**, and public release remains **NO-GO**.

## Rollback and recovery notes

Published history must not be reset or force-updated. Correct defects with
reviewed forward commits. Deleted branch histories remain reachable through main
or exact archival tags and can be reconstructed only through a separately audited
operation. The old develop tip is preserved by `archive/develop-pre-v2`; the agent
tip is preserved by its archive tag; Desktop/V1 branches remain present.

If protection blocks emergency recovery, the owner/admin may use the documented
bypass because `enforce_admins` is false, then immediately restore normal PR/check
flow and record the intervention. Do not weaken or delete the required check in
ordinary work.
