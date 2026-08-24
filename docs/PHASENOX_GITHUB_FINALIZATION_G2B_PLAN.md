# PHASENOX GitHub Finalization G2-B Main Transition Plan

## Phase status

- Phase: **G2-B transition preparation only**
- Repository: `N0ises/NOISYNE`
- Local integration branch: `g2-main-integration`
- Integration branch created from local `v2-development`:
  `3b9272790ad1cbea5b89947761ceecb52a32cb89`
- Current remote `main`:
  `a1946dd838d4918cac5d78f906719e62a9dbcc32`
- Merge executed: **no**
- Push executed: **no**
- Repository/default-branch migration executed: **no**

This document specifies the future local preservation merge. It does not
authorize pushing the integration branch, advancing `main`, renaming the
repository, changing the default branch, or altering protected historical refs.

## 1. Branch creation proof

The local branch was created with:

```powershell
git switch --create g2-main-integration v2-development
```

Immediately after creation:

```text
g2-main-integration = 3b9272790ad1cbea5b89947761ceecb52a32cb89
v2-development     = 3b9272790ad1cbea5b89947761ceecb52a32cb89
```

No remote branch named `g2-main-integration` was created. The local
`v2-development` ref was not moved.

## 2. Main history analysis

### Ancestry

| Item | Observed value |
| --- | --- |
| Integration/V2 parent | `3b9272790ad1cbea5b89947761ceecb52a32cb89` |
| Old `main` | `a1946dd838d4918cac5d78f906719e62a9dbcc32` |
| Merge base | `62a3631db856538484b7ba047769a5b08b0a41c2` |
| Commits unique to old `main` | 1 |
| Commits unique to integration branch | 116 |
| Direct fast-forward possible in either direction | no |

The single old-`main`-unique commit is:

```text
a1946dd838d4918cac5d78f906719e62a9dbcc32
Merge pull request #1 from HamidCooper7/agent/sprint-3-core-integration
```

Its parents are:

1. `b101d4f3522b152869d00e4dfe2253bf208c38a1`
2. `62a3631db856538484b7ba047769a5b08b0a41c2`

The second parent is already reachable from the integration/V2 lineage. Old
`main`'s tree is `7286640e4a2dbf401dc2f99a885ae8be6bf5a504`, exactly equal to that second
parent's tree. The unique merge commit therefore contributes historical topology
but no file content that is absent from V2.

### Read-only merge simulation

The audit ran:

```powershell
git merge-tree --write-tree `
  3b9272790ad1cbea5b89947761ceecb52a32cb89 `
  a1946dd838d4918cac5d78f906719e62a9dbcc32
```

Result:

- exit code: 0;
- conflicts: 0;
- simulated result tree:
  `49c32f17f164a5b0d2d49e6cd7b5ea2c1adfa126`;
- integration tree at simulation time:
  `49c32f17f164a5b0d2d49e6cd7b5ea2c1adfa126`;
- result matches integration tree: yes.

That tree includes the committed G2-A plan but precedes this G2-B plan commit.
The future merge must compare against the integration HEAD/tree captured
immediately before execution, not blindly reuse the pre-plan tree above.

## 3. Expected merge identity

The future merge commit SHA cannot be truthfully predetermined. A Git commit ID
includes its tree, both parents, author/committer identity, timestamps, and commit
message. The commit does not exist during G2-B preparation, and fabricating an
“expected SHA” would provide false assurance.

The expected result is instead defined exactly by these invariants:

| Field | Required value |
| --- | --- |
| First parent | integration HEAD captured immediately before merge |
| Second parent | `a1946dd838d4918cac5d78f906719e62a9dbcc32` |
| Result tree | exactly the first parent's tree |
| Content delta from first parent | zero |
| Old `main` reachable from result | yes |
| V2 lineage reachable from result | yes |

The actual resulting merge SHA must be recorded after commit creation and before
any subsequent change or push. A SHA is acceptable only if every invariant above
passes.

## 4. Exact future merge command sequence

These commands are for a separately authorized execution phase. They were not run
in G2-B.

```powershell
$expectedIntegrationBranch = 'g2-main-integration'
$expectedMain = 'a1946dd838d4918cac5d78f906719e62a9dbcc32'

git switch $expectedIntegrationBranch
git fetch origin

$integrationHead = (git rev-parse HEAD).Trim()
$integrationTree = (git rev-parse 'HEAD^{tree}').Trim()
$remoteMain = (git rev-parse origin/main).Trim()
$localV2 = (git rev-parse v2-development).Trim()

if ($remoteMain -ne $expectedMain) {
    throw "origin/main changed; repeat the forensic audit"
}
if ($localV2 -ne '3b9272790ad1cbea5b89947761ceecb52a32cb89') {
    throw "local v2-development changed; stop"
}

# Repeat the read-only simulation against the exact current integration HEAD.
$simulatedTree = (git merge-tree --write-tree HEAD origin/main | Select-Object -First 1).Trim()
if ($LASTEXITCODE -ne 0 -or $simulatedTree -ne $integrationTree) {
    throw "merge simulation changed or conflicted; do not merge"
}

# Stage the normal recursive/ort merge without committing it yet.
git merge --no-ff --no-commit origin/main
if ($LASTEXITCODE -ne 0) {
    git merge --abort
    throw "unexpected merge conflict; stop and re-audit"
}

$stagedTree = (git write-tree).Trim()
if ($stagedTree -ne $integrationTree) {
    git merge --abort
    throw "merge changes the integration tree; stop and re-audit"
}

# No content may differ from the first parent.
git diff --cached --exit-code $integrationHead
if ($LASTEXITCODE -ne 0) {
    git merge --abort
    throw "unexpected content delta; stop"
}

git commit -m "chore(repository): preserve pre-phasenox main history"
$mergeSha = (git rev-parse HEAD).Trim()

# Validate exact parent ordering and result tree.
if ((git rev-parse 'HEAD^1').Trim() -ne $integrationHead) {
    throw "unexpected first parent"
}
if ((git rev-parse 'HEAD^2').Trim() -ne $expectedMain) {
    throw "unexpected second parent"
}
if ((git rev-parse 'HEAD^{tree}').Trim() -ne $integrationTree) {
    throw "unexpected merge tree"
}

git merge-base --is-ancestor $integrationHead HEAD
if ($LASTEXITCODE -ne 0) { throw "integration lineage not preserved" }
git merge-base --is-ancestor $expectedMain HEAD
if ($LASTEXITCODE -ne 0) { throw "old main history not preserved" }

Write-Output "Validated local preservation merge: $mergeSha"
```

