# request-lifecycle-and-recovery Specification

## Purpose
TBD - created by archiving change bootstrap-openspec-baseline. Update Purpose after archive.
## Requirements
### Requirement: Background diagnostic execution
Network diagnostic refresh operations SHALL execute through QRunnable workers
submitted to `QThreadPool` and SHALL return progress, status, result, error,
connection, and completion information through worker signals. Workers SHALL
disconnect handlers in their cleanup paths when a handler was created. PDU
refresh paths, including Extron IPL T PCS4i Telnet status reads and HTTP
outlet-name enrichment, SHALL follow this background execution boundary.
Extron DMP 64 Plus meter diagnostics SHALL also follow a background execution
boundary; DMP SSH connection, SIS reads, stream processing, recovery commands,
and continuous polling SHALL NOT run in the Qt GUI thread. Worker module
decomposition SHALL preserve these background execution, cleanup, and signal
lifecycle contracts without moving network I/O into the Qt GUI thread.

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

#### Scenario: Decomposed worker keeps background boundary
- **WHEN** a worker implementation moves from `core/worker.py` into a focused `core/workers/` module
- **THEN** the worker still executes device network I/O through the existing background worker boundary
- **AND** GUI consumers receive the same completion lifecycle as before

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

### Requirement: Credential retry and connection-profile memory
The application SHALL try configured credentials in order for a supported
device refresh, interactive session, or eligible PDU operation when a confirmed
authentication failure is classified and additional credentials remain. It
SHALL begin at the valid successful credential index for the exact device/IP
context, advance a request-scoped cursor monotonically without wrap-around,
and retain the successful credential index and connection profile for that
context only after a final successful operation. A supported retained
connection profile SHALL be the first transport candidate for later refresh
and interactive connections.

For a PDU bulk sequence attempt, the application/composition layer SHALL assign
one credential to the sequence. The worker and handler SHALL NOT select later
credential candidates. Credential fallback for bulk SHALL be allowed only when
the failure classification is a structured confirmed `AuthenticationError` and
structured execution state proves that no state-changing outlet send was
attempted or could have been delivered. After mutation begins or may have
begun, the bulk sequence SHALL NOT restart with another credential, repeat
completed outlets, or start again from the beginning.

Credential fallback authority SHALL NOT be inferred from `successful_outlets`
being empty, the stopping outlet, user-facing error text, exception message
text, HTTP status substrings, or the absence of success. A first outlet command
that was invoked, may have been delivered to the transport, or has an ambiguous
outcome SHALL be treated as mutation started for credential-fallback purposes.
Successful credential index for bulk SHALL be saved only after full successful
bulk sequence completion. Partial completion, terminal failure, and stale
termination SHALL NOT save a new successful credential index. PCS4i unused
credential behavior for passwordless operation remains unchanged: an assigned
but unused credential is not saved even after full bulk success.

#### Scenario: Retry after authentication failure
- **WHEN** a current refresh worker reports a confirmed authentication failure and another credential exists
- **THEN** the application advances its request-scoped credential cursor and starts the applicable refresh path again

#### Scenario: Interactive authentication failure advances the chain
- **WHEN** an interactive handler cannot establish a new session because the assigned credential is rejected
- **AND** another credential remains in the current suffix
- **THEN** the application-owned interactive controller tries exactly that next credential
- **AND** the handler does not select the credential

#### Scenario: Successful profile retained
- **WHEN** a refresh or interactive operation completes successfully with a credential index and connection profile
- **THEN** subsequent actions for that device/IP use that retained credential index and supported profile first

#### Scenario: Failed next candidate is not cached as successful
- **WHEN** authentication fallback advances a request cursor and the next candidate also fails
- **THEN** the application does not commit that failed candidate as the successful index

#### Scenario: Saved profile is unsupported at runtime
- **WHEN** a retained profile is not in the selected model's current supported profile list
- **THEN** the application skips it and uses the model's supported default order

#### Scenario: One credential per bulk sequence attempt
- **WHEN** a bulk PDU sequence attempt starts
- **THEN** it uses one assigned credential for the whole sequence attempt
- **AND** the worker and handler do not iterate credential candidates

#### Scenario: Authentication failure before any send
- **WHEN** handler/session establishment returns structured `AuthenticationError`
- **AND** structured execution state confirms zero state-changing send attempts
- **THEN** application may advance to the next credential

#### Scenario: Authentication-looking failure after possible send
- **WHEN** a failure classified during or after an outlet command occurs
- **AND** structured state says a state-changing send was attempted or may have been delivered
- **THEN** no credential fallback occurs

#### Scenario: Empty success list is not retry authority
- **WHEN** no outlet completed successfully
- **AND** the first outlet command may have been sent
- **THEN** the application does not infer that credential fallback is safe

#### Scenario: No credential restart after mutation
- **WHEN** at least one state-changing outlet command has been sent or may have been sent
- **AND** a later authentication, connection, protocol, or indeterminate failure occurs
- **THEN** the application does not restart the bulk sequence with another credential
- **AND** completed outlet sub-operations are not repeated

#### Scenario: Bulk success stores credential only on full success
- **WHEN** a bulk PDU sequence completes fully and successfully with a used credential index
- **THEN** the application may save that credential index according to the existing successful credential policy

#### Scenario: Partial or stale bulk does not store successful credential
- **WHEN** a bulk PDU sequence completes partially, fails terminally, or terminates stale
- **THEN** the application does not store a new successful credential index from that sequence

#### Scenario: PCS4i passwordless bulk does not cache unused credential
- **WHEN** PCS4i bulk execution was assigned a credential but the device operated passwordless and the credential was not used
- **THEN** that credential index is not stored as successful

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

### Requirement: Serialized background interactive execution
Interactive codec network work SHALL execute outside the Qt GUI thread through
one serialized application-owned execution path per codec screen. Each result,
error, and completion SHALL carry an operation identifier and non-secret
model/IP context generation, and the GUI SHALL ignore callbacks that do not
match the current generation. Only one live-audio poll SHALL be pending at a
time.

#### Scenario: Interactive command is slow
- **WHEN** a codec command blocks on network I/O
- **THEN** the Qt event loop remains responsive while the operation runs in the serialized background path

#### Scenario: Poll timer fires while a poll is pending
- **WHEN** live-audio polling fires before the previous poll completes
- **THEN** the application does not queue another copy of that poll

#### Scenario: Old operation completes after context change
- **WHEN** an operation from an earlier model or IP generation completes
- **THEN** its callback does not change values, buttons, dialogs, or connection state for the current screen

#### Scenario: Queued stale command is dropped before network I/O
- **WHEN** an operation is queued with one context generation
- **AND** the model, IP, or credential context changes before that operation begins execution
- **THEN** the controller rechecks the operation at the head of the queue and drops it
- **AND** it does not acquire or invoke a handler, open a transport, or send a device command

#### Scenario: In-flight old operation cannot authorize later stale work
- **WHEN** network I/O from an old generation was already in flight when the context changed
- **THEN** its result cannot update the current context
- **AND** every later queued operation from that old generation is dropped before network I/O

### Requirement: Structured codec authentication classification
Codec refresh and interactive paths SHALL authorize credential advancement only
from a structured failure classification derived from a confirmed
`AuthenticationError` while establishing a new session. They SHALL NOT use
generic message substring matching, arbitrary numeric-code matching, empty or
malformed response shapes, or the legacy `is_authentication_error()` heuristic
as retry authority. An HTTP 401/403 SHALL be classified according to operation
phase: new-session login as authentication failure and an established-session
operation as session invalidation. User-facing text SHALL remain separate from
the machine-readable retry decision.

#### Scenario: Transport error text contains 401
- **WHEN** a codec refresh or interactive transport failure contains the text `401` but is not classified as `AuthenticationError`
- **THEN** the application does not advance to another credential

#### Scenario: Established session returns 401 or 403
- **WHEN** an established codec session operation receives HTTP 401 or 403
- **THEN** the failure is classified as session invalidation
- **AND** same-credential bounded recovery occurs before any credential advancement is considered

#### Scenario: Confirmed new login rejects credentials
- **WHEN** a new codec login produces a confirmed `AuthenticationError`
- **AND** another unattempted credential remains
- **THEN** the application may advance the request-scoped credential plan monotonically

