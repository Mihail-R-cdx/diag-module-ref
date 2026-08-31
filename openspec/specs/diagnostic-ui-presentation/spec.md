# diagnostic-ui-presentation Specification

## Purpose
TBD - created by archiving change room-diagnostic-modern-ui. Update Purpose after archive.
## Requirements
### Requirement: Diagnostic shell follows a self-contained modern room-oriented foundation contract

The desktop application SHALL present the user-visible title `Диагностический модуль` and SHALL use a card-based desktop layout with consistent semantic spacing, typography, borders, radii, icons, and status styling. External screenshots are product-design inputs only; implementation and review SHALL be possible from this repository-local foundation contract without access to the original conversation images.

The baseline visual acceptance viewport SHALL be `1440 x 900` logical pixels. The layout SHALL remain usable at a minimum `1180 x 720` logical-pixel window; below the baseline, vertical scrolling or controlled card reflow MAY occur, but target-search, top Refresh, current selected-room cue, room/network cards, common equipment accordion, and expanded current device content SHALL remain reachable.

At the baseline viewport the following common visual scale SHALL apply:

```text
outer content margin              20-28 px
major section gap                 16-24 px
card internal padding             16-20 px
card radius                       8-12 px
toolbar/control height            44-56 px
collapsed equipment row height    52-64 px
common equipment-row device-class icon  48 x 48 px
section icon                       18-24 px
room hero icon                    28-36 px
body text                         10-11 pt
secondary text                    9-10 pt
section heading                   12-14 pt
page/application heading          18-22 pt
```

The primary toolbar SHALL expose the single target-search field, top Refresh, application actions, and the session theme control. At baseline width, the target-search area including its selected-room cue SHALL consume approximately 45-60% of the usable toolbar width; top actions SHALL remain compact and SHALL NOT visually dominate the search field.

Room mode SHALL place the room-summary card and network-connections card above the equipment accordion. At baseline width the two cards SHALL have aligned tops and approximately peer weight with a width ratio between `0.9:1` and `1.1:1`; neither card SHALL collapse into a narrow sidebar while the other occupies the full row.

This foundation contract does not define final family-specific visual geometry for Audio DSP, Matrix/IN1804, codec, or PDU expanded content. Those redesigns are deferred to dedicated follow-up OpenSpec changes. The common shell redesign SHALL NOT make Qt widget state authoritative for target identity, credentials, request generation, handler/session ownership, or device I/O.

#### Scenario: Room shell is rendered at baseline size

- **WHEN** room mode has an authoritative current room at the baseline viewport
- **THEN** the room-summary and network cards appear side by side above the equipment accordion with peer visual weight
- **AND** the common spacing/typography/icon scale is applied
- **AND** device/network authority remains outside the presentation widgets

#### Scenario: Minimum supported window remains usable

- **WHEN** the application is shown at `1180 x 720` logical pixels
- **THEN** target-search, selected-room cue when present, top Refresh, room/network cards, equipment accordion, and current expanded device content remain reachable through controlled reflow/scrolling
- **AND** no target or device authority changes merely because layout reflows

### Requirement: Selected room remains visibly identifiable without replacing raw search text

When room-name resolution produces an explicit selected room, the shell SHALL render a secondary selected-room label/chip/line directly associated with the search control. It SHALL use the deterministic `selection_label` from the current room-search result and SHALL NOT replace the raw query string.

The selected-room cue SHALL be visually subordinate to the raw search editor but plainly visible at baseline size. It SHALL disappear immediately when query editing invalidates the selection. Repeated top Refresh of an unchanged multi-match query SHALL continue to show the exact selection that application authority may reuse; if that selection becomes stale/invalid, the cue SHALL be cleared before a new diagnostic start.

#### Scenario: Duplicate room names are selected safely

- **GIVEN** autocomplete contains several visibly distinguishable results whose room names are identical
- **WHEN** the operator selects one result
- **THEN** the raw search text remains unchanged
- **AND** the selected-room cue displays that result's exact deterministic selection label
- **AND** the cue maps to the same current canonical room ID used by application authority

### Requirement: Room summary card derives busy indication only from typed codec call activity

The room-summary card SHALL permanently include presentation slots for room name, room address, VIP, warranty, and occupancy. Current canonical `room_name`, `room_address`, and `room_vip` SHALL use the room metadata authority defined by `room-equipment-diagnostics`.

The confirmed product decision for this change is that real warranty data is not implemented yet. This scope decision is independent of the current schema limitation. Because canonical schema v4 contains no authoritative warranty field, the permanent row SHALL render `Гарантия: Нет данных` and SHALL NOT infer warranty from unrelated inventory columns, timestamps, device data, room text, or local UI state. A future reviewed change may add an authoritative warranty source/schema mapping.

