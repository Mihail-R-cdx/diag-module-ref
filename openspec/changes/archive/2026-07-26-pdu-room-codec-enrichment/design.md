## Context

The completed `equipment-inventory-snapshot` change is implemented, archived, and merged.
Normal runtime can load one immutable `EquipmentInventory` revision and query multi-value
indexes by IP, room, and room/device kind. The inventory layer intentionally returns zero,
one, or many records and does not classify those counts as resolved, not found, or
ambiguous.

The current PDU lifecycle is owned by `PDUController`. It has one common PDU context plus
independent refresh and mutation authority lanes. Mutation reconciliation is refresh-lane
work whose `originating_mutation_operation_id` is non-null. Only callbacks accepted by the
PDU controller may affect current PDU presentation or lifecycle state.

The current user codec paths are not a safe orchestration boundary for this feature:

- generic codec refresh is bound to the main window's single `_active_request` and
  `current_worker` lifecycle;
- `CodecScreen.interactive_controller` is owned by the user-selected codec screen and tied to
  that screen's model/IP identity;
- automatic work for a codec found from a PDU room must not replace either user codec
  lifecycle.

The lower-level codec contracts remain reusable: model handlers, status methods, parser
normalization, `order_codec_profiles`, structured codec failure classification, application-
resolved credential chains, saved credential/profile memory, and bounded read-only recovery.

A critical implementation detail of the existing `InteractiveSessionController` must be
accounted for explicitly. `activate_context()` does not roll generation when model, IP,
credential identities, starting index, and saved profile are unchanged. Therefore a repeat
PDU refresh that resolves the same codec cannot rely on `activate_context()` alone to make
old queued work stale.

## Goals

- Resolve an accepted current user PDU refresh to exactly one canonical PDU record and its
  authoritative `room_id`.
- Resolve exactly one usable VCS codec from that room without implicit first-match selection.
- Read at least call status and presentation/broadcast status from the related codec.
- Keep automatic related-codec work independent from user codec refresh and interactive
  session state.
- Keep codec network I/O outside the Qt GUI thread.
- Supersede old enrichment immediately when the PDU context is changing, even when the new
  PDU refresh later fails.
- Drop stale queued codec work before handler acquisition and first network I/O, including a
  repeat refresh that resolves the same codec with the same credentials and profile.
- Preserve application ownership of credentials, fallback, successful credential index, and
  connection-profile memory.
- Render room and related-codec state inline without changing successful PDU diagnostics into
  an error.
- Preserve inventory multiplicity and expose structured safe resolution outcomes.
- Keep public contexts and diagnostics free of secrets and session artifacts.

## Non-Goals

- Do not change canonical equipment inventory schema v1 or query semantics.
- Do not add or infer a primary codec.
- Do not diagnose every codec when one room contains multiple codec records.
- Do not start enrichment from PDU mutation reconciliation.
- Do not add continuous related-codec polling or codec control actions.
- Do not reuse the `CodecScreen.interactive_controller` instance.
- Do not route related-codec work through generic codec `refresh_*` methods,
  `_active_request`, or global `current_worker` authority.
- Do not move inventory lookup, codec selection, credentials, or codec network work into
  `PDUController` or `PDUScreen`.
- Do not create a second PDU generation authority in `VCSDiagnosticApp`.
- Do not commit real organization inventory data.

## Decision 1: A focused application controller owns enrichment

Add a focused application/composition component equivalent to:

```text
PDURoomCodecEnrichmentController
```

It owns:

- enrichment generation and operation identity;
- accepted-PDU-context intake;
- PDU-context supersession intake;
- inventory availability and resolution orchestration;
- related-codec candidate acceptance;
- related-codec credential attempt state;
- one independent serialized read-only codec session lane;
- stale callback acceptance;
- successful credential/profile persistence callbacks;
- safe terminal result composition;
- shutdown and context invalidation.

It does not own:

- PDU refresh or mutation authority;
- PDU context generation;
- canonical inventory loading/validation rules;
- protocol parsing inside handlers;
- credential storage/provider implementation;
- global GUI request authority;
- user codec interactive controls;
- PDU rendering widgets.

`VCSDiagnosticApp` composes the controller and supplies focused providers/callbacks for the
current inventory or safe load failure, codec credential candidates, saved credential index,
saved connection profile, accepted-success persistence, and accepted presentation rendering.

