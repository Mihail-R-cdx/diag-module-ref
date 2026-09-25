# diagnostic-application-shell Specification

## Purpose
TBD - created by archiving change bootstrap-openspec-baseline. Update Purpose after archive.
## Requirements
### Requirement: Desktop diagnostic application startup
The application SHALL start from `main.py`, create a PyQt5 `QApplication`,
apply the configured theme, show `VCSDiagnosticApp`, and enter the Qt event
loop. Unhandled main-thread exceptions SHALL be appended to `app_crash.log` and
shown in a critical dialog when a QApplication exists; unhandled Python-thread
exceptions SHALL be appended to the same log.

#### Scenario: Normal application launch
- **WHEN** `main.py` is executed in an environment with its GUI dependencies
- **THEN** the diagnostic main window is constructed and shown with the Qt event loop running

#### Scenario: Unhandled main-thread exception
- **WHEN** the configured main-thread exception hook receives an exception
- **THEN** it appends a timestamped traceback to `app_crash.log` and presents a critical dialog when possible

### Requirement: Device selection and refresh input validation

The main window target panel SHALL use one permanent target-search field as its only persistent diagnostic-target editor. The field SHALL accept either a syntactically valid IPv4 address or non-empty room-name text and SHALL NOT expose a persistent device-model selector, a `deviceCombo` equivalent, or the `Устройство` label.

The application SHALL preserve the operator's raw entered search text as presentation state until the operator edits it. Inventory normalization, canonical IP, selected room ID, exact model, current room generation, or result rendering SHALL NOT replace the visible raw query text.

The application/composition layer SHALL hold accepted exact model/room authority only in a current purpose-bound context produced by current inventory resolution or confirmed unavailable-inventory fallback. A user-initiated top Refresh or equivalent Enter action SHALL reject an empty/blank target before inventory resolution, credential resolution, reachability, handler acquisition, worker/controller submission, or device network I/O. For a non-empty target, application composition SHALL classify a normalized copy as follows:

```text
valid IPv4                -> IP target
otherwise non-empty text  -> room-name target
```

Typing, autocomplete computation, or selecting a room-name suggestion SHALL perform no ping, credential resolution, handler acquisition, worker/controller submission, or device network I/O.

For an IP target with valid current inventory, source-IP lookup SHALL preserve zero/one/many multiplicity without model/kind filtering:

- zero records SHALL fail closed as not found;
- more than one record SHALL fail closed as ambiguous;
- exactly one record with non-null authoritative `room_id` SHALL establish room diagnostic mode for that whole room even if the source model is unsupported/null;
- exactly one record with `room_id = null` and an exact registered `diagnostic_model` SHALL use the existing legacy single-device path;
- exactly one no-room record with null/unsupported model SHALL fail closed.

Valid-inventory not-found, ambiguous, unmapped, and unsupported IP outcomes SHALL NOT open manual model fallback or select a target by source text, `device_kind`, page type, room display data, previous request state, or prior fallback state.

For an IP target when canonical inventory is unavailable, unloadable, or corrupt under the existing structured inventory-load contract, diagnostic start SHALL automatically open the existing fail-closed diagnostic-purpose model fallback or focused equivalent. Only a new explicit model selection and explicit `Подключиться` confirmation bound to that current diagnostic-start purpose MAY create the fallback request context. A confirmed fallback SHALL remain purpose-bound and SHALL NOT be reused implicitly by a later request or by a room-name query.

For a room-name target, valid current inventory is mandatory. The application SHALL query the storage-independent canonical room-name search boundary and reason in distinct authoritative `room_id` results:

- zero matching room IDs SHALL produce a controlled no-match outcome;
- exactly one matching room ID MAY be selected by Enter/top Refresh directly;
- more than one matching room ID SHALL require an explicit current dropdown selection before Enter/top Refresh can start diagnostics;
- each suggestion SHALL expose a deterministic non-authoritative display label sufficient to distinguish otherwise identical room names within the current result set;
- selection SHALL bind the exact current inventory snapshot and query revision and SHALL NOT rewrite the raw search text;
- a selected room ID SHALL establish room mode directly and SHALL NOT create a synthetic source device.

When an explicit room-name selection exists, the GUI SHALL expose a separate visible current-selection cue adjacent to or directly associated with the target field. That cue SHALL display the selected result's deterministic selection label without replacing `raw_query`. The cue is presentation evidence only; exact `room_id + inventory snapshot + query revision` remains application authority. Editing the target-search text SHALL clear the cue and invalidate the prior selection. A stale selection from an older query revision or inventory snapshot SHALL NOT authorize diagnostics.

Room-name search with unavailable, unloadable, or corrupt inventory SHALL fail closed with a safe inventory-unavailable outcome and SHALL NOT open diagnostic model fallback, credential fallback, or guess a room/model.

For room diagnostic mode, global preliminary reachability SHALL NOT run against one selected model before the tree exists. The room lifecycle SHALL build the authoritative room context/tree first and apply the approved per-record credential-plan and reachability gates immediately before each eligible row's model-specific acquisition. A per-record reachability failure SHALL stop that row before its assigned model-specific worker/controller network operation while allowing later eligible room rows to continue. For the legacy supported no-room IP path, the existing single-device reachability gate remains after final exact model assignment.

The permanent `Пароль` capability MAY remain as an application-level action, including inside a `Действия` menu, but it SHALL remain network-free credential configuration and SHALL NOT read model authority from Qt selector state, prior requests, prior fallback state, current screen identity, or room-row presentation.

With valid inventory, exactly one IP record whose exact canonical `diagnostic_model` is registered MAY open that model's existing credential configuration, including when the record belongs to a room; it SHALL NOT start room polling. Valid-inventory zero-record, many-record, null-model, or unsupported-model outcomes SHALL report a controlled safe configuration-resolution error and SHALL NOT open manual model fallback.

For a valid IP target when inventory is unavailable, unloadable, or corrupt, `Пароль` MAY use the existing explicit credential-configuration fallback selection under its current purpose-bound confirmation contract. A room-name target SHALL NOT select an arbitrary room record/model for credentials and SHALL NOT use credential-configuration fallback.

#### Scenario: Main panel has one search field and no model selector

- **WHEN** the main diagnostic window is constructed
- **THEN** it exposes one persistent target-search field plus model-independent application actions
- **AND** it does not expose `deviceCombo`, another persistent model selector, or the `Устройство` label

#### Scenario: Main panel has no persistent model selector

- **WHEN** the main diagnostic window is constructed
- **THEN** the permanent connection panel exposes the target-search input and model-independent actions
- **AND** it does not expose `deviceCombo`, another persistent model selector, or the `Устройство` label
- **AND** no default, previous Qt selection, or expanded room row acts as model authority

#### Scenario: Password action has no widget model authority

- **WHEN** the main window exposes the permanent `Пароль` action
- **THEN** that action does not read a model from `deviceCombo`, current screen, room-row label, window title, prior diagnostic request, prior fallback, or another Qt presentation value
- **AND** it begins the purpose-bound credential-configuration resolution flow

#### Scenario: Raw room query remains visible with a separate selected-room cue

- **GIVEN** the operator types `Перег` and selects a matching room from multiple suggestions
- **WHEN** room diagnostics starts and renders results
- **THEN** the search field still displays `Перег`
- **AND** a separate visible cue identifies the selected room using the deterministic suggestion label
- **AND** selected canonical `room_id` is stored separately as application authority

#### Scenario: Identical room names remain visibly distinguishable

- **GIVEN** multiple distinct canonical room IDs have the same room display name
- **WHEN** the autocomplete results are shown
- **THEN** each result has a deterministic distinguishable selection label using approved room display metadata and, if still necessary, a neutral deterministic result discriminator
- **AND** selecting one result visibly identifies that same selection without exposing raw `room_id` as operator identity

#### Scenario: Valid room device IP opens the whole room

- **GIVEN** valid inventory contains exactly one record for the entered IPv4 target
- **AND** that record has non-null `room_id`
- **WHEN** Enter/top Refresh starts diagnostics
- **THEN** the complete room session/tree is established from that room ID
- **AND** the entered IP text remains visible unchanged

#### Scenario: Valid supported device refresh

- **GIVEN** valid current inventory contains exactly one source-IP record for the normalized IPv4 target
- **WHEN** the operator starts Refresh or equivalent Enter action
- **THEN** a non-null authoritative `room_id` on that source record establishes room diagnostic mode regardless of whether its source `diagnostic_model` is null, unsupported, or supported
- **AND** the room tree/lifecycle is built before ordinary model-specific diagnostic work
- **AND** ordinary manual model fallback is not offered
- **AND** each supported eligible room record is handled by the room queue with credentials, preliminary reachability, and worker/controller acquisition evaluated for that exact row
- **AND** when the one source record instead has `room_id = null` and an exact registered `diagnostic_model`, the existing legacy single-device diagnostic path assigns the matching registered screen and lifecycle
- **AND** that legacy path applies model-specific credential and reachability rules, creates no synthetic room, and offers no ordinary manual override

#### Scenario: Valid supported device refresh enters room mode

- **GIVEN** valid current inventory contains exactly one record for the normalized IPv4 target
- **AND** that record has a non-null authoritative `room_id`
- **WHEN** the operator starts Refresh or equivalent Enter action
- **THEN** the record and `room_id` become the authoritative source for a new room diagnostic session
- **AND** the room tree/lifecycle is composed before per-row credentials, reachability checks, handlers, or workers start
- **AND** ordinary manual model fallback is not offered

