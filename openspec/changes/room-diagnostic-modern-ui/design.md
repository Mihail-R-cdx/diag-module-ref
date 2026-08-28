## Context

Current `master` at change creation is `7e9fd4720d682c232e69179df7cc825afd29bd1d`. The room-diagnostic stack already separates application authority from Qt presentation:

- canonical inventory owns room/device evidence;
- `room_id` is authoritative room identity;
- exact canonical `diagnostic_model` owns support/dispatch;
- room acquisition is sequential and one-shot;
- per-record state is authoritative over reusable widgets;
- post-cycle live/read/mutation work is serialized and bound to the exact expanded record;
- widgets emit intent and do not own credentials, handlers, retry/fallback, sessions, or stale-operation authority.

The existing runtime inventory schema v4 exposes `room_name`, `room_address`, `room_vip`, `switch_ip_address`, and `switch_port`. It does not expose warranty or occupancy. Warranty is explicitly deferred by product decision. Occupancy in this change is not added to inventory: it is a presentation-only derivation from current accepted codec call-state evidence already held in exact room-row application state. The optional network workbook is reconciled MAC-only into per-equipment switch IP/port fields; it does not currently publish an authoritative room-level switch inventory capable of proving that a switch with no attached room equipment exists, and empty-switch presentation is explicitly deferred by product decision.

The GUI change therefore has two layers:

1. a real application behavior change for target search and direct room selection;
2. a presentation redesign that reuses existing device/application lifecycles and deliberately keeps future unsupported controls disabled.

The original product screenshots are design inputs but are not repository authority. This design and `diagnostic-ui-presentation/spec.md` therefore encode enough relative geometry and hierarchy for a clean Codex/reviewer session to implement and evaluate the target without needing those screenshots.

## Goals

- Provide one clear target field for IP or room-name search.
- Preserve the operator's raw query text during diagnostics.
- Make duplicate human-readable room names safely distinguishable while keeping exact hidden `room_id` authority.
- Make direct room-name selection authoritative by canonical `room_id`, not by a fabricated source device.
- Preserve the full current fail-closed IP multiplicity, diagnostic fallback, credential fallback, and network-safety rules.
- Present room metadata and all available canonical network topology evidence prominently above the equipment tree.
- Derive the room `Занятость` presentation from existing accepted codec call state without introducing a booking source or occupancy-specific device I/O.
- Preserve the tree/accordion information architecture with exactly one expanded device.
- Give codec, PDU, Matrix, and audio DSP data a coherent card-based visual system.
- Preserve current Matrix/PDU/codec/audio interactive capability boundaries.
- Make dark and light themes semantic, centralized, geometry-stable, and session-only.
- Keep the approved reference proportions and visual hierarchy without requiring pixel-identical reproduction.

## Non-Goals

- No inventory schema v5.
- No warranty source or warranty-data implementation in this change; `Гарантия` remains a visible `Нет данных` row.
- No booking/calendar integration and no independent occupancy poll/source; occupancy is derived only from existing accepted codec call-state evidence.
- No new authoritative room-level switch source and no data-driven unattached-switch/`Нет подключенных устройств` state in this change.
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
    selected_label,        # presentation-only, never identity
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

### 2. Deterministic room-name search and visible disambiguation

`EquipmentInventory` gains a storage-independent query equivalent to `find_rooms_by_name(query)`.

Search uses canonical records with non-null `room_id` and nonblank `room_name`. Matching is Unicode NFC + trim + `casefold()` substring matching. It is deliberately not fuzzy matching, token similarity, transliteration, edit distance, or device-model recognition.

One room result corresponds to one distinct canonical `room_id`. If records under one room ID carry multiple nonblank room names, any of those names may cause that room to match, but the room appears only once.

For each result, presentation evidence is derived in canonical `record_id` order:

```text
display_name     = first nonblank room_name
display_address  = first nonblank room_address or null
selection_label  = display_name + optional address + optional neutral discriminator
```

Address is display-only disambiguation and never creates a search match. When several distinct room IDs still produce the same normalized name/address label, append a neutral deterministic `Вариант N` based on already deterministic result ordering. This ordinal is not persisted and never replaces `room_id` authority.

