## ADDED Requirements

### Requirement: Source IP establishes authoritative room diagnostic context

For a syntactically valid normalized IPv4 address, the application SHALL resolve the current validated immutable equipment inventory before room-mode model-specific credential resolution, handler acquisition, worker/controller submission, or device network I/O.

When inventory is available and valid, source-IP multiplicity SHALL be preserved exactly. Zero matching records SHALL fail closed as not found. More than one matching record SHALL fail closed as ambiguous. Neither outcome SHALL open manual model fallback or select a record by diagnostic model, device kind, room metadata, page type, or position.

Exactly one source record with non-null canonical `room_id` SHALL establish a room diagnostic session even when that source record has null or unsupported `diagnostic_model`. Exactly one source record with null `room_id` MAY continue through the existing legacy single-device path only when its exact canonical `diagnostic_model` is registered as supported. A unique no-room record with null or unsupported model SHALL fail closed.

Manual model fallback SHALL remain available only when the canonical inventory is unavailable, unloadable, or corrupt under the existing structured inventory-load contract. Valid inventory data SHALL NOT be bypassed by model guessing.

#### Scenario: Unsupported source still establishes its room

- **GIVEN** valid inventory contains exactly one record for the entered IP
- **AND** that record has a non-null authoritative `room_id`
- **AND** its canonical `diagnostic_model` is null or unsupported
- **WHEN** diagnostic start is requested
- **THEN** the application establishes room mode from that record and `room_id`
- **AND** the source row is represented as unsupported rather than blocking discovery of other room equipment
- **AND** no manual model fallback is opened

#### Scenario: Source IP is absent from valid inventory

- **GIVEN** valid inventory is loaded
- **WHEN** zero records match the entered normalized IP
- **THEN** diagnostic start fails closed with a safe not-found outcome
- **AND** no fallback dialog, credential resolution, handler acquisition, or device network I/O starts

#### Scenario: Source IP is globally ambiguous

- **GIVEN** valid inventory is loaded
- **WHEN** more than one record matches the entered normalized IP
- **THEN** diagnostic start fails closed as ambiguous
- **AND** no record is selected by model, room, kind, or position
- **AND** no manual fallback or device network I/O starts

#### Scenario: Supported source has no room ID

- **GIVEN** exactly one valid-inventory record matches the source IP
- **AND** `room_id` is null
- **AND** its exact canonical `diagnostic_model` is registered as supported
- **WHEN** diagnostic start is requested
- **THEN** the existing legacy single-device diagnostic path remains available
- **AND** no synthetic room identity is created

### Requirement: Room tree preserves complete deterministic membership

A room diagnostic session SHALL include every canonical inventory record whose authoritative `room_id` equals the source record's resolved room ID. Tree construction SHALL NOT filter records by `diagnostic_model`, `device_kind`, IP availability, screen type, or diagnostic eligibility.

The source record SHALL appear first exactly once. Every remaining room record SHALL appear in ascending canonical `record_id` order.

Same-room IP ambiguity SHALL be computed across all room records with non-null IP, including unsupported records. A supported record whose IP is shared by any other record in the same room SHALL be diagnostically ambiguous and SHALL receive no device I/O. After room authority is established, an equal IP on a record in another room SHALL NOT by itself make a room row ambiguous.

#### Scenario: Room contains supported and unsupported equipment

- **GIVEN** one authoritative room contains supported, unsupported, missing-IP, and ordinary records
- **WHEN** the tree is built
- **THEN** every room record is present exactly once
- **AND** supportability changes diagnostic eligibility but not tree membership

#### Scenario: Source row is ordered first

- **GIVEN** the source record is not first by canonical `record_id`
- **WHEN** the room tree is built
- **THEN** the source row is first
- **AND** all other rows follow in canonical `record_id` order

#### Scenario: Unsupported record makes a supported IP ambiguous

