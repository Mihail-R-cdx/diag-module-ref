# Design: Inventory switch-port enrichment

## Context

The approved runtime boundary remains:

```text
organization equipment workbook
    + optional network-connection workbook
    -> offline importer
    -> canonical versioned JSON snapshot
    -> runtime EquipmentInventory
    -> application-owned exact dispatch and orchestration
```

Normal diagnostic runtime code must not parse `.xlsx` files or depend on spreadsheet libraries. The second workbook is an offline source only.

The inspected network workbook contains:

```text
sheet: Устройства
required columns for this change:
    MAC-адрес
    IP коммутатора
    Порт

other sheet:
    Изменения
```

The `Изменения` sheet is historical audit data and is not a source of current canonical state. The `Корректная запись` column on `Устройства` is explicitly ignored.

## Goals

1. Reconcile current switch connection evidence into canonical equipment records by normalized MAC only.
2. Preserve all existing primary-workbook authorities and current diagnostic-model reconciliation.
3. Add schema v3 with nullable `switch_ip_address` and `switch_port`.
4. Preserve runtime loading of valid schema-v1 and schema-v2 snapshots.
5. Preserve existing one-workbook conversion behavior until a network source is explicitly supplied.
6. Preserve deterministic identity, strict per-version record validation, and atomic publication.
7. Make ambiguity observable without first-row selection or source-order authority.
8. Keep switch fields passive in runtime during this change.
9. Establish exact public configuration names that the future standalone converter GUI can call without inventing another adapter contract.

## Non-goals

- Do not add the standalone converter GUI or any PyQt dependency.
- Do not read or interpret sheet `Изменения`.
- Do not use or validate `Корректная запись`.
- Do not join by device IP, room address, room name, manufacturer, model, source label, confidence, prefix, row number, or source order.
- Do not add switch discovery, switch credentials, SNMP, SSH, port-state queries, topology validation, or device I/O.
- Do not display switch data in the diagnostic GUI.
- Do not add runtime indexes or public queries for switch IP or port.
- Do not change PDU-room-codec enrichment, diagnostic dispatch, credentials, handlers, controllers, workers, or transports.
- Do not commit production workbooks, generated production snapshots, internal topology, or Graphify output.

## Decision 1: Preserve two explicit conversion modes

The importer supports two intentional modes.

### Existing one-source mode

```text
primary equipment workbook only
    -> schema_version = 2
```

Existing direct API, CLI, and configured-path usage remain valid. No synthetic switch fields are written into a schema-v2 record.

### Network-enriched mode

```text
primary equipment workbook
    + explicitly supplied network workbook
    -> schema_version = 3
```

Supplying a network source explicitly requests schema-v3 conversion. The importer must not silently downgrade that run to schema v2.

The fatal boundary for the requested two-source run is exact:

```text
fatal
    network path/configuration failure
    network workbook unreadable
    worksheet Устройства missing or ambiguous
    required network header missing or ambiguous
    complete candidate fails runtime schema validation
    output publication fails
```

Row-level network quality and reconciliation conditions are non-fatal when the primary candidate remains representable:

```text
non-fatal
    missing or invalid network MAC
    valid MAC with no usable switch IP and no usable port
    invalid or missing switch IP or port
    repeated identical connection rows
    conflicting distinct connection rows
    duplicate primary MAC for enrichment
    network MAC absent from primary inventory
```

This split preserves existing deployment behavior while giving the future operator GUI one explicit two-input schema-v3 path.

## Decision 2: Use a closed network-workbook source contract

Only sheet `Устройства` participates.

The required exact source headers are:

```text
MAC-адрес       -> cross-source join evidence
IP коммутатора  -> switch_ip_address candidate
Порт            -> switch_port candidate
```

Header matching follows the importer's established worksheet/header discovery conventions but does not add aliases for these semantic columns.

All other columns are ignored by canonical reconciliation, including:

```text
№
Производитель
Модель
IP устройства
Адрес помещения
Помещение
Источник
Источник производителя
Уверенность производителя
Префикс производителя
Источник модели
Уверенность модели
Префикс модели
Корректная запись
```

`Корректная запись` is neither required nor optional evidence. Its presence, absence, and value must have no effect on row eligibility, issues, canonical fields, counts used for identity, or publication.

Sheet `Изменения` is not opened as current-state input and cannot add, override, delete, or repair a `Устройства` row.

## Decision 3: Normalize approved fields narrowly

### MAC

Network `MAC-адрес` uses the same canonical MAC normalizer as primary `MAC`:

