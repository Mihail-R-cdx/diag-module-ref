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
properties, to decide whether an operation is current. Worker module
decomposition SHALL NOT move request-context ownership into focused worker
modules or the `core.worker` facade.

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
