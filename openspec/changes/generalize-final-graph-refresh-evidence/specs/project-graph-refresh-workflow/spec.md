# project-graph-refresh-workflow Specification

## ADDED Requirements

### Requirement: Final Graphify refresh supports ordinary archived changes

The repository-local Graphify refresh workflow SHALL support a final refresh
checkpoint for an ordinary archived OpenSpec change without requiring that change
to impersonate the historical `frozen-project-graph-baseline` workflow.

#### Scenario: Ordinary archived change reaches final refresh

- **GIVEN** an ordinary OpenSpec change has a dedicated archive commit
- **AND** its final source commit has been independently validated after every required prerequisite merge
- **AND** a dedicated evidence-only commit follows that validated source commit
- **AND** the change is absent from the active change directory and present at its declared archive path
- **WHEN** the final Graphify wrapper is invoked with the deterministic change-scoped evidence path and explicit source ref
- **THEN** the wrapper accepts the workflow only when all evidence, lineage, source-binding, protection, and graph-integrity contracts pass
- **AND** it binds generated baseline metadata to the wrapper-derived evidence commit that equals source `HEAD`

### Requirement: Change-scoped evidence path is deterministic and repository-verifiable

The final Graphify workflow SHALL derive the ordinary evidence path as
`openspec/validation/<change-name>.post-archive.json` from a semantic OpenSpec
change name and SHALL verify the evidence against committed repository bytes.

#### Scenario: Valid committed evidence

- **GIVEN** evidence exists at the path derived from the requested change name
- **AND** the file is tracked, not ignored, present in source `HEAD`, and its working-tree bytes hash to the committed `HEAD` blob after repository filters
- **AND** the evidence change name matches the path-derived change name
- **WHEN** the final gate evaluates the evidence
- **THEN** it proceeds to exact-schema, archive-state, ancestry, verdict, source-binding, and evidence-only delta checks

#### Scenario: Invalid evidence location or bytes

- **GIVEN** evidence is absolute, outside the source tree, path-traversing, at a non-derived path, has an alternate extension, is untracked, ignored, locally modified, missing from `HEAD`, or mismatched to the declared change name
- **WHEN** the final gate evaluates the evidence
- **THEN** it fails before Graphify generation

### Requirement: Ordinary evidence schema is exact and non-self-referential

Ordinary evidence SHALL contain exactly the following top-level fields:

- `schema_version` equal to `1`;
- `change_name`;
- `archive_path`;
- `archive_commit`;
- `validated_source_commit`;
- `openspec_all_validation` with only `status`;
- `python_tests` with only `status`, `tests`, `failures`, `errors`, and `skips`;
- `git_diff_check` with only `status`;
- `repository_protection` with only `status`;
- `verdict`.

The evidence SHALL NOT contain `evidence_commit`, `indexed_source_commit`, or any
other field whose value depends on the commit containing the evidence file.
Unknown or missing top-level or nested fields SHALL be rejected.

#### Scenario: Exact ordinary evidence is accepted

- **GIVEN** every required field is present with the required type
- **AND** every required check has `status = pass`
- **AND** the verdict is `APPROVE` or `APPROVE WITH NON-BLOCKING NOTES`
- **AND** every stored commit SHA is a full 40-character repository commit SHA
- **WHEN** the final gate validates the schema
- **THEN** it accepts the schema for lineage checks

#### Scenario: Self-referential or extensible evidence is rejected

- **GIVEN** ordinary evidence contains `evidence_commit`, `indexed_source_commit`, an unknown field, a missing required field, an unknown nested field, a failed check, or a disallowed verdict
- **WHEN** the final gate validates the schema
- **THEN** it fails before Graphify generation

### Requirement: Evidence and indexed commits are wrapper-derived

For an ordinary change, the wrapper SHALL derive both `evidence_commit` and
`indexed_source_commit` as the clean source worktree `HEAD`, and the explicit
source ref SHALL resolve to that same commit.

#### Scenario: Source binding is exact

- **GIVEN** source `HEAD` is clean
- **AND** the explicit source ref resolves to source `HEAD`
- **WHEN** the final gate derives commit identity
- **THEN** `evidence_commit = indexed_source_commit = SourceRoot HEAD`
- **AND** the generated baseline records that full commit SHA

#### Scenario: Source ref differs from source HEAD

- **GIVEN** the explicit source ref does not resolve to source `HEAD`
- **WHEN** the final gate derives commit identity
- **THEN** it fails before Graphify generation

