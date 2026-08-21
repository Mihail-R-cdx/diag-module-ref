## MODIFIED Requirements

### Requirement: Device selection and refresh input validation

The main window connection panel SHALL use the IP address as its only permanent diagnostic-target input. It SHALL NOT expose a persistent device-model selector, a `deviceCombo` equivalent, or the `Устройство` label. The permanent `Пароль` action MAY remain, but it SHALL resolve its exact model through the application-owned credential-configuration flow defined by this capability and SHALL NOT read a model from Qt selector state, previous request state, previous fallback state, or room-row presentation state.

The application/composition layer SHALL hold accepted exact model/room authority only in a current purpose-bound context produced by current inventory resolution or confirmed unavailable-inventory fallback. A user-initiated Refresh or equivalent Enter action SHALL reject an empty or malformed IPv4 address before inventory resolution. For a valid normalized IPv4 address, the application SHALL resolve current inventory context before model-specific credential resolution, preliminary reachability validation, handler acquisition, worker/controller submission, or device network I/O.

When current inventory is valid, source-IP lookup SHALL preserve zero/one/many multiplicity without model/kind filtering:

- zero records SHALL fail closed as not found;
- more than one record SHALL fail closed as ambiguous;
- exactly one record with non-null authoritative `room_id` SHALL establish room diagnostic mode even if that source record has null or unsupported `diagnostic_model`;
- exactly one record with null `room_id` SHALL use the existing legacy single-device path only when its exact canonical `diagnostic_model` is present in the application dispatch registry;
- exactly one no-room record with null or unsupported `diagnostic_model` SHALL fail closed.

Valid-inventory not-found, ambiguous, unmapped, and unsupported outcomes SHALL NOT open manual model fallback or select a target by source text, `device_kind`, page type, room display data, or previous state. Manual model fallback SHALL be available only when inventory is unavailable, unloadable, or corrupt under the structured inventory load contract. A confirmed fallback remains purpose-bound and SHALL NOT be reused implicitly by a later request.

For room diagnostic mode, global preliminary reachability is not performed against one selected model before the tree exists. Instead the room lifecycle SHALL build the room context/tree first and perform the approved per-record reachability gate immediately before each eligible row's model-specific diagnostic acquisition. A per-record reachability failure SHALL stop that row before its assigned device worker/controller network operation while allowing the room queue to continue.

For the legacy single-device path, the existing preliminary reachability gate remains: after final exact model assignment, reachability failure SHALL stop before starting the assigned device worker/controller network operation.

The `Пароль` action SHALL be network-free diagnostic configuration. With valid inventory, exactly one IP record with an exact supported canonical `diagnostic_model` MAY open the model's existing credential configuration even when the record belongs to a room; it SHALL NOT start room polling. Valid-inventory zero-record, many-record, null-model, or unsupported-model outcomes SHALL report a safe error and SHALL NOT open manual model fallback. Only unavailable/unloadable/corrupt inventory MAY use the existing explicit credential-configuration fallback selection.

#### Scenario: Main panel has no persistent model selector

- **WHEN** the main diagnostic window is constructed
- **THEN** the permanent connection panel exposes the IP input and model-independent actions
- **AND** it does not expose `deviceCombo`, another persistent model selector, or the `Устройство` label
- **AND** no default, previous Qt selection, or expanded room row acts as model authority

#### Scenario: Password action has no widget model authority

- **WHEN** the main window exposes the permanent `Пароль` action
- **THEN** that action does not read a model from `deviceCombo`, current screen, room-row label, window title, prior diagnostic request, prior fallback, or another Qt presentation value
- **AND** it begins the purpose-bound credential-configuration resolution flow

#### Scenario: Valid supported device refresh enters room mode

- **GIVEN** a valid current inventory contains exactly one record for the normalized IP
- **AND** that record has a non-null authoritative `room_id`
- **WHEN** the operator starts Refresh or equivalent Enter action
- **THEN** the record and `room_id` become the authoritative source for a new room diagnostic session
- **AND** the room tree/lifecycle is composed before per-row credentials, reachability checks, handlers, or workers start
- **AND** ordinary manual model fallback is not offered

#### Scenario: Unsupported source record still enters room mode

- **GIVEN** a valid current inventory contains exactly one record for the normalized IP
- **AND** that record has a non-null authoritative `room_id`
- **AND** its canonical `diagnostic_model` is null or not registered
- **WHEN** the operator starts Refresh
- **THEN** room mode is still established from the authoritative room ID
- **AND** the source row is represented as unsupported in the room tree
- **AND** other supported eligible room records may still be diagnosed
- **AND** no fallback model is requested for the source row

#### Scenario: Valid supported record has no room ID

- **GIVEN** a valid current inventory contains exactly one record for the normalized IP
- **AND** `room_id` is null
- **AND** the record has an exact `diagnostic_model` present in the application dispatch registry
- **WHEN** the operator starts Refresh
- **THEN** the matching registered screen and existing legacy model-specific lifecycle are assigned
- **AND** model-specific credentials and the existing single-device reachability check use only that assigned model
- **AND** no synthetic room is created and no ordinary manual override is offered

#### Scenario: Valid inventory source IP is not found

