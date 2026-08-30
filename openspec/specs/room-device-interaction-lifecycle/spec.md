# room-device-interaction-lifecycle Specification

## Purpose
TBD - created by archiving change room-device-interaction-lifecycle. Update Purpose after archive.
## Requirements
### Requirement: Post-cycle room interaction is bound to the exact expanded record

After the automatic room cycle reaches a terminal state, room-mode network interaction SHALL use the exact current expanded room record as target authority. The application SHALL bind every room live, local Refresh, auxiliary read, and state-changing intent to immutable non-secret context containing current room generation, canonical `record_id`, exact canonical `diagnostic_model`, exact canonical IP, and an operation/currentness token or equivalent.

The persistent target-search text, resolved initial source IP/record, reusable screen identity, prior legacy single-device context, row label, model text rendered in Qt, or previous expanded row SHALL NOT substitute for exact current row authority. Reusable screens SHALL remain presentation projections of per-record state.

Failed, degraded, unsupported, missing-IP, and same-room ambiguous rows SHALL expose no row network/state-changing actions except presentation allowed by their existing terminal state. An initially failed supported row may remain expandable for safe diagnostics, but retry is through top full Refresh rather than a row-local retry path.

#### Scenario: Two same-model records remain independent

- **GIVEN** two room records share the same supported diagnostic model
- **AND** each has its own exact record/IP state
- **WHEN** the operator alternates the expanded row
- **THEN** every network intent uses only the exact current row context
- **AND** no cache, session, callback, control authority, or credential-success update crosses from one record to the other

#### Scenario: Top source IP differs from expanded row

- **GIVEN** room mode was entered through source record A
- **AND** supported record B is currently expanded
- **WHEN** a room interaction is requested
- **THEN** the target is B's exact canonical record/model/IP context
- **AND** neither A's resolved source IP nor the persistent raw target-search text is used as B's device target

#### Scenario: Initial IP target differs from expanded row

- **GIVEN** room mode was entered through an IP target that resolved source record A
- **AND** supported record B is currently expanded
- **WHEN** a room interaction is requested
- **THEN** the target is B's exact canonical record/model/IP context
- **AND** neither the raw target-search text nor A's resolved source IP is used as B's device target

### Requirement: One serialized room interaction lane owns all network lifecycle kinds

The application SHALL serialize all post-cycle room network interaction through one application-owned room interaction lane. At most one room interactive network lifecycle of any kind SHALL be active, pending retirement, or eligible to acquire or await device network resources at a time.

The mutually exclusive lifecycle kinds are:

```text
LIVE
LOCAL_REFRESH
AUXILIARY_READ
MUTATION
RECONCILIATION
```

Starting or accepting a lifecycle intent SHALL NOT allow a second lifecycle kind to acquire a handler/session, open a transport, queue current device I/O, or wait as a concurrently authoritative network owner. A replacement action MAY proceed only through its explicitly approved supersession/handoff rule after prior authority is invalidated and cleanup/release reaches completion or an allowed bounded-abandonment boundary. Purely local presentation actions, including the current Debug presentation, are outside this network lane.

#### Scenario: Auxiliary read blocks another row network lifecycle

- **GIVEN** an auxiliary read is active or retiring
- **WHEN** the operator attempts Local Refresh or a state-changing command
- **THEN** the new network lifecycle does not start
- **AND** it acquires no handler/session and performs no device network I/O until the auxiliary lifecycle has reached its permitted retirement boundary

#### Scenario: Mutation and reconciliation remain one exclusive lifecycle

- **GIVEN** a confirmed mutation has started and mandatory reconciliation is not terminal
- **WHEN** any live, Local Refresh, auxiliary read, or other mutation intent is produced
- **THEN** no competing room network lifecycle starts
- **AND** the mutation/reconciliation lifecycle retains exclusive room interaction authority until its terminal boundary

### Requirement: One application model registration owns room interactive capabilities

The existing exact application-level model registration SHALL remain the sole support/dispatch authority for room interaction capabilities. For each exact `diagnostic_model`, that one registration SHALL provide or explicitly declare absence of the model's:

- screen/view binding;
- room one-shot adapter binding;
- post-cycle live binding;
- Local Refresh binding;
- auxiliary network action bindings;
- state-changing action bindings;
- call-activity normalization/projection binding when the model's approved diagnostic snapshot exposes call-state evidence;
- lifecycle cleanup/release hooks required by those bindings.

Room interaction composition SHALL derive capability availability from this registration rather than from independent model lists, duplicated support tables, widget type checks, source-model text, or registry order. Separate `LIVE_SUPPORTED_MODELS`, Local Refresh model lists, auxiliary model lists, mutation model lists, `OCCUPANCY_SUPPORTED_MODELS`, call-activity model lists, or equivalent parallel application authorities SHALL NOT be introduced.

Application startup/composition SHALL fail fast when a model declares a room interactive capability but its required binding/cleanup hook is missing or contradictory. It SHALL also fail fast when an exact codec registration that is required by the approved `device-diagnostics-and-control` call-activity contract omits its call-activity binding or names a binding unavailable to composition.

#### Scenario: Registered model exposes its room interaction surface

- **WHEN** a connected room row uses an exact registered model
- **THEN** live, Local Refresh, auxiliary, mutation, presentation, call-activity projection where applicable, and cleanup availability are resolved from that model's single application registration
- **AND** no second model-support table is consulted

#### Scenario: Capability is absent from the registration

- **WHEN** the exact model registration does not advertise a particular optional room interactive capability
- **THEN** that capability is unavailable for the row
- **AND** runtime does not infer it from the current screen class, handler type, model substring, or another independent list

#### Scenario: Required call-activity binding is missing

- **GIVEN** an exact codec model is required by `device-diagnostics-and-control` to project approved call-state evidence
- **WHEN** its unified application registration has no bound call-activity projection or references an unavailable binding
- **THEN** application startup/composition fails closed
- **AND** the model cannot be silently omitted from room busy aggregation

### Requirement: Live ownership follows the latest expanded connected row

Automatic one-shot room acquisition SHALL leave no persistent live activity. After the entire room cycle reaches terminal state, the application MAY start an existing model-specific live capability only for the exact row that is currently expanded, has accepted usable connected state, is not degraded/blocked, and advertises that live capability in the unified model registry.

At most one room live lifecycle SHALL own network resources at a time, subject to the stronger cross-type serialized interaction-lane requirement above. Collapsing the current row SHALL invalidate and retire its live context and SHALL NOT auto-expand another row. Switching rows SHALL immediately change presentation but SHALL start new live I/O only after bounded cleanup/release of prior live authority. Pending target selection SHALL be latest-wins: if the operator switches A -> B -> C before A cleanup completes, B SHALL perform no live I/O and only current C MAY start after cleanup.

During live handoff, network-backed controls for the newly expanded row SHALL remain disabled until prior network authority is released. A terminal typed connection/session failure, or terminal authentication failure after approved fallback/recovery, SHALL stop automatic live restart, mark only that exact row `соединение потеряно`, keep its accepted cache visible as stale, and require top full Refresh for recovery.

#### Scenario: Room cycle ends with a current live-capable row

- **GIVEN** the room cycle has fully terminated
- **AND** the current expanded row is connected and supports live
- **WHEN** post-cycle interaction becomes active
- **THEN** live may start for that exact row only
- **AND** no hidden row starts polling, keepalive, or live sampling

#### Scenario: Rapid row switching skips stale targets

- **GIVEN** live for row A is being retired
- **WHEN** the operator expands B and then C before A cleanup completes
- **THEN** B performs no live network I/O
- **AND** after cleanup only current C may start live

#### Scenario: Last row is collapsed

- **WHEN** the operator collapses the only expanded row
- **THEN** its live context is retired
- **AND** no other row is opened or started automatically

### Requirement: Local Refresh replaces one exact row snapshot through a fresh read-only lifecycle

