## MODIFIED Requirements

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

For automatic room one-shot diagnostics, authoritative diagnostic usability and
successful-credential persistence SHALL be evaluated independently. A
model-specific optional-enrichment failure MAY still yield an explicitly
approved usable room diagnostic outcome without proving that the assigned
credential completed the model-specific successful-credential boundary. Such
an optional-enrichment failure SHALL NOT itself authorize credential fallback,
SHALL NOT by itself cache a newly attempted candidate as successful, and SHALL
NOT overwrite successful-candidate memory from a prior proven operation.

For Polycom room one-shot acquisition specifically, authoritative HTTPS status
success followed by failure of the optional SSH enrichment SHALL yield usable
room diagnostic data with a structured warning rather than a terminal room
failure. The generic legacy rule for a partial result followed by a later
failure SHALL NOT convert that explicitly approved room-only
optional-enrichment outcome into a GUI/room error. This exact warning outcome
SHALL NOT persist a newly attempted Polycom candidate as successful. Existing
successful-candidate memory for the exact model/IP, if any, SHALL remain
unchanged by the warning outcome.

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
- **AND** the Polycom room one-shot warning outcome defined below is an explicit exception that does not persist a newly attempted candidate

#### Scenario: Failed attempt is not a result
- **WHEN** a worker receives an authentication or non-authentication failure
- **THEN** the worker emits an error signal
- **AND** it does not emit a final result containing an error description

#### Scenario: Partial result is followed by failure
- **WHEN** a diagnostic path emits a partial result and a later required parsing, transport, protocol, or non-optional acquisition stage fails
- **THEN** the candidate is not cached as successful
- **AND** no final non-partial result or success dialog is produced
- **AND** the GUI enters an error state
- **AND** this generic legacy scenario does not override an explicitly approved room one-shot optional-enrichment outcome

#### Scenario: Polycom room one-shot SSH enrichment is unavailable
- **GIVEN** Polycom room one-shot acquisition has accepted authoritative HTTPS diagnostic status
- **WHEN** the optional SSH enrichment later fails
- **THEN** the exact Polycom room row keeps the authoritative HTTPS data as usable
- **AND** the room adapter returns usable success with a structured warning rather than terminal failure
- **AND** the optional SSH failure does not start another credential candidate
- **AND** the room row does not enter the generic legacy partial-result error state solely because that optional enrichment failed

#### Scenario: Polycom room warning does not persist a new credential
- **GIVEN** a Polycom room one-shot attempt used a candidate that was not already proven successful for the exact model/IP context
- **AND** authoritative HTTPS diagnostic status succeeded
- **WHEN** optional SSH enrichment fails
- **THEN** the room row remains usable with warning
- **AND** the newly attempted candidate is not cached as successful
- **AND** prior successful-candidate memory, if any, is not overwritten or cleared by this outcome

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
