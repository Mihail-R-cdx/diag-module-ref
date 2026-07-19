## MODIFIED Requirements

### Requirement: Background diagnostic execution
Network diagnostic refresh operations SHALL execute through QRunnable workers
submitted to `QThreadPool` and SHALL return progress, status, result, error,
connection, and completion information through worker signals. Workers SHALL
disconnect handlers in their cleanup paths when a handler was created. PDU
refresh paths, including Extron IPL T PCS4i Telnet status reads and HTTP
outlet-name enrichment, SHALL follow this background execution boundary.
Worker module decomposition SHALL preserve these background execution,
cleanup, and signal lifecycle contracts without moving network I/O into the
Qt GUI thread.

#### Scenario: Worker succeeds
- **WHEN** a device worker connects, collects status, and parses a response
- **THEN** it emits a result for the GUI and releases its handler before emitting completion

#### Scenario: Worker fails
- **WHEN** a device worker encounters an authentication or connection exception
- **THEN** it emits a classified error and emits completion after its cleanup path

#### Scenario: PCS4i refresh stays off the GUI thread
- **WHEN** PCS4i refresh performs Telnet connect/read work or HTTP outlet-name enrichment
- **THEN** that network work runs in a background worker rather than the Qt GUI thread

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
refresh-button state.

For PDU operations, including PCS4i refresh, PCS4i ON/OFF commands, Aten
refresh, and Aten ON/OFF/REBOOT commands, the application/composition layer
SHALL own the current operation context generation. Background workers SHALL
NOT read Qt widgets, including `device_combo`, `ip_entry`, `PDUScreen`, or
other QWidget properties, to decide whether a PDU operation is current.
Worker module decomposition SHALL NOT move request-context ownership into
focused worker modules or the `core.worker` facade.

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

#### Scenario: Decomposed worker does not own request generation
- **WHEN** a worker is moved into a focused module
- **THEN** request generation, stale-result suppression, and credential memory updates remain owned by the application/composition layer
