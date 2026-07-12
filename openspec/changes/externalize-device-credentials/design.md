## Context

The current application keeps device credential material in GUI-managed
structures and passes it into device-specific workers. `core/worker.py` and
`core/te20_worker.py` construct handlers directly or through
`core/factory.py`; the factory and base/individual handlers also expose
credential defaults. The production GUI wires TE20, TE40, Bar 310, Polycom,
Biamp, Extron, and Aten paths. Existing diagnostics include print/log/error
and serialized-output paths that must be assessed for disclosure rather than
treated as safe by default.

The repository contains a mix of production code, tests, documentation,
reference drivers, tooling, logs, and generated diagnostic artifacts. The
initial repository scan found credential-flow and observability risk categories
in each of these areas. This design deliberately records no secret value.

The user-selected first store is a plain-text, unencrypted local JSON file.
It must be ignored by Git, read only through the standard-library `json`
module, and introduce no new runtime dependency.

## Goals / Non-Goals

**Goals:**

- Separate credential acquisition from protocol code with `CredentialProvider`
  and `JsonCredentialProvider`.
- Resolve a predictable `credentials.local.json` beside the application entry
  point, not from a process current directory.
- Support named profiles and device-model selection, username/password,
  password-only, and unauthenticated device contracts.
- Preserve direct credential injection for callers and tests, with direct input
  taking priority over provider output.
- Remove operational hardcoded defaults, avoid credential persistence in public
  worker/status results, and redact all observability boundaries.
- Make the JSON limitation, Git protection, migration, rotation, and future
  secure-provider path explicit.

**Non-Goals:**

- Implement these production changes in this planning change.
- Create a real `credentials.local.json`, alter `.gitignore`, add the example
  JSON, remove a value, modify tests, or add dependencies at this stage.
- Encrypt JSON, use `.env`, `python-dotenv`, `keyring`, `cryptography`, a vault
  SDK, Base64-as-encryption, or Windows Credential Manager now.
- Read JSON in every worker or handler, introduce a hidden global provider, or
  use one global password for every device.

## Decisions

### Provider boundary and target flow

Add a small provider contract at the application/core composition boundary and
implement `JsonCredentialProvider` there. The bootstrap/application layer owns
the provider instance and resolves credentials before creating or restarting a
worker. The target flow is:

```text
application-root/credentials.local.json
        -> JsonCredentialProvider
        -> application / GUI request composition
        -> worker or ProtocolFactory
        -> protocol handler
```

Workers, factories, and handlers receive credential data explicitly through
their existing inputs and do not know the file format or location. This keeps
tests able to inject values directly and makes a later secure provider a
composition change rather than a handler rewrite. A global singleton was
rejected because it hides source selection and weakens isolation/testing.

### Store location, schema, and profile resolution

The local file belongs at the application/project root beside `main.py`, named
exactly `credentials.local.json`. The resolver derives this root from a stable
module/entry-point path; it never uses `Path.cwd()` for the default location.
The tracked example uses the same versioned document shape:

```json
{
  "version": 1,
  "profiles": {
    "profile-name": {"auth_mode": "username_password", "username": "<placeholder>", "password": "<placeholder>"}
  },
  "device_profiles": {"device-model": "profile-name"}
}
```

`auth_mode` defines username/password, password-only, or unauthenticated
semantics. The provider validates the root, version, profile object, mode,
required fields, and model mapping before network I/O. Explicit credentials
provided to a caller/test win; otherwise an explicit requested profile wins;
otherwise the selected device model resolves through `device_profiles`. There
is no global fallback. Missing file, malformed JSON, invalid structure,
missing profile, and missing field use separate safe configuration errors;
they are not device authentication failures.

### Integration and compatibility

The implementation inventory starts with `gui/main_window.py`,
`core/worker.py`, `core/te20_worker.py`, `core/factory.py`,
`core/base_handler.py`, and all production handlers. It replaces operational
defaults while preserving device-specific constructor compatibility where
feasible. Authentication-required handlers validate required credentials
before connection; unauthenticated contracts receive no credentials. Each
active request retains its own device/IP/profile context, and only resolved
credentials travel into its worker/handler path.

Provider failures are surfaced through the existing GUI/worker error path as
configuration errors. Authentication failures remain device outcomes. No
worker result, status dictionary, diagnostic output, exception, print, log,
or serialized artifact may expose resolved credential values.

All current production device handlers require explicit authentication before
network I/O. Although the provider supports an `unauthenticated` profile
contract for a future handler, no active Huawei, Polycom, Biamp, Extron, or
Aten path is declared unauthenticated merely because a password is blank.

### Repository protection and remediation

Implementation adds only `.gitignore` protection and a placeholder
`credentials.example.json`; it does not generate the real file. A safe scanner
will inventory all tracked files and report only paths/categories. Suspected
previous exposure is not asserted without history evidence. If an operational
credential is confirmed, remediation includes removal, review of Git history,
and possible rotation; history rewriting requires separate approval and is not
part of the default implementation.

The JSON store remains plain text. Documentation must tell operators to limit
filesystem access, avoid synchronizing it to untrusted locations, and create a
new local file on a new PC. A future Windows Credential Manager provider can
reuse the contract without changing handlers.

### Rejected alternatives

- `.env`/`python-dotenv`: adds a dependency and lacks the requested structured
  profile model.
- Direct JSON reads in handlers or each worker: duplicates logic and couples
  protocols to storage.
- Tracked `credentials.json`, passwords in a model registry, and hardcoded
  defaults: risk source-control exposure and ambiguous selection.
- Adjacent encryption key, Base64, immediate enterprise vault, and Windows
  Credential Manager: do not satisfy the stated first-step scope or security
  boundary.

## Risks / Trade-offs

- [Plain-text JSON can be read by someone with local filesystem access] ->
  document permissions and storage limitations; plan a future secure provider.
- [Removing defaults exposes incomplete device configuration] -> fail before
  network I/O with a precise, redacted configuration error and provide a safe
  template/setup guide.
- [Credential refactoring touches multiple workers and handlers] -> inventory
  every production path, retain explicit test injection, and migrate in small
  verified steps.
- [Tracked history may contain prior exposure] -> inspect history safely and
  rotate confirmed operational credentials; do not echo values or rewrite
  history without separate approval.
- [Existing logs and artifacts have broad formats] -> centralize redaction,
  test every public sink, and avoid treating a scan result as proof of safety.

## Migration Plan

1. Complete the implementation inventory and safe tracked-file scan.
2. Add provider/model code, ignore rule, safe example, documentation, and
   redaction coverage without committing a real local file.
3. Migrate bootstrap, GUI, workers, factory, and handlers in request-scoped
   increments; remove defaults only after their replacement path is covered.
4. Operators create a fresh local file from the template after upgrading or on
   each new PC; the file is never transferred by Git.
5. Run focused offline tests, full offline suite, safe secret scan, and strict
   OpenSpec validation. Roll back by restoring the previous application build;
   preserve and protect the operator's local file, which remains outside Git.
6. Review repository history and rotate any confirmed prior operational
   credentials under the organization's incident process. Reconsider a secure
   provider only if a future product decision changes the current local-JSON
   storage approach.

## Open Questions

- Which project-owned component will expose the final application-root path to
  the composition layer without importing GUI code into core?
- Which existing device model labels require aliases in `device_profiles`, and
  which production handlers are genuinely unauthenticated?
- Which detected tracked diagnostic artifacts are intentional fixtures versus
  material requiring removal and rotation after value-safe review?
- What local filesystem/backup policy is required for operator workstations?
