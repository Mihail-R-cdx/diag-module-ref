## MODIFIED Requirements

### Requirement: Offline equipment inventory conversion boundary

The application SHALL treat organization equipment workbooks and optional approved enrichment workbooks as external import sources rather than normal runtime storage formats. A dedicated offline importer SHALL convert the inspected primary equipment workbook, and when explicitly configured the inspected network-connection workbook, into one canonical equipment-inventory snapshot before the diagnostic application consumes the data.

Normal diagnostic application runtime modules SHALL NOT parse `.xlsx` workbooks and SHALL NOT require a spreadsheet parsing dependency to start, load a canonical inventory snapshot, perform inventory queries, or execute existing device diagnostics. An import-only dependency such as `openpyxl` MAY be used by the offline importer provided that the runtime inventory path does not import or require it.

The confirmed primary organization source mapping and the confirmed network-enrichment source mapping defined by this capability SHALL be implemented explicitly. Source-only fields and consistency evidence SHALL remain inside the importer boundary unless the canonical schema explicitly includes them.

Every newly successful conversion SHALL publish schema version 4. A one-source conversion with no network workbook configured SHALL remain an intentional supported mode and SHALL publish schema v4 with null switch fields. A conversion with an explicitly configured valid network workbook SHALL also publish schema v4 and SHALL populate switch fields only through the approved reconciliation contract. If a network workbook is explicitly configured but its path/configuration is invalid, the workbook is unreadable, worksheet `Устройства` is missing or ambiguous, or a required network header is missing or ambiguous, the importer SHALL fail before publication and SHALL NOT silently reinterpret the run as primary-only conversion.

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

For the confirmed organization workbook, `ID комнаты` SHALL map to canonical `room_id` and SHALL remain the authoritative room identity. `Название комнаты` SHALL map to canonical `room_name` as a display attribute. Schema v4 additionally carries `room_address` and the existing `room_vip` as per-record display metadata; none of those display fields SHALL identify or merge rooms.

The importer SHALL NOT automatically substitute `room_name`, `room_address`, or `room_vip` for missing `room_id` and SHALL NOT merge rooms because display metadata matches. Records sharing one non-null `room_id` SHALL remain members of that authoritative room even when their non-null display metadata differs.

For current schema-v4 import, the importer SHALL preserve normalized per-record room display metadata without cross-record reconciliation. Different `room_name`, `room_address`, or `room_vip` values under the same `room_id` SHALL NOT by themselves produce a room-display conflict issue, SHALL NOT cause record deletion, and SHALL NOT cause the importer to select or rewrite a room-wide display value.

Missing or blank `ID комнаты` SHALL produce `room_id = null` and MAY produce an observable data-quality or consistency issue. It SHALL NOT by itself make an otherwise representable canonical record fatal.

#### Scenario: Devices share one authoritative room ID

- **WHEN** multiple records have the same canonical `ID комнаты`
- **THEN** they have the same canonical `room_id`
- **AND** the room index returns all of them under that one `room_id`

#### Scenario: One room ID has differing display metadata

- **WHEN** records with the same canonical `room_id` contain different non-null `room_name`, `room_address`, or `room_vip` values
- **THEN** all canonical records and their normalized per-record display values are preserved
- **AND** no room-display conflict issue is emitted solely for that difference
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

For the primary source, missing or ambiguous discovery of the required exact `Адрес комнаты` header SHALL be a fatal source-structure issue. A blank individual address cell SHALL NOT be fatal and SHALL normalize to `room_address = null`.

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

A row with a usable partial candidate MAY produce both the candidate and a missing/invalid-field issue. A non-fatal row-level network issue SHALL NOT block schema-v4 publication, delete a primary record, or cause silent fallback to another import mode.

Different non-null `room_name`, `room_address`, or `room_vip` values on records sharing one authoritative `room_id` SHALL NOT be reported as importer room-display conflicts. In particular, current schema-v4 import SHALL NOT emit `ROOM_NAME_CONFLICT`, `ROOM_VIP_CONFLICT`, or a new `ROOM_ADDRESS_CONFLICT` solely from those differences. Row-level unsupported non-blank `VIP оборудование` values SHALL still produce the existing `INVALID_ROOM_VIP` data-quality issue.

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

#### Scenario: Required room-address header is missing

