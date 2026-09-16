# equipment-inventory-snapshot Specification

## Purpose
TBD - created by archiving change equipment-inventory-snapshot. Update Purpose after archive.
## Requirements
### Requirement: Offline equipment inventory conversion boundary

The application SHALL treat organization equipment workbooks and optional approved enrichment workbooks as external import sources rather than normal runtime storage formats. A dedicated offline importer SHALL convert the inspected primary equipment workbook, and when explicitly configured the inspected network-connection workbook, into one canonical equipment-inventory snapshot before the diagnostic application consumes the data.

Normal diagnostic application runtime modules SHALL NOT parse `.xlsx` workbooks and SHALL NOT require a spreadsheet parsing dependency to start, load a canonical inventory snapshot, perform inventory queries, or execute existing device diagnostics. An import-only dependency such as `openpyxl` MAY be used by the offline importer provided that the runtime inventory path does not import or require it.

The confirmed primary organization source mapping and the confirmed network-enrichment source mapping defined by this capability SHALL be implemented explicitly. Source-only fields and consistency evidence SHALL remain inside the importer boundary unless the canonical schema explicitly includes them.

Every newly successful conversion SHALL publish schema version 4. A one-source conversion with no network workbook configured SHALL remain an intentional supported mode and SHALL publish schema v4 with null switch fields. A conversion with an explicitly configured valid network workbook SHALL also publish schema v4 and SHALL populate switch fields only through the approved reconciliation contract. If a network workbook is explicitly configured but its path/configuration is invalid, the workbook is unreadable, worksheet `Устройства` is missing or ambiguous, or a required network header is missing or ambiguous, the importer SHALL fail before publication and SHALL NOT silently reinterpret the run as primary-only conversion.

Row-level network data-quality, duplication, unmatched-MAC, and ambiguity outcomes SHALL remain non-fatal when the primary candidate can still be represented. They SHALL preserve otherwise valid primary records and SHALL NOT change the requested import mode.

For archive applicability, the two inherited conversion scenario headings below remain
stable identifiers. Their normative GIVEN/WHEN/THEN outcomes are updated to the
schema-v4 contract in this replacement requirement; no current conversion publishes
schema v2 or schema v3.

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
- **THEN** it publishes a schema-v4 snapshot
- **AND** every record contains null `switch_ip_address` and null `switch_port`

#### Scenario: Explicit two-source conversion publishes schema v3

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

For the confirmed organization workbook, `ID комнаты` SHALL map to canonical `room_id` and SHALL remain the authoritative room identity. `Название комнаты` SHALL map to canonical `room_name` as a display attribute. Schema v4 additionally carries `room_address` and the existing `room_vip` as per-record display metadata; none of those display fields SHALL identify or merge rooms.

The importer SHALL NOT automatically substitute `room_name`, `room_address`, or `room_vip` for missing `room_id` and SHALL NOT merge rooms because display metadata matches. Records sharing one non-null `room_id` SHALL remain members of that authoritative room even when their non-null display metadata differs.

For current schema-v4 import, the importer SHALL preserve normalized per-record room display metadata without cross-record reconciliation. Different `room_name`, `room_address`, or `room_vip` values under the same `room_id` SHALL NOT by themselves produce a room-display conflict issue, SHALL NOT cause record deletion, and SHALL NOT cause the importer to select or rewrite a room-wide display value.

Missing or blank `ID комнаты` SHALL produce `room_id = null` and MAY produce an observable data-quality or consistency issue. It SHALL NOT by itself make an otherwise representable canonical record fatal.

For archive applicability, the inherited differing-room-name scenario heading below
remains a stable identifier. Its normative outcome is updated to the current
per-record display-metadata contract.

#### Scenario: Devices share one authoritative room ID

- **WHEN** multiple records have the same canonical `ID комнаты`
- **THEN** they have the same canonical `room_id`
- **AND** the room index returns all of them under that one `room_id`

