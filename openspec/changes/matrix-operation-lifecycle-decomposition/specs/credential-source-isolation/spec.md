## ADDED Requirements

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

Matrix credential fallback SHALL be authorized only by a structured confirmed
authentication failure and only when the operation is safe for fallback. Message
text, localized authentication words, `auth`, `401`, `403`, timeout text,
connection text, malformed payloads, or generic failures SHALL NOT authorize
credential advancement.

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
- **WHEN** Matrix session acquisition returns a structured confirmed authentication failure before any state-changing route command could have been sent
- **AND** another unattempted candidate remains
- **THEN** the application-owned credential policy may start the next candidate

#### Scenario: Matrix text does not advance credentials
- **WHEN** a Matrix failure contains text such as `auth`, `401`, or `403` but is not classified as a structured confirmed authentication failure
- **THEN** the application does not advance to another credential candidate

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
