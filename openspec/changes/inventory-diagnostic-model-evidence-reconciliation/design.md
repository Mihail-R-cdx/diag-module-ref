# Design: Inventory diagnostic model evidence reconciliation and standalone converter workflow

## Context

The approved inventory boundary remains:

```text
organization Excel workbook
    -> offline importer
    -> canonical versioned JSON snapshot
    -> runtime EquipmentInventory
    -> application-owned exact dispatch and orchestration
```

Canonical runtime records deliberately separate:

```text
source_model
    = normalized organization value from Наименование

diagnostic_model
    = exact application-supported canonical model or null
```

That separation remains correct. The current recognition authority is too narrow because only source `Модель` participates in the reviewed registry, while `Наименование` is preserved but ignored as recognition evidence. A reviewed production-data example proves that `Наименование` may contain unique deterministic evidence for an existing supported model when `Модель` does not produce a mapping.

The importer is also currently exposed mainly through a command-line entry point. Operators must type paths and inspect JSON written to a console. The existing `ImportResult` already contains useful structured evidence, but configuration failures are reported through a separate ad hoc shape, output-write failures can escape the result boundary, and source-layout failures do not identify the missing required headers in enough detail.

The correction belongs entirely inside the offline conversion toolchain. The converter GUI is a separate program and is not integrated into the diagnostic application.

## Goals

1. Use both source `Модель` and source `Наименование` as independent deterministic recognition evidence.
2. Preserve the existing closed nine-model registry and exact component-boundary semantics.
3. Accept one canonical model only when the distinct match union contains exactly one model.
4. Preserve ambiguity when evidence within or across the two fields names multiple supported models.
5. Preserve `Наименование -> source_model` without rewriting the source value.
6. Add a standalone PyQt5 converter GUI with native path-selection dialogs.
7. Keep the importer implementation UI-independent and reusable by CLI, tests, and the GUI.
8. Run conversion outside the Qt GUI thread.
9. Produce one complete structured run report for success and every known failure stage.
10. Make fatal source-contract failures directly understandable without exposing complete workbook rows or operational inventory.
11. Preserve atomic publication and runtime exact-only behavior.

## Non-goals

- Do not add the converter to the diagnostic application's main window, menus, pages, dialogs, startup, or lifecycle.
- Do not let the diagnostic application import or launch the standalone converter GUI.
- Do not add a new supported canonical diagnostic model.
- Do not map `Huawei CloudLink Box 610` or any other currently unsupported model.
- Do not change canonical JSON schema versions or record fields.
- Do not infer `diagnostic_model` at runtime from `source_model` or other free-form text.
- Do not modify diagnostic dispatch, credentials, controllers, workers, handlers, transports, PDU enrichment, or related-codec status logic.
- Do not let recognized model evidence override authoritative `Тип модели -> device_kind` mapping.
- Do not add fuzzy matching, arbitrary substring matching, typo correction, transliteration, edit distance, token similarity, manufacturer guessing, or machine-learning classification.
- Do not add workbook editing, row correction, in-place spreadsheet modification, automatic retry, background file watching, or scheduled conversion.
- Do not package a Windows installer or standalone `.exe` in this change.
- Do not persist recent-path history or application settings in the first implementation.
- Do not commit production workbook rows, generated production snapshots, internal IP addresses, room IDs, equipment IDs, MAC addresses, or serial numbers.

## Decision 1: Preserve the source/canonical split

`Наименование` remains authoritative for canonical `source_model`:

```text
normalize source Наименование
    -> source_model
```

Using the same normalized value as importer-only recognition evidence does not make `source_model` a runtime authority and does not authorize rewriting it.

Example:

```text
Наименование: ATEN Aten PE8208AV
Модель: blank

source_model: ATEN Aten PE8208AV
diagnostic_model: Aten PE8208AV
```

## Decision 2: Evaluate each evidence field independently

The importer applies the same existing normalization and component extraction to each field independently:

```text
source Модель
    -> normalized component set
    -> complete matching canonical-rule set

source Наименование
    -> normalized component set
    -> complete matching canonical-rule set
```

Normalization remains Unicode NFC, trim, Unicode-aware casefold, exact non-alphanumeric boundaries, exact letter/digit transitions, and the already approved `4i` mixed-component behavior.