- **GIVEN** the primary workbook cannot provide one unambiguous exact `Адрес комнаты` header
- **WHEN** primary preflight or conversion is attempted
- **THEN** the importer reports a fatal source-structure issue
- **AND** the previous valid output remains intact

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
- `UNSUPPORTED_SCHEMA`: the JSON root declares a `schema_version` other than supported integer versions `1`, `2`, `3`, or `4`;
- `INVALID_SNAPSHOT`: canonical shape/content is invalid for its declared supported version, required fields are invalid, record IDs collide, or declared `snapshot_id` does not match recomputed canonical content.

No failed load SHALL publish a partial `EquipmentInventory`, partial records, or partial indexes. Runtime consumers SHALL NOT need to inspect raw storage-specific exception types or strings to understand inventory availability.

#### Scenario: Snapshot schema version is unsupported

- **WHEN** the runtime loader receives a JSON object whose `schema_version` is not integer `1`, `2`, `3`, or `4`
- **THEN** loading fails with category `UNSUPPORTED_SCHEMA`
- **AND** no inventory is published

#### Scenario: Supported schema has invalid record shape

- **WHEN** a snapshot declares schema version `1`, `2`, `3`, or `4` but its canonical record shape is invalid for that exact version
- **THEN** loading fails with category `INVALID_SNAPSHOT`
- **AND** no inventory is published

### Requirement: Schema v2 carries explicit room VIP state

Historical schema-v2 canonical equipment inventory snapshots use `schema_version` exactly `2` and every schema-v2 equipment record contains exactly one field in addition to schema v1:

```text
room_vip
```

`room_vip` SHALL be a JSON boolean or JSON null. `true` means the source explicitly identifies the authoritative room as VIP, `false` means the source explicitly identifies it as non-VIP, and null means the source value is absent, unsupported, or unresolved.

The deterministic schema-v2 snapshot identity SHALL include `room_vip` for every record. Generation metadata SHALL remain outside snapshot identity.

The current importer SHALL no longer publish new schema-v2 snapshots. New successful conversions publish schema v4, while valid historical schema-v2 snapshots remain loadable under their exact original shape and identity contract.

#### Scenario: Historical VIP room snapshot remains loadable

- **GIVEN** a valid schema-v2 snapshot contains an explicitly supported VIP value
- **WHEN** the runtime loader validates it
- **THEN** the schema-v2 record contains the corresponding JSON boolean
- **AND** the boolean participates in deterministic schema-v2 snapshot identity

#### Scenario: Historical VIP value is unavailable

- **GIVEN** a valid schema-v2 snapshot contains null `room_vip`
- **WHEN** the runtime loader validates it
- **THEN** the canonical `room_vip` value remains null
- **AND** the loader does not invent a room-wide value

#### Scenario: Current primary-only conversion does not emit schema v2

- **WHEN** the current offline importer successfully converts a primary workbook without a network source
- **THEN** the candidate schema version is `4`
- **AND** no new schema-v2 snapshot is published

### Requirement: Existing schema-v1 snapshots remain loadable

The runtime inventory loader SHALL continue to accept valid schema-v1 snapshots and SHALL additionally accept valid schema-v2, schema-v3, and schema-v4 snapshots. It SHALL strictly validate each supported schema version against its own approved exact record fields and identity payload.

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

#### Scenario: Existing deployment snapshot is loaded

- **GIVEN** a valid schema-v1 snapshot created before this change
- **WHEN** the runtime loader loads it
- **THEN** the inventory is available
- **AND** every runtime record exposes unknown VIP state and null room-address and switch fields

#### Scenario: Hybrid snapshot is rejected

- **WHEN** a snapshot claims schema version 1 but contains `room_vip`, `room_address`, or either switch field, claims schema version 2 but contains `room_address` or either switch field, or claims schema version 3 but contains `room_address`
- **THEN** loading fails as an invalid snapshot
- **AND** no partial inventory is published

#### Scenario: Existing schema-v2 deployment snapshot is loaded

- **GIVEN** a valid schema-v2 snapshot
- **WHEN** the runtime loader loads it
- **THEN** the inventory is available
- **AND** every runtime record exposes source `room_vip`, null `room_address`, and null switch fields

#### Scenario: Valid schema-v3 snapshot is loaded

- **GIVEN** a valid schema-v3 snapshot with correct deterministic identity
- **WHEN** the runtime loader loads it
- **THEN** the inventory is available
- **AND** every runtime record exposes null `room_address`
- **AND** both switch fields are exposed exactly as canonical nullable attributes

#### Scenario: Valid schema-v4 snapshot is loaded