The confirmed product meaning of the operator-facing `Занятость` row in this change is **busy by current VKS call**, not physical room occupancy and not booking/calendar occupancy. Occupancy SHALL NOT become an inventory field and SHALL NOT introduce a booking/calendar source in this change. It SHALL consume only current model-neutral `CallActivity` evidence produced under `device-diagnostics-and-control`; the room presentation SHALL NOT parse model-specific or localized call-status strings.

The current product decision defines only a positive busy indication:

```text
at least one current accepted relevant room codec has CallActivity.ACTIVE
    -> `Занято`

otherwise
    -> `Нет данных`
```

`CallActivity.INACTIVE` is intentionally not presented as `Свободно` in this change because absence of a codec call does not establish physical room availability. `CallActivity.UNKNOWN`, missing/stale/failed call evidence, or a room with no current active call likewise renders `Нет данных`.

A relevant call-capable codec row is defined exclusively by capability authority: its exact unified application model registration declares the required available call-activity normalization/projection binding defined by `device-diagnostics-and-control`. Runtime presence or absence of a `CallActivity` field or call-status payload SHALL NOT decide applicability. A registry-relevant row whose current evidence is missing, stale, failed, contradictory, or unrecognized remains relevant and contributes `CallActivity.UNKNOWN`; it SHALL NOT silently disappear from aggregation. Presentation SHALL NOT keep a second occupancy-supported model list.

The occupancy projection SHALL update only when the existing application-owned room diagnostic or post-cycle codec lifecycle accepts new current typed call-activity evidence/currentness. Rendering occupancy SHALL NOT start a new timer, poll, handler/session acquisition, worker, credential attempt, or device network request.

Hovering the `Занятость` row/value SHALL show a local tooltip or equivalent non-modal explanatory popup whose meaning is equivalent to: `Занятость определяется по текущему состоянию звонка кодека.` The tooltip SHALL perform no device I/O and SHALL NOT imply that occupancy comes from a room-booking/calendar system.

VIP true SHALL have a clear badge/indicator in addition to textual/accessibility meaning. VIP false/null SHALL not be rendered as VIP true.

At baseline size the room identity/name is the strongest text inside the card; address/warranty/occupancy are secondary rows. A room-card refresh icon MAY be present to match the visual hierarchy, but if actionable it SHALL be only an alias of the existing top full Refresh intent.

#### Scenario: Typed active codec call marks the room busy

- **GIVEN** a registry-relevant current room codec row has non-stale accepted `CallActivity.ACTIVE`
- **WHEN** the room summary is rendered or that accepted typed activity changes
- **THEN** occupancy is displayed as `Занято`
- **AND** no additional occupancy-specific network request is started

#### Scenario: Typed inactive evidence does not claim physical availability

- **GIVEN** every registry-relevant current room codec has current accepted `CallActivity.INACTIVE`
- **WHEN** the room summary is rendered
- **THEN** occupancy is displayed as `Нет данных`
- **AND** the GUI does not claim `Свободно`

#### Scenario: Registry-relevant codec remains relevant without usable evidence

- **GIVEN** a room codec exact registration declares the required call-activity binding
- **AND** its current call evidence is missing, stale, failed, contradictory, or unrecognized
- **WHEN** occupancy is aggregated
- **THEN** that codec remains a relevant row
- **AND** its contribution is `CallActivity.UNKNOWN`
- **AND** runtime field absence does not remove it from applicability

#### Scenario: Occupancy evidence is incomplete

- **GIVEN** no registry-relevant current room codec has `CallActivity.ACTIVE`
- **AND** call activity is `UNKNOWN`, missing, stale, failed, or otherwise unusable for one or more registry-relevant rows
- **WHEN** the room summary is rendered
- **THEN** occupancy is displayed as `Нет данных`
- **AND** the GUI does not guess that the room is free

#### Scenario: Occupancy explanation is available on hover

- **WHEN** the operator hovers the occupancy row or value
- **THEN** a local explanatory tooltip/popup states that occupancy is derived from the current codec call state
- **AND** opening the explanation performs no device I/O

### Requirement: Network card preserves all available canonical connection evidence

The network-connections card SHALL use a hierarchical tree with columns equivalent to `Коммутатор (IP) / Устройства` and `Порт`. Expanding/collapsing the network tree SHALL be local presentation only and SHALL perform no device network I/O.

Canonical connection evidence SHALL be presented according to these exact cases:

```text
switch_ip_address known + switch_port known
    -> group under the exact switch-IP parent
    -> device child shows the known port

switch_ip_address known + switch_port null
    -> group under the exact switch-IP parent
    -> device child shows `Нет данных` for port

switch_ip_address null + switch_port known
    -> do not invent or merge switch identity
    -> create an evidence branch equivalent to `Коммутатор не определён`
       bound to that exact equipment record only
    -> its device child shows the known port

switch_ip_address null + switch_port null
    -> that record contributes no switch/port topology evidence
```