```text
00:02:2E:81:9D:61
00-02-2E-81-9D-61
0002.2E81.9D61
    -> 00:02:2e:81:9d:61
```

Missing or invalid network MAC cannot participate in the join and produces a structured non-fatal source issue. No fallback identity is manufactured.

### Switch IP

`IP коммутатора`, when present, must normalize to canonical dotted-decimal IPv4. Invalid non-blank input becomes null plus `INVALID_SWITCH_IP`.

### Switch port

`Порт` is canonical nullable text under Unicode NFC normalization and leading/trailing trim. Empty normalized text becomes null. Case and internal text are preserved.

The importer treats the port as an opaque interface identifier. It must not parse or require a particular vendor grammar such as `GigabitEthernet1/0/20`.

## Decision 4: Reconcile by multiplicity on both sides

The importer builds immutable reconciliation groups equivalent to:

```text
primary canonical MAC
    -> all primary EquipmentRecord candidates

network canonical MAC
    -> all distinct usable normalized (switch_ip_address, switch_port) candidates
```

A network row creates a connection candidate only when at least one of `switch_ip_address` or `switch_port` is usable after normalization.

A row with a valid MAC and both normalized connection fields null does not create a connection candidate:

```text
valid MAC + blank switch IP + blank port
    -> no candidate
    -> EMPTY_SWITCH_CONNECTION
```

If invalid non-blank switch IP already produces `INVALID_SWITCH_IP` and the port is null, the row still creates no candidate; `INVALID_SWITCH_IP` is the row-level issue and an additional `EMPTY_SWITCH_CONNECTION` is not required. An empty or unusable row for a MAC does not create ambiguity with another usable row for that same MAC, but it remains visible through its structured issue.

A connection may be assigned only when:

```text
exactly one primary record has the MAC
and
exactly one distinct usable normalized network connection candidate exists
```

The outcome table is:

```text
primary record has null MAC
    -> switch_ip_address = null
    -> switch_port = null
    -> no join attempted

one primary record, no usable network candidate
    -> both switch fields null
    -> absence alone is not a per-record error

one primary record, one distinct usable network candidate
    -> copy each normalized candidate field independently

multiple primary records share the MAC
    -> enrich none of those records
    -> AMBIGUOUS_INVENTORY_MAC_FOR_SWITCH

one primary record, repeated identical usable network candidates
    -> treat as one distinct candidate
    -> DUPLICATE_SWITCH_CONNECTION_SOURCE

one primary record, multiple distinct usable network candidates
    -> enrich neither field
    -> AMBIGUOUS_SWITCH_CONNECTION

network MAC has no primary record
    -> NETWORK_MAC_NOT_IN_INVENTORY
```

No row or registry order may break ambiguity. The importer must not prefer a non-null field, a valid IP, the last row, the first row, a `Корректная запись` value, or matching device IP/model/room evidence.

A unique partial network candidate remains useful:

```text
valid switch IP + null port
    -> preserve switch_ip_address
    -> switch_port = null
    -> MISSING_SWITCH_PORT

blank switch IP + normalized port
    -> switch_ip_address = null
    -> preserve switch_port
    -> MISSING_SWITCH_IP

invalid non-blank switch IP + normalized port
    -> switch_ip_address = null
    -> preserve switch_port
    -> INVALID_SWITCH_IP
```

If multiple usable rows produce different partial or complete normalized pairs, the connection is ambiguous and both canonical fields remain null.

## Decision 5: Add strict schema v3

Schema-v3 records contain all schema-v2 fields plus exactly:

```text
switch_ip_address
switch_port
```

Both are nullable. `switch_ip_address`, when non-null, is canonical IPv4. `switch_port`, when non-null, is normalized non-empty text.

The schema-v3 exact record set is:

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

The deterministic schema-v3 identity payload remains:

```text
schema_version
records sorted by record_id
```

Both switch fields participate in identity. Generation metadata and import-report counters remain outside identity.

Canonical root metadata keeps its existing meaning:

```text
source_row_count
    = number of inspected rows from the primary equipment workbook
```

The network workbook row count is report metadata only. It must not be added to `source_row_count` and must not affect `snapshot_id`.

The loader validates every version against its own exact fields:

```text
schema v1 -> room_vip = null, switch_ip_address = null, switch_port = null
schema v2 -> read room_vip, switch_ip_address = null, switch_port = null
schema v3 -> read room_vip and both switch fields
```

A hybrid record claiming v1/v2 while containing later-version fields is invalid. Unknown schema versions remain unsupported.

## Decision 6: Runtime behavior remains passive

`EquipmentRecord` exposes both new nullable attributes after loading schema v3. No current index includes them and no current public query uses them.

