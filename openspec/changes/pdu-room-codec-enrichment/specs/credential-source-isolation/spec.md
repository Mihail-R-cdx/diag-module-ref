## ADDED Requirements

### Requirement: Application-owned credentials for related-codec enrichment

Before related-codec handler or session construction, the application credential boundary
SHALL resolve the complete validated credential candidate chain for the exact resolved codec
`diagnostic_model`. The related-codec enrichment controller SHALL start from the valid saved
successful credential index for the exact codec model/IP context and SHALL supply the
supported saved connection profile as the first transport candidate.

One assigned credential SHALL be used for all supported transport attempts within one
acquisition/recovery attempt. Handlers, status adapters, workers, and protocol transports
SHALL NOT read the credential provider, inspect the complete candidate chain, choose a later
candidate, wrap to an earlier candidate, or persist successful credential/profile memory.

#### Scenario: Related codec has a saved credential and profile

- **WHEN** enrichment resolves an exact supported codec model/IP with retained credential index and supported connection profile
- **THEN** application composition supplies the ordered candidate chain and saved starting index to the dedicated related-codec lane
- **AND** the saved supported profile is tried first with that one assigned credential

#### Scenario: Related codec credentials are not configured

- **WHEN** the resolved codec requires credentials but application credential resolution fails safely before handler construction
- **THEN** no codec handler or network transport is created
- **AND** enrichment reports a safe configuration/unavailable outcome without exposing profile or credential values
- **AND** successful PDU diagnostics remain accepted

### Requirement: Structured authentication-only advancement for related-codec status

Related-codec candidate advancement SHALL be application-owned, monotonic, non-wrapping,
and authorized only by a structured confirmed `AuthenticationError` from new-session login.
An established-session 401/403 or other confirmed session rejection SHALL first be treated as
session invalidation under bounded same-credential recovery. Transport, timeout, SSL,
protocol, parser, empty-response, malformed-response, and command/status-unavailable
failures SHALL NOT advance the credential chain.

Message substrings, arbitrary numeric codes, generic text containing `auth`, `401`, or `403`,
the legacy `is_authentication_error()` heuristic, and absence of a successful value SHALL NOT
be credential-fallback authority.

#### Scenario: New related-codec login rejects the assigned credential

- **WHEN** related-codec handler acquisition produces a structured confirmed `AuthenticationError`
- **AND** another unattempted candidate remains in the current suffix
- **THEN** the application-owned attempt plan advances exactly once to that next candidate
- **AND** the handler does not choose the candidate

#### Scenario: Established related-codec session is rejected

- **WHEN** an established related-codec operation receives a confirmed invalid-session response
- **THEN** the session is invalidated and bounded same-credential recovery is attempted first
- **AND** the response does not directly authorize credential advancement

#### Scenario: Authentication-looking text is received

- **WHEN** a transport, parser, or generic response contains `auth`, `401`, `403`, or similar text without structured new-login authentication rejection
- **THEN** the related-codec credential plan does not advance

#### Scenario: Remaining suffix is exhausted

- **WHEN** the saved starting candidate and every later candidate produce structured new-login authentication rejection
- **THEN** each candidate in that suffix is attempted no more than once
- **AND** no earlier candidate is retried
- **AND** one safe terminal authentication outcome is presented

### Requirement: Related-codec credential and profile memory commits only accepted success

The application SHALL persist the successful credential index and supported connection
profile for the exact related codec model/IP only after a current final read-only status
operation has succeeded, its required normalization has completed, and the enclosing
enrichment context has been accepted as current.

Candidate advancement, connection establishment without accepted status, partial/raw status,
resolution-only results, stale completion, normalization failure, unavailable status, and
terminal errors SHALL NOT persist a new successful credential index or profile.

#### Scenario: Current final related-codec status succeeds

- **WHEN** a current related-codec status read and normalization complete successfully with an assigned credential index and supported connection profile
- **THEN** application composition may persist that index and profile for the exact codec model/IP

#### Scenario: Related-codec result becomes stale

- **WHEN** status was acquired but the enrichment context is superseded before the result is accepted
- **THEN** neither credential index nor connection profile is persisted from that result

#### Scenario: Connection succeeds but normalization fails

- **WHEN** handler/session acquisition succeeds but the required related-codec status cannot be normalized into an accepted final result
- **THEN** no new successful credential index or profile is persisted

### Requirement: Related-codec credential observability is secret-free

Public related-codec contexts, result/error/status signals, logs, dialogs, and PDU
presentation models SHALL NOT contain credential values, credential dictionaries, candidate
identities derived from secret values, credential profile names, cookies, Session IDs,
CSRF/access tokens, or session/transport objects.

Public attempt progress MAY expose only the current attempt ordinal and total candidate
count. Safe terminal messages SHALL identify the semantic configuration, authentication,
transport, protocol, or unavailable-status category without disclosing secret material.

#### Scenario: Related-codec attempt progress is displayed

- **WHEN** enrichment attempts any credential in a configured chain
- **THEN** public status may show only attempt position and total count
- **AND** no profile name, username, password, token, or candidate dictionary is exposed

#### Scenario: Related-codec error contains session material internally

- **WHEN** a handler or transport exception contains a cookie, token, Session ID, CSRF value, credential value, or session object detail
- **THEN** public error and log output is redacted before it crosses the application boundary
