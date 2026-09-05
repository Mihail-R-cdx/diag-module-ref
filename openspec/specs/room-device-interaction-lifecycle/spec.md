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

### Requirement: Extron IN1804 room routing uses the unified serialized mutation and reconciliation lifecycle

The exact `Extron IN1804` unified application registration SHALL be the sole authority for enabling Matrix room routing. MIH-11 SHALL add explicit Matrix room mutation and reconciliation bindings to that existing exact-model registration rather than introducing a separate Matrix route model list, widget-type check, model substring test, standalone-screen capability inference, or other parallel authority.

The approved registration shape SHALL be equivalent in meaning to:

```text
mutation binding       -> matrix_room_route
reconciliation binding -> matrix_room_route_reconcile
cleanup/release        -> approved room interaction cleanup authority
```

Existing Extron IN1804 room one-shot/local-refresh and `matrix_room_live` bindings SHALL remain the acquisition/live authorities. Adding Matrix mutation SHALL NOT create a second room interaction lane or replace those bindings.

Application startup/composition SHALL fail closed if the exact Extron IN1804 registration declares Matrix room routing but its mutation, reconciliation, cancellation, or required cleanup/release hook is unavailable or contradictory.

#### Scenario: Exact Extron registration owns route capability

- **GIVEN** current exact model registration for `Extron IN1804`
- **WHEN** room interaction capabilities are composed
- **THEN** Matrix route mutation/reconciliation availability comes from that one registration
- **AND** no `MATRIX_ROUTE_MODELS`, widget-type inference, standalone `MatrixScreen` signal, or equivalent parallel capability authority is consulted

#### Scenario: Matrix route binding is declared but unavailable

- **GIVEN** the exact Extron IN1804 registration declares Matrix room mutation/reconciliation
- **WHEN** composition cannot resolve a required mutation, reconciliation, cancellation, or cleanup hook
- **THEN** startup/composition fails closed
- **AND** the GUI cannot expose a route control that would bypass the missing lifecycle authority

### Requirement: Matrix route intent is exact-row, confirmed, and stale-safe before device acquisition

A Matrix room route may start only from the current expanded exact `Extron IN1804` record after the room automatic cycle is terminal and the row has current usable connected state. The route intent SHALL be immutable and non-secret, containing output 1 and one accepted current input number; target authority remains the existing immutable `RoomInteractionContext` with exact room generation, `record_id`, model, IP, operation token/currentness, and credential context revision.

The room presentation SHALL NOT supply credentials, handler/session identity, target-search text, initial source IP/record, standalone Matrix screen state, or another widget's target as mutation authority.

Opening the confirmation dialog SHALL perform no Matrix I/O, stop no live owner, and change no room generation. Cancel SHALL be a no-op. Only explicit confirmation MAY call the existing `RoomInteractionCoordinator.confirm_mutation()` path.

Before a Matrix mutation adapter acquires a handler/session or sends a route command, composition/application currentness checks SHALL still accept the exact mutation context. Active Matrix live SHALL be invalidated and retired through the existing bounded cleanup/release boundary before mutation acquisition. If live cleanup cannot reach the permitted boundary, the route SHALL NOT be sent.

A stale/superseded context SHALL be rejected before handler/session acquisition and before route send. Late presentation events or callbacks from an old exact row SHALL NOT start or revive Matrix mutation.

#### Scenario: Confirmation is canceled

- **GIVEN** a current actionable Matrix output cell produced a safe route intent
- **WHEN** the operator cancels the confirmation dialog
- **THEN** no room mutation generation is started
- **AND** current Matrix live remains unchanged
- **AND** no handler/session is acquired and no route command is sent

#### Scenario: Live cannot retire before route

- **GIVEN** Matrix live owns the current exact row
- **AND** the operator confirms a route
- **WHEN** live cleanup cannot release authority within the approved bounded policy
- **THEN** the route command is not sent
- **AND** no Matrix mutation owner acquires overlapping device resources

#### Scenario: Stale route is rejected before acquisition

- **GIVEN** a route intent was produced for Matrix record A
- **WHEN** A loses exact-row/current-room authority before mutation acquisition
- **THEN** the route is rejected
- **AND** no Matrix handler/session, credential attempt, or network I/O starts for that stale intent

### Requirement: Matrix mutation receives one application-selected credential attempt and never owns fallback policy

For each Matrix room mutation attempt, application/composition SHALL select the current approved credential candidate/index using the existing exact-row credential plan and SHALL give the background Matrix mutation owner exactly one candidate for that attempt. The Matrix route worker/adapter/handler SHALL NOT enumerate or advance credential candidates.

A structured authentication rejection MAY authorize the application to advance to the next approved candidate only when the rejection is proven to occur before the state-changing route command could have been delivered and only after prior attempt cleanup/release. Existing successful-candidate preference and successful-index persistence rules remain unchanged; an index is remembered only after accepted success evidence at the existing application boundary.

Once the route send has been invoked, may have reached the device, or otherwise has ambiguous delivery/outcome, no automatic credential advance, command replay, read-only retry policy, or user-facing string heuristic may repeat the route. `auth`, `401`, `403`, empty result data, timeout text, or another public error string SHALL NOT independently authorize fallback.