Records with unknown switch IP but known port SHALL NOT be grouped together merely because port text matches. Each such branch remains tied to the exact canonical record evidence so no fictitious common switch is created.

For an authoritative switch-IP parent, attached room-equipment children SHALL be ordered by canonical `record_id`, SHALL display the existing safe device/model label, and SHALL display canonical `switch_port` or the safe no-data value.

The parent `Порт` column SHALL be a presentation summary of child attachment-port evidence rather than a new switch property. For each authoritative switch-IP parent, collect non-null canonical child `switch_port` values in child `record_id` order and de-duplicate by first occurrence:

```text
zero known child ports     -> `Нет данных`
one unique known port      -> that exact port, e.g. `Gi1/0/5`
multiple unique ports      -> comma-separated exact values in deterministic child order
```

Each expanded child SHALL still display its own exact canonical `switch_port` or `Нет данных`. The summary SHALL NOT be persisted as canonical data and SHALL NOT be used as switch identity or device-routing authority.

For a record-bound `Коммутатор не определён` evidence branch with a known canonical port, the branch-level `Порт` cell MAY repeat that exact port as a presentation summary because the branch is bound to one exact record; its child still displays the same exact evidence.

A user-friendly switch name MAY be shown only from safe unique current canonical display evidence for that exact switch IP. Otherwise a generic `Коммутатор (<IP>)` style label SHALL be used.

If the room contains no presentable switch-IP or port evidence at all, the card SHALL show a safe empty state equivalent to `Нет данных о сетевых подключениях` rather than an invented topology.

The confirmed product decision for this change is that room switches with zero attached canonical equipment are not implemented now. This is an intentional scope decision, not an inference from schema v4. Current schema v4 also cannot authoritatively establish such a switch, so implementation SHALL NOT fabricate it and acceptance SHALL NOT require the `Нет подключенных устройств` runtime state. A future reviewed source/schema change is required before that state becomes data-driven.

#### Scenario: Two room devices share a switch

- **GIVEN** two room records contain the same non-null canonical `switch_ip_address`
- **AND** their canonical ports are `Gi1/0/5` and `Gi1/0/6`
- **WHEN** the network tree is rendered
- **THEN** one switch parent is shown for that IP
- **AND** both attached devices appear as deterministic children with their canonical ports
- **AND** the parent Port summary displays `Gi1/0/5, Gi1/0/6`
- **AND** that summary does not become canonical switch state

#### Scenario: Parent port summary de-duplicates repeated child evidence

- **GIVEN** several children under one exact switch IP contain the same non-null canonical port text
- **WHEN** the parent summary is rendered
- **THEN** the repeated port appears once according to first child occurrence
- **AND** every child still retains its own exact port presentation

#### Scenario: Known port with missing switch IP is not lost

- **GIVEN** one room record has null `switch_ip_address` and non-null canonical `switch_port`
- **WHEN** the network card renders
- **THEN** the known port remains visible under a `Коммутатор не определён` evidence branch bound to that exact record
- **AND** no switch IP or shared switch identity is guessed

#### Scenario: Empty switch state is explicitly out of current scope

- **GIVEN** the confirmed product scope defers room switches with zero attached canonical equipment
- **WHEN** no canonical room record/evidence establishes an unattached switch node
- **THEN** the GUI does not fabricate a switch solely to display `Нет подключенных устройств`
- **AND** acceptance does not require that state in this change

### Requirement: Equipment rows share one non-color accordion header contract

Every room equipment record SHALL use one common top-level row layout equivalent to:

```text
expand chevron -> device-class icon -> model label -> status cue + status text -> IP -> overflow action
```

At baseline size a collapsed row SHALL remain within the `52-64 px` height range. The chevron/icon cluster SHALL remain compact, model text SHALL receive the largest flexible width, status and IP SHALL remain readable without forcing the row into multiple lines under ordinary baseline content, and the overflow action SHALL remain visually secondary.

Status SHALL remain understandable without color alone. The row SHALL retain explicit text/non-color meaning for connected, waiting, connecting, unsupported, missing-IP, ambiguous-IP, failed, connection-lost, and other approved states.

Exactly one room equipment row MAY be expanded at a time. Expanding another expandable row SHALL collapse the previous row. Accordion changes SHALL remain presentation/current-selection behavior and SHALL NOT reorder the automatic room acquisition queue.

The overflow action SHALL expose only current application-authorized actions. When no action is authorized it SHALL be disabled or non-actionable and SHALL NOT provide an alternate direct network path.

#### Scenario: Another device row is expanded

