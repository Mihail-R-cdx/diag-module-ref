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

### Requirement: Canonical inventory snapshot schema v1

The first runtime storage adapter SHALL consume a UTF-8 JSON document whose root is a
JSON object. For schema v1 the required root fields SHALL be:

- `schema_version`: JSON integer and exactly `1`;
- `snapshot_id`: non-empty JSON string satisfying the deterministic snapshot identity contract;
- `records`: JSON array of canonical equipment record objects.

The schema-v1 root MAY additionally contain only reviewed non-secret generation metadata.
The initially approved optional metadata fields are:

- `generated_at`: RFC 3339 UTC timestamp string;
- `source_row_count`: non-negative JSON integer.

Generation metadata SHALL NOT affect runtime lookup semantics or `snapshot_id` identity.
A field outside this approved schema SHALL require a reviewed schema change rather than
being copied opportunistically from the source workbook.

Each schema-v1 canonical equipment record SHALL contain exactly these runtime fields:

- `record_id`: non-empty JSON string, unique within the snapshot after canonical normalization;
- `source_model`: JSON string or null;
- `diagnostic_model`: JSON string or null, containing an exact supported application model name only when such a reviewed mapping is explicitly known;
- `ip_address`: canonical IPv4 JSON string or null;
- `room_id`: non-empty normalized JSON string or null;
- `room_name`: non-empty normalized JSON string or null;
- `device_kind`: JSON string containing exactly one schema-v1 canonical vocabulary value.

Schema-v1 `device_kind` is a closed vocabulary:

```text
pdu
video_codec
other
```

The importer SHALL map source equipment types into this vocabulary explicitly. Unknown,
unmapped, or irrelevant equipment SHALL use `other`; importers SHALL NOT emit ad hoc
alternatives such as `codec`, `vcs_codec`, `video-codec`, or organization-specific labels
as canonical `device_kind` values.

Canonical string normalization for `record_id`, `source_model`, `diagnostic_model`,
`room_id`, and `room_name` SHALL normalize Unicode text to NFC and remove leading and
trailing whitespace. Empty normalized `record_id` is invalid. Empty normalized nullable
text SHALL become null. Canonical normalization SHALL preserve case and internal text
unless a separately reviewed source mapping explicitly defines a stronger authoritative
identifier rule before canonicalization.

`ip_address`, when present, SHALL be the normalized dotted-decimal representation of a
valid IPv4 address. Invalid source IP text SHALL become null under the approved unresolved
import semantics and SHALL NOT be retained as an index key.

A canonical snapshot SHALL contain only fields approved for runtime use. The importer
SHALL NOT copy every source workbook column into canonical records by default.

#### Scenario: Valid schema-v1 snapshot is loaded

- **WHEN** a canonical JSON snapshot contains integer `schema_version` equal to `1`, a valid deterministic `snapshot_id`, and a JSON-array `records` value whose records satisfy the schema-v1 field contract
- **THEN** the runtime loader may publish one inventory instance representing that snapshot revision

#### Scenario: Canonical device kind is emitted

- **WHEN** the inspected source mapping identifies a source row as a video-conferencing codec
- **THEN** the canonical `device_kind` is exactly `video_codec`
- **AND** runtime consumers do not need to recognize organization-specific codec category spellings

#### Scenario: Unsupported source model remains explicit

- **WHEN** an imported source model has no reviewed mapping to a supported diagnostic application model
- **THEN** the canonical record retains its normalized source model when available
- **AND** `diagnostic_model` remains null rather than fabricating a supported model name

### Requirement: Stable deterministic canonical record identity

Schema-v1 `record_id` SHALL be a stable deterministic identity for one canonical equipment
record under the reviewed source contract. The importer SHALL NOT generate `record_id`
from random UUIDs, timestamps, per-import counters, or other values that can change when
the same logical source inventory is imported again.

