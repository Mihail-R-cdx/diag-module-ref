## Why

The diagnostic application needs a stable equipment-inventory boundary before it can
associate a successfully diagnosed PDU with its room and later resolve related room
equipment such as a VCS codec. The current source data is an organization-owned Excel
workbook with roughly 17,000 equipment rows and source-specific columns. Reading that
workbook directly from normal application runtime would couple production behavior to
Excel sheet/column layout, introduce an unnecessary runtime spreadsheet dependency,
and make data-quality and ambiguity handling difficult to test independently.

The first step is therefore to separate source ingestion from runtime lookup. An
offline importer will translate the external workbook into a versioned canonical JSON
snapshot. Runtime code will load that snapshot once through a storage-independent
`EquipmentInventory` boundary and build deterministic in-memory indexes for IP and
room lookups. Duplicate IPs, missing room data, unsupported models, and other source
ambiguities must remain explicit rather than being silently resolved by first-match
selection.

This change deliberately stops at the inventory data boundary. It does not connect a
PDU result to a room, start codec network operations, alter `PDUController`, or reuse
codec polling/session lifecycle. Those concerns belong to the subsequent
`pdu-room-codec-enrichment` change after this inventory contract is implemented and
independently reviewed.

## What Changes

- Add an offline equipment-inventory import boundary that accepts the external Excel
  source and produces a canonical versioned JSON snapshot.
- Keep Excel parsing and any spreadsheet-only dependency outside normal diagnostic
  application runtime imports.
- Define a minimal canonical equipment record containing stable runtime fields for
  equipment identity, source model, optional normalized diagnostic model, IP address,
  optional physical device identifiers, room identity/display name, and device kind.
- Require explicit source-column mapping after the real workbook or a sanitized schema
  sample is inspected; implementation must not guess organization-specific column
  names or sheet layout, including columns for authoritative database identity, MAC
  address, or serial number.
- Validate source rows during import and account for every row as imported or reported
  with a structured issue; do not silently discard or deduplicate conflicting records.
- Use JSON as the first runtime snapshot format and Python standard-library JSON loading
  in the application runtime.
- Add a storage-independent `EquipmentInventory` runtime abstraction so a future
  SQLite adapter can be introduced without changing inventory consumers.
- Build immutable in-memory indexes at load time for IP, room, and room/device-kind
  lookup. Index values preserve all matching records rather than selecting the first.
- Give each loaded snapshot an explicit non-secret identity so a later orchestration
  change can bind derived room context to the exact inventory revision it used.
- Keep real organization Excel files and generated production inventory snapshots out
  of Git; track only importer/schema code, documentation, and synthetic test fixtures.

## Target Data Flow

```text
organization equipment workbook (.xlsx)
        |
        | offline import only
        v
EquipmentInventoryImporter
        |
        +--> structured import report
        |
        v
versioned canonical JSON snapshot
        |
        | runtime load once
        v
EquipmentInventory
        |
        +--> ip_address -> tuple[EquipmentRecord, ...]
        +--> room_id -> tuple[EquipmentRecord, ...]
        +--> (room_id, device_kind) -> tuple[EquipmentRecord, ...]
```

## Capabilities

### New Capabilities

- `equipment-inventory-snapshot`: define offline workbook conversion, canonical
  snapshot schema, validation and ambiguity preservation, runtime loading, immutable
  in-memory indexes, storage abstraction, and deployment-data isolation.

### Modified Capabilities

None. This first change introduces an independent inventory capability and does not yet
modify PDU, codec, diagnostic-shell, credential, or request-lifecycle behavior.

## Impact

Implementation is expected to add a focused runtime inventory module, an offline import
tool, synthetic fixtures, tests, and local-data ignore rules. It may add an import-only
spreadsheet dependency such as `openpyxl`, but normal application runtime modules must
not import or require it.

No existing device handler, worker, controller, credential policy, transport fallback,
interactive codec session, PDU lifecycle, Qt screen, or network behavior is changed by
this change. Real production inventory data is deployment-local and is not part of the
repository or test fixtures.