Local Refresh SHALL be available only for the current expanded exact row whose accepted state is connected/usable and whose interaction state is not degraded or blocked. Before local Refresh device I/O starts, active live SHALL be invalidated and retired through bounded cleanup/release.

From acceptance of a Local Refresh intent through its terminal cleanup/release boundary, the application SHALL disable target-search editing, Password, top full Refresh, accordion switching/collapse, state-changing actions, auxiliary network actions, additional Local Refresh intents, and any other row network action. Purely local Debug presentation MAY remain available for the same immutable exact row because it performs no device I/O and cannot change target authority.

The local Refresh SHALL reuse application-owned exact-row credential selection/fallback, preliminary reachability, model diagnostic acquisition, and typed failure rules. Only an accepted final usable result MAY atomically replace that row's authoritative cache. An approved usable-success-with-warning result remains successful and MAY replace cache while preserving its non-modal warning.

A terminal local Refresh failure SHALL stop live, set the exact row to `не удалось подключиться`, block its local Refresh, auxiliary network actions, live, and state-changing controls, and require top full room Refresh for retry. Previously accepted data MAY remain visible only as stale context. Local Refresh SHALL NOT change the room-level `Последнее обновление` timestamp.

#### Scenario: Local Refresh succeeds

- **GIVEN** a connected current row
- **WHEN** local Refresh completes with accepted usable data
- **THEN** that exact row cache is atomically replaced
- **AND** eligible live may resume only after cleanup/currentness checks
- **AND** `Последнее обновление` remains the last full room-cycle completion time

#### Scenario: Local Refresh locks target-changing controls

- **GIVEN** Local Refresh has been accepted for the current exact row
- **WHEN** the refresh or its cleanup is still active
- **THEN** target-search editing, Password, top full Refresh, accordion switching/collapse, auxiliary actions, mutations, and another Local Refresh are disabled
- **AND** no competing room network lifecycle starts

#### Scenario: Local Refresh fails terminally

- **WHEN** a current row local Refresh reaches terminal failure
- **THEN** the row becomes `не удалось подключиться`
- **AND** row network/state-changing controls remain blocked
- **AND** recovery requires top full Refresh

### Requirement: Auxiliary read-only actions are exact-row serialized operations

A network-backed auxiliary action, including `Журнал звонков`, SHALL run only for the current expanded connected exact row and SHALL use the room interaction lane rather than the persistent target-search/initial-source context or a reusable-widget target. Only one auxiliary network action MAY be active at a time, subject to the stronger cross-type serialized interaction-lane requirement. Active live SHALL be invalidated and retired before auxiliary device I/O begins.

While an auxiliary read is active or retiring, the application SHALL disable target-search editing, Password, Local Refresh, all state-changing actions, other auxiliary network actions, and any other competing row network action. Top full Refresh SHALL remain available as the global supersession action. Accordion switching/collapse SHALL remain available and SHALL cancel/invalidate the auxiliary operation for the old exact row before any newly selected row network lifecycle may begin. Purely local Debug presentation MAY remain available while its exact-row context remains current.

Auxiliary reads SHALL preserve existing application-owned structured credential behavior. A rejected candidate MAY advance only after structured new-login `AuthenticationError` and only within the existing allowed candidate suffix. Timeout, transport, protocol, parse, business error, public strings such as `auth`, `401`, or `403`, and absence of success SHALL NOT independently authorize credential advancement.

An ordinary auxiliary failure that does not prove loss of the current connection/session context SHALL NOT by itself degrade the row. After bounded cleanup, live MAY resume when the same row remains current and usable. Terminal typed connection/session failure, or terminal authentication failure after allowed credential fallback is exhausted, SHALL degrade that exact row to `соединение потеряно` and require top full Refresh.

Device-specific auxiliary child windows SHALL remain bound to the exact row generation. Switching/collapsing the row or starting top full Refresh SHALL close/invalidate the child context and prevent late callbacks from updating another row. User-closing an active auxiliary child window SHALL itself invalidate/cancel that exact auxiliary operation, publish the available cancel/stop intent, perform bounded cleanup/release, and prevent late callbacks from updating or reopening the closed child presentation. If the same row remains current, connected/usable, and live-capable after cleanup, eligible live SHALL resume. A later explicit opening SHALL always start a fresh acquisition rather than reuse the cancelled request.

