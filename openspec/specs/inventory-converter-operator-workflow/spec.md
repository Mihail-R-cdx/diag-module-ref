# inventory-converter-operator-workflow Specification

## Purpose
TBD - created by archiving change standalone-inventory-converter-operator-workflow. Update Purpose after archive.
## Requirements
### Requirement: Converter GUI is a separate offline application

The repository SHALL provide a standalone PyQt5 inventory-converter application with its own launch entry point and `QApplication`. It SHALL run as a separate process from the diagnostic application and SHALL call the approved UI-independent inventory importer APIs.

The main diagnostic application SHALL NOT import the converter GUI, expose it in navigation, launch it at startup, or depend on converter paths, tests, reports, worker state, or PyQt widgets. The importer/domain layer SHALL NOT import PyQt5.

#### Scenario: Standalone converter starts independently

- **WHEN** an operator launches the converter entry point
- **THEN** it creates its own `QApplication` and converter window
- **AND** it does not create the main diagnostic window or application controllers

#### Scenario: Diagnostic application remains independent

- **WHEN** the normal diagnostic application starts and loads a canonical snapshot
- **THEN** it does not import or launch the converter GUI
- **AND** it does not require converter configuration or state

### Requirement: Operator selects exact source and output paths by operation

The standalone GUI SHALL display separate path controls for:

```text
primary equipment workbook
network connection workbook
exact output JSON file
```

Each workbook control SHALL use an `.xlsx` file-selection dialog. The output control SHALL use a JSON `Save As` dialog and SHALL display the exact selected filename. GUI conversion SHALL require both workbook paths and an output path and SHALL pass those explicit paths to the direct conversion API.

The GUI SHALL NOT silently substitute environment or module configuration for a path after the operator has selected or edited a value. The selected output path SHALL NOT normalize to either input path.

Operation prerequisites SHALL be exactly:

```text
Primary Test:
    primary workbook

Network Test:
    network workbook

Check all:
    primary workbook
    network workbook

Convert:
    primary workbook
    network workbook
    exact output JSON
```

An empty output path SHALL NOT block `Check all`. If an output path is already selected, `Check all` MAY additionally report a path conflict, but it SHALL remain a read-only operation over the two source workbooks and in-memory candidate.

#### Scenario: Operator selects all conversion paths

- **WHEN** the operator chooses the primary workbook, network workbook, and output JSON
- **THEN** the window displays all three exact paths
- **AND** conversion passes those explicit paths to the shared importer API

#### Scenario: Combined preflight runs before output selection

- **GIVEN** valid primary and network workbook paths
- **AND** the output path is blank
- **WHEN** the operator requests `Check all`
- **THEN** combined preflight runs normally
- **AND** it validates and reports the in-memory candidate
- **AND** it publishes no JSON

#### Scenario: Conversion path is missing

- **GIVEN** one of the two workbook paths or the output path is blank
- **WHEN** the operator requests `Convert`
- **THEN** the GUI presents a structured configuration failure
- **AND** it starts no publication operation

#### Scenario: Output conflicts with an input

- **GIVEN** the normalized output path equals either selected workbook path
- **WHEN** conversion preflight runs
- **THEN** the operation fails safely before publication
- **AND** neither workbook is modified

### Requirement: Each workbook has an independent read-only test state

The primary and network workbook controls SHALL each have a separate `Test` action. A test SHALL run the corresponding approved read-only source preflight outside the GUI thread and SHALL NOT publish JSON or modify source files.

Each source test presentation state SHALL be exactly one of:

```text
NOT_TESTED
RUNNING
PASSED
PASSED_WITH_WARNINGS
FAILED
STALE
```

`NOT_TESTED`, `RUNNING`, and `STALE` are GUI presentation states only and SHALL NOT appear as terminal report statuses. Completed report statuses map exactly:

```text
SUCCEEDED               -> PASSED
SUCCEEDED_WITH_WARNINGS -> PASSED_WITH_WARNINGS
FAILED                  -> FAILED
```

#### Scenario: Source test passes cleanly

- **GIVEN** a selected source satisfies its approved source contract without issues
- **WHEN** its `Test` action finishes with report status `SUCCEEDED`
- **THEN** its state becomes `PASSED`
- **AND** no output JSON is created or changed

#### Scenario: Source test passes with non-fatal issues

