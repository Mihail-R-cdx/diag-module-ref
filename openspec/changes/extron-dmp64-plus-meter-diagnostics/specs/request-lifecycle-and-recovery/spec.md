## MODIFIED Requirements

### Requirement: Background diagnostic execution
Network diagnostic refresh operations SHALL execute through QRunnable workers
submitted to `QThreadPool` and SHALL return progress, status, result, error,
connection, and completion information through worker signals. Workers SHALL
disconnect handlers in their cleanup paths when a handler was created. PDU
refresh paths, including Extron IPL T PCS4i Telnet status reads and HTTP
outlet-name enrichment, SHALL follow this background execution boundary.
Extron DMP 64 Plus meter diagnostics SHALL also follow a background execution
boundary; DMP SSH connection, SIS reads, stream processing, recovery commands,
and continuous polling SHALL NOT run in the Qt GUI thread.

#### Scenario: Worker succeeds
- **WHEN** a device worker connects, collects status, and parses a response
- **THEN** it emits a result for the GUI and releases its handler before emitting completion

#### Scenario: Worker fails
- **WHEN** a device worker encounters an authentication or connection exception
- **THEN** it emits a classified error and emits completion after its cleanup path

#### Scenario: PCS4i refresh stays off the GUI thread
- **WHEN** PCS4i refresh performs Telnet connect/read work or HTTP outlet-name enrichment
- **THEN** that network work runs in a background worker rather than the Qt GUI thread

#### Scenario: DMP meter polling stays off the GUI thread
- **WHEN** DMP meter diagnostics establish SSH, read SIS meter values, filter PTY echo, perform conditional recovery, or poll the next snapshot
- **THEN** that network work runs in a background execution path rather than the Qt GUI thread

### Requirement: Request-context isolation
The main window SHALL associate device results, errors, completions, and PDU
command outcomes with the active request context, including the selected model,
IP address, target screen, credential context, and request identifier. It SHALL
ignore callbacks from superseded requests and shall not let them change the
current screen, outlet table, command state, credential memory, or
refresh-button state. This includes bulk PDU sequence results, errors,
progress, partial terminal outcomes, completions, and DMP meter snapshot,
error, recovery, and polling-session callbacks.

For PDU operations, including PCS4i refresh, PCS4i ON/OFF commands, PCS4i bulk
ON/OFF, Aten refresh, Aten ON/OFF/REBOOT commands, and Aten bulk ON/OFF, the
application/composition layer SHALL own the current operation context
generation. For Extron DMP 64 Plus meter diagnostics, the
application/composition layer SHALL own the current DMP polling context
generation. Background workers SHALL NOT read Qt widgets, including
`device_combo`, `ip_entry`, `PDUScreen`, `AudioDSPScreen`, or other QWidget
properties, to decide whether an operation is current.

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

#### Scenario: Stale DMP snapshot arrives after context change
- **WHEN** an old DMP polling session emits a meter snapshot after model, IP, screen, or credential context changed
- **THEN** the old snapshot does not update `AudioDSPScreen`
- **AND** it does not update credential memory or restart the current DMP context

#### Scenario: DMP worker does not inspect widgets
- **WHEN** a DMP polling worker checks whether its context is still current
- **THEN** it uses an application-owned non-GUI validity mechanism
- **AND** it does not read `device_combo`, `ip_entry`, or `AudioDSPScreen`

### Requirement: Persistent resource release
The application SHALL disconnect the persistent Extron handler on window close
and SHALL stop timers, invalidate reusable codec interactive contexts, and
close their HTTP sessions, cookies, tokens, cookie jars, SSH channels, and
handlers when their screen is destroyed or the application closes. A codec
model, IP, or credential-context change SHALL close the superseded interactive
handler before it can be reused by the new context.

The application SHALL also stop/cancel the active Extron DMP 64 Plus polling
context on model change, IP change, leaving the DMP screen, explicit repeat
Refresh, and application close. The DMP worker/session owner SHALL close the
SSH channel, SSH client/session, and related transport resources on the
background execution lane that owns those resources. Cleanup SHALL be
idempotent or guaranteed to run exactly once, and terminal completion/error
callbacks SHALL be emitted only after cleanup according to the selected worker
contract.

#### Scenario: Application window closes after matrix use
- **WHEN** the window receives its close event with a persistent Extron handler
- **THEN** it disconnects that handler before delegating the close event

#### Scenario: Codec screen is destroyed with a cached session
- **WHEN** a codec screen with a cached interactive handler is destroyed
- **THEN** its polling and follow-up timers stop
- **AND** the handler and all model-specific session resources are closed on their owning execution lane

#### Scenario: IP changes with a cached session
- **WHEN** the selected codec IP changes before another interactive operation
- **THEN** the old-IP handler is invalidated and disconnected
- **AND** no callback from the old context updates the new screen

#### Scenario: Credentials change with a cached session
- **WHEN** newly resolved credentials no longer match the assigned cached credential context
- **THEN** the cached handler is invalidated before network work continues
- **AND** queued operations carrying the superseded credential context cannot invoke it

#### Scenario: DMP resources close on cancellation
- **WHEN** a DMP polling context terminates through normal stop, context cancellation, authentication failure, transport/session failure, application close, or unexpected exception
- **THEN** the DMP session owner closes its SSH channel, SSH client/session, and related transport resources on the owning background lane
- **AND** cleanup completes before terminal completion or error is emitted

#### Scenario: DMP cleanup is not GUI-thread network work
- **WHEN** a DMP polling context is stopped from the GUI
- **THEN** the GUI publishes cancellation to the worker
- **AND** the actual SSH/channel cleanup runs on the background execution lane that owns the network resources

