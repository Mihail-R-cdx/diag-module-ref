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
and Extron IPL T PCS4i outlet on/off actions. Unsupported device actions SHALL
not be reported as successful. PCS4i REBOOT SHALL be unsupported and SHALL NOT
be exposed to the operator.

#### Scenario: Extron routing action
- **WHEN** an operator selects an actionable Extron input/output-1 cell with a connected handler
- **THEN** the handler is asked to route that input to output 1 and the screen schedules a status refresh

#### Scenario: Aten outlet action
- **WHEN** an operator confirms an `on`, `off`, or `reboot` action for an Aten outlet
- **THEN** the application executes the matching handler action through the background PDU command path, reports its outcome, and refreshes after success

#### Scenario: PCS4i outlet action
- **WHEN** an operator confirms an `on` or `off` action for a PCS4i outlet from 1 through 4
- **THEN** the application executes the matching PCS4i handler action through the background PDU command path and reports its outcome

#### Scenario: PCS4i reboot is not available
- **GIVEN** selected device is Extron IPL T PCS4i
- **WHEN** `PDUScreen` renders supported outlet controls
- **THEN** ON is available
- **AND** OFF is available
- **AND** REBOOT is not available to the operator

#### Scenario: Unsupported SIP update
- **WHEN** a codec handler does not implement SIP server update
- **THEN** the operation reports an unsupported or failed outcome rather than claiming the setting changed

## ADDED Requirements

### Requirement: Shared PDU screen with device-specific capabilities
The application SHALL use the existing `PDUScreen` for Aten PE8208AV and
Extron IPL T PCS4i. The screen SHALL render the outlet records returned by the
active handler/worker and SHALL not hard-code the PCS4i outlet count to Aten's
eight-outlet layout. Device protocols SHALL remain in device-specific handlers.
Control rendering SHALL use selected-model capabilities rather than assuming
all PDU models expose the same operation set.

#### Scenario: PCS4i uses existing PDU screen
- **WHEN** an operator refreshes `Extron IPL T PCS4i`
- **THEN** the application displays the existing `PDUScreen`
- **AND** no PCS4i-specific screen is created

#### Scenario: PCS4i renders four outlets
- **WHEN** the PCS4i worker returns four outlet records
- **THEN** `PDUScreen` displays exactly four outlet rows
- **AND** each row exposes ON and OFF controls only

#### Scenario: Aten remains on the same PDU screen
- **WHEN** an operator refreshes `Aten PE8208AV`
- **THEN** the application continues to display Aten outlet data on `PDUScreen` with its existing behavior

#### Scenario: Aten capabilities are preserved
- **GIVEN** selected device is a supported Aten PDU
- **WHEN** operator controls an outlet
- **THEN** existing ON/OFF/REBOOT capabilities remain available
- **AND** PCS4i capability restrictions do not alter Aten protocol semantics

### Requirement: PCS4i PDU handler contract
The PCS4i handler SHALL expose a PDU-compatible operation surface consisting of
`get_outlets_status()`, `get_device_info()`, `turn_on(outlet_number)`, and
`turn_off(outlet_number)`. The PCS4i handler SHALL NOT expose a supported
`reboot(outlet_number)` operation. The handler SHALL return exactly four PCS4i
outlet records and SHALL reject outlet numbers outside 1 through 4 before
sending any command.

#### Scenario: PCS4i status shape
- **WHEN** PCS4i outlet status is read successfully
- **THEN** the handler returns four records containing outlet number, normalized status, and display name

#### Scenario: PCS4i device info shape
- **WHEN** PCS4i device information is read successfully
- **THEN** the handler returns at least model, manufacturer, IP address, and connection status fields suitable for the PDU screen

#### Scenario: PCS4i rejects invalid outlet number
- **WHEN** a caller requests PCS4i outlet 0 or outlet 5
- **THEN** the handler rejects the request before sending any Telnet command

#### Scenario: PCS4i handler has no reboot command
- **WHEN** application dispatch builds PCS4i supported operations
- **THEN** the supported PCS4i operation set excludes REBOOT

### Requirement: PCS4i authoritative Telnet protocol
PCS4i Telnet SHALL be authoritative for connection, session readiness, device
identity, outlet state reads, outlet ON, outlet OFF, and final state readback.
The handler SHALL use the confirmed SIS commands and response semantics.

