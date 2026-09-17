## MODIFIED Requirements

### Requirement: Extron IN1804 room routing uses the unified serialized mutation and reconciliation lifecycle

The unified exact-model registration SHALL remain the sole authority for enabling Matrix room routing. The existing `Extron IN1804` registration remains supported, and each newly supported exact Matrix registration introduced by this change SHALL declare explicit Matrix room mutation and reconciliation bindings rather than introducing a separate route-model list, widget-type check, model substring test, standalone-screen capability inference, or other parallel authority.

The approved registration shape remains equivalent in meaning to:

```text
mutation binding       -> matrix_room_route
reconciliation binding -> matrix_room_route_reconcile
cleanup/release        -> approved room interaction cleanup authority
```

Existing Matrix room one-shot/local-refresh and Matrix live bindings remain acquisition/live authorities. Adding multi-output models SHALL NOT create a second room interaction lane or replace those bindings.

Application startup/composition SHALL fail closed if an exact supported Matrix registration declares room routing but its mutation, reconciliation, cancellation, or required cleanup/release hook is unavailable or contradictory.

#### Scenario: Exact Extron registration owns route capability
- **GIVEN** current exact model registration for a supported Extron Matrix
- **WHEN** room interaction capabilities are composed
- **THEN** Matrix route mutation/reconciliation availability comes from that one registration
- **AND** no `MATRIX_ROUTE_MODELS`, widget-type inference, standalone `MatrixScreen` signal, model-substring inference, or equivalent parallel capability authority is consulted

#### Scenario: Matrix route binding is declared but unavailable
- **GIVEN** an exact supported Matrix registration declares Matrix room mutation/reconciliation
- **WHEN** composition cannot resolve a required mutation, reconciliation, cancellation, or cleanup hook
- **THEN** startup/composition fails closed
- **AND** the GUI cannot expose a route control that would bypass the missing lifecycle authority

### Requirement: Matrix route intent is exact-row, confirmed, and stale-safe before device acquisition

A Matrix room route may start only from the current expanded exact supported Matrix record after the room automatic cycle is terminal and the row has current usable connected state. The immutable non-secret route intent SHALL contain one accepted current `input_id` and one accepted current logical `output_id`; for existing IN1804 the output remains `1`. Target authority remains the existing immutable `RoomInteractionContext` with exact room generation, `record_id`, model, IP, operation token/currentness, and credential context revision.

The requested input/output IDs SHALL both be authoritative available IDs in the current accepted Matrix topology before handler/session acquisition or route send. The room presentation SHALL NOT supply credentials, handler/session identity, target-search text, initial source IP/record, standalone Matrix screen state, raw SIS command syntax, or another widget's target as mutation authority.

Opening confirmation performs no Matrix I/O, stops no live owner, and changes no room generation. Cancel is a no-op. Only explicit confirmation MAY call the existing `RoomInteractionCoordinator.confirm_mutation()` path.

Before a mutation adapter acquires a handler/session or sends a route command, composition/application currentness checks SHALL still accept the exact mutation context. Active Matrix live SHALL be invalidated and retired through the existing bounded cleanup/release boundary before mutation acquisition. If live cleanup cannot reach the permitted boundary, the route SHALL NOT be sent.

A stale/superseded context or an unavailable input/output ID SHALL be rejected before handler/session acquisition and route send. Late presentation events or callbacks from an old exact row SHALL NOT start or revive Matrix mutation.

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

A structured authentication rejection MAY authorize application advance to the next approved candidate only when rejection is proven before the state-changing route command could have been delivered and only after prior attempt cleanup/release. Existing successful-candidate preference and successful-index persistence rules remain unchanged; an index is remembered only after accepted success evidence at the existing application boundary.

Once the route send has been invoked, may have reached the device, or otherwise has ambiguous delivery/outcome, no automatic credential advance, command replay, read-only retry policy, or user-facing string heuristic may repeat the route. `auth`, `401`, `403`, empty result data, timeout text, or another public error string SHALL NOT independently authorize fallback.

The Matrix mutation adapter SHALL preserve the existing typed failure separation between structured pre-delivery authentication rejection and ambiguous/unknown command outcome for both single-output and multi-output profiles.

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

The Matrix state-changing route operation SHALL execute outside the Qt GUI thread. It SHALL use the exact current `RoomInteractionContext`, authoritative requested logical output O, accepted current input N, and one application-selected credential attempt. The active approved Matrix profile SHALL generate the exact route command; presentation/lifecycle code SHALL NOT construct SIS syntax. The route command SHALL be treated as non-replay-safe.

For one confirmed mutation generation, route send SHALL be attempted at most once per credential attempt, and no attempt after possible delivery may repeat it. If a pre-delivery structured authentication rejection safely authorizes a different candidate, the previous attempt must be proven not to have delivered the route and must reach cleanup/release before the next candidate may acquire device resources.

Mutation transport success or device ACK SHALL NOT be accepted as authoritative route state. It SHALL NOT directly replace row cache, modify accepted `routes[O]`, set legacy `current_connection`, or render the requested input as authoritative active. Mutation success hands only non-secret requested-route evidence to mandatory Matrix reconciliation.

Any Matrix route transport/session owner SHALL release or reach its approved bounded cleanup boundary before reconciliation may acquire conflicting Matrix device resources. If implementation cannot prove that boundary, it SHALL not overlap mutation and reconciliation and must return for architecture review rather than weaken serialization.

