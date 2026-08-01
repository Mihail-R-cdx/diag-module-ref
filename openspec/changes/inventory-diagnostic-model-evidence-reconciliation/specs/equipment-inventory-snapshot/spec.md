# equipment-inventory-snapshot Specification

## MODIFIED Requirements

### Requirement: Confirmed organization source-to-canonical mapping

For the inspected organization workbook, the importer SHALL use this authoritative schema-v1 mapping:

```text
SmartRoomID       -> record_id
ID комнаты        -> room_id
Название комнаты  -> room_name
Наименование      -> source_model
IP                -> ip_address
MAC               -> mac_address
Серийный номер    -> serial_number
Тип модели        -> device_kind
```

`diagnostic_model` SHALL be populated only through the separate explicit reviewed component registry defined by this capability. The importer SHALL apply that registry independently to normalized source `Модель` evidence and normalized source `Наименование` evidence, then reconcile the complete distinct canonical match union under the explicit cardinality requirement. `Наименование` SHALL remain authoritative for canonical `source_model`; using it as importer-side recognition evidence SHALL NOT rewrite `source_model` or make free-form source text a runtime dispatch authority.

The importer SHALL NOT guess a supported `diagnostic_model` from fuzzy, approximate, similar-looking, or arbitrary substring text. The source column `Производитель` MAY be used only as importer-side consistency evidence. It SHALL NOT be required for diagnostic-model recognition, add or remove a registry match, veto a unique reconciled match, or select between multiple matching registry rules. Neither `Производитель` nor `Модель` becomes a separate canonical schema-v1 field.

The source column `SmartRoomID контроллера` MAY be used only as importer-side consistency evidence for this capability. It SHALL NOT create `controller_record_id` or another controller relation in schema v1 and SHALL NOT create a runtime controller index.

#### Scenario: Confirmed source row is mapped

- **WHEN** the importer reads a source equipment row using the confirmed organization source contract
- **THEN** each available mapped source value is normalized into its corresponding canonical field
- **AND** source-only evidence fields are not copied into schema v1 unless explicitly approved by the schema
- **AND** diagnostic-model recognition follows only the reviewed component registry over the two approved model-text evidence fields

#### Scenario: Manufacturer evidence is unavailable

- **GIVEN** a source row has no usable `Производитель` value
- **WHEN** the reconciled match union from normalized `Модель` and `Наименование` evidence contains exactly one canonical model
- **THEN** the importer publishes that exact canonical `diagnostic_model`
- **AND** missing manufacturer evidence does not veto the result

#### Scenario: Model field is blank but name field is recognized

- **GIVEN** normalized source `Модель` is blank or unmapped
- **WHEN** normalized source `Наименование` satisfies exactly one reviewed registry rule and no other rule matches either field
- **THEN** the importer publishes that rule's exact canonical `diagnostic_model`
- **AND** canonical `source_model` remains the normalized `Наименование` value

### Requirement: Наименование is the authoritative source_model value

For the confirmed organization workbook, `Наименование` SHALL map directly to canonical `source_model` after canonical text normalization. If `Наименование` is absent or blank, `source_model` SHALL be null.

When `Наименование` is present, the importer SHALL NOT silently reconstruct or overwrite `source_model` from `Производитель` plus `Модель`. `Наименование` MAY also supply importer-side diagnostic-model recognition evidence through the same closed reviewed component registry used for `Модель`, but that derived use SHALL NOT alter the canonical `source_model` value and SHALL NOT authorize runtime dispatch from `source_model`.

`Производитель` and `Модель` MAY be used for consistency diagnostics. A mismatch among `Наименование`, `Производитель`, and `Модель` SHALL NOT by itself block snapshot publication or rewrite canonical `source_model`. When approved model-text evidence yields multiple distinct supported canonical matches, the diagnostic model outcome SHALL remain ambiguous under the separate cardinality requirement.

#### Scenario: Source model evidence disagrees

- **WHEN** normalized `Наименование` does not match an expected manufacturer/model combination derived for consistency checking
- **THEN** canonical `source_model` remains the normalized `Наименование` value
- **AND** the importer may report a structured non-fatal consistency issue
- **AND** it does not silently rewrite the source value

#### Scenario: Name evidence supplies a diagnostic model