### Requirement: Ordinary lineage uses a strict evidence-only boundary

For an ordinary archived change, the wrapper SHALL verify that:

- `archive_commit` and `validated_source_commit` resolve to full commits;
- `archive_commit` is an ancestor of or equal to `validated_source_commit`;
- `validated_source_commit` contains the declared archive path;
- the active change path is absent from `validated_source_commit`;
- the evidence path is absent from `validated_source_commit` and present in source `HEAD`;
- the complete path delta from `validated_source_commit` to source `HEAD` contains exactly the deterministic evidence JSON.

No process-only allowlist SHALL be accepted in this version.

#### Scenario: Valid evidence-only lineage

- **GIVEN** all lineage and archive-state checks pass
- **AND** `validated_source_commit..HEAD` changes exactly the derived evidence path
- **WHEN** the final gate validates lineage
- **THEN** it accepts the source for later Graphify integrity checks

#### Scenario: Material or process mutation follows validation

- **GIVEN** any production, test, root-spec, archive, validation, Graphify-policy, application-configuration, documentation, or other repository path besides the derived evidence JSON changes in `validated_source_commit..HEAD`
- **WHEN** the final gate validates lineage
- **THEN** it fails before Graphify generation
- **AND** requires renewed independent validation on a new source commit

### Requirement: Prerequisite Graphify repair requires renewed feature validation

An ordinary feature branch that incorporates a Graphify-workflow repair after its
previous validation SHALL undergo renewed independent validation before publishing
ordinary final-refresh evidence. Cross-change infrastructure commits SHALL NOT be
accepted through a post-validation allowlist.

#### Scenario: Older blocked feature incorporates repaired master

- **GIVEN** the Graphify infrastructure change has been independently validated, archived, and merged to `master`
- **AND** an older archived feature branch incorporates that repaired `master`
- **WHEN** the feature prepares its final Graphify evidence
- **THEN** the resulting published remote feature HEAD is independently validated again
- **AND** that renewed validated commit is recorded as `validated_source_commit`
- **AND** the following commit changes only the deterministic feature evidence JSON

#### Scenario: Older validation is reused after infrastructure merge

- **GIVEN** the feature branch incorporated the repaired wrapper after its recorded validation commit
- **BUT** no renewed independent validation was performed
- **WHEN** the final gate evaluates its evidence
- **THEN** the lineage cannot satisfy the strict evidence-only boundary
- **AND** the wrapper rejects the refresh

### Requirement: Historical frozen-baseline compatibility remains explicit

The repository SHALL preserve the published `frozen-project-graph-baseline` final
workflow as an explicit compatibility contract unless a separately approved
migration replaces it.

#### Scenario: Historical baseline evidence remains valid

- **GIVEN** the historical evidence path, change name, commit ordering, and evidence-only delta satisfy the existing frozen-baseline contract
- **WHEN** the final gate evaluates that historical workflow
- **THEN** it applies the historical compatibility rules without reinterpreting the published evidence

#### Scenario: Ordinary change uses historical identity

- **GIVEN** an ordinary later change supplies the historical evidence path or declares `frozen-project-graph-baseline` to bypass ordinary-change checks
- **WHEN** the final gate evaluates the request
- **THEN** it rejects the mismatch

### Requirement: Existing graph publication protections are preserved

Generalizing evidence SHALL NOT weaken Graphify version pinning, clean-worktree
checks, generated artifact allowlists, UTF-8 without BOM and LF canonicalization,
JSON validation, published-byte hashes, sensitive-data scans, absolute-path scans,
rename/delete checks, ghost-node checks, topology checks, deterministic
publication, or graph-only commit scope.

#### Scenario: Evidence passes but graph integrity fails

- **GIVEN** the change-scoped evidence and lineage checks pass
- **BUT** any existing graph integrity, security, encoding, hash, topology, or publication check fails
- **WHEN** the wrapper runs the refresh
- **THEN** it exits nonzero
- **AND** it does not publish a partial or unverified replacement baseline

### Requirement: Failures are structured and non-sensitive

The wrapper SHALL identify the failed contract sufficiently for diagnosis without
exposing secrets, concrete inventory data, or user-specific absolute paths.

#### Scenario: Gate rejects invalid input

- **GIVEN** a final refresh input violates an evidence, schema, lineage, archive-state, source-binding, or mutation-boundary contract
- **WHEN** the wrapper rejects the input
- **THEN** the error identifies the contract category
- **AND** does not print sensitive repository contents or user-specific absolute paths
