## Context

Current `master` at change creation is `7e9fd4720d682c232e69179df7cc825afd29bd1d`. The room-diagnostic stack already separates application authority from Qt presentation:

- canonical inventory owns room/device evidence;
- `room_id` is authoritative room identity;
- exact canonical `diagnostic_model` owns support/dispatch;
- room acquisition is sequential and one-shot;
- per-record state is authoritative over reusable widgets;
- post-cycle live/read/mutation work is serialized and bound to the exact expanded record;
- widgets emit intent and do not own credentials, handlers, retry/fallback, sessions, or stale-operation authority.

The existing runtime inventory schema v4 exposes `room_name`, `room_address`, `room_vip`, `switch_ip_address`, and `switch_port`. It does not expose warranty or occupancy. Three product decisions are explicitly confirmed for this change rather than inferred from those schema gaps: real warranty data is not implemented and the visible row remains `Нет данных`; the user-visible `Занятость` row means only busy-by-current-VKS-call and is not physical/calendar occupancy; and room switches with zero attached canonical equipment are deferred until a future room-level switch authority exists. The optional network workbook is reconciled MAC-only into per-equipment switch IP/port fields and cannot currently prove an unattached room switch.

This change is deliberately a **common room UI foundation**, not a bundle of four device-family redesigns. It has two layers:

1. a real application behavior change for target search and direct room selection;
2. a common shell/presentation foundation that preserves the current **room-mode exact-row** Audio DSP, Matrix/IN1804, codec, and PDU presentation/interaction surfaces inside the room accordion without redesigning their family-specific interiors or promoting standalone/single-device capabilities.

Detailed expanded-screen redesigns are deferred to later semantic OpenSpec changes after this foundation is merged to `master`. The expected follow-up boundaries are equivalent to `audio-diagnostic-modern-ui`, `matrix-diagnostic-modern-ui`, `codec-diagnostic-modern-ui`, and `pdu-diagnostic-modern-ui`.

The original product screenshots are design inputs but are not repository authority. This design and `diagnostic-ui-presentation/spec.md` therefore encode enough relative geometry and hierarchy for a clean Codex/reviewer session to implement and evaluate the **foundation shell** without needing those screenshots.

## Goals

- Provide one clear target field for IP or room-name search.
- Preserve the operator's raw query text during diagnostics.
- Make duplicate human-readable room names safely distinguishable while keeping exact hidden `room_id` authority.
- Make direct room-name selection authoritative by canonical `room_id`, not by a fabricated source device.
- Preserve the full current fail-closed IP multiplicity, diagnostic fallback, credential fallback, and network-safety rules.
- Present room metadata and all available canonical network topology evidence prominently above the equipment tree.
- Derive only the room `Занято` busy-by-call indication from existing accepted typed codec call activity, without introducing a booking source, string heuristics, or occupancy-specific device I/O.
- Preserve the tree/accordion information architecture with exactly one expanded device.
- Define one common equipment-row/header and shell visual system while keeping current room-mode exact-row device-family presentations functional and presentation-only.
- Make dark and light themes semantic, centralized, geometry-stable, and session-only for the common shell.
- Keep approved foundation proportions and visual hierarchy without requiring pixel-identical reproduction.

## Non-Goals

- No inventory schema v5.
- No warranty source or warranty-data implementation in this change; `Гарантия` remains a visible `Нет данных` row by confirmed product decision.
- No booking/calendar integration and no independent occupancy poll/source.
- No claim that `CallActivity.INACTIVE` means the physical room is free; `Свободно` is not emitted by this change.
- No shared room-GUI parsing of model-specific/localized call-state strings.
- No runtime inference of call-activity applicability from payload/field presence; the unified exact-model registry remains authority.
- No new authoritative room-level switch source and no data-driven unattached-switch/`Нет подключенных устройств` state in this change by confirmed product decision.
- No Audio DSP family-specific redesign: no new segmented-meter geometry contract, selected-channel visual redesign, or new gain/mute placeholder layout in this change.
- No Matrix/IN1804 family-specific redesign: no new per-input visual table/column hierarchy contract and no new room-mode route-mutation capability in this change.
- No promotion of standalone/single-device screens, controls, signals, or capabilities into room mode merely because they belong to the same device family.
- No codec family-specific grouped-card redesign in this change.
- No PDU family-specific grouped-card/outlet redesign in this change.
- No new screen-specific reference-only controls merely to match deferred screenshots.
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

