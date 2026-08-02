# inventory-converter-operator-workflow Specification

## ADDED Requirements

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

### Requirement: Operator selects exact two-source inputs and output

The standalone GUI SHALL display separate path controls for:

```text
primary equipment workbook
network connection workbook
exact output JSON file
```

Each workbook control SHALL use an `.xlsx` file-selection dialog. The output control SHALL use a JSON `Save As` dialog and SHALL display the exact selected filename. GUI conversion SHALL require both workbook paths and an output path and SHALL pass those explicit paths to the direct conversion API.

The GUI SHALL NOT silently substitute environment or module configuration for a path after the operator has selected or edited a value. The selected output path SHALL NOT normalize to either input path.

#### Scenario: Operator selects all conversion paths

- **WHEN** the operator chooses the primary workbook, network workbook, and output JSON
- **THEN** the window displays all three exact paths
- **AND** conversion passes those explicit paths to the shared importer API

#### Scenario: Required GUI path is missing

- **GIVEN** one of the two workbook paths or the output path is blank
- **WHEN** the operator requests combined validation or conversion
- **THEN** the GUI presents a structured configuration failure
- **AND** it starts no publication operation

#### Scenario: Output conflicts with an input

- **GIVEN** the normalized output path equals either selected workbook path
- **WHEN** conversion preflight runs
- **THEN** the operation fails safely before publication
- **AND** neither workbook is modified

### Requirement: Each workbook has an independent read-only test state

The primary and network workbook controls SHALL each have a separate `Test` action. A test SHALL run the corresponding approved read-only source preflight outside the GUI thread and SHALL NOT publish JSON or modify source files.

Each source test state SHALL be exactly one of:

```text
NOT_TESTED
RUNNING
PASSED
PASSED_WITH_WARNINGS
FAILED
STALE
```

No fatal issue SHALL result in `PASSED` or `PASSED_WITH_WARNINGS`. Non-fatal issues SHALL distinguish `PASSED_WITH_WARNINGS` from `PASSED`.

#### Scenario: Source test passes cleanly

- **GIVEN** a selected source satisfies its approved source contract without issues
- **WHEN** its `Test` action finishes
- **THEN** its state becomes `PASSED`
- **AND** no output JSON is created or changed

#### Scenario: Source test passes with non-fatal issues

- **GIVEN** a selected source has no fatal issue but has data-quality or consistency issues
- **WHEN** its `Test` action finishes
- **THEN** its state becomes `PASSED_WITH_WARNINGS`
- **AND** the report exposes those issues

#### Scenario: Source test fails

- **GIVEN** a selected source has a fatal read, worksheet, header, or source-contract issue
- **WHEN** its `Test` action finishes
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

The GUI SHALL provide a `Check all` action that runs the approved combined two-source preflight without publication and a `Convert` action that repeats full validation and then delegates atomic publication to the importer.

All source tests, combined preflight, workbook reads, reconciliation, candidate validation, serialization, and publication SHALL execute outside the Qt GUI thread. Only one operation may run at a time. While an operation runs, path controls and conflicting actions SHALL be disabled. Widgets SHALL be modified only in the GUI thread through signals or an equivalent safe queued mechanism.

The worker SHALL NOT be forcefully terminated. Window close while an operation runs SHALL be blocked or deferred with a clear message, including during atomic publication. Progress SHALL be indeterminate unless a real measurable progress contract exists; the GUI SHALL NOT invent percentages.

#### Scenario: Combined preflight completes without publication

- **WHEN** the operator selects valid current inputs and chooses `Check all`
- **THEN** both workbooks are reread and reconciled in the worker
- **AND** an in-memory candidate is validated and reported
- **AND** the output JSON is not created or replaced

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

### Requirement: Existing output replacement requires explicit confirmation

If the selected output path already exists, the GUI SHALL request explicit operator confirmation immediately before starting conversion. Declining SHALL start no conversion and SHALL leave the existing output unchanged.

After confirmation, the GUI SHALL NOT delete, truncate, pre-create, or directly rewrite the output. Publication remains owned by the importer and SHALL use the existing atomic replacement contract. A fatal failure SHALL preserve the previous valid output.

#### Scenario: Operator declines overwrite

- **GIVEN** the selected output exists
- **WHEN** the operator declines replacement confirmation
- **THEN** no conversion worker starts
- **AND** the existing output remains byte-for-byte unchanged

#### Scenario: Confirmed conversion fails

- **GIVEN** the operator confirms replacement of an existing output
- **AND** conversion later encounters a fatal issue before successful atomic replacement
- **WHEN** the operation finishes
- **THEN** the prior output remains intact
- **AND** the GUI presents the failed run report

### Requirement: GUI presents and exports the complete safe report

After every completed source test, combined preflight, or conversion, the GUI SHALL show the shared operation report for success or failure.

The summary SHALL display, where applicable:

```text
operation result
published state
output path
stage reached
primary and network source row counts
record count
snapshot ID
network reconciliation counters
fatal, data-quality, and consistency issue counts
```

The issue table SHALL show fatal issues before non-fatal issues and SHALL expose class, stage, code, source role, worksheet, row, source column, record ID, and safe description when available. The operator SHALL be able to filter the table by issue class and inspect safe details for a selected issue.

Filtering SHALL affect presentation only. `Save report` SHALL export the complete unfiltered shared report as UTF-8 JSON with a trailing newline. Reports and exports SHALL NOT include complete source rows, workbook content, production inventory dumps, secrets, credentials, or unnecessary free-form evidence.

#### Scenario: Successful conversion report is displayed

- **WHEN** conversion publishes a valid snapshot
- **THEN** the GUI shows publication state, output path, record count, snapshot ID, counters, and all non-fatal issues
- **AND** the complete report can be exported

#### Scenario: Failed operation report is displayed

- **WHEN** a test, combined preflight, or conversion fails
- **THEN** the GUI shows the reached stage and fatal issues
- **AND** the report remains exportable even though no new snapshot was published

#### Scenario: Filtering does not alter export

- **GIVEN** the operator filters the issue table to one class
- **WHEN** the operator saves the report
- **THEN** the exported JSON contains the complete unfiltered issue collection

### Requirement: Standalone GUI remains testable and locally disposable

GUI behavior SHALL be testable with synthetic workbooks and temporary files under an offscreen Qt platform. Tests SHALL cover state transitions, stale detection, serialized operations, overwrite decline, close blocking, report rendering, filtering, and export without requiring production workbooks or the main diagnostic application.

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