- **GIVEN** a valid schema-v4 snapshot with correct deterministic identity
- **WHEN** the runtime loader loads it
- **THEN** the inventory is available
- **AND** `room_vip`, `room_address`, `switch_ip_address`, and `switch_port` are exposed exactly as canonical nullable attributes

#### Scenario: Future schema is rejected

- **WHEN** a snapshot declares an undeclared schema version
- **THEN** loading fails as `UNSUPPORTED_SCHEMA`
- **AND** no partial inventory is published

### Requirement: Room VIP evidence uses normative room-wide aggregation

Canonical `room_vip` remains per-record source metadata. The current schema-v4 importer SHALL preserve equipment-record multiplicity and each normalized `room_vip` value without performing cross-record VIP conflict reconciliation. Null remains absence of authoritative VIP evidence for that record.

The existing runtime room-context layer used before the separate room-tree orchestration change SHALL continue to evaluate VIP evidence across all records sharing one non-null authoritative `room_id` when that legacy presentation path requests a room-wide VIP label. The runtime aggregation table remains:

```text
no room records                         -> unresolved room
all room_vip values null                -> NO_DATA
one or more true, all others null/true  -> VIP_TRUE
one or more false, all others null/false-> VIP_FALSE
at least one true and at least one false-> CONFLICT
```

The importer SHALL NOT report `ROOM_VIP_CONFLICT` solely because both true and false occur under the same authoritative `room_id`. It SHALL preserve those record values unchanged. Runtime room-context resolution SHALL continue to expose `ДА` for `VIP_TRUE`, `НЕТ` for `VIP_FALSE`, `НЕТ ДАННЫХ` for `NO_DATA`, `КОНФЛИКТ ДАННЫХ` for `CONFLICT`, and unresolved room state when no records exist for the authoritative room lookup. The legacy runtime aggregation SHALL NOT rewrite canonical inventory and SHALL NOT grant importer reconciliation authority.

#### Scenario: All room VIP evidence is absent

- **WHEN** all records sharing one authoritative `room_id` contain `room_vip = null`
- **THEN** legacy runtime VIP presentation is `НЕТ ДАННЫХ`
- **AND** the importer reports no room-wide VIP conflict

#### Scenario: Known VIP evidence is mixed with null

- **WHEN** records sharing one authoritative `room_id` contain one or more true values and all remaining values are true or null
- **THEN** legacy runtime VIP presentation is `ДА`
- **AND** null does not weaken or conflict with the known consistent value

#### Scenario: Known non-VIP evidence is mixed with null

- **WHEN** records sharing one authoritative `room_id` contain one or more false values and all remaining values are false or null
- **THEN** legacy runtime VIP presentation is `НЕТ`
- **AND** null does not weaken or conflict with the known consistent value

#### Scenario: One room contains differing VIP flags

- **WHEN** records sharing one authoritative `room_id` contain at least one true and at least one false VIP value
- **THEN** all otherwise valid records remain in the snapshot with their own canonical values
- **AND** the importer does not report `ROOM_VIP_CONFLICT` solely for that difference
- **AND** the legacy runtime presentation remains `КОНФЛИКТ ДАННЫХ`
- **AND** canonical inventory is not rewritten

### Requirement: Converter paths use repository-safe absolute configuration