#### Scenario: Unsupported source record still enters room mode

- **GIVEN** valid current inventory contains exactly one record for the normalized IPv4 target
- **AND** that record has a non-null authoritative `room_id`
- **AND** its canonical `diagnostic_model` is null or not registered
- **WHEN** the operator starts Refresh
- **THEN** room mode is still established from the authoritative room ID
- **AND** the source row is represented as unsupported in the room tree
- **AND** other supported eligible room records may still be diagnosed
- **AND** no fallback model is requested for the source row

#### Scenario: Room-name query has exactly one room result

- **GIVEN** valid inventory room-name search returns one distinct canonical `room_id`
- **WHEN** the operator presses Enter or top Refresh
- **THEN** that exact room is selected and room diagnostics may start
- **AND** the visible current-selection cue identifies the selected room
- **AND** no synthetic source record is created

#### Scenario: Room-name query has multiple room results

- **GIVEN** valid inventory room-name search returns multiple distinct canonical `room_id` values
- **WHEN** no current suggestion has been explicitly selected
- **THEN** Enter/top Refresh starts no room/device network I/O
- **AND** the operator must select one exact room result

#### Scenario: Selecting a room suggestion is network-free

- **WHEN** the operator selects one room from the autocomplete dropdown
- **THEN** application state records that exact current room candidate
- **AND** the GUI shows the corresponding current-selection cue
- **AND** no ping, credential resolution, handler acquisition, worker submission, or device network I/O starts merely from selection

#### Scenario: Search text edit invalidates selection

- **GIVEN** a room suggestion was selected for query revision N
- **WHEN** the operator edits the search field
- **THEN** the old selection and its visible selection cue are cleared
- **AND** the old selection cannot authorize a later diagnostic start
- **AND** a new resolution is required for the new query revision

#### Scenario: Repeated Refresh uses the visible current selection

- **GIVEN** a multi-match room-name query has one explicit current selection
- **AND** the raw query text has not changed
- **WHEN** top Refresh is requested again
- **THEN** the application may reuse only that same selected `room_id` if it is still a member of the current candidate set in the current inventory snapshot
- **AND** the visible selection cue continues to identify that exact selection
- **AND** otherwise the selection is invalidated and a new explicit choice is required

#### Scenario: Room-name search inventory is unavailable

- **GIVEN** the target is not a valid IPv4 address
- **WHEN** canonical inventory is unavailable, unloadable, or corrupt
- **THEN** the application reports a controlled inventory-unavailable outcome
- **AND** it does not open model fallback, credential fallback, or perform device network I/O

#### Scenario: Valid supported record has no room ID

- **GIVEN** valid current inventory contains exactly one record for the normalized IPv4 target
- **AND** `room_id` is null
- **AND** the record has an exact `diagnostic_model` present in the application dispatch registry
- **WHEN** the operator starts Refresh
- **THEN** the matching registered screen and existing legacy model-specific lifecycle are assigned
- **AND** model-specific credentials and the existing single-device reachability check use only that assigned model
- **AND** no synthetic room is created and no ordinary manual override is offered

#### Scenario: Legacy supported no-room IP remains available

- **GIVEN** exactly one inventory record matches the valid IPv4 target
- **AND** `room_id = null`
- **AND** its exact canonical model is registered
- **WHEN** diagnostics starts
- **THEN** the existing legacy single-device screen/lifecycle remains available
- **AND** no synthetic room is created

#### Scenario: Valid inventory source IP is not found

- **GIVEN** current inventory is valid
- **WHEN** the normalized IPv4 target has zero records
- **THEN** the application reports a controlled not-found outcome
- **AND** it selects no automatic model, room, page, credential chain, handler, worker, or controller
- **AND** it does not open manual model fallback or perform device network I/O

#### Scenario: Valid inventory source IP is ambiguous

- **GIVEN** current inventory is valid
- **WHEN** the normalized IPv4 target has more than one record
- **THEN** the application reports a controlled ambiguous outcome
- **AND** it does not filter by model, device kind, room, page type, or record order to choose a target
- **AND** it opens no manual model fallback and performs no device network I/O

#### Scenario: Valid no-room record cannot assign a supported model

- **GIVEN** current inventory is valid
- **AND** exactly one record matches the normalized IPv4 target
- **AND** that record has `room_id = null`
- **AND** its canonical `diagnostic_model` is null or unsupported
- **WHEN** diagnostic start is requested
- **THEN** the application selects no page, credential chain, handler, worker, or controller
- **AND** it reports a safe unsupported/unmapped outcome
- **AND** it does not open manual model fallback

#### Scenario: Valid no-room unsupported IP remains fail-closed

- **GIVEN** current inventory is valid
- **AND** exactly one record matches the valid IPv4 target
- **AND** `room_id = null`
- **AND** its canonical model is null or unsupported
- **WHEN** diagnostic start is requested
- **THEN** no page, credential chain, handler, worker, controller, or manual model fallback is selected
- **AND** the application reports a safe unsupported/unmapped outcome

#### Scenario: Inventory cannot assign a supported diagnostic model

- **WHEN** valid current inventory has zero source-IP records for the normalized IPv4 target
- **THEN** the application fails closed without selecting a model, page, credential chain, handler, worker, or controller
- **AND** it opens no manual model fallback and performs no device network I/O
- **WHEN** valid current inventory has more than one source-IP record for the normalized IPv4 target
- **THEN** the application fails closed as ambiguous without selecting a model or manual fallback and performs no device network I/O
- **WHEN** valid current inventory has exactly one source-IP record with `room_id = null` and a null or unsupported `diagnostic_model`
- **THEN** the application fails closed without manual fallback or device network I/O
- **WHEN** valid current inventory has exactly one source-IP record with a non-null `room_id` and a null or unsupported `diagnostic_model`
- **THEN** that record is not an unresolved target: room mode starts from its authoritative room ID, the source row is unsupported, other eligible supported room records may run, and no fallback is requested for the source row
- **WHEN** inventory is unavailable, unloadable, or corrupt for a normalized IPv4 target
- **THEN** diagnostic-purpose manual fallback remains permitted only after a new confirmed model selection creates the fallback context

#### Scenario: Inventory is unavailable for diagnostic start

- **GIVEN** the current target is a valid IPv4 address
- **WHEN** canonical inventory is unavailable, unloadable, or corrupt
- **THEN** the application automatically opens the existing fail-closed diagnostic-purpose model fallback or focused equivalent
- **AND** only a new explicit model selection and `Подключиться` confirmation bound to that diagnostic-start purpose may create the manual-fallback request context

#### Scenario: IP target inventory is unavailable for diagnostic start

- **GIVEN** the target is a valid IPv4 address
- **WHEN** canonical inventory is unavailable, unloadable, or corrupt
- **THEN** the application automatically opens the existing fail-closed diagnostic-purpose model fallback or focused equivalent
- **AND** only a new explicit model selection and `Подключиться` confirmation may establish current diagnostic fallback authority

#### Scenario: Password resolves a supported inventory model without diagnostics

- **GIVEN** current inventory is valid
- **AND** exactly one record matches the valid IPv4 target
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

#### Scenario: Password fallback remains available only for unavailable inventory IP context

- **GIVEN** the current target is a valid IPv4 address
- **WHEN** inventory is unavailable, unloadable, or corrupt
- **THEN** the existing explicit credential-configuration fallback selection MAY be used
- **AND** the resulting model authority is bound only to that credential-configuration purpose
- **AND** no diagnostic device I/O starts

#### Scenario: Password is not room-name model selection

- **GIVEN** the current target is a room-name query or room-name selection
- **WHEN** the operator requests credential configuration
- **THEN** no arbitrary room record/model is selected for `Пароль`
- **AND** no diagnostic or credential fallback is opened
- **AND** no device network I/O starts

#### Scenario: Invalid refresh input

- **WHEN** the target-search field is empty or blank
- **THEN** the application displays a controlled warning
- **AND** it does not query inventory, open fallback, build a room session, resolve model-specific credentials, perform reachability validation, acquire a handler, submit a worker/controller operation, or perform device network I/O
- **AND** a non-empty value that is not a valid IPv4 address is treated as room-name text rather than rejected solely as a malformed IPv4 address

#### Scenario: Preliminary reachability validation fails

- **GIVEN** a final exact legacy single-device automatic or confirmed-fallback diagnostic model has been assigned for a valid IPv4 target
- **WHEN** preliminary reachability validation fails
- **THEN** the application displays the existing controlled warning, does not start the assigned device worker/controller, and performs zero model-specific device diagnostic I/O
- **GIVEN** room mode is active and an exact supported eligible row reaches its queue turn
- **WHEN** that row fails its per-row preliminary reachability validation
- **THEN** that row receives a terminal controlled failure, its worker/controller does not start, and later eligible room rows continue

#### Scenario: Legacy preliminary reachability validation fails

- **GIVEN** a final exact legacy single-device automatic or confirmed-fallback diagnostic model has been assigned for a valid IPv4 target
- **WHEN** preliminary reachability validation fails
- **THEN** the application displays the existing controlled warning
- **AND** it does not start the assigned device diagnostic worker/controller network operation

#### Scenario: Legacy preliminary reachability validation remains in force

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

#### Scenario: Room-row preliminary reachability validation remains in force