- **GIVEN** a supported room record and an unsupported room record share the same non-null IP
- **WHEN** row eligibility is calculated
- **THEN** the supported row is classified as same-room ambiguous
- **AND** it is not diagnosed
- **AND** the unsupported row remains classified as unsupported

### Requirement: Shared room metadata is source-first display evidence

Room mode SHALL present shared room display metadata once above the equipment tree. The shared presentation SHALL include room name, room address, and VIP state and SHALL NOT display `room_id` to the operator.

For each display field independently, the application SHALL use the source-record value when it is nonblank/non-null. Otherwise it SHALL select the first nonblank/non-null value from room records in canonical `record_id` order. If no usable value exists, it SHALL present a safe no-data value.

The room diagnostic session SHALL NOT compare same-room `room_name`, `room_address`, or `room_vip` values to select a majority, emit a conflict outcome, or replace authoritative `room_id` identity. Boolean `false` SHALL be treated as a meaningful non-null VIP value.

#### Scenario: Source record carries the room address

- **GIVEN** the source record has nonblank `room_address`
- **AND** another room record has a different nonblank address
- **WHEN** the shared header is rendered
- **THEN** the source-record address is displayed
- **AND** no address conflict is raised

#### Scenario: Source metadata is missing

- **GIVEN** the source record has null room name, address, and VIP
- **WHEN** canonical room records contain later usable values
- **THEN** each field independently uses the first usable canonical value
- **AND** `room_id` remains the only room identity authority

### Requirement: Per-record diagnostic state is authoritative over reusable views

The application SHALL maintain independent diagnostic state for every room record. Canonical `record_id` SHALL remain equipment identity, and each asynchronous row operation SHALL additionally capture the row's exact canonical `diagnostic_model` and `ip_address` context plus room/operation generation so callbacks cannot be applied to a different runtime target.

Per-record state SHALL contain enough non-secret information to preserve row status, accepted authoritative diagnostic snapshot, partial/unconfirmed data, warnings, safe typed failure reason, and presentation/capability binding.

Reusable device screens/widgets SHALL be presentation projections only. They SHALL NOT be the authoritative store for hidden row diagnostic data, request freshness, credential memory, or session ownership. Rebinding/rebuilding a view for another row SHALL render only that exact row's accepted state.

#### Scenario: Two records use the same device screen class

- **GIVEN** two room records have the same exact supported model
- **AND** both are diagnosed with different results
- **WHEN** the operator alternates which row is expanded
- **THEN** each row renders its own state
- **AND** no value, warning, failure, or operation context is inherited from the other record

#### Scenario: Hidden row has no presentation-owned lifecycle

- **WHEN** a previously expanded row becomes hidden
- **THEN** its authoritative cache remains in per-record application state
- **AND** a hidden widget does not retain diagnostic timers, handlers, workers, or sessions merely to preserve that cache

### Requirement: One exact application model registry owns room support and adapter binding

The application SHALL use one application-level exact `diagnostic_model` registry as the support/dispatch authority for both existing device routing and room diagnostics. The room workflow SHALL extend the existing exact dispatch registration rather than maintaining a second independent supported-model list.

Each model supported for room diagnostics SHALL have a valid presentation binding and one-shot adapter binding in that authority. Application startup/composition SHALL fail fast for duplicate exact model registrations or missing room-required bindings rather than discovering inconsistent support only after user interaction.

Runtime code SHALL NOT reproduce importer recognition rules or infer diagnostic support from `source_model`, manufacturer text, `device_kind`, substrings, tokenization, fuzzy matching, or registry order.

#### Scenario: Room model registration is complete

- **WHEN** a canonical room record has an exact supported `diagnostic_model`
- **THEN** one registry entry supplies its existing presentation/lifecycle route and room one-shot adapter binding
- **AND** no secondary room-only model table is consulted

#### Scenario: Canonical model is absent from registry

- **WHEN** a room record has null or unregistered `diagnostic_model`
- **THEN** the row is unsupported
- **AND** runtime does not guess support from `source_model` or other free-form inventory evidence

