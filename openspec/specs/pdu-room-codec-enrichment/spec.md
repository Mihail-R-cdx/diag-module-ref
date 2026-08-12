# pdu-room-codec-enrichment Specification

## Purpose
TBD - created by archiving change pdu-room-codec-enrichment. Update Purpose after archive.
## Requirements
### Requirement: PDU lifecycle exposes accepted-refresh and supersession boundaries

The application SHALL start PDU-room-codec resolution only from a successful user PDU
refresh result already accepted as current by `PDUController`. The accepted trigger SHALL
carry immutable non-secret PDU generation/revision identity, accepted refresh operation
identity, model, IP address, and non-secret credential-context revision or equivalent token.

A PDU refresh performed as mutation reconciliation SHALL NOT start enrichment. Stale PDU
callbacks, PDU errors, progress/status callbacks, and completion without accepted success
SHALL NOT start enrichment.

Separately, the PDU lifecycle SHALL publish or invoke a focused non-secret supersession
boundary whenever the current PDU context is being replaced or invalidated. The exact event
or callback type is not normative, but it SHALL be equivalent to:

```text
PDUContextSuperseded(
    pdu_generation_or_revision,
    reason,
)
```

It SHALL occur no later than:

- selected PDU model change;
- selected PDU IP change;
- PDU credential-context change;
- start of a new user PDU refresh, including repeat Refresh for the same model/IP;
- explicit PDU context invalidation or deactivation;
- application shutdown.

The supersession boundary SHALL immediately invalidate active enrichment and its dedicated
related-codec lane, prevent old callbacks from updating UI or successful credential/profile
memory, and clear or reset the related-room presentation even when the replacement PDU
refresh later fails.

`PDUController` SHALL remain the sole owner of PDU context generation and refresh/mutation
lane authority. `VCSDiagnosticApp` SHALL only forward PDU-owned accepted/superseded lifecycle
facts and SHALL NOT create a second PDU generation authority or determine freshness by
reading Qt widgets.

Both boundaries SHALL exclude credentials, candidate lists, outlet data, complete device
results, handlers, workers, sessions, cookies, tokens, and transports.

#### Scenario: User PDU refresh is accepted

- **WHEN** a current user-initiated PDU refresh succeeds and is accepted by `PDUController`
- **THEN** application composition starts one new PDU-room-codec enrichment generation from the accepted non-secret PDU context
- **AND** accepted PDU data remains available independently of enrichment outcome

#### Scenario: Reconciliation refresh succeeds

- **GIVEN** a PDU mutation started a context-bound reconciliation refresh
- **WHEN** that reconciliation succeeds
- **THEN** PDU state may be reconciled through the existing PDU lifecycle
- **AND** no new room-codec enrichment generation is started

#### Scenario: New PDU refresh starts but later fails

- **GIVEN** room and codec data for PDU A are visible
- **WHEN** the operator starts a refresh for another PDU context and that new refresh later fails
- **THEN** PDU-context supersession invalidates the old enrichment immediately
- **AND** old room/codec data are cleared or reset before replacement success is known
- **AND** old related-codec work cannot continue as current or restore the old values

#### Scenario: Repeat Refresh uses the same PDU identity

- **GIVEN** related-codec work is pending for one accepted PDU refresh
- **WHEN** the operator starts repeat Refresh for the same PDU model/IP
- **THEN** the PDU lifecycle supersession boundary immediately invalidates the old enrichment
- **AND** a later accepted result may start a distinct new enrichment generation

### Requirement: Pure authoritative PDU and room resolution

The enrichment capability SHALL resolve the accepted PDU IP through the current immutable `EquipmentInventory` revision using indexed zero/one/many semantics. It SHALL use exact canonical fields and the exact model carried by the accepted current `PDUController` context. It SHALL NOT use fuzzy matching, source-model guessing, room-name fallback, `device_kind` as PDU identity, page key, record order, or first-match selection.

The resolver SHALL require exactly one total record from `find_by_ip(accepted_pdu_ip)`. It SHALL NOT reduce duplicate-IP ambiguity by filtering records by `device_kind`, diagnostic support, or page classification.

The accepted PDU context model SHALL be exactly one of this closed set:

```text
Aten PE8208AV
Extron IPL T PCS4i
```