- **GIVEN** room mode is active and a supported eligible row reaches its queue turn
- **WHEN** that exact row fails preliminary reachability validation
- **THEN** the row receives a controlled terminal failure
- **AND** its assigned model-specific worker/controller does not start
- **AND** later eligible room rows remain eligible to run

### Requirement: User-visible request state
The GUI SHALL expose loading, connected, authentication-error, request-error,
unavailable, disabled, and command states through text and non-color cues. It
SHALL disable the refresh action while an active refresh is pending and restore
it when the current request finishes or fails.

#### Scenario: Current request completes
- **WHEN** the active worker emits completion after a refresh
- **THEN** the refresh action is restored and the screen retains the state set by the current request outcome

#### Scenario: Authentication failure
- **WHEN** a current request exhausts its available credentials
- **THEN** the application leaves loading state, surfaces an authentication outcome, and re-enables refresh

### Requirement: MatrixScreen intent and display boundary
`MatrixScreen` SHALL remain a Matrix UI boundary that renders Matrix data and
publishes non-secret user intents. It SHALL NOT own credential candidate
selection, credential indexes, handler acquisition, persistent handler/session
state, transport lifecycle, retry policy, credential fallback, keepalive, exact
SIS command generation, or direct Matrix network I/O.

Matrix route and refresh user actions SHALL cross the screen boundary as
non-secret intent or callback data. A route intent SHALL identify the selected
authoritative logical `input_id` and `output_id`; for existing single-output
IN1804 this remains output `1`. Presentation SHALL NOT decide whether the
resulting command is `N!`, `N*1!`, `N*M!`, or another approved profile syntax.

Qt signals or callbacks from `MatrixScreen` SHALL NOT carry credential values,
credential candidate lists, handler objects, session objects, transport
objects, cookies/tokens, raw SIS commands, or other secret/session material.

The application/controller boundary SHALL validate intent IDs against the
current exact Matrix target's accepted topology/capability context before
creating a state-changing operation. A stale capability/profile from a replaced
target SHALL NOT authorize a route.

#### Scenario: Route click emits intent only
- **WHEN** the operator clicks an actionable Matrix routing cell
- **THEN** `MatrixScreen` publishes a route intent for the selected authoritative Matrix input/output context
- **AND** the intent contains explicit non-secret input/output identity
- **AND** it does not call `ExtronIN1804Handler.set_connection()` or another model handler directly
- **AND** it does not construct SIS command syntax
- **AND** it does not acquire or reuse a handler/session object

#### Scenario: Quick refresh is not screen-owned network I/O
- **WHEN** Matrix route status needs to be refreshed after a route action
- **THEN** `MatrixScreen` requests or receives the update through the Matrix application boundary
- **AND** it does not call `ExtronIN1804Handler.get_connections()` or another handler read directly

#### Scenario: Screen does not own credentials
- **WHEN** a Matrix route or refresh intent is submitted
- **THEN** `MatrixScreen` does not read or mutate credential candidate lists or successful credential indexes
- **AND** credential ownership remains outside the screen boundary

#### Scenario: Screen signal payloads are secret-free
- **WHEN** `MatrixScreen` emits a route or refresh signal/callback
- **THEN** the payload contains no credential values, credential candidate lists, handler objects, session objects, cookies, tokens, transport objects, or raw SIS command strings

#### Scenario: Rendering remains screen-owned
- **WHEN** the active Matrix controller accepts current Matrix data
- **THEN** `MatrixScreen` remains responsible for rendering the routing table, accepted route state, signal/HDCP indicators, and device information
- **AND** a multi-output accepted route map MAY render multiple output columns without transferring protocol authority into the screen

### Requirement: PDUScreen intent and display boundary
`PDUScreen` SHALL be a PDU UI boundary that renders accepted PDU device data, outlet records, model capabilities, refresh-lane state, mutation-lane control state, and current busy/loading presentation. It SHALL publish non-secret user intents for refresh, individual outlet mutation, and sequential bulk mutation. It SHALL NOT own credential candidate selection, credential indexes, credential fallback, successful credential memory, worker creation or submission, handler acquisition, request/operation generation authority, refresh lane authority, mutation lane authority, stale operation acceptance, or direct PDU network I/O.

PDU refresh and mutation actions SHALL cross the screen boundary through an explicit signal or callback interface. `PDUScreen` SHALL NOT depend on arbitrary parent orchestration methods such as `control_pdu_outlet(...)`, `control_pdu_outlets_bulk(...)`, or `refresh_data()` to execute PDU lifecycle. The screen MAY retain local rendering helpers and confirmation dialogs that are view responsibilities.

Qt signals or callbacks from `PDUScreen` SHALL NOT carry credential values, credential candidate lists, credential dictionaries, handler objects, session objects, transport objects, cookies, Session IDs, CSRF tokens, or other secret or session material.

#### Scenario: Individual outlet action emits intent only
- **WHEN** the operator confirms an individual PDU outlet action
- **THEN** `PDUScreen` publishes the outlet number and requested non-secret operation through the explicit PDU intent boundary
- **AND** it does not acquire a handler, create a worker, select a credential candidate, or call an arbitrary parent outlet-control method

#### Scenario: Bulk action emits intent only
- **WHEN** the operator confirms bulk ON or bulk OFF
- **THEN** `PDUScreen` publishes the requested non-secret bulk operation through the explicit PDU intent boundary
- **AND** it does not build credential attempts, create workers, or call an arbitrary parent bulk-control method

#### Scenario: Refresh emits intent only
- **WHEN** the operator requests a PDU status refresh from `PDUScreen`
- **THEN** the screen publishes a refresh intent through the explicit PDU application boundary
- **AND** it does not execute PDU network I/O or directly invoke generic parent refresh orchestration as the PDU lifecycle authority

#### Scenario: Screen does not own PDU operation freshness
- **WHEN** a PDU result, error, progress/status, or completion is associated with an operation context
- **THEN** `PDUScreen` does not decide whether that operation is current from credential state, worker identity, request generation, lane identity, or Qt widget values
- **AND** it renders only state or outcomes accepted by the PDU application lifecycle boundary

#### Scenario: Screen signal payloads are secret-free
- **WHEN** `PDUScreen` emits a refresh, individual mutation, or bulk mutation intent
- **THEN** the payload contains no credential values, credential candidate lists, handler/session objects, cookies, tokens, or transport objects

#### Scenario: Rendering and confirmation remain screen responsibilities
- **WHEN** the active PDU controller accepts current device data or control state
- **THEN** `PDUScreen` remains responsible for rendering device information, dynamic outlet records, capability-driven controls, refresh presentation, and mutation busy/loading presentation
- **AND** implementation may keep individual and bulk confirmation dialogs in the screen without giving it application lifecycle ownership

### Requirement: DMP polling controller composition boundary

`VCSDiagnosticApp` SHALL compose a DMP-specific polling controller as the application lifecycle boundary for Extron DMP 64 Plus meter diagnostics.

The main window SHALL retain global input validation, generic request composition, credential-provider ownership, successful credential memory, global UI state helpers, and rendering integration. It SHALL delegate DMP polling generation, cancellation publication, worker submission/binding, stale callback authority, DMP credential-attempt coordination, first-complete-snapshot success gating, and DMP shutdown/invalidation to the DMP controller.

`AudioDSPScreen` SHALL remain the rendering boundary for accepted DMP data. It SHALL NOT own DMP worker creation, cancellation authority, credential candidate selection, credential fallback, successful credential persistence, handler/session ownership, or stale callback decisions.

The DMP controller SHALL receive only the focused application callbacks/providers required to obtain public model/IP/request context and application-owned credential policy decisions. It SHALL NOT become a generic shell replacement or a generic device lifecycle manager.

#### Scenario: MainWindow routes DMP refresh to the controller
- **WHEN** global refresh validation and generic request setup succeed for `Extron DMP 64 Plus`
- **THEN** `VCSDiagnosticApp` delegates DMP polling startup to the DMP controller
- **AND** it does not directly construct and bind the authoritative DMP worker lifecycle

#### Scenario: MainWindow delegates DMP invalidation
- **WHEN** model, IP, DMP credential context, repeat Refresh, relevant screen lifecycle, or application shutdown supersedes the active DMP context
- **THEN** the shell delegates DMP invalidation/cancellation to the controller
- **AND** it does not maintain a second independent DMP generation authority

#### Scenario: Generic shell callbacks contain no DMP stale policy
- **WHEN** DMP lifecycle extraction is complete
- **THEN** generic device result, error, progress, status, and finished handlers receive only DMP callbacks already accepted by the DMP controller
- **AND** they do not independently evaluate DMP-specific worker context freshness

#### Scenario: Generic shell error handling does not retry DMP credentials
- **WHEN** a DMP worker reports a failure
- **THEN** DMP retry eligibility and candidate advancement are decided at the DMP controller/application credential boundary
- **AND** generic device-error dispatch does not independently restart DMP polling with another candidate

#### Scenario: AudioDSPScreen remains rendering-only for DMP lifecycle
- **WHEN** the DMP controller accepts a current meter snapshot
- **THEN** `AudioDSPScreen` renders the accepted DMP data
- **AND** it does not decide whether the worker/context is current or manage DMP credentials/sessions

### Requirement: PDU room-codec enrichment composition boundary

`VCSDiagnosticApp` SHALL compose validated equipment-inventory availability, a focused
room-context resolver, and a dedicated PDU-room-codec enrichment controller. The main window
SHALL remain the owner of credential-provider access, successful credential-index memory,
saved codec connection-profile memory, and shutdown wiring.

