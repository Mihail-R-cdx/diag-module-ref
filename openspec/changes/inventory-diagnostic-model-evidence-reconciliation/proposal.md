# Change: inventory-diagnostic-model-evidence-reconciliation

## Why

The current offline importer ignores useful supported-model evidence from `Наименование`, and its command-line-only workflow is inconvenient for routine operator use. Conversion failures are printed as JSON in a console, while some blocking failures do not yet produce a complete structured report. The converter needs deterministic two-field model recognition, a separate standalone GUI for selecting paths, and a detailed safe report that clearly explains blocking and non-blocking issues without integrating the converter into the diagnostic application.

## What Changes

### Diagnostic-model evidence reconciliation

- Keep `Наименование -> source_model` unchanged and additionally evaluate normalized `Наименование` as importer-only diagnostic-model evidence.
- Continue evaluating normalized source `Модель` through the existing closed nine-model component registry.
- Evaluate both fields independently, combine the complete distinct canonical match union, and classify it:
  - zero matches -> `diagnostic_model = null` plus `UNMAPPED_DIAGNOSTIC_MODEL`;
  - one match -> publish that exact canonical model;
  - more than one match -> `diagnostic_model = null` plus `AMBIGUOUS_DIAGNOSTIC_MODEL`.
- Keep `Производитель` optional and non-authoritative.

### Standalone converter GUI

- Add a separate offline converter program with its own entry point and top-level window. It is not a screen, dialog, menu item, or lifecycle inside the diagnostic application.
- Provide an editable source-workbook path field with a standard native file-selection dialog filtered for `.xlsx` files.
- Provide an editable output-JSON path field with a standard native `Save As` dialog. The operator selects the exact output file rather than only a directory; the suggested file name is `equipment_inventory.local.json`.
- Require explicit confirmation before replacing an existing output file.
- Run conversion outside the Qt GUI thread, disable conflicting controls while it runs, and show an indeterminate progress state.
- Keep the existing CLI and direct import API available and backed by the same importer implementation.

### Detailed run report

- Produce one structured report for every attempted conversion, including configuration, workbook-read, source-layout, row-mapping, candidate-validation, and publication failures.
- Show an operator summary in the GUI: success/failure, source and output paths, worksheet/header, source-row and canonical-record counts, snapshot ID, publication result, and issue counts.
- Show issues in a sortable/filterable read-only table with fatal issues first and fields equivalent to class, stage, code, worksheet, row, source column, record ID, and safe description.
- Make missing required columns explicit by reporting which required headers were absent from candidate worksheets without dumping workbook rows or cell contents.
- Make fatal row-level errors such as missing or duplicate `SmartRoomID` identify the safe row and relevant source column, including the first conflicting row when available.
- Convert output-publication failures into structured fatal issues while preserving the existing atomic-publication guarantee.
- Allow the complete report to be saved as UTF-8 JSON independently of whether snapshot publication succeeded.

## Impact

Affected specification:

- `equipment-inventory-snapshot`

Expected implementation areas:

- `tools/import_equipment_inventory.py`
- a new standalone GUI entry point such as `tools/equipment_inventory_converter_gui.py`
- `tests/test_equipment_inventory.py`
- focused standalone converter-GUI tests
- `docs/equipment-inventory-runbook.md`

The standalone GUI may use the repository's existing PyQt5 environment, but the importer remains UI-independent and the normal diagnostic runtime does not import the converter GUI.

This change does not add a new supported canonical model. Unsupported values such as `Huawei CloudLink Box 610` remain unmapped until a separate reviewed model-support change exists. It does not add converter controls to the diagnostic application, change canonical schema versions, modify runtime inventory resolution or dispatch, change credentials/controllers/workers/handlers/PDU-codec orchestration, commit operational inventory, package an installer or `.exe`, or modify Graphify artifacts.
