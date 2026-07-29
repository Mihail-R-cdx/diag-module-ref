# Design: Decouple project graph refresh

## Context

The repository publishes a Graphify map whose committed metadata currently records:

```text
baseline_stage = final
indexed_source_commit = 2ad5c67b5413627cfc15fb327c0e6f856cf9b264
```

That map is intentionally non-authoritative and may lag current `master`. Current `RULES.md` already states that a stale or absent graph does not block ordinary development or validation. However, the root `agent-project-navigation` specification still defines final refresh as a standard post-archive checkpoint and allows graph failure to block the graph-enabled merge checkpoint unless an architect records an exception.

PR #17, `generalize-final-graph-refresh-evidence`, attempted to make that checkpoint reusable through a mandatory ordinary-change lineage containing renewed validation, a report-only commit, an evidence-only commit, and a graph-only commit. That PR is paused and superseded because the graph does not have sufficient authority to justify this lifecycle complexity.

The current wrapper also contains publication-blocking application-specific smoke queries tied to historical file paths, node IDs, and relationships. Those probes are incompatible with a maintenance workflow intended to run after module moves, package-boundary changes, and mass rename/delete operations, because a correct new graph may intentionally no longer contain the historical symbols.

## Goals

1. Remove Graphify refresh from the mandatory lifecycle of ordinary OpenSpec changes.
2. Preserve the committed frozen code map as an optional navigation artifact.
3. Make graph staleness non-blocking for ordinary validation, archive, and merge.
4. Define a separate architect-triggered maintenance workflow for refreshing the map.
5. Simplify the repository-local wrapper by removing OpenSpec archive and validation-evidence coupling.
6. Preserve graph publication security, integrity, determinism, and exact source/output binding protections.
7. Make publication acceptance independent of historical application symbol identities.
8. Preserve the original frozen-baseline workflow only as historical evidence.

## Non-goals

- Do not refresh or modify `graphify-out/` in this change.
- Do not modify application production code or application behavior.
- Do not weaken independent validation, archive, or post-archive checks for ordinary OpenSpec changes.
- Do not make Graphify a validation authority, architecture authority, or source of review findings.
- Do not create a new generic validation-evidence JSON framework.
- Do not define or maintain a versioned application-specific smoke profile in this change.
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

### Exact source and output boundary

Before generation:

1. Fetch current remote state.
2. Record full `origin/master` SHA as `S`.
3. Create a clean detached source worktree whose `HEAD` equals `S`.
4. Create a separate maintenance output worktree and branch from the same exact `S`.
5. Require `SourceRoot` and `OutputRoot` to resolve to different worktree paths.
6. Require both worktrees to be clean before generation.
7. Require both worktree `HEAD` values to equal `S` before generation.
8. Require explicit `SourceRef` to resolve to the same `S` inside the source worktree.
9. Require the output branch to have no pre-existing diff from `S`.
10. Make no source, test, OpenSpec, rule, runbook, wrapper, dependency-policy, validation-evidence, or other non-graph changes on the maintenance branch.

Graphify processes source bytes only from `SourceRoot` at `S`. Accepted generated artifacts are published only into `OutputRoot`.

`.graphifyignore` is an indexed policy input and must come from `SourceRoot`, not from caller-controlled or output-worktree bytes. Before generation, the wrapper must verify that the source working-tree `.graphifyignore` hashes to the committed `S:.graphifyignore` blob after repository filters. The wrapper must not overlay a different `.graphifyignore` from `OutputRoot` into the staging copy.

Immediately before publication, `OutputRoot` must still have no changes from `S`. After publication and before commit, every output mutation must be confined to the four allowlisted `graphify-out/` paths.

### Publication boundary

The maintenance branch contains exactly one graph publication commit `G` on top of `S` when accepted generated bytes differ from `S`.

The tree at `G` must contain and validate all four canonical artifacts:

```text
graphify-out/graph.json
graphify-out/manifest.json
graphify-out/GRAPH_REPORT.md
graphify-out/baseline.json
```

The complete `S..G` diff must be non-empty and may change only a non-empty subset of those four paths. A generated artifact whose canonical bytes are identical to the version already present at `S` must not be artificially modified merely to appear in the diff. No path outside the allowlist may change.

