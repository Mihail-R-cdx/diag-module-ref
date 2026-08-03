# equipment-inventory-snapshot Specification Delta

## ADDED Requirements

### Requirement: Importer exposes reusable read-only source preflight

The offline inventory importer SHALL expose UI-independent read-only preflight operations for the primary equipment workbook and the network-connection workbook. These operations SHALL reuse the same workbook reader, worksheet/header discovery, source normalization, row validation, diagnostic-model recognition, network candidate normalization, and issue classification used by conversion.

A source preflight SHALL NOT create, replace, truncate, rename, or validate through publication an output JSON file. It SHALL NOT modify either workbook. It SHALL return a structured result for both success and failure rather than requiring a GUI caller to parse console text or reproduce importer rules.

Primary-source preflight SHALL evaluate only primary-source structure and data. Network-source preflight SHALL evaluate only network-source structure and data that can be determined without a primary inventory. Inventory-relative network outcomes SHALL remain part of combined preflight or conversion.

#### Scenario: Primary workbook is tested without publication

- **GIVEN** a primary workbook path and an existing canonical output file
- **WHEN** the primary read-only preflight runs
- **THEN** it uses the approved primary workbook parser and validation rules
- **AND** it returns worksheet, header, row-count, and issue metadata
- **AND** the existing output file is unchanged

#### Scenario: Network workbook is tested independently

- **GIVEN** a network workbook with worksheet `Устройства`
- **WHEN** the network read-only preflight runs without a primary workbook
- **THEN** it validates the exact required network headers and row-level MAC, switch-IP, and port evidence
- **AND** it ignores worksheet `Изменения` and column `Корректная запись`
- **AND** it does not invent inventory-relative unmatched or join outcomes
- **AND** it publishes no canonical snapshot

#### Scenario: Source preflight returns a safe fatal result

- **GIVEN** a configured workbook cannot be read or does not satisfy its approved source contract
- **WHEN** source preflight runs
- **THEN** it returns a structured fatal issue and failed operation status
- **AND** it does not raise an uncaught UI-facing workbook exception
- **AND** it does not change any output file

### Requirement: Combined preflight validates current two-source candidate without publication

The importer SHALL expose a UI-independent combined preflight for an explicitly supplied primary workbook and network workbook. Combined preflight SHALL reread both current files, repeat both source validations, apply the approved MAC-only switch reconciliation, build the schema-v3 candidate in memory, compute its deterministic snapshot identity, and validate the candidate through the runtime loader.

Combined preflight SHALL require exactly the two workbook paths. It SHALL NOT require or own an output path. If a caller supplies an already selected output path as optional additional configuration evidence, that path MAY be checked for conflict with either input, but absence of output SHALL NOT block combined preflight.

Combined preflight SHALL NOT publish the candidate. A prior per-source preflight result SHALL NOT substitute for rereading either current source. Combined preflight SHALL report inventory-relative network outcomes under the same severity and ambiguity contracts used by conversion.

#### Scenario: Combined preflight reports a valid schema-v3 candidate without output configuration

- **GIVEN** valid current primary and network workbooks
- **AND** no output path is selected
- **WHEN** combined preflight completes without a fatal issue
- **THEN** it reports candidate schema version 3, record count, snapshot ID, source metadata, network counters, and all non-fatal issues
- **AND** it does not create or replace any JSON file

#### Scenario: Combined preflight observes cross-source ambiguity

- **GIVEN** current source rows produce multiple distinct switch candidates for one canonical MAC
- **WHEN** combined preflight reconciles the workbooks
- **THEN** it reports `AMBIGUOUS_SWITCH_CONNECTION` under the approved contract
- **AND** the affected candidate record has null switch fields
- **AND** no output is published

#### Scenario: Conversion repeats validation after preflight

- **GIVEN** a previous source or combined preflight completed
- **WHEN** conversion is requested later
- **THEN** conversion rereads and revalidates the current workbook bytes
- **AND** the previous preflight result is not treated as publication authority

### Requirement: Converter operations expose one closed additive safe structured report

CLI conversion, direct API conversion, source preflight, and combined preflight SHALL expose reports through shared UI-independent result structures. Existing conversion report keys and the existing public `import_equipment_inventory(...)` call SHALL remain supported. New metadata SHALL be additive.

The exact `operation` values are:

```text
PRIMARY_SOURCE_PREFLIGHT
NETWORK_SOURCE_PREFLIGHT
COMBINED_PREFLIGHT
CONVERSION
```

The exact terminal `status` values are:

```text
SUCCEEDED
SUCCEEDED_WITH_WARNINGS
FAILED
```

`SUCCEEDED` means no issue was emitted. `SUCCEEDED_WITH_WARNINGS` means no fatal issue was emitted and at least one `data_quality` or `consistency` issue was emitted. `FAILED` means at least one fatal issue was emitted or the operation could not safely produce its intended terminal result.

The exact `stage_reached` values are:

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

`stage_reached` records the furthest stage entered. `COMPLETE` is used only for a successful or successful-with-warnings terminal operation. `INTERNAL` is used only when an unexpected internal failure prevents a more specific stage classification.

Every serialized report SHALL contain these additive keys with exact names and types:

```text
operation: non-null operation enum
status: non-null terminal-status enum
stage_reached: non-null stage enum
schema_version: integer or null
source_files: object with exact keys
    primary: resolved absolute string or null
    network: resolved absolute string or null
output_path: resolved absolute string or null
published: boolean
data_quality_issue_count: non-negative integer
consistency_issue_count: non-negative integer
```

The existing conversion report keys SHALL remain present with their existing names and meanings:

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

