## Why

The current room-diagnostic architecture already provides the correct authority model: validated inventory resolution, deterministic room membership, one-shot sequential acquisition, exact per-record state, presentation-only reusable widgets, and a serialized post-cycle interaction lifecycle. The remaining product gap is primarily operator experience. The current Qt room tree is functional but visually utilitarian and the permanent top-level input is still modeled as an IP-only field.

The target product experience is a polished room-oriented desktop interface while preserving the existing tree/accordion interaction model and all network-safety contracts. The operator must be able to enter either a device IP address or a full/partial room name in one persistent search field. A device IP continues to resolve its authoritative room and open the whole room. A room-name selection establishes the room directly by canonical `room_id` without inventing a synthetic source device.

The visual redesign is reference-guided rather than pixel-exact, but the approved repository artifacts must be self-contained enough for a clean implementation/review session that has no access to the original conversation screenshots. The change therefore defines baseline viewport, proportions, spacing, typography, row density, card hierarchy, audio-meter geometry, Matrix column hierarchy, and dark/light acceptance behavior in the new `diagnostic-ui-presentation` capability.

The change preserves existing fallback semantics. For a valid IP target with unavailable/unloadable/corrupt inventory, diagnostic start still automatically opens the existing fail-closed diagnostic-purpose model fallback. The network-free `Пароль` flow still has its existing explicit credential-configuration fallback for that same unavailable-inventory IP context. Valid-inventory zero/many/unmapped outcomes remain fail-closed and do not gain fallback.

Room-name results remain exact `room_id` authorities even when human-readable names collide. Autocomplete uses deterministic display-only disambiguation, preferably room address, and a neutral deterministic result discriminator if name/address are still identical. The operator's raw query remains unchanged, while a separate visible selected-room cue shows which exact current result is selected.

Repository inspection also shows two current data-boundary limitations that this GUI change must not hide:

- canonical inventory schema v4 has `room_name`, `room_address`, `room_vip`, `switch_ip_address`, and `switch_port`, but it has no authoritative warranty or occupancy fields;
- current canonical network enrichment associates each equipment record with optional switch IP/port evidence, but it does not represent an authoritative room-level set of empty switches.

Therefore warranty/occupancy remain permanent safe no-data rows in this change. The network tree preserves every available canonical switch/port evidence state, including known port with unknown switch IP, without inventing shared switch identity. The product-reference state `Нет подключенных устройств` is explicitly deferred: current schema v4 cannot prove an unattached room switch, so this change does not fabricate or require that runtime state. A separate future reviewed source/schema change is required to make it authoritative.

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
- Redesign the room shell around the approved self-contained visual structure:
  - application title `Диагностический модуль`;
  - baseline acceptance viewport `1440 x 900`, minimum supported `1180 x 720`;
  - upper-left room card and upper-right network-connections tree with peer width;
  - room equipment accordion below;
  - explicit spacing/radius/typography/icon scales;
  - bottom room status/last-update presentation retained.
- Make the room card permanently present in room mode with room name, address, VIP, warranty, and occupancy rows. Current authoritative name/address/VIP are populated from inventory. Warranty and occupancy remain explicit `Нет данных` placeholders in this change because schema v4 has no authority for them.
- Render network connections as a switch/device tree that preserves all current canonical evidence:
  - known switch IP + known port -> exact switch parent and child port;
  - known switch IP + missing port -> exact switch parent and child `Нет данных`;
  - missing switch IP + known port -> record-bound `Коммутатор не определён` evidence branch retaining the port;
  - both missing -> no fabricated topology evidence.
  Parent Port cells are not populated from child attachment ports.
- Explicitly defer authoritative empty-switch presentation (`Нет подключенных устройств`) until a future source/schema change can prove a room switch with zero attached room equipment.
- Standardize every equipment top-level row as an accordion header equivalent to `expand -> class icon -> model label -> status icon/text -> IP -> overflow menu`, with baseline collapsed row height `52-64 px` and non-color status meaning.
- Restyle expanded device presentations while preserving existing application/controller ownership:
  - audio DSP: vertical segmented dBFS meters with defined relative geometry, selected-channel emphasis, reserved disabled gain/mute controls;
  - Matrix/IN1804: per-input table combining signal, HDCP, input name, and active routing with a defined column hierarchy; existing routing remains interactive through the current Matrix intent boundary;
  - codec and PDU: grouped card-oriented diagnostics/actions with defined primary/secondary proportions.
- Show future controls in their intended final positions only as disabled controls. They SHALL NOT call handlers, create workers, acquire sessions, or fake success.
- Add dark/light semantic palettes. Every application start begins in dark mode. The sun/moon toggle changes theme only for the current process, is not persisted, and must not materially change geometry at a fixed window size.
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
        upper room card + network tree
        -> deterministic equipment accordion
        -> existing sequential acquisition
        -> existing exact-row post-cycle interaction lifecycle
```

## Capabilities

### New Capabilities

- `diagnostic-ui-presentation`: self-contained room shell visual contract, semantic themes, selected-room cue, room/network cards, common equipment-row contract, device-specific expanded presentation, and disabled future-control placeholders.

### Modified Capabilities

- `diagnostic-application-shell`: replace permanent IP-only diagnostic input with IP-or-room search while preserving the full existing IP diagnostic/credential fallback semantics.
- `equipment-inventory-snapshot`: add deterministic room-name substring search and display-only disambiguation as a storage-independent runtime query without changing schema v4.
- `room-equipment-diagnostics`: allow direct `room_id` authority from an explicit room-name selection, define source-less ordering, and define deterministic shared metadata when no source record exists.
- `room-device-interaction-lifecycle`: treat edits to the generic target-search context as the same supersession/invalidation boundary previously owned by source-IP edits.

## Impact

Implementation is expected to refactor the Qt shell and room presentation, extend the runtime inventory query boundary with an immutable room-search projection/index, add explicit search-selection application state and visible selection presentation, extend room session construction to support an optional source record, preserve partial network evidence, and add focused GUI/presentation regression coverage plus manual dark/light baseline visual acceptance.

The change must not redesign credential storage or fallback, move network ownership into widgets, add new protocol commands, perform network I/O on the Qt GUI thread, change automatic room queue sequencing, introduce fuzzy model dispatch, persist the selected theme, invent warranty/occupancy values, fabricate switch identity, or change inventory schema v4. Populating warranty/occupancy or representing room switches with zero attached canonical devices requires a separate reviewed inventory/source-authority change.
