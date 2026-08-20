## MODIFIED Requirements

### Requirement: Offline equipment inventory conversion boundary

The application SHALL treat organization equipment workbooks and optional approved enrichment workbooks as external import sources rather than normal runtime storage formats. A dedicated offline importer SHALL convert the inspected primary equipment workbook, and when explicitly configured the inspected network-connection workbook, into one canonical equipment-inventory snapshot before the diagnostic application consumes the data.

Normal diagnostic application runtime modules SHALL NOT parse `.xlsx` workbooks and SHALL NOT require a spreadsheet parsing dependency to start, load a canonical inventory snapshot, perform inventory queries, or execute existing device diagnostics. An import-only dependency such as `openpyxl` MAY be used by the offline importer provided that the runtime inventory path does not import or require it.

The confirmed primary organization source mapping and the confirmed network-enrichment source mapping defined by this capability SHALL be implemented explicitly. Source-only fields and consistency evidence SHALL remain inside the importer boundary unless the canonical schema explicitly includes them.

Every newly successful conversion SHALL publish schema version 4. A one-source conversion with no network workbook configured SHALL publish schema v4 with `switch_ip_address = null` and `switch_port = null` on every record. A conversion with an explicitly configured valid network workbook SHALL also publish schema v4 and SHALL populate switch fields only through the existing approved reconciliation contract.

If a network workbook is explicitly configured but its path/configuration is invalid, the workbook is unreadable, worksheet `Устройства` is missing or ambiguous, or a required network header is missing or ambiguous, the importer SHALL fail before publication and SHALL NOT silently reinterpret the run as primary-only conversion.

Row-level network data-quality, duplication, unmatched-MAC, and ambiguity outcomes SHALL remain non-fatal when the primary candidate can still be represented. They SHALL preserve otherwise valid primary records and SHALL NOT change the requested import mode.

#### Scenario: Runtime loads inventory without Excel support

- **GIVEN** a valid canonical equipment inventory snapshot exists
- **AND** the spreadsheet import dependency is unavailable
- **WHEN** the diagnostic runtime imports and loads the equipment inventory
- **THEN** the inventory loads through the canonical snapshot path
- **AND** no `.xlsx` parser is imported or required

#### Scenario: Primary-only conversion publishes schema v4

- **GIVEN** the primary equipment workbook is configured
- **AND** no network workbook is configured
- **WHEN** the offline importer completes successfully
- **THEN** it publishes a schema-v4 snapshot
- **AND** every record contains null `switch_ip_address` and null `switch_port`

#### Scenario: Explicit two-source conversion publishes schema v4

- **GIVEN** both the primary equipment workbook and a valid network workbook are explicitly configured
- **WHEN** the offline importer completes successfully despite any non-fatal row-level network issues
- **THEN** it publishes a schema-v4 canonical snapshot
- **AND** the diagnostic runtime still consumes only the canonical JSON snapshot

#### Scenario: Invalid requested network source does not downgrade

- **GIVEN** a network workbook path is explicitly configured
- **AND** that source has a fatal path, read, worksheet, or required-header failure
- **WHEN** conversion is attempted
- **THEN** the importer reports a structured fatal source failure
- **AND** it does not publish a primary-only candidate as fallback
- **AND** any previous valid output remains intact

### Requirement: ID комнаты is authoritative room identity

For the confirmed organization workbook, `ID комнаты` SHALL map to canonical `room_id` and SHALL remain the only authoritative room identity. `Название комнаты` SHALL map to canonical `room_name` as per-record display metadata. Schema v4 additionally carries `room_address` and the existing `room_vip` as per-record display metadata; none of those display fields SHALL identify or merge rooms.

The importer SHALL NOT automatically substitute `room_name`, `room_address`, or `room_vip` for missing `room_id` and SHALL NOT merge rooms because display metadata matches. Records sharing one non-null `room_id` SHALL remain members of that authoritative room even when their non-null display metadata differs.

For current schema-v4 import, the importer SHALL preserve normalized per-record room display metadata without cross-record reconciliation. Different `room_name`, `room_address`, or `room_vip` values under the same `room_id` SHALL NOT by themselves produce a room-display conflict issue, SHALL NOT cause record deletion, and SHALL NOT cause the importer to select or rewrite a room-wide display value.

