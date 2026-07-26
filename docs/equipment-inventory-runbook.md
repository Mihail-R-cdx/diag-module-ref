# Equipment Inventory Runbook

## Purpose and authority

This document is the operational map for equipment-inventory work in
`Mihail-R-cdx/diag-module-ref`. It is intended for developers, reviewers,
ChatGPT sessions, and local Codex sessions.

The normative contracts remain the current root OpenSpec specifications:

- `openspec/specs/equipment-inventory-snapshot/spec.md`
- `openspec/specs/pdu-room-codec-enrichment/spec.md`, when that capability is
  present on the current branch
- the related root specifications for application composition, request
  lifecycle, credentials, and device diagnostics

When the second root specification is not yet present on a branch, read the
current active or archived `pdu-room-codec-enrichment` change instead. If this
runbook conflicts with an approved OpenSpec specification, the OpenSpec
specification wins.

Any change to source-column mapping, canonical schema, identity authority,
ambiguity handling, PDU-to-room resolution, codec selection, or enrichment
lifecycle requires a semantic OpenSpec change before production implementation.

## Data flow

The approved boundary is:

```text
organization Excel workbook
    -> offline importer
    -> canonical versioned JSON snapshot
    -> runtime loader
    -> immutable indexed EquipmentInventory
    -> application-owned resolution/orchestration
```

Excel is an offline source format only. Normal diagnostic runtime code must not
parse `.xlsx` files and must not require a spreadsheet library.

The deployment-local runtime snapshot is:

```text
equipment_inventory.local.json
```

The real workbook and the generated production snapshot are operational data.
They must not be committed to Git. Tests use synthetic inventory only.

## Key implementation files

```text
core/equipment_inventory.py
tools/import_equipment_inventory.py
core/room_context.py
core/related_codec_status.py
gui/pdu_room_codec_enrichment.py
gui/pdu_controller.py
gui/screens/pdu_screen.py
tests/test_equipment_inventory.py
tests/test_pdu_room_codec_enrichment.py
```

## Authoritative Excel mapping

The inspected organization workbook uses this schema-v1 mapping:

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

Importer-only evidence may include:

```text
Производитель
Модель
SmartRoomID контроллера
```

These evidence columns do not become separate canonical schema-v1 fields.
`diagnostic_model` is populated only through an explicit reviewed mapping to an
application-supported model name. Approximate matching, fuzzy matching, and
model guessing are forbidden.

## Identity rules

### Equipment identity

`SmartRoomID` is the only authoritative source for canonical `record_id`.

Missing, blank-after-normalization, or duplicate `SmartRoomID` is a fatal
source-contract error. It blocks publication of the candidate snapshot.

Do not manufacture fallback identity from:

- workbook row number or order;
- IP or MAC address;
- serial number;
- room ID or room name;
- model text;
- UUID, timestamp, suffix, or counter.

### Room identity

`ID комнаты` is authoritative for `room_id`.

`Название комнаты` maps to `room_name` and is display evidence only. Never use
`room_name` as fallback identity, never merge rooms by display name, and never
select one conflicting name as authoritative.

## Canonical snapshot schema v1

The JSON root contains required fields:

```text
schema_version
snapshot_id
records
```

Optional generation metadata:

```text
generated_at
source_row_count
```

