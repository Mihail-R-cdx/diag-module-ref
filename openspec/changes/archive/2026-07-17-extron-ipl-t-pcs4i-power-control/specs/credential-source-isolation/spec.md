## MODIFIED Requirements

### Requirement: Explicit protocol authentication inputs
Production factories and protocol handlers SHALL receive already-resolved
credentials through explicit existing constructor, factory, or worker inputs.
Hardcoded operational usernames, passwords, tokens, and `admin/admin`-style
fallbacks SHALL be removed from production credential flow. A handler that
requires authentication SHALL fail safely when needed credentials are absent;
a handler that supports unauthenticated operation SHALL be able to run without
credentials. Extron IPL T PCS4i SHALL use the existing password-only
`auth_mode: "password"` contract, SHALL NOT invent a username, and SHALL allow
the assigned credential to be absent until the Telnet protocol actually
requests `Password`. For PCS4i only, absence of an explicit credential,
explicit profile, and device mapping SHALL NOT by itself be a configuration
error; the application/composition layer SHALL be able to submit one
credentialless attempt.

#### Scenario: Authenticated handler receives no credentials
- **WHEN** an authentication-required handler is selected without a valid credential object
- **THEN** it returns a safe configuration/authentication-precondition error and does not substitute an operational default

#### Scenario: Unauthenticated handler is selected
- **WHEN** the selected handler contract does not require authentication
- **THEN** it can connect without a credential profile

#### Scenario: PCS4i receives password-only credential
- **WHEN** PCS4i refresh or control is submitted with an assigned credential candidate
- **THEN** the application passes only the assigned password to the worker/handler boundary
- **AND** no username is invented

#### Scenario: PCS4i receives no assigned credential
- **WHEN** PCS4i refresh is submitted without an assigned credential
- **THEN** the handler may still connect and attempt a verified read-only passwordless readiness probe

#### Scenario: Other authenticated handler receives no credentials
- **WHEN** an authentication-required non-PCS4i handler is selected without required credentials
- **THEN** the application reports a safe configuration/authentication-precondition error before network I/O
- **AND** it does not create a credentialless device attempt

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
same ownership model; repeating the same assigned password for a second PCS4i
prompt is not credential fallback.

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

#### Scenario: PCS4i second prompt repeats the same credential
- **WHEN** PCS4i returns a new `Password` marker after the assigned password was sent once
- **THEN** the handler sends the same assigned password exactly one additional time
- **AND** it does not choose a different credential candidate

## ADDED Requirements

### Requirement: PCS4i application credentialless attempt composition
When PCS4i has an explicit credential, explicit profile, or mapped credential
chain, the application/composition layer SHALL build the normal ordered
credential plan. Each worker attempt SHALL receive at most one assigned
credential, and credential fallback SHALL remain application-owned.

When PCS4i has no explicit credential, no explicit profile, and no device
mapping, the application/composition layer SHALL create exactly one
credentialless attempt instead of failing before network I/O. That attempt SHALL
carry assigned credential `none`, SHALL have no candidate index, and SHALL have
no successful credential index. If the credentialless attempt succeeds without
the device requesting `Password`, the operation MAY complete successfully but
SHALL NOT create, update, persist, or invalidate credential memory. If the
credentialless attempt receives a `Password` marker, the outcome SHALL be
structured `CredentialRequired`; no password SHALL be sent, no
`AuthenticationError` SHALL be returned, and no next credential candidate SHALL
start because no credential plan existed.

This exception SHALL be scoped only to device/protocol paths that support
unauthenticated/passwordless operation. In this change, the exception applies
to PCS4i only and SHALL NOT weaken missing-credential behavior for other
authentication-required devices.

#### Scenario: PCS4i without mapping starts credentialless attempt
- **GIVEN** selected device is Extron IPL T PCS4i
- **AND** no explicit credential is supplied
- **AND** no explicit profile is supplied
- **AND** no PCS4i device mapping exists
- **WHEN** application composition builds the attempt plan
- **THEN** it creates one credentialless attempt
- **AND** assigned credential is none
- **AND** candidate index is absent