## ADDED Requirements

### Requirement: Extron DMP 64 Plus continuous meter polling lifecycle
The application SHALL run DMP meter diagnostics through one long-lived
background polling context per active DMP model/IP/credential generation. The
polling context SHALL use one persistent SSH session and one sequential polling
flow for all ten physical meter OIDs. It SHALL NOT create overlapping polling
workers, ten SSH connections, ten parallel requests, or a new polling cycle
before the previous complete snapshot finishes.

The application/composition layer SHALL own the DMP polling context generation
and a thread-safe cancellation state/token. The worker SHALL receive immutable
context identity and a thread-safe cancellation handle. The worker SHALL NOT
read Qt widgets for freshness or cancellation.

The polling context SHALL be cancelled when the selected model changes, the IP
address changes, the operator leaves the DMP screen, an explicit repeat
Refresh starts a new DMP context, or the application closes. A queued stale DMP
operation SHALL be dropped before handler acquisition and before network I/O
where applicable. In-flight stale network work may finish or time out, but the
worker SHALL return to a cancellation checkpoint in bounded time and SHALL NOT
continue polling the old context. Its callbacks SHALL NOT update the new UI
context, credential memory, recovery budget, or polling state.

Cancellation/freshness SHALL be checked at least before handler/session
acquisition, before each new full polling cycle, before each new OID read,
before each conditional `*2` recovery command, before each recovery retry read,
and before snapshot/result emission. After cancellation, the worker SHALL NOT
start new network I/O at any later checkpoint.

SSH/SIS read operations SHALL use bounded timeouts. Cancellation SHALL NOT
depend on an infinite blocking `recv()`. The architecture does not require an
instant hard interruption of an already blocked socket/channel call, but the
worker must reach the next cancellation checkpoint within bounded time.

#### Scenario: One active DMP polling context
- **WHEN** DMP meter diagnostics are active for one model/IP context
- **THEN** exactly one DMP polling worker/session context owns the repeated meter snapshots for that context

#### Scenario: No overlapping snapshot cycle
- **WHEN** a DMP snapshot cycle is still reading physical OIDs
- **THEN** the application does not start another DMP snapshot cycle for the same context

#### Scenario: Complete snapshot emission
- **WHEN** the DMP polling worker finishes attempting all ten physical OIDs
- **THEN** it emits one normalized snapshot containing available channel samples and per-channel unavailable entries

#### Scenario: Partial channel failure does not destroy snapshot
- **WHEN** one DMP OID is unavailable or malformed but the SSH session remains usable
- **THEN** that channel is marked unavailable
- **AND** successful channels in the same snapshot remain usable

#### Scenario: Stop when leaving DMP context
- **WHEN** the operator changes model, changes IP, leaves the DMP screen, starts a new DMP context, or closes the application
- **THEN** the active DMP polling context receives cancellation
- **AND** old callbacks cannot update the new context

#### Scenario: Cancellation before handler acquisition
- **WHEN** a queued DMP polling worker is cancelled before handler/session acquisition
- **THEN** it exits without creating the handler/session
- **AND** it performs zero DMP network I/O

#### Scenario: Cancellation between OIDs
- **WHEN** cancellation is observed after OID `40000` completes and before OID `40001` starts
- **THEN** OID `40001` is not sent
- **AND** no old-context snapshot is applied to the GUI
- **AND** the worker proceeds to cleanup

#### Scenario: Cancellation before recovery command
- **WHEN** direct read returns `0*0`
- **AND** cancellation is observed before the conditional `*2` recovery checkpoint
- **THEN** the recovery command is not sent
- **AND** the worker proceeds to cleanup

#### Scenario: Cancellation during bounded wait
- **WHEN** cancellation is requested while a DMP SSH/SIS read is already waiting
- **THEN** the read may finish or time out within the bounded transaction timeout
- **AND** the worker checks cancellation before any next DMP network I/O

#### Scenario: No next cycle after cancellation
- **WHEN** cancellation is observed after a polling cycle completes
- **THEN** the worker does not start another full polling cycle for the stale context

#### Scenario: Repeat Refresh replaces current DMP context
- **WHEN** the operator explicitly refreshes the same DMP model/IP while polling is active
- **THEN** the application creates a new DMP polling generation/context
- **AND** it cancels the previous DMP context
- **AND** only the new context is authoritative for the Audio DSP UI

#### Scenario: Repeat Refresh old callbacks ignored
- **WHEN** the old DMP context from a repeat Refresh later emits result, error, or completion
- **THEN** those callbacks do not update the new UI context
- **AND** they do not change credential memory for the new context

### Requirement: Extron DMP 64 Plus polling error contract
DMP polling SHALL distinguish structured authentication failure,
transport/session failure, SIS protocol error, per-OID unavailable meter
sample, malformed meter payload, and stale/cancelled polling session. These
categories SHALL be machine-readable at the worker/application boundary. GUI
messages SHALL be derived from structured categories rather than credential
fallback, retry, or stale decisions being inferred from user-facing text.

#### Scenario: Authentication failure is structured
- **WHEN** DMP SSH session acquisition confirms that the assigned credential is rejected
- **THEN** the worker reports structured authentication failure
- **AND** the application may decide whether another credential candidate remains

#### Scenario: Per-OID unavailable is not transport failure
- **WHEN** one DMP meter read returns `0*0` after its recovery budget is exhausted
- **THEN** that channel is marked unavailable
- **AND** the polling session can continue if transport remains usable

#### Scenario: Stale session is non-failure for new context
- **WHEN** a DMP polling context is cancelled or stale
- **THEN** its terminal callback is ignored for the active context
- **AND** no credential index is changed because of stale completion