The shell SHALL consume two focused non-secret lifecycle boundaries owned by
`PDUController`:

```text
accepted current user PDU refresh
PDU context superseded/invalidated
```

The accepted-refresh boundary SHALL be delegated to the enrichment controller only after the
PDU controller has accepted a current successful user refresh. Stale results, PDU errors,
completion without accepted success, and mutation reconciliation refreshes SHALL NOT start
enrichment.

The supersession boundary SHALL be delegated immediately when PDU model, IP, credential
context, repeat/new user refresh, explicit PDU context invalidation/deactivation, or shutdown
supersedes the current PDU context. The shell SHALL NOT wait for a replacement successful PDU
result before invalidating old enrichment.

The shell SHALL NOT infer supersession or background freshness by reading Qt widgets. It
SHALL NOT maintain a second PDU generation authority. It SHALL only forward the PDU-owned
context generation/revision and safe reason, or invoke an equivalent focused controller
method at the PDU lifecycle boundary.

The enrichment controller SHALL receive only focused providers/callbacks needed to obtain the
immutable inventory, codec credential candidates, saved exact model/IP credential index and
profile, accepted-success persistence, and accepted presentation rendering. It SHALL NOT
become a generic main-window replacement or take ownership of PDU refresh/mutation lifecycle.

#### Scenario: Application starts with valid inventory

- **WHEN** the canonical inventory snapshot loads successfully
- **THEN** the shell composes that immutable inventory revision into the focused enrichment boundary
- **AND** existing device dispatch remains unchanged until a current user PDU refresh is accepted

#### Scenario: Application starts without valid inventory

- **WHEN** canonical inventory cannot be loaded
- **THEN** the shell retains the safe structured load failure for enrichment presentation
- **AND** startup and existing PDU, codec, Matrix, and audio-DSP diagnostics remain available

#### Scenario: PDU controller accepts a user refresh

- **WHEN** `PDUController` publishes an accepted current user-refresh context
- **THEN** the shell delegates it to the enrichment controller
- **AND** the shell does not perform room lookup or codec network I/O itself

#### Scenario: PDU context is superseded before replacement success

- **GIVEN** room/codec data from the current PDU are visible or related-codec work is pending
- **WHEN** `PDUController` publishes model/IP/credential/new-refresh/context/shutdown supersession
- **THEN** the shell immediately delegates supersession to the enrichment controller
- **AND** the old dedicated codec lane is invalidated
- **AND** old room/codec presentation is cleared or reset
- **AND** replacement PDU refresh success is not required for that invalidation

#### Scenario: Replacement PDU refresh fails

- **WHEN** a new PDU refresh superseded old enrichment and then completes with error
- **THEN** no accepted-success enrichment is started
- **AND** old room/codec values remain cleared
- **AND** stale old callbacks cannot restore or persist them

#### Scenario: PDU reconciliation is accepted

- **WHEN** current PDU mutation reconciliation completes
- **THEN** the shell does not treat it as a room-codec enrichment trigger

### Requirement: PDUScreen related-room presentation boundary

`PDUScreen` SHALL remain a rendering boundary while presenting accepted PDU-room-codec
state. It MAY render neutral/pending state, room identity/display evidence, related codec
model/IP, normalized call status, normalized presentation status, and safe structured
resolution/diagnostic outcomes.

`PDUScreen` SHALL NOT load/query inventory, interpret multiplicity, select a codec, resolve
credentials, create or submit codec work, acquire a handler, perform network I/O, decide
freshness, or persist credential/profile memory.

Automatic enrichment failures SHALL be inline and non-modal. They SHALL NOT clear accepted
PDU outlet/device data or change PDU refresh/mutation authority.

The related-room section SHALL be reset immediately on PDU-context supersession, including
new/repeat Refresh before its outcome is known. Reset SHALL NOT be deferred until a later
accepted successful refresh.

#### Scenario: New PDU refresh starts

- **GIVEN** old room/codec values are displayed
- **WHEN** PDU context is superseded at new user-refresh start
- **THEN** `PDUScreen` clears or resets the previous related-room section immediately
- **AND** stale old callbacks cannot restore previous values

#### Scenario: Enrichment resolution is unavailable

- **WHEN** the controller accepts current not-found, ambiguous, unsupported, or inventory-unavailable state
- **THEN** `PDUScreen` renders the safe inline outcome
- **AND** accepted PDU information, outlet table, controls, and connection state remain available

#### Scenario: Related codec status is accepted

- **WHEN** the controller accepts current normalized call and presentation status
- **THEN** `PDUScreen` renders those values
- **AND** it receives no raw codec status, credential values, or session objects

#### Scenario: Screen payload is secret-free

- **WHEN** the shell/controller sends an enrichment presentation model
- **THEN** it contains no credential values, candidate dictionaries, profile names, cookies, Session IDs, CSRF/access tokens, handlers, workers, transports, or sessions

### Requirement: Equipment pages expose current room context

The diagnostic application composition layer SHALL resolve room context for the currently selected equipment from the already loaded immutable equipment inventory. Resolution SHALL use the exact current equipment IP, require exactly one total IP match, and use non-null `room_id` as the only room identity authority.

The shared room context SHALL expose safe presentation state for:

```text
room address from consistent room_name evidence
room VIP state from normative room_vip aggregation
structured missing, ambiguous, and conflict outcomes
inventory snapshot identity
current equipment model/IP/page generation
```

The resolver SHALL NOT perform network I/O, query a device handler, use `room_name` as fallback identity, select the first record from an ambiguous result, or change device diagnostic success/failure authority.

#### Scenario: Equipment room context resolves

- **GIVEN** the current equipment IP has exactly one inventory record with authoritative room identity
- **AND** the room has consistent address and VIP evidence
- **WHEN** room context is resolved
- **THEN** the application exposes the room address and VIP state for presentation
- **AND** no device network request is performed

#### Scenario: Equipment IP is ambiguous

- **WHEN** more than one inventory record matches the current equipment IP
- **THEN** room context is ambiguous
- **AND** no matching record is selected by order or device kind
- **AND** device diagnostics remain independently usable

### Requirement: Non-PDU equipment pages render a shared room-information block

Every equipment page registered by the application equipment-page registry SHALL pass through the centralized equipment-page shell or equivalent shared layout boundary. That boundary SHALL render exactly one shared room-information block for every registered non-PDU page and SHALL omit that bottom block only for PDU pages, which retain their dedicated placement contract.

The registry/shell invariant, rather than a manually maintained subset of screen classes, SHALL define the complete supported non-PDU page scope. Tests SHALL enumerate every registered equipment-page entry and prove that each non-PDU registration receives the shared block while each PDU registration uses the dedicated PDU presentation.

The shared non-PDU block SHALL be placed at the bottom of the equipment page and SHALL show:

```text
Адрес: <resolved room_name or safe unavailable text>
VIP: ДА | НЕТ | НЕТ ДАННЫХ | КОНФЛИКТ ДАННЫХ
```

The block SHALL use one shared presentation model or reusable widget so normalization, lifecycle binding, and safe fallback behavior are not independently reimplemented by individual equipment screens or controllers.

The room-information block SHALL remain informational. Missing inventory, unresolved room identity, duplicate IP, address conflict, or VIP conflict SHALL be shown inline and SHALL NOT open an automatic modal connection error, disable valid equipment controls, or convert a successful device diagnostic result into failure.

#### Scenario: Registered non-PDU page displays VIP room

- **GIVEN** a non-PDU equipment page is registered through the application equipment-page registry
- **AND** its current equipment context resolves to a VIP room
- **WHEN** that page context becomes current
- **THEN** the centralized equipment-page shell renders the bottom room-information block
- **AND** the block shows the resolved address
- **AND** it shows `VIP: ДА`

#### Scenario: Registry coverage is complete

- **WHEN** the application enumerates all registered equipment pages
- **THEN** every non-PDU registration is routed through the shared room-information boundary
- **AND** no supported non-PDU page relies on manual opt-in to receive the block
- **AND** PDU registrations are identified explicitly and use the dedicated PDU placement contract

#### Scenario: Inventory is unavailable

- **GIVEN** device diagnostics can run but inventory loading failed
- **WHEN** a non-PDU equipment page becomes current
- **THEN** the room-information block shows safe unavailable state
- **AND** device diagnostics and controls retain their existing authority

### Requirement: Non-PDU room context uses one application-owned publication lifecycle

For non-PDU pages, changing the selected model, normalized IP address, page context, credential context, or accepted inventory snapshot SHALL immediately invalidate the previously published room presentation and create a new application-owned room-context generation.

After invalidation, the application SHALL resolve room context for the new current `(model, normalized_ip, snapshot_id, page_context, generation)` from the immutable inventory without waiting for, depending on, or being triggered by device network success. The pure resolver MAY run synchronously. If coordination or publication is asynchronous, the result SHALL be rendered only after all bound context values and generation still match the current application context.

Device refresh start, progress, success, error, completion, and stale callbacks SHALL NOT be room-context publication authorities. They SHALL NOT rerun room resolution, publish room context, clear a valid independently resolved room context, or restore an older room context.

#### Scenario: New IP resolves without device refresh

- **GIVEN** a registered non-PDU page is current
- **WHEN** the operator selects a new model/IP context without starting device refresh
- **THEN** prior room presentation is invalidated immediately
- **AND** room context for the new exact model/IP and current snapshot is resolved from inventory
- **AND** matching room presentation may be published without device network I/O