### Requirement: Room diagnostics use a unified one-shot adapter contract

The room orchestrator SHALL interact with supported models through a model-neutral read-only one-shot adapter boundary. An adapter SHALL receive immutable exact row/attempt context and at most one application-assigned credential candidate for one attempt. It SHALL NOT select, iterate, or persist credential candidates.

The adapter boundary SHALL distinguish intermediate partial data, final usable success, final usable success with warning, terminal failure, and lifecycle cleanup completion. A model-specific controller/worker/handler MAY implement those semantics internally, but protocol commands, transport negotiation, session artifacts, polling mechanics, and parser details SHALL remain outside the generic room orchestrator.

A one-shot adapter SHALL retire model-specific persistent diagnostic activity before its cleanup-complete boundary. Continuous polling, keepalive, live timers, or reusable network sessions SHALL NOT remain active merely because automatic room acquisition succeeded.

#### Scenario: DMP first complete snapshot is enough for room acquisition

- **WHEN** the DMP adapter receives the first complete authoritative meter/device snapshot
- **THEN** it may publish usable final room data
- **AND** it stops further polling and closes/retire owned polling resources before cleanup completion

#### Scenario: Matrix room acquisition succeeds

- **WHEN** Matrix room acquisition obtains the required authoritative routing/device snapshot
- **THEN** it publishes usable final room data
- **AND** its automatic one-shot path stops keepalive and releases persistent session resources before cleanup completion

#### Scenario: Adapter cannot advance credentials

- **WHEN** an assigned attempt encounters any failure
- **THEN** the adapter returns the structured outcome to application composition
- **AND** it does not inspect or try another credential candidate

### Requirement: Automatic room cycle is strictly sequential

The application SHALL execute room diagnostic network work for at most one record at a time. Eligible rows SHALL be processed in tree queue order. For each eligible row the normal sequence SHALL be equivalent to:

```text
verify current room/row generation
-> resolve and validate application-owned credential attempt plan
-> if required authenticated credentials are absent for a non-PCS4i model:
       terminal configuration failure with zero network I/O
       continue to the next eligible row
-> preliminary reachability check
-> one assigned diagnostic attempt
-> optional next assigned attempt only after structured AuthenticationError
-> accept final row outcome
-> cleanup/release or bounded abandonment
-> next eligible row
```

Credential-plan resolution/validation SHALL occur before preliminary reachability because absence of required authenticated credentials is a pre-I/O configuration failure. For an authenticated non-PCS4i model with no valid required credentials, the row SHALL perform no ping, handler acquisition, worker/controller submission, or other device network I/O; it SHALL expose the safe reason `Credentials не настроены` and the room queue SHALL continue.

The approved PCS4i exception SHALL remain application-owned: when no explicit/profile/mapped credential exists, composition MAY create the approved credentialless attempt plan. Only after that plan has been successfully formed does PCS4i proceed to preliminary reachability.

After a valid attempt plan exists, preliminary reachability failure SHALL stop that row before model-specific handler/worker acquisition. Accordion selection SHALL NOT change queue order or cause a waiting row to start early.

#### Scenario: Missing required credentials stops before ping

- **GIVEN** a supported authenticated non-PCS4i room row requires credentials
- **AND** no valid credential candidate is configured for that model
- **WHEN** the row reaches its queue turn
- **THEN** credential-plan validation ends the row as a safe terminal configuration failure
- **AND** the row displays `Credentials не настроены`
- **AND** no ping, handler acquisition, worker/controller submission, or other device network I/O occurs for that row
- **AND** the room queue continues to later eligible rows

#### Scenario: PCS4i credentialless plan precedes ping

- **GIVEN** a supported PCS4i room row has no explicit credential, explicit profile, or mapped credential chain
- **WHEN** the row reaches its queue turn
- **THEN** application composition forms the approved credentialless attempt plan
- **AND** only after that plan exists may preliminary reachability run

