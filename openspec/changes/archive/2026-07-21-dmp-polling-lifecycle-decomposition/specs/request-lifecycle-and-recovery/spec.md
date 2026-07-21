## ADDED Requirements

### Requirement: DMP polling application lifecycle controller

Extron DMP 64 Plus polling lifecycle SHALL be owned by a DMP-specific application/composition controller rather than directly by generic `VCSDiagnosticApp` result/error/progress/status/finished handlers, by `AudioDSPScreen`, by the DMP worker, or by a generic multi-device manager.

The controller SHALL own DMP polling generation, active immutable non-secret polling context, cancellation publication, expected worker identity, DMP-specific worker signal binding, callback acceptance, structured authentication-only fallback coordination through application-owned credential policy callbacks, pending-retry/retiring-attempt handoff authority, first-success credential persistence gating, and lifecycle invalidation/shutdown.

All DMP network I/O, SSH/SIS session ownership, blocking transport cleanup, model discovery, meter reads, recovery commands, and poll timing SHALL remain on the existing background worker/handler execution boundary. Moving blocking DMP network work into an ordinary controller method on the Qt GUI thread SHALL NOT satisfy this requirement.

The controller SHALL remain DMP-specific and SHALL NOT become a generic Matrix/PDU/codec/SIP request or operation manager.

#### Scenario: DMP refresh is submitted through the controller
- **WHEN** a valid DMP refresh request is ready for device execution
- **THEN** the DMP controller captures the immutable polling context and submits the DMP background worker
- **AND** `VCSDiagnosticApp` does not directly own the DMP worker lifecycle state machine

#### Scenario: Controller remains DMP-specific
- **WHEN** DMP lifecycle is extracted from `VCSDiagnosticApp`
- **THEN** the controller owns only DMP polling lifecycle responsibilities
- **AND** it does not become a generic lifecycle manager for Matrix, PDU, codec, SIP, or unrelated devices

#### Scenario: DMP cleanup remains background work
- **WHEN** the application invalidates or shuts down an active DMP polling context
- **THEN** the controller publishes cancellation and supersedes callback authority without blocking for SSH cleanup
- **AND** the worker/session owner performs blocking disconnect and cleanup on its background execution lane

### Requirement: DMP polling context and callback authority

Each DMP polling attempt SHALL have immutable non-secret context identity sufficient to determine callback authority. The identity SHALL include or be equivalent to DMP generation, selected model, IP address, generic request identifier, assigned candidate index, non-secret credential-context revision, and attempt/operation identity when needed. Expected worker identity SHALL also be part of controller acceptance authority.

Credential values, credential dictionaries, profile secrets, cancellation tokens, worker objects, handlers, SSH clients/channels, sessions, transports, cookies, Session IDs, CSRF tokens, or other secret/session material SHALL NOT be exposed in public DMP context or public controller signals.

Candidate index alone SHALL NOT prove credential-context currentness. A credential configuration change SHALL invalidate the active DMP polling context even when model, IP, and numeric candidate index are unchanged.

The controller SHALL invalidate and supersede the active DMP context on model change, IP change, leaving or superseding the DMP diagnostic context, DMP credential-context change, explicit repeat Refresh, and application shutdown.

`result`, `error`, `progress`, `status`, `terminal_log`, and `finished` callbacks SHALL be accepted only when their immutable DMP context and expected worker identity match current controller authority, except for the narrowly defined retiring-attempt `finished` authority required for cleanup-complete credential retry handoff. DMP `terminal_log` SHALL pass through the controller freshness boundary and SHALL NOT be wired directly from the worker to terminal rendering without the same context and expected-worker check.

Stale callbacks SHALL NOT update `AudioDSPScreen`, append terminal output, alter current request/UI state, save credential memory, advance fallback, start another DMP attempt, alter refresh controls, or affect a newer DMP context.

#### Scenario: Credential configuration change invalidates active DMP polling
- **GIVEN** a DMP polling session is current for model, IP, and candidate index N
- **WHEN** DMP credential configuration changes while the numeric candidate index remains N
- **THEN** the old DMP context is superseded and cancellation is published
- **AND** callbacks from the old polling session are stale

#### Scenario: Stale DMP snapshot cannot update the new context
- **GIVEN** DMP context A has been superseded by context B
- **WHEN** the worker from context A emits a meter snapshot
- **THEN** the snapshot does not update `AudioDSPScreen` or global request state
- **AND** it does not update credential memory or start credential fallback

#### Scenario: Stale DMP error cannot start fallback
- **GIVEN** an old DMP attempt has been superseded
- **WHEN** that attempt later emits an authentication error
- **THEN** no next credential candidate is started for the current context

#### Scenario: Stale DMP terminal log cannot update the new context
- **GIVEN** DMP context A has been superseded by context B
- **WHEN** the worker from context A emits `terminal_log`
- **THEN** the old terminal text is ignored
- **AND** it is not appended to the current DMP terminal UI

#### Scenario: Stale DMP completion cannot alter newer refresh state
- **GIVEN** a newer DMP request is current
- **WHEN** an older canceled DMP worker emits an ordinary stale `finished`
- **THEN** the old completion does not re-enable, disable, or otherwise change controls owned by the newer request

#### Scenario: Repeat Refresh replaces the polling context
- **GIVEN** a DMP polling context is active
- **WHEN** the operator explicitly requests a new DMP refresh
- **THEN** the old context is superseded and canceled
- **AND** the new attempt uses a fresh cancellation token, worker, and SSH/SIS session

### Requirement: DMP polling credential attempt lifecycle

