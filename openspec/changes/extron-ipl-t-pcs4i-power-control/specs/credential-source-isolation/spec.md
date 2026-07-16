## MODIFIED Requirements

### Requirement: Explicit protocol authentication inputs
Production factories and protocol handlers SHALL receive already-resolved
credentials through explicit existing constructor, factory, or worker inputs.
Hardcoded operational usernames, passwords, tokens, and `admin/admin`-style
fallbacks SHALL be removed from production credential flow. A handler that
requires authentication SHALL fail safely when needed credentials are absent;
a handler that supports unauthenticated operation SHALL be able to run without
credentials. Extron IPL T PCS4i SHALL use the existing password-only
`auth_mode: "password"` contract and SHALL NOT invent a username.

#### Scenario: Authenticated handler receives no credentials
- **WHEN** an authentication-required handler is selected without a valid credential object
- **THEN** it returns a safe configuration/authentication-precondition error and does not substitute an operational default

#### Scenario: Unauthenticated handler is selected
- **WHEN** the selected handler contract does not require authentication
- **THEN** it can connect without a credential profile

#### Scenario: PCS4i receives password-only credential
- **WHEN** PCS4i refresh or control is submitted
- **THEN** the application resolves a credential with `auth_mode: "password"` and passes only the assigned password to the worker/handler boundary

### Requirement: Ordered credential candidates and authentication fallback
The credential boundary SHALL expose an ordered sequence of request-scoped
credential candidates while preserving the existing one-candidate resolution
contract. Explicit credentials and an explicit profile SHALL each yield one
candidate. The complete candidate sequence SHALL be validated before it is
given to a worker. The existing retry mechanism SHALL try a later candidate
only after a confirmed authentication failure, SHALL stop for a
non-authentication error, SHALL retain a successful candidate index for the
same device/IP context, and SHALL emit one safe terminal authentication error
after exhaustion. The GUI/application composition layer SHALL be the sole
owner of credential fallback and SHALL advance monotonically to higher
candidate indexes without wrap-around. Each worker instance SHALL use only its
assigned candidate, SHALL NOT change the credential index, and SHALL emit at
most one terminal result or error. PCS4i workers and handlers SHALL follow this
same ownership model.

#### Scenario: Legacy provider is used
- **WHEN** a provider implements only the existing one-candidate method
- **THEN** request composition receives a one-element candidate sequence

#### Scenario: Authentication failure advances the chain
- **WHEN** a worker reports a confirmed authentication failure before the final candidate
- **THEN** the existing retry mechanism starts exactly one next attempt

#### Scenario: Worker performs one credential attempt
- **WHEN** the GUI creates a worker for credential candidate N
- **THEN** the worker uses only candidate N
- **AND** the worker does not advance to another credential candidate itself

#### Scenario: Protocol fallback preserves credential
- **WHEN** a worker tries another supported transport or protocol
- **THEN** every protocol attempt uses the same assigned credential candidate

#### Scenario: Authentication failure returns to the GUI
- **WHEN** a worker receives a confirmed authentication failure
- **THEN** the worker emits one authentication error
- **AND** the GUI decides whether to start the next candidate

#### Scenario: Non-authentication failure stops the chain
- **WHEN** an attempt fails with timeout, transport, SSL, parsing, or protocol error
- **THEN** no next credential candidate is started
- **AND** the worker does not use another credential candidate

#### Scenario: Chain is exhausted
- **WHEN** every candidate fails authentication
- **THEN** no additional worker is created and the user receives one safe terminal authentication error

#### Scenario: Saved candidate exhausts the remaining chain
- **WHEN** a request starts from a saved candidate with an index greater than zero
- **AND** that candidate and every later candidate fail authentication
- **THEN** each candidate in the remaining suffix is attempted no more than once
- **AND** the request ends with one safe terminal authentication error without wrapping to an earlier candidate

#### Scenario: Retry ownership remains in the application layer
- **WHEN** credential fallback is active for a request
- **THEN** only the GUI/application composition layer changes the credential index between attempts

#### Scenario: Credential index is isolated by device and IP
- **WHEN** one device/IP request succeeds with a later candidate and a new IP
  for the same device starts a request
- **THEN** the new IP starts at candidate zero, while a later request for the
  original IP reuses only that IP's successful candidate

#### Scenario: Stored index no longer fits the chain
- **WHEN** a saved credential index is outside the current candidate sequence
- **THEN** the request starts safely at candidate zero without an index error

#### Scenario: Partial result precedes completion
- **WHEN** a worker emits a partial result before completing authentication and
  final data collection