- **GIVEN** a selected source has no fatal issue but has data-quality or consistency issues
- **WHEN** its `Test` action finishes with report status `SUCCEEDED_WITH_WARNINGS`
- **THEN** its state becomes `PASSED_WITH_WARNINGS`
- **AND** the report exposes those issues

#### Scenario: Source test fails

- **GIVEN** a selected source has a fatal read, worksheet, header, or source-contract issue
- **WHEN** its `Test` action finishes with report status `FAILED`
- **THEN** its state becomes `FAILED`
- **AND** the safe failure report remains available

### Requirement: Source test freshness is explicit and non-authoritative

After a source test, the GUI SHALL retain a safe fingerprint containing the resolved path, file size, and highest available last-modified time. Editing a path SHALL reset that source state to `NOT_TESTED`. If the current fingerprint differs from the stored fingerprint, the prior state SHALL become `STALE` before it is presented as current or used for an operator decision.

No file watcher or full-file hash is required. A test result SHALL remain operator convenience only. Combined preflight and conversion SHALL reread and revalidate current source bytes regardless of previous test state.

#### Scenario: Path edit resets a test

- **GIVEN** a source is `PASSED`
- **WHEN** the operator edits its path
- **THEN** its state becomes `NOT_TESTED`
- **AND** the previous result is not presented as validation of the new path

#### Scenario: Tested file changes on disk

- **GIVEN** a source has a stored completed-test fingerprint
- **AND** its current size or last-modified time differs
- **WHEN** freshness is checked before a later action
- **THEN** its state becomes `STALE`

#### Scenario: Conversion ignores a fresh prior test as authority

- **GIVEN** both source tests currently show successful states
- **WHEN** the operator requests conversion
- **THEN** conversion still rereads and revalidates both files
- **AND** publication does not rely on cached test results

### Requirement: Combined preflight and conversion use one serialized worker lifecycle

The GUI SHALL provide a `Check all` action that runs the approved combined two-source preflight without publication and a `Convert` action that repeats full validation and then delegates guarded atomic publication to the importer.

All source tests, combined preflight, workbook reads, reconciliation, candidate validation, serialization, publication-precondition validation, and publication SHALL execute outside the Qt GUI thread. Only one operation may run at a time. While an operation runs, path controls and conflicting actions SHALL be disabled. Widgets SHALL be modified only in the GUI thread through signals or an equivalent safe queued mechanism.

The worker SHALL NOT be forcefully terminated. Window close while an operation runs SHALL be blocked or deferred with a clear message, including during atomic publication. Progress SHALL be indeterminate unless a real measurable progress contract exists; the GUI SHALL NOT invent percentages.

#### Scenario: Combined preflight completes without publication

- **GIVEN** valid primary and network workbook paths
- **WHEN** the operator chooses `Check all`
- **THEN** both workbooks are reread and reconciled in the worker
- **AND** an in-memory candidate is validated and reported
- **AND** no output path is required
- **AND** no JSON is created or replaced

#### Scenario: Conversion runs without freezing the GUI thread

- **WHEN** the operator starts conversion
- **THEN** workbook I/O and conversion execute in the worker
- **AND** the GUI thread remains responsible only for widgets and queued result handling
- **AND** conflicting controls remain disabled until completion

#### Scenario: Close is requested during publication

- **GIVEN** a conversion operation is running
- **WHEN** the operator attempts to close the window
- **THEN** the GUI does not terminate the worker
- **AND** close is blocked or deferred until the operation reaches a safe completion state

### Requirement: Existing output replacement uses a guarded confirmation precondition

Immediately before starting a GUI conversion, the GUI SHALL resolve the selected output path and record a publication precondition containing:

```text
resolved normalized output path
existed at confirmation: true | false
for an existing output:
    file size
    last-modified time with the platform's highest available precision
    stable file identity when available without reading unsafe content
```

If the output exists, the GUI SHALL request explicit confirmation to replace that exact observed file state. If the output is absent, the GUI SHALL proceed only under the explicit precondition that the path remains absent until publication. Declining confirmation SHALL start no conversion and SHALL leave the output unchanged.

After confirmation, the GUI SHALL NOT delete, truncate, pre-create, rename, or directly rewrite the output. It SHALL pass the precondition to the approved UI-independent guarded-publication boundary.

Immediately before atomic replacement, the publication boundary SHALL reject the operation if:

```text
a confirmed-absent output appeared;
a confirmed-existing output disappeared;
a confirmed-existing output size or mtime changed;
available stable file identity changed;
the normalized output path differs from the confirmed path.
```