Results are ordered by casefolded display name, then casefolded display address with consistent null ordering, then canonical `room_id`.

For efficient repeated autocomplete, inventory construction should precompute an immutable room-search projection rather than rescan/renormalize the complete record set for every keystroke. The exact data structure is not normative.

### 3. Search selection and start semantics

For room-name mode:

```text
zero distinct room_id matches
    -> controlled no-match state

one distinct room_id match
    -> Enter/top Refresh may use it directly
    -> visible selected-room cue is populated

multiple distinct room_id matches
    -> dropdown is shown with distinguishable selection labels
    -> operator must select one exact room result
    -> selected-room cue is populated
    -> no device I/O occurs merely from selection
```

The selected `room_id` and selected label are stored separately from the raw query. Selecting a room after typing `Перег` does not replace `Перег` in the editor.

The selected-room cue is immediately adjacent to or otherwise directly associated with the search editor. It is visibly subordinate to the raw editor but plainly identifies which current result owns authority. Editing the raw query increments query revision, clears the cue, and invalidates prior room selection.

Top Refresh against an unchanged multi-match query may reuse the currently selected `room_id` only if that room still exists in current valid inventory and remains a member of the current candidate set. Otherwise the selection/cue is invalidated and a new explicit choice is required.

### 4. IP path preserves the complete existing fallback contract

A valid IPv4 query continues through current IP multiplicity rules:

- zero canonical matches -> controlled not found, no fallback while inventory is valid;
- many -> controlled ambiguous, no fallback while inventory is valid;
- exactly one with non-null `room_id` -> room mode for the whole room;
- exactly one with null `room_id` and registered model -> legacy single-device path;
- exactly one no-room unsupported/null model -> controlled unsupported/unmapped outcome, no fallback while inventory is valid.

When inventory is unavailable/unloadable/corrupt for a valid IP diagnostic start, the application automatically opens the existing fail-closed diagnostic-purpose model fallback. Only a new explicit model selection and `Подключиться` confirmation bound to that request may create fallback authority; it is not reused implicitly later.

`Пароль` remains network-free credential configuration. With valid inventory, exactly one IP record with an exact registered model may open existing model-wide credential configuration; valid-inventory zero/many/null/unsupported results remain safe errors with no fallback. When inventory is unavailable/unloadable/corrupt for a valid IP target, the existing explicit credential-configuration fallback may be used under its current purpose-bound contract. Room-name mode uses neither diagnostic nor credential fallback.

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

### 6. Shared room metadata and derived occupancy

Room identity always remains exact canonical `room_id` and is not shown as operator-facing identity.

For `room_name`, `room_address`, and `room_vip` independently:

- IP-entry room mode uses existing source-first evidence and canonical-order fallback;
- direct room-name entry has no source evidence, so it uses the first usable value in canonical `record_id` order;
- boolean `false` remains meaningful VIP data;
- differing same-room display values do not vote, merge rooms, or become identity conflicts.

The room card also contains `Гарантия` and `Занятость` rows.

`Гарантия` is intentionally not implemented as data in this change and renders `Нет данных`. No inventory/schema expansion or inference is allowed for warranty here.

`Занятость` is derived from current accepted non-stale normalized codec call-state evidence already present in exact room-row application state. At least one proven active call makes the room `Занято`. `Свободно` is shown only when every relevant call-capable codec row has current accepted evidence proving no active call. Otherwise the safe presentation is `Нет данных`. This is presentation-only derivation: it creates no occupancy-specific network operation, timer, worker, handler/session acquisition, or credential flow.

The occupancy row/value exposes a local hover tooltip/popup equivalent to `Занятость определяется по текущему состоянию звонка кодека.` It does not claim booking/calendar authority.

### 7. Self-contained visual scale

The normative visual acceptance baseline is `1440 x 900` logical pixels. The minimum supported window is `1180 x 720`. Below baseline width/height, controlled reflow and vertical scrolling are permitted; required controls must remain reachable.

At baseline the common scale is:

```text
outer margin                      20-28 px
major section gap                 16-24 px
card padding                      16-20 px
card radius                       8-12 px
toolbar/control height            44-56 px
collapsed equipment row height    52-64 px
body text                         10-11 pt
secondary text                    9-10 pt
section heading                   12-14 pt
page heading                      18-22 pt
row icon                          18-22 px
section icon                      18-24 px
room hero icon                    28-36 px
```

