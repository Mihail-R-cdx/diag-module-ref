# equipment-inventory-snapshot Specification

## Purpose
TBD - created by archiving change equipment-inventory-snapshot. Update Purpose after archive.
## Requirements
### Requirement: Offline equipment inventory conversion boundary

The application SHALL treat the organization equipment workbook as an external import
source rather than as a normal runtime storage format. A dedicated offline importer SHALL
convert the inspected workbook into a canonical equipment-inventory snapshot before the
diagnostic application consumes the data.

Normal diagnostic application runtime modules SHALL NOT parse `.xlsx` workbooks and
SHALL NOT require a spreadsheet parsing dependency to start, load a canonical inventory
snapshot, perform inventory queries, or execute existing device diagnostics. An
import-only dependency such as `openpyxl` MAY be used by the offline importer provided
that the runtime inventory path does not import or require it.

The confirmed organization source mapping defined by this capability SHALL be implemented
explicitly. Source-only fields and consistency evidence SHALL remain inside the importer
boundary unless the canonical schema explicitly includes them.

#### Scenario: Runtime loads inventory without Excel support

- **GIVEN** a valid canonical equipment inventory snapshot exists
- **AND** the spreadsheet import dependency is unavailable
- **WHEN** the diagnostic runtime imports and loads the equipment inventory
- **THEN** the inventory loads through the canonical snapshot path
- **AND** no `.xlsx` parser is imported or required

### Requirement: Confirmed organization source-to-canonical mapping

For the inspected organization workbook, the importer SHALL use this authoritative
schema-v1 mapping:

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

`diagnostic_model` SHALL be populated only through a separate explicit reviewed mapping to
application-supported diagnostic model names. The importer SHALL NOT guess a supported
`diagnostic_model` from approximate or similar-looking text.

The source columns `Производитель` and `Модель` MAY be used as evidence for explicit
`diagnostic_model` mapping and importer-side consistency diagnostics, but schema v1 SHALL
NOT require them as separate canonical fields.

The source column `SmartRoomID контроллера` MAY be used only as importer-side consistency
evidence for this capability. It SHALL NOT create `controller_record_id` or another
controller relation in schema v1 and SHALL NOT create a runtime controller index.

#### Scenario: Confirmed source row is mapped

- **WHEN** the importer reads a source equipment row using the confirmed organization source contract
- **THEN** each available mapped source value is normalized into its corresponding canonical field
- **AND** source-only evidence fields are not copied into schema v1 unless explicitly approved by the schema

### Requirement: Canonical inventory snapshot schema v1

The first runtime storage adapter SHALL consume a UTF-8 JSON document whose root is a JSON
object with these required fields:

- `schema_version`: JSON integer exactly `1`;
- `snapshot_id`: non-empty JSON string satisfying the deterministic snapshot identity contract;
- `records`: JSON array of canonical equipment record objects.

The initially approved optional root generation metadata is:

- `generated_at`: RFC 3339 UTC timestamp string;
- `source_row_count`: non-negative JSON integer.

Generation metadata SHALL NOT affect runtime lookup semantics or `snapshot_id` identity.

Each schema-v1 equipment record SHALL contain exactly these runtime fields:

- `record_id`: non-empty JSON string, unique within the snapshot after canonical normalization;
- `source_model`: normalized JSON string or null;
- `diagnostic_model`: exact supported application model JSON string or null;
- `ip_address`: canonical IPv4 JSON string or null;
- `mac_address`: canonical MAC-address JSON string or null;
- `serial_number`: normalized JSON string or null;
- `room_id`: non-empty normalized JSON string or null;
- `room_name`: non-empty normalized JSON string or null;
- `device_kind`: JSON string containing exactly one schema-v1 canonical vocabulary value.

The required non-null record fields are exactly:

```text
record_id
device_kind
```

The nullable record fields are exactly:

```text
source_model
diagnostic_model
ip_address
mac_address
serial_number
room_id
room_name
```

