## Why

The current room-diagnostic architecture already provides the correct authority model: validated inventory resolution, deterministic room membership, one-shot sequential acquisition, exact per-record state, presentation-only reusable widgets, and a serialized post-cycle interaction lifecycle. The remaining foundation-level product gap is operator experience. The current Qt room tree is functional but visually utilitarian and the permanent top-level input is still modeled as an IP-only field.

The target foundation experience is a polished room-oriented desktop shell while preserving the existing tree/accordion interaction model, current room-mode exact-row device-family presentations, and all network-safety contracts. The operator must be able to enter either a device IP address or a full/partial room name in one persistent search field. A device IP continues to resolve its authoritative room and open the whole room. A room-name selection establishes the room directly by canonical `room_id` without inventing a synthetic source device.

The shell redesign is reference-guided rather than pixel-exact, but the approved repository artifacts must be self-contained enough for a clean implementation/review session that has no access to the original conversation screenshots. This change therefore defines the common foundation only: baseline viewport, shell proportions, spacing, typography, common row density, room/network card hierarchy, selected-room cue, and dark/light acceptance behavior. Detailed redesign of the expanded Audio DSP, Matrix/IN1804, codec, and PDU presentations is explicitly deferred to later independent OpenSpec changes after this foundation is merged.

The change preserves existing fallback semantics. For a valid IP target with unavailable/unloadable/corrupt inventory, diagnostic start still automatically opens the existing fail-closed diagnostic-purpose model fallback. The network-free `Пароль` flow still has its existing explicit credential-configuration fallback for that same unavailable-inventory IP context. Valid-inventory zero/many/unmapped outcomes remain fail-closed and do not gain fallback.

Room-name results remain exact `room_id` authorities even when human-readable names collide. Autocomplete uses deterministic display-only disambiguation, preferably room address, and a neutral deterministic result discriminator if name/address are still identical. The operator's raw query remains unchanged, while a separate visible selected-room cue shows which exact current result is selected.

## Confirmed product decisions for this change

The following scope and semantics are explicit product decisions confirmed for `room-diagnostic-modern-ui`; they are not inferred from current schema limitations:

- **Warranty:** real warranty data is not implemented in this change. The permanent GUI row remains `Гарантия: Нет данных`. A future reviewed change may add an authoritative warranty source/schema mapping.
- **Occupancy:** in this change the operator-facing `Занятость` row is intentionally a **busy-by-current-VKS-call indicator**, not physical room occupancy and not calendar/booking authority. At least one current registry-relevant codec with typed `CallActivity.ACTIVE` renders `Занято`; every other case renders `Нет данных`. The GUI does not render `Свободно` from no-call evidence. Hovering the row explains that the value is formed from the codec call state.
- **Empty switches:** switches with zero attached canonical room equipment are not implemented in this change. `Нет подключенных устройств` is explicitly deferred until a future reviewed source/schema change can authoritatively establish room-level switch existence independent of equipment attachments.
- **Device-family visual redesigns:** the common room shell and accordion foundation are implemented here, but detailed expanded-screen redesigns are not. For this foundation, “existing/current/reused device-family presentation” means the current **room-mode exact-row** presentation/interaction surface and its unified-registry/current-lifecycle capabilities, not an arbitrary standalone/single-device screen for the same family. Their dedicated modern visual redesigns will be separate follow-up OpenSpec changes after this foundation reaches `master`.
- **Matrix room interaction:** current room-mode Matrix remains read-only for routing in this foundation. Existing Matrix room live/local-refresh behavior is preserved; standalone `MatrixScreen.routeRequested` is not promoted into room mode, and no Matrix room route-mutation registry binding is added. Interactive Matrix room routing belongs to `matrix-diagnostic-modern-ui`.

Current schema v4 has no warranty or occupancy columns. The warranty decision above therefore requires no schema-v4 expansion in this change. Occupancy is not stored as room metadata: exact codec model normalization projects current accepted call evidence to typed `CallActivity.ACTIVE / INACTIVE / UNKNOWN`, and room presentation consumes the typed result only through unified-registry capability authority. The derivation creates no occupancy-specific network request or booking/calendar authority.

Current canonical network enrichment associates each equipment record with optional switch IP/port evidence, but it does not represent an authoritative room-level set of empty switches. The empty-switch decision above therefore forbids fabrication while preserving all present canonical attachment evidence. Existing child port evidence is summarized on each known switch parent for the visual `Порт` column without inventing a canonical switch-port property.

Change base: `7e9fd4720d682c232e69179df7cc825afd29bd1d` (`master`).

