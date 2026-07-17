# secure-observability-and-validation Specification

## Purpose
TBD - created by archiving change bootstrap-openspec-baseline. Update Purpose after archive.
## Requirements
### Requirement: Redacted protocol diagnostics
Handler command logging and worker error handling SHALL redact known usernames,
passwords, authentication tokens, sensitive request payloads, and sensitive
response bodies before they are emitted to terminal/debug output. New tests and
new documentation SHALL use synthetic credentials only. PCS4i Telnet
authentication, Telnet SIS commands, HTTP outlet-name enrichment, PDU command
outcomes, unsupported-operation outcomes, and public diagnostics SHALL never
expose the real assigned password.

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

#### Scenario: PCS4i password is not logged during second send
- **WHEN** PCS4i requires the same assigned password to be sent a second time
- **THEN** no stdout, debug log, GUI message, exception, public diagnostic, test assertion, or validation report contains the password value

### Requirement: Offline verification boundary
The repository SHALL keep normal automated verification offline. Hardware
network probes and device-mutating tools SHALL remain opt-in and SHALL not be
required for the offline test suite.

#### Scenario: Offline validation
- **WHEN** maintainers run `python -m unittest discover -s tests -p "test_*.py"`
- **THEN** the suite exercises repository tests without requiring live AV equipment

### Requirement: OpenSpec change completion
A future OpenSpec change SHALL be ready to archive only when its required
artifacts, requirements, scenarios, implementation status, strict OpenSpec
validation, relevant offline tests, and documentation checks agree. The change
SHALL explicitly describe any runtime behavior change and SHALL not hide
unrelated fixes outside its scope.

#### Scenario: Completed future change
- **WHEN** a change has completed its required artifacts and implementation
- **THEN** maintainers can validate it with `openspec validate --all --strict` and archive it through the standard OpenSpec command

### Requirement: PCS4i offline protocol validation
PCS4i protocol behavior SHALL be verified with offline tests using synthetic
Telnet and HTTP transports. Normal automated verification SHALL not require
live PCS4i hardware, and hardware-mutating tools SHALL remain opt-in. The
offline suite SHALL also cover Aten refresh stale-generation behavior and the
shared PDU command boundary for Aten regression behavior.

#### Scenario: Telnet authentication cases are synthetic
- **WHEN** maintainers run the offline PCS4i authentication tests
- **THEN** the tests cover passwordless readiness, prompt chunking, decorated prompt, prompt without colon, phase-scoped repeated prompt detection, same-password second send, two-send limit, `CredentialRequired`, `AuthenticationError`, timeout, disconnect, and the rule that ON/OFF are not authentication probes using synthetic transport data

#### Scenario: Telnet SIS cases are synthetic
- **WHEN** maintainers run offline PCS4i SIS tests
- **THEN** the tests cover model query, firmware query, security-level query, `PC` returning OFF, `PC` returning ON, `PS` not being interpreted as power, outlet numbers outside 1..4 rejected before network I/O, ON command grammar, OFF command grammar, and authoritative `PC` readback after state-changing operation

#### Scenario: HTTP name loading cases are synthetic
- **WHEN** maintainers run the offline PCS4i HTTP name-loading tests
- **THEN** the tests cover successful `xName1` through `xName4` replacing fallback names, one missing name falling back per outlet, malformed response, HTTP unavailable, HTTP 401/403, verified no-auth device behavior, and runtime HTTP failures preserving Telnet status with fallback names
- **AND** HTTP 401, HTTP 403, login rejection, timeout, transport failure, malformed response, and unsupported response do not authorize credential fallback

#### Scenario: PCS4i command safety is offline-testable
- **WHEN** maintainers run offline PCS4i PDU command tests
- **THEN** one initial ON/OFF send maximum, one reconciliation cycle maximum, one reconciliation decision readback maximum, one controlled ON/OFF resend maximum, one terminal confirmation `PC` readback after controlled resend, total state-changing sends maximum two, acknowledged mismatch handling with saved `PRE_STATE`, unknown `PRE_STATE` valid non-target readback producing indeterminate with no resend, opposite state not implicitly becoming `PRE_STATE`, `PC == PRE_STATE` after controlled resend producing failure, unavailable terminal readback producing indeterminate, and no recursive recovery are verified without sending commands to live hardware

#### Scenario: PCS4i REBOOT unsupported is offline-testable
- **WHEN** maintainers run offline PCS4i capability and dispatch tests
- **THEN** PCS4i REBOOT is absent from `PDUScreen` controls
- **AND** programmatic PCS4i REBOOT is rejected before handler acquisition and before any Telnet or HTTP network I/O

#### Scenario: Aten refresh stale generation is regression-tested
- **WHEN** maintainers run offline Aten PDU refresh tests
- **THEN** stale queued Aten refresh before handler acquisition, stale context before first network I/O, in-flight old refresh result isolation, and normal current Aten refresh behavior are verified

#### Scenario: Aten command migration is regression-tested
- **WHEN** maintainers run offline Aten PDU command tests
- **THEN** Aten ON/OFF/REBOOT dispatch, ambiguous ON/OFF reconciliation, ambiguous REBOOT non-replay, successful refresh-after-command, no GUI-thread network I/O, stale queued command drop, outlet count/rendering, unchanged wire protocol, and normal successful behavior are verified

#### Scenario: Hardware QA remains opt-in
- **WHEN** PCS4i live-device verification is needed
- **THEN** it is run only through authorized opt-in hardware QA and is not required for the normal offline suite
