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
- Define a stable, normative, versioned canonical JSON snapshot contract.
- Preserve source ambiguity instead of silently selecting first matches or deduplicating
  conflicting equipment records.
- Build efficient in-memory indexes once at load time for the expected 17,000-record
  scale.
- Keep runtime consumers independent of JSON so SQLite can be introduced later without
  changing lookup semantics.
- Make production inventory deployment-local and keep real organization data out of Git.
- Provide enough canonical model/type metadata for later room-to-codec resolution
  without performing any network operation in this change.
- Make inventory revision identity deterministic from canonical content so later
  application lifecycles can compare revisions without depending on import timestamps.
- Make canonical record identity deterministic from the reviewed source contract so
  logically unchanged inventory does not acquire a new revision solely because import
  execution details or source row order changed.

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
- Do not make generation timestamps part of inventory revision identity.
- Do not invent per-import `record_id` values or silently repair conflicting source
  identities with arbitrary suffixes.
- Do not guess source columns for the source database ID, MAC address, serial number, or
  other source fields before inspecting the real workbook or a sanitized schema/header
  sample.

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
- conversion of valid MAC values to canonical normalized strings;
- normalization of optional serial-number text;
- mapping source room fields into canonical room identity/display fields;
- reviewed canonical `record_id` provenance and derivation;
- import diagnostics and row accounting.

The real workbook, or at minimum a sanitized workbook schema/header sample, must be
inspected before implementing its concrete mapping. If the source layout is ambiguous,
the implementer must stop and request clarification rather than infer column semantics.
The same source-data gate applies to equipment identity: implementation must not invent a
`record_id` strategy before the source contract is inspected.

The preferred schema-v1 identity rule is:

```text
authoritative stable database record ID
    -> canonical record_id
```

This rule applies only after source analysis confirms the corresponding workbook column
and verifies that the source database ID is stable for normal record edits, including IP,
room, MAC, serial-number, or other mutable attribute changes. Deleting a source record and
creating a replacement may legitimately produce a new database ID, representing a new
canonical equipment record.

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

## Decision 3: Schema v1 is a strict intercomponent contract

The schema-v1 root is a UTF-8 JSON object with required fields:

```text
schema_version: integer, exactly 1
snapshot_id: non-empty string with schema-v1 deterministic SHA-256 identity format
records: JSON array
```

The only initially approved optional root generation metadata is:

```text
generated_at: RFC 3339 UTC string
source_row_count: non-negative integer
```

Generation metadata is informational only. It does not affect inventory identity or
runtime lookup semantics.

Every schema-v1 canonical equipment record contains exactly:

```text
record_id: non-empty string
source_model: string | null
diagnostic_model: string | null
ip_address: canonical IPv4 string | null
mac_address: canonical MAC address string | null
serial_number: string | null
room_id: non-empty normalized string | null
room_name: non-empty normalized string | null
device_kind: canonical string
```

Schema-v1 `device_kind` is deliberately a closed vocabulary:

```text
pdu
video_codec
other
```

This vocabulary is a contract for the later `pdu-room-codec-enrichment` change. A source
workbook may use any organization-specific type names, but the importer must map them
explicitly into these canonical values. Unknown or unmapped equipment becomes `other`;
the importer must not emit aliases such as `codec`, `vcs_codec`, or `video-codec`.

Canonical textual normalization uses NFC Unicode normalization and trims leading and
trailing whitespace. Empty nullable text becomes null, including empty `serial_number`.
`record_id` must remain non-empty and unique after normalization. Case and internal text
are preserved unless the inspected source contract has an explicitly reviewed stronger
authoritative identifier rule.

`record_id` provenance is part of the concrete reviewed source mapping, not an importer
implementation detail. The preferred rule is to use a stable authoritative unique
equipment identifier supplied by the source, after canonical normalization. If the
inspected source has no such field, a derived `record_id` is allowed only when a reviewed
deterministic derivation can be defined from stable source identity fields.

Schema-v1 explicitly separates record identity from physical device identifiers and
network attributes:

- `record_id` identifies the stable source database equipment record;
- `mac_address` and `serial_number` identify or describe the physical device when source
  data provides usable values;
- `ip_address` is a mutable network attribute and must not drive canonical record
  identity when an authoritative stable database ID is available.

Random UUIDs, timestamps, per-import counters, and other execution-specific values are
forbidden. Source row number or row order is also forbidden unless the reviewed source
contract explicitly declares row position authoritative. Mutable placement, display,
network, or device-attribute fields such as `ip_address`, `mac_address`,
`serial_number`, `room_id`, or `room_name` must not be used merely as convenient
disambiguators; they may participate only when the reviewed source contract explicitly
makes them part of the equipment identity key.

Duplicate normalized authoritative IDs and collisions from an approved deterministic
derivation are fatal source-contract failures. The importer must not append arbitrary
suffixes, counters, timestamps, or row numbers to manufacture uniqueness. If the real
source contract does not provide enough stable information to define unique deterministic
record identity, mapping and publication remain blocked until architectural review defines
the rule.

