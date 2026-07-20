# credential-source-isolation Specification

## Purpose
TBD - created by archiving change externalize-device-credentials. Update Purpose after archive.
## Requirements
### Requirement: Central credential-provider boundary
The application SHALL define a `CredentialProvider` contract owned by the
application/core boundary and a `JsonCredentialProvider` implementation. A
protocol handler, factory, or worker SHALL NOT parse `credentials.local.json`
directly; credential values SHALL cross their existing construction boundary
explicitly.

#### Scenario: Provider supplies a selected profile
- **WHEN** a refresh request needs authentication and no explicit credential is supplied
- **THEN** application/bootstrap code resolves the selected profile through `CredentialProvider` before constructing the worker or handler

#### Scenario: Handler is replaced in a unit test
- **WHEN** a unit test supplies credentials directly to a worker, factory, or handler
- **THEN** the test runs without a local JSON file and without changing protocol-handler code

### Requirement: Local JSON storage and predictable path
The first provider implementation SHALL load the unencrypted local file named
`credentials.local.json` from the application/project root adjacent to the
launch entry point, resolved independently of the current working directory.
The provider SHALL use only Python's standard `json` module and SHALL introduce
no third-party dependency.

#### Scenario: Application starts from another working directory
- **WHEN** the program is launched with a different current working directory
- **THEN** the provider resolves the same application-root local file and does not read an unrelated file from that directory

#### Scenario: Valid local JSON is available
- **WHEN** the configured local file contains a valid selected profile
- **THEN** `JsonCredentialProvider` returns the profile for application use

### Requirement: Credential profile schema and validation
The local JSON document SHALL use a versioned object with a `profiles` object
and an optional device-model-to-profile mapping. Each profile SHALL declare its
authentication mode and contain only the fields required for that mode:
username/password, password-only, or unauthenticated. A device mapping value
SHALL be either a non-empty profile-name string or a non-empty ordered list of
non-empty profile-name strings. The provider SHALL reject an invalid root
shape, unknown mode, missing required field, invalid mapping, empty list,
non-string list member, or blank profile name with a safe configuration error
that does not include credential or profile values.

#### Scenario: Profile has required fields
- **WHEN** a username/password profile includes both required fields
- **THEN** the provider returns a credential object with that authentication mode

#### Scenario: Required password is missing
- **WHEN** a selected authenticated profile omits its required password field
- **THEN** no network connection starts and the caller receives a safe configuration error

#### Scenario: JSON structure is invalid
- **WHEN** the local file root or profile structure does not match the documented schema
- **THEN** the provider rejects it with a configuration error that names no credential value

#### Scenario: Device mapping has an invalid chain
- **WHEN** a mapped profile list is empty or contains a blank or non-string item
- **THEN** the provider rejects the request before returning any candidate

### Requirement: Profile selection and source priority
Credential resolution SHALL use an explicit profile requested by the caller
when present; otherwise it SHALL use the selected device model's local mapping.
Credentials explicitly supplied by a caller or unit test SHALL take documented
priority over a provider result. An unmapped device or unknown profile SHALL
produce a safe configuration error rather than selecting a global default. A
string mapping SHALL resolve as one candidate, while a list mapping SHALL
resolve candidates in JSON order without a fixed maximum length.

#### Scenario: Explicit credentials take priority
- **WHEN** a caller provides credentials and a local profile is also configured
- **THEN** the explicitly supplied credentials are used for that request

#### Scenario: Device model selects a profile
- **WHEN** no explicit profile is requested and the selected device model has a local profile mapping
- **THEN** the mapped profile is resolved deterministically

#### Scenario: Selected profile is absent
- **WHEN** a requested or mapped profile does not exist
- **THEN** the request stops before network I/O with a safe configuration error

#### Scenario: Device model selects an ordered chain
- **WHEN** a selected device has a list-valued mapping
- **THEN** all referenced profiles resolve in the listed order before network I/O starts

### Requirement: Safe local-configuration failures
The provider SHALL distinguish missing-file, invalid-JSON, invalid-schema, and
missing-profile failures from device authentication failures. Messages surfaced
to GUI, logs, workers, and exceptions SHALL identify the configuration problem
without disclosing a password, token, or other credential material.

