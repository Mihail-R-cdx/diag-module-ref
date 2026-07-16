## MODIFIED Requirements

### Requirement: Background diagnostic execution
Network diagnostic refresh operations SHALL execute through QRunnable workers
submitted to `QThreadPool` and SHALL return progress, status, result, error,
connection, and completion information through worker signals. Workers SHALL
disconnect handlers in their cleanup paths when a handler was created. PDU
refresh paths, including Extron IPL T PCS4i Telnet status reads and optional
HTTP outlet-name enrichment, SHALL follow this background execution boundary.

#### Scenario: Worker succeeds
- **WHEN** a device worker connects, collects status, and parses a response
- **THEN** it emits a result for the GUI and releases its handler before emitting completion

#### Scenario: Worker fails
- **WHEN** a device worker encounters an authentication or connection exception
- **THEN** it emits a classified error and emits completion after its cleanup path

#### Scenario: PCS4i refresh stays off the GUI thread
- **WHEN** PCS4i refresh performs Telnet connect/read work or HTTP outlet-name enrichment
- **THEN** that network work runs in a background worker rather than the Qt GUI thread

### Requirement: Request-context isolation
The main window SHALL associate device results, errors, completions, and PDU
command outcomes with the active request context, including the selected model,
IP address, target screen, credential context, and request identifier. It SHALL
ignore callbacks from superseded requests and shall not let them change the
current screen, outlet table, command state, or refresh-button state.

For PDU operations, the application/composition layer SHALL own the current
operation context generation. Background workers SHALL NOT read Qt widgets,
including `device_combo`, `ip_entry`, `PDUScreen`, or other QWidget properties,
to decide whether a PDU operation is current.

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

### Requirement: Operation-specific replay and reconciliation
The application SHALL distinguish connection recovery from replay of the
original operation. A read-only operation MAY be replayed once after successful
reconnect. A state-changing operation SHALL NOT be blindly replayed after an
unknown delivery outcome; it SHALL first perform an authoritative readback and
then confirm the target, issue at most one absolute desired-state command when
the observed state permits it, or return an indeterminate/conflict outcome.
Relative volume and toggle intent SHALL never be sent twice as a relative
operation. PDU ON/OFF and REBOOT commands SHALL follow the same no-blind-replay
safety rule and the bounded PDU reconciliation budget.

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
- **AND** that cycle includes at most one recovery/reconnect sequence when needed for readback and at most one authoritative readback decision
- **AND** recovery or reconciliation does not recurse

#### Scenario: Ambiguous PCS4i reboot is not replayed
- **WHEN** a PCS4i reboot command may have reached the device but acknowledgement is lost
- **THEN** the application does not automatically send another reboot command
- **AND** it reports an indeterminate outcome with redacted details

## ADDED Requirements

### Requirement: Background PDU control execution
PDU outlet control operations for Extron IPL T PCS4i and Aten PE8208AV SHALL
execute outside the Qt GUI thread through a shared application-owned background
PDU command execution boundary. The shared boundary SHALL own operation
dispatch, background execution, lifecycle cleanup, stale-operation protection,
and structured command outcomes. Device-specific handlers SHALL remain
separate, and the boundary SHALL NOT merge Aten wire protocol, PCS4i Telnet
protocol, or PCS4i HTTP protocol.

#### Scenario: PCS4i command is slow
- **WHEN** a PCS4i outlet command blocks on Telnet network I/O
- **THEN** the Qt event loop remains responsive while the command runs in the background

#### Scenario: Aten command path is migrated
- **WHEN** an operator confirms an Aten ON, OFF, or REBOOT command
- **THEN** Aten command dispatch runs through the background PDU command worker and retains existing handler behavior
- **AND** Aten network I/O does not run on the Qt GUI thread

#### Scenario: PDU command worker cleans up
- **WHEN** a PDU command succeeds, fails, or reports an indeterminate result
- **THEN** the worker releases the handler/transport before emitting completion

