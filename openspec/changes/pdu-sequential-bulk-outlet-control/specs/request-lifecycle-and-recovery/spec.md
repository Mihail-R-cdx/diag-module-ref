## MODIFIED Requirements

### Requirement: Request-context isolation
The main window SHALL associate device results, errors, completions, and PDU
command outcomes with the active request context, including the selected model,
IP address, target screen, credential context, and request identifier. It SHALL
ignore callbacks from superseded requests and shall not let them change the
current screen, outlet table, command state, credential memory, or
refresh-button state. This includes bulk PDU sequence results, errors,
progress, partial terminal outcomes, and completions.

For PDU operations, including PCS4i refresh, PCS4i ON/OFF commands, PCS4i bulk
ON/OFF, Aten refresh, Aten ON/OFF/REBOOT commands, and Aten bulk ON/OFF, the
application/composition layer SHALL own the current operation context
generation. Background workers SHALL NOT read Qt widgets, including
`device_combo`, `ip_entry`, `PDUScreen`, or other QWidget properties, to decide
whether a PDU operation is current.

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
