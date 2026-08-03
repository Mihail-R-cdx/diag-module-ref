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

The existing report is intentionally small. It lacks reusable read-only preflight operations, operation/stage metadata, source-file roles, source columns, related rows, and file-test state. Change 3 may extend those UI-independent structures additively, but it must preserve current CLI keys, the public direct conversion call, and all conversion behavior approved by Change 1 and Change 2.

## Goals

1. Provide an operator-friendly standalone Windows GUI for approved two-source schema-v3 conversion.
2. Keep importer/domain logic UI-independent and authoritative for CLI, GUI, and direct API use.
3. Test each workbook independently without writing JSON.
4. Revalidate both current source files together before every conversion.
5. Keep all workbook and conversion work outside the Qt GUI thread.
6. Preserve atomic publication, require overwrite confirmation, and reject publication when the output changes after confirmation.
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

The current direct conversion call remains valid:

```python
import_equipment_inventory(
    source_path,
    *,
    network_source_path=None,
    output_path=None,
    generated_at=None,
)
```

The implementation MAY add one optional keyword-only publication-precondition argument or expose a separate UI-independent guarded-publication entry point. Existing callers using the current call SHALL continue to work without changes. Existing serialized CLI report keys remain present. New report metadata is additive.

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

Operation prerequisites are distinct:

```text
PRIMARY_SOURCE_PREFLIGHT
    primary workbook

NETWORK_SOURCE_PREFLIGHT
    network workbook

COMBINED_PREFLIGHT
    primary workbook
    network workbook

CONVERSION from the standalone GUI
    primary workbook
    network workbook
    exact output JSON path
```

An empty output path SHALL NOT block `COMBINED_PREFLIGHT`. If an output path has already been selected, combined preflight MAY report a path conflict as additional configuration evidence, but output is not an input to candidate construction and is not a prerequisite for `Check all`.

## Decision 4: Independent read-only source tests

Each source row has a `Test` operation.

Primary-source test validates only primary-workbook concerns, including readability, unambiguous layout/header discovery, required columns, identity contract, field normalization, model recognition outcomes, and primary cross-row diagnostics.

Network-source test validates only network-workbook concerns, including readability, exact `Устройства` worksheet selection, required headers, MAC/IP/port normalization, empty candidates, duplicate normalized candidates, and source-internal ambiguity. It cannot classify inventory-relative outcomes such as `NETWORK_MAC_NOT_IN_INVENTORY` without the primary source.

A source test SHALL NOT:

- publish or replace JSON;
- modify either workbook;
- perform partial conversion publication;
- become authority for a later conversion.

The GUI presentation states are exactly:

```text
NOT_TESTED
RUNNING
PASSED
PASSED_WITH_WARNINGS
FAILED
STALE
```

These values are GUI state only. `NOT_TESTED`, `RUNNING`, and `STALE` are not terminal report statuses. A completed report maps to GUI state as follows:

```text
SUCCEEDED               -> PASSED
SUCCEEDED_WITH_WARNINGS -> PASSED_WITH_WARNINGS
FAILED                  -> FAILED
```

## Decision 5: Fingerprint and stale semantics

A successful or failed source test stores a safe fingerprint:

```text
resolved absolute path
file size
last-modified time with the platform's highest available precision
```

Changing the path text resets the corresponding result to `NOT_TESTED`. Before the GUI displays a prior result as current, before combined preflight, and before conversion, it compares the current fingerprint. A mismatch changes the result to `STALE`.

No background file watcher or full-workbook hash is required. Conversion always rereads and revalidates current bytes regardless of test status.

## Decision 6: Combined preflight is distinct from individual tests and publication

`Check all` runs a read-only combined preflight over both current sources. It repeats each source validation and additionally performs the approved MAC-only reconciliation needed to expose:

```text
NETWORK_MAC_NOT_IN_INVENTORY
AMBIGUOUS_INVENTORY_MAC_FOR_SWITCH
AMBIGUOUS_SWITCH_CONNECTION
DUPLICATE_SWITCH_CONNECTION_SOURCE
partial connection outcomes
```