#### Scenario: One room ID has conflicting room names

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

### Requirement: Device kind uses exact authoritative source type mapping

Schema-v1 `device_kind` SHALL use the closed vocabulary:

```text
pdu
video_codec
other
```

For the confirmed organization workbook, the importer SHALL map exact normalized source `Тип модели` values as follows:

```text
Video Conference -> video_codec
БРП              -> pdu
any other value  -> other
```

The importer SHALL NOT use substring matching, fuzzy matching, model-name guessing, manufacturer guessing, recognized diagnostic-model evidence, GUI page registration, or runtime diagnostic routing to silently override the result of this exact source-type mapping.

A known supported model whose source `Тип модели` maps to an unexpected `device_kind` MAY produce the structured non-fatal consistency issue `KNOWN_MODEL_TYPE_MISMATCH`. The expected-kind registry used by that diagnostic is importer-only consistency evidence. It SHALL NOT grant authority to change `device_kind`, suppress an exact recognized `diagnostic_model`, choose a runtime page/controller, or alter canonical schema.

For the currently reviewed diagnostic models, the importer-side consistency expectations SHALL be:

```text
Huawei TE50          -> video_codec
Aten PE8208AV        -> other
Extron IPL T PCS4i   -> other
```

These expected values reflect the authoritative source-type contract for the reviewed organization rows. Runtime PDU or codec dispatch is independently authorized by exact canonical `diagnostic_model`; it SHALL NOT require an expected `device_kind` result.

#### Scenario: Video Conference type is mapped

- **WHEN** normalized `Тип модели` is exactly `Video Conference`
- **THEN** canonical `device_kind` is exactly `video_codec`

#### Scenario: БРП type is mapped

- **WHEN** normalized `Тип модели` is exactly `БРП`
- **THEN** canonical `device_kind` is exactly `pdu`

#### Scenario: Other type value is mapped safely

- **WHEN** normalized `Тип модели` is any value other than the two explicitly mapped values, including an unknown or new value
- **THEN** canonical `device_kind` is exactly `other`
- **AND** the importer does not guess a more specific kind from other text, recognized model, or diagnostic page registration

#### Scenario: Huawei TE50 has a video-codec consistency expectation

- **GIVEN** reviewed recognition yields exact `diagnostic_model = Huawei TE50`
- **WHEN** importer consistency diagnostics evaluate the expected-kind registry
- **THEN** the expected kind is exactly `video_codec`
- **AND** exact source `Тип модели` mapping remains the sole authority for canonical `device_kind`
- **AND** a mismatch is non-fatal consistency evidence and does not suppress the recognized diagnostic model

#### Scenario: Correct Aten source type has no known-model mismatch

- **GIVEN** source `Модель` evidence recognizes exact `diagnostic_model = Aten PE8208AV`
- **AND** exact source `Тип модели` mapping produces `device_kind = other`
- **WHEN** importer consistency diagnostics are evaluated
- **THEN** no `KNOWN_MODEL_TYPE_MISMATCH` is emitted for that record
- **AND** `device_kind` remains `other`

#### Scenario: Correct PCS4i source type has no known-model mismatch

- **GIVEN** source `Модель` evidence recognizes exact `diagnostic_model = Extron IPL T PCS4i`
- **AND** exact source `Тип модели` mapping produces `device_kind = other`
- **WHEN** importer consistency diagnostics are evaluated
- **THEN** no `KNOWN_MODEL_TYPE_MISMATCH` is emitted for that record
- **AND** `device_kind` remains `other`

#### Scenario: Known model conflicts with source type

- **GIVEN** source `Модель` evidence recognizes exact `diagnostic_model = Aten PE8208AV`
- **AND** exact source `Тип модели` mapping produces `device_kind = pdu` or `video_codec`
- **WHEN** importer consistency diagnostics are evaluated
- **THEN** the importer emits non-fatal `KNOWN_MODEL_TYPE_MISMATCH`
- **AND** canonical `device_kind` remains the exact authoritative source-type result
- **AND** canonical `diagnostic_model` remains `Aten PE8208AV`
- **AND** the importer does not silently rewrite either field