For identity/session metadata, `1I<CR>` SHALL read model, `2I<CR>` SHALL read
description, `N<CR>` SHALL read part number, `Q<CR>` SHALL read firmware, and
`<ESC>CK<CR>` SHALL read session security level. For outlet `N` in 1..4,
`<ESC>NPC<CR>` SHALL be authoritative power-state readback where `0<CR><LF>`
means OFF and `1<CR><LF>` means ON. `<ESC>NPS<CR>` SHALL be treated only as
current/reference threshold state. ON SHALL send `<ESC>N*1PC<CR>` and OFF SHALL
send `<ESC>N*0PC<CR>`. Final state after ON or OFF SHALL be determined through
a separate authoritative `PC` readback, not acknowledgement alone.

#### Scenario: Model query
- **WHEN** PCS4i handler sends `1I<CR>`
- **THEN** response `IPL T PCS4i` identifies the model

#### Scenario: Firmware query
- **WHEN** PCS4i handler sends `Q<CR>`
- **THEN** the firmware response is parsed as firmware metadata

#### Scenario: Security-level query
- **WHEN** PCS4i handler sends `<ESC>CK<CR>`
- **THEN** response `11<CR><LF>` is User level
- **AND** response `12<CR><LF>` is Administrator level

#### Scenario: PC returns OFF
- **WHEN** PCS4i outlet `PC` readback returns `0<CR><LF>`
- **THEN** the outlet status is normalized as OFF

#### Scenario: PC returns ON
- **WHEN** PCS4i outlet `PC` readback returns `1<CR><LF>`
- **THEN** the outlet status is normalized as ON

#### Scenario: PS is not power state
- **WHEN** PCS4i `PS` readback returns `0`, `1`, or `2`
- **THEN** that value is interpreted only as current/reference threshold state
- **AND** it is not used as authoritative ON/OFF status

#### Scenario: Outlet number outside range is rejected
- **WHEN** PCS4i outlet number is less than 1 or greater than 4
- **THEN** the request is rejected before Telnet network I/O

#### Scenario: ON command grammar
- **WHEN** PCS4i outlet 1 is turned ON
- **THEN** the command bytes are `<ESC>1*1PC<CR>`
- **AND** acknowledgement `Cpn1 Ppc1<CR><LF>` is accepted as command acknowledgement

#### Scenario: OFF command grammar
- **WHEN** PCS4i outlet 1 is turned OFF
- **THEN** the command bytes are `<ESC>1*0PC<CR>`
- **AND** acknowledgement `Cpn1 Ppc0<CR><LF>` is accepted as command acknowledgement

#### Scenario: Authoritative readback after state change
- **WHEN** PCS4i ON or OFF acknowledgement is received
- **THEN** final outlet state is read through a separate `<ESC>NPC<CR>` query

### Requirement: PCS4i HTTP outlet-name enrichment
HTTP SHALL be used only as read-only enrichment for the four PCS4i outlet
display names after authoritative Telnet status succeeds. The confirmed name
representation is `xName1`, `xName2`, `xName3`, and `xName4`, mapped to outlets
1 through 4. A completed implementation SHALL include a verified HTTP
name-loading GET path that actually returns these variables. If the exact path
has not been confirmed from retained evidence, production parser
implementation SHALL remain incomplete until that path is confirmed.

HTTP SHALL NOT be authoritative for outlet power state. When the implemented
HTTP request fails at runtime, returns HTTP 401/403, returns an unsupported or
malformed response, or lacks a usable non-empty name for a specific outlet, the
handler SHALL preserve Telnet outlet status and use safe fallback names for
affected outlets. The live discovered no-auth HTTP behavior SHALL be treated as
device/configuration-specific evidence, not a universal PCS4i rule.

#### Scenario: All names available
- **WHEN** HTTP name response contains usable `xName1`, `xName2`, `xName3`, and `xName4`
- **THEN** all four returned outlet names are used

#### Scenario: One name missing
- **WHEN** one `xNameN` value is missing or empty
- **THEN** fallback name is used only for that outlet
- **AND** other usable names are retained

#### Scenario: Malformed response
- **WHEN** HTTP name response is malformed
- **THEN** Telnet status is retained
- **AND** fallback names are used

#### Scenario: HTTP unavailable
- **WHEN** HTTP name loading is unavailable or times out
- **THEN** Telnet status is retained
- **AND** fallback names are used

#### Scenario: HTTP 401 or 403
- **WHEN** HTTP name loading returns HTTP 401 or HTTP 403
- **THEN** no credential fallback is authorized
- **AND** no Telnet `AuthenticationError` is produced
- **AND** Telnet status is retained

#### Scenario: Verified no-auth device
- **WHEN** the tested PCS4i configuration serves names without HTTP credentials
- **THEN** the read succeeds without HTTP credentials
- **AND** this does not require every PCS4i configuration to be no-auth
