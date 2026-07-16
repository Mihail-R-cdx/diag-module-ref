## MODIFIED Requirements

### Requirement: Redacted protocol diagnostics
Handler command logging and worker error handling SHALL redact known usernames,
passwords, authentication tokens, sensitive request payloads, and sensitive
response bodies before they are emitted to terminal/debug output. New tests and
new documentation SHALL use synthetic credentials only. PCS4i Telnet
authentication, Telnet commands, HTTP outlet-name enrichment, PDU command
outcomes, and public diagnostics SHALL never expose the real assigned password.

#### Scenario: Handler logs a credential-bearing request
- **WHEN** a supported Huawei, Polycom, Aten, or PCS4i handler records a request containing credentials or a token
- **THEN** the recorded terminal message replaces sensitive content with a redaction marker

#### Scenario: Worker reports a credential-bearing exception
- **WHEN** a worker catches an exception whose text contains the credential it used
- **THEN** its emitted error message masks that credential before reaching the GUI path

#### Scenario: PCS4i prompt contains asterisks
- **WHEN** PCS4i emits `Password:**********************`
- **THEN** public diagnostics may include the device-emitted asterisks only when useful
- **AND** the actual password sent by the application remains redacted everywhere

## ADDED Requirements

### Requirement: PCS4i offline protocol validation
PCS4i protocol behavior SHALL be verified with offline tests using synthetic
Telnet and HTTP transports. Normal automated verification SHALL not require
live PCS4i hardware, and hardware-mutating tools SHALL remain opt-in. The
offline suite SHALL also cover the shared PDU command boundary for Aten
regression behavior when this change migrates Aten commands.

#### Scenario: Telnet authentication cases are synthetic
- **WHEN** maintainers run the offline PCS4i authentication tests
- **THEN** the tests cover prompt chunking, two-send limits, documented ready-marker success, read-only-probe success, rejection, timeout, disconnect, and the rule that ON/OFF/REBOOT are not authentication probes using synthetic transport data

#### Scenario: HTTP name loading cases are synthetic
- **WHEN** maintainers run the offline PCS4i HTTP name-loading tests
- **THEN** the tests cover successful HTTP names replacing fallback names and runtime HTTP failures preserving Telnet status with fallback names
- **AND** HTTP 401, HTTP 403, login rejection, timeout, transport failure, malformed response, and unsupported response do not authorize credential fallback

#### Scenario: PDU command safety is offline-testable
- **WHEN** maintainers run offline PDU command tests
- **THEN** one initial send maximum, one reconciliation cycle maximum, one authoritative readback maximum, one controlled ON/OFF resend maximum, second ambiguous ON/OFF outcome as indeterminate, ambiguous REBOOT zero-resend behavior, and no recursive recovery are verified without sending commands to live hardware

#### Scenario: Aten command migration is regression-tested
- **WHEN** maintainers run offline Aten PDU command tests
- **THEN** Aten ON/OFF/REBOOT dispatch, successful refresh-after-command, no GUI-thread network I/O, stale queued command drop, outlet count/rendering, unchanged wire protocol, and normal successful behavior are verified

#### Scenario: Hardware QA remains opt-in
- **WHEN** PCS4i live-device verification is needed
- **THEN** it is run only through authorized opt-in hardware QA and is not required for the normal offline suite
