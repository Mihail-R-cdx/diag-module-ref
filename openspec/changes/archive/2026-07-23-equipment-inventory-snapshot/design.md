## Context

The diagnostic application already owns device diagnostic lifecycles for codecs, Matrix,
PDU, audio DSP, and DMP, but it has no external equipment-inventory boundary. The planned
room-context feature needs to resolve a diagnosed PDU IP into inventory records, identify
the PDU room, and later locate codec candidates in that room.

The source inventory is an organization-owned Excel workbook with approximately 17,000
rows. The relevant source-column semantics have now been inspected and confirmed for this
change. The source remains external operational data; only the mapping contract belongs in
the repository.

This change creates only the inventory data foundation. The later
`pdu-room-codec-enrichment` change owns application orchestration that consumes accepted
PDU context and starts an independent read-only codec-status lifecycle.

The existing architectural principles remain unchanged:

- application/composition code owns cross-device orchestration and credential policy;
- handlers and workers do not acquire unrelated application responsibilities;
- stale-operation policy remains separate from inventory lookup policy;
- secrets and sensitive operational data are not emitted casually;
- focused domain components are preferred over a generic universal manager;
- ambiguity is preserved unless a reviewed contract defines authority to resolve it.

## Goals

- Decouple runtime inventory lookup from Excel workbook structure and spreadsheet libraries.
- Define a strict, versioned canonical JSON snapshot contract.
- Encode the confirmed source-to-canonical mapping explicitly rather than guessing at implementation time.
- Make `SmartRoomID` the stable authoritative equipment-record identity for this source.
- Keep `ID комнаты` authoritative for room identity and `Название комнаты` display-only.
- Preserve invalid-field, multiplicity, and consistency evidence without silently correcting source data.
- Build efficient immutable in-memory indexes for the expected 17,000-record scale.
- Keep runtime consumers storage-independent so SQLite remains a future option.
- Keep real production inventory and workbook content outside Git.
- Preserve deterministic snapshot identity and validate that identity at runtime load.

## Non-Goals

- Do not change `PDUController`, `PDUScreen`, `VCSDiagnosticApp`, codec screens, codec interactive sessions, codec polling, credentials, transport fallback, or network workers.
- Do not trigger inventory lookup after a PDU refresh in this change.
- Do not select a codec or PDU when multiple candidates exist in one room.
- Do not add SQLite in the first implementation.
- Do not turn the inventory into an editable application database.
- Do not commit the real workbook or generated production snapshot.
- Do not add a runtime controller relation or controller index from `SmartRoomID контроллера`.
- Do not use secondary consistency evidence to rewrite authoritative canonical fields.
- Do not invent fallback `record_id` values when `SmartRoomID` is missing or duplicated.

## Decision 1: Excel is an offline import format

The approved boundary remains:

```text
Excel source
  -> offline importer
  -> canonical snapshot + structured import report
  -> runtime loader
  -> indexed EquipmentInventory
```

The importer may use an import-only dependency such as `openpyxl`. Normal diagnostic
runtime modules must not import the workbook parser or require a spreadsheet library to
start, load inventory, or execute device diagnostics.

The importer owns all source-specific concerns:

- workbook and worksheet selection;
- confirmed source-column mapping;
- normalization of source values;
- authoritative identity mapping;
- source model and device-kind mapping;
- explicit reviewed diagnostic-model mapping;
- invalid-field and consistency diagnostics;
- source-row accounting;
- canonical snapshot generation and atomic publication.

The runtime owns only canonical schema validation, snapshot identity verification, index
construction, and the storage-independent query boundary.

## Decision 2: Confirmed source-to-canonical mapping

The confirmed organization mapping is:

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

`diagnostic_model` is not copied from one source column. It is populated only by a
separate explicit reviewed mapping from supported source manufacturer/model evidence to
application-supported diagnostic model names.

`Производитель` and `Модель` remain importer-side evidence. They may support explicit
`diagnostic_model` mapping and consistency diagnostics, but schema v1 does not store them
as separate canonical fields.

`SmartRoomID контроллера` also remains importer-side evidence. It is not required by the
runtime path:

```text
PDU IP -> record -> room_id -> equipment in room
```

