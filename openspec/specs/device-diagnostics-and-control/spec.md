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

### Requirement: Model-specific interactive codec session paths
The shared interactive controller SHALL preserve the supported transports,
session artifacts, and operation boundaries of Huawei TE20, Huawei TE40,
CloudLink Bar 310, and Polycom RPG 310. A model SHALL use only its supported
interactive functions, and functions on a separate worker path SHALL remain
separate unless explicitly listed.

#### Scenario: Huawei TE20 interactive session
- **WHEN** TE20 performs live audio, sleep/Wake, volume, mute, presentation, or call-log work
- **THEN** it uses saved-first HTTP:80 and runtime-supported HTTPS:443 candidates with one credential
- **AND** recovery replaces invalid Session ID, cookie, CSRF, and transport state as one handler unit

#### Scenario: Huawei TE40 interactive session
- **WHEN** TE40 performs live audio, sleep-related presentation preparation, volume, mute, presentation, or call-log work
- **THEN** it uses saved-first HTTPS:443 and HTTP:80 candidates with one credential
- **AND** recovery replaces invalid opener, cookie, Session ID, CSRF, and browser-session state as one handler unit

#### Scenario: CloudLink Bar 310 interactive session
- **WHEN** Bar 310 performs sleep-related presentation preparation, volume, mute/gain, presentation, or call-log work
- **THEN** it uses HTTPS:443 with one credential and one Basic-auth session, cookie, and CSRF context
- **AND** call-log reads use the recovered token through the required `X-Access-Token` header

#### Scenario: Polycom interactive controls
- **WHEN** Polycom performs volume, mute, or presentation work
- **THEN** its serialized shared handler uses HTTPS:443 login and the same credential for its lazy SSH:22 control session
- **AND** failure of either sub-session follows the bounded interactive recovery contract

#### Scenario: Polycom call log remains separate
- **WHEN** the operator loads the Polycom call log
- **THEN** the existing short-lived Polycom call-log worker remains the owner of that operation
- **AND** it is not routed through the Huawei/shared call-log session path

### Requirement: Recovered interactive feature availability
A confirmed invalid session in one shared interactive handler SHALL be recovered
through the common controller rather than through feature-specific reconnect
logic. After successful recovery, read-only functions SHALL resume according to
their replay policy and state-changing functions SHALL follow reconciliation.
An unsupported or failed operation SHALL not be reported as successful.

#### Scenario: Live audio recovers after session invalidation
- **WHEN** TE20 or TE40 live-audio polling encounters an invalid session and reconnect succeeds
- **THEN** one replay updates microphone and codec-output levels without a modal failure dialog

#### Scenario: Wake uses the recovered path
- **WHEN** TE20 Wake loses its session and reconnect succeeds
- **THEN** sleep state is read before Wake is confirmed or sent again

#### Scenario: Huawei call log uses recovered session
- **WHEN** a Huawei call-log read detects an invalid cached session
- **THEN** the shared controller reconnects once and replays that read once

#### Scenario: Bar 310 remains regression-free
- **WHEN** Bar 310 executes supported interactive operations without session failure
- **THEN** the operation uses one HTTPS profile and retains its current successful behavior

#### Scenario: Polycom controls remain regression-free
- **WHEN** Polycom executes a supported interactive control without session failure
- **THEN** it uses the existing HTTPS/SSH command semantics and sends the state-changing command no more than once
