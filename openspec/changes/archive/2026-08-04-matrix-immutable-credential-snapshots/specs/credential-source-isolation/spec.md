# credential-source-isolation Delta

## ADDED Requirements

### Requirement: Matrix assigned credential mappings preserve immutable snapshot semantics

The application/composition layer MAY represent a resolved request-scoped Matrix credential candidate as a mutable or immutable object implementing `collections.abc.Mapping`. Freezing the candidate for request isolation SHALL preserve its semantic credential content, assigned candidate index, ordering, and fallback meaning.

`MatrixController`, Matrix background operations, and Matrix session acquisition SHALL accept the assigned candidate through the mapping interface and SHALL NOT require the concrete candidate object to be `dict`. They MAY read required fields and values but SHALL NOT mutate the candidate or convert it into shared mutable credential state.

The same accepted mapping candidate SHALL supply both the scalar authentication inputs used to construct `ExtronIN1804Handler` and the candidate values used by the existing Matrix redaction boundary. Container mutability or concrete mapping implementation SHALL NOT remove assigned credential values from redaction.

An absent, out-of-range, or non-mapping candidate SHALL fail safely before handler construction and network I/O. That local precondition failure SHALL disclose no candidate content, SHALL NOT be treated as confirmed device rejection of the assigned credential, and SHALL NOT authorize credential fallback.

Public Matrix contexts, handles, signals, results, errors, status text, logs, and terminal output SHALL remain free of candidate mappings, credential values, profile identity, and other private credential material.

#### Scenario: Immutable Matrix candidate is accepted

- **GIVEN** application composition resolves an Extron IN1804 username/password candidate
- **AND** freezes that candidate as a `MappingProxyType`
- **WHEN** the assigned Matrix operation reaches controller session acquisition
- **THEN** the controller accepts the candidate through the `Mapping` contract
- **AND** it does not report missing credentials solely because the mapping is immutable
- **AND** it does not mutate the candidate.

#### Scenario: Immutable candidate supplies handler authentication inputs

- **GIVEN** the assigned immutable Matrix mapping contains validated username and password fields
- **WHEN** the controller constructs `ExtronIN1804Handler`
- **THEN** it passes the same assigned candidate's scalar username and password values through the existing constructor boundary
- **AND** it invokes connection under the existing Matrix lifecycle
- **AND** it does not read another candidate or re-resolve provider storage.

#### Scenario: Immutable candidate participates in redaction

- **GIVEN** the assigned Matrix candidate is an immutable mapping
- **WHEN** candidate values appear in a handler exception, terminal callback, or other redaction input
- **THEN** the existing Matrix redaction boundary receives those non-empty candidate values
- **AND** public error, status, log, terminal, and result output contains no credential value.

#### Scenario: Mutable dictionary remains supported

- **GIVEN** an explicit caller or focused unit test supplies the assigned Matrix candidate as a normal `dict`
- **WHEN** the controller uses that candidate
- **THEN** the candidate remains supported through the same mapping contract
- **AND** handler inputs and redaction semantics match an equivalent immutable mapping.

#### Scenario: Non-mapping candidate stops before network I/O

- **WHEN** candidate lookup returns an absent, out-of-range, or non-mapping value
- **THEN** the Matrix operation fails before `ExtronIN1804Handler` construction and connection
- **AND** the failure discloses no candidate content
- **AND** it does not authorize advancement to another credential candidate.

#### Scenario: Snapshot representation does not change fallback policy

- **WHEN** a Matrix request uses an immutable mapping candidate
- **THEN** application-owned candidate ordering, starting index, monotonic fallback, no-wrap behavior, structured authentication authority, and successful-index persistence gates remain unchanged
- **AND** the controller and handler still use only the one assigned candidate for that attempt.

#### Scenario: Public Matrix handle remains secret-free

- **WHEN** a Matrix operation emits result, error, progress, status, terminal, or completion callbacks
- **THEN** the public operation handle and callback payloads contain no candidate mapping or credential value
- **AND** immutable snapshot support does not widen the public Matrix data model.