Canonical textual normalization SHALL use NFC Unicode normalization and trim leading and
trailing whitespace. Empty normalized nullable text SHALL become null. Canonical
normalization SHALL preserve case and internal text unless a separately reviewed mapping
defines stronger normalization for an authoritative identifier.

`ip_address`, when present, SHALL be normalized dotted-decimal IPv4 text. Invalid non-empty
source IP data SHALL become canonical null plus a structured non-fatal issue when the rest
of the canonical record can be represented safely.

`mac_address`, when present, SHALL be lowercase colon-separated 48-bit MAC text in this
form:

```text
aa:bb:cc:dd:ee:ff
```

Valid common textual representations MAY be normalized to that form. Invalid non-empty
source MAC data SHALL become canonical null plus a structured non-fatal issue when the
record can otherwise be represented safely.

A canonical snapshot SHALL contain only fields approved for runtime use. The importer
SHALL NOT copy every workbook column into canonical records by default.

#### Scenario: Nullable source data is incomplete

- **GIVEN** a source row has a valid `SmartRoomID` and can produce a valid canonical `device_kind`
- **WHEN** one or more nullable source fields are absent or invalid
- **THEN** the importer retains the canonical record when it can be represented safely
- **AND** unresolved nullable fields are null
- **AND** the row is not silently dropped solely because optional data is incomplete

### Requirement: SmartRoomID is the authoritative record identity

For the confirmed organization workbook, `SmartRoomID` SHALL be the authoritative source
identity for schema-v1 `record_id`.

The importer SHALL normalize the source `SmartRoomID` under the canonical identifier rules
and SHALL use that value directly as `record_id`. `SmartRoomID` is confirmed to identify a
specific equipment database record and to remain stable across ordinary edits to IP,
room, model, MAC address, serial number, and other mutable attributes.

This source contract SHALL NOT define or use a fallback `record_id`. A missing, blank after
normalization, or duplicate canonical `SmartRoomID` SHALL be a fatal source-contract
violation. The importer SHALL NOT recover identity from row number, IP address, MAC
address, serial number, room fields, model text, UUID, timestamp, counter, suffix, or
another mutable or invented value.

A fatal `SmartRoomID` identity violation SHALL block publication of the complete candidate
snapshot. The importer SHALL NOT select one duplicate row, silently deduplicate records, or
append a suffix to manufacture uniqueness.

#### Scenario: SmartRoomID becomes record_id

- **WHEN** a source equipment row has a usable `SmartRoomID`
- **THEN** its canonical normalized value is used as `record_id`
- **AND** changing mutable equipment attributes does not require changing that `record_id`

#### Scenario: SmartRoomID is missing

- **WHEN** a source equipment row has no usable `SmartRoomID`
- **THEN** the importer reports a structured fatal source-contract issue
- **AND** it generates no fallback `record_id`
- **AND** the new snapshot is not published

#### Scenario: SmartRoomID is duplicated

- **WHEN** two source equipment rows have the same canonical normalized `SmartRoomID`
- **THEN** the importer reports a structured fatal identity conflict
- **AND** it does not choose one row, append a suffix, or use row position as a disambiguator
- **AND** the new snapshot is not published

### Requirement: ID комнаты is authoritative room identity

For the confirmed organization workbook, `ID комнаты` SHALL map to canonical `room_id` and
SHALL remain the authoritative room identity. `Название комнаты` SHALL map to canonical
`room_name` as a display attribute.

The importer SHALL NOT automatically substitute `room_name` for missing `room_id`, SHALL
NOT merge rooms because they have the same display name, and SHALL NOT silently choose one
room name as authoritative when records sharing one `room_id` contain conflicting names.

Missing or blank `ID комнаты` SHALL produce `room_id = null` and MAY produce an observable
data-quality or consistency issue. It SHALL NOT by itself make an otherwise representable
canonical record fatal.

