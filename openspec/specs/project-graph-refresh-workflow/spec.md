# project-graph-refresh-workflow Specification

## Purpose

Define the repository-local Final Graphify refresh workflow for ordinary
archived OpenSpec changes while preserving the published frozen-baseline
compatibility workflow and graph integrity protections.

## Requirements

### Requirement: Final Graphify refresh supports ordinary archived changes

The repository-local Graphify workflow SHALL support final refresh for an
ordinary archived OpenSpec change without requiring historical
`frozen-project-graph-baseline` identity.

#### Scenario: Ordinary archived change reaches final refresh

- **GIVEN** an ordinary change has archive commit `A`
- **AND** its final source commit `V` was independently validated after every
  required prerequisite merge
- **AND** validation-report commit `R` contains only the renewed archived
  `verification-report.md`
- **AND** Graphify-evidence commit `E` contains only the deterministic
  change-scoped JSON
- **WHEN** the final wrapper is invoked at clean source `HEAD = E`
- **THEN** it accepts only when evidence, report, metadata, lineage,
  source-binding, protection, and graph-integrity contracts pass
- **AND** baseline metadata records wrapper-derived indexed source commit `E`.

### Requirement: Evidence and report paths are deterministic

For ordinary changes, Graphify evidence SHALL be
`openspec/validation/<change-name>.post-archive.json`, where `<change-name>` is
the semantic OpenSpec change name. The JSON SHALL declare the exact archived
`verification-report.md` path.

#### Scenario: Invalid path or bytes are rejected

- **WHEN** either artifact is absolute, path-traversing, at a wrong path,
  untracked, ignored, missing, locally modified, absent from its declared
  commit, or inconsistent with the declared change/archive path
- **THEN** the wrapper fails before Graphify generation.

### Requirement: Ordinary Graphify evidence schema is exact

Ordinary Graphify evidence SHALL contain only `schema_version`, `change_name`,
`archive_path`, `archive_commit`, `validated_source_commit`,
`verification_report_path`, `verification_report_commit`,
`openspec_all_validation`, `python_tests`, `git_diff_check`,
`repository_protection`, and `verdict`.

#### Scenario: Exact evidence is accepted

- **GIVEN** all exact fields and types are present
- **AND** stored SHAs are full 40-character lowercase repository commit SHAs
- **AND** required checks have exact `pass` status
- **AND** test counts are non-negative integers
- **AND** verdict is `APPROVE` or `APPROVE WITH NON-BLOCKING NOTES`
- **WHEN** schema validation runs
- **THEN** it proceeds to report and lineage checks.

#### Scenario: Extensible or self-referential evidence is rejected

- **GIVEN** evidence has an unknown or missing field, failed check, disallowed
  verdict, `evidence_commit`, or `indexed_source_commit`
- **WHEN** schema validation runs
- **THEN** it fails before generation.

### Requirement: Validation report has one exact metadata block

The renewed archived `verification-report.md` SHALL contain exactly one
metadata block delimited by literal `BEGIN VALIDATION METADATA` and
`END VALIDATION METADATA` lines. The block SHALL contain exactly these ordered
keys: `schema_version`, `validated_remote_branch`, `validated_source_commit`,
`verdict`, `archive_permitted`, `merge_permitted`,
`production_code_changed_by_validator`, and `tests_changed_by_validator`.

#### Scenario: Exact metadata block is accepted

- **GIVEN** the markers occur exactly once, in order, on their own lines
- **AND** the eight key/value lines use exact `key: value` grammar
- **AND** branch, SHA, verdict, booleans, archive permission, and validator
  mutation flags satisfy the repository contract
- **WHEN** the gate parses committed bytes from `R:<verification_report_path>`
- **THEN** it accepts the block for report and lineage checks.

#### Scenario: Ambiguous metadata is rejected

- **GIVEN** the report contains missing, duplicate, quoted, fenced, malformed,
  unknown, missing, duplicate, or reordered metadata lines or contradictory
  authoritative human-readable statements
- **WHEN** metadata validation runs
- **THEN** it fails before Graphify generation.

### Requirement: Ordinary lineage uses exact V-R-E boundaries

For ordinary changes, the wrapper SHALL verify that `A <= V < R < E`,
`V` contains the archive path and lacks the active change path, `V..R` changes
only the declared report, the report metadata binds to `V`,
`verification_report_commit = R`, the JSON is absent from `R`, `R..E` changes
only deterministic Graphify evidence, and clean `SourceRoot HEAD = SourceRef =
E`.

#### Scenario: Additional mutation after validation

- **GIVEN** any additional repository path changes in `V..R` or `R..E`
- **WHEN** lineage validation runs
- **THEN** it fails before generation.

### Requirement: Historical compatibility remains explicit

The repository SHALL preserve the published `frozen-project-graph-baseline`
workflow as a separate compatibility path unless separately migrated.

#### Scenario: Ordinary change impersonates historical identity

- **GIVEN** ordinary evidence uses the historical name or path
- **WHEN** the gate evaluates it
- **THEN** it rejects the mismatch.

### Requirement: Existing graph publication protections are preserved

Generalization SHALL NOT weaken version pinning, clean-worktree checks,
generated artifact allowlists, UTF-8 without BOM/LF canonicalization, JSON
validation, hashes, sensitive-data and absolute-path scans, rename/delete
checks, ghost-node checks, topology checks, deterministic publication, source
commit binding, or graph-only commit scope.

#### Scenario: Graph integrity fails after lineage passes

- **WHEN** report and lineage checks pass but graph integrity or publication
  checks fail
- **THEN** the wrapper exits nonzero without publishing a partial replacement.

### Requirement: Failures are structured and non-sensitive

Final gate failures SHALL identify the failed contract category without
printing secrets, concrete inventory data, repository file contents, or
user-specific absolute paths.

#### Scenario: Rejected input produces a structured error

- **WHEN** final Graphify input violates evidence, metadata, lineage,
  archive-state, source-binding, required-check, verdict, historical, or
  graph-integrity contracts
- **THEN** the wrapper reports a typed category and fails closed.