`ip_address`, when present, is canonical dotted-decimal IPv4 text. Invalid source IP text
is reported and does not become an index key.

`mac_address`, when present, is canonical lowercase colon-separated 48-bit MAC text:

```text
aa:bb:cc:dd:ee:ff
```

The importer must accept common textual representations of the same 48-bit MAC when they
can be unambiguously normalized to that canonical representation. A missing or blank MAC
becomes null. Invalid non-empty MAC source text is reported as an observable data-quality
issue and produces canonical `mac_address = null` when the rest of the record can still
be safely imported. MAC addresses are canonical equipment attributes; schema v1 does not
introduce a MAC index without a proven runtime need. Duplicate MAC values must not cause
arbitrary deletion, deduplication, or first-match selection.

`serial_number`, when present, uses the general canonical text normalization contract. A
missing serial number or a value that normalizes to an empty string becomes null. Schema
v1 does not assume global serial-number uniqueness, does not introduce a serial-number
index without a proven runtime need, and does not allow serial number to replace the
authoritative database ID as `record_id`.

The canonical snapshot is intentionally not a wholesale copy of all Excel columns.
Additional fields require a reviewed schema change rather than ad hoc importer output.

## Decision 4: snapshot_id identifies canonical data, not an import execution

`snapshot_id` is deterministic identity for one canonical data revision.

Required semantics:

```text
identical normalized canonical content
    -> identical snapshot_id

changed canonical content
    -> changed snapshot_id in ordinary operation
```

Schema v1 uses:

```text
snapshot_id = "sha256:" + lowercase_sha256_hex(canonical_identity_payload)
```

The identity payload contains exactly `schema_version` and `records`. Records are sorted
in deterministic ascending normalized `record_id` order. Because `record_id` itself is
stable under the reviewed source contract, reordering non-authoritative workbook rows does
not change canonical order or `snapshot_id`. The canonical JSON identity serialization
uses sorted object keys, compact separators with no insignificant whitespace, and direct
UTF-8 encoding of normalized Unicode text.

Because `mac_address` and `serial_number` are canonical record fields, they are included
in canonical `records` content and therefore participate in snapshot identity:

```text
change mac_address or serial_number
    -> canonical records change
    -> snapshot_id changes
```

They must not be moved into optional generation metadata.

Optional generation metadata such as `generated_at` and `source_row_count` is excluded
from the identity payload. Therefore importing the same canonical data at two different
times produces the same `snapshot_id`, even if informational timestamps differ.

This choice removes the previous ambiguity between random revision IDs and content-based
revision identity. The later enrichment lifecycle may safely capture `snapshot_id` and
compare equality to determine whether inventory canonical content changed.

## Decision 5: Import validation separates fatal structure from data-quality issues

The importer must produce a structured report and account for each source row. A source
row must not disappear silently.

Fatal import conditions include cases such as:

- workbook/sheet selection cannot be resolved;
- required source-column mapping is unavailable;
- no reviewed stable unique `record_id` rule can be defined from the inspected source;
- duplicate normalized authoritative equipment identifiers are present;
- an approved deterministic derived-identity rule produces a collision;
- canonical root/schema construction fails;
- duplicate canonical `record_id` values remain after the approved identity rule;
- complete schema-v1 validation fails before publication.

Fatal conditions prevent publication of a new canonical snapshot. Identity conflicts are
not repaired silently by suffixing or by switching to row numbers or another unreviewed
fallback rule.

Non-fatal data-quality conditions may include:

- blank IP address;
- invalid IP text that cannot be normalized;
- blank MAC address;
- invalid MAC text that cannot be normalized;
- missing serial number;
- missing room identity;
- unmapped/unsupported diagnostic model;
- duplicate IP address across multiple records;
- duplicate MAC address across multiple records;
- duplicate serial number across multiple records;
- multiple devices of the same relevant kind in one room.

These conditions are reported but are not automatically "fixed" by deleting records or
selecting one candidate. Where possible the canonical record is retained with a null or
unresolved field. Invalid source IP text must never become an index key. Invalid source
MAC text must never become a valid canonical MAC value.

Schema v1 permits null for these record fields:

```text
source_model
diagnostic_model
ip_address
mac_address
serial_number
room_id
room_name
```

Only `record_id` and `device_kind` remain required non-null record fields. Missing or
invalid nullable source data must not silently drop the source row, block the whole
snapshot by itself, or turn incomplete data into an automatically invalid record when the
canonical record can still be safely represented. Missing or invalid authoritative
`record_id` remains a separate identity/source-contract failure, and unknown equipment
type continues to normalize to `device_kind = other`.

The report should use structured issue codes, counts, and source row/record identities.
It must avoid dumping entire source rows or unrelated organization data into logs.

## Decision 6: Snapshot publication is atomic