For preflight reports, existing fields that are not applicable SHALL be present with `null`, except known counts remain non-negative integers. For conversion reports, existing values SHALL retain their current semantics. `output_path` SHALL be null for all preflight operations and non-null for `CONVERSION`. `schema_version` SHALL be null until a candidate schema is known.

`published` SHALL be exactly:

```text
PRIMARY_SOURCE_PREFLIGHT -> false
NETWORK_SOURCE_PREFLIGHT -> false
COMBINED_PREFLIGHT       -> false
successful CONVERSION    -> true
failed CONVERSION        -> false
```

Every serialized issue SHALL contain all existing keys:

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

`details` SHALL be a flat JSON object. Its values SHALL be JSON scalars or arrays of JSON scalars. It SHALL NOT contain nested source rows, workbook fragments, canonical record dumps, credentials, secrets, or unnecessary free-form evidence. All consumers SHALL serialize this same shape and SHALL NOT rename or omit additive issue keys.

GUI presentation values `NOT_TESTED`, `RUNNING`, `PASSED`, `PASSED_WITH_WARNINGS`, `FAILED`, and `STALE` are not report statuses. Only completed operations produce reports. Terminal report statuses map to completed GUI source-test states under the operator-workflow capability.

#### Scenario: Existing CLI report remains compatible

- **GIVEN** a caller consumes the currently approved conversion report keys
- **WHEN** the report contract is extended for the standalone GUI
- **THEN** the existing keys remain present with their existing meaning
- **AND** new operation, status, stage, source-role, issue-detail, and issue-count metadata is additive

#### Scenario: Failed conversion still has a complete report

- **GIVEN** conversion fails before publication
- **WHEN** the result is serialized
- **THEN** `operation` is `CONVERSION`
- **AND** `status` is `FAILED`
- **AND** `published` is false
- **AND** the report identifies the reached stage, known source metadata, and safe issues
- **AND** it does not require an output snapshot to exist

#### Scenario: Report serialization is UI-independent

- **WHEN** a CLI, direct API, or GUI adapter serializes an operation result
- **THEN** the report is produced without importing PyQt5
- **AND** all consumers observe the same enums, fields, issue codes, severity, and source metadata

### Requirement: Guarded publication enforces the confirmed output precondition

The UI-independent publication boundary SHALL support an optional output-publication precondition for callers that require confirmed replacement semantics. The existing direct conversion call without a precondition SHALL remain supported and SHALL retain current atomic-publication behavior.

A publication precondition SHALL record:

```text
resolved normalized output path
whether the output existed when confirmed
for an existing output:
    file size
    last-modified time with the platform's highest available precision
    stable file identity when the platform exposes one without reading unsafe content
```

Immediately before atomic replacement, after candidate validation, the publication boundary SHALL resolve and inspect the output again. It SHALL replace the output only when the current state matches the precondition:

```text
confirmed absent -> output is still absent
confirmed existing -> output is still the confirmed observed file state
```

The precondition SHALL fail if the absent output appears, the existing output disappears, its size or last-modified time changes, available stable identity changes, or the resolved normalized output path differs. Failure SHALL emit fatal issue `OUTPUT_CHANGED_SINCE_CONFIRMATION` with `stage = PUBLICATION` and `source_file_role = OUTPUT`, SHALL set `published = false`, and SHALL leave the current output untouched.

The implementation MAY add one optional keyword-only precondition parameter to `import_equipment_inventory(...)` or expose a separate UI-independent guarded-publication entry point. Existing callers using the current call SHALL continue to work.

#### Scenario: Confirmed absent output appears before publication

- **GIVEN** a guarded conversion confirmed that the output did not exist
- **AND** another process creates the output before replacement
- **WHEN** the publication precondition is checked
- **THEN** conversion reports fatal `OUTPUT_CHANGED_SINCE_CONFIRMATION`
- **AND** the current output is not replaced or removed

#### Scenario: Confirmed existing output changes before publication

- **GIVEN** a guarded conversion recorded an existing output fingerprint
- **AND** the output is modified or replaced before atomic replacement
- **WHEN** the publication precondition is checked
- **THEN** conversion reports fatal `OUTPUT_CHANGED_SINCE_CONFIRMATION`
- **AND** the changed output remains untouched

#### Scenario: Unchanged confirmed output is replaced atomically

- **GIVEN** a guarded conversion recorded an output precondition
- **AND** the output state still matches immediately before publication
- **WHEN** candidate validation succeeds
- **THEN** publication proceeds through the existing atomic replacement boundary

### Requirement: Existing conversion modes and publication semantics remain supported

The standalone GUI support SHALL NOT remove or change the intentional one-source schema-v2 CLI/direct API mode or the explicit two-source schema-v3 mode. The direct conversion API SHALL continue to accept an optional network source under the existing path-priority contract.

Preflight APIs, guarded publication, and report extensions SHALL NOT change canonical fields, schema versions, source authorities, diagnostic-model recognition, MAC-only reconciliation, deterministic snapshot identity, runtime candidate validation, or ordinary atomic publication. The importer/domain layer SHALL NOT import PyQt5.

#### Scenario: One-source CLI conversion remains schema v2

- **GIVEN** the CLI or direct API explicitly performs conversion without a network source
- **WHEN** conversion succeeds
- **THEN** it publishes schema version 2 under the existing contract
- **AND** standalone GUI support does not require PyQt5 in the importer or runtime loader

#### Scenario: Two-source direct conversion remains schema v3

- **GIVEN** the direct API receives explicit valid primary, network, and output paths
- **WHEN** conversion succeeds
- **THEN** it publishes schema version 3 under the existing reconciliation and atomic-publication contracts
- **AND** the same operation result can be rendered by CLI or GUI consumers
