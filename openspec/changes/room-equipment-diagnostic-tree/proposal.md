## Why

The application currently diagnoses one selected target at a time even though the canonical equipment inventory can identify the authoritative room for an entered source IP and enumerate all equipment records in that room. The next room-centric workflow needs a stable application-level contract before interactive behavior is added: resolve one source IP to one room, show the complete room tree, diagnose every supported eligible room record sequentially, and retain independent exact-record state.

Canonical inventory v4 is already merged and provides the required room metadata. This change therefore introduces the automatic room diagnostic tree and its one-shot lifecycle boundaries without redesigning inventory import, post-cycle live interaction, local row Refresh, auxiliary requests, or state-changing controls.

## What Changes

- Resolve a valid source IP against the immutable canonical inventory with strict zero/one/many semantics. Valid inventory not-found/ambiguous/unmapped/unsupported outcomes fail closed instead of opening manual model fallback.
- Enter room mode whenever exactly one source record has a non-null authoritative `room_id`, even if that source record itself is unsupported.
- Preserve legacy single-device mode for a unique supported source record whose `room_id` is null, and preserve manual model fallback only when inventory is unavailable/unloadable/corrupt.
- Build the complete room tree from every canonical record under the resolved `room_id`, with source first and all remaining records ordered by canonical `record_id`.
- Present shared room name/address/VIP above the tree using source-record value first and canonical-order fallback without conflict arbitration; never show `room_id` as display identity.
- Establish per-record `DeviceRowState`/equivalent application state so reusable device screens become projections rather than state/session authority.
- Extend the existing exact model dispatch into one application-level model capability registry with one-shot room adapter binding; do not add runtime `source_model` recognition.
- Run automatic room diagnostics strictly sequentially: preliminary ping, application-owned credential plan, one assigned attempt at a time, accepted terminal outcome, cleanup/release, then next record.
- Preserve existing structured credential fallback rules, saved exact model/IP successful candidate/profile policy, and the approved PCS4i credentialless exception.
- Normalize partial, usable-success-with-warning, ordinary failure, and cleanup-degraded outcomes without treating optional warnings as total failures.
- Adapt persistent Matrix/DMP/codec diagnostic paths to bounded one-shot acquisition and retire polling/keepalive/session resources before queue advancement.
- Bound cleanup so one stuck device cannot block the entire room; stale callbacks lose authority and the queue may continue after logical abandonment.
- Keep automatic room polling off the Qt GUI thread and non-modal.
- Keep automatic room PDU one-shot acquisition from triggering the existing legacy PDU-to-related-codec enrichment lane.
- Keep MIH-7 room mode presentation-only even after terminal room-cycle completion: reused row network/state-changing/live/auxiliary controls remain disabled or unbound, and top-level `Отладка` is unavailable until exact-row interaction binding is introduced by MIH-8.
- Make accordion initialization/reset deterministic: expandable source row initially expanded; otherwise fully collapsed; top full Refresh never preserves prior secondary selection or resurrects old tree/cache after failed re-resolution.
- Defer post-cycle live handoff, local row Refresh, Call Log/auxiliary operations, mutations/readback, exact-row Debug binding, and post-cycle connection recovery to `room-device-interaction-lifecycle`.

## Target Flow

```text
valid source IPv4
    -> immutable inventory zero/one/many source resolution
    -> authoritative source record + room_id
    -> complete deterministic room tree
    -> exact per-record state
    -> source-first sequential queue
        -> ping
        -> application-owned credential attempt(s)
        -> model one-shot adapter
        -> terminal row outcome
        -> cleanup/release or bounded abandonment
    -> terminal room summary + presentation-only room state
```

## Capabilities

### New Capabilities

- `room-equipment-diagnostics`: authoritative source-to-room resolution, deterministic room tree, per-record state, one-shot adapter contract, sequential automatic room cycle, row/global terminal state, presentation-only post-cycle boundary, deterministic accordion/reset behavior, and stale/cleanup rules.

### Modified Capabilities

- `diagnostic-application-shell`: change diagnostic-start inventory resolution so valid inventory is fail-closed and room-aware, preserve the legacy no-room supported-device path, keep credential configuration network-free, and keep legacy interactive shell actions including Debug fail-closed in MIH-7 room mode.
- `request-lifecycle-and-recovery`: extend request-context/stale-callback and background cleanup requirements for exact room generation/record one-shot work while preserving application-owned credential fallback.
- `device-diagnostics-and-control`: require every supported exact model to expose bounded one-shot room acquisition without changing its approved transport/control semantics, and keep existing network controls disabled/unbound in MIH-7 room mode until MIH-8 supplies exact-row authority.

## Impact

Implementation is expected to modify application/composition routing, room-session state/orchestration, exact model capability registration, one-shot adapters around existing model lifecycle owners, room-tree GUI projection, and focused regression tests.

The change must not alter canonical inventory schema/importer recognition, add per-IP credential storage, move credential fallback into handlers/workers, run network I/O on the Qt GUI thread, silently remove legacy PDU enrichment, or enable exact-row interaction before the following reviewed change.
