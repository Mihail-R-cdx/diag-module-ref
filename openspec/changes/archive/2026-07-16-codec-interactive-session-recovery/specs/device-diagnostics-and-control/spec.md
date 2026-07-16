## ADDED Requirements

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
