# agent-project-navigation Specification

## ADDED Requirements

### Requirement: Published project graph is a frozen navigation baseline

The repository SHALL MAY publish a committed Graphify map of one exact stable source commit for read-only agent navigation. The map SHALL NOT be treated as architecture, workflow state, validation evidence, or a substitute for current source and tests.

#### Scenario: Agent begins graph-assisted orientation

- **WHEN** an agent uses a published project graph
- **THEN** it reads `RULES.md`, applicable OpenSpec artifacts, and `graphify-out/baseline.json` first
- **AND** identifies the full `indexed_source_commit`
- **AND** treats the current branch diff separately
- **AND** verifies every material conclusion in current source.

#### Scenario: Graph is absent or stale

- **WHEN** graph artifacts are absent, invalid, or explicitly stale
- **THEN** ordinary development and validation remain possible through authoritative sources
- **AND** the agent reports the graph condition rather than silently rebuilding it.

### Requirement: Authority and confidence remain explicit

Graph edges SHALL be consumed according to their confidence category. `EXTRACTED` is a static observation only; `INFERRED` is a navigation hypothesis; `AMBIGUOUS` SHALL NOT be used as evidence. Review findings SHALL cite current source evidence.

#### Scenario: Query returns an inferred relationship

- **WHEN** a graph query returns an `INFERRED` or `AMBIGUOUS` relationship
- **THEN** the agent labels the confidence honestly
- **AND** opens the relevant source files
- **AND** does not issue a material finding from graph output alone.

### Requirement: Graph generation is explicit and pinned

The pilot generator SHALL be the isolated package `graphifyy==0.9.26`, invoked through the `graphify` executable. It SHALL NOT be added as a runtime dependency. Floating installs are forbidden.

#### Scenario: Wrapper starts a build or refresh

- **WHEN** `tools/refresh_project_graph.ps1` starts graph generation
- **THEN** it verifies the repository root, exact Graphify version, clean required source state, full source SHA, and `.graphifyignore`
- **AND** fails nonzero when any prerequisite or Graphify command fails.

### Requirement: Initial graph is local code-only and has no visualization

The first baseline SHALL index only the actual supported code corpus using code-only behavior and SHALL disable/reject HTML visualization. It SHALL NOT require an external LLM API.

#### Scenario: Initial baseline is generated

- **WHEN** the approved initial-build mode runs on a clean source commit
- **THEN** nonzero graph nodes and edges are produced from actual code roots
- **AND** OpenSpec Markdown, real inventory, Excel, secrets, temporary worktrees, and graph output are absent
- **AND** `graph.html` is neither required nor committed.

### Requirement: Baseline metadata proves the indexed source

`graphify-out/baseline.json` SHALL use schema version 1 and record generator, exact Graphify version, mode, full indexed source SHA, indexed branch, UTC generation time, graph and ignore-file SHA-256 hashes, and node/edge counts. It SHALL contain no user-specific path or secret.

#### Scenario: Graph artifacts are stored in a following commit

- **GIVEN** source commit `S` is checked out and indexed
- **WHEN** graph artifacts are committed in following graph-only commit `G`
- **THEN** `indexed_source_commit` equals `S`
- **AND** `G` is not considered missing from the graph because graph artifacts are excluded from the corpus.

### Requirement: Generated committed files use an allowlist

The committed generated baseline SHALL be limited to `graphify-out/graph.json`, `graphify-out/manifest.json`, `graphify-out/GRAPH_REPORT.md`, and project-owned `graphify-out/baseline.json`, unless pinned-version evidence proves an additional machine file is essential and architecture is amended.

#### Scenario: Unexpected generated file appears

- **WHEN** Graphify emits HTML, cache, converted document, API/cost output, log, environment, package, or temporary data
- **THEN** the wrapper or review rejects it from the commit.

### Requirement: Frozen baseline remains unchanged during active work

During architecture implementation, independent review, testing, and validation, agents SHALL NOT rebuild or incrementally update the graph. Hooks, watch mode, MCP, Graphify-installed skills, persistent Graphify agent instructions, and merge drivers SHALL be absent.

#### Scenario: Feature branch differs from indexed baseline

- **WHEN** a feature branch contains changes after the indexed source commit
- **THEN** the agent reads every material changed file directly
- **AND** uses the graph only for candidate relationships in the unchanged baseline
- **AND** does not modify graph artifacts in that session.

