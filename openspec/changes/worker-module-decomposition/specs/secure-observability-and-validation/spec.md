## MODIFIED Requirements

### Requirement: Redacted protocol diagnostics
Handler command logging and worker error handling SHALL redact known usernames,
passwords, authentication tokens, sensitive request payloads, and sensitive
response bodies before they are emitted to terminal/debug output. New tests and
new documentation SHALL use synthetic credentials only. PCS4i Telnet
authentication, Telnet SIS commands, HTTP outlet-name enrichment, PDU command
outcomes, unsupported-operation outcomes, and public diagnostics SHALL never
expose the real assigned password. Worker module decomposition SHALL preserve
redaction behavior when `WorkerSignals`, worker-secret collection, safe-error
formatting, and worker error emission helpers move into shared worker
infrastructure.

#### Scenario: Handler logs a credential-bearing request
- **WHEN** a supported Huawei, Polycom, Aten, or PCS4i handler records a request containing credentials or a token
- **THEN** the recorded terminal message replaces sensitive content with a redaction marker

#### Scenario: Worker reports a credential-bearing exception
- **WHEN** a worker catches an exception whose text contains the credential it used
- **THEN** its emitted error message masks that credential before reaching the GUI path

#### Scenario: PCS4i prompt contains asterisks
- **WHEN** PCS4i emits `Password:**********************`
- **THEN** public diagnostics may include the device-emitted asterisks only when useful
- **AND** the actual password sent by the application remains redacted everywhere

#### Scenario: PCS4i password is not logged during second send
- **WHEN** PCS4i requires the same assigned password to be sent a second time
- **THEN** no stdout, debug log, GUI message, exception, public diagnostic, test assertion, or validation report contains the password value

#### Scenario: Decomposed worker error remains redacted
- **WHEN** a worker moved into `core/workers/` emits an error, result, terminal log, stdout diagnostic, or completion-related public payload
- **THEN** credentials, Session IDs, cookies, CSRF tokens, and other known secrets are redacted at least as strictly as before the move

### Requirement: OpenSpec change completion
A future OpenSpec change SHALL be ready to archive only when its required
artifacts, requirements, scenarios, implementation status, strict OpenSpec
validation, relevant offline tests, and documentation checks agree. The change
SHALL explicitly describe any runtime behavior change and SHALL not hide
unrelated fixes outside its scope. A worker-module decomposition change SHALL
also provide evidence that the refactor is structural and that production
worker behavior, signal contracts, credential ownership, fallback semantics,
mutation safety, DMP lifecycle, GUI-threading, and redaction did not change.

#### Scenario: Completed future change
- **WHEN** a change has completed its required artifacts and implementation
- **THEN** maintainers can validate it with `openspec validate --all --strict` and archive it through the standard OpenSpec command

#### Scenario: Worker decomposition completion evidence
- **WHEN** the worker decomposition implementation is ready for review
- **THEN** the change evidence identifies moved modules, compatibility exports, patch/mock strategy, focused regression tests, full offline suite result, and strict OpenSpec validation result
- **AND** it states whether any runtime behavior changed