#### Scenario: Credentialless PCS4i succeeds without Password prompt
- **GIVEN** a credentialless PCS4i attempt is running
- **WHEN** connection is established
- **AND** no `Password` marker is observed
- **AND** a verified read-only SIS readiness probe succeeds
- **THEN** the operation may complete successfully as passwordless
- **AND** zero password sends occur

#### Scenario: Credentialless PCS4i receives Password prompt
- **GIVEN** a credentialless PCS4i attempt is running
- **WHEN** new phase bytes contain `Password`
- **THEN** the outcome is structured `CredentialRequired`
- **AND** `AuthenticationError` is not returned
- **AND** no next credential candidate is started
- **AND** no password is sent
- **AND** the user-facing error safely explains that a credential must be configured

#### Scenario: Credentialless success does not update credential index
- **GIVEN** a credentialless PCS4i attempt succeeds
- **WHEN** application composition processes the final result
- **THEN** no successful credential index is created
- **AND** no successful credential index is updated
- **AND** credential memory is unchanged

#### Scenario: Other authentication-required devices remain blocked
- **GIVEN** selected device requires authentication and is not in a passwordless-capable path
- **WHEN** no required credential, profile, or mapping is available
- **THEN** application composition reports a safe configuration error before network I/O
- **AND** it does not create a credentialless attempt

### Requirement: PCS4i optional credential and phase-scoped password flow
PCS4i Telnet session establishment SHALL support passwordless and
password-protected configurations. A credential candidate MAY be assigned to a
PCS4i attempt, but the handler SHALL NOT send it until new bytes in the current
protocol phase contain the `Password` marker. Prompt detection SHALL depend on
the marker `Password` in new phase bytes and SHALL NOT require a colon,
asterisks, a specific asterisk count, or an exact prompt string.

Prompt detection SHALL be scoped to the initial receive phase, post password
send #1 phase, and post password send #2 phase. A `Password` marker observed in
initial receive bytes SHALL NOT be reused to authorize password send #2. After
password send #1, repeated-prompt detection SHALL inspect only bytes received
after send #1. After password send #2, rejection detection SHALL inspect only
bytes received after send #2.

When no `Password` marker is observed, absence of a prompt SHALL NOT by itself
prove readiness. PCS4i SHALL become ready without password only after a verified
non-mutating SIS probe succeeds, such as `<ESC>CK<CR>` or a verified `PC`
readback. If a `Password` marker appears and no credential was assigned, the
handler SHALL return structured `CredentialRequired`, SHALL send no password,
and SHALL NOT return `AuthenticationError`. If a credential was assigned, the
handler SHALL send that same password at most twice during one connection
attempt. A third new prompt after two sends SHALL produce structured
`AuthenticationError`, and no third password send SHALL occur.

#### Scenario: Passwordless PCS4i
- **GIVEN** PCS4i has no configured password
- **WHEN** connection is established
- **AND** no `Password` marker is observed
- **AND** a verified read-only SIS probe succeeds
- **THEN** session becomes ready
- **AND** zero password sends occur

#### Scenario: Initial decorated Password prompt
- **GIVEN** initial session bytes contain `Password:**********************`
- **WHEN** prompt detection runs
- **THEN** it is classified as one initial password prompt
- **AND** asterisk count is ignored
- **AND** exactly one first password send occurs when an assigned credential exists

#### Scenario: Prompt without colon
- **GIVEN** new session bytes contain `Password`
- **WHEN** prompt detection runs
- **THEN** it is recognized as a password prompt without requiring `:` or `*`

#### Scenario: Second Password prompt
- **GIVEN** assigned password was sent once
- **WHEN** new post-send bytes contain `Password`
- **THEN** the same assigned password is sent exactly one additional time

#### Scenario: Third prompt forbidden
- **GIVEN** the same assigned password has already been sent twice
- **WHEN** new post-send bytes again contain `Password`
- **THEN** a structured `AuthenticationError` is returned
- **AND** no third password send occurs

#### Scenario: Initial prompt cannot be reused
- **GIVEN** initial receive buffer contained `Password`
- **WHEN** password #1 is sent
- **THEN** repeated-prompt detection examines only bytes received after password #1
- **AND** the initial `Password` occurrence cannot trigger password #2

