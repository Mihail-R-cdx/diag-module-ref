# Design: Decouple project graph refresh

## Context

The repository publishes a Graphify map whose committed metadata currently records:

```text
baseline_stage = final
indexed_source_commit = 2ad5c67b5413627cfc15fb327c0e6f856cf9b264
```

That map is intentionally non-authoritative and may lag current `master`. Current `RULES.md` already states that a stale or absent graph does not block ordinary development or validation. However, the root `agent-project-navigation` specification still defines final refresh as a standard post-archive checkpoint and allows graph failure to block the graph-enabled merge checkpoint unless an architect records an exception.

PR #17, `generalize-final-graph-refresh-evidence`, attempted to make that checkpoint reusable through a mandatory ordinary-change lineage containing renewed validation, a report-only commit, an evidence-only commit, and a graph-only commit. That PR is paused and superseded because the graph does not have sufficient authority to justify this lifecycle complexity.

## Goals

1. Remove Graphify refresh from the mandatory lifecycle of ordinary OpenSpec changes.
2. Preserve the committed frozen code map as an optional navigation artifact.
3. Make graph staleness non-blocking for ordinary validation, archive, and merge.
4. Define a separate architect-triggered maintenance workflow for refreshing the map.
5. Simplify the repository-local wrapper by removing OpenSpec archive and validation-evidence coupling.
6. Preserve graph publication security, integrity, determinism, and source-binding protections.
7. Preserve the original frozen-baseline workflow only as historical evidence.

## Non-goals

- Do not refresh or modify `graphify-out/` in this change.
- Do not modify application production code or application behavior.
- Do not weaken independent validation, archive, or post-archive checks for ordinary OpenSpec changes.
- Do not make Graphify a validation authority, architecture authority, or source of review findings.
- Do not create a new generic validation-evidence JSON framework.
- Do not reinterpret or delete historical archived artifacts or the existing committed baseline.
- Do not merge, repair, or continue PR #17.

## Authority model

The authoritative order remains:

```text
RULES.md
-> approved OpenSpec
-> current source/tests
-> Git diff
-> runbooks
-> Graphify
-> agent reports
```

Graphify remains useful only for finding candidate files, symbols, and relationships in its indexed source state. `EXTRACTED` is a static observation; `INFERRED` is a hypothesis; `AMBIGUOUS` is not evidence. Every material conclusion must be verified in current source and tests.

## Ordinary OpenSpec lifecycle

The normative ordinary workflow is:

```text
Architecture
-> Implementation
-> Independent validation
-> Archive + post-archive checks
-> Merge
```

Once ordinary archive and post-archive requirements pass, the feature may merge without any of the following:

```text
Graphify refresh
renewed validation solely for Graphify
validation-report-only commit
post-archive Graphify evidence JSON
evidence-only commit
graph-only commit
stale-graph merge exception
```

A branch may therefore merge while `graphify-out/baseline.json.indexed_source_commit` is older than the feature source. That condition is expected frozen-baseline behavior, not a validation defect.

Ordinary implementation, review, validation, archive, and merge sessions must continue to leave `graphify-out/` unchanged unless the user has explicitly authorized a separate maintenance refresh stage.

## Separate maintenance workflow

A graph refresh is a standalone repository-maintenance operation initiated by an architect when the map has become materially stale or after significant structural changes.

The normative flow is:

```text
S = exact stable current remote master
-> Full Graphify rebuild
-> G = graph-only commit
-> lightweight graph review
-> merge
```

### Source boundary

Before generation:

1. Fetch current remote state.
2. Record full `origin/master` SHA as `S`.
3. Use a clean detached source worktree whose `HEAD` equals `S`.
4. Require `SourceRef` to resolve to the same `S` inside that worktree.
5. Create the maintenance output branch from `S`.
6. Make no source, test, OpenSpec, rule, runbook, wrapper, dependency-policy, or validation-evidence changes on the maintenance branch.

The source and output worktrees remain separate. Graphify processes the source bytes at `S`; accepted generated artifacts are published only into the maintenance output worktree.

### Publication boundary

The maintenance branch contains exactly one graph publication commit `G` on top of `S`. `G` may change only:

```text
graphify-out/graph.json
graphify-out/manifest.json
graphify-out/GRAPH_REPORT.md
graphify-out/baseline.json
```

`baseline.json` records:

```text
baseline_stage = final
indexed_source_commit = S
indexed_source_ref = origin/master
target_branch = master
```

`G` is not the indexed source commit because `graphify-out/` is excluded from the indexed corpus.

Before merging the maintenance PR, review must recheck that remote `master` still equals `S` and that remote branch HEAD still equals reviewed `G`. If `master` advanced, the refresh no longer represents current stable `master`; regenerate from the new source SHA rather than merging the stale maintenance branch.

## Wrapper contract

The publication interface becomes maintenance-focused. The standard invocation is:

```powershell
.\tools\refresh_project_graph.ps1 `
  -Mode FullRebuild `
  -SourceRoot <clean-detached-master-worktree> `
  -SourceRef origin/master `
  -OutputRoot <maintenance-worktree> `
  -TargetBranch master