Combined preflight builds and validates an in-memory candidate document but SHALL NOT publish it. It may compute candidate schema version 3, record count, and snapshot ID for reporting. It neither requires nor owns an output path.

`Convert` does not trust a previous combined result. It repeats full preflight and candidate validation on current bytes before guarded atomic publication.

## Decision 7: One serialized background operation

All source tests, combined preflight, workbook reads, reconciliation, candidate validation, JSON serialization, publication-precondition validation, and publication run outside the GUI thread.

Only one operation may run at a time. While an operation is active, the GUI disables path editing, browse buttons, tests, combined preflight, conversion, and report export actions that could conflict with the operation.

A `QThread` plus worker `QObject`, or an equivalent testable PyQt5 pattern, SHALL communicate immutable result objects back by signals. Widgets are read and modified only in the GUI thread.

The worker SHALL NOT be killed with `terminate()`. Closing the window while an operation is running is blocked or deferred with a clear message. In particular, the GUI must not interrupt importer-owned atomic publication.

The progress indicator is indeterminate unless a real measurable progress contract is introduced. The status label may display coarse operation/stage names from the UI-independent report callback; it must not invent percentages.

## Decision 8: Closed unified safe report contract

CLI conversion, GUI conversion, direct API conversion, source tests, and combined preflight SHALL serialize reports from shared UI-independent result types.

### Operations

`operation` is exactly one of:

```text
PRIMARY_SOURCE_PREFLIGHT
NETWORK_SOURCE_PREFLIGHT
COMBINED_PREFLIGHT
CONVERSION
```

### Terminal statuses

`status` is exactly one of:

```text
SUCCEEDED
SUCCEEDED_WITH_WARNINGS
FAILED
```

`SUCCEEDED` means no issue was emitted. `SUCCEEDED_WITH_WARNINGS` means no fatal issue was emitted and at least one `data_quality` or `consistency` issue was emitted. `FAILED` means at least one fatal issue was emitted or the operation could not safely produce its intended terminal result.

### Stages

`stage_reached` is exactly one of:

```text
CONFIGURATION
SOURCE_PREFLIGHT
WORKBOOK_READ
LAYOUT_DISCOVERY
ROW_MAPPING
SOURCE_VALIDATION
CROSS_SOURCE_RECONCILIATION
CANDIDATE_VALIDATION
PUBLICATION
COMPLETE
INTERNAL
```

It records the furthest stage entered by the operation. `COMPLETE` is used only for a successful or successful-with-warnings terminal operation. `INTERNAL` is used only when an unexpected internal failure prevents a more specific stage classification.

### Exact additive root keys

Every serialized shared report contains all of these additive keys:

```text
operation: non-null operation enum
status: non-null terminal-status enum
stage_reached: non-null stage enum
schema_version: integer or null
source_files: object
    primary: resolved absolute string or null
    network: resolved absolute string or null
output_path: resolved absolute string or null
published: boolean
data_quality_issue_count: non-negative integer
consistency_issue_count: non-negative integer
```

The existing conversion report keys remain present with their current names and meanings:

```text
worksheet
header_row
source_row_count
record_count
snapshot_id
network_worksheet
network_header_row
network_source_row_count
distinct_network_mac_count
enriched_record_count
empty_connection_row_count
duplicate_connection_count
ambiguity_count
unmatched_network_mac_count
fatal_issue_count
non_fatal_issue_count
issues
```

For preflight reports, existing fields that are not applicable are present with `null`, except counts that are known for that operation remain non-negative integers. For conversion reports, existing values preserve their current semantics. `output_path` is non-null for `CONVERSION` and null for all three preflight operations. `schema_version` is null until a candidate schema is known.

`published` is normative:

```text
PRIMARY_SOURCE_PREFLIGHT -> false
NETWORK_SOURCE_PREFLIGHT -> false
COMBINED_PREFLIGHT       -> false
successful CONVERSION    -> true
failed CONVERSION        -> false
```

### Exact issue shape

Every serialized issue contains all existing keys:

