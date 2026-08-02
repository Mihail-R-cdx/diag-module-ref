# equipment-inventory-snapshot Specification

## MODIFIED Requirements

### Requirement: Offline equipment inventory conversion boundary

The application SHALL treat organization equipment workbooks and optional approved enrichment workbooks as external import sources rather than normal runtime storage formats. A dedicated offline importer SHALL convert the inspected primary equipment workbook, and when explicitly configured the inspected network-connection workbook, into one canonical equipment-inventory snapshot before the diagnostic application consumes the data.

Normal diagnostic application runtime modules SHALL NOT parse `.xlsx` workbooks and SHALL NOT require a spreadsheet parsing dependency to start, load a canonical inventory snapshot, perform inventory queries, or execute existing device diagnostics. An import-only dependency such as `openpyxl` MAY be used by the offline importer provided that the runtime inventory path does not import or require it.

The confirmed primary organization source mapping and the confirmed network-enrichment source mapping defined by this capability SHALL be implemented explicitly. Source-only fields and consistency evidence SHALL remain inside the importer boundary unless the canonical schema explicitly includes them.

A one-source conversion with no network workbook configured SHALL remain an intentional supported mode and SHALL publish schema version 2 under the existing schema-v2 contract. A conversion with an explicitly configured valid network workbook SHALL publish schema version 3. If a network workbook is explicitly configured but its path/configuration is invalid, the workbook is unreadable, worksheet `Устройства` is missing or ambiguous, or a required network header is missing or ambiguous, the importer SHALL fail before publication and SHALL NOT silently downgrade the requested run to schema version 2.

Row-level network data-quality, duplication, unmatched-MAC, and ambiguity outcomes SHALL remain non-fatal when the primary candidate can still be represented. They SHALL preserve otherwise valid primary records and SHALL NOT downgrade the run to schema v2.

#### Scenario: Runtime loads inventory without Excel support

- **GIVEN** a valid canonical equipment inventory snapshot exists
- **AND** the spreadsheet import dependency is unavailable
- **WHEN** the diagnostic runtime imports and loads the equipment inventory
- **THEN** the inventory loads through the canonical snapshot path
- **AND** no `.xlsx` parser is imported or required

#### Scenario: Existing one-source conversion remains supported

- **GIVEN** the primary equipment workbook is configured
- **AND** no network workbook is configured
- **WHEN** the offline importer completes successfully
- **THEN** it publishes a schema-v2 snapshot under the existing schema-v2 contract
- **AND** it does not add undeclared switch fields to schema-v2 records

#### Scenario: Explicit two-source conversion publishes schema v3

- **GIVEN** both the primary equipment workbook and a valid network workbook are explicitly configured
- **WHEN** the offline importer completes successfully despite any non-fatal row-level network issues
- **THEN** it publishes a schema-v3 canonical snapshot
- **AND** the diagnostic runtime still consumes only the canonical JSON snapshot

#### Scenario: Invalid requested network source does not downgrade

- **GIVEN** a network workbook path is explicitly configured
- **AND** that source has a fatal path, read, worksheet, or required-header failure
- **WHEN** conversion is attempted
- **THEN** the importer reports a structured fatal source failure
- **AND** it does not publish schema v2 as a fallback
- **AND** any previous valid output remains intact

### Requirement: Converter paths use repository-safe absolute configuration

The offline converter SHALL preserve execution-time configuration variables named `SOURCE_XLSX_PATH` and `OUTPUT_JSON_PATH` and SHALL add the exact optional network-source configuration variable `NETWORK_XLSX_PATH`. Every configured value SHALL be a resolved absolute `Path` before workbook reading or snapshot publication begins.

Primary source and output path resolution priority SHALL remain:

```text
explicit command-line override
environment variable
repository-safe default where approved
configuration failure
```

The supported primary/output environment variables SHALL remain `DIAG_INVENTORY_XLSX` and `DIAG_INVENTORY_JSON`. The exact network environment variable SHALL be:

```text
DIAG_INVENTORY_NETWORK_XLSX
```

The exact network CLI option SHALL be:

```text
--network-source
```