- **GIVEN** current inventory is valid
- **WHEN** the normalized IP has zero records
- **THEN** the application reports a controlled not-found outcome
- **AND** it selects no automatic model, room, page, credential chain, handler, worker, or controller
- **AND** it does not open manual model fallback or perform device network I/O

#### Scenario: Valid inventory source IP is ambiguous

- **GIVEN** current inventory is valid
- **WHEN** the normalized IP has more than one record
- **THEN** the application reports a controlled ambiguous outcome
- **AND** it does not filter by model, device kind, room, page type, or record order to choose a target
- **AND** it opens no manual model fallback and performs no device network I/O

#### Scenario: Valid no-room record cannot assign a supported model

- **GIVEN** current inventory is valid
- **AND** exactly one record matches the normalized IP
- **AND** that record has `room_id = null`
- **AND** its canonical `diagnostic_model` is null or unsupported
- **WHEN** diagnostic start is requested
- **THEN** the application selects no page, credential chain, handler, worker, or controller
- **AND** it reports a safe unsupported/unmapped outcome
- **AND** it does not open manual model fallback

#### Scenario: Inventory is unavailable for diagnostic start

- **WHEN** canonical inventory is unavailable, unloadable, or corrupt for a valid normalized IP
- **THEN** the application automatically opens the existing fail-closed diagnostic-purpose model fallback or focused equivalent
- **AND** only a new explicit model selection and `Подключиться` confirmation bound to that diagnostic-start purpose may create the manual-fallback request context

#### Scenario: Password resolves a supported inventory model without diagnostics

- **GIVEN** current inventory is valid
- **AND** exactly one record matches the normalized IP
- **AND** its exact canonical `diagnostic_model` is registered
- **WHEN** the operator selects `Пароль`
- **THEN** credential configuration opens for that model-wide credential chain
- **AND** no ping, room cycle, handler acquisition, worker submission, or device network I/O starts

#### Scenario: Password cannot resolve a valid-inventory target

- **GIVEN** current inventory is valid
- **WHEN** IP lookup returns zero/many records or the unique record has null/unsupported `diagnostic_model`
- **THEN** the application reports a controlled safe configuration-resolution error
- **AND** it does not open manual model fallback
- **AND** it performs no device network I/O

#### Scenario: Invalid refresh input

- **WHEN** the IP field is empty or malformed
- **THEN** the application displays a controlled warning
- **AND** it does not query inventory, open fallback, build a room session, resolve model-specific credentials, perform reachability validation, acquire a handler, submit a worker/controller operation, or perform device network I/O

#### Scenario: Legacy preliminary reachability validation fails

- **GIVEN** a final exact legacy single-device automatic or confirmed-fallback diagnostic model has been assigned for a valid IP
- **WHEN** preliminary reachability validation fails
- **THEN** the application displays the existing controlled warning
- **AND** it does not start the assigned device diagnostic worker/controller network operation

#### Scenario: Room-row preliminary reachability validation fails

- **GIVEN** room mode is active and a supported eligible row reaches its queue turn
- **WHEN** that exact row fails preliminary reachability validation
- **THEN** the row receives a controlled terminal failure
- **AND** its assigned model-specific worker/controller does not start
- **AND** later eligible room rows remain eligible to run

## ADDED Requirements

### Requirement: MIH-7 room mode keeps legacy interactive shell actions fail-closed

For the lifetime of a room-mode session implemented by this capability, including after the automatic room cycle reaches terminal completion, existing device-specific network-backed controls SHALL remain unavailable unless and until a later approved exact-row interaction capability binds them to the current row context. This includes local device Refresh actions, Matrix route actions, PDU mutations, codec state-changing controls, live/polling starts, Call Log or other auxiliary network reads, and equivalent network-backed actions exposed by reused device views.

The permanent top-level `Отладка` action SHALL be unavailable in room mode in this capability. MIH-7 SHALL NOT derive Debug model/IP authority from the top IP field, current reusable screen, prior single-device request, or another presentation value. Exact-row Debug binding is deferred to `room-device-interaction-lifecycle`.

These restrictions SHALL remain in force after both clean and problem terminal room-cycle outcomes. Presentation of accepted per-record cache does not authorize a network operation. The permanent top full-room Refresh and network-free credential configuration remain governed by their separate room-mode contracts and are not row interaction authority.

#### Scenario: Clean room cycle does not enable old row controls

- **GIVEN** a room cycle completes with a supported row in `подключено` state
- **WHEN** the operator views that row before `room-device-interaction-lifecycle` exists
- **THEN** existing local Refresh, mutation, auxiliary, and live network actions remain disabled or unbound
- **AND** none of those intents can acquire a handler, open a transport, or send a device request

#### Scenario: Failed room cycle does not expose stale interactive authority

- **GIVEN** a room cycle completes with one or more failed or degraded rows
- **WHEN** the operator expands any row
- **THEN** MIH-7 exposes only presentation of that row's accepted or safe failed state
- **AND** no reused legacy row control can start network I/O from top-level or previous target state

#### Scenario: Debug is disabled in room mode

- **WHEN** a current diagnostic context is room mode
- **THEN** the permanent `Отладка` action is disabled or otherwise unavailable
- **AND** opening a room row cannot bind Debug implicitly from the top-level source IP or a prior single-device context