#### Scenario: Consistency registry has no runtime dispatch authority

- **WHEN** runtime diagnostics consume a valid canonical record
- **THEN** importer expected-kind evidence is not used to select a page, controller, handler, or fallback model
- **AND** runtime dispatch may use only the exact canonical `diagnostic_model` under the diagnostic-application-shell contract

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

Historical schema-v2 canonical equipment inventory snapshots use `schema_version` exactly `2` and every schema-v2 equipment record contains exactly one field in addition to schema v1:

```text
room_vip
```

`room_vip` SHALL be a JSON boolean or JSON null. `true` means the source explicitly identifies the authoritative room as VIP, `false` means the source explicitly identifies it as non-VIP, and null means the source value is absent, unsupported, or unresolved.

The deterministic schema-v2 snapshot identity SHALL include `room_vip` for every record. Generation metadata SHALL remain outside snapshot identity.

The current importer SHALL no longer publish new schema-v2 snapshots. New successful conversions publish schema v4, while valid historical schema-v2 snapshots remain loadable under their exact original shape and identity contract.

For archive applicability, the inherited VIP scenario headings below remain stable
identifiers. Their normative outcomes describe historical schema-v2 loading; current
conversion continues to publish only schema v4.

#### Scenario: VIP room is published

- **GIVEN** a valid schema-v2 snapshot contains an explicitly supported VIP value
- **WHEN** the runtime loader validates it
- **THEN** the schema-v2 record contains the corresponding JSON boolean
- **AND** the boolean participates in deterministic schema-v2 snapshot identity

#### Scenario: VIP value is unavailable

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

#### Scenario: One room contains conflicting VIP flags

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

### Requirement: Diagnostic model recognition uses deterministic reviewed components

The importer SHALL evaluate source `Модель` and source `Наименование` as two independent approved model-text evidence fields. For each field separately, it SHALL apply Unicode NFC normalization, leading/trailing trim, and Unicode-aware casefold before recognition. A blank normalized value SHALL provide no components.

Recognition SHALL use exact components rather than arbitrary substrings. Non-alphanumeric characters SHALL act as component boundaries. Letter-to-digit and digit-to-letter transitions inside one alphanumeric chunk SHALL expose exact alphabetic and decimal components so compact forms such as `TE40`, `IN1804`, `PE8208`, and `DMP64` are recognized. An immediately adjacent decimal run plus alphabetic suffix SHALL also expose the exact reviewed mixed component needed for `4i` in `PCS4i`.

Component order and repetition SHALL NOT affect rule satisfaction. Space, hyphen, underscore, dot, slash, and other non-alphanumeric separators SHALL be treated as equivalent boundaries. The importer SHALL NOT use transliteration, typo correction, edit distance, token similarity, manufacturer guessing, field-specific aliases, or undeclared aliases.

The same closed reviewed registry SHALL be evaluated independently against each evidence field and SHALL remain exactly:

| Canonical `diagnostic_model` | Mandatory components in either approved evidence field |
| --- | --- |
| `Huawei TE20` | `te` and `20` |
| `Huawei TE40` | `te` and `40` |
| `Huawei TE50` | `te` and `50` |
| `CloudLink Bar 310` | `cloudlink`, `bar`, and `310` |
| `CloudLink Box 310` | `cloudlink`, `box`, and `310` |
| `Polycom RPG 310` | (`rpg` and `310`) or (`realpresence`, `group`, and `310`) |
| `Extron IN1804` | `in` and `1804` |
| `Aten PE8208AV` | `pe` and `8208` |
| `Extron IPL T PCS4i` | `ipl`, `pcs`, and `4i` |
| `Biamp Tesira Forte CI` | `tesira` and (`forte` or `forté`) |
| `Extron DMP 64 Plus` | `dmp` and `64` |