The Matrix mutation adapter SHALL preserve the existing typed failure separation between structured pre-delivery authentication rejection and ambiguous/unknown command outcome.

#### Scenario: First candidate is rejected before route delivery

- **GIVEN** candidate 0 is selected for a confirmed exact Matrix route
- **WHEN** a typed authentication rejection is proven before the route command can be delivered
- **THEN** candidate 0 is cleaned up
- **AND** application composition MAY advance to the next approved candidate
- **AND** the worker/handler itself does not choose the next candidate

#### Scenario: Authentication-like failure follows route send invocation

- **GIVEN** the route send has been invoked or may have been delivered
- **WHEN** a later failure appears authentication-like or otherwise ambiguous
- **THEN** the operation is treated as unconfirmed/unknown outcome
- **AND** no credential candidate advance or route replay occurs
- **AND** user-facing error strings do not change that decision

### Requirement: Matrix route send is background-owned, at-most-once, and non-authoritative until readback

The Matrix state-changing route operation SHALL execute outside the Qt GUI thread. It SHALL use the exact current `RoomInteractionContext`, output 1, accepted current input N, and one application-selected credential attempt. The route command SHALL be treated as non-replay-safe.

For one confirmed mutation generation, the route send SHALL be attempted at most once per credential attempt, and no attempt after possible delivery may repeat it. If a pre-delivery structured authentication rejection safely authorizes a different candidate, the previous attempt must be proven not to have delivered the route and must reach cleanup/release before the next candidate may acquire device resources.

Mutation transport success or device ACK SHALL NOT be accepted as authoritative route state. It SHALL NOT directly replace the row cache, set `current_connection`, or render the requested input as authoritative active. Mutation success hands only non-secret requested-route evidence to mandatory Matrix reconciliation.

Any Matrix route transport/session owner SHALL release or reach its approved bounded cleanup boundary before reconciliation may acquire conflicting Matrix device resources. If an implementation cannot prove that boundary, it SHALL not overlap mutation and reconciliation and must return for architecture review rather than weaken serialization.

#### Scenario: Route ACK is received

- **WHEN** an exact Matrix route send returns ACK/apparent success
- **THEN** the mutation remains non-authoritative for final route state
- **AND** accepted row cache/current connection are unchanged
- **AND** mandatory Matrix reconciliation begins only through the serialized lifecycle

#### Scenario: Route outcome is ambiguous

- **WHEN** route delivery or result is ambiguous after a possible send
- **THEN** no replay occurs
- **AND** the exact row becomes blocked/unconfirmed according to the existing state-changing room contract
- **AND** prior accepted cache may remain only as stale/unconfirmed presentation
- **AND** top full Refresh is required for recovery

### Requirement: Matrix reconciliation confirms the requested input before accepting new route state

Every successful Matrix room route mutation SHALL enter the existing `RECONCILIATION` phase. The Matrix reconciliation binding SHALL preserve the requested output/input identity as non-secret operation evidence and SHALL perform current exact-row read-only Matrix acquisition using the current reconciliation context rather than standalone/global Matrix target state.

A successful readback is authoritative for the mutation only when accepted current evidence establishes:

```text
current_connection == requested input_num
```

The expected output is always output 1 for the current Extron IN1804 contract.

If readback succeeds but reports a different connection, no current connection, malformed/unknown route evidence, or otherwise fails to confirm the requested input, reconciliation SHALL fail unconfirmed. Prior accepted cache may remain visible only as stale/unconfirmed context; the row SHALL remain blocked from live, Local Refresh, auxiliary network actions, further mutation, and other row network I/O until top full Refresh establishes a new room generation, according to the existing generic mutation contract.

If readback confirms the requested input, the full accepted reconciliation snapshot MAY atomically replace the exact row's cache. Only then MAY normal usable interaction state and eligible Matrix live resume after cleanup/currentness checks.

A stale reconciliation callback from a superseded room/record/operation context SHALL be ignored and SHALL NOT update visible route state, row cache, credential memory, or lifecycle authority.

#### Scenario: Readback confirms requested route

- **GIVEN** output 1/input N was delivered successfully and entered reconciliation
- **WHEN** current exact-row readback returns an accepted Matrix snapshot with `current_connection == N`
- **THEN** that full snapshot atomically becomes accepted row state
- **AND** input N may render as authoritative `активен`
- **AND** normal eligible room interaction/live may resume only after lifecycle cleanup/currentness checks

#### Scenario: Readback returns another input

- **GIVEN** output 1/input N was requested
- **WHEN** reconciliation returns accepted Matrix evidence with `current_connection != N`
- **THEN** the command is not considered confirmed
- **AND** the row remains blocked/unconfirmed with prior cache only as stale context
- **AND** no further row network operation is allowed before top full Refresh

#### Scenario: Reconciliation route evidence is unknown

- **GIVEN** a route mutation entered reconciliation
- **WHEN** the readback cannot establish a current input
- **THEN** reconciliation fails unconfirmed
- **AND** the GUI does not optimistically mark the requested input active
- **AND** top full Refresh is required for recovery

