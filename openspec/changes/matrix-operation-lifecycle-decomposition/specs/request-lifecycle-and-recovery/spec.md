## ADDED Requirements

### Requirement: Matrix application lifecycle controller
Matrix refresh, route mutation, quick/status refresh, persistent
handler/session reuse, keepalive/liveness, and cleanup SHALL be owned by a
Matrix-specific application/composition controller boundary rather than by
`MatrixScreen` or by a generic multi-device manager.

The controller SHALL capture an explicit immutable Matrix operation context
before background work starts. The context SHALL include the selected Matrix
model, IP address, operation kind, request/generation identity, expected
worker/background-operation identity when applicable, and route output/input
numbers for route mutation. Qt widgets SHALL NOT be the authoritative source
for determining whether a submitted background Matrix operation is current.

All Matrix network I/O SHALL execute outside the Qt GUI thread. This includes
initial Matrix refresh, route mutation, quick/status refresh after mutation,
persistent handler/session acquisition or reconnect, keepalive/liveness
probes, and blocking session cleanup.

#### Scenario: Matrix refresh stays off the GUI thread
- **WHEN** Matrix refresh connects to Extron IN1804, reads status, or parses device data
- **THEN** the network I/O runs through a background execution boundary rather than the Qt GUI thread

#### Scenario: Matrix route mutation stays off the GUI thread
- **WHEN** the operator requests a Matrix route change
- **THEN** handler/session acquisition and `set_connection()` execution run through a background execution boundary rather than the Qt GUI thread

#### Scenario: Matrix quick refresh stays off the GUI thread
- **WHEN** route status is refreshed after a Matrix mutation
- **THEN** `get_connections()` or equivalent handler I/O runs through a background execution boundary rather than the Qt GUI thread

#### Scenario: Explicit Matrix context is captured
- **WHEN** a Matrix operation is submitted
- **THEN** the controller captures immutable model, IP, operation kind, request/generation identity, and expected operation identity before network I/O starts
- **AND** later changes to `device_combo`, `ip_entry`, or `MatrixScreen` widgets do not mutate that operation context

#### Scenario: Controller remains Matrix-specific
- **WHEN** the Matrix lifecycle is extracted from `MainWindow` and `MatrixScreen`
- **THEN** the new component owns only Matrix-specific lifecycle responsibilities
- **AND** it does not become a generic controller for PDU, DMP, codec, SIP, or unrelated device lifecycles

### Requirement: Matrix stale operation suppression
The Matrix application lifecycle SHALL ignore callbacks from superseded Matrix
contexts. Stale Matrix result, error, progress/status, terminal/log, and
finished callbacks SHALL NOT update the current Matrix screen, publish old
routes into the new context, save credential memory, start credential fallback,
reset current worker/session ownership, re-enable or unlock a newer active
operation, start refresh for a newer context, or reuse an old handler/session
for the newer context.

Staleness SHALL be decided from controller-owned context identity such as
generation/request ID, model, IP address, non-secret credential context, and
expected worker/background-operation identity.

#### Scenario: Stale Matrix result is suppressed
- **WHEN** Matrix operation A emits a result after the operator has started Matrix operation B for a different model/IP/context
- **THEN** result A does not update Matrix data, route display, credential memory, or session ownership for operation B

#### Scenario: Stale Matrix error is suppressed
- **WHEN** Matrix operation A emits an error after the operator has started Matrix operation B for a different model/IP/context
- **THEN** error A does not display as the active Matrix error
- **AND** it does not start credential fallback for operation B

#### Scenario: Stale Matrix finished is suppressed
- **WHEN** Matrix operation A emits finished while Matrix operation B is active
- **THEN** finished A does not re-enable, unlock, or reset lifecycle state owned by operation B

#### Scenario: Stale Matrix status is suppressed
- **WHEN** Matrix operation A emits progress, status, or terminal/log output after context change
- **THEN** that callback does not change user-visible state for the active Matrix context

