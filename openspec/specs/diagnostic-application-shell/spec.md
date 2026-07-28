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
The main window SHALL expose only device models wired into `device_to_screen`
as selectable diagnostic targets and SHALL route each target to its configured
codec, matrix, PDU, or audio-DSP screen. A refresh request SHALL reject an
empty or malformed IPv4 address and SHALL stop before starting a device worker
when preliminary reachability validation fails.

#### Scenario: Valid supported device refresh
- **WHEN** an operator selects a mapped device, enters a valid reachable IPv4 address, and refreshes
- **THEN** the matching screen is selected, enters loading state, and the device-specific refresh path starts

#### Scenario: Invalid refresh input
- **WHEN** the IP field is empty, malformed, or fails preliminary reachability validation
- **THEN** the application displays a warning and does not start a diagnostic worker

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
`MatrixScreen` SHALL be a Matrix UI boundary that renders Matrix data and
publishes non-secret user intents. It SHALL NOT own credential candidate
selection, credential indexes, handler acquisition, persistent handler/session
state, transport lifecycle, retry policy, credential fallback, keepalive, or
direct Matrix network I/O.

Matrix route and refresh user actions SHALL cross the screen boundary as
non-secret intent or callback data. Qt signals or callbacks from
`MatrixScreen` SHALL NOT carry credential values, credential candidate lists,
handler objects, session objects, transport objects, cookies/tokens, or other
secret/session material.

#### Scenario: Route click emits intent only
- **WHEN** the operator clicks a Matrix routing cell
- **THEN** `MatrixScreen` publishes a route intent for the selected Matrix input/output context
- **AND** it does not call `ExtronIN1804Handler.set_connection()` directly
- **AND** it does not acquire or reuse a handler/session object

#### Scenario: Quick refresh is not screen-owned network I/O
- **WHEN** Matrix route status needs to be refreshed after a route action
- **THEN** `MatrixScreen` requests or receives the update through the Matrix application boundary
- **AND** it does not call `ExtronIN1804Handler.get_connections()` directly

#### Scenario: Screen does not own credentials
- **WHEN** a Matrix route or refresh intent is submitted
- **THEN** `MatrixScreen` does not read or mutate credential candidate lists or successful credential indexes
- **AND** credential ownership remains outside the screen boundary

#### Scenario: Screen signal payloads are secret-free
- **WHEN** `MatrixScreen` emits a route or refresh signal/callback
- **THEN** the payload contains no credential values, credential candidate lists, handler objects, session objects, cookies, tokens, or transport objects

#### Scenario: Rendering remains screen-owned
- **WHEN** the active Matrix controller accepts current Matrix data
- **THEN** `MatrixScreen` remains responsible for rendering the routing table, current connection, signal/HDCP indicators, and device information

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
