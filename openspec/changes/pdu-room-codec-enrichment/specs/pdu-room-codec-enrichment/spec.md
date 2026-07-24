## ADDED Requirements

### Requirement: Accepted user PDU refresh starts focused enrichment

The application SHALL start PDU-room-codec enrichment only from a successful PDU refresh
result that has already been accepted as current by the PDU application lifecycle boundary.
The trigger SHALL carry an immutable non-secret PDU context containing the PDU request or
generation identity, accepted refresh operation identity, model, IP address, and non-secret
credential-context revision or equivalent freshness token.

A PDU refresh performed as reconciliation for an accepted state-changing PDU operation SHALL
NOT start room-codec enrichment. A stale PDU result, a PDU error, progress/status callback,
or completion without accepted success SHALL NOT start enrichment.

`PDUController` SHALL remain responsible only for PDU lifecycle and accepted trigger
publication. It SHALL NOT load or query inventory, resolve a room, select a codec, resolve
codec credentials, create a codec session, or perform codec network I/O.

#### Scenario: User PDU refresh is accepted

- **WHEN** a current user-initiated PDU refresh succeeds and is accepted by `PDUController`
- **THEN** application composition starts one new PDU-room-codec enrichment generation from the accepted non-secret PDU context
- **AND** accepted PDU data remains available independently of the enrichment outcome

#### Scenario: Reconciliation refresh succeeds

- **GIVEN** a PDU mutation has started a context-bound reconciliation refresh
- **WHEN** that reconciliation refresh succeeds
- **THEN** the PDU state may be reconciled through the existing PDU lifecycle
- **AND** no new PDU-room-codec enrichment generation is started

#### Scenario: Stale PDU refresh returns

- **WHEN** a superseded PDU refresh emits result, error, or completion
- **THEN** it does not start or replace room-codec enrichment

### Requirement: Pure authoritative PDU and room resolution

The enrichment capability SHALL resolve the accepted PDU IP through the current immutable
`EquipmentInventory` revision using its indexed zero/one/many query contract. Resolution
SHALL use exact canonical fields and SHALL NOT use source-model guessing, fuzzy matching,
room-name fallback, record order, or first-match selection.

The resolver SHALL require exactly one total record from `find_by_ip(pdu_ip)`. It SHALL NOT
reduce duplicate-IP ambiguity by filtering the returned collection to PDU records. The one
record SHALL have `device_kind == "pdu"` and a non-null authoritative `room_id`.

Resolution SHALL classify outcomes using machine-readable states equivalent to:

```text
INVENTORY_UNAVAILABLE
PDU_NOT_FOUND
AMBIGUOUS_PDU_IP
PDU_KIND_MISMATCH
ROOM_UNRESOLVED
```

The resolver SHALL be a pure non-network component with no Qt widget access, credential
resolution, handler/worker/session construction, or network I/O.

#### Scenario: PDU IP is absent

- **WHEN** the current inventory returns zero records for the accepted PDU IP
- **THEN** enrichment resolution is `PDU_NOT_FOUND`
- **AND** no room or codec network operation starts

#### Scenario: PDU IP has duplicate assignments

- **WHEN** the current inventory returns more than one total record for the accepted PDU IP
- **THEN** enrichment resolution is `AMBIGUOUS_PDU_IP`
- **AND** the resolver does not select, filter, deduplicate, or prefer one record

#### Scenario: One PDU and one non-PDU share the IP

- **WHEN** an IP lookup returns exactly one canonical PDU record and one record of another kind
- **THEN** enrichment resolution remains `AMBIGUOUS_PDU_IP`
- **AND** the PDU record is not selected merely because its device kind matches the expected kind

#### Scenario: Exact IP record is not a PDU

- **WHEN** an IP lookup returns exactly one record whose `device_kind` is not `pdu`
- **THEN** enrichment resolution is `PDU_KIND_MISMATCH`
- **AND** no room-codec selection or codec network operation starts

#### Scenario: PDU has no authoritative room ID

- **WHEN** the one canonical PDU record has `room_id = null`
- **THEN** enrichment resolution is `ROOM_UNRESOLVED`
- **AND** `room_name` is not used as substitute room identity

#### Scenario: Inventory is unavailable

- **WHEN** application composition has no successfully loaded immutable inventory revision
- **THEN** enrichment resolution is `INVENTORY_UNAVAILABLE`
- **AND** it carries only the existing safe inventory-load category/message
- **AND** existing PDU diagnostics continue to function

### Requirement: Exact related-codec candidate resolution

After exact PDU and room resolution, the application SHALL query the inventory for
`(room_id, "video_codec")` and preserve result multiplicity. It SHALL require exactly one
canonical video-codec record with a usable canonical IP address and an exact
`diagnostic_model` supported by the application's VCS codec diagnostic set.

Codec resolution SHALL classify outcomes using machine-readable states equivalent to:

```text
CODEC_NOT_FOUND
AMBIGUOUS_CODEC
CODEC_IP_MISSING
CODEC_UNSUPPORTED
RESOLVED
```

The application SHALL NOT select `codecs[0]`, use source row order, use `source_model` as
runtime dispatch authority, infer a primary codec, or diagnose every candidate when the
room contains multiple codec records.

#### Scenario: Room has no codec record

- **WHEN** the authoritative room lookup returns zero `video_codec` records
- **THEN** codec resolution is `CODEC_NOT_FOUND`
- **AND** no codec credentials or network session are acquired

#### Scenario: Room has multiple codec records

- **WHEN** the authoritative room lookup returns more than one `video_codec` record
- **THEN** codec resolution is `AMBIGUOUS_CODEC`
- **AND** no record is selected by position, model preference, IP order, or first match
- **AND** no codec network operation starts

#### Scenario: Exact codec has no IP

- **WHEN** the room contains exactly one `video_codec` record with `ip_address = null`
- **THEN** codec resolution is `CODEC_IP_MISSING`
- **AND** no codec network operation starts

#### Scenario: Exact codec has no supported diagnostic model

- **WHEN** the room contains exactly one `video_codec` record whose `diagnostic_model` is null or is not a supported VCS codec model
- **THEN** codec resolution is `CODEC_UNSUPPORTED`
- **AND** the application may display its safe source model as inventory information
- **AND** it does not guess a handler or protocol from source text

#### Scenario: Exact related codec is usable

- **WHEN** the room contains exactly one `video_codec` record with canonical IP and supported VCS `diagnostic_model`
- **THEN** codec resolution is `RESOLVED`
- **AND** the resolved context binds that exact codec record/model/IP to the current inventory snapshot and accepted PDU context

### Requirement: Room display evidence does not replace room identity

The resolved room context SHALL use canonical `room_id` as authority. `room_name` SHALL be
optional display evidence derived from all records indexed under that room ID. When zero
non-null names exist, the resolved context SHALL have no room display name. When exactly
one distinct non-null name exists, it MAY be displayed. When more than one distinct
non-null name exists, the application SHALL NOT select one as authoritative and SHALL
attach a safe `ROOM_NAME_CONFLICT` warning while continuing resolution by `room_id`.

#### Scenario: Room has one consistent display name

- **WHEN** every non-null room name under the authoritative room ID has the same canonical value
- **THEN** that value may be included as the room display name

#### Scenario: Room has conflicting display names

- **WHEN** records under one authoritative room ID contain multiple distinct non-null room names
- **THEN** no one name is selected as authoritative
- **AND** a safe `ROOM_NAME_CONFLICT` warning is exposed
- **AND** codec resolution continues using the authoritative room ID

### Requirement: Independent bounded related-codec status lifecycle

A resolved related codec SHALL be read through a dedicated application-owned serialized
read-only session lane that is independent from the user-selected codec refresh request and
from the `CodecScreen` interactive-session instance.

The related-codec lane SHALL NOT replace or participate in the generic `_active_request`,
global `current_worker`, selected codec model/IP widgets, current screen selection, generic
codec progress dialog, or user codec terminal window. It SHALL NOT invalidate, reuse, or
change the handler/session owned by `CodecScreen.interactive_controller`.

The lane SHALL reuse the existing model handler factory or equivalent existing handlers,
supported connection-profile ordering, structured codec failure classification, and
bounded interactive read-only recovery contract. It SHALL perform codec network I/O outside
the Qt GUI thread.

#### Scenario: User works with codec A while PDU resolves codec B

- **GIVEN** the user codec screen has an active interactive context for codec A
- **AND** a PDU enrichment resolves codec B
- **WHEN** the application reads codec B status
- **THEN** it uses an independent related-codec session context
- **AND** codec A's interactive generation, cached handler, callbacks, controls, and selected widgets remain unchanged

#### Scenario: Related-codec read is slow

- **WHEN** related-codec connection or status reading blocks on network I/O
- **THEN** it runs on the dedicated background lane
- **AND** the Qt GUI thread remains responsive

#### Scenario: Generic codec request remains independent

- **WHEN** related-codec status starts or completes
- **THEN** it does not replace generic `_active_request` or global `current_worker` authority
- **AND** it does not switch the current device, IP, screen, progress dialog, or terminal window

### Requirement: Related-codec status normalization

For a successfully resolved and connected supported VCS codec, the enrichment capability
SHALL produce a narrow normalized status containing at least:

```text
call_status
presentation_status
```

The implementation SHALL reuse existing handler status methods and existing parser logic
where available. Model-specific raw status shapes SHALL remain behind a focused adapter or
equivalent boundary. The PDU screen SHALL NOT receive complete raw codec status payloads.

When an authoritative status field is unavailable, the adapter SHALL represent it as
unavailable/unknown and SHALL NOT infer it from arbitrary text, unrelated fields, or a
successful connection alone.

#### Scenario: Related codec status is available