#### Scenario: Local file is missing
- **WHEN** authentication is required and `credentials.local.json` is absent
- **THEN** the application reports an actionable configuration error and does not start device authentication

#### Scenario: Local JSON is syntactically invalid
- **WHEN** JSON parsing fails
- **THEN** the application reports a distinct safe configuration error rather than an authentication failure

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

### Requirement: Provider replacement and credential isolation
The `CredentialProvider` contract SHALL permit a future secure provider, such
as Windows Credential Manager, to replace `JsonCredentialProvider` without
protocol-handler changes. Credential context SHALL remain scoped to the active
device/IP/request and SHALL NOT be retained in shared status dictionaries or
worker-result payloads.

#### Scenario: Provider is substituted
- **WHEN** a test or future bootstrap supplies another `CredentialProvider`
- **THEN** workers and handlers receive resolved credentials without depending on JSON-provider internals

#### Scenario: Worker completes
- **WHEN** a credential-bearing worker emits result, status, error, or completion data
- **THEN** the emitted public payload contains no credential fields or credential values

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
prompt is not credential fallback. Worker module decomposition SHALL NOT move
credential candidate selection, credential fallback, or successful credential
index memory into focused worker modules, handlers, or the `core.worker`
facade, including for `ExtronDMP64PlusMeterWorker`.

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

#### Scenario: Decomposed worker cannot become credential owner
- **WHEN** a worker implementation moves from `core/worker.py` into a focused module
- **THEN** the worker still receives only its assigned credential candidate
- **AND** the move does not introduce provider reads, credential iteration, candidate advancement, wrap-around, or successful-index persistence inside the worker module

### Requirement: Safe candidate observability and provider isolation
Workers and handlers SHALL receive resolved credential values through existing
construction inputs and SHALL NOT read JSON-provider internals. Public
attempt status, logs, errors, exceptions, signals, and results SHALL disclose
only the current attempt number and total candidate count, never profile names
or credential values.

#### Scenario: Long-chain attempt status is rendered
- **WHEN** a request is using any candidate in an ordered chain
- **THEN** public status identifies only its current position and the total count

#### Scenario: Provider rejects a later profile
- **WHEN** any profile in a mapped chain is missing or invalid
- **THEN** no worker starts and the safe configuration error discloses neither profile nor credential values

#### Scenario: TE20 or Extron worker error reaches a public terminal
- **WHEN** a TE20 or Extron error contains credential values or authorization
  material from any candidate in the active chain
- **THEN** terminal, status, and dialog output receive only redacted safe text
  before any rendering occurs

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

#### Scenario: Codec retry authority is structured
- **WHEN** a codec refresh worker or interactive handler reports a failure
- **THEN** credential advancement depends on a machine-readable classification derived from its typed failure boundary
- **AND** message text, localized authentication words, HTTP-like digits embedded in transport text, and the legacy authentication helper do not grant retry authority

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

### Requirement: Matrix credential ownership and fallback boundary
Matrix credential candidate selection, credential fallback, and successful
credential index memory SHALL remain owned by the application/composition
layer. A Matrix controller may participate in this boundary by requesting
resolved candidates and reporting structured outcomes, but it SHALL NOT create
a second independent credential manager.

Each Matrix worker, background operation, and handler/session acquisition
attempt SHALL receive at most one assigned credential candidate. Matrix workers
and Extron IN1804 handlers SHALL NOT read `credentials.local.json`, inspect
candidate lists, choose another credential candidate, advance credential
indexes, wrap candidate order, or commit successful credential memory.

Matrix credential fallback SHALL be authorized only by a structured
authentication outcome whose semantics explicitly confirm that the assigned
credential was rejected by the device on a supported authentication path, and
only when the operation is safe for fallback. An exception class alone,
including `AuthenticationError`, SHALL NOT authorize credential advancement.
Message text, localized authentication words, `auth`, `401`, `403`, timeout
text, connection text, malformed payloads, or generic failures SHALL NOT
authorize credential advancement.