`AV`, `CI`, and `Plus` SHALL NOT be required components for their canonical rules. Rule order and evidence-field order SHALL NOT grant authority or priority. This requirement SHALL NOT add any canonical model outside this reviewed registry.

After deployment of this reviewed recognition-registry change, the organization workbook SHALL be converted again to regenerate deployment-local `equipment_inventory.local.json`. The workbook and generated snapshot SHALL remain outside Git, runtime SHALL continue to consume only the canonical JSON snapshot, and runtime SHALL NOT parse `.xlsx` data.

#### Scenario: Compact TE40 evidence is recognized

- **WHEN** normalized source `Модель` or normalized source `Наименование` is `TE40`, `TE 40`, or `TE-40`
- **THEN** that field's evidence contains exact components `te` and `40`
- **AND** the `Huawei TE40` rule matches that field

#### Scenario: Compact TE50 evidence is recognized

- **WHEN** normalized source `Модель` or normalized source `Наименование` is `TE50`, `TE 50`, `TE-50`, `Huawei TE50`, or `Huawei_TE.50`
- **THEN** that field's evidence contains exact components `te` and `50`
- **AND** the `Huawei TE50` rule matches that field without a new tokenization rule

#### Scenario: TE50 recognition publishes the exact canonical diagnostic model

- **GIVEN** the combined distinct match union from the two approved evidence fields contains only `Huawei TE50`
- **WHEN** the diagnostic-model cardinality contract is applied
- **THEN** canonical `diagnostic_model` is exactly `Huawei TE50`

#### Scenario: TE20, TE40, and TE50 remain distinct component rules

- **WHEN** approved evidence has exact components `te` and `40`
- **THEN** `Huawei TE40` matches and `Huawei TE50` does not match
- **WHEN** approved evidence has exact components `te` and `50`
- **THEN** `Huawei TE50` matches and `Huawei TE40` does not match
- **AND** existing `Huawei TE20` recognition remains unchanged

#### Scenario: Optional canonical suffix is absent

- **WHEN** either normalized approved evidence field contains exact components `pe` and `8208` without `av`
- **THEN** the `Aten PE8208AV` rule matches that field
- **AND** the importer does not require the optional canonical suffix in source evidence

#### Scenario: Forte accent alternative is recognized

- **WHEN** either normalized approved evidence field contains `tesira` and exact component `forte` or `forté`
- **THEN** the `Biamp Tesira Forte CI` rule matches that field

#### Scenario: Similar longer components are rejected

- **WHEN** either normalized approved evidence field is `LTE 40`, `TE200`, `TE401`, `TE500`, `TE501`, `IN18040`, `PE82080`, or `DMP640`
- **THEN** no reviewed rule matches that field merely because a shorter key appears as a substring

#### Scenario: CloudLink Box 310 evidence is recognized

- **WHEN** either normalized approved evidence field contains exact components `cloudlink`, `box`, and `310`
- **THEN** the `CloudLink Box 310` rule matches that field
- **AND** the `CloudLink Bar 310` rule does not match merely because both products share `cloudlink` and `310`

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

#### Scenario: Exactly one rule matches

- **WHEN** the union of all reviewed matches from `Модель` and `Наименование` contains exactly one canonical model
- **THEN** canonical `diagnostic_model` is that exact supported model name
- **AND** no unmapped or ambiguous model issue is emitted

#### Scenario: No rule matches

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

#### Scenario: Multiple rules match

- **GIVEN** one approved evidence field satisfies more than one registry rule, such as combined `TE20 / TE40` evidence
- **WHEN** the other field is unmapped or agrees with only one of those candidates
- **THEN** the combined distinct union still contains more than one model
- **AND** canonical `diagnostic_model` is null
- **AND** the importer emits `AMBIGUOUS_DIAGNOSTIC_MODEL`
- **AND** it does not erase contradictory evidence through field priority or manufacturer evidence

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