- **GIVEN** normalized `Наименование` contains one unique reviewed supported-model pattern
- **WHEN** the importer uses that value as recognition evidence
- **THEN** canonical `source_model` remains the complete normalized `Наименование` text
- **AND** canonical `diagnostic_model` may contain the exact reviewed canonical model
- **AND** runtime consumers still use only `diagnostic_model` as dispatch authority

### Requirement: Diagnostic model recognition uses deterministic reviewed components

The importer SHALL evaluate source `Модель` and source `Наименование` as two independent approved model-text evidence fields. For each field separately, it SHALL apply Unicode NFC normalization, leading/trailing trim, and Unicode-aware casefold before recognition. A blank normalized value SHALL provide no components.

Recognition SHALL use exact components rather than arbitrary substrings. Non-alphanumeric characters SHALL act as component boundaries. Letter-to-digit and digit-to-letter transitions inside one alphanumeric chunk SHALL expose exact alphabetic and decimal components so compact forms such as `TE40`, `IN1804`, `PE8208`, and `DMP64` are recognized. An immediately adjacent decimal run plus alphabetic suffix SHALL also expose the exact reviewed mixed component needed for `4i` in `PCS4i`.

Component order and repetition SHALL NOT affect rule satisfaction. Space, hyphen, underscore, dot, slash, and other non-alphanumeric separators SHALL be treated as equivalent boundaries. The importer SHALL NOT use transliteration, typo correction, edit distance, token similarity, manufacturer guessing, field-specific aliases, or undeclared aliases.

The same closed reviewed registry SHALL be evaluated independently against each evidence field and SHALL remain exactly:

| Canonical `diagnostic_model` | Mandatory components in either approved evidence field |
| --- | --- |
| `Huawei TE20` | `te` and `20` |
| `Huawei TE40` | `te` and `40` |
| `CloudLink Bar 310` | `cloudlink`, `bar`, and `310` |
| `Polycom RPG 310` | (`rpg` and `310`) or (`realpresence`, `group`, and `310`) |
| `Extron IN1804` | `in` and `1804` |
| `Aten PE8208AV` | `pe` and `8208` |
| `Extron IPL T PCS4i` | `ipl`, `pcs`, and `4i` |
| `Biamp Tesira Forte CI` | `tesira` and (`forte` or `forté`) |
| `Extron DMP 64 Plus` | `dmp` and `64` |

`AV`, `CI`, and `Plus` SHALL NOT be required components for their canonical rules. Rule order and evidence-field order SHALL NOT grant authority or priority. This requirement SHALL NOT add any canonical model outside the existing registry.

#### Scenario: Compact TE40 evidence is recognized in either field

- **WHEN** normalized source `Модель` or normalized source `Наименование` is `TE40`, `TE 40`, or `TE-40`
- **THEN** that field's evidence contains exact components `te` and `40`
- **AND** the `Huawei TE40` rule matches that field

#### Scenario: Optional canonical suffix is absent

- **WHEN** either normalized approved evidence field contains exact components `pe` and `8208` without `av`
- **THEN** the `Aten PE8208AV` rule matches that field
- **AND** the importer does not require the optional canonical suffix in source evidence

#### Scenario: Forte accent alternative is recognized

- **WHEN** either normalized approved evidence field contains `tesira` and exact component `forte` or `forté`
- **THEN** the `Biamp Tesira Forte CI` rule matches that field

#### Scenario: Similar longer components are rejected

- **WHEN** either normalized approved evidence field is `LTE 40`, `TE200`, `TE401`, `IN18040`, `PE82080`, or `DMP640`
- **THEN** no reviewed rule matches that field merely because a shorter key appears as a substring

#### Scenario: Unsupported model remains unmapped

- **WHEN** approved evidence contains `Huawei CloudLink Box 610` and no existing registry rule is satisfied
- **THEN** this requirement adds no new canonical model match
- **AND** separate support for that device requires another reviewed OpenSpec change

### Requirement: Diagnostic model match cardinality remains explicit

The importer SHALL evaluate every reviewed diagnostic-model rule independently against normalized source `Модель` evidence and normalized source `Наименование` evidence before selecting an outcome for a source row. Each field SHALL produce the complete set of matching canonical models. The importer SHALL form one combined set containing the distinct union of matches from both fields.