#### Scenario: Device refresh fails after room resolution

- **GIVEN** current room context was resolved and published from inventory
- **WHEN** the device network refresh fails
- **THEN** the matching room address and VIP state remain available
- **AND** the device failure does not clear, replace, or republish room context

#### Scenario: Old refresh completes after IP change

- **GIVEN** a device refresh for an old equipment context remains in flight
- **WHEN** the selected IP changes and a new room-context generation becomes current
- **AND** the old refresh later completes
- **THEN** its callback cannot publish or restore room presentation
- **AND** only room context bound to the new full context tuple may remain visible

### Requirement: Inventory-driven diagnostic dispatch uses exact canonical diagnostic_model

The application/composition layer SHALL own inventory-driven diagnostic dispatch. For a valid normalized IP and current immutable `EquipmentInventory`, it SHALL call `find_by_ip(...)`, classify the complete returned tuple as zero, one, or many, and inspect canonical fields only when exactly one total record exists.

For one record, automatic dispatch SHALL use only its exact non-null canonical `diagnostic_model`. The application SHALL NOT derive, repair, or choose a model from `device_kind`, `source_model`, manufacturer/model evidence, substring or fuzzy matching, aliases, handler availability, source row order, registry order, prior user selection, prior request context, or protocol failure.

The closed dispatch registry SHALL be exactly:

| Exact canonical `diagnostic_model` | Screen key | Existing diagnostic lifecycle |
| --- | --- | --- |
| `Huawei TE20` | `codec` | Huawei TE20 refresh path |
| `Huawei TE40` | `codec` | Huawei TE40 refresh path |
| `CloudLink Bar 310` | `codec` | shared CloudLink Bar/Box 310 lifecycle `cloudlink_bar_310` |
| `CloudLink Box 310` | `codec` | shared CloudLink Bar/Box 310 lifecycle `cloudlink_bar_310` |
| `Polycom RPG 310` | `codec` | Polycom RPG 310 refresh path |
| `Extron IN1804` | `matrix` | `MatrixController` refresh path |
| `Extron IN1806` | `matrix` | `MatrixController` with exact Matrix model context |
| `Extron IN1808` | `matrix` | `MatrixController` with exact Matrix model context |
| `Extron IN1608 xi` | `matrix` | `MatrixController` with exact Matrix model context |
| `Extron DTP CrossPoint 84` | `matrix` | `MatrixController` with exact Matrix model context |
| `Extron DTP CrossPoint 82 4K` | `matrix` | `MatrixController` with exact Matrix model context |
| `Extron DTP CrossPoint 84 4K` | `matrix` | `MatrixController` with exact Matrix model context |
| `Extron DTP CrossPoint 86 4K` | `matrix` | `MatrixController` with exact Matrix model context |
| `Extron DTP CrossPoint 108 4K` | `matrix` | `MatrixController` with exact Matrix model context |
| `Aten PE8208AV` | `pdu` | `PDUController` with exact Aten model context |
| `Extron IPL T PCS4i` | `pdu` | `PDUController` with exact PCS4i model context |
| `Biamp Tesira Forte CI` | `audio_dsp` | existing Biamp polling path |
| `Extron DMP 64 Plus` | `audio_dsp` | `DMPPollingController` refresh path |

Each exact model SHALL have one and only one registry entry. Multiple exact models MAY share one explicitly reviewed lifecycle route while retaining distinct application model identity. Unknown models SHALL have no default route. Diagnostic fallback choices, credential-configuration fallback choices, page registration, and lifecycle routing SHALL derive from or be integrity-checked against this same closed registry.

The registry SHALL contain no credentials, credential candidate lists, successful indexes, handler/session/transport instances, cookies/tokens, or mutable worker state.

#### Scenario: Unique Aten record selects PDU diagnostics

- **GIVEN** exactly one inventory record matches the current IP
- **AND** its `diagnostic_model` is exactly `Aten PE8208AV`
- **AND** its `device_kind` is `other`
- **WHEN** diagnostic inventory dispatch is accepted
- **THEN** the application assigns the `pdu` screen and exact Aten `PDUController` path
- **AND** `device_kind = other` does not block or alter dispatch

#### Scenario: Unique PCS4i record selects PDU diagnostics

- **GIVEN** exactly one inventory record matches the current IP
- **AND** its `diagnostic_model` is exactly `Extron IPL T PCS4i`
- **AND** its `device_kind` is `other`
- **WHEN** diagnostic inventory dispatch is accepted
- **THEN** the application assigns the `pdu` screen and exact PCS4i `PDUController` path

#### Scenario: Unique TE40 record selects codec diagnostics

- **GIVEN** exactly one inventory record matches the current IP
- **AND** its `diagnostic_model` is exactly `Huawei TE40`
- **WHEN** diagnostic inventory dispatch is accepted
- **THEN** the application assigns the `codec` screen and Huawei TE40 refresh path

#### Scenario: Unique CloudLink Box 310 record selects shared Bar/Box diagnostics

- **GIVEN** exactly one inventory record matches the current IP
- **AND** its `diagnostic_model` is exactly `CloudLink Box 310`
- **WHEN** diagnostic inventory dispatch is accepted
- **THEN** the application assigns the `codec` screen and lifecycle route `cloudlink_bar_310`
- **AND** the accepted application model remains exactly `CloudLink Box 310`
- **AND** the application does not rewrite the request model to `CloudLink Bar 310`

#### Scenario: Unique IN1804 record selects Matrix diagnostics

- **GIVEN** exactly one inventory record matches the current IP
- **AND** its `diagnostic_model` is exactly `Extron IN1804`
- **WHEN** diagnostic inventory dispatch is accepted
- **THEN** the application assigns the `matrix` screen and `MatrixController` refresh path

#### Scenario: Unique approved expanded Matrix record selects Matrix diagnostics

- **GIVEN** exactly one inventory record matches the current IP
- **AND** its exact `diagnostic_model` is one of `Extron IN1806`, `Extron IN1808`, `Extron IN1608 xi`, `Extron DTP CrossPoint 84`, `Extron DTP CrossPoint 82 4K`, `Extron DTP CrossPoint 84 4K`, `Extron DTP CrossPoint 86 4K`, or `Extron DTP CrossPoint 108 4K`
- **WHEN** diagnostic inventory dispatch is accepted
- **THEN** the application assigns the `matrix` screen and approved `MatrixController` lifecycle
- **AND** the exact canonical Matrix model remains the application/controller model context
- **AND** no XTP/XTP II model is selected by this registry

#### Scenario: Device kind alone grants no route or credential model

- **GIVEN** one inventory record has any canonical `device_kind`
- **AND** its `diagnostic_model` is null or unsupported
- **WHEN** application model resolution evaluates the record
- **THEN** no automatic page, lifecycle, or credential-model context is selected
- **AND** the application does not infer a model from kind or source text

#### Scenario: Unknown exact model has no default route

- **GIVEN** one inventory record has a non-null canonical `diagnostic_model` absent from the closed registry
- **WHEN** application model resolution evaluates the record
- **THEN** the outcome is unsupported
- **AND** the application does not default to codec, a same-kind page, the nearest handler, or a prior model

### Requirement: Application model resolution preserves complete IP cardinality

The application SHALL classify the complete `find_by_ip(...)` result before filtering or ranking by `device_kind`, `diagnostic_model`, source text, screen support, handler availability, or action purpose.

Observable outcomes SHALL distinguish at least:

```text
INVENTORY_UNAVAILABLE
IP_NOT_FOUND
AMBIGUOUS_IP
MODEL_UNMAPPED
MODEL_UNSUPPORTED
RESOLVED
```

The same exact cardinality and canonical-model interpretation SHALL be used by diagnostic startup and model-bound credential configuration. Concrete private types are not normative, but the outcomes SHALL remain independently testable.

An unresolved outcome SHALL not be treated as a device connection failure and SHALL not start automatic modal network-error presentation. The requesting action MAY open only its controlled purpose-bound fallback.

The application SHALL NOT select `records[0]`, the first supported record, the only familiar `device_kind`, or a record favored by registry order when multiple total records share one IP.

#### Scenario: IP is absent from inventory

- **WHEN** `find_by_ip(...)` returns zero records
- **THEN** no automatic model, page, credentials, controller, handler, or worker is selected
- **AND** the requesting action opens fallback with the safe not-found reason

#### Scenario: Duplicate IP is ambiguous before filtering

- **GIVEN** two or more total records share the normalized IP
- **WHEN** application model resolution evaluates that IP
- **THEN** the outcome is ambiguous
- **AND** the application does not inspect the records to select a preferred kind, model, page, credential key, or handler
- **AND** the requesting action opens fallback with the safe ambiguity reason

#### Scenario: One record has no recognized model

- **GIVEN** exactly one record matches the normalized IP
- **AND** its `diagnostic_model` is null
- **WHEN** application model resolution evaluates the record
- **THEN** no automatic model or page is selected
- **AND** source-model or manufacturer evidence is not reanalyzed at runtime
- **AND** the requesting action opens fallback with the safe unmapped reason

#### Scenario: Inventory is unavailable

- **WHEN** no valid immutable inventory is loaded
- **THEN** the requesting action opens controlled fallback with the safe inventory category
- **AND** it performs no model-specific work before explicit confirmation

### Requirement: Unresolved inventory uses an explicit purpose-bound fail-closed model fallback dialog