#### Scenario: Devices share one authoritative room ID

- **WHEN** multiple records have the same canonical `ID комнаты`
- **THEN** they have the same canonical `room_id`
- **AND** the room index returns all of them under that one `room_id`

#### Scenario: One room ID has conflicting room names

- **WHEN** records with the same canonical `room_id` contain different non-null `room_name` values
- **THEN** all canonical records are preserved
- **AND** no room name is silently selected as authoritative
- **AND** a structured non-fatal consistency issue makes the conflict observable

#### Scenario: One room name is reused by different room IDs

- **WHEN** the same canonical `room_name` appears under different non-null `room_id` values
- **THEN** the importer preserves the distinct authoritative room IDs
- **AND** it does not merge the rooms by display name

#### Scenario: Room name exists without room ID

- **WHEN** `Название комнаты` is present but `ID комнаты` is absent
- **THEN** canonical `room_name` is retained
- **AND** canonical `room_id` is null
- **AND** the importer does not invent room identity from the display name

### Requirement: Наименование is the authoritative source_model value

For the confirmed organization workbook, `Наименование` SHALL map directly to canonical
`source_model` after canonical text normalization. If `Наименование` is absent or blank,
`source_model` SHALL be null.

When `Наименование` is present, the importer SHALL NOT silently reconstruct or overwrite
`source_model` from `Производитель` plus `Модель`. Those separate source columns MAY be
used for consistency diagnostics and explicit reviewed `diagnostic_model` mapping.

A mismatch between `Наименование`, `Производитель`, and `Модель` SHALL NOT by itself block
snapshot publication or rewrite canonical `source_model`.

#### Scenario: Source model evidence disagrees

- **WHEN** normalized `Наименование` does not match an expected manufacturer/model combination derived for consistency checking
- **THEN** canonical `source_model` remains the normalized `Наименование` value
- **AND** the importer may report a structured non-fatal consistency issue
- **AND** it does not silently rewrite the source value

### Requirement: Device kind uses exact authoritative source type mapping

Schema-v1 `device_kind` SHALL use the closed vocabulary:

```text
pdu
video_codec
other
```

For the confirmed organization workbook, the importer SHALL map exact normalized source
`Тип модели` values as follows:

```text
Video Conference -> video_codec
БРП              -> pdu
any other value   -> other
```

The importer SHALL NOT use substring matching, fuzzy matching, model-name guessing,
manufacturer guessing, or recognized diagnostic-model evidence to silently override the
result of this exact source-type mapping.

A known supported model whose source `Тип модели` maps to an unexpected `device_kind` MAY
produce a structured consistency issue such as a known-model/type mismatch. Recognition of
a model SHALL NOT grant authority to change `device_kind`.

#### Scenario: Video Conference type is mapped

- **WHEN** normalized `Тип модели` is exactly `Video Conference`
- **THEN** canonical `device_kind` is exactly `video_codec`

#### Scenario: БРП type is mapped

- **WHEN** normalized `Тип модели` is exactly `БРП`
- **THEN** canonical `device_kind` is exactly `pdu`

#### Scenario: Other type value is mapped safely

- **WHEN** normalized `Тип модели` is any value other than the two explicitly mapped values, including an unknown or new value
- **THEN** canonical `device_kind` is exactly `other`
- **AND** the importer does not guess a more specific kind from other text

#### Scenario: Known model conflicts with source type

- **WHEN** source evidence identifies a model known to the diagnostic application but exact `Тип модели` mapping produces an unexpected `device_kind`
- **THEN** the exact source-type mapping remains the canonical `device_kind`
- **AND** the importer may report a structured non-fatal consistency issue
- **AND** it does not silently override `device_kind`

### Requirement: Structured importer diagnostics and source-row accounting

Every inspected source equipment row SHALL be accounted for as either a canonical record or
a structured issue. A source row SHALL NOT disappear silently.

