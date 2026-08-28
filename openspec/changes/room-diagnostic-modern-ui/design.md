## Context

Current `master` at change creation is `7e9fd4720d682c232e69179df7cc825afd29bd1d`. The room-diagnostic stack already separates application authority from Qt presentation:

- canonical inventory owns room/device evidence;
- `room_id` is authoritative room identity;
- exact canonical `diagnostic_model` owns support/dispatch;
- room acquisition is sequential and one-shot;
- per-record state is authoritative over reusable widgets;
- post-cycle live/read/mutation work is serialized and bound to the exact expanded record;
- widgets emit intent and do not own credentials, handlers, retry/fallback, sessions, or stale-operation authority.

The existing runtime inventory schema v4 exposes `room_name`, `room_address`, `room_vip`, `switch_ip_address`, and `switch_port`. It does not expose warranty or occupancy. The optional network workbook is reconciled MAC-only into per-equipment switch IP/port fields; it does not currently publish an authoritative room-level switch inventory capable of proving that a switch with no attached room equipment exists.

The GUI change therefore has two layers:

1. a real application behavior change for target search and direct room selection;
2. a presentation redesign that reuses existing device/application lifecycles and deliberately keeps future unsupported controls disabled.

## Goals

- Provide one clear target field for IP or room-name search.
- Preserve the operator's raw query text during diagnostics.
- Make direct room-name selection authoritative by canonical `room_id`, not by a fabricated source device.
- Preserve all current fail-closed multiplicity and network-safety rules.
- Present room metadata and network topology prominently above the equipment tree.
- Preserve the tree/accordion information architecture with exactly one expanded device.
- Give codec, PDU, Matrix, and audio DSP data a coherent card-based visual system.
- Preserve current Matrix/PDU/codec/audio interactive capability boundaries.
- Make dark and light themes semantic, centralized, and session-only.
- Keep reference-image proportions and visual hierarchy without requiring pixel-identical reproduction.

## Non-Goals

- No inventory schema v5.
- No new source-column mapping for warranty or occupancy.
- No new authoritative empty-switch topology source.
- No protocol implementation for controls that are currently unsupported.
- No direct handler/controller calls from new Qt widgets.
- No persistent theme preference.
- No change to credential fallback, successful-index memory, or secret boundaries.
- No parallel room network work.
- No replacement of the accordion/tree navigation model with tabs, dashboards, or independent device windows.
- No pixel-perfect screenshot tracing.

## Architecture

### 1. One application-owned target-search context

Replace the semantic concept of a permanent `source IP editor` with one application-owned target-search state. Concrete class names are implementation details, but the state SHALL be equivalent to:

```text
TargetSearchContext(
    raw_query,
    query_revision,
    mode,                  # IP or ROOM_NAME
    selected_room_id,      # optional, room-name path only
    selected_inventory_snapshot_id,
)
```

`raw_query` is presentation text supplied by the operator. It is not canonical network authority after resolution. The application stores exact resolved IP/source record or exact selected `room_id` separately.

Typing does not trigger ping, credential resolution, handler acquisition, worker submission, or device I/O. Autocomplete/search is an in-memory canonical inventory query only.

Query classification is deterministic:

```text
trim/NFC query
empty                    -> invalid/no target
valid dotted IPv4        -> IP mode
anything else non-empty  -> ROOM_NAME mode
```

The field remains exactly as typed for display. Resolution code may normalize a copy but does not rewrite the editor text.

### 2. Deterministic room-name search

`EquipmentInventory` gains a storage-independent query equivalent to `find_rooms_by_name(query)`.

Search uses canonical records with non-null `room_id` and nonblank `room_name`. Matching is Unicode NFC + trim + `casefold()` substring matching. It is deliberately not fuzzy matching, token similarity, transliteration, edit distance, or device-model recognition.

One room result corresponds to one distinct canonical `room_id`. If records under one room ID carry multiple nonblank room names, any of those names may cause that room to match, but the room appears only once. The display label for that result is the first nonblank `room_name` in canonical `record_id` order. Distinct room IDs are never merged merely because their display names are equal.

Results are deterministic, ordered by casefolded display label and then canonical `room_id`.

For efficient repeated autocomplete, inventory construction should precompute an immutable room-search projection rather than rescan/renormalize the complete record set for every keystroke. The exact data structure is not normative.

### 3. Search selection and start semantics

For room-name mode:

```text
zero distinct room_id matches
    -> controlled no-match state

one distinct room_id match
    -> Enter/top Refresh may use it directly

multiple distinct room_id matches
    -> dropdown is shown
    -> operator must select one exact room result
    -> no device I/O occurs merely from selection
```

The selected `room_id` is stored separately from the raw query. Selecting `Переговорная 305` after typing `Перег` does not replace `Перег` in the editor.

Editing the raw query increments query revision and invalidates any prior room selection. A stale dropdown selection from an older query revision cannot start diagnostics.

Top Refresh against an unchanged multi-match query may reuse the currently selected `room_id` only if that room still exists in the current valid inventory and remains a member of the current candidate set. Otherwise the selection becomes invalid and a new explicit choice is required.