When the inspected source provides an authoritative equipment identifier that is intended
to be unique and stable, the importer SHALL use its canonical normalized value as
`record_id`. If the source does not provide such an identifier, `record_id` MAY be derived
only by an explicitly reviewed deterministic rule over stable source identity fields.
The derivation rule SHALL be documented as part of the concrete source mapping before the
importer is considered implementation-complete.

Source row number or physical workbook row order SHALL NOT participate in `record_id`
derivation unless the reviewed authoritative source contract explicitly defines row
position as part of equipment identity. Mutable placement/display attributes such as
`room_id` or `room_name` SHALL NOT be used in a derived identity merely for convenience;
they MAY participate only when the reviewed source contract explicitly defines them as
part of the equipment identity key.

Duplicate normalized authoritative identifiers and collisions produced by an approved
deterministic derivation SHALL be fatal source-contract failures. The importer SHALL NOT
silently repair such conflicts by appending arbitrary suffixes, row numbers, counters, or
other invented disambiguators. If the inspected source contract does not provide enough
stable information to define a unique deterministic `record_id`, source mapping and
snapshot publication SHALL remain blocked until a reviewed architectural decision defines
the identity rule.

#### Scenario: Authoritative equipment identity is available

- **WHEN** the inspected source provides a stable authoritative unique equipment identifier
- **THEN** the importer canonically normalizes that identifier and uses it as `record_id`
- **AND** importing the same logical equipment again produces the same `record_id`

#### Scenario: Source has no authoritative unique identifier

- **WHEN** the inspected source has no single authoritative unique equipment identifier
- **AND** a reviewed deterministic derivation from stable source identity fields has been approved
- **THEN** the importer applies exactly that derivation rule
- **AND** it does not substitute a random, timestamp-based, row-position-based, or per-import identity

#### Scenario: Stable identity cannot be defined

- **WHEN** the inspected source contract provides neither a stable authoritative unique identifier nor enough stable fields for an approved deterministic derivation
- **THEN** source mapping remains blocked pending architectural review
- **AND** the importer does not publish a snapshot using invented `record_id` values

#### Scenario: Authoritative or derived identity collides

- **WHEN** two source records normalize or derive to the same `record_id`
- **THEN** the importer reports a fatal identity conflict
- **AND** it does not append arbitrary suffixes or row positions to manufacture uniqueness
- **AND** no new snapshot is published from that import

#### Scenario: Non-authoritative source rows are reordered

- **GIVEN** source row order is not part of the reviewed authoritative source contract
- **WHEN** the same normalized logical inventory is imported with its workbook rows reordered
- **THEN** each logical equipment record retains the same `record_id`
- **AND** canonical record order remains unchanged
- **AND** `snapshot_id` remains unchanged

### Requirement: Deterministic canonical snapshot identity

Schema-v1 `snapshot_id` SHALL identify canonical inventory data content, not one execution
of the importer. Identical normalized canonical content SHALL produce the same
`snapshot_id`; changed canonical content SHALL produce a different `snapshot_id` for
ordinary operation.

For schema v1, canonical records SHALL be published in deterministic ascending
`record_id` order using Unicode code-point ordering after canonical normalization.
`snapshot_id` SHALL use this exact representation:

```text
sha256:<64 lowercase hexadecimal characters>
```

The digest SHALL be SHA-256 over the UTF-8 canonical JSON serialization of an identity
payload containing exactly:

```text
schema_version
records
```

The identity payload SHALL use integer `schema_version` equal to `1`, the deterministic
canonical record order, lexicographically sorted JSON object keys, compact JSON separators
with no insignificant whitespace, and direct UTF-8 encoding of normalized Unicode text.
Optional generation metadata such as `generated_at` and `source_row_count` SHALL be
excluded from the identity payload.

