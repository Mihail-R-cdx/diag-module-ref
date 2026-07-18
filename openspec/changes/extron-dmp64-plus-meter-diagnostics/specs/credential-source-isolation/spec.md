## ADDED Requirements

### Requirement: Extron DMP 64 Plus credential ownership
Extron DMP 64 Plus credential selection, credential fallback, and successful
credential memory SHALL remain owned by the application/composition layer. The
application SHALL resolve and validate the ordered credential candidate
sequence before a DMP session acquisition attempt starts. One DMP worker or
session acquisition attempt SHALL receive at most one assigned credential. The
DMP handler and polling worker SHALL NOT read `credentials.local.json`, inspect
candidate lists, advance candidate indexes, wrap the chain, select another
credential, or commit successful credential memory.

DMP credential fallback SHALL be authorized only by a structured confirmed
authentication failure during SSH session acquisition for the assigned
credential. Timeout, disconnect, PTY echo, SIS `E13`, malformed meter payload,
`0*0`, per-OID unavailable samples, transport-wide failures, and message text
containing authentication-like substrings SHALL NOT authorize credential
advancement.

Successful credential index for DMP SHALL be saved only after a real successful
connection is established and used for a successful DMP operation according to
the implementation contract, such as producing at least one valid final meter
snapshot. Stale, cancelled, failed, or authentication-precondition outcomes
SHALL NOT save a new successful credential index.

#### Scenario: DMP candidates are resolved before network I/O
- **WHEN** a DMP meter polling session is requested
- **THEN** application composition resolves the ordered credential candidates before worker/session acquisition starts

#### Scenario: DMP worker receives one assigned credential
- **WHEN** a DMP worker/session acquisition attempt starts with candidate N
- **THEN** the worker and handler use only candidate N
- **AND** they do not inspect or attempt candidate N+1

#### Scenario: Structured DMP authentication failure may advance chain
- **WHEN** DMP SSH session acquisition returns structured confirmed authentication failure for the assigned credential
- **AND** another candidate remains in the request-scoped suffix
- **THEN** the application may start a new DMP acquisition attempt with the next candidate

#### Scenario: DMP protocol data does not advance credentials
- **WHEN** DMP polling receives `E13`, `0*0`, malformed meter payload, timeout, PTY echo, or per-OID unavailable data
- **THEN** the application does not advance to another credential because of that data

#### Scenario: Stale DMP session does not cache credentials
- **WHEN** a DMP session becomes stale before its result is accepted by the active context
- **THEN** no successful credential index is saved from that stale session