Missing username, missing password, incomplete or invalid credential
configuration, and other local authentication/configuration precondition
failures that occur before the device confirms rejection of the assigned
credential SHALL NOT be treated as confirmed credential rejection and SHALL NOT
authorize credential fallback, even if they are represented by
`AuthenticationError`.

`ExtronIN1804Worker` and any new Matrix background operation SHALL classify
fallback-eligible authentication failure only from a structured outcome that
explicitly carries or unambiguously expresses confirmed device rejection of the
assigned credential. A caught `AuthenticationError` SHALL NOT by itself be
translated into fallback authority. Matrix workers and background operations
SHALL NOT search exception text for `auth`, `authentication`, `login`,
`password`, `401`, `403`, or similar strings. They SHALL NOT convert generic
connection, timeout, transport, negotiation, protocol, malformed response, or
command failures into authentication failures based on message text.

`BaseExtronMatrixHandler.connect()` or Matrix-specific replacement connection
logic SHALL preserve a structured failure category for each transport attempt.
It SHALL NOT determine final authentication classification by searching
aggregated exception strings for authentication-like words. Transport fallback
attempts within one Matrix connection operation SHALL use the same assigned
credential candidate. The handler and worker SHALL NOT select, inspect, or
advance to another credential candidate during transport fallback.

The final Matrix connection outcome SHALL be a structured confirmed
authentication failure only when structured failure semantics unambiguously
prove that the assigned credential was rejected by the device on a supported
authentication path. Timeout, connection refusal, socket failure,
SSH/Telnet negotiation failure, unsupported service, malformed protocol
response, and other transport/protocol failures SHALL remain non-authentication
failures. A mixed transport sequence containing ambiguous authentication and
non-authentication failures SHALL NOT authorize credential fallback unless the
final structured outcome is an unambiguous confirmed authentication rejection.

For Matrix route mutation, credential fallback SHALL be forbidden after the
state-changing route command was invoked, may have been delivered, or has an
ambiguous outcome.

Matrix persistent session identity SHALL include a non-secret credential
context revision or equivalent opaque token in addition to the assigned
candidate index. Candidate index alone SHALL NOT prove credential identity or
session reuse safety. Credential configuration changes SHALL publish a new
credential context revision for Matrix lifecycle purposes without exposing
username, password, profile name, or other secret credential values through
public context identity, signals, results, logs, or terminal output.

Matrix successful credential memory SHALL have these gates:

- an accepted, non-stale, final successful full Matrix refresh with parsed
  device data MAY save the assigned credential index as successful for that
  model/IP context;
- Matrix session acquisition, connect, login/authentication, or persistent
  session creation alone SHALL NOT save a successful credential index;
- successful Matrix route mutation SHALL NOT save or change successful
  credential memory in this structural change;
- quick/status refresh used as route reconciliation SHALL NOT introduce a new
  independent credential-memory semantic;
- stale Matrix success SHALL NOT save or change successful credential memory.

#### Scenario: Matrix candidates are resolved before network I/O
- **WHEN** a Matrix refresh, route mutation, or session acquisition needs credentials
- **THEN** application composition resolves the ordered credential candidates before Matrix network I/O starts

#### Scenario: Matrix worker receives one assigned candidate
- **WHEN** a Matrix worker or background Matrix operation starts with credential candidate N
- **THEN** it uses only candidate N
- **AND** it does not inspect or attempt candidate N+1

#### Scenario: Handler does not own fallback
- **WHEN** `ExtronIN1804Handler` encounters authentication, connection, protocol, or command failure
- **THEN** it reports the failure through the Matrix operation boundary
- **AND** it does not select another credential candidate itself

#### Scenario: Structured Matrix authentication may advance
- **WHEN** Matrix session acquisition returns a structured authentication failure that explicitly confirms the assigned credential was rejected by the device on a supported authentication path before any state-changing route command could have been sent
- **AND** another unattempted candidate remains
- **THEN** the application-owned credential policy may start the next candidate

#### Scenario: Confirmed credential rejection may advance
- **WHEN** the Matrix handler reports a structured authentication failure that explicitly represents confirmed rejection of the assigned credential by the device on a supported authentication path
- **AND** no state-changing route command could have been sent
- **THEN** the application may consider the next credential candidate

