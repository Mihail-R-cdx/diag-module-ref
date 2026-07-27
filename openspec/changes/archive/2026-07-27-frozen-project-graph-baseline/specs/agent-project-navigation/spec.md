# agent-project-navigation Specification

## ADDED Requirements

### Requirement: Published project graph is a frozen navigation baseline

The repository MAY publish a committed Graphify map of one exact stable source commit for read-only agent navigation. The map SHALL NOT be treated as architecture, workflow state, validation evidence, or a substitute for current source and tests.

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
- **THEN** it verifies the repository root, exact Graphify version, clean
  required source state, explicit baseline stage, source ref, target branch,
  full source SHA, and `.graphifyignore`
- **AND** it verifies that the explicit source ref resolves to the source
  worktree `HEAD`
- **AND** fails nonzero when any prerequisite or Graphify command fails.

#### Scenario: Final mode is attempted before archive validation

- **WHEN** `tools/refresh_project_graph.ps1` is invoked with
  `BaselineStage = Final` before the change is archived and post-archive
  validation evidence exists
- **THEN** it fails nonzero before Graphify generation
- **AND** reports that final baseline generation requires project-owned
  post-archive validation evidence.

### Requirement: Initial graph is local code-only and has no visualization

The first baseline SHALL index only the actual supported code corpus using code-only behavior and SHALL disable/reject HTML visualization. It SHALL NOT require an external LLM API.

#### Scenario: Initial baseline is generated

- **WHEN** the approved initial-build mode runs on a clean source commit
- **THEN** nonzero graph nodes and edges are produced from actual code roots
- **AND** OpenSpec Markdown, real inventory, Excel, secrets, temporary worktrees, and graph output are absent
- **AND** `graph.html` is neither required nor committed.

### Requirement: Baseline metadata proves the indexed source

`graphify-out/baseline.json` SHALL use schema version 2 and record generator,
exact Graphify version, mode, baseline stage, full indexed source SHA, indexed
source ref, target branch, UTC generation time, graph and ignore-file SHA-256
hashes, and node/edge counts. It SHALL NOT contain user-specific paths,
secrets, ambiguous `indexed_branch`, or a `detached` placeholder.

The ignore-file SHA-256 SHALL be computed from the actual `.graphifyignore`
bytes read by Graphify. The repository SHALL pin `/.graphifyignore text eol=lf`
in `.gitattributes` so Windows `core.autocrlf=true` checkouts preserve the same
hash as LF checkouts.

The graph SHA-256 SHALL be computed from the actual canonical
`graphify-out/graph.json` bytes published by the wrapper. The four generated
artifacts SHALL be deterministic UTF-8 without BOM and LF files, and the wrapper
SHALL canonicalize them before JSON parsing, structural validation,
security/path scans, hash calculation, and publication. The repository SHALL pin
exact LF rules for `graphify-out/graph.json`, `graphify-out/manifest.json`,
`graphify-out/GRAPH_REPORT.md`, and `graphify-out/baseline.json` in
`.gitattributes`.

#### Scenario: Bootstrap graph is generated

- **WHEN** bootstrap generation runs
- **THEN** metadata records `baseline_stage = bootstrap`
- **AND** `indexed_source_ref` resolves to the exact indexed source commit
- **AND** `target_branch` identifies the merge target
- **AND** `ignore_file_sha256` matches the actual LF `.graphifyignore`
  working-tree bytes
- **AND** `graph_sha256` matches the actual canonical UTF-8/LF
  `graphify-out/graph.json` working-tree bytes
- **AND** the report states that the graph is pre-archive, non-final, and not
  the navigation baseline for the next ordinary change.

#### Scenario: Final graph is generated

- **WHEN** final generation runs after independent review, archive, and
  post-archive validation
- **THEN** metadata records `baseline_stage = final`
- **AND** the source commit includes the reviewed production/test state,
  archived OpenSpec state, Graphify wrapper, `.graphifyignore`, runbook, and
  `RULES.md`
