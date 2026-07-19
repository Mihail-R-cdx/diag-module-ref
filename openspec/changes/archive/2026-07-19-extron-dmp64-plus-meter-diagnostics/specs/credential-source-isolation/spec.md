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

A DMP SIS transaction timeout, including meter-read timeout and recovery-
acknowledgement timeout, SHALL be treated as a structured transport/session
failure and SHALL NOT be reclassified as `AuthenticationError` or equivalent
credential rejection. It SHALL NOT advance the credential chain, select another
candidate, wrap candidate order, or change successful credential memory.

Successful credential index for DMP SHALL be saved at most once for the
current session acquisition attempt and only after the first accepted complete
ten-OID polling cycle. For DMP, this is the long-lived polling equivalent of a
final non-partial acquisition result.

An accepted complete ten-OID polling cycle means the SSH/SIS session was
successfully established, all ten physical OIDs were attempted and either
produced a valid sample or a structured per-channel unavailable/protocol
outcome, a snapshot was formed, no session-level authentication or transport
failure terminated that cycle, and the snapshot was accepted by the active
non-stale DMP context. Per-channel unavailable entries MAY be present and SHALL
NOT by themselves block credential success. Successful SSH login alone, one
successful OID, stale snapshot completion, cancellation, authentication
precondition failure, or session-level failure before the first accepted
complete cycle SHALL NOT save a new successful credential index.

After the DMP credential index is saved for a session acquisition attempt,
later snapshots from that same polling session SHALL NOT repeatedly alter
credential memory.

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

#### Scenario: Transaction timeout does not advance DMP credential chain
- **WHEN** a DMP meter read or recovery acknowledgement times out
- **THEN** the application does not advance to the next credential candidate
- **AND** the DMP handler and worker do not select or attempt another credential

#### Scenario: SSH login alone does not cache DMP credential
- **WHEN** DMP SSH/SIS session acquisition succeeds
- **AND** no complete ten-OID polling cycle has been accepted by the active context
- **THEN** no successful credential index is saved

#### Scenario: One channel result does not cache DMP credential
- **WHEN** one DMP OID produces a valid meter sample
- **AND** the ten-OID polling cycle has not completed and been accepted
- **THEN** no successful credential index is saved

#### Scenario: Timed-out cycle does not cache DMP credential
- **WHEN** a DMP polling cycle is abandoned because a SIS transaction times out before the first accepted complete ten-OID cycle
- **THEN** no successful credential index is saved

#### Scenario: First accepted complete snapshot caches DMP credential once
- **WHEN** the first DMP polling cycle attempts all ten physical OIDs
- **AND** the snapshot is accepted by the active non-stale context
- **AND** no session-level authentication or transport failure terminated the cycle
- **THEN** the application may save the assigned credential index once for that session acquisition attempt

#### Scenario: Per-channel unavailable does not block DMP credential success
- **WHEN** a complete DMP ten-OID snapshot contains one or more per-channel unavailable entries
- **AND** the snapshot is accepted by the active non-stale context
- **THEN** those unavailable channel entries do not by themselves block saving the assigned credential index

#### Scenario: Stale complete DMP snapshot does not cache credentials
- **WHEN** a DMP session becomes stale before its complete ten-OID snapshot is accepted by the active context
- **THEN** no successful credential index is saved from that stale session

#### Scenario: Repeated DMP snapshots do not alter credential memory repeatedly
- **GIVEN** a DMP session acquisition attempt has already saved its assigned credential index after the first accepted complete snapshot
- **WHEN** later snapshots from the same session are accepted
- **THEN** they do not repeatedly change credential memory

#### Scenario: Session-level failure before first accepted snapshot
- **WHEN** DMP authentication, transport, or session failure occurs before any accepted complete ten-OID snapshot
- **THEN** no successful credential index is saved
