# Verification report: inventory-driven-diagnostic-dispatch

## Verdict

CHANGES REQUIRED.

Archive permitted: no.
Merge permitted: no.

## Repository and PR

- Repository: `Mihail-R-cdx/diag-module-ref`
- PR: `#21` (`Define inventory-driven diagnostic dispatch`)
- PR state: open
- Draft: true
- Mergeability: mergeable
- Base branch: `master`
- Base SHA: `d68e746fe644cd522555378b6bf00c9f5d59214f`
- Feature branch: `agent/inventory-driven-diagnostic-dispatch`
- Expected source SHA: `47ec04e4abae90a6763c18817d2e646844b54f81`
- Actual validated source SHA: `47ec04e4abae90a6763c18817d2e646844b54f81`
- Source commit subject: `Fix reachability preconditions and UI ownership`
- Approved architecture base commit: `4c7a26e1e1fcea1f15b5be6c3647812c3588ef44`
- Validation worktree: `C:\root folder\temp\diag module agent mode\diag-module-ref\.worktrees\validation-inventory-dispatch-47ec04e4`
- Archive-check worktree: `C:\root folder\temp\diag module agent mode\diag-module-ref\.worktrees\archive-check-inventory-dispatch-47ec04e4`
- Validation HEAD/source equality: yes
- Initial validation worktree status: clean

## Toolchain

- Python executable: `C:\Users\Mih\AppData\Local\Programs\Python\Python312\python.exe`
- Python version: `Python 3.12.9`
- Node version: `v20.19.0`
- npm version: `10.8.2`
- Dependency restoration: `npm ci` completed successfully; 79 packages installed/audited, 0 vulnerabilities.

## Reviewed artifacts

- Project rules and runbook: `RULES.md`, `docs/equipment-inventory-runbook.md`
- Change proposal/design/tasks: `openspec/changes/inventory-driven-diagnostic-dispatch/proposal.md`, `design.md`, `tasks.md`
- Change specs:
  - `openspec/changes/inventory-driven-diagnostic-dispatch/specs/diagnostic-application-shell/spec.md`
  - `openspec/changes/inventory-driven-diagnostic-dispatch/specs/equipment-inventory-snapshot/spec.md`
  - `openspec/changes/inventory-driven-diagnostic-dispatch/specs/pdu-room-codec-enrichment/spec.md`
- Relevant root specs:
  - `openspec/specs/credential-source-isolation/spec.md`
  - `openspec/specs/request-lifecycle-and-recovery/spec.md`
  - `openspec/specs/diagnostic-application-shell/spec.md`
  - `openspec/specs/equipment-inventory-snapshot/spec.md`
  - `openspec/specs/pdu-room-codec-enrichment/spec.md`
  - `openspec/specs/device-diagnostics-and-control/spec.md`

## Validation commands

- `git diff --check origin/master...HEAD`: passed with no output.
- Mandatory focused tests:
  - Command: `python -m unittest tests.test_equipment_inventory tests.test_inventory_diagnostic_dispatch tests.test_inventory_credential_configuration tests.test_credential_fallback_retry tests.test_pdu_controller tests.test_pdu_room_codec_enrichment tests.test_pdu_gui_composition tests.test_extron_dmp64_plus_meter_diagnostics tests.test_biamp_tesira_forte_ci_audio_signal_status tests.test_equipment_room_context_gui tests.test_device_screens tests.test_codec_screen tests.test_release_ui_qa tests.test_ui_states tests.test_gui_theme -v`
  - Result: passed; 308 tests in 71.592s.
- Additional focused tests:
  - Command: `python -m unittest tests.test_matrix_controller tests.test_matrix_handler_security tests.test_credential_propagation tests.test_credential_worker_retry_ownership tests.test_codec_session_contracts tests.test_codec_handler_session_failures tests.test_interactive_session tests.test_worker_module_decomposition tests.test_worker_outcomes tests.test_pdu_operations tests.test_extron_pcs4i tests.test_aten_pdu_safety -v`
  - Result: passed; 191 tests in 8.350s.
- Full offline suite:
  - Command: `python -m unittest discover -s tests -p "test_*.py" -v`
  - Result: passed; 568 tests in 81.555s.