Importer diagnostics SHALL distinguish at least these semantic classes:

```text
fatal source-contract issue
non-fatal invalid-field/data-quality issue
cross-row or source-consistency issue
```

The concrete Python exception hierarchy and exact implementation type names are not part of
this architecture contract. Each diagnostic SHALL nevertheless expose a machine-readable
issue category/code, its semantic class, and only the minimum safe row or record reference
needed to investigate the problem.

Normal diagnostics SHALL NOT dump complete source rows, complete canonical records when not
needed, or the complete organization inventory. A row reference and `record_id` MAY be used
when safe and available.

Fatal source-contract issues SHALL include at least missing/blank `SmartRoomID`, duplicate
canonical `SmartRoomID`, unresolved required source structure needed to perform the
confirmed mapping, and failure to construct a complete valid candidate snapshot.

Non-fatal invalid-field/data-quality issues MAY include invalid IP or MAC text, missing room
identity, missing optional values, duplicate IP/MAC/serial values, and unsupported or
unmapped `diagnostic_model`, provided the canonical record can still be represented safely.

Consistency issues MAY include conflicting room names for one room ID, one room name reused
across different room IDs, mismatch between `Наименование` and manufacturer/model evidence,
known diagnostic model versus unexpected source type, multiple relevant device kinds in one
room, and controller-reference inconsistencies.

Consistency evidence SHALL NOT grant authority to delete records, rewrite authoritative
source mappings, guess missing values, change `record_id`, change `device_kind`, merge rooms,
or select a first match.

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

### Requirement: Controller source evidence remains importer-side only

`SmartRoomID контроллера` MAY be inspected as non-fatal consistency evidence. Examples of
observable inconsistencies include:

- records sharing one `room_id` referring to different controller IDs;
- a controller reference missing from only some records in a room;
- a referenced controller ID matching no source equipment `SmartRoomID`;
- one room indirectly containing multiple distinct controller references.

Such conditions SHALL NOT automatically alter canonical records or block the complete
snapshot when the primary canonical mapping remains valid. This capability SHALL NOT add a
controller relation field or controller index to runtime schema v1 solely to perform these
checks.

#### Scenario: Controller references are inconsistent

- **WHEN** importer-side `SmartRoomID контроллера` evidence is inconsistent for an otherwise valid room inventory
- **THEN** the importer may report a structured non-fatal consistency issue
- **AND** canonical records remain based on the primary source mapping
- **AND** schema v1 gains no controller relation field or runtime controller index

### Requirement: Multiplicity and ambiguity are preserved

Source and canonical multiplicity SHALL remain observable. Operational expectations such as
one PDU, one video codec, or one controller per room SHALL NOT be treated as strict source
uniqueness guarantees unless a future reviewed contract explicitly makes them so.

Duplicate IP, MAC, or serial-number values SHALL NOT cause record deletion, record
coalescing, or first-match selection. Multiple `pdu` or multiple `video_codec` records in one
room SHALL remain multiple records.

#### Scenario: Multiple PDU exist in one room

- **WHEN** a room/device-kind lookup for `pdu` matches multiple records
- **THEN** every matching record is returned in deterministic canonical order
- **AND** the inventory layer does not choose a primary PDU

#### Scenario: Multiple video codecs exist in one room

- **WHEN** a room/device-kind lookup for `video_codec` matches multiple records
- **THEN** every matching record is returned in deterministic canonical order
- **AND** the inventory layer does not apply `records[0]` or another implicit primary-codec rule

#### Scenario: Physical identifiers are duplicated

- **WHEN** multiple otherwise valid records share the same canonical IP, MAC, or serial number
- **THEN** all records are preserved
- **AND** relevant duplication remains observable through query multiplicity and/or importer diagnostics

### Requirement: Deterministic canonical snapshot identity

Schema-v1 `snapshot_id` SHALL identify canonical inventory content, not one execution of the
importer. Canonical records SHALL be published in deterministic ascending normalized
`record_id` order using Unicode code-point ordering.