The registry remains exactly the existing nine canonical models. No field-specific aliases, manufacturer requirements, or different rule ordering are introduced.

## Decision 3: Reconcile by distinct-match union

Let:

```text
M = complete canonical match set from Модель
N = complete canonical match set from Наименование
C = M union N
```

The outcome is determined only from the cardinality of `C`:

```text
|C| = 0
    -> diagnostic_model = null
    -> UNMAPPED_DIAGNOSTIC_MODEL

|C| = 1
    -> diagnostic_model = the one exact canonical model
    -> no unmapped or ambiguous model issue

|C| > 1
    -> diagnostic_model = null
    -> AMBIGUOUS_DIAGNOSTIC_MODEL
```

This policy is symmetric. Neither evidence field overrides the other.

## Decision 4: Reconciliation examples

### Blank model field, unique name field

```text
Модель: blank
Наименование: ATEN Aten PE8208AV
M = {}
N = {Aten PE8208AV}
C = {Aten PE8208AV}
```

Result: `Aten PE8208AV`.

### Unique model field, unmapped name field

```text
Модель: TE40
Наименование: ВКС терминал
M = {Huawei TE40}
N = {}
C = {Huawei TE40}
```

Result: `Huawei TE40`.

### Both fields agree

```text
Модель: PE8208AV
Наименование: ATEN Aten PE8208AV
M = {Aten PE8208AV}
N = {Aten PE8208AV}
C = {Aten PE8208AV}
```

Result: `Aten PE8208AV`.

### Fields disagree

```text
Модель: PCS4i
Наименование: ATEN Aten PE8208AV
M = {Extron IPL T PCS4i}
N = {Aten PE8208AV}
C = {Extron IPL T PCS4i, Aten PE8208AV}
```

Result: null plus `AMBIGUOUS_DIAGNOSTIC_MODEL`.

### One field is internally ambiguous

```text
Модель: TE20 / TE40
Наименование: Huawei TE20
M = {Huawei TE20, Huawei TE40}
N = {Huawei TE20}
C = {Huawei TE20, Huawei TE40}
```

Result: null plus `AMBIGUOUS_DIAGNOSTIC_MODEL`.

### Neither field maps

```text
Модель: CloudLink Box 610
Наименование: Huawei CloudLink Box 610
M = {}
N = {}
C = {}
```

Result: null plus `UNMAPPED_DIAGNOSTIC_MODEL`.

## Decision 5: The GUI is a separate offline program

The standalone entry point should be equivalent to:

```text
tools/equipment_inventory_converter_gui.py
```

It creates its own `QApplication` and top-level window. It must not import `gui.main_window`, instantiate `VCSDiagnosticApp`, register a diagnostic page, or participate in application composition.

The dependency direction is:

```text
standalone converter GUI
    -> importer public API
    -> canonical inventory primitives
```

Forbidden directions are:

```text
importer -> PyQt5 GUI
main diagnostic application -> converter GUI
converter GUI -> diagnostic controllers/workers/handlers
```

The existing CLI remains available through `tools/import_equipment_inventory.py` and calls the same importer API used by the GUI.

## Decision 6: Operator window layout

The initial window contains:

```text
Source workbook
    [editable path field] [Choose Excel...]

Output JSON
    [editable path field] [Save as...]

[Convert]
[indeterminate progress bar / current stage]

Run summary
Issue counters and publication status

Detailed issues table

[Save report...]
```

The source button uses the native `QFileDialog.getOpenFileName` behavior with an `.xlsx` filter. The output button uses native `QFileDialog.getSaveFileName` behavior with a `.json` filter and suggests `equipment_inventory.local.json`.

Selecting the exact output file is preferred over selecting only a directory because it keeps the final deployed file name visible and unambiguous. If the operator types a path without `.json`, the GUI may append `.json` after confirmation, but it must not silently change a non-empty different suffix.

The path fields remain editable so paths can be pasted, while the browse buttons satisfy normal mouse-only operation.

## Decision 7: Preflight behavior

Before starting conversion, the GUI validates only operator configuration that can be checked without parsing the workbook:

- source path is non-empty;
- source path resolves to an existing regular file;
- output path is non-empty and resolves to a file location rather than an existing directory;
- source and output paths are not the same file;
- output parent can be resolved or created under the existing importer publication policy.

The Convert button is disabled while mandatory path fields are empty. Invalid preflight produces a structured failed run report rather than only a transient message box.

When the selected output file already exists, the GUI requires explicit replacement confirmation immediately before submitting the run. Declining confirmation performs no conversion and no file mutation. It may leave the previous completed report visible.

## Decision 8: Conversion must not block the GUI thread

Workbook parsing and snapshot generation run in one dedicated worker object owned by a `QThread` or an equivalent Qt-safe worker boundary.

The main thread owns all widgets and dialogs. The worker receives immutable resolved source/output paths and emits only progress-stage text and the final structured report.

While a run is active:

- path fields and browse buttons are disabled;
- Convert is disabled;
- Save report remains available only for the last completed report;
- an indeterminate progress indicator is visible;
- closing the window either waits for completion or asks the operator to keep the program open; the first implementation does not abruptly terminate the worker during publication.

No cancellation contract is added in this change because safe interruption during workbook parsing and atomic publication requires a separate reviewed lifecycle.

## Decision 9: One structured report model

The importer/reporting boundary should return one structured report for every attempted run. Concrete private names are not contracts, but the observable report is equivalent to:

```text
status: SUCCESS | FAILED
published: boolean
source_path: absolute path or null
output_path: absolute path or null
started_at / finished_at or duration metadata
stage_reached
worksheet
header_row
source_row_count
record_count
snapshot_id
issue counts by class
issues[]
```

Every issue is equivalent to:

```text
issue_class: fatal | data_quality | consistency
stage: CONFIGURATION | WORKBOOK_READ | LAYOUT_DISCOVERY |
       ROW_MAPPING | CROSS_ROW_VALIDATION |
       CANDIDATE_VALIDATION | PUBLICATION | INTERNAL
code
worksheet: optional
row: optional
source_column: optional
record_id: optional
related_row: optional
safe description
safe structured details: optional
```

The report shape must be deterministic for equivalent input and failure conditions except for explicitly non-identity run timing metadata.

CLI JSON output and GUI report export use the same report serializer. The GUI may derive presentation labels from the structured fields but must not parse human-readable descriptions to determine severity or behavior.

## Decision 10: Fatal failures remain detailed and safe

Known blocking failures must not escape as unstructured exceptions. At minimum:

```text
SOURCE_NOT_CONFIGURED
SOURCE_NOT_FOUND
SOURCE_NOT_FILE
WORKBOOK_UNREADABLE
SOURCE_STRUCTURE_MISSING
SOURCE_STRUCTURE_AMBIGUOUS
MISSING_RECORD_ID
DUPLICATE_RECORD_ID
CANDIDATE_SNAPSHOT_INVALID
OUTPUT_WRITE_FAILED
UNEXPECTED_CONVERTER_FAILURE
```

The implementation may preserve existing codes where already normative, but all blocking outcomes must appear as `fatal` report issues with a stage.

`SOURCE_STRUCTURE_MISSING` must identify missing required headers using safe source-column names. The report may include a bounded structure equivalent to:

```text
worksheet
candidate header row when identifiable
missing required column names
```

It must not include arbitrary cell values or complete rows.

`MISSING_RECORD_ID` identifies the source row and `SmartRoomID` column.

`DUPLICATE_RECORD_ID` identifies the later row, the canonical record ID, and the first conflicting row when available.

`OUTPUT_WRITE_FAILED` identifies the output path and safe exception type or OS error category, while preserving the previous output through atomic publication.

Unexpected failures are caught at the outer converter boundary, reported as `UNEXPECTED_CONVERTER_FAILURE`, and may include exception type and stage but not workbook contents, credentials, or complete traceback text in the normal report.

## Decision 11: GUI report presentation

After every completed run, the GUI displays:

- a prominent success or failure state;
- whether a snapshot was published;
- source and output paths;
- selected worksheet and header row when available;
- source rows examined and canonical records produced;
- snapshot ID when published;
- fatal, data-quality, and consistency issue counts.

The detailed issue table is read-only and ordered by:

```text
fatal first
then data_quality
then consistency
then deterministic stage/row/code order
```

