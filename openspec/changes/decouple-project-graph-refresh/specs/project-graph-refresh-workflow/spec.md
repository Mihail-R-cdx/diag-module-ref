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
- **AND** creates a separate clean maintenance output worktree and branch from the same `S`
- **AND** verifies the explicit source ref resolves to source `HEAD = S`.

#### Scenario: Maintenance branch contains non-graph mutation

- **WHEN** the maintenance branch differs from `S` in any path outside the four allowlisted graph artifacts
- **THEN** graph publication or review fails
- **AND** the branch is not approved for merge.

### Requirement: Source and output worktrees bind to the same exact clean base

Before generation, `SourceRoot` and `OutputRoot` SHALL identify distinct Git worktrees. Both worktrees SHALL be clean and both SHALL have `HEAD = S`. The output branch SHALL be created from `S` and SHALL have no pre-existing diff from `S`.

The explicit `SourceRef` SHALL resolve to `S` inside `SourceRoot`. The wrapper SHALL reject a shared source/output path, dirty source, dirty output, output `HEAD` not equal to `S`, pre-existing output mutation, or source-ref mismatch before Graphify generation or publication.

`.graphifyignore` SHALL be read from `SourceRoot`. Its working-tree bytes, after repository filters, SHALL match the committed blob at `S:.graphifyignore`. Differing or caller-controlled `.graphifyignore` bytes from `OutputRoot` SHALL NOT be used as the generation policy.

Immediately before accepted publication, `OutputRoot` SHALL still contain no changes from `S`. After publication and before commit, all output mutations SHALL be confined to the four allowlisted graph artifact paths.

#### Scenario: Exact source and output boundary is accepted

- **GIVEN** source and output are different worktrees
- **AND** both are clean at `HEAD = S`
- **AND** the output branch was created from `S` with no existing diff
- **AND** `SourceRef` resolves to `S`
- **AND** source `.graphifyignore` matches committed `S` bytes
- **WHEN** maintenance generation begins
- **THEN** the wrapper may proceed to Graphify and artifact checks.

#### Scenario: Output worktree is dirty or based on another commit

- **WHEN** `OutputRoot` is dirty, has `HEAD != S`, has a pre-existing diff from `S`, or is the same worktree as `SourceRoot`
- **THEN** the wrapper fails before generation or publication
- **AND** it does not attribute caller-controlled output bytes to source commit `S`.

#### Scenario: Output ignore policy differs from source commit

- **GIVEN** `OutputRoot/.graphifyignore` differs from committed `S:.graphifyignore`
- **WHEN** the wrapper prepares the build staging area
- **THEN** it uses only the verified `SourceRoot` policy bytes
- **AND** it does not copy or trust the differing output-worktree policy.

### Requirement: Standard maintenance refresh uses full rebuild

`FullRebuild` SHALL be the standard Graphify publication mode. The repository-local wrapper SHALL generate from clean exact source `S`, stage generation outside both repository worktrees, and publish accepted artifacts only to the clean maintenance output worktree.

The standard command SHALL not require baseline-stage, OpenSpec archive, verification-report, post-archive evidence, or feature-lineage parameters.

#### Scenario: Standard full rebuild succeeds

- **GIVEN** exact source/output boundary checks pass
- **AND** the exact pinned Graphify version and verified source ignore policy are present
- **WHEN** `FullRebuild` passes generation, structural, security, path, hash, and publication checks
- **THEN** all four accepted graph artifacts are present and valid in the output tree
- **AND** the source worktree remains clean
- **AND** no output path outside the graph allowlist is modified.

#### Scenario: Historical evidence is present in the repository

- **GIVEN** historical archived changes or post-archive evidence JSON remain committed
- **WHEN** a new maintenance rebuild runs
- **THEN** the wrapper does not parse or require those artifacts
- **AND** generation authority comes only from the exact source/output boundary and graph integrity contract.

### Requirement: Publication gate is application-structure agnostic

The blocking publication gate SHALL NOT require fixed application file paths, historical node IDs, class or function names, or concrete application relationships to exist in the new graph.

Historical project-specific smoke queries, including probes tied to `gui/pdu_controller.py`, `core/interactive_session.py`, `core/equipment_inventory.py`, or specific controller, resolver, credential, and enrichment edges, SHALL be removed from publication authority.

Blocking acceptance SHALL instead verify graph and manifest schema, approved current corpus boundaries, nonzero node and edge counts, internal node/edge reference integrity, repository-relative current-source paths, topology sanity, rename/delete cleanup, absence of ghost nodes, security scans, hashes, and safe publication.

Application-specific queries MAY be emitted only as explicitly non-blocking diagnostic observations. Their failure or the intentional movement, rename, or removal of a historical symbol SHALL NOT reject an otherwise correct rebuild.

#### Scenario: Historical smoke symbol was moved or removed

- **GIVEN** source commit `S` validly moved, renamed, or removed an application symbol used by an older smoke query
- **AND** the rebuilt graph satisfies current schema, corpus, topology, integrity, security, and publication contracts
- **WHEN** `FullRebuild` is evaluated
- **THEN** publication succeeds without requiring the historical file path or node ID
- **AND** no wrapper change is required merely to rename the old probe.

#### Scenario: Structurally invalid graph is produced

- **WHEN** the graph has invalid schema, missing internal references, disallowed corpus paths, ghost nodes, invalid topology, or another structural publication defect
- **THEN** publication fails independently of application-specific symbol identity.

