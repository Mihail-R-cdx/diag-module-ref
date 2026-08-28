## Why

The current room-diagnostic architecture already provides the correct authority model: validated inventory resolution, deterministic room membership, one-shot sequential acquisition, exact per-record state, presentation-only reusable widgets, and a serialized post-cycle interaction lifecycle. The remaining product gap is primarily operator experience. The current Qt room tree is functional but visually utilitarian and the permanent top-level input is still modeled as an IP-only field.

The target product experience is a polished room-oriented desktop interface while preserving the existing tree/accordion interaction model and all network-safety contracts. The operator must be able to enter either a device IP address or a full/partial room name in one persistent search field. A device IP continues to resolve its authoritative room and open the whole room. A room-name selection establishes the room directly by canonical `room_id` without inventing a synthetic source device.

The visual redesign is reference-guided rather than pixel-exact: dark card surfaces, compact equipment rows, a room card on the upper left, a network-connections tree on the upper right, device-specific expanded cards, and a session-only dark/light theme toggle. Existing supported actions remain real application intents. Controls shown for future capabilities are intentionally disabled and perform no hidden device I/O.

Repository inspection also shows two current data-boundary limitations that this GUI change must not hide:

- canonical inventory schema v4 has `room_name`, `room_address`, `room_vip`, `switch_ip_address`, and `switch_port`, but it has no authoritative warranty or occupancy fields;
- current canonical network enrichment associates room equipment with switch IP/port, but it does not represent an authoritative room-level set of empty switches.

Therefore this change reserves permanent GUI slots for warranty and occupancy and supports the empty-switch visual state, but it does not invent either data source. Warranty/occupancy render a safe no-data value until a separate approved inventory-schema change provides authority. The network tree renders only switch nodes supported by current canonical data; it never fabricates an empty switch merely to match a reference image.

Change base: `7e9fd4720d682c232e69179df7cc825afd29bd1d` (`master`).

## What Changes

- Replace the permanent IP-only target editor with one persistent search field that accepts either:
  - a syntactically valid IPv4 address;
  - a complete room name;
  - a room-name substring.
- Preserve exactly what the operator typed in the search field across target resolution, room diagnostics, refresh, and result rendering. Canonical IP, selected `room_id`, and model authority remain separate application state and never overwrite the raw query text.
- Add deterministic room-name autocomplete/search over valid canonical inventory:
  - zero matching rooms -> controlled no-match outcome;
  - exactly one matching room -> Enter/top Refresh may select it directly;
  - multiple matching rooms -> an explicit dropdown selection is required before diagnostics;
  - typing or selecting a suggestion performs no device network I/O.
- Keep the existing IP path semantics: a unique IP record with non-null `room_id` opens the complete room; a unique supported no-room record may continue through the legacy single-device path; valid-inventory zero/many IP matches remain fail-closed.
- Add direct room-name entry semantics: the selected canonical `room_id` becomes room authority without a synthetic source record. Room membership is all canonical records for that `room_id` in deterministic canonical order.
- Redesign the room shell around the approved visual structure:
  - application title `Диагностический модуль`;
  - upper-left room card;
  - upper-right network-connections tree;
  - room equipment accordion below;
  - bottom room status/last-update presentation retained.
- Make the room card permanently present in room mode with room name, address, VIP, warranty, and occupancy rows. Current authoritative name/address/VIP are populated from inventory. Warranty and occupancy remain explicit `Нет данных` placeholders in this change because schema v4 has no authority for them.
- Render network connections as a switch/device tree using current canonical `switch_ip_address` and `switch_port` evidence. A switch node contains attached room-equipment children and their ports. Missing authoritative switch-name evidence uses a safe generic label plus IP.
- Standardize every equipment top-level row as an accordion header equivalent to:

```text
expand -> class icon -> model label -> status icon/text -> IP -> overflow menu
```

  Status remains understandable without color alone. Exactly one equipment row may be expanded at a time.
- Restyle expanded device presentations while preserving existing application/controller ownership:
  - audio DSP: vertical segmented dBFS meters, selected-channel emphasis, reserved gain/mute controls;
  - Matrix/IN1804: per-input table combining signal, HDCP, input name, and active routing; existing routing remains interactive through the current Matrix intent boundary;
  - codec and PDU: card-oriented grouped diagnostics/actions following the same visual language.
- Show future controls in their intended final positions only as disabled controls. They SHALL NOT call handlers, create workers, acquire sessions, or fake success.
- Add dark/light semantic palettes. Every application start begins in dark mode. The sun/moon toggle changes theme only for the current process and is not persisted.
- Preserve all existing credential ownership, structured fallback, one-device-at-a-time automatic room cycle, post-cycle serialized interaction, stale callback rejection, mutation/reconciliation rules, Qt-thread non-blocking guarantees, and exact-row authority.

## Target Flow

```text
operator types target query
    -> raw query remains visible unchanged
    -> classify
        valid IPv4
            -> current exact IP inventory resolution
            -> room mode or supported no-room legacy mode
        otherwise
            -> canonical room-name substring search
            -> zero / one / many distinct room_id results
            -> explicit room choice when many
            -> selected room_id, no synthetic source record
    -> Enter / top Refresh starts diagnostics only after one authoritative target exists
    -> room mode
        upper room card + network tree
        -> deterministic equipment accordion
        -> existing sequential acquisition
        -> existing exact-row post-cycle interaction lifecycle
```

## Capabilities

### New Capabilities

- `diagnostic-ui-presentation`: reference-guided room shell, semantic themes, room/network cards, common equipment-row visual contract, device-specific expanded presentation, and disabled future-control placeholders.

### Modified Capabilities

- `diagnostic-application-shell`: replace permanent IP-only diagnostic input with IP-or-room search resolution while preserving legacy IP/fallback behavior where applicable.
- `equipment-inventory-snapshot`: add deterministic room-name substring search as a storage-independent runtime query without changing schema v4.
- `room-equipment-diagnostics`: allow direct `room_id` authority from an explicit room-name selection, define source-less ordering, and define deterministic shared metadata when no source record exists.
- `room-device-interaction-lifecycle`: treat edits to the generic target-search context as the same supersession/invalidation boundary previously owned by source-IP edits.

## Impact

Implementation is expected to refactor the Qt shell and room presentation, extend the runtime inventory query boundary with an immutable room-search projection/index, add explicit search-selection application state, extend room session construction to support an optional source record, and add focused GUI/presentation regression coverage.

The change must not redesign credential storage or fallback, move network ownership into widgets, add new protocol commands, perform network I/O on the Qt GUI thread, change automatic room queue sequencing, introduce fuzzy model dispatch, persist the selected theme, invent warranty/occupancy values, fabricate empty network switches, or change inventory schema v4. Populating warranty/occupancy or representing room switches with zero attached canonical devices requires a separate reviewed inventory/source-authority change.
