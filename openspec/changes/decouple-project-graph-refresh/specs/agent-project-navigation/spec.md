# agent-project-navigation Delta

## RENAMED Requirements

- FROM: `### Requirement: Initial graph is local code-only and has no visualization`
- TO: `### Requirement: Graph corpus is local code-only and has no visualization`
- FROM: `### Requirement: Refresh occurs at a controlled post-archive checkpoint`
- TO: `### Requirement: Refresh occurs only as separate maintenance`
- FROM: `### Requirement: Documentation-only changes use a scoped refresh decision`
- TO: `### Requirement: Ordinary changes do not trigger automatic refresh`

## MODIFIED Requirements

### Requirement: Published project graph is a frozen navigation baseline

The repository MAY publish a committed Graphify map of one exact stable source commit for read-only agent navigation. The map SHALL NOT be treated as architecture, workflow state, validation evidence, production correctness evidence, or a substitute for current source and tests.

An absent, invalid, or stale map SHALL NOT block ordinary architecture, implementation, independent validation, archive, post-archive checks, or merge. Ordinary changes SHALL NOT require a Graphify refresh, Graphify evidence JSON, renewed validation solely for Graphify, or a stale-graph merge exception.

#### Scenario: Agent begins graph-assisted orientation

- **WHEN** an agent uses a published project graph
- **THEN** it reads `RULES.md`, applicable OpenSpec artifacts, and `graphify-out/baseline.json` first
- **AND** identifies the full `indexed_source_commit`
- **AND** treats the current branch diff separately
- **AND** verifies every material conclusion in current source.

#### Scenario: Graph is absent or stale during ordinary work

- **WHEN** graph artifacts are absent, invalid, or older than the current branch or `master`
- **THEN** ordinary architecture, implementation, validation, archive, post-archive checks, and merge remain possible through authoritative sources
- **AND** the agent reports the graph condition rather than silently rebuilding it
- **AND** no change-specific Graphify evidence or stale-graph exception is required.

#### Scenario: Ordinary change merges after the indexed source

- **GIVEN** an ordinary change satisfies its approved OpenSpec, tests, independent validation, archive, and post-archive requirements
- **WHEN** the committed graph still indexes an older source commit
- **THEN** the change may merge without modifying `graphify-out/`
- **AND** the existing graph remains a frozen navigation baseline until a separately authorized maintenance refresh.

### Requirement: Graph generation is explicit and pinned

The generator SHALL remain the isolated package `graphifyy==0.9.26`, invoked through the `graphify` executable, unless a separately approved change updates the version. It SHALL NOT be added as an application runtime dependency. Floating installs are forbidden.

Graph publication SHALL occur only in an explicitly authorized graph-maintenance workflow. The repository-local wrapper SHALL verify repository root, exact Graphify version, clean source state, explicit source ref, target branch, full source SHA, source-ref equality to source `HEAD`, source/output separation, and `.graphifyignore` before generation. It SHALL fail nonzero when any prerequisite or Graphify command fails.

The wrapper SHALL NOT require an OpenSpec archive, `verification-report.md`, post-archive Graphify evidence JSON, validation-report-only commit, evidence-only commit, or ordinary feature-change lineage as a graph generation prerequisite.

#### Scenario: Maintenance wrapper starts a full rebuild

- **GIVEN** an architect authorized a graph maintenance refresh
- **AND** `SourceRoot` is a clean detached worktree at exact current `origin/master` SHA `S`
- **AND** explicit `SourceRef` resolves to the same `S`
- **WHEN** `tools/refresh_project_graph.ps1` starts `FullRebuild`
- **THEN** it verifies the pinned generator and all source, ref, target, ignore, output, and repository prerequisites
- **AND** it does not inspect ordinary OpenSpec validation reports or Graphify evidence JSON.

#### Scenario: Source ref does not equal source HEAD

- **WHEN** explicit `SourceRef` does not resolve to clean `SourceRoot HEAD`
- **THEN** the wrapper fails nonzero before Graphify generation
- **AND** it does not publish replacement graph artifacts.

#### Scenario: Ordinary change reaches archive

- **WHEN** an ordinary OpenSpec change reaches archive or post-archive checks
- **THEN** the graph wrapper is not a mandatory lifecycle command
- **AND** no Graphify input or evidence artifact is created for that change.

### Requirement: Graph corpus is local code-only and has no visualization

Every future maintenance refresh SHALL index only the actual supported code corpus using code-only behavior and SHALL disable or reject HTML visualization. It SHALL NOT require an external LLM API.

Historical bootstrap terminology may remain in archived forensic artifacts and the existing committed baseline history, but the maintenance wrapper SHALL NOT expose a publishing mode named `Initial` or require a caller-selected bootstrap stage.

#### Scenario: Maintenance baseline is generated

- **WHEN** an authorized full rebuild runs on clean exact source commit `S`
- **THEN** nonzero graph nodes and edges are produced from the approved code roots
- **AND** OpenSpec Markdown, archived changes, real inventory, Excel, secrets, temporary worktrees, and graph output are absent from the indexed corpus
- **AND** `graph.html` is neither required nor committed.

#### Scenario: Publishing caller requests historical initial mode

- **WHEN** a caller attempts to use the removed `Initial` publishing mode or caller-controlled bootstrap stage
- **THEN** the repository-local wrapper rejects the unsupported interface
- **AND** directs publication through the current maintenance `FullRebuild` or eligible `Incremental` mode.

### Requirement: Baseline metadata proves the indexed source