The outcome SHALL be exactly one of:

```text
zero distinct matches across both fields
    -> diagnostic_model = null
    -> one non-fatal data-quality issue UNMAPPED_DIAGNOSTIC_MODEL

exactly one distinct match across both fields
    -> diagnostic_model = that exact canonical value
    -> no UNMAPPED_DIAGNOSTIC_MODEL or AMBIGUOUS_DIAGNOSTIC_MODEL issue

more than one distinct match across both fields
    -> diagnostic_model = null
    -> one non-fatal data-quality issue AMBIGUOUS_DIAGNOSTIC_MODEL
```

The importer SHALL NOT select the first matching rule, depend on registry order, prioritize `Модель` over `Наименование`, prioritize `Наименование` over `Модель`, use `Производитель` as a tie-breaker, discard an internally ambiguous field because the other field agrees with one candidate, or emit both unmapped and ambiguous issues for the same row.

An unmapped or ambiguous model SHALL NOT by itself make an otherwise representable canonical record fatal or remove it from the candidate snapshot. Structured model-recognition issues MAY expose the safe source row number and canonical `record_id`. Normal diagnostics SHALL NOT dump either complete source field, the complete source row, workbook, production snapshot, or organization inventory.

#### Scenario: Exactly one distinct rule matches across the evidence fields

- **WHEN** the union of all reviewed matches from `Модель` and `Наименование` contains exactly one canonical model
- **THEN** canonical `diagnostic_model` is that exact supported model name
- **AND** no unmapped or ambiguous model issue is emitted

#### Scenario: No rule matches either field

- **WHEN** no reviewed rule matches normalized `Модель` or normalized `Наименование`, including when either or both fields are missing or blank
- **THEN** canonical `diagnostic_model` is null
- **AND** the importer emits `UNMAPPED_DIAGNOSTIC_MODEL`
- **AND** the row remains publishable when otherwise valid

#### Scenario: Both fields agree on one model

- **WHEN** `Модель` and `Наименование` independently match the same one canonical model and no additional rule matches either field
- **THEN** the distinct union contains one model
- **AND** canonical `diagnostic_model` is that model
- **AND** duplicate agreement does not create ambiguity

#### Scenario: Evidence fields resolve to different models

- **WHEN** normalized `Модель` matches one supported canonical model and normalized `Наименование` matches a different supported canonical model
- **THEN** canonical `diagnostic_model` is null
- **AND** the importer emits `AMBIGUOUS_DIAGNOSTIC_MODEL`
- **AND** neither evidence field overrides the other
- **AND** the row remains publishable when otherwise valid

#### Scenario: One evidence field is internally ambiguous

- **GIVEN** one approved evidence field satisfies more than one registry rule, such as combined `TE20 / TE40` evidence
- **WHEN** the other field is unmapped or agrees with only one of those candidates
- **THEN** the combined distinct union still contains more than one model
- **AND** canonical `diagnostic_model` is null
- **AND** the importer emits `AMBIGUOUS_DIAGNOSTIC_MODEL`
- **AND** it does not erase contradictory evidence through field priority or manufacturer evidence

## ADDED Requirements

### Requirement: Converter GUI is a separate offline program

The repository SHALL provide a standalone equipment-inventory converter GUI with its own process entry point and top-level Qt application. The converter GUI SHALL call the same UI-independent importer boundary used by CLI and direct automation.

The standalone converter SHALL NOT be added as a page, dialog, menu item, button, startup action, controller, worker, or composition dependency of the diagnostic application. The diagnostic application SHALL NOT import, launch, or require the converter GUI to start or execute device diagnostics.

The importer/domain module SHALL NOT import PyQt or require a running `QApplication`.

#### Scenario: Converter starts independently

- **WHEN** the standalone converter entry point starts
- **THEN** it creates its own Qt application and converter window
- **AND** it does not create the diagnostic main window
- **AND** it does not initialize diagnostic controllers, workers, handlers, credentials, or network operations

#### Scenario: Diagnostic application starts without converter GUI

- **WHEN** the normal diagnostic application starts
- **THEN** it does not import or instantiate the standalone converter GUI
- **AND** converter-GUI availability does not affect runtime inventory loading or diagnostics