#### Scenario: Auxiliary parse error preserves connection context

- **GIVEN** the row was connected before an auxiliary request
- **WHEN** the auxiliary request ends with a parse/business error that is not a typed session/connection failure
- **THEN** the row remains connected
- **AND** the accepted diagnostic cache remains authoritative for its prior refresh point
- **AND** live may resume after cleanup if the row is still current

#### Scenario: Auxiliary controls use the approved lock matrix

- **GIVEN** an auxiliary read is active
- **THEN** target-search editing, Password, Local Refresh, mutations, other auxiliary actions, and competing row network actions are disabled
- **AND** top full Refresh remains available as global supersession
- **AND** accordion switching/collapse remains available as an auxiliary cancellation boundary
- **AND** current exact-row local Debug may remain available without acquiring network resources

#### Scenario: User closes active auxiliary child window

- **GIVEN** an auxiliary child window is open for a current connected exact row
- **AND** its network request is still active or retiring
- **WHEN** the user closes that child window directly
- **THEN** the exact auxiliary request loses authority and cancellation/stop is published where supported
- **AND** bounded cleanup/release runs before the room interaction lane is free for a replacement lifecycle
- **AND** late callbacks cannot update or reopen the closed child window
- **AND** eligible live resumes after cleanup only if the same row remains current and usable
- **AND** reopening the auxiliary action later starts a fresh acquisition

#### Scenario: Auxiliary authentication chain is exhausted

- **WHEN** every allowed candidate in the exact-row auxiliary credential suffix is rejected by structured authentication failure
- **THEN** the exact row becomes `соединение потеряно`
- **AND** no additional auxiliary/live/Local Refresh/mutation I/O starts until top full Refresh

### Requirement: Debug is local exact-row presentation

The current `Отладка` action in room mode SHALL be bound to the exact current expanded supported row and SHALL display only that row's accumulated terminal/log presentation. Opening or closing Debug SHALL NOT by itself create device network I/O, stop live, select credentials, or acquire a handler/session.

When no supported expandable row is current, Debug SHALL be unavailable. Switching/collapsing the row SHALL close/invalidate the row-specific Debug presentation so logs cannot be attributed to another record. Any future Debug sub-action that performs device I/O SHALL explicitly enter an approved auxiliary-read or state-changing lifecycle; this change SHALL NOT create an arbitrary network command console.

#### Scenario: Debug opens while live is active

- **GIVEN** the current exact row has active live
- **WHEN** the operator opens Debug
- **THEN** Debug shows that exact row's local accumulated log/terminal state
- **AND** live continues because opening Debug creates no device I/O

### Requirement: State-changing room commands require live retirement and mandatory reconciliation

Opening a state-changing confirmation dialog SHALL NOT stop live or change room/row authority. Cancel SHALL be a no-op. After explicit confirmation, the application SHALL lock incompatible top/accordion/network actions, invalidate active live, complete bounded cleanup/release, and only then submit one exact-row state-changing operation.

If prior live cleanup cannot release authority within policy timeout, the mutation SHALL NOT be sent. Once a state-changing send is attempted or may have been delivered, the application SHALL NOT blindly repeat the command, restart it with another credential, or infer retry safety from user-facing error text, empty success lists, `auth`, `401`, or `403` strings.

Mutation ACK or transport success SHALL NOT be authoritative final state. Every supported room-mode state-changing command SHALL require the existing model-appropriate readback/reconciliation before terminal success. Only successful reconciliation MAY atomically replace the exact row's authoritative cache and permit normal live/controls to resume.