- **AND** the wrapper verifies valid project-owned evidence JSON with
  `change_name = frozen-project-graph-baseline`
- **AND** the evidence path is exactly
  `openspec/validation/frozen-project-graph-baseline.post-archive.json`
- **AND** the evidence is tracked by Git, exists in the source `HEAD` tree, is
  not ignored, and hashes to the same Git blob as the committed `HEAD` blob
  after repository filters
- **AND** `archive_commit` is a full SHA and an ancestor of
  `validated_source_commit`
- **AND** `validated_source_commit` is a full SHA and an ancestor of the source
  worktree `HEAD`
- **AND** the delta from `validated_source_commit` to source worktree `HEAD`
  contains only
  `openspec/validation/frozen-project-graph-baseline.post-archive.json`
- **AND** that evidence path is absent from `validated_source_commit`
- **AND** an archived `frozen-project-graph-baseline` artifact exists under
  `openspec/changes/archive/`
- **AND** active `openspec/changes/frozen-project-graph-baseline/` is absent
- **AND** `openspec_change_validation`, `openspec_all_validation`,
  `python_tests`, and `git_diff_check` have `status = pass`
- **AND** the final graph-only commit contains only allowlisted generated graph
  artifacts.

#### Scenario: Final evidence is local-only or tampered

- **WHEN** final generation receives evidence from an ignored path, untracked
  file, file absent from source `HEAD`, wrong repository path, or tracked file
  modified after commit
- **THEN** the wrapper fails nonzero before Graphify generation
- **AND** does not publish graph artifacts.

#### Scenario: Final evidence commit contains extra changes

- **WHEN** final generation receives committed evidence but the delta from
  `validated_source_commit` to source worktree `HEAD` contains production,
  test, wrapper, ignore, documentation, graph, dependency, archived OpenSpec,
  or any other non-evidence path
- **THEN** the wrapper fails nonzero before Graphify generation
- **AND** does not publish graph artifacts.

#### Scenario: Graph artifacts are stored in a following commit

- **GIVEN** archive commit `A` is an ancestor of validated source commit `S`
- **AND** evidence-only commit `E` records validation of `S`
- **WHEN** graph artifacts are committed in following graph-only commit `G`
- **THEN** `indexed_source_commit` equals `E`
- **AND** `G` is not considered missing from the graph because graph artifacts are excluded from the corpus.

### Requirement: Generated committed files use an allowlist

The committed generated baseline SHALL be limited to `graphify-out/graph.json`, `graphify-out/manifest.json`, `graphify-out/GRAPH_REPORT.md`, and project-owned `graphify-out/baseline.json`, unless pinned-version evidence proves an additional machine file is essential and architecture is amended. These four files SHALL be published as canonical UTF-8 without BOM and LF artifacts.

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

#### Scenario: Implementation review uses bootstrap only

- **WHEN** the architecture implementation is still under independent review
- **THEN** agents may rebuild the bootstrap graph to validate the Graphify
  workflow
- **AND** they SHALL NOT build the final graph, archive, merge, or mark the PR
  ready.

#### Scenario: Small completed change qualifies for incremental refresh

- **WHEN** version, ignore policy, source roots, and package boundaries are unchanged and deletion/rename checks pass
- **THEN** the wrapper runs pinned-version update-check and incremental-update commands accepted by local CLI help
- **AND** updates metadata to the exact final source commit.

#### Scenario: Rebuild trigger is present

- **WHEN** the version or ignore policy changed, source topology changed materially, mass rename/delete occurred, ghost nodes or integrity failure appear, topology shrinks unexpectedly, the rebuild threshold is reached, or an architect requests it
- **THEN** a full rebuild is required instead of ordinary incremental refresh.

#### Scenario: Generated artifact encoding policy changes

- **WHEN** `.gitattributes`, `.graphifyignore`, or generated artifact encoding
  and line-ending policy changes
- **THEN** a full rebuild is required
- **AND** metadata hashes are regenerated by the wrapper from actual canonical
  published bytes.

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
