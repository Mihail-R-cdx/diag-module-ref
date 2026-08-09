# device-diagnostics-and-control Specification

## MODIFIED Requirements

### Requirement: Supported production device diagnostics
The application SHALL provide production GUI diagnostic paths for Huawei TE20,
Huawei TE40, CloudLink Bar 310, CloudLink Box 310, Polycom RPG 310, Extron
IN1804, Aten PE8208AV, Extron IPL T PCS4i, Biamp Tesira Forte CI, and Extron
DMP 64 Plus only where those devices are connected to the main-window dispatch.
Each diagnostic path SHALL obtain device data through its worker/handler path and
present parser-normalized or handler-normalized data on the corresponding
screen.

CloudLink Bar 310 and CloudLink Box 310 SHALL remain two distinct exact
application models even though both dispatch through the reviewed shared
`cloudlink_bar_310` lifecycle. Supporting Box 310 SHALL NOT rewrite its accepted
application identity to Bar 310.

#### Scenario: Codec diagnostic refresh
- **WHEN** an operator refreshes a supported codec with a successful device response
- **THEN** the codec screen receives normalized diagnostic data including the target IP and available device status values

#### Scenario: CloudLink Box 310 diagnostic refresh
- **GIVEN** the selected exact application model is `CloudLink Box 310`
- **WHEN** its production diagnostic refresh succeeds through the shared Bar/Box lifecycle
- **THEN** the codec screen receives normalized Box 310 diagnostic data
- **AND** the accepted application model remains exactly `CloudLink Box 310`
- **AND** the operation is not represented as `CloudLink Bar 310`

#### Scenario: Matrix or PDU diagnostic refresh
- **WHEN** an operator refreshes Extron IN1804, Aten PE8208AV, or Extron IPL T PCS4i successfully
- **THEN** the matrix or PDU screen receives the parsed routing or outlet data for that device

#### Scenario: PCS4i power-control category
- **WHEN** the operator opens the device selector
- **THEN** `Extron IPL T PCS4i` is listed under the `Управление питанием` category

#### Scenario: DMP audio-DSP category
- **WHEN** the operator opens the device selector
- **THEN** `Extron DMP 64 Plus` is listed under the `Audio DSP` category next to `Biamp Tesira Forte CI`
- **AND** it routes to the Audio DSP screen path

### Requirement: Device-specific diagnostic transports
The diagnostic paths SHALL preserve their current protocol boundaries: TE20
uses its HTTP profile and optionally a ready HTTPS stack; TE40 attempts HTTPS
and falls back to HTTP; CloudLink Bar 310 and CloudLink Box 310 use the same
existing Huawei web/API session implementation and approved HTTPS:443 profile;
Polycom uses HTTPS status with SSH enrichment; Extron IN1804 uses its handler
transport sequence; Aten uses its HTTPS API path; and Extron IPL T PCS4i uses
Telnet for authoritative outlet status/control plus required HTTP outlet-name
enrichment. A protocol fallback or enrichment failure SHALL be observable in
the worker/handler outcome and SHALL not be represented as a different device.

For the closed Bar/Box 310 protocol family, transport equivalence SHALL NOT
collapse exact application identity, authorize credential sharing, or authorize
retrying one family member as the other.

#### Scenario: TE40 HTTPS fallback
- **WHEN** TE40 HTTPS diagnostic connection fails and its HTTP fallback succeeds
- **THEN** the worker returns the HTTP connection profile with the parsed diagnostic data

#### Scenario: CloudLink Box 310 uses the shared Bar transport boundary
- **GIVEN** the exact application model is `CloudLink Box 310`
- **WHEN** the diagnostic path acquires its supported transport
- **THEN** it uses the same existing Huawei web/API session implementation and HTTPS:443 profile as Bar 310
- **AND** the transport path remains bound to exact `CloudLink Box 310` operation context
- **AND** transport or authentication failure does not switch the model to `CloudLink Bar 310`

#### Scenario: Polycom enrichment is unavailable
- **WHEN** Polycom HTTPS status succeeds but SSH enrichment fails
- **THEN** the available HTTPS diagnostic data remains usable and the enrichment failure is reported through the worker path