#### Scenario: Authentication precondition does not advance credentials
- **WHEN** a Matrix operation fails because required authentication input is missing, invalid, incomplete, or otherwise fails before the device confirms rejection of the assigned credential
- **THEN** the failure does not authorize credential fallback
- **AND** the application does not advance to another credential candidate
- **AND** missing username or password is not treated as confirmed credential rejection
- **AND** an `AuthenticationError` exception class alone is not sufficient fallback authority

#### Scenario: Matrix text does not advance credentials
- **WHEN** a Matrix failure contains text such as `auth`, `401`, or `403` but is not classified as a structured confirmed authentication failure
- **THEN** the application does not advance to another credential candidate

#### Scenario: Authentication word in connection error is non-authentication
- **WHEN** a Matrix connection or transport failure message contains the word `authentication`
- **AND** the structured failure semantics do not explicitly confirm device rejection of the assigned credential
- **THEN** the outcome remains non-authentication or otherwise non-fallback-authorizing
- **AND** credential fallback is not authorized

#### Scenario: Authentication-like generic text does not classify auth
- **WHEN** generic Matrix exception text contains `auth`, `authentication`, `login`, `password`, `401`, or `403`
- **AND** no structured outcome explicitly confirming device rejection of the assigned credential was produced
- **THEN** the worker and application do not classify it as a fallback-authorizing authentication failure
- **AND** the assigned credential candidate does not change

#### Scenario: Timeout remains transport failure
- **WHEN** a Matrix transport attempt ends with timeout
- **THEN** the outcome remains a non-authentication transport failure
- **AND** credential fallback is not authorized

#### Scenario: Connection and protocol failures remain non-authentication
- **WHEN** a Matrix transport attempt ends with connection refusal, socket failure, SSH/Telnet negotiation failure, unsupported service, or malformed protocol response
- **THEN** the outcome remains non-authentication
- **AND** credential fallback is not authorized from message text

#### Scenario: Same credential across Matrix transport fallback
- **WHEN** the Matrix handler tries multiple supported transport attempts for one connection operation
- **THEN** every attempt uses the same assigned credential candidate
- **AND** the handler and worker do not advance to another candidate during the transport sequence

#### Scenario: Mixed transport outcomes are conservative
- **WHEN** a Matrix transport sequence contains a mix of structured authentication-related and non-authentication failures
- **AND** the final outcome is not an unambiguous structured confirmed authentication rejection
- **THEN** credential fallback is not authorized

#### Scenario: Credential revision participates in session identity
- **WHEN** Matrix credential configuration changes while the selected candidate index remains the same
- **THEN** the Matrix credential context revision changes
- **AND** any persistent Matrix session from the previous revision is not reusable under the new revision
- **AND** no credential value is emitted in context identity, signals, results, logs, or terminal output

#### Scenario: Route mutation blocks fallback after possible send
- **WHEN** a Matrix route command was invoked, may have reached the transport, or has an ambiguous delivery outcome
- **THEN** the application does not advance credentials for that route operation
- **AND** it does not replay the route mutation with another candidate

#### Scenario: Accepted full Matrix refresh may cache credentials
- **WHEN** a full Matrix refresh produces a final successful parsed result
- **AND** that result is accepted by the current non-stale Matrix context
- **THEN** the application may save the assigned credential index as successful for that model/IP context

#### Scenario: Session acquisition alone does not cache credentials
- **WHEN** Matrix session acquisition, connect, login/authentication, or persistent session creation succeeds
- **AND** no accepted final successful full Matrix refresh has completed
- **THEN** the application does not save the assigned credential index as successful

#### Scenario: Successful route mutation does not cache credentials
- **WHEN** a Matrix route mutation succeeds
- **THEN** the application does not save or change successful credential memory because of that route mutation

#### Scenario: Route reconciliation does not cache credentials
- **WHEN** quick/status refresh runs as reconciliation after a route mutation
- **THEN** it does not introduce a new independent successful credential memory update

#### Scenario: Stale Matrix success does not cache credentials
- **WHEN** a Matrix operation succeeds after its Matrix context became stale
- **THEN** the application does not save its credential index as successful for the active context
