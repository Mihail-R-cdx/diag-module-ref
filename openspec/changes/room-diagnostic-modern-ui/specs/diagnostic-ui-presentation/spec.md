## ADDED Requirements

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

Expanded Audio DSP, Matrix/IN1804, codec, and PDU content SHALL remain presentation projections of exact per-record state using the existing supported production presentation path for that family. The foundation MAY add only the minimum container/reparenting/theme compatibility needed to mount the current view in the common room accordion and keep it reachable at supported window sizes.

This change SHALL NOT define or implement a new family-specific internal visual contract. It SHALL NOT require new Audio segmented-meter geometry, a new Matrix column hierarchy, new codec grouped cards, new PDU grouped cards, or new screen-specific reference-only controls. Those redesigns belong to separate follow-up OpenSpec changes after this foundation is merged.

Existing supported controls SHALL remain connected through their current non-secret application intent/controller boundaries and SHALL remain enabled only when current lifecycle/capability state permits them. Existing Matrix routing, PDU mutation/reconciliation, codec auxiliary/live behavior, and Audio DSP live/meter behavior SHALL remain governed by the current corresponding lifecycle contracts.

Compatibility adaptation SHALL NOT make expanded widgets authoritative for credential selection/fallback, handlers, sessions, transports, successful credential memory, stale-operation authority, request generations, exact-row identity, or direct device network I/O.

#### Scenario: Existing device view opens inside the common accordion

- **GIVEN** an exact supported room row has an existing expanded presentation path
- **WHEN** the operator expands that row under the new common accordion
- **THEN** the existing family presentation remains reachable and bound to that exact row state
- **AND** no family-specific redesign is required for acceptance of this change
- **AND** no widget gains direct credential/session/network authority

#### Scenario: Existing device action preserves its application boundary

- **GIVEN** an existing current device-family action is authorized by its current lifecycle
- **WHEN** the operator invokes it from the reused expanded presentation inside the accordion
- **THEN** the existing application intent/controller boundary is used
- **AND** the foundation introduces no direct handler call or parallel network lifecycle

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