For every unresolved automatic outcome, the application SHALL open `DeviceModelFallbackDialog` or a focused equivalent bound to the current action purpose, action generation, normalized IP, and immutable inventory context.

Supported purposes SHALL include:

```text
DIAGNOSTIC_START
CREDENTIAL_CONFIGURATION
```

The dialog SHALL display a safe unresolved reason and only models from the closed dispatch registry. It SHALL NOT receive or display complete inventory records, source rows, credential values, handlers, workers, sessions, transports, or secrets.

No model SHALL be accepted merely because it is first, previously chosen, remembered, present in a prior request context, or visible on a diagnostic page. Confirmation SHALL remain disabled or be rejected until the operator explicitly selects one model during the current dialog interaction.

For `DIAGNOSTIC_START`, explicit selection plus `Подключиться` MAY create a `MANUAL_FALLBACK` diagnostic request context and continue to model-specific credentials and reachability checks.

For `CREDENTIAL_CONFIGURATION`, explicit selection plus `Продолжить` or equivalent non-connection confirmation MAY create a model-bound credential-configuration context and open the credential dialog only. It SHALL NOT create a diagnostic request context or start diagnostics.

Fallback selection SHALL NOT mutate or persist inventory, workbook, JSON, aliases, or canonical model memory. Cancel and window close SHALL dismiss the requesting action, return or retain controlled idle/current presentation, and perform no purpose-specific mutation or device I/O.

Fallback SHALL NOT be available as an override after a `RESOLVED` diagnostic outcome.

#### Scenario: Operator confirms diagnostic fallback

- **GIVEN** diagnostic-start resolution is unresolved
- **AND** current fallback has no accepted model
- **WHEN** the operator explicitly selects one registered model and confirms `Подключиться`
- **THEN** the application creates a current `MANUAL_FALLBACK` diagnostic request context for that exact model and IP
- **AND** only then may it resolve model-specific credentials and perform reachability validation

#### Scenario: Operator confirms credential-configuration fallback

- **GIVEN** credential-configuration resolution is unresolved
- **AND** current fallback has no accepted model
- **WHEN** the operator explicitly selects one registered model and confirms the non-connection continuation action
- **THEN** the application creates a current credential-configuration context for that exact model and IP
- **AND** it may open only that model's credential dialog
- **AND** it does not start diagnostic credentials, ping, page transition, controller/worker work, or device I/O

#### Scenario: No implicit first or previous selection

- **GIVEN** fallback opens for either purpose
- **WHEN** the operator has not explicitly selected a model in this dialog interaction
- **THEN** no model is accepted from item order, prior dialog state, former main-window state, or prior request context
- **AND** confirmation cannot continue the action

#### Scenario: Operator cancels or closes fallback

- **GIVEN** fallback is open for either purpose
- **WHEN** the operator activates Cancel or closes the window
- **THEN** the requesting action fails closed
- **AND** no model-specific credential resolution or mutation, ping, handler, worker/controller, page lifecycle, automatic diagnostic start, or device I/O occurs

#### Scenario: Resolved diagnostic inventory cannot be overridden

- **GIVEN** diagnostic dispatch accepted one exact registered model
- **WHEN** the diagnostic request proceeds
- **THEN** the automatic model remains authoritative for that request
- **AND** no fallback dialog or ordinary UI control permits replacement with another model

### Requirement: Password action configures credentials for one current exact model without device I/O

The permanent `Пароль` action SHALL be an application-owned model-bound credential-configuration action. Each activation SHALL validate and normalize the current IP and create a new `CREDENTIAL_CONFIGURATION` generation/binding distinct from diagnostic-start context.

For a valid IP, the action SHALL run the same exact inventory zero/one/many and canonical-model resolution defined by this capability. It SHALL NOT reuse `_active_request`, a previous successful model, a previous fallback model, current screen, window title, widget text, or another presentation value as model authority.

When resolution is `RESOLVED`, the action SHALL bind the exact inventory `diagnostic_model` and normalized IP and open the credential dialog for that model only. When resolution is unresolved, it SHALL first obtain a new explicit model through purpose-bound fail-closed fallback and only then open the credential dialog.

Before opening the credential dialog and again before credential mutation, the application SHALL verify that action purpose, generation, normalized IP, immutable inventory context, selection source, accepted exact model, and dialog identity are current.

Credential-dialog confirmation MAY add a new credential candidate or move an identical existing candidate to the configured first-attempt position according to existing application-owned credential-store semantics. The mutation SHALL affect only the accepted exact model and current normalized IP wherever existing credential APIs are IP-scoped. It MAY invoke the existing credential-context invalidation for that affected model/IP.

Credential configuration SHALL NOT:

- perform ping or another reachability check;
- change the visible diagnostic page;
- acquire a handler/session/transport;
- create or submit a worker/controller operation;
- perform device network I/O;
- create or replace a diagnostic request context;
- automatically start or refresh diagnostics after saving;
- mark the entered candidate as a confirmed successful credential;
- persist a connection profile;
- mutate another model's credential chain.

Credential-dialog Cancel or window close SHALL perform no credential mutation. Invalid/empty IP SHALL produce a controlled warning and SHALL not query inventory, open model fallback, open a credential dialog, or mutate credentials.

Secret values SHALL remain excluded from logs, public errors, status presentation, fallback payloads, and non-secret action bindings.

#### Scenario: Resolved inventory opens credentials for exact model

- **GIVEN** exactly one inventory record matches the current valid IP
- **AND** its exact `diagnostic_model` is registered
- **WHEN** the operator activates `Пароль`
- **THEN** the application opens the credential dialog for exactly that inventory model and IP
- **AND** it does not use a previous diagnostic or fallback model
- **AND** it performs no ping, page transition, device operation, or network I/O

#### Scenario: Unresolved credential action requires fallback

- **WHEN** credential-configuration resolution is inventory-unavailable, not found, ambiguous, unmapped, or unsupported
- **THEN** no credential model is chosen automatically
- **AND** purpose-bound fallback opens before the credential dialog
- **AND** no credential list is mutated before explicit fallback confirmation and credential-dialog confirmation

#### Scenario: Credential fallback is cancelled

- **GIVEN** credential-purpose fallback is open
- **WHEN** the operator cancels or closes it
- **THEN** no credential dialog opens
- **AND** no credentials, indexes, profiles, diagnostic context, page, controller, worker, or device I/O change

#### Scenario: Credential dialog is cancelled

- **GIVEN** a current exact model/IP credential dialog is open
- **WHEN** the operator cancels or closes it
- **THEN** no credential candidate, configured ordering, successful index, profile, inventory, or diagnostic context changes

#### Scenario: Credential save is model-bound but not success evidence

- **GIVEN** a current credential dialog is bound to exact model M and normalized IP A
- **WHEN** the operator confirms valid credential input
- **THEN** only M's candidate configuration for A is added/promoted under existing storage semantics
- **AND** the entered candidate is not recorded as a confirmed successful credential
- **AND** no connection profile is persisted
- **AND** diagnostics are not started automatically

#### Scenario: Stale credential dialog cannot mutate configuration

- **GIVEN** a credential fallback or credential dialog was opened under an older binding
- **WHEN** IP, inventory context, reset/shutdown, or a newer credential action supersedes it
- **THEN** later selection or confirmation is rejected before credential mutation
- **AND** no device work or I/O occurs

### Requirement: Purpose-bound model resolution freshness is application-owned and precedes work

Every user-initiated diagnostic start and every `Пароль` activation SHALL create a distinct application action generation. A shared global serial MAY be used only when action purpose is part of the binding and cross-purpose callbacks cannot be accepted.

A current binding SHALL include at least action purpose, generation, normalized IP, immutable inventory context/revision identity, resolution outcome, selection source (`AUTO_INVENTORY` or `MANUAL_FALLBACK`), exact assigned model when present, fallback-dialog identity when open, and credential-dialog identity for credential configuration.

IP change, inventory replacement/availability change, reset, and shutdown SHALL supersede all pending model-resolution/dialog work. A newer same-purpose action SHALL supersede an older action. Diagnostic and credential actions SHALL NOT reuse each other's accepted model context as authority.

A stale lookup, fallback selection/confirmation, credential-dialog confirmation, or diagnostic-start continuation SHALL be rejected before model-specific credential access or mutation, handler acquisition, worker/controller submission, and network I/O. It SHALL NOT publish/replace a model request context, change the visible page, change room/VIP presentation, alter credentials, start a controller operation, persist successful credential/profile memory, or start PDU-related-codec enrichment.

The application MAY execute bounded in-memory inventory query synchronously. It SHALL NOT reread JSON, parse Excel, or perform network I/O on the Qt GUI thread. If lookup is queued or asynchronous, publication SHALL pass the same binding checks.

After accepted diagnostic dispatch enters an existing device-specific lifecycle, approved Matrix, PDU, DMP, codec, or audio-DSP authority SHALL remain sole authority for that device operation. Credential configuration SHALL not create a device operation authority.

#### Scenario: New IP supersedes older pending actions

- **GIVEN** an older diagnostic lookup, credential lookup, fallback, or credential dialog is pending for IP A
- **WHEN** the operator changes input to IP B
- **THEN** the older binding is stale
- **AND** its result or confirmation cannot publish a model, mutate credentials, acquire a handler, submit work, change pages, or perform I/O

#### Scenario: Diagnostic and credential purposes do not cross-authorize

- **GIVEN** a current accepted diagnostic request model exists
- **WHEN** the operator activates `Пароль`
- **THEN** the credential action performs its own current IP/inventory resolution
- **AND** it does not reuse the diagnostic request model as credential authority