#### Scenario: Unstructured response does not advance credentials
- **WHEN** a codec path receives generic `success: 0`, an empty mapping, malformed data, or arbitrary text containing `auth`
- **AND** no typed new-login authentication failure was produced
- **THEN** the application does not advance to another credential

### Requirement: Cached interactive session validity and invalidation
A cached interactive handler SHALL be reusable only when model, IP, assigned
credential identity, selected transport, and local connected state match the
current interactive context. Matching cache identity SHALL NOT by itself prove
remote liveness. An established-session rejection or invalid required session
artifact SHALL be classified as session invalidation, SHALL invalidate the
handler, and SHALL remain distinct from initial authentication failure and
normal command rejection.

#### Scenario: Cached handler is locally disconnected
- **WHEN** a matching cached handler reports that it is not connected
- **THEN** the application invalidates it instead of returning it for use

#### Scenario: Cached cookies or token are rejected
- **WHEN** an established operation receives a confirmed invalid-session response
- **THEN** the handler is invalidated before recovery
- **AND** the response is not immediately treated as failure of the configured credential

#### Scenario: Device returns a normal negative command result
- **WHEN** a valid session receives a well-formed device rejection for one command
- **THEN** the application reports a command failure without advancing credentials or assuming the session expired

### Requirement: Bounded interactive session recovery
Each submitted interactive operation SHALL have at most one reconnect cycle.
Recovery SHALL first use the same assigned credential, SHALL apply the supported
saved-first transport order, and SHALL advance to a later credential only when
the new login produces a confirmed authentication failure. Transport,
connection, session, protocol, and command failures SHALL remain separately
classified. Recovery and any operation replay SHALL use separate budgets and
SHALL NOT recurse.

#### Scenario: First transport raises an exception
- **WHEN** the first transport attempt raises a non-authentication exception
- **AND** another supported transport remains
- **THEN** connection attempts continue with the same credential on the next transport

#### Scenario: Established session expires
- **WHEN** an operation detects confirmed invalidation of an established session
- **THEN** the application invalidates the cached handler and performs at most one reconnect cycle

#### Scenario: Reconnect fails again
- **WHEN** the one permitted reconnect cycle cannot restore a usable session
- **THEN** the operation emits one terminal redacted failure and starts no further reconnect

#### Scenario: Reconnect login rejects the same credential
- **WHEN** recovery login returns a confirmed authentication failure for the assigned credential
- **AND** a later unattempted candidate remains
- **THEN** the application attempt plan may advance once to that next candidate without wrapping

### Requirement: Operation-specific replay and reconciliation
The application SHALL distinguish connection recovery from replay of the
original operation. A read-only operation MAY be replayed once after successful
reconnect. A state-changing operation SHALL NOT be blindly replayed after an
unknown delivery outcome; it SHALL first perform an authoritative readback and
then confirm the target, issue at most one absolute desired-state command when
the observed state permits it, or return an indeterminate/conflict outcome.
Relative volume and toggle intent SHALL never be sent twice as a relative
operation. PCS4i ON/OFF commands and Aten ON/OFF/REBOOT commands SHALL follow
the bounded PDU safety rules. PCS4i has no REBOOT replay or recovery behavior
because PCS4i REBOOT is unsupported.

#### Scenario: Read-only operation loses its session
- **WHEN** live polling, status, sleep, volume, presentation, Huawei call-log reading, or PDU outlet status reading fails because the session is invalid
- **AND** reconnect succeeds
- **THEN** the application replays the read exactly once

#### Scenario: Absolute target already took effect
- **WHEN** a state-changing operation loses its response and post-reconnect readback equals the requested target
- **THEN** the application reports the target as achieved without sending the command again

#### Scenario: Absolute target is authoritatively absent
- **WHEN** post-reconnect readback authoritatively shows the known pre-command state
- **THEN** the application may send the absolute target once
- **AND** it performs no further reconnect or replay for that operation

#### Scenario: Relative volume outcome is ambiguous
- **WHEN** a volume increment or decrement loses its response
- **AND** readback shows neither the recorded original value nor the computed absolute target
- **THEN** the application refreshes the displayed value and does not apply the relative change again

#### Scenario: State cannot be read after reconnect
- **WHEN** an operation-changing command has an unknown first outcome and authoritative readback is unavailable
- **THEN** the application reports an indeterminate outcome and does not replay the command

#### Scenario: PDU reconciliation is bounded
- **WHEN** one user PDU state-changing operation has ambiguous initial delivery
- **THEN** the application performs at most one reconciliation cycle
- **AND** that cycle includes at most one recovery/reconnect sequence when needed for device-specific authoritative outlet-state readback
- **AND** that cycle includes at most one reconciliation decision readback
- **AND** one terminal confirmation readback remains allowed after the only controlled resend
- **AND** recovery or reconciliation does not recurse

#### Scenario: PCS4i ON/OFF recovery uses PC readback
- **WHEN** a PCS4i ON or OFF command has ambiguous delivery
- **THEN** reconciliation uses PCS4i Telnet `PC` readback as authoritative outlet-state evidence
- **AND** unavailable, unknown, or conflicting readback returns indeterminate without blind resend

### Requirement: Background PDU control execution
PDU outlet control operations for Extron IPL T PCS4i and Aten PE8208AV SHALL
execute outside the Qt GUI thread through a shared application-owned background
PDU command execution boundary. The shared boundary SHALL own operation
dispatch, background execution, lifecycle cleanup, stale-operation protection,
model-capability validation, structured command outcomes, and sequential bulk
PDU orchestration. Device-specific handlers SHALL remain separate, and the
boundary SHALL NOT merge Aten wire protocol, PCS4i Telnet protocol, or PCS4i
HTTP protocol.

A bulk PDU ON/OFF operation SHALL execute as one serial background sequence,
not as multiple concurrent workers, not as a GUI loop over
`control_pdu_outlet(...)`, and not as repeated returns to GUI dispatch between
outlets. The sequence SHALL acquire and release handler or session resources
according to the chosen worker boundary and SHALL clean up on success, partial
completion, stale termination, or failure.

#### Scenario: PCS4i command is slow
- **WHEN** a PCS4i outlet ON or OFF command blocks on Telnet network I/O
- **THEN** the Qt event loop remains responsive while the command runs in the background

#### Scenario: Aten command path is migrated
- **WHEN** an operator confirms an Aten ON, OFF, or REBOOT command
- **THEN** Aten command dispatch runs through the background PDU command worker and retains existing handler behavior
- **AND** Aten network I/O does not run on the Qt GUI thread

#### Scenario: PDU command worker cleans up
- **WHEN** a PDU command succeeds, fails, reports unsupported, or reports an indeterminate result
- **THEN** the worker releases the handler/transport before emitting completion

#### Scenario: Bulk sequence is one background operation
- **WHEN** an operator confirms bulk ON or bulk OFF
- **THEN** the application submits one managed background bulk PDU operation
- **AND** it does not submit independent concurrent workers for every outlet
- **AND** it does not emulate several independent user clicks

#### Scenario: Bulk command is slow
- **WHEN** a bulk sequence performs PDU network I/O and waits between outlets
- **THEN** the Qt event loop remains responsive while the sequence runs in the background

#### Scenario: Bulk worker cleans up
- **WHEN** a bulk sequence succeeds, fails, becomes stale, or completes partially
- **THEN** the worker releases the handler/transport resources owned by that sequence boundary
- **AND** terminal callbacks carry only redacted non-secret outcome data

### Requirement: PDU queued operation staleness and capability validation
PDU refresh, command, and bulk workers SHALL carry an immutable operation
descriptor with operation id, generation, model, IP address, non-secret
credential context, operation type, outlet number when applicable, desired
command/target when applicable, and immutable ordered outlet identity sequence
when applicable. This applies to PCS4i refresh, PCS4i ON/OFF commands, PCS4i
bulk ON/OFF, Aten refresh, Aten ON/OFF/REBOOT commands, and Aten bulk ON/OFF.
The application/composition layer SHALL own the current PDU generation and
increment or replace it when relevant PDU context changes.

