# Design: equipment-room-vip-context

## Context

The current canonical inventory schema is closed and versioned as schema v1. Records contain room identity and room name but no VIP state. The importer maps an inspected workbook into an immutable JSON snapshot; runtime code loads only JSON and never parses Excel.

The PDU flow already resolves PDU IP to room and related codec context after an accepted current refresh. Other device pages use the selected model/IP context but do not expose room information.

## Goals

- carry the room VIP flag from the workbook into runtime inventory without weakening snapshot validation;
- expose one consistent room presentation contract to all equipment screens;
- preserve stale-operation and identity safety;
- keep local absolute paths configurable without committing workstation-specific values.

## Non-Goals

- parsing Excel during normal application runtime;
- changing credential, transport, retry, or device-handler ownership;
- using room name as room identity;
- choosing the first record when IP or room evidence is ambiguous;
- committing the real workbook or generated production JSON;
- refreshing Graphify artifacts.

## Decisions

### 1. Schema v2 adds nullable `room_vip`

New snapshots use `schema_version = 2`. Every schema-v2 record contains exactly one additional field:

```text
room_vip: true | false | null
```

Meaning:

- `true`: source explicitly identifies the room as VIP;
- `false`: source explicitly identifies the room as non-VIP;
- `null`: source value is absent, unsupported, or cannot be resolved for that record.

The runtime loader accepts existing schema-v1 snapshots and adapts them to `room_vip = null`. It publishes no partially parsed inventory and continues to verify deterministic snapshot identity under the source schema version.

### 2. Authoritative source mapping and normalization

The inspected workbook column is `VIP`. The importer treats it as room display/context data rather than equipment identity.

Accepted source values are normalized explicitly:

```text
Excel boolean true                 -> true
Excel boolean false                -> false
1, "1", "да", "true", "yes"     -> true
0, "0", "нет", "false", "no"    -> false
blank                              -> null
any other non-blank value          -> null + structured INVALID_ROOM_VIP issue
```

String comparison is trimmed and case-insensitive after Unicode normalization. Approximate or substring interpretation is forbidden.

### 3. Room VIP aggregation is room-wide and deterministic

The resolver and importer evaluate all records sharing one authoritative non-null `room_id`. Null is missing evidence, not a contradictory value.

```text
no room records                          -> unresolved room
all values null                          -> NO_DATA
true plus only true/null                 -> VIP_TRUE
false plus only false/null               -> VIP_FALSE
at least one true and at least one false -> CONFLICT
```

Only the final case produces `ROOM_VIP_CONFLICT`. Neither `true + null` nor `false + null` is a conflict. The resolver uses the same table and never chooses a first record or a preferred device kind.

### 4. Equipment room context is application-owned and read-only

A shared pure resolver accepts the loaded immutable inventory and current equipment IP. It:

1. normalizes and queries the exact IP;
2. requires exactly one total IP match before interpreting device kind;
3. requires authoritative `room_id` for room resolution;
4. reads all records for that room;
5. derives room address from consistent `room_name` evidence;
6. derives VIP state through the normative room-wide aggregation table;
7. returns structured status and warnings without network I/O.

The resolver never uses `room_name` as fallback identity and never uses implicit first-match selection.

The existing PDU-to-related-codec flow may compose this shared room context with its codec-specific resolution. Related-codec diagnostics remain independent and read-only.

### 5. Presentation scope uses a centralized equipment-page boundary

A reusable room-information presentation model/widget renders:

```text
Адрес: <room_name or safe unavailable text>
VIP: ДА | НЕТ | НЕТ ДАННЫХ | КОНФЛИКТ ДАННЫХ
```

The application equipment-page registry routes every registered page through a centralized equipment-page shell or equivalent shared layout boundary. That boundary is the architectural definition of supported page coverage:

- every registered non-PDU page receives the shared bottom room-information block automatically;
- PDU registrations are explicitly identified and use the dedicated PDU placement;
- no screen family manually opts in or reimplements room presentation;
- a registry enumeration test proves complete coverage.

PDU behavior:

- the VIP line is placed above the existing room-characteristics block;
- `VIP: ДА` is visually prominent;
- the existing room and related-codec information remains in its current block;
- enrichment failure never converts accepted PDU success into PDU failure.

Non-PDU behavior:

- the shared room-information block is placed at the bottom of the centralized equipment-page layout;
- it shows address and VIP state only;
- it does not perform device or room network operations.

### 6. Non-PDU lifecycle has one publication authority

A change to model, normalized IP, page context, credential context, or accepted inventory snapshot invalidates old presentation immediately and creates a new room-context generation.

The application then resolves and publishes room context from inventory alone for the exact bound tuple:

```text
(model, normalized_ip, snapshot_id, page_context, generation)
```

This resolution does not wait for device refresh success and is not triggered by a device callback. It may be synchronous. If publication is asynchronous, the complete tuple must still match before rendering.

Device refresh start, success, failure, completion, progress, and stale callbacks are not room-context authorities. They may neither rerun nor restore room context. Therefore:

- selecting a new IP can show room data without starting device refresh;
- device refresh failure does not remove independently resolved room data;
- an old refresh completing after context change cannot publish room data for either context;
- starting a refresh for unchanged context does not create a competing room-context generation.

Inventory absence, ambiguous IP, missing room identity, or room evidence conflict is rendered inline and must not trigger a modal connection error or change device diagnostic success/failure authority.

### 7. Converter absolute-path configuration

The converter defines repository-safe configuration variables that always hold resolved absolute `Path` values at execution time:

```text
SOURCE_XLSX_PATH
OUTPUT_JSON_PATH
```

Resolution order:

```text
explicit CLI override
-> environment variable
-> repository-safe default where available
-> clear configuration error
```

Environment variables:

```text
DIAG_INVENTORY_XLSX
DIAG_INVENTORY_JSON
```

No user-specific absolute path is committed. `OUTPUT_JSON_PATH` may default to the repository-local deployment snapshot path. The source workbook has no committed workstation default and therefore requires CLI or environment configuration unless a repository-safe local convention is explicitly approved.

The existing import function remains directly callable with explicit paths for tests.

## Risks and Mitigations

- Schema migration could invalidate old snapshots: runtime explicitly supports v1 and v2.
- Room VIP values may be incomplete or inconsistent: apply the normative room-wide aggregation table and expose conflict only for true plus false.
- Shared GUI integration may omit rare screens: enforce the equipment-page registry/shell invariant and enumerate registrations in tests.
- Device callbacks may compete with room presentation: make inventory context change the only non-PDU publication authority.
- Stale room data may remain visible after context change: invalidate immediately and bind asynchronous results to the full context tuple and generation.
- Local path configuration may leak workstation details: use environment variables and resolved `Path` objects, never committed concrete user paths.
