# Tasks: Standalone inventory converter operator workflow

## Implementation evidence: 2026-08-02 (independent-validation follow-up)

- Remote refs before the follow-up:
  - `origin/master = 642d691d9065fb04c8e6c94f4d26af3921e20430`
  - `origin/agent/standalone-inventory-converter-operator-workflow = c051be35f0c081378d230fceb581e6c05cca5496`
  - clean starting `HEAD = c051be35f0c081378d230fceb581e6c05cca5496`
- Independent validation found two MEDIUM findings. This implementation follow-up fixes them; independent revalidation remains pending.
- Missing-source completed observation fix:
  - `tools/inventory_converter_gui.py` now keeps an internal `SourceObservation` separate from GUI `NOT_TESTED` state.
  - A completed missing Primary or Network test remains `FAILED` while the source is still absent and becomes `STALE` when that same path appears later.
  - Path edits still clear the completed observation and reset the presentation state to `NOT_TESTED`.
  - The observation remains GUI-only; canonical JSON, `ImportResult`, report shape, snapshot identity, and importer/domain behavior are unchanged.
- Archive EOF formatting fix:
  - Initial disposable archive from `c051be35f0c081378d230fceb581e6c05cca5496` reproduced `openspec/specs/equipment-inventory-snapshot/spec.md:1578: new blank line at EOF` from `git diff --check`.
  - The root-spec EOF boundary now has the same terminal separator that repository-local OpenSpec emits when rebuilding a terminal `## Requirements` section.
  - Temporary committed-baseline archive applicability passed: archive exit 0, `validate --all --strict` 11 passed/0 failed, and `git diff --check` exit 0.
  - Requirement and scenario text are unchanged; this is an EOF-formatting-only root-spec change.
- Accepted UX waiver: manual verification not performed; project owner accepted residual UX risk; offscreen regression coverage exists.
- Fresh validation results:
  - `node --version -> v20.19.0`; `npm --version -> 10.8.2`; `npm ci -> added 79 packages, audited 80 packages, 0 vulnerabilities`.
  - `QT_QPA_PLATFORM=offscreen python -m unittest tests.test_inventory_converter_gui -v -> Ran 16 tests, OK`.
  - `python -m unittest tests.test_equipment_inventory -v -> Ran 29 tests, OK`.
  - `python -m unittest tests.test_equipment_inventory tests.test_inventory_diagnostic_dispatch tests.test_inventory_credential_configuration tests.test_pdu_room_codec_enrichment tests.test_equipment_room_context_gui -v -> Ran 127 tests, OK`.
  - `QT_QPA_PLATFORM=offscreen python -m unittest discover -s tests -p "test_*.py" -v -> Ran 629 tests, OK`.
  - `./openspec.cmd validate standalone-inventory-converter-operator-workflow --strict -> valid`.
  - `./openspec.cmd validate --all --strict -> 11 passed, 0 failed`.

## Implementation evidence: 2026-08-02

- Remote refs before follow-up fixes:
  - `origin/master = 642d691d9065fb04c8e6c94f4d26af3921e20430`
  - `origin/agent/standalone-inventory-converter-operator-workflow = 98bb2aaa72f17ac64bb42c3949b076e5008d9878`
- Implementation worktree:
  - `.worktrees/impl-standalone-inventory-converter-operator-workflow`
  - starting `HEAD = 98bb2aaa72f17ac64bb42c3949b076e5008d9878`
- Python:
  - `C:\Users\Mih\AppData\Local\Programs\Python\Python312\python.exe`
  - `Python 3.12.9`
- Node/npm:
  - `node --version -> v20.19.0`
  - `npm --version -> 10.8.2`
  - `npm ci -> added 79 packages, audited 80 packages, 0 vulnerabilities`
- Fresh validation results:
  - `python -m unittest tests.test_equipment_inventory -v -> Ran 29 tests, OK`
  - `QT_QPA_PLATFORM=offscreen python -m unittest tests.test_inventory_converter_gui -v -> Ran 14 tests, OK`
  - `python -m unittest tests.test_equipment_inventory tests.test_inventory_diagnostic_dispatch tests.test_inventory_credential_configuration tests.test_pdu_room_codec_enrichment tests.test_equipment_room_context_gui -v -> Ran 127 tests, OK`
  - `QT_QPA_PLATFORM=offscreen python -m unittest discover -s tests -p "test_*.py" -v -> Ran 627 tests, OK`
  - `.\openspec.cmd validate standalone-inventory-converter-operator-workflow --strict -> valid`
  - `.\openspec.cmd validate --all --strict -> 11 passed, 0 failed`
  - `git diff --check -> passed`
