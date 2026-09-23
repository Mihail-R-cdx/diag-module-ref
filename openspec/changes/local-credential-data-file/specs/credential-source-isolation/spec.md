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