Missing or blank `ID комнаты` SHALL produce `room_id = null` and MAY produce an observable data-quality issue. It SHALL NOT by itself make an otherwise representable canonical record fatal.

#### Scenario: Devices share one authoritative room ID

- **WHEN** multiple records have the same canonical `ID комнаты`
- **THEN** they have the same canonical `room_id`
- **AND** the room index returns all of them under that one `room_id`

#### Scenario: Same room ID has different display metadata

- **WHEN** records with the same canonical `room_id` contain different non-null `room_name`, `room_address`, or `room_vip` values
- **THEN** all canonical records and their normalized per-record values are preserved
- **AND** the importer does not report a room-display conflict solely for that difference
- **AND** the importer does not select or rewrite one value as room-wide authority

#### Scenario: One room name is reused by different room IDs

- **WHEN** the same canonical `room_name` appears under different non-null `room_id` values
- **THEN** the importer preserves the distinct authoritative room IDs
- **AND** it does not merge the rooms by display name

#### Scenario: Room name exists without room ID

- **WHEN** `Название комнаты` is present but `ID комнаты` is absent
- **THEN** canonical `room_name` is retained
- **AND** canonical `room_id` is null
- **AND** the importer does not invent room identity from the display name

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

For the primary source, missing or ambiguous discovery of the required `Адрес комнаты` header SHALL be a fatal source-structure issue. A blank individual address cell SHALL NOT be fatal and SHALL normalize to `room_address = null`.

For the network source, fatal outcomes SHALL remain limited to configured path/read/configuration failure, missing or ambiguous `Устройства`, missing or ambiguous required headers, complete candidate validation failure, and output publication failure.

Existing row-level invalid-field, diagnostic-model recognition, physical-identifier multiplicity, controller-evidence, and network reconciliation diagnostics SHALL keep their approved severity unless explicitly modified by this change.

Different non-null `room_name`, `room_address`, or `room_vip` values on records sharing one authoritative `room_id` SHALL NOT be reported as importer room-display conflicts. In particular, schema-v4 publication SHALL NOT emit `ROOM_NAME_CONFLICT`, `ROOM_VIP_CONFLICT`, or a new `ROOM_ADDRESS_CONFLICT` solely from those differences. Row-level unsupported non-blank `VIP оборудование` values SHALL still produce the existing `INVALID_ROOM_VIP` data-quality issue.

Consistency evidence SHALL NOT grant authority to delete records, rewrite authoritative source mappings, guess missing values, change `record_id`, change `device_kind`, merge rooms, or select a first match.

#### Scenario: Invalid optional field is encountered

- **WHEN** a source row has valid required fields but contains invalid optional IP or MAC data
- **THEN** the affected canonical nullable field is null
- **AND** the importer reports a non-fatal data-quality issue
- **AND** the row remains represented as a canonical record

#### Scenario: Room display metadata differs

- **GIVEN** otherwise valid records share one canonical `room_id`
- **AND** one or more of `room_name`, `room_address`, or `room_vip` differs between those records
- **WHEN** importer consistency diagnostics are produced
- **THEN** the records remain publishable with their own normalized values
- **AND** no room-display conflict issue is emitted solely for that difference

#### Scenario: Required room-address header is missing

- **WHEN** the primary source does not expose one unambiguous exact `Адрес комнаты` column
- **THEN** the importer reports a fatal source-structure issue
- **AND** no candidate snapshot replaces the previous valid output

### Requirement: Structured runtime inventory load failure contract

The runtime inventory loader SHALL expose safe structured load failures through a machine-readable category and a non-secret human-readable message. Every failed load SHALL classify as exactly one of:

```text
NOT_FOUND
UNREADABLE
INVALID_FORMAT
UNSUPPORTED_SCHEMA
INVALID_SNAPSHOT
```

The categories SHALL mean:

- `NOT_FOUND`: configured snapshot path does not exist;
- `UNREADABLE`: the snapshot exists but cannot be read because of filesystem/access failure;
- `INVALID_FORMAT`: readable content is not valid UTF-8 JSON;
- `UNSUPPORTED_SCHEMA`: the JSON root declares a schema version outside the explicitly supported integer versions 1, 2, 3, and 4;
- `INVALID_SNAPSHOT`: canonical shape/content is invalid for its declared supported version, required fields are invalid, record IDs collide, or declared `snapshot_id` does not match recomputed canonical content.

