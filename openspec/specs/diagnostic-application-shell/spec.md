# diagnostic-application-shell Specification

## Purpose
TBD - created by archiving change bootstrap-openspec-baseline. Update Purpose after archive.
## Requirements
### Requirement: Desktop diagnostic application startup
The application SHALL start from `main.py`, create a PyQt5 `QApplication`,
apply the configured theme, show `VCSDiagnosticApp`, and enter the Qt event
loop. Unhandled main-thread exceptions SHALL be appended to `app_crash.log` and
shown in a critical dialog when a QApplication exists; unhandled Python-thread
exceptions SHALL be appended to the same log.

#### Scenario: Normal application launch
- **WHEN** `main.py` is executed in an environment with its GUI dependencies
- **THEN** the diagnostic main window is constructed and shown with the Qt event loop running

#### Scenario: Unhandled main-thread exception
- **WHEN** the configured main-thread exception hook receives an exception
- **THEN** it appends a timestamped traceback to `app_crash.log` and presents a critical dialog when possible

### Requirement: Device selection and refresh input validation
The main window SHALL expose only device models wired into `device_to_screen`
as selectable diagnostic targets and SHALL route each target to its configured
codec, matrix, PDU, or audio-DSP screen. A refresh request SHALL reject an
empty or malformed IPv4 address and SHALL stop before starting a device worker
when preliminary reachability validation fails.

#### Scenario: Valid supported device refresh
- **WHEN** an operator selects a mapped device, enters a valid reachable IPv4 address, and refreshes
- **THEN** the matching screen is selected, enters loading state, and the device-specific refresh path starts

#### Scenario: Invalid refresh input
- **WHEN** the IP field is empty, malformed, or fails preliminary reachability validation
- **THEN** the application displays a warning and does not start a diagnostic worker

### Requirement: User-visible request state
The GUI SHALL expose loading, connected, authentication-error, request-error,
unavailable, disabled, and command states through text and non-color cues. It
SHALL disable the refresh action while an active refresh is pending and restore
it when the current request finishes or fails.

#### Scenario: Current request completes
- **WHEN** the active worker emits completion after a refresh
- **THEN** the refresh action is restored and the screen retains the state set by the current request outcome

#### Scenario: Authentication failure
- **WHEN** a current request exhausts its available credentials
- **THEN** the application leaves loading state, surfaces an authentication outcome, and re-enables refresh

### Requirement: MatrixScreen intent and display boundary
`MatrixScreen` SHALL be a Matrix UI boundary that renders Matrix data and
publishes non-secret user intents. It SHALL NOT own credential candidate
selection, credential indexes, handler acquisition, persistent handler/session
state, transport lifecycle, retry policy, credential fallback, keepalive, or
direct Matrix network I/O.

Matrix route and refresh user actions SHALL cross the screen boundary as
non-secret intent or callback data. Qt signals or callbacks from
`MatrixScreen` SHALL NOT carry credential values, credential candidate lists,
handler objects, session objects, transport objects, cookies/tokens, or other
secret/session material.

#### Scenario: Route click emits intent only
- **WHEN** the operator clicks a Matrix routing cell
- **THEN** `MatrixScreen` publishes a route intent for the selected Matrix input/output context
- **AND** it does not call `ExtronIN1804Handler.set_connection()` directly
- **AND** it does not acquire or reuse a handler/session object

#### Scenario: Quick refresh is not screen-owned network I/O
- **WHEN** Matrix route status needs to be refreshed after a route action
- **THEN** `MatrixScreen` requests or receives the update through the Matrix application boundary
- **AND** it does not call `ExtronIN1804Handler.get_connections()` directly

#### Scenario: Screen does not own credentials
- **WHEN** a Matrix route or refresh intent is submitted
- **THEN** `MatrixScreen` does not read or mutate credential candidate lists or successful credential indexes
- **AND** credential ownership remains outside the screen boundary

#### Scenario: Screen signal payloads are secret-free
- **WHEN** `MatrixScreen` emits a route or refresh signal/callback
- **THEN** the payload contains no credential values, credential candidate lists, handler objects, session objects, cookies, tokens, or transport objects

#### Scenario: Rendering remains screen-owned
- **WHEN** the active Matrix controller accepts current Matrix data
- **THEN** `MatrixScreen` remains responsible for rendering the routing table, current connection, signal/HDCP indicators, and device information

### Requirement: PDUScreen intent and display boundary
`PDUScreen` SHALL be a PDU UI boundary that renders accepted PDU device data, outlet records, model capabilities, refresh-lane state, mutation-lane control state, and current busy/loading presentation. It SHALL publish non-secret user intents for refresh, individual outlet mutation, and sequential bulk mutation. It SHALL NOT own credential candidate selection, credential indexes, credential fallback, successful credential memory, worker creation or submission, handler acquisition, request/operation generation authority, refresh lane authority, mutation lane authority, stale operation acceptance, or direct PDU network I/O.