- **GIVEN** one expandable equipment row is open
- **WHEN** the operator expands a second row
- **THEN** the first row collapses
- **AND** only the second row owns current expanded presentation selection
- **AND** automatic queue order is unchanged

### Requirement: Existing expanded device presentations remain compatible and are not redesigned by this foundation

For this foundation, `existing`, `current`, or `reused` device-family presentation means the **current room-mode exact-row presentation/interaction surface** for that family, as bound by the room diagnostic presentation path and the unified exact-model registry/lifecycle capabilities. A standalone or legacy single-device screen SHALL NOT be selected, embedded, or treated as room capability merely because it represents the same device family. The foundation MAY add only the minimum container/reparenting/theme compatibility needed to keep the current room-mode surface reachable at supported window sizes.

Expanded Audio DSP, Matrix/IN1804, codec, and PDU content SHALL remain projections of exact per-record state through that current room-mode surface. This change SHALL NOT define or implement a new family-specific internal visual contract. It SHALL NOT require new Audio segmented-meter geometry, a new Matrix column hierarchy, new codec grouped cards, new PDU grouped cards, or new screen-specific reference-only controls. Those redesigns belong to separate follow-up OpenSpec changes after this foundation is merged.

Existing **room-mode** controls SHALL remain connected through their current non-secret application intent/controller boundaries and SHALL remain enabled only when current registry/lifecycle capability state permits them. The foundation SHALL NOT promote an action, control, or signal that exists only on a standalone/single-device screen into room mode. Existing room-mode PDU mutation/reconciliation, codec auxiliary/live behavior, Audio DSP live/meter behavior, and Matrix room live/local-refresh behavior SHALL remain governed by their current corresponding lifecycle contracts.

For Matrix/IN1804 specifically, the foundation SHALL preserve the current room-mode read-only Matrix presentation. It SHALL preserve only the Matrix room interactions already declared by the unified exact-model registry/current room lifecycle, including the existing room live/local-refresh behavior. It SHALL NOT add a room-mode route-mutation intent or registry mutation binding, SHALL NOT wire or embed standalone `MatrixScreen.routeRequested` as a room action, and SHALL NOT treat standalone Matrix routing as an existing room capability. Any interactive/new Matrix room routing presentation belongs to the later `matrix-diagnostic-modern-ui` change.

Compatibility adaptation SHALL NOT make expanded widgets authoritative for credential selection/fallback, handlers, sessions, transports, successful credential memory, stale-operation authority, request generations, exact-row identity, or direct device network I/O.

#### Scenario: Existing room-mode device view opens inside the common accordion

- **GIVEN** an exact supported room row has a current room-mode expanded presentation path
- **WHEN** the operator expands that row under the new common accordion
- **THEN** the current room-mode family presentation remains reachable and bound to that exact row state
- **AND** no standalone/single-device screen is promoted merely because it has the same family
- **AND** no family-specific redesign is required for acceptance of this change
- **AND** no widget gains direct credential/session/network authority

#### Scenario: Existing room-mode device action preserves its application boundary

- **GIVEN** an existing current room-mode device-family action is authorized by its current unified-registry/lifecycle capability
- **WHEN** the operator invokes it from the reused expanded presentation inside the accordion
- **THEN** the existing application intent/controller boundary is used
- **AND** the foundation introduces no direct handler call, new capability, or parallel network lifecycle

#### Scenario: Matrix remains read-only in room mode under the foundation

- **GIVEN** an exact `Extron IN1804` room row whose current unified-registry entry has room live/local-refresh capability but no route-mutation binding
- **WHEN** the row is expanded in the foundation accordion
- **THEN** the current room-mode read-only Matrix projection remains exact-row bound
- **AND** existing Matrix room live/local-refresh behavior remains governed by the current lifecycle
- **AND** no Matrix route-mutation intent or registry mutation binding is introduced
- **AND** standalone `MatrixScreen.routeRequested` is not wired into the room accordion

### Requirement: Dark and light themes are semantic, foundation-geometry-stable, and session-only

The application SHALL support dark and light semantic themes. Every new process launch SHALL start in dark mode regardless of the theme used before the previous process exited.

A user-visible sun/moon theme control SHALL toggle the active palette for the current process only. The application SHALL NOT persist theme choice to a file, settings store, registry, environment variable, inventory, credential file, or other durable state.

Theme switching SHALL preserve the same common toolbar, upper-card, and common-row geometry, spacing scale, card hierarchy, disabled-control clarity, focus indication, and status meaning. Theme switching SHALL NOT intentionally resize/reflow those foundation regions at the same window size. Both themes SHALL keep primary text, secondary text, borders, focus, status cues, and disabled controls visually distinguishable.

For reused existing expanded device presentations, foundation theme integration is compatibility-only: required text and existing controls SHALL remain readable/usable in both themes, but this change SHALL NOT impose their final family-specific modern visual design.