The exact optional direct API keyword SHALL be:

```text
network_source_path
```

The direct API contract SHALL be:

```python
import_equipment_inventory(
    source_path,
    *,
    network_source_path=None,
    output_path=None,
    generated_at=None,
)
```

Network source resolution SHALL use this priority:

```text
explicit network_source_path or --network-source
DIAG_INVENTORY_NETWORK_XLSX
explicitly configured NETWORK_XLSX_PATH
no network source configured -> intentional one-source schema-v2 mode
```

Supplying a network source through any approved public surface SHALL request schema-v3 conversion. Failure of that configured source SHALL be fatal for that run and SHALL NOT be interpreted as absence of configuration. No equivalent or implementation-selected public name is permitted.

The JSON output MAY default to the repository-local deployment snapshot path. No user-specific workbook path SHALL be committed as a default. A source-path configuration failure SHALL occur before candidate publication and SHALL leave any previous valid output intact.

#### Scenario: Environment paths are resolved

- **GIVEN** relative or user-expanded path text is supplied through the supported environment variables
- **WHEN** converter configuration is initialized
- **THEN** `SOURCE_XLSX_PATH`, `OUTPUT_JSON_PATH`, and any configured `NETWORK_XLSX_PATH` contain absolute resolved `Path` values

#### Scenario: Source path is not configured

- **GIVEN** no CLI source override, no source environment variable, and no approved repository-safe source default
- **WHEN** the converter starts
- **THEN** it exits with a clear safe configuration error
- **AND** it does not modify the existing JSON snapshot

#### Scenario: Network source is not configured

- **GIVEN** `network_source_path`, `--network-source`, `DIAG_INVENTORY_NETWORK_XLSX`, and `NETWORK_XLSX_PATH` provide no network source
- **WHEN** converter configuration is initialized
- **THEN** the run remains in intentional one-source mode
- **AND** absence of the optional source is not reported as a failure

#### Scenario: Configured network path is unusable

- **GIVEN** a network source path is explicitly or environmentally configured
- **AND** the path does not resolve to a readable regular workbook file
- **WHEN** the converter starts
- **THEN** it returns a structured fatal configuration/source issue
- **AND** it does not publish or replace the output snapshot

#### Scenario: Direct API uses the approved keyword

- **WHEN** a caller supplies `network_source_path` to `import_equipment_inventory`
- **THEN** that exact value requests schema-v3 conversion
- **AND** the caller does not need another implementation-specific adapter or keyword

### Requirement: Existing schema-v1 snapshots remain loadable

The runtime inventory loader SHALL continue to accept valid schema-v1 snapshots and SHALL additionally accept valid schema-v2 and schema-v3 snapshots. It SHALL strictly validate each supported schema version against its own approved exact record fields and identity payload.

Runtime adaptation SHALL be exactly:

```text
schema v1
    -> room_vip = null
    -> switch_ip_address = null
    -> switch_port = null

schema v2
    -> room_vip read from the source record
    -> switch_ip_address = null
    -> switch_port = null

schema v3
    -> room_vip, switch_ip_address, and switch_port read and validated
```

Adaptation SHALL NOT rewrite the source file or bypass or alter source-version snapshot identity verification. The loader SHALL NOT accept undeclared hybrid records. Unknown schema versions SHALL remain `UNSUPPORTED_SCHEMA`; missing, extra, or hybrid fields in a declared supported version SHALL remain `INVALID_SNAPSHOT`.

#### Scenario: Existing deployment snapshot is loaded

- **GIVEN** a valid schema-v1 snapshot created before this change
- **WHEN** the runtime loader loads it
- **THEN** the inventory is available
- **AND** every runtime record exposes unknown VIP state and null switch fields

#### Scenario: Hybrid snapshot is rejected

- **WHEN** a snapshot claims schema version 1 but contains `room_vip` or either switch field, or claims schema version 2 but contains either switch field
- **THEN** loading fails as an invalid snapshot
- **AND** no partial inventory is published

#### Scenario: Existing schema-v2 deployment snapshot is loaded

