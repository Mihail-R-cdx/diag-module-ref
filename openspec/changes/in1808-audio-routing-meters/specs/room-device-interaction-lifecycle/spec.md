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

On Audio entry, the GUI SHALL first commit/render the local Audio presentation
state synchronously. Controller acquisition, temporary-busy retry, metadata
reads and meter polling occur only after that visible transition. The
application SHALL then acquire Audio names/routing metadata as a diagnostic
snapshot and SHALL poll approved meter OIDs at a target cadence of approximately
one completed snapshot per second where transport throughput permits.

Only one meter cycle may be outstanding. If a cycle takes longer than the
target cadence, another cycle SHALL NOT overlap or build an unbounded queue.

DSP routing SHALL not be re-read on every meter tick. A new routing snapshot
may be acquired on a new Audio-mode entry or an explicit accepted current
refresh.

#### Scenario: First Audio click is visible before I/O

- **GIVEN** exact current IN1808 row is in Video mode
- **WHEN** the operator activates `Аудио`
- **THEN** the row enters/render Audio mode immediately with neutral placeholders
- **AND** the control immediately reads `Видео`
- **AND** controller busy state may delay background acquisition but cannot
  keep the old Video tile visible or require another click

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

The hardware evidence does not establish ownership scope for meter-update
state. Cleanup SHALL stop scheduling Audio reads and quiesce/cancel current
Audio work through the existing Matrix LIVE boundary, but SHALL NOT send
`V<OID>*0AU` under this change and SHALL NOT reconnect solely to modify
meter-update state.

Stale work SHALL be rejected before handler acquisition/I/O when possible and
again before accepted publication. An old callback SHALL NOT update a
replacement row/context or restore old Audio mode/instrumentation authority.

#### Scenario: Row collapses during Audio polling

- **GIVEN** current IN1808 row is in Audio mode with live work active
- **WHEN** that row collapses
- **THEN** its Audio subcontext is superseded and no new meter cycle starts
- **AND** cleanup sends no meter-disable command under the current unknown-scope policy
- **AND** late callbacks cannot update the collapsed/replacement context

### Requirement: IN1808 Audio LIVE obeys existing Matrix handoff and mutation gates

IN1808 Audio polling SHALL be owned by the existing
`RoomInteractionKind.LIVE` lifecycle. It SHALL NOT introduce another lifecycle
kind or bypass the common serialized room interaction lane.

When the operator switches Audio -> Video, presentation MAY change immediately,
but video route and Local Refresh network actions SHALL remain disabled/rejected
until the Audio subcontext is quiescent and the current LIVE owner satisfies
the applicable cleanup/release boundary.

A confirmed video route while Audio LIVE is active SHALL use the existing
Matrix rule: invalidate/retire Matrix LIVE through bounded cleanup before
mutation handler/session acquisition or send. If that cleanup boundary is not
reached, the route SHALL NOT be sent.

Local Refresh SHALL not overlap an Audio meter cycle and SHALL acquire no
handler/session until prior LIVE cleanup/release permits it. Once mutation
starts, Audio polling remains stopped; reconciliation remains exclusive and
Audio/other LIVE work cannot resume until reconciliation is terminal and its
cleanup boundary permits resumption.

#### Scenario: Video route waits for Audio LIVE retirement

- **GIVEN** current IN1808 Audio LIVE owns the exact row
- **AND** the operator switches to Video and confirms a video route
- **WHEN** LIVE cleanup has not reached the approved bounded release boundary
- **THEN** the route is not sent
- **AND** no mutation handler/session acquires overlapping Matrix resources

#### Scenario: Local Refresh does not overlap Audio polling

- **GIVEN** current IN1808 Audio LIVE has an in-flight or retiring meter cycle
- **WHEN** Local Refresh is requested
- **THEN** Local Refresh performs no device I/O until prior LIVE cleanup/release permits acquisition
- **AND** no Audio meter cycle overlaps the Local Refresh owner

#### Scenario: Reconciliation excludes Audio LIVE

- **GIVEN** an accepted Matrix video mutation has entered mandatory reconciliation
- **WHEN** the IN1808 row remains expanded
- **THEN** Audio polling does not start/resume during reconciliation
- **AND** eligible LIVE may resume only after reconciliation is terminal and cleanup permits it

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