#### Scenario: Second device waits for first cleanup

- **GIVEN** two supported eligible room rows are queued
- **WHEN** the first row has produced final diagnostic data but its one-shot lifecycle has not yet completed cleanup
- **THEN** the second row performs no diagnostic network I/O
- **AND** it starts only after cleanup completion or the bounded abandonment boundary

#### Scenario: Ping fails

- **GIVEN** a valid credential attempt plan exists for the eligible row
- **WHEN** that row fails preliminary reachability validation
- **THEN** no model-specific diagnostic handler/worker starts for that row
- **AND** the row receives a safe terminal failure
- **AND** the room queue proceeds to later rows

#### Scenario: Accordion switches while a row is waiting

- **WHEN** the operator expands another waiting row during the automatic cycle
- **THEN** the expanded presentation changes
- **AND** queue ordering and device network I/O remain unchanged

### Requirement: Room credential fallback remains application-owned and structured

Room diagnostic attempts SHALL reuse the existing ordered credential-candidate contract. The application SHALL begin at a valid retained successful candidate index for the exact canonical model/IP pair when available, otherwise candidate zero, and SHALL consider only the remaining suffix without wrap-around.

Only a machine-readable confirmed new-login `AuthenticationError` SHALL authorize advancing to a later candidate. Timeout, transport, TLS, protocol, parse, malformed/empty payload, arbitrary error text, localized authentication words, and numeric strings such as `401` or `403` SHALL NOT authorize credential advancement by themselves.

A newly attempted candidate SHALL be persisted as successful only after a final accepted usable operation whose model-specific acquisition/authentication contract is complete. Partial data, terminal failure, stale completion, or cleanup-degraded retirement SHALL NOT save a new successful candidate/profile.

The existing PCS4i credentialless composition exception SHALL remain: when no explicit/profile/mapped credential exists, application composition MAY submit the approved credentialless attempt rather than treating absence alone as a configuration error.

#### Scenario: Saved successful candidate is tried first

- **GIVEN** exact model/IP successful credential memory points to a still-valid candidate
- **WHEN** room acquisition begins for that record
- **THEN** the attempt plan starts at that candidate
- **AND** failure does not wrap to earlier candidates

#### Scenario: Structured authentication failure advances the chain

- **WHEN** the current assigned attempt fails with confirmed new-login `AuthenticationError`
- **AND** a later candidate remains
- **THEN** application composition may start exactly the next candidate
- **AND** the failed adapter/worker/handler does not choose it

#### Scenario: Transport error text looks like authentication

- **WHEN** an attempt has a transport/protocol failure whose public or private text contains `auth`, `401`, or `403`
- **AND** no typed new-login `AuthenticationError` exists
- **THEN** no later credential candidate is started

### Requirement: Room row eligibility and status are fail-closed

Before network I/O, each room row SHALL receive status using this priority:

```text
null or unregistered diagnostic_model -> не поддерживается
registered model with null IP         -> IP не указан
registered model with same-room duplicate IP -> неоднозначный IP
otherwise                             -> ожидание опроса
```

Unsupported status SHALL take precedence over missing/ambiguous IP status. When both `diagnostic_model` and `source_model` are null/unusable for display, the row SHALL use `Модель не определена` rather than guessing another name.

Unsupported, missing-IP, and same-room ambiguous rows SHALL receive zero device network I/O and expose no active network/state-changing controls. Eligible rows SHALL use `подключение...` while their one-shot acquisition is active, `подключено` after accepted usable success, and `не удалось подключиться` after ordinary terminal failure.

#### Scenario: Unsupported row also has no IP

- **WHEN** a room record has unsupported/null `diagnostic_model` and null IP
- **THEN** its status is `не поддерживается`
- **AND** no network I/O is attempted

#### Scenario: Supported row has no IP

- **WHEN** a registered model has null canonical IP
- **THEN** its status is `IP не указан`
- **AND** no reachability or device I/O starts