- **WHEN** the existing codec handler returns authoritative status data and normalization succeeds
- **THEN** the accepted enrichment result contains normalized call and presentation status
- **AND** complete raw handler status is not exposed to the PDU presentation

#### Scenario: One status field is unavailable

- **WHEN** the related codec connects successfully but one required field is not authoritatively available
- **THEN** that field is represented as unavailable/unknown
- **AND** the application does not fabricate a value

#### Scenario: Status adapter cannot interpret the response

- **WHEN** a supported codec response cannot be normalized according to the reviewed adapter contract
- **THEN** codec diagnostics reports a structured protocol/unavailable outcome
- **AND** it does not report successful call or presentation state

### Requirement: Independent enrichment generation and stale safety

Every accepted user PDU refresh SHALL create a new immutable enrichment generation and
operation identity, including repeat Refresh for the same PDU model/IP. The captured context
SHALL bind the accepted PDU generation/refresh identity, PDU model/IP, inventory
`snapshot_id`, exact resolved record identities, codec model/IP, and non-secret credential
context revisions.

The controller SHALL invalidate the current enrichment when a newer accepted PDU refresh,
PDU model/IP/context change, relevant credential configuration change, inventory revision
replacement, or application shutdown supersedes it.

Queued related-codec work SHALL recheck currentness before handler acquisition and before
first network I/O when those phases are separable. Stale queued work SHALL perform zero
handler construction and zero network I/O. An in-flight stale result, error, completion,
credential index, or connection profile SHALL not update current presentation or memory.
Background currentness SHALL NOT depend on reading Qt widgets.

#### Scenario: Repeat PDU refresh supersedes old enrichment

- **GIVEN** enrichment is pending for one accepted PDU refresh
- **WHEN** the operator refreshes the same PDU again and the new PDU result is accepted
- **THEN** a new enrichment generation supersedes the old one
- **AND** old callbacks cannot update the new generation

#### Scenario: Queued related-codec work becomes stale

- **WHEN** a related-codec operation is queued and its enrichment context changes before execution
- **THEN** the operation is dropped before handler acquisition and first network I/O
- **AND** it opens no transport and sends no device request

#### Scenario: Related-codec I/O is already in flight

- **WHEN** old related-codec network I/O was already in flight when enrichment was superseded
- **THEN** its result, error, completion, credential index, and connection profile cannot update the current context
- **AND** its resources are still cleaned up on the owning execution lane

### Requirement: Composite enrichment outcome preserves PDU success

The application SHALL represent inventory/room/codec resolution separately from related
codec diagnostic execution. A final non-secret enrichment presentation model SHALL contain
the current context, resolution status, optional resolved room/codec context, optional safe
resolution warnings, codec diagnostic status, optional call/presentation values, and an
optional safe message.

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

An inventory or codec enrichment failure SHALL NOT convert an accepted PDU result into a
PDU authentication, connection, request, or mutation failure. It SHALL NOT clear accepted
PDU data, change PDU refresh/mutation authority, or open a modal automatic-error dialog.

#### Scenario: PDU succeeds but inventory has no match

- **WHEN** PDU diagnostics succeeds and enrichment resolves `PDU_NOT_FOUND`
- **THEN** accepted PDU data and outlet controls remain available
- **AND** the inline enrichment section shows the not-found state
- **AND** codec diagnostics remains `NOT_STARTED`

#### Scenario: PDU succeeds but codec connection fails

- **WHEN** PDU diagnostics succeeds, room/codec resolution is `RESOLVED`, and the related codec has a transport failure
- **THEN** accepted PDU data remains successful and usable
- **AND** the inline enrichment section reports `TRANSPORT_FAILED`
- **AND** no generic PDU or codec modal connection error is shown automatically

#### Scenario: Related codec status succeeds

- **WHEN** current room/codec resolution is `RESOLVED` and the current related-codec read succeeds
- **THEN** codec diagnostics is `SUCCESS`
- **AND** normalized call and presentation values are rendered for that exact PDU/room/codec context

### Requirement: Related-codec resources have explicit lifecycle cleanup

The application SHALL invalidate and close the dedicated related-codec handler/session on
terminal success, terminal failure, context supersession, relevant credential change, and
application shutdown. Cleanup SHALL execute on the background lane that owns network/session
resources and SHALL be idempotent or exactly once according to the reused session contract.
The Qt GUI thread SHALL NOT block on network cleanup.

#### Scenario: Application closes during related-codec work

- **WHEN** the application closes while a related-codec operation or cached handler exists
- **THEN** the enrichment context is invalidated
- **AND** handler/session resources are closed on their owning lane
- **AND** later callbacks cannot update destroyed or superseded UI state

#### Scenario: Successful read completes

- **WHEN** one bounded related-codec status read succeeds
- **THEN** the accepted result may be rendered and remembered
- **AND** the bounded related-codec session is invalidated or closed according to the focused controller lifecycle