For the one inventory record, canonical `diagnostic_model` SHALL be non-null, SHALL be in the same closed PDU set, and SHALL exactly equal the accepted PDU context model. The resolver SHALL NOT require `device_kind == "pdu"`; a correct Aten or PCS4i record with `device_kind = other` remains eligible. After exact model agreement, the record SHALL have a non-null authoritative `room_id`.

Resolution SHALL distinguish:

```text
INVENTORY_UNAVAILABLE
PDU_NOT_FOUND
AMBIGUOUS_PDU_IP
PDU_MODEL_UNSUPPORTED
PDU_MODEL_MISMATCH
ROOM_UNRESOLVED
```

`PDU_MODEL_UNSUPPORTED` SHALL mean that the model in the accepted `PDUController` context is absent from the closed PDU set. `PDU_MODEL_MISMATCH` SHALL mean that exactly one IP record exists but its canonical `diagnostic_model` is null, outside the closed PDU set, or not exactly equal to the accepted context model.

Both model failures SHALL stop before room-codec credential resolution, handler/session construction, worker submission, or network I/O. The pure resolver SHALL perform no Qt access, credential work, handler/session construction, worker submission, or network I/O.

#### Scenario: PDU IP is absent

- **WHEN** the inventory returns zero records for the accepted PDU IP
- **THEN** resolution is `PDU_NOT_FOUND`
- **AND** no codec credential or network work starts

#### Scenario: PDU IP has duplicate assignments

- **WHEN** the inventory returns more than one total record for the accepted PDU IP
- **THEN** resolution is `AMBIGUOUS_PDU_IP`
- **AND** no record is filtered, preferred, deduplicated, or selected by kind or model

#### Scenario: One PDU and one non-PDU share the IP

- **WHEN** IP lookup returns one record whose model matches the accepted PDU context and one additional record
- **THEN** resolution remains `AMBIGUOUS_PDU_IP`
- **AND** the matching record is not selected merely because its model or page is familiar

#### Scenario: Accepted PDU model is unsupported

- **GIVEN** the accepted current PDU context carries a model outside `Aten PE8208AV` and `Extron IPL T PCS4i`
- **WHEN** enrichment resolution begins
- **THEN** resolution is `PDU_MODEL_UNSUPPORTED`
- **AND** no inventory record is treated as a PDU by `device_kind`, page key, or source text
- **AND** no related-codec credential or network work starts

#### Scenario: Exact Aten context matches an Aten inventory record of kind other

- **GIVEN** the accepted current PDU context model is exactly `Aten PE8208AV`
- **AND** exactly one inventory record matches the accepted PDU IP
- **AND** that record has `diagnostic_model = Aten PE8208AV`
- **AND** that record has `device_kind = other`
- **WHEN** enrichment resolves PDU identity
- **THEN** exact PDU model validation succeeds
- **AND** `device_kind = other` does not block room resolution

#### Scenario: Exact PCS4i context matches a PCS4i inventory record of kind other

- **GIVEN** the accepted current PDU context model is exactly `Extron IPL T PCS4i`
- **AND** exactly one inventory record matches the accepted PDU IP
- **AND** that record has `diagnostic_model = Extron IPL T PCS4i`
- **AND** that record has `device_kind = other`
- **WHEN** enrichment resolves PDU identity
- **THEN** exact PDU model validation succeeds
- **AND** room resolution may continue

#### Scenario: Inventory model differs from accepted PDU model

- **GIVEN** exactly one inventory record matches the accepted PDU IP
- **AND** the accepted context model and inventory `diagnostic_model` are different exact values
- **WHEN** enrichment resolves PDU identity
- **THEN** resolution is `PDU_MODEL_MISMATCH`
- **AND** no room-codec credential or network work starts

#### Scenario: Inventory PDU model is null or unsupported

- **GIVEN** exactly one inventory record matches the accepted PDU IP
- **AND** its canonical `diagnostic_model` is null or outside the closed PDU set
- **WHEN** enrichment resolves PDU identity
- **THEN** resolution is `PDU_MODEL_MISMATCH`
- **AND** the resolver does not guess from `device_kind`, `source_model`, or page classification
- **AND** no room-codec credential or network work starts

#### Scenario: Exact IP record is not a PDU

- **GIVEN** accepted model and the one inventory record's exact `diagnostic_model` agree in the closed PDU set
- **WHEN** the inventory record has any canonical `device_kind`, including `other` or `pdu`
- **THEN** PDU identity remains established by exact model agreement
- **AND** the resolver does not emit a kind-mismatch outcome