Application dispatch SHALL validate that the selected model supports the
requested operation before handler acquisition. Bulk dispatch SHALL validate
that every captured outlet identity is present, well-formed, supported for the
selected model, and unique before state-changing network I/O. Duplicate outlet
identities SHALL NOT be silently removed. A queued operation SHALL recheck the
captured descriptor against the current application-owned context immediately
before handler acquisition. When handler construction/preparation and first
network I/O are separate phases, it SHALL also recheck immediately before first
network I/O. A bulk sequence SHALL also recheck currentness before starting
each next outlet sub-operation. A stale queued operation SHALL be dropped
without creating a handler, opening Telnet, HTTP, or Aten transport, or sending
a command. A bulk sequence that becomes stale between outlets SHALL stop before
the next outlet command and SHALL NOT wait for a next outlet that will not be
started.

#### Scenario: Stale PCS4i refresh is dropped
- **WHEN** a PCS4i refresh is queued and the selected device or IP changes before it starts network work
- **THEN** the operation is dropped before Telnet connect or HTTP request

#### Scenario: Stale Aten refresh is dropped
- **WHEN** an Aten refresh is queued and the selected device, IP, or credential context changes before it starts network work
- **THEN** the operation is dropped before handler acquisition
- **AND** it performs zero network I/O

#### Scenario: Stale PCS4i command is dropped
- **WHEN** a PCS4i outlet command is queued and the model, IP, or credential context changes before execution
- **THEN** the worker does not acquire a handler or send the command

#### Scenario: Stale Aten command is dropped
- **WHEN** an Aten outlet command is queued and the model, IP, or credential context changes before execution
- **THEN** the worker does not acquire a handler, open transport, or send the command

#### Scenario: Stale operation is dropped before first network I/O
- **WHEN** a PDU worker acquires or prepares a handler and the context becomes stale before the first network I/O
- **THEN** the worker performs the final validity check and exits without opening transport or sending device bytes

#### Scenario: In-flight Aten refresh cannot update a new context
- **WHEN** Aten refresh network I/O was already in flight when the PDU context changed
- **THEN** its result, error, or completion cannot update the current screen, outlet table, credential memory, or later queued PDU work

#### Scenario: In-flight PDU work cannot update a new context
- **WHEN** PDU network I/O was already in flight when the context changed
- **THEN** its result cannot update the current screen or authorize later stale queued PDU work

#### Scenario: PCS4i REBOOT rejected before network I/O
- **GIVEN** a PCS4i REBOOT operation is submitted programmatically
- **WHEN** application dispatch validates model capability
- **THEN** the operation is rejected as unsupported
- **AND** rejection happens before handler acquisition
- **AND** rejection happens before any Telnet or HTTP network I/O

#### Scenario: Stale bulk before start is dropped
- **WHEN** a bulk PDU sequence is queued and the selected device, IP, or credential context changes before execution starts
- **THEN** the operation is dropped before handler acquisition
- **AND** zero outlet commands are sent

#### Scenario: Stale bulk between outlet sub-operations
- **WHEN** context changes after one outlet sub-operation completes and before the next begins
- **THEN** the next outlet command is not sent
- **AND** the sequence terminates as stale or partial according to the terminal result contract

#### Scenario: In-flight bulk context change
- **WHEN** context changes while one outlet sub-operation is in flight
- **THEN** the in-flight sub-operation may finish
- **AND** its stale callback does not update the new GUI context
- **AND** the sequence does not continue to another outlet

#### Scenario: Duplicate outlet number
- **GIVEN** current outlet records contain a duplicate outlet identity
- **WHEN** bulk dispatch validates the sequence
- **THEN** the bulk operation is rejected before state-changing network I/O

#### Scenario: Malformed outlet number
- **GIVEN** one outlet record has missing or invalid outlet identity
- **WHEN** bulk dispatch validates the sequence
- **THEN** the operation is rejected before state-changing network I/O

#### Scenario: Immutable capture
- **WHEN** a bulk sequence is submitted
- **THEN** later mutation of GUI outlet records does not change the captured execution sequence

#### Scenario: Bulk capability rejected before network I/O
- **GIVEN** a PDU model does not support the requested bulk target
- **WHEN** application dispatch validates the bulk operation
- **THEN** the operation is rejected as unsupported before handler acquisition
- **AND** no network I/O occurs

### Requirement: PDU state-changing command safety
The application SHALL treat supported PDU state-changing operations as unsafe
to blindly repeat after an ambiguous transport outcome. For PCS4i, supported
state-changing operations are ON and OFF only. For Aten, supported
state-changing operations are ON, OFF, and REBOOT. ON/OFF MAY use
device-specific authoritative outlet-state readback to reconcile an ambiguous
outcome within one bounded reconciliation cycle. Aten REBOOT SHALL not be
automatically replayed when first delivery is uncertain.

For one user PDU state-changing operation, the application SHALL send at most
one initial command. Acknowledged success SHALL complete successfully only after
any required device-specific final-state confirmation. Authoritative device
rejection SHALL complete failure with no credential fallback and no command
replay. Ambiguous delivery SHALL allow at most one reconciliation cycle and no
recursive recovery/reconciliation. ON/OFF MAY perform at most one controlled
absolute resend only when device-specific readback authoritatively shows the
known pre-command state. The shared PDU command boundary SHALL call a
device-specific handler readback operation and SHALL NOT encode PCS4i Telnet or
Aten status API wire details.

A bulk PDU operation SHALL be treated as one orchestration sequence composed of
multiple independent outlet sub-operations. Each outlet sub-operation SHALL be
treated as one PDU state-changing operation for purposes of the existing
per-operation safety budget. The safety budget of one outlet SHALL NOT consume,
relax, or authorize the safety budget of another outlet. Completed outlet
sub-operations SHALL NOT be repeated because a later outlet fails. Completed
outlet sub-operations SHALL NOT be rolled back. Bulk PDU operations SHALL NOT
be transactional. A terminal failure, command rejection, indeterminate outcome,
connection/protocol failure, or terminal authentication failure for one outlet
SHALL stop the sequence and prevent commands to remaining outlets.

For PCS4i ON/OFF, the application SHALL attempt to obtain and preserve
authoritative `PRE_STATE` through `PC` before the first state-changing send and
SHALL define `TARGET` as ON for `turn_on` and OFF for `turn_off`. Obtaining
valid `PRE_STATE` is desirable for safe recovery, but failure to obtain it SHALL
NOT by itself block the initial absolute ON or OFF command. If the initial
command proceeds without known `PRE_STATE`, the operation SHALL NOT perform a
controlled resend. A readback obtained after the first state-changing send SHALL
NOT be retroactively treated as pre-command state. One user PCS4i ON/OFF
operation SHALL have these budgets: initial command send max 1, controlled
resend max 1, total state-changing sends max 2, reconciliation cycles max 1,
reconciliation decision readback max 1, terminal confirmation readback after
controlled resend max 1, and recursive recovery max 0.

The reconciliation decision readback and terminal confirmation readback SHALL
be separate. The decision readback after ambiguous initial delivery decides
whether `TARGET` is already reached, whether the only controlled resend is
allowed because readback equals a known saved `PRE_STATE`, or whether the
outcome is indeterminate. If the controlled resend is used, exactly one
terminal confirmation `PC` readback SHALL run after it and SHALL NOT count as a
second reconciliation cycle. A valid non-target readback SHALL NOT be treated
as `PRE_STATE` unless it exactly matches authoritative `PRE_STATE` captured
before the first state-changing send.

PCS4i terminal outcomes SHALL be:

- structured device rejection -> `FAILURE`;
- initial acknowledgement followed by `PC == TARGET` -> `SUCCESS`;
- initial acknowledgement followed by known saved `PRE_STATE` and
  `PC == PRE_STATE` -> one controlled absolute resend is allowed, and terminal
  success still requires final `PC == TARGET`;
- initial acknowledgement with unknown `PRE_STATE` followed by valid
  `PC != TARGET` -> `INDETERMINATE` and no controlled resend;
- initial acknowledgement followed by unavailable, unknown, or conflicting
  `PC` -> `INDETERMINATE` with no resend;
- ambiguous initial delivery followed by reconciliation `PC == TARGET` ->
  `SUCCESS` with no resend;
- ambiguous initial delivery followed by reconciliation readback with known
  saved `PRE_STATE` and `PC == PRE_STATE` -> one controlled absolute resend is
  allowed;
- ambiguous initial delivery with unknown `PRE_STATE` followed by valid
  `PC != TARGET` -> `INDETERMINATE` and no controlled resend;
- ambiguous initial delivery followed by unavailable, unknown, or conflicting
  `PC` -> `INDETERMINATE` with no resend;
