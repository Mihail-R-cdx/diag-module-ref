## Context

Canonical equipment inventory v4 is now merged in `master`. Runtime inventory records expose exact `record_id`, `diagnostic_model`, `ip_address`, authoritative `room_id`, and per-record room display metadata including `room_name`, `room_address`, and `room_vip`. The inventory loader remains immutable/indexed and runtime model dispatch is exact-only.

The current GUI lifecycle is still centered on one diagnostic target. `gui/diagnostic_dispatch.py` owns an exact model registry and resolves an IP to one supported model for diagnostic-start or credential-configuration purposes. Current unresolved-inventory behavior opens manual fallback for several valid-inventory outcomes that the room workflow must instead treat fail-closed.

`core/room_context.py` and `pdu-room-codec-enrichment` solve a different legacy problem: after an accepted user PDU refresh they resolve one PDU room and exactly one related codec. That path aggregates room-name/VIP conflicts and owns a dedicated related-codec lane. It is not a suitable authority for a complete room equipment tree and must not become the new room orchestrator.

Several model paths have persistent or semi-persistent execution semantics today. Matrix may retain a handler/session and keepalive behavior; DMP performs continuous polling after its first complete snapshot; codec screens own serialized interactive/live behavior. Automatic room diagnostics require a bounded one-shot interpretation of those model paths so one record cannot retain background polling while the room queue proceeds to another record.

## Goals

- Resolve one entered source IP into one authoritative room session when valid inventory provides a non-null `room_id`.
- Render all records of that room in deterministic order with one shared room metadata header.
- Preserve every canonical room record, including unsupported, missing-IP, and ambiguous-IP rows.
- Store diagnostic state per exact record instead of inside reusable screen widgets.
- Establish one application-level model capability/dispatch authority and a uniform one-shot adapter contract.
- Run supported eligible room diagnostics strictly sequentially and off the GUI thread.
- Preserve current model-specific transport, parser, credential, and successful-profile rules behind adapters.
- Bound cleanup and make stale callbacks powerless before proceeding to later records.
- Produce stable room/session/row contracts that the following `room-device-interaction-lifecycle` change can reuse.

## Non-goals

- No canonical inventory schema/importer change.
- No fuzzy runtime model recognition and no dispatch from `source_model`, manufacturer text, `device_kind`, or row position.
- No post-cycle live handoff between accordion rows.
- No local per-device Refresh lifecycle after the automatic room cycle.
- No Call Log or other auxiliary network operation lifecycle.
- No state-changing command lifecycle or mutation readback/reconciliation redesign.
- No per-IP credential store; existing model-wide candidate chains and exact model/IP successful-index/profile memory remain.
- No removal/archive of the legacy `pdu-room-codec-enrichment` capability in this change.
- No separate Cancel control for the automatic room cycle.
- No Graphify artifact or workflow requirement.

## Decisions

### 1. Source resolution establishes room authority before device support

For a syntactically valid normalized IPv4 address, application composition first resolves the source against the current validated immutable inventory.

With valid inventory:

```text
0 source records
    -> fail closed: IP not found

>1 source records
    -> fail closed: globally ambiguous source IP

1 source record + non-null room_id
    -> create room session
    -> source record need not itself be diagnostically supported

1 source record + room_id = null + exact supported diagnostic_model
    -> retain existing legacy single-device flow

1 source record + room_id = null + null/unsupported diagnostic_model
    -> fail closed
```

Manual model fallback is not a repair mechanism for valid inventory data. It remains available only when inventory is unavailable/unloadable/corrupt for the current application session.

This ordering is essential for scenarios where the entered source is unsupported but belongs to a room containing other supported equipment: supportability controls each row's diagnostic eligibility, not whether the room exists.

Credential configuration (`Пароль`) uses the same valid-inventory fail-closed principle but does not start room diagnostics. A unique exact supported model may open its existing model-wide credential configuration; zero/many/unmapped/unsupported valid-inventory outcomes are safe errors. Inventory unavailable/unloadable/corrupt may use the existing explicit manual model fallback for credential configuration.

### 2. A RoomDiagnosticSession is immutable identity plus a mutable generation-owned state aggregate

The room session identity contains only non-secret canonical/application facts, conceptually:

```text
RoomDiagnosticSessionIdentity
    inventory_snapshot_id
    room_generation
    normalized_source_ip
    source_record_id
    room_id
```

`room_id` is the only room identity authority. `room_name`, `room_address`, and `room_vip` are selected display values, not identity.