#### Scenario: PDU has no authoritative room ID

- **GIVEN** the accepted PDU model and one inventory record match exactly
- **WHEN** that record has `room_id = null`
- **THEN** resolution is `ROOM_UNRESOLVED`
- **AND** `room_name` is not substituted as identity

#### Scenario: Inventory is unavailable

- **WHEN** composition has no validated inventory revision
- **THEN** resolution is `INVENTORY_UNAVAILABLE`
- **AND** only the existing safe load category/message is exposed
- **AND** accepted PDU diagnostics continue to function independently

### Requirement: Exact related-codec candidate resolution

After exact PDU and room resolution, the application SHALL query
`find_by_room_and_kind(room_id, "video_codec")` and preserve zero/one/many multiplicity. It
SHALL require exactly one codec record with usable canonical IP and exact supported VCS
`diagnostic_model`.

Codec resolution SHALL distinguish:

```text
CODEC_NOT_FOUND
AMBIGUOUS_CODEC
CODEC_IP_MISSING
CODEC_UNSUPPORTED
RESOLVED
```

The application SHALL NOT select `codecs[0]`, infer a primary codec, use source row order,
use `source_model` as dispatch authority, or diagnose all candidates when more than one codec
exists.

#### Scenario: Room has no codec record

- **WHEN** the authoritative room lookup returns zero `video_codec` records
- **THEN** codec resolution is `CODEC_NOT_FOUND`
- **AND** no codec credentials or network session are acquired

#### Scenario: Room has multiple codec records

- **WHEN** the authoritative room lookup returns more than one `video_codec` record
- **THEN** codec resolution is `AMBIGUOUS_CODEC`
- **AND** no record is selected by position, model preference, or IP order
- **AND** no codec network operation starts

#### Scenario: Exact codec has no IP

- **WHEN** one codec record has `ip_address = null`
- **THEN** codec resolution is `CODEC_IP_MISSING`
- **AND** no codec network operation starts

#### Scenario: Exact codec is unsupported

- **WHEN** one codec record has null or unsupported `diagnostic_model`
- **THEN** codec resolution is `CODEC_UNSUPPORTED`
- **AND** safe source model information may be displayed
- **AND** no handler or protocol is guessed from source text

#### Scenario: Exact codec is usable

- **WHEN** one codec record has canonical IP and supported VCS `diagnostic_model`
- **THEN** codec resolution is `RESOLVED`
- **AND** that exact record/model/IP is bound to the inventory snapshot and accepted PDU context

### Requirement: Room display evidence does not replace room identity

Resolved room context SHALL use `room_id` as authority. `room_name` SHALL be optional display
evidence derived from every record indexed under that room ID. Zero non-null names yields no
display name. One distinct non-null name MAY be displayed. Multiple distinct names SHALL
produce no selected authoritative name plus a safe `ROOM_NAME_CONFLICT` warning while codec
resolution continues by `room_id`.

#### Scenario: Room names conflict

- **WHEN** one authoritative room ID has multiple distinct non-null room names
- **THEN** no one name is selected as authoritative
- **AND** `ROOM_NAME_CONFLICT` is exposed safely
- **AND** codec resolution continues by room ID

### Requirement: Independent bounded related-codec status lifecycle

A resolved related codec SHALL be read through a dedicated application-owned serialized
read-only session lane independent from generic codec refresh and the
`CodecScreen.interactive_controller` instance.

The related-codec lane SHALL NOT replace or participate in generic `_active_request`, global
`current_worker`, selected codec widgets, current screen selection, generic codec progress
UI, or user codec terminal UI. It SHALL NOT invalidate, reuse, or change the handler/session
owned by `CodecScreen.interactive_controller`.

The lane SHALL reuse existing supported model handlers, profile ordering, structured failure
classification, and bounded read-only recovery. All codec network I/O SHALL execute outside
the Qt GUI thread.

#### Scenario: User works with codec A while PDU resolves codec B

- **GIVEN** the user codec screen owns an interactive context for codec A
- **AND** PDU enrichment resolves codec B
- **WHEN** codec B status is read
- **THEN** an independent related-codec session context is used
- **AND** codec A generation, handler, controls, callbacks, and selected widgets remain unchanged

#### Scenario: Related-codec read is slow