Theme switching SHALL be presentation-only and SHALL NOT invalidate target/room generations, change credentials, stop/restart live work, submit refresh, or perform device network I/O.

#### Scenario: Application restarts after light mode

- **GIVEN** the operator switched the running application to light mode
- **WHEN** the application is closed and started again
- **THEN** the new process starts in dark mode
- **AND** no persisted theme preference is consulted

#### Scenario: Theme changes during connected room state

- **GIVEN** a connected room session exists at a fixed window size
- **WHEN** the operator toggles the theme
- **THEN** only visual palette/style state changes
- **AND** common shell/card/row geometry remains materially unchanged
- **AND** reused expanded content remains readable/usable
- **AND** room authority, live/network ownership, and accepted diagnostic caches remain unchanged

### Requirement: Expanded Audio DSP redesign targets the current room exact-row presentation surface

MIH-10 SHALL render its modern Audio DSP content inside the current room-mode exact-row presentation owned by `RoomDiagnosticTreeWidget`. On the current change base, an expandable Audio DSP row is projected through `RoomReadOnlyPresentation`, and `screen_key == "audio_dsp"` is rendered by its Audio DSP builder.

A focused presentation-only Audio DSP widget/component MAY be extracted and embedded from that room path. Such a widget SHALL NOT own room identity, request generation, credentials, polling/session lifecycle, or network I/O.

The standalone `AudioDSPScreen` SHALL NOT be selected, embedded, or promoted as a room capability merely because it represents the same device family. It MAY reuse a presentation-only widget as a secondary consumer after the room target is satisfied, but standalone rendering is not MIH-10 acceptance authority.

#### Scenario: Expanded room Audio DSP row uses the modern presentation

- **GIVEN** the current room session contains an expandable Audio DSP exact row
- **WHEN** the operator expands that row
- **THEN** the modern Audio DSP presentation is rendered inside the `RoomDiagnosticTreeWidget` exact-row content
- **AND** room/record authority remains the current exact row
- **AND** standalone `AudioDSPScreen` is not required or promoted as room authority

#### Scenario: Optional reusable widget remains presentation-only

- **GIVEN** implementation extracts a focused Audio DSP meter widget for reuse
- **WHEN** that widget is embedded in the room Audio DSP projection
- **THEN** it consumes current accepted presentation data only
- **AND** it does not create or own a worker, handler/session, credential plan, room generation, or device request

### Requirement: Expanded Audio DSP numeric meter evidence uses a deterministic vertical segmented presentation

When the current accepted exact-row Audio DSP presentation receives numeric `meter_sections` evidence, it SHALL render that evidence as separate Input/source and Output/destination groups using vertical segmented meters. Applicability SHALL follow the accepted payload contract rather than a presentation-owned model-name allowlist: a channel is numeric-meter capable only when its accepted channel evidence uses the existing meter contract with `available` and, when available, numeric `dbfs` plus numeric `normalized`.

For the current change base, Extron DMP 64 Plus provides deterministic `Inputs` and `Outputs` meter sections with six input channels and four output channels. Presentation SHALL preserve accepted section/channel order and SHALL NOT sort by value, availability, outcome, color zone, or local selection.

At the accepted baseline viewport (`1440 x 900` logical pixels), the Audio DSP content SHALL form a compact dashboard with a narrow General information card, a dominant central meter area, and a narrow Quick actions card. Inputs and Outputs SHALL appear as peer section cards in one horizontal central meter area where width permits; Inputs receive more width than Outputs because the accepted DMP payload contains six Inputs and four Outputs.

Each numeric meter channel SHALL have a compact ordinal caption above its meter and visible numeric dBFS evidence below it. The caption SHALL omit the repeated `Input` or `Output` prefix, while exact `section` + `oid` remains the channel identity. Exact pixel sizes, gaps, and card ratios are presentation tuning rather than a normative contract. Each meter SHALL have exactly 20 segments and retain deterministic order, visible numeric evidence, and supported-size reachability.

The visual scale SHALL correspond to `-60 dBFS` through `+12 dBFS`. Accepted numeric `dbfs` SHALL remain visibly operator-readable and authoritative as evidence. Accepted `normalized` SHALL be used only for meter fill.

For an available channel, presentation SHALL calculate fill deterministically as:

```text
n = clamp(accepted normalized, 0.0, 1.0)
filled_segments = floor(n * 20 + 0.5)
```

This is explicit round-half-up behavior producing an integer from `0` through `20`; language/runtime banker rounding SHALL NOT substitute for this formula.

Physical meter segments SHALL be indexed bottom-to-top from `0` through `19`. Each segment SHALL use the fixed midpoint:

```text
segment_midpoint_dbfs(i) = -60 + (i + 0.5) * 3.6
```

A filled segment SHALL use theme-aware semantic styling according to that midpoint:

```text
midpoint < -18 dBFS         green/success zone
-18 <= midpoint < -6 dBFS   yellow/warning zone
midpoint >= -6 dBFS         orange/elevated zone
```

Unfilled segments remain neutral/inactive. Color SHALL NOT replace numeric meaning.

When `available = false`, numeric presentation SHALL render an empty/neutral segmented track and a non-color value equivalent to `— dBFS`; it SHALL NOT fabricate `0 dBFS` or reuse a prior numeric value as current.

The redesign SHALL preserve current accepted safe structured diagnostic evidence separately from numeric meter value. If the accepted channel contains `outcome`, the room presentation SHALL keep that value visible through a secondary status/detail line, badge, or tooltip. If an accepted safe `error_code` is present, it MAY be shown alongside the structured outcome. Raw protocol payload, command echo, debug text, exception text, or newly inferred categories SHALL NOT be introduced by this presentation change.

#### Scenario: Current DMP snapshot renders deterministic Input and Output meters

- **GIVEN** the current accepted exact-row Audio DSP payload contains the baseline DMP `Inputs` section with six channels and `Outputs` section with four channels
- **WHEN** the expanded room Audio DSP presentation renders at the baseline viewport
- **THEN** Inputs and Outputs are shown as separate peer groups in accepted order
- **AND** each available channel renders one 20-segment vertical meter using the exact fill formula
- **AND** each channel visibly shows its accepted numeric `dbfs`
- **AND** no channel is reordered by value, availability, outcome, or color

#### Scenario: Quantization is deterministic at segment boundaries

- **GIVEN** an accepted available channel has normalized value `n`
- **WHEN** the meter determines its filled segment count
- **THEN** it uses `floor(clamp(n, 0, 1) * 20 + 0.5)` exactly
- **AND** each filled physical segment derives its semantic zone from the fixed segment midpoint
- **AND** no alternative floor, ceil, banker-rounding, or value-dependent zone algorithm is used

#### Scenario: Unavailable numeric channel preserves diagnostic outcome

- **GIVEN** a current accepted meter channel has `available = false`
- **AND** its accepted evidence contains a structured `outcome`
- **WHEN** the room Audio DSP meter view renders
- **THEN** its segmented track is neutral/empty
- **AND** its visible numeric value is equivalent to `— dBFS`
- **AND** the safe structured `outcome` remains available in secondary presentation
- **AND** an accepted safe `error_code` MAY also be shown when present
- **AND** no prior numeric value or fabricated `0 dBFS` is shown as current

### Requirement: Audio DSP channel selection is stable local non-authoritative room presentation state

The expanded numeric Audio DSP room view MAY allow the operator to select one current meter channel for visual emphasis. Channel selection SHALL be local presentation state only and SHALL NOT change room/record authority, diagnostic acquisition order, credentials, request generation/currentness, handler/session ownership, polling state, retry state, or device configuration.

Selected-channel identity SHALL be scoped by current exact room context plus `record_id` plus stable channel identity (`section` + `oid`). A selected channel SHALL have a non-color cue in addition to optional color, such as a visible outline plus a selection marker/accessibility state. No first channel SHALL become implicitly selected merely because the row is expanded.

While the same exact room context/generation and same `record_id` remain current, every accepted snapshot update SHALL preserve the selected channel if that accepted payload still contains the same `section` + `oid`. Rendering a new current meter value SHALL NOT clear that valid same-context selection.

Selection SHALL clear when the exact room context/generation is superseded or cleared, when the selected record is replaced/removed, or when accepted current evidence no longer contains the selected `section` + `oid`.

Because current room rendering may rebuild child presentation widgets, selected-channel state SHALL be owned at a room-presentation level that survives such same-context rebuilds; a disposable child widget SHALL NOT be the sole owner if that would reset valid selection on every accepted snapshot. This ownership remains non-authoritative presentation state.

#### Scenario: Operator selects a current channel

- **GIVEN** an expanded current Audio DSP row with no selected channel
- **WHEN** the operator selects one meter channel
- **THEN** that channel receives an explicit non-color selection cue
- **AND** selection starts no polling/lifecycle, acquisition, retry/recovery, credential, or mutation timer; no worker, handler/session, credential attempt, room interaction intent, or device command
- **AND** selection MAY indirectly schedule the permitted widget-owned single-shot presentation timer solely to defer showing, hiding, or repositioning local controls
- **AND** that timer remains disposable local UI state and does not perform I/O, emit interaction intent, start a worker/session, select credentials, drive acquisition/polling/retry/recovery/mutation, alter room/record authority, request generation/currentness, accepted evidence, or application/device state authority
- **AND** room acquisition order and exact-row authority remain unchanged

#### Scenario: Same-context accepted snapshot preserves selected channel

