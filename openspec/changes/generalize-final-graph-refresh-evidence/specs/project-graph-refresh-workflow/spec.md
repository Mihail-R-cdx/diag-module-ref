# project-graph-refresh-workflow Specification

## ADDED Requirements

### Requirement: Final Graphify refresh supports ordinary archived changes

The repository-local Graphify refresh workflow SHALL support a final refresh checkpoint for an ordinary archived OpenSpec change without requiring that change to impersonate the historical `frozen-project-graph-baseline` workflow.

#### Scenario: Ordinary archived change reaches final refresh

- **GIVEN** an OpenSpec change has approved implementation, published independent validation, a dedicated archive commit, passing post-archive strict validation, and a passing full offline test suite
- **AND** the change is absent from the active change directory and present under `openspec/changes/archive/`
- **WHEN** the final Graphify wrapper is invoked with the change-scoped committed validation evidence and an explicit source ref
- **THEN** the wrapper accepts the workflow when all source, evidence, lineage, protection, and integrity contracts pass
- **AND** it binds generated baseline metadata to the exact indexed source commit

### Requirement: Change-scoped evidence is deterministic and repository-verifiable

The final Graphify workflow SHALL use a deterministic repository-owned evidence path derived from the semantic OpenSpec change name and SHALL verify the evidence against committed repository bytes.

#### Scenario: Valid committed evidence

- **GIVEN** evidence exists at the approved change-scoped path under `openspec/validation/`
- **AND** the file is tracked, not ignored, present in source `HEAD`, and its working-tree bytes hash to the committed `HEAD` blob after repository filters
- **AND** the evidence change name matches the path-derived change name
- **WHEN** the final gate evaluates the evidence
- **THEN** it proceeds to schema, archive-state, ancestry, verdict, and source-binding checks

#### Scenario: Invalid evidence location or bytes

- **GIVEN** evidence is absolute, outside the source tree, path-traversing, at a non-approved path, untracked, ignored, locally modified, missing from `HEAD`, or mismatched to the declared change name
- **WHEN** the final gate evaluates the evidence
- **THEN** it fails before Graphify generation

### Requirement: Evidence records the accepted workflow lineage

The evidence contract SHALL identify the archived change, archive commit, independently validated source commit, evidence commit, intended indexed source commit, required passing checks, and accepted validation verdict using full commit SHAs and structured fields.

#### Scenario: Valid lineage

- **GIVEN** all declared commits resolve in the repository
- **AND** their ancestry matches the approved workflow
- **AND** the archive commit contains the declared archived change path
- **AND** the active change path is absent from the indexed source commit
- **AND** the indexed source commit equals the clean source worktree `HEAD` and resolved source ref
- **WHEN** the final gate validates lineage
- **THEN** it accepts the source for later Graphify integrity checks

#### Scenario: Invalid lineage

- **GIVEN** a declared SHA is partial, missing, unrelated, out of order, inconsistent with the archive state, or different from the clean source `HEAD` or source ref
- **WHEN** the final gate validates lineage
- **THEN** it fails before Graphify generation

### Requirement: Post-evidence source mutations fail closed

The final Graphify workflow SHALL define an explicit post-evidence source boundary and SHALL reject unvalidated production, test, root-spec, archived-evidence, Graphify-policy, or application-configuration mutations after that boundary.

#### Scenario: No mutation after accepted boundary

- **GIVEN** the indexed source commit equals the accepted evidence boundary commit, or differs only by an explicitly approved deterministic process-only allowlist
- **WHEN** the final gate compares the source range
- **THEN** it accepts the range

#### Scenario: Material mutation after accepted boundary

- **GIVEN** production source, tests, root specs, archive evidence, Graphify policy, or application configuration changed after the accepted evidence boundary
- **WHEN** the final gate compares the source range
- **THEN** it fails and requires renewed independent validation or a newly approved source boundary

### Requirement: Historical frozen-baseline compatibility remains explicit

The repository SHALL preserve the published `frozen-project-graph-baseline` final workflow as an explicit compatibility contract unless a separately approved migration replaces it.

#### Scenario: Historical baseline evidence remains valid

- **GIVEN** the historical evidence path, change name, commit ordering, and evidence-only delta satisfy the existing frozen-baseline contract
- **WHEN** the final gate evaluates that historical workflow
- **THEN** it applies the historical compatibility rules without reinterpreting the published evidence

#### Scenario: Ordinary change uses historical identity

- **GIVEN** an ordinary later change supplies the historical evidence path or declares `frozen-project-graph-baseline` to bypass ordinary-change checks
- **WHEN** the final gate evaluates the request
- **THEN** it rejects the mismatch

### Requirement: Existing graph publication protections are preserved

Generalizing evidence SHALL NOT weaken Graphify version pinning, clean-worktree checks, generated artifact allowlists, UTF-8 without BOM and LF canonicalization, JSON validation, published-byte hashes, sensitive-data scans, absolute-path scans, rename/delete checks, ghost-node checks, topology checks, deterministic publication, or graph-only commit scope.

#### Scenario: Evidence passes but graph integrity fails

- **GIVEN** the change-scoped evidence and lineage checks pass
- **BUT** any existing graph integrity, security, encoding, hash, topology, or publication check fails
- **WHEN** the wrapper runs the refresh
- **THEN** it exits nonzero
- **AND** it does not publish a partial or unverified replacement baseline

### Requirement: Failures are structured and non-sensitive

The wrapper SHALL identify the failed contract sufficiently for diagnosis without exposing secrets, concrete inventory data, or user-specific absolute paths.

#### Scenario: Gate rejects invalid input

- **GIVEN** a final refresh input violates an evidence, lineage, archive-state, source-binding, or mutation-boundary contract
- **WHEN** the wrapper rejects the input
- **THEN** the error identifies the contract category
- **AND** does not print sensitive repository contents or user-specific absolute paths.