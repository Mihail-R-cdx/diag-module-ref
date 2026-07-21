## MODIFIED Requirements

### Requirement: Request-context isolation
The application SHALL associate device results, errors, completions, and command outcomes with the active request context, including the selected model, IP address, target screen, credential context, and request identifier. It SHALL ignore callbacks from superseded requests and shall not let them change the current screen, outlet table, command state, credential memory, or refresh-button state. This includes bulk PDU sequence results, errors, progress, partial terminal outcomes, completions, and DMP meter snapshot, error, recovery, and polling-session callbacks.

For PDU operations, including PCS4i refresh, PCS4i ON/OFF commands, PCS4i bulk ON/OFF, Aten refresh, Aten ON/OFF/REBOOT commands, and Aten bulk ON/OFF, a PDU-specific application/composition controller SHALL own the current PDU context generation, independent refresh and mutation operation authority lanes, and PDU callback acceptance after lifecycle extraction. The controller SHALL NOT model all PDU operation freshness through one global `current_operation_id`.

For Extron DMP 64 Plus meter diagnostics, the application/composition layer SHALL own the current DMP polling context generation. Background workers SHALL NOT read Qt widgets, including `device_combo`, `ip_entry`, `PDUScreen`, `AudioDSPScreen`, or other QWidget properties, to decide whether an operation is current. Worker module decomposition SHALL NOT move request-context ownership into focused worker modules or the `core.worker` facade.

Bulk busy/lock state SHALL be scoped to the PDU context generation/token and mutation-lane operation identity that started it. When the application activates a new PDU context, the new context SHALL establish its own control state independently of the superseded context. A superseded bulk operation SHALL NOT keep the new context locked. A stale callback from the old context SHALL NOT unlock, relock, or otherwise change controls belonging to the new context.

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
PDU refresh, individual outlet mutation, sequential bulk mutation, PDU common context identity, independent refresh and mutation authority lanes, PDU-specific worker signal binding, stale callback acceptance, context-scoped mutation/busy state, and PDU mutation reconciliation SHALL be owned by a PDU-specific application/composition controller boundary rather than by `PDUScreen`, directly by `VCSDiagnosticApp`, or by a generic multi-device manager.

The controller SHALL capture immutable non-secret context before background work is submitted. The common PDU context identity SHALL include the selected PDU model, IP address, PDU context generation or equivalent opaque revision, and non-secret credential-context revision. Credential values, credential dictionaries, cookies, Session IDs, CSRF tokens, handler/session objects, and transport objects SHALL NOT be part of public PDU operation context.

The controller SHALL invalidate superseded PDU lifecycle authority on relevant model, IP, credential-context revision, screen lifecycle, and application shutdown changes. A stale queued operation SHALL be rejected before handler acquisition and network I/O whenever its background execution has not yet started device work.

All PDU network work SHALL remain outside the Qt GUI thread through the existing background execution boundary. This includes refresh, individual outlet mutation, sequential bulk mutation and its inter-outlet delays, refresh/reconciliation after mutation, handler acquisition/connect, and blocking handler/session cleanup when such cleanup belongs to the operation lifecycle. A synchronous handler call moved from `VCSDiagnosticApp` into an ordinary controller method SHALL NOT satisfy this requirement.

#### Scenario: Explicit immutable PDU context is captured
- **WHEN** a PDU refresh, individual mutation, bulk mutation, or reconciliation operation is submitted
- **THEN** the controller captures immutable common model, IP, PDU generation, and credential-context revision
- **AND** it also captures the applicable refresh-lane or mutation-lane operation identity and expected worker identity
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

#### Scenario: Controller remains PDU-specific
- **WHEN** PDU lifecycle is extracted from `VCSDiagnosticApp`
- **THEN** the new controller owns only PDU-specific refresh and mutation lifecycle responsibilities
- **AND** it does not become a generic controller for Matrix, DMP, codec, SIP, or unrelated device families

#### Scenario: MainWindow retains only PDU composition ownership
- **WHEN** the PDU lifecycle extraction is complete
- **THEN** `VCSDiagnosticApp` creates and wires the PDU screen/controller, supplies global model/IP context and application-owned credential callbacks, maps accepted controller outcomes into global shell state, and delegates invalidation/shutdown
- **AND** it no longer directly owns PDU operation state machines, PDU worker binding, PDU context generation, PDU-specific stale callback logic, or PDU-specific refresh-after-mutation policy