Existing indexes remain equivalent to:

```text
ip_address -> tuple[EquipmentRecord, ...]
room_id -> tuple[EquipmentRecord, ...]
(room_id, device_kind) -> tuple[EquipmentRecord, ...]
```

Diagnostic dispatch, PDU-room-codec resolution, room VIP aggregation, credential selection, and device operations ignore both switch fields in this change.

## Decision 7: Extend configuration with exact public names

The public configuration and invocation contract is fixed as follows:

```text
module configuration variable
    NETWORK_XLSX_PATH

environment variable
    DIAG_INVENTORY_NETWORK_XLSX

CLI option
    --network-source

direct API keyword
    network_source_path
```

The direct API signature is:

```python
import_equipment_inventory(
    source_path,
    *,
    network_source_path=None,
    output_path=None,
    generated_at=None,
)
```

Semantic priority is:

```text
explicit API/CLI network source
environment variable DIAG_INVENTORY_NETWORK_XLSX
module configuration NETWORK_XLSX_PATH when explicitly configured
no network source -> intentional schema-v2 mode
```

All configured paths are resolved absolute paths before workbook I/O. No user-specific workbook path is committed. The future standalone GUI must call this approved direct API keyword rather than create a second reconciliation entry point.

## Decision 8: Preserve structured reporting and atomic publication

The existing `ImportResult`/JSON report remains the single conversion result. It is extended only with safe optional network-run context and counts needed to validate two-source conversion, such as network worksheet/header, network source row count, distinct normalized network MAC count, enriched record count, and ambiguity count.

Every non-empty network source row is accounted for as one or more of:

```text
a usable connection candidate
a structured row-level issue
```

A row may contribute both a usable partial candidate and a missing/invalid-field issue. No non-empty network row disappears silently.

Fatal conversion outcomes are limited to configuration/path failure, unreadable workbook, missing or ambiguous required network structure, candidate schema validation failure, and publication failure. Row-level quality, duplication, unmatched, and ambiguity outcomes remain non-fatal and preserve otherwise valid primary records with null switch fields where no unique candidate exists.

Normal issues may expose safe sheet name, row number, issue code, and canonical `record_id` where available. They must not dump complete source rows, complete workbook contents, production snapshots, or unrelated network topology.

The complete candidate is validated through the runtime schema loader before publication. Any fatal primary-source error, fatal network-source error, candidate-validation error, or output-write error leaves the previous output intact. Publication remains atomic.

## Regression coverage

Synthetic tests must cover at least:

- one-source conversion still emits schema v2 with unchanged identity behavior;
- exact public names `NETWORK_XLSX_PATH`, `DIAG_INVENTORY_NETWORK_XLSX`, `--network-source`, and `network_source_path`;
- two-source conversion emits schema v3;
- exact sheet/header requirements;
- complete ignoring of `Изменения` and `Корректная запись`;
- canonical MAC joins across supported textual forms;
- no join by IP, room, manufacturer, model, or source order;
- one unique complete connection;
- unique partial connection;
- valid MAC with blank IP and blank port producing `EMPTY_SWITCH_CONNECTION` and no candidate;
- an empty row not creating ambiguity with another usable row for the same MAC;
- invalid/missing network MAC;
- invalid/missing switch IP;
- missing switch port;
- duplicate identical network rows;
- distinct conflicting network rows;
- duplicate primary MAC;
- network MAC absent from primary inventory;
- exact fatal versus non-fatal boundary;
- schema-v3 `source_row_count` remaining the primary-workbook row count;
- v1/v2/v3 loader compatibility and runtime null adaptation;
- strict rejection of hybrid records and unsupported schema versions;
- schema-v3 identity changes when either switch field changes;
- unchanged existing inventory indexes and queries;
- unchanged diagnostic dispatch, PDU enrichment, room context, and credential behavior;
- atomic preservation of previous output on every fatal two-source failure.

All fixtures use synthetic addresses and identifiers.

## Rollout

1. Approve this architecture at its exact remote HEAD.
2. Implement the importer, schema-v3 loader support, focused tests, and runbook updates only.
3. Run focused and full offline tests plus strict OpenSpec validation.
4. Independently validate the exact published implementation HEAD in a clean detached worktree.
5. Perform disposable archive-applicability validation because root requirements are modified and added.
6. Archive and perform post-archive checks only after independent approval and explicit authorization.
7. Merge before starting the separate `inventory-converter-operator-workflow` change.

Production workbooks and the generated deployment snapshot are regenerated only during the later authorized operational rollout, not committed during this change.
