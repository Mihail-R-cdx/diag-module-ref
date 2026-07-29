# agent-project-navigation Delta

## RENAMED Requirements

- FROM: `### Requirement: Published project graph is a frozen navigation baseline`
- TO: `### Requirement: Project graph is a local-only optional navigation helper`
- FROM: `### Requirement: Graph generation is explicit and pinned`
- TO: `### Requirement: Local graph helper is explicit and pinned`
- FROM: `### Requirement: Initial graph is local code-only and has no visualization`
- TO: `### Requirement: Local graph corpus is code-only and has no visualization`
- FROM: `### Requirement: Security exclusions are layered and verified`
- TO: `### Requirement: Local graph security exclusions are layered and verified`

## MODIFIED Requirements

### Requirement: Project graph is a local-only optional navigation helper

Graphify MAY be used as an optional local navigation helper for candidate file,
symbol, and relationship discovery. Generated graph output SHALL NOT be a
repository artifact, OpenSpec authority, validation evidence, archive
requirement, merge requirement, CI requirement, production correctness evidence,
or required dependency for ChatGPT or Codex.

Generated graph output SHALL be written only to an ignored local output
directory, `.graphify-local/`, and SHALL NOT be committed, included in PR diffs,
stored as validation evidence, archived, or required for merge. Absence,
failure, or staleness of local graph output SHALL NOT block architecture,
implementation, independent validation, archive, post-archive checks, or merge.

#### Scenario: Agent begins graph-assisted orientation

- **WHEN** an agent uses local graph output for orientation
- **THEN** it treats that output only as candidate navigation data
- **AND** it reads `RULES.md`, applicable OpenSpec artifacts, current source,
  tests, and the current branch diff before making material conclusions
- **AND** it does not require any committed `graphify-out/` metadata.

#### Scenario: Graph is absent or stale

- **WHEN** local graph output is absent, invalid, stale, or unavailable in the
  current session
- **THEN** ordinary development and validation remain possible through
  authoritative sources
- **AND** the agent reports the graph condition rather than silently rebuilding
  it as part of an unrelated task
- **AND** no Graphify evidence, stale-graph exception, or graph refresh commit
  is required.

#### Scenario: Ordinary change completes without graph output

- **GIVEN** an ordinary change satisfies its approved OpenSpec, source, tests,
  independent validation, archive, and post-archive requirements
- **WHEN** no local graph exists or the local graph is stale
- **THEN** the change may continue and merge without generating or committing
  graph artifacts.

### Requirement: Authority and confidence remain explicit

Graph edges SHALL be consumed according to their confidence category.
`EXTRACTED` is a static observation only; `INFERRED` is a navigation
hypothesis; `AMBIGUOUS` SHALL NOT be used as evidence. Review findings SHALL
cite current source evidence.

#### Scenario: Query returns an inferred relationship

- **WHEN** a graph query returns an `INFERRED` or `AMBIGUOUS` relationship
- **THEN** the agent labels the confidence honestly
- **AND** opens the relevant source files
- **AND** does not issue a material finding from graph output alone.

### Requirement: Local graph helper is explicit and pinned

The local helper SHALL use the isolated package `graphifyy==0.9.26`, invoked
through the `graphify` executable, unless a separately approved architecture
change updates the version. It SHALL NOT be added as an application runtime
dependency. Floating installs are forbidden.

The repository-local helper, if retained, SHALL run against the current
checkout or an explicitly supplied local source and SHALL write only under
ignored `.graphify-local/`. It SHALL NOT create commits, branches, worktrees,
archives, validation evidence, publication metadata, frozen baselines, graph
review artifacts, or merge gates.

#### Scenario: Wrapper starts a build or refresh

- **WHEN** `tools/refresh_project_graph.ps1` starts local graph generation
- **THEN** it verifies repository root, pinned Graphify version,
  `.graphifyignore`, local output path, and source/output boundaries
- **AND** writes accepted output only under ignored `.graphify-local/`
- **AND** fails nonzero when prerequisites or Graphify execution fail.

#### Scenario: Final mode is attempted before archive validation

- **WHEN** a caller attempts to use final-baseline, archive-lineage,
  evidence-only, graph-only, or publication-target behavior
