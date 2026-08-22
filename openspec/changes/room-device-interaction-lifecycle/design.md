## Context

The archived `room-equipment-diagnostic-tree` change provides the room session identity, deterministic rows, exact per-record `DeviceRowState`, one-shot model adapters, application-owned credential attempt planning, strict sequential acquisition, and bounded one-shot retirement. It deliberately leaves room mode presentation-only after terminal completion.

Production already contains interactive capabilities that predate room mode:

- CloudLink live microphone metering and other persistent/polling diagnostics;
- Matrix persistent session/keepalive and route + quick-refresh behavior;
- DMP polling/meter lifecycle;
- local device Refresh paths;
- codec `Журнал звонков` and other read-only interactive requests;
- PDU mutation/reconciliation lanes;
- model-wide credential chains with exact model/IP successful-index/profile memory;
- reusable Qt screens that historically represented one selected device at a time.

The new architecture must reuse those protocol/model behaviors without allowing a reusable widget, top source IP, prior single-device context, or hidden screen to become authority for a room-row network operation.

The change is stacked initially on published archive HEAD `d3dfb5e50752b0a6c07c223c6bd47b2455a6d684` of `agent/room-equipment-diagnostic-tree` because PR #31 is not yet merged. After PR #31 is merged, this feature branch/PR may be retargeted to current `master` only after reviewing the resulting remote state.

## Goals

- Make the exact expanded room record the only room-mode interactive target authority.
- Preserve per-record authoritative cache and independent same-model records.
- Allow at most one room interactive network lifecycle at a time.
- Reuse approved model-specific live, read-only, credential, mutation, and reconciliation semantics through application-owned adapters/coordinators.
- Separate read-only recovery from state-changing safety so ambiguous mutation outcomes are never blindly replayed.
- Keep Qt responsive and keep cleanup/resource ownership off the GUI thread.
- Retire legacy PDU related-codec enrichment and duplicated presentation.
- Preserve legacy single-device behavior when `room_id = null`.

## Non-Goals

- No inventory/schema/importer redesign.
- No new device model recognition or fuzzy runtime dispatch.
- No new device-specific mutation capability beyond controls already supported in legacy single-device mode.
- No per-IP credential store; credential candidates remain model-wide.
- No parallel room interactive network operations.
- No automatic retry of failed initial room rows, degraded rows, or ambiguous mutations outside the approved credential/session rules.
- No redesign of the automatic room one-shot queue established by MIH-7.

## Architecture

### 1. RoomInteractionCoordinator owns post-cycle authority

Introduce a focused application/composition owner, referred to here as `RoomInteractionCoordinator`. The exact class/module name is not normative. It owns post-cycle room interaction state and receives the current `RoomDiagnosticSession`/equivalent plus the current exact expanded record.

It SHALL NOT read Qt widget text as network authority. Each network-capable interaction captures an immutable context equivalent to:

```text
RoomInteractionContext(
    inventory_snapshot_id,
    room_generation,
    record_id,
    diagnostic_model,
    ip_address,
    row_operation_token,
    interaction_generation,
    credential_context_revision,
)
```

Every queued operation rechecks currentness before handler/session acquisition and before first I/O where separable. Late callbacks from superseded contexts may clean up resources but cannot change row cache, row controls, successful credential/profile memory, child windows, or room summary.

### 2. Per-record state remains authoritative

`DeviceRowState` or a focused companion interaction state remains the authoritative non-secret store for each exact record. It may be extended with explicit interaction fields such as:

```text
interaction_state
live_state
network_actions_enabled
mutation_blocked
stale
unconfirmed_after_command
last_safe_operation_error
```

Qt screens are rebuilt/rebound from the exact row state. Hidden widgets own no background timer, persistent handler, session, credential cursor, or request generation merely because they were once shown.

Two records of the same model remain fully independent. A view bound to record A cannot apply data or callbacks to record B.

### 3. One serialized room interaction lane

Post-cycle room network activity is serialized through one application-owned lane for the active room session. At most one of these may own room interactive network resources at a time:

```text
LIVE
LOCAL_REFRESH
AUXILIARY_READ
MUTATION
RECONCILIATION
```

Pure local presentation actions are outside the network lane. `Отладка` remains local-only under current production behavior and therefore does not stop live by itself.