Why ordinary `ort` merge rather than `--strategy=ours`:

- the read-only simulation proves the natural merge is conflict-free;
- the natural merge already produces the exact integration tree;
- `--no-commit` allows inspection before the commit exists;
- an `ours` strategy could conceal an unexpected future content change if a ref
  moved after this audit.

No push command belongs in the merge-execution sequence. Pushing the integration
branch and later advancing `main` require their own authorization and validation
phase.

## 5. Conflict handling

Any conflict is unexpected and invalidates this plan's merge assumptions.

If simulation reports a conflict:

1. do not run `git merge`;
2. record the new refs and merge-base information;
3. return to forensic analysis;
4. do not substitute `ours`, `theirs`, manual resolution, rebase, or force.

If `git merge --no-commit` reports a conflict:

```powershell
git status --short
git merge --abort
git status --short
```

Then stop. Do not resolve a conflict inside this migration phase. The expected
state after abort is the unchanged integration HEAD plus only the two protected
untracked Desktop roadmap files.

If the staged tree differs despite no textual conflict, abort the merge and treat
the tree difference as a forensic failure. A “clean” merge that changes content
is not acceptable for the history-preservation step.

## 6. Validation checks

### Before merge execution

- branch is exactly `g2-main-integration`;
- tracked worktree and index are clean;
- only the two protected roadmap files are untracked;
- local `v2-development` remains `3b927279...`;
- `origin/main` remains `a1946dd...`;
- `origin/desktop-ui` remains `e2dd11e...`;
- no local or remote tag was created by G2-B;
- no remote integration branch exists unless a later phase explicitly created it.

### During the uncommitted merge

- merge simulation exit code 0;
- simulated tree equals captured integration tree;
- `git merge --no-commit` exit code 0;
- no unmerged paths;
- `git write-tree` equals captured integration tree;
- cached diff from the captured first parent is empty.

### After local merge commit

- parent 1 equals captured integration HEAD;
- parent 2 equals `a1946dd...`;
- result tree equals captured integration tree;
- both histories are ancestors of the result;
- commit contains no file change relative to parent 1;
- protected refs remain byte-for-byte unchanged;
- no remote ref moved;
- actual merge SHA is recorded in the execution report.

### Before any later push

- migration-only reference, metadata, CODEOWNERS, and CI commits are separately
  reviewed;
- local regression and clean-build gates pass;
- remote refs are fetched again;
- the integration branch is pushed alone first;
- canonical CI passes on its exact SHA;
- advancing `main` remains a normal fast-forward.

## 7. Rollback procedure

### Simulation failure

No repository state changes. Stop and repeat analysis.

### Uncommitted merge failure

Run `git merge --abort`, verify the original integration HEAD and clean tracked
state, and stop. Do not clean, reset, or touch the protected untracked files.

### Committed but unpushed merge fails validation

Do not push. Preserve the integration branch for forensic inspection, switch back
to `v2-development`, and report the invalid merge SHA. A later explicitly
authorized cleanup may replace/delete the temporary branch; G2-B does not do so.

### Later integration-branch push fails CI

Leave `main` untouched. Correct through reviewed forward commits on the integration
branch or abandon it. Never force-update `main`, `v2-development`, or the
integration branch.

### Later `main` fast-forward requires rollback

Do not reset published `main`. Use a separately reviewed forward fix or temporarily
select the frozen V2 reference for comparison. Old `main` history remains
reachable through the preservation merge.

## 8. Protected-ref contract

G2-B must leave these refs unchanged:

| Ref | SHA |
| --- | --- |
| local `v2-development` | `3b9272790ad1cbea5b89947761ceecb52a32cb89` |
| `origin/v2-development` | `bcb2a6c573d1c25308780696167fc1cf12b92fab` |
| `origin/main` | `a1946dd838d4918cac5d78f906719e62a9dbcc32` |
| `origin/desktop-ui` | `e2dd11e4193f32cd4f31cda5bca8cbd322bec3af` |
| `origin/develop` | `53bd19802593905ec7ff20144bff0fc35b23d92b` |
| `origin/v1-freeze-candidate` | `04b896f151e17e9d4cf35b31afc4e68a254e0306` |
| `origin/v1-ui-baseline` | `04b896f151e17e9d4cf35b31afc4e68a254e0306` |

The G2-B plan commit advances only local `g2-main-integration` and adds only this
document. It is not a product, CI, metadata, branch, or GitHub migration.

## 9. Completion condition

G2-B preparation is complete when:

- local `g2-main-integration` exists from the required V2 tip;
- main history and merge simulation are recorded;
- this plan is the only committed file;
- no merge commit exists;
- no remote branch or tag was created;
- nothing was pushed;
- repository name/default branch/settings remain unchanged;
- protected refs remain unchanged;
- only the two protected Desktop roadmap files remain untracked.
