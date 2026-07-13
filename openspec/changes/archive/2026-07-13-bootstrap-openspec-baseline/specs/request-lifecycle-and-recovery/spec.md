## ADDED Requirements

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
device refresh when an authentication failure is classified and additional
credentials remain. It SHALL retain the successful credential index and
connection profile for the applicable device/IP context when the worker returns
them.

#### Scenario: Retry after authentication failure
- **WHEN** a current worker reports an authentication failure and another credential exists
- **THEN** the main window advances the credential index and starts the applicable refresh path again

#### Scenario: Successful profile retained
- **WHEN** a worker result identifies a successful credential index or connection profile
- **THEN** subsequent actions for that device/IP can use the retained context

### Requirement: Persistent resource release
The application SHALL disconnect the persistent Extron handler on window close
and reset reusable codec volume sessions when the application window closes.

#### Scenario: Application window closes after matrix use
- **WHEN** the window receives its close event with a persistent Extron handler
- **THEN** it disconnects that handler before delegating the close event