The coordinator uses a bounded handoff:

```text
invalidate old authority
-> request stop/cancel
-> cleanup/release on owning background lane
-> cleanup complete OR policy timeout/abandonment
-> only then consider next network action
```

A stale pending target never starts merely because an older cleanup eventually finishes. The latest current expanded target is re-evaluated at the handoff boundary.

### 4. Post-cycle live lifecycle

Automatic room one-shot adapters leave no persistent live activity. After the entire room cycle reaches terminal state, the coordinator may start live only when the currently expanded exact row:

- has accepted usable diagnostic state;
- is not stale/degraded/interaction-blocked;
- advertises an existing live capability in the unified model registry.

If no row is expanded or the expanded row has no live capability, no live I/O starts.

Collapse stops current live and starts nothing else. Switching rows immediately changes presentation, invalidates the old live context, and begins bounded cleanup. The new row's network-backed controls remain disabled until the old lifecycle has released authority. If the operator switches A -> B -> C before cleanup of A completes, B receives no I/O and only current C may start after cleanup.

A terminal typed connection/session/auth failure after allowed recovery causes only that exact row to become `соединение потеряно`; cached data remains visible as stale, automatic live restart stops, network/state-changing controls for that row are disabled, and recovery requires top full Refresh. Other room rows remain usable.

### 5. Local exact-row Refresh

Local Refresh exists only for the currently expanded row with accepted connected/usable state. It never acts on a failed initial row, ambiguous row, missing-IP row, unsupported row, or already degraded row.

Sequence:

```text
local Refresh intent
-> lock row network/state-changing actions and top context-changing controls
-> invalidate current live
-> bounded cleanup/release
-> exact-row credential plan
-> preliminary reachability
-> model read-only diagnostic lifecycle
-> accepted usable terminal result
-> cleanup
-> atomically replace authoritative row cache
-> resume live if still current and supported
```

The local Refresh reuses approved structured credential fallback. It does not update the room-level `Последнее обновление` timestamp because that timestamp belongs to the last full room cycle.

Usable final success with optional warning remains successful and may replace cache. A terminal local Refresh failure changes the row to `не удалось подключиться`, stops live, disables local/mutation/auxiliary network controls, and requires top full Refresh for retry. Previously accepted data may remain visible as stale where useful.

### 6. Auxiliary read-only operations

Auxiliary network operations, including `Журнал звонков`, are exact-row read-only operations. Only one may run at a time. Before the auxiliary request starts, active live is invalidated and retired through bounded cleanup.

The operation reuses the existing application-owned credential/session contract:

- start from retained successful candidate/profile where valid;
- advance only after structured new-login `AuthenticationError`;
- ordinary timeout/transport/protocol/parse/business error is not credential-advance authority;
- a successful later candidate may update exact model/IP successful memory under the existing contract.

An ordinary auxiliary parse/business/error outcome that does not prove loss of the connection context does not degrade the row. After cleanup, live may resume when the same row is still current. A terminal typed connection/session failure, or terminal authentication failure after allowed fallback is exhausted, degrades the exact row and requires full room Refresh.

Device-specific auxiliary child windows are bound to exact `record_id + model + IP + room generation`. Collapsing/switching the row closes the child window, invalidates the auxiliary request, and prevents late callbacks from writing into a new context. Explicit reopening begins a fresh acquisition when the underlying feature contract requires one.

Top full Refresh remains a global supersession action during auxiliary read. It invalidates/cancels the auxiliary context, performs bounded cleanup, clears the old room state, and starts a new full room cycle. No auxiliary read may hold the application in an old room generation forever.

### 7. Debug remains local presentation

Current `Отладка` opens accumulated terminal/log presentation and does not itself send network commands. In room mode it is bound to the exact current expanded row, not to the top source IP.

It is unavailable when no supported expandable row is current. Switching/collapsing a row closes the row-specific Debug window so logs cannot be misattributed. Opening or closing current Debug does not stop live. If a future Debug action introduces actual device I/O, that action must explicitly enter the auxiliary-read or state-changing lifecycle; arbitrary network command consoles are not introduced by this change.

### 8. State-changing command and reconciliation lifecycle

