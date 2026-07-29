# project-graph-refresh-workflow Delta

## ADDED Requirements

### Requirement: Ordinary OpenSpec lifecycle excludes Graphify refresh

The ordinary OpenSpec lifecycle SHALL be:

```text
Architecture
-> Implementation
-> Independent validation
-> Archive + post-archive checks
-> Merge
```

Graphify refresh SHALL NOT be a mandatory stage of an ordinary change. Ordinary changes SHALL NOT require renewed validation solely for Graphify, a validation-report-only commit, post-archive Graphify evidence JSON, an evidence-only commit, a graph-only commit, or a stale-graph merge exception.

#### Scenario: Ordinary implementation is ready to archive

- **GIVEN** the published remote implementation HEAD passes required tests, strict OpenSpec validation, independent validation, and repository-protection checks
- **WHEN** the change is approved for archive
- **THEN** archive proceeds without Graphify generation or Graphify evidence
- **AND** post-archive checks use the ordinary repository workflow.

#### Scenario: Ordinary archived change is ready to merge

- **GIVEN** archive and ordinary post-archive checks pass
- **WHEN** remote feature HEAD still equals the reviewed archive commit
- **THEN** the change may merge even when the committed graph indexes an older source commit
- **AND** no graph-specific commit or exception is required.

### Requirement: Graph refresh is a separate architect-triggered maintenance operation

A new project graph SHALL be published only through a separate maintenance operation explicitly authorized by an architect. The maintenance operation SHALL start from one exact stable current remote `master` commit `S` and SHALL not contain application, test, OpenSpec, rule, runbook, wrapper, dependency-policy, validation-evidence, archive, or unrelated source changes.

#### Scenario: Maintenance refresh begins

- **GIVEN** an architect authorizes graph maintenance
- **WHEN** the operator fetches current GitHub state
- **THEN** it records full `origin/master` SHA as `S`
- **AND** creates a clean detached source worktree at `S`
- **AND** creates the maintenance output branch from `S`
- **AND** verifies the source ref resolves to source `HEAD = S`.

#### Scenario: Maintenance branch contains non-graph mutation

- **WHEN** the maintenance branch differs from `S` in any path outside the four allowlisted graph artifacts
- **THEN** graph publication or review fails
- **AND** the branch is not approved for merge.

### Requirement: Standard maintenance refresh uses full rebuild

`FullRebuild` SHALL be the standard Graphify publication mode. The repository-local wrapper SHALL generate from clean exact source `S`, stage generation outside the source worktree, and publish accepted artifacts only to the maintenance output worktree.

The standard command SHALL not require baseline-stage, OpenSpec archive, verification-report, post-archive evidence, or feature-lineage parameters.

#### Scenario: Standard full rebuild succeeds

- **GIVEN** clean source `HEAD = SourceRef = S`
- **AND** the exact pinned Graphify version and required ignore policy are present
- **WHEN** `FullRebuild` passes generation, structural, security, path, hash, and publication checks
- **THEN** exactly four accepted graph artifacts are published to the output worktree
- **AND** the source worktree remains clean.

#### Scenario: Historical evidence is present in the repository

- **GIVEN** historical archived changes or post-archive evidence JSON remain committed
- **WHEN** a new maintenance rebuild runs
- **THEN** the wrapper does not parse or require those artifacts
- **AND** generation authority comes only from the clean exact source/ref and graph integrity contract.

### Requirement: Maintenance metadata binds the exact stable master source

A newly published maintenance `baseline.json` SHALL use schema version 2 and SHALL record:

```text
baseline_stage = final
indexed_source_commit = S
indexed_source_ref = origin/master
target_branch = master
```

It SHALL also record the exact generator/version, code-only mode, UTC generation time, graph and ignore-file SHA-256 hashes, and nonzero node/edge counts. It SHALL NOT record OpenSpec validation authority, archive lineage, evidence commit, user-specific paths, or ambiguous source identity.

#### Scenario: Metadata is accepted

- **WHEN** metadata is checked against actual source and published bytes
- **THEN** `indexed_source_commit` equals clean source `HEAD = S`
- **AND** explicit source ref resolves to `S`
- **AND** graph and ignore hashes match actual canonical bytes
- **AND** node and edge counts are nonzero.

#### Scenario: Metadata source differs from source worktree

- **WHEN** metadata, source `HEAD`, or explicit source ref identifies a different commit
- **THEN** publication fails before replacing the accepted baseline.

### Requirement: Maintenance publication uses one graph-only commit

After successful generation, the maintenance branch SHALL contain one graph-only commit `G` on top of `S`. The complete `S..G` diff SHALL contain only:

```text
graphify-out/graph.json
graphify-out/manifest.json
graphify-out/GRAPH_REPORT.md
graphify-out/baseline.json
```

`indexed_source_commit` SHALL remain `S`, not `G`.

#### Scenario: Graph-only commit is reviewable

- **GIVEN** generation succeeded from `S`
- **WHEN** artifacts are committed as `G`
- **THEN** the complete diff from `S` to `G` contains exactly the four allowlisted paths
- **AND** no validation evidence, source, test, specification, rule, runbook, wrapper, dependency, archive, or temporary file is included.

