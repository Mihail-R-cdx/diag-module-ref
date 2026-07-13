## ADDED Requirements

### Requirement: Redacted protocol diagnostics
Handler command logging and worker error handling SHALL redact known usernames,
passwords, authentication tokens, sensitive request payloads, and sensitive
response bodies before they are emitted to terminal/debug output. New tests and
new documentation SHALL use synthetic credentials only.

#### Scenario: Handler logs a credential-bearing request
- **WHEN** a supported Huawei or Polycom handler records a request containing credentials or a token
- **THEN** the recorded terminal message replaces sensitive content with a redaction marker

#### Scenario: Worker reports a credential-bearing exception
- **WHEN** a worker catches an exception whose text contains the credential it used
- **THEN** its emitted error message masks that credential before reaching the GUI path

### Requirement: Offline verification boundary
The repository SHALL keep normal automated verification offline. Hardware
network probes and device-mutating tools SHALL remain opt-in and SHALL not be
required for the offline test suite.

#### Scenario: Offline validation
- **WHEN** maintainers run `python -m unittest discover -s tests -p "test_*.py"`
- **THEN** the suite exercises repository tests without requiring live AV equipment

### Requirement: OpenSpec change completion
A future OpenSpec change SHALL be ready to archive only when its required
artifacts, requirements, scenarios, implementation status, strict OpenSpec
validation, relevant offline tests, and documentation checks agree. The change
SHALL explicitly describe any runtime behavior change and SHALL not hide
unrelated fixes outside its scope.

#### Scenario: Completed future change
- **WHEN** a change has completed its required artifacts and implementation
- **THEN** maintainers can validate it with `openspec validate --all --strict` and archive it through the standard OpenSpec command