- after the controlled resend, terminal confirmation `PC == TARGET` ->
  `SUCCESS`;
- after the controlled resend, terminal confirmation `PC == PRE_STATE` ->
  `FAILURE`;
- after the controlled resend, terminal confirmation unavailable, unknown, or
  conflicting -> `INDETERMINATE`.

After the controlled-resend terminal confirmation, no further resend, reconnect,
or reconciliation SHALL occur. Acknowledgement of either the initial command or
controlled resend SHALL NOT by itself establish terminal success for PCS4i.

#### Scenario: ON target already applied
- **WHEN** a PDU ON command loses acknowledgement and device-specific authoritative readback shows the outlet is on
- **THEN** the operation reports success without sending ON again

#### Scenario: OFF target still absent
- **GIVEN** authoritative ON was captured as `PRE_STATE` before the initial OFF command
- **WHEN** a PDU OFF command loses acknowledgement and device-specific authoritative readback shows the outlet is still on
- **THEN** policy may send one controlled OFF command and performs no blind replay loop

#### Scenario: Controlled ON/OFF resend remains ambiguous
- **WHEN** the one controlled ON or OFF resend after readback has an ambiguous outcome
- **THEN** the operation reports indeterminate
- **AND** no additional command replay, recovery, or reconciliation loop runs

#### Scenario: ON/OFF state remains unknown
- **WHEN** a PDU ON or OFF command has ambiguous delivery and device-specific authoritative readback is unavailable, unknown, or conflicting
- **THEN** the operation reports indeterminate and does not resend the command

#### Scenario: PCS4i acknowledged ON/OFF uses final PC readback
- **WHEN** PCS4i ON or OFF command acknowledgement is received
- **THEN** final success is based on authoritative Telnet `PC` readback

#### Scenario: Acknowledged PCS4i command still equals PRE_STATE
- **GIVEN** PCS4i ON/OFF command acknowledgement was received
- **AND** authoritative `PRE_STATE` was captured before the initial command
- **WHEN** authoritative `PC` readback still equals saved `PRE_STATE`
- **THEN** acknowledgement alone does not mean success
- **AND** policy may perform the single controlled absolute resend
- **AND** terminal success requires final `PC == TARGET`

#### Scenario: Unknown PRE_STATE reaches target
- **GIVEN** valid `PRE_STATE` could not be obtained before initial PCS4i command
- **WHEN** initial command is sent
- **AND** authoritative post-command `PC == TARGET`
- **THEN** operation reports `SUCCESS`
- **AND** no resend occurs

#### Scenario: Unknown PRE_STATE returns non-target state
- **GIVEN** valid `PRE_STATE` could not be obtained before initial PCS4i command
- **WHEN** authoritative post-command `PC` returns a valid state different from `TARGET`
- **THEN** operation reports `INDETERMINATE`
- **AND** no controlled resend occurs

#### Scenario: Controlled resend requires preserved PRE_STATE
- **GIVEN** authoritative `PRE_STATE` was captured before initial command
- **WHEN** post-command authoritative `PC == PRE_STATE`
- **THEN** the single controlled resend may be performed

#### Scenario: Opposite state is not implicitly PRE_STATE
- **GIVEN** no authoritative `PRE_STATE` was captured before initial command
- **WHEN** `TARGET` is OFF and post-command `PC` is ON
- **THEN** ON must not automatically be treated as `PRE_STATE`
- **AND** no controlled resend is allowed

#### Scenario: Controlled resend confirmation
- **GIVEN** policy performed the only controlled resend for a PCS4i ON/OFF operation
- **WHEN** resend completes
- **THEN** application performs exactly one terminal authoritative `PC` confirmation readback
- **AND** `PC == TARGET` produces `SUCCESS`
- **AND** `PC == PRE_STATE` produces `FAILURE`
- **AND** unavailable, unknown, or conflicting `PC` produces `INDETERMINATE`
- **AND** no further resend, recovery, or reconciliation occurs

#### Scenario: PCS4i ambiguous initial delivery reaches target
- **GIVEN** PCS4i initial ON/OFF delivery is ambiguous
- **WHEN** the one reconciliation decision `PC` readback equals `TARGET`
- **THEN** the operation reports `SUCCESS`
- **AND** no resend occurs

#### Scenario: PCS4i ambiguous initial delivery remains at PRE_STATE
- **GIVEN** PCS4i initial ON/OFF delivery is ambiguous
- **WHEN** the one reconciliation decision `PC` readback equals `PRE_STATE`
- **THEN** policy may perform the single controlled absolute resend
- **AND** exactly one terminal confirmation `PC` readback follows the resend

#### Scenario: PCS4i reconciliation readback is unavailable
- **GIVEN** PCS4i initial ON/OFF delivery is ambiguous
- **WHEN** reconciliation `PC` readback is unavailable, unknown, or conflicting
- **THEN** the operation reports `INDETERMINATE`
- **AND** no resend occurs

#### Scenario: Aten ON/OFF uses existing authoritative status
- **WHEN** an Aten ON or OFF command has ambiguous delivery
- **THEN** reconciliation uses the existing Aten authoritative outlet-status handler path
- **AND** it does not introduce new Aten wire protocol semantics

#### Scenario: Aten REBOOT is not replayed
- **WHEN** an Aten REBOOT command has ambiguous delivery
- **THEN** automatic resend is zero
- **AND** the user operation sends REBOOT at most once

#### Scenario: PDU command rejection is final
- **WHEN** a supported PDU state-changing command receives an authoritative device rejection
- **THEN** the operation reports failure
- **AND** it does not advance credentials or replay the command

#### Scenario: Bulk outlet safety budget is per outlet
- **WHEN** a bulk ON or OFF sequence processes outlet N
- **THEN** outlet N uses the existing bounded PDU ON/OFF safety policy
- **AND** its send, readback, reconciliation, and confirmation budget does not consume, relax, or authorize the budget for outlet N+1

#### Scenario: Bulk fail-fast preserves completed outlets
- **WHEN** outlets 1 through N-1 complete successfully and outlet N fails terminally
- **THEN** outlets N+1 and later are not commanded
- **AND** outlets 1 through N-1 are not repeated or rolled back

#### Scenario: Bulk indeterminate outcome stops sequence
- **WHEN** one outlet sub-operation reports an indeterminate outcome
- **THEN** the bulk sequence stops
- **AND** no remaining outlet receives a command

#### Scenario: Bulk terminal result is secret-free
- **WHEN** bulk execution reports success, partial completion, stale termination, or failure
- **THEN** result and error payloads contain no credentials, cookies, session identifiers, CSRF tokens, or other secrets

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

Any DMP SIS transaction timeout SHALL terminate the current polling session as
a structured session/transport failure. The worker SHALL NOT start the next
OID request or next polling cycle on that session after timeout. It SHALL
abandon the current cycle, close the SSH channel/client/session through the
background cleanup path, and emit terminal error/completion only after cleanup.
A later DMP polling context may establish a fresh SSH/SIS session with clean
stream and transaction state through the normal application-owned lifecycle.

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

#### Scenario: Transaction timeout is not partial snapshot success
- **WHEN** a DMP SIS transaction times out before all ten OIDs complete
- **THEN** the current polling cycle is abandoned as a session-level failure
- **AND** it is not emitted as a successful complete snapshot
- **AND** it does not continue to remaining OIDs on the same session

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

#### Scenario: Timeout cleanup releases DMP session
- **WHEN** a DMP SIS transaction times out
- **THEN** the worker closes the SSH channel, SSH client/session, and related transport resources on the owning background lane
- **AND** terminal error/completion is emitted only after cleanup

#### Scenario: Later fresh session starts clean
- **WHEN** a later DMP polling context starts after a previous transaction timeout
- **THEN** it establishes a new SSH/SIS session
- **AND** it starts with clean stream, transaction, and session-scoped recovery state

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

### Requirement: Matrix application lifecycle controller
Matrix refresh, route mutation, quick/status refresh, persistent
handler/session reuse, keepalive/liveness, and cleanup SHALL be owned by a
Matrix-specific application/composition controller boundary rather than by
`MatrixScreen` or by a generic multi-device manager.

