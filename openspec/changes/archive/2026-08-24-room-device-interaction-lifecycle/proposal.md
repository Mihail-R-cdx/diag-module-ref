## Why

`room-equipment-diagnostic-tree` establishes authoritative room identity, deterministic tree membership, exact per-record diagnostic state, serialized one-shot acquisition, and a presentation-only terminal room state. The remaining product workflow is intentionally deferred: after the automatic room cycle finishes, the operator must be able to interact safely with the exact expanded room record without falling back to the old single-device widget/session authority.

The application already has model-specific live polling, local refresh, call-log and other auxiliary reads, Matrix/PDU state-changing commands, credential fallback, and reconciliation behavior. Reusing those capabilities directly from room-tree widgets would be unsafe because the top source IP may differ from the expanded row, reusable screens are not state authority, two records may use the same model/screen class, and stale/persistent sessions can outlive a row switch.

This change therefore introduces one application-owned post-cycle interaction lifecycle bound to the exact current room record. It also removes the legacy PDU-to-room-to-related-codec enrichment path and duplicated PDU room/codec presentation because the room tree now represents and diagnoses the codec independently.

This change depends on the archived `room-equipment-diagnostic-tree` architecture and is initially authored as a stacked change on its published archive HEAD until PR #31 is merged.

## What Changes

- Bind every room-mode live, local Refresh, auxiliary read, Debug context, and state-changing operation to the exact current room record and room generation rather than the top source IP or reusable widget state.
- Keep authoritative state/cache per record; reusable device screens remain temporary projections and never become request/session authority.
- Start post-cycle live only for the latest currently expanded successfully diagnosed row that supports live; collapse or row switch retires the previous live context before another live/network action may start.
- Serialize room post-cycle network work. No room live, local Refresh, auxiliary read, mutation, or reconciliation runs in parallel with another room interactive network operation.
- Use bounded `invalidate -> cleanup/release -> next I/O` handoff. Cleanup timeout abandons old authority, ignores late callbacks, and degrades only the affected record rather than blocking the whole room forever.
- Make local per-device Refresh available only for the exact expanded connected row. It stops live first, performs a fresh exact-row read-only diagnostic lifecycle, atomically replaces cache only on accepted usable success, and requires a full top Refresh after terminal failure.
- Make auxiliary read-only operations such as `Журнал звонков` exact-row operations. They stop live, reuse approved structured credential fallback, clean up deterministically, and restore live after ordinary non-connection failure when the row remains current.
- Keep `Отладка` as a pure local exact-row log/terminal presentation. Opening Debug does not itself create device I/O or stop live.
- Treat confirmed state-changing intent as a separate lifecycle: confirmation first, then live retirement, then one mutation attempt, then mandatory readback/reconciliation. Command ACK alone is not terminal success and cannot update authoritative cache.
- For mutation failure, ambiguous outcome, or unconfirmed reconciliation, do not blindly repeat the state-changing command. Keep the prior cache visibly stale/unconfirmed, disable further state-changing actions for that record, and require top full Refresh for recovery. Typed connection/session loss additionally moves the row to `соединение потеряно`.
- Preserve application-owned credential selection/fallback. Credential candidates remain model-wide; successful candidate/profile memory remains exact `model + IP`; handlers/workers do not iterate candidates. Structured authentication failure is the only retry authority before state-changing delivery can occur.
- Define post-cycle degradation as per-record: one broken device does not disable other successfully diagnosed room records.
- Keep the bottom room result historical: `Последнее обновление` is the completion time of the last full room cycle; local/live/auxiliary/mutation work does not rewrite it. Post-cycle degradation may change the global message to `Есть проблемы с соединением`, but only a new full room cycle can restore a clean room summary.
- Make top full Refresh the room-wide recovery/supersession action for read-only activity. It clears the room context and repeats the full process as a first connection. It is not allowed to interrupt an already confirmed state-changing command before that command reaches its mutation/reconciliation terminal boundary.
- Define IP/credential context changes: editing the source IP invalidates the old room context immediately; an actual saved credential-chain change stops live, invalidates sessions, clears tree/room state, and requires a new Enter/full Refresh. Password Cancel or Save-without-effective-change is a no-op.
- Remove the legacy `pdu-room-codec-enrichment` lifecycle, dedicated related-codec lane, duplicated room/VIP/codec block, and PDU-hosted CloudLink microphone meter. PDU rows retain their own device diagnostics and controls; related codecs appear only as independent room-tree rows.
- Preserve the legacy `room_id = null` single-device path and its existing interactive behavior; this change only replaces post-cycle interaction authority in room mode.

## Target Flow

```text
terminal room cycle
    -> current expanded exact record (optional)
    -> application-owned RoomInteractionCoordinator
        -> optional live start for current connected row
        -> user interaction
            local Refresh:
                stop live -> bounded cleanup -> exact-row read-only refresh
                -> accepted cache replacement or terminal row failure
            auxiliary read:
                stop live -> bounded cleanup -> exact-row auxiliary operation
                -> cleanup -> resume live if still current and usable
            state-changing command:
                confirm -> stop live -> bounded cleanup
                -> one mutation attempt -> mandatory readback/reconciliation
                -> authoritative cache replacement only on confirmed reconciliation
        -> row switch/collapse/currentness change
            invalidate old exact-row context -> bounded cleanup
            -> start only latest current target, if any
```

## Capabilities

### New Capabilities

- `room-device-interaction-lifecycle`: exact-row post-cycle interaction authority, live handoff, local Refresh, auxiliary reads, mutations with mandatory reconciliation, per-record degradation/recovery, room-level control semantics, and bounded cleanup/shutdown.

### Removed Capabilities

- `pdu-room-codec-enrichment`: the PDU page no longer resolves, diagnoses, presents, or live-polls a related codec through a separate enrichment lane. Room membership and codec diagnostics are now owned by the room tree and exact codec row.

## Impact

Implementation is expected to add a focused application-owned room interaction coordinator, extend the existing exact model capability registry with interactive capability bindings, bind reused screens to exact per-record state, adapt existing live/refresh/auxiliary/mutation controllers to explicit room-row contexts, remove legacy PDU enrichment code/UI, and add focused regression coverage for currentness, cleanup, reconciliation, and per-record isolation.

The change must not redesign inventory v4 or automatic room-cycle membership/order, add per-IP secret storage, move credential fallback into handlers/workers, add new device-specific control capabilities, run network I/O on the Qt GUI thread, reintroduce related-codec selection inside PDU logic, or alter the legacy no-room single-device lifecycle except where shared infrastructure must remain compatible.
