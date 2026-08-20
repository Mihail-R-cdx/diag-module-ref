## Why

The planned room-equipment diagnostic tree needs one canonical inventory snapshot that
contains the room address visible in the organization workbook and exposes the same record
shape regardless of whether optional switch-connection enrichment was configured during
import. The current importer drops the source column `Адрес комнаты` and publishes schema
v2 for primary-only conversion or schema v3 for primary-plus-network conversion. That
forces later application orchestration to branch on import mode and leaves no canonical
room-address value for the GUI.

The existing importer also treats disagreement between display metadata on records sharing
one authoritative `room_id` as a room-level consistency problem. The approved direction for
the room diagnostic workflow is simpler: `ID комнаты`/`room_id` is the only room identity
authority, while `room_name`, `room_address`, and `room_vip` remain per-record display
metadata. The importer must preserve those source values without deciding which display
value is correct for a room. Selection of display metadata for a concrete room session
belongs to the later room-orchestration change.

This change therefore upgrades only the equipment-inventory data contract. It does not add
the room tree, sequential diagnostics, per-record GUI state, live polling, state-changing
controls, credential changes, or related-device network orchestration.

## What Changes

- Add the exact primary-workbook source column `Адрес комнаты` and map it to nullable
  canonical `room_address`.
- Require the `Адрес комнаты` header for every new import. A blank cell remains valid and
  becomes `room_address = null`; a missing or ambiguous required header is a fatal source
  structure failure and preserves the previous published snapshot.
- Introduce canonical schema v4 as the only schema emitted by newly successful imports.
- Make schema v4 independent of import mode: primary-only and primary-plus-network imports
  both produce the same exact record shape containing `room_vip`, `room_address`,
  `switch_ip_address`, and `switch_port`. In primary-only mode both switch fields are null.
- Preserve the existing optional network-workbook contract and MAC-only reconciliation.
  Configuring an invalid network source remains fatal and must not silently fall back to a
  primary-only conversion.
- Keep valid schema v1, v2, and v3 snapshots loadable. The runtime loader adapts missing
  newer fields to null while still validating each declared historical version against its
  exact original record shape and deterministic identity.
- Validate schema v4 strictly. Missing, extra, or hybrid v4 record fields are invalid; the
  loader must not repair a malformed v4 snapshot.
- Include `room_address` and all other schema-v4 record fields in deterministic snapshot
  identity while keeping generation/report metadata outside identity.
- Stop importer-level conflict diagnostics for differing `room_name` or `room_vip` values
  within one `room_id`, and do not introduce a `room_address` conflict diagnostic. The
  importer preserves each record and its display metadata exactly after canonical field
  normalization. Existing runtime room-display selection is not redesigned by this change.
- Update importer/preflight/report semantics so any candidate schema produced by current
  conversion or combined preflight is schema v4.

## Target Data Flow

```text
primary organization workbook
    + optional approved network workbook
    -> offline importer
    -> canonical schema-v4 JSON snapshot
    -> strict runtime loader
    -> immutable EquipmentInventory

schema v1/v2/v3 deployment snapshot
    -> strict historical-version validation
    -> runtime adaptation with room_address = null when absent historically
```

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `equipment-inventory-snapshot`: add room-address metadata, make schema v4 the single
  generated schema for both import modes, preserve strict v1-v3 backward loading, and
  remove importer authority to classify disagreements among room display attributes.

## Impact

Implementation is expected to modify the offline importer, the canonical inventory model
and loader, synthetic inventory fixtures/tests, and the equipment-inventory runbook. It
must not commit real workbooks or generated production snapshots.

No normal diagnostic handler, worker, credential fallback chain, transport policy, PDU or
codec controller, live polling lifecycle, Qt room tree, or state-changing device behavior
is changed by this inventory-only change. Those behaviors belong to subsequent reviewed
OpenSpec changes.