The controller SHALL capture an explicit immutable Matrix operation context
before background work starts. The context SHALL include the selected Matrix
model, IP address, operation kind, request/generation identity, expected
worker/background-operation identity when applicable, and route output/input
numbers for route mutation. The context SHALL also include a non-secret
credential context revision or equivalent opaque token and the assigned
candidate index when credentials participate in the operation. Qt widgets
SHALL NOT be the authoritative source for determining whether a submitted
background Matrix operation is current.

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
- **THEN** the controller captures immutable model, IP, operation kind, request/generation identity, expected operation identity, credential context revision, and candidate index before network I/O starts when applicable
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
generation/request ID, model, IP address, non-secret credential context
revision, assigned candidate index when applicable, and expected
worker/background-operation identity. Candidate index alone SHALL NOT be
sufficient to prove freshness or session reuse.

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
The Matrix application controller SHALL retain and own one persistent Matrix
handler/session for the active Matrix context. The persistent handler/session
SHALL NOT be owned by `MatrixScreen` and SHALL NOT remain directly owned by
`VCSDiagnosticApp` after extraction.

A persistent Matrix session SHALL be reusable only when model, IP address,
protocol/port, non-secret credential context revision or equivalent opaque
token, assigned candidate index, and local connected state all match the
current Matrix context. Candidate index alone SHALL NOT be sufficient for
reuse. Username, password, profile name, or other secret credential values
SHALL NOT be included in public context identity, signals, results, logs, or
terminal output.

The Matrix application lifecycle SHALL invalidate and close the superseded
session on model change, IP change, credential configuration revision change,
credential fallback to another candidate, explicit reconnect,
authentication/session failure, screen destruction, and application close.
Blocking session acquisition, route mutation, refresh, quick/status refresh,
keepalive/liveness checks, and cleanup SHALL run on the owning background
execution boundary outside the Qt GUI thread. Cleanup SHALL be idempotent and
stale-safe.

Access to the one persistent Matrix handler SHALL be serialized. Overlapping
refresh, route, quick/status refresh, and keepalive operations SHALL NOT invoke
the same persistent handler concurrently.

#### Scenario: No cross-context session reuse
- **WHEN** a persistent handler/session was created for Matrix device A
- **AND** the operator changes model, IP, or credential context to device B
- **THEN** the session for A is not reused for B

#### Scenario: Candidate index alone is not session identity
- **WHEN** Matrix candidate index `0` remains selected
- **AND** credential configuration changes so candidate `0` has a new credential context revision
- **THEN** the existing Matrix persistent session is invalidated
- **AND** it is not reused under the new credential context revision

#### Scenario: Credential fallback invalidates session
- **WHEN** Matrix credential fallback advances to another candidate
- **THEN** any persistent session created with the superseded credential context is invalidated before the next Matrix network operation

#### Scenario: Cleanup is stale-safe
- **WHEN** cleanup or finished handling for an old Matrix session completes after a newer Matrix context is active
- **THEN** old cleanup does not clear or disconnect the newer context's handler/session ownership

#### Scenario: Session access is serialized
- **WHEN** one persistent Matrix handler is retained for an active context
- **THEN** overlapping refresh, route, quick refresh, and keepalive operations do not invoke that handler concurrently

#### Scenario: Application close releases Matrix session
- **WHEN** the application closes with a persistent Matrix handler/session active
- **THEN** the Matrix lifecycle owner releases it through the defined cleanup boundary
- **AND** terminal callbacks cannot update a destroyed or newer context

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

### Requirement: Independent related-codec request context

Automatic related-codec status work started from an accepted PDU refresh SHALL have an
application-owned request context independent from PDU refresh/mutation lanes, generic
`_active_request`, global `current_worker`, and the user codec interactive-session context.

The immutable context SHALL bind at least enrichment generation/operation identity, accepted
PDU generation and refresh operation identity, PDU model/IP, immutable inventory
`snapshot_id`, selected PDU/codec record identities, authoritative room ID, codec model/IP,
and non-secret credential-context revisions or equivalent freshness tokens.

A repeat accepted user PDU refresh SHALL create a new enrichment generation even when every
resolved public and credential/profile identity value is unchanged.

PDU model/IP/context change, PDU credential-context change, start of a new or repeat user PDU
refresh, explicit PDU context invalidation/deactivation, inventory replacement, relevant
codec credential change, and application shutdown SHALL supersede old enrichment immediately
through a focused PDU/application lifecycle boundary. Supersession SHALL NOT wait for a new
successful PDU result.

#### Scenario: Repeat Refresh uses the same PDU and codec identity

- **GIVEN** related-codec work is active or queued for one accepted PDU refresh
- **WHEN** a later refresh for the same PDU resolves the same codec model/IP, credential chain/index, and saved profile
- **THEN** the later lifecycle creates a distinct enrichment generation
- **AND** the old generation cannot update presentation or credential/profile memory
- **AND** equal public/session identity does not preserve currentness

#### Scenario: Replacement PDU refresh fails

- **GIVEN** old enrichment was superseded when replacement PDU refresh started
- **WHEN** replacement PDU refresh fails without accepted success
- **THEN** old enrichment remains stale
- **AND** no old related-codec callback or queued operation becomes current again

#### Scenario: User codec session has another context

- **GIVEN** `CodecScreen` owns an interactive session for codec A
- **WHEN** PDU enrichment starts status for codec B
- **THEN** distinct context generations and session ownership are used
- **AND** neither context invalidates, reuses, or authorizes callbacks for the other

### Requirement: Every new enrichment forces dedicated session-generation rollover

Before activating the dedicated related-codec session for every new enrichment generation,
the enrichment controller SHALL invalidate the previous dedicated session context even when
the prospective session identity is unchanged.

The compliant lifecycle SHALL be equivalent to:

```text
new enrichment generation becomes current
    -> dedicated session invalidate_context or equivalent force rollover
    -> dedicated session activate_context
    -> related-codec read submission
```

The implementation MAY add an explicit force-rollover API or include enrichment generation in
private session identity, but it SHALL prove equivalent behavior. Calling the existing
`activate_context()` with equal model/IP/credential identities/start index/saved profile and
accepting its existing generation SHALL NOT satisfy this requirement.

The force rollover SHALL happen synchronously with currentness publication before old queued
work can acquire a handler. Cleanup may remain serialized on the owning execution lane.

#### Scenario: Old operation is queued and next context is identical

- **GIVEN** an old related-codec operation is queued behind other lane work
- **WHEN** repeat PDU Refresh produces an identical related-codec session identity
- **THEN** the dedicated session generation is rolled over before new activation
- **AND** the old operation observes stale generation at the head of the queue
- **AND** handler factory/acquisition is not invoked for that old operation
- **AND** the old operation performs zero network I/O

### Requirement: Related-codec stale work is suppressed before network I/O

Queued related-codec work SHALL recheck both its captured enrichment generation and dedicated
session generation immediately before handler acquisition. When handler preparation and first
network I/O are separate, it SHALL recheck again immediately before first network I/O.

A stale queued operation SHALL be dropped without constructing or acquiring a handler,
opening HTTP/HTTPS/SSH or another transport, or sending a device request. Background code
SHALL NOT read Qt widget values as freshness authority.

If I/O was already in flight when context became stale, its result, error, progress,
completion, credential index, and connection profile SHALL NOT change current presentation,
PDU state, or successful credential/profile memory. Cleanup SHALL still occur on the owning
execution lane.

#### Scenario: Queued enrichment is superseded before execution

- **WHEN** related-codec status is queued and a new enrichment generation is published before it reaches the lane head
- **THEN** the operation is dropped before handler acquisition
- **AND** it performs zero network I/O

#### Scenario: Context changes after handler preparation

- **WHEN** a related-codec handler is prepared and context becomes stale before first network I/O
- **THEN** the final freshness check prevents transport open and device request
- **AND** prepared resources are released safely

#### Scenario: Old status returns after new PDU context

- **WHEN** in-flight status from an old PDU context completes after supersession
- **THEN** old status does not update related-room presentation, PDU state, dialogs, controls, or credential/profile memory

### Requirement: Bounded read-only related-codec recovery

Related-codec status SHALL execute outside the Qt GUI thread through one dedicated serialized
application-owned lane. It SHALL use read-only semantics and permit at most one reconnect
cycle and one replay after successful recovery. Recovery SHALL not recurse.

Confirmed established-session invalidation SHALL first invalidate the old handler/session and
reconnect with the same assigned credential using supported saved-first transport order.
Credential advancement MAY occur only when a new login during acquisition/recovery produces
structured confirmed authentication rejection and another unattempted candidate remains.
Transport, session, authentication, protocol, and unavailable-status failures SHALL remain
separately classified.