Every full room Refresh creates a new `room_generation`. Old callbacks may still finish physically, but they lose authority immediately and cannot mutate the new session, save credential/profile memory, advance its queue, or enable/disable its controls.

### 3. Tree membership is complete and deterministic

Room membership is exactly all canonical records returned for the resolved non-null `room_id`. No filtering by `device_kind`, diagnostic support, page type, or IP happens before the tree is built.

Order is:

```text
source record
then every other room record sorted by canonical record_id
```

The source record appears once even if normal canonical ordering would place it elsewhere.

Same-room duplicate-IP detection is computed across every room record with a non-null IP. Unsupported rows participate in ambiguity evidence even though they do not receive I/O. A supported row whose IP occurs on another record in the same room is not diagnosed. A duplicate IP in another room does not invalidate an already established room row; top-level source resolution remains globally zero/one/many before room authority is established.

### 4. Shared room metadata uses source-first display selection without conflict arbitration

The shared room header shows:

```text
Название комнаты
Адрес
VIP
```

It does not show `room_id`.

For each field independently:

```text
value on source record when nonblank/non-null
    else first nonblank/non-null value in canonical room-record order
    else safe no-data display
```

For text, blank means absent after canonical normalization. For VIP, both `true` and `false` are meaningful non-null values. The room session does not compare multiple non-null display values for equality, emit room-name/address/VIP conflict outcomes, or choose a value because a majority agrees.

This is intentionally distinct from the legacy PDU enrichment resolver; MIH-7 does not silently change that legacy capability's normative room-conflict semantics.

### 5. DeviceRowState is authoritative; device widgets are projections

Each tree row owns a state record keyed by canonical `record_id` together with captured exact `diagnostic_model` and `ip_address` values. `record_id` remains the stable equipment identity; the captured model/IP prevent a callback from being applied to another runtime context.

Conceptually the state contains:

```text
record identity/context
row status
accepted authoritative snapshot or none
partial/unconfirmed data or none
warnings
safe typed terminal reason or none
capability/view binding
row operation generation/token
```

The state is not stored in `CodecScreen`, `PDUScreen`, `MatrixScreen`, or `AudioDSPScreen`. Only one accordion row is expanded at a time. Heavy model-specific presentation may be built lazily and rebound/rebuilt from the exact row state. Hidden rows do not keep timers, handlers, workers, sessions, or polling alive merely because a widget was previously created.

Two records of the same model therefore remain independent even when they reuse one screen class.

### 6. One application-level model registry is support authority

The existing exact dispatch registry is extended rather than shadowed by a separate room-only supported-model list.

A registry entry must be sufficient to bind at least:

```text
exact diagnostic_model
presentation/view route
existing lifecycle route
room one-shot adapter factory/key
capability metadata required by later interaction composition
```

MIH-7 consumes the view and one-shot portions. MIH-8 may extend/consume interactive capability metadata, but it must not create a second conflicting support registry.

Startup/composition validation fails fast for duplicate exact models, missing view bindings, missing one-shot adapter bindings for supported room diagnostics, or other incomplete registration required by this change.

Importer recognition rules remain importer-only. Runtime never tokenizes or guesses `source_model` to repair a missing/unsupported canonical `diagnostic_model`.

### 7. One-shot adapters hide model-specific lifecycle details

The room orchestrator communicates with a uniform read-only adapter contract. Exact class/API names are implementation choices, but the semantic boundary is equivalent to:

```text
activate immutable exact row attempt context
start one assigned-credential acquisition
publish zero or more partial updates
publish exactly one terminal diagnostic outcome
retire persistent polling/keepalive/session work
publish cleanup completion
```

Normalized outcomes distinguish:

```text
PARTIAL
USABLE_SUCCESS
USABLE_SUCCESS_WITH_WARNING
TERMINAL_FAILURE
CLEANUP_COMPLETE
```

The adapter may delegate to existing controllers/workers/handlers and parser logic. It must not copy protocol details into the room orchestrator and must not select another credential candidate itself.

Persistent model paths are adapted to one-shot semantics. Examples:

- Matrix: obtain the final required routing/device snapshot, then stop keepalive/release the persistent session before the row is retired.
- DMP: accept the first complete authoritative snapshot, stop further polling, and close owned SSH/channel resources before retirement.
- CloudLink/codec live mechanisms: automatic acquisition may collect approved one-shot status, but no live timer/polling session remains active after row retirement.

A terminal adapter outcome is not sufficient to advance the room queue until cleanup has either completed or reached the bounded abandonment rule.

### 8. Automatic room diagnostics are strictly serialized

For each eligible row the orchestrator performs:

```text
pre-I/O currentness check
-> resolve/validate application-owned credential attempt plan
-> if required authenticated credentials are unavailable for a non-PCS4i model:
       publish safe terminal configuration failure with zero ping/handler/device I/O
       continue to the next eligible row
-> ping/reachability check
-> start one assigned-candidate diagnostic attempt
-> if and only if structured new-login AuthenticationError and candidates remain:
       start the next candidate attempt
-> accept terminal row outcome
-> cleanup/release
-> next eligible row
```

Only one room record owns diagnostic network activity at a time. Accordion selection never changes queue order and never causes a waiting row to leap ahead.

Credential-plan resolution and validation is a strict pre-I/O gate and therefore precedes ping. An authenticated non-PCS4i row with no valid required credentials ends with the safe inline reason `Credentials не настроены`, performs no ping, handler acquisition, or other device network I/O, and does not block later queue rows. PCS4i retains its approved exception: when no explicit/profile/mapped credential exists, application composition forms the approved credentialless attempt plan; only after that valid plan exists does the row proceed to ping.

After a valid attempt plan exists, preliminary ping failure is terminal for that row and stops before model-specific handler/worker acquisition. The queue continues to later eligible rows.

### 9. Credential fallback remains application-owned and exact model/IP scoped

The existing ordered candidate contract is reused unchanged:

- start from a valid saved successful candidate index for exact model/IP, otherwise index zero;
- consider only the remaining suffix without wrap-around;
- change candidate only after machine-readable structured new-login `AuthenticationError`;
- timeout, transport, TLS, protocol, parse, malformed/empty payload, or arbitrary text such as `auth`, `401`, or `403` does not authorize candidate advancement;
- one adapter/worker/handler attempt receives only one assigned candidate;
- successful candidate index/profile is saved only after an accepted final success whose model-specific acquisition/authentication contract is complete;
- partial results and failed/degraded terminal outcomes do not persist a new successful candidate.

Candidate lists remain model-wide configuration. MIH-7 does not introduce per-IP credential storage; only successful-index/profile memory remains exact model/IP scoped.

### 10. Row eligibility and visible status are deterministic

Before I/O, status priority is:

```text
canonical diagnostic_model absent or not registered
    -> НЕ ПОДДЕРЖИВАЕТСЯ

registered model + ip_address = null
    -> IP НЕ УКАЗАН

registered model + same-room duplicate IP
    -> НЕОДНОЗНАЧНЫЙ IP

otherwise
    -> ОЖИДАНИЕ ОПРОСА
```

Unsupported wins even when its IP is null or duplicated, because IP is not diagnostically meaningful for an unsupported row. If `source_model` is also null, the row label uses `Модель не определена`; no alternate name is inferred.

Unsupported, missing-IP, and ambiguous-IP rows receive zero device network I/O and expose no network/state-changing actions. Missing-IP and ambiguous-IP supported rows are not expandable as active device screens. Unsupported rows are visible but non-actionable/non-expandable.

Eligible rows transition through `подключение...` while their turn is active. Accepted usable success becomes `подключено`. Terminal failure becomes `не удалось подключиться`. Cleanup timeout after an already usable snapshot may instead produce the degraded `соединение потеряно` presentation described below.

### 11. Partial data, usable warning, and terminal failure are separate concepts

Intermediate data may render in an expanded row while status remains `подключение...`. It does not advance the queue, enable controls, authorize credential persistence, or become the authoritative successful cache.

A model-specific final result may be usable even when optional enrichment failed. Existing approved examples include Polycom authoritative HTTPS status with unavailable SSH enrichment and PCS4i authoritative Telnet outlet status with unavailable HTTP outlet names. In that case:

- row status is `подключено`;
- usable authoritative fields become the row cache;
- a safe inline warning is retained;
- the overall room cycle is classified as completed with problems;
- an optional failure does not by itself advance credentials.

If a terminal failure follows earlier partial data, the partial values may remain visible as explicitly incomplete/unconfirmed diagnostic evidence, but they do not become the successful cache and do not enable later interaction.

Safe row error detail is derived from typed/category outcomes, for example unreachable, authentication exhausted, timeout, protocol error, invalid data, or credentials not configured. Raw exception text, credentials, tokens, cookies, request bodies, and secret-bearing URLs are not user-facing reason authority. Unknown failures use a generic safe diagnostic failure message.

### 12. Cleanup is bounded and one stuck device cannot block the room

Every automatic one-shot lifecycle has a configurable/testable cleanup deadline. The exact production number is implementation policy rather than a product requirement.