- `.\openspec.cmd validate inventory-driven-diagnostic-dispatch --strict`: passed.
- `.\openspec.cmd validate --all --strict`: passed; 11 passed, 0 failed.

## Archive simulation

Archive simulation was run in a disposable worktree at the validated source SHA. `npm ci` succeeded, but `.\openspec.cmd archive inventory-driven-diagnostic-dispatch --yes` aborted before changing files:

```text
Proposal warnings in proposal.md (non-blocking):
  WARNING Why section should not exceed 1000 characters
Task status: 120/129 tasks
Warning: 9 incomplete task(s) found. Continuing due to --yes flag.

Specs to update:
  diagnostic-application-shell: update
  equipment-inventory-snapshot: update
  pdu-room-codec-enrichment: update
diagnostic-application-shell MODIFIED failed for header "### Requirement: Device selection and refresh input validation" - current spec contains scenario(s) not present in the modified block: "Valid supported device refresh". Refresh the change spec before archiving to avoid dropping scenarios.
Aborted. No files were changed.
```

Post-simulation `openspec validate --all --strict` passed because the archive command aborted without changing files. Post-simulation `git status --short`, `git diff --check`, `git diff --stat`, and `git diff --name-status` were clean/empty.

## Findings

### HIGH: OpenSpec archive applicability fails

- Files:
  - `openspec/changes/inventory-driven-diagnostic-dispatch/specs/diagnostic-application-shell/spec.md`
  - `openspec/specs/diagnostic-application-shell/spec.md`
- Evidence:
  - The change modifies `### Requirement: Device selection and refresh input validation`.
  - The root requirement already contains scenario `Valid supported device refresh`.
  - `openspec archive inventory-driven-diagnostic-dispatch --yes` aborts because the modified block does not preserve that existing scenario.
- Impact:
  - The accepted change cannot be archived safely.
  - OpenSpec refuses to apply the root spec update because archiving would drop an existing scenario.
- Required fix:
  - Refresh the delta `MODIFIED` block so it preserves all existing root scenarios, including `Valid supported device refresh`, then rerun archive simulation and strict validation.

### HIGH: Biamp credential fallback still accepts legacy error-text heuristics

- Files:
  - `gui/main_window.py`
  - `openspec/specs/credential-source-isolation/spec.md`
  - `openspec/changes/inventory-driven-diagnostic-dispatch/design.md`
- Evidence:
  - `_is_structured_retry_authentication_error` returns structured authentication checks only for VCS codec, PCS4i, and Matrix devices.
  - Other devices fall through to `is_authentication_error(error_type, error_message)`, which treats substrings such as `auth`, `401`, and `403` in the message as authentication failures.
  - `Biamp Tesira Forte CI` is not covered by the structured-only branch, but `on_device_error` still uses this classifier to advance credential fallback state and resubmit `refresh_biamp_tesira_forte_ci`.
  - The change adds misleading-text regression coverage for other device families, but not for Biamp.
- Contract:
  - `credential-source-isolation` requires retrying a later credential candidate only after a confirmed authentication failure and stopping for non-authentication errors.
  - The change design requires credential advancement only after structured authentication failure; text such as `auth`, `401`, or `403` must not authorize fallback.
- Impact:
  - A non-authentication Biamp transport/protocol failure whose text mentions `auth`, `401`, or `403` can incorrectly advance credential state and trigger a retry.
  - This violates the structured-auth-only fallback requirement and can mutate successful credential ordering after a non-auth failure.
- Required fix:
  - Route Biamp/audio-DSP retry decisions through structured authentication classification only, or disable retry unless the worker boundary reports a confirmed authentication error.
  - Add a Biamp regression test proving misleading authentication-like text in a non-auth error does not advance credentials or resubmit diagnostics.

## Validation-side changes

- Production code changed by validator: no.
- Tests changed by validator: no.
- Specs/proposal/design/tasks changed by validator: no.
- Runbooks changed by validator: no.
- Verification evidence file added by validator: `openspec/changes/inventory-driven-diagnostic-dispatch/verification-report.md`.
