## ADDED Requirements

### Requirement: Diagnostic shell follows a self-contained modern room-oriented visual contract

The desktop application SHALL present the user-visible title `Диагностический модуль` and SHALL use a card-based desktop layout with consistent semantic spacing, typography, borders, radii, icons, and status styling. External screenshots are product-design inputs only; implementation and review SHALL be possible from this repository-local contract without access to the original conversation images.

The baseline visual acceptance viewport SHALL be `1440 x 900` logical pixels. The layout SHALL remain usable at a minimum `1180 x 720` logical-pixel window; below the baseline, vertical scrolling or controlled card reflow MAY occur, but target-search, top Refresh, current selected-room cue, room/network cards, and equipment accordion SHALL remain reachable.

At the baseline viewport the following visual scale SHALL apply:

```text
outer content margin              20-28 px
major section gap                 16-24 px
card internal padding             16-20 px
card radius                       8-12 px
toolbar/control height            44-56 px
collapsed equipment row height    52-64 px
row icon                           18-22 px
section icon                       18-24 px
room hero icon                    28-36 px
body text                         10-11 pt
secondary text                    9-10 pt
section heading                   12-14 pt
page/application heading          18-22 pt
```

The primary toolbar SHALL expose the single target-search field, top Refresh, application actions, and the session theme control. At baseline width, the target-search area including its selected-room cue SHALL consume approximately 45-60% of the usable toolbar width; top actions SHALL remain compact and SHALL NOT visually dominate the search field.

Room mode SHALL place the room-summary card and network-connections card above the equipment accordion. At baseline width the two cards SHALL have aligned tops and approximately peer weight with a width ratio between `0.9:1` and `1.1:1`; neither card SHALL collapse into a narrow sidebar while the other occupies the full row.

The visual redesign SHALL NOT make Qt widget state authoritative for target identity, credentials, request generation, handler/session ownership, or device I/O.

#### Scenario: Room shell is rendered at baseline size

- **WHEN** room mode has an authoritative current room at the baseline viewport
- **THEN** the room-summary and network cards appear side by side above the equipment accordion with peer visual weight
- **AND** the common spacing/typography/icon scale is applied
- **AND** device/network authority remains outside the presentation widgets

### Requirement: Selected room remains visibly identifiable without replacing raw search text

When room-name resolution produces an explicit selected room, the shell SHALL render a secondary selected-room label/chip/line directly associated with the search control. It SHALL use the deterministic `selection_label` from the current room-search result and SHALL NOT replace the raw query string.

The selected-room cue SHALL be visually subordinate to the raw search editor but plainly visible at baseline size. It SHALL disappear immediately when query editing invalidates the selection. Repeated top Refresh of an unchanged multi-match query SHALL continue to show the exact selection that application authority may reuse; if that selection becomes stale/invalid, the cue SHALL be cleared before a new diagnostic start.

#### Scenario: Duplicate room names are selected safely

- **GIVEN** autocomplete contains several visibly distinguishable results whose room names are identical
- **WHEN** the operator selects one result
- **THEN** the raw search text remains unchanged
- **AND** the selected-room cue displays that result's exact deterministic selection label
- **AND** the cue maps to the same current canonical room ID used by application authority

### Requirement: Room summary card has permanent room-information slots

The room-summary card SHALL permanently include presentation slots for room name, room address, VIP, warranty, and occupancy. Current canonical `room_name`, `room_address`, and `room_vip` SHALL use the room metadata authority defined by `room-equipment-diagnostics`.

Because canonical schema v4 does not contain authoritative warranty or occupancy fields, this change SHALL render `Гарантия: Нет данных` and `Занятость: Нет данных` and SHALL NOT infer those values from unrelated inventory columns, timestamps, device data, room text, or local UI state.

VIP true SHALL have a clear badge/indicator in addition to textual/accessibility meaning. VIP false/null SHALL not be rendered as VIP true.

At baseline size the room identity/name is the strongest text inside the card; address/warranty/occupancy are secondary rows. A room-card refresh icon MAY be present to match the visual hierarchy, but if actionable it SHALL be only an alias of the existing top full Refresh intent.

