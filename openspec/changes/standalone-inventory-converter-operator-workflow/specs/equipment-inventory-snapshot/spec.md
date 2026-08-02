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

Combined preflight SHALL NOT publish the candidate. A prior per-source preflight result SHALL NOT substitute for rereading either current source. Combined preflight SHALL report inventory-relative network outcomes under the same severity and ambiguity contracts used by conversion.

#### Scenario: Combined preflight reports a valid schema-v3 candidate

- **GIVEN** valid current primary and network workbooks
- **WHEN** combined preflight completes without a fatal issue
- **THEN** it reports candidate schema version 3, record count, snapshot ID, source metadata, network counters, and all non-fatal issues
- **AND** it does not create or replace the selected output JSON

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

### Requirement: Converter operations expose one additive safe structured report

CLI conversion, direct API conversion, source preflight, and combined preflight SHALL expose reports through shared UI-independent result structures. Existing conversion report keys and the public `import_equipment_inventory(...)` signature SHALL remain supported. New metadata SHALL be additive.

A report SHALL identify the operation and final status and SHALL include, where applicable:

```text
published
output_path
stage_reached
source file roles and resolved paths
primary worksheet, header row, and source row count
network worksheet, header row, and source row count
record_count
snapshot_id
existing network reconciliation counters
fatal, data-quality, and consistency issue counts
issues
```

Each issue SHALL retain its existing safe class, code, worksheet, row, record ID, and description representation. The report MAY add:

```text
stage
source_file_role
source_column
related_row
safe structured details
```

Reports SHALL NOT contain complete source rows, workbook content, canonical production inventory dumps, credentials, secrets, or unnecessary free-form recognition evidence.

#### Scenario: Existing CLI report remains compatible

- **GIVEN** a caller consumes the currently approved conversion report keys
- **WHEN** the report contract is extended for the standalone GUI
- **THEN** the existing keys remain present with their existing meaning
- **AND** new operation, stage, source-role, and detail metadata is additive

#### Scenario: Failed conversion still has a complete report

- **GIVEN** conversion fails before publication
- **WHEN** the result is serialized
- **THEN** the report identifies the reached stage, publication state, known source metadata, and safe issues
- **AND** it does not require an output snapshot to exist

#### Scenario: Report serialization is UI-independent

- **WHEN** a CLI, direct API, or GUI adapter serializes an operation result
- **THEN** the report is produced without importing PyQt5
- **AND** all consumers observe the same issue codes, severity, and source metadata

### Requirement: Existing conversion modes and publication semantics remain supported

The standalone GUI support SHALL NOT remove or change the intentional one-source schema-v2 CLI/direct API mode or the explicit two-source schema-v3 mode. The direct conversion API SHALL continue to accept an optional network source under the existing signature and path-priority contract.

Preflight APIs and report extensions SHALL NOT change canonical fields, schema versions, source authorities, diagnostic-model recognition, MAC-only reconciliation, deterministic snapshot identity, runtime candidate validation, or atomic publication. The importer/domain layer SHALL NOT import PyQt5.

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