### Requirement: PDU operation authority lanes
The PDU controller SHALL use a common PDU context identity plus independent operation authority lanes. The common context identity SHALL include PDU context generation, selected model, IP address, and non-secret credential-context revision. The controller SHALL NOT use one global `current_operation_id` for all PDU refresh and mutation operations.

The refresh lane SHALL own user refresh, normal PDU status refresh, and mutation reconciliation refresh. It SHALL have its own current refresh/reconciliation operation identity and expected refresh worker identity. A newer refresh may supersede an older refresh in the refresh lane.

The mutation lane SHALL own individual outlet mutation and sequential bulk mutation. It SHALL have its own current mutation operation identity, mutation kind, and expected mutation worker identity. Individual and bulk mutations SHALL be mutually exclusive in one current PDU context.

Starting a refresh SHALL NOT replace current mutation operation identity, SHALL NOT clear mutation busy state, and SHALL NOT make mutation result/error/finished stale merely because the refresh started. Refresh completion SHALL NOT unlock mutation controls, clear mutation busy state, finalize mutation, or invalidate current mutation worker identity.

Mutation lifecycle SHALL NOT use refresh operation identity as its freshness authority. Mutation completion SHALL NOT accidentally finish, supersede, or clear a newer unrelated refresh lifecycle.

#### Scenario: Refresh does not invalidate active mutation
- **GIVEN** mutation A is active in the mutation lane
- **WHEN** refresh B starts in the refresh lane
- **THEN** refresh B does not replace mutation A operation identity
- **AND** refresh B does not clear mutation busy state
- **AND** mutation A result, error, or finished remains current when its common context and mutation lane identity still match

#### Scenario: Refresh completion cannot finalize mutation
- **GIVEN** mutation A is active
- **AND** refresh B started after mutation A
- **WHEN** refresh B completes
- **THEN** refresh B does not unlock mutation controls, clear mutation busy state, finalize mutation A, or invalidate mutation A worker identity

#### Scenario: Mutation completion cannot finalize unrelated refresh
- **GIVEN** refresh B is current in the refresh lane
- **AND** mutation A is current in the mutation lane
- **WHEN** mutation A completes
- **THEN** mutation A does not complete, clear, or supersede refresh B unless a separate refresh-lane rule accepts or supersedes B

#### Scenario: Conflicting individual and bulk mutations are rejected
- **GIVEN** an individual mutation is active in the mutation lane
- **WHEN** a bulk mutation is requested for the same current PDU context
- **THEN** the bulk mutation is rejected or ignored before worker creation and before state-changing network I/O
- **AND** the active individual mutation remains the mutation-lane owner

#### Scenario: Conflicting bulk and individual mutations are rejected
- **GIVEN** a bulk mutation is active in the mutation lane
- **WHEN** an individual mutation is requested for the same current PDU context
- **THEN** the individual mutation is rejected or ignored before worker creation and before state-changing network I/O
- **AND** the active bulk mutation remains the mutation-lane owner

### Requirement: PDU refresh snapshot ordering and reconciliation authority
A refresh snapshot submitted before a later state-changing mutation starts SHALL NOT later be accepted as authoritative post-mutation PDU state. The controller MAY enforce this through a state epoch, a refresh submission sequence relative to mutation start, explicit supersession of old refresh-lane authority, or an equivalent non-secret mechanism.

Reconciliation SHALL be a refresh-lane operation with additional immutable origin identity. A reconciliation operation SHALL carry or be equivalent to the common PDU context identity, its own refresh/reconciliation operation identity, expected reconciliation worker identity, and originating mutation operation identity. It MAY also include mutation kind and assigned credential index when needed for freshness, but SHALL NOT include credential values or session objects.

Reconciliation MAY start only after the originating mutation outcome is accepted as current by the mutation lane. A stale mutation SHALL NOT start reconciliation. Reconciliation SHALL NOT become mutation owner, SHALL NOT clear busy state on behalf of a different mutation, SHALL NOT update a new model/IP/common context, and SHALL NOT displace an authoritative refresh-lane operation of a newer common context.

#### Scenario: Pre-mutation refresh cannot overwrite later mutation state
- **GIVEN** refresh A was submitted for PDU context X
- **AND** mutation B starts later for the same context X before refresh A completes
- **WHEN** refresh A result arrives after mutation B started
- **THEN** refresh A is not accepted as authoritative post-mutation PDU state
- **AND** it does not overwrite PDU data produced by mutation-era or later accepted refresh/reconciliation authority