#### Scenario: Related-codec session expires

- **WHEN** read-only status detects confirmed established-session invalidation
- **THEN** the lane invalidates that session and performs at most one reconnect cycle
- **AND** successful reconnect permits at most one replay

#### Scenario: Transport fallback is available

- **WHEN** one supported transport fails without structured authentication rejection and another remains
- **THEN** acquisition may continue on the next transport with the same assigned credential
- **AND** no credential advancement occurs from transport failure

### Requirement: Related-codec resource release

The dedicated related-codec lane SHALL invalidate and release its handler, HTTP opener,
cookies, Session ID, CSRF/access token, SSH client/channel, and other model-specific resources
on terminal success, terminal failure, PDU/enrichment supersession, relevant credential
change, inventory replacement, and application shutdown.

Network/session cleanup SHALL run on the owning background lane. GUI invalidation SHALL
publish cancellation/currentness without blocking the Qt GUI thread on network cleanup.
Cleanup SHALL be idempotent or exactly once, and callbacks after supersession SHALL remain
stale.

#### Scenario: Application closes during related-codec work

- **WHEN** shutdown supersedes active related-codec work
- **THEN** enrichment and session contexts are invalidated immediately
- **AND** resource cleanup runs on the owning background lane
- **AND** no later callback updates closing or destroyed GUI

### Requirement: CloudLink Bar 310 polling uses a closed resilient status plan

An ordinary CloudLink Bar 310 status refresh SHALL execute an explicit reviewed read-only polling plan rather than iterate every entry in the handler command map.

The required core request SHALL be exactly `get_version`. The optional read-only enrichment requests SHALL be limited to MAC, audio, line/SIP, call, presentation, sleep, camera, and HD-AI microphone status. Configuration requests including `get_config_default` and `get_config`, every state-changing request, and future command-map-only entries SHALL NOT run during ordinary status refresh unless added to the reviewed polling plan by a later approved change.

After the required core request succeeds, an endpoint-specific optional `CommandError`, unsuccessful optional response, or optional payload `ProtocolError` SHALL omit only the fields owned by that endpoint and SHALL NOT erase already collected canonical status. The handler MAY emit a safe redacted diagnostic for the unavailable optional endpoint.

`AuthenticationError`, `SessionInvalidError`, and `ConnectionError` SHALL remain terminal typed failures from every phase of status collection. An established-session HTTP 401 or 403 SHALL therefore remain `SessionInvalidError`, and a transport failure during an optional read SHALL remain `ConnectionError`. Unexpected exceptions SHALL NOT be converted into an empty successful payload.

#### Scenario: Configuration endpoint exists in the command map

- **GIVEN** `get_config` or `get_config_default` remains available for another handler purpose
- **WHEN** ordinary Bar 310 status refresh runs
- **THEN** the refresh does not invoke that configuration endpoint
- **AND** command-map membership alone does not grant polling authority

#### Scenario: Optional presentation read is unavailable

- **GIVEN** the required version response and other status responses succeeded
- **WHEN** the optional presentation endpoint returns an endpoint-specific unsuccessful or malformed response
- **THEN** the handler preserves the already collected canonical fields
- **AND** it omits `presentation` from that refresh result
- **AND** it does not return an empty mapping
- **AND** it does not authorize credential fallback

#### Scenario: Established session is rejected during optional read

- **GIVEN** Bar 310 login completed and the required core response succeeded
- **WHEN** an optional established-session request returns HTTP 401 or 403
- **THEN** status collection raises `SessionInvalidError`
- **AND** the failure remains available to the application-owned same-credential recovery policy
- **AND** partial status is not emitted as successful evidence

#### Scenario: Optional read has a transport failure

- **WHEN** an optional Bar 310 request times out or loses transport
- **THEN** status collection raises `ConnectionError`
- **AND** the handler does not downgrade the transport failure to partial success

### Requirement: CloudLink Bar 310 required core evidence is exact

For the closed CloudLink Bar/Box 310 protocol family, a successful `get_version` observation SHALL require all of the following:

```text
outer response is a Mapping
outer response["success"] == 1
outer response["data"] is a Mapping
"softVersion" exists in data
data["softVersion"] is a string
version = data["softVersion"].strip()
version is non-empty
version.casefold() != "unknown"
```

`softVersion` SHALL remain the only approved software-version source key. The shared handler SHALL NOT use another response key, `Unknown`, `N/A`, an empty value, a model constant, or another manufactured default as software-version evidence.

Before the shared Bar/Box protocol path executes, the already assigned exact application model SHALL determine one trusted expected handler/parser/display identity through this closed mapping:

```text
CloudLink Bar 310 -> Huawei CloudLink Bar 310
CloudLink Box 310 -> Huawei CloudLink Box 310
```

No other input SHALL select or alter that identity. In particular, device response text, source inventory text, model substrings, handler availability, protocol success/failure, prior requests, or the other family member SHALL NOT become model-identity authority.

After the exact core gate succeeds, the shared handler result SHALL contain exactly:

```text
model == expected handler/parser/display identity for the already assigned application model
version == data["softVersion"].strip()
```

The model string SHALL NOT be copied from a free-form device response or changed to another spelling. The same successful response MAY add `serial_number` from observed `data["lisence"]` and `mic_version` from observed `data["micVersion"]`; absence of those optional values SHALL NOT invalidate core success and SHALL NOT create `N/A` defaults.

An unsuccessful required core response SHALL raise `CommandError`. Missing/non-Mapping core data, a missing `softVersion`, `None`, a non-string value, an empty or whitespace-only string, or a case-insensitive `Unknown` value SHALL raise `ProtocolError`. No result mapping SHALL be returned as success for those outcomes.

#### Scenario: Required core response is successful

- **GIVEN** the already assigned application model is exactly `CloudLink Bar 310`
- **WHEN** `get_version.data["softVersion"]` is a non-empty string after `strip()` and is not `Unknown`
- **THEN** handler `model` is exactly `Huawei CloudLink Bar 310`
- **AND** handler `version` is exactly the stripped `softVersion`
- **AND** no response-provided model label or manufactured version default is used

#### Scenario: Box 310 required core response is successful

- **GIVEN** the already assigned application model is exactly `CloudLink Box 310`
- **WHEN** `get_version.data["softVersion"]` is a non-empty string after `strip()` and is not `Unknown`
- **THEN** handler `model` is exactly `Huawei CloudLink Box 310`
- **AND** handler `version` is exactly the stripped `softVersion`
- **AND** no response-provided model label or Bar identity is used

#### Scenario: Required core response is unsuccessful

- **WHEN** the required version endpoint returns `success != 1`
- **THEN** status collection raises `CommandError`
- **AND** no result mapping is returned as success

#### Scenario: Required core version key is absent

- **WHEN** successful core data lacks exact key `softVersion`
- **THEN** status collection raises `ProtocolError`
- **AND** another version key does not satisfy the gate

#### Scenario: Required core version value is unusable

- **WHEN** `softVersion` is `None`, non-string, empty, whitespace-only, or case-insensitive `Unknown`
- **THEN** status collection raises `ProtocolError`
- **AND** canonical model/version defaults are not manufactured

### Requirement: CloudLink Bar 310 optional field ownership and precedence are closed

The canonical handler result SHALL use this exact endpoint ownership map:

| Endpoint | Canonical fields |
| --- | --- |
| `get_version` | required `model`, required `version`; optional `serial_number`, `mic_version` |
| `get_mac` | `mac_address` |
| `get_audio_status` | `mic_mute`, `speaker_mute`, `speaker_volume` |
| `get_line_state` | `uptime`, `sip_server`, `sip_number`, primary `sip_status` |
| `get_call_status` | `call_status`; fallback `sip_status` only when line-state produced no valid SIP observation |
| `get_presentation` | `presentation` |
| `get_sleep_mode` | `sleep_mode` |
| `get_camera_status` | `camera_status` |
| `GET /v1/mediacontrol/mic/devices` | `mic_connection_status`, `mic_volume` |

`get_mac` SHALL use the first non-empty observed value in this order: `system_wanMAC_addr`, then `system_lanMAC_addr`.