Schema v1 SHALL use this representation:

```text
snapshot_id = "sha256:" + lowercase_sha256_hex(canonical_identity_payload)
```

The identity payload SHALL contain exactly `schema_version` and canonical `records`. It
SHALL use integer schema version `1`, deterministic canonical record order,
lexicographically sorted JSON object keys, compact JSON separators with no insignificant
whitespace, and direct UTF-8 encoding of normalized Unicode text.

Optional generation metadata such as `generated_at` and `source_row_count` SHALL be
excluded from the identity payload. Canonical fields including `mac_address` and
`serial_number` SHALL remain part of `records` and therefore participate in revision
identity.

The runtime loader SHALL independently recompute the expected `snapshot_id` from the
actually loaded and validated canonical content using the same normative algorithm before
publishing an `EquipmentInventory`. A declared/recomputed mismatch SHALL fail as
`INVALID_SNAPSHOT` with no partial publication.

#### Scenario: Equivalent canonical content is imported again

- **WHEN** two imports produce identical normalized canonical records
- **THEN** they produce identical canonical record order
- **AND** they produce the same `snapshot_id`
- **AND** differing generation metadata does not change revision identity

#### Scenario: Declared snapshot identity does not match content

- **GIVEN** a schema-v1 snapshot has otherwise valid canonical content
- **AND** its declared `snapshot_id` is syntactically valid but differs from the recomputed content digest
- **WHEN** the runtime loader validates the snapshot
- **THEN** loading fails with category `INVALID_SNAPSHOT`
- **AND** no inventory, partial records, or partial indexes are published

### Requirement: Atomic canonical snapshot publication

The offline importer SHALL publish a new production snapshot only after the complete
candidate snapshot has been constructed and validated successfully. Any fatal import
failure before publication SHALL leave the previously published production snapshot intact
and SHALL NOT expose partial candidate output under the production snapshot path.

The concrete atomic-write mechanism is an implementation detail.

#### Scenario: Fatal identity failure occurs

- **GIVEN** a previously valid production snapshot exists
- **WHEN** the current import contains missing or duplicate authoritative `SmartRoomID`
- **THEN** the importer does not publish the candidate snapshot
- **AND** the previously published snapshot remains intact
- **AND** no partial candidate is exposed at the production snapshot path

### Requirement: Structured runtime inventory load failure contract

The runtime inventory loader SHALL expose safe structured load failures through a
machine-readable category and a non-secret human-readable message. Every failed load SHALL
classify as exactly one of:

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
- `UNSUPPORTED_SCHEMA`: the JSON root declares a `schema_version` other than integer `1`;
- `INVALID_SNAPSHOT`: canonical shape/content is invalid, required fields are invalid, record IDs collide, or declared `snapshot_id` does not match recomputed canonical content.

No failed load SHALL publish a partial `EquipmentInventory`, partial records, or partial
indexes. Runtime consumers SHALL NOT need to inspect raw storage-specific exception types
or strings to understand inventory availability.

#### Scenario: Snapshot schema version is unsupported

- **WHEN** the runtime loader receives a JSON object whose `schema_version` is not integer `1`
- **THEN** loading fails with category `UNSUPPORTED_SCHEMA`
- **AND** no inventory is published

### Requirement: Storage-independent equipment inventory runtime boundary

Runtime consumers SHALL access equipment data through a focused `EquipmentInventory`
boundary rather than reading JSON structures directly. The first loader SHALL use Python
standard-library JSON support, but public inventory query semantics SHALL NOT depend on JSON
serialization details.

A successfully loaded inventory SHALL build immutable indexes equivalent to:

```text
ip_address -> tuple[EquipmentRecord, ...]
room_id -> tuple[EquipmentRecord, ...]
(room_id, device_kind) -> tuple[EquipmentRecord, ...]
```