#### Scenario: Late reconciliation callback is stale

- **GIVEN** Matrix reconciliation context A has been superseded by a new room generation or exact-row context
- **WHEN** A later returns a matching route snapshot
- **THEN** the stale callback is ignored
- **AND** it cannot update current route presentation, accepted cache, credential memory, or interaction state

### Requirement: Matrix room routing preserves existing PDU, Matrix live, and standalone lifecycle boundaries

MIH-11 SHALL add Matrix route mutation as a model-specific binding within the existing room interaction architecture rather than by renaming PDU-specific code into an unsafe shared handler path. Composition MAY generalize dispatch/cleanup plumbing where appropriate, but model-specific mutation owners SHALL remain explicit and cancellation SHALL target the actual current owner.

Existing PDU mutation/reconciliation behavior SHALL remain unchanged. Existing Matrix room automatic one-shot/local Refresh and `matrix_room_live` behavior SHALL remain unchanged except that confirmed Matrix mutation uses the already-approved live-retirement lock before send and may resume eligible live only after confirmed reconciliation.

Standalone `MatrixScreen` and standalone `MatrixController` routing SHALL remain a separate supported surface. MIH-11 SHALL NOT make room routing depend on standalone widget selection/global target state, and SHALL NOT make standalone routing depend on room expanded-row state.

#### Scenario: PDU mutation remains independent

- **GIVEN** Matrix room routing support is present
- **WHEN** an existing PDU room mutation is performed
- **THEN** its existing PDU mutation/reconciliation binding and cancellation behavior remain unchanged
- **AND** no Matrix route owner is acquired

#### Scenario: Matrix room live resumes only after confirmed reconciliation

- **GIVEN** Matrix live was retired for a confirmed route
- **WHEN** Matrix reconciliation succeeds and cleanup/currentness checks complete
- **THEN** eligible live MAY resume through the existing `matrix_room_live` binding
- **AND** no second Matrix live lane is created

#### Scenario: Standalone route remains separate

- **GIVEN** the standalone Matrix screen/controller supports output-1 routing
- **WHEN** MIH-11 room routing is implemented
- **THEN** standalone routing keeps its own existing application controller boundary
- **AND** room routing does not use standalone widget target state as exact-row authority

### Requirement: Codec expansion performs at most one automatic call-log preview attempt per expansion epoch

After the automatic room cycle is terminal, when a current connected/usable exact codec row whose unified registration advertises the existing call-log auxiliary binding transitions from collapsed to expanded under current room authority, the application SHALL admit exactly one automatic call-log preview attempt for that new **expansion epoch** through the existing serialized room interaction lane. Admission of that automatic intent is mandatory for the eligible post-terminal expansion; later currentness, retirement, cancellation or cleanup gates MAY prevent device I/O, but the implementation SHALL NOT leave the row merely "eligible" without submitting the one automatic attempt.

An expansion epoch SHALL be application-owned non-secret presentation/lifecycle state identified by the current room generation, exact `record_id`, and a monotonically changing row-expansion token or equivalent. A new epoch begins only when that exact row transitions from collapsed to expanded under current room authority. Re-rendering, resize, theme switching, hover, repaint, duplicate Qt expansion notifications, or rebuilding the same already-expanded presentation SHALL NOT create a new epoch.

If the codec row becomes expanded before the automatic room cycle reaches terminal state, the application SHALL remember only that current expanded selection/epoch and SHALL admit its one automatic preview attempt after the cycle becomes terminal if the same exact row/epoch remains current and eligible. The pre-terminal expansion itself SHALL NOT start device I/O.

All preview network acquisition SHALL enter the existing single serialized room interaction lane as `AUXILIARY_READ` and SHALL preserve the existing auxiliary credential, lock, cleanup, degradation and supersession rules. Before preview I/O begins, any current LIVE owner for that row SHALL lose authority and retire through the existing bounded cleanup/release boundary. Preview I/O SHALL start only after that boundary and only if the same room generation, `record_id`, exact model/IP, expansion epoch and operation/currentness token remain current and eligible. After terminal preview cleanup, eligible LIVE MAY start/resume only for the still-current expanded usable row.

The automatic-attempt marker SHALL become terminal for that expansion epoch after any current terminal preview result, including:

```text
accepted success with records
accepted success with zero records
ordinary parse/business/no-data failure that does not degrade the row
typed terminal connection/session/authentication failure
```

A terminal ordinary failure SHALL therefore render `Нет данных` and complete the automatic attempt; it SHALL NOT leave the same expansion epoch eligible for an automatic retry. Re-render, theme switch, resize, repaint, hover, duplicate expansion events, LIVE resume, or another local presentation event SHALL cause zero additional automatic preview I/O for that completed epoch.

A new automatic preview attempt SHALL be admitted only after an authority boundary creates a new current eligible expansion epoch and the automatic room cycle is terminal. Such boundaries include collapse followed by explicit re-expand of that codec row, expansion of another row followed by a later re-expand, a new room generation/top full Refresh followed by a new current expansion, or target/context/credential-context invalidation followed by a new valid room context and a new current expansion. Merely returning the UI to the same visible values or rebuilding an already-expanded row does not create or admit another automatic attempt.

