## Why

Device credentials are currently represented in production paths and risk-bearing
tracked artifacts, making accidental disclosure through Git, diagnostics, or
runtime observability possible. The application needs one explicit, local-only
credential source that preserves device-specific authentication without adding
third-party dependencies.

## What Changes

- Define a `CredentialProvider` boundary and a first `JsonCredentialProvider`
  implementation backed by an unencrypted, local-only `credentials.local.json`.
- Define named credential profiles, their JSON shape, deterministic path and
  profile resolution, validation, and safe configuration-error behavior.
- Route credentials from application/bootstrap code through existing worker,
  factory, and handler boundaries; retain explicit credential injection for
  callers and unit tests.
- Plan removal of hardcoded operational credential defaults and protection of
  credential-bearing tracked artifacts, diagnostic output, exceptions, status
  dictionaries, and worker results.
- Plan repository protection and migration material: `.gitignore`, a safe
  `credentials.example.json`, local setup documentation, secret scanning,
  history-review guidance, and credential-rotation guidance.
- Do not add dependencies or claim encryption: the initial JSON store is plain
  text, is excluded from Git, and is a migration step toward a future secure
  provider such as Windows Credential Manager.

## Capabilities

### New Capabilities

- `credential-source-isolation`: Local JSON credential profiles, provider
  contract, source precedence, validation, and explicit propagation to device
  authentication boundaries.
- `repository-secret-hygiene`: Tracked-secret remediation, redaction and
  non-disclosure rules, repository protection, and verification expectations.

### Modified Capabilities

- None. The repository has no archived primary specs under `openspec/specs/`;
  the active bootstrap change remains independent and is not altered here.

## Impact

Future implementation will affect application/bootstrap integration in
`gui/main_window.py`, `core/worker.py`, `core/te20_worker.py`,
`core/factory.py`, `core/base_handler.py`, and production protocol handlers,
plus relevant tests and documentation. It will add only a tracked template and
ignore rule; it will never create or track a real credential file. Runtime
changes will require operators to create a local credential file when their
selected device path requires authentication.
