# Tasks: inventory-diagnostic-model-evidence-reconciliation

## 1. Confirm implementation baseline

- [ ] Перед началом работы прочитай RULES.md.
- [ ] Read `docs/equipment-inventory-runbook.md`, this approved change, the current root `equipment-inventory-snapshot` specification, importer source, current importer tests, and existing Qt test conventions.
- [ ] Fetch `origin`, record exact `origin/master`, remote feature-branch HEAD, PR state/Draft/base/head/mergeability, and inspect every commit newer than the approved architecture HEAD before implementation.
- [ ] Confirm the converter remains a separate offline program and no diagnostic-application page, menu, dialog, startup, composition, controller, worker, handler, or runtime import is added.

## 2. Implement two-field model evidence evaluation

- [ ] Preserve normalized `Наименование -> source_model` exactly as today.
- [ ] Apply the existing reviewed component recognizer independently to source `Модель` and source `Наименование`.
- [ ] Return the complete matching canonical-model set for each evidence field rather than selecting the first rule.
- [ ] Combine the two match sets by distinct canonical-model union.
- [ ] Publish one exact canonical `diagnostic_model` only when the combined union contains exactly one model.
- [ ] Emit only `UNMAPPED_DIAGNOSTIC_MODEL` when the combined union is empty.
- [ ] Emit only `AMBIGUOUS_DIAGNOSTIC_MODEL` when the combined union contains more than one model.
- [ ] Keep unmapped and ambiguous outcomes non-fatal when the canonical row is otherwise representable.

## 3. Unify structured conversion reporting

- [ ] Refactor converter execution so CLI, direct import API, and standalone GUI receive one structured report model for success and every known failure stage.
- [ ] Preserve existing report fields while adding stage and safe source-location context needed by the approved GUI/report contract.
- [ ] Represent configuration failures such as missing/nonexistent source and invalid output path as structured fatal issues.
- [ ] Represent workbook-read failures as structured fatal issues without exposing workbook contents.
- [ ] Enhance missing-source-structure reporting to identify missing required column names for candidate worksheets without dumping complete rows or arbitrary cell values.
- [ ] Include `SmartRoomID` source column and row for missing record ID failures.
- [ ] Include the later row and first conflicting row for duplicate record IDs when available.
- [ ] Catch candidate validation and output publication failures and return structured fatal issues.
- [ ] Preserve the previous output file on every failure before atomic replacement.
- [ ] Catch unexpected outer-boundary failures as `UNEXPECTED_CONVERTER_FAILURE` with safe exception type/stage only.
- [ ] Keep report serialization deterministic, UTF-8, JSON-safe, and independent of snapshot identity.

## 4. Add the standalone converter GUI

- [ ] Add a separate entry point such as `tools/equipment_inventory_converter_gui.py` that creates its own `QApplication` and top-level window.
- [ ] Do not import `gui.main_window`, construct `VCSDiagnosticApp`, or add converter controls to the diagnostic application.
- [ ] Add an editable source path field and a native `.xlsx` open-file dialog.
- [ ] Add an editable exact output-file path field and a native `.json` Save As dialog with suggested name `equipment_inventory.local.json`.
- [ ] Validate non-empty source/output paths, existing regular source file, output not being a directory, and source/output not resolving to the same file.
- [ ] Disable Convert while required paths are empty or a run is active.
- [ ] Require explicit confirmation before replacing an existing output file.
- [ ] Execute conversion through a dedicated Qt worker thread or equivalent Qt-safe worker boundary; do not parse the workbook on the GUI thread.
- [ ] Disable conflicting path controls during execution and show indeterminate progress/current stage.
- [ ] Prevent unsafe abrupt worker termination during publication; no cancellation feature is required.
- [ ] Keep the importer/domain module free of PyQt imports.

## 5. Present and export the detailed report