### Requirement: Refresh occurs at a controlled post-archive checkpoint

The standard graph-enabled workflow SHALL refresh after archive and post-archive validation, using the final source state, followed by a separate graph-only commit and lightweight integrity review.

#### Scenario: Small completed change qualifies for incremental refresh

- **WHEN** version, ignore policy, source roots, and package boundaries are unchanged and deletion/rename checks pass
- **THEN** the wrapper runs pinned-version update-check and incremental-update commands accepted by local CLI help
- **AND** updates metadata to the exact final source commit.

#### Scenario: Rebuild trigger is present

- **WHEN** the version or ignore policy changed, source topology changed materially, mass rename/delete occurred, ghost nodes or integrity failure appear, topology shrinks unexpectedly, the rebuild threshold is reached, or an architect requests it
- **THEN** a full rebuild is required instead of ordinary incremental refresh.

### Requirement: Deletions and renames receive explicit integrity checks

Incremental acceptance SHALL verify that deleted or renamed source nodes and their edges are removed. A failure SHALL trigger the full-rebuild policy rather than preserving ghost topology.

#### Scenario: Disposable incremental probe renames or deletes a file

- **WHEN** a synthetic probe is incrementally updated and then renamed or removed
- **THEN** stale nodes disappear
- **OR** the wrapper fails and directs a full rebuild
- **AND** no probe artifact is committed.

### Requirement: Security exclusions are layered and verified

`.graphifyignore`, code-only mode, wrapper allowlists, textual scans, and structured scans SHALL protect credentials, environment files, private keys, cookies, sessions, tokens, real Excel/inventory data, deployment-local files, Git credential storage, temporary worktrees, and user-specific absolute paths.

#### Scenario: Sensitive or absolute-path evidence is detected

- **WHEN** generated output contains excluded paths, secret-like values, real inventory, a Windows drive/UNC checkout path, or a POSIX absolute checkout path
- **THEN** generation fails nonzero
- **AND** artifacts are not approved for commit.

### Requirement: Graph consumption works through GitHub without local Graphify

A ChatGPT session with repository access SHALL be able to read baseline metadata, the compact report, and targeted portions of the JSON graph, identify candidate files/symbols, and verify them in GitHub source without installing Graphify.

#### Scenario: ChatGPT investigates a project flow

- **WHEN** ChatGPT has GitHub access but no local Graphify executable
- **THEN** it verifies the baseline SHA and hashes from committed metadata
- **AND** uses report/graph content only to narrow candidate source
- **AND** checks the current GitHub branch and source before concluding.

### Requirement: Reproducibility is topology-based where bytes are unstable

Acceptance SHALL compare source-file sets, node identities, extracted relationships, counts, and absence of checkout paths across repeated runs/worktrees. Byte-for-byte equality SHALL NOT be required when the pinned official format contains timestamps or non-semantic ordering, but every material difference SHALL be explained.

#### Scenario: Same source commit is built twice

- **WHEN** the same exact source commit and ignore file are processed twice with Graphify 0.9.26
- **THEN** source-file set and node identities match
- **AND** extracted-edge differences are absent or documented and accepted
- **AND** no checkout-specific absolute path appears.

### Requirement: Graph failure does not redefine production correctness

Graph refresh is a separate artifact step. Failure after successful production validation SHALL NOT invalidate that validation, but it SHALL block the normal graph-enabled merge checkpoint unless an architect records an explicit stale-graph exception and follow-up.

#### Scenario: Graph generation fails after archive validation

- **WHEN** production implementation and post-archive checks passed but graph generation fails
- **THEN** no fabricated baseline is committed
- **AND** the existing graph is marked stale
- **AND** an architect explicitly decides repair-before-merge or temporary merge with tracked follow-up.

### Requirement: Documentation-only changes use a scoped refresh decision

A documentation-only change that does not affect indexed code, graph policy, source roots, ignore rules, wrapper behavior, or metadata contract SHALL NOT require graph refresh.

#### Scenario: Non-indexed documentation changes only

- **WHEN** a completed change modifies only non-indexed documentation and no graph contract
- **THEN** the architect may record that graph refresh is unnecessary
- **AND** the existing indexed source relationship remains accurately described.