## Decision 2: PDU lifecycle exposes two focused non-secret boundaries

`PDUController` remains the sole PDU context authority. Application composition does not
infer PDU freshness by reading Qt widgets and does not maintain a parallel PDU generation.

### Accepted user-refresh boundary

After `PDUController` accepts a current successful user refresh whose refresh lane has no
`originating_mutation_operation_id`, it publishes a non-secret context equivalent to:

```text
PDUAcceptedRefreshContext(
    pdu_generation,
    pdu_refresh_operation_id,
    model,
    ip_address,
    credential_context_revision,
)
```

This event starts resolution and related-codec diagnostics. Reconciliation refreshes, stale
callbacks, errors, progress, status, and completion without accepted success do not publish
it.

### PDU-context supersession boundary

`PDUController` also publishes or invokes a focused non-secret lifecycle callback equivalent
to:

```text
PDUContextSuperseded(
    pdu_generation_or_revision,
    reason,
)
```

The exact type name is not normative. The boundary is normative. It fires no later than:

- selected PDU model change;
- selected PDU IP change;
- PDU credential-context change;
- start of a new user PDU refresh, including repeat Refresh for the same model/IP;
- explicit PDU context invalidation or deactivation;
- application shutdown.

The event carries no credentials, candidate lists, outlet data, worker/handler/session
objects, cookies, tokens, or transports. The shell only forwards this PDU-owned lifecycle
fact to the enrichment controller and presentation reset path.

On receipt, the enrichment controller immediately:

1. advances/supersedes its own enrichment generation;
2. invalidates the dedicated related-codec session lane;
3. prevents old callbacks from rendering or persisting memory;
4. clears or resets the related-room section to a neutral/pending-PDU state.

This happens before the next PDU result is known. If that PDU refresh fails, old room/codec
data remain cleared and no accepted-success enrichment is started.

## Decision 3: Inventory availability is non-fatal to diagnostics

Application composition attempts to load the deployment-local inventory through
`load_equipment_inventory()`. It retains either one validated immutable
`EquipmentInventory` or the existing safe structured load failure.

Inventory load failure does not prevent application startup or existing device diagnostics.
When an accepted PDU refresh arrives without available inventory, enrichment resolves
`INVENTORY_UNAVAILABLE`. No raw storage exception is exposed.

This change adds no file watching, hot reload, or GUI inventory editor.

## Decision 4: Room resolution is pure and ambiguity-preserving

Add a pure resolver equivalent to:

```text
RoomContextResolver.resolve_related_codec(inventory, pdu_ip)
```

It performs no Qt access, credential work, handler construction, worker submission, or
network I/O.

Resolution follows this exact sequence:

1. Query `find_by_ip(pdu_ip)`.
2. Require exactly one total IP match.
3. Require that record's `device_kind == "pdu"`.
4. Require non-null authoritative `room_id`.
5. Query `find_room_equipment(room_id)` for room display consistency.
6. Query `find_by_room_and_kind(room_id, "video_codec")`.
7. Require exactly one codec record.
8. Require non-null canonical codec IP.
9. Require exact supported VCS `diagnostic_model`.

Duplicate IP results are not filtered to PDU records. The resolver does not use
`source_model`, manufacturer text, room name, record order, `records[0]`, or fuzzy matching as
selection authority.

## Decision 5: Resolution and diagnostics are separate result dimensions

Resolution status uses a closed vocabulary equivalent to:

```text
INVENTORY_UNAVAILABLE
PDU_NOT_FOUND
AMBIGUOUS_PDU_IP
PDU_KIND_MISMATCH
ROOM_UNRESOLVED
CODEC_NOT_FOUND
AMBIGUOUS_CODEC
CODEC_IP_MISSING
CODEC_UNSUPPORTED
RESOLVED
```

The immutable resolved context contains only non-secret canonical data equivalent to:

```text
RoomContext(
    snapshot_id,
    pdu_record_id,
    pdu_model,
    pdu_ip_address,
    room_id,
    room_name,
    codec_record_id,
    codec_source_model,
    codec_diagnostic_model,
    codec_ip_address,
)
```

