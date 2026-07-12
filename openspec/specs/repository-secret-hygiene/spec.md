# repository-secret-hygiene Specification

## Purpose
TBD - created by archiving change externalize-device-credentials. Update Purpose after archive.
## Requirements
### Requirement: Local credential-file repository protection
The implementation SHALL add `credentials.local.json` to `.gitignore` and
SHALL NOT create, add, or publish that file. It SHALL add only a tracked
`credentials.example.json` template whose values are non-operational
placeholders and whose schema matches the documented local format.

#### Scenario: Operator creates a real local file
- **WHEN** an operator creates `credentials.local.json` from the template
- **THEN** Git ignores the local file while the safe template remains trackable

#### Scenario: Template is reviewed
- **WHEN** the example JSON is inspected or committed
- **THEN** it contains schema guidance and placeholders but no usable credential

### Requirement: Tracked-secret remediation inventory
Before remediation, maintainers SHALL inventory credential flows and
credential-like material across production code, tests, fixtures, tools,
examples, reference drivers, documentation, logs, serialized diagnostic
artifacts, and all tracked Git files. Findings SHALL be recorded only by path,
secret category, exposure risk, removal need, and possible rotation need; the
secret value SHALL never be copied into change artifacts, tests, logs, or
reports.

#### Scenario: A credential-like value is found
- **WHEN** a scan identifies a potentially operational credential in a tracked file
- **THEN** the remediation record identifies its path and risk category without displaying its value

#### Scenario: No tracked values remain after remediation
- **WHEN** the agreed repository secret scan completes after implementation
- **THEN** it reports the result without echoing matched secret values

### Requirement: Redacted observability and serialized outputs
Credential values, authentication headers, tokens, session identifiers, and
credential-bearing request or response bodies SHALL be redacted before they
reach `print`, logging, GUI debug output, exceptions, application logs, worker
results, status dictionaries, test output, or serialized diagnostic artifacts.
Redaction SHALL preserve enough non-sensitive context to diagnose the failure.

#### Scenario: Credential-bearing exception occurs
- **WHEN** a handler, worker, or provider catches an exception containing a credential value
- **THEN** the user-visible and logged message replaces the sensitive portion with a redaction marker

#### Scenario: Worker reports a result
- **WHEN** a device worker emits status or result data after authenticated work
- **THEN** the public result and status dictionary contain no credential material

### Requirement: Plain-text local-store documentation and migration
Documentation SHALL explain that `credentials.local.json` is an unencrypted
local store, must be protected by local filesystem permissions and excluded
from backups/shares as appropriate, and must be manually recreated when the
application moves to another PC. It SHALL include migration, history-review,
and credential-rotation guidance, and it SHALL identify a future secure
provider as follow-up work rather than part of this change.

#### Scenario: New-machine setup
- **WHEN** an operator installs or copies the application to a new PC
- **THEN** the setup guide directs the operator to create a new local credential file and does not expect the old file to travel through Git

#### Scenario: Plain-text limitation is reviewed
- **WHEN** a maintainer reads the credential setup documentation
- **THEN** it states that JSON is not encrypted and lists local protection and future-migration limitations

### Requirement: Offline verification and safe remediation completion
Implementation verification SHALL include focused provider and redaction tests,
repository secret scanning or an equivalent safe check, strict OpenSpec
validation, and the offline test suite. Hardware tools SHALL remain opt-in;
the change SHALL not require live device credentials for normal automated
verification.

#### Scenario: Offline verification runs
- **WHEN** maintainers run the documented offline validation commands
- **THEN** provider, redaction, and repository checks run without contacting live equipment or requiring a real credential file
