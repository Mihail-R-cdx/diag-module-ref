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
- `null`: source value is absent, unsupported, or cannot be resolved consistently.

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

If records sharing one authoritative `room_id` contain conflicting non-null VIP values, the importer preserves the records, reports `ROOM_VIP_CONFLICT`, and room-context resolution exposes unknown/conflicted VIP state rather than selecting one value.

### 3. Equipment room context is application-owned and read-only

A shared pure resolver accepts the loaded immutable inventory and current equipment IP. It:

1. normalizes and queries the exact IP;
2. requires exactly one total IP match before interpreting device kind;
3. requires authoritative `room_id` for room resolution;
4. reads all records for that room;
5. derives room address from consistent `room_name` evidence;
6. derives VIP state from consistent `room_vip` evidence;
7. returns structured status and warnings without network I/O.

The resolver never uses `room_name` as fallback identity and never uses implicit first-match selection.

The existing PDU-to-related-codec flow may compose this shared room context with its codec-specific resolution. Related-codec diagnostics remain independent and read-only.

### 4. Presentation contract

A reusable room-information presentation model/widget renders:

```text
Адрес: <room_name or safe unavailable text>
VIP: ДА | НЕТ | НЕТ ДАННЫХ | КОНФЛИКТ ДАННЫХ
```

PDU behavior:

- the VIP line is placed above the existing room-characteristics block;
- `VIP: ДА` is visually prominent;
- the existing room and related-codec information remains in its current block;
- enrichment failure never converts accepted PDU success into PDU failure.

Other equipment pages:

- the shared room-information block is placed at the bottom of the equipment page;
- it shows address and VIP state only;
- it does not perform device or room network operations.

### 5. Lifecycle and stale-context safety

Changing selected model, IP, credential context, page context, or starting a superseding refresh clears or invalidates prior room presentation immediately.

Room context may be rendered only when it matches the current accepted equipment model/IP context and current inventory snapshot. A stale worker result or old device refresh must not restore prior address or VIP values.

Inventory absence, ambiguous IP, missing room identity, or room evidence conflict is rendered inline and must not trigger a modal connection error or change device diagnostic success/failure authority.

### 6. Converter absolute-path configuration

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
- Room VIP values may be inconsistent across equipment rows: preserve multiplicity, emit structured conflict, render unknown.
- Shared GUI integration may duplicate logic: use one presentation model/widget and screen-specific placement only.
- Stale room data may remain visible after context change: invalidate before new lookup or I/O and test supersession.
- Local path configuration may leak workstation details: use environment variables and resolved `Path` objects, never committed concrete user paths.