Line-state SIP evidence SHALL be authoritative for the refresh. Call-state `state.sip == 1` MAY populate `sip_status = On` and `state.sip == 0` MAY populate `sip_status = Off` only when line-state produced no valid `sip_status`. Call-state evidence SHALL NOT overwrite line-state evidence. On disagreement, line-state SHALL win.

Camera normalization SHALL map only `localInMainSource == 255` to `camera_status = On` and `localInMainSource == 0` to `camera_status = Off`. A missing or unsupported value SHALL be an endpoint-local protocol failure and `camera_status` SHALL be omitted.

For a successful HD-AI microphone response, decoded `data` SHALL be a Mapping and `data["deviceList"]` SHALL be a list. The handler SHALL keep Mapping entries whose `groupName == "HD-AI"`, preserve source list order, and use the first matching entry. A successfully observed empty filtered list SHALL produce `mic_connection_status = "Микрофон не подключён"` and SHALL omit `mic_volume`.

For the selected HD-AI entry:

```text
str(plugStatus) == "0"
    -> mic_connection_status = "Микрофон не подключён"
    -> mic_volume omitted

str(plugStatus) == "1"
    -> mic_connection_status = "Подключён"
    -> mic_volume = observed gainVolume, including numeric zero
```

Missing/unsupported `plugStatus`, malformed `deviceList`, or a connected entry with absent/`None` `gainVolume` SHALL be endpoint-local `ProtocolError` outcomes and both microphone fields SHALL be omitted. Endpoint unavailability SHALL NOT be converted into an observed disconnected microphone.

Failure or absence of one optional endpoint SHALL NOT delete or manufacture fields owned by another endpoint. The parser SHALL NOT add an endpoint-owned field that was absent from the canonical handler mapping.

#### Scenario: Line and call SIP observations agree

- **GIVEN** line-state produced a valid SIP observation
- **AND** call-state produced the same SIP observation
- **WHEN** the refresh result is composed
- **THEN** the line-state value remains canonical
- **AND** call-state does not overwrite it

#### Scenario: Line and call SIP observations conflict

- **GIVEN** line-state produced a valid SIP observation
- **AND** call-state produced the opposite observation
- **WHEN** the refresh result is composed
- **THEN** line-state wins
- **AND** call-state does not overwrite `sip_status`

#### Scenario: Call SIP fallback is used

- **GIVEN** line-state produced no valid SIP observation
- **AND** call-state reports `state.sip == 1` or `state.sip == 0`
- **WHEN** the refresh result is composed
- **THEN** call-state supplies the fallback `sip_status`

#### Scenario: Successful HD-AI list is empty

- **WHEN** the HD-AI endpoint succeeds with a valid empty `deviceList` or no `HD-AI` entries
- **THEN** `mic_connection_status` is `Микрофон не подключён`
- **AND** `mic_volume` is omitted
- **AND** this observed state remains distinguishable from endpoint unavailability

#### Scenario: HD-AI microphone is physically disconnected

- **WHEN** the selected HD-AI entry reports `plugStatus == 0`
- **THEN** `mic_connection_status` is `Микрофон не подключён`
- **AND** `mic_volume` is omitted

#### Scenario: Connected HD-AI microphone reports zero gain

- **WHEN** the selected HD-AI entry reports `plugStatus == 1` and `gainVolume == 0`
- **THEN** `mic_connection_status` is `Подключён`
- **AND** `mic_volume` remains present with value zero

#### Scenario: HD-AI list is malformed

- **WHEN** the HD-AI endpoint succeeds but `deviceList` is not a list
- **THEN** the endpoint has a local `ProtocolError`
- **AND** both microphone fields are omitted
- **AND** already collected fields remain available

#### Scenario: Camera endpoint is unavailable

- **WHEN** the camera endpoint is not successfully observed
- **THEN** `camera_status` is omitted
- **AND** the parser does not manufacture `Статус камеры = Подключена`

#### Scenario: Camera is observed disconnected

- **WHEN** a successful camera response reports `localInMainSource == 0`
- **THEN** canonical `camera_status` is `Off`
- **AND** parser display status is `Не подключена`

### Requirement: CloudLink Bar 310 normalization distinguishes unavailable from observed state

CloudLink Bar 310 canonical status fields SHALL be populated only from successful structured endpoint observations. An unavailable optional endpoint SHALL cause its canonical fields to be omitted rather than replaced with semantic defaults such as `Off`, `Stop`, `No Call`, `Подключена`, `Микрофон не подключён`, or zero.

A successful endpoint value that is legitimately zero, false, idle, stopped, muted, disconnected, or sleeping SHALL remain present and SHALL NOT be mistaken for missing data.

Presentation normalization SHALL map only `isSendAux == auxOpen` to `Start` and `isSendAux == auxClose` to `Stop`. Sleep normalization SHALL map only `isSystemSleep == sleep` to `On` and `isSystemSleep == unsleep` to `Off`. Unsupported or malformed values SHALL be endpoint-specific protocol failures rather than guessed states.

The same presentation and sleep normalization logic SHALL be used by ordinary full status refresh and interactive readback methods.

#### Scenario: Presentation endpoint is absent from a partial result

- **WHEN** the presentation endpoint was not successfully observed
- **THEN** canonical presentation is omitted
- **AND** the parser does not convert absence into `Stop`

#### Scenario: Presentation is observed inactive

- **WHEN** a successful structured presentation response reports `auxClose`
- **THEN** canonical presentation is `Stop`
- **AND** the value remains distinguishable from an unavailable endpoint

#### Scenario: Sleep endpoint reports active sleep

- **WHEN** a successful structured sleep response reports `sleep`
- **THEN** canonical sleep mode is `On`
- **AND** ordinary polling and interactive readback produce the same value

#### Scenario: Observed speaker volume is zero

- **WHEN** a successful audio response reports a valid speaker volume of zero
- **THEN** canonical speaker volume remains present with value zero
- **AND** zero is not treated as unavailable data

### Requirement: CloudLink Bar 310 parser and worker success require exact usable canonical status

For each operation in the closed Bar/Box 310 protocol family, `HuaweiBar310DataParser` and `HuaweiBar310Worker` SHALL validate against the trusted expected handler/parser/display identity derived from the already assigned exact application model:

```text
CloudLink Bar 310 -> Huawei CloudLink Bar 310
CloudLink Box 310 -> Huawei CloudLink Box 310
```

`HuaweiBar310DataParser` SHALL reject raw data unless it is a Mapping with exact `model == expected handler/parser/display identity` and a non-empty string `version` that is not `Unknown`.

The parser SHALL produce these exact required display fields without defaults:

```text
"Модель" == expected handler/parser/display identity
"Версия ПО" is non-empty and derived from raw_data["version"]
```

A missing model, a model different from the expected identity for the bound operation, a missing/non-string/empty version, `Unknown`, or a version that becomes empty after display cleanup SHALL raise `ParseError`. Accepting either Bar or Box identity without checking which exact application model owns the operation SHALL NOT satisfy this requirement. Optional display fields SHALL be emitted only when their canonical handler fields are present. In particular, `Статус камеры`, SIP, call, presentation, sleep, microphone status, and microphone volume SHALL NOT be manufactured from absence.

`HuaweiBar310Worker` SHALL defensively raise `ProtocolError` for an empty Mapping, non-Mapping payload, payload whose exact `model` differs from the expected identity for its already assigned application model, payload without a non-empty usable `version`, or metadata-only payload. It SHALL add technical `ip_address` and `connection_profile` fields only after raw and parsed payload validation succeeds.

Raw-payload `ProtocolError` and parser `ParseError` SHALL pass through the existing typed codec failure classifier and SHALL emit exact machine category:

```text
protocol_error
```

The worker SHALL NOT represent these contract failures with `ValueError`, a generic exception, an explicit `connection_error`, or another transport category.

For an unusable payload, the worker SHALL emit no result signal, SHALL emit `protocol_error`, SHALL disconnect any created handler, and SHALL emit completion. For a usable partial payload, the worker SHALL emit the canonical result and preserve the existing cleanup/completion lifecycle.

The application/composition layer SHALL remain the authority for stale-result acceptance and successful credential-index/profile persistence. An unusable Bar/Box 310 payload SHALL NOT become successful-operation evidence for that policy.

#### Scenario: Handler returns an empty mapping

- **WHEN** `handler.get_status()` returns `{}`
- **THEN** the worker raises `ProtocolError`
- **AND** it emits no success result
- **AND** it emits error category `protocol_error`
- **AND** it disconnects the handler before completion
- **AND** technical metadata is not used to turn the payload into success