#### Scenario: Refresh after mutation start does not destroy mutation authority
- **GIVEN** mutation A is active
- **WHEN** refresh B is submitted after mutation A started
- **THEN** refresh B is judged through the refresh lane
- **AND** it does not automatically invalidate mutation A authority

#### Scenario: Reconciliation starts only from accepted mutation
- **GIVEN** mutation A emits a terminal outcome
- **WHEN** mutation A is accepted as current by the mutation lane and existing policy requires reconciliation
- **THEN** reconciliation R may be submitted in the refresh lane with its own operation identity and originating mutation A identity

#### Scenario: Stale mutation cannot start reconciliation
- **GIVEN** mutation A has become stale
- **WHEN** mutation A emits result, error, or finished
- **THEN** mutation A cannot start reconciliation for the current or newer PDU context

#### Scenario: Reconciliation cannot update new context
- **GIVEN** reconciliation R originated from mutation A in context X
- **WHEN** model, IP, credential-context revision, or PDU generation changes before R completes
- **THEN** R cannot update the new context
- **AND** R cannot unlock or clear mutation state for the new context

#### Scenario: Reconciliation cannot clear another mutation
- **GIVEN** reconciliation R originated from mutation A
- **AND** newer mutation B owns the mutation lane
- **WHEN** R completes
- **THEN** R does not clear, unlock, or relock mutation state owned by B

### Requirement: PDU controller stale callback acceptance
The PDU application controller SHALL accept a PDU callback only when its common context and the relevant lane identity match the controller's current lifecycle authority. Common currentness SHALL account for PDU generation, model, IP address, and non-secret credential-context revision. Refresh-lane currentness SHALL additionally account for refresh/reconciliation operation identity and expected refresh worker identity. Mutation-lane currentness SHALL additionally account for mutation operation identity, mutation kind, and expected mutation worker identity. Candidate index alone SHALL NOT be sufficient to prove currentness.

This acceptance rule SHALL apply independently to refresh, individual mutation, bulk mutation, and post-mutation reconciliation result, error, progress/status, and finished callbacks, including structured partial bulk outcomes. A stale callback SHALL NOT update `PDUScreen`, change current outlet/device data, save credential memory, advance credential fallback, start another credential attempt, start refresh or reconciliation for a newer context, change current mutation/busy state, unlock or relock controls owned by a newer operation, change global refresh/loading state for a newer request, or surface the old operation outcome as the result of the current context.

#### Scenario: Stale refresh callback is suppressed
- **WHEN** refresh A emits result, error, progress/status, or finished after PDU context B has become current or refresh B has superseded it in the refresh lane
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

### Requirement: PDU sequential bulk mid-operation currentness gate
Sequential bulk PDU execution SHALL re-check the controller-supplied thread-safe currentness/stale predicate or equivalent non-GUI token contract before every next state-changing outlet sub-operation. This check SHALL occur before the next outlet command is sent, not only when Qt callbacks are later accepted or suppressed.

If the PDU context, mutation-lane identity, credential-context revision, or other required currentness authority becomes stale after one outlet completes but before the next outlet command is sent, the next outlet command SHALL NOT be sent and no later outlet command SHALL be sent. Completed outlets SHALL NOT be replayed or rolled back. The terminal outcome SHALL preserve existing structured stale/partial semantics, SHALL NOT start credential fallback, SHALL NOT persist a successful credential, and SHALL NOT start reconciliation for a newer PDU context.

The worker/core execution layer SHALL obtain currentness authority from the PDUController/application boundary. It SHALL NOT read `device_combo`, `ip_entry`, `PDUScreen`, or other QWidget values to decide whether a bulk sequence remains current.

#### Scenario: Mid-bulk stale stop before next send
- **GIVEN** bulk operation A is current
- **AND** outlet 1 completed
- **WHEN** PDU context A becomes stale before outlet 2 state-changing send
- **THEN** outlet 2 is not sent
- **AND** no later outlet is sent
- **AND** completed outlet 1 is not replayed or rolled back
- **AND** terminal outcome preserves the existing stale/partial structured semantics
- **AND** no credential fallback is started
- **AND** no successful credential is persisted
- **AND** no reconciliation for a newer PDU context is started

#### Scenario: Bulk currentness check is non-GUI
- **WHEN** `core/workers/pdu.py` or `core.pdu` checks whether a bulk sequence may continue to the next outlet
- **THEN** it calls the controller-supplied thread-safe predicate or equivalent non-GUI token contract
- **AND** it does not inspect `device_combo`, `ip_entry`, `PDUScreen`, or other QWidget values