If regeneration produces no changed canonical artifact bytes, no artificial graph commit is created; the maintenance operation records that the accepted baseline is already byte-current and does not open or merge an empty publication change.

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
  -OutputRoot <clean-maintenance-worktree-created-from-S> `
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
- require distinct clean source and output worktrees whose initial `HEAD` values both equal `S`;
- reject any pre-existing output diff or any non-allowlisted output mutation;
- read `.graphifyignore` from `SourceRoot` and verify it against committed bytes at `S`;
- publish new baselines with `baseline_stage = final`.

Historical evidence files may remain committed, but the wrapper does not read them and they do not authorize generation.

## Application-agnostic publication gate

Publication acceptance must not depend on historical application file paths, node IDs, class names, functions, or concrete controller/resolver/enrichment edges.

The blocking publication gate must remove hard-coded probes such as the historical requirements for:

```text
gui/pdu_controller.py
core/interactive_session.py
core/equipment_inventory.py
specific PDU/controller/credential/enrichment node IDs and edges
```

Instead, blocking acceptance is based on current-source structural contracts:

- generated graph and manifest schemas are valid;
- the indexed source-file set follows the current approved corpus policy;
- node and edge counts are nonzero;
- graph node and edge references are internally consistent;
- generated paths are repository-relative and correspond to the current source corpus;
- rename/delete, ghost-node, topology, security, hash, and publication checks pass.

Optional application-specific queries may be emitted as non-blocking diagnostics for navigation quality, but they must be clearly labelled as observations and must never reject publication when a historical symbol was intentionally moved, renamed, or removed. This change chooses removal of application-specific smoke queries from publication authority rather than introducing a versioned smoke-profile lifecycle.

A `FullRebuild` after a valid structural refactor must therefore succeed without first changing the wrapper merely to teach it the new application symbol names.

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
- distinct clean source and output worktrees, both initially at exact `S`;
- exact source-ref/HEAD binding;
- committed-source `.graphifyignore` identity and hashing;
- code-only corpus and exclusion of Graphify output, archives, inventory, Excel, secrets, local deployment files, and temporary worktrees;
- rejection of HTML and unexpected generated files;
- all four allowlisted artifacts present and valid in the resulting tree;
- a non-empty publication diff limited to a non-empty subset of the allowlist;
- canonical UTF-8 without BOM and LF output;
- valid JSON before publication;
- nonzero node and edge counts;
- `graph_sha256` and `ignore_file_sha256` calculated from actual published/source-policy bytes;
- repository-relative paths only;
- secret, credential, inventory, Windows/UNC, POSIX checkout-path, and user-specific path scans;
- safe backup-and-restore publication behavior;
- no hooks, watch mode, MCP, Graphify skills, `AGENTS.md`, or merge drivers.

Failure messages must identify the failed contract category without exposing sensitive values, inventory contents, or user-specific absolute paths.

## Lightweight graph review

Graph maintenance review verifies only graph publication authority:

1. source SHA `S`, source ref, distinct source/output worktrees, clean initial states, and both initial `HEAD` values equal to `S`;
2. committed-source `.graphifyignore` identity and absence of caller-controlled policy bytes;
3. all four allowlisted artifacts are present and valid in the `G` tree;
4. the complete `S..G` diff is non-empty and changes only a non-empty subset of the four allowlisted paths;
5. no pre-existing or non-graph output mutations exist;
6. valid JSON, nonzero counts, canonical encoding, and hashes matching published bytes;
7. repository-relative paths and absence of secrets, inventory, and user-specific absolute paths;
8. current-corpus source-file, node, edge, rename/delete, ghost-node, and topology integrity without historical application-symbol requirements;
9. `baseline.json.indexed_source_commit = S`;
10. remote `master = S` and remote maintenance HEAD = reviewed `G` before merge.

The reviewer does not treat application tests, OpenSpec validation reports, feature-change evidence, or historical application-specific smoke probes as Graphify input or publication authority. Existing validation of source at `master` remains separate from this artifact review.

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
- `SourceRoot` and `OutputRoot` are distinct worktrees, both initially clean and both initially at `HEAD = S`;
- an output worktree not created from `S`, a dirty output worktree, a pre-existing output diff, or a same-path source/output boundary is rejected before generation/publication;
- `.graphifyignore` is read from `SourceRoot`, matches committed `S:.graphifyignore` bytes after repository filters, and cannot be overridden by differing output-worktree bytes;
- `baseline.json` records source SHA `S`, `origin/master`, target `master`, and `final` stage;
- dirty source, unresolved/mismatched source ref, invalid target, and unexpected source mutations fail before publication;
- legacy post-archive evidence and verification-report parsing are no longer required or consulted;
- removal or relocation of a formerly hard-coded smoke symbol does not block a structurally valid `FullRebuild` and does not require the old node ID;
- malformed graph/corpus/topology output still fails structural publication checks;
- all four canonical artifacts exist and validate in the resulting tree;
- the `S..G` diff is non-empty and contains only a non-empty subset of the four allowlisted paths;
- unchanged canonical artifacts are not artificially modified;
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