- **WHEN** related-codec connection or status reading blocks
- **THEN** it runs on the dedicated background lane
- **AND** the Qt GUI thread remains responsive

### Requirement: Every enrichment generation forces dedicated session rollover

Every accepted user PDU refresh that starts enrichment SHALL create a new immutable
enrichment generation and operation identity, including repeat Refresh for the same PDU and
the same resolved codec.

The dedicated related-codec session SHALL be invalidated before activating the session
context for every new enrichment generation. This invalidation is mandatory even when codec
model, codec IP, credential identities, starting credential index, and saved connection
profile are unchanged.

A compliant sequence is:

```text
publish new enrichment generation
    -> dedicated_session.invalidate_context()
    -> resolve codec and credential/profile context
    -> dedicated_session.activate_context(...)
    -> submit read-only status operation
```

An equivalent force-rollover API or inclusion of enrichment generation in private session
identity MAY be used, but it SHALL prove the same pre-I/O behavior. Calling the current
`activate_context()` with equal prospective identity without prior invalidation or equivalent
force rollover SHALL NOT be compliant.

Queued work SHALL check both captured session generation and enrichment generation before
handler acquisition and again before first network I/O when separable. Stale queued work
SHALL perform zero handler factory/acquisition calls and zero network I/O. In-flight stale
callbacks SHALL update neither presentation nor credential/profile memory.

Background currentness SHALL NOT depend on reading Qt widgets.

#### Scenario: Same-identity repeat refresh supersedes queued work before I/O

- **GIVEN** an old related-codec status operation is queued
- **AND** repeat PDU Refresh resolves the same codec model/IP with the same credential chain, starting index, and saved profile
- **WHEN** the new enrichment generation is activated
- **THEN** the dedicated session generation is forcibly rolled over before new activation
- **AND** the old queued operation is dropped before handler factory/acquisition
- **AND** the old operation performs zero network I/O

#### Scenario: Queued work becomes stale for another reason

- **WHEN** PDU context, relevant credentials, inventory revision, or shutdown supersedes queued related-codec work
- **THEN** the work is dropped before handler acquisition and first network I/O
- **AND** it opens no transport and sends no device request

#### Scenario: Related-codec I/O is already in flight

- **WHEN** old network I/O is in flight when enrichment is superseded
- **THEN** its result, error, completion, credential index, and connection profile cannot update the current context
- **AND** resources are cleaned up on their owning lane

### Requirement: Related-codec status normalization

For a successfully resolved and connected supported VCS codec, the capability SHALL produce
narrow normalized status containing at least:

```text
call_status
presentation_status
```

Existing handler status methods and parser logic SHALL be reused where available. Complete
raw model-specific status SHALL remain behind a focused adapter or equivalent boundary and
SHALL NOT be sent to PDU presentation.

An unavailable authoritative field SHALL be represented as unavailable/unknown and SHALL NOT
be inferred from unrelated text or successful connection alone.

#### Scenario: Related codec status is available

- **WHEN** an existing codec handler returns authoritative status and normalization succeeds
- **THEN** accepted enrichment contains normalized call and presentation status
- **AND** complete raw handler status is not exposed to `PDUScreen`

#### Scenario: Status cannot be normalized

- **WHEN** a supported codec response cannot be interpreted under the reviewed adapter contract
- **THEN** diagnostics reports structured protocol/unavailable outcome
- **AND** no fabricated status is reported

### Requirement: Related-codec credential and transport policy remains application-owned

Application composition SHALL resolve the complete codec credential candidate chain before
handler/session construction. One assigned credential SHALL be used across all supported
transport attempts. A supported saved profile SHALL be tried first.

Credential advancement SHALL occur only after a structured confirmed new-login
`AuthenticationError`. Transport, protocol, established-session invalidation, malformed
response, empty result, or text containing `auth`, `401`, or `403` SHALL NOT authorize
credential advancement. Candidate movement SHALL be monotonic without wrap-around. Handlers,
adapters, and session workers SHALL NOT inspect or iterate candidate chains.

Successful exact model/IP credential index and connection profile SHALL be persisted only
after accepted current final status success. Stale, partial, resolution-only, unsupported, or
failed outcomes SHALL persist nothing.

At most one reconnect cycle and one read-only replay are permitted. Recovery SHALL not
recurse.

#### Scenario: Transport fallback is available