If command execution fails, the outcome is ambiguous, or readback cannot confirm final state, the application SHALL set the exact record's interaction state to blocked/unconfirmed, keep prior cache only as stale/unconfirmed presentation, show a safe operation-specific error, keep live stopped, and require top full Refresh for recovery. Until that full Refresh establishes a new room generation, the record SHALL allow no live, Local Refresh, auxiliary network action, further mutation, or other row network operation; only local presentation remains available. The row SHALL NOT become `не удалось подключиться` merely because a mutation failed. A typed connection/session loss MAY additionally move it to `соединение потеряно`.

#### Scenario: Confirmation is canceled

- **WHEN** the operator opens a mutation confirmation and selects Cancel
- **THEN** no interaction generation is replaced
- **AND** live continues unchanged
- **AND** no mutation or reconciliation I/O starts

#### Scenario: Command ACK arrives before readback

- **WHEN** a confirmed state-changing command receives an ACK or apparent transport success
- **THEN** the operation remains non-terminal
- **AND** authoritative cache is unchanged until mandatory reconciliation succeeds

#### Scenario: Readback cannot confirm the command

- **WHEN** the mutation may have occurred but mandatory readback fails or cannot confirm final state
- **THEN** the mutation is not automatically repeated
- **AND** prior cache remains stale/unconfirmed rather than being overwritten optimistically
- **AND** live, Local Refresh, auxiliary network actions, further mutations, and all other row network I/O stay blocked until top full Refresh
- **AND** local presentation may remain available

### Requirement: Authoritative room cache changes only after accepted read-only data or confirmed reconciliation

Room interaction SHALL treat per-record accepted cache as authoritative snapshot data, not optimistic UI state. Live samples MAY update fields explicitly defined as live presentation but SHALL NOT manufacture a new authoritative device snapshot outside the model's approved live contract.

A local Refresh or auxiliary operation MAY update authoritative cache only where its existing capability explicitly defines the returned data as authoritative device state. A state-changing operation SHALL update authoritative cache only from successful mandatory readback/reconciliation, never from the command request or ACK itself.

If a command is unconfirmed, old cache MAY remain visible but SHALL be marked stale/unconfirmed. Collapse/reopen SHALL render the same exact-row authority state and SHALL NOT resurrect pre-command values as if they were freshly confirmed.

#### Scenario: Successful PDU reconciliation replaces cache

- **WHEN** an exact-row PDU mutation completes and mandatory reconciliation returns accepted current outlet state
- **THEN** that reconciled state atomically replaces the PDU row's authoritative cache
- **AND** collapse/reopen renders the reconciled state

### Requirement: Room credential selection remains application-owned during interaction

Room interactive operations SHALL reuse the existing model-wide ordered credential chains and exact `model + IP` successful candidate/profile memory. The room row SHALL NOT own a secret store and this change SHALL NOT create per-IP credential candidate lists.

Handlers, workers, live samplers, auxiliary readers, mutation workers, and reconciliation workers SHALL NOT select or iterate later credential candidates. Application composition MAY advance only from structured authentication authority under the applicable read-only or pre-mutation rule. A successful candidate/profile SHALL be persisted only after the relevant existing successful-operation boundary is satisfied.

The existing PCS4i credentialless exception remains valid where its approved operation contract permits credentialless access.

#### Scenario: Same-model room devices use independent successful memory

- **GIVEN** two room records use the same model-wide credential chain
- **WHEN** each exact model/IP succeeds with a different candidate index
- **THEN** each exact model/IP retains its own successful memory
- **AND** editing the shared model-wide chain may remap/invalidate successful indexes under the existing credential contract

### Requirement: Top room controls and context changes supersede interaction safely

Top full Refresh SHALL remain the from-scratch room recovery action. When allowed, it SHALL invalidate the old room interaction generation, stop/cancel read-only activity, clear room tree/header/cache presentation, resolve the current target-search context against current inventory/fallback rules, and execute the resulting room cycle again as a first connection. It SHALL NOT preserve a prior expanded secondary row or reuse old per-record cache as current state.

For an unchanged room-name query that still has multiple matches, top full Refresh MAY reuse the currently selected exact `room_id` only when that selection is still current for the same query revision, current inventory snapshot/candidate set, and current room-search result. Otherwise it SHALL require a new explicit selection and SHALL perform no device I/O from the stale candidate.