- **GIVEN** a valid schema-v2 snapshot
- **WHEN** the runtime loader loads it
- **THEN** the inventory is available
- **AND** every runtime record exposes source `room_vip` and null switch fields

#### Scenario: Valid schema-v3 snapshot is loaded

- **GIVEN** a valid schema-v3 snapshot with correct deterministic identity
- **WHEN** the runtime loader loads it
- **THEN** the inventory is available
- **AND** both switch fields are exposed exactly as canonical nullable attributes

#### Scenario: Future schema is rejected

- **WHEN** a snapshot declares an undeclared schema version
- **THEN** loading fails as `UNSUPPORTED_SCHEMA`
- **AND** no partial inventory is published

### Requirement: Structured importer diagnostics and source-row accounting

Every inspected source equipment row SHALL remain accounted for as either a canonical record or a structured issue. Every non-empty inspected row from network worksheet `Устройства` SHALL additionally be accounted for as a usable connection candidate, a structured issue, or both. No non-empty row from either approved source SHALL disappear silently.

Importer diagnostics SHALL continue to distinguish at least these semantic classes:

```text
fatal source-contract issue
non-fatal invalid-field/data-quality issue
cross-row or source-consistency issue
```

The concrete Python exception hierarchy and exact implementation type names are not part of this architecture contract. Each diagnostic SHALL nevertheless expose a machine-readable issue category/code, its semantic class, and only the minimum safe worksheet, row, or record reference needed to investigate the problem.

Normal diagnostics SHALL NOT dump complete source rows, complete canonical records when not needed, complete workbook contents, production snapshots, or unrelated topology.

For the network source, fatal outcomes SHALL be limited to:

```text
network path or configuration failure
network workbook unreadable
worksheet Устройства missing or ambiguous
required network header missing or ambiguous
complete candidate fails runtime schema validation
output publication failure
```

The following network conditions SHALL be non-fatal when the primary candidate remains representable:

```text
missing or invalid network MAC
EMPTY_SWITCH_CONNECTION
invalid or missing switch IP or port
DUPLICATE_SWITCH_CONNECTION_SOURCE
AMBIGUOUS_SWITCH_CONNECTION
AMBIGUOUS_INVENTORY_MAC_FOR_SWITCH
NETWORK_MAC_NOT_IN_INVENTORY
```

A row with a usable partial candidate MAY produce both the candidate and a missing/invalid-field issue. A non-fatal row-level network issue SHALL NOT block schema-v3 publication, delete a primary record, or cause silent fallback to schema v2.

Consistency evidence SHALL NOT grant authority to delete records, rewrite authoritative source mappings, guess missing values, change `record_id`, change `device_kind`, merge rooms, or select a first match.

#### Scenario: Invalid optional field is encountered

- **WHEN** a source row has valid required fields but contains invalid optional IP or MAC data
- **THEN** the affected canonical nullable field is null
- **AND** the importer reports a non-fatal data-quality issue
- **AND** the row remains represented as a canonical record

#### Scenario: Consistency evidence conflicts with authoritative mapping

- **WHEN** importer-side evidence suggests an authoritative mapped value may be inconsistent
- **THEN** the importer preserves the authoritative mapping
- **AND** it may report a consistency issue
- **AND** it does not silently correct the canonical record from secondary evidence

#### Scenario: Empty network connection row is accounted for

- **GIVEN** a non-empty `Устройства` row has a valid canonical MAC
- **AND** both switch IP and port normalize to null without another invalid-field issue describing the row
- **WHEN** network candidates are built
- **THEN** the row creates no connection candidate
- **AND** the importer emits non-fatal `EMPTY_SWITCH_CONNECTION`

#### Scenario: Row-level network ambiguity remains non-fatal

- **GIVEN** one canonical MAC has multiple distinct usable network candidates
- **WHEN** reconciliation runs
- **THEN** the importer emits non-fatal `AMBIGUOUS_SWITCH_CONNECTION`
- **AND** otherwise valid primary records remain publishable with null switch fields

#### Scenario: Fatal network structure blocks publication

- **GIVEN** an explicitly configured network workbook lacks the required worksheet or required header structure
- **WHEN** conversion is attempted
- **THEN** the importer reports a fatal source-structure issue
- **AND** the previous valid output remains intact