A confirmation dialog is a view-only boundary. Opening it does not stop live or mutate operation generations. Cancel is a no-op.

After explicit confirmation, the coordinator:

```text
locks top context-changing controls, accordion, other network actions and mutations
-> invalidates active live
-> bounded cleanup/release
-> creates one exact-row mutation context
-> performs one state-changing command attempt
-> performs mandatory readback/reconciliation
-> reaches terminal confirmed or unconfirmed state
```

No state-changing command is sent if prior live cleanup cannot release authority within policy timeout.

The command is not automatically replayed after any send may have occurred. Credential fallback is permitted only before mutation delivery when structured state proves no state-changing send was attempted or could have been delivered, consistent with existing mutation contracts. Error strings such as `auth`, `401`, or `403` are never retry authority by themselves.

ACK/transport success of the mutation is not authoritative device state. Only successful mandatory readback/reconciliation may atomically replace the exact row's authoritative cache and permit live/network controls to resume.

When command execution fails, outcome is ambiguous, or readback cannot confirm final state:

- do not blindly repeat the mutation;
- retain the previous cache only as stale/unconfirmed presentation;
- show a safe operation-specific error such as `Состояние после команды не подтверждено`;
- keep live stopped;
- block further state-changing commands for that record;
- require top full Refresh for recovery.

The row does not become `не удалось подключиться` merely because a mutation failed. A typed connection/session loss may additionally move it to `соединение потеряно`.

### 9. Top controls, source IP, and credential mutation

During active full room cycle and after a mutation is confirmed through the end of reconciliation, source IP, Password, top full Refresh, and incompatible accordion/network actions are blocked under the existing room-state rules.

During ordinary post-cycle idle/live state, editing the source IP immediately invalidates current room/live/pending-start authority and clears tree/room/cache presentation. Editing alone starts no network I/O. Returning the text to the old IP does not resurrect the old generation; Enter/top Refresh establishes a new context.

`Пароль` remains source-IP/model configuration, not a secondary-row credential editor. It may resolve the currently entered IP through inventory without diagnostics as already approved. In an established tree whose source is unsupported, Password remains unavailable. To configure another device, the operator enters that device IP as the top source; globally ambiguous top-level IP remains fail-closed.

Cancel in Password is a no-op. Saving an effective configuration identical to the prior configuration is also a no-op. A real model-wide credential-chain change invalidates current exact-row sessions/live, clears the current room tree/room info/cache, and requires a new full diagnostic start.

### 10. Room summary and per-record degradation

`Последнее обновление` is the completion time of the most recent full room cycle, even when the room cycle performed no device I/O. Local Refresh, live samples, auxiliary reads, mutations, and reconciliation do not change it.

A post-cycle typed connection loss, failed local Refresh, failed/ambiguous/unconfirmed mutation, or cleanup abandonment may change the global message to `Есть проблемы с соединением`. A successful local action does not rewrite the historical clean/problem result for the entire room. Only a new top full Refresh recomputes the full room outcome.

Degradation is isolated to the exact record. Other connected rows remain expandable and may continue their own permitted live/read/control lifecycle when selected.

### 11. Cleanup and application shutdown

Read-only room activity (live, local Refresh, auxiliary read) is invalidated immediately on application close without a confirmation dialog. The GUI publishes cancellation and does not wait for network timeout; resource cleanup is best-effort on the owning background lane and late callbacks lose authority.

If a state-changing command has been confirmed and may have been sent, close requests warn that the operation may remain unconfirmed. If the operator cancels application close, the operation continues. If close is confirmed, no retry or rollback is attempted; generations are invalidated, cleanup is best-effort, late callbacks cannot update UI, and the application may exit with unknown real device state.

Read-only cleanup waits are bounded by policy. Timeout logically abandons old authority, ignores late callbacks, and must not permanently prevent a later top full Refresh from establishing a new generation.

### 12. Legacy single-device mode remains compatible

When a unique supported source record has `room_id = null`, the existing single-device screen, live, local Refresh, auxiliary, Debug, and state-changing lifecycle remains authoritative. Room-tree post-cycle rules do not silently replace or remove that legacy path.

Shared model-specific handlers/controllers may be refactored for reuse, but behavior changes to legacy single-device mode require explicit compatibility evidence and must not arise merely from the room interaction coordinator.