- **THEN** that candidate is not cached as successful

#### Scenario: Successful final result permits credential caching
- **WHEN** a worker emits a final non-partial result
- **THEN** device acquisition and parsing completed successfully
- **AND** only that result permits the GUI to cache the assigned candidate

#### Scenario: Failed attempt is not a result
- **WHEN** a worker receives an authentication or non-authentication failure
- **THEN** the worker emits an error signal
- **AND** it does not emit a final result containing an error description

#### Scenario: Partial result is followed by failure
- **WHEN** Polycom emits a partial HTTPS result and a later SSH, parsing, transport, or protocol stage fails
- **THEN** the candidate is not cached as successful
- **AND** no final non-partial result or success dialog is produced
- **AND** the GUI enters an error state

#### Scenario: Confirmed authentication failure ends protocol fallback
- **WHEN** a protocol attempt returns a confirmed authentication failure
- **THEN** the worker immediately emits one authentication error for the GUI
- **AND** it does not hide that failure behind another protocol attempt

#### Scenario: PCS4i handler cannot advance credentials
- **WHEN** PCS4i Telnet authentication fails for the assigned password
- **THEN** the handler reports a structured failure to the worker/application boundary
- **AND** it does not inspect or attempt another credential

## ADDED Requirements

### Requirement: PCS4i Telnet authentication retry authority
PCS4i credential fallback SHALL be authorized only by a structured confirmed
`AuthenticationError` from the Telnet session establishment state machine. The
state machine SHALL send the assigned password no more than twice during one
connection attempt. Timeout, disconnect, malformed prompt flow, command
rejection, and message text containing `auth`, `password`, `401`, or `403`
SHALL NOT authorize credential advancement.

HTTP outlet-name enrichment SHALL NOT be credential fallback authority. HTTP
401, HTTP 403, HTTP login rejection, HTTP timeout, HTTP transport failure,
malformed HTTP response, unsupported HTTP response, and missing or empty HTTP
outlet names SHALL only cause fallback display names for the current refresh.
They SHALL NOT switch the device credential, change the successful credential
index, or advance the credential candidate chain.

Before sending any PCS4i ON, OFF, or REBOOT command, the Telnet session SHALL
be confirmed authenticated by a documented session-ready prompt, another
documented non-mutating ready marker, or a successful verified read-only
outlet-status query. A state-changing command response SHALL NOT be used as the
first evidence that authentication succeeded.

#### Scenario: Initial password prompt with asterisks
- **WHEN** the initial Telnet buffer contains `Password:**********************`
- **THEN** the handler treats it as the initial password prompt
- **AND** it does not count it as a repeated prompt after the first password send

#### Scenario: Repeated prompt after first send
- **WHEN** new transport bytes received after the first password send contain a new `Password:` prompt
- **THEN** the handler may send the same assigned password a second time

#### Scenario: Repeated prompt after second send
- **WHEN** new transport bytes received after the second password send contain another `Password:` prompt
- **THEN** the handler reports a confirmed `AuthenticationError`

#### Scenario: Timeout is not retry authority
- **WHEN** PCS4i times out before the initial password prompt or disconnects without confirmed rejection
- **THEN** the application does not advance to the next credential

#### Scenario: Password send limit
- **WHEN** one PCS4i connection attempt runs
- **THEN** the handler sends the assigned password no more than two times

#### Scenario: Documented ready marker authenticates session
- **WHEN** PCS4i emits a verified documented ready marker after password submission
- **THEN** the session may be treated as authenticated before state-changing commands are allowed

#### Scenario: Read-only probe authenticates session
- **WHEN** PCS4i has no separately verified ready marker but a verified read-only outlet-status query succeeds after password submission
- **THEN** the session may be treated as authenticated before state-changing commands are allowed

#### Scenario: State-changing command is not an auth probe
- **WHEN** PCS4i password submission has not produced a verified ready marker or successful read-only status probe
- **THEN** ON, OFF, and REBOOT are not sent to test whether authentication succeeded

#### Scenario: HTTP 401 does not advance PCS4i credentials
- **WHEN** Telnet status succeeds and HTTP outlet-name loading returns HTTP 401 or HTTP 403
- **THEN** the current credential candidate remains selected
- **AND** the application does not start the next credential candidate

#### Scenario: HTTP name failure uses display fallback only
- **WHEN** HTTP outlet-name loading times out, rejects login, fails transport, returns malformed data, or returns an unsupported response
- **THEN** PCS4i outlet display names fall back for the current refresh
- **AND** credential fallback is not authorized