Collapsing the row, expanding another row, top full Refresh, target-search/context invalidation, credential-context invalidation or application shutdown SHALL immediately make active preview callbacks stale and publish cancellation/retirement where applicable. Late preview callbacks SHALL NOT update another row, reopen a child window, resume LIVE for an old context, change credential-success memory outside an accepted current operation, or become current cache authority.

An ordinary preview parse/business failure without typed connection/session loss SHALL keep the row connected. Terminal typed connection/session loss or terminal authentication failure after allowed fallback is exhausted SHALL follow the existing auxiliary degradation/recovery contract.

#### Scenario: Post-terminal codec expansion automatically admits preview

- **GIVEN** the automatic room cycle is terminal
- **AND** a current connected/usable exact codec row with the registered call-log auxiliary binding is collapsed
- **WHEN** the operator expands that codec row and creates a new current expansion epoch
- **THEN** the application admits exactly one automatic call-log preview attempt through the existing `AUXILIARY_READ` lane for that epoch
- **AND** duplicate expansion notifications, render, resize, repaint or theme switching do not admit another automatic attempt for the same epoch

#### Scenario: Codec was expanded before the room cycle finished

- **GIVEN** a codec row owns a current expansion epoch while the automatic room cycle is still running
- **WHEN** the room cycle later reaches terminal state and that exact row/epoch remains current, connected/usable and call-log capable
- **THEN** one automatic call-log preview attempt is admitted through the auxiliary lane
- **AND** the earlier expansion itself performed no device I/O before the terminal room boundary

#### Scenario: Preview business failure is one-shot for the epoch

- **GIVEN** an automatic preview attempt for the current exact row/expansion epoch ends with an ordinary parse/business/no-data failure
- **WHEN** the same expanded presentation is rebuilt, resized, repainted, theme-switched or receives duplicate expansion notifications
- **THEN** no additional automatic call-log read is admitted for that epoch
- **AND** the row remains connected unless the failure separately proves typed connection/session loss

#### Scenario: Collapse and re-expand creates a new attempt boundary

- **GIVEN** the current codec expansion epoch already completed its automatic preview attempt
- **WHEN** the operator collapses that row and later explicitly expands it again under the same otherwise-current terminal room generation
- **THEN** the new expansion receives a new expansion epoch
- **AND** one new automatic preview attempt is admitted if the row is still current, connected/usable and call-log capable

#### Scenario: Codec expansion starts preview after live retirement

- **GIVEN** a terminal room has a current connected codec row with a registered call-log auxiliary binding
- **AND** LIVE currently owns that row
- **WHEN** the current expansion epoch's mandatory automatic call-log preview attempt is admitted
- **THEN** LIVE is invalidated and retired before preview handler/session acquisition
- **AND** exactly one `AUXILIARY_READ` preview may perform network I/O
- **AND** eligible LIVE may resume only after preview cleanup and currentness checks

#### Scenario: Row switch makes old preview stale

- **GIVEN** row A has an active call-log preview
- **WHEN** the operator expands row B
- **THEN** A's preview loses authority and is cancelled/retired under the existing auxiliary boundary
- **AND** late A callbacks cannot update B or restart A live
- **AND** any B network lifecycle waits for the permitted A retirement boundary

### Requirement: Room codec controls use registry-owned exact-row state-changing lifecycle bindings

The unified exact application model registration SHALL remain the sole runtime capability authority for codec room controls. Each current exact codec registration SHALL explicitly declare support or absence for:

```text
speaker_adjust
speaker_mute
microphone_adjust
microphone_mute
reboot
```

The required current-baseline values are the OpenSpec test oracle defined by `device-diagnostics-and-control`; they SHALL NOT be copied into a second runtime support table. Application composition SHALL fail closed if a codec operation is declared supported but its required adapter, model-safe target policy, readback/reconciliation binding, cancellation or cleanup hook is unavailable or contradictory.

A dashboard click for an explicitly unsupported operation SHALL be resolved locally before `RoomInteractionCoordinator` mutation admission. The local affordance SHALL show the approved non-secret informational result and SHALL NOT invalidate LIVE, replace an interaction generation, acquire a handler/session, select credentials or perform device network I/O. The operation remains an unsupported **network capability** even though the fixed dashboard retains a visible local affordance. Existing active/retiring lifecycle locks MAY temporarily disable the common controls.

A supported codec state-changing operation SHALL bind to the current immutable exact-row `RoomInteractionContext` and use the existing `MUTATION -> RECONCILIATION` lifecycle. It SHALL preserve all stronger generic mutation rules: LIVE retirement before send, no send if cleanup cannot reach its permitted boundary, one state-changing delivery attempt at most under current policy, no blind replay/credential advance after possible delivery, mandatory model-appropriate readback, authoritative cache update only after confirmed reconciliation, and row network blocking until top full Refresh after ambiguous/unconfirmed outcome.

For non-disruptive codec audio controls, the operator's click on an explicit provable desired-state control SHALL constitute the explicit mutation confirmation required by the generic room mutation contract; no second confirmation dialog SHALL be inserted between the control click and lifecycle admission. A future supported `reboot` would require a separate explicit confirmation dialog because reboot is disruptive; current baseline reboot support is `UNSUPPORTED` for all five codecs.