### 4. IP path remains fail-closed

A valid IPv4 query continues through current IP multiplicity rules:

- zero canonical matches -> controlled not found;
- many -> controlled ambiguous;
- exactly one with non-null `room_id` -> room mode for the whole room;
- exactly one with null `room_id` and registered model -> legacy single-device path;
- exactly one no-room unsupported/null model -> controlled unsupported/unmapped outcome.

Manual model fallback remains available only for an IP-mode request when inventory itself is unavailable/unloadable/corrupt under the existing structured contract. Room-name search requires valid inventory and never guesses a room/model when inventory is unavailable.

`Пароль` remains network-free credential configuration. It is available only when the current query is a resolvable IP target under the existing exact-model configuration contract; a room-name query does not choose one room device as credential authority.

### 5. Direct room selection has no synthetic source record

An explicit room-name result establishes room mode through:

```text
selected current inventory snapshot
-> exact selected room_id
-> find_room_equipment(room_id)
-> RoomDiagnosticSession with source_record_id = None (or equivalent)
```

No record is promoted to source merely because it sorts first, has an IP, is supported, is a codec/PDU, or supplied a display name match.

IP-entry room mode retains source-record semantics. Direct room-entry mode has no source record.

Membership/queue ordering becomes:

```text
IP room entry:
    exact unique source record first
    then every other room record by ascending record_id

room-name entry:
    every room record by ascending record_id
```

Same-room duplicate-IP ambiguity and all row eligibility rules remain unchanged.

### 6. Shared room metadata with and without a source

Room identity always remains exact canonical `room_id` and is not shown as operator-facing identity.

For `room_name`, `room_address`, and `room_vip` independently:

- IP-entry room mode uses existing source-first evidence and canonical-order fallback;
- direct room-name entry has no source evidence, so it uses the first usable value in canonical `record_id` order;
- boolean `false` remains meaningful VIP data;
- differing same-room display values do not vote, merge rooms, or become identity conflicts.

The room presentation card also contains `Гарантия` and `Занятость` rows. They are presentation reservations only in this change. Because current schema v4 contains no authoritative fields, both render `Нет данных`. Implementation SHALL NOT derive them from unrelated columns, timestamps, room text, or device values.

### 7. Top shell and visual hierarchy

The window title is `Диагностический модуль`.

The top application toolbar follows the reference hierarchy:

```text
Помещения и оборудование
[ search by IP or room name ... ] [ Обновить ] [ Действия ] [ theme toggle ]
```

The exact pixel dimensions are not normative. Relative proportions, compact density, spacing rhythm, subtle bordered cards, rounded corners, and clear primary/secondary typography are normative design intent.

`Действия` may host existing application-level actions such as credential configuration; moving an existing action into a menu is presentation only and does not change its application contract.

Theme switching uses centralized semantic tokens. Per-widget hard-coded dark/light color forks should be avoided.

### 8. Upper room area

Room mode renders two peer cards above the equipment accordion with approximately equal horizontal weight at normal desktop width:

```text
left:  room summary
right: network connections
```

The room summary displays:

```text
room icon + room name + VIP badge (when true)
Адрес: ...
Гарантия: ...
Занятость: ...
```

A room-card refresh icon, if implemented to match the visual reference, is an alias of top full Refresh. It SHALL NOT create a second refresh lane or bypass the existing room lifecycle.

Missing room name/address uses existing safe no-data presentation. VIP false is not displayed as true; implementation may omit the badge and retain textual/non-color semantics elsewhere. Warranty/occupancy are always present as rows and show `Нет данных` under current schema.

### 9. Network-connections tree

The right card is a real tree presentation, not a flat summary table. It uses columns equivalent to:

```text
Коммутатор (IP) / Устройства | Порт
```

Current canonical v4 projection groups exact room records by non-null `switch_ip_address`. For each authoritative switch node:

- the parent displays a safe switch label and IP;
- children display attached room equipment and that record's `switch_port`;
- attached children are deterministic by canonical `record_id`;
- a missing port uses a safe no-data value;
- expanding/collapsing this topology tree is presentation-only and starts no device I/O.

A user-friendly switch name MAY be used only when current canonical inventory can resolve safe unique display evidence for that exact switch IP. Otherwise the label is generic, for example `Коммутатор (10.10.0.2)`. Model/source substrings SHALL NOT become network authority.

The visual component supports a `Нет подключенных устройств` child for an authoritative switch node whose child set is empty. Current schema v4 does not provide an authoritative room-level set of unattached switches, so this change SHALL NOT fabricate such nodes. Adding real empty switches requires a separate source/schema authority change.

### 10. Common equipment row and accordion

Every room equipment record uses one top-level visual template equivalent to:

```text
chevron | class icon | model label | status cue + status text | IP | overflow
```

The model label uses exact diagnostic model where available and the existing safe display fallback otherwise. The IP column uses canonical IP or the existing no-data label.

Status is never conveyed by color alone. Text/non-color cues remain present for connected, waiting, connection failure, unsupported, missing IP, ambiguous IP, connection lost, and other approved row states.