### Requirement: Standalone GUI selects exact source and output paths

The converter window SHALL expose an editable source-workbook path and an editable exact output-JSON file path.

The source browse action SHALL use the platform-native open-file dialog where available and SHALL filter for `.xlsx` workbooks. The output browse action SHALL use the platform-native Save As dialog where available, SHALL filter for `.json`, and SHALL suggest `equipment_inventory.local.json` as the output file name.

The GUI SHALL validate that the source path is non-empty, resolves to an existing regular file, the output path is non-empty and does not resolve to an existing directory, and source and output are not the same file. Invalid preflight SHALL produce a structured failed report and SHALL perform no workbook import or output mutation.

When the output file already exists, the GUI SHALL require explicit operator confirmation immediately before conversion. Declining replacement SHALL perform no conversion and no file mutation.

#### Scenario: Operator chooses paths with native dialogs

- **WHEN** the operator activates the source and output browse actions
- **THEN** the GUI opens the corresponding native file dialogs where supported
- **AND** accepted selections populate the exact path fields

#### Scenario: Existing output replacement is declined

- **GIVEN** the selected output file already exists
- **WHEN** the operator declines replacement confirmation
- **THEN** conversion does not start
- **AND** the existing output remains unchanged

#### Scenario: Preflight path is invalid

- **WHEN** the source is missing, is not a regular file, the output is an existing directory, or source and output resolve to the same file
- **THEN** the GUI publishes a structured failed run report
- **AND** it performs no workbook parsing or snapshot publication

### Requirement: Standalone GUI keeps conversion off the GUI thread

Workbook reading, row conversion, candidate validation, and snapshot publication SHALL execute outside the Qt GUI thread through one dedicated worker boundary.

While conversion is active, the GUI SHALL disable path mutation and additional conversion submission, SHALL show an indeterminate progress state or current safe stage, and SHALL keep widget mutation on the GUI thread.

The initial implementation SHALL NOT forcibly terminate the conversion worker during publication. Closing the window during an active run SHALL not abruptly kill the worker in a way that can bypass atomic-publication cleanup.

#### Scenario: Conversion is running

- **WHEN** the operator starts conversion with valid confirmed paths
- **THEN** the importer runs through the dedicated worker boundary
- **AND** source/output controls and Convert are disabled until completion
- **AND** the GUI thread remains available to paint progress and receive the final report

#### Scenario: Second conversion is requested while active

- **WHEN** one conversion is already active
- **THEN** the GUI does not submit another importer run
- **AND** the active run retains sole ownership of its immutable path inputs

### Requirement: Every attempted conversion produces one structured run report

The converter boundary SHALL produce one structured report for successful publication and every known failure stage. CLI output, direct API consumers, GUI presentation, and report export SHALL use the same report serializer rather than separate ad hoc result shapes.

The report SHALL expose fields equivalent to:

```text
status
published
source_path
output_path
stage_reached
worksheet
header_row
source_row_count
record_count
snapshot_id
issue counts by class
issues
```

Each issue SHALL expose fields equivalent to:

```text
issue_class
stage
code
worksheet, when applicable
row, when applicable
source_column, when applicable
record_id, when safe and applicable
related_row, when applicable
safe description
safe structured details, when applicable
```

Known blocking outcomes SHALL be represented as `fatal` issues rather than escaping as unstructured exceptions. At minimum, configuration, missing/non-file source, unreadable workbook, missing/ambiguous source structure, missing/duplicate `SmartRoomID`, invalid candidate snapshot, and output publication failure SHALL be structured.

Unexpected outer-boundary failures SHALL become a safe fatal `UNEXPECTED_CONVERTER_FAILURE` report containing stage and exception type but not complete workbook rows, cell contents, production inventory, or complete traceback text.

#### Scenario: Conversion succeeds

- **WHEN** the complete candidate validates and atomic publication succeeds
- **THEN** the report has success status and `published = true`
- **AND** it contains the output path, source-row count, canonical-record count, snapshot ID, and all non-fatal issues

#### Scenario: Conversion fails before publication

