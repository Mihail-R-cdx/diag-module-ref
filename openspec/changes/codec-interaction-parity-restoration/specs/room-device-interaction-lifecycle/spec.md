## ADDED Requirements

### Requirement: Automatic codec preview cannot starve current live telemetry

Automatic call-log preview enrichment SHALL NOT retire, supersede, or indefinitely delay an otherwise eligible current codec LIVE owner merely because a codec row was expanded. The one serialized room network lane remains authoritative: this requirement does not allow concurrent network owners.

When current LIVE owns the exact expanded codec row, automatic preview MAY use already acquired authoritative preview data or remain unavailable/deferred until a naturally idle admissible boundary. It SHALL NOT request LIVE retirement solely to populate the preview card.

An explicit operator call-log action remains an `AUXILIARY_READ` and MAY retire LIVE under the existing serialized-lane rules. After explicit auxiliary cleanup, eligible LIVE SHALL resume only if the same exact row is still current and usable.

#### Scenario: CloudLink row is expanded

- **GIVEN** a connected CloudLink Bar 310 or Box 310 row supports LIVE
- **WHEN** the operator expands the row
- **THEN** eligible microphone LIVE may start and remain owner
- **AND** automatic call-log preview does not retire that LIVE owner
- **AND** absence of preview data does not prevent live telemetry from updating

#### Scenario: Operator explicitly opens call log during LIVE

- **GIVEN** codec LIVE is active for the current exact row
- **WHEN** the operator explicitly opens the call log
- **THEN** the auxiliary action follows the existing LIVE-retirement and bounded-cleanup handoff
- **AND** no concurrent network owner is introduced
- **AND** eligible LIVE resumes after auxiliary cleanup if the same row remains current and usable

### Requirement: Codec interactive operations have bounded release on every terminal path

Every room codec Local Refresh, explicit call-log auxiliary read, supported audio mutation/reconciliation, and LIVE retirement SHALL reach either physical cleanup/release or the existing allowed bounded-abandonment boundary on success, typed authentication exhaustion, ordinary protocol/parse failure, transport/session loss, user cancellation, row collapse/switch, timeout, and stale supersession.

A terminal or cancelled codec operation SHALL NOT leave the room interaction lane, row controls, or top-level controls permanently locked because a callback was dropped or a session shutdown signal never arrived. Late callbacks after currentness revocation SHALL have no presentation, credential, cache, or lock side effects.

#### Scenario: Codec operation fails ordinarily

- **WHEN** a current codec operation ends with an ordinary protocol/parse/business failure that does not prove connection loss
- **THEN** bounded cleanup releases its room-lane ownership
- **AND** the UI lock matrix returns to the state permitted by the still-current row
- **AND** eligible LIVE may resume when current contracts allow it

#### Scenario: Cleanup signal never arrives

- **GIVEN** codec operation authority has been revoked
- **AND** expected physical cleanup notification does not arrive within policy timeout
- **WHEN** the bounded-abandonment boundary is reached
- **THEN** stale authority cannot keep the GUI permanently locked
- **AND** no late callback can regain currentness
