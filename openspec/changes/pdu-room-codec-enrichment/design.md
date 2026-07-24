## Context

The completed `equipment-inventory-snapshot` change is implemented, archived, and merged.
Normal runtime can load one immutable `EquipmentInventory` revision and query multi-value
indexes by IP, room, and room/device kind. The inventory layer intentionally returns only
zero, one, or many records and does not classify those counts as resolved, not found, or
ambiguous.

The current PDU lifecycle is owned by `PDUController`. It has a common PDU context plus
independent refresh and mutation authority lanes. A mutation reconciliation is represented
as refresh-lane work whose `originating_mutation_operation_id` is non-null. Current accepted
PDU refresh data is rendered through the shell, while stale callbacks are discarded by the
PDU controller.

The current user codec paths are not a safe orchestration boundary for this feature:

- generic codec refresh is bound to the main window's single `_active_request` and
  `current_worker` lifecycle;
- `CodecScreen.interactive_controller` is activated from the user-selected codec model and
  IP and rejects callbacks that do not match those widgets;
- using either path for a codec discovered from a PDU room could displace or conflict with
  an unrelated user codec session.

The reusable lower-level codec contracts are nevertheless suitable. Codec handlers already
implement model-specific status reads. Transport ordering is defined by
`order_codec_profiles`. `InteractiveSessionController` provides a serialized background
lane, immutable context generation, pre-handler stale checks, cached-handler invalidation,
structured failure classification, application-supplied credential candidates, saved-first
transport ordering, bounded read-only recovery, and result metadata containing the used
credential index and connection profile.

This change connects those existing boundaries without changing inventory schema v1 and
without making PDU success depend on enrichment success.

## Goals

- Resolve an accepted current user PDU refresh to exactly one canonical PDU record and its
  authoritative `room_id`.
- Resolve exactly one usable VCS codec candidate from the same room without implicit
  first-match selection.
- Read at least call status and presentation/broadcast status from the related codec.
- Keep automatic related-codec work independent from the user codec refresh and interactive
  session contexts.
- Keep all codec network I/O outside the Qt GUI thread.
- Drop stale queued enrichment before handler acquisition and first network I/O, and ignore
  stale in-flight callbacks.
- Preserve application ownership of credentials, fallback, successful credential index,
  and connection-profile memory.
- Render room and related-codec state inline on the PDU screen without changing successful
  PDU diagnostics into an error.
- Preserve inventory multiplicity and expose structured safe resolution outcomes.
- Keep public contexts and diagnostics free of secrets and session artifacts.

## Non-Goals

- Do not change canonical equipment inventory schema v1 or its index/query semantics.
- Do not add a primary-codec field or infer a primary codec from record order.
- Do not diagnose every codec when a room contains multiple codec records.
- Do not aggregate multiple room codecs into one result.
- Do not start related-codec diagnostics from PDU mutation reconciliation.
- Do not add continuous or periodic related-codec polling.
- Do not add related-codec control actions.
- Do not reuse the `CodecScreen.interactive_controller` instance.
- Do not route related-codec work through generic codec `refresh_*` methods,
  `_active_request`, or global `current_worker` authority.
- Do not move inventory lookup, codec selection, credentials, or codec network work into
  `PDUController` or `PDUScreen`.
- Do not commit real organization inventory data.

## Decision 1: A focused application orchestration controller owns enrichment

Add a focused application/composition component equivalent to:

```text
PDURoomCodecEnrichmentController
```

The controller owns:

- enrichment context generation and operation identity;
- accepted-PDU-context intake;
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
- canonical inventory loading/validation rules;
- protocol parsing inside handlers;
- credential storage/provider implementation;
- global GUI request authority;
- user codec interactive controls;
- PDU rendering widgets.

`VCSDiagnosticApp` composes this controller and supplies focused providers/callbacks for:

- the current immutable inventory or its safe load failure;
- application-owned codec credential candidates;
- saved credential index for exact codec model/IP;
- saved connection profile for exact codec model/IP;
- successful credential/profile persistence;
- accepted result/error rendering into `PDUScreen`.