`room_id` is authoritative. `room_name` is display-only evidence. Zero names yields no name;
one distinct name may be shown; conflicting names yield no selected name plus a safe
`ROOM_NAME_CONFLICT` warning while resolution continues by `room_id`.

Codec diagnostic state is separate:

```text
NOT_STARTED
PENDING
SUCCESS
AUTHENTICATION_FAILED
TRANSPORT_FAILED
PROTOCOL_FAILED
UNAVAILABLE
```

A stale operation is not rendered as a terminal result for the new context.

## Decision 6: The related codec uses a separate serialized read-only lane

The enrichment controller owns a separate `InteractiveSessionController` instance or an
equivalent focused serialized read-only component. It never uses the instance owned by
`CodecScreen`.

For a resolved codec, the controller obtains the full application-resolved credential chain,
saved exact model/IP index, and supported saved profile, then submits one quiet read-only
status operation. Existing handlers, status methods, parser logic, profile ordering, and
structured classification remain reusable.

The controller does not call generic codec refresh methods, replace `_active_request`, assign
global `current_worker`, switch selected model/IP/screen, or open generic codec progress or
terminal UI.

## Decision 7: Every enrichment generation forces session-generation rollover

The dedicated session lane must not rely on same-identity `activate_context()` to supersede
old work.

For every accepted user PDU refresh that starts enrichment, including repeat Refresh for the
same PDU and the same resolved codec, the controller performs this order:

```text
publish new enrichment generation/operation identity
    -> dedicated_session.invalidate_context()
    -> resolve inventory and codec context
    -> dedicated_session.activate_context(...)
    -> submit read-only status operation
```

`invalidate_context()` is mandatory before activation even when codec model, codec IP,
credential identities, starting credential index, and saved profile are unchanged. Because
invalidation changes the session generation synchronously and clears its context, an old
queued operation cannot remain current merely because the prospective identity is equal.

An equivalent implementation may add an explicit force-rollover API or include the
enrichment generation in private session identity, but it must prove the same behavior. A
plain call to the current `activate_context()` with equal identity is not compliant.

A PDU-context supersession event also invalidates the dedicated session immediately, even
before an accepted replacement PDU result exists.

## Decision 8: Stale work is suppressed before I/O and after in-flight completion

Before handler acquisition, and again before first network I/O when separable, the dedicated
lane checks both captured session generation and captured enrichment context.

A queued stale operation:

- creates or acquires no handler;
- opens no HTTP, HTTPS, SSH, Telnet, or other transport;
- sends no device request;
- updates no screen state;
- updates no credential or profile memory.

If I/O was already in flight when superseded, its result, error, progress, completion,
credential index, and connection profile cannot update the new context. Cleanup still runs
on the owning execution lane.

The required same-identity regression is:

```text
old related-codec operation is queued
    -> repeat Refresh starts for the same PDU
    -> the same codec model/IP, credential chain/index, and saved profile resolve again
    -> old operation is dropped before handler factory and network I/O
```

Background currentness never reads Qt widget values.

## Decision 9: Credential and transport policy remains application-owned

The related-codec controller receives the complete validated candidate chain before session
construction.

Normative policy:

- one credential is used across all supported transport attempts;
- a supported saved profile is tried first;
- transport fallback keeps the same credential;
- credential advancement occurs only after structured confirmed new-login
  `AuthenticationError`;
- text such as `auth`, `401`, or `403` is not retry authority;
- candidate advancement is monotonic and does not wrap;
- handlers and adapters do not inspect or iterate candidates;
- public attempt state exposes only position and total;
- successful credential index/profile are committed only after accepted current final
  status success;
- stale, partial, unsupported, resolution-only, or failed outcomes commit nothing.

Because the operation is read-only, at most one reconnect cycle and one replay are allowed.
Recovery does not recurse.

## Decision 10: PDU success and enrichment success are independent

An accepted PDU result remains rendered and usable regardless of enrichment outcome.
Enrichment must not convert PDU state into an authentication/request error, clear outlet
rows, disable valid mutation controls, alter PDU lanes, show an automatic modal connection
error, or trigger PDU retry/reconciliation.

Examples:

```text
PDU diagnostics = SUCCESS
resolution = PDU_NOT_FOUND
codec diagnostics = NOT_STARTED
```

```text
PDU diagnostics = SUCCESS
resolution = RESOLVED
codec diagnostics = TRANSPORT_FAILED
```