The runtime loader SHALL independently recompute the expected schema-v1 `snapshot_id`
from the actually loaded and validated `schema_version` and canonical `records` using this
exact canonical identity algorithm before publishing an `EquipmentInventory`. The loader
SHALL compare the recomputed value with the declared `snapshot_id`. A syntactically valid
declared `snapshot_id` that does not equal the recomputed value SHALL make the snapshot
invalid; loading SHALL fail as `INVALID_SNAPSHOT`, and no inventory, records, or indexes
from that snapshot SHALL be published.

Importer generation and runtime verification SHALL share the same normative canonical
serialization and digest semantics. They SHALL NOT use different key ordering, record
ordering, Unicode normalization, optional metadata, or whitespace rules when calculating
or verifying the identity.

#### Scenario: Same canonical content is imported twice

- **WHEN** two imports produce identical normalized canonical records
- **THEN** they produce the same canonical record order
- **AND** they produce the same `snapshot_id`
- **AND** differing generation timestamps, if present, do not change `snapshot_id`

#### Scenario: Canonical content changes

- **WHEN** at least one canonical identity field or canonical record membership changes
- **THEN** the resulting canonical identity payload changes
- **AND** the newly generated snapshot uses the SHA-256 identity derived from that changed payload

#### Scenario: Declared snapshot identity does not match loaded content

- **GIVEN** a schema-v1 snapshot has otherwise valid canonical fields and records
- **AND** its declared `snapshot_id` is syntactically valid but does not equal the value recomputed from the loaded `schema_version` and canonical `records`
- **WHEN** the runtime loader validates the snapshot before publication
- **THEN** loading fails with category `INVALID_SNAPSHOT`
- **AND** no `EquipmentInventory`, partial records, or partial indexes from that snapshot are published

### Requirement: Structured runtime inventory load failure contract

The runtime inventory loader SHALL expose safe structured load failures through a
machine-readable category and a non-secret human-readable message. The concrete Python
exception hierarchy is an implementation detail, but every failed load SHALL classify as
exactly one of:

```text
NOT_FOUND
UNREADABLE
INVALID_FORMAT
UNSUPPORTED_SCHEMA
INVALID_SNAPSHOT
```

The category semantics SHALL be:

- `NOT_FOUND`: the configured snapshot path does not exist;
- `UNREADABLE`: the snapshot exists but cannot be read as required because of filesystem or access failure;
- `INVALID_FORMAT`: the file can be read but is not valid UTF-8 JSON;
- `UNSUPPORTED_SCHEMA`: the JSON root declares a `schema_version` other than integer `1`;
- `INVALID_SNAPSHOT`: the JSON value has an invalid root shape, missing/invalid required fields, duplicate normalized `record_id`, invalid canonical field values/types, a malformed schema-v1 `snapshot_id`, a declared `snapshot_id` that does not match the digest recomputed from the actual canonical content, or otherwise violates the canonical schema contract.

A failed load SHALL NOT publish a partial `EquipmentInventory`, partial records, or partial
indexes. Runtime consumers SHALL NOT need to inspect raw `FileNotFoundError`,
`JSONDecodeError`, `ValueError`, or other implementation-specific exception types to
distinguish these failure categories.

#### Scenario: Inventory file is absent

- **WHEN** the configured canonical snapshot path does not exist
- **THEN** loading fails with category `NOT_FOUND`
- **AND** no `EquipmentInventory` is published

#### Scenario: Inventory file contains invalid JSON

- **WHEN** the configured snapshot can be read but is not valid UTF-8 JSON
- **THEN** loading fails with category `INVALID_FORMAT`
- **AND** no `EquipmentInventory` is published

#### Scenario: Snapshot schema version is unsupported

- **WHEN** the runtime loader receives a JSON object with `schema_version` other than integer `1`
- **THEN** it rejects the snapshot with category `UNSUPPORTED_SCHEMA`
- **AND** it does not partially publish records from that snapshot

#### Scenario: Snapshot has duplicate record identity

- **WHEN** two canonical records have the same normalized `record_id`
- **THEN** loading fails with category `INVALID_SNAPSHOT`
- **AND** the loader does not silently deduplicate or select one record

