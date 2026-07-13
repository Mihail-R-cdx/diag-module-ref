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