During auxiliary read, top full Refresh SHALL remain available and SHALL act as the global supersession action after bounded cleanup/abandonment. During Local Refresh, target-search editing, Password, top full Refresh, accordion switching/collapse, and incompatible network/state-changing actions SHALL remain blocked until its terminal cleanup/release boundary. During a confirmed state-changing command through its mandatory reconciliation terminal boundary, top full Refresh, target-search editing, Password, and incompatible accordion/network actions SHALL remain blocked.

Editing the target-search text in post-cycle idle/live state SHALL immediately invalidate current room/live/pending-start authority, invalidate any room-name selection, and clear room presentation. Editing alone SHALL start no network I/O. Returning the field text to the previous value SHALL NOT resurrect the prior generation or prior stale selection.

`Пароль` remains an IP-target/model-wide configuration action rather than a room-name or secondary-row credential editor. It MAY be exposed through an application `Действия` menu. Cancel and Save-without-effective-change SHALL preserve the current room/live state. A real effective credential-chain change SHALL invalidate exact-row sessions/live, clear current room/tree/cache state, and require a new diagnostic start.

Theme switching is presentation-only and SHALL NOT be treated as a target/context change: it SHALL NOT invalidate room generations, stop live, clear caches, or start device I/O.

#### Scenario: Auxiliary read is superseded by top Refresh

- **GIVEN** an auxiliary read is active
- **WHEN** top full Refresh is requested
- **THEN** the auxiliary context loses authority and is cancelled/retired
- **AND** the new full room cycle starts only under the new room generation after current target resolution
- **AND** late auxiliary callbacks cannot update it

#### Scenario: Source IP is edited after room completion

- **GIVEN** room mode was entered through an IP target
- **WHEN** the operator changes the persistent target-search text
- **THEN** the current room interaction/tree/cache authority and any current room-name selection are invalidated immediately
- **AND** no replacement device I/O begins until Enter/top Refresh creates a new current context

#### Scenario: Target search is edited after room completion

- **WHEN** the operator changes the target-search text
- **THEN** the current room interaction/tree/cache authority and any room-name selection are invalidated immediately
- **AND** no replacement device I/O begins until Enter/top Refresh creates a new current context

#### Scenario: Old room selection cannot survive query edit

- **GIVEN** a multi-result room-name query has an exact selected room ID
- **WHEN** the search field is edited and later returned to the old visible text
- **THEN** the old selected room does not regain authority automatically
- **AND** current room resolution/selection is required again

#### Scenario: Theme toggle does not supersede room interaction

- **GIVEN** a room is connected and an allowed live lifecycle is active
- **WHEN** the operator switches between dark and light themes
- **THEN** current exact-row authority and live lifecycle remain unchanged
- **AND** no device network I/O is started by theme switching

### Requirement: Post-cycle degradation is isolated per record and room summary remains full-cycle based

A post-cycle typed connection loss, terminal local Refresh failure, cleanup abandonment, or failed/ambiguous/unconfirmed state-changing outcome SHALL affect only the exact room record that owns that operation. Other connected room records SHALL retain their authoritative cache and eligible interaction capabilities.

For each of those terminal degradation/problem categories, the global bottom status SHALL become `Есть проблемы с соединением`. `Последнее обновление` SHALL remain the completion time of the last full room cycle, including a cycle that performed zero device I/O. Local Refresh, live, auxiliary reads, mutations, and reconciliation SHALL NOT change that timestamp.

An ordinary auxiliary parse/business failure or warning that does not degrade the row's connection/session state SHALL NOT by itself change the global bottom status to a connection problem. A later successful local/auxiliary operation SHALL NOT declare the entire room clean or rewrite the historical result of the last full cycle. Only a new top full Refresh MAY recompute a clean `Опрос завершён` room summary.

#### Scenario: One record loses live while another remains healthy