For archive applicability, the inherited switch-connection scenario headings below
remain stable identifiers. Their normative outcomes describe historical schema-v3
loading; current candidate publication continues to target schema v4.

#### Scenario: Unique connection is published

- **GIVEN** a valid historical schema-v3 record contains one normalized switch IP and port pair
- **WHEN** the runtime loader validates the snapshot
- **THEN** those switch values participate in deterministic schema-v3 snapshot identity
- **AND** runtime adaptation exposes them with `room_address = null`

#### Scenario: Connection is unavailable

- **GIVEN** a valid historical schema-v3 record has no unambiguous network connection
- **WHEN** the runtime loader validates the snapshot
- **THEN** both schema-v3 switch fields remain null unless one historical unique partial field is valid
- **AND** the record remains present when otherwise valid

#### Scenario: Switch field changes identity

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

The importer SHALL expose a UI-independent combined preflight for an explicitly supplied primary workbook and network workbook. Combined preflight SHALL reread both current files, repeat both source validations, apply the approved MAC-only switch reconciliation, build the schema-v4 candidate in memory, compute its deterministic snapshot identity, and validate the candidate through the runtime loader.

Combined preflight SHALL require exactly the two workbook paths. It SHALL NOT require or own an output path. If a caller supplies an already selected output path as optional additional configuration evidence, that path MAY be checked for conflict with either input, but absence of output SHALL NOT block combined preflight.

Combined preflight SHALL NOT publish the candidate. A prior per-source preflight result SHALL NOT substitute for rereading either current source. Combined preflight SHALL report inventory-relative network outcomes under the same severity and ambiguity contracts used by conversion.

For archive applicability, the inherited schema-v3 scenario heading below remains a
stable identifier. Its normative outcome is updated to the current schema-v4
preflight contract.

#### Scenario: Combined preflight reports a valid schema-v3 candidate without output configuration

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

The standalone GUI support SHALL NOT remove or change the intentional one-source and explicit two-source CLI/direct API conversion entry points. Both current conversion modes SHALL publish schema version 4 under this change. The direct conversion API SHALL continue to accept an optional network source under the existing path-priority contract.

Except for the explicitly approved schema-v4 migration and the added canonical `room_address` field, preflight APIs, guarded publication, and report extensions SHALL NOT independently change canonical source authorities, diagnostic-model recognition, MAC-only reconciliation, deterministic snapshot identity semantics, runtime candidate validation, or ordinary atomic publication. The importer/domain layer SHALL NOT import PyQt5.

For archive applicability, the inherited schema-v2/schema-v3 scenario headings below
remain stable identifiers. Their normative outcomes are updated to the current
schema-v4 conversion contract.

#### Scenario: One-source CLI conversion remains schema v2

- **GIVEN** the CLI or direct API explicitly performs conversion without a network source
- **WHEN** conversion succeeds
- **THEN** it publishes schema version 4 under the primary-only schema-v4 contract
- **AND** standalone GUI support does not require PyQt5 in the importer or runtime loader

#### Scenario: Two-source direct conversion remains schema v3

- **GIVEN** the direct API receives explicit valid primary, network, and output paths
- **WHEN** conversion succeeds
- **THEN** it publishes schema version 4 under the existing reconciliation and atomic-publication contracts
- **AND** the same operation result can be rendered by CLI or GUI consumers

### Requirement: Schema-v3 switch fields are non-authoritative runtime inventory metadata

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

#### Scenario: Diagnostics run with schema v3

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

### Requirement: Room-name search is room-id preserving, distinguishable, and deterministic

The storage-independent `EquipmentInventory` runtime boundary SHALL provide a room-name search operation equivalent to `find_rooms_by_name(query)` for application autocomplete and direct room selection. This query SHALL NOT change canonical schema version 4 and SHALL perform no device/network I/O.

