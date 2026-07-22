## ADDED Requirements

### Requirement: Offline equipment inventory conversion boundary

The application SHALL treat the organization equipment workbook as an external import
source rather than as a normal runtime storage format. A dedicated offline importer SHALL
convert the inspected workbook source into a canonical equipment-inventory snapshot
before the diagnostic application consumes the data.

Normal diagnostic application runtime modules SHALL NOT parse `.xlsx` workbooks and
SHALL NOT require a spreadsheet parsing dependency to start, load a canonical inventory
snapshot, perform inventory queries, or execute existing device diagnostics. An
import-only dependency such as `openpyxl` MAY be used by the offline importer provided
that the runtime inventory path does not import or require it.

The concrete importer mapping SHALL be based on the real workbook or a sanitized source
schema/header sample. Source worksheet names and column semantics SHALL NOT be guessed
or inferred from unrelated repository code.

#### Scenario: Runtime loads inventory without Excel support

- **GIVEN** a valid canonical equipment inventory snapshot exists
- **AND** the spreadsheet import dependency is unavailable
- **WHEN** the diagnostic runtime imports and loads the equipment inventory
- **THEN** the inventory loads through the canonical snapshot path
- **AND** no `.xlsx` parser is imported or required

#### Scenario: Source workbook layout is not yet known

- **WHEN** implementation cannot verify the authoritative worksheet or source-column mapping
- **THEN** it does not invent column names or silently map ambiguous fields
- **AND** the source mapping remains blocked until the real workbook or a sanitized schema sample is inspected

### Requirement: Versioned canonical inventory snapshot

The first runtime storage adapter SHALL consume a UTF-8 JSON document whose root is a
versioned object containing at least `schema_version`, `snapshot_id`, and `records`.
Unsupported schema versions, an invalid root shape, or invalid canonical record shapes
SHALL be rejected before an `EquipmentInventory` is published to runtime consumers.

Each canonical equipment record SHALL contain the following runtime fields:

- non-empty `record_id` unique within the snapshot;
- nullable `source_model`;
- nullable `diagnostic_model` containing an exact supported application model name only when such a mapping is explicitly known;
- nullable normalized `ip_address`;
- nullable authoritative `room_id`;
- nullable `room_name` for display;
- non-empty normalized `device_kind`.

A canonical snapshot SHALL contain only fields approved for runtime use. The importer
SHALL NOT copy every source workbook column into canonical records by default.

#### Scenario: Valid versioned snapshot is loaded

- **WHEN** a canonical JSON snapshot has a supported `schema_version`, a non-empty `snapshot_id`, and valid records
- **THEN** the runtime loader publishes one inventory instance representing that snapshot revision

#### Scenario: Snapshot schema version is unsupported

- **WHEN** the runtime loader receives a snapshot with an unsupported `schema_version`
- **THEN** it rejects the snapshot with a structured safe configuration error
- **AND** it does not partially publish records from that snapshot

#### Scenario: Unsupported source model remains explicit

- **WHEN** an imported source model has no reviewed mapping to a supported diagnostic application model
- **THEN** the canonical record retains its source model when available
- **AND** `diagnostic_model` remains null rather than fabricating a supported model name

### Requirement: Explicit import validation and source-row accounting

The offline importer SHALL validate source structure and canonical output separately from
normal runtime loading. Every inspected source equipment row SHALL be accounted for as a
canonical imported record or as a structured reported issue; a source row SHALL NOT be
silently discarded.

Fatal structural conditions, including unresolved required worksheet/column mapping,
invalid canonical root construction, or non-resolvable duplicate canonical `record_id`
values, SHALL prevent publication of a new snapshot.

Data-quality conditions including missing IP address, invalid IP text, missing room
identity, unsupported/unmapped diagnostic model, duplicate IP assignments, or multiple
relevant devices in one room SHALL remain observable. They SHALL NOT be silently fixed by
deleting records, deduplicating records, selecting the first record, or inventing values.
Where the canonical record can still be represented safely, the importer MAY retain it
with the affected canonical field unresolved and report the issue.

Import diagnostics SHALL use structured issue categories and minimal source row or
record references. They SHALL NOT dump complete source rows or the complete organization
inventory into normal logs or public errors.

#### Scenario: Duplicate IP appears in the source

- **WHEN** two or more valid source rows normalize to the same IP address
- **THEN** every valid canonical record is preserved
- **AND** the duplicate assignment is reported as a data-quality issue
- **AND** the importer does not select or retain only one arbitrary winner

#### Scenario: Source IP is invalid

- **WHEN** a non-empty source IP value cannot be normalized as a valid supported IP address
- **THEN** that invalid text is not inserted into the runtime IP index
- **AND** the source row is accounted for through the canonical unresolved semantics and import report

#### Scenario: Fatal source mapping is unresolved

- **WHEN** the importer cannot resolve a required authoritative source column
- **THEN** it reports a fatal import condition
- **AND** it does not replace a previously valid canonical snapshot with partial output

### Requirement: Storage-independent equipment inventory runtime boundary

Runtime consumers SHALL access equipment data through a focused `EquipmentInventory`
query boundary rather than reading JSON structures directly. The first loader SHALL use
Python standard-library JSON support, but the public inventory query semantics SHALL NOT
depend on JSON-specific dictionary layout, file offsets, or serialization details.

A future storage adapter, including a possible SQLite adapter, SHALL be able to construct
or implement the same inventory query boundary without changing the semantics expected
by application consumers.

The preferred default deployment snapshot path SHALL be
`equipment_inventory.local.json` resolved deterministically from the application/project
root independently of the process current working directory. Tests and explicit callers
MAY provide another path.

#### Scenario: Runtime consumer performs a lookup