Therefore schema v1 does not add `controller_record_id`, a controller relation, or a
controller index solely to represent this source column.

## Decision 3: SmartRoomID is authoritative record identity

The source analysis confirmed these semantics:

- `SmartRoomID` is unique for each equipment database record;
- it is always expected to be populated;
- ordinary edits to IP, room, model, MAC, serial number, and other attributes do not change it;
- deleting a record and creating a new one may legitimately create a new `SmartRoomID`.

The normative mapping is therefore:

```text
SmartRoomID -> canonical record_id
```

There is no fallback identity strategy for this source. Missing or blank-after-normalization
`SmartRoomID` is fatal. Duplicate canonical `SmartRoomID` is fatal.

The importer must not recover from either condition by using:

- workbook row number or row order;
- IP address;
- MAC address;
- serial number;
- room identity or display name;
- model text;
- random UUID;
- timestamp or counter;
- suffixing a duplicate ID.

A fatal identity failure blocks publication of the complete candidate snapshot. The
previous valid production snapshot remains intact under the atomic-publication contract.

## Decision 4: ID комнаты is authoritative room identity

The source analysis confirmed:

```text
ID комнаты       -> room_id
Название комнаты -> room_name
```

`room_id` is authoritative. `room_name` is a display attribute and never becomes a fallback
room identity automatically.

The importer must preserve source evidence rather than force consistency:

- same `room_id` with different `room_name` values: preserve all records, report consistency issue;
- same `room_name` with different `room_id` values: preserve distinct rooms, do not merge;
- `room_name` present with missing `room_id`: preserve display text, use `room_id = null`;
- missing room identity is non-fatal when the record remains otherwise representable.

Runtime indexes use `room_id`, never `room_name`, as the room key.

## Decision 5: Наименование is source_model

The source analysis confirmed that `Наименование` is the human-readable source model value,
for example `Huawei TE20`.

The canonical rule is:

```text
Наименование -> source_model
```

The importer normalizes and preserves this value. It must not silently reconstruct or
replace it from `Производитель + Модель` when `Наименование` already has a source value.

`Производитель` and `Модель` may be used for:

- an explicit reviewed `diagnostic_model` mapping;
- consistency diagnostics when the source fields appear contradictory.

A mismatch between the three source fields is non-fatal by itself and does not authorize
rewriting canonical `source_model`.

## Decision 6: Device kind follows exact source type authority

Schema-v1 `device_kind` remains a closed vocabulary:

```text
pdu
video_codec
other
```

The confirmed exact mapping from `Тип модели` is:

```text
Video Conference -> video_codec
БРП              -> pdu
all other values  -> other
```

This is an authority rule, not a heuristic. The importer must not use fuzzy matching,
substring matching, manufacturer names, model names, or known diagnostic-model recognition
to silently change `device_kind`.

Secondary evidence may show a likely source inconsistency. For example, a known codec model
may arrive with an unexpected `Тип модели`. That can produce a consistency issue such as a
known-model/type mismatch, but recognized model evidence does not override the exact source
type mapping.

The principle is:

```text
consistency evidence != mapping authority
recognized model != permission to override source type
```

## Decision 7: Schema v1 remains minimal and runtime-focused

The canonical root contains:

```text
schema_version: integer, exactly 1
snapshot_id: deterministic content-derived string
records: JSON array
```

Optional generation metadata may include:

```text
generated_at
source_row_count
```

Each canonical record contains exactly:

```text
record_id: non-empty string
source_model: string | null
diagnostic_model: string | null
ip_address: canonical IPv4 string | null
mac_address: canonical MAC string | null
serial_number: string | null
room_id: non-empty normalized string | null
room_name: non-empty normalized string | null
device_kind: pdu | video_codec | other
```

Required record fields are:

```text
record_id
device_kind
```

Nullable record fields are:

```text
source_model
diagnostic_model
ip_address
mac_address
serial_number
room_id
room_name
```

The core rule is:

```text
incomplete optional data != automatically invalid record
```

Invalid or absent nullable source data is represented as null when safe and made observable
through importer diagnostics. It does not silently drop an otherwise representable row.

`mac_address` uses lowercase colon-separated 48-bit canonical text. `serial_number` uses
general normalized text. Neither replaces `SmartRoomID` as record identity, and neither
requires a runtime index in schema v1.