The search SHALL use only canonical records whose `room_id` is non-null and whose `room_name` is nonblank. The query and candidate names SHALL be compared after the existing canonical text normalization plus Unicode `casefold()`. A nonblank query matches when its complete normalized/casefolded text is a substring of a normalized/casefolded canonical `room_name`.

Matching SHALL NOT use fuzzy similarity, edit distance, transliteration, token guessing, device model text, address, VIP state, IP, `device_kind`, `source_model`, or registry order.

Search identity SHALL remain exact canonical `room_id`. Every matching room ID SHALL appear at most once even when several records or several differing names under that room ID match. Distinct room IDs SHALL remain distinct results even when their display names are identical.

For one matched room ID, the search projection SHALL derive presentation evidence independently and deterministically from canonical room records in ascending canonical `record_id` order:

```text
display_name     = first nonblank room_name
display_address  = first nonblank room_address, or null
```

A room MAY match because of another nonblank name present on a later record; this SHALL NOT change room identity or rewrite canonical records.

Autocomplete SHALL expose a deterministic `selection_label` or equivalent display string for each result. The label SHALL begin with `display_name`; when `display_address` is available it SHALL append that address as display-only disambiguation, for example `Переговорная — ул. ..., д. ...`. If two or more distinct room IDs in the same current result set still produce the same normalized name/address label, the application/inventory presentation projection SHALL append a neutral deterministic result discriminator such as `Вариант 1`, `Вариант 2` according to the already-defined deterministic result ordering. The discriminator SHALL NOT become room identity and SHALL NOT be persisted as canonical data.

Raw canonical `room_id` MAY remain hidden from ordinary operator presentation. Regardless of the displayed label, authority SHALL remain the exact result `room_id` bound to the current inventory snapshot.

Results SHALL be deterministic and ordered by casefolded `display_name`, then casefolded `display_address` with null sorting consistently, and then canonical `room_id`. Blank/empty normalized query SHALL return an empty result collection.

The runtime inventory implementation SHALL maintain an immutable room-search projection/index or equivalent precomputed structure so normal autocomplete queries do not repeatedly reconstruct room identity or normalize the complete canonical record set on every keystroke.

#### Scenario: Partial room name returns one room

- **GIVEN** canonical room ID `room-305` has nonblank room name `Переговорная 305`
- **WHEN** the application searches for `говорная 30`
- **THEN** the result contains `room-305`
- **AND** no device network I/O occurs

#### Scenario: Same room has several name values

- **GIVEN** records under one canonical `room_id` contain more than one nonblank `room_name`
- **WHEN** the query matches any one of those names
- **THEN** that room ID appears exactly once
- **AND** its display name is the first nonblank room name in canonical record order

#### Scenario: Same room name belongs to different room IDs with different addresses

- **GIVEN** two distinct canonical room IDs have the same `display_name`
- **AND** their first usable canonical room addresses differ
- **WHEN** that name is searched
- **THEN** both room IDs remain separate results
- **AND** their selection labels include the respective addresses so the operator can distinguish them
- **AND** the inventory does not merge them by display text

#### Scenario: Same room name and address still remain distinguishable

- **GIVEN** two or more distinct room IDs in one result set have equal normalized display name and display address
- **WHEN** autocomplete labels are produced
- **THEN** each result receives a deterministic neutral result discriminator in the display label
- **AND** each label still maps to exactly one canonical room ID
- **AND** the discriminator is not canonical identity or persisted room metadata

#### Scenario: Search does not use address or device model to create matches

- **GIVEN** a query appears only in a room address or device model text and not in any canonical room name
- **WHEN** room-name search runs
- **THEN** that evidence does not create a room match
- **AND** address may only decorate an already matched room result

#### Scenario: Blank search is empty

- **WHEN** room-name search receives only blank/whitespace text
- **THEN** it returns an empty result collection
- **AND** it creates no fallback or network activity