The public query surface SHALL provide operations equivalent to:

```text
find_by_ip(ip_address)
find_room_equipment(room_id)
find_by_room_and_kind(room_id, device_kind)
```

Normal lookups SHALL use the prebuilt indexes rather than repeatedly scan all records.
Index values SHALL preserve all matches and deterministic canonical order.

Every normal inventory query SHALL return a result collection containing zero or more
canonical records. A valid lookup with no match SHALL return an empty result collection:

```text
no IP match               -> empty result collection
no room match             -> empty result collection
no room/device-kind match -> empty result collection
```

An ordinary zero-match SHALL NOT return `None`, raise a device-connection-style error, or
produce an inventory-layer resolution status. The inventory layer SHALL preserve zero,
one, or many result semantics only. Interpretation of those result counts as
`NOT_FOUND`, `RESOLVED`, or `AMBIGUOUS` belongs to the later application/composition
orchestration and SHALL NOT be embedded in `EquipmentInventory`.

Schema v1 SHALL expose `mac_address` and `serial_number` only as canonical record
attributes. It SHALL NOT require indexes for MAC address, serial number, room name, or
`SmartRoomID контроллера` without a future reviewed runtime requirement.

The default deployment snapshot path SHALL be `equipment_inventory.local.json`, resolved
deterministically from the application/project root rather than the process current working
directory. Explicit callers and tests MAY provide another path.

#### Scenario: IP lookup has no match

- **WHEN** `find_by_ip` receives a valid normalized IP address that is absent from the inventory
- **THEN** it returns an empty result collection
- **AND** it does not return `None`, raise a connection-style error, or synthesize `NOT_FOUND`

#### Scenario: Room lookup has no match

- **WHEN** `find_room_equipment` receives a canonical `room_id` with no indexed records
- **THEN** it returns an empty result collection
- **AND** it does not invent room data from `room_name`

#### Scenario: Room and device-kind lookup has no match

- **WHEN** `find_by_room_and_kind` receives a canonical room/device-kind pair with no indexed records
- **THEN** it returns an empty result collection
- **AND** the inventory layer does not classify the result as `NOT_FOUND`

#### Scenario: Devices in one room are queried

- **WHEN** an application consumer queries one canonical `room_id`
- **THEN** the inventory returns all records indexed under that authoritative room ID
- **AND** it does not merge records from a different `room_id` merely because `room_name` matches

#### Scenario: Query result multiplicity is interpreted by application orchestration

- **WHEN** an inventory lookup returns zero, one, or multiple records
- **THEN** `EquipmentInventory` returns that result collection without assigning `NOT_FOUND`, `RESOLVED`, or `AMBIGUOUS`
- **AND** any such resolution state is determined only by later application/composition orchestration

### Requirement: Immutable snapshot revision identity

Each loaded `EquipmentInventory` SHALL represent one immutable validated snapshot revision.
Runtime consumers SHALL NOT mutate canonical records or indexes in place.

Replacing inventory data SHALL require constructing and validating a new inventory instance
before a future application composition boundary publishes it. This capability does not add
automatic file watching, hot reload, GUI controls, PDU orchestration, or codec lifecycle.

#### Scenario: Inventory records are queried

- **WHEN** runtime consumers perform inventory lookups
- **THEN** the loaded snapshot records, metadata, and indexes remain unchanged by those queries

### Requirement: Production inventory data isolation

Real organization workbooks and generated production inventory snapshots SHALL be treated
as deployment-local operational data and SHALL NOT be committed by implementation of this
capability.

The default `equipment_inventory.local.json` production snapshot SHALL be ignored by Git.
Tests SHALL use synthetic fixtures containing no real organization IP addresses, room
identities, equipment IDs, controller references, or other operational inventory data.

Runtime and importer diagnostics SHALL NOT emit the complete inventory or complete source
rows. Repository code MAY contain canonical schema definitions, importer normalization and
mapping logic, synthetic fixtures, and documentation needed to reproduce the import.