Until cleanup completes, the next device does not start. If the deadline expires:

- the old adapter/session generation is logically abandoned and loses authority forever;
- late result/error/completion/cleanup callbacks are ignored;
- best-effort physical cleanup may continue only on the owning background lane;
- the queue proceeds to the next row;
- if no usable final snapshot existed, the row is terminal failed;
- if a usable final snapshot existed but safe retirement could not be established, keep the snapshot visible as stale and present the row as `соединение потеряно`/degraded;
- the global room result is completed with problems;
- no post-cycle live or action for that degraded row is enabled by MIH-7.

Cleanup network/resource work owned by a background controller/worker remains off the GUI thread. The GUI publishes invalidation/cancellation and never blocks waiting on a network timeout.

### 13. Room generation owns callback acceptance and queue advancement

Every operation callback carries or is associated with:

```text
room generation
exact record_id
captured exact model/IP context
row attempt/operation token
```

Currentness is checked before handler acquisition and before first network I/O when those phases are separable. Superseded queued work performs zero handler acquisition and zero I/O. In-flight stale I/O may finish physically but cannot update row/cache/header/global status, save credential/profile memory, unlock a newer context, or schedule the next room operation.

Background code never reads Qt widget text/current screen as freshness authority.

### 14. Automatic-cycle UI is non-modal and accordion selection is presentation-only

After room resolution, the GUI renders the complete tree immediately. No automatic per-device progress, error, or terminal modal is opened during the room cycle.

During the cycle:

- top IP, Password, and full Refresh controls are disabled until terminal room completion;
- there is no separate Cancel button;
- accordion selection remains available and does not alter queue order;
- only one row is visually expanded at a time;
- expanding a waiting eligible row shows its model-specific layout with placeholder/waiting values but starts no early I/O;
- partial/final updates for the currently expanded row render in place;
- all row network/state-changing controls remain disabled;
- cycle progress is visible through row status and one global room status.

A newly established room session has deterministic initial accordion state. When the source row is supported and expandable, the source row is the one initially expanded row. When the source row is unsupported, missing-IP, same-room ambiguous, or otherwise non-expandable, the tree starts fully collapsed. The application never chooses a secondary row on the user's behalf. Automatic success, warning, or failure never changes expansion.

MIH-7 room mode remains presentation-only after terminal room completion as well as during the cycle. A successful `подключено` row does not enable legacy local Refresh, Matrix route, PDU/codec mutation, live/polling, Call Log/auxiliary network requests, or equivalent network-backed controls. Those controls remain disabled or unbound until MIH-8 supplies exact-row interaction authority. The permanent top-level `Отладка` action is disabled for the entire MIH-7 room-mode session; it must not derive a model/IP from the top source IP, current reused screen, or prior single-device context.

Closing the application during read-only room-cycle activity invalidates the generation and publishes stop/cancel best-effort without waiting for remote network timeout or showing a mutation-warning dialog.

### 15. Global room summary belongs only to full room cycles

While automatic polling runs, the shared status is equivalent to:

```text
Опрос оборудования помещения...
```

Terminal clean result is:

```text
Опрос завершён
```

If any row is unsupported, missing-IP, ambiguous-IP, failed, cleanup-degraded, or final-success-with-warning, terminal room result is:

```text
Опрос завершён с проблемами
```

A room with no eligible network rows still completes a full cycle, performs no device I/O, and ends with problems rather than hanging in an empty/loading state.

`Последнее обновление` means completion time of the most recent full room cycle, not the last successful device response. It updates even when no network I/O was eligible.

### 16. Full Refresh rebuilds the room session from source authority

In room mode the permanent top Refresh is a full room Refresh. It does not selectively reuse a previous row cache as current authority.

As soon as full Refresh starts, the previous room generation, tree/cache presentation, row/view bindings, and accordion selection lose authority and are cleared/reset before new source resolution. The application then creates a new room generation, revalidates/re-resolves the current top-level source IP against the immutable loaded inventory, rebuilds shared room display selection and every row state, and runs the entire sequential cycle again.

The new tree always applies the deterministic source-row initial-state rule from Decision 14; a previously expanded secondary row is never carried into the new generation. If new source re-resolution fails, the old room tree/cache/presentation is not restored as current authority.

Editing the top IP after a completed room cycle invalidates the current room presentation/pending room authority immediately. Returning the text to the previous IP does not resurrect the old room state; Enter/full Refresh is required to establish a new session.

Inventory itself remains the startup-loaded immutable snapshot under the current inventory contract; MIH-7 does not introduce hot reload or file watching.