The controller must not become a generic device manager or a replacement shell.

## Decision 2: `PDUController` publishes only an accepted user-refresh context

`PDUController` remains PDU-specific. After it accepts a current successful refresh whose
refresh lane has no `originating_mutation_operation_id`, it publishes or invokes one focused
non-secret application callback equivalent to:

```text
PDUAcceptedRefreshContext(
    pdu_generation,
    pdu_refresh_operation_id,
    model,
    ip_address,
    credential_context_revision,
)
```

The event contains no credentials, credential candidate list, outlet data, handler, worker,
transport, cookie, token, or session object.

Publication occurs only after PDU freshness has been accepted. A stale PDU callback cannot
start enrichment. A refresh created for mutation reconciliation does not publish the event.
Repeated user Refresh creates a new enrichment generation even when model and IP are
unchanged, so the new request supersedes prior related-codec work.

`PDUController` does not load or query inventory, resolve a room, select a codec, resolve
codec credentials, create a codec handler, or render enrichment state.

## Decision 3: Inventory is loaded once and failure is non-fatal to diagnostics

Application composition attempts to load the deployment-local inventory through the
existing `load_equipment_inventory()` boundary. It retains either:

```text
EquipmentInventory
```

or a safe structured inventory-load failure category already defined by the completed
capability.

Inventory load failure does not prevent application startup and does not disable existing
PDU or codec diagnostics. When a PDU refresh is accepted while no inventory is available,
the enrichment result is `INVENTORY_UNAVAILABLE` with the safe load category and message.
No raw JSON/storage exception is exposed to the screen.

This change adds no file watching, hot reload, or GUI inventory editor. Replacing an
inventory revision remains a future composition concern.

## Decision 4: Room resolution is pure and ambiguity-preserving

Add a pure resolver and immutable result model in a focused core/application-domain module,
equivalent to:

```text
RoomContextResolver.resolve_related_codec(inventory, pdu_ip)
```

The resolver performs no Qt access, credentials, logging of full records, handler
construction, worker submission, or network I/O.

Resolution uses the current immutable inventory revision and follows this exact sequence:

1. Query `find_by_ip(pdu_ip)`.
2. Require exactly one total IP match.
3. Require that record's `device_kind` to be `pdu`.
4. Require a non-null authoritative `room_id`.
5. Query `find_room_equipment(room_id)` to derive safe room display consistency.
6. Query `find_by_room_and_kind(room_id, "video_codec")`.
7. Require exactly one codec record.
8. Require a non-null canonical IPv4 `ip_address`.
9. Require `diagnostic_model` to be one of the application-supported VCS codec models.

The resolver does not reduce duplicate IP matches by filtering them to PDU records. If one
IP maps to a PDU record and another equipment record, the IP remains ambiguous because the
source assignment itself conflicts.

The resolver does not use `source_model`, manufacturer text, room name, record order,
`records[0]`, or fuzzy matching as selection authority.

## Decision 5: Structured resolution outcomes are separate from codec diagnostics

The resolution result uses a closed machine-readable status vocabulary equivalent to:

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

Semantics:

- `INVENTORY_UNAVAILABLE`: no validated inventory revision is published to composition;
- `PDU_NOT_FOUND`: IP lookup returns zero records;
- `AMBIGUOUS_PDU_IP`: IP lookup returns more than one record;
- `PDU_KIND_MISMATCH`: exactly one IP record exists but it is not canonical kind `pdu`;
- `ROOM_UNRESOLVED`: the exact PDU record has no authoritative `room_id`;
- `CODEC_NOT_FOUND`: the room has zero canonical `video_codec` records;
- `AMBIGUOUS_CODEC`: the room has more than one canonical `video_codec` record;
- `CODEC_IP_MISSING`: the one codec record has no usable canonical IP;
- `CODEC_UNSUPPORTED`: the one codec record does not map to a supported VCS diagnostic model;
- `RESOLVED`: exactly one usable codec model/IP is available for diagnostic startup.

A resolved room context is immutable and contains only non-secret canonical data equivalent
to:

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