```text
class: fatal | data_quality | consistency
code: non-empty string
sheet: string or null
row: positive integer or null
record_id: string or null
description: safe string
```

and all additive keys:

```text
stage: stage enum
source_file_role: PRIMARY | NETWORK | OUTPUT | null
source_column: string or null
related_row: positive integer or null
details: object
```

`details` is a flat JSON object whose values are JSON scalars or arrays of JSON scalars. It SHALL NOT contain nested source rows, workbook fragments, canonical record dumps, credentials, secrets, or unnecessary free-form evidence. Consumers SHALL serialize the same shape; adapters may not invent alternate field names or omit the additive issue keys.

The GUI displays fatal issues first, supports filtering by issue class, and shows details for the selected issue. Filtering affects presentation only. `Save report` writes the complete unfiltered report as UTF-8 JSON with a trailing newline.

## Decision 9: Overwrite confirmation creates a publication precondition

Immediately before starting a GUI conversion, the GUI resolves the selected output path and records a UI-independent publication precondition:

```text
resolved output path
existed at confirmation: true | false
if existing:
    file size
    last-modified time with the platform's highest available precision
    file identity when the platform exposes a stable identity without opening unsafe content
```

If the output exists, the operator confirms replacement of that exact observed file state. If the output does not exist, the operator confirms creation only under the precondition that it remains absent until publication.

After confirmation, the GUI delegates conversion and guarded publication to the UI-independent importer/publication boundary. The GUI SHALL NOT delete, truncate, pre-create, rename, or directly rewrite the output.

Immediately before `os.replace` or an equivalent atomic replacement, the publication boundary SHALL resolve and inspect the output again. Publication proceeds only when the current state matches the confirmed precondition:

```text
confirmed absent -> still absent
confirmed existing -> still the same observed file state
```

The precondition fails when, after confirmation:

```text
the absent output appears;
the existing output disappears;
the existing output size or mtime changes;
the existing path resolves to a replacement file with different available identity;
the normalized output path no longer matches the confirmed path.
```

A failed precondition emits structured fatal issue:

```text
OUTPUT_CHANGED_SINCE_CONFIRMATION
```

with `stage = PUBLICATION` and `source_file_role = OUTPUT`. It SHALL leave the current output untouched. The guard is checked after candidate validation and immediately before replacement, closing the time-of-check/time-of-use gap as far as the local filesystem contract permits.

CLI/direct API callers that do not supply a publication precondition retain the existing atomic-publication behavior. The current direct conversion call remains valid. The standalone GUI SHALL always use guarded publication.

The output path may equal neither input path after path normalization. Invalid path relationships are fatal conversion-configuration issues. They do not block combined preflight when no output is selected.

## Decision 10: Tests and manual validation

Domain tests cover preflight/report compatibility and guarded publication without Qt. GUI tests run with `QT_QPA_PLATFORM=offscreen` and verify state transitions, path resets, stale detection, disabled controls, signal handling, report filtering/export, overwrite decline, output-change rejection, and close blocking without reading production workbooks.

Manual smoke validation launches the standalone GUI as a detached process under the repository GUI launch rule. It uses synthetic workbooks and must not generate or commit production inventory.

## Risks and mitigations

- **Risk: GUI duplicates importer behavior.** Mitigation: only shared UI-independent APIs may classify or convert source data.
- **Risk: operator trusts stale tests.** Mitigation: fingerprint state plus mandatory reread on every combined preflight and conversion.
- **Risk: GUI freezes.** Mitigation: all workbook and conversion operations run in one background worker.
- **Risk: existing CLI consumers break.** Mitigation: preserve the current direct call and existing serialized report keys; additions are backward-compatible.
- **Risk: output changes after confirmation.** Mitigation: mandatory publication precondition and immediate pre-replacement recheck for GUI conversion.
- **Risk: output is damaged on failure or close.** Mitigation: guarded importer-owned atomic publication and no worker termination.
- **Risk: reports leak operational data.** Mitigation: closed safe structured metadata only and no source-row dumps.
