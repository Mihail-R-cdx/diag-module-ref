## MODIFIED Requirements

### Requirement: Local credential-file repository protection
The implementation SHALL add `data.local.json` to `.gitignore` and
SHALL NOT create, add, or publish that file. It SHALL retain the retired
`credentials.local.json` filename in repository protection rules because an
existing workstation copy may still contain live secrets, even though production
runtime SHALL no longer read it. The implementation SHALL add only a tracked
`data.example.json` template whose values are non-operational placeholders and
whose schema matches the documented local format, and SHALL remove the superseded
tracked `credentials.example.json` template.

#### Scenario: Operator creates the canonical real local file
- **WHEN** an operator creates `data.local.json` from `data.example.json`
- **THEN** Git ignores the local file while the safe template remains trackable

#### Scenario: Retired local file remains protected
- **WHEN** an older workstation still contains `credentials.local.json`
- **THEN** repository ignore/protection rules continue to exclude that secret-bearing file
- **AND** runtime does not treat it as the canonical credential source

#### Scenario: Template is reviewed
- **WHEN** `data.example.json` is inspected or committed
- **THEN** it contains schema guidance and placeholders but no usable credential

### Requirement: Plain-text local-store documentation and migration
Documentation SHALL explain that `data.local.json` is an unencrypted local
credential store despite its generic filename, must be protected by local
filesystem permissions and excluded from backups/shares as appropriate, and
must be manually recreated when the application moves to another PC. It SHALL
include migration from the retired `credentials.local.json` filename,
history-review, and credential-rotation guidance, and it SHALL identify a future
secure provider as follow-up work rather than part of this change.

#### Scenario: New-machine setup
- **WHEN** an operator installs or copies the application to a new PC
- **THEN** the setup guide directs the operator to create a new `data.local.json` from the safe template and does not expect the old file to travel through Git

#### Scenario: Plain-text limitation is reviewed
- **WHEN** a maintainer reads the credential setup documentation
- **THEN** it states that JSON is not encrypted and lists local protection and future-migration limitations