- **GIVEN** a channel is selected for the current exact room context and record by `section` + `oid`
- **AND** a later accepted current snapshot still contains that same channel identity
- **WHEN** the room presentation rebuilds or updates its Audio DSP child
- **THEN** the meter value updates
- **AND** the same channel SHALL remain selected
- **AND** selection does not alter callback-currentness authority

#### Scenario: Supersession or channel disappearance clears selection

- **GIVEN** one Audio DSP row/context has a locally selected channel
- **WHEN** the exact room context is superseded, the record is removed/replaced, or the selected `section` + `oid` is absent from accepted current evidence
- **THEN** the old local channel selection is cleared
- **AND** a stale callback cannot restore it as current selection

### Requirement: Audio DSP future gain and mute controls remain local disabled placeholders until separately authorized

The modern room Audio DSP presentation SHALL expose local controls visually associated with a hovered channel or a selected/pinned channel. They contain a channel context/label, gain decrement `-`, current gain/value, gain increment `+`, and `Mute`; a permanent full-width selected-channel control strip is not part of the accepted dashboard.

On the current change base there is no approved exact-row Audio DSP gain/mute mutation binding. Therefore:

```text
gain `-`                disabled/non-actionable
current gain/value      `—` or equivalent `Нет данных`
gain `+`                disabled/non-actionable
`Mute`                  disabled/non-actionable
```

The GUI SHALL NOT infer current gain or mute state from meter level, normalized fill, Biamp signal-source values, labels, or local widget state. Disabled placeholders SHALL emit no application/room interaction intent, signal, worker start, handler/session acquisition, protocol command, or device request.

Enabling any of these controls requires a later approved capability defining exact target identity, application-owned intent binding, mutation safety, reconciliation/readback, lifecycle/currentness, and failure semantics.

#### Scenario: Selected channel exposes only disabled future controls

- **GIVEN** a current room Audio DSP meter channel is locally selected
- **WHEN** the local future controls are shown
- **THEN** `-`, `+`, and `Mute` are disabled/non-actionable
- **AND** current gain/value is shown as `—` or equivalent no-data text when no authoritative field exists
- **AND** interacting with the disabled presentation starts no device I/O or mutation intent

### Requirement: Audio DSP Quick actions remain truthful to existing safe room capability

The narrow Audio DSP Quick actions card SHALL contain only already-approved existing safe local room actions supplied by the current room presentation. It SHALL NOT add, imply, or enable an Audio DSP gain/mute or other device mutation capability. When no approved action is supplied, it SHALL show a truthful non-actionable empty state.

#### Scenario: Quick actions do not fabricate a capability

- **GIVEN** an expanded Audio DSP room row has no approved local action supplied to its presentation
- **WHEN** the Audio DSP dashboard renders
- **THEN** its Quick actions card shows a truthful non-actionable empty state
- **AND** no new device request, mutation intent, worker, or session is created

### Requirement: Audio DSP redesign preserves room lifecycle bindings and stale-operation boundaries

The modern Audio DSP room presentation SHALL consume only accepted current exact-row data from the existing application/composition room lifecycle and SHALL NOT create or substitute another Audio DSP/DMP polling/session lifecycle.

For Extron DMP 64 Plus, the existing lifecycle separation SHALL remain:

```text
room automatic acquisition -> `dmp_one_shot`
room live interaction       -> `dmp_room_live`
standalone screen lifecycle -> `DMPPollingController`
```

The room accordion SHALL NOT be routed through standalone `DMPPollingController`, and this change SHALL NOT add a second DMP room live binding or modify unified registry capability merely to render the new presentation.

The following presentation events SHALL perform zero device network I/O by themselves:

- equipment row expand/collapse;
- channel select/deselect;
- meter repaint/visual animation;
- hover/focus over meter or disabled controls;
- dark/light theme toggle;
- resize, reflow, or scrolling.

Presentation SHALL NOT create a polling, acquisition, retry/recovery, credential, handler/session lifecycle, or mutation `QTimer`; nor a worker, controller, handler/session, credential plan, retry lane, or mutation lane merely to drive the modern visual design. A focused presentation widget MAY own a single-shot `QTimer` solely to defer showing, hiding, or repositioning its local controls. This timer is disposable widget-owned presentation state only: it SHALL perform no device/network I/O, emit no application/room interaction intent, start no worker or handler/session, acquire or choose credentials, drive acquisition, polling, retry/recovery, or mutation, alter room/record authority, alter request generation/currentness, alter accepted diagnostic evidence, or become application/device state authority.

Existing application-owned room generation/record/credential/currentness checks SHALL remain authority for accepting callbacks. A stale snapshot from a superseded room context SHALL NOT update the replacement Audio DSP presentation, selected-channel state, credential memory, or lifecycle state.