### Requirement: Explicit import validation and source-row accounting

The offline importer SHALL validate source structure and canonical output separately from
normal runtime loading. Every inspected source equipment row SHALL be accounted for as a
canonical imported record or as a structured reported issue; a source row SHALL NOT be
silently discarded.

Fatal structural conditions, including unresolved required worksheet/column mapping,
absence of an approved stable unique `record_id` rule, duplicate normalized authoritative
identifiers, collisions in an approved deterministic `record_id` derivation, invalid
canonical root construction, or duplicate canonical `record_id` values SHALL prevent
publication of a new snapshot. These identity conflicts SHALL NOT be repaired by arbitrary
suffixes, counters, timestamps, or non-authoritative row positions.

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

- **WHEN** a non-empty source IP value cannot be normalized as a valid IPv4 address
- **THEN** that invalid text is not inserted into the runtime IP index
- **AND** the source row is accounted for through the canonical unresolved semantics and import report

### Requirement: Atomic canonical snapshot publication

The offline importer SHALL publish a new production snapshot only after the complete
candidate snapshot has been constructed and validated successfully. A failed import at
any point before complete publication SHALL leave the previously published snapshot
intact and SHALL NOT expose partial candidate output under the production snapshot path.

The concrete atomic-write mechanism is an implementation detail. An implementation MAY
use a temporary file in the target filesystem followed by an atomic replacement operation,
provided the normative preservation and no-partial-publication behavior is satisfied.

#### Scenario: Fatal source mapping is unresolved

- **GIVEN** a previously valid production snapshot exists
- **WHEN** the importer cannot resolve a required authoritative source column
- **THEN** it reports a fatal import condition
- **AND** the previously published snapshot remains intact
- **AND** no partial new snapshot is exposed under the production snapshot path

#### Scenario: Publication fails after candidate generation begins

- **GIVEN** a previously valid production snapshot exists
- **WHEN** importer processing fails before the new complete validated snapshot is published
- **THEN** the previous snapshot remains the production snapshot
- **AND** partial candidate content is not visible at the production snapshot path

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
- **THEN** IP lookup returns every matching record in deterministic canonical record order
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
is absent unless the inspected source contract explicitly defines that mapping before
canonicalization.

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
revision identified by its deterministic non-secret `snapshot_id`. Runtime consumers
SHALL NOT mutate canonical records or indexes in place.

Replacing inventory data SHALL create and validate a new inventory instance before it is
published by a future application composition boundary. This change does not require
automatic file watching, runtime hot reload, or GUI reload controls.

#### Scenario: Loaded records are queried

- **WHEN** runtime consumers perform inventory lookups
- **THEN** the loaded snapshot records and indexes remain unchanged by those queries

#### Scenario: Equivalent snapshot is loaded later

- **WHEN** a future composition path loads another valid snapshot with identical canonical identity content
- **THEN** the new inventory instance has the same `snapshot_id`
- **AND** identity equality means the canonical inventory revision is unchanged even if generation metadata differs

#### Scenario: Changed snapshot is loaded later

- **WHEN** a future composition path replaces the current inventory with newly validated changed canonical content
- **THEN** the replacement carries the deterministic `snapshot_id` derived from the new canonical content
- **AND** the old inventory instance is not mutated into the new revision

### Requirement: Production inventory data isolation

Real organization equipment workbooks and generated production inventory snapshots
SHALL be treated as deployment-local operational data and SHALL NOT be committed to the
public or shared repository by the implementation of this capability.

The default `equipment_inventory.local.json` production snapshot SHALL be ignored by
Git. Tests SHALL use synthetic fixtures that contain no real organization IP addresses,
room identities, equipment identifiers, or other operational inventory data. A tracked
example snapshot MAY exist only when all values are synthetic.

Runtime and importer logs/errors SHALL NOT emit the complete inventory or complete source
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
