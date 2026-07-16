## MODIFIED Requirements

### Requirement: Supported production device diagnostics
The application SHALL provide production GUI diagnostic paths for Huawei TE20,
Huawei TE40, CloudLink Bar 310, Polycom RPG 310, Extron IN1804, Aten
PE8208AV, Extron IPL T PCS4i, and Biamp Tesira Forte CI only where those
devices are connected to the main-window dispatch. Each diagnostic path SHALL
obtain device data through its worker/handler path and present
parser-normalized or handler-normalized data on the corresponding screen.

#### Scenario: Codec diagnostic refresh
- **WHEN** an operator refreshes a supported codec with a successful device response
- **THEN** the codec screen receives normalized diagnostic data including the target IP and available device status values

#### Scenario: Matrix or PDU diagnostic refresh
- **WHEN** an operator refreshes Extron IN1804, Aten PE8208AV, or Extron IPL T PCS4i successfully
- **THEN** the matrix or PDU screen receives the parsed routing or outlet data for that device

#### Scenario: PCS4i power-control category
- **WHEN** the operator opens the device selector
- **THEN** `Extron IPL T PCS4i` is listed under the `Управление питанием` category

### Requirement: Device-specific diagnostic transports
The diagnostic paths SHALL preserve their current protocol boundaries: TE20
uses its HTTP profile and optionally a ready HTTPS stack; TE40 attempts HTTPS
and falls back to HTTP; Bar 310 uses its Huawei web/API session; Polycom uses
HTTPS status with SSH enrichment; Extron IN1804 uses its handler transport
sequence; Aten uses its HTTPS API path; and Extron IPL T PCS4i uses Telnet for
authoritative outlet status/control plus required HTTP outlet-name enrichment.
A protocol fallback or enrichment failure SHALL be observable in the
worker/handler outcome and SHALL not be represented as a different device.

#### Scenario: TE40 HTTPS fallback
- **WHEN** TE40 HTTPS diagnostic connection fails and its HTTP fallback succeeds
- **THEN** the worker returns the HTTP connection profile with the parsed diagnostic data

#### Scenario: Polycom enrichment is unavailable
- **WHEN** Polycom HTTPS status succeeds but SSH enrichment fails
- **THEN** the available HTTPS diagnostic data remains usable and the enrichment failure is reported through the worker path

#### Scenario: PCS4i HTTP outlet names are unavailable at runtime
- **WHEN** PCS4i Telnet outlet status succeeds and the implemented HTTP outlet-name path fails at runtime
- **THEN** the worker returns the four Telnet outlet states with safe fallback outlet names
- **AND** the HTTP failure is not represented as a failed Telnet status read or a different device

### Requirement: Limited device control
The GUI SHALL expose only the control operations implemented by the selected
device path: codec presentation, audio/microphone operations, supported SIP
server actions, Extron routing to output 1, Aten outlet on/off/reboot actions,
and Extron IPL T PCS4i outlet on/off/reboot actions. Unsupported device
actions SHALL not be reported as successful.

#### Scenario: Extron routing action
- **WHEN** an operator selects an actionable Extron input/output-1 cell with a connected handler
- **THEN** the handler is asked to route that input to output 1 and the screen schedules a status refresh

#### Scenario: Aten outlet action
- **WHEN** an operator confirms an `on`, `off`, or `reboot` action for an Aten outlet
- **THEN** the application executes the matching handler action through the background PDU command path, reports its outcome, and refreshes after success

#### Scenario: PCS4i outlet action
- **WHEN** an operator confirms an `on`, `off`, or `reboot` action for a PCS4i outlet from 1 through 4
- **THEN** the application executes the matching PCS4i handler action through the background PDU command path and reports its outcome

#### Scenario: Unsupported SIP update
- **WHEN** a codec handler does not implement SIP server update
- **THEN** the operation reports an unsupported or failed outcome rather than claiming the setting changed

## ADDED Requirements