The presentation SHALL NOT call standalone `CodecScreen`, handlers or transports directly and SHALL NOT determine support from widget type, handler method presence, model substring, localized text or an independent codec model list.

#### Scenario: Unsupported codec control is local only

- **GIVEN** the exact codec registration explicitly marks the requested dashboard network operation unsupported
- **AND** the common controls are not temporarily locked by another lifecycle
- **WHEN** the operator clicks its visible affordance
- **THEN** the application displays the unsupported-operation information locally
- **AND** no room interaction generation or network owner changes
- **AND** no handler/session is acquired and current LIVE remains eligible/unchanged

#### Scenario: Audio control click is its explicit desired-state confirmation

- **GIVEN** an eligible current codec row supports the selected audio operation
- **WHEN** the operator clicks `+`, `−` or mute with a provable desired target
- **THEN** no secondary modal confirmation is required
- **AND** the click may be admitted into the existing mutation lifecycle after normal exact-row/currentness gates

#### Scenario: Declared codec control binding is unavailable

- **GIVEN** an exact codec registration declares a dashboard operation supported
- **WHEN** composition cannot resolve its required operation/readback/cleanup binding
- **THEN** startup/composition fails closed
- **AND** the GUI cannot expose that operation as a network-capable room control

### Requirement: Codec relative and mute controls derive only from authoritative typed audio evidence

Room codec `+` and `−` controls SHALL NOT be implemented as blind relative device commands or by guessing a starting value. Before mutation admission, application/core codec-control composition SHALL use current accepted exact-row numeric `speaker_volume` or `microphone_volume` plus the registry-bound model range/step policy to derive one valid absolute target.

If the current numeric value, range, step or applicable operation support cannot be proven for the exact row, the click SHALL produce a safe local unavailable/unsupported informational result and SHALL perform no device I/O. A fallback default such as minimum volume, zero, another model's range, or a stale standalone-widget value SHALL NOT become mutation authority.

Mute/unmute SHALL likewise resolve to an explicit desired model-safe target, not a blind toggle. The application SHALL consume the separate typed mute-state and restore authority defined by `device-diagnostics-and-control`:

- supported TE20/TE40/Polycom microphone mute uses typed `MUTED`/`UNMUTED` readback and never numeric-gain inference;
- supported speaker mute for current codecs may map to absolute zero/restore only when current numeric volume and exact-row room-owned restore evidence prove the target;
- widget-local `last_unmuted_volume`, fallback `1`, minimum volume or requested-but-unconfirmed values SHALL NOT supply restore authority;
- when unmute cannot prove a restore target, the click remains local unavailable and starts zero mutation/network I/O.

Model-specific range/step/mute policy SHALL come from the registry-owned binding/adapter. Shared Qt presentation SHALL NOT hard-code model names to choose command semantics.

#### Scenario: Volume value is unavailable

- **GIVEN** a supported codec row has no current authoritative speaker value from which a `+` target can be derived
- **WHEN** the operator clicks `+`
- **THEN** no guessed absolute target is created
- **AND** no mutation/handler/device I/O starts
- **AND** a safe informational unavailable result is shown

#### Scenario: Speaker unmute lacks restore authority

- **GIVEN** the current exact row has accepted speaker volume zero
- **AND** no current exact-row/generation non-zero restore target is proven
- **WHEN** the operator clicks speaker unmute
- **THEN** no fallback target is fabricated
- **AND** no mutation/handler/device I/O starts

#### Scenario: Supported audio target reconciles

- **GIVEN** current authoritative audio evidence and registry-bound model policy produce a valid absolute or typed desired target
- **WHEN** the operator requests an audio change
- **THEN** one exact-row mutation may send that desired target after currentness/live-retirement gates
- **AND** only matching accepted readback may confirm the operation and replace authoritative row audio state

### Requirement: Fixed PDU dashboard reuses the existing exact-row refresh and mutation lifecycle

The dedicated common room PDU dashboard SHALL remain a presentation/application-intent surface over the existing exact-row room interaction architecture. It SHALL NOT introduce a PDU-specific interaction lane, direct widget-to-handler path, alternate credential owner, optimistic accepted-state owner, or independent request generation.

The sole visible PDU refresh control, `Обновить статус`, SHALL publish the existing exact-row `LOCAL_REFRESH` intent/lifecycle. It SHALL use the existing eligibility state, lock state, current exact-row context, operation token/generation, stale-result suppression, and serialized interaction policy. Activating it while another Local Refresh or incompatible room network lifecycle is active/retiring SHALL not create a concurrent PDU refresh.

A supported individual PDU action (`Вкл`, `Выкл`, or supported `Перезапуск`) and supported bulk action (`Включить всё` or `Выключить всё`) SHALL enter only the existing state-changing room path after its existing explicit confirmation boundary. Existing LIVE retirement where applicable, exact-row currentness, credential ownership, no-blind-retry policy, mutation ambiguity handling and mandatory reconciliation remain unchanged. A command ACK/request result SHALL NOT become accepted outlet state; only successful current reconciliation MAY atomically replace the exact PDU row cache.

