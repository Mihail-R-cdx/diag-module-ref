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
ambiguous outcome. Successful credential memory SHALL be updated only from an
accepted, non-stale, final successful Matrix operation according to the
existing application-owned policy.

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

#### Scenario: Route mutation blocks fallback after possible send
- **WHEN** a Matrix route command was invoked, may have reached the transport, or has an ambiguous delivery outcome
- **THEN** the application does not advance credentials for that route operation
- **AND** it does not replay the route mutation with another candidate

#### Scenario: Stale Matrix success does not cache credentials
- **WHEN** a Matrix operation succeeds after its Matrix context became stale
- **THEN** the application does not save its credential index as successful for the active context

#### Scenario: Accepted Matrix success may cache credentials
- **WHEN** a Matrix operation produces a final successful result accepted by the current non-stale Matrix context
- **THEN** the application may save the assigned credential index according to the existing successful credential policy