#### Scenario: Warranty authority is absent

- **GIVEN** current schema-v4 room data is loaded
- **WHEN** the room summary renders
- **THEN** warranty and occupancy remain visible as permanent rows
- **AND** both use the safe no-data presentation rather than invented values

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

The parent `Порт` column SHALL display `—` (or an equivalent not-applicable cue), because schema v4 defines `switch_port` as the equipment attachment port, not as an attribute of the switch parent. Port evidence belongs on the exact equipment child row.

A user-friendly switch name MAY be shown only from safe unique current canonical display evidence for that exact switch IP. Otherwise a generic `Коммутатор (<IP>)` style label SHALL be used.

If the room contains no presentable switch-IP or port evidence at all, the card SHALL show a safe empty state equivalent to `Нет данных о сетевых подключениях` rather than an invented topology.

The supplied product direction includes an eventual `Нет подключенных устройств` state for a known room switch. Current schema v4 cannot authoritatively establish a room switch with zero attached room equipment. Therefore that runtime state is explicitly DEFERRED from this change: implementation SHALL NOT fabricate it, and acceptance of this change SHALL NOT require an empty-switch node. A future reviewed source/schema change must establish room-level switch inventory authority before `Нет подключенных устройств` becomes a reachable data-driven state.

#### Scenario: Two room devices share a switch

- **GIVEN** two room records contain the same non-null canonical `switch_ip_address`
- **WHEN** the network tree is rendered
- **THEN** one switch parent is shown for that IP
- **AND** both attached devices appear as deterministic children with their canonical ports
- **AND** the parent Port column is not populated from either child's attachment port

#### Scenario: Known port with missing switch IP is not lost

- **GIVEN** one room record has null `switch_ip_address` and non-null canonical `switch_port`
- **WHEN** the network card renders
- **THEN** the known port remains visible under a `Коммутатор не определён` evidence branch bound to that exact record
- **AND** no switch IP or shared switch identity is guessed

#### Scenario: Empty switch state is deferred honestly

- **GIVEN** no canonical room record/evidence establishes an unattached switch node
- **WHEN** the network card renders
- **THEN** the GUI does not fabricate a switch solely to display `Нет подключенных устройств`
- **AND** the absence of that state is accepted as an explicit current-data limitation of this change

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

### Requirement: Expanded device presentations preserve application intent boundaries and card proportions

Expanded codec, PDU, Matrix, and audio DSP content SHALL be presentation projections of exact per-record state. Restyled widgets SHALL NOT own credential selection, credential fallback, handlers, sessions, transports, successful credential memory, stale-operation authority, request generations, or direct device network I/O.

Existing supported controls SHALL remain connected through their current non-secret application intent/controller boundaries and SHALL remain enabled only when current lifecycle/capability state permits them.

At baseline width, expanded device content SHALL use the full accordion content width. Where a device view has a primary data area plus a secondary actions/status area, their horizontal split SHOULD remain approximately `55-65% / 35-45%`, with `12-20 px` internal card gaps. Full-width tables or meter groups MAY occupy the complete row below those cards. The layout MAY reflow vertically below the minimum supported width without changing authority or hiding required controls.

Controls included in the visual target for capabilities not currently implemented SHALL be visibly disabled. A disabled future control SHALL NOT emit a network/mutation intent, create a worker, acquire a handler/session, start a timer, or fake a successful state change.

#### Scenario: Future reboot control is shown before capability exists

- **WHEN** a reference-aligned device card includes a reboot control but no approved reboot capability exists for that model/path
- **THEN** the control is disabled
- **AND** activating/clicking it cannot perform device I/O or change authoritative state

### Requirement: Audio DSP presentation uses segmented vertical level meters with defined geometry

Audio DSP room presentation SHALL render input/source and output/destination level groups using vertical segmented meters with displayed dBFS values. Meter zones SHALL use semantic theme tokens equivalent to low/normal green, caution yellow, and high orange presentation without altering the underlying numeric dBFS value or meter lifecycle.

