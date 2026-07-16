# request-lifecycle-and-recovery Specification

## Purpose
TBD - created by archiving change bootstrap-openspec-baseline. Update Purpose after archive.
## Requirements
### Requirement: Background diagnostic execution
Network diagnostic refresh operations SHALL execute through QRunnable workers
submitted to `QThreadPool` and SHALL return progress, status, result, error,
connection, and completion information through worker signals. Workers SHALL
disconnect handlers in their cleanup paths when a handler was created.

#### Scenario: Worker succeeds
- **WHEN** a device worker connects, collects status, and parses a response
- **THEN** it emits a result for the GUI and releases its handler before emitting completion

#### Scenario: Worker fails
- **WHEN** a device worker encounters an authentication or connection exception
- **THEN** it emits a classified error and emits completion after its cleanup path

### Requirement: Request-context isolation
The main window SHALL associate device results, errors, and completion with the
active request context, including the selected model, IP address, target screen,
and request identifier. It SHALL ignore callbacks from superseded requests and
shall not let them change the current screen or refresh-button state.

#### Scenario: Stale result arrives after a newer request
- **WHEN** a prior worker emits a result after the operator has started a newer request for a different IP or screen
- **THEN** the prior result is ignored and the newer request remains active

#### Scenario: Stale completion arrives after a newer request
- **WHEN** a prior worker emits completion while a newer request is loading
- **THEN** the prior completion does not re-enable refresh or replace the newer state

### Requirement: Credential retry and connection-profile memory
The application SHALL try configured credentials in order for a supported
device refresh or interactive session when a confirmed authentication failure
is classified and additional credentials remain. It SHALL begin at the valid
successful credential index for the exact device/IP context, advance a
request-scoped cursor monotonically without wrap-around, and retain the
successful credential index and connection profile for that context only after
a final successful operation. A supported retained connection profile SHALL be
the first transport candidate for later refresh and interactive connections.

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

### Requirement: Persistent resource release
The application SHALL disconnect the persistent Extron handler on window close
and SHALL stop timers, invalidate reusable codec interactive contexts, and
close their HTTP sessions, cookies, tokens, cookie jars, SSH channels, and
handlers when their screen is destroyed or the application closes. A codec
model, IP, or credential-context change SHALL close the superseded interactive
handler before it can be reused by the new context.

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
operation.

#### Scenario: Read-only operation loses its session
- **WHEN** live polling, status, sleep, volume, presentation, or Huawei call-log reading fails because the session is invalid
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