### 17. Legacy PDU enrichment is isolated during the transition

MIH-7 does not remove the current PDU-room-codec enrichment capability or its root spec. It does, however, prevent automatic room PDU one-shot acquisition from masquerading as the legacy accepted **user PDU refresh** trigger.

In tree mode:

- shared room name/address/VIP is rendered above the tree, not duplicated as authoritative room metadata inside a device row;
- room-cycle PDU diagnostics do not start related-codec enrichment;
- codec rows are diagnosed by the room orchestrator in their own queue position;
- old PDU-related codec state cannot become the room tree's source of truth.

Legacy single-device PDU mode may retain its existing enrichment until the following change explicitly removes/reconciles it.

### 18. MIH-8 owns post-cycle interaction

At terminal room-cycle completion MIH-7 provides:

```text
current RoomDiagnosticSession identity/generation
complete deterministic tree
per-record authoritative or failed/degraded state
exact view/capability registry binding
typed warnings/failures
no automatic one-shot persistent lifecycle left running
```

The terminal room tree is presentation-only in MIH-7. Existing device-specific network-backed controls remain disabled or unbound after both clean and problem completion, and attempts to invoke them must be rejected before handler acquisition/device I/O. This includes local row Refresh, Matrix routing, PDU or codec mutations, live/polling starts, Call Log/auxiliary network reads, and equivalent reused-screen actions. The top-level `Отладка` action also remains unavailable in room mode until exact-row Debug binding is explicitly introduced.

MIH-7 does not start live polling after that terminal boundary and does not define local row Refresh, Call Log/auxiliary network requests, state-changing commands, mandatory mutation readback, or post-cycle connection-loss recovery. Those behaviors are the scope of `room-device-interaction-lifecycle` and must build on the exact per-record state rather than reintroducing selected-widget or top-IP target authority.

## Risks / Trade-offs

### More application orchestration

A room cycle introduces a higher-level state machine above existing model lifecycle owners. The adapter boundary is required to prevent this from becoming a second copy of protocol logic. Tests must prove that model-specific controllers still own their resources while the room orchestrator owns only sequence and acceptance.

### Temporary coexistence with PDU enrichment

For one change, legacy single-device PDU enrichment and new room-tree diagnostics coexist. The separation is intentional: automatic room PDU adapters must not emit the legacy user-refresh trigger. MIH-8 must remove/reconcile the obsolete duplicate experience after room interaction is established.

### Sequential diagnostics are slower than parallel diagnostics

Strict serialization increases total room scan duration but makes resource ownership, credential fallback, cleanup, and UI ordering predictable and prevents multiple persistent model sessions from competing. This is an accepted safety/clarity trade-off.

### Reusable views require explicit state projection

Moving authority out of widgets requires more mapping code and regression coverage, but it is necessary for multiple same-model records and for stale-callback safety.

## Migration / Implementation Sequence

1. Extend exact application dispatch into one validated capability registry without changing importer recognition.
2. Add pure source-to-room session resolution and deterministic room row construction/display metadata selection.
3. Add `DeviceRowState`/room generation ownership independent of screen widgets.
4. Define the one-shot adapter interface and adapt existing model lifecycle owners incrementally while preserving their transport/credential contracts.
5. Add the serialized room orchestrator with a pre-I/O credential-plan gate, then the reachability gate, assigned credential attempt loop, terminal/partial/warning normalization, and bounded cleanup.
6. Add tree/header presentation and projection of exact row state into lazy reusable views, including deterministic source-row initial expansion/reset.
7. Add the transitional MIH-7 interaction lock: keep reused row network controls and top-level Debug disabled/unbound throughout room mode, including after terminal completion.
8. Ensure tree-mode PDU one-shot does not trigger legacy PDU-related codec enrichment.
9. Add focused regression coverage, including zero-ping/no-handler proof for authenticated non-PCS4i rows whose required credentials are not configured, and run full repository validation before implementation publication.

## Validation Strategy

Architecture and implementation must be validated with the repository-local wrapper only:

```powershell
.\openspec.cmd validate room-equipment-diagnostic-tree --strict
.\openspec.cmd validate --all --strict
git diff --check
git diff --cached --check
```

Implementation validation must additionally run focused room/inventory/dispatch/controller tests and the full offline suite:

```powershell
python -m unittest discover -s tests -p "test_*.py"
```

Because this change adds a root capability and modifies an existing root requirement, independent validation must perform the disposable archive-applicability check required by `RULES.md` before `READY FOR ARCHIVE`.