#### Scenario: Inventory tests require example data

- **WHEN** automated tests exercise inventory loading, mapping, indexing, ambiguity, or importer diagnostics
- **THEN** they use synthetic source and canonical inventory values
- **AND** no real organization inventory is required

### Requirement: Schema v2 carries explicit room VIP state

Newly generated canonical equipment inventory snapshots SHALL use `schema_version` exactly `2` and every schema-v2 equipment record SHALL contain exactly one additional field:

```text
room_vip
```

`room_vip` SHALL be a JSON boolean or JSON null. `true` means the source explicitly identifies the authoritative room as VIP, `false` means the source explicitly identifies it as non-VIP, and null means the source value is absent, unsupported, or unresolved.

The deterministic schema-v2 snapshot identity SHALL include `room_vip` for every record. Generation metadata SHALL remain outside snapshot identity.

#### Scenario: VIP room is published

- **WHEN** a source row contains an explicitly supported VIP value
- **THEN** the schema-v2 record contains the corresponding JSON boolean
- **AND** the boolean participates in deterministic snapshot identity

#### Scenario: VIP value is unavailable

- **WHEN** the source VIP value is blank or cannot be represented under the approved mapping
- **THEN** the canonical `room_vip` value is null
- **AND** unsupported non-blank source data produces a structured non-fatal issue

### Requirement: Existing schema-v1 snapshots remain loadable

The runtime inventory loader SHALL continue to accept valid schema-v1 snapshots. A loaded schema-v1 record SHALL expose `room_vip = null` to runtime consumers without rewriting the source file or bypassing schema-v1 snapshot identity verification.

The loader SHALL strictly validate each supported schema version against its own approved exact record fields and identity payload. It SHALL NOT accept an undeclared hybrid record containing schema-v2 fields while claiming schema version 1.

#### Scenario: Existing deployment snapshot is loaded

- **GIVEN** a valid schema-v1 snapshot created before this change
- **WHEN** the runtime loader loads it
- **THEN** the inventory is available
- **AND** every runtime record exposes unknown VIP state

#### Scenario: Hybrid snapshot is rejected

- **WHEN** a snapshot claims schema version 1 but contains `room_vip`
- **THEN** loading fails as an invalid snapshot
- **AND** no partial inventory is published

### Requirement: VIP source mapping is explicit and closed

For the confirmed deployment workbook, the exact source column `VIP оборудование` SHALL map to canonical `room_vip`.

The importer SHALL normalize only these semantic values:

```text
Excel boolean true                  -> true
Excel boolean false                 -> false
"истина"                            -> true
"ложь"                              -> false
blank                               -> null
```

Text comparison SHALL apply Unicode normalization, trim leading and trailing whitespace, and perform case-insensitive exact comparison. The confirmed workbook values are `ИСТИНА`, `ЛОЖЬ`, and blank. No other textual or numeric aliases are approved by this contract.

Any other non-blank value SHALL become null plus a structured `INVALID_ROOM_VIP` non-fatal issue. Substring, fuzzy, approximate, or locale-guessing interpretation is forbidden.

#### Scenario: Confirmed true textual VIP value is normalized

- **WHEN** the source `VIP оборудование` cell contains `ИСТИНА` with arbitrary surrounding whitespace or case
- **THEN** canonical `room_vip` is true

#### Scenario: Confirmed false textual VIP value is normalized

- **WHEN** the source `VIP оборудование` cell contains `ЛОЖЬ` with arbitrary surrounding whitespace or case
- **THEN** canonical `room_vip` is false

#### Scenario: Unsupported VIP value is preserved as unknown

- **WHEN** the source `VIP оборудование` cell contains a non-blank value outside the closed mapping
- **THEN** canonical `room_vip` is null
- **AND** the importer reports `INVALID_ROOM_VIP`
- **AND** the row is not silently dropped solely for this condition

