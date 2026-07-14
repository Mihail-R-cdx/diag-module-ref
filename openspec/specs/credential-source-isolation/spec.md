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
credentials.

#### Scenario: Authenticated handler receives no credentials
- **WHEN** an authentication-required handler is selected without a valid credential object
- **THEN** it returns a safe configuration/authentication-precondition error and does not substitute an operational default

#### Scenario: Unauthenticated handler is selected
- **WHEN** the selected handler contract does not require authentication
- **THEN** it can connect without a credential profile

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
most one terminal result or error.

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
