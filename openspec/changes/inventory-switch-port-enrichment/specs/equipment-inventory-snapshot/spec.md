# equipment-inventory-snapshot Specification

## MODIFIED Requirements

### Requirement: Offline equipment inventory conversion boundary

The application SHALL treat organization equipment workbooks and optional approved enrichment workbooks as external import sources rather than normal runtime storage formats. A dedicated offline importer SHALL convert the inspected primary equipment workbook, and when explicitly configured the inspected network-connection workbook, into one canonical equipment-inventory snapshot before the diagnostic application consumes the data.

Normal diagnostic application runtime modules SHALL NOT parse `.xlsx` workbooks and SHALL NOT require a spreadsheet parsing dependency to start, load a canonical inventory snapshot, perform inventory queries, or execute existing device diagnostics. An import-only dependency such as `openpyxl` MAY be used by the offline importer provided that the runtime inventory path does not import or require it.

The confirmed primary organization source mapping and the confirmed network-enrichment source mapping defined by this capability SHALL be implemented explicitly. Source-only fields and consistency evidence SHALL remain inside the importer boundary unless the canonical schema explicitly includes them.

A one-source conversion with no network workbook configured SHALL remain an intentional supported mode and SHALL publish schema version 2 under the existing schema-v2 contract. A conversion with an explicitly configured valid network workbook SHALL publish schema version 3. If a network workbook is explicitly configured but cannot be read or does not satisfy its required source structure, the importer SHALL fail before publication and SHALL NOT silently downgrade the requested run to schema version 2.

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
- **WHEN** the offline importer completes successfully
- **THEN** it publishes a schema-v3 canonical snapshot
- **AND** the diagnostic runtime still consumes only the canonical JSON snapshot

#### Scenario: Invalid requested network source does not downgrade

- **GIVEN** a network workbook path is explicitly configured
- **AND** that source is missing, unreadable, or structurally invalid
- **WHEN** conversion is attempted
- **THEN** the importer reports a structured fatal source failure
- **AND** it does not publish schema v2 as a fallback
- **AND** any previous valid output remains intact

### Requirement: Converter paths use repository-safe absolute configuration

The offline converter SHALL expose execution-time configuration variables named `SOURCE_XLSX_PATH` and `OUTPUT_JSON_PATH`. It SHALL additionally expose a network-source configuration value equivalent to `NETWORK_XLSX_PATH`. Each configured value SHALL be a resolved absolute `Path` before workbook reading or snapshot publication begins.

Primary source and output path resolution priority SHALL remain:

```text
explicit command-line override
environment variable
repository-safe default where approved
configuration failure
```

The supported primary/output environment variables SHALL remain `DIAG_INVENTORY_XLSX` and `DIAG_INVENTORY_JSON`. The JSON output MAY default to the repository-local deployment snapshot path. No user-specific source workbook path SHALL be committed as a default.

Network source resolution SHALL use this semantic priority:

```text
explicit API or command-line network source
environment or approved configured network source
no network source configured -> intentional one-source schema-v2 mode
```

The supported network environment variable SHALL be `DIAG_INVENTORY_NETWORK_XLSX`, or an exactly equivalent reviewed implementation name documented by the runbook before implementation approval. Supplying a network source SHALL request schema-v3 conversion; failure of that configured source SHALL be fatal for that run and SHALL NOT be interpreted as absence of configuration.

The direct import API SHALL continue to accept explicit primary source and output paths for tests and automation and SHALL accept an explicit optional network source path. A source-path configuration failure SHALL occur before candidate publication and SHALL leave any previous valid output intact.

#### Scenario: Environment paths are resolved

- **GIVEN** relative or user-expanded path text is supplied through supported environment variables
- **WHEN** converter configuration is initialized
- **THEN** every configured source/output path contains an absolute resolved `Path` value

#### Scenario: Primary source path is not configured

- **GIVEN** no CLI primary source override, no primary source environment variable, and no approved repository-safe primary source default
- **WHEN** the converter starts
- **THEN** it exits with a clear safe configuration error
- **AND** it does not modify the existing JSON snapshot

#### Scenario: Network source is not configured

- **GIVEN** no explicit or configured network source exists
- **WHEN** converter configuration is initialized
- **THEN** the run remains in intentional one-source mode
- **AND** absence of the optional source is not reported as a failure

#### Scenario: Configured network path is unusable

- **GIVEN** a network source path is explicitly or environmentally configured
- **AND** the path does not resolve to a readable regular workbook file
- **WHEN** the converter starts
- **THEN** it returns a structured fatal configuration/source issue
- **AND** it does not publish or replace the output snapshot

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

A configured network workbook missing worksheet `Устройства` or any required semantic column SHALL produce a structured fatal source-structure issue and SHALL block candidate publication.

