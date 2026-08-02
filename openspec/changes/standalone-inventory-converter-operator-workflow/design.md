# Design: Standalone inventory converter operator workflow

## Context

The current approved pipeline is:

```text
primary equipment workbook
    + optional approved network workbook
    -> tools/import_equipment_inventory.py
    -> schema-v2 or schema-v3 canonical JSON
    -> runtime EquipmentInventory
    -> diagnostic application
```

The importer already owns workbook parsing, source layout discovery, normalization, diagnostic-model reconciliation, MAC-only switch enrichment, candidate validation through the runtime loader, deterministic identity, atomic publication, CLI configuration, and `ImportResult`/`ImportIssue` reporting.

The diagnostic application uses PyQt5, but the converter must be a separate process. The main application must not import the converter GUI, launch it, expose it in navigation, or depend on its configuration or state.

The existing report is intentionally small. It lacks reusable read-only preflight operations, operation/stage metadata, source-file roles, source columns, related rows, and file-test state. Change 3 may extend those UI-independent structures additively, but it must preserve current CLI keys, the public direct conversion signature, and all conversion behavior approved by Change 1 and Change 2.

## Goals

1. Provide an operator-friendly standalone Windows GUI for approved two-source schema-v3 conversion.
2. Keep importer/domain logic UI-independent and authoritative for CLI, GUI, and direct API use.
3. Test each workbook independently without writing JSON.
4. Revalidate both current source files together before every conversion.
5. Keep all workbook and conversion work outside the Qt GUI thread.
6. Preserve atomic publication and require overwrite confirmation in the GUI.
7. Show and export one safe complete report on success or failure.
8. Preserve one-source schema-v2 CLI/direct API operation and schema-v1/v2/v3 runtime loading.
9. Make state transitions deterministic and testable without relying on manual timing.

## Non-goals

- No integration into `main.py`, `gui/main_window.py`, diagnostic pages, controllers, handlers, workers, credentials, transports, or device I/O.
- No new schema version or canonical field.
- No changes to MAC reconciliation, model recognition, source authority, or runtime indexes.
- No parsing of `Изменения`; no validation or use of `Корректная запись`.
- No source editing, auto-correction, switch access, topology discovery, installer, or executable packaging.
- No percentage progress invented from operations that do not expose measurable progress.

## Decision 1: Separate executable and dependency direction

The converter GUI SHALL have its own launch entry point and `QApplication`. A preferred shape is:

```text
tools/inventory_converter_gui.py     standalone entry point and window
tools/import_equipment_inventory.py  UI-independent conversion authority
```

A focused sibling GUI support module under `tools/` is allowed if it improves testability. The importer/domain layer SHALL NOT import PyQt5. The main diagnostic application SHALL NOT import any converter GUI module.

The standalone GUI MAY reuse repository theme helpers only if doing so does not import the main application, create application-owned controllers, or introduce diagnostic runtime dependencies. A self-contained basic Fusion presentation is acceptable.

## Decision 2: Preserve the importer as the only business authority

The GUI SHALL call explicit UI-independent APIs for:

```text
primary-source preflight
network-source preflight
combined two-source preflight
conversion and publication
```

Those operations SHALL reuse the same workbook reader, layout discovery, normalization, source validation, diagnostic-model rules, MAC reconciliation, schema construction, runtime candidate validation, and publication code used by the CLI conversion path.

The GUI SHALL NOT reproduce source headers, model rules, issue severity, MAC joins, schema fields, snapshot identity, or publication logic.

The current public conversion signature remains supported:

```python
import_equipment_inventory(
    source_path,
    *,
    network_source_path=None,
    output_path=None,
    generated_at=None,
)
```

Existing serialized CLI report keys remain present. New report metadata is additive.

## Decision 3: GUI conversion is explicit two-source schema-v3 workflow

The standalone operator conversion requires:

```text
primary equipment workbook
network connection workbook
exact output JSON path
```

Both input paths are visible and explicitly supplied to the direct API. GUI conversion does not rely on module globals or silently choose environment/configuration paths after the operator has selected files.

This GUI requirement does not remove the importer's intentional one-source schema-v2 mode. CLI and direct API callers may still omit the network source under the existing contract.

File dialogs use `.xlsx` filters for inputs and a JSON `Save As` dialog for output. The selected exact output filename remains visible before conversion.

## Decision 4: Independent read-only source tests

Each source row has a `Test` operation.

Primary-source test validates only primary-workbook concerns, including readability, unambiguous layout/header discovery, required columns, identity contract, field normalization, model recognition outcomes, and primary cross-row diagnostics.

Network-source test validates only network-workbook concerns, including readability, exact `Устройства` worksheet selection, required headers, MAC/IP/port normalization, empty candidates, duplicate normalized candidates, and source-internal ambiguity. It cannot classify inventory-relative outcomes such as `NETWORK_MAC_NOT_IN_INVENTORY` without the primary source.

A source test SHALL NOT:

- publish or replace JSON;
- modify either workbook;
- perform partial conversion publication;
- become authority for a later conversion.