### Requirement: Room VIP evidence uses normative room-wide aggregation

The importer and runtime room-context layer SHALL preserve equipment-record multiplicity and SHALL evaluate VIP evidence across all records sharing one non-null authoritative `room_id`. Null means absence of authoritative VIP evidence for that record. Null SHALL NOT conflict with a consistent known boolean.

The normative aggregation table is:

```text
no room records                         -> unresolved room
all room_vip values null                -> NO_DATA
one or more true, all others null/true  -> VIP_TRUE
one or more false, all others null/false-> VIP_FALSE
at least one true and at least one false-> CONFLICT
```

The importer SHALL report structured non-fatal `ROOM_VIP_CONFLICT` only when both true and false occur under the same authoritative `room_id`. It SHALL NOT report a conflict for `true + null`, `false + null`, repeated equal booleans, or all-null evidence.

Runtime room-context resolution SHALL apply the same table exactly. It SHALL expose `ДА` for `VIP_TRUE`, `НЕТ` for `VIP_FALSE`, `НЕТ ДАННЫХ` for `NO_DATA`, `КОНФЛИКТ ДАННЫХ` for `CONFLICT`, and unresolved room state when no records exist for the authoritative room lookup. It SHALL NOT select the first record or apply device-kind preference.

#### Scenario: All room VIP evidence is absent

- **WHEN** all records sharing one authoritative `room_id` contain `room_vip = null`
- **THEN** runtime VIP presentation is `НЕТ ДАННЫХ`
- **AND** no conflict is reported

#### Scenario: Known VIP evidence is mixed with null

- **WHEN** records sharing one authoritative `room_id` contain one or more true values and all remaining values are true or null
- **THEN** runtime VIP presentation is `ДА`
- **AND** null does not weaken or conflict with the known consistent value

#### Scenario: Known non-VIP evidence is mixed with null

- **WHEN** records sharing one authoritative `room_id` contain one or more false values and all remaining values are false or null
- **THEN** runtime VIP presentation is `НЕТ`
- **AND** null does not weaken or conflict with the known consistent value

#### Scenario: One room contains conflicting VIP flags

- **WHEN** records sharing one authoritative `room_id` contain at least one true and at least one false VIP value
- **THEN** all otherwise valid records remain in the snapshot
- **AND** the importer reports `ROOM_VIP_CONFLICT`
- **AND** runtime presentation is `КОНФЛИКТ ДАННЫХ`
- **AND** runtime does not claim either VIP or non-VIP authority

### Requirement: Converter paths use repository-safe absolute configuration

The offline converter SHALL expose execution-time configuration variables named `SOURCE_XLSX_PATH` and `OUTPUT_JSON_PATH`. Each configured value SHALL be a resolved absolute `Path` before workbook reading or snapshot publication begins.

Path resolution priority SHALL be:

```text
explicit command-line override
environment variable
repository-safe default where approved
configuration failure
```

The supported environment variables SHALL be `DIAG_INVENTORY_XLSX` and `DIAG_INVENTORY_JSON`. The JSON output MAY default to the repository-local deployment snapshot path. No user-specific source workbook path SHALL be committed as a default.

The direct import API SHALL continue to accept explicit source and output paths for tests and automation. A source-path configuration failure SHALL occur before candidate publication and SHALL leave any previous valid output intact.

#### Scenario: Environment paths are resolved

- **GIVEN** relative or user-expanded path text is supplied through the supported environment variables
- **WHEN** converter configuration is initialized
- **THEN** `SOURCE_XLSX_PATH` and `OUTPUT_JSON_PATH` contain absolute resolved `Path` values

#### Scenario: Source path is not configured

- **GIVEN** no CLI source override, no source environment variable, and no approved repository-safe source default
- **WHEN** the converter starts
- **THEN** it exits with a clear safe configuration error
- **AND** it does not modify the existing JSON snapshot