## Decision 8: Authoritative mapping and consistency expectations are separate

The source database is maintained by people and cannot be assumed perfectly consistent.
The importer must distinguish authority from evidence.

Authoritative mappings are the rules that produce canonical fields. Consistency
expectations are checks that may indicate likely source-data problems but do not grant
permission to rewrite canonical values.

The importer diagnostics must distinguish at least three semantic classes:

```text
1. fatal source-contract issues
2. non-fatal invalid-field/data-quality issues
3. cross-row/source consistency issues
```

### Fatal source-contract issues

At minimum:

- missing or unusable `SmartRoomID`;
- duplicate canonical `SmartRoomID`;
- missing required source structure needed to apply the confirmed mapping;
- failure to construct a complete valid candidate snapshot.

Fatal issues block publication of the new snapshot.

### Non-fatal invalid-field/data-quality issues

Examples include:

- invalid or missing IP address;
- invalid or missing MAC address;
- missing serial number;
- missing room identity;
- unmapped/unsupported `diagnostic_model`;
- duplicate IP, MAC, or serial values.

When a canonical record remains safely representable, these issues do not block the whole
snapshot and do not remove the record.

### Cross-row/source consistency issues

Examples include:

- same `room_id` with conflicting room names;
- same room name reused across different room IDs;
- room name present while room ID is absent;
- mismatch between `Наименование`, `Производитель`, and `Модель`;
- known diagnostic model with unexpected source `Тип модели`;
- multiple PDU or multiple codecs in one room;
- inconsistent controller references.

Consistency issues do not authorize:

- deleting or deduplicating records;
- guessing missing values;
- first-match selection;
- changing `record_id`;
- changing `device_kind`;
- merging rooms;
- rewriting `source_model`.

Each source row is still accounted for as a canonical record or a structured issue. No row
disappears silently.

## Decision 9: Controller reference is consistency evidence only

`SmartRoomID контроллера` may be inspected for source consistency. Potential non-fatal
issues include:

- different equipment rows in one `room_id` referring to different controller IDs;
- controller reference missing from only part of a room;
- referenced controller ID matching no source equipment `SmartRoomID`;
- one room indirectly containing several controller IDs.

These checks do not modify canonical records. They do not make a complete otherwise-valid
snapshot fatal by themselves. They also do not justify adding a controller relation to
runtime schema v1.

## Decision 10: Multiplicity is preserved

Operational expectations do not become uniqueness constraints automatically.

The importer and runtime must preserve:

- duplicate IP assignments;
- duplicate MAC values;
- duplicate serial values;
- multiple PDU records in one room;
- multiple video codecs in one room;
- any other non-identity multiplicity that can be represented safely.

Only duplicate `SmartRoomID` is a fatal identity conflict because it violates the confirmed
record identity contract.

Runtime indexes therefore remain multi-value:

```text
ip_address -> tuple[EquipmentRecord, ...]
room_id -> tuple[EquipmentRecord, ...]
(room_id, device_kind) -> tuple[EquipmentRecord, ...]
```

Normal lookup returns zero, one, or many records. The inventory layer never hides ambiguity
by returning only `records[0]`.

## Decision 11: Snapshot identity is deterministic and verified

Schema v1 uses deterministic content identity:

```text
snapshot_id = "sha256:" + lowercase_sha256_hex(canonical_identity_payload)
```

The identity payload contains exactly:

```text
schema_version
records
```

Records are sorted by normalized `record_id`. JSON object keys are sorted, insignificant
whitespace is excluded, and normalized Unicode text is encoded directly as UTF-8.

Optional generation metadata such as `generated_at` and `source_row_count` is excluded.
All canonical record fields, including MAC address and serial number, remain part of
`records` and therefore participate in revision identity.

The runtime loader independently recomputes the expected digest from the loaded canonical
content before publishing an `EquipmentInventory`. A syntactically valid but stale or wrong
`snapshot_id` fails as `INVALID_SNAPSHOT`.

Importer generation and runtime verification must share exactly the same canonical identity
algorithm.

## Decision 12: Snapshot publication is atomic

A candidate production snapshot is published only after complete import and validation.

The invariant is:

```text
fatal import before complete publication
    -> previous production snapshot remains intact
    -> no partial candidate appears under the production snapshot path
```

This applies to missing or duplicate `SmartRoomID`, source-structure failure, schema
failure, snapshot-identity failure during candidate validation, and any other fatal
pre-publication condition.

A temporary file followed by atomic replacement is an expected implementation approach,
but the exact filesystem API is an implementation detail.

## Decision 13: Runtime load failures are structured

The runtime loader exposes one of these machine-readable categories:

```text
NOT_FOUND
UNREADABLE
INVALID_FORMAT
UNSUPPORTED_SCHEMA
INVALID_SNAPSHOT
```

`INVALID_SNAPSHOT` includes invalid canonical shape/content, duplicate record IDs, invalid
canonical field values, or declared/recomputed `snapshot_id` mismatch.

No failed load publishes partial records, indexes, or an `EquipmentInventory`. Application
consumers do not need to inspect raw Python exception strings to classify inventory
availability.

## Decision 14: Runtime boundary stays storage-independent

The preferred focused runtime location is:

```text
core/equipment_inventory.py
```

It owns:

- immutable `EquipmentRecord` representation;
- immutable snapshot metadata;
- JSON snapshot loading and schema validation;
- `snapshot_id` verification;
- structured load-failure classification;
- immutable index construction;
- query input normalization;
- the `EquipmentInventory` query surface.

The preferred offline importer location is:

```text
tools/import_equipment_inventory.py
```

The importer is not imported by normal application runtime modules.

The public query surface remains equivalent to:

```text
find_by_ip(ip_address)
find_room_equipment(room_id)
find_by_room_and_kind(room_id, device_kind)
```

No MAC, serial-number, room-name, or controller-reference index is added without a future
reviewed runtime requirement.

## Decision 15: Production inventory remains local operational data

The real workbook and generated production snapshot contain internal infrastructure data.
They are not repository fixtures.

Implementation must:

- ignore `equipment_inventory.local.json` in Git;
- avoid adding the real workbook to the repository;
- use only synthetic inventory fixtures in tests;
- avoid full-row and full-inventory dumps in diagnostics;
- expose only minimal safe row references, safe `record_id` where available, issue class,
  issue code, and short safe descriptions.

Source-only evidence such as controller references must also remain absent from synthetic
fixtures unless represented with fully synthetic values.

## Alternatives considered

### Read Excel directly at runtime

Rejected. It couples device diagnostics to workbook structure and adds spreadsheet parsing
to the normal runtime dependency path.

### Use SQLite immediately

Rejected for the first implementation. The current scale and lookup needs fit an immutable
in-memory snapshot with indexes. The storage-independent boundary keeps SQLite available
later.

### Generate fallback record identity

Rejected for the confirmed source. `SmartRoomID` is the authoritative stable identity.
Missing or duplicate values are source-contract failures, not opportunities to manufacture
identity from mutable attributes or row order.

### Infer device kind from model names

Rejected. Exact `Тип модели` mapping is authoritative. Model recognition is consistency
evidence only and cannot silently override `device_kind`.

### Merge rooms by display name

Rejected. `ID комнаты` is authoritative room identity; `Название комнаты` is display data.

### Add controller relation to schema v1

Rejected. The current runtime path does not need it. `SmartRoomID контроллера` may support
importer-side consistency diagnostics without expanding the canonical runtime contract.

### Store one record per IP

Rejected. IP is not unique identity. Multi-value indexes preserve duplicate assignments and
ambiguity.

## Handoff to the next change

After this change is implemented, independently validated, archived, and merged, the
planned `pdu-room-codec-enrichment` change may rely on:

```text
accepted PDU IP
  -> EquipmentInventory.find_by_ip(...)
  -> resolve authoritative room_id
  -> EquipmentInventory.find_by_room_and_kind(room_id, "video_codec")
  -> resolve zero/one/many codec candidates
```

The next change may also consume structured inventory load failures and capture
`snapshot_id` to bind derived context to one validated inventory revision.

That later change owns PDU accepted-result integration, room-context result modeling,
codec lifecycle, credentials, network I/O, stale-operation protection, and GUI
presentation. None of those responsibilities move into the inventory module.