## Decision 11: `PDUScreen` remains the rendering boundary

Extend the existing PDU screen with one related-room/codec section for pending/neutral state,
room ID, unambiguous room name, codec model/IP, call status, presentation/broadcast status,
and structured resolution/diagnostic states.

The screen receives only accepted current non-secret presentation models. It does not query
inventory, classify multiplicity, resolve credentials, acquire a handler, submit network
work, decide freshness, or persist memory.

On PDU-context supersession, old room/codec presentation is cleared or reset immediately,
not only after a later successful PDU result. Stale callbacks cannot restore old values.
Automatic enrichment failures are concise, safe, inline, and non-modal.

## Decision 12: Safe observability and cleanup

Public contexts may contain only minimum non-secret operational identifiers needed for the
current presentation. They must not contain credential values/dictionaries, profile names,
secret-derived candidate identity material, cookies, Session IDs, CSRF/access tokens,
handlers, workers, transports, sessions, complete inventory records/snapshots, complete raw
codec status, or source workbook rows.

The application close path publishes PDU/enrichment supersession and shuts down the dedicated
session controller without blocking the Qt GUI thread on network cleanup. Handler/session
cleanup runs on the execution lane that owns those resources and is idempotent or exactly
once. Later callbacks remain stale.

## Rejected Alternatives

### Put the full chain in `PDUController`

Rejected because it would combine PDU lifecycle authority with inventory resolution, codec
selection, credential orchestration, and unrelated codec network state.

### Reuse `CodecScreen.interactive_controller`

Rejected because that instance belongs to the user-selected codec context.

### Call generic codec refresh methods

Rejected because they participate in the shell's single user request/current-worker lifecycle.

### Rely on equal-identity `activate_context()`

Rejected because the current implementation returns the existing generation when identity is
unchanged. That cannot guarantee pre-I/O stale suppression for repeat same-PDU refresh.

### Wait for the next successful PDU result before invalidating old enrichment

Rejected because a model/IP change or new refresh may fail. Old room/codec state and old
queued codec work must be superseded immediately by the PDU lifecycle event.

### Select the first matching inventory record

Rejected because inventory multiplicity grants no first-match authority.

### Treat enrichment failure as PDU failure

Rejected because enrichment is optional contextual diagnostics.

## Risks and Mitigations

### Risk: model-specific status shapes differ

Mitigation: use a narrow adapter and existing parsers; expose only normalized call and
presentation status, with `UNAVAILABLE` when authoritative data is absent.

### Risk: same-identity repeat refresh leaves old work current

Mitigation: mandatory dedicated-session invalidation before every enrichment activation, plus
a focused regression that asserts zero handler-factory and zero network calls.

### Risk: failed replacement PDU refresh leaves old room data visible

Mitigation: a PDU-owned supersession callback immediately invalidates enrichment and resets
presentation before replacement success is known.

### Risk: credential memory is updated from stale enrichment

Mitigation: persistence occurs only after both session and enrichment contexts are current and
a final status result is accepted.

### Risk: inventory inconsistencies misidentify a device

Mitigation: require exactly one total IP match, exact PDU kind, authoritative room ID, and
exactly one supported codec candidate.

## Migration Plan

1. Add pure resolution/status models and synthetic tests.
2. Add the focused enrichment controller and dedicated session lane.
3. Add mandatory session invalidation before every enrichment activation.
4. Add the PDU-owned supersession callback and immediate presentation reset.
5. Wire accepted user-refresh publication, excluding reconciliation refreshes.
6. Compose inventory, credentials/profile callbacks, and status adapter in
   `VCSDiagnosticApp`.
7. Add `PDUScreen` presentation.
8. Run focused tests, full offline suite, strict change validation, strict all validation,
   and independent review before implementation approval/archive.

## Resolved Architecture Questions

- Storage remains JSON-backed behind `EquipmentInventory`.
- Inventory lookup remains synchronous indexed in-memory work.
- More than one codec is ambiguous.
- Automatic codec diagnostics use an independent serialized read-only lane.
- Every new enrichment generation forcibly rolls the dedicated session generation.
- PDU context supersession is delivered separately from accepted-success enrichment trigger.
- Reconciliation refresh does not start enrichment.
- PDU success remains valid regardless of enrichment outcome.