## ADDED Requirements

### Requirement: Network connection source contract is exact and closed

When a network workbook is configured, the importer SHALL use only worksheet `Устройства` as current network-connection evidence. The required exact semantic source columns SHALL be:

```text
MAC-адрес       -> cross-source join evidence
IP коммутатора  -> switch_ip_address candidate
Порт            -> switch_port candidate
```

The importer SHALL ignore worksheet `Изменения` completely. Historical rows from that worksheet SHALL NOT add, remove, repair, override, or select current connection evidence.

The importer SHALL ignore column `Корректная запись` completely. That column SHALL NOT be required, SHALL NOT filter rows, SHALL NOT add or suppress issues, SHALL NOT select between candidates, SHALL NOT affect canonical fields, and SHALL NOT affect `snapshot_id`.

All other columns in `Устройства`, including device IP, room text, manufacturer, model, source labels, confidence values, and prefixes, SHALL remain non-authoritative and SHALL NOT participate in the join or break ambiguity.

A configured network workbook missing or ambiguously identifying worksheet `Устройства`, or missing or ambiguously identifying any required semantic column, SHALL produce a structured fatal source-structure issue and SHALL block candidate publication.

#### Scenario: Required network source structure is present

- **WHEN** the configured workbook contains one worksheet `Устройства` and one unambiguous instance of all three required semantic columns
- **THEN** the importer may construct normalized network connection candidates
- **AND** no other workbook column gains canonical authority

#### Scenario: Changes worksheet contains newer-looking data

- **GIVEN** worksheet `Изменения` contains a row for a MAC also present in `Устройства`
- **WHEN** the importer builds current network evidence
- **THEN** it uses only `Устройства`
- **AND** the historical row has no effect on canonical output

#### Scenario: Correct-record marker differs

- **GIVEN** otherwise identical source rows differ only in `Корректная запись`, including `Да`, `Нет`, blank, or another value
- **WHEN** the importer evaluates those rows
- **THEN** the marker has no effect on row eligibility or reconciliation

#### Scenario: Required network column is missing

- **WHEN** `Устройства` lacks `MAC-адрес`, `IP коммутатора`, or `Порт`
- **THEN** the importer reports a structured fatal source-structure issue
- **AND** no candidate snapshot is published

### Requirement: Switch connection enrichment uses unambiguous canonical MAC

The importer SHALL normalize network `MAC-адрес` with the same canonical MAC normalization used for primary canonical `mac_address`. Missing or invalid network MAC SHALL not participate in reconciliation and SHALL produce a structured non-fatal source issue.

`IP коммутатора`, when present, SHALL normalize to canonical dotted-decimal IPv4. Invalid non-blank switch IP SHALL become null plus `INVALID_SWITCH_IP`.

`Порт` SHALL use canonical nullable text normalization: Unicode NFC and leading/trailing trim, with empty normalized text becoming null. Case and internal text SHALL be preserved. The importer SHALL treat the value as opaque and SHALL NOT require a vendor-specific interface grammar.

A network row SHALL create a connection candidate only when at least one normalized connection field is usable. A row with valid canonical MAC and both normalized connection fields null SHALL create no candidate. When both source fields are blank/empty and no other invalid-field issue describes the condition, the importer SHALL emit `EMPTY_SWITCH_CONNECTION`. When invalid non-blank switch IP already emits `INVALID_SWITCH_IP` and port is null, the row SHALL create no candidate and an additional `EMPTY_SWITCH_CONNECTION` is not required.

A no-candidate row SHALL NOT create candidate multiplicity or ambiguity with another usable row for the same canonical MAC, but its structured issue SHALL remain visible.

The importer SHALL preserve multiplicity on both sides of the join. A canonical connection SHALL be assigned only when exactly one primary canonical record and exactly one distinct usable normalized network connection candidate share one canonical MAC.

Reconciliation SHALL follow this table:

```text
primary record has null MAC
    -> switch_ip_address = null
    -> switch_port = null
    -> no join attempted

one primary record, no usable network candidate
    -> both switch fields null
    -> absence alone is not a per-record issue

one primary record, one distinct usable network candidate
    -> copy each normalized candidate field independently

multiple primary records share one MAC
    -> enrich none
    -> AMBIGUOUS_INVENTORY_MAC_FOR_SWITCH

repeated identical usable network candidates
    -> one distinct candidate
    -> DUPLICATE_SWITCH_CONNECTION_SOURCE

multiple distinct usable network candidates
    -> both canonical switch fields null
    -> AMBIGUOUS_SWITCH_CONNECTION

network MAC has no primary record
    -> NETWORK_MAC_NOT_IN_INVENTORY
```

A unique partial candidate SHALL preserve its valid field. A null port with a valid switch IP SHALL produce `MISSING_SWITCH_PORT`; a blank switch IP with a valid port SHALL produce `MISSING_SWITCH_IP`; an invalid non-blank switch IP with a valid port SHALL produce `INVALID_SWITCH_IP` rather than an additional missing-IP issue.

The importer SHALL NOT break ambiguity by first/last row, source order, non-null preference, valid-IP preference, device IP, room evidence, manufacturer, model, source metadata, confidence, prefixes, worksheet `Изменения`, or `Корректная запись`.

#### Scenario: Canonical MAC forms join

- **GIVEN** the primary record and network row contain different supported textual representations of the same 48-bit MAC
- **WHEN** both values normalize to the same canonical MAC
- **AND** multiplicity is one-to-one
- **THEN** the unique normalized switch connection enriches that primary record

#### Scenario: Device IP agrees but MAC does not

- **GIVEN** a network row has the same device IP or room text as a primary record
- **AND** canonical MAC does not match
- **WHEN** reconciliation runs
- **THEN** no connection is assigned from that evidence

#### Scenario: Empty connection row creates no candidate

- **GIVEN** one `Устройства` row has a valid canonical MAC and no usable switch IP or port
- **WHEN** candidates for that MAC are counted
- **THEN** that row contributes no candidate
- **AND** its row-level issue remains observable

#### Scenario: Empty row does not create ambiguity

- **GIVEN** one row for a canonical MAC has no usable connection fields
- **AND** another row for that MAC provides one usable connection candidate
- **WHEN** reconciliation runs
- **THEN** the usable row remains the only candidate
- **AND** the empty row does not create `AMBIGUOUS_SWITCH_CONNECTION`

#### Scenario: Duplicate identical network rows

- **GIVEN** multiple `Устройства` rows for one canonical MAC normalize to the same usable switch IP and port pair
- **WHEN** reconciliation runs
- **THEN** the pair is treated as one distinct candidate
- **AND** the importer emits `DUPLICATE_SWITCH_CONNECTION_SOURCE`

#### Scenario: Conflicting network rows remain ambiguous

- **GIVEN** multiple `Устройства` rows for one canonical MAC normalize to different usable switch IP and/or port pairs
- **WHEN** reconciliation runs
- **THEN** both canonical switch fields are null
- **AND** the importer emits `AMBIGUOUS_SWITCH_CONNECTION`
- **AND** no row is selected by order or ignored metadata

#### Scenario: Primary MAC is duplicated

- **GIVEN** multiple primary canonical records share one non-null canonical MAC
- **WHEN** network reconciliation runs
- **THEN** none of those records receives switch enrichment
- **AND** the importer emits `AMBIGUOUS_INVENTORY_MAC_FOR_SWITCH`

#### Scenario: Unique partial connection is retained

- **GIVEN** exactly one primary record and one distinct usable network candidate share a canonical MAC
- **AND** exactly one of switch IP or port is usable
- **WHEN** reconciliation runs
- **THEN** the usable field is retained
- **AND** the unavailable field is null
- **AND** the applicable structured issue is emitted

### Requirement: Canonical inventory snapshot schema v3

A network-enriched snapshot SHALL use `schema_version` equal to JSON integer `3`.

The schema-v3 root fields and optional generation metadata SHALL remain the same approved root vocabulary used by schema v2. Schema-v3 records SHALL contain all schema-v2 fields plus exactly:

```text
switch_ip_address
switch_port
```