#### Scenario: Supported row has same-room duplicate IP

- **WHEN** a registered model's canonical IP is shared by another record in the same room
- **THEN** its status is `неоднозначный IP`
- **AND** no record is chosen as the network target by model, kind, or position

### Requirement: Partial, warning, and failed results retain distinct authority

Intermediate partial diagnostic data SHALL remain non-final. It MAY be shown in the currently expanded row while the row remains `подключение...`, but it SHALL NOT advance the room queue, become the authoritative successful cache, enable post-cycle actions, or persist a successful credential candidate.

When an existing model-specific contract defines a final result as usable despite optional enrichment failure, the room adapter SHALL preserve that semantics. Usable final data SHALL become authoritative row cache, row status SHALL be `подключено`, and a safe inline warning SHALL be retained. Such a warning SHALL make the full room cycle a completed-with-problems result without converting the row into an ordinary connection failure.

If terminal failure occurs after partial data, the partial values MAY remain visible only as incomplete/unconfirmed evidence. They SHALL NOT be promoted to accepted cache or successful credential/profile memory.

#### Scenario: Optional enrichment fails after authoritative status

- **GIVEN** a model-specific approved contract treats the primary diagnostic result as usable
- **WHEN** an optional enrichment stage fails
- **THEN** the row retains accepted usable data and `подключено` status
- **AND** a safe warning is displayed
- **AND** the room cycle is classified as completed with problems

#### Scenario: Partial data is followed by terminal failure

- **WHEN** intermediate data was emitted and the attempt later fails terminally
- **THEN** the row ends in failure
- **AND** any retained partial values are explicitly incomplete/unconfirmed
- **AND** no successful cache or credential persistence is created from them

### Requirement: One-shot cleanup is bounded and stale callbacks are powerless

Every automatic one-shot lifecycle SHALL have a bounded cleanup/release policy. The exact duration MAY be implementation-configurable/test-injectable and is not a fixed user-facing value in this capability.

The next eligible row SHALL not start until the previous row's cleanup completes or the cleanup deadline establishes logical abandonment. On abandonment, the old lifecycle SHALL immediately lose application authority. Late result, error, completion, cleanup, progress, or status callbacks SHALL NOT update room/row presentation, accepted cache, credential/profile memory, control state, or queue scheduling.

If abandonment occurs before usable final data, the row SHALL remain terminal failed. If usable final data was already accepted but resource retirement cannot be confirmed, the application MAY retain that snapshot visibly as stale but SHALL present the row as degraded/`соединение потеряно` and SHALL classify the room cycle as completed with problems.

Physical best-effort resource cleanup MAY continue on its owning background execution lane, but the Qt GUI thread SHALL NOT synchronously wait for network timeout/cleanup.

#### Scenario: Cleanup hangs after usable data

- **WHEN** a row has accepted usable data but its one-shot resource cleanup exceeds the policy deadline
- **THEN** the old lifecycle is abandoned
- **AND** the room queue proceeds
- **AND** the snapshot remains only as stale presentation
- **AND** the row is degraded rather than reported as cleanly connected

#### Scenario: Late callback arrives after abandonment

- **WHEN** an abandoned row lifecycle later emits result or completion
- **THEN** the callback is ignored
- **AND** it cannot change any current room state or start another device operation

### Requirement: Automatic room-cycle GUI remains responsive and non-modal

Automatic room diagnostic network work SHALL execute outside the Qt GUI thread. During an active room cycle, the top IP, Password, and full Refresh controls SHALL be unavailable and row-level network/state-changing controls SHALL remain unavailable. Accordion switching SHALL remain responsive and presentation-only.

The GUI SHALL NOT open per-device automatic progress, error, or terminal modal dialogs during the room cycle. Row status/detail and one global room status SHALL present automatic outcomes inline.

At most one row SHALL be expanded at a time. Expanding an eligible waiting row MAY show its model-specific layout with waiting placeholders but SHALL NOT start its I/O early. The cycle SHALL NOT auto-expand rows merely because they succeed or fail. When the source row is not expandable, the application SHALL not automatically select another device as a substitute.

