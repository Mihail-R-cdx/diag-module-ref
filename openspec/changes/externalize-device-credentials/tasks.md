## 1. Discovery and containment inventory

- [x] 1.1 Inventory every production credential flow from `gui/main_window.py` through `core/worker.py`, `core/te20_worker.py`, `core/factory.py`, and each production handler; record only component, path, authentication mode, and handoff boundary.
- [x] 1.2 Inventory hardcoded credential-like values and operational defaults across all tracked files, including tests, fixtures, tools, examples, reference drivers, documentation, logs, and serialized artifacts; never copy values into an issue, test, or report.
- [x] 1.3 Classify each finding by secret category, exposure risk, removal need, possible rotation need, and whether it is production behavior, an intentional synthetic fixture, or historical/generated material.

## 2. Repository protection and operator material

- [x] 2.1 Add `credentials.local.json` to `.gitignore` and verify Git ignores it without creating a real local file.
- [x] 2.2 Add a safe root-level `credentials.example.json` with version, named profiles, device-profile mapping, authentication modes, and clearly non-operational placeholders.
- [x] 2.3 Document local JSON setup, application-root location, profile selection, per-new-PC setup, and the rule that a real local file is never committed or copied through Git.
- [x] 2.4 Document plain-text storage limitations and workstation filesystem/backup protection recommendations; state explicitly that the first provider does not encrypt JSON.
- [x] 2.5 Add safe Git-history inspection and credential-rotation guidance for confirmed prior exposure, including the requirement for separate approval before any history rewrite.

## 3. Credential model and provider foundation

- [x] 3.1 Define a credential model covering username/password, password-only, and unauthenticated device contracts without storing values in a model registry.
- [x] 3.2 Define the `CredentialProvider` contract at the application/core composition boundary, including safe configuration-error types and replacement expectations.
- [x] 3.3 Implement `JsonCredentialProvider` using only the standard `json` module and an injected/resolved local-file path; add no dependency.
- [x] 3.4 Implement application-root path resolution anchored to `main.py` or an equivalent stable module path, independent of `Path.cwd()`.
- [x] 3.5 Implement versioned JSON root, profile, authentication-mode, required-field, and device-profile-mapping validation.
- [x] 3.6 Implement deterministic profile resolution: direct test/caller credentials, then explicit requested profile, then selected-model mapping, with no global operational fallback.
- [x] 3.7 Implement distinct, redacted errors for missing local file, invalid JSON, invalid structure, missing profile, and missing required field.

## 4. Application, worker, factory, and handler integration

- [x] 4.1 Instantiate and own the provider at the application/bootstrap composition point without introducing a hidden global singleton.
- [x] 4.2 Integrate profile selection with `gui/main_window.py` request context so model, IP, profile, and credentials remain scoped to the active request.
- [x] 4.3 Update `core/worker.py` and `core/te20_worker.py` to accept resolved credentials explicitly while retaining direct injection for unit tests.
- [x] 4.4 Update `core/factory.py` to pass only explicit resolved credentials and to stop substituting operational default values.
- [x] 4.5 Update `core/base_handler.py` and production Huawei, Polycom, Biamp, Extron, and Aten handlers to validate their own required authentication inputs before network I/O.
- [x] 4.6 Preserve or explicitly define unauthenticated-handler behavior and password-only authentication without forcing unused fields into every handler.
- [x] 4.7 Remove hardcoded operational credential defaults and credential-bearing model-registry data only after all corresponding provider paths are verified.

## 5. Observability and tracked-artifact remediation

- [x] 5.1 Define one reusable redaction policy for credential values, tokens, session identifiers, authentication headers, and sensitive request/response bodies.
- [x] 5.2 Apply redaction to handler debug/print/log paths, GUI debug output, worker errors, application logs, and exception formatting while preserving non-sensitive diagnostic context.
- [x] 5.3 Ensure worker results, status dictionaries, callbacks, and serialized diagnostic artifacts omit credential fields and values.
- [x] 5.4 Remediate confirmed credential-bearing tracked material according to the inventory, replacing only with safe synthetic examples where documentation or tests need structure.
- [x] 5.5 Review tools, reference drivers, fixtures, logs, and documentation separately from production code; keep hardware tools opt-in and do not turn secret scanning into value disclosure.

## 6. Focused automated verification

- [x] 6.1 Add unit tests for successful JSON loading and valid username/password profile resolution using synthetic data.
- [x] 6.2 Add unit tests for password-only and unauthenticated profile contracts.
- [x] 6.3 Add unit tests for invalid JSON, invalid root/profile structure, and missing required fields with safe error text.
- [x] 6.4 Add unit tests for missing local file and unknown/missing profile behavior before network I/O.
- [x] 6.5 Add unit tests proving application-root path resolution remains stable from a different working directory.
- [x] 6.6 Add unit tests proving direct caller/test credential injection works without a local file and wins over provider output.
- [x] 6.7 Add focused GUI/application tests for model-to-profile selection and configuration-error presentation without rendering secret values.
- [x] 6.8 Add factory/worker/handler integration tests for explicit credential propagation across TE20, TE40, Bar 310, Polycom, Biamp, Extron, and Aten paths as applicable.
- [x] 6.9 Add tests that required-authentication handlers reject absent credentials without an `admin/admin`-style fallback.
- [x] 6.10 Add tests that unauthenticated device paths can start without credentials when their contracts permit it.
- [x] 6.11 Add redaction tests for logs, print/debug output, exceptions, worker results, and status dictionaries using synthetic secrets only.
- [x] 6.12 Add regression tests proving a provider replacement reaches workers/handlers without coupling them to JSON implementation details.

## 7. Verification, migration, and follow-up

- [x] 7.1 Run a safe repository secret scan or equivalent verification over all tracked files; report only paths, categories, and pass/fail status.
- [x] 7.2 Run the complete offline test suite with no real credential file and no live hardware: `python -m unittest discover -s tests -p "test_*.py"`.
- [ ] 7.3 Perform opt-in manual GUI verification for authenticated, configuration-error, unauthenticated, and redacted-error states using non-production credentials only.
- [x] 7.4 Verify a clean/new-PC setup requires a fresh ignored local JSON file and never creates or retrieves one through Git.
- [x] 7.5 Verify documentation, example JSON, tests, OpenSpec artifacts, and reports contain no real secret values and accurately describe plain-text storage.
- [ ] 7.6 Review Git history under approved incident guidance, rotate any confirmed previously exposed operational credentials, and document only the remediation status.
- [x] 7.7 Run `openspec validate externalize-device-credentials --strict` and resolve every artifact-structure or scenario inconsistency.
- [ ] 7.8 Propose a separate future OpenSpec change for Windows Credential Manager or another approved secure provider after this JSON migration is stable.