- [ ] Show a prominent success/failure state and whether snapshot publication occurred.
- [ ] Show source/output paths, worksheet/header, source-row count, canonical-record count, snapshot ID, and issue counts.
- [ ] Show a read-only issue table with fields equivalent to class, stage, code, worksheet, row, source column, record ID, and description.
- [ ] Order fatal issues before data-quality and consistency issues using deterministic underlying order.
- [ ] Add at least issue-class filtering without modifying the underlying exported report.
- [ ] Show full safe details for the selected issue without truncation.
- [ ] Add `Save report...` using a native JSON save dialog and a distinct suggested name such as `equipment_inventory_import_report.json`.
- [ ] Permit report export after both successful and failed conversions.
- [ ] Treat optional report-save failure as a GUI-local error that does not change the conversion result.

## 6. Preserve authorities and runtime boundaries

- [ ] Preserve the existing closed nine-model registry unchanged.
- [ ] Preserve Unicode NFC, trim, casefold, separator, letter/digit transition, and reviewed `4i` component semantics unchanged for both evidence fields.
- [ ] Preserve `Производитель` as optional consistency evidence only; it must not add, veto, remove, or select a match.
- [ ] Preserve exact `Тип модели -> device_kind` mapping and do not infer or override kind from recognized model evidence.
- [ ] Preserve canonical schema versions, exact record fields, deterministic snapshot identity, atomic publication, runtime loader behavior, and inventory query APIs.
- [ ] Keep CLI and direct import API supported through the same importer implementation used by the standalone GUI.
- [ ] Do not add runtime fallback from `source_model`; diagnostic GUI, dispatch, controllers, workers, handlers, credentials, PDU enrichment, and related-codec logic remain unchanged.
- [ ] Do not add a Windows installer, packaged `.exe`, persistent recent-path settings, workbook editing, cancellation, or automatic file watching.
- [ ] Keep diagnostics safe: no complete source rows, production inventory, secrets, internal IPs, room IDs, MAC addresses, serial numbers, or unnecessary free-form evidence in normal output.

## 7. Add synthetic regression coverage

### Model reconciliation

- [ ] Add blank `Модель` plus recognized `Наименование` coverage.
- [ ] Add recognized `Модель` plus blank or unmapped `Наименование` coverage.
- [ ] Add both fields resolving to the same canonical model.
- [ ] Add fields resolving to different canonical models and prove ambiguity.
- [ ] Add one internally ambiguous field plus one agreeing unique field; ambiguity must remain.
- [ ] Add one internally ambiguous field plus an unmapped field.
- [ ] Add both fields unmapped.
- [ ] Cover all nine existing canonical models through `Наименование` evidence.
- [ ] Repeat positive separator/compact/optional-suffix/accent cases and boundary-negative cases for `Наименование` evidence.
- [ ] Prove exactly one mapped/unmapped/ambiguous outcome per row, unchanged `source_model`, unchanged `device_kind`, and deterministic snapshot identity.

### Structured report

- [ ] Test missing configuration, missing source, non-file source, unreadable workbook, missing/ambiguous source structure, missing/duplicate record ID, candidate-validation failure, and output-write failure.
- [ ] Prove missing-column reports contain safe required header names but no arbitrary row values.
- [ ] Prove output-write failure preserves the previous output.
- [ ] Prove success report contains counts, paths, publication state, snapshot ID, and non-fatal issues.
- [ ] Prove report JSON is deterministic and UTF-8 safe.

### Standalone GUI

- [ ] Test that the GUI module starts independently without importing or constructing the diagnostic main window.
- [ ] Test source and output native-dialog adapters and path-field population.
- [ ] Test Convert enablement, active-run disablement, and existing-output confirmation.
- [ ] Prove conversion is submitted to a worker and is not invoked synchronously on the GUI thread.
- [ ] Test success/failure summary rendering, issue-table ordering/filtering, selected-issue detail, and report export after both outcomes.
- [ ] Use only synthetic values and verify that no production workbook or inventory data appears in fixtures, reports, screenshots, or logs.