Every canonical record contains exactly:

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
```

Required non-null record fields:

```text
record_id
device_kind
```

Nullable fields:

```text
source_model
diagnostic_model
ip_address
mac_address
serial_number
room_id
room_name
```

Allowed `device_kind` values:

```text
pdu
video_codec
other
```

Exact source-type mapping:

```text
Video Conference -> video_codec
БРП              -> pdu
all other values -> other
```

Recognized model evidence must not override the exact `Тип модели` mapping.

## Normalization

Canonical text uses Unicode NFC normalization and trims leading and trailing
whitespace. Empty nullable text becomes `null`.

When present, IP must be canonical dotted-decimal IPv4. Invalid source IP is
represented as `null` plus a structured non-fatal import issue when the record
is otherwise representable.

When present, MAC must use lowercase colon-separated text:

```text
aa:bb:cc:dd:ee:ff
```

Invalid source MAC is represented as `null` plus a structured non-fatal import
issue when the record is otherwise representable.

## Snapshot identity and publication

Schema v1 uses deterministic content identity:

```text
snapshot_id = "sha256:" + sha256(canonical identity payload)
```

The identity payload contains only:

```text
schema_version
records
```

Records are sorted by normalized `record_id`. `generated_at` and
`source_row_count` do not affect identity. The runtime loader recomputes the
digest and rejects a mismatch as `INVALID_SNAPSHOT`.

Publication is atomic. A fatal import failure must leave the previous valid
production snapshot intact and must not expose a partial candidate at the
production path.

## Runtime inventory boundary

A successful load creates one immutable `EquipmentInventory` revision and
prebuilds multi-value indexes equivalent to:

```text
ip_address -> tuple[EquipmentRecord, ...]
room_id -> tuple[EquipmentRecord, ...]
(room_id, device_kind) -> tuple[EquipmentRecord, ...]
```

Public query methods are:

```python
inventory.find_by_ip(ip_address)
inventory.find_room_equipment(room_id)
inventory.find_by_room_and_kind(room_id, device_kind)
```

Every normal query returns a tuple containing zero, one, or many records.
The inventory layer preserves multiplicity and does not classify it as
`NOT_FOUND`, `RESOLVED`, or `AMBIGUOUS`.

Do not use implicit first-match selection such as `records[0]` or `codecs[0]`.
Interpretation of zero/one/many belongs to application/composition code.

## Structured runtime load failures

Runtime inventory loading classifies failures as exactly one of:

```text
NOT_FOUND
UNREADABLE
INVALID_FORMAT
UNSUPPORTED_SCHEMA
INVALID_SNAPSHOT
```

No failed load may publish partial records, indexes, or an
`EquipmentInventory` instance.

## PDU to room to codec resolution

Resolution starts only after a current successful user-initiated PDU refresh
has been accepted by `PDUController`.

A mutation reconciliation refresh, stale callback, PDU error, progress event,
or completion without accepted success must not start enrichment.

The exact resolution sequence is:

```text
1. Receive the accepted current PDU IP.
2. Call inventory.find_by_ip(pdu_ip).
3. Require exactly one total IP match.
4. Require that record.device_kind == "pdu".
5. Require non-null authoritative room_id.
6. Call inventory.find_room_equipment(room_id) for display consistency evidence.
7. Call inventory.find_by_room_and_kind(room_id, "video_codec").
8. Require exactly one codec record.
9. Require non-null canonical codec ip_address.
10. Require an exact supported codec diagnostic_model.
11. Bind the result to the inventory snapshot and accepted PDU context.
12. Run an independent read-only codec-status operation.
13. Render only accepted current non-secret presentation on PDUScreen.
```

Duplicate IP ambiguity is evaluated before filtering by device kind. If one PDU
and one non-PDU share the IP, the result remains `AMBIGUOUS_PDU_IP`.

Room name never replaces room ID. When one `room_id` has multiple distinct room
names, no name is selected; a safe `ROOM_NAME_CONFLICT` warning is exposed and
resolution continues by `room_id`.

## Resolution statuses

```text
INVENTORY_UNAVAILABLE
PDU_NOT_FOUND
AMBIGUOUS_PDU_IP
PDU_KIND_MISMATCH
ROOM_UNRESOLVED
CODEC_NOT_FOUND
AMBIGUOUS_CODEC
CODEC_IP_MISSING
CODEC_UNSUPPORTED
RESOLVED
```

These statuses are application resolution outcomes. They are not emitted by the
inventory query layer itself.

## Supported related-codec models

Automatic related-codec diagnostics use exact canonical `diagnostic_model`
values only:

```text
Huawei TE20
Huawei TE40
CloudLink Bar 310
Polycom RPG 310
```

Do not choose a handler from `source_model`, manufacturer substrings, similar
text, source row order, or a first matching record.

## Related-codec operation boundary

Automatic related-codec diagnostics are read-only and obtain only narrow
normalized status such as:

```text
call_status
presentation_status
```

They must not issue Wake, volume, mute, SIP update, call placement, call
termination, presentation control, or any other state-changing command.

The operation uses an independent serialized `InteractiveSessionController` or
equivalent lane. It must not reuse:

```text
CodecScreen.interactive_controller
generic _active_request
global current_worker
```

A user-selected codec context and an automatically resolved related codec must
remain independent.

## Generation and stale-work safety

Every accepted PDU refresh creates a distinct enrichment generation, including
a repeat refresh for the same PDU and the same resolved codec.

Required order:

```text
new enrichment generation
    -> dedicated session invalidate_context()
    -> resolve inventory and codec context
    -> activate dedicated codec context
    -> submit one read-only status operation
```

A stale queued operation must be dropped before handler acquisition and before
network I/O. A stale in-flight result must not:

- update the GUI;
- restore old room or codec values;
- persist a credential index;
- persist a connection profile;
- change PDU lifecycle state.

Starting a new or repeat PDU refresh, changing PDU model/IP/credential context,
explicit invalidation, or shutdown must supersede old enrichment immediately,
without waiting for replacement success.

## Credential and transport rules

Application/composition code resolves the complete credential chain before
handler or session construction.

One assigned credential is used across all supported transport attempts.
Transport fallback and credential fallback are separate mechanisms.

Credential advancement is allowed only after a structured confirmed
`AuthenticationError` from new-session login. Transport errors, timeouts, SSL
errors, protocol/parser failures, empty or malformed responses, and text such as
`auth`, `401`, or `403` do not authorize credential advancement.

A supported saved connection profile is tried first. Credential index and
profile are persisted only after an accepted current complete success. Stale,
partial, resolution-only, unsupported, and failed outcomes persist nothing.

## PDU result independence

Inventory and related-codec enrichment are optional contextual diagnostics.
Their failure must not convert an accepted PDU success into a PDU failure.

Enrichment failure must not:

- clear accepted PDU device or outlet data;
- disable valid PDU controls;
- change PDU refresh or mutation authority;
- trigger PDU retry or reconciliation;
- open an automatic modal connection error.

Related-room failures are rendered safely and inline.

## Data and secret protection

Do not commit or expose:

- the real organization workbook;
- `equipment_inventory.local.json`;
- real organization inventory in tests;
- complete source rows or complete inventory dumps;
- credential dictionaries or values;
- cookies, Session IDs, CSRF/access tokens;
- handler, worker, transport, or session objects;
- complete raw codec status when a narrow result is sufficient.

Importer and runtime diagnostics should expose only the minimum safe evidence:
issue class, issue code, row reference, safe `record_id` when appropriate, and a
short safe description.

## Checklist for future agent sessions

Before any inventory-related task:

1. Read `RULES.md`.
2. Read this runbook.
3. Read the current root OpenSpec inventory specification.
4. Read the current PDU-room-codec specification or active/archived change when relevant.
5. Verify the current GitHub branch, PR, and `master`; do not rely on old session memory.
6. Preserve zero/one/many semantics and authoritative identity rules.
7. Use only synthetic fixtures.
8. Create a semantic OpenSpec change before changing a normative contract.
9. Use only the repository-local `./openspec.cmd` or `.\openspec.cmd` wrapper.
10. Run focused tests, the full offline suite, strict OpenSpec validation, and Git checks required by `RULES.md`.