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

#### Scenario: Stale bulk completion arrives after a newer context
- **WHEN** a prior bulk PDU sequence emits result, error, or completion after the operator has changed PDU context
- **THEN** the prior callback does not change the current outlet table, dialogs, locked controls, credential memory, or refresh state

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
credential candidates. Credential fallback for bulk SHALL be allowed only after
a structured confirmed `AuthenticationError` before the first state-changing
outlet command has been sent or may have been sent. After mutation begins, the
bulk sequence SHALL NOT restart with another credential, repeat completed
outlets, or start again from the beginning.

#### Scenario: One credential per bulk sequence attempt
- **WHEN** a bulk PDU sequence attempt starts
- **THEN** it uses one assigned credential for the whole sequence attempt
- **AND** the worker and handler do not iterate credential candidates

#### Scenario: Authentication failure before mutation
- **WHEN** a structured `AuthenticationError` occurs before the first state-changing outlet send
- **AND** another credential candidate remains
- **THEN** the application-owned credential policy may start a new bulk sequence attempt with the next credential
- **AND** no outlet command from the failed attempt was sent

#### Scenario: No credential restart after mutation
- **WHEN** at least one state-changing outlet command has been sent or may have been sent
- **AND** a later authentication, connection, protocol, or indeterminate failure occurs
- **THEN** the application does not restart the bulk sequence with another credential
- **AND** completed outlet sub-operations are not repeated

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
not as multiple concurrent workers and not as a GUI loop over
`control_pdu_outlet(...)`. The sequence SHALL acquire and release handler or
session resources according to the chosen worker boundary and SHALL clean up on
success, partial completion, stale termination, or failure.

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
command/target when applicable, and ordered outlet sequence when applicable.
This applies to PCS4i refresh, PCS4i ON/OFF commands, PCS4i bulk ON/OFF, Aten
refresh, Aten ON/OFF/REBOOT commands, and Aten bulk ON/OFF. The
application/composition layer SHALL own the current PDU generation and
increment or replace it when relevant PDU context changes.

Application dispatch SHALL validate that the selected model supports the
requested operation before handler acquisition. A queued operation SHALL recheck
the captured descriptor against the current application-owned context
immediately before handler acquisition. A bulk sequence SHALL also recheck
currentness before starting each next outlet sub-operation. A stale queued
operation SHALL be dropped without creating a handler, opening Telnet, HTTP, or
Aten transport, or sending a command. A bulk sequence that becomes stale
between outlets SHALL stop before the next outlet command.

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
one initial command. A bulk PDU operation SHALL be treated as one
orchestration sequence composed of multiple independent outlet
sub-operations. Each outlet sub-operation SHALL receive its own existing
bounded safety budget. The safety budget for one outlet sub-operation SHALL
not apply to commands for another outlet in the same bulk sequence.

Completed outlet sub-operations SHALL NOT be repeated because a later outlet
fails. Completed outlet sub-operations SHALL NOT be rolled back. Bulk PDU
operations SHALL NOT be transactional. A terminal failure, command rejection,
indeterminate outcome, connection/protocol failure, or terminal authentication
failure for one outlet SHALL stop the sequence and prevent commands to
remaining outlets.

#### Scenario: Bulk outlet safety budget is per outlet
- **WHEN** a bulk ON or OFF sequence processes outlet N
- **THEN** outlet N uses the existing bounded PDU ON/OFF safety policy
- **AND** its send, readback, reconciliation, and confirmation budget does not consume or authorize the budget for outlet N+1

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
