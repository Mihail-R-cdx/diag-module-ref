## Why

The completed `equipment-inventory-snapshot` capability gives the diagnostic application a
validated immutable inventory with ambiguity-preserving IP, room, and room/device-kind
indexes. The application still does not connect that data boundary to an accepted PDU
refresh. An operator can diagnose a PDU, but the application cannot yet identify the PDU's
room, locate the VCS codec in that room, or show the room codec's call and presentation
status alongside the PDU diagnostics.

This integration is cross-device application orchestration. It must not expand
`PDUController` into an inventory or codec manager, must not reuse the user-selected
`CodecScreen` interactive-session instance, and must not route the automatic codec read
through the generic user codec refresh lifecycle. Those existing paths are bound to the
active user-selected codec/model/IP context and would allow a related-room codec operation
to displace or conflict with an unrelated interactive codec session.

The application therefore needs a focused PDU-room-codec enrichment boundary. It will
consume only an already accepted user-initiated PDU refresh context, resolve inventory
multiplicity explicitly, and run one independent bounded read-only codec-status operation.
The PDU result remains authoritative even when inventory resolution or codec diagnostics
are unavailable, ambiguous, unsupported, stale, or failed.

## What Changes

- Add a focused `pdu-room-codec-enrichment` application capability that composes the
  completed `EquipmentInventory` query boundary with accepted PDU refresh outcomes.
- Add a pure room-context resolver that interprets zero/one/many inventory results without
  Qt, credentials, workers, handlers, network I/O, or first-match selection.
- Add a dedicated application-owned enrichment controller with its own generation,
  operation identity, stale acceptance, credential-attempt state, and lifecycle cleanup.
- Let `PDUController` publish a non-secret accepted user-refresh context after current PDU
  success. It remains the sole owner of PDU refresh/mutation lanes and does not read the
  inventory or connect to codecs.
- Do not start room-codec enrichment from mutation reconciliation refreshes. A successful
  reconciliation may update PDU state but is not a new user request to resolve room context.
- Resolve the current PDU IP through the immutable inventory revision, require exactly one
  matching canonical PDU record with an authoritative `room_id`, and then require exactly
  one usable `video_codec` record in that room.
- Preserve and expose structured resolution outcomes for unavailable inventory, no PDU
  match, duplicate IP match, non-PDU IP match, missing room identity, no codec, multiple
  codecs, missing codec IP, and unsupported codec model.
- Run the related codec status read on an independent serialized read-only session lane,
  separate from the `CodecScreen.interactive_controller`, generic `_active_request`, and
  global `current_worker` codec polling path.
- Reuse existing codec handlers, connection-profile ordering, structured authentication
  classification, application-owned credential chains, bounded read-only recovery, and
  successful credential/profile memory without giving handlers or workers credential
  fallback authority.
- Extract and present at least normalized call status and presentation/broadcast status.
  Model-specific raw response shapes remain behind existing handler/parser or focused
  adapter boundaries.
- Keep every codec network operation off the Qt GUI thread and recheck currentness before
  handler acquisition and first network I/O. In-flight stale callbacks cannot update the
  current PDU/room presentation or credential memory.
- Extend the PDU presentation boundary with an inline related-room/codec section. Enrichment
  failures are non-modal and do not convert successful PDU diagnostics into a connection
  failure, clear outlet data, or alter PDU mutation authority.
- Keep public contexts, results, errors, logs, dialogs, and signals free of credentials,
  profile names, cookies, Session IDs, CSRF tokens, handlers, and transport/session objects.

## Target Data Flow

```text
accepted current user PDU refresh
        |
        | non-secret PDU refresh context
        v
PDURoomCodecEnrichmentController
        |
        +--> EquipmentInventory.find_by_ip(pdu_ip)
        |          |
        |          v
        |    RoomContextResolver
        |          |
        |          +--> exact PDU record / room resolution
        |          +--> exact room codec candidate resolution
        |
        +--> application-owned codec credentials/profile memory
        |
        v
independent bounded read-only codec session lane
        |
        +--> existing model handler + supported transport ordering
        +--> structured auth-only credential advancement
        +--> at most one read-only recovery/replay
        |
        v
accepted PDU-room-codec enrichment result
        |
        v
PDUScreen related room / codec status section
```

## Capabilities

### New Capabilities

- `pdu-room-codec-enrichment`: define PDU-to-room resolution, related-codec candidate
  resolution, independent read-only codec status lifecycle, structured outcome composition,
  stale safety, and PDU-context presentation.

### Modified Capabilities

- `diagnostic-application-shell`: compose the inventory, resolver, and focused enrichment
  controller; route only accepted current user PDU refresh contexts; keep `PDUScreen` as the
  rendering boundary.
- `request-lifecycle-and-recovery`: add an independent related-codec generation/lane with
  pre-I/O stale suppression, bounded read-only recovery, and resource cleanup.
- `credential-source-isolation`: apply application-owned candidate resolution, structured
  auth-only advancement, and accepted-success persistence to related-codec diagnostics.
- `device-diagnostics-and-control`: present room and related-codec call/presentation status
  without changing PDU success semantics or the user codec interactive session.

The completed `equipment-inventory-snapshot` capability is consumed without changing its
zero/one/many query semantics. Interpretation as resolved, not found, ambiguous, or
unsupported remains in the new application orchestration capability as already required by
that root specification.

## Impact

Implementation is expected to add a focused resolver/result model, a dedicated enrichment
controller or equivalent application component, application composition wiring, a
related-codec presentation section on `PDUScreen`, and focused regression tests. Existing
codec protocol handlers and transport/profile policies should be reused rather than copied.
A narrow status adapter may be added where a handler's existing status payload requires
model-specific normalization.

The change must not add real organization inventory data to Git, modify canonical inventory
schema v1, invent a primary-codec field, select `records[0]`, move credential ownership into
a handler/worker, use string authentication heuristics, perform network I/O in the GUI
thread, or couple automatic room-codec diagnostics to the user-selected codec screen
session.