### 6. Shared room metadata and registry-owned typed call-activity busy projection

Room identity always remains exact canonical `room_id` and is not shown as operator-facing identity.

For `room_name`, `room_address`, and `room_vip` independently:

- IP-entry room mode uses existing source-first evidence and canonical-order fallback;
- direct room-name entry has no source evidence, so it uses the first usable value in canonical `record_id` order;
- boolean `false` remains meaningful VIP data;
- differing same-room display values do not vote, merge rooms, or become identity conflicts.

The room card also contains `Гарантия` and `Занятость` rows.

`Гарантия` is intentionally not implemented as data in this change and renders `Нет данных`. This is a confirmed scope decision, not an inferred consequence of schema v4. No inventory/schema expansion or inference is allowed for warranty here.

The user-facing `Занятость` row in this change means only busy-by-current-VKS-call. It is not physical room availability and not calendar/booking occupancy authority.

Applicability is owned by the same unified exact-model registry used for diagnostic/room capability dispatch. A room codec is relevant to busy aggregation exactly when its exact registration declares the required available call-activity normalization/projection binding. Runtime presence or absence of a call field or `CallActivity` value never decides relevance and no second occupancy-model list exists.

Every registry-relevant exact codec projects its current accepted call evidence to application-owned `CallActivity.ACTIVE`, `CallActivity.INACTIVE`, or `CallActivity.UNKNOWN` before room aggregation. Model-specific parser/adapter normalization owns any mapping from protocol or legacy normalized values; shared room/presentation code never classifies localized or protocol strings. Missing/stale/failed/contradictory/unrecognized evidence produces `UNKNOWN` while the codec remains relevant.

`Занятость` renders `Занято` when at least one current registry-relevant room codec has `CallActivity.ACTIVE`. Every other case, including all codecs being `INACTIVE` or one or more relevant codecs being `UNKNOWN`, renders `Нет данных`. The change intentionally does not render `Свободно`, because a codec not being in a call does not prove physical room availability.

This projection is presentation-only: it creates no occupancy-specific network operation, timer, worker, handler/session acquisition, or credential flow. The occupancy row/value exposes a local hover tooltip/popup equivalent to `Занятость определяется по текущему состоянию звонка кодека.` It does not claim booking/calendar authority.

### 7. Self-contained foundation visual scale

The normative visual acceptance baseline is `1440 x 900` logical pixels. The minimum supported window is `1180 x 720`. Below baseline width/height, controlled reflow and vertical scrolling are permitted; required foundation controls must remain reachable.

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

Theme changes at a fixed window size must preserve this common shell/card/row geometry and hierarchy. No family-specific Audio/Matrix/codec/PDU internal geometry is defined by this change.

### 8. Upper room area

Room mode renders two peer cards above the equipment accordion:

```text
left:  room summary
right: network connections
```

The room summary displays room icon + room name + VIP badge (when true), address, warranty, and occupancy. Room identity/name is strongest; the remaining rows are secondary. Warranty remains `Нет данных` in this change. Occupancy uses the registry-owned typed codec-call busy projection defined above and exposes its explanatory hover tooltip.

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

By confirmed product decision, `Нет подключенных устройств` for an unattached room switch is not implemented in this change. This is an intentional scope decision, not an inference from the current schema. Current schema v4 also cannot prove that state and it must not be fabricated. A future source/schema change must first publish authoritative room-level switch inventory.

### 10. Common equipment row and accordion

Every room equipment record uses:

```text
chevron | class icon | model label | status cue + status text | IP | overflow
```

At baseline, collapsed rows are `52-64 px` high. Model text receives the largest flexible width; status and IP remain one-line under ordinary data; overflow remains secondary.