- **WHEN** one supported transport fails without structured authentication rejection
- **AND** another supported transport remains
- **THEN** the next transport uses the same assigned credential
- **AND** credential index does not advance

#### Scenario: Stale success returns

- **WHEN** a codec operation succeeds after its enrichment generation is superseded
- **THEN** its credential index/profile are not persisted
- **AND** its status is not rendered

### Requirement: Composite enrichment outcome preserves PDU success

Inventory/room/codec resolution SHALL remain separate from codec diagnostic execution. The
accepted non-secret presentation model SHALL contain current context, resolution status,
optional room/codec context, safe warnings, codec diagnostic status, optional call and
presentation values, and optional safe message.

Codec diagnostic status SHALL distinguish states equivalent to:

```text
NOT_STARTED
PENDING
SUCCESS
AUTHENTICATION_FAILED
TRANSPORT_FAILED
PROTOCOL_FAILED
UNAVAILABLE
```

Inventory or codec enrichment failure SHALL NOT convert accepted PDU diagnostics into a PDU
authentication, connection, request, or mutation failure. It SHALL NOT clear accepted PDU
device/outlet data, change PDU lane authority, disable otherwise valid controls, or open an
automatic modal error dialog.

#### Scenario: PDU succeeds but inventory has no match

- **WHEN** PDU diagnostics succeeds and resolution is `PDU_NOT_FOUND`
- **THEN** accepted PDU data and controls remain available
- **AND** the inline section shows not found
- **AND** codec diagnostics remains `NOT_STARTED`

#### Scenario: PDU succeeds but codec connection fails

- **WHEN** PDU diagnostics succeeds, resolution is `RESOLVED`, and codec transport fails
- **THEN** accepted PDU data remains successful and usable
- **AND** the inline section reports `TRANSPORT_FAILED`
- **AND** no generic modal connection error is shown automatically

#### Scenario: Related codec status succeeds

- **WHEN** current resolution is `RESOLVED` and the current read succeeds
- **THEN** codec diagnostics is `SUCCESS`
- **AND** normalized values render only for that exact current PDU/room/codec context

### Requirement: Related-codec resources have explicit lifecycle cleanup

The application SHALL invalidate and close the dedicated related-codec handler/session on terminal failure, PDU-context supersession, relevant credential change, inventory replacement, and application shutdown. Cleanup SHALL run on the execution lane that owns network/session resources and SHALL be idempotent or exactly once. The Qt GUI thread SHALL NOT block on network cleanup.

For a resolved related codec outside `CloudLink Bar 310` and `CloudLink Box 310`, terminal status success SHALL retain the existing behavior: it SHALL invalidate/close the dedicated related-codec handler/session after accepted status publication.

For exact `CloudLink Bar 310` or `CloudLink Box 310`, accepted initial related-codec status success SHALL be terminal only for the initial status operation and SHALL NOT by itself close the dedicated session while live microphone metering remains current. The same dedicated session context MAY remain active solely for the approved serialized read-only meter lifecycle. It SHALL be closed when the meter context is superseded, when a typed failure makes the session unusable after approved bounded recovery, when relevant credential or inventory context changes, when explicit PDU/enrichment invalidation occurs, or when the application shuts down.

An endpoint-local unavailable or malformed microphone sample on an otherwise usable session SHALL NOT require session teardown; the next scheduled sample may reuse the current dedicated session. This exception SHALL NOT weaken cleanup for authentication rejection, established-session invalidation, transport/session failure, stale context, or shutdown.

#### Scenario: Application closes during related-codec work

- **WHEN** application shutdown supersedes related-codec work
- **THEN** enrichment and dedicated session contexts are invalidated immediately
- **AND** resource cleanup runs on the owning lane
- **AND** later callbacks cannot update destroyed or superseded UI state

#### Scenario: Non-CloudLink status succeeds

- **WHEN** a resolved related codec outside Bar 310 and Box 310 completes accepted status successfully
- **THEN** its dedicated related-codec handler/session is cleaned up under the existing one-shot lifecycle
- **AND** no live microphone-meter work remains

#### Scenario: CloudLink status succeeds and meter continues

- **GIVEN** exact related-codec model is Bar 310 or Box 310
- **WHEN** initial related-codec status succeeds and the enrichment generation remains current
- **THEN** the dedicated session is not closed merely because initial status succeeded
- **AND** it remains available only for the approved serialized live-meter lifecycle