The DMP controller MAY coordinate credential attempts only through application-owned credential policy callbacks. The application/composition credential boundary SHALL remain the owner of candidate resolution, saved successful candidate memory, and monotonic no-wrap candidate advancement policy.

Each DMP worker SHALL receive exactly one assigned credential candidate for one SSH/SIS session attempt. The worker and handler SHALL NOT iterate credential candidates or persist a successful candidate index.

Credential fallback SHALL occur only after a current structured confirmed `authentication_error` and only when another candidate remains in the current no-wrap suffix. Timeout, disconnect, SIS protocol error, unsupported model, malformed data, cancellation, unavailable samples, or other non-authentication failures SHALL NOT authorize fallback. String heuristics such as matching `auth`, `401`, or `403` SHALL NOT authorize fallback.

The current DMP worker signal ordering SHALL be preserved: a failed attempt may emit `error` before its `finally` cleanup, and it emits `finished` only after handler/session cleanup completes. Therefore a structured authentication error MAY cause application-owned policy to select the next candidate as a pending retry, but the controller SHALL NOT construct, submit, connect, or start the next DMP worker from that `error` callback.

The pending retry SHALL be bound to the exact failed attempt/context and expected worker. The failed worker SHALL remain a retiring attempt until its matching `finished` callback confirms cleanup completion. That retiring-attempt `finished` callback SHALL have authority only to release the already-planned retry. It SHALL NOT act as ordinary request completion, SHALL NOT alter refresh controls or current UI state, SHALL NOT persist credential success, and SHALL NOT independently select or advance another credential candidate.

Only after the matching retiring worker emits cleanup-complete `finished` MAY the controller create a fresh DMP attempt context, fresh cancellation token, fresh worker, and fresh SSH/SIS session for the already-selected next candidate. Consecutive DMP credential attempts SHALL NOT have overlapping polling workers or SSH/SIS sessions.

If model, IP, credential-context revision, generic request authority, DMP lifecycle generation, or application lifecycle is superseded before the retiring worker emits `finished`, the pending retry SHALL be discarded. A stale or non-matching retiring `finished` callback SHALL NOT launch a retry.

#### Scenario: Structured authentication failure schedules but does not immediately start retry
- **WHEN** the current DMP worker reports a structured confirmed authentication failure
- **AND** another unattempted candidate remains
- **THEN** application-owned policy advances to exactly the next candidate without wrap-around and records it as a pending retry for the failed attempt
- **AND** the next DMP worker is not started from the `error` callback

#### Scenario: Cleanup-complete finished releases the pending retry
- **GIVEN** candidate N failed with a structured confirmed authentication error
- **AND** candidate N+1 was recorded as the pending retry for that exact retiring worker/context
- **WHEN** candidate N's matching worker emits `finished` after cleanup
- **THEN** the controller may create and submit a fresh attempt for candidate N+1
- **AND** the failed worker/session is no longer active when the new attempt starts

#### Scenario: Retiring finished has narrow authority only
- **GIVEN** a failed DMP attempt is retiring with one pending retry
- **WHEN** its matching cleanup-complete `finished` is accepted
- **THEN** that callback may only release the already-planned retry
- **AND** it does not perform ordinary completion UI, credential persistence, refresh-control changes, or further candidate selection

#### Scenario: Stale retiring finished cannot launch retry
- **GIVEN** a DMP attempt has a pending retry
- **AND** its model, IP, credential context, request authority, generation, or application lifecycle is superseded before cleanup finishes
- **WHEN** the old retiring worker later emits `finished`
- **THEN** the pending retry is discarded or remains invalid
- **AND** no new DMP worker is started from that stale callback

#### Scenario: Non-authentication failure stops the DMP credential chain
- **WHEN** the current DMP attempt fails with timeout, transport/session failure, SIS protocol error, unsupported model, malformed data, or another non-authentication outcome
- **THEN** no later credential candidate is started

#### Scenario: Exhausted candidate suffix ends once
- **WHEN** the saved starting candidate and every later candidate fail authentication
- **THEN** no earlier candidate is retried
- **AND** one terminal authentication outcome is surfaced for the current DMP request

### Requirement: DMP first-complete-snapshot success gate

A DMP credential candidate SHALL be eligible for successful-index persistence only after the first accepted complete ten-OID meter snapshot from the current non-stale polling attempt and only when the assigned credential was actually used according to the existing DMP worker result contract.

SSH login, model discovery, one OID, a partial cycle, a stale snapshot, timeout, cancellation, terminal failure, or any later continuous snapshot after the first accepted complete snapshot SHALL NOT independently persist DMP credential success.

The DMP controller SHALL ensure the generic shell result path does not independently persist the same DMP candidate after the controller has handled the DMP-specific success gate.

#### Scenario: First accepted complete snapshot stores success once
- **WHEN** the current DMP polling attempt emits its first accepted complete ten-OID snapshot using the assigned credential
- **THEN** the application may store that candidate as successful for the exact DMP model/IP context
- **AND** the same polling session does not store it again from later continuous snapshots

#### Scenario: Stale first complete snapshot does not store success
- **GIVEN** a DMP attempt has become stale before its first complete snapshot is accepted
- **WHEN** that old worker emits a complete snapshot
- **THEN** no successful credential index is stored from that snapshot

#### Scenario: Partial or failed acquisition does not store success
- **WHEN** DMP acquisition reaches only login, model discovery, one or more individual OIDs, a partial cycle, timeout, cancellation, or terminal failure
- **THEN** the assigned candidate is not stored as successful