### Requirement: PDU queued operation staleness
PDU refresh and command workers SHALL carry an immutable operation descriptor
with operation id, generation, model, IP address, non-secret credential context,
operation type, outlet number when applicable, and desired command/target when
applicable. The application/composition layer SHALL own the current PDU
generation and increment or replace it when relevant PDU context changes. A
queued operation SHALL recheck the captured descriptor against the current
application-owned context immediately before handler acquisition. When handler
construction and first network I/O are separate phases, it SHALL also recheck
immediately before first network I/O. A stale queued operation SHALL be dropped
without creating a handler, opening Telnet, HTTP, or Aten transport, or sending
a command.

#### Scenario: Stale PCS4i refresh is dropped
- **WHEN** a PCS4i refresh is queued and the selected device or IP changes before it starts network work
- **THEN** the operation is dropped before Telnet connect or HTTP request

#### Scenario: Stale PCS4i command is dropped
- **WHEN** a PCS4i outlet command is queued and the model, IP, or credential context changes before execution
- **THEN** the worker does not acquire a handler or send the command

#### Scenario: Stale Aten command is dropped
- **WHEN** an Aten outlet command is queued and the model, IP, or credential context changes before execution
- **THEN** the worker does not acquire a handler, open transport, or send the command

#### Scenario: Stale operation is dropped before first network I/O
- **WHEN** a PDU worker acquires or prepares a handler and the context becomes stale before the first network I/O
- **THEN** the worker performs the final validity check and exits without opening transport or sending device bytes

#### Scenario: In-flight PDU work cannot update a new context
- **WHEN** PDU network I/O was already in flight when the context changed
- **THEN** its result cannot update the current screen or authorize later stale queued PDU work

### Requirement: PDU state-changing command safety
The application SHALL treat PDU ON, OFF, and REBOOT operations as
state-changing. It SHALL not blindly repeat a command after an ambiguous
transport outcome. ON/OFF MAY use authoritative outlet readback to reconcile an
ambiguous outcome within one bounded reconciliation cycle; REBOOT SHALL not be
automatically replayed when first delivery is uncertain.

For one user PDU state-changing operation, the application SHALL send at most
one initial command. Acknowledged success SHALL complete successfully with no
additional command sends. Authoritative device rejection SHALL complete failure
with no credential fallback and no command replay. Ambiguous delivery SHALL
allow at most one reconciliation cycle, at most one authoritative readback
decision, and no recursive recovery/reconciliation. ON/OFF MAY perform at most
one controlled absolute resend only when readback authoritatively shows the
known pre-command state. REBOOT SHALL have a maximum of one send.

#### Scenario: ON target already applied
- **WHEN** a PCS4i ON command loses acknowledgement and authoritative readback shows the outlet is on
- **THEN** the operation reports success without sending ON again

#### Scenario: OFF target still absent
- **WHEN** a PCS4i OFF command loses acknowledgement and authoritative readback shows the outlet is still on
- **THEN** policy may send one controlled OFF command and performs no blind replay loop

#### Scenario: Controlled ON/OFF resend remains ambiguous
- **WHEN** the one controlled ON or OFF resend after readback has an ambiguous outcome
- **THEN** the operation reports indeterminate
- **AND** no additional command replay, recovery, or reconciliation loop runs

#### Scenario: ON/OFF state remains unknown
- **WHEN** a PCS4i ON or OFF command has ambiguous delivery and authoritative readback is unavailable
- **THEN** the operation reports indeterminate and does not resend the command

#### Scenario: REBOOT delivery is ambiguous
- **WHEN** a PCS4i REBOOT command has ambiguous delivery
- **THEN** the application does not automatically send a second REBOOT

#### Scenario: PDU command rejection is final
- **WHEN** a PDU ON, OFF, or REBOOT command receives an authoritative device rejection
- **THEN** the operation reports failure
- **AND** it does not advance credentials or replay the command
