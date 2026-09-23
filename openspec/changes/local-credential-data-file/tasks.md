# Tasks: Local credential data file

## 1. Architecture

- [x] 1.1 Define `data.local.json` as the canonical application-root credential store.
- [x] 1.2 Define `data.example.json` as the tracked safe template.
- [x] 1.3 Preserve `credentials.local.json` only as a retired ignored sensitive filename; runtime fallback to it is forbidden.
- [x] 1.4 Keep provider/schema/fallback/redaction architecture unchanged.

## 2. Implementation

- [ ] 2.1 Change the provider default path to `data.local.json` and update safe missing-file guidance.
- [ ] 2.2 Rename the tracked template to `data.example.json` without changing its schema or introducing usable credentials.
- [ ] 2.3 Update `.gitignore`, Graphify/local-corpus exclusions, and relevant operator documentation; keep the legacy local filename protected.
- [ ] 2.4 Update focused tests so default-path, missing-file, alternate-CWD, schema, and secret-hygiene behavior use the canonical new names.
- [ ] 2.5 Verify the provider does not fall back to `credentials.local.json` when `data.local.json` is absent.

## 3. Validation and completion

- [ ] 3.1 Run focused credential-provider and repository-secret-hygiene tests.
- [ ] 3.2 Run the full offline Python test suite.
- [ ] 3.3 Run `.\openspec.cmd validate local-credential-data-file --strict` and `.\openspec.cmd validate --all --strict`.
- [ ] 3.4 Run `git diff --check` and `git diff --cached --check`.
- [ ] 3.5 Perform independent validation on the exact published remote HEAD.
- [ ] 3.6 Because this change MODIFIES root requirements, perform disposable archive-applicability validation before `READY FOR ARCHIVE`.
- [ ] 3.7 Archive only after a permitting independent verdict, then repeat strict-all, full offline tests, Git checks, and archive/root-spec diff review before merge.