Status is never conveyed by color alone. Exactly one equipment row may be expanded. Expanding another collapses the previous row without changing automatic queue order.

The overflow action exposes only current application-authorized actions. If the current foundation does not have a valid action for that row/context, overflow remains disabled/non-actionable; it does not create a new device I/O path.

### 11. Current room-mode device-family presentations remain compatible and out of redesign scope

For this foundation, the terms `existing`, `current`, and `reused` device-family presentation refer specifically to the **current room-mode exact-row presentation/interaction surface** produced by the room diagnostic presentation path and permitted by the unified exact-model registry/current room lifecycle. They do not refer to an arbitrary standalone or legacy single-device screen simply because it represents the same family.

When a row is expanded, its content remains a projection of that exact row's accepted per-record state through the current room-mode Audio DSP, Matrix/IN1804, codec, or PDU presentation surface. The foundation MAY add only the minimum container/theme adaptation required to keep that current room-mode surface reachable inside the common accordion at supported window sizes.

This change SHALL NOT define or implement a new family-specific internal composition for those views. In particular it does not introduce new Audio segmented-meter geometry, Matrix table columns, codec grouped cards, PDU grouped cards, or new screen-specific placeholder controls. Those details belong to later dedicated OpenSpec changes.

Only actions/capabilities already available in the current room-mode surface and declared by the unified exact-model registry/current room lifecycle are preserved. A standalone/single-device control, signal, or action is not a room capability and must not be promoted into room mode by foundation integration.

For Matrix/IN1804, the current room-mode presentation is intentionally read-only for routing. The foundation preserves the exact-row Matrix projection and its already-declared room live/local-refresh behavior, but adds no route-mutation intent, no registry mutation binding, and no wiring of standalone `MatrixScreen.routeRequested` into the room accordion. Interactive/new Matrix room routing belongs to `matrix-diagnostic-modern-ui`.

Current room-mode PDU mutation/reconciliation, codec live/auxiliary operations, and Audio DSP live/meter acquisition remain governed by their existing application intent/controller and lifecycle/capability boundaries. No compatibility adaptation may make a widget authoritative for credentials, handler/session ownership, request freshness, fallback cursors, exact-row identity, or device I/O.

If a current room-mode family presentation cannot fit the new accordion without a minimal structural wrapper/reparenting change, the implementation must preserve its existing room-mode semantics and interaction boundary; it must not substitute a standalone screen or opportunistically redesign the family while performing that integration.

### 12. Theme lifecycle

Dark mode is the startup default on every process launch. The sun/moon control toggles dark/light semantic palettes only for the current process; nothing persists.

At the same window size theme switching must not intentionally resize/reflow the common toolbar, upper cards, or common equipment rows. Both themes preserve primary/secondary hierarchy, disabled-state clarity, focus indication, borders, and text/status distinguishability.

For the reused current room-mode expanded device presentations, foundation theme integration is compatibility-only: required text/controls must remain readable and usable in both themes, but this change does not impose their final family-specific modern visual design.

Theme change is presentation-only: no generation invalidation, live restart, refresh, credential change, or device I/O.

### 13. Search edits reuse existing supersession safety

The target-search editor replaces the source-IP editor as the context-changing control. Editing after room completion immediately invalidates current room/live/pending-start authority and clears room/tree/cache presentation under existing bounded cleanup rules. Editing alone starts no device I/O.

During lifecycle states where source-IP editing is currently blocked, target-search editing is blocked instead. Top full Refresh repeats target resolution from current inventory and current unchanged selected-room context; stale selection is never reused.

### 14. Legacy no-room mode remains compatible

A supported unique IP record with `room_id = null` retains the existing legacy single-device diagnostic/interactive path. The modern toolbar/theme applies globally, but no synthetic room card, room network tree, or room equipment accordion is created solely to satisfy the new room layout.

## Follow-up device-family changes

After this foundation reaches `master`, create separate OpenSpec changes for the family-specific presentation redesigns rather than stacking them on the unarchived foundation branch:

```text
audio-diagnostic-modern-ui
matrix-diagnostic-modern-ui
codec-diagnostic-modern-ui
pdu-diagnostic-modern-ui
```

Each follow-up change must define its own repository-local visual contract, lifecycle impact, regression coverage, manual acceptance, independent validation, archive applicability, and merge boundary. The common shell/accordion contracts from this foundation are upstream dependencies, not duplicated architecture.

## Risks / Trade-offs

- **Partial-room-name ambiguity:** explicit selection, display address, neutral deterministic discriminator, and separate visible selected-room cue.
- **Stale autocomplete selection:** query revision + inventory snapshot identity; cue clears with authority.
- **Fallback regression:** full existing unavailable-inventory diagnostic and credential-configuration fallback semantics are restated in the modified shell requirement.
- **Call-activity applicability drift:** unified exact-model registry binding is the only applicability authority; missing runtime evidence yields `UNKNOWN` rather than removing a codec from relevance.
- **Call-activity normalization drift:** exact-model normalization produces typed `ACTIVE/INACTIVE/UNKNOWN`; room presentation never owns string heuristics and unrecognized evidence fails to `UNKNOWN`.
- **Occupancy semantics:** confirmed product meaning is busy-by-current-VKS-call only; `ACTIVE` drives `Занято`, while `INACTIVE` does not claim physical availability and therefore still displays `Нет данных`.
- **Warranty gap:** explicitly user-approved as not implemented; the visible row remains `Нет данных`.
- **Partial network evidence loss:** all three meaningful partial combinations are specified; known port is never discarded merely because switch IP is missing.
- **Switch parent port semantics:** parent value is only a deterministic summary of child attachment evidence, never canonical switch authority.
- **Empty-switch reference gap:** explicitly user-approved as deferred rather than simulated from nonexistent authority.
- **Foundation/family scope creep:** implementation may be tempted to substitute a standalone screen or redesign individual screens while integrating them into the accordion. The room-mode-only compatibility contract makes that a violation; family redesigns and any new family capability are separate changes.
- **Matrix capability promotion:** standalone Matrix routing exists, but current room mode has no route-mutation capability. Foundation must preserve the room read-only boundary; interactive room routing is deferred to `matrix-diagnostic-modern-ui`.
- **Theme compatibility with legacy family views:** both themes must keep reused room-mode content readable/usable, but final family visual polish is deliberately postponed.
- **Theme QSS duplication:** centralized semantic token/palette generation.

## Validation Strategy

Architecture validation:

```powershell
.\openspec.cmd validate room-diagnostic-modern-ui --strict
.\openspec.cmd validate --all --strict
git diff --check
git diff --cached --check
```

Implementation validation must include focused target-search, direct-room, shell/theme, room-card, network-card, common-row/accordion, unified-registry applicability, and typed call-activity normalization tests, plus compatibility regression tests proving the current **room-mode** Audio DSP, Matrix/IN1804, codec, and PDU presentation/interaction boundaries remain usable and do not gain direct network authority or capabilities that exist only in standalone screens. Matrix coverage must prove the current room projection remains read-only for routing, retains its existing room live/local-refresh behavior, and gains no route-mutation intent/registry binding.

Manual visual acceptance is mandatory during implementation validation: launch the GUI detached per `RULES.md`, set the window to the baseline `1440 x 900`, capture local non-committed dark/light room-mode screenshots, and compare them against the repository-local **foundation** proportion/hierarchy contract. The check must explicitly inspect toolbar/search dominance, selected-room cue, room/network peer-card width, room occupancy row/tooltip, switch-parent port summary, spacing/radius scale, `52-64 px` common row density, one-row accordion behavior, and geometry stability across theme switch. It must also verify that each reused current room-mode family presentation remains reachable/readable inside the accordion, but it SHALL NOT judge deferred Audio meter geometry, Matrix column hierarchy, codec card layout, or PDU card layout as acceptance criteria for this change.

Because this change adds a new root capability and modifies existing root requirements, independent validation must perform the disposable archive-applicability check from current `origin/agent/room-diagnostic-modern-ui` before `READY FOR ARCHIVE`.