- **WHEN** an application consumer needs equipment records
- **THEN** it queries `EquipmentInventory` through the documented lookup methods
- **AND** it does not inspect the canonical JSON root or records list directly

#### Scenario: Application starts from another working directory

- **WHEN** the application process current working directory differs from the project/application root
- **THEN** the default local inventory path resolves to the same deployment snapshot location

#### Scenario: Future storage adapter is introduced

- **WHEN** a future implementation loads the same canonical equipment semantics from another storage technology
- **THEN** inventory consumers retain the same zero/one/many query-result behavior
- **AND** PDU or codec application logic does not need storage-format-specific changes

### Requirement: Indexed in-memory inventory lookup

A successfully loaded inventory SHALL build immutable in-memory indexes once for the
normal lookup paths required by later room-context orchestration. The indexes SHALL
provide semantics equivalent to:

```text
ip_address -> tuple[EquipmentRecord, ...]
room_id -> tuple[EquipmentRecord, ...]
(room_id, device_kind) -> tuple[EquipmentRecord, ...]
```

Normal lookup methods SHALL use the indexes rather than perform a full scan of all
records for every query. Index values SHALL preserve every matching canonical record.

The inventory query surface SHALL provide operations equivalent to:

```text
find_by_ip(ip_address)
find_room_equipment(room_id)
find_by_room_and_kind(room_id, device_kind)
```

Exact implementation names MAY differ only if these semantics remain unchanged.

#### Scenario: IP has one matching record

- **WHEN** a normalized IP address exists on exactly one canonical record
- **THEN** IP lookup returns a one-record result collection

#### Scenario: IP has multiple matching records

- **WHEN** a normalized IP address exists on multiple canonical records
- **THEN** IP lookup returns every matching record in deterministic order
- **AND** the inventory layer does not choose the first record as authoritative

#### Scenario: Room equipment is queried repeatedly

- **GIVEN** the inventory loaded its room indexes successfully
- **WHEN** a consumer repeatedly queries one room or one room/device-kind pair
- **THEN** those lookups use the prebuilt indexes
- **AND** they do not repeatedly scan the complete records collection

### Requirement: Ambiguity-preserving inventory query contract

Inventory query methods SHALL return zero or more records and SHALL preserve ambiguity
for their caller. The inventory layer SHALL NOT convert a multi-match lookup into a
single authoritative device, room, or codec selection.

An IP lookup with no match SHALL return an empty result collection rather than a generic
connection failure. A room lookup with no matching device kind SHALL likewise return an
empty result collection. Interpretation of zero, one, or multiple matches as
`NOT_FOUND`, `RESOLVED`, or `AMBIGUOUS` belongs to the later application orchestration
change and SHALL NOT be hidden inside the storage layer.

`room_name` SHALL NOT be silently used as an authoritative room identity when `room_id`
is absent unless the inspected source contract explicitly defines that mapping.

#### Scenario: IP is absent from inventory

- **WHEN** no canonical record matches the requested IP address
- **THEN** the inventory returns an empty result collection
- **AND** it does not raise or synthesize a device connection error

#### Scenario: Multiple codecs exist in one room

- **WHEN** a room/device-kind lookup for `video_codec` matches more than one record
- **THEN** every matching record is returned
- **AND** the inventory layer does not apply `records[0]` or another implicit primary-codec rule

#### Scenario: Record has no authoritative room identity

- **WHEN** a record has a display `room_name` but no authoritative `room_id`
- **AND** the source mapping does not explicitly define the display name as room identity
- **THEN** the record is not silently indexed under an invented room identifier

### Requirement: Immutable snapshot revision identity

Each loaded `EquipmentInventory` SHALL represent one immutable canonical snapshot
revision identified by its non-secret `snapshot_id`. Runtime consumers SHALL NOT mutate
canonical records or indexes in place.

Replacing inventory data SHALL create and validate a new inventory instance before it is
published by a future application composition boundary. This change does not require
automatic file watching, runtime hot reload, or GUI reload controls.

#### Scenario: Loaded records are queried

- **WHEN** runtime consumers perform inventory lookups
- **THEN** the loaded snapshot records and indexes remain unchanged by those queries

#### Scenario: A newer snapshot is loaded later

- **WHEN** a future composition path replaces the current inventory with a newly validated snapshot
- **THEN** the replacement has its own `snapshot_id`
- **AND** the old inventory instance is not mutated into the new revision

### Requirement: Production inventory data isolation

Real organization equipment workbooks and generated production inventory snapshots
SHALL be treated as deployment-local operational data and SHALL NOT be committed to the
public or shared repository by the implementation of this capability.

The default `equipment_inventory.local.json` production snapshot SHALL be ignored by
Git. Tests SHALL use synthetic fixtures that contain no real organization IP addresses,
room identities, equipment identifiers, or other operational inventory data. A tracked
example snapshot MAY exist only when all values are synthetic.

Runtime and importer logs/errors SHALL not emit the complete inventory or complete source
rows. Repository code MAY contain the canonical schema, importer, normalization logic,
synthetic fixtures, and documentation needed to reproduce the import process.

#### Scenario: Developer has a local production snapshot

- **WHEN** `equipment_inventory.local.json` exists in the developer or deployment checkout
- **THEN** normal Git status does not propose that production snapshot for tracking

#### Scenario: Inventory tests require example data

- **WHEN** automated tests exercise inventory loading, indexing, ambiguity, or importer behavior
- **THEN** they use synthetic equipment, room, model, and IP values
- **AND** no real organization inventory is required

#### Scenario: Import fails on one row

- **WHEN** the importer reports a row-specific validation issue
- **THEN** the public diagnostic identifies the structured issue and minimal row/record reference needed for correction
- **AND** it does not dump the complete source row or full inventory snapshot
