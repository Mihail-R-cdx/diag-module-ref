## MODIFIED Requirements

### Requirement: Background diagnostic execution
Network diagnostic refresh operations SHALL execute through QRunnable workers
submitted to `QThreadPool` and SHALL return progress, status, result, error,
connection, and completion information through worker signals. Workers SHALL
disconnect handlers in their cleanup paths when a handler was created. PDU
refresh paths, including Extron IPL T PCS4i Telnet status reads and HTTP
outlet-name enrichment, SHALL follow this background execution boundary.

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
current screen, outlet table, command state, credential memory, or
refresh-button state.

For PDU operations, including PCS4i refresh, PCS4i ON/OFF commands, Aten
refresh, and Aten ON/OFF/REBOOT commands, the application/composition layer
SHALL own the current operation context generation. Background workers SHALL
NOT read Qt widgets, including `device_combo`, `ip_entry`, `PDUScreen`, or
other QWidget properties, to decide whether a PDU operation is current.

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
- **AND** that cycle includes at most one recovery/reconnect sequence when needed for device-specific authoritative outlet-state readback and at most one normalized authoritative outlet-state decision
- **AND** recovery or reconciliation does not recurse

#### Scenario: PCS4i ON/OFF recovery uses PC readback
- **WHEN** a PCS4i ON or OFF command has ambiguous delivery
- **THEN** reconciliation uses PCS4i Telnet `PC` readback as authoritative outlet-state evidence
- **AND** unavailable, unknown, or conflicting readback returns indeterminate without blind resend

## ADDED Requirements

### Requirement: Background PDU control execution
PDU outlet control operations for Extron IPL T PCS4i and Aten PE8208AV SHALL
execute outside the Qt GUI thread through a shared application-owned background
PDU command execution boundary. The shared boundary SHALL own operation
dispatch, background execution, lifecycle cleanup, stale-operation protection,
model-capability validation, and structured command outcomes. Device-specific
handlers SHALL remain separate, and the boundary SHALL NOT merge Aten wire
protocol, PCS4i Telnet protocol, or PCS4i HTTP protocol.

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

### Requirement: PDU queued operation staleness and capability validation
PDU refresh and command workers SHALL carry an immutable operation descriptor
with operation id, generation, model, IP address, non-secret credential context,
operation type, outlet number when applicable, and desired command/target when
applicable. This applies to PCS4i refresh, PCS4i ON/OFF commands, Aten refresh,
and Aten ON/OFF/REBOOT commands. The application/composition layer SHALL own
the current PDU generation and increment or replace it when relevant PDU
context changes.

Application dispatch SHALL validate that the selected model supports the
requested operation before handler acquisition. A queued operation SHALL recheck
the captured descriptor against the current application-owned context
immediately before handler acquisition. When handler construction/preparation
and first network I/O are separate phases, it SHALL also recheck immediately
before first network I/O. A stale queued operation SHALL be dropped without
creating a handler, opening Telnet, HTTP, or Aten transport, or sending a
command.

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
replay. Ambiguous delivery SHALL allow at most one reconciliation cycle, at most
one normalized authoritative outlet-state decision, and no recursive
recovery/reconciliation. ON/OFF MAY perform at most one controlled absolute
resend only when device-specific readback authoritatively shows the known
pre-command state. The shared PDU command boundary SHALL call a
device-specific handler readback operation and SHALL NOT encode PCS4i Telnet or
Aten status API wire details.

#### Scenario: ON target already applied
- **WHEN** a PDU ON command loses acknowledgement and device-specific authoritative readback shows the outlet is on
- **THEN** the operation reports success without sending ON again

#### Scenario: OFF target still absent
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