A rejected publication SHALL report fatal `OUTPUT_CHANGED_SINCE_CONFIRMATION`, `stage = PUBLICATION`, and `source_file_role = OUTPUT`. It SHALL leave the current output untouched.

#### Scenario: Operator declines overwrite

- **GIVEN** the selected output exists
- **WHEN** the operator declines replacement confirmation
- **THEN** no conversion worker starts
- **AND** the existing output remains byte-for-byte unchanged

#### Scenario: Absent output appears during conversion

- **GIVEN** the output was absent when conversion started
- **AND** another process creates it before publication
- **WHEN** the publication precondition is checked
- **THEN** conversion fails with `OUTPUT_CHANGED_SINCE_CONFIRMATION`
- **AND** the newly created file is not replaced or removed

#### Scenario: Existing output changes during conversion

- **GIVEN** the operator confirmed an existing output fingerprint
- **AND** the output is modified or replaced before publication
- **WHEN** the publication precondition is checked
- **THEN** conversion fails with `OUTPUT_CHANGED_SINCE_CONFIRMATION`
- **AND** the changed output remains untouched

#### Scenario: Confirmed output remains unchanged

- **GIVEN** the output state still matches the recorded precondition
- **WHEN** candidate validation succeeds and publication begins
- **THEN** the importer replaces the output through the existing atomic-publication boundary

### Requirement: GUI presents and exports the complete closed safe report

After every completed source test, combined preflight, or conversion, the GUI SHALL show the shared operation report for success or failure.

The GUI SHALL consume the exact report enums and fields defined by `equipment-inventory-snapshot`. It SHALL NOT invent alternate terminal statuses, stages, issue keys, or source-role names.

The summary SHALL display, where applicable:

```text
operation
terminal status
published state
output path
stage reached
primary and network source row counts
record count
snapshot ID
network reconciliation counters
fatal, data-quality, and consistency issue counts
```

The issue table SHALL show fatal issues before non-fatal issues and SHALL expose class, stage, code, source role, worksheet, row, source column, record ID, and safe description. The operator SHALL be able to filter the table by issue class and inspect the exact shared `details` object for a selected issue.

Filtering SHALL affect presentation only. `Save report` SHALL export the complete unfiltered shared report as UTF-8 JSON with a trailing newline. Reports and exports SHALL NOT include complete source rows, workbook content, production inventory dumps, secrets, credentials, or unnecessary free-form evidence.

#### Scenario: Successful conversion report is displayed

- **WHEN** conversion publishes a valid snapshot
- **THEN** the report has `operation = CONVERSION`, terminal status `SUCCEEDED` or `SUCCEEDED_WITH_WARNINGS`, and `published = true`
- **AND** the GUI shows output path, record count, snapshot ID, counters, and all issues
- **AND** the complete report can be exported

#### Scenario: Failed conversion report is displayed

- **WHEN** conversion fails
- **THEN** the report has `operation = CONVERSION`, `status = FAILED`, and `published = false`
- **AND** the GUI shows the reached stage and fatal issues
- **AND** the report remains exportable even though no new snapshot was published

#### Scenario: Preflight publication state is false

- **WHEN** any primary, network, or combined preflight completes
- **THEN** its report has `published = false`
- **AND** no output path is required

#### Scenario: Filtering does not alter export

- **GIVEN** the operator filters the issue table to one class
- **WHEN** the operator saves the report
- **THEN** the exported JSON contains the complete unfiltered issue collection

### Requirement: Standalone GUI remains testable and locally disposable

GUI behavior SHALL be testable with synthetic workbooks and temporary files under an offscreen Qt platform. Tests SHALL cover state transitions, stale detection, serialized operations, overwrite decline, output-change rejection, close blocking, report rendering, filtering, and export without requiring production workbooks or the main diagnostic application.

Local selected-path preferences MAY be retained only as ignored local user state. Such preferences SHALL NOT be canonical data, snapshot identity, repository artifacts, validation evidence, or required configuration for CLI/direct API use.

#### Scenario: GUI tests run without a display server

- **WHEN** focused GUI tests run with `QT_QPA_PLATFORM=offscreen`
- **THEN** they exercise converter-window state and worker signal behavior using synthetic inputs
- **AND** they do not launch or import the main diagnostic application window

#### Scenario: Local path preferences are absent

- **GIVEN** no prior local GUI preference state exists
- **WHEN** the converter starts
- **THEN** it remains usable through explicit path selection
- **AND** no repository file is required or modified
