# device-diagnostics-and-control Specification

## Purpose
TBD - created by archiving change bootstrap-openspec-baseline. Update Purpose after archive.
## Requirements
### Requirement: Supported production device diagnostics
The application SHALL provide production GUI diagnostic paths for Huawei TE20,
Huawei TE40, CloudLink Bar 310, Polycom RPG 310, Extron IN1804, Aten
PE8208AV, and Biamp Tesira Forte CI only where those devices are connected to
the main-window dispatch. Each diagnostic path SHALL obtain device data through
its worker/handler path and present parser-normalized data on the corresponding
screen.

#### Scenario: Codec diagnostic refresh
- **WHEN** an operator refreshes a supported codec with a successful device response
- **THEN** the codec screen receives normalized diagnostic data including the target IP and available device status values

#### Scenario: Matrix or PDU diagnostic refresh
- **WHEN** an operator refreshes Extron IN1804 or Aten PE8208AV successfully
- **THEN** the matrix or PDU screen receives the parsed routing or outlet data for that device

### Requirement: Device-specific diagnostic transports
The diagnostic paths SHALL preserve their current protocol boundaries: TE20
uses its HTTP profile and optionally a ready HTTPS stack; TE40 attempts HTTPS
and falls back to HTTP; Bar 310 uses its Huawei web/API session; Polycom uses
HTTPS status with SSH enrichment; Extron uses its handler transport sequence;
and Aten uses its HTTPS API path. A protocol fallback SHALL be observable in
the worker/handler outcome and SHALL not be represented as a different device.

#### Scenario: TE40 HTTPS fallback
- **WHEN** TE40 HTTPS diagnostic connection fails and its HTTP fallback succeeds
- **THEN** the worker returns the HTTP connection profile with the parsed diagnostic data

#### Scenario: Polycom enrichment is unavailable
- **WHEN** Polycom HTTPS status succeeds but SSH enrichment fails
- **THEN** the available HTTPS diagnostic data remains usable and the enrichment failure is reported through the worker path

### Requirement: Limited device control
The GUI SHALL expose only the control operations implemented by the selected
device path: codec presentation, audio/microphone operations, supported SIP
server actions, Extron routing to output 1, and Aten outlet on/off/reboot
actions. Unsupported device actions SHALL not be reported as successful.

#### Scenario: Extron routing action
- **WHEN** an operator selects an actionable Extron input/output-1 cell with a connected handler
- **THEN** the handler is asked to route that input to output 1 and the screen schedules a status refresh

#### Scenario: Aten outlet action
- **WHEN** an operator confirms an `on`, `off`, or `reboot` action for an Aten outlet
- **THEN** the application executes the matching handler action, reports its outcome, and refreshes after success

#### Scenario: Unsupported SIP update
- **WHEN** a codec handler does not implement SIP server update
- **THEN** the operation reports an unsupported or failed outcome rather than claiming the setting changed
