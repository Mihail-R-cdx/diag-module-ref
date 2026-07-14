## MODIFIED Requirements

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

## ADDED Requirements

### Requirement: Ordered credential candidates and authentication fallback
The credential boundary SHALL expose an ordered sequence of request-scoped
credential candidates while preserving the existing one-candidate resolution
contract. Explicit credentials and an explicit profile SHALL each yield one
candidate. The complete candidate sequence SHALL be validated before it is
given to a worker. The existing retry mechanism SHALL try a later candidate
only after a confirmed authentication failure, SHALL stop for a
non-authentication error, SHALL retain a successful candidate index for the
same device/IP context, and SHALL emit one safe terminal authentication error
after exhaustion.

#### Scenario: Legacy provider is used
- **WHEN** a provider implements only the existing one-candidate method
- **THEN** request composition receives a one-element candidate sequence

#### Scenario: Authentication failure advances the chain
- **WHEN** a worker reports a confirmed authentication failure before the final candidate
- **THEN** the existing retry mechanism starts exactly one next attempt

#### Scenario: Non-authentication failure stops the chain
- **WHEN** an attempt fails with timeout, transport, SSL, parsing, or protocol error
- **THEN** no next credential candidate is started

#### Scenario: Chain is exhausted
- **WHEN** every candidate fails authentication
- **THEN** no additional worker is created and the user receives one safe terminal authentication error

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