#### Scenario: Stale route follow-up refresh is suppressed
- **WHEN** a route mutation schedules a read-only follow-up refresh for context A
- **AND** the operator changes to context B before that refresh starts or completes
- **THEN** the follow-up refresh does not update context B
- **AND** it does not reuse context A's handler/session for context B

### Requirement: Matrix route mutation safety
Matrix route mutation SHALL be treated as a state-changing command. The
application SHALL NOT blindly repeat a route mutation after an ambiguous
outcome or after the route command may have been delivered.

Credential fallback for a Matrix route operation MAY occur only before any
possible state-changing route command send and only after a structured
confirmed authentication failure. Once `set_connection()` has been invoked,
may have reached the transport, or has an ambiguous outcome, the route
operation SHALL NOT be replayed automatically and SHALL NOT be retried with a
different credential candidate.

After an accepted successful route mutation, the application MAY schedule a
read-only refresh/status reconciliation. That reconciliation SHALL remain bound
to the original Matrix context and SHALL be stale-suppressed if the context
changes.

#### Scenario: Authentication failure before route send may advance
- **WHEN** Matrix route operation setup receives a structured confirmed authentication failure before any route command could be sent
- **AND** another credential candidate remains
- **THEN** the application-owned credential policy may start the next candidate

#### Scenario: Ambiguous route send is not replayed
- **WHEN** a Matrix route command is invoked or may have been delivered and the outcome becomes ambiguous
- **THEN** the application does not automatically send the same route command again
- **AND** it does not retry the mutation with another credential candidate

#### Scenario: Route refresh is context-bound
- **WHEN** a successful Matrix route mutation schedules a follow-up refresh
- **THEN** that refresh uses the original Matrix operation context
- **AND** it cannot update a newer Matrix model/IP/context

### Requirement: Matrix persistent session ownership
If a persistent Matrix handler/session is retained, the Matrix application
controller SHALL own its lifecycle. A persistent Matrix session SHALL be
reusable only when model, IP address, assigned non-secret credential identity
or credential index, protocol/port, and local connected state match the
current Matrix context. Cross-context handler/session reuse SHALL be forbidden.

The Matrix application lifecycle SHALL invalidate and close the superseded
session on model change, IP change, credential change or fallback, explicit
reconnect, authentication/session failure, screen destruction, and application
close. Blocking session creation, liveness checks, route mutation, quick
refresh, and cleanup SHALL run on the owning background execution boundary.
Cleanup SHALL be idempotent and stale-safe.

One persistent Matrix handler SHALL NOT be used concurrently by overlapping
refresh and route operations unless implementation proves the handler is safe
for concurrent use. The conservative requirement is serialized Matrix handler
access per active Matrix context.

#### Scenario: No cross-context session reuse
- **WHEN** a persistent handler/session was created for Matrix device A
- **AND** the operator changes model, IP, or credential context to device B
- **THEN** the session for A is not reused for B

#### Scenario: Credential fallback invalidates session
- **WHEN** Matrix credential fallback advances to another candidate
- **THEN** any persistent session created with the superseded credential context is invalidated before the next Matrix network operation

#### Scenario: Cleanup is stale-safe
- **WHEN** cleanup or finished handling for an old Matrix session completes after a newer Matrix context is active
- **THEN** old cleanup does not clear or disconnect the newer context's handler/session ownership

#### Scenario: Session access is serialized
- **WHEN** one persistent Matrix handler is retained for an active context
- **THEN** overlapping refresh, route, quick refresh, and keepalive operations do not invoke that handler concurrently unless the implementation has a tested thread-safety contract for that handler

#### Scenario: Application close releases Matrix session
- **WHEN** the application closes with a persistent Matrix handler/session active
- **THEN** the Matrix lifecycle owner releases it through the defined cleanup boundary
- **AND** terminal callbacks cannot update a destroyed or newer context