PDU refresh and mutation actions SHALL cross the screen boundary through an explicit signal or callback interface. `PDUScreen` SHALL NOT depend on arbitrary parent orchestration methods such as `control_pdu_outlet(...)`, `control_pdu_outlets_bulk(...)`, or `refresh_data()` to execute PDU lifecycle. The screen MAY retain local rendering helpers and confirmation dialogs that are view responsibilities.

Qt signals or callbacks from `PDUScreen` SHALL NOT carry credential values, credential candidate lists, credential dictionaries, handler objects, session objects, transport objects, cookies, Session IDs, CSRF tokens, or other secret or session material.

#### Scenario: Individual outlet action emits intent only
- **WHEN** the operator confirms an individual PDU outlet action
- **THEN** `PDUScreen` publishes the outlet number and requested non-secret operation through the explicit PDU intent boundary
- **AND** it does not acquire a handler, create a worker, select a credential candidate, or call an arbitrary parent outlet-control method

#### Scenario: Bulk action emits intent only
- **WHEN** the operator confirms bulk ON or bulk OFF
- **THEN** `PDUScreen` publishes the requested non-secret bulk operation through the explicit PDU intent boundary
- **AND** it does not build credential attempts, create workers, or call an arbitrary parent bulk-control method

#### Scenario: Refresh emits intent only
- **WHEN** the operator requests a PDU status refresh from `PDUScreen`
- **THEN** the screen publishes a refresh intent through the explicit PDU application boundary
- **AND** it does not execute PDU network I/O or directly invoke generic parent refresh orchestration as the PDU lifecycle authority

#### Scenario: Screen does not own PDU operation freshness
- **WHEN** a PDU result, error, progress/status, or completion is associated with an operation context
- **THEN** `PDUScreen` does not decide whether that operation is current from credential state, worker identity, request generation, lane identity, or Qt widget values
- **AND** it renders only state or outcomes accepted by the PDU application lifecycle boundary

#### Scenario: Screen signal payloads are secret-free
- **WHEN** `PDUScreen` emits a refresh, individual mutation, or bulk mutation intent
- **THEN** the payload contains no credential values, credential candidate lists, handler/session objects, cookies, tokens, or transport objects

#### Scenario: Rendering and confirmation remain screen responsibilities
- **WHEN** the active PDU controller accepts current device data or control state
- **THEN** `PDUScreen` remains responsible for rendering device information, dynamic outlet records, capability-driven controls, refresh presentation, and mutation busy/loading presentation
- **AND** implementation may keep individual and bulk confirmation dialogs in the screen without giving it application lifecycle ownership

### Requirement: DMP polling controller composition boundary

`VCSDiagnosticApp` SHALL compose a DMP-specific polling controller as the application lifecycle boundary for Extron DMP 64 Plus meter diagnostics.

The main window SHALL retain global input validation, generic request composition, credential-provider ownership, successful credential memory, global UI state helpers, and rendering integration. It SHALL delegate DMP polling generation, cancellation publication, worker submission/binding, stale callback authority, DMP credential-attempt coordination, first-complete-snapshot success gating, and DMP shutdown/invalidation to the DMP controller.

`AudioDSPScreen` SHALL remain the rendering boundary for accepted DMP data. It SHALL NOT own DMP worker creation, cancellation authority, credential candidate selection, credential fallback, successful credential persistence, handler/session ownership, or stale callback decisions.

The DMP controller SHALL receive only the focused application callbacks/providers required to obtain public model/IP/request context and application-owned credential policy decisions. It SHALL NOT become a generic shell replacement or a generic device lifecycle manager.

#### Scenario: MainWindow routes DMP refresh to the controller
- **WHEN** global refresh validation and generic request setup succeed for `Extron DMP 64 Plus`
- **THEN** `VCSDiagnosticApp` delegates DMP polling startup to the DMP controller
- **AND** it does not directly construct and bind the authoritative DMP worker lifecycle

#### Scenario: MainWindow delegates DMP invalidation
- **WHEN** model, IP, DMP credential context, repeat Refresh, relevant screen lifecycle, or application shutdown supersedes the active DMP context
- **THEN** the shell delegates DMP invalidation/cancellation to the controller
- **AND** it does not maintain a second independent DMP generation authority

#### Scenario: Generic shell callbacks contain no DMP stale policy
- **WHEN** DMP lifecycle extraction is complete
- **THEN** generic device result, error, progress, status, and finished handlers receive only DMP callbacks already accepted by the DMP controller
- **AND** they do not independently evaluate DMP-specific worker context freshness

#### Scenario: Generic shell error handling does not retry DMP credentials
- **WHEN** a DMP worker reports a failure
- **THEN** DMP retry eligibility and candidate advancement are decided at the DMP controller/application credential boundary
- **AND** generic device-error dispatch does not independently restart DMP polling with another candidate

#### Scenario: AudioDSPScreen remains rendering-only for DMP lifecycle
- **WHEN** the DMP controller accepts a current meter snapshot
- **THEN** `AudioDSPScreen` renders the accepted DMP data
- **AND** it does not decide whether the worker/context is current or manage DMP credentials/sessions
