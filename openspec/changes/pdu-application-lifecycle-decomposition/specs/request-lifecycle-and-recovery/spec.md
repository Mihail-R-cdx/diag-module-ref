## MODIFIED Requirements

### Requirement: Request-context isolation
The application SHALL associate device results, errors, completions, and command
outcomes with the active request context, including the selected model, IP
address, target screen, credential context, and request identifier. It SHALL
ignore callbacks from superseded requests and shall not let them change the
current screen, outlet table, command state, credential memory, or
refresh-button state. This includes bulk PDU sequence results, errors, progress,
partial terminal outcomes, completions, and DMP meter snapshot, error, recovery,
and polling-session callbacks.

For PDU operations, including PCS4i refresh, PCS4i ON/OFF commands, PCS4i bulk
ON/OFF, Aten refresh, Aten ON/OFF/REBOOT commands, and Aten bulk ON/OFF, a
PDU-specific application/composition controller SHALL own the current PDU
operation context generation and PDU callback acceptance after lifecycle
extraction. For Extron DMP 64 Plus meter diagnostics, the
application/composition layer SHALL own the current DMP polling context
generation. Background workers SHALL NOT read Qt widgets, including
`device_combo`, `ip_entry`, `PDUScreen`, `AudioDSPScreen`, or other QWidget
properties, to decide whether an operation is current. Worker module
decomposition SHALL NOT move request-context ownership into focused worker
modules or the `core.worker` facade.

Bulk busy/lock state SHALL be scoped to the PDU context generation/token that
started it. When the application activates a new PDU context, the new context
SHALL establish its own control state independently of the superseded context.
A superseded bulk operation SHALL NOT keep the new context locked. A stale
callback from the old context SHALL NOT unlock, relock, or otherwise change
controls belonging to the new context.

#### Scenario: Stale result arrives after a newer request
- **WHEN** a prior worker emits a result after the operator has started a newer request for a different IP or screen
- **THEN** the prior result is ignored and the newer request remains active

#### Scenario: Stale completion arrives after a newer request
- **WHEN** a prior worker emits completion while a newer request is loading
- **THEN** the prior completion does not re-enable refresh or replace the newer state

#### Scenario: Stale PDU command result arrives
- **WHEN** a PDU command result for an old device/IP/credential context arrives after the operator has switched context
- **THEN** the result does not change the current outlet table, dialogs, status, or credential memory

#### Scenario: Worker does not inspect widgets for staleness
- **WHEN** a background PDU worker checks whether an operation is still current
- **THEN** it uses an application-owned thread-safe validity mechanism
- **AND** it does not read Qt widget properties as the authoritative source

#### Scenario: Stale bulk completion arrives after a newer context
- **WHEN** a prior bulk PDU sequence emits result, error, or completion after the operator has changed PDU context
- **THEN** the prior callback does not change the current outlet table, dialogs, locked controls, credential memory, or refresh state

#### Scenario: Context switch while bulk active
- **GIVEN** Aten bulk is active and its controls are locked
- **WHEN** operator switches to a new PCS4i context
- **THEN** the new context does not inherit the old bulk lock
- **AND** old Aten callbacks cannot change the PCS4i control state

#### Scenario: Stale completion cannot unlock new active bulk
- **GIVEN** old context bulk becomes stale
- **AND** a new context starts its own bulk operation
- **WHEN** old bulk completion arrives
- **THEN** it does not unlock controls owned by the new bulk operation

#### Scenario: Worker does not inspect widgets for bulk staleness
- **WHEN** a background bulk PDU worker checks whether the sequence or next outlet is still current
- **THEN** it uses an application-owned non-GUI validity mechanism
- **AND** it does not read Qt widget properties as authoritative context

#### Scenario: Stale DMP snapshot arrives after context change
- **WHEN** an old DMP polling session emits a meter snapshot after model, IP, screen, or credential context changed
- **THEN** the old snapshot does not update `AudioDSPScreen`
- **AND** it does not update credential memory or restart the current DMP context

#### Scenario: DMP worker does not inspect widgets
- **WHEN** a DMP polling worker checks whether its context is still current
- **THEN** it uses an application-owned non-GUI validity mechanism
- **AND** it does not read `device_combo`, `ip_entry`, or `AudioDSPScreen`

#### Scenario: Decomposed worker does not own request generation
- **WHEN** a worker is moved into a focused module
- **THEN** request generation, stale-result suppression, and credential memory updates remain owned by the application/composition layer

## ADDED Requirements

### Requirement: PDU application lifecycle controller
PDU refresh, individual outlet mutation, sequential bulk mutation, PDU operation
identity, PDU context generation, PDU-specific worker signal binding, stale
callback acceptance, context-scoped mutation/busy state, and PDU mutation
reconciliation SHALL be owned by a PDU-specific application/composition
controller boundary rather than by `PDUScreen`, directly by
`VCSDiagnosticApp`, or by a generic multi-device manager.

The controller SHALL capture an immutable non-secret PDU operation context before
background work is submitted. The effective context identity SHALL include at
least the selected PDU model, IP address, operation kind, PDU context generation
or equivalent opaque revision, unique operation ID, non-secret credential
context revision, assigned credential candidate index when applicable, outlet
number or immutable bulk operation identity when applicable, and expected
worker/background-operation identity when applicable. Credential values,
credential dictionaries, cookies, Session IDs, CSRF tokens, handler/session
objects, and transport objects SHALL NOT be part of public PDU operation
context.

The controller SHALL invalidate superseded PDU lifecycle authority on relevant
model, IP, credential-context revision, screen lifecycle, and application
shutdown changes. A stale queued operation SHALL be rejected before handler
acquisition and network I/O whenever its background execution has not yet
started device work.