`graphify-out/baseline.json` SHALL use schema version 2 and record generator, exact Graphify version, mode, baseline stage, full indexed source SHA, indexed source ref, target branch, UTC generation time, graph and ignore-file SHA-256 hashes, and node/edge counts. It SHALL NOT contain user-specific paths, secrets, ambiguous `indexed_branch`, validation-report authority, archive lineage, or a `detached` placeholder.

The ignore-file SHA-256 SHALL be computed from the actual `.graphifyignore` bytes read by Graphify. The graph SHA-256 SHALL be computed from the actual canonical `graphify-out/graph.json` bytes published by the wrapper. The four generated artifacts SHALL be deterministic UTF-8 without BOM and LF files, and the wrapper SHALL canonicalize them before JSON parsing, structural validation, security/path scans, hash calculation, and publication.

A newly published maintenance baseline SHALL record:

```text
baseline_stage = final
indexed_source_commit = exact maintenance source SHA S
indexed_source_ref = origin/master
target_branch = master
```

The following graph-only commit `G` SHALL NOT replace `S` as `indexed_source_commit` because `graphify-out/` is excluded from the indexed corpus.

#### Scenario: Maintenance baseline is generated

- **GIVEN** a clean exact current `origin/master` source commit `S`
- **WHEN** the authorized maintenance rebuild passes all generation and publication checks
- **THEN** metadata records `baseline_stage = final`
- **AND** `indexed_source_commit` equals `S`
- **AND** `indexed_source_ref` equals `origin/master`
- **AND** `target_branch` equals `master`
- **AND** hashes and counts describe the actual canonical published artifacts.

#### Scenario: Graph artifacts are stored in following commit

- **GIVEN** maintenance source commit `S`
- **WHEN** allowlisted graph artifacts are committed in following graph-only commit `G`
- **THEN** `indexed_source_commit` remains `S`
- **AND** `G` is not considered missing from the graph because graph artifacts are excluded from the corpus.

#### Scenario: Master advances after publication

- **WHEN** `master` advances beyond the recorded `indexed_source_commit`
- **THEN** baseline metadata continues to identify the exact older indexed source honestly
- **AND** the map becomes stale navigation data without becoming invalid production or validation evidence.

### Requirement: Refresh occurs only as separate maintenance

The historical `frozen-project-graph-baseline` publication used a controlled post-archive `A -> S -> E -> G` checkpoint. That ordering SHALL remain historical forensic evidence only and SHALL NOT define the lifecycle of future ordinary OpenSpec changes.

Future graph refresh SHALL occur only as a separate architect-triggered maintenance operation from one exact stable current `master` source commit `S`, followed by graph-only commit `G` and lightweight graph integrity review. It SHALL NOT be automatically triggered by ordinary archive or merge.

#### Scenario: Ordinary change completes without refresh

- **GIVEN** an ordinary change has passed independent validation, archive, and post-archive checks
- **WHEN** it is ready to merge
- **THEN** it does not run Graphify refresh as part of its lifecycle
- **AND** it does not create validation-report-only, Graphify-evidence, evidence-only, or graph-only commits.

#### Scenario: Architect schedules maintenance refresh

- **GIVEN** the committed map has become materially stale or source topology changed significantly
- **WHEN** an architect explicitly authorizes graph maintenance
- **THEN** the refresh starts from exact stable current `master` source SHA `S`
- **AND** publishes only graph-only commit `G`
- **AND** receives lightweight graph integrity review before merge.

#### Scenario: Master advances before maintenance merge

- **GIVEN** a maintenance graph was generated from `S`
- **WHEN** remote `master` advances before the maintenance PR merges
- **THEN** the maintenance branch is not merged as the current-master refresh
- **AND** generation restarts from the new stable `master` SHA.

### Requirement: Graph failure does not redefine production correctness

Graph refresh is a separate artifact-maintenance operation. Failure before or after successful ordinary production validation SHALL NOT invalidate that validation and SHALL NOT block unrelated ordinary archive, post-archive checks, or merge.

A generation or graph-review failure SHALL block only publication or merge of the graph-maintenance branch. The existing accepted baseline SHALL remain intact and may remain stale until a later authorized maintenance attempt succeeds.

#### Scenario: Graph generation fails during maintenance

- **WHEN** graph generation or publication integrity checks fail
- **THEN** no fabricated or partial replacement baseline is committed
- **AND** the previous accepted graph remains intact
- **AND** the maintenance PR is not approved for merge
- **AND** unrelated ordinary changes remain governed by their own OpenSpec, source, tests, and validation evidence.

#### Scenario: Ordinary feature validation succeeds while graph is stale

- **GIVEN** an ordinary feature passes all required tests, strict validation, independent review, archive, and post-archive checks
- **WHEN** the graph is stale or a separate maintenance attempt failed
- **THEN** the feature may merge without a Graphify repair or stale-graph exception.

### Requirement: Ordinary changes do not trigger automatic refresh

No ordinary OpenSpec change SHALL automatically require graph refresh based on whether its diff contains code, tests, specifications, documentation, or other indexed or non-indexed repository paths. Refresh timing SHALL be a separate architectural maintenance decision based on accumulated staleness, structural navigation value, package-boundary changes, major movement or renames, integrity needs, or direct architect instruction.

#### Scenario: Ordinary code change completes

- **GIVEN** an ordinary change modifies indexed application code
- **AND** it passes its approved lifecycle
- **WHEN** it is ready to merge
- **THEN** it may merge without graph refresh
- **AND** the accumulated graph staleness may be considered later in a separate maintenance decision.

#### Scenario: Documentation-only change completes

- **WHEN** an ordinary change modifies only documentation and passes its approved lifecycle
- **THEN** it does not require graph refresh
- **AND** it does not need a special scoped refresh decision or Graphify evidence.