The complete exact schema-v3 record field set SHALL be:

```text
record_id
source_model
diagnostic_model
ip_address
mac_address
serial_number
room_id
room_name
device_kind
room_vip
switch_ip_address
switch_port
```

`switch_ip_address` SHALL be canonical dotted-decimal IPv4 text or null. `switch_port` SHALL be normalized non-empty JSON text or null.

The deterministic schema-v3 identity payload SHALL contain only:

```text
schema_version
records
```

Records SHALL remain sorted by normalized `record_id` for identity construction. Both switch fields SHALL participate in schema-v3 identity. Generation metadata and structured import-report metadata/counters SHALL remain outside identity.

For schema v3, canonical root metadata `source_row_count` SHALL retain its existing meaning and SHALL count inspected rows from the primary equipment workbook only. It SHALL NOT be the sum of both workbooks. Network worksheet row counts SHALL exist only in `ImportResult` or report metadata and SHALL NOT affect canonical identity.

Schema-v3 publication SHALL remain atomic and SHALL validate the complete candidate through the runtime loader before replacing the prior output.

#### Scenario: Unique connection is published

- **WHEN** a primary record has one unambiguous normalized network connection
- **THEN** its schema-v3 record contains the normalized switch IP and port values
- **AND** those values participate in deterministic snapshot identity

#### Scenario: Connection is unavailable

- **WHEN** no unambiguous network connection is available for a primary record
- **THEN** both schema-v3 switch fields are null unless one unique partial field is valid
- **AND** the primary record remains present when otherwise valid

#### Scenario: Switch field changes identity

- **GIVEN** two otherwise identical schema-v3 canonical snapshots
- **WHEN** one record's `switch_ip_address` or `switch_port` differs
- **THEN** their deterministic `snapshot_id` values differ

#### Scenario: Primary source row count remains canonical metadata

- **GIVEN** two successful schema-v3 conversions inspect the same primary equipment rows but different numbers of network rows
- **WHEN** canonical root metadata is produced
- **THEN** `source_row_count` equals the primary equipment-workbook row count in both outputs
- **AND** the network row count remains report metadata only

#### Scenario: Hybrid schema-v2 record is rejected

- **WHEN** a snapshot claims schema version 2 but contains either schema-v3 switch field
- **THEN** loading fails as an invalid snapshot
- **AND** no partial inventory is published

### Requirement: Schema-v3 switch fields are passive runtime data in this change

The runtime `EquipmentRecord` SHALL expose nullable `switch_ip_address` and `switch_port` for schema-v3 records and null-adapted values for older records.

Existing inventory indexes SHALL remain equivalent to:

```text
ip_address -> tuple[EquipmentRecord, ...]
room_id -> tuple[EquipmentRecord, ...]
(room_id, device_kind) -> tuple[EquipmentRecord, ...]
```

This change SHALL NOT add an index or public query by switch IP or switch port. Diagnostic dispatch, credential configuration, room-context aggregation, PDU-room-codec enrichment, related-codec status, handlers, controllers, workers, transports, and device I/O SHALL ignore both switch fields.

The importer MAY extend its structured result with safe network worksheet/header context and aggregate counts needed to validate two-source conversion. Those report fields SHALL NOT enter canonical records, canonical `source_row_count`, or `snapshot_id`.

#### Scenario: Existing IP and room queries are unchanged

- **WHEN** a schema-v3 inventory is loaded
- **THEN** `find_by_ip`, `find_room_equipment`, and `find_by_room_and_kind` preserve their existing zero/one/many semantics
- **AND** switch fields do not alter membership or ordering

#### Scenario: Diagnostics run with schema v3

- **GIVEN** the application loads a valid schema-v3 snapshot
- **WHEN** existing diagnostic dispatch, credential, room, or PDU enrichment workflows execute
- **THEN** their authority and lifecycle remain unchanged
- **AND** they do not inspect switch IP or port

#### Scenario: Report metadata is not canonical identity

- **WHEN** safe network-run counters or source-location context differ while canonical schema-v3 records remain identical
- **THEN** deterministic `snapshot_id` remains identical
