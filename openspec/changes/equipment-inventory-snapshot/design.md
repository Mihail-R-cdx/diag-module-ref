## Context

The diagnostic application currently owns device diagnostic lifecycles for codecs,
Matrix, PDU, audio DSP, and DMP, but it has no external equipment-inventory boundary.
The planned room-context feature needs to resolve a diagnosed PDU IP into inventory
records, identify the PDU room, and later locate codec candidates in that room.

The source inventory is an organization-owned Excel workbook with approximately 17,000
rows and about 15 columns. The exact workbook sheet names, column headers, and source
model/type conventions have not yet been inspected in this change. Those source details
must not leak into the runtime API or be guessed during implementation.

The current repository already has strong precedents that this change must preserve:

- application/composition code owns orchestration and device credential policy;
- protocol workers and handlers must not acquire unrelated application responsibilities;
- stale operation policy remains separate from data lookup policy;
- secrets and sensitive operational data must not be emitted casually;
- focused domain components are preferred over a generic universal manager.

This change creates only the inventory data foundation. The later
`pdu-room-codec-enrichment` change will own the application orchestration that consumes
accepted PDU context and starts an independent read-only codec-status lifecycle.

## Goals

- Decouple runtime inventory lookup from Excel workbook structure and spreadsheet
  libraries.
- Define a stable versioned canonical JSON snapshot contract.
- Preserve source ambiguity instead of silently selecting first matches or deduplicating
  conflicting equipment records.
- Build efficient in-memory indexes once at load time for the expected 17,000-record
  scale.
- Keep runtime consumers independent of JSON so SQLite can be introduced later without
  changing lookup semantics.
- Make production inventory deployment-local and keep real organization data out of Git.
- Provide enough canonical model/type metadata for later room-to-codec resolution
  without performing any network operation in this change.

## Non-Goals

- Do not change `PDUController`, `PDUScreen`, `VCSDiagnosticApp`, codec screens, codec
  interactive sessions, codec polling, credentials, transport fallback, or network
  workers.
- Do not trigger inventory lookup automatically after a PDU refresh.
- Do not select a codec for a room or define multi-codec primary-selection policy beyond
  preserving the data needed for the later change.
- Do not add SQLite in the first implementation.
- Do not turn the equipment inventory into an editable application database.
- Do not commit the real Excel workbook or a generated production snapshot.
- Do not hard-code guessed organization-specific Excel sheet names or column headers.

## Decision 1: Excel is an offline import format, not a runtime dependency

The approved boundary is:

```text
Excel source
  -> offline importer
  -> canonical snapshot
  -> runtime loader
  -> indexed EquipmentInventory
```

The importer may use an import-only dependency such as `openpyxl`. The normal
diagnostic runtime must not import the workbook parser or require the spreadsheet
library to start, load inventory, or execute device diagnostics.

The importer owns all source-specific concerns:

- workbook and worksheet selection;
- source-column mapping;
- normalization of blank cells and source value types;
- source model/type alias mapping;
- conversion of valid IP values to canonical normalized strings;
- mapping source room fields into canonical room identity/display fields;
- import diagnostics and row accounting.

The real workbook, or at minimum a sanitized workbook schema/header sample, must be
inspected before implementing its concrete mapping. If the source layout is ambiguous,
the implementer must stop and request clarification rather than infer column semantics.

## Decision 2: JSON is the first canonical runtime storage format

For the current expected scale, approximately 17,000 records, a fully loaded immutable
snapshot with dictionary indexes is simpler than introducing a query database. JSON is
human-inspectable, easy to produce offline, and can be loaded with Python's standard
library.

SQLite is intentionally deferred. The runtime contract must nevertheless avoid exposing
JSON-specific details to consumers. A future SQLite loader may construct the same
`EquipmentInventory` abstraction and preserve the same query/result semantics.

The recommended deployment-local default snapshot name is:

```text
equipment_inventory.local.json
```

Path resolution should be deterministic and independent of the process current working
directory, following the repository's existing local-configuration precedent. Tests may
supply an explicit path.

## Decision 3: Canonical snapshot schema

The snapshot root is a versioned object. The first implementation should contain at
least:

```text
schema_version
snapshot_id
records
```

Optional non-secret generation metadata may be included if useful, for example a UTC
generation timestamp or imported row count, but runtime behavior must not depend on
source workbook path names or other workstation-specific details.

Each canonical equipment record contains the minimal runtime fields:

```text
record_id
source_model
diagnostic_model
ip_address
room_id
room_name
device_kind
```

Field semantics:

- `record_id`: non-empty identity unique within one snapshot. A real authoritative asset
  identifier is preferred when the source provides one; otherwise the importer may
  derive a deterministic import identity appropriate to the inspected source.
- `source_model`: normalized source model text retained for traceability; may be null
  when genuinely absent.
- `diagnostic_model`: exact supported application model name when the importer mapping
  can resolve one; otherwise null. Unknown or unsupported models are not fabricated.
- `ip_address`: normalized IPv4 text when a valid source address exists; otherwise null.
- `room_id`: authoritative room identity when available; otherwise null.
- `room_name`: display name when available; otherwise null. `room_name` is not silently
  promoted to authoritative room identity unless the inspected source contract
  explicitly defines it that way.