No dedicated room-cycle Cancel button is required. Application close during read-only automatic room work SHALL invalidate/cancel current room authority best-effort and SHALL not block the GUI waiting for remote network cleanup.

#### Scenario: Waiting row is expanded

- **WHEN** the operator expands an eligible row whose queue turn has not started
- **THEN** its view shows waiting/placeholder state
- **AND** no handler acquisition or device network I/O starts because of expansion

#### Scenario: Device fails automatically

- **WHEN** one room row fails during the automatic cycle
- **THEN** its safe failure is rendered inline
- **AND** no per-device error modal is required
- **AND** later eligible room rows continue to be processed

### Requirement: Full room Refresh owns global room summary and timestamp

Room mode top-level Refresh SHALL represent a full room diagnostic cycle. A full Refresh SHALL create a new room generation, re-resolve the current source IP, rebuild shared room metadata and every row state from canonical inventory, and execute the complete sequential room cycle. It SHALL NOT be a local per-row refresh.

While the cycle is active, the shared status SHALL indicate room equipment polling. A terminal cycle with no unsupported, missing-IP, ambiguous-IP, failed, degraded, or usable-warning rows SHALL display `Опрос завершён`. A terminal cycle containing any such problem SHALL display `Опрос завершён с проблемами`.

A room containing no eligible network rows SHALL still reach terminal completion, perform zero device I/O, and be classified as completed with problems.

`Последнее обновление` SHALL represent completion time of the most recent full room cycle, even when no device I/O was eligible. It SHALL NOT be changed merely by rendering cached row data.

#### Scenario: Full room cycle is clean

- **WHEN** every room row is eligible and completes with clean usable success
- **THEN** global status becomes `Опрос завершён`
- **AND** `Последнее обновление` records full-cycle completion time

#### Scenario: Room contains an unsupported record

- **WHEN** supported eligible rows complete successfully but another room record is unsupported
- **THEN** the room cycle still completes
- **AND** global status is `Опрос завершён с проблемами`

#### Scenario: Room has no eligible network rows

- **WHEN** every room row is unsupported, missing-IP, or ambiguous-IP
- **THEN** no device network I/O occurs
- **AND** the full cycle terminates as completed with problems
- **AND** `Последнее обновление` is updated

### Requirement: Room one-shot PDU diagnostics do not trigger legacy related-codec enrichment

The automatic room diagnostic path SHALL treat every room record, including PDU and codec records, as independently scheduled rows. An automatic PDU one-shot acquisition SHALL NOT publish or emulate the legacy accepted-current **user PDU refresh** boundary that starts `pdu-room-codec-enrichment`.

In room mode, room name/address/VIP authority SHALL be the shared room header and codec diagnostic authority SHALL belong to the codec row's own room queue operation. Existing legacy PDU enrichment MAY remain available for the legacy single-device PDU lifecycle until a later approved change removes or reconciles it.

#### Scenario: Room queue diagnoses a PDU before a codec

- **GIVEN** one room contains a supported PDU and a supported codec
- **WHEN** automatic room polling completes the PDU row
- **THEN** no PDU-related codec enrichment operation is started from that result
- **AND** the codec is diagnosed only when its own room-queue turn begins

#### Scenario: Legacy single-device PDU mode remains separate

- **WHEN** the application is operating through an existing legacy single-device PDU lifecycle outside room mode
- **THEN** this capability does not itself remove the existing enrichment trigger
- **AND** full removal/reconciliation remains deferred to the later interaction change

### Requirement: Post-cycle interactive network lifecycle is deferred

At full room-cycle completion, this capability SHALL leave a stable room session/tree and terminal per-record state without starting a new persistent live lifecycle. Post-cycle live handoff, local per-device Refresh, auxiliary network reads such as Call Log, state-changing commands, mandatory mutation readback/reconciliation, and post-cycle connection-loss recovery SHALL NOT be introduced as part of this capability.

