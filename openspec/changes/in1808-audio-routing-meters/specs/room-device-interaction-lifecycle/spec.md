## ADDED Requirements

### Requirement: IN1808 Audio live work is a subcontext of the existing serialized Matrix owner

IN1808 Audio diagnostics SHALL run through the existing room Matrix application
owner and persistent-session authority. The capability SHALL extend the current
`matrix_room_live` / `MatrixController` ownership model rather than create a
second persistent Matrix handler/session, a second room interaction lane, or a
GUI-owned transport.

All Audio SIS I/O SHALL execute in background work and SHALL serialize with
existing Matrix operations through the current Matrix transport/session owner.
Qt GUI callbacks/timers MAY request work but SHALL NOT perform device I/O.

Handler/worker code receives one application-selected credential and SHALL NOT
iterate credential candidates.

#### Scenario: Audio mode reuses current Matrix owner

- **GIVEN** exact current IN1808 row has an eligible current Matrix context
- **WHEN** Audio live diagnostics start
- **THEN** work is submitted through the existing serialized Matrix owner
- **AND** no parallel persistent SIS session or credential-selection lane is created
- **AND** GUI-thread code performs no SIS I/O

### Requirement: IN1808 Audio live acquisition starts only for current Audio mode

The expanded row defaults to Video mode. IN1808 meter polling SHALL start only
after the current exact row enters Audio mode and composition revalidates room
identity, record identity, exact IN1808 capability, Matrix context and current
generation.

On Audio entry, the application SHALL acquire Audio names/routing metadata as
a diagnostic snapshot and SHALL then poll approved meter OIDs at a target
cadence of approximately one completed snapshot per second where transport
throughput permits.

Only one meter cycle may be outstanding. If a cycle takes longer than the
target cadence, another cycle SHALL NOT overlap or build an unbounded queue.

DSP routing SHALL not be re-read on every meter tick. A new routing snapshot
may be acquired on a new Audio-mode entry or an explicit accepted current
refresh.

#### Scenario: Video mode does not poll audio meters

- **GIVEN** exact current row is IN1808 but its expanded mode is Video
- **WHEN** room live processing is eligible
- **THEN** no IN1808 Audio meter poll cycle is started merely because the row is expanded

#### Scenario: Slow meter cycle does not overlap

- **GIVEN** one current IN1808 Audio meter cycle has not finished
- **WHEN** the nominal next poll time arrives
- **THEN** no second meter cycle is submitted
- **AND** the next cycle may start only after completion and currentness revalidation

### Requirement: IN1808 Audio cleanup is bound to exact room and record currentness

The current IN1808 Audio subcontext SHALL be cancelled/superseded when any of
the following occurs:

- the operator switches to Video;
- the IN1808 row collapses;
- another row becomes expanded;
- room/search/target context changes;
- the exact record is removed or replaced;
- credential-context revision invalidates the Matrix owner;
- Matrix context is invalidated;
- the application shuts down.

Cleanup SHALL restore only meter instrumentation states changed by this exact
subcontext when the same safe current session permits restoration. Cleanup
SHALL NOT reconnect solely to send restoration commands.

Stale work SHALL be rejected before handler acquisition/I/O when possible and
again before accepted publication. An old callback SHALL NOT update a
replacement row/context or restore old Audio mode/instrumentation authority.

#### Scenario: Row collapses during Audio polling

- **GIVEN** current IN1808 row is in Audio mode with live work active
- **WHEN** that row collapses
- **THEN** its Audio subcontext is superseded and no new meter cycle starts
- **AND** orderly same-session restoration is attempted only for meter states
  changed by that subcontext
- **AND** late callbacks cannot update the collapsed/replacement context

### Requirement: Audio read failure does not authorize credential or routing mutation

An IN1808 Audio read failure SHALL remain a read-only diagnostic failure. Error
text containing authentication-like words, status codes, or protocol fragments
SHALL NOT by itself authorize credential advancement.

Audio routing is read-only in this change. No Audio live failure, timeout,
unknown mix-point state, or meter failure SHALL authorize a route mutation,
gain/mute mutation, or blind replay of a possibly sent instrumentation command.

#### Scenario: Audio meter read fails after session use began

- **WHEN** a current Audio meter transaction fails after the session has been used
- **THEN** the failure is classified through structured Matrix failure semantics
- **AND** no audio-route mutation is generated
- **AND** no credential candidate advances solely from an error string