#### Scenario: PCS4i HTTP outlet names are unavailable at runtime
- **WHEN** PCS4i Telnet outlet status succeeds and the implemented HTTP outlet-name path fails at runtime
- **THEN** the worker returns the four Telnet outlet states with safe fallback outlet names
- **AND** the HTTP failure is not represented as a failed Telnet status read or a different device

### Requirement: Model-specific interactive codec session paths
The shared interactive controller SHALL preserve the supported transports,
session artifacts, and operation boundaries of Huawei TE20, Huawei TE40,
CloudLink Bar 310, CloudLink Box 310, and Polycom RPG 310. A model SHALL use
only its supported interactive functions, and functions on a separate worker
path SHALL remain separate unless explicitly listed.

CloudLink Bar 310 and CloudLink Box 310 SHALL use the same reviewed
`CloudLinkBar310Handler` protocol implementation for supported interactive
operations while retaining their exact assigned application model in interactive
context. Shared protocol capability SHALL NOT authorize Bar/Box model aliasing,
credential sharing, or model switching during recovery.

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

#### Scenario: CloudLink Box 310 interactive session
- **GIVEN** the interactive context model is exactly `CloudLink Box 310`
- **WHEN** Box 310 performs an operation supported by the existing Bar 310 interactive capability
- **THEN** it uses HTTPS:443 through the same `CloudLinkBar310Handler` session semantics
- **AND** the interactive context remains exactly `CloudLink Box 310`
- **AND** recovery does not retry or relabel the operation as `CloudLink Bar 310`

#### Scenario: Polycom interactive controls
- **WHEN** Polycom performs volume, mute, or presentation work
- **THEN** its serialized shared handler uses HTTPS:443 login and the same credential for its lazy SSH:22 control session
- **AND** failure of either sub-session follows the bounded interactive recovery contract

#### Scenario: Polycom call log remains separate
- **WHEN** the operator loads the Polycom call log
- **THEN** the existing short-lived Polycom call-log worker remains the owner of that operation
- **AND** it is not routed through the Huawei/shared call-log session path

### Requirement: Related-codec status reuses supported codec protocol boundaries

Automatic related-codec status SHALL use the existing supported handler and transport
boundaries for Huawei TE20, Huawei TE40, CloudLink Bar 310, CloudLink Box 310, and
Polycom RPG 310. It SHALL reuse existing status methods and parser normalization where
available and SHALL NOT invent a protocol from `source_model`, a manufacturer substring,
or an unsupported inventory record.

For exact `CloudLink Box 310`, the related-codec path SHALL reuse the existing Bar 310
call/presentation command semantics and HTTPS:443 protocol boundary while keeping exact
Box application identity, Box credential selection, and Box successful connection memory.
Protocol equivalence SHALL NOT authorize implicit Bar credential/profile reuse or model
switching.

The focused related-codec adapter SHALL expose only normalized call and presentation status
to PDU presentation. Complete raw status and model-specific session artifacts SHALL remain
inside the handler/session/adapter boundary.

#### Scenario: Huawei related codec is resolved

- **WHEN** the inventory resolves an exact supported Huawei codec model/IP
- **THEN** automatic status uses that model's existing supported handler and saved-first transport order
- **AND** normalized call and presentation status are derived through the existing parser or an equivalent focused adapter

#### Scenario: CloudLink Box 310 related codec is resolved

- **GIVEN** inventory resolution returns exact `codec_diagnostic_model = CloudLink Box 310`
- **WHEN** automatic related-codec status is requested
- **THEN** it uses the shared Bar protocol handler and existing Bar call/presentation semantics over HTTPS:443
- **AND** credentials and saved connection state are resolved for exact `CloudLink Box 310` and codec IP
- **AND** accepted presentation remains exactly `CloudLink Box 310`
- **AND** the operation is not retried or relabeled as `CloudLink Bar 310`

#### Scenario: Polycom related codec is resolved

- **WHEN** the inventory resolves exact `Polycom RPG 310`
- **THEN** automatic status uses the existing Polycom status/session protocol boundary
- **AND** it does not reuse or alter the user codec interactive session

#### Scenario: Inventory codec is unsupported

- **WHEN** a canonical `video_codec` record has no exact supported VCS `diagnostic_model`
- **THEN** the related-codec section reports unsupported
- **AND** no handler is guessed or constructed from source text