No failed load SHALL publish a partial `EquipmentInventory`, partial records, or partial indexes. Runtime consumers SHALL NOT need to inspect raw storage-specific exception types or strings to understand inventory availability.

#### Scenario: Snapshot schema version is unsupported

- **WHEN** the runtime loader receives a JSON object whose `schema_version` is not integer 1, 2, 3, or 4
- **THEN** loading fails with category `UNSUPPORTED_SCHEMA`
- **AND** no inventory is published

#### Scenario: Declared supported schema has invalid shape

- **WHEN** a snapshot declares schema version 1, 2, 3, or 4 but contains missing, extra, or otherwise invalid record fields for that exact version
- **THEN** loading fails with category `INVALID_SNAPSHOT`
- **AND** the loader does not repair or partially publish the candidate

### Requirement: Schema v2 carries explicit room VIP state

Historical schema-v2 snapshots contain all schema-v1 record fields plus exactly:

```text
room_vip
```

`room_vip` SHALL be a JSON boolean or JSON null under the approved schema-v2 source mapping. The deterministic schema-v2 snapshot identity includes `room_vip` for every record. Generation metadata remains outside snapshot identity.

The current importer SHALL no longer publish new schema-v2 snapshots; new successful conversions publish schema v4. Valid historical schema-v2 snapshots SHALL remain loadable under their exact original shape and identity contract.

#### Scenario: Historical schema-v2 snapshot remains valid

- **GIVEN** a valid schema-v2 snapshot whose `room_vip` values satisfy the approved mapping
- **WHEN** the runtime loader loads it
- **THEN** it validates schema-v2 identity and record shape before runtime adaptation
- **AND** the snapshot remains usable

#### Scenario: Current conversion does not emit schema v2

- **WHEN** the current offline importer successfully converts a primary workbook without a network source
- **THEN** the candidate schema version is 4
- **AND** no new schema-v2 snapshot is published

### Requirement: Existing schema-v1 snapshots remain loadable

The runtime inventory loader SHALL continue to accept valid schema-v1, schema-v2, and schema-v3 snapshots and SHALL additionally accept valid schema-v4 snapshots. It SHALL strictly validate each supported schema version against its own approved exact record fields and identity payload before runtime adaptation.

Runtime adaptation SHALL be exactly:

```text
schema v1
    -> room_vip = null
    -> room_address = null
    -> switch_ip_address = null
    -> switch_port = null

schema v2
    -> room_vip read from the source record
    -> room_address = null
    -> switch_ip_address = null
    -> switch_port = null

schema v3
    -> room_vip read from the source record
    -> room_address = null
    -> switch_ip_address and switch_port read and validated

schema v4
    -> room_vip, room_address, switch_ip_address, and switch_port read and validated
```

Adaptation SHALL NOT rewrite the source file or bypass or alter source-version snapshot identity verification. The loader SHALL NOT accept undeclared hybrid records. Unknown schema versions SHALL remain `UNSUPPORTED_SCHEMA`; missing, extra, or hybrid fields in a declared supported version SHALL remain `INVALID_SNAPSHOT`.

#### Scenario: Existing schema-v1 deployment snapshot is loaded

- **GIVEN** a valid schema-v1 snapshot
- **WHEN** the runtime loader loads it
- **THEN** the inventory is available
- **AND** every runtime record exposes null VIP, room-address, and switch fields

#### Scenario: Existing schema-v2 deployment snapshot is loaded

- **GIVEN** a valid schema-v2 snapshot
- **WHEN** the runtime loader loads it
- **THEN** the inventory is available
- **AND** every runtime record exposes source `room_vip`, null `room_address`, and null switch fields

#### Scenario: Existing schema-v3 deployment snapshot is loaded

- **GIVEN** a valid schema-v3 snapshot with correct deterministic identity
- **WHEN** the runtime loader loads it
- **THEN** the inventory is available
- **AND** `room_address` is null
- **AND** both switch fields are exposed exactly as historical canonical nullable attributes

