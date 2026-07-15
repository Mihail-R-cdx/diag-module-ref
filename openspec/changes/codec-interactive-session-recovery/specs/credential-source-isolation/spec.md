## ADDED Requirements

### Requirement: Interactive credential fallback ownership
The GUI/application composition layer SHALL resolve the complete ordered
credential sequence before submitting an interactive codec operation and SHALL
remain the sole owner of its request-scoped credential attempt plan. The plan
SHALL start at the valid successful index for the exact model/IP pair, SHALL
consider only the remaining suffix without wrap-around, and SHALL commit an
index only after a final successful or successfully reconciled operation. Each
interactive handler instance SHALL receive only one assigned credential and
SHALL NOT inspect candidates, change an index, or cache success.

#### Scenario: Interactive path resolves candidates before network I/O
- **WHEN** an interactive operation needs a codec handler
- **THEN** application composition resolves and validates every ordered candidate before the controller starts network I/O

#### Scenario: Interactive path reuses the successful index
- **WHEN** the exact model/IP pair has a valid successful credential index
- **THEN** the interactive attempt plan starts at that index and does not wrap to earlier candidates

#### Scenario: Transport fallback keeps one credential
- **WHEN** an interactive connection tries more than one supported transport
- **THEN** every transport attempt uses the same assigned credential

#### Scenario: Only confirmed login failure advances credentials
- **WHEN** a transport, connection, established-session, protocol, parse, or command failure occurs
- **THEN** the application does not advance to another credential
- **AND** only a confirmed authentication failure from a new login permits monotonic advancement

#### Scenario: Handler cannot become a retry owner
- **WHEN** an interactive handler encounters any failure
- **THEN** it returns a typed outcome to the application controller
- **AND** it does not select or retry another credential itself

#### Scenario: Failed candidate is not persisted
- **WHEN** a later interactive candidate fails before a final successful operation
- **THEN** that candidate index is not stored as successful for the model/IP pair

### Requirement: Interactive session secret isolation
Interactive session context, failure classification, recovery, and replay SHALL
not disclose credential values, private credential identity, request payloads,
response bodies containing authentication material, cookies, Session IDs, CSRF
tokens, or SSH authentication material through logs, signals, results, errors,
dialogs, or status text. Public attempt information SHALL contain only model,
IP, operation kind, ordinal counts, transport label, and redacted category.

#### Scenario: Session recovery fails with secret-bearing details
- **WHEN** an exception or device response includes any active credential or session artifact
- **THEN** every public operation error, terminal message, signal, and dialog contains only redacted text

#### Scenario: Credential identity changes
- **WHEN** private credential identity is used to invalidate a cached handler
- **THEN** that identity is neither persisted nor emitted to public diagnostics