- **WHEN** a blocking failure occurs at configuration, workbook read, layout discovery, row mapping, candidate validation, or publication
- **THEN** the report has failed status and `published = false`
- **AND** it contains at least one fatal issue identifying the failure stage and code
- **AND** the failure is available to CLI and GUI consumers through the same report shape

### Requirement: Fatal source-structure and required-value evidence is detailed but safe

When no worksheet contains the required source structure, the fatal report SHALL identify required header names missing from inspected candidate worksheets using safe worksheet/header metadata. It SHALL NOT dump complete source rows or arbitrary cell values.

A missing `SmartRoomID` fatal issue SHALL identify the source row and `SmartRoomID` source column. A duplicate `SmartRoomID` fatal issue SHALL identify the later row, safe canonical record ID, and first conflicting row when available.

Output publication failure SHALL identify the resolved output path and safe exception type or OS error category. It SHALL preserve the previous valid output through the atomic-publication contract.

#### Scenario: Required columns are missing

- **WHEN** layout discovery cannot find all required headers
- **THEN** the failed report identifies the missing required column names for inspected candidate worksheet/header locations
- **AND** it does not include complete source rows or unrelated cell values

#### Scenario: SmartRoomID is missing

- **WHEN** a source equipment row has no usable `SmartRoomID`
- **THEN** the fatal issue identifies that row and source column
- **AND** the report explains that publication was blocked

#### Scenario: SmartRoomID is duplicated

- **WHEN** a later row repeats a canonical `SmartRoomID`
- **THEN** the fatal issue identifies the later row and first conflicting row when available
- **AND** no fallback identity is generated

#### Scenario: Output cannot be replaced

- **GIVEN** a previous valid output exists
- **WHEN** temporary output creation or atomic replacement fails
- **THEN** the report contains fatal `OUTPUT_WRITE_FAILED`
- **AND** the previous valid output remains intact

### Requirement: GUI presents and exports the complete report

After each completed run, the standalone GUI SHALL present a prominent success/failure state, snapshot publication state, source/output paths, worksheet/header when available, source-row count, canonical-record count, snapshot ID when available, and issue counts by class.

The GUI SHALL show a read-only detailed issue table with fields equivalent to class, stage, code, worksheet, row, source column, record ID, and description. Fatal issues SHALL appear before data-quality and consistency issues in the deterministic initial order. The GUI SHALL support at least issue-class filtering and SHALL show full safe details for the selected issue.

The GUI SHALL allow the operator to save the complete report as UTF-8 JSON after both successful and failed runs. Report export SHALL use a file name distinct from the snapshot, such as `equipment_inventory_import_report.json`. Filtering or sorting the visible table SHALL NOT alter the exported report content or order.

Failure to save the optional report SHALL be presented as a GUI-local error and SHALL NOT change the completed conversion result or snapshot publication state.

#### Scenario: Fatal conversion report is displayed

- **WHEN** conversion completes with fatal issues
- **THEN** the GUI shows failed publication prominently
- **AND** fatal issues are visible before non-fatal issues
- **AND** the operator can inspect row/column/missing-header context where available

#### Scenario: Successful report is displayed

- **WHEN** snapshot publication succeeds
- **THEN** the GUI shows success, output path, record counts, snapshot ID, and any non-fatal issues

#### Scenario: Report is saved after failure

- **GIVEN** a failed conversion produced a structured report
- **WHEN** the operator saves the report
- **THEN** the complete UTF-8 JSON report is written independently of snapshot publication
- **AND** the failed conversion does not create or replace the snapshot

### Requirement: CLI and direct importer API remain supported

The existing command-line converter and direct import API SHALL remain supported. They SHALL use the same importer/domain execution and report serialization as the standalone GUI.

The CLI SHALL continue returning a non-zero process exit code when publication fails and zero when publication succeeds. It SHALL emit the complete structured report as UTF-8 JSON in both cases.

Adding the standalone GUI SHALL NOT require CLI callers or tests to create a Qt application.

#### Scenario: CLI conversion succeeds

- **WHEN** the CLI runs with valid source and output paths and publication succeeds
- **THEN** it emits the shared successful report
- **AND** exits with code zero

#### Scenario: CLI conversion fails

- **WHEN** the CLI encounters a structured blocking failure
- **THEN** it emits the shared failed report
- **AND** exits with a non-zero code
- **AND** no Qt application is required