- Detached GUI smoke:
  - `Start-Process` launched `tools\inventory_converter_gui.py` as a standalone process; the main diagnostic application did not launch.
  - Real detached GUI checks passed with synthetic inputs: startup separation, Primary Test success, Primary Test `PASSED_WITH_WARNINGS`, Primary Test failed report, Network Test success, Network Test failed report, path-edit reset to `NOT_TESTED`, file-change `STALE`, `Check all` without output, successful conversion, failed conversion without publication, overwrite decline preserving output, overwrite acceptance replacing output, `OUTPUT_CHANGED_SINCE_CONFIRMATION` with output preserved and exported report, main application launch without converter window, controls disabled/re-enabled across a worker run, and close blocked while an operation runs.
  - Real detached GUI report checks passed: failed report table visible with fatal issue first and native Save report dialog can export UTF-8 JSON with exactly one trailing newline.
  - manual verification not performed; project owner accepted residual UX risk; offscreen regression coverage exists.

## 1. Architecture and baseline

- [x] Read current `RULES.md` and `docs/equipment-inventory-runbook.md` before implementation.
- [x] Confirm `origin/master`, feature remote HEAD, PR state, Draft state, base/head, mergeability, and new commits.
- [x] Confirm exact local/remote feature SHA equality before starting work.
- [x] Review the archived `inventory-switch-port-enrichment` artifacts and current root `equipment-inventory-snapshot` specification.
- [x] Confirm the current importer direct API, CLI report keys, schema-v2/v3 modes, atomic publication, and PyQt5 application conventions.
- [x] Run `npm ci` with Node 20.19.0 or later.
- [x] Run `git diff --check` and inspect `git status --short` before implementation.
- [x] Run `.\openspec.cmd validate standalone-inventory-converter-operator-workflow --strict` and `.\openspec.cmd validate --all --strict` before implementation.

## 2. Add UI-independent preflight, report, and publication contracts

- [x] Add a read-only primary-workbook preflight operation that reuses the current workbook reader, layout discovery, row mapping, normalization, model recognition, and primary diagnostics without publication.
- [x] Add a read-only network-workbook preflight operation that reuses the current network reader/layout/candidate rules without primary-inventory reconciliation or publication.
- [x] Add a read-only combined two-source preflight operation that requires only the primary and network paths, repeats both source validations, performs approved MAC-only reconciliation, builds and validates an in-memory schema-v3 candidate, and does not publish JSON.
- [x] Ensure an empty output path never blocks combined preflight; an already selected output may be checked only as optional additional conflict evidence.
- [x] Preserve the existing `import_equipment_inventory(...)` call and intentional one-source schema-v2 behavior.
- [x] Add exact closed enums for operations, terminal statuses, stages, and source-file roles.
- [x] Preserve every existing serialized conversion report key and add the exact normative root and issue keys only additively.
- [x] Enforce report nullability and `published` semantics for every operation.
- [x] Keep `NOT_TESTED`, `RUNNING`, and `STALE` as GUI presentation states rather than terminal report statuses.
- [x] Keep all result/report and output-precondition types independent of PyQt5.
- [x] Ensure configuration and preflight failures produce safe structured reports instead of uncaught GUI-facing exceptions.
- [x] Add an optional UI-independent publication precondition or guarded-publication entry point that preserves existing unguarded callers.
- [x] Recheck the output precondition immediately before atomic replacement and report fatal `OUTPUT_CHANGED_SINCE_CONFIRMATION` without modifying the current output when it fails.

## 3. Implement the standalone GUI

- [x] Add a standalone PyQt5 entry point with its own `QApplication`; do not modify `main.py` or the main diagnostic window.
- [x] Add visible path controls and browse dialogs for the primary `.xlsx`, network `.xlsx`, and exact output `.json` path.
- [x] Require only the relevant paths per operation: one workbook for its individual test, both workbooks for `Check all`, and both workbooks plus output for `Convert`.
- [x] Require both workbook paths for GUI conversion while preserving optional network input for CLI/direct API use.
- [x] Add independent `Test` buttons and exact states `NOT_TESTED`, `RUNNING`, `PASSED`, `PASSED_WITH_WARNINGS`, `FAILED`, and `STALE`.
- [x] Store and compare safe path/size/last-modified fingerprints; reset state on path edits and mark stale results before reuse.
- [x] Add `Check all` combined preflight and `Convert` actions; conversion must repeat full validation on current bytes.
- [x] Add one serialized background worker lifecycle for all workbook/preflight/conversion/publication-precondition work.
- [x] Disable conflicting controls while an operation runs and update widgets only in the GUI thread.
- [x] Use an indeterminate progress indicator unless real measurable progress is available.
- [x] Block or defer window close while an operation is running; never terminate the worker during atomic publication.
- [x] Capture normalized output existence/fingerprint state at confirmation and pass it to the UI-independent guarded-publication boundary.
- [x] Leave output publication entirely to the importer; do not delete, truncate, pre-create, rename, or directly rewrite the output in GUI code.

## 4. Present and export the report

