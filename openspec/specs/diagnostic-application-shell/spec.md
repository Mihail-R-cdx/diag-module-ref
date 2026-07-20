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