`room_name` is display-only. The resolver gathers distinct non-null room names from all
records with the authoritative `room_id`:

- zero names: `room_name` is absent;
- one distinct name: that display name may be shown;
- more than one distinct name: no name is selected as authoritative and a safe
  `ROOM_NAME_CONFLICT` warning is attached while codec resolution continues by `room_id`.

The final enrichment result composes resolution and codec diagnostic state rather than
collapsing them into one exception:

```text
PduRoomCodecEnrichmentResult
    enrichment_context
    resolution_status
    room_context | null
    resolution_warnings
    codec_diagnostic_status
    call_status | null
    presentation_status | null
    safe_message | null
```

Codec diagnostic state uses a separate closed vocabulary equivalent to:

```text
NOT_STARTED
PENDING
SUCCESS
AUTHENTICATION_FAILED
TRANSPORT_FAILED
PROTOCOL_FAILED
UNAVAILABLE
```

A stale superseded operation is not rendered as a terminal result for the new context.

## Decision 6: The related codec uses a separate serialized read-only session lane

The new controller owns a separate `InteractiveSessionController` instance or an equivalent
focused serialized read-only session component. It must not use the instance owned by
`CodecScreen`.

For one resolved related codec, the controller:

1. obtains the complete application-resolved credential candidate sequence before network
   I/O;
2. obtains the saved credential index and supported saved connection profile for the exact
   codec model/IP;
3. activates the dedicated session context with those values;
4. submits one quiet `READ_ONLY` status operation;
5. accepts only callbacks matching the current enrichment and session generations;
6. closes/invalidates the bounded related-codec session after terminal success, terminal
   error, supersession, credential-context change, or application shutdown.

The operation may call the existing handler's read-only status method. Raw model-specific
status remains internal to the controller/adapter. A focused `RelatedCodecStatusAdapter`
or equivalent normalizes only the fields needed by this feature:

```text
call_status
presentation_status
```

The adapter may reuse existing parser classes where existing polling workers already parse
the handler response. It must not duplicate transport/login logic, create its own handler,
or expose complete raw status payloads to `PDUScreen`.

Using a separate `InteractiveSessionController` instance is deliberate. It reuses the
approved handler factory, profile ordering, candidate identity, background serialized lane,
pre-handler stale check, structured failure classification, and bounded read-only recovery
without sharing user codec session state.

## Decision 7: Existing generic codec polling orchestration is not reused directly

Existing `VCSDiagnosticApp.refresh_huawei_*` and equivalent generic codec refresh methods
remain user-request paths. The related-codec operation must not:

- call those methods;
- replace `_active_request`;
- assign the related codec worker to global `current_worker` authority;
- switch `device_combo`, `ip_entry`, or the current screen;
- show the generic codec progress dialog or terminal window;
- invoke generic codec result/error handlers as if the user selected that codec.

Existing polling parsers, handlers, and transport behavior may be reused behind the focused
status adapter. Existing QRunnable polling workers may be reused only if implementation
proves they receive an immutable enrichment descriptor and perform application-owned
freshness checks before handler acquisition and first network I/O. Direct reuse without
those checks is not compliant.

The preferred implementation is the dedicated serialized session lane because its existing
contract already provides the required pre-I/O freshness and bounded read-only recovery.

## Decision 8: Enrichment has an independent immutable context

Each accepted user PDU refresh creates an immutable context equivalent to:

```text
PDURoomCodecEnrichmentContext(
    enrichment_generation,
    enrichment_operation_id,
    pdu_generation,
    pdu_refresh_operation_id,
    pdu_model,
    pdu_ip_address,
    pdu_credential_context_revision,
    inventory_snapshot_id,
    codec_record_id | null,
    codec_model | null,
    codec_ip_address | null,
    codec_credential_context_revision,
)
```

Secret candidate identities may be compared internally by the dedicated session controller,
but credential values or derived secret-bearing identities are not part of public context
or screen payloads.

The controller invalidates the current enrichment when any of these supersede it:

- a new accepted user PDU refresh;
- selected PDU model or IP change;
- PDU context invalidation;
- related codec credential configuration change;
- replacement of the inventory instance in a future composition path;
- application shutdown.

Inventory resolution is synchronous in memory and may run in the GUI thread because it is
bounded dictionary lookup with no file or network I/O. Codec status network work always
runs on the dedicated background lane.

## Decision 9: Stale work is suppressed before I/O and after in-flight completion

Before related codec handler acquisition, and again before first network I/O when those
phases are separable, the dedicated lane checks that the captured session generation and
enrichment context remain current.

A queued stale operation:

- creates no handler;
- opens no HTTP, HTTPS, SSH, Telnet, or other transport;
- sends no device request;
- updates no screen state;
- updates no credential or profile memory.

If network I/O was already in flight when the context changed, its result, error, progress,
completion, credential index, or connection profile cannot update the new PDU/room context.
The dedicated lane is still cleaned up on its owning execution path.

The new controller must not infer currentness from current Qt widget values inside a
background worker. Currentness comes from application-owned immutable generation/context
state.

## Decision 10: Credential and transport policy remains application-owned

The related codec controller receives the complete validated candidate chain from the
application credential boundary before handler/session construction.

The existing policy remains normative:

- one credential is assigned across all supported transport attempts;
- the supported saved connection profile is tried first;
- transport failure may advance only to another supported transport with the same
  credential;
- credential advancement occurs only after a structured confirmed new-login
  `AuthenticationError`;
- text such as `auth`, `401`, or `403` is not retry authority;
- candidate advancement is monotonic and does not wrap to an earlier candidate;
- handlers do not inspect or iterate the candidate chain;
- public attempt observability may expose only attempt position and total count;
- successful credential index/profile memory is committed only after an accepted current
  final status success;
- stale, partial, unsupported, resolution-only, or failed results do not commit success.

Because the operation is read-only, the approved bounded recovery policy permits at most
one reconnect cycle and one replay after successful recovery. Recovery does not recurse.

## Decision 11: PDU success and enrichment success are independent

An accepted PDU result is rendered and retained regardless of enrichment outcome.

The enrichment controller must not:

- turn the PDU connection state into authentication/request error;
- clear accepted outlet rows or PDU device information;
- disable PDU mutation controls solely because enrichment failed;
- alter PDU refresh/mutation lane authority;
- display a modal connection-error dialog for inventory or related-codec failure;
- trigger automatic PDU retry or reconciliation.

Examples:

```text
PDU diagnostics = SUCCESS
inventory resolution = PDU_NOT_FOUND
codec diagnostics = NOT_STARTED
```

```text
PDU diagnostics = SUCCESS
inventory resolution = RESOLVED
codec diagnostics = TRANSPORT_FAILED
```

Both remain successful PDU diagnostics with an inline enrichment state.

## Decision 12: `PDUScreen` remains the rendering boundary

Extend the existing `PDUScreen` with one related-room/codec presentation section capable of
rendering:

- enrichment loading/pending state;
- authoritative room ID;
- room display name when unambiguous;
- related codec source/display model;
- related codec IP;
- call status;
- presentation/broadcast status;
- structured not-found, ambiguous, unsupported, unavailable, and diagnostic-failure states.

The screen receives only accepted current non-secret presentation models. It does not query
inventory, classify multiplicity, resolve credentials, acquire a handler, submit network
work, decide staleness, or persist credential/profile memory.

On a new PDU context, the old related-room/codec section is cleared or reset to pending
before new enrichment can complete. Stale callbacks cannot restore old room/codec values.

Inline enrichment failure text must be concise and safe. Modal dialogs are reserved for
existing explicit user actions, not automatic enrichment failure.

## Decision 13: Safe observability and operational-data protection

Public contexts and signals may include only the minimum non-secret operational identifiers
needed to render the current result, such as PDU/codec IP, canonical record IDs, room ID,
room display name, model names, snapshot ID, operation IDs, and safe status categories.

They must not include:

- credential values or credential dictionaries;
- credential profile names;
- candidate identity material derived from secret values;
- cookies, Session IDs, CSRF/access tokens, cookie jars;
- handlers, workers, HTTP openers, SSH clients/channels, transports, or sessions;
- complete inventory records when a narrow presentation model is sufficient;
- complete raw codec status payloads;
- complete inventory snapshots or source workbook rows.

Tests continue to use synthetic inventory records and fake handlers only. No real production
room, IP, equipment, or credential data is committed.

## Decision 14: Shutdown and cleanup are explicit

The application close path invalidates the enrichment context and shuts down the dedicated
related-codec session controller without blocking the Qt GUI thread on network I/O.

Handler/session cleanup runs on the execution lane that owns those resources. Cleanup is
idempotent or exactly-once according to the existing interactive-session contract. A
finished callback after invalidation cannot render or persist stale state.

## Rejected Alternatives

### Put the full chain in `PDUController`

Rejected because it would combine PDU lifecycle authority with inventory resolution,
codec selection, credential orchestration, and unrelated codec network state.

### Reuse `CodecScreen.interactive_controller`

Rejected because that instance is explicitly tied to the user-selected codec model/IP and
its callbacks are validated against the codec screen widgets. Automatic codec B work must
not invalidate or reuse the user's codec A session.

### Call generic codec refresh methods

Rejected because those methods participate in the shell's one active user request/current
worker lifecycle, switch generic codec presentation, and do not provide an independent
PDU-derived context.

### Select the first matching inventory record

Rejected because the completed inventory capability preserves multiplicity and grants no
primary-selection authority. Schema v1 has no primary-codec field.

### Diagnose all codecs when the room is ambiguous

Rejected for this change because it changes the product behavior from one related-room
status into multi-device aggregation and multiplies credential/network operations without
an approved selection or presentation contract.

### Treat enrichment failure as PDU failure

Rejected because the PDU diagnostic result is already accepted independently and inventory
or codec status is optional contextual enrichment.

## Risks and Mitigations

### Risk: model-specific status shapes differ

Mitigation: use a narrow reviewed adapter and existing parsers; expose only normalized call
and presentation status, with `UNAVAILABLE` for fields not authoritatively available.

### Risk: background codec work outlives a PDU context

Mitigation: independent immutable enrichment/session generations, pre-I/O checks, stale
callback suppression, and explicit cleanup.

### Risk: credential memory is updated from stale enrichment

Mitigation: persistence is an application callback invoked only after both session and
enrichment contexts are current and a final status result is accepted.

### Risk: inventory inconsistencies misidentify a device

Mitigation: require exactly one total IP match, exact canonical `device_kind`, authoritative
`room_id`, and exactly one supported codec candidate; never use first-match or fuzzy rules.

### Risk: automatic failure creates modal-dialog noise

Mitigation: all enrichment states are rendered inline and do not use generic user codec
error dialogs.

## Migration Plan

1. Introduce pure resolution/status models and tests against synthetic `EquipmentInventory`
   instances.
2. Introduce the focused enrichment controller with fake credential/session providers and
   deterministic stale tests.
3. Wire accepted user-refresh publication from `PDUController`, explicitly excluding
   reconciliation refreshes.
4. Compose inventory availability, credential/profile callbacks, and the dedicated
   related-codec session lane in `VCSDiagnosticApp`.
5. Add model-specific related-codec status adaptation using existing handlers/parsers.
6. Add `PDUScreen` presentation and reset behavior.
7. Run focused tests, the full offline suite, strict change validation, strict all-change
   validation, and independent review/testing before archive.

## Open Questions Resolved by This Design

- Storage remains JSON-backed behind `EquipmentInventory`; no SQLite change is needed.
- Inventory lookup stays synchronous and indexed; no background thread is needed for the
  in-memory dictionary lookups.
- More than one codec is ambiguous; this change does not choose one.
- Automatic codec diagnostics use an independent serialized read-only session lane.
- Only accepted user PDU refresh starts enrichment; reconciliation refresh does not.
- PDU success remains valid regardless of enrichment outcome.
