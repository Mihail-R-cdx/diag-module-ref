## MODIFIED Requirements

### Requirement: Central credential-provider boundary
The application SHALL define a `CredentialProvider` contract owned by the
application/core boundary and a `JsonCredentialProvider` implementation. A
protocol handler, factory, or worker SHALL NOT parse `data.local.json`
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
`data.local.json` from the application/project root adjacent to the
launch entry point, resolved independently of the current working directory.
The provider SHALL use only Python's standard `json` module and SHALL introduce
no third-party dependency. The default provider SHALL NOT probe, merge, or fall
back to the retired `credentials.local.json` filename.

#### Scenario: Application starts from another working directory
- **WHEN** the program is launched with a different current working directory
- **THEN** the provider resolves the same application-root local file and does not read an unrelated file from that directory

#### Scenario: Valid local JSON is available
- **WHEN** `data.local.json` contains a valid selected profile
- **THEN** `JsonCredentialProvider` returns the profile for application use

#### Scenario: Only retired legacy filename exists
- **GIVEN** `data.local.json` is absent
- **AND** a retired `credentials.local.json` file exists in the application root
- **WHEN** default credential resolution begins
- **THEN** the provider treats the canonical local configuration as missing
- **AND** it does not read or migrate the retired file
- **AND** no device network I/O starts from that missing configuration

### Requirement: Safe local-configuration failures
The provider SHALL distinguish missing-file, invalid-JSON, invalid-schema, and
missing-profile failures from device authentication failures. Messages surfaced
to GUI, logs, workers, and exceptions SHALL identify the configuration problem
without disclosing a password, token, or other credential material.

#### Scenario: Local file is missing
- **WHEN** authentication is required and `data.local.json` is absent
- **THEN** the application reports an actionable configuration error referring to the canonical local setup and does not start device authentication

#### Scenario: Local JSON is syntactically invalid
- **WHEN** JSON parsing fails
- **THEN** the application reports a distinct safe configuration error rather than an authentication failure

### Requirement: Extron DMP 64 Plus credential ownership
Extron DMP 64 Plus credential selection, credential fallback, and successful
credential memory SHALL remain owned by the application/composition layer. The
application SHALL resolve and validate the ordered credential candidate
sequence before a DMP session acquisition attempt starts. One DMP worker or
session acquisition attempt SHALL receive at most one assigned credential. The
DMP handler and polling worker SHALL NOT read the local credential store or provider storage directly, inspect
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
and Extron IN1804 handlers SHALL NOT read the local credential store or provider storage directly, inspect
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

### Requirement: DMP controller credential delegation

A DMP-specific application polling controller MAY coordinate Extron DMP 64 Plus credential attempts only through the existing application/composition credential boundary. It SHALL NOT read credential-provider storage directly, SHALL NOT become an independent credential source, and SHALL NOT persist credential values.

The application credential boundary SHALL remain authoritative for ordered candidate resolution, exact device/IP successful-index memory, valid starting candidate selection, and monotonic no-wrap advancement. The DMP controller MAY request those decisions through focused callbacks/providers and MAY request successful-index persistence only after the DMP-specific first-complete-snapshot success gate is satisfied.

Each DMP worker and handler SHALL receive only one assigned credential candidate per attempt. Transport/session work within that attempt SHALL use the same assigned credential. Credential fallback SHALL remain distinct from transport/session failure handling.

Public DMP controller contexts, signals, logs, errors, and status data SHALL NOT contain credential values, candidate dictionaries, profile names where they disclose credential configuration, or handler/session/transport objects.

#### Scenario: DMP controller obtains candidates through application policy
- **WHEN** a DMP polling request needs credentials
- **THEN** the controller receives the ordered candidate sequence through the application/composition credential boundary
- **AND** it does not read the local credential store or provider storage directly

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