### Requirement: Shared PDU screen with device-specific handlers
The application SHALL use the existing `PDUScreen` for Aten PE8208AV and
Extron IPL T PCS4i. The screen SHALL render the outlet records returned by the
active handler/worker and SHALL not hard-code the PCS4i outlet count to Aten's
eight-outlet layout. Device protocols SHALL remain in device-specific handlers.

#### Scenario: PCS4i uses existing PDU screen
- **WHEN** an operator refreshes `Extron IPL T PCS4i`
- **THEN** the application displays the existing `PDUScreen`
- **AND** no PCS4i-specific screen is created

#### Scenario: PCS4i renders four outlets
- **WHEN** the PCS4i worker returns four outlet records
- **THEN** `PDUScreen` displays exactly four outlet rows with on, off, and reboot controls

#### Scenario: Aten remains on the same PDU screen
- **WHEN** an operator refreshes `Aten PE8208AV`
- **THEN** the application continues to display Aten outlet data on `PDUScreen` with its existing behavior

### Requirement: PCS4i PDU handler contract
The PCS4i handler SHALL expose a PDU-compatible operation surface consisting of
`get_outlets_status()`, `get_device_info()`, `turn_on(outlet_number)`,
`turn_off(outlet_number)`, and `reboot(outlet_number)`. The handler SHALL
return exactly four PCS4i outlet records and SHALL reject outlet numbers
outside 1 through 4 before sending any command.

#### Scenario: PCS4i status shape
- **WHEN** PCS4i outlet status is read successfully
- **THEN** the handler returns four records containing outlet number, normalized status, and display name

#### Scenario: PCS4i device info shape
- **WHEN** PCS4i device information is read successfully
- **THEN** the handler returns at least model, manufacturer, IP address, and connection status fields suitable for the PDU screen

#### Scenario: PCS4i rejects invalid outlet number
- **WHEN** a caller requests PCS4i outlet 0 or outlet 5
- **THEN** the handler rejects the request before sending any Telnet command

### Requirement: PCS4i authoritative Telnet and required HTTP name enrichment
PCS4i Telnet SHALL be authoritative for connection, authentication, outlet
state reads, and outlet control. HTTP SHALL be used only as read-only
enrichment for the four outlet display names after Telnet status succeeds. A
completed implementation SHALL include a verified HTTP name-loading path. When
the implemented HTTP request fails at runtime, returns an unsupported or
malformed response, or lacks a usable non-empty name for a specific outlet, the
handler SHALL preserve Telnet outlet status and use safe fallback names for
affected outlets.

#### Scenario: Telnet controls status and power
- **WHEN** PCS4i refresh or outlet control runs
- **THEN** Telnet is the transport used for outlet state and state-changing commands

#### Scenario: HTTP names enrich successful Telnet status
- **WHEN** Telnet status returns four outlets and HTTP returns verified names
- **THEN** the handler applies the names to the corresponding outlet records

#### Scenario: HTTP name loading path is mandatory
- **WHEN** PCS4i implementation is considered complete
- **THEN** it includes a real HTTP name-loading path whose endpoint, request format, response format, and authentication/session mechanism were verified from allowed protocol evidence

#### Scenario: Missing HTTP names use fallback
- **WHEN** an outlet name is unavailable
- **THEN** the handler uses `Розетка N` for that outlet

#### Scenario: HTTP protocol is not guessed
- **WHEN** the HTTP endpoint, response format, or authentication mechanism has not been verified from code, official protocol material, or provided data
- **THEN** the implementation is incomplete/blocking rather than disabling HTTP name loading or completing with permanent fallback names

#### Scenario: HTTP failure preserves Telnet status
- **WHEN** Telnet status succeeds and HTTP connection, timeout, authentication, parsing, or unsupported-response failure prevents name enrichment
- **THEN** the handler returns Telnet outlet state with fallback names for the affected outlets
- **AND** the HTTP failure does not change credential selection