A fixed visible PDU affordance that exact capability authority marks unsupported SHALL resolve locally before interaction-coordinator admission. Such a local unsupported click SHALL NOT invalidate LIVE, acquire credentials/handler/session, reserve the interaction lane, create a mutation/reconciliation generation, alter accepted cache or perform device network I/O. During any active/retiring lifecycle that normally disables the corresponding refresh or state-changing controls, the visible common PDU controls SHALL obey that same temporary lock; the local-only unsupported exception does not bypass lifecycle locking.

Bulk ON/OFF SHALL reuse the current application-owned bulk policy and deterministic outlet sequencing. Presentation SHALL NOT implement bulk by programmatically clicking individual Qt controls or create a parallel set of per-outlet network owners. No bulk reboot lifecycle is introduced.

PDU dashboard rendering, theme switching, hover, scrolling, resizing and power-placeholder presentation SHALL perform no network interaction.

#### Scenario: Sole PDU text refresh uses the existing lifecycle

- **GIVEN** a current expanded connected PDU row is eligible for Local Refresh
- **WHEN** the operator activates `Обновить статус`
- **THEN** the same existing exact-row `LOCAL_REFRESH` intent/lifecycle is requested
- **AND** the control owns no separate worker/session/generation
- **AND** it follows the existing active/retiring lock state

#### Scenario: Supported Aten outlet mutation keeps mandatory reconciliation

- **GIVEN** a current connected Aten outlet is eligible for a supported state-changing action
- **WHEN** the operator confirms `Вкл`, `Выкл`, or `Перезапуск`
- **THEN** the existing exact-row PDU mutation path owns the send
- **AND** accepted outlet state changes only after current mandatory reconciliation succeeds
- **AND** ambiguous/failed reconciliation follows the existing blocked/unconfirmed recovery policy

#### Scenario: Unsupported fixed PDU action never enters room interaction

- **GIVEN** the fixed common PDU dashboard shows an affordance unsupported by the exact model
- **AND** no lifecycle lock currently disables that affordance
- **WHEN** the operator activates it
- **THEN** support is resolved before room interaction admission and a local unsupported information result is shown
- **AND** no lifecycle authority, handler/session, credentials, network I/O or accepted state changes

#### Scenario: Bulk operation does not use Qt buttons as execution owners

- **WHEN** an eligible current PDU row starts `Включить всё` or `Выключить всё`
- **THEN** the existing application-owned bulk PDU lifecycle owns deterministic execution/reconciliation
- **AND** the dashboard does not emulate bulk by triggering individual outlet buttons

### Requirement: Modern PDU presentation preserves exact-row and related-codec separation

All PDU dashboard refresh/mutation intents SHALL remain bound to the immutable exact current expanded PDU row context required by the root lifecycle. Model/IP/record identity SHALL NOT be reconstructed from displayed card text, outlet names, target-search contents or standalone screen state.

The modern PDU dashboard SHALL continue to present/control only that exact PDU. It SHALL NOT restore the removed PDU-hosted related-codec resolver, credential/session path, call/presentation read, microphone meter, worker or child network lane. Shared room metadata and codec diagnostics remain owned by the common room header and the codec row respectively.

#### Scenario: Modern PDU local refresh remains PDU-only

- **WHEN** the modern PDU `Обновить статус` control completes an accepted exact-row refresh
- **THEN** only current PDU data/presentation is eligible to update
- **AND** no related-codec lookup/session/status/meter lifecycle starts
- **AND** codec data remains owned by its own exact room row

### Requirement: Debug visibility is exact-row presentation for approved non-codec/non-PDU families

The current `Отладка` action in room mode SHALL be bound to the exact current expanded supported row only on device-family presentations that explicitly retain the approved Debug affordance. Opening or closing Debug SHALL NOT by itself create device network I/O, stop live, select credentials, or acquire a handler/session.

When no supported row with an approved visible Debug affordance is current, Debug SHALL be unavailable. Switching/collapsing the row SHALL close/invalidate the row-specific Debug presentation so logs cannot be attributed to another record. Any future Debug sub-action that performs device I/O SHALL explicitly enter an approved auxiliary-read or state-changing lifecycle; this change SHALL NOT create an arbitrary network command console.

The modern expanded **codec** dashboard intentionally exposes no local `Отладка` affordance. The modern expanded **PDU** dashboard continues to expose no local `Отладка` affordance. These are presentation-visibility exceptions only: they do not delete accumulated logs, change codec/PDU network capability, create alternate Debug paths, authorize hidden direct commands, or alter approved exact-row Debug controls for other device families.

For another device family whose approved presentation retains Debug, the action remains local exact-row presentation and remains outside the serialized network lane because it performs no device I/O.

#### Scenario: Retained-family Debug opens while live is active

- **GIVEN** a current exact supported non-codec/non-PDU row with an approved Debug affordance has active live
- **WHEN** the operator opens Debug
- **THEN** Debug shows that exact row's local accumulated log/terminal state
- **AND** opening Debug creates no device I/O, credential selection, or handler/session acquisition
- **AND** live continues because opening Debug creates no device I/O