### Requirement: Maintenance metadata binds the exact stable master source

A newly published maintenance `baseline.json` SHALL use schema version 2 and SHALL record:

```text
baseline_stage = final
indexed_source_commit = S
indexed_source_ref = origin/master
target_branch = master
```

It SHALL also record the exact generator/version, code-only mode, UTC generation time, graph and ignore-file SHA-256 hashes, and nonzero node/edge counts. It SHALL NOT record OpenSpec validation authority, archive lineage, evidence commit, user-specific paths, or ambiguous source identity.

The ignore-file hash SHALL describe the verified `.graphifyignore` bytes from `SourceRoot` at `S`, not uncommitted or output-worktree policy bytes.

#### Scenario: Metadata is accepted

- **WHEN** metadata is checked against actual source and published bytes
- **THEN** `indexed_source_commit` equals clean source `HEAD = S`
- **AND** explicit source ref resolves to `S`
- **AND** graph and source-policy hashes match actual canonical bytes
- **AND** node and edge counts are nonzero.

#### Scenario: Metadata source differs from source worktree

- **WHEN** metadata, source `HEAD`, output base, or explicit source ref identifies a different commit
- **THEN** publication fails before replacing the accepted baseline.

### Requirement: Maintenance publication uses one graph-only commit

After successful generation, the maintenance branch SHALL contain one graph-only commit `G` on top of `S` when accepted canonical artifact bytes differ from the artifacts already present at `S`.

The tree at `G` SHALL contain and validate all four canonical artifacts:

```text
graphify-out/graph.json
graphify-out/manifest.json
graphify-out/GRAPH_REPORT.md
graphify-out/baseline.json
```

The complete `S..G` diff SHALL be non-empty and SHALL change only a non-empty subset of those four paths. No unchanged artifact SHALL be artificially modified merely to force all four paths into the diff. `indexed_source_commit` SHALL remain `S`, not `G`.

If all four regenerated canonical artifacts are byte-identical to `S`, the workflow SHALL NOT fabricate an empty or artificial graph commit.

#### Scenario: Graph-only commit is reviewable

- **GIVEN** generation succeeded from `S`
- **AND** at least one canonical artifact differs from `S`
- **WHEN** changed artifacts are committed as `G`
- **THEN** all four canonical artifacts are present and valid in the `G` tree
- **AND** the complete diff from `S` to `G` is non-empty
- **AND** the diff contains only a non-empty subset of the four allowlisted paths
- **AND** no validation evidence, source, test, specification, rule, runbook, wrapper, dependency, archive, or temporary file is included.

#### Scenario: Some generated artifacts are unchanged

- **GIVEN** one or more regenerated canonical artifacts have bytes identical to `S`
- **WHEN** `G` is created
- **THEN** those unchanged paths need not appear in `S..G`
- **AND** they remain present and valid in the `G` tree
- **AND** no artificial mutation is introduced.

#### Scenario: Unexpected file is committed

- **WHEN** `S..G` includes any path outside the allowlist
- **THEN** lightweight graph review returns changes required
- **AND** the maintenance PR is not merged.

### Requirement: Graph publication protections remain strict

The maintenance wrapper and review SHALL preserve:

- exact pinned Graphify version;
- distinct clean source and output worktrees initially at exact `S`;
- clean source and exact source-ref binding;
- verified committed-source `.graphifyignore` policy;
- code-only corpus;
- exclusion of graph output, archives, real inventory, Excel, credentials, local deployment data, temporary worktrees, and secrets;
- rejection of HTML and unexpected generated files;
- all four canonical artifacts present and valid in the resulting tree;
- non-empty graph-only diff limited to a non-empty subset of the allowlist;
- canonical UTF-8 without BOM and LF artifacts;
- valid JSON and nonzero node/edge counts;
- hashes calculated from actual source-policy and published bytes;
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
- **THEN** incremental artifacts may proceed to the same exact source/output, publication, and graph-only review checks as a full rebuild.

#### Scenario: Incremental integrity fails

- **WHEN** a deleted or renamed node remains, topology changes unexpectedly, or a required policy input changed
- **THEN** incremental publication fails
- **AND** the previous accepted baseline remains intact
- **AND** the next attempt uses `FullRebuild`.

### Requirement: Lightweight review verifies graph authority only

The graph-maintenance reviewer SHALL verify:

- source SHA `S` and explicit source-ref equality;
- distinct source/output worktrees, both initially clean and both initially at `HEAD = S`;
- output branch created exactly from `S` with no pre-existing diff;
- `.graphifyignore` identity against committed source bytes;
- all four canonical artifacts present and valid in the `G` tree;
- non-empty `S..G` diff limited to a non-empty subset of the allowlist;
- absence of non-graph output mutations;
- JSON validity, nonzero counts, canonical bytes, hashes, repository-relative paths, and sensitive-data exclusions;
- current-corpus source-file, node, edge, rename/delete, ghost-node, and topology integrity without historical application-symbol requirements.

Before merge, the reviewer SHALL confirm remote maintenance HEAD still equals reviewed `G` and remote `master` still equals `S`.

The reviewer SHALL NOT treat application tests, OpenSpec validation reports, feature verification reports, post-archive evidence JSON, or historical application-specific smoke queries as Graphify inputs or graph-review authority.

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