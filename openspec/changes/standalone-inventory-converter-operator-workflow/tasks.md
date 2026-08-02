# Tasks: Standalone inventory converter operator workflow

## 1. Architecture and baseline

- [ ] Read current `RULES.md` and `docs/equipment-inventory-runbook.md` before implementation.
- [ ] Confirm `origin/master`, feature remote HEAD, PR state, Draft state, base/head, mergeability, and new commits.
- [ ] Review the archived `inventory-switch-port-enrichment` artifacts and current root `equipment-inventory-snapshot` specification.
- [ ] Confirm the current importer direct API, CLI report keys, schema-v2/v3 modes, atomic publication, and PyQt5 application conventions.
- [ ] Run `npm ci` with Node 20.19.0 or later.
- [ ] Run `./openspec.cmd validate standalone-inventory-converter-operator-workflow --strict` and `./openspec.cmd validate --all --strict` before implementation.

## 2. Add UI-independent preflight and report contracts

- [ ] Add a read-only primary-workbook preflight operation that reuses the current workbook reader, layout discovery, row mapping, normalization, model recognition, and primary diagnostics without publication.
- [ ] Add a read-only network-workbook preflight operation that reuses the current network reader/layout/candidate rules without primary-inventory reconciliation or publication.
- [ ] Add a read-only combined two-source preflight operation that repeats both source validations, performs approved MAC-only reconciliation, builds and validates an in-memory schema-v3 candidate, and does not publish JSON.
- [ ] Preserve the existing `import_equipment_inventory(...)` signature and intentional one-source schema-v2 behavior.
- [ ] Preserve every existing serialized conversion report key and add operation, status, stage, source-role, source-column, related-row, and safe-detail metadata only additively.
- [ ] Keep all result/report types independent of PyQt5.
- [ ] Ensure configuration and preflight failures produce safe structured reports instead of uncaught GUI-facing exceptions.

## 3. Implement the standalone GUI

- [ ] Add a standalone PyQt5 entry point with its own `QApplication`; do not modify `main.py` or the main diagnostic window.
- [ ] Add visible path controls and browse dialogs for the primary `.xlsx`, network `.xlsx`, and exact output `.json` path.
- [ ] Require both workbook paths for GUI conversion while preserving optional network input for CLI/direct API use.
- [ ] Add independent `Test` buttons and exact states `NOT_TESTED`, `RUNNING`, `PASSED`, `PASSED_WITH_WARNINGS`, `FAILED`, and `STALE`.
- [ ] Store and compare safe path/size/last-modified fingerprints; reset state on path edits and mark stale results before reuse.
- [ ] Add `Check all` combined preflight and `Convert` actions; conversion must repeat full validation on current bytes.
- [ ] Add one serialized background worker lifecycle for all workbook/preflight/conversion work.
- [ ] Disable conflicting controls while an operation runs and update widgets only in the GUI thread.
- [ ] Use an indeterminate progress indicator unless real measurable progress is available.
- [ ] Block or defer window close while an operation is running; never terminate the worker during atomic publication.
- [ ] Require explicit confirmation before replacing an existing output and leave publication to the importer.

## 4. Present and export the report

- [ ] Show result status, publication state, output path, schema version where applicable, snapshot ID, source row counts, record count, network enrichment counters, and issue counts.
- [ ] Show fatal issues first in a table with class, stage, code, source role, worksheet, row, source column, record ID, and safe description.
- [ ] Add issue-class filtering and selected-issue details without mutating the underlying report.
- [ ] Export the complete unfiltered report as UTF-8 JSON with a trailing newline.
- [ ] Ensure report rendering and export work after success and failure.
- [ ] Ensure reports never dump complete source rows, workbook contents, production inventory, credentials, secrets, or unnecessary evidence.

## 5. Regression coverage

- [ ] Add focused domain tests for primary preflight, network preflight, combined preflight, no-publication behavior, additive report compatibility, and safe failures.
- [ ] Preserve all current importer, schema-v1/v2/v3, reconciliation, runtime inventory, dispatch, and PDU-room-codec tests.
- [ ] Add offscreen GUI tests for browse/path state, path-edit resets, fingerprint stale transitions, independent tests, combined preflight, conversion result handling, and serialized operation ownership.
- [ ] Add offscreen GUI tests for disabled controls, overwrite decline, close blocking, fatal-first issue ordering, filtering, details, and complete report export.
- [ ] Use only synthetic workbooks and temporary output/report paths.
- [ ] Verify neither GUI modules nor PyQt5 are imported by normal runtime inventory loading or importer/domain modules.

## 6. Documentation and manual smoke validation

- [ ] Update `docs/equipment-inventory-runbook.md` with the standalone launch command, exact GUI workflow, test-state semantics, fingerprints, report/export behavior, overwrite confirmation, and continued CLI/direct API support.
- [ ] Document that GUI conversion is the explicit two-source schema-v3 operator workflow and that CLI/direct API one-source schema-v2 mode remains supported.
- [ ] Document that `Изменения` and `Корректная запись` remain ignored.
- [ ] Launch the standalone GUI as a detached process under `RULES.md` using synthetic inputs.
- [ ] Manually verify primary test, network test, stale transition, combined preflight, successful conversion, failed conversion, overwrite decline/acceptance, report filtering, report export, and close behavior.
- [ ] Confirm the main diagnostic application starts and operates without importing or launching the converter GUI.

## 7. Required validation

- [ ] Run focused importer/preflight tests.
- [ ] Run focused offscreen converter GUI tests with `QT_QPA_PLATFORM=offscreen`.
- [ ] Run existing inventory runtime regression modules.
- [ ] Run the full offline suite with actual fresh counts.
- [ ] Run `./openspec.cmd validate standalone-inventory-converter-operator-workflow --strict`.
- [ ] Run `./openspec.cmd validate --all --strict`.
- [ ] Run `git diff --check`, inspect `git status --short`, and review the full diff against approved architecture.
- [ ] Confirm no production workbook, generated deployment snapshot, exported report, local preferences, `node_modules`, temporary artifacts, or Graphify output is tracked.

## 8. Publication and independent validation

- [ ] Create a focused implementation commit and push it to the existing feature branch without amend, rebase, or force-push.
- [ ] Confirm local HEAD equals remote feature-branch HEAD and the PR remains Draft.
- [ ] Run independent validation in a new clean detached worktree from exact `origin/<feature-branch>`.
- [ ] Independently rerun focused tests, offscreen GUI tests, runtime regressions, full suite, both strict validations, and repository-protection checks.
- [ ] Independently review GUI thread ownership, no duplicated importer rules, overwrite/close safety, report safety, main-application separation, and current remote SHA.
- [ ] Perform a disposable archive-applicability check because this change adds root-spec requirements and a new root capability.
- [ ] Obtain `APPROVE` or `APPROVE WITH NON-BLOCKING NOTES` before archive.

## 9. Archive and merge

- [ ] Archive only after an independent approving verdict using `./openspec.cmd archive standalone-inventory-converter-operator-workflow --yes`.
- [ ] Review the archived change and root-spec diffs, including the new `inventory-converter-operator-workflow` root capability.
- [ ] Run post-archive `./openspec.cmd validate --all --strict`, full offline tests, and `git diff --check`.
- [ ] Create and push a dedicated archive commit.
- [ ] Reconfirm current `master`, remote archive HEAD, PR Draft/state/base/head, mergeability, and absence of new commits.
- [ ] Merge only with explicit user permission; do not close the PR or delete the branch manually unless separately instructed.