#### Scenario: Valid schema-v4 snapshot is loaded

- **GIVEN** a valid schema-v4 snapshot with correct deterministic identity
- **WHEN** the runtime loader loads it
- **THEN** the inventory is available
- **AND** runtime records expose canonical `room_vip`, `room_address`, `switch_ip_address`, and `switch_port`

#### Scenario: Hybrid snapshot is rejected

- **WHEN** a snapshot contains fields not declared by its supported schema version or omits a field required as a key by that version
- **THEN** loading fails as `INVALID_SNAPSHOT`
- **AND** no partial inventory is published

#### Scenario: Future schema is rejected

- **WHEN** a snapshot declares an undeclared schema version
- **THEN** loading fails as `UNSUPPORTED_SCHEMA`
- **AND** no partial inventory is published

### Requirement: Room VIP evidence uses normative room-wide aggregation

Canonical `room_vip` remains per-record source metadata. The schema-v4 importer SHALL preserve each normalized record value and SHALL NOT perform cross-record VIP reconciliation or emit `ROOM_VIP_CONFLICT` merely because both true and false occur under the same authoritative `room_id`.

The existing runtime room-context layer used before the separate room-tree orchestration change SHALL continue to evaluate already loaded room VIP evidence across records when that legacy presentation path requests a room-wide VIP label. Null means absence of evidence for that record. The existing runtime aggregation table remains:

```text
no room records                          -> unresolved room
all room_vip values null                 -> NO_DATA
one or more true, all others null/true   -> VIP_TRUE
one or more false, all others null/false -> VIP_FALSE
at least one true and at least one false -> CONFLICT
```

This runtime-only aggregation SHALL NOT grant authority back to the importer, SHALL NOT rewrite canonical records, and SHALL NOT affect snapshot publication. Selection semantics for the future room-tree UI belong to a separate reviewed OpenSpec change.

#### Scenario: Importer sees mixed known VIP values

- **WHEN** schema-v4 source records sharing one authoritative `room_id` contain at least one true and at least one false `room_vip`
- **THEN** every otherwise valid record preserves its own canonical value
- **AND** the importer emits no `ROOM_VIP_CONFLICT` solely for that mixture

#### Scenario: Legacy runtime presentation sees mixed VIP values

- **GIVEN** loaded canonical records contain both true and false `room_vip` under one non-null `room_id`
- **WHEN** the existing pre-room-tree runtime room-context presentation requests its legacy room-wide label
- **THEN** that legacy path may report the existing runtime `CONFLICT` presentation
- **AND** canonical inventory remains unchanged

### Requirement: Converter paths use repository-safe absolute configuration

The offline converter SHALL preserve execution-time configuration variables named `SOURCE_XLSX_PATH` and `OUTPUT_JSON_PATH` and the exact optional network-source configuration variable `NETWORK_XLSX_PATH`. Every configured value SHALL be a resolved absolute `Path` before workbook reading or snapshot publication begins.

Primary source and output path resolution priority SHALL remain:

```text
explicit command-line override
environment variable
repository-safe default where approved
configuration failure
```

The supported primary/output environment variables SHALL remain `DIAG_INVENTORY_XLSX` and `DIAG_INVENTORY_JSON`. The exact network environment variable SHALL remain `DIAG_INVENTORY_NETWORK_XLSX`; the exact network CLI option SHALL remain `--network-source`; and the exact optional direct API keyword SHALL remain `network_source_path`.