Those later operations SHALL consume the exact room session, per-record state/cache, and single model capability registry established here rather than restoring widget-selected target authority.

#### Scenario: Automatic room cycle completes

- **WHEN** the final room row has reached terminal outcome and cleanup/abandonment
- **THEN** the room session and per-record states remain available for presentation
- **AND** MIH-7 starts no new post-cycle live, auxiliary, or mutation network operation

#### Scenario: Later interaction capability is added

- **WHEN** `room-device-interaction-lifecycle` is implemented
- **THEN** it binds interaction to the exact current room record/state established by this capability
- **AND** it does not redefine room identity or create a competing per-widget source of truth

### Requirement: MIH-7 room mode remains presentation-only after terminal completion

For the lifetime of a room-mode session implemented by this capability, terminal automatic success SHALL authorize presentation only. Existing model-specific network-backed controls SHALL remain disabled or unbound after both clean and problem room-cycle completion until the separately approved `room-device-interaction-lifecycle` establishes exact-row interaction authority.

A `подключено` row SHALL NOT by itself authorize local Refresh, live/polling, Matrix routing, PDU or codec mutations, Call Log/auxiliary network reads, or any equivalent reused-screen network action. Attempts to invoke those paths SHALL be rejected before handler acquisition and device network I/O. Failed or degraded rows SHALL have the same interaction lock and may expose only their safe cached/partial/error presentation.

#### Scenario: Successful row remains presentation-only

- **GIVEN** a supported row reaches accepted `подключено` state and the full room cycle terminates
- **WHEN** the operator expands that row under MIH-7
- **THEN** accepted cached data may be rendered
- **AND** every row network/state-changing action remains disabled or unbound
- **AND** no reused legacy intent can use the top-level source IP or prior single-device context as target authority

#### Scenario: Problem row remains presentation-only

- **GIVEN** a row ends failed or degraded and the room cycle terminates
- **WHEN** the operator expands that row
- **THEN** safe failed/stale presentation may be rendered
- **AND** no local retry, auxiliary request, live start, mutation, or other device network I/O is available from that row

### Requirement: Room accordion initial state and full-refresh reset are deterministic

Every newly established room session, including one created by top full Refresh, SHALL start from a deterministic accordion state derived only from the new source record. If the source row is supported and expandable under the room-row eligibility contract, that source row SHALL be the one initially expanded row. If the source row is not expandable, no row SHALL be expanded initially; the application SHALL NOT choose a secondary row automatically.

A new full Refresh SHALL NOT carry forward the previously expanded secondary row or any previous accordion selection. Before re-resolution starts, the old room generation, tree/cache presentation, row bindings, and accordion selection SHALL lose authority and SHALL be cleared/reset. If new source re-resolution fails, the previous room tree/cache/presentation SHALL NOT be restored as current authority.

Automatic row success, warning, or failure during the new room cycle SHALL NOT change this user-selection state.

#### Scenario: Expandable source starts expanded

- **GIVEN** a new room session is established and the source row is supported and expandable
- **WHEN** the tree is first presented
- **THEN** the source row is the only initially expanded row
- **AND** no later automatic row outcome changes expansion on the operator's behalf

#### Scenario: Non-expandable source starts fully collapsed

- **GIVEN** a new room session is established and the source row is unsupported, missing-IP, or same-room ambiguous and therefore not expandable
- **WHEN** the tree is first presented
- **THEN** no room row is initially expanded
- **AND** no secondary row is selected automatically

#### Scenario: Full Refresh does not preserve prior secondary selection

- **GIVEN** a secondary row was expanded in the previous room generation
- **WHEN** top full Refresh starts a new room generation
- **THEN** the previous selection and old room presentation lose authority before re-resolution
- **AND** the new tree uses only the new source-row initial-state rule
- **AND** failed re-resolution does not resurrect the previous tree or selection