#### Scenario: Required network source structure is present

- **WHEN** the configured workbook contains worksheet `Устройства` and all three required semantic columns
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

`IP коммутатора`, when present, SHALL normalize to canonical dotted-decimal IPv4. Invalid non-blank switch IP SHALL become null plus `INVALID_SWITCH_IP` when the network row can otherwise contribute safe enrichment evidence.

`Порт` SHALL use canonical nullable text normalization: Unicode NFC and leading/trailing trim, with empty normalized text becoming null. Case and internal text SHALL be preserved. The importer SHALL treat the value as opaque and SHALL NOT require a vendor-specific interface grammar.

The importer SHALL preserve multiplicity on both sides of the join. A canonical connection SHALL be assigned only when exactly one primary canonical record and exactly one distinct normalized network connection candidate share one canonical MAC.

Reconciliation SHALL follow this table:

```text
primary record has null MAC
    -> switch_ip_address = null
    -> switch_port = null
    -> no join attempted

one primary record, no network candidate
    -> both switch fields null
    -> absence alone is not a per-record issue

one primary record, one distinct network candidate
    -> copy each normalized candidate field independently

multiple primary records share one MAC
    -> enrich none
    -> AMBIGUOUS_INVENTORY_MAC_FOR_SWITCH

repeated identical normalized network candidates
    -> one distinct candidate
    -> DUPLICATE_SWITCH_CONNECTION_SOURCE

multiple distinct normalized network candidates
    -> both canonical switch fields null
    -> AMBIGUOUS_SWITCH_CONNECTION

network MAC has no primary record
    -> NETWORK_MAC_NOT_IN_INVENTORY
```

A unique partial candidate SHALL preserve its valid field. A null port with a valid switch IP SHALL produce `MISSING_SWITCH_PORT`; a null switch IP with a valid port SHALL produce `MISSING_SWITCH_IP` unless `INVALID_SWITCH_IP` already describes invalid non-blank source input.

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

#### Scenario: Duplicate identical network rows

- **GIVEN** multiple `Устройства` rows for one canonical MAC normalize to the same switch IP and port pair
- **WHEN** reconciliation runs
- **THEN** the pair is treated as one distinct candidate
- **AND** the importer emits `DUPLICATE_SWITCH_CONNECTION_SOURCE`

#### Scenario: Conflicting network rows remain ambiguous

- **GIVEN** multiple `Устройства` rows for one canonical MAC normalize to different switch IP and/or port pairs
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

- **GIVEN** exactly one primary record and one distinct network candidate share a canonical MAC
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

#### Scenario: Hybrid schema-v2 record is rejected

- **WHEN** a snapshot claims schema version 2 but contains either schema-v3 switch field
- **THEN** loading fails as an invalid snapshot
- **AND** no partial inventory is published

### Requirement: Existing schema-v1 and schema-v2 snapshots remain loadable after schema v3

The runtime loader SHALL accept valid snapshots with schema versions 1, 2, and 3 and SHALL strictly validate each version against its own exact record fields and identity payload.

Runtime adaptation SHALL be:

```text
schema v1
    -> room_vip = null
    -> switch_ip_address = null
    -> switch_port = null

schema v2
    -> room_vip read from source record
    -> switch_ip_address = null
    -> switch_port = null

schema v3
    -> room_vip, switch_ip_address, and switch_port read and validated
```

Adaptation SHALL NOT rewrite the source file or alter source-version identity verification. Unknown schema versions SHALL remain `UNSUPPORTED_SCHEMA`. Missing, extra, or hybrid fields within a declared supported version SHALL remain `INVALID_SNAPSHOT`.

#### Scenario: Existing schema-v1 deployment snapshot is loaded

- **GIVEN** a valid schema-v1 snapshot
- **WHEN** the runtime loader loads it
- **THEN** the inventory is available
- **AND** runtime records expose null VIP and null switch fields

#### Scenario: Existing schema-v2 deployment snapshot is loaded

- **GIVEN** a valid schema-v2 snapshot
- **WHEN** the runtime loader loads it
- **THEN** the inventory is available
- **AND** runtime records expose source `room_vip` and null switch fields

#### Scenario: Valid schema-v3 snapshot is loaded

- **GIVEN** a valid schema-v3 snapshot with correct deterministic identity
- **WHEN** the runtime loader loads it
- **THEN** the inventory is available
- **AND** both switch fields are exposed exactly as canonical nullable attributes

#### Scenario: Future schema is rejected

- **WHEN** a snapshot declares an undeclared schema version
- **THEN** loading fails as `UNSUPPORTED_SCHEMA`
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

The importer MAY extend its structured result with safe network worksheet/header context and aggregate counts needed to validate two-source conversion. Those report fields SHALL NOT enter canonical records or `snapshot_id`.

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
