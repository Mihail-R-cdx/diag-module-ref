## MODIFIED Requirements

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

#### Scenario: Initial IP target differs from expanded row

- **GIVEN** room mode was entered through an IP target that resolved source record A
- **AND** supported record B is currently expanded
- **WHEN** a room interaction is requested
- **THEN** the target is B's exact canonical record/model/IP context
- **AND** neither the raw target-search text nor A's resolved source IP is used as B's device target

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