#### Scenario: Modern codec row omits local Debug

- **WHEN** a current supported codec row is expanded in the modern five-card dashboard
- **THEN** no local `Отладка` control is visible
- **AND** no Debug network capability or alternate lifecycle is created
- **AND** removal of the affordance does not delete internal accumulated logs

#### Scenario: Modern PDU row omits local Debug

- **WHEN** a current supported PDU row is expanded in the modern dashboard
- **THEN** no local `Отладка` control is visible
- **AND** no Debug network capability or alternate lifecycle is created

#### Scenario: Other approved device family Debug remains exact-row presentation

- **GIVEN** a current expanded supported non-codec/non-PDU row has an approved visible Debug presentation
- **WHEN** the operator opens Debug
- **THEN** Debug shows that exact row's local accumulated log/terminal state
- **AND** opening it creates no device I/O, credential/session acquisition, or change to row authority
- **AND** active live may continue because local Debug creates no network lifecycle

### Requirement: Codec automatic preview and explicit detail retain distinct call-log acquisition authority

The existing room call-log application/controller boundary SHALL separate normalized acquisition/result ownership from the side effect of showing `CallLogWindow`. Automatic room preview and explicit detailed-journal opening SHALL use the same approved call-log capability, parser/normalizer contract, credential authority, and serialized room `AUXILIARY_READ` lane, but they SHALL remain distinct acquisition epochs/results.

A current accepted automatic-preview result SHALL remain bound to its immutable exact row/generation/expansion epoch and MAY populate only the inline three-record preview plus other preview-owned presentation state approved for that automatic acquisition. It SHALL NOT become the accepted load result for a later explicit detailed-journal opening.

Every eligible explicit `Развернуть` / detailed call-log opening SHALL be treated as a new operator auxiliary intent and SHALL start one fresh serialized exact-row call-log `AUXILIARY_READ` even when a current accepted full automatic-preview result already exists. The detailed child window MAY open immediately in its existing loading state, while the already accepted room-card preview MAY remain visible as preview-only evidence. The preview result SHALL NOT suppress the fresh device read and SHALL NOT populate authoritative detailed rows or usage statistics for that explicit load.

Only a fresh explicit result accepted for the same current exact row/generation/currentness MAY populate authoritative detailed call rows and usage statistics for that opening. If the explicit acquisition becomes stale, cancelled, superseded, or otherwise fails currentness before acceptance, it SHALL NOT populate/repopulate authoritative detailed content, publish detailed statistics, mutate replacement presentation, or emit a current-row result for a replacement context.

The explicit detail acquisition SHALL NOT clear, reuse, or reset the completed automatic-attempt marker for the current expansion epoch, and its completion SHALL NOT cause an automatic retry loop. Automatic preview remains exactly-once per eligible expansion epoch under the existing requirement; explicit openings are operator-driven fresh acquisitions and do not create another automatic attempt.

The existing direct child-window close rule remains authoritative for an active explicit window-owned network request: user close invalidates/cancels that exact request, bounded cleanup follows, late callbacks cannot reopen it, and a later explicit opening starts a new fresh acquisition. A completed automatic-preview result from the same current row remains a distinct preview acquisition and SHALL NOT be confused with or substituted for the cancelled explicit child-window request.

#### Scenario: Detail opens with fresh acquisition despite current preview

- **GIVEN** a completed accepted automatic-preview result belongs to the current exact codec row/generation
- **WHEN** the operator clicks `Развернуть`
- **THEN** one fresh serialized exact-row call-log `AUXILIARY_READ` is admitted for the explicit opening
- **AND** the room-card preview MAY remain visible while that request is pending
- **AND** the detailed window MAY show only its loading state before fresh acceptance
- **AND** the automatic-preview result is not promoted to authoritative detailed/statistics state

#### Scenario: Fresh detail result becomes authoritative only after current acceptance

- **GIVEN** one explicit detailed-journal acquisition is active for the current exact row/generation
- **WHEN** application authority accepts its fresh normalized result while that context is still current
- **THEN** that explicit result may populate the detailed window and usage statistics
- **AND** the automatic-preview result remains a separate acquisition result

#### Scenario: Failed automatic preview can be retried only by explicit detail intent

- **GIVEN** the current expansion epoch's automatic preview completed with an ordinary failure/no-data result
- **WHEN** no explicit call-log action occurs
- **THEN** presentation events cause zero further automatic call-log I/O
- **WHEN** the operator explicitly clicks `Развернуть`
- **THEN** one fresh call-log auxiliary acquisition is admitted through the serialized lane
- **AND** the automatic-attempt marker for that expansion epoch remains completed

#### Scenario: Explicit detail becomes stale or cancelled

- **GIVEN** a fresh explicit detailed-journal acquisition exists for row/generation A
- **WHEN** A loses authority or the child request is cancelled before result acceptance
- **THEN** its late result cannot populate authoritative detailed content or statistics
- **AND** it cannot update a replacement row/context
- **AND** the automatic-attempt marker is not reset or retried

#### Scenario: Reopening after explicit cancellation is fresh again