Columns are equivalent to:

```text
Class
Stage
Code
Worksheet
Row
Column
Record ID
Description
```

The GUI provides filtering at least by issue class and supports row selection to show full safe details without truncation. Sorting may be enabled only if it does not mutate the underlying report order or exported JSON.

## Decision 12: Report export is independent of snapshot publication

After a run completes, `Save report...` uses a native save dialog and writes the complete structured report as UTF-8 JSON with a terminal newline.

Report export is available after both success and failure. It must not overwrite the generated snapshot implicitly, and the default report file name should be distinct, such as:

```text
equipment_inventory_import_report.json
```

Failure to save the optional report is shown as a GUI-local error and does not retroactively change the conversion result or snapshot publication state.

## Decision 13: Preserve atomic publication

The existing candidate validation and temporary-file replacement flow remains authoritative:

```text
build complete candidate
    -> validate candidate
    -> write temporary JSON in output directory
    -> atomic replace
```

Any fatal condition before replacement leaves the previous output intact. Output-directory creation or replacement failure becomes `OUTPUT_WRITE_FAILED` and returns a failed report instead of terminating the GUI or CLI unexpectedly.

## Decision 14: Manufacturer and runtime boundaries remain unchanged

`Производитель` remains optional consistency evidence only. It cannot add, veto, remove, or select a model match.

The runtime contract remains:

```text
canonical diagnostic_model
    -> exact application-owned dispatch
```

Runtime modules must not reproduce component extraction, inspect `source_model` as protocol authority, or compensate for old snapshots. Deployment regenerates `equipment_inventory.local.json` with the corrected standalone converter.

## Implementation shape

A compliant implementation should separate:

```text
importer/domain layer
    - workbook read
    - layout selection
    - row mapping
    - model recognition
    - cross-row validation
    - candidate validation
    - atomic publication
    - structured report serialization

standalone GUI layer
    - native file dialogs
    - preflight path capture
    - worker thread lifecycle
    - progress presentation
    - summary and issue-table rendering
    - report export
```

No Qt type should be required to import or unit-test the importer/domain layer.

## Regression coverage

Focused synthetic tests must cover at least:

### Model evidence

- blank `Модель` plus recognized `Наименование`;
- recognized `Модель` plus blank or unmapped `Наименование`;
- both fields resolving to the same model;
- fields resolving to different models;
- one internally ambiguous field plus one agreeing unique field;
- one internally ambiguous field plus an unmapped field;
- both fields unmapped;
- all nine canonical models through `Наименование` evidence;
- existing separators, compact forms, optional suffix behavior, accent alternatives, and boundary-negative cases for both evidence fields;
- unchanged normalized `source_model` and authoritative `device_kind`.

### Structured report

- configuration failure produces a failed report;
- unreadable workbook produces a failed report;
- missing required headers identify the missing column names without row dumps;
- ambiguous worksheet layout is fatal and structured;
- missing and duplicate `SmartRoomID` include row/column/conflict context;
- candidate-validation failure is structured;
- output-write failure is structured and preserves the previous output;
- success report includes counts, snapshot ID, paths, and non-fatal issues;
- report serialization is deterministic and UTF-8 safe.

### Standalone GUI

- GUI module can start independently without importing or constructing the diagnostic main window;
- source chooser applies `.xlsx` filtering and populates the source field;
- output chooser applies `.json` filtering and populates the exact file field;
- Convert remains disabled for incomplete paths and during an active worker;
- existing output requires explicit confirmation;
- conversion is submitted to the worker rather than executed on the GUI thread;
- success and failure reports populate summary and issue table correctly;
- issue-class filtering does not change exported report content;
- report can be saved after both success and failure;
- no real organization data appears in fixtures, screenshots, logs, or diagnostics.

## Rollout

After implementation and validation:

1. Launch the standalone converter program separately from the diagnostic application.
2. Select the organization workbook and exact deployment-local JSON output path.
3. Run conversion and review fatal, data-quality, and consistency sections.
4. Save the report when operational evidence is required.
5. Replace the previous snapshot only through successful atomic publication.
6. Start or reload the diagnostic application under the existing deployment procedure.

No runtime migration, converter integration, or compatibility fallback is added.