All PDU network work SHALL remain outside the Qt GUI thread through the existing
background execution boundary. This includes refresh, individual outlet
mutation, sequential bulk mutation and its inter-outlet delays,
refresh/reconciliation after mutation, handler acquisition/connect, and blocking
handler/session cleanup when such cleanup belongs to the operation lifecycle. A
synchronous handler call moved from `VCSDiagnosticApp` into an ordinary
controller method SHALL NOT satisfy this requirement.

#### Scenario: Explicit immutable PDU context is captured
- **WHEN** a PDU refresh, individual mutation, bulk mutation, or reconciliation operation is submitted
- **THEN** the controller captures immutable model, IP, operation kind, PDU generation, unique operation identity, credential-context revision, assigned candidate index when applicable, target outlet or bulk identity when applicable, and expected worker/background identity when applicable
- **AND** later changes to `device_combo`, `ip_entry`, `PDUScreen`, or credential configuration do not mutate that submitted context

#### Scenario: Stale queued PDU operation stops before network I/O
- **GIVEN** a PDU operation was queued for context A
- **AND** context A becomes superseded before the operation acquires a handler or starts device network I/O
- **WHEN** the queued operation reaches its execution gate
- **THEN** it is discarded as stale before handler acquisition and network I/O

#### Scenario: PDU refresh stays off the GUI thread
- **WHEN** PDU refresh connects to Aten or PCS4i and reads device/outlet state
- **THEN** handler acquisition and network I/O execute through the PDU background worker boundary rather than the Qt GUI thread

#### Scenario: Individual mutation stays off the GUI thread
- **WHEN** the operator requests an individual PDU outlet mutation
- **THEN** handler acquisition, state-changing send, readback, and reconciliation I/O execute through the PDU background execution boundary rather than the Qt GUI thread

#### Scenario: Bulk mutation stays off the GUI thread
- **WHEN** the operator requests sequential bulk ON or OFF
- **THEN** handler acquisition, outlet sub-operations, inter-outlet delays, and terminal cleanup execute through the PDU background execution boundary rather than the Qt GUI thread

#### Scenario: Reconciliation is bound to the originating context
- **WHEN** an accepted PDU mutation outcome requires refresh/reconciliation
- **THEN** the follow-up operation is bound to the originating immutable PDU context
- **AND** a later model, IP, credential-context, or generation change prevents that old reconciliation from updating the newer PDU context

#### Scenario: Controller remains PDU-specific
- **WHEN** PDU lifecycle is extracted from `VCSDiagnosticApp`
- **THEN** the new controller owns only PDU-specific refresh and mutation lifecycle responsibilities
- **AND** it does not become a generic controller for Matrix, DMP, codec, SIP, or unrelated device families

#### Scenario: MainWindow retains only PDU composition ownership
- **WHEN** the PDU lifecycle extraction is complete
- **THEN** `VCSDiagnosticApp` creates and wires the PDU screen/controller, supplies global model/IP context and application-owned credential callbacks, maps accepted controller outcomes into global shell state, and delegates invalidation/shutdown
- **AND** it no longer directly owns PDU operation state machines, PDU worker binding, PDU context generation, PDU-specific stale callback logic, or PDU-specific refresh-after-mutation policy

### Requirement: PDU controller stale callback acceptance
The PDU application controller SHALL accept a PDU callback only when its
immutable context and expected operation/worker identity match the controller's
current PDU lifecycle authority. Currentness SHALL account for PDU generation,
model, IP address, unique operation identity, non-secret credential-context
revision, assigned candidate index when applicable, and expected
worker/background-operation identity when applicable. Candidate index alone
SHALL NOT be sufficient to prove currentness.

This acceptance rule SHALL apply independently to refresh, individual mutation,
bulk mutation, and post-mutation reconciliation result, error, progress/status,
and finished callbacks, including structured partial bulk outcomes. A stale
callback SHALL NOT update `PDUScreen`, change current outlet/device data, save
credential memory, advance credential fallback, start another credential
attempt, start refresh or reconciliation for a newer context, change current
mutation/busy state, unlock or relock controls owned by a newer operation,
change global refresh/loading state for a newer request, or surface the old
operation outcome as the result of the current context.

#### Scenario: Stale refresh callback is suppressed
- **WHEN** refresh A emits result, error, progress/status, or finished after PDU context B has become current
- **THEN** callback A does not update PDU data or global request state for context B
- **AND** it does not save a credential or start credential fallback for context B

#### Scenario: Stale individual mutation callback is suppressed
- **WHEN** individual mutation A emits result, error, progress/status, or finished after another PDU context or mutation B has become current
- **THEN** callback A does not update outlet data, show an old mutation outcome as current, change credential memory, or alter controls owned by B

#### Scenario: Stale bulk callback is suppressed
- **WHEN** bulk operation A emits full result, partial terminal result, error, progress/status, or finished after context B has become current
- **THEN** callback A does not update context B, change its busy state, unlock its controls, persist a credential, or start bulk retry/fallback for B

#### Scenario: Stale finished cannot clear newer mutation state
- **GIVEN** operation A is superseded and operation B owns current individual or bulk mutation busy state
- **WHEN** finished for operation A arrives
- **THEN** it does not clear, unlock, relock, or otherwise change mutation state owned by operation B

#### Scenario: Stale mutation cannot refresh a newly selected PDU
- **WHEN** mutation A completes after the operator changed to a different PDU model, IP, credential context, or generation
- **THEN** mutation A does not trigger refresh/reconciliation for the newly selected PDU
- **AND** any already queued reconciliation from A is suppressed before it can update the new context