The direct API contract SHALL remain:

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
no network source configured -> intentional primary-only mode
```

Supplying a network source through any approved public surface SHALL request network-enriched schema-v4 conversion. Absence of a network source SHALL request primary-only schema-v4 conversion. Failure of an explicitly configured network source SHALL be fatal for that run and SHALL NOT be interpreted as absence of configuration.

The JSON output MAY default to the repository-local deployment snapshot path. No user-specific workbook path SHALL be committed as a default. A source-path configuration failure SHALL occur before candidate publication and SHALL leave any previous valid output intact.

#### Scenario: Network source is not configured

- **GIVEN** `network_source_path`, `--network-source`, `DIAG_INVENTORY_NETWORK_XLSX`, and `NETWORK_XLSX_PATH` provide no network source
- **WHEN** converter configuration is initialized
- **THEN** the run remains in intentional primary-only mode
- **AND** successful conversion still targets schema version 4

#### Scenario: Direct API uses the approved keyword

- **WHEN** a caller supplies `network_source_path` to `import_equipment_inventory`
- **THEN** that exact value requests network-enriched schema-v4 conversion
- **AND** the caller does not need another implementation-specific adapter or keyword

### Requirement: Canonical inventory snapshot schema v3

Historical network-enriched schema-v3 snapshots use `schema_version` equal to JSON integer `3` and contain all schema-v2 fields plus exactly:

```text
switch_ip_address
switch_port
```

The complete exact schema-v3 record field set remains:

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

`switch_ip_address` remains canonical dotted-decimal IPv4 text or null. `switch_port` remains normalized non-empty JSON text or null. The deterministic schema-v3 identity payload contains only `schema_version` and canonical `records`; both switch fields participate in that historical identity and generation/report metadata remains outside it.

The runtime loader SHALL continue to validate and load valid historical schema-v3 snapshots under that exact contract. The current importer and combined preflight SHALL no longer generate new schema-v3 candidates; they target schema v4.

#### Scenario: Historical schema-v3 snapshot remains loadable

- **GIVEN** a valid schema-v3 snapshot with one unambiguous historical switch connection
- **WHEN** the runtime loader validates it
- **THEN** the switch fields participate in schema-v3 deterministic identity
- **AND** the runtime exposes those switch fields with `room_address = null`

#### Scenario: Current network-enriched conversion does not emit schema v3

- **GIVEN** a valid configured network source
- **WHEN** current conversion succeeds
- **THEN** the candidate schema version is 4
- **AND** no new schema-v3 snapshot is published

### Requirement: Combined preflight validates current two-source candidate without publication

The importer SHALL expose a UI-independent combined preflight for an explicitly supplied primary workbook and network workbook. Combined preflight SHALL reread both current files, repeat both source validations, apply the approved MAC-only switch reconciliation, build the schema-v4 candidate in memory, compute its deterministic snapshot identity, and validate the candidate through the runtime loader.

Combined preflight SHALL require exactly the two workbook paths. It SHALL NOT require or own an output path. If a caller supplies an already selected output path as optional additional configuration evidence, that path MAY be checked for conflict with either input, but absence of output SHALL NOT block combined preflight.

Combined preflight SHALL NOT publish the candidate. A prior per-source preflight result SHALL NOT substitute for rereading either current source. Combined preflight SHALL report inventory-relative network outcomes under the same severity and ambiguity contracts used by conversion.

#### Scenario: Combined preflight reports a valid schema-v4 candidate without output configuration

- **GIVEN** valid current primary and network workbooks
- **AND** no output path is selected
- **WHEN** combined preflight completes without a fatal issue
- **THEN** it reports candidate schema version 4, record count, snapshot ID, source metadata, network counters, and all non-fatal issues
- **AND** it does not create or replace any JSON file

#### Scenario: Combined preflight observes cross-source ambiguity

- **GIVEN** current source rows produce multiple distinct switch candidates for one canonical MAC
- **WHEN** combined preflight reconciles the workbooks
- **THEN** it reports `AMBIGUOUS_SWITCH_CONNECTION` under the approved contract
- **AND** the affected schema-v4 candidate record has null switch fields
- **AND** no output is published

#### Scenario: Conversion repeats validation after preflight

- **GIVEN** a previous source or combined preflight completed
- **WHEN** conversion is requested later
- **THEN** conversion rereads and revalidates the current workbook bytes
- **AND** the previous preflight result is not treated as publication authority

## ADDED Requirements

### Requirement: Room address source mapping is exact and nullable

The current primary equipment workbook SHALL expose one unambiguous source column with exact semantic header:

```text
Адрес комнаты
```

That source column SHALL map to canonical schema-v4 `room_address`. Header recognition SHALL use the same approved worksheet/header discovery boundary as the other required primary source columns; the importer SHALL NOT add aliases, substring matching, fuzzy matching, transliteration, or inference from another source field.

The `Адрес комнаты` header SHALL be mandatory for current primary-source preflight and current conversion. Missing or ambiguous discovery of the header SHALL be a fatal source-structure failure.

Each row value SHALL remain nullable. Canonical room-address normalization SHALL use Unicode NFC normalization and leading/trailing trim, preserve case and internal text, and convert blank normalized text to JSON null. A blank address cell SHALL NOT by itself produce a data-quality issue or make an otherwise representable row fatal.

`room_address` SHALL be display metadata only. It SHALL NOT identify a room, replace `room_id`, join records, break ambiguity, select another record, or authorize network routing.

#### Scenario: Room address is mapped

- **WHEN** a source row contains non-blank `Адрес комнаты`
- **THEN** schema-v4 `room_address` contains the canonical normalized text
- **AND** the value participates in schema-v4 deterministic identity

#### Scenario: Room address cell is blank

- **WHEN** a source row has a blank `Адрес комнаты` cell
- **THEN** schema-v4 `room_address` is null
- **AND** the row remains publishable when otherwise valid

#### Scenario: Room address header is absent

- **WHEN** primary-source preflight or conversion cannot discover exactly one required `Адрес комнаты` header
- **THEN** the operation reports a structured fatal source-structure issue
- **AND** conversion does not replace any previous valid snapshot

### Requirement: Canonical inventory snapshot schema v4

Every newly generated canonical equipment inventory snapshot SHALL use `schema_version` equal to JSON integer `4`.

The schema-v4 root fields and optional generation metadata SHALL remain the approved root vocabulary used by historical schemas. Each schema-v4 equipment record SHALL contain exactly:

```text
record_id
source_model
diagnostic_model
ip_address
mac_address
serial_number
room_id
room_name
room_address
device_kind
room_vip
switch_ip_address
switch_port
```

The required non-null record fields remain exactly:

```text
record_id
device_kind
```

The other schema-v4 record fields are nullable under their approved canonical normalization and validation rules. Every declared schema-v4 key SHALL nevertheless be present on every record, including nullable `room_address`, `switch_ip_address`, and `switch_port`.

For primary-only conversion, `switch_ip_address` and `switch_port` SHALL be null on every record. For conversion with an explicitly configured valid network source, those fields SHALL be populated only through the approved MAC-only reconciliation contract.

The deterministic schema-v4 identity payload SHALL contain exactly:

```text
schema_version
records
```

Records SHALL remain sorted by normalized `record_id` for identity construction. Every schema-v4 canonical record field, including `room_address`, `room_vip`, `switch_ip_address`, and `switch_port`, SHALL participate in deterministic identity. `generated_at`, `source_row_count`, import-report fields, and network counters SHALL remain outside identity.

Schema-v4 publication SHALL remain atomic and SHALL validate the complete candidate through the runtime loader before replacing the prior output. Missing or extra schema-v4 record keys, invalid field types or canonical values, duplicate `record_id`, or a declared/recomputed identity mismatch SHALL fail as `INVALID_SNAPSHOT` with no partial publication.

#### Scenario: Primary-only schema-v4 record has stable shape

- **GIVEN** no network source is configured
- **WHEN** conversion succeeds
- **THEN** every record includes `room_address`, `room_vip`, `switch_ip_address`, and `switch_port`
- **AND** both switch fields are null

#### Scenario: Network-enriched schema-v4 record has stable shape

- **GIVEN** a valid network source is configured
- **WHEN** conversion succeeds
- **THEN** every record uses the same exact schema-v4 key set as primary-only conversion
- **AND** switch values reflect only the approved reconciliation result

#### Scenario: Room address changes snapshot identity

- **GIVEN** two otherwise identical valid schema-v4 canonical snapshots
- **WHEN** one record's canonical `room_address` differs
- **THEN** their deterministic `snapshot_id` values differ

#### Scenario: Schema-v4 field is missing

- **WHEN** a snapshot declares schema version 4 but one record omits a declared schema-v4 key even when that field could otherwise be null
- **THEN** loading fails as `INVALID_SNAPSHOT`
- **AND** no partial inventory is published

#### Scenario: Schema-v4 record contains an extra key

- **WHEN** a snapshot declares schema version 4 but one record contains an undeclared extra field
- **THEN** loading fails as `INVALID_SNAPSHOT`
- **AND** the loader does not silently ignore or normalize the extra field