- `device_kind`: normalized category used for generic inventory filtering, including at
  least the ability to distinguish a PDU, a video codec, and unknown/other equipment.

The canonical snapshot is intentionally not a wholesale copy of all Excel columns.
Additional fields may be added only when a reviewed runtime use case requires them.

## Decision 4: Import validation separates fatal structure from data-quality issues

The importer must produce a structured report and account for each source row. A source
row must not disappear silently.

Fatal import conditions include cases such as:

- workbook/sheet selection cannot be resolved;
- required source-column mapping is unavailable;
- canonical root/schema construction fails;
- duplicate canonical `record_id` values cannot be resolved deterministically.

Fatal conditions prevent publication of a new canonical snapshot.

Non-fatal data-quality conditions may include:

- blank IP address;
- invalid IP text that cannot be normalized;
- missing room identity;
- unmapped/unsupported diagnostic model;
- duplicate IP address across multiple records;
- multiple devices of the same relevant kind in one room.

These conditions are reported but are not automatically "fixed" by deleting records or
selecting one candidate. Where possible the canonical record is retained with a null or
unresolved field. Invalid source IP text must never become an index key.

The report should use structured issue codes, counts, and source row/record identities.
It must avoid dumping entire source rows or unrelated organization data into logs.

## Decision 5: Runtime abstraction and module boundary

The preferred focused runtime location is:

```text
core/equipment_inventory.py
```

It owns:

- immutable `EquipmentRecord` representation;
- immutable loaded snapshot metadata;
- `EquipmentInventory` query surface;
- JSON snapshot loading and canonical schema validation;
- in-memory index construction;
- normalized lookup input validation.

The preferred offline import location is:

```text
tools/import_equipment_inventory.py
```

The importer must not be imported by normal application runtime modules.

A later implementation may split these files if they become materially large, but it
must not introduce a generic persistence framework or a cross-device lifecycle manager
for this change.

## Decision 6: Build indexes once and preserve multiplicity

On successful load, `EquipmentInventory` builds immutable indexes equivalent to:

```text
ip_address -> tuple[EquipmentRecord, ...]
room_id -> tuple[EquipmentRecord, ...]
(room_id, device_kind) -> tuple[EquipmentRecord, ...]
```

Normal lookup methods use these indexes and do not repeatedly scan all records.

The public query surface should be equivalent to:

```text
find_by_ip(ip_address)
find_room_equipment(room_id)
find_by_room_and_kind(room_id, device_kind)
```

Exact Python names may vary only if the reviewed semantics remain unchanged.

All query methods return zero or more records. They never hide ambiguity by returning
only the first matching row. Callers in the later integration change will decide how a
zero, one, or multiple-match result maps to `NOT_FOUND`, `RESOLVED`, or `AMBIGUOUS`.

## Decision 7: Loaded inventory is immutable and revision-identifiable

A loaded `EquipmentInventory` represents one snapshot revision. Its records and indexes
are not mutated in place by runtime consumers. Replacing inventory data means loading a
new snapshot and publishing a new inventory instance through the later application
composition boundary.

`snapshot_id` is a non-secret opaque identity carried by the loaded inventory. The later
PDU-room enrichment lifecycle may capture this identity so results derived from an old
inventory revision cannot be confused with results derived from a newer snapshot.

This change does not yet add automatic runtime reload or GUI controls for snapshot
replacement.

## Decision 8: Production inventory is local operational data

The real organization workbook and generated production snapshot may contain internal IP
addresses, room structure, equipment identities, and other operational information.
They are not repository fixtures.

Implementation must:

- ignore the deployment-local production snapshot in Git;
- avoid adding the real workbook to the repository;
- use synthetic inventory fixtures in tests;
- avoid full-record dumps in ordinary logs and public errors;
- keep import reports scoped to the minimum data needed to identify and correct issues.

A tracked example snapshot may exist only when every value is synthetic.

## Alternatives Considered

### Read Excel directly in runtime

Rejected. It couples production behavior to workbook layout, adds spreadsheet parsing to
normal runtime dependency/loading paths, and makes source-data validation part of device
diagnostics.

### Use SQLite immediately

Rejected for the first version. The current lookup requirements are small and
index-oriented, and approximately 17,000 records fit comfortably in memory. The storage
abstraction keeps SQLite available later without paying its complexity now.

### Store one record per IP in a dictionary

Rejected. Duplicate IP assignments are a real data-quality/ambiguity condition. A
single-value dictionary would silently discard evidence and force an arbitrary winner.

### Put room/codec orchestration in `PDUController`

Out of scope and architecturally rejected for the subsequent change. `PDUController`
remains PDU-specific. This change only creates the inventory data boundary that later
application/composition orchestration will consume.

## Handoff to the Next Change

After this change is implemented, reviewed, validated, archived, and merged, the planned
`pdu-room-codec-enrichment` change may depend only on the stable inventory surface:

```text
accepted PDU IP
  -> EquipmentInventory.find_by_ip(...)
  -> resolve unique room
  -> EquipmentInventory.find_by_room_and_kind(room_id, "video_codec")
  -> resolve codec candidate
```

That later change owns PDU accepted-result integration, room-context result modeling,
codec lifecycle, credentials, network I/O, stale-operation protection, and GUI
presentation. None of those responsibilities move into the inventory module.