- **THEN** the local helper rejects the retired committed-publication workflow
- **AND** directs the caller to local disposable output only.

### Requirement: Local graph corpus is code-only and has no visualization

Local graph generation SHALL index only the supported code corpus using
code-only behavior and SHALL disable or reject HTML visualization. It SHALL NOT
require an external LLM API. OpenSpec Markdown, archived changes, credentials,
real inventory, Excel files, local output, worktrees, generated graph output,
and deployment-local data SHALL be excluded.

#### Scenario: Initial baseline is generated

- **WHEN** a developer runs the local helper against the current checkout
- **THEN** any generated graph describes only the approved code corpus visible
  to the local run
- **AND** OpenSpec Markdown, real inventory, Excel, secrets, temporary
  worktrees, `.graphify-local/`, `graphify-out/`, and generated graph output
  are absent from the indexed corpus
- **AND** `graph.html` is neither required nor committed.

### Requirement: Local graph security exclusions are layered and verified

`.graphifyignore`, code-only mode, local-helper checks, textual scans, and
structured scans SHALL protect credentials, environment files, private keys,
cookies, sessions, tokens, real Excel/inventory data, deployment-local files,
Git credential storage, temporary worktrees, local graph output, and
user-specific absolute paths.

#### Scenario: Sensitive or absolute-path evidence is detected

- **WHEN** local generated output contains excluded paths, secret-like values,
  real inventory, a Windows drive or UNC checkout path, or a POSIX absolute
  checkout path
- **THEN** generation fails nonzero or rejects the local output
- **AND** no tracked repository file is modified
- **AND** errors avoid printing secret values.

## ADDED Requirements

### Requirement: Generated graph artifacts are not tracked

The repository SHALL NOT track generated Graphify output. Implementation SHALL
remove tracked `graphify-out/graph.json`, `graphify-out/manifest.json`,
`graphify-out/GRAPH_REPORT.md`, and `graphify-out/baseline.json` without
rewriting Git history. New local output SHALL be stored under ignored
`.graphify-local/`.

#### Scenario: Implementation removes committed graph output

- **WHEN** the local-only implementation updates the repository
- **THEN** the tracked generated Graphify files are removed from the current
  tree
- **AND** `.graphify-local/` is ignored
- **AND** historical commits containing older graph artifacts remain available
  through Git history.

#### Scenario: Developer rebuilds local graph

- **WHEN** a developer rebuilds the graph locally
- **THEN** output is written to `.graphify-local/`
- **AND** `git status --short` shows no generated Graphify output staged or
  modified in tracked files.

### Requirement: Standard lifecycle is graph-unaware

The ordinary OpenSpec lifecycle SHALL NOT include Graphify refresh,
graph-only branches, graph-only commits, final graph review, Graphify evidence
JSON, validation-report-only commits, evidence-only commits, stale-graph
exceptions, or any `A -> S -> E -> G` publication workflow.

#### Scenario: Ordinary OpenSpec change reaches merge

- **GIVEN** an ordinary change passes architecture, implementation,
  independent validation, archive, post-archive checks, and merge readiness
- **WHEN** local graph output is absent or stale
- **THEN** no Graphify command or evidence is required
- **AND** merge readiness is decided by the change's authoritative OpenSpec,
  source, tests, validation, archive, and Git evidence.

#### Scenario: Local helper fails

- **WHEN** local Graphify generation fails
- **THEN** the failure affects only that local helper run
- **AND** unrelated production validation, archive, post-archive checks, and
  merge decisions remain governed by authoritative project evidence.

## REMOVED Requirements

### Requirement: Baseline metadata proves the indexed source

### Requirement: Generated committed files use an allowlist

### Requirement: Frozen baseline remains unchanged during active work

### Requirement: Refresh occurs at a controlled post-archive checkpoint

### Requirement: Deletions and renames receive explicit integrity checks

### Requirement: Graph consumption works through GitHub without local Graphify

### Requirement: Reproducibility is topology-based where bytes are unstable

### Requirement: Graph failure does not redefine production correctness

### Requirement: Documentation-only changes use a scoped refresh decision