The search area including selected-room cue occupies approximately 45-60% of usable toolbar width. Top actions remain compact.

The upper room and network cards are peers: aligned tops, approximately equal width, ratio within `0.9:1` to `1.1:1` at baseline. They must not degenerate into one full-width card plus one narrow sidebar.

Theme changes at a fixed window size must preserve this geometry and hierarchy.

### 8. Upper room area

Room mode renders two peer cards above the equipment accordion:

```text
left:  room summary
right: network connections
```

The room summary displays room icon + room name + VIP badge (when true), address, warranty, and occupancy. Room identity/name is strongest; the remaining rows are secondary. Warranty remains `Нет данных` in this change. Occupancy uses the accepted codec-call derivation defined above and exposes its explanatory hover tooltip.

A room-card refresh icon, if implemented, is an alias of top full Refresh and never creates a second refresh lane.

### 9. Network-connections tree preserves partial canonical evidence and summarizes child ports

The right card is a real tree with columns equivalent to:

```text
Коммутатор (IP) / Устройства | Порт
```

Canonical cases are exact:

```text
IP known, port known
    parent = exact switch IP
    child  = exact equipment + known port

IP known, port null
    parent = exact switch IP
    child  = exact equipment + `Нет данных`

IP null, port known
    parent-like evidence branch = `Коммутатор не определён`
    branch is bound to that exact equipment record only
    child shows exact equipment + known port
    no grouping with another unknown-switch record

IP null, port null
    record contributes no network-tree topology evidence
```

Switch-IP parents group exact room records by switch IP and order children by `record_id`. A safe friendly switch name may be shown only from unique canonical evidence; otherwise use `Коммутатор (<IP>)`.

The parent `Порт` cell is a display summary of child attachment ports, not canonical switch state. Collect non-null child `switch_port` values in canonical child order and de-duplicate by first occurrence: zero known ports -> `Нет данных`; one -> that exact port; several -> comma-separated exact ports. Every child retains its exact port/no-data presentation. A record-bound unknown-switch branch may repeat its one exact known port in the parent-like cell.

If no room record contributes switch IP or port evidence, show `Нет данных о сетевых подключениях`.

By explicit product decision, `Нет подключенных устройств` for an unattached room switch is not implemented in this change. Current schema v4 cannot prove that state and it must not be fabricated. A future source/schema change must first publish authoritative room-level switch inventory.

### 10. Common equipment row and accordion

Every room equipment record uses:

```text
chevron | class icon | model label | status cue + status text | IP | overflow
```

At baseline, collapsed rows are `52-64 px` high. Model text receives the largest flexible width; status and IP remain one-line under ordinary data; overflow remains secondary.

Status is never conveyed by color alone. Exactly one equipment row may be expanded. Expanding another collapses the previous row without changing automatic queue order.

### 11. Expanded device cards remain presentation boundaries

Expanded content is rebuilt/projected from exact per-record state. New layouts do not own handlers, credentials, sessions, timers, fallback cursors, or request generations.

At baseline, where a primary data card sits beside a secondary action/status card, use approximately `55-65% / 35-45%` width with `12-20 px` gaps. Full-width tables/meter groups may sit below. Below minimum supported width, reflow vertically rather than hiding controls.

Future placeholders are allowed only if disabled and incapable of emitting network/application mutation intent, starting workers/timers, or faking success.

### 12. Audio DSP visual contract

Audio DSP expanded presentation uses separate input/source and output/destination groups, vertical segmented dBFS meters, semantic green/yellow/orange zones, numeric dBFS text, selected-channel emphasis, and reserved disabled `+ / - / value / Mute` controls.

At baseline an ordinary meter is `16-22 px` wide and `180-240 px` tall with `10-16 px` between channels. The selected-channel control strip uses approximately `32-40 px` control height. These geometry rules do not change the underlying numeric value or polling lifecycle.

### 13. Matrix visual contract

Matrix/IN1804 uses one per-input table with:

```text
input number      8-12%
signal            16-20%
HDCP              16-20%
input name        30-40%
route/current     18-24%
```