#### Scenario: CloudLink meter context is superseded

- **GIVEN** a CloudLink related-codec session remains open for live metering
- **WHEN** PDU context, codec credential context, inventory context, explicit invalidation, or shutdown supersedes it
- **THEN** meter authority is invalidated immediately
- **AND** session cleanup runs on the owning background lane
- **AND** no later sample can update current presentation

### Requirement: PDU room block emphasizes VIP state

After an accepted current PDU refresh resolves room context, the PDU page SHALL render the room VIP state as the first room-context line above the existing room-characteristics and related-codec information.

When current exact related-codec resolution selects `CloudLink Bar 310` or `CloudLink Box 310`, the optional `Уровень микрофонов` live-meter row SHALL be the top overall line of the `Комната и связанный кодек` section and the VIP line SHALL appear immediately below it as the first room-context line. For all other related-codec states, the hidden/absent meter SHALL leave VIP as the top visible room-context line under the existing layout.

VIP presentation SHALL distinguish exactly:

```text
VIP: ДА
VIP: НЕТ
VIP: НЕТ ДАННЫХ
VIP: КОНФЛИКТ ДАННЫХ
```

`VIP: ДА` SHALL receive visually prominent treatment so that it is immediately noticeable after refresh. Visual emphasis SHALL not change lifecycle, focus, accessibility, or device-control authority.

The existing PDU room and related-codec block SHALL otherwise retain its approved behavior. VIP resolution SHALL use the shared equipment room-context contract and SHALL not create a second independent room-identity algorithm. Live microphone metering SHALL NOT become room-identity or VIP authority.

#### Scenario: Accepted PDU refresh resolves a VIP room

- **GIVEN** a current accepted PDU refresh succeeds
- **AND** the exact PDU inventory record resolves to a room with consistent VIP=true evidence
- **WHEN** PDU enrichment presentation is rendered
- **THEN** the first room-context line is `VIP: ДА`
- **AND** it is visually prominent
- **AND** the existing room and related-codec details remain available below it

#### Scenario: VIP room has a supported CloudLink related codec

- **GIVEN** current enrichment resolves a VIP room and exact Bar 310 or Box 310 related codec
- **WHEN** the related-codec section is rendered
- **THEN** `Уровень микрофонов` is the top overall row
- **AND** `VIP: ДА` is immediately below it as the first room-context row
- **AND** VIP remains visually prominent

#### Scenario: VIP evidence conflicts

- **GIVEN** the PDU room contains conflicting non-null VIP evidence
- **WHEN** PDU room presentation is rendered
- **THEN** it shows `VIP: КОНФЛИКТ ДАННЫХ`
- **AND** it does not select one record's value
- **AND** accepted PDU device data and controls remain valid

### Requirement: PDU VIP presentation follows enrichment supersession

Starting a new or repeated PDU refresh, changing PDU model/IP/credential context, explicit invalidation, or shutdown SHALL clear or supersede the previously rendered VIP state at the same boundary as the existing PDU room enrichment.

A stale enrichment result SHALL NOT restore an old VIP value, room address, or related-codec presentation. VIP lookup failure SHALL remain optional contextual-diagnostic failure and SHALL NOT convert accepted PDU success into PDU failure, trigger PDU retry, or open an automatic modal connection error.

#### Scenario: Repeat refresh supersedes prior VIP state

- **GIVEN** a VIP value from an earlier accepted PDU refresh is visible
- **WHEN** a repeat refresh begins
- **THEN** the earlier VIP presentation is invalidated immediately
- **AND** only the result bound to the new refresh generation may be rendered

### Requirement: PDU related-codec enrichment may continue CloudLink live microphone metering

After exact PDU/room/related-codec resolution and successful initial related-codec status normalization, `PDURoomCodecEnrichmentController` or an equivalent focused application-owned enrichment boundary SHALL continue live microphone metering only when the exact resolved related codec is:

```text
CloudLink Bar 310
CloudLink Box 310
```

The PDU meter SHALL use the same model-specific extraction, zero/unavailable distinction, fixed display ceiling of `20`, and one-second serialized cadence defined by the `cloudlink-live-microphone-metering` capability.

The existing dedicated related-codec serialized read-only session lane SHALL remain independent from generic codec refresh and from `CodecScreen.interactive_controller`. For a supported CloudLink related codec, the initial call/presentation status operation and subsequent microphone samples SHALL use the same current dedicated related-codec session context rather than opening a second simultaneous PDU-related CloudLink session solely for the meter.