- [x] Show exact operation, terminal status, publication state, output path, schema version where applicable, stage reached, snapshot ID, source row counts, record count, network enrichment counters, and issue counts.
- [x] Show fatal issues first in a table with exact shared class, stage, code, source role, worksheet, row, source column, record ID, and safe description fields.
- [x] Add issue-class filtering and selected-issue `details` display without mutating the underlying report.
- [x] Export the complete unfiltered report as UTF-8 JSON with a trailing newline.
- [x] Ensure report rendering and export work after success and failure.
- [x] Ensure all report consumers serialize the same closed root and issue shapes.
- [x] Ensure reports never dump complete source rows, workbook contents, production inventory, credentials, secrets, or unnecessary evidence.

## 5. Regression coverage

- [x] Add focused domain tests for primary preflight, network preflight, combined preflight without output, no-publication behavior, additive report compatibility, exact enums/shapes/nullability, and safe failures.
- [x] Add guarded-publication tests for absent-output appearance, existing-output modification, deletion/replacement, normalized-path mismatch, unchanged-output success, and preservation of current output after rejection.
- [x] Preserve all current importer, schema-v1/v2/v3, reconciliation, runtime inventory, dispatch, and PDU-room-codec tests.
- [x] Add offscreen GUI tests for browse/path state, path-edit resets, fingerprint stale transitions, independent tests, combined preflight without output, conversion result handling, and serialized operation ownership.
- [x] Add offscreen GUI tests for disabled controls, overwrite decline, output-change rejection, close blocking, fatal-first issue ordering, filtering, details, and complete report export.
- [x] Use only synthetic workbooks and temporary output/report paths.
- [x] Verify neither GUI modules nor PyQt5 are imported by normal runtime inventory loading or importer/domain modules.

## 6. Documentation and manual smoke validation

- [x] Update `docs/equipment-inventory-runbook.md` with the standalone launch command, exact per-operation path requirements, GUI workflow, test-state semantics, fingerprints, closed report contract, report/export behavior, guarded overwrite confirmation, and continued CLI/direct API support.
- [x] Document that GUI conversion is the explicit two-source schema-v3 operator workflow and that CLI/direct API one-source schema-v2 mode remains supported.
- [x] Document that `Check all` requires no output path.
- [x] Document that `Изменения` and `Корректная запись` remain ignored.
- [x] Launch the standalone GUI as a detached process under `RULES.md` using synthetic inputs.
- [ ] Manually verify primary test, network test, stale transition, combined preflight before output selection, successful conversion, failed conversion, overwrite decline/acceptance, output-change rejection, report filtering, report export, and close behavior.
- [x] Confirm the main diagnostic application starts and operates without importing or launching the converter GUI.

## 7. Required validation

- [x] Run focused importer/preflight/publication-guard tests.
- [x] Run focused offscreen converter GUI tests with `QT_QPA_PLATFORM=offscreen`.
- [x] Run existing inventory runtime regression modules.
- [x] Run the full offline suite with actual fresh counts.
- [x] Run `.\openspec.cmd validate standalone-inventory-converter-operator-workflow --strict`.
- [x] Run `.\openspec.cmd validate --all --strict`.
- [x] Run `git diff --check`, inspect `git status --short`, and review the full diff against approved architecture.
- [x] Confirm no production workbook, generated deployment snapshot, exported report, local preferences, `node_modules`, temporary artifacts, or Graphify output is tracked.

## 8. Publication and independent validation

- [x] Create a focused implementation commit and push it to the existing feature branch without amend, rebase, or force-push.
- [x] Confirm local HEAD equals remote feature-branch HEAD and the PR remains Draft.
- [ ] Run independent validation in a new clean detached worktree from exact `origin/<feature-branch>`.
- [ ] Independently rerun focused tests, offscreen GUI tests, runtime regressions, full suite, both strict validations, and repository-protection checks.
- [ ] Independently review GUI thread ownership, no duplicated importer rules, output precondition/overwrite/close safety, closed report compatibility, main-application separation, and current remote SHA.
- [x] Perform a disposable archive-applicability check because this change adds root-spec requirements and a new root capability.
- [ ] Obtain `APPROVE` or `APPROVE WITH NON-BLOCKING NOTES` before archive.

## 9. Archive and merge

- [ ] Archive only after an independent approving verdict using `.\openspec.cmd archive standalone-inventory-converter-operator-workflow --yes`.
- [ ] Review the archived change and root-spec diffs, including the new `inventory-converter-operator-workflow` root capability.
- [ ] Run post-archive `.\openspec.cmd validate --all --strict`, full offline tests, and `git diff --check`.
- [ ] Create and push a dedicated archive commit.
- [ ] Reconfirm current `master`, remote archive HEAD, PR Draft/state/base/head, mergeability, and absence of new commits.
- [ ] Merge only with explicit user permission; do not close the PR or delete the branch manually unless separately instructed.