```

The implementation shall:

- make `FullRebuild` the default publication mode;
- retain `Incremental` only as an optional publication mode under the preconditions below;
- allow `InstallExact` to remain only as a non-publishing pinned-tool helper if still useful;
- remove the publishing mode `Initial`;
- remove `BaselineStage` as caller-controlled workflow state;
- remove `PostArchiveValidationEvidence`;
- remove parsing or validation of `verification-report.md`;
- remove lookup of `openspec/validation/*.post-archive.json`;
- remove archive presence, active-change absence, and feature-commit lineage checks;
- derive `indexed_source_commit` directly from clean `SourceRoot HEAD`;
- require explicit `SourceRef` equality to that HEAD;
- publish new baselines with `baseline_stage = final`.

Historical evidence files may remain committed, but the wrapper does not read them and they do not authorize generation.

## Full rebuild and incremental modes

`FullRebuild` is the preferred standard because it avoids accumulated stale topology and keeps maintenance review simple.

`Incremental` may be used only when all of the following remain unchanged since the previous accepted baseline:

- Graphify version;
- `.graphifyignore` bytes and policy;
- `.gitattributes` encoding and line-ending policy for Graphify inputs/outputs;
- indexed source roots and package boundaries;
- output schema and metadata contract.

Incremental acceptance must also prove:

- all deleted paths and nodes disappear;
- old renamed paths do not remain as ghost nodes;
- new renamed paths appear when included in the corpus;
- topology deltas remain within approved limits;
- source and output path sets remain repository-relative;
- the previous accepted baseline remains intact after any failure.

A version, ignore, encoding, package-boundary, mass rename/delete, ghost-node, topology, or integrity change requires `FullRebuild`.

## Preserved publication protections

The simplified workflow must preserve:

- exact pinned `graphifyy==0.9.26` unless a separately approved change updates it;
- clean source worktree and exact source-ref/HEAD binding;
- code-only corpus and exclusion of Graphify output, archives, inventory, Excel, secrets, local deployment files, and temporary worktrees;
- rejection of HTML and unexpected generated files;
- exactly four allowlisted committed artifacts;
- canonical UTF-8 without BOM and LF output;
- valid JSON before publication;
- nonzero node and edge counts;
- `graph_sha256` and `ignore_file_sha256` calculated from actual published bytes;
- repository-relative paths only;
- secret, credential, inventory, Windows/UNC, POSIX checkout-path, and user-specific path scans;
- safe backup-and-restore publication behavior;
- no hooks, watch mode, MCP, Graphify skills, `AGENTS.md`, or merge drivers.

Failure messages must identify the failed contract category without exposing sensitive values, inventory contents, or user-specific absolute paths.

## Lightweight graph review

Graph maintenance review verifies only graph publication authority:

1. source SHA `S`, source ref, clean source worktree, and output-branch base;
2. graph-only diff scope from `S` to `G`;
3. exactly four allowlisted artifacts and no other changes;
4. valid JSON, nonzero counts, canonical encoding, and hashes matching published bytes;
5. repository-relative paths and absence of secrets, inventory, and user-specific absolute paths;
6. expected source-file, node, edge, rename/delete, ghost-node, and topology integrity;
7. `baseline.json.indexed_source_commit = S`;
8. remote `master = S` and remote maintenance HEAD = reviewed `G` before merge.

The reviewer does not treat application tests, OpenSpec validation reports, or feature-change evidence as Graphify input. Existing validation of source at `master` remains separate from this artifact review.

A failed graph review blocks only the graph-maintenance PR. It does not invalidate any ordinary feature validation and does not block unrelated feature archive or merge.

## Historical compatibility and PR #17

The existing frozen baseline, archived `frozen-project-graph-baseline` change, historical post-archive evidence JSON, and historical `A -> S -> E -> G` ordering remain committed forensic records. They are not migrated, generalized, or required for future refreshes.

After this replacement architecture receives `APPROVE`:

- close PR #17 without merge;
- retain `agent/generalize-final-graph-refresh-evidence` temporarily for forensic/reference use;
- do not copy implementation from PR #17 unless a later implementation session independently determines that a narrow non-workflow helper remains useful and conforms to this approved design.

## Implementation boundaries

The implementation may modify only the workflow/policy surface required by this change:

```text
RULES.md
openspec/specs/agent-project-navigation/spec.md
openspec/specs/project-graph-refresh-workflow/spec.md
docs/project-graph-runbook.md
tools/refresh_project_graph.ps1
tests/test_project_graph_refresh_workflow.py
openspec/changes/decouple-project-graph-refresh/tasks.md
```

No application production code, unrelated tests, validation reports, archived changes, evidence JSON, or `graphify-out/` artifacts are in scope.

## Required test coverage

Implementation tests must prove:

- a valid `FullRebuild` accepts one clean exact `origin/master` source SHA without OpenSpec archive or evidence inputs;
- `baseline.json` records that source SHA, `origin/master`, target `master`, and `final` stage;
- dirty source, unresolved/mismatched source ref, wrong source/output boundary, invalid target, and unexpected source mutations fail before publication;
- legacy post-archive evidence and verification-report parsing are no longer required or consulted;
- only the four generated artifacts can be published;
- JSON, nonzero count, canonical encoding, published-byte hash, secret/inventory/path, and safe-publication checks remain enforced;
- incremental mode accepts only unchanged policy/topology conditions and rejects rename/delete ghosts or integrity failures;
- a failed generation leaves the previous accepted baseline intact;
- focused tests no longer encode ordinary feature `A -> V -> R -> E -> G` lineage as a supported workflow.

## Rollout

1. Validate and approve this architecture-only change.
2. Close PR #17 without merge and retain its branch for forensic/reference purposes.
3. Implement the approved policy, wrapper, runbook, root specs, and focused tests without modifying `graphify-out/`.
4. Independently validate the published implementation HEAD in a clean detached remote worktree.
5. Archive after approval, run ordinary post-archive checks, and merge through the normal OpenSpec lifecycle.
6. Perform a separate full Graphify maintenance refresh only when the architect explicitly schedules it.
