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
username/password, password-only, or unauthenticated. The provider SHALL
reject an invalid root shape, unknown mode, missing required field, or invalid
profile mapping with a safe configuration error that does not include secret
values.

#### Scenario: Profile has required fields
- **WHEN** a username/password profile includes both required fields
- **THEN** the provider returns a credential object with that authentication mode

#### Scenario: Required password is missing
- **WHEN** a selected authenticated profile omits its required password field
- **THEN** no network connection starts and the caller receives a safe configuration error

#### Scenario: JSON structure is invalid
- **WHEN** the local file root or profile structure does not match the documented schema
- **THEN** the provider rejects it with a configuration error that names no credential value

### Requirement: Profile selection and source priority
Credential resolution SHALL use an explicit profile requested by the caller
when present; otherwise it SHALL use the selected device model's local mapping.
Credentials explicitly supplied by a caller or unit test SHALL take documented
priority over a provider result. An unmapped device or unknown profile SHALL
produce a safe configuration error rather than selecting a global default.

#### Scenario: Explicit credentials take priority
- **WHEN** a caller provides credentials and a local profile is also configured
- **THEN** the explicitly supplied credentials are used for that request

#### Scenario: Device model selects a profile
- **WHEN** no explicit profile is requested and the selected device model has a local profile mapping
- **THEN** the mapped profile is resolved deterministically

#### Scenario: Selected profile is absent
- **WHEN** a requested or mapped profile does not exist
- **THEN** the request stops before network I/O with a safe configuration error

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