Expanding/collapsing the Audio DSP row SHALL NOT create, leak, or duplicate a room live/session lane. Theme changes SHALL alter styling only and SHALL NOT restart acquisition. Cleanup/cancellation remains owned by the existing room/background lifecycle and SHALL NOT move network cleanup into the GUI thread.

If implementation appears to require changes to `dmp_one_shot`, `dmp_room_live`, dispatch registry, DMP protocol helpers/workers/handlers, credentials, or `DMPPollingController`, it SHALL return for architecture review before making those changes.

#### Scenario: Room DMP lifecycle remains on registered room bindings

- **GIVEN** the exact current room row is `Extron DMP 64 Plus`
- **WHEN** automatic acquisition or an approved room live interaction supplies data for the modern Audio DSP presentation
- **THEN** automatic acquisition remains owned by `dmp_one_shot`
- **AND** room live interaction remains owned by `dmp_room_live`
- **AND** standalone `DMPPollingController` is not promoted into room authority

#### Scenario: Theme toggle during room live DMP presentation is local only

- **GIVEN** a current room Audio DSP row is receiving accepted live DMP snapshots
- **WHEN** the operator switches between dark and light theme
- **THEN** meter styling changes without restarting room acquisition/session ownership
- **AND** channel order, exact-row authority, accepted evidence, and currentness remain unchanged
- **AND** no new device I/O is started by theme toggle

#### Scenario: Stale room DMP snapshot stays rejected

- **GIVEN** an old room DMP context has been superseded by another context
- **WHEN** the old context later produces a callback
- **THEN** that callback cannot update the current modern Audio DSP view
- **AND** it cannot restore stale selected-channel state or restart acquisition

### Requirement: Non-meter Audio DSP evidence is not fabricated into dBFS presentation

Audio DSP payloads that do not establish the numeric `meter_sections` contract SHALL remain truthful to accepted evidence. Current Biamp Tesira Forte CI `signal_sources` rows MAY receive family-consistent card, spacing, typography, and theme styling, but arbitrary scalar or boolean source values SHALL NOT be converted into dBFS levels, vertical numeric meters, invented Input/Output groups, gain state, or mute state.

The safe source/value presentation MAY remain tabular/card-based. If no numeric meter sections are available, the UI SHALL clearly present the evidence it actually has rather than visually implying DMP-equivalent meter authority.

#### Scenario: Biamp boolean source value stays scalar evidence

- **GIVEN** a current Biamp Audio DSP payload contains `signal_sources` with boolean/scalar values and no numeric `meter_sections`
- **WHEN** the expanded room Audio DSP presentation renders
- **THEN** those values remain source/scalar evidence
- **AND** no dBFS value or vertical numeric meter is fabricated from them
- **AND** no gain or mute state is inferred from them

### Requirement: Modern room Audio DSP content remains usable in foundation themes and supported sizes

The Audio DSP redesign SHALL inherit the foundation baseline viewport of `1440 x 900` and minimum supported window of `1180 x 720` logical pixels. At baseline width it SHALL show the accepted dashboard hierarchy: narrow General information, dominant central Inputs/Outputs meter area, and narrow Quick actions. Inputs and Outputs cards SHALL be side by side in the central area. At narrower supported widths, controlled reflow MAY place auxiliary cards above the meter area, stack the meter cards vertically, or use existing expanded-content scrolling, provided all current channels, numeric values, secondary diagnostic outcome detail, selection cue, and disabled local controls remain reachable.

Responsive behavior SHALL NOT change channel identity, order, accepted numeric/structured evidence, selected exact channel, or device lifecycle authority. Channel labels SHALL remain visible rather than existing solely as hover tooltips.

Dark and light themes SHALL preserve equivalent geometry, channel order, evidence, disabled-control meaning, and selection meaning. Theme styling SHALL use shared/theme-aware semantic tokens. This change SHALL NOT persist theme across application restarts and SHALL NOT change the foundation rule that the application starts in dark theme.

#### Scenario: Baseline dark and light room layouts preserve evidence

- **GIVEN** the same accepted current room DMP meter snapshot
- **WHEN** the expanded Audio DSP row is rendered at `1440 x 900` in dark theme and then light theme
- **THEN** dashboard hierarchy, Inputs/Outputs grouping, compact captions, channel order, segment count, numeric dBFS, structured outcome detail, disabled-control state, and selected identity remain equivalent
- **AND** only theme styling changes

#### Scenario: Minimum supported window keeps room Audio DSP content reachable

- **WHEN** the application is shown at `1180 x 720` logical pixels with an expanded numeric Audio DSP room row
- **THEN** controlled reflow/scrolling keeps every current meter channel, numeric value, secondary diagnostic outcome, selected cue, and disabled local control reachable
- **AND** no channel/data authority changes because of layout reflow