## What Changes

- Replace the permanent IP-only target editor with one persistent search field that accepts a syntactically valid IPv4 address, a complete room name, or a room-name substring.
- Preserve exactly what the operator typed in the search field across target resolution, room diagnostics, refresh, and result rendering. Canonical IP, selected `room_id`, and model authority remain separate application state and never overwrite the raw query text.
- Add deterministic room-name autocomplete/search over valid canonical inventory:
  - zero matching rooms -> controlled no-match outcome;
  - exactly one matching room -> Enter/top Refresh may select it directly;
  - multiple matching rooms -> an explicit dropdown selection is required before diagnostics;
  - duplicate room names remain visibly distinguishable through deterministic selection labels;
  - typing or selecting a suggestion performs no device network I/O.
- Add a separate selected-room cue adjacent to the search control. It shows the exact current selection label without changing raw query text and is cleared whenever the selection becomes stale or query text changes.
- Keep the existing IP path semantics, including automatic diagnostic model fallback only when inventory itself is unavailable/unloadable/corrupt and the existing explicit `Пароль` credential-configuration fallback for that unavailable-inventory IP context.
- Add direct room-name entry semantics: the selected canonical `room_id` becomes room authority without a synthetic source record. Room membership is all canonical records for that `room_id` in deterministic canonical order.
- Redesign the common room shell around the approved self-contained visual structure:
  - application title `Диагностический модуль`;
  - baseline acceptance viewport `1440 x 900`, minimum supported `1180 x 720`;
  - upper-left room card and upper-right network-connections tree with peer width;
  - room equipment accordion below;
  - explicit common spacing/radius/typography/icon scales;
  - bottom room status/last-update presentation retained.
- Make the room card permanently present in room mode with room name, address, VIP, warranty, and occupancy rows. Current authoritative name/address/VIP are populated from inventory. Warranty remains `Нет данных` by the confirmed scope decision. `Занятость` means busy-by-current-VKS-call in this change: any current registry-relevant `ACTIVE` -> `Занято`; `INACTIVE`, `UNKNOWN`, missing, or stale evidence -> safe `Нет данных`; hover shows a local explanation that the value comes from codec call state.
- Add a model-neutral `CallActivity.ACTIVE / INACTIVE / UNKNOWN` projection at exact-model diagnostic normalization boundaries. Applicability is owned only by the same unified exact-model registry used for diagnostic/room capability dispatch; runtime presence/absence of a typed field does not decide whether a codec participates. Shared room GUI code must not classify protocol/localized strings or use substring heuristics.
- Render network connections as a switch/device tree that preserves all current canonical evidence:
  - known switch IP + known port -> exact switch parent and child port;
  - known switch IP + missing port -> exact switch parent and child `Нет данных`;
  - missing switch IP + known port -> record-bound `Коммутатор не определён` evidence branch retaining the port;
  - both missing -> no fabricated topology evidence.
- Populate the parent `Порт` column only as a deterministic display summary of non-null child attachment ports: zero -> `Нет данных`, one -> exact port, many -> comma-separated unique exact ports in child order. Children retain exact individual ports; parent summary is never canonical authority.
- Explicitly defer authoritative empty-switch presentation (`Нет подключенных устройств`) by confirmed product decision until a future source/schema change can prove a room switch with zero attached room equipment.
- Standardize every equipment top-level row as an accordion header equivalent to `expand -> class icon -> model label -> status icon/text -> IP -> overflow menu`, with baseline collapsed row height `52-64 px` and non-color status meaning.
- Integrate the current supported **room-mode exact-row** device-family presentation/interaction surfaces into the common room accordion without redesigning their family-specific internal layout. Preserve only controls/actions/capabilities already present in current room mode and authorized by the unified exact-model registry/current room lifecycle; do not substitute or promote standalone/single-device screens or signals.
- Preserve current room-mode PDU mutation/reconciliation, codec auxiliary/live behavior, Audio DSP live metering, and Matrix live/local-refresh boundaries through their existing application/controller paths. Matrix routing remains read-only in room mode in this change: no room route-mutation intent/binding is added and standalone `MatrixScreen.routeRequested` is not wired into the accordion.
- Do not introduce new device-family reference-only controls merely to match the deferred screen redesigns. Any future gain/mute/reboot/card/table/meter or interactive Matrix room-routing redesign belongs to the later device-family change that owns that screen.
- Add dark/light semantic palettes. Every application start begins in dark mode. The sun/moon toggle changes theme only for the current process, is not persisted, and must not materially change common shell/card/row geometry at a fixed window size.
- Preserve all existing credential ownership, structured fallback, one-device-at-a-time automatic room cycle, post-cycle serialized interaction, stale callback rejection, mutation/reconciliation rules, Qt-thread non-blocking guarantees, and exact-row authority.