#### Scenario: Passwordless session with candidate assigned
- **GIVEN** application assigned a credential candidate
- **AND** PCS4i never requested `Password`
- **AND** read-only session probe succeeds
- **THEN** the credential was not used
- **AND** successful credential index is not updated

#### Scenario: Password required but no assigned credential
- **GIVEN** PCS4i requests `Password`
- **AND** no credential was assigned
- **THEN** return structured `CredentialRequired`
- **AND** do not return `AuthenticationError`
- **AND** send no password

### Requirement: PCS4i Telnet authentication retry authority
PCS4i credential fallback SHALL be authorized only by a structured confirmed
`AuthenticationError` from the Telnet session establishment state machine after
an actually sent assigned password is rejected. Timeout, disconnect, malformed
prompt flow, command rejection, `CredentialRequired`, passwordless success, and
message text containing `auth`, `password`, `401`, or `403` SHALL NOT authorize
credential advancement.

HTTP outlet-name enrichment SHALL NOT be credential fallback authority. HTTP
401, HTTP 403, HTTP login rejection, HTTP timeout, HTTP transport failure,
malformed HTTP response, unsupported HTTP response, and missing or empty HTTP
outlet names SHALL only cause fallback display names for the current refresh.
The HTTP enrichment outcome itself SHALL NOT switch the device credential,
advance the credential candidate chain, invalidate the assigned credential,
roll back a successful Telnet credential, or independently commit a credential
index. A final PCS4i refresh that successfully completes authoritative Telnet
authentication and outlet-state acquisition MAY commit the assigned credential
index according to the normal successful-operation contract only if that
credential was actually used, or if the existing application contract permits a
successful passwordless operation with no credential use to complete without
changing credential memory.

Before sending any PCS4i ON or OFF command, the Telnet session SHALL be
confirmed ready by documented login-ready evidence or a successful verified
read-only SIS probe. A state-changing command response SHALL NOT be used as the
first evidence that authentication/session readiness succeeded.

#### Scenario: Timeout is not retry authority
- **WHEN** PCS4i times out before readiness or disconnects without confirmed credential rejection
- **THEN** the application does not advance to the next credential

#### Scenario: Password send limit
- **WHEN** one PCS4i connection attempt runs
- **THEN** the handler sends the assigned password no more than two times

#### Scenario: Documented ready marker authenticates session
- **WHEN** PCS4i emits verified `Login Administrator` or `Login User` evidence after password submission
- **THEN** the session may be treated as authenticated before state-changing commands are allowed

#### Scenario: Read-only probe authenticates session
- **WHEN** PCS4i has no separately verified ready marker but a verified read-only SIS probe succeeds
- **THEN** the session may be treated as ready before state-changing commands are allowed

#### Scenario: State-changing command is not an auth probe
- **WHEN** PCS4i password submission or passwordless connect has not produced verified ready evidence
- **THEN** ON and OFF are not sent to test whether authentication succeeded

#### Scenario: HTTP 401 does not advance PCS4i credentials
- **WHEN** Telnet status succeeds and HTTP outlet-name loading returns HTTP 401 or HTTP 403
- **THEN** the current credential candidate remains selected
- **AND** the application does not start the next credential candidate

#### Scenario: HTTP name failure uses display fallback only
- **WHEN** HTTP outlet-name loading times out, rejects login, fails transport, returns malformed data, or returns an unsupported response
- **THEN** PCS4i outlet display names fall back for the current refresh
- **AND** credential fallback is not authorized

#### Scenario: HTTP degradation does not block Telnet success
- **WHEN** PCS4i Telnet authentication succeeds and authoritative Telnet outlet status succeeds
- **AND** HTTP outlet-name loading times out or otherwise degrades to fallback names
- **THEN** the refresh is a successful authoritative device operation
- **AND** HTTP degradation does not authorize another credential candidate

#### Scenario: Later Telnet credential survives HTTP 401
- **WHEN** candidate 0 fails with a confirmed Telnet `AuthenticationError`
- **AND** candidate 1 authenticates over Telnet and reads authoritative outlet status successfully
- **AND** HTTP outlet-name loading returns HTTP 401
- **THEN** the refresh succeeds with fallback names
- **AND** candidate 2 is not attempted
- **AND** candidate 1 is eligible to be committed as the successful credential index