Initial status success SHALL set the existing codec diagnostic status to `SUCCESS` and publish call/presentation data under the existing contract. Live-meter availability SHALL be an independent optional presentation field and SHALL NOT change `codec_diagnostic_status`, erase accepted call/presentation values, or change accepted PDU success.

An endpoint-local unavailable/malformed meter sample on an otherwise usable session SHALL affect only the meter for that cycle and SHALL allow the next scheduled sample. A typed session/transport/authentication failure SHALL use existing bounded read-only recovery and credential policy; meter recovery SHALL NOT become an unbounded one-second reconnect/login loop and meter success SHALL NOT persist credential/profile memory.

The live meter SHALL remain bound to the exact current enrichment generation, PDU accepted-refresh identity, inventory/room/codec resolution, codec model/IP, and codec credential-context revision. PDU supersession, relevant credential change, inventory replacement, explicit invalidation, or shutdown SHALL invalidate meter authority immediately. Queued stale sample work SHALL be rejected before handler acquisition and network I/O where applicable, and stale callbacks SHALL update neither PDU presentation nor credential/profile memory.

For a resolved related codec outside the two supported CloudLink models, no live-meter loop SHALL start and existing one-shot related-codec status behavior SHALL remain unchanged.

#### Scenario: PDU resolves Bar 310

- **GIVEN** an accepted current PDU refresh resolves exactly one `CloudLink Bar 310`
- **WHEN** initial related-codec status succeeds
- **THEN** codec diagnostic status becomes `SUCCESS`
- **AND** the same dedicated related-codec session context remains current for serialized one-second microphone samples
- **AND** no second simultaneous PDU-related CloudLink session is opened solely for the meter

#### Scenario: One PDU meter sample is unavailable

- **GIVEN** accepted related-codec call/presentation status is already visible
- **WHEN** one sample has an endpoint-local unsuccessful or malformed payload while the session remains usable
- **THEN** only the microphone meter becomes unavailable for that cycle
- **AND** PDU data, codec diagnostic `SUCCESS`, call status, and presentation status remain accepted
- **AND** the next scheduled sample may run

#### Scenario: PDU resolves unsupported related codec

- **WHEN** exact related-codec resolution selects a supported VCS model other than `CloudLink Bar 310` or `CloudLink Box 310`
- **THEN** no CloudLink microphone-meter polling starts
- **AND** existing one-shot related-codec status cleanup remains authoritative

#### Scenario: Repeat PDU refresh supersedes live metering

- **GIVEN** live microphone samples are being accepted for one enrichment generation
- **WHEN** repeat PDU Refresh starts, including for the same PDU and same related codec
- **THEN** the old meter authority is invalidated immediately
- **AND** queued old sample work performs no new handler acquisition or network I/O
- **AND** old callbacks cannot restore the prior meter

### Requirement: PDU related-codec block renders the CloudLink meter as its top row

When exact current related-codec resolution selects `CloudLink Bar 310` or `CloudLink Box 310`, the existing PDU `Комната и связанный кодек` section SHALL render exactly one row labelled `Уровень микрофонов` as the top overall row in the section.

The row SHALL contain a horizontal live meter with no numeric text overlay and the same available/unavailable presentation semantics as the codec-page CloudLink meter. The existing VIP row SHALL appear immediately below it and SHALL remain the first room-context row.

Before supported related-codec resolution is established, and for resolved related codecs outside the two supported CloudLink models, the meter row SHALL be hidden. Hiding the unsupported meter SHALL NOT reorder, remove, or change the semantics of existing room/codec rows.

PDU enrichment reset/supersession SHALL immediately clear or hide the old meter at the same authoritative boundary that clears the existing related-room/codec presentation. A stale sample SHALL NOT restore a bar value after supersession.

#### Scenario: Supported CloudLink related codec is resolved

- **WHEN** current PDU enrichment resolves exact `CloudLink Box 310`
- **THEN** `Уровень микрофонов` is the first overall row in `Комната и связанный кодек`
- **AND** `VIP` is immediately below it as the first room-context row

#### Scenario: Related codec does not support the meter

- **WHEN** current related-codec resolution selects another supported codec model
- **THEN** the microphone-meter row is hidden
- **AND** the existing room and related-codec presentation remains available