Exactly one equipment row may be expanded. Expanding another row collapses the current row under the existing accordion behavior. Presentation changes do not reorder the automatic room queue.

The overflow control may expose only actions authorized by current application capability/state. If no action is available, it remains disabled or contains no actionable item; it must never become an alternate network authority.

### 11. Expanded device cards remain presentation boundaries

Expanded content is rebuilt/projected from exact per-record state. New layouts do not store hidden authoritative device state and do not own handlers, credentials, sessions, timers, fallback cursors, or request generations.

Existing real actions stay connected to existing application intents and lifecycle gates. Visual restyling SHALL NOT replace them with direct handler calls.

Future-control placeholders are allowed only when:

- they are visually disabled;
- they emit no network/application mutation intent;
- they do not start timers/workers;
- they do not fake a successful result;
- they can later be activated only by a separate approved capability change.

### 12. Audio DSP visual contract

Audio DSP expanded presentation uses the supplied visual language:

- separate input/source and output/destination meter groups;
- vertical segmented level meters;
- live/read values displayed in dBFS;
- semantic low/medium/high meter zones using green/yellow/orange-style theme tokens;
- selected-channel emphasis by border/background in addition to meter color;
- reserved `+`, `-`, gain value, and `Mute` controls adjacent to the selected channel.

Meter segmentation and colors do not alter underlying dBFS values or polling semantics. Existing supported live metering remains owned by the current application lifecycle. Gain/mute controls stay disabled until a separately approved state-changing capability exists for that model/path.

### 13. Matrix visual contract

Matrix/IN1804 expanded presentation uses one per-input table combining at least:

```text
input number
signal presence/state
HDCP state
input name
active/current routing state
```

Existing Matrix routing remains interactive where current capability/state allows it. A route click continues to emit non-secret Matrix intent through the existing Matrix screen/controller boundary and never calls the handler directly.

Signal/HDCP/current-route status uses text/non-color cues as well as semantic icons/color.

### 14. Codec and PDU visual contract

Codec and PDU expanded presentations use the same card hierarchy as the references: grouped general information/status, device-specific live/read sections, and a visually separate actions area.

Existing supported actions remain active only under their existing lifecycle rules. Examples already supported by production, such as PDU outlet control/bulk actions, Matrix routing, codec call-log access, or approved local refresh, are not disabled merely because the GUI is restyled.

Reference-only actions that lack production capability, such as a generic reboot button or unimplemented codec volume mutation, remain visible only as disabled placeholders when included in the target layout.

### 15. Theme lifecycle

Dark mode is the startup default on every process launch. The theme toggle switches between dark and light semantic palettes for the current process only.

No theme preference is written to disk, settings, registry, environment, inventory, credentials, or another persistence mechanism. Restart always returns to dark mode.

The control uses sun/moon visual state so the current/alternate theme is understandable without relying on color alone. Theme change is presentation-only and SHALL NOT invalidate room generations, stop live, start refresh, modify credentials, or perform device network I/O.

Both themes preserve the same information hierarchy, layout proportions, disabled-state clarity, focus visibility, and text contrast expectations.

### 16. Search edits reuse existing supersession safety

The target-search editor replaces the source-IP editor as a context-changing control. Editing the query after room completion immediately invalidates current room/live/pending-start authority and clears room/tree/cache presentation under the existing bounded cleanup rules. Editing alone starts no device I/O.

During lifecycle states where source-IP editing is currently blocked (for example Local Refresh or confirmed mutation through reconciliation), target-search editing is blocked instead. Top full Refresh repeats target resolution from current inventory and current unchanged search selection; it does not rely on old widgets as authority.

### 17. Legacy no-room mode remains compatible

A supported unique IP record with `room_id = null` retains the existing legacy single-device diagnostic/interactive path. The modern top toolbar/theme applies globally, but no synthetic room card, room network tree, or room equipment accordion is created for that no-room target solely to satisfy the new room layout.

## Risks / Trade-offs

- **Partial-room-name ambiguity:** handled by explicit room-level dropdown selection and exact `room_id` storage.
- **Stale autocomplete selection:** query revision + inventory snapshot identity prevents an old suggestion from becoming authority.
- **Same room ID with conflicting display names:** any name may match search, but result identity remains one `room_id`; display remains deterministic.
- **Visual placeholders mistaken for working controls:** placeholders are explicitly disabled and have regression coverage proving no intent/network call.
- **Theme QSS duplication:** mitigate with semantic token/palette generation rather than independent widget-specific style files.
- **Missing warranty/occupancy authority:** show explicit no-data; do not expand inventory scope silently.
- **Empty-switch reference state unavailable from v4:** do not fabricate topology; treat source expansion as a separate change.

## Validation Strategy

Architecture validation:

```powershell
.\openspec.cmd validate room-diagnostic-modern-ui --strict
.\openspec.cmd validate --all --strict
git diff --check
git diff --cached --check
```

Implementation validation must include focused search/presentation tests plus the full offline test suite. Because this change adds a new root capability and modifies existing root requirements, independent validation must perform the disposable archive-applicability check from `origin/agent/room-diagnostic-modern-ui` before `READY FOR ARCHIVE`.