The result states are exactly:

```text
NOT_TESTED
RUNNING
PASSED
PASSED_WITH_WARNINGS
FAILED
STALE
```

No fatal issue yields `PASSED` or `PASSED_WITH_WARNINGS`; any fatal issue yields `FAILED`. Non-fatal issues distinguish the two successful states.

## Decision 5: Fingerprint and stale semantics

A successful or failed source test stores a safe fingerprint:

```text
resolved absolute path
file size
last-modified time with the platform's highest available precision
```

Changing the path text resets the corresponding result to `NOT_TESTED`. Before the GUI displays a prior result as current, before combined preflight, and before conversion, it compares the current fingerprint. A mismatch changes the result to `STALE`.

No background file watcher or full-workbook hash is required. Conversion always rereads and revalidates current bytes regardless of test status.

## Decision 6: Combined preflight is distinct from individual tests

`Check all` runs a read-only combined preflight over both current sources. It repeats each source validation and additionally performs the approved MAC-only reconciliation needed to expose:

```text
NETWORK_MAC_NOT_IN_INVENTORY
AMBIGUOUS_INVENTORY_MAC_FOR_SWITCH
AMBIGUOUS_SWITCH_CONNECTION
DUPLICATE_SWITCH_CONNECTION_SOURCE
partial connection outcomes
```

Combined preflight builds and validates an in-memory candidate document but SHALL NOT publish it. It may compute the candidate schema version, record count, and snapshot ID for reporting.

`Convert` does not trust a previous combined result. It repeats full preflight and candidate validation on current bytes before atomic publication.

## Decision 7: One serialized background operation

All source tests, combined preflight, workbook reads, reconciliation, candidate validation, JSON serialization, and publication run outside the GUI thread.

Only one operation may run at a time. While an operation is active, the GUI disables path editing, browse buttons, tests, combined preflight, conversion, and report export actions that could conflict with the operation.

A `QThread` plus worker `QObject`, or an equivalent testable PyQt5 pattern, SHALL communicate immutable result objects back by signals. Widgets are read and modified only in the GUI thread.

The worker SHALL NOT be killed with `terminate()`. Closing the window while an operation is running is blocked or deferred with a clear message. In particular, the GUI must not interrupt importer-owned atomic publication.

The progress indicator is indeterminate unless a real measurable progress contract is introduced. The status label may display coarse operation/stage names from the UI-independent report callback; it must not invent percentages.

## Decision 8: Unified safe report contract

CLI conversion, GUI conversion, direct API conversion, source tests, and combined preflight SHALL serialize reports from shared UI-independent result types.

The report contains, where applicable:

```text
operation
status
published
source file roles and resolved paths
output_path
stage_reached
primary worksheet/header/row metadata
network worksheet/header/row metadata
record_count
snapshot_id
existing network counters
issue counts
issues
```

Existing conversion report keys remain present for compatibility.

Each issue retains existing safe fields and may add:

```text
stage
source_file_role
source_column
related_row
safe structured details
```

Reports SHALL NOT contain complete source rows, workbook content, production inventory dumps, secrets, credentials, or unnecessary free-form evidence.

The GUI displays fatal issues first, supports filtering by issue class, and shows details for the selected issue. Filtering affects presentation only. `Save report` writes the complete unfiltered report as UTF-8 JSON with a trailing newline.

## Decision 9: Overwrite confirmation and publication ownership

If the selected output exists, the GUI asks for explicit confirmation immediately before starting conversion. Declining confirmation performs no conversion and changes no file.

After confirmation, the GUI delegates publication to the importer. It does not pre-delete, truncate, rename, or directly rewrite the existing output. Fatal failure leaves the previous output unchanged under the importer atomic-publication contract.

The output path may equal neither input path after path normalization. Invalid path relationships are fatal configuration/preflight issues.

## Decision 10: Tests and manual validation

Domain tests cover preflight/report compatibility without Qt. GUI tests run with `QT_QPA_PLATFORM=offscreen` and verify state transitions, path resets, stale detection, disabled controls, signal handling, report filtering/export, overwrite decline, and close blocking without reading production workbooks.

Manual smoke validation launches the standalone GUI as a detached process under the repository GUI launch rule. It uses synthetic workbooks and must not generate or commit production inventory.

## Risks and mitigations

- **Risk: GUI duplicates importer behavior.** Mitigation: only shared UI-independent APIs may classify or convert source data.
- **Risk: operator trusts stale tests.** Mitigation: fingerprint state plus mandatory reread on every combined preflight and conversion.
- **Risk: GUI freezes.** Mitigation: all workbook and conversion operations run in one background worker.
- **Risk: existing CLI consumers break.** Mitigation: preserve conversion signature and existing serialized report keys; additions are backward-compatible.
- **Risk: output is damaged on failure or close.** Mitigation: explicit confirmation, importer-owned atomic publication, and no worker termination.
- **Risk: reports leak operational data.** Mitigation: safe structured metadata only and no source-row dumps.
