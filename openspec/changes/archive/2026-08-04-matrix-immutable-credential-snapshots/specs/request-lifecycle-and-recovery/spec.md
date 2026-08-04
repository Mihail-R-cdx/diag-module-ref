# request-lifecycle-and-recovery Delta

## ADDED Requirements

### Requirement: Matrix credential snapshot continuity across operation lifecycle

When application composition submits a Matrix refresh, route, or quick/status operation with a request-scoped credential candidate snapshot, the Matrix lifecycle SHALL preserve the assigned candidate's mapping semantics from submission through candidate lookup, redaction preparation, handler/session acquisition, operation execution, and terminal cleanup.

The submitted snapshot SHALL remain bound to the immutable Matrix operation context and assigned candidate index. The controller SHALL NOT discard, replace, or re-resolve that candidate merely because its concrete container is immutable or is not a `dict`. Mapping mutability SHALL NOT participate in operation freshness, session identity, credential fallback authority, or successful credential persistence.

Candidate lookup and validation SHALL occur before handler acquisition for a queued current operation. If the operation becomes stale before network work begins, existing stale suppression SHALL discard it before handler construction and network I/O. Adding immutable mapping support SHALL NOT permit stale work to acquire a handler, update the current screen, change credential memory, or emit secret material.

Operation-scoped candidate snapshots SHALL remain private controller state and SHALL be released through the existing terminal/stale cleanup lifecycle. Public operation identity SHALL continue to use only non-secret model, IP, operation/generation identity, credential-context revision, assigned candidate index, and other approved non-secret fields.

#### Scenario: Full refresh preserves immutable candidate snapshot

- **GIVEN** application composition submits a full Extron IN1804 refresh with a frozen candidate tuple and assigned candidate index
- **WHEN** the background Matrix operation reaches candidate lookup and session acquisition
- **THEN** it uses the candidate at that submitted index through its mapping interface
- **AND** the same candidate supplies redaction and handler inputs
- **AND** no provider re-resolution occurs because the candidate is immutable.

#### Scenario: Queued route preserves one assigned candidate

- **GIVEN** a route operation is queued with an assigned immutable candidate mapping
- **WHEN** the operation remains current and reaches the serialized execution lane
- **THEN** session acquisition uses that one assigned mapping
- **AND** route mutation safety and credential fallback rules remain unchanged
- **AND** the candidate container is not exposed in the route intent or public callbacks.

#### Scenario: Mapping implementation is not freshness authority

- **WHEN** two otherwise equivalent Matrix contexts use mutable and immutable mapping implementations for the same assigned candidate index and credential-context revision
- **THEN** container mutability alone does not make either context stale or reusable
- **AND** existing generation, operation identity, model, IP, revision, candidate index, protocol/port, and connected-state rules remain authoritative.

#### Scenario: Stale immutable snapshot stops before handler acquisition

- **GIVEN** a Matrix operation was submitted with an immutable candidate snapshot
- **AND** its Matrix context becomes stale before handler acquisition
- **WHEN** the queued operation reaches its execution gate
- **THEN** it is discarded before handler construction and network I/O
- **AND** its candidate values are not emitted or used to change active credential memory.

#### Scenario: Candidate snapshot is private and released

- **WHEN** a Matrix operation finishes, fails, or is discarded as stale
- **THEN** its private candidate snapshot is removed through the existing operation cleanup lifecycle
- **AND** no candidate mapping is retained in `MatrixOperationHandle`, public context, result, error, status, terminal, or completion payloads.

#### Scenario: Immutable snapshot does not create a new success gate

- **WHEN** Matrix session acquisition succeeds using an immutable candidate mapping
- **THEN** that success alone does not persist the assigned credential index
- **AND** only the existing accepted final full-refresh gate may update successful credential memory
- **AND** route success, quick refresh, keepalive, and stale success remain non-persistence events.

#### Scenario: Local candidate-shape failure does not trigger retry

- **WHEN** a submitted Matrix snapshot yields an absent, out-of-range, or non-mapping assigned candidate before handler acquisition
- **THEN** the operation terminates as a safe local precondition failure
- **AND** no network I/O starts
- **AND** no structured confirmed device rejection exists
- **AND** the application does not advance to another credential candidate.