- **GIVEN** two room records completed the room cycle successfully
- **WHEN** live/session failure degrades one record
- **THEN** that record's network/state-changing actions are blocked
- **AND** the global bottom status becomes `Есть проблемы с соединением`
- **AND** the other record remains eligible for its normal interaction lifecycle when expanded

#### Scenario: Ordinary auxiliary parse error does not create a room connection problem

- **GIVEN** a connected row remains connection/session-usable
- **WHEN** an auxiliary read ends with an ordinary parse/business failure only
- **THEN** the row remains connected
- **AND** that failure alone does not change the global bottom status to `Есть проблемы с соединением`

### Requirement: Room interaction cleanup and shutdown are bounded and non-blocking

Room live, local Refresh, auxiliary read, mutation/reconciliation network work, and their cleanup SHALL execute outside the Qt GUI thread. Invalidation SHALL make old callbacks stale immediately; actual network/session cleanup SHALL run on the owning background lane and SHALL be bounded by policy rather than wait forever.

If read-only cleanup times out, the old context SHALL be logically abandoned and late callbacks SHALL remain powerless. The affected row SHALL become degraded as applicable, the global bottom status SHALL become `Есть проблемы с соединением`, and the abandonment SHALL NOT permanently prevent a later top full Refresh/new room generation.

Closing the application during read-only room activity SHALL require no warning dialog: generations are invalidated immediately, cancellation is published, GUI close does not wait for network timeout, and cleanup is best-effort. If a confirmed state-changing operation may have been sent and has not reached its reconciliation terminal boundary, application close SHALL warn that the final device state may be unconfirmed. If the user confirms close, the application SHALL perform no mutation retry or rollback and late callbacks SHALL not update destroyed UI.

#### Scenario: Read-only cleanup times out

- **WHEN** an invalidated live/auxiliary/local-refresh lifecycle does not confirm cleanup within policy timeout
- **THEN** old authority is abandoned
- **AND** late callbacks are ignored
- **AND** the global bottom status becomes `Есть проблемы с соединением`
- **AND** a later top full Refresh may establish a new generation without waiting forever for the abandoned lifecycle

#### Scenario: Application closes during possible mutation

- **WHEN** a confirmed mutation may have been sent and reconciliation is not terminal
- **AND** the operator confirms application close after warning
- **THEN** no retry or rollback is attempted
- **AND** current generations are invalidated
- **AND** the application may exit with real device state unknown

### Requirement: Legacy no-room single-device interaction remains compatible

When a unique supported inventory source has `room_id = null`, the existing legacy single-device interactive behavior SHALL remain available under its current model-specific lifecycle. Room exact-row interaction authority, room summary state, and room full-refresh-only recovery SHALL NOT be imposed merely because shared infrastructure was refactored for room mode.

#### Scenario: Supported no-room codec is diagnosed

- **GIVEN** a unique supported source record has `room_id = null`
- **WHEN** legacy single-device diagnostics completes
- **THEN** its existing live, local Refresh, auxiliary, Debug, and supported state-changing behavior remains governed by the legacy contracts
- **AND** no synthetic room interaction session is created

### Requirement: PDU room presentation no longer owns related-codec enrichment

In room mode, a PDU row SHALL present and control only that exact PDU record under its existing supported PDU capability. Accepted PDU refresh or mutation reconciliation SHALL NOT start a secondary room lookup, related-codec credential/session lifecycle, related-codec status read, or PDU-hosted codec live meter.

Shared room name, address, and VIP SHALL appear only in the shared room header above the tree. Related codec diagnostics, call/presentation state, and supported live metering SHALL appear only through the related codec's own exact room row. The legacy PDU `Комната и связанный кодек` block and its dedicated related-codec lane SHALL be removed.

#### Scenario: PDU row refreshes after migration

- **WHEN** a room-mode Aten or PCS4i row completes an accepted PDU refresh
- **THEN** its PDU data/controls remain available
- **AND** no related-codec resolver, session, worker, status normalization, or live meter starts as a side effect
- **AND** the codec remains independently represented by its own room row
