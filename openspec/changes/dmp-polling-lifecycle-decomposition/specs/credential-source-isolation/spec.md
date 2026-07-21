## ADDED Requirements

### Requirement: DMP controller credential delegation

A DMP-specific application polling controller MAY coordinate Extron DMP 64 Plus credential attempts only through the existing application/composition credential boundary. It SHALL NOT read credential-provider storage directly, SHALL NOT become an independent credential source, and SHALL NOT persist credential values.

The application credential boundary SHALL remain authoritative for ordered candidate resolution, exact device/IP successful-index memory, valid starting candidate selection, and monotonic no-wrap advancement. The DMP controller MAY request those decisions through focused callbacks/providers and MAY request successful-index persistence only after the DMP-specific first-complete-snapshot success gate is satisfied.

Each DMP worker and handler SHALL receive only one assigned credential candidate per attempt. Transport/session work within that attempt SHALL use the same assigned credential. Credential fallback SHALL remain distinct from transport/session failure handling.

Public DMP controller contexts, signals, logs, errors, and status data SHALL NOT contain credential values, candidate dictionaries, profile names where they disclose credential configuration, or handler/session/transport objects.

#### Scenario: DMP controller obtains candidates through application policy
- **WHEN** a DMP polling request needs credentials
- **THEN** the controller receives the ordered candidate sequence through the application/composition credential boundary
- **AND** it does not read `credentials.local.json` or another credential store directly

#### Scenario: Worker receives one assigned candidate
- **WHEN** DMP polling attempt N starts
- **THEN** its worker and handler receive only candidate N
- **AND** they do not inspect or attempt later candidates

#### Scenario: DMP authentication fallback remains application-owned
- **WHEN** the current DMP attempt reports a structured confirmed authentication failure
- **AND** another candidate remains
- **THEN** the controller requests the next candidate through application-owned advancement policy
- **AND** the worker or handler does not choose that candidate

#### Scenario: Non-authentication text cannot authorize fallback
- **WHEN** a DMP error message contains text such as `auth`, `401`, or `403` without the structured authentication classification
- **THEN** the DMP controller does not advance the credential chain

#### Scenario: DMP public context is secret-free
- **WHEN** the controller publishes or logs DMP operation context or accepted lifecycle status
- **THEN** no username, password, credential dictionary, profile secret, handler, SSH session, channel, or transport object is exposed

### Requirement: DMP credential-context revision isolation

The DMP application lifecycle SHALL track a non-secret credential-context revision or equivalent opaque authority that changes when DMP credential configuration is changed. Candidate index alone SHALL NOT be used to prove that an existing DMP session still belongs to the current credential context.

A credential-context change SHALL supersede and cancel the active DMP polling context before further callbacks from the old context can be accepted as current.

#### Scenario: Same index with changed credentials is a new context
- **GIVEN** active DMP polling uses candidate index N
- **WHEN** credential configuration changes but the selected numeric index remains N
- **THEN** the old polling context is invalidated
- **AND** callbacks from the old session cannot update UI, credential memory, or fallback state

#### Scenario: Credential reordering invalidates old polling authority
- **WHEN** the configured DMP candidate order changes during active polling
- **THEN** the active DMP polling context is superseded even if its stored candidate index is still in range