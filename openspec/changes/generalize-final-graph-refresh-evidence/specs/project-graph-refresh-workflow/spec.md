# project-graph-refresh-workflow Specification

## ADDED Requirements

### Requirement: Final Graphify refresh supports ordinary archived changes

The repository-local Graphify workflow SHALL support final refresh for an ordinary
archived OpenSpec change without requiring historical frozen-baseline identity.

#### Scenario: Ordinary archived change reaches final refresh

- **GIVEN** an ordinary change has archive commit `A`
- **AND** its final source commit `V` was independently validated after every required prerequisite merge
- **AND** validation-report commit `R` contains only the renewed archived `verification-report.md`
- **AND** Graphify-evidence commit `E` contains only the deterministic change-scoped JSON
- **WHEN** the final wrapper is invoked at clean source `HEAD = E`
- **THEN** it accepts only when evidence, report, metadata, lineage, source-binding, protection, and graph-integrity contracts pass
- **AND** baseline metadata records wrapper-derived indexed source commit `E`

### Requirement: Evidence and report paths are deterministic and repository-verifiable

The workflow SHALL derive Graphify evidence as
`openspec/validation/<change-name>.post-archive.json` and SHALL require the JSON
to declare the exact archived `verification-report.md` path.

#### Scenario: Valid committed paths and bytes

- **GIVEN** both paths are repository-relative, change-consistent, tracked, not ignored, present in their declared commits, and unchanged in the working tree
- **WHEN** the final gate evaluates them
- **THEN** it proceeds to schema, report metadata, archive, ancestry, source-binding, and exact-delta checks

#### Scenario: Invalid location or bytes

- **GIVEN** either artifact is absolute, path-traversing, at a wrong path, untracked, ignored, missing, locally modified, or inconsistent with the declared change/archive path
- **WHEN** the final gate evaluates it
- **THEN** it fails before Graphify generation

### Requirement: Ordinary Graphify evidence schema is exact and non-self-referential

Ordinary Graphify evidence SHALL contain exactly:

- `schema_version = 1`;
- `change_name`;
- `archive_path`;
- `archive_commit`;
- `validated_source_commit`;
- `verification_report_path`;
- `verification_report_commit`;
- `openspec_all_validation` with only `status`;
- `python_tests` with only `status`, `tests`, `failures`, `errors`, `skips`;
- `git_diff_check` with only `status`;
- `repository_protection` with only `status`;
- `verdict`.

It SHALL NOT contain `evidence_commit`, `indexed_source_commit`, or another field
whose value depends on the commit containing the JSON. Unknown or missing top-level
or nested fields SHALL be rejected.

#### Scenario: Exact evidence is accepted

- **GIVEN** all exact fields and types are present
- **AND** stored SHAs are full 40-character lowercase repository commit SHAs
- **AND** required checks pass
- **AND** verdict is `APPROVE` or `APPROVE WITH NON-BLOCKING NOTES`
- **WHEN** schema validation runs
- **THEN** it proceeds to report and lineage checks

#### Scenario: Extensible or self-referential evidence is rejected

- **GIVEN** evidence has an unknown/missing field, failed check, disallowed verdict, `evidence_commit`, or `indexed_source_commit`
- **WHEN** schema validation runs
- **THEN** it fails before generation

### Requirement: Validation report has one exact machine-readable metadata block

The renewed archived `verification-report.md` SHALL contain exactly one metadata
block delimited by the literal lines `BEGIN VALIDATION METADATA` and
`END VALIDATION METADATA`.

The block SHALL contain exactly these eight key/value lines in this order:

- `schema_version: 1`;
- `validated_remote_branch: <branch>`;
- `validated_source_commit: <40-char-lowercase-sha>`;
- `verdict: <APPROVE|APPROVE WITH NON-BLOCKING NOTES>`;
- `archive_permitted: <true|false>`;
- `merge_permitted: <true|false>`;
- `production_code_changed_by_validator: <true|false>`;
- `tests_changed_by_validator: <true|false>`.

Each line SHALL use exactly one ASCII colon followed by one ASCII space. Blank
lines, comments, indentation, quoting, duplicate keys, unknown keys, missing keys,
additional keys, duplicate blocks, and reordered keys SHALL be rejected.

#### Scenario: Exact metadata block is accepted

- **GIVEN** the report contains exactly one literal begin marker and one literal end marker
- **AND** the eight required lines occur exactly once in the approved order and grammar
- **AND** `schema_version` is literal `1`
- **AND** `validated_remote_branch` is accepted by `git check-ref-format --branch`
- **AND** `validated_source_commit` is a full lowercase SHA equal to `V`
- **AND** verdict is allowed and equals the Graphify JSON verdict
- **AND** booleans are lowercase literals
- **AND** `archive_permitted = true`
- **AND** validator code/test change flags are both `false`
- **WHEN** the gate parses committed bytes from `R:<verification_report_path>`
- **THEN** it accepts the block for report and lineage checks

#### Scenario: Ambiguous or permissive metadata is rejected

- **GIVEN** the report contains a second block, duplicate or conflicting marker, quoted/example block, malformed line, unknown/missing/duplicate/reordered key, invalid branch, non-lowercase or partial SHA, disallowed verdict, uppercase/non-boolean value, `archive_permitted = false`, or validator code/test change flag `true`
- **WHEN** the gate parses the metadata
- **THEN** it fails before Graphify generation
- **AND** it does not fall back to substring search or free-form Markdown interpretation

