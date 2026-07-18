## MODIFIED Requirements

### Requirement: Redacted protocol diagnostics
Handler command logging and worker error handling SHALL redact known usernames,
passwords, authentication tokens, sensitive request payloads, and sensitive
response bodies before they are emitted to terminal/debug output. New tests and
new documentation SHALL use synthetic credentials only. PCS4i Telnet
authentication, Telnet SIS commands, HTTP outlet-name enrichment, PDU command
outcomes, unsupported-operation outcomes, DMP SSH/SIS meter polling, DMP PTY
echo handling, DMP recovery commands, and public diagnostics SHALL never expose
real assigned passwords or SSH secret material.

#### Scenario: Handler logs a credential-bearing request
- **WHEN** a supported Huawei, Polycom, Aten, PCS4i, or DMP handler records a request containing credentials or a token
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

#### Scenario: DMP SSH credentials are redacted
- **WHEN** DMP SSH connection or SIS polling fails with exception text containing an assigned credential
- **THEN** logs, worker signals, GUI dialogs, terminal output, and validation evidence contain only redacted text

## ADDED Requirements

### Requirement: Extron DMP 64 Plus offline protocol validation
DMP meter diagnostics SHALL be verifiable offline with synthetic SSH/channel
transport and parser tests. Normal automated verification SHALL NOT require
live DMP hardware. Opt-in live-device QA may be used to gather additional
evidence, but live hardware SHALL NOT be required for the main automated test
suite.

Offline tests SHALL cover stream buffering/framing, PTY echo filtering,
serialized transaction correlation, fragmented reads, multiple frames in one
read, unrelated/unsolicited frames before expected responses, wrong recovery
acknowledgement before correct acknowledgement, expected response timeout,
leftover-frame isolation, clean SIS payload parsing, valid `1*NNN` and
`2*NNN` samples, `0*0`, `E13`, malformed payloads, dBFS conversion,
`-60 dB .. +12 dB` normalization, clamping, unavailable bar rendering,
one-shot `*2` recovery, no repeated recovery every polling cycle, partial
snapshots, worker cancellation checkpoints, bounded wait cancellation,
resource cleanup, repeat Refresh context replacement, credential success gate,
supported variant recognition, structured authentication failure, secret
redaction, and absence of GUI-thread network I/O.

#### Scenario: DMP transport tests are synthetic
- **WHEN** maintainers run offline DMP transport tests
- **THEN** PTY echo filtering, fragmented SSH reads, multiple logical frames in one read, unrelated frames before expected payload, unsolicited frames before expected payload, wrong recovery acknowledgement, expected response timeout, and leftover-frame isolation are verified without live hardware

#### Scenario: DMP parser tests are synthetic
- **WHEN** maintainers run offline DMP parser tests
- **THEN** valid samples, `0*0`, `E13`, malformed payloads, dBFS conversion, and scale normalization are verified without live hardware

#### Scenario: DMP recovery tests are bounded
- **WHEN** maintainers run offline DMP recovery tests
- **THEN** one-shot `*2` recovery and no repeated recovery loop are verified with synthetic responses

#### Scenario: DMP lifecycle tests are offline
- **WHEN** maintainers run offline DMP worker/controller tests
- **THEN** cancellation before handler acquisition, cancellation between OIDs, cancellation before `*2`, cancellation during bounded wait, no next cycle after cancellation, SSH resource release, repeat Refresh context replacement, application-close cleanup, stale-result suppression, context switch behavior, partial snapshot behavior, structured errors, and GUI-thread isolation are verified without live DMP hardware

#### Scenario: DMP credential success tests are offline
- **WHEN** maintainers run offline DMP credential tests
- **THEN** SSH-login-only no-cache, one-channel-result no-cache, first accepted complete snapshot caches once, complete snapshot with per-channel unavailable may cache, stale complete snapshot no-cache, repeated snapshots no repeated credential-memory mutation, and session-level failure before first accepted snapshot no-cache are verified without live DMP hardware

#### Scenario: DMP variant-boundary tests are offline
- **WHEN** maintainers run offline DMP model discovery tests
- **THEN** supported variants are accepted
- **AND** unknown variants are not accepted solely by substring matching

#### Scenario: DMP hardware QA remains opt-in
- **WHEN** DMP live-device verification is needed
- **THEN** it is run only through authorized opt-in hardware QA
- **AND** it is not required for the normal offline suite