Localized-text adjustment is allowed, but input name stays the widest semantic column and number stays compact. Existing routing remains interactive through the current non-secret Matrix intent boundary.

### 14. Codec and PDU visual contract

Codec and PDU expanded views use grouped bordered cards: primary identity/status, device-specific live/read data, and secondary actions. Where adjacent summary/action cards are used, actions/status occupy about `35-45%`, primary information the remainder. PDU outlet tables and comparable main data tables may occupy full-width rows below.

Existing supported actions remain real under current lifecycle rules. Reference-only generic reboot/volume/gain/mute controls remain disabled until separate capabilities exist.

### 15. Theme lifecycle

Dark mode is the startup default on every process launch. The sun/moon control toggles dark/light semantic palettes only for the current process; nothing persists.

At the same window size theme switching must not intentionally resize/reflow toolbar, cards, rows, meters, or tables. Both themes preserve primary/secondary hierarchy, disabled-state clarity, focus indication, borders, and text/status distinguishability.

Theme change is presentation-only: no generation invalidation, live restart, refresh, credential change, or device I/O.

### 16. Search edits reuse existing supersession safety

The target-search editor replaces the source-IP editor as the context-changing control. Editing after room completion immediately invalidates current room/live/pending-start authority and clears room/tree/cache presentation under existing bounded cleanup rules. Editing alone starts no device I/O.

During lifecycle states where source-IP editing is currently blocked, target-search editing is blocked instead. Top full Refresh repeats target resolution from current inventory and current unchanged selected-room context; stale selection is never reused.

### 17. Legacy no-room mode remains compatible

A supported unique IP record with `room_id = null` retains the existing legacy single-device diagnostic/interactive path. The modern toolbar/theme applies globally, but no synthetic room card, room network tree, or room equipment accordion is created solely to satisfy the new room layout.

## Risks / Trade-offs

- **Partial-room-name ambiguity:** explicit selection, display address, neutral deterministic discriminator, and separate visible selected-room cue.
- **Stale autocomplete selection:** query revision + inventory snapshot identity; cue clears with authority.
- **Fallback regression:** full existing unavailable-inventory diagnostic and credential-configuration fallback semantics are restated in the modified shell requirement.
- **Occupancy freshness/authority:** only current accepted non-stale codec call-state evidence can drive `Занято`/`Свободно`; incomplete evidence degrades to `Нет данных` rather than guessing. No booking semantics are implied.
- **Warranty gap:** explicitly user-approved as not implemented; the visible row remains `Нет данных`.
- **Partial network evidence loss:** all three meaningful partial combinations are specified; known port is never discarded merely because switch IP is missing.
- **Switch parent port semantics:** parent value is only a deterministic summary of child attachment evidence, never canonical switch authority.
- **Empty-switch reference gap:** explicitly user-approved as deferred rather than simulated from nonexistent authority.
- **Visual drift across clean sessions:** repository-local baseline geometry, typography, icon, meter, table, and card proportion contract plus manual screenshot acceptance.
- **Future controls mistaken for working:** disabled with zero intent/I/O regression coverage.
- **Theme QSS duplication:** centralized semantic token/palette generation.

## Validation Strategy

Architecture validation:

```powershell
.\openspec.cmd validate room-diagnostic-modern-ui --strict
.\openspec.cmd validate --all --strict
git diff --check
git diff --cached --check
```

Implementation validation must include focused search/presentation tests plus the full offline test suite.

Manual visual acceptance is mandatory during implementation validation: launch the GUI detached per `RULES.md`, set the window to the baseline `1440 x 900`, capture local non-committed screenshots for dark and light room mode, and compare them against the repository-local proportion/hierarchy contract. The check must explicitly inspect upper-card peer width, toolbar/search dominance, row density, occupancy display/tooltip, switch-parent port summary, expanded card hierarchy, audio-meter geometry, Matrix column hierarchy, and geometry stability across theme switch. These screenshots are local validation aids and SHALL NOT become tracked evidence unless separately requested.

Because this change adds a new root capability and modifies existing root requirements, independent validation must perform the disposable archive-applicability check from current `origin/agent/room-diagnostic-modern-ui` before `READY FOR ARCHIVE`.