### Requirement: Renewed validation report satisfies repository evidence policy

The validation-report commit `R` SHALL contain only the declared archived
`verification-report.md`. Its human-readable portion SHALL satisfy the complete
independent-validation evidence requirements of `RULES.md`, while the exact
metadata block SHALL bind machine-verifiable authority to `V`.

#### Scenario: Complete renewed report

- **GIVEN** the human-readable report records validated remote branch and SHA `V`, commit subject, clean worktree evidence, tool versions, dependency restoration, exact commands and counts, repository-protection findings, verdict and permissions, and whether validator changed code/tests
- **AND** its exact metadata block records the same authoritative branch, SHA, verdict, permissions, and validator-change facts
- **AND** the report is committed unchanged at `R`
- **WHEN** the gate validates the report
- **THEN** it accepts the report for lineage checks

#### Scenario: Incomplete, mismatched, or contradictory report

- **GIVEN** the report omits required human-readable validation facts, has invalid metadata, does not approve `V`, declares another SHA, is modified, is not the only path changed in `V..R`, or contains authoritative human-readable statements that contradict the metadata block
- **WHEN** the gate validates it
- **THEN** it fails before Graphify generation

### Requirement: Ordinary lineage uses exact V-R-E boundaries

For an ordinary change, the wrapper SHALL verify:

- `A`, `V`, and `R` resolve to full commits;
- `A` is an ancestor of or equal to `V`;
- `V` contains the archive path and lacks the active change path;
- `V` is an ancestor of `R`;
- `V..R` changes exactly `verification_report_path`;
- the committed report at `R` contains the exact metadata block binding `V`;
- `verification_report_commit = R`;
- the JSON is absent from `R` and present in `E`;
- `R..E` changes exactly the deterministic JSON;
- clean `SourceRoot HEAD`, explicit `SourceRef`, `E`, derived `evidence_commit`, and derived `indexed_source_commit` are equal.

No process-only allowlist SHALL be accepted.

#### Scenario: Valid V-R-E lineage

- **GIVEN** all ancestry, archive-state, report-binding, exact-metadata, exact-delta, and source-ref checks pass
- **WHEN** the final gate validates lineage
- **THEN** it accepts the source for graph integrity checks

#### Scenario: Additional mutation after validation

- **GIVEN** any additional repository path changes in `V..R` or `R..E`
- **WHEN** lineage validation runs
- **THEN** it fails before generation
- **AND** requires a new valid boundary and renewed validation where applicable

### Requirement: Evidence and indexed commits are wrapper-derived

For ordinary changes, the wrapper SHALL derive both `evidence_commit` and
`indexed_source_commit` as clean source `HEAD`, and explicit `SourceRef` SHALL
resolve to that same commit.

#### Scenario: Exact source binding

- **GIVEN** source is clean and source ref resolves to `HEAD = E`
- **WHEN** commit identity is derived
- **THEN** `evidence_commit = indexed_source_commit = E`

#### Scenario: Source binding differs

- **GIVEN** source ref differs from source HEAD
- **WHEN** identity is derived
- **THEN** it fails before generation

### Requirement: Prerequisite repair requires renewed feature validation

An older feature incorporating a Graphify workflow repair after its previous
validation SHALL be independently revalidated before `R` and `E` are created.
Cross-change post-validation allowlists SHALL NOT be used.

#### Scenario: PR #16 incorporates repaired master

- **GIVEN** the infrastructure repair is validated, archived, and merged
- **AND** PR #16 incorporates repaired `master`
- **WHEN** it prepares final refresh evidence
- **THEN** its new published remote HEAD becomes `V` only after renewed independent validation
- **AND** renewed report commit `R` contains the exact metadata block for `V`
- **AND** JSON commit `E` follows the exact lineage contract

### Requirement: Historical frozen-baseline compatibility remains explicit

The repository SHALL preserve the published `frozen-project-graph-baseline`
workflow as an explicit compatibility path unless separately migrated.

#### Scenario: Historical workflow remains valid

- **GIVEN** historical evidence satisfies its published special-case contract
- **WHEN** the final gate evaluates it
- **THEN** it applies that contract without reinterpretation

#### Scenario: Ordinary change impersonates historical identity

- **GIVEN** an ordinary change supplies historical path or name
- **WHEN** the gate evaluates it
- **THEN** it rejects the mismatch

### Requirement: Existing graph publication protections are preserved

Generalization SHALL NOT weaken version pinning, clean-worktree checks, artifact
allowlists, UTF-8 without BOM/LF canonicalization, JSON validation, published-byte
hashes, sensitive-data and absolute-path scans, rename/delete, ghost-node,
topology, deterministic publication, or graph-only commit scope.

#### Scenario: Lineage passes but graph integrity fails

- **GIVEN** report and lineage checks pass
- **BUT** any graph integrity or publication check fails
- **WHEN** refresh runs
- **THEN** it exits nonzero without publishing a partial replacement

### Requirement: Failures are structured and non-sensitive

The wrapper SHALL identify the failed contract category without exposing secrets,
concrete inventory data, or user-specific absolute paths.