## Target Flow

```text
operator types target query
    -> raw query remains visible unchanged
    -> classify
        valid IPv4
            -> current exact IP inventory resolution
            -> valid inventory: existing zero/one/many semantics
            -> unavailable inventory: existing automatic diagnostic fallback
        otherwise
            -> canonical room-name substring search
            -> zero / one / many distinct room_id results
            -> deterministic visibly distinguishable labels
            -> explicit room choice when many
            -> selected-room cue + hidden exact room_id authority
    -> Enter / top Refresh starts diagnostics only after one authoritative target exists
    -> room mode
        room card
            -> name/address/VIP from room authority
            -> warranty = `Нет данных`
            -> unified registry declares call-activity applicability
            -> exact-model call normalization -> typed CallActivity
            -> any registry-relevant ACTIVE -> occupancy `Занято`, otherwise `Нет данных`
        network tree
            -> exact child attachment evidence
            -> parent port display summary
        -> deterministic common equipment accordion
        -> current room-mode exact-row family presentations
            -> Matrix room projection remains read-only for routing
            -> only current room registry/lifecycle actions are preserved
        -> existing sequential acquisition
        -> existing exact-row post-cycle interaction lifecycle
```

## Capabilities

### New Capabilities

- `diagnostic-ui-presentation`: self-contained common room-shell visual contract, semantic themes, selected-room cue, room/network cards, call-derived busy presentation, switch-parent port summary, common equipment-row contract, and compatibility boundary for current room-mode expanded device presentations. Detailed family-specific expanded-screen redesign and new family capabilities are explicitly outside this capability's current change scope.

### Modified Capabilities

- `diagnostic-application-shell`: replace permanent IP-only diagnostic input with IP-or-room search while preserving the full existing IP diagnostic/credential fallback semantics.
- `equipment-inventory-snapshot`: add deterministic room-name substring search and display-only disambiguation as a storage-independent runtime query without changing schema v4.
- `room-equipment-diagnostics`: allow direct `room_id` authority from an explicit room-name selection, define source-less ordering, define deterministic shared metadata when no source record exists, and explicitly keep derived busy presentation outside canonical room metadata authority.
- `room-device-interaction-lifecycle`: treat edits to the generic target-search context as the same supersession/invalidation boundary previously owned by source-IP edits.
- `device-diagnostics-and-control`: add unified-registry-owned, model-neutral typed `CallActivity` normalization for approved codec call evidence, with exact-model mappings and unknown-by-default semantics.

## Deferred Follow-up Changes

After this foundation is implemented, independently validated, archived, and merged to `master`, create separate semantic OpenSpec changes for the device-family presentation redesigns. Expected boundaries are equivalent to:

```text
audio-diagnostic-modern-ui
matrix-diagnostic-modern-ui
codec-diagnostic-modern-ui
pdu-diagnostic-modern-ui
```

Those follow-up changes own their own visual contracts, regression coverage, manual acceptance, lifecycle review, independent validation, archive, and merge. They must build on the merged common room/accordion foundation rather than stack unarchived presentation changes onto this branch. `matrix-diagnostic-modern-ui` also owns any reviewed decision to add interactive Matrix routing to room mode.

## Impact

Implementation is expected to refactor the Qt shell and common room presentation, extend the runtime inventory query boundary with an immutable room-search projection/index, add explicit search-selection application state and visible selection presentation, extend room session construction to support an optional source record, add unified-registry call-activity bindings and exact-model typed normalization, derive only the confirmed busy-by-call presentation from them, preserve/summarize partial network evidence, and embed current room-mode exact-row device presentations inside the new common accordion without changing their device-family visual design or promoting standalone-only capabilities.

The change must not redesign credential storage or fallback, move network ownership into widgets, add new protocol commands, perform network I/O on the Qt GUI thread, change automatic room queue sequencing, introduce fuzzy model dispatch, persist the selected theme, invent warranty values, create an independent occupancy/booking source, classify call activity in shared GUI code from strings, claim room availability from no-call evidence, infer call-activity applicability from runtime field presence, fabricate switch identity or empty switches, redesign Audio DSP/Matrix/codec/PDU expanded content, add new screen-specific placeholder controls, promote standalone/single-device controls into room mode, add Matrix room route-mutation capability, or change inventory schema v4.