#### Scenario: Repeat action creates a new generation

- **GIVEN** one action of a purpose has started or completed
- **WHEN** the operator repeats that action
- **THEN** the application creates a distinct newer generation
- **AND** old lookup/dialog actions cannot affect the new context

#### Scenario: Lookup remains external-I/O-free

- **WHEN** the application resolves an IP from loaded inventory for either purpose
- **THEN** it uses only immutable in-memory query
- **AND** it does not load Excel, reread deployment JSON, ping, or perform device/network I/O on the GUI thread

### Requirement: Inventory dispatch ownership does not leak into dialogs, screens, handlers, or workers

`EquipmentInventory` SHALL return canonical records and multiplicity only. It SHALL NOT choose pages, lifecycle routes, fallback models, credential models, or UI outcomes.

The fallback dialog SHALL render safe reason/model choices and publish non-secret selection, confirmation, and cancellation intent only. It SHALL NOT query inventory, read/mutate credentials, acquire handlers, submit work, or perform network I/O.

The credential dialog SHALL receive one already accepted exact public model/IP context and publish credential confirm/cancel data to application composition. It SHALL NOT choose a model, query inventory, start diagnostics, ping, acquire handlers, submit workers/controllers, or perform device network I/O.

Diagnostic screens SHALL render accepted state and publish existing non-secret device intents. They SHALL NOT query inventory, interpret multiplicity, infer model support, choose another screen, or start another model lifecycle.

Controllers, handlers, sessions, and workers SHALL receive one already assigned exact model/IP diagnostic operation context through existing application wiring. They SHALL NOT receive complete IP-match tuples or candidate-model lists and SHALL NOT search inventory, analyze `source_model` or importer evidence, choose pages, iterate models, or switch models after authentication, transport, protocol, parser, timeout, or ambiguous-result failure.

#### Scenario: Assigned diagnostic lifecycle receives one model path

- **WHEN** application dispatch accepts an automatic or confirmed-fallback diagnostic model
- **THEN** the selected existing lifecycle receives only its exact model/IP and approved credential context
- **AND** no dialog, handler, or worker receives all inventory matches or alternative model candidates

#### Scenario: Device failure does not trigger model guessing

- **WHEN** the assigned diagnostic path reports authentication, transport, protocol, parser, timeout, or another device failure
- **THEN** existing retry and credential policies apply only within that exact model path
- **AND** no component retries with another diagnostic model

#### Scenario: PDU enrichment remains gated by accepted PDU success

- **GIVEN** diagnostic dispatch assigns Aten or PCS4i to the PDU page/controller
- **WHEN** the PDU diagnostic starts
- **THEN** related-room/codec enrichment does not start from dispatch alone
- **AND** it starts only after `PDUController` accepts a current successful user refresh under the modified exact-model enrichment contract

#### Scenario: Password action cannot start PDU enrichment

- **GIVEN** credential configuration resolves Aten or PCS4i
- **WHEN** the credential dialog opens, is cancelled, or saves candidate configuration
- **THEN** no PDU refresh or related-room/codec enrichment starts

### Requirement: Registered equipment pages render inventory switch connection fields

Every equipment page registered by the application equipment-page registry SHALL render exactly one inventory-backed row labelled `IP коммутатора` and exactly one inventory-backed row labelled `Порт коммутатора`.

The two rows SHALL be placed in that screen's existing device-information card. For the current registered pages, placement SHALL be:

```text
codec      -> Основная информация
matrix     -> Информация об устройстве
pdu        -> Информация об устройстве
audio_dsp  -> Информация об устройстве
```

The rows SHALL NOT be placed in a separate switch card, the shared non-PDU room block, the PDU related-room/codec section, a control section, a routing table, an outlet table, or another page-specific section.

The equipment-page registry SHALL remain the completeness authority. Tests SHALL enumerate every registered page, including PDU pages with dedicated room placement, and prove that each page receives the same two switch rows without relying on a manually maintained subset of screen classes.

Each row SHALL render the corresponding canonical inventory value for the current unique device record. Null or unavailable values SHALL render as `—`. The two fields SHALL be independent so a unique partial connection preserves the available switch IP or opaque switch-port text while the other row renders `—`.

Switch connection presentation SHALL remain informational and non-blocking. Missing inventory, invalid current IP, zero or multiple matching records, older snapshots with null-adapted switch fields, or null schema-v3 fields SHALL NOT open an automatic modal error, change the device request outcome, disable valid equipment controls, or prevent existing diagnostics.

#### Scenario: Codec page shows switch connection in existing information card

- **GIVEN** the current codec IP resolves to one schema-v3 equipment record with both switch fields
- **WHEN** the codec page becomes current
- **THEN** its existing `Основная информация` card shows `IP коммутатора` with the exact canonical switch IP
- **AND** it shows `Порт коммутатора` with the exact canonical opaque port text
- **AND** no separate switch card is created

#### Scenario: Matrix page shows switch connection in existing information card

- **GIVEN** the current Matrix IP resolves to one schema-v3 equipment record with switch connection data
- **WHEN** the Matrix page becomes current
- **THEN** its existing `Информация об устройстве` card contains both inventory-backed switch rows
- **AND** Matrix routing and device-observed information retain their existing authority

#### Scenario: PDU page is included despite dedicated room placement

- **GIVEN** the current PDU IP resolves to one schema-v3 equipment record with switch connection data
- **WHEN** the PDU page becomes current
- **THEN** its existing `Информация об устройстве` card contains both switch rows
- **AND** its dedicated `Комната и связанный кодек` section remains separate and unchanged

#### Scenario: Audio DSP page shows switch connection in existing information card

- **GIVEN** the current audio-DSP IP resolves to one schema-v3 equipment record with switch connection data
- **WHEN** the audio-DSP page becomes current
- **THEN** its existing `Информация об устройстве` card contains both inventory-backed switch rows
- **AND** meter rendering retains its existing authority

#### Scenario: Unique partial switch connection is displayed

- **GIVEN** the current device resolves to one record with exactly one non-null switch field
- **WHEN** its registered equipment page renders inventory context
- **THEN** the available canonical field is displayed exactly
- **AND** the unavailable field displays `—`
- **AND** the page does not infer or manufacture the missing value

#### Scenario: Switch connection is unavailable

- **WHEN** inventory is unavailable, the current IP is invalid, lookup returns zero or multiple records, or both canonical switch fields are null
- **THEN** both switch rows display `—`
- **AND** no automatic modal connection error is opened
- **AND** existing device diagnostics and controls remain available

#### Scenario: Registry coverage remains complete

- **WHEN** tests enumerate the application equipment-page registry
- **THEN** every current registered page exposes exactly one switch-IP row and one switch-port row in its existing information card
- **AND** repeated page activation or widget reconstruction does not duplicate either row

### Requirement: Switch connection presentation uses one application-owned inventory lifecycle

The application/composition layer SHALL own resolution, freshness, and publication of equipment-page switch connection presentation. Registered equipment screens SHALL remain rendering boundaries and SHALL NOT load or query inventory, interpret zero/one/many lookup outcomes, select an equipment record, decide stale-result acceptance, or derive switch values from device responses.

For a valid normalized current device IP, the application SHALL use the existing immutable inventory device-IP lookup. Exactly one matching record SHALL authorize display of that record's `switch_ip_address` and `switch_port` independently. Zero or multiple matching records SHALL authorize neither value. The application SHALL NOT break ambiguity by selected diagnostic model, `device_kind`, MAC, room, row order, non-null preference, or Qt presentation state.

The switch presentation SHALL be bound to current exact model, normalized IP, inventory snapshot identity or inventory-unavailable identity, registered page context, and an application-owned generation, or an equivalent complete immutable context. Changing any authoritative context SHALL invalidate prior presentation immediately. A delayed or queued publication SHALL render only when its complete binding and generation still match the current application context.

Current switch presentation SHALL be resolved and may be published without device network I/O. Preliminary reachability, credential resolution, handler acquisition, worker/controller submission, device refresh result/error/completion, interactive actions, PDU mutation, Matrix route, and audio polling SHALL NOT be switch-presentation authorities. They SHALL NOT overwrite inventory-backed values from device payloads, convert unavailable switch context into device failure, or restore an older inventory context.

When a screen reconstructs its information-row widgets, the shell MAY re-render the already accepted current inventory presentation into the new widgets. Re-rendering SHALL preserve the same current binding and SHALL NOT reclassify widget reconstruction as device or inventory authority.

#### Scenario: Switch context publishes without device success

- **GIVEN** the current model/IP/page and inventory snapshot resolve one device record
- **WHEN** that equipment context becomes current before any device request succeeds
- **THEN** the application publishes the record's switch connection presentation
- **AND** no handler, worker, controller, or switch network operation is required

#### Scenario: Ambiguous device IP is not narrowed

- **GIVEN** current inventory contains multiple records for the normalized device IP
- **WHEN** one record happens to match the selected model or has more complete switch fields
- **THEN** the application publishes neither record's switch values
- **AND** both rows remain unavailable
- **AND** model or completeness does not break ambiguity

#### Scenario: Current IP changes

- **GIVEN** switch values from one current device are visible
- **WHEN** the normalized IP context changes
- **THEN** the old values are invalidated immediately
- **AND** only a presentation resolved for the new current binding may be rendered

#### Scenario: Inventory snapshot changes