#### Scenario: Route ACK is received
- **WHEN** an exact Matrix route send returns ACK/apparent success
- **THEN** the mutation remains non-authoritative for final route state
- **AND** accepted row cache/route state are unchanged
- **AND** mandatory Matrix reconciliation begins only through the serialized lifecycle

#### Scenario: Route outcome is ambiguous
- **WHEN** route delivery or result is ambiguous after a possible send
- **THEN** no replay occurs
- **AND** the exact row becomes blocked/unconfirmed according to the existing state-changing room contract
- **AND** prior accepted cache may remain only as stale/unconfirmed presentation
- **AND** top full Refresh is required for recovery

### Requirement: Matrix reconciliation confirms the requested input before accepting new route state

Every successful Matrix room route mutation SHALL enter the existing `RECONCILIATION` phase. The reconciliation binding SHALL preserve requested output/input identity as non-secret operation evidence and SHALL perform current exact-row read-only Matrix acquisition using the current reconciliation context rather than standalone/global Matrix target state.

A successful readback is authoritative for the mutation only when accepted current evidence establishes:

```text
routes[requested_output_id] == requested_input_id
```

For existing IN1804, output is `1` and fail-closed accepted `current_connection == requested_input_id` remains the compatibility evidence that projects to `routes[1]`. For multi-output Matrix profiles, another output's route or a scalar fallback SHALL NOT confirm the requested output.

If readback succeeds but reports a different input, an explicitly untied output, no current route, malformed/unknown route evidence, unavailable output, or otherwise fails to confirm the requested input, reconciliation SHALL fail unconfirmed. Prior accepted cache may remain visible only as stale/unconfirmed context; the row SHALL remain blocked from live, Local Refresh, auxiliary network actions, further mutation, and other row network I/O until top full Refresh establishes a new room generation, according to the existing generic mutation contract.

If readback confirms the requested input on the requested output, the full accepted reconciliation snapshot MAY atomically replace the exact row's cache. Only then MAY normal usable interaction state and eligible Matrix live resume after cleanup/currentness checks.

A stale reconciliation callback from a superseded room/record/operation context SHALL be ignored and SHALL NOT update visible route state, row cache, credential memory, or lifecycle authority.

#### Scenario: Readback confirms requested route
- **GIVEN** authoritative output O/input N was delivered successfully and entered reconciliation
- **WHEN** current exact-row readback returns an accepted Matrix snapshot with `routes[O] == N`
- **THEN** that full snapshot atomically becomes accepted row state
- **AND** input N may render as authoritative active for output O
- **AND** normal eligible room interaction/live may resume only after lifecycle cleanup/currentness checks

#### Scenario: Readback returns another input
- **GIVEN** output O/input N was requested
- **WHEN** reconciliation returns accepted Matrix evidence with `routes[O] != N`
- **THEN** the command is not considered confirmed
- **AND** the row remains blocked/unconfirmed with prior cache only as stale context
- **AND** no further row network operation is allowed before top full Refresh

#### Scenario: Reconciliation route evidence is unknown
- **GIVEN** a route mutation entered reconciliation
- **WHEN** readback cannot establish the requested output's current route
- **THEN** reconciliation fails unconfirmed
- **AND** the GUI does not optimistically mark the requested input active
- **AND** top full Refresh is required for recovery

#### Scenario: Late reconciliation callback is stale
- **GIVEN** Matrix reconciliation context A has been superseded by a new room generation or exact-row context
- **WHEN** A later returns a matching route snapshot
- **THEN** the stale callback is ignored
- **AND** it cannot update current route presentation, accepted cache, credential memory, or interaction state

### Requirement: Matrix room routing preserves existing PDU, Matrix live, and standalone lifecycle boundaries

This change SHALL generalize Matrix route mutation as a model-specific binding within the existing room interaction architecture rather than renaming PDU-specific code into an unsafe shared handler path. Composition MAY generalize dispatch/cleanup plumbing where appropriate, but model-specific Matrix profile/handler mutation owners SHALL remain explicit and cancellation SHALL target the actual current owner.

Existing PDU mutation/reconciliation behavior SHALL remain unchanged. Existing Matrix room automatic one-shot/local Refresh and Matrix room live behavior SHALL remain unchanged except that confirmed Matrix mutation uses the already-approved live-retirement lock before send and may resume eligible live only after confirmed reconciliation.

Standalone `MatrixScreen` and standalone `MatrixController` routing SHALL remain a separate supported surface. Room routing SHALL NOT depend on standalone widget selection/global target state, and standalone routing SHALL NOT depend on room expanded-row state.

#### Scenario: PDU mutation remains independent
- **GIVEN** Matrix room routing support is present
- **WHEN** an existing PDU room mutation is performed
- **THEN** its existing PDU mutation/reconciliation binding and cancellation behavior remain unchanged
- **AND** no Matrix route owner is acquired

#### Scenario: Matrix room live resumes only after confirmed reconciliation
- **GIVEN** Matrix live was retired for a confirmed route
- **WHEN** Matrix reconciliation succeeds and cleanup/currentness checks complete
- **THEN** eligible live MAY resume through the existing Matrix room live binding
- **AND** no second Matrix live lane is created

#### Scenario: Standalone route remains separate
- **GIVEN** the standalone Matrix screen/controller supports routing under its existing application boundary
- **WHEN** room routing supports additional approved Matrix profiles
- **THEN** standalone routing keeps its own existing application controller boundary
- **AND** room routing does not use standalone widget target state as exact-row authority