The offline converter SHALL preserve execution-time configuration variables named `SOURCE_XLSX_PATH` and `OUTPUT_JSON_PATH` and SHALL preserve the exact optional network-source configuration variable `NETWORK_XLSX_PATH`. Every configured value SHALL be a resolved absolute `Path` before workbook reading or snapshot publication begins.

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
no network source configured -> intentional primary-only schema-v4 mode
```

Supplying a network source through any approved public surface SHALL request network-enriched schema-v4 conversion. Failure of that configured source SHALL be fatal for that run and SHALL NOT be interpreted as absence of configuration. No equivalent or implementation-selected public name is permitted.

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
- **THEN** the run remains in intentional primary-only mode
- **AND** absence of the optional source is not reported as a failure
- **AND** successful conversion targets schema version 4

#### Scenario: Configured network path is unusable

- **GIVEN** a network source path is explicitly or environmentally configured
- **AND** the path does not resolve to a readable regular workbook file
- **WHEN** the converter starts
- **THEN** it returns a structured fatal configuration/source issue
- **AND** it does not publish or replace the output snapshot

#### Scenario: Direct API uses the approved keyword

- **WHEN** a caller supplies `network_source_path` to `import_equipment_inventory`
- **THEN** that exact value requests network-enriched schema-v4 conversion
- **AND** the caller does not need another implementation-specific adapter or keyword

### Requirement: Canonical inventory snapshot schema v3

Historical network-enriched schema-v3 snapshots use `schema_version` equal to JSON integer `3`.

The schema-v3 root fields and optional generation metadata SHALL remain the same approved root vocabulary used by schema v2. Schema-v3 records SHALL contain all schema-v2 fields plus exactly:

```text
switch_ip_address
switch_port
```

The complete exact schema-v3 record field set SHALL remain:

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

The runtime loader SHALL continue to validate and load valid historical schema-v3 snapshots under this exact contract. The current importer and combined preflight SHALL no longer create new schema-v3 candidates; current candidate publication targets schema v4.

#### Scenario: Historical unique connection is loaded

- **GIVEN** a valid historical schema-v3 record contains one normalized switch IP and port pair
- **WHEN** the runtime loader validates the snapshot
- **THEN** those switch values participate in deterministic schema-v3 snapshot identity
- **AND** runtime adaptation exposes them with `room_address = null`

#### Scenario: Historical connection is unavailable

- **GIVEN** a valid historical schema-v3 record has no unambiguous network connection
- **WHEN** the runtime loader validates the snapshot
- **THEN** both schema-v3 switch fields remain null unless one historical unique partial field is valid
- **AND** the record remains present when otherwise valid

#### Scenario: Historical switch field changes identity

- **GIVEN** two otherwise identical valid schema-v3 canonical snapshots
- **WHEN** one record's `switch_ip_address` or `switch_port` differs
- **THEN** their deterministic `snapshot_id` values differ

#### Scenario: Primary source row count remains canonical metadata

- **GIVEN** a valid historical schema-v3 snapshot declares `source_row_count`
- **WHEN** its metadata is interpreted
- **THEN** `source_row_count` retains the primary equipment-workbook row-count meaning
- **AND** network row count remains report metadata only

#### Scenario: Hybrid schema-v2 record is rejected

- **WHEN** a snapshot claims schema version 2 but contains either schema-v3 switch field
- **THEN** loading fails as an invalid snapshot
- **AND** no partial inventory is published

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

### Requirement: Existing conversion modes and publication semantics remain supported

The standalone GUI support SHALL NOT remove or change the intentional one-source and explicit two-source CLI/direct API conversion entry points. Both current conversion modes SHALL publish schema version 4 under this change. The direct conversion API SHALL continue to accept an optional network source under the existing path-priority contract.

Except for the explicitly approved schema-v4 migration and the added canonical `room_address` field, preflight APIs, guarded publication, and report extensions SHALL NOT independently change canonical source authorities, diagnostic-model recognition, MAC-only reconciliation, deterministic snapshot identity semantics, runtime candidate validation, or ordinary atomic publication. The importer/domain layer SHALL NOT import PyQt5.

#### Scenario: One-source CLI conversion publishes schema v4

- **GIVEN** the CLI or direct API explicitly performs conversion without a network source
- **WHEN** conversion succeeds
- **THEN** it publishes schema version 4 under the primary-only schema-v4 contract
- **AND** standalone GUI support does not require PyQt5 in the importer or runtime loader

#### Scenario: Two-source direct conversion publishes schema v4

- **GIVEN** the direct API receives explicit valid primary, network, and output paths
- **WHEN** conversion succeeds
- **THEN** it publishes schema version 4 under the existing reconciliation and atomic-publication contracts
- **AND** the same operation result can be rendered by CLI or GUI consumers

### Requirement: Switch fields are non-authoritative runtime inventory metadata

The runtime `EquipmentRecord` SHALL expose nullable `switch_ip_address` and `switch_port` for every supported snapshot version. Schema-v1 and schema-v2 records SHALL expose loader-adapted null values. Schema-v3 and schema-v4 records SHALL expose their validated canonical switch fields.

Existing inventory indexes SHALL remain equivalent to:

```text
ip_address -> tuple[EquipmentRecord, ...]
room_id -> tuple[EquipmentRecord, ...]
(room_id, device_kind) -> tuple[EquipmentRecord, ...]
```

This capability SHALL NOT add an index or public query by switch IP or switch port.

The application/composition layer MAY read `switch_ip_address` and `switch_port` from the one unambiguous record returned through the existing current-device IP lookup solely to create non-blocking equipment-page presentation. It SHALL pass only safe scalar presentation values to registered equipment screens. Screens SHALL NOT receive or query the complete inventory, interpret lookup multiplicity, reconcile source evidence, or use switch fields as device-observation data.

The switch fields remain non-authoritative runtime inventory metadata. Diagnostic model dispatch, credential configuration or fallback, handler acquisition, request retry, successful credential memory, room-context aggregation, PDU-room-codec enrichment, related-codec selection, device controllers, workers, handlers, parsers, transports, protocol behavior, device control, and device or switch network I/O SHALL ignore both switch fields. Switch values SHALL NOT change lookup membership or ordering, select between ambiguous records, authorize a diagnostic lifecycle, classify a device request, or become a precondition for existing diagnostics.

A unique record's two switch fields SHALL remain independent for presentation. A non-null canonical field MAY be displayed while the other field is null. Null fields, loader-adapted null fields from schema v1/v2, unavailable inventory, invalid current device IP, zero matching records, or multiple matching records SHALL produce unavailable display values without changing the validity or availability of existing device diagnostics.

The importer MAY extend its structured result with safe network worksheet/header context and aggregate counts needed to validate two-source conversion. Those report fields SHALL NOT enter canonical records, canonical `source_row_count`, or `snapshot_id`.

#### Scenario: Existing IP and room queries are unchanged

- **WHEN** any valid supported inventory version is loaded
- **THEN** `find_by_ip`, `find_room_equipment`, and `find_by_room_and_kind` preserve their existing zero/one/many semantics
- **AND** switch fields do not alter membership or ordering
- **AND** no switch-IP or switch-port query is added

#### Scenario: Unique current record supplies display-only values

- **GIVEN** existing device-IP lookup returns exactly one record
- **WHEN** the application prepares equipment-page inventory presentation
- **THEN** it may read that record's runtime `switch_ip_address` and `switch_port`
- **AND** schema-v3/v4 canonical values and schema-v1/v2 loader-adapted nulls follow the same presentation boundary
- **AND** only safe scalar display values are passed to the registered screen
- **AND** neither field becomes device-response or network-I/O authority

#### Scenario: Unique partial switch connection remains useful

- **GIVEN** existing device-IP lookup returns exactly one record
- **AND** exactly one switch field is non-null
- **WHEN** the application prepares equipment-page presentation
- **THEN** it preserves the non-null canonical field for display
- **AND** the null field remains unavailable
- **AND** it does not infer, reconstruct, or query the missing value

#### Scenario: Ambiguous current device is not narrowed for display

- **GIVEN** existing device-IP lookup returns multiple records
- **WHEN** one record has a matching diagnostic model, preferred device kind, or more complete switch values
- **THEN** the application displays neither record's switch connection
- **AND** it does not break ambiguity by model, kind, MAC, room, completeness, or order

#### Scenario: Older snapshots remain compatible

- **GIVEN** a valid schema-v1 or schema-v2 snapshot is loaded
- **WHEN** equipment-page switch presentation is requested
- **THEN** the loader-provided null switch fields produce unavailable display values
- **AND** the source snapshot is not rewritten or upgraded
- **AND** existing diagnostics remain available

#### Scenario: Diagnostics ignore switch metadata for schema v3 and v4

- **GIVEN** the application loads a valid schema-v3 or schema-v4 snapshot
- **WHEN** existing diagnostic dispatch, credential, request, room, PDU enrichment, handler, worker, controller, transport, or control workflows execute
- **THEN** their authority and lifecycle remain unchanged
- **AND** they do not inspect switch IP or port
- **AND** informational equipment-page rendering does not become a success or failure gate

#### Scenario: Device payload cannot redefine canonical switch presentation

- **GIVEN** a device handler, parser, worker, or controller produces an IP, port, interface, MAC, or connection value
- **WHEN** the result is rendered
- **THEN** that value does not replace or supplement canonical `switch_ip_address` or `switch_port`
- **AND** no switch field is added to the device-result contract by this capability

#### Scenario: No switch management is introduced

- **WHEN** switch IP or port is available for display
- **THEN** the application performs no switch reachability check, authentication, link-state query, configuration, or other switch network I/O
- **AND** it does not request or resolve switch credentials

#### Scenario: Report metadata is not canonical identity

- **WHEN** safe network-run counters or source-location context differ while canonical records for the same schema version remain identical
- **THEN** deterministic `snapshot_id` remains identical
- **AND** report-only metadata does not gain canonical authority

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
