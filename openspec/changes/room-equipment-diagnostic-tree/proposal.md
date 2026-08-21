## Why

The application currently treats a diagnostic Refresh primarily as one selected device/IP request. Canonical inventory v4 now provides stable `room_id`, `room_name`, `room_address`, `room_vip`, exact `record_id`, canonical `diagnostic_model`, and device IP metadata for every represented equipment record. The next step is to use that approved inventory contract to diagnose the room as a unit rather than duplicating room discovery separately inside individual device pages.

The present PDU-related-codec enrichment is intentionally narrow and PDU-centric: it resolves one PDU, expects one related codec, and owns a separate related-codec read lane. It cannot represent all equipment records in the room, multiple supported devices, unsupported rows, missing IPs, or independent per-record diagnostic state. Reusing that enrichment as the room-tree authority would also preserve the wrong ownership direction: a PDU would continue to own room discovery and codec diagnostics.

The room workflow therefore needs a new application-owned boundary that resolves one source IP to one authoritative room, builds a deterministic equipment tree for that room, and performs one bounded read-only diagnostic attempt for every eligible supported record in strict sequence. The tree must retain exact per-record state rather than treating reusable screen widgets as the source of truth. Model-specific workers/controllers may be reused behind adapters, but transport details and persistent polling lifecycles must not leak into the room orchestrator.

This change deliberately stops at automatic one-shot room diagnostics. Post-cycle live polling, local per-device Refresh, call-log/auxiliary reads, state-changing commands, mandatory mutation readback, and post-cycle interaction recovery belong to the following `room-device-interaction-lifecycle` change.

## What Changes

- Introduce a room-diagnostic session resolved from the current canonical inventory before ordinary model-specific diagnostic dispatch.
- With a valid inventory, require the entered source IP to resolve to exactly one canonical record. Zero or multiple source records fail closed and do not open manual model fallback.
- When that unique source record has a non-null `room_id`, enter room-tree mode even when the source record itself is unsupported or has no canonical diagnostic model. `room_id` remains the only room identity authority.
- When the unique source record has no `room_id`, retain legacy single-device diagnostics only if its exact canonical `diagnostic_model` is supported. A valid inventory with an unresolved/unsupported model does not authorize fallback guessing.
- Keep manual model fallback only for inventory unavailable/unloadable/corrupt conditions. The same fail-closed principle applies to credential configuration: a valid inventory with zero/many/unmapped/unsupported IP resolution does not become a model-guessing path.
- Build a room equipment tree from every canonical record with the resolved `room_id`. The source record is first; remaining records use canonical `record_id` order.
- Present room name, address, and VIP once in a shared room header. For each field, use the source-record value first, otherwise the first nonblank/non-null value in canonical room-record order. Display metadata never replaces `room_id`, and the room workflow does not perform same-room display conflict arbitration.
- Give every room row independent authoritative runtime state keyed by exact canonical record identity (`record_id` plus its exact model/IP context). Reusable/heavy device widgets become temporary projections of the currently expanded row rather than state owners.
- Extend the existing application-owned exact model dispatch into one model capability registry that also provides the one-shot diagnostic adapter/view binding needed by room mode. Runtime support remains exact-only by canonical `diagnostic_model`; source text is never re-recognized at runtime.
- Introduce a unified one-shot adapter contract so the room orchestrator receives model-neutral partial data, usable final success, usable final success with warning, terminal failure, and cleanup completion. Model-specific protocol/session details remain behind existing controllers/workers/handlers.
- Execute the automatic room cycle strictly sequentially: `ping -> diagnostic attempt -> final accepted outcome -> cleanup/release -> next record`. No two room records perform diagnostic network I/O concurrently.
- Preserve application-owned credential fallback. A worker/handler/adapter gets one assigned candidate; only structured new-login `AuthenticationError` may advance the request-scoped candidate cursor. Saved supported index/profile remains first for the exact model/IP context and is persisted only after accepted success. The existing PCS4i credentialless exception remains unchanged.
- Represent unsupported, missing-IP, and same-room duplicate-IP records without device I/O. Duplicate-IP ambiguity is calculated over all room records, including unsupported records, and is not resolved by model/kind filtering.
- Keep partial data visible without treating it as success. Preserve model-specific usable-success-with-warning behavior (for example optional enrichment failures) while distinguishing it from terminal failure.
- Bound cleanup for every one-shot lifecycle. Cleanup timeout abandons the old lifecycle, blocks its late callbacks, marks the affected row degraded/failed as appropriate, and continues the room queue instead of hanging the whole room.
- Keep all automatic room diagnostic network work off the Qt GUI thread. Automatic per-device modal/progress/terminal windows are suppressed; row status, row detail, and global room status carry the outcome.
- Make top-level Refresh in room mode a full room refresh: invalidate the prior room generation, rebuild room context/tree/cache from the current source IP, and run the complete sequential room cycle again.
- Do not start the legacy PDU->room->codec enrichment from automatic room PDU one-shot diagnostics. The existing PDU enrichment remains available only through its existing legacy user-PDU lifecycle until the later interaction change removes/replaces that duplication.

## Target Flow

```text
source IP
    -> validate IPv4
    -> resolve exact source record from immutable inventory
    -> if source has room_id:
           build RoomDiagnosticSession
           -> build deterministic room rows
           -> sequential one-shot room cycle
              row A: ping -> attempt/fallback -> final -> cleanup
              row B: ping -> attempt/fallback -> final -> cleanup
              ...
           -> terminal room summary + per-record authoritative cache
       else if source has exact supported diagnostic_model:
           existing single-device diagnostic flow
       else:
           safe fail-closed outcome

inventory unavailable/unloadable/corrupt
    -> existing explicit manual model fallback path
```

## Capabilities

### New Capabilities

- `room-equipment-diagnostics`: authoritative room-session resolution, deterministic tree membership/order, shared room metadata presentation, per-record state/cache, unified model/adapter authority, sequential one-shot diagnostics, bounded cleanup, stale-generation isolation, and terminal room status.

### Modified Capabilities

- `diagnostic-application-shell`: change source-IP and credential-configuration resolution so valid inventory enters room mode or fails closed instead of treating every unresolved model as manual-fallback authority.
- `request-lifecycle-and-recovery`: add room-generation/per-record callback isolation and bounded serialized one-shot lifecycle rules.
- `device-diagnostics-and-control`: define how existing supported model diagnostic paths are adapted to one-shot room acquisition without changing their approved transport/credential ownership.

## Impact

Implementation is expected to add a focused room-session/orchestration boundary, per-record state model, tree presentation, capability-registry extensions, one-shot adapters around existing model-specific lifecycle owners, and regression coverage across source resolution, row eligibility, sequencing, cleanup, and GUI projection.

The implementation must not move network I/O to the Qt GUI thread, move credential fallback into handlers/workers, infer models from `source_model`, change canonical inventory schema v4, or commit operational inventory/credentials.

The old PDU-room-codec enrichment root capability is not removed by this change. Automatic room PDU diagnostics must avoid triggering it, and tree-mode room metadata must be presented only in the shared room header. Full removal/reconciliation of the legacy enrichment and all post-cycle interactive lifecycle is deferred to `room-device-interaction-lifecycle`.