#### Scenario: Handler returns technical metadata without core status

- **WHEN** a payload contains an IP address or connection profile but lacks exact usable core model/version evidence for the bound Bar/Box operation
- **THEN** the worker raises `ProtocolError`
- **AND** it emits error category `protocol_error`
- **AND** successful credential or profile memory is not updated from that attempt

#### Scenario: Bar context rejects Box identity

- **GIVEN** the operation is bound to exact application model `CloudLink Bar 310`
- **WHEN** raw or parsed canonical identity is `Huawei CloudLink Box 310`
- **THEN** the worker or parser rejects the mismatch through `ProtocolError` or `ParseError` as applicable
- **AND** no result signal is emitted
- **AND** the operation is not rewritten or retried as Box 310

#### Scenario: Box context rejects Bar identity

- **GIVEN** the operation is bound to exact application model `CloudLink Box 310`
- **WHEN** raw or parsed canonical identity is `Huawei CloudLink Bar 310`
- **THEN** the worker or parser rejects the mismatch through `ProtocolError` or `ParseError` as applicable
- **AND** no result signal is emitted
- **AND** the operation is not rewritten or retried as Bar 310

#### Scenario: Parser result lacks required display fields

- **WHEN** parser output lacks exact expected `Модель` or a non-empty derived `Версия ПО`
- **THEN** parsing raises `ParseError`
- **AND** worker error category is `protocol_error`
- **AND** no result signal is emitted

#### Scenario: Required core and some optional reads succeed

- **GIVEN** the operation is bound to exact `CloudLink Bar 310`
- **AND** the exact required version response succeeded
- **AND** at least one optional endpoint was unavailable without a terminal session or transport failure
- **WHEN** the handler returns the usable partial canonical mapping
- **THEN** parser `Модель` is exactly `Huawei CloudLink Bar 310`
- **AND** parser `Версия ПО` is a non-empty value derived from handler `version`
- **AND** the worker emits a success result containing observed fields
- **AND** unavailable optional fields remain omitted
- **AND** cleanup and completion follow the normal success lifecycle

#### Scenario: Box required core and some optional reads succeed

- **GIVEN** the operation is bound to exact `CloudLink Box 310`
- **AND** the exact required version response succeeded
- **AND** at least one optional endpoint was unavailable without a terminal session or transport failure
- **WHEN** the shared handler returns the usable partial canonical mapping
- **THEN** parser `Модель` is exactly `Huawei CloudLink Box 310`
- **AND** parser `Версия ПО` is a non-empty value derived from handler `version`
- **AND** the worker emits a success result containing observed fields
- **AND** unavailable optional fields remain omitted
- **AND** cleanup and completion follow the normal success lifecycle

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

### Requirement: CloudLink Box 310 reuses the approved CloudLink Bar 310 protocol lifecycle with distinct identity

For an application request whose already assigned exact canonical model is `CloudLink Box 310`, the codec lifecycle SHALL use the same management protocol implementation, supported transport profile, command semantics, polling plan, endpoint ownership, normalization, typed failure behavior, recovery policy, cleanup, and redaction boundaries already approved for `CloudLink Bar 310`.

The shared protocol lifecycle SHALL preserve distinct trusted product identity. The exact mapping SHALL be:

```text
application model CloudLink Bar 310
    -> handler/parser/display model Huawei CloudLink Bar 310

application model CloudLink Box 310
    -> handler/parser/display model Huawei CloudLink Box 310
```

The expected handler/parser/display identity SHALL be derived only from the already assigned exact application model through a closed reviewed mapping or equivalent exact construction parameter. It SHALL NOT be inferred from device response text, source inventory text, model substrings, handler availability, protocol success/failure, or another family member.

`CloudLinkBar310Handler` SHALL remain the shared protocol implementation for both approved products. Implementation SHALL NOT create a second independent Box 310 copy of the Bar command map, polling plan, endpoint normalizers, or transport/session logic solely to support the additional name.

For both products, the currently approved Bar 310 required-core version gate, explicit optional read-only polling plan, endpoint field ownership and precedence, optional command/protocol failure isolation, terminal authentication/session/transport failures, presentation/sleep normalization, observed-zero preservation, parser success gate, worker cleanup, and secret-redaction requirements SHALL apply unchanged except for the exact expected product identity defined by the modified requirements above.

All existing application paths that select protocol capability by exact Bar 310 model SHALL treat `CloudLink Bar 310` and `CloudLink Box 310` as one closed protocol family while preserving the exact assigned model in operation context. This includes ordinary status refresh, supported interactive codec operations, related-codec read-only status acquisition, and existing Bar-supported SIP-server configuration behavior.

The application SHALL continue to own credentials and successful connection memory by exact canonical model and IP. Protocol equivalence SHALL NOT authorize implicit credential sharing, credential fallback, successful-index sharing, connection-profile sharing, or model switching between Bar 310 and Box 310. A deployment MAY explicitly configure the same credential profile for both exact models, but that is configuration rather than runtime alias behavior.

A failure in a Box 310 operation SHALL remain a failure of the already assigned Box 310 path under existing typed policy. No authentication, session, transport, protocol, parser, timeout, or ambiguous-result failure SHALL cause the application, worker, handler, parser, or interactive controller to retry the operation as `CloudLink Bar 310`. The inverse restriction applies to Bar 310.

#### Scenario: Box 310 ordinary refresh uses the shared protocol implementation

- **GIVEN** application dispatch assigned exact model `CloudLink Box 310`
- **WHEN** ordinary codec refresh acquires the Bar/Box protocol implementation
- **THEN** it uses the same approved Bar 310 transport and polling semantics
- **AND** the canonical raw status model is exactly `Huawei CloudLink Box 310`
- **AND** parsed GUI model is exactly `Huawei CloudLink Box 310`
- **AND** no second Box-specific command map or polling plan is required

#### Scenario: Existing Bar 310 identity remains unchanged

- **GIVEN** application dispatch assigned exact model `CloudLink Bar 310`
- **WHEN** the shared protocol implementation completes a usable refresh
- **THEN** the canonical raw status model remains exactly `Huawei CloudLink Bar 310`
- **AND** parsed GUI model remains exactly `Huawei CloudLink Bar 310`
- **AND** Box 310 support does not weaken the existing Bar identity gate

#### Scenario: Shared implementation receives the wrong expected identity

- **GIVEN** an operation is bound to exact application model `CloudLink Box 310`
- **WHEN** the worker or parser observes/receives canonical protocol identity `Huawei CloudLink Bar 310` instead of the expected Box identity
- **THEN** the operation fails through the existing protocol/parser error path
- **AND** it does not silently rewrite the result, accept the other family identity, or change the assigned model

#### Scenario: Box 310 interactive operation uses the Bar protocol capability

- **GIVEN** the current interactive context model is exactly `CloudLink Box 310`
- **WHEN** an operation supported by the existing Bar 310 handler is submitted
- **THEN** handler acquisition uses the shared `CloudLinkBar310Handler` implementation and the approved Box transport profile
- **AND** the interactive context and result model remain exactly `CloudLink Box 310`
- **AND** stale and retry policy remains unchanged

#### Scenario: Box 310 is the related room codec

- **GIVEN** PDU room resolution returns exact `codec_diagnostic_model = CloudLink Box 310`
- **WHEN** related-codec read-only status is acquired
- **THEN** the controller resolves credentials and connection memory for exact Box 310 model/IP
- **AND** it uses the same Bar 310 call/presentation command semantics
- **AND** accepted presentation still reports exact `CloudLink Box 310`

#### Scenario: Bar and Box credential success is not shared implicitly

- **GIVEN** a credential candidate succeeds for `CloudLink Box 310` at one IP
- **WHEN** application success memory is persisted
- **THEN** only the exact Box 310 model/IP successful index and connection profile are updated
- **AND** no `CloudLink Bar 310` credential index or connection profile is changed solely because the protocol is shared

#### Scenario: Box failure does not retry as Bar

- **GIVEN** an operation is bound to exact model `CloudLink Box 310`
- **WHEN** the operation fails with authentication, session, transport, protocol, parser, timeout, or ambiguous-result failure
- **THEN** existing retry/recovery policy applies only within the Box 310 operation context
- **AND** no component changes the model to `CloudLink Bar 310` as fallback