A candidate production snapshot is not published until the complete import has finished
and the candidate passes canonical schema validation.

The normative behavior is:

```text
failed import before complete publication
    -> previous production snapshot remains intact
    -> no partial candidate appears at the production snapshot path
```

A temporary file in the target filesystem followed by atomic replacement is the expected
implementation approach, but the exact filesystem mechanism is an implementation detail.
The invariant, not the specific API call, is part of the capability contract.

This protection applies to every failure before successful publication, including failure
to establish or apply the approved stable `record_id` rule.

## Decision 7: Runtime load failures have stable machine-readable categories

The runtime loader exposes safe structured failures independent of the underlying Python
exception implementation. The categories are:

```text
NOT_FOUND
UNREADABLE
INVALID_FORMAT
UNSUPPORTED_SCHEMA
INVALID_SNAPSHOT
```

Their meanings are:

- `NOT_FOUND`: configured snapshot path does not exist;
- `UNREADABLE`: the file exists but cannot be read because of filesystem/access failure;
- `INVALID_FORMAT`: readable content is not valid UTF-8 JSON;
- `UNSUPPORTED_SCHEMA`: declared schema version is not integer `1`;
- `INVALID_SNAPSHOT`: JSON shape or canonical content violates schema v1, including
  duplicate normalized `record_id` or invalid canonical field values.

No failed load publishes a partial `EquipmentInventory`, partial records, or partial
indexes. Application consumers, including the later PDU-room enrichment controller, must
not need to catch raw `FileNotFoundError`, `JSONDecodeError`, or other storage-specific
exceptions to understand inventory availability.

The later integration change may map these loader failures into higher-level application
states such as inventory unavailable/configuration invalid, but it must consume this
stable structured boundary rather than inventing classifications from exception strings.

## Decision 8: Runtime abstraction and module boundary

The preferred focused runtime location is:

```text
core/equipment_inventory.py
```

It owns:

- immutable `EquipmentRecord` representation;
- immutable loaded snapshot metadata;
- `EquipmentInventory` query surface;
- JSON snapshot loading and canonical schema validation;
- structured safe load-failure classification;
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

## Decision 9: Build indexes once and preserve multiplicity

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
only the first matching row. Result ordering follows deterministic canonical record order.
Callers in the later integration change will decide how a zero, one, or multiple-match
result maps to `NOT_FOUND`, `RESOLVED`, or `AMBIGUOUS`.

## Decision 10: Loaded inventory is immutable and revision-identifiable

A loaded `EquipmentInventory` represents one canonical snapshot revision. Its records and
indexes are not mutated in place by runtime consumers. Replacing inventory data means
loading a new complete validated snapshot and publishing a new inventory instance through
the later application composition boundary.

`snapshot_id` is non-secret deterministic content identity carried by the loaded
inventory. Loading another file with identical canonical identity content yields the same
`snapshot_id`; loading changed canonical identity content yields the identity derived from
that changed content.

This change does not add automatic runtime reload or GUI controls for snapshot
replacement.

## Decision 11: Production inventory is local operational data

The real organization workbook and generated production snapshot may contain internal IP
addresses, room structure, equipment identities, and other operational information. They
are not repository fixtures.

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

### Use a random UUID for record_id

Rejected. It makes logically unchanged source inventory produce different canonical
records and therefore different `snapshot_id` values on each import. Schema v1 requires
record identity to come from a stable authoritative source identifier or an explicitly
reviewed deterministic derivation from stable source identity fields.

### Use source row number as record_id

Rejected by default. Reordering workbook rows would change canonical identity even when
the logical inventory is unchanged. Row position may participate only when the reviewed
authoritative source contract explicitly defines it as part of equipment identity.

### Repair duplicate equipment identities with suffixes

Rejected. Silent suffixing hides a source-contract identity conflict and makes identity
semantics depend on importer behavior or row order. Duplicate authoritative IDs or derived
identity collisions are fatal until the source mapping or architecture defines a stable
unique rule.

### Use a random UUID for snapshot_id

Rejected. It makes repeated imports of identical canonical content appear to be different
inventory revisions and conflicts with deterministic importer output. Schema v1 uses
content-derived identity instead.

### Include generation timestamp in snapshot identity

Rejected. A timestamp describes an import execution, not canonical inventory content. It
may exist as optional informational metadata but is excluded from `snapshot_id`.

### Store one record per IP in a dictionary

Rejected. Duplicate IP assignments are a real data-quality/ambiguity condition. A
single-value dictionary would silently discard evidence and force an arbitrary winner.

### Put room/codec orchestration in PDUController

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

The next change may also consume the stable inventory load-failure categories and capture
`snapshot_id` when it needs to bind derived room/codec context to one inventory revision.

That later change owns PDU accepted-result integration, room-context result modeling,
codec lifecycle, credentials, network I/O, stale-operation protection, and GUI
presentation. None of those responsibilities move into the inventory module.