- **GIVEN** an explicit child-window request was cancelled by close or supersession
- **WHEN** the operator later explicitly opens the detailed journal again for an eligible current exact row
- **THEN** a new fresh serialized call-log acquisition is required
- **AND** neither the cancelled request nor any automatic-preview result substitutes for that new explicit load

### Requirement: Codec Local Refresh publishes one typed terminal outcome to presentation

The modern codec `Обновить статус` action SHALL remain only an alias of the existing exact-row `LOCAL_REFRESH` intent and SHALL NOT create a codec-specific refresh controller, second network owner, direct widget-to-handler dispatch, or second credential/retry authority.

For presentation purposes, Local Refresh completion SHALL be classified only after the application lifecycle checks exact row/generation/currentness. Semantics SHALL be equivalent to:

```text
ACCEPTED_SUCCESS
ACCEPTED_TERMINAL_FAILURE
STALE_OR_SUPERSEDED
CANCELLED
```

`ACCEPTED_SUCCESS` SHALL atomically publish the accepted exact-row usable snapshot according to the existing Local Refresh contract and SHALL NOT produce an error modal merely because a lower-level worker emitted an intermediate/final callback.

`ACCEPTED_TERMINAL_FAILURE` SHALL follow the existing terminal Local Refresh row transition (`не удалось подключиться`, blocked row network actions, top full Refresh required). At most one current non-secret user-facing error presentation MAY be emitted for that accepted operation; presentation SHALL NOT independently display the same lower-level failure a second time.

`STALE_OR_SUPERSEDED` and `CANCELLED` SHALL mutate no current row cache/state and SHALL produce no current-row error modal/dialog. A late lower-level callback from such an operation SHALL remain stale and silent for replacement presentation.

Presentation SHALL NOT parse public error strings to reclassify these outcomes. Structured application failure/currentness authority remains decisive.

#### Scenario: Codec Local Refresh succeeds

- **GIVEN** `Обновить статус` starts the existing Local Refresh for the current connected codec row
- **WHEN** current application authority accepts a usable result
- **THEN** that exact row cache is atomically replaced
- **AND** no error modal is shown for the successful operation
- **AND** eligible live may resume only under the existing cleanup/currentness rules

#### Scenario: Codec Local Refresh terminal failure is presented once

- **WHEN** the current exact codec Local Refresh reaches accepted terminal failure
- **THEN** the existing row failure/blocking contract applies
- **AND** at most one non-secret current-operation error presentation is emitted
- **AND** no presentation-owned duplicate failure path exists

#### Scenario: Old codec Local Refresh completes after supersession

- **GIVEN** Local Refresh for row/generation A loses authority before completion
- **WHEN** its result or error arrives after row/generation B is current
- **THEN** A does not update B or the current room cache
- **AND** no error modal for A is shown as a current-row failure

### Requirement: Codec audio controls derive pending and terminal state only from the common mutation lifecycle

For modern room codec speaker-volume `−`/`+` controls, an exact-model supported click SHALL enter only the existing exact-row `MUTATION` -> mandatory `RECONCILIATION` lifecycle. Presentation SHALL NOT own a parallel network operation, pending timer, retry owner, credential fallback, or authoritative pending flag whose lifetime can outlive/disagree with the common room interaction lane.

Before interaction admission, unified exact-model capability authority SHALL resolve support. An unsupported codec audio affordance SHALL use the approved local-only informational path and SHALL perform zero LIVE invalidation, handler/session acquisition, credential selection, mutation generation, or device I/O.

For admitted supported mutation, the common room lifecycle lock state SHALL be the source of button busy/disabled state. A send/ACK alone SHALL NOT make the operation successful or accepted volume current. Only accepted reconciliation may publish final current speaker state/percentage and release normal controls for the same still-current usable row.

If command execution may have been delivered, its outcome is ambiguous, reconciliation fails/times out, or final state cannot be confirmed, the existing blocked/unconfirmed mutation contract SHALL apply. Presentation SHALL NOT clear the state by blind resend, local timeout, optimistic percentage, or direct status request outside the reconciliation owner.

A stale/superseded mutation/reconciliation completion SHALL NOT re-enable controls for a replacement exact row, overwrite replacement percentage, display success for the new row, or start a retry.

#### Scenario: Supported speaker adjustment reconciles successfully

- **GIVEN** the current exact codec registration supports the requested speaker adjustment
- **WHEN** the existing mutation lifecycle sends one operation and reconciliation accepts final exact-row state
- **THEN** the accepted current speaker state/percentage may update
- **AND** common lifecycle authority releases the controls when the same row remains eligible
- **AND** no independent presentation pending timer must be cleared

#### Scenario: Speaker mutation result is ambiguous

- **WHEN** a speaker mutation may have been delivered but final state cannot be authoritatively reconciled
- **THEN** the row follows the existing blocked/unconfirmed mutation contract
- **AND** the GUI does not blindly resend or optimistically accept the requested percentage

#### Scenario: Unsupported speaker action remains local

- **GIVEN** unified exact-model registration marks a speaker operation unsupported
- **WHEN** its common visible affordance is activated while otherwise eligible
- **THEN** the approved local informational result is shown
- **AND** no room network lifecycle starts