### 13. Legacy PDU related-codec enrichment is retired

The room tree is the only room-mode presentation/orchestration authority for room equipment. PDU screens in room mode display the PDU record's own accepted diagnostics and existing PDU controls only. Shared room name/address/VIP remain in the single room header above the tree, and codec state/metering appears only in the codec's own room row when that row is current.

Implementation removes the dedicated PDU-room-related-codec resolver/controller/session lane, its related-codec status normalization/presentation, duplicated room/VIP/codec section, and PDU-hosted CloudLink microphone meter. Accepted PDU refresh or mutation reconciliation no longer starts related-codec work as a side effect.

The canonical room codec remains available as an independent room record and is diagnosed/interacted with only through its exact row lifecycle.

## Key Decisions

1. **Exact-record authority over widget authority.** A room interaction always captures immutable row identity/currentness before any device I/O.
2. **One serialized room interaction lane.** Simpler, safer ownership is preferred over parallel post-cycle device activity.
3. **Live is subordinate to explicit operations.** Local Refresh, auxiliary reads, and mutations retire live before using network resources.
4. **Mutation success requires reconciliation.** ACK is not state authority; authoritative cache changes only after confirmed readback.
5. **Read-only and state-changing recovery are different.** Read-only work may use bounded cancellation/retry; a possibly delivered mutation is never blindly replayed.
6. **Credential selection stays in application composition.** Model-wide chains and exact model/IP successful memory are preserved; handlers/workers never iterate candidates.
7. **Per-record degradation.** Failure of one device does not make the entire room unusable.
8. **Remove duplicated PDU enrichment instead of adapting it.** The room tree already provides the correct room/codec abstraction.
9. **Legacy no-room mode stays intact.** The change is an extension of room mode, not a rewrite of all interaction paths.

## Risks and Mitigations

- **Risk: reused widgets accidentally send the top source IP.** Mitigation: network actions accept only immutable exact-row contexts from the coordinator; widgets publish non-secret intents.
- **Risk: live and mutation run concurrently.** Mitigation: single room interaction lane and mandatory live cleanup before explicit network actions.
- **Risk: stale cleanup launches the wrong row after rapid switching.** Mitigation: latest-target re-evaluation plus room/row/interaction generations at the handoff boundary.
- **Risk: command is replayed after ambiguous delivery.** Mitigation: structured execution state and mandatory no-replay policy after any possible mutation send.
- **Risk: old cache is presented as post-command truth.** Mitigation: only reconciliation can replace authoritative cache; old cache becomes stale/unconfirmed.
- **Risk: child dialogs receive callbacks for another same-model row.** Mitigation: child-window exact-row identity and forced closure/invalidation on row switch/collapse.
- **Risk: cleanup hangs forever.** Mitigation: bounded policy timeout and logical abandonment; top full Refresh can establish a new generation.
- **Risk: removal of PDU enrichment regresses PDU controls.** Mitigation: separate PDU device diagnostics/control from the removed related-codec side lane and add focused regression tests.

## Validation Strategy

Implementation validation must prove both exact-row correctness and non-regression of legacy single-device behavior. Focused coverage should include:

- two same-model room records with independent cache and callbacks;
- live start only after terminal room cycle and only for the latest expanded connected row;
- rapid A -> B -> C switching with no I/O for stale intermediate targets;
- collapse-to-none live teardown;
- local Refresh success/warning/failure and full-refresh-only retry after failure;
- Call Log/auxiliary typed credential fallback, close/cancel, ordinary failure live resume, and terminal connection degradation;
- Debug exact-row binding with zero network I/O on open;
- mutation confirmation Cancel no-op, confirmed live teardown, no-send on cleanup timeout, mandatory reconciliation, no blind replay, cache replacement only after readback;
- post-cycle degradation isolated to one record while another record remains interactive;
- source IP edit and real credential change invalidate the entire current room context; Cancel/no-op Save do not;
- read-only shutdown without warning and mutation shutdown warning/no rollback;
- removal of all PDU related-codec enrichment side effects/UI while PDU own controls remain functional;
- full legacy single-device regression suite;
- strict OpenSpec validation, full offline tests, `git diff --check`, and the required disposable archive-applicability check because this change removes requirements from an existing root capability.