At the baseline viewport, an ordinary meter SHALL be approximately `16-22 px` wide and `180-240 px` tall with `10-16 px` horizontal spacing between adjacent channels. Channel label and numeric dBFS text SHALL align below or immediately adjacent to the meter without visually exceeding the meter group's hierarchy. A selected-channel control strip SHALL reserve approximately `32-40 px` control height for gain `+`, `-`, value, and `Mute` controls.

A selected channel SHALL be indicated through a border/background or another non-color-only cue. The gain/mute controls SHALL remain disabled unless a separately approved capability already authorizes the exact operation.

Existing DMP/live meter acquisition SHALL remain owned by the application lifecycle and SHALL NOT move polling/network I/O into the Qt GUI thread merely to animate the new meter.

#### Scenario: DMP meter value updates

- **WHEN** current application-owned live/polling state supplies a new accepted dBFS value
- **THEN** the segmented meter updates its visual segments and numeric dBFS text
- **AND** presentation does not create an additional network poll

### Requirement: Matrix presentation combines signal, HDCP, name, and routing per input with stable column hierarchy

Matrix/IN1804 expanded presentation SHALL use a per-input table that combines at least input number, signal presence/state, HDCP state, input name, and current/active route indication in one row per input.

At baseline table width the visual hierarchy SHOULD allocate columns approximately as follows:

```text
input number      8-12%
signal            16-20%
HDCP              16-20%
input name        30-40%
route/current     18-24%
```

Minor adjustment for localized text is permitted, but input name remains the widest semantic column and number remains compact.

Existing Matrix route interaction SHALL remain available when current capability/lifecycle state permits it. A route action SHALL continue to cross the existing non-secret Matrix intent/application-controller boundary and SHALL NOT call the handler directly from the table widget.

Signal, HDCP, and route state SHALL have text/non-color meaning in addition to semantic icon/color cues.

#### Scenario: Operator selects a Matrix route

- **WHEN** a current Matrix row is connected and routing is authorized
- **AND** the operator selects a route in the new table presentation
- **THEN** the widget emits only the existing non-secret route intent
- **AND** handler/session/credential ownership remains outside the widget

### Requirement: Codec and PDU expanded cards use grouped diagnostic and action surfaces

Codec and PDU expanded presentation SHALL group related state into compact bordered cards/sections rather than one undifferentiated text form. General identity/status SHALL be visually primary; live/read data and tables SHALL receive the largest content area; actions SHALL remain visually distinct and secondary.

At baseline width, a side action/status card when present SHOULD occupy approximately `35-45%` of an adjacent two-card row, with the primary information card occupying the remainder. PDU outlet tables and comparable device data tables SHALL be allowed full-width rows below the summary cards.

Codec presentation MAY include grouped general state, call/presentation state, audio/live state, call-log entry point, and actions. PDU presentation MAY include grouped general device state, outlet table/control state, and actions. Only existing production-supported actions SHALL be actionable in this change; reference-only future actions remain disabled under the future-control contract.

Existing PDU mutation/reconciliation, codec auxiliary/live behavior, and all exact-row interaction gates SHALL remain unchanged by visual restyling.

#### Scenario: Existing PDU outlet action remains real

- **GIVEN** a connected PDU room row whose current lifecycle permits an existing outlet action
- **WHEN** the operator invokes that action from the restyled PDU card
- **THEN** the existing PDU application intent/mutation lifecycle is used
- **AND** no direct handler call is introduced by the new view

### Requirement: Dark and light themes are semantic, geometry-stable, and session-only

The application SHALL support dark and light semantic themes. Every new process launch SHALL start in dark mode regardless of the theme used before the previous process exited.

A user-visible sun/moon theme control SHALL toggle the active palette for the current process only. The application SHALL NOT persist theme choice to a file, settings store, registry, environment variable, inventory, credential file, or other durable state.

Theme switching SHALL preserve the same baseline geometry, spacing scale, card hierarchy, disabled-control clarity, focus indication, and status meaning. Theme switching SHALL NOT intentionally resize/reflow cards or rows at the same window size. Both themes SHALL keep primary text, secondary text, borders, focus, status cues, and disabled controls visually distinguishable.

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
- **AND** room/card/row geometry remains materially unchanged
- **AND** room authority, live/network ownership, and accepted diagnostic caches remain unchanged