- **GIVEN** a current page displays switch values from one accepted inventory snapshot
- **WHEN** the application replaces that snapshot or inventory becomes unavailable
- **THEN** the old presentation is invalidated
- **AND** current values are resolved and published only from the new snapshot or unavailable context

#### Scenario: Stale publication is rejected

- **GIVEN** an older switch presentation was resolved for a prior model, IP, page, snapshot, or generation
- **WHEN** it reaches the rendering boundary after current context changed
- **THEN** the application rejects it
- **AND** it cannot restore old switch values

#### Scenario: Device request failure does not clear current switch context

- **GIVEN** current switch values have been accepted from inventory
- **WHEN** the device request fails, times out, or exhausts credentials
- **THEN** the current inventory-backed values remain visible
- **AND** the device failure retains its existing independent presentation

#### Scenario: Device payload cannot override inventory connection

- **GIVEN** a handler or worker result contains a similarly named IP, port, MAC, interface, or connection field
- **WHEN** the screen renders that device result
- **THEN** it does not replace `IP коммутатора` or `Порт коммутатора`
- **AND** only the application-owned canonical inventory presentation controls those rows

### Requirement: Codec page rebuild preserves shared inventory presentation boundaries

`CodecScreen` MAY reconstruct codec-owned information and control widgets when codec model context or diagnostic lifecycle requires it. The shell-owned `RoomInformationBlock` SHALL remain outside codec-owned deletion authority.

`CodecScreen.update_parameters_display()` SHALL remove and recreate only codec-owned widgets. It SHALL NOT hide, detach, or call `deleteLater()` on the shell-owned room block during normal reconstruction. A generic remove-all-then-reattach strategy SHALL NOT satisfy this requirement.

After every codec parameter-display rebuild used during model change, diagnostic startup, refresh, or equivalent current-page reconstruction, and after Qt has processed posted `QEvent.DeferredDelete` events, the codec page SHALL contain exactly one live shared `RoomInformationBlock` at the bottom of its equipment-page content. The screen's `shared_room_information_block` reference SHALL point to that exact live block.

The block SHALL show the current accepted room address, VIP state, and safe room status under the existing room-context lifecycle without waiting for codec network success. A hidden, detached, deleted, or pending-deletion block SHALL NOT be accepted as the current presentation target and SHALL NOT receive later publication.

The rebuild SHALL also leave exactly one `IP коммутатора` row and exactly one `Порт коммутатора` row in the codec's existing `Основная информация` card and SHALL render the current accepted switch presentation into those current row widgets.

A focused shell recovery path MAY attach a replacement block only when the previous block is genuinely missing or already deleted. Recovery SHALL clear stale references and SHALL NOT be the normal repair mechanism for codec reconstruction.

Repeated rebuilds SHALL NOT leave visible, hidden, detached, pending-deletion, or deleted duplicate room blocks or switch rows. Codec request start, success, failure, and completion SHALL remain independent from room and switch inventory publication authority.

#### Scenario: Real codec refresh preserves the shell-owned block

- **GIVEN** a current codec context has one live shell-owned room block with resolved address and VIP state
- **WHEN** normal diagnostic startup calls the codec parameter-display rebuild
- **THEN** codec reconstruction does not schedule that room block for deletion
- **AND** the same live block remains attached at the bottom
- **AND** no codec network success is required to keep it visible

#### Scenario: Deferred deletion cannot hide the defect

- **GIVEN** the real codec rebuild path has completed
- **WHEN** posted `QEvent.DeferredDelete` events and the Qt event loop are processed
- **THEN** exactly one live shared room block remains
- **AND** `shared_room_information_block` points to that block
- **AND** it shows the current address and VIP state
- **AND** no stale or pending-deletion block is accepted as current

#### Scenario: Real codec refresh rebuild keeps switch context

- **GIVEN** a current codec context has accepted switch IP and port presentation
- **WHEN** normal diagnostic startup reconstructs the codec information card
- **THEN** the reconstructed card contains exactly one switch row pair
- **AND** both rows show the current accepted inventory values
- **AND** device data clearing does not permanently erase them

#### Scenario: Repeated codec rebuild does not duplicate inventory widgets

- **WHEN** codec parameter display is rebuilt multiple times and deferred deletions are processed after each rebuild
- **THEN** the live codec page contains exactly one shared room block
- **AND** it contains exactly one `IP коммутатора` row and one `Порт коммутатора` row
- **AND** stale or deleted widgets cannot receive later publication

#### Scenario: Codec failure leaves inventory context visible

- **GIVEN** current room and switch presentation is visible after codec rebuild and deferred-deletion processing
- **WHEN** the codec diagnostic request fails
- **THEN** current room address, VIP state, switch IP, and switch port remain independently visible
- **AND** the codec request error does not clear or replace them

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

### Requirement: Modern operator toolbar does not expose the legacy global Debug control

The legacy global `Отладка` control SHALL NOT be visible as an operator toolbar control in the modern diagnostic interface. Its internal legacy implementation MAY remain for compatibility, but it is hidden from the visible toolbar.

This is a presentation-only visibility decision. It SHALL NOT change target authority, perform device I/O, choose credentials, acquire a handler/session, create a lifecycle/generation, or replace approved exact-row Debug presentation for individual device families. Theme, search, Password and top full Refresh semantics remain unchanged.

#### Scenario: Modern toolbar is rendered

- **WHEN** the modern diagnostic operator toolbar is rendered
- **THEN** no visible global `Отладка` control is present
- **AND** target-search, Password, top full Refresh and theme controls retain their existing semantics

#### Scenario: Family Debug remains independent

- **GIVEN** a device family has approved exact-row Debug presentation
- **WHEN** its current row/dashboard is rendered
- **THEN** the hidden global toolbar control does not replace or alter that family-specific Debug contract

### Requirement: Target-search visual label describes room and equipment IP input

The sole existing target-search `QLineEdit` SHALL have the visible label exactly `Введите название помещения или IP-адрес оборудования`. It remains the same one field for partial room-name search, IPv4 input, autocomplete, explicit selection, and top Refresh; no second input or model selector is introduced. Existing raw-query, selected-room, inventory-resolution, diagnostic-start, and Refresh authority remains unchanged. Placeholder and accessibility text MAY remain where they do not conflict with this visible-label contract. Rendering the label and field starts zero new I/O.

#### Scenario: Target search uses the descriptive visible label

- **WHEN** the main diagnostic window is constructed
- **THEN** the one persistent target-search field has visible label `Введите название помещения или IP-адрес оборудования`
- **AND** no visible field label exactly `IP-адрес` remains
- **AND** partial room-name search, IPv4 input, autocomplete, explicit selection, and top Refresh retain their existing behavior and authority
- **AND** constructing or rendering the label starts zero new I/O

### Requirement: Matrix route reconciliation targets the intended authoritative logical output

After a successful or uncertain Matrix route mutation, reconciliation SHALL query the specific logical output targeted by the intent using the active approved profile's read command. The controller SHALL NOT assume output `1` for a multi-output Matrix.

#### Scenario: CrossPoint output 7 mutation is reconciled independently
- **WHEN** a route mutation targets approved CrossPoint output `7`
- **THEN** reconciliation reads output `7` through the active CrossPoint route-query profile
- **AND** another output's route cannot confirm the mutation

### Requirement: Matrix capability context remains current-operation scoped

Exact model/frame identity, topology and profile selection used for validation/reconciliation SHALL belong to the current Matrix target/context. Deferred XTP/XTP II evidence SHALL NOT become current production capability authority in this change.

#### Scenario: Matrix target changes to deferred XTP
- **WHEN** the active Matrix target changes from a supported IN/DTP Matrix to XTP or XTP II evidence
- **THEN** old route/topology/profile authority is invalidated
- **AND** no production Matrix handler/session, route mutation, credential attempt, or topology I/O starts for the deferred target
- **AND** historical XTP parser state cannot restore support

### Requirement: Matrix GUI preserves canonical HDCP and temperature evidence

Both standalone and room Matrix presentations SHALL consume canonical
`input_hdcp[input_id]` as their input-HDCP authority. They SHALL present
`PRESENT_HDCP` as confirmed positive, `PRESENT_NO_HDCP` and `ABSENT` as
confirmed negative, and `UNKNOWN` or missing evidence as unavailable. Input
HDCP authorization and output HDCP SHALL NOT substitute for this state.
Successful current temperature evidence SHALL reach the existing Matrix
temperature field; unavailable current evidence SHALL render its established
empty state and SHALL NOT retain an earlier value or invent `0°C`.

#### Scenario: Canonical false HDCP is not displayed as unknown

- **GIVEN** canonical input states `PRESENT_HDCP`, `PRESENT_NO_HDCP`, `ABSENT`, and `UNKNOWN`
- **WHEN** each Matrix GUI table renders them
- **THEN** the visible room cells are respectively a filled green indicator, a neutral empty indicator, a neutral empty indicator, and a neutral non-positive indicator
- **AND** Qt semantic data/tooltips distinguish confirmed `PRESENT_NO_HDCP` and `ABSENT` from unavailable `UNKNOWN` data
- **AND** signal presence remains an independent column

#### Scenario: Current temperature reaches both Matrix surfaces

- **GIVEN** an accepted Matrix snapshot with `temperature=59`
- **WHEN** standalone and room Matrix presentation render it
- **THEN** each existing temperature field displays `59°C`
- **WHEN** a later current snapshot has unavailable temperature
- **THEN** the standalone field displays its empty state
