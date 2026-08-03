# Proposal: Standalone inventory converter operator workflow

## Why

The approved equipment-inventory pipeline now supports both the primary organization workbook and the optional network-connection workbook, schema-v2 and schema-v3 publication, deterministic identity, structured import issues, and atomic JSON replacement. The only supported operator surface is still the command line or a direct Python API.

Operational users need a separate Windows GUI that can select the two approved source workbooks and the exact output JSON path, test each workbook without publication, run combined cross-source validation before choosing an output path, execute conversion without blocking the Qt GUI thread, guard confirmed output state against concurrent changes, and present one safe detailed report for both success and failure.

The GUI must reuse the importer as the only conversion authority. It must not duplicate workbook parsing, model recognition, MAC reconciliation, schema generation, candidate validation, snapshot identity, report classification, or atomic publication rules, and it must not be integrated into the main diagnostic application.

## What changes

- Add a standalone PyQt5 inventory-converter application with its own `QApplication` and launch entry point.
- Add explicit path controls for the primary equipment workbook, the network workbook, and the exact output JSON file.
- Add independent read-only `Test` operations for each workbook with explicit result states and safe file fingerprints.
- Add combined preflight validation for both current workbook bytes without requiring or publishing an output path.
- Run workbook I/O, validation, reconciliation, guarded publication, and conversion in one serialized background operation outside the Qt GUI thread.
- Extend the UI-independent importer boundary with reusable preflight operations and one closed additive structured report contract shared by CLI, GUI, and direct API consumers.
- Add an optional UI-independent output-publication precondition that rejects replacement if output state changes after operator confirmation.
- Present summary counts and a filterable issue table, and export the complete unfiltered UTF-8 JSON report.
- Require explicit confirmation before replacing an existing output file while preserving importer-owned atomic publication.
- Preserve current one-source CLI/direct API conversion and all schema-v1/v2/v3 runtime behavior.

## Capabilities

### New capability

- `inventory-converter-operator-workflow`: standalone GUI ownership, file-test states, background operation lifecycle, report presentation, export, overwrite precondition, and close behavior.

### Extended capability

- `equipment-inventory-snapshot`: reusable read-only source preflight, closed additive structured reporting, and optional guarded publication for CLI, GUI, and direct API use.

## Non-goals

- Do not add a converter page, button, menu, import, startup dependency, or lifecycle dependency to the main diagnostic application.
- Do not change schema v3, MAC-only switch reconciliation, diagnostic-model recognition, snapshot identity, or runtime inventory queries.
- Do not add switch discovery, SNMP, SSH, credentials, topology polling, port-state diagnostics, or switch controls.
- Do not read worksheet `Изменения` or use column `Корректная запись`.
- Do not modify source workbooks or automatically repair source data.
- Do not package an installer or executable in this change.
- Do not commit production workbooks, generated deployment snapshots, exported operator reports, local path preferences, or Graphify output.

## Expected implementation scope

```text
tools/import_equipment_inventory.py
tools/inventory_converter_gui.py
optional focused GUI support module under tools/
tests/test_equipment_inventory.py
tests/test_inventory_converter_gui.py
docs/equipment-inventory-runbook.md
```

Exact private module names may vary during implementation, but the dependency direction and public contracts in this change remain normative.