## 8. Update operational documentation

- [ ] Update `docs/equipment-inventory-runbook.md` with independent `Модель`/`Наименование` recognition and union cardinality.
- [ ] Document that `Наименование` remains canonical `source_model` while also supplying importer-only recognition evidence.
- [ ] Document the standalone converter launch path and explicitly state that it is not part of the diagnostic application.
- [ ] Document source and exact output-file selection, existing-file confirmation, progress behavior, report summary/table, and report export.
- [ ] Document all blocking report stages/codes and the safe evidence shown for missing headers and required values.
- [ ] Document that unsupported models, including `Huawei CloudLink Box 610`, remain unmapped.
- [ ] Require offline regeneration of `equipment_inventory.local.json` after deployment.

## 9. Validate implementation

- [ ] Run focused importer tests with the repository-supported Python interpreter and record exact counts:

```powershell
<python> -m unittest tests.test_equipment_inventory -v
```

- [ ] Run focused standalone converter GUI tests using the repository's headless Qt test convention:

```powershell
<python> -m unittest tests.test_equipment_inventory_converter_gui -v
```

- [ ] Run inventory-driven dispatch and PDU enrichment regression modules to prove runtime behavior remains unchanged:

```powershell
<python> -m unittest tests.test_inventory_diagnostic_dispatch tests.test_pdu_room_codec_enrichment -v
```

- [ ] Run the canonical full offline test suite and record exact counts:

```powershell
<python> -m unittest discover -s tests -p "test_*.py" -v
```

- [ ] Run repository-local OpenSpec validation only:

```powershell
.\openspec.cmd validate inventory-diagnostic-model-evidence-reconciliation --strict
.\openspec.cmd validate --all --strict
```

- [ ] Run repository protection checks:

```powershell
git diff --check
git status --short
git diff --stat origin/master...HEAD
git diff --name-only origin/master...HEAD
```

- [ ] Review that no diagnostic-application GUI, runtime dispatch, controllers, workers, handlers, credentials, production workbook/snapshot, installer output, Graphify output, or unrelated files changed.

## 10. Publish implementation for independent validation

- [ ] Create focused implementation commit(s) and push to `agent/inventory-diagnostic-model-evidence-reconciliation` without force-push.
- [ ] Verify local HEAD equals `origin/agent/inventory-diagnostic-model-evidence-reconciliation` after push.
- [ ] Update implementation evidence with exact branch SHA, change base, commands, exit codes, test counts, and changed-file scope.
- [ ] Do not self-issue final `APPROVE`; request independent validation from a separate clean detached worktree created from the exact published remote branch HEAD.

## 11. Independent validation and archive applicability

- [ ] Independently repeat focused importer tests, standalone GUI tests, runtime regression modules, the full offline suite, both strict OpenSpec validations, `git diff --check`, architecture correspondence, scope review, safe-data checks, and local/remote SHA equality in a clean detached worktree from `origin/agent/inventory-diagnostic-model-evidence-reconciliation`.
- [ ] Independently launch the standalone GUI as a detached process for a synthetic manual smoke test when the environment supports GUI display; do not treat an unavailable display as passing manual evidence.
- [ ] The validator must not fix findings or change production code, tests, proposal, design, tasks, or specs.
- [ ] Because this change uses `MODIFIED` root requirements, perform a disposable archive-applicability check outside the feature branch: archive with `.\openspec.cmd archive inventory-diagnostic-model-evidence-reconciliation --yes` in a throwaway worktree, inspect the archive/root-spec diff against the then-current root specification, run `.\openspec.cmd validate --all --strict`, and discard the worktree without publishing archive output.
- [ ] Do not issue `READY FOR ARCHIVE` while any Critical, High, or Medium finding remains, a required check fails, the validated remote HEAD changes, the validation worktree is dirty, or archive applicability is unproven.