#### Scenario: Unexpected file is committed

- **WHEN** `S..G` includes any additional path
- **THEN** lightweight graph review returns changes required
- **AND** the maintenance PR is not merged.

### Requirement: Graph publication protections remain strict

The maintenance wrapper and review SHALL preserve:

- exact pinned Graphify version;
- clean source and exact source-ref binding;
- code-only corpus;
- exclusion of graph output, archives, real inventory, Excel, credentials, local deployment data, temporary worktrees, and secrets;
- rejection of HTML and unexpected generated files;
- canonical UTF-8 without BOM and LF artifacts;
- valid JSON and nonzero node/edge counts;
- hashes calculated from actual published bytes;
- repository-relative paths;
- secret, credential, inventory, Windows drive, UNC, POSIX checkout, and user-specific absolute-path scans;
- safe backup-and-restore publication;
- absence of hooks, watch mode, MCP, Graphify skills, `AGENTS.md`, and merge drivers.

#### Scenario: Generated artifact fails a protection check

- **WHEN** an artifact is malformed, empty, unexpected, noncanonical, hash-inconsistent, path-unsafe, inventory-bearing, or secret-bearing
- **THEN** publication fails nonzero
- **AND** no partial replacement is accepted
- **AND** the failure reports a non-sensitive contract category.

### Requirement: Incremental refresh is optional and constrained

`Incremental` MAY be used only when Graphify version, `.graphifyignore`, `.gitattributes` encoding policy, indexed source roots, package boundaries, output schema, and metadata contract are unchanged from the previous accepted baseline.

Incremental acceptance SHALL verify rename/delete cleanup, absence of ghost nodes, expected new paths, unchanged-node preservation, topology bounds, source-path integrity, and safe rollback. Any unverifiable rename/delete, ghost node, policy change, package-boundary change, mass structural change, or integrity failure SHALL require `FullRebuild`.

#### Scenario: Small compatible source delta qualifies

- **GIVEN** all incremental policy inputs are unchanged
- **AND** changed-file and rename/delete counts remain within approved limits
- **WHEN** update and integrity checks pass
- **THEN** incremental artifacts may proceed to the same publication and graph-only review checks as a full rebuild.

#### Scenario: Incremental integrity fails

- **WHEN** a deleted or renamed node remains, topology changes unexpectedly, or a required policy input changed
- **THEN** incremental publication fails
- **AND** the previous accepted baseline remains intact
- **AND** the next attempt uses `FullRebuild`.

### Requirement: Lightweight review verifies graph authority only

The graph-maintenance reviewer SHALL verify source SHA `S`, source/ref equality, clean source, output-branch base, exact graph-only diff scope, JSON validity, nonzero counts, canonical bytes, hashes, repository-relative paths, sensitive-data exclusions, and expected source-file/node/edge/topology integrity.

Before merge, the reviewer SHALL confirm remote maintenance HEAD still equals reviewed `G` and remote `master` still equals `S`.

The reviewer SHALL NOT treat application tests, OpenSpec validation reports, feature verification reports, or post-archive evidence JSON as Graphify inputs or graph-review authority.

#### Scenario: Master remains stable

- **GIVEN** graph commit `G` passed lightweight review
- **WHEN** remote `master` still equals `S` and remote maintenance HEAD still equals `G`
- **THEN** the maintenance PR is eligible to merge.

#### Scenario: Master advanced after generation

- **WHEN** remote `master` no longer equals `S` before maintenance merge
- **THEN** the maintenance PR is not merged as the current-master refresh
- **AND** refresh restarts from the new stable remote `master` SHA.

### Requirement: Graph maintenance failure is isolated from ordinary delivery

A graph generation, publication, review, or merge-precondition failure SHALL block only the graph-maintenance operation. It SHALL NOT invalidate previously accepted production validation and SHALL NOT block unrelated ordinary implementation, validation, archive, post-archive checks, or merge.

#### Scenario: Maintenance refresh fails while ordinary change is ready

- **GIVEN** an unrelated ordinary change passed its approved lifecycle
- **AND** graph maintenance failed or remains incomplete
- **WHEN** the ordinary change is considered for merge
- **THEN** it remains eligible under its own OpenSpec, source, tests, validation, and archive evidence
- **AND** no stale-graph exception is required.

### Requirement: Historical frozen-baseline workflow remains forensic only

The committed frozen baseline, archived `frozen-project-graph-baseline` artifacts, historical evidence JSON, and historical `A -> S -> E -> G` sequence SHALL remain valid records of how the initial baseline was produced. They SHALL NOT be generalized into a required or supported future ordinary-change workflow.

#### Scenario: Future change encounters historical artifacts

- **WHEN** an agent reads historical frozen-baseline or superseded PR #17 artifacts
- **THEN** it treats them as forensic context
- **AND** follows the current separate maintenance workflow
- **AND** does not create new ordinary-change validation-report, evidence, or graph commit chains from those examples.
