# diagnostic-ui-presentation Specification

## Purpose
TBD - created by archiving change room-diagnostic-modern-ui. Update Purpose after archive.
## Requirements
### Requirement: Diagnostic shell follows a self-contained modern room-oriented foundation contract

The desktop application SHALL present the user-visible title `Диагностический модуль` and SHALL use a card-based desktop layout with consistent semantic spacing, typography, borders, radii, standard Qt/device-class icons, and status styling. External screenshots are product-design inputs only; implementation and review SHALL be possible from this repository-local foundation contract without access to the original conversation images.

The baseline visual acceptance viewport SHALL be `1440 x 900` logical pixels. The layout SHALL remain usable at a minimum `1180 x 720` logical-pixel window; below the baseline, vertical scrolling or controlled card reflow MAY occur, but target-search, top Refresh, current selected-room cue, room/network peer tiles, common equipment accordion, and expanded current device content SHALL remain reachable.

At the baseline viewport the following common visual scale SHALL apply:

```text
outer content margin              20-28 px
major section gap                 16-24 px
card internal padding             16-20 px
card radius                       8-12 px
toolbar/control height            44-56 px
collapsed equipment row height    38-46 px (accepted target about 42 px)
common equipment-row device-class icon  approximately 28 x 28 px
section icon                       18-24 px
room hero icon                    28-36 px
body text                         10-11 pt
secondary text                    9-10 pt
section heading                   12-14 pt
page/application heading          18-22 pt
```

The primary toolbar SHALL expose the single target-search field, top Refresh, application actions, and the session theme control. At baseline width, the target-search area including its selected-room cue SHALL consume approximately 45-60% of the usable toolbar width; top actions SHALL remain compact and SHALL NOT visually dominate the search field.

Room mode SHALL place the outer room-summary peer tile and the outer network peer tile above the equipment accordion. At baseline width the two outer tiles SHALL have aligned tops and approximately peer weight with a width ratio between `0.9:1` and `1.1:1`; neither tile SHALL collapse into a narrow sidebar while the other occupies the full row. The accepted upper-tile block SHALL be about `186` logical pixels high (a tuning range of `178-194` is permitted). The left room-summary tile SHALL have no separate visible heading `Информация о комнате`, section icon, SectionCard header, header spacer, or header chrome; its room-information body is its sole visible content. The right network tile SHALL have no separate visible heading, icon, dynamic switch-count title, header spacing, or SectionCard header; its network table/tree is its sole visible content.

The foundation contract itself does not define final family-specific visual geometry for Audio DSP, Matrix/IN1804, codec, or PDU expanded content; such geometry is owned only by dedicated reviewed follow-up OpenSpec changes. MIH-10 and MIH-11 are those approved follow-ups for Audio DSP and Matrix/IN1804 respectively; codec and PDU redesign remain deferred. The common shell redesign SHALL NOT make Qt widget state authoritative for target identity, credentials, request generation, handler/session ownership, or device I/O.

The accepted shell uses a transparent/common diagnostic-tree background with card-like equipment surfaces. Its compact accordion has no visible tree column header and no visible trailing common overflow/action placeholder. A hidden data-bearing or accessibility surface MAY retain cycle health, but the shell SHALL NOT insert a second visible global-cycle line between the upper tiles and the accordion. Hover, repaint, resize, theme switch, reflow, and scrolling remain presentation-only and SHALL start no device I/O or change authority.

#### Scenario: Room shell is rendered at baseline size

- **WHEN** room mode has an authoritative current room at the baseline viewport
- **THEN** the headerless room-summary tile and headerless network table-only tile appear side by side above the compact equipment accordion with peer visual weight
- **AND** the accepted common spacing/typography/icon scale and taller upper-tile geometry are applied
- **AND** device/network authority remains outside the presentation widgets

#### Scenario: Minimum supported window remains usable

- **WHEN** the application is shown at `1180 x 720` logical pixels
- **THEN** target-search, selected-room cue when present, top Refresh, room/network peer tiles, equipment accordion, and current expanded device content remain reachable through controlled reflow/scrolling
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

The room-summary card SHALL permanently include labelled presentation slots for `Название комнаты`, `Адрес комнаты`, `Гарантия`, and `Занятость`, plus VIP. Current canonical `room_name`, `room_address`, and `room_vip` SHALL use the room metadata authority defined by `room-equipment-diagnostics`.

The outer room-summary peer tile SHALL retain its container but render no separate `Информация о комнате` title, section icon, SectionCard header, header spacer, or header chrome. Its first visible content row SHALL be `Название комнаты`; `Адрес комнаты`, `Гарантия`, and `Занятость` SHALL follow in that order. VIP remains associated with the room-name presentation. The body MAY retain ordinary non-zero content padding and SHALL NOT be made full-bleed against the outer tile border merely because the header is absent.

The confirmed temporary product decision for this change is that the permanent warranty row SHALL always render exactly `Гарантия: Нет гарантии`. This is presentation-only placeholder text: it SHALL NOT fabricate or publish canonical warranty evidence, set a session warranty field, change the inventory schema, infer warranty from unrelated inventory columns, timestamps, device data, room text, or local UI state, or start an external lookup/device or network I/O. Future real warranty integration is tracked as Linear `MIH-28` — `Room diagnostics: заменить заглушку «Нет гарантии» реальными данными` — and requires a separately reviewed authoritative source and canonical semantics before implementation.

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

#### Scenario: Warranty placeholder is always visible and fixed

- **WHEN** the room summary renders with any room evidence state
- **THEN** its warranty row renders exactly `Гарантия: Нет гарантии`
- **AND** it never renders `Нет данных`, `—`, or `Unknown`

#### Scenario: Warranty placeholder does not create authority or I/O

- **WHEN** the room summary renders or refreshes the warranty placeholder
- **THEN** no canonical warranty field, session warranty field, inventory-schema change, inference, lookup, device request, or network I/O is created
- **AND** room name, address, VIP, and occupancy retain their existing independent authority and behavior

#### Scenario: TE40 static microphone gain is distinct from live level

- **GIVEN** TE40 has accepted static `microphone_volume = 18`
- **AND** current live `MicValueIndex` evidence is also available
- **WHEN** the Audio card renders
- **THEN** the configured microphone value region displays `+6 dB`
- **AND** `Микрофон (уровень)` reflects only the live sample
- **AND** neither value overwrites or reclassifies the other

#### Scenario: TE40 microphone plus requests exactly one dB

- **GIVEN** TE40 has current accepted static `microphone_volume = 18` / `+6 dB`
- **AND** room interaction controls are eligible
- **WHEN** the operator activates microphone `+`
- **THEN** the presentation requests the typed exact-model gain intent for `+7 dB` / wire `19`
- **AND** presentation itself sends no protocol request
- **AND** microphone mute state is not changed by that gain intent

#### Scenario: TE50 shares the Huawei dB microphone contract

- **GIVEN** exact model is `Huawei TE50`
- **AND** accepted configured `microphone_volume = 18`
- **WHEN** the Audio card renders
- **THEN** the configured microphone value displays `+6 dB`
- **AND** no percentage is derived from the speaker `0..21` scale
- **AND** microphone mute and microphone LIVE remain separate evidence

#### Scenario: Huawei microphone upper bound remains distinct from speaker upper bound

- **GIVEN** exact model is `Huawei TE40` or `Huawei TE50`
- **AND** accepted configured `mic1Value = 24`
- **WHEN** the Audio card renders
- **THEN** configured microphone gain displays `+12 dB`
- **AND** the value is not rejected merely because Huawei speaker volume has upper bound `21`

### Requirement: Network card preserves all available canonical connection evidence

The headerless right network peer tile SHALL use a compact summary tree/table with columns exactly `Коммутатор (IP)`, `Порты`, and `Подключено устройств`. It SHALL contain no separate visible `Сетевые подключения` title, dynamic `Сетевые подключения (N коммутаторов)` title, network-card icon, SectionCard header, or header spacer. The table/tree SHALL be the tile's sole visible content and fill all available area within the preserved outer peer tile; ordinary SectionCard inner padding or margins SHALL NOT reduce that table/tree area. Rendering, hover, disclosure, child-row display, and local table interaction SHALL be presentation-only and SHALL perform no device network I/O.

Canonical connection evidence SHALL be presented according to these exact cases:

```text
switch_ip_address known + switch_port known
    -> one summary row for the exact switch IP with that port in its summary

switch_ip_address known + switch_port null
    -> one summary row for the exact switch IP; its port summary may be `Нет данных`

switch_ip_address null + switch_port known
    -> do not invent or merge switch identity
    -> one record-bound `Коммутатор не определён` row with that exact port and count 1

switch_ip_address null + switch_port null
    -> that record contributes no switch/port topology evidence
```

Records with unknown switch IP but known port SHALL NOT be grouped together merely because port text matches. Each such summary row remains tied to the exact canonical record evidence so no fictitious common switch is created.

For each authoritative switch-IP row, attached canonical room-equipment records SHALL be ordered by canonical `record_id`. Its `Порты` cell SHALL collect non-null canonical `switch_port` values in that order and de-duplicate by first occurrence:

```text
zero known child ports     -> `Нет данных`
one unique known port      -> that exact port, e.g. `Gi1/0/5`
multiple unique ports      -> comma-separated exact values in deterministic child order
```

The summary row SHALL use a safe generic name equivalent to `SW (<IP>)` unless safe unique current canonical display evidence establishes a user-friendly name. The displayed ports summary and record count SHALL not be persisted as canonical data and SHALL not be used as switch identity, routing, or device-topology authority.

Each known-switch summary row SHALL be a real disclosure parent with one visual child per current canonical room-equipment record attached to that exact switch, ordered by canonical `record_id`. A child SHALL display safe current equipment identity in the first column and that exact record's canonical `switch_port` or `Нет данных` in the Ports column; the parent remains the owner of the aggregate count. Child rows are read-only presentation of existing canonical records and SHALL NOT become target/routing/topology authority or start device I/O.

User expansion/collapse of a known-switch row SHALL update presentation-local disclosure state only. That state SHALL survive background refresh/re-render while the exact `RoomDiagnosticSessionIdentity` remains unchanged and the switch row still exists. Background refresh SHALL NOT independently expand or collapse a current switch row. A different room/session identity or explicit presentation clear SHALL reset prior disclosure state rather than restore it into the new context. The default for a newly encountered known-switch row in a new presentation context SHALL be collapsed.

For a record-bound `Коммутатор не определён` row with a known canonical port, the `Порты` cell SHALL display that exact port and count `1`. Such rows SHALL remain ungrouped and need not expose disclosure children because no authoritative common switch identity exists.

If the room contains no presentable switch-IP or port evidence at all, the table/tree SHALL show a safe empty state equivalent to `Нет данных о сетевых подключениях` rather than an invented topology.

The confirmed product decision that room switches with zero attached canonical equipment are not implemented remains unchanged. Current schema v4 cannot authoritatively establish such a switch, so implementation SHALL NOT fabricate it merely to provide an empty disclosure parent.

#### Scenario: Network tile renders table without a title

- **WHEN** the right network peer tile renders
- **THEN** no visible `Сетевые подключения` text, dynamic switch-count title, network-card icon, or separate header is rendered
- **AND** the network table/tree is visible
- **AND** its column headers are exactly `Коммутатор (IP)`, `Порты`, and `Подключено устройств`

#### Scenario: Network table fills the peer tile

- **WHEN** the right network peer tile renders at an accepted layout size
- **THEN** the table/tree fills its available outer-tile area
- **AND** no header spacer or ordinary SectionCard inner padding reduces that area

#### Scenario: Room summary has no separate title chrome

- **WHEN** the upper peer tiles render
- **THEN** the left room-summary tile renders no visible `Информация о комнате` text, section icon, SectionCard header, header spacer, or header chrome
- **AND** its room-information body remains visible without becoming full-bleed against the preserved outer tile border
- **AND** the right network tile does not add a separate heading

#### Scenario: Network data and disclosure semantics remain unchanged

- **GIVEN** current canonical switch evidence and same-context disclosure state exist
- **WHEN** the table-only network tile renders or re-renders
- **THEN** grouping, canonical `switch_ip_address`/`switch_port` evidence, counts, child rows, ordering, unknown-switch behavior, empty-state semantics, and disclosure restoration retain their existing contract
- **AND** no visual simplification changes topology or target authority

#### Scenario: Network tile rendering starts no I/O

- **WHEN** the table-only network tile renders, reflows, repaints, or restores disclosure state
- **THEN** it starts zero device/network I/O

#### Scenario: Two room devices share a switch

- **GIVEN** two room records contain the same non-null canonical `switch_ip_address`
- **AND** their canonical ports are `Gi1/0/5` and `Gi1/0/6`
- **WHEN** the network summary renders
- **THEN** one switch summary row is shown for that IP
- **AND** its Port summary displays `Gi1/0/5, Gi1/0/6` and its device count is `2`
- **AND** expanding that row reveals exactly those two canonical equipment children in deterministic `record_id` order
- **AND** neither displayed summary nor children become canonical switch/target state

#### Scenario: Parent port summary de-duplicates repeated child evidence

- **GIVEN** several canonical records under one exact switch IP contain the same non-null canonical port text
- **WHEN** the network summary renders
- **THEN** the repeated port appears once according to first canonical `record_id` occurrence
- **AND** each canonical record may still appear as its own disclosed visual child
- **AND** the summary does not replace the per-record canonical evidence

#### Scenario: Known port with missing switch IP is not lost

- **GIVEN** one room record has null `switch_ip_address` and non-null canonical `switch_port`
- **WHEN** the network card renders
- **THEN** the known port remains visible under a `Коммутатор не определён` record-bound row with count `1`
- **AND** no switch IP, shared switch identity, or fictitious disclosure group is guessed

#### Scenario: User disclosure survives same-context refresh

- **GIVEN** the operator has manually expanded or collapsed a known-switch summary row
- **AND** the current `RoomDiagnosticSessionIdentity` remains unchanged
- **WHEN** background refresh/re-render rebuilds current network evidence
- **THEN** the rebuilt current switch row restores that user disclosure state
- **AND** refresh itself does not choose the expanded/collapsed state
- **AND** restoration performs zero device I/O

#### Scenario: Empty switch state is explicitly out of current scope

- **GIVEN** the confirmed product scope defers room switches with zero attached canonical equipment
- **WHEN** no canonical room record/evidence establishes an unattached switch node
- **THEN** the GUI does not fabricate a switch solely to display an empty disclosure group
- **AND** acceptance does not require that state in this change

### Requirement: Equipment rows share one non-color accordion header contract

Every room equipment record SHALL use one compact top-level row layout equivalent to:

```text
expand chevron -> device-class icon -> model label -> status cue + status text -> IP
```

At baseline size a collapsed row SHALL remain within the `38-46 px` height range, targeting about `42 px`. The device-class icon SHALL be approximately `28 x 28 px` and the chevron/icon cluster SHALL remain compact. Model text SHALL receive the largest flexible width, and status and IP SHALL remain readable without forcing the row into multiple lines under ordinary baseline content. The tree header and trailing common overflow/action placeholder are intentionally not visible.

Status SHALL remain understandable without color alone. The row SHALL retain explicit text/non-color meaning for connected, waiting, connecting, unsupported, missing-IP, ambiguous-IP, failed, connection-lost, and other approved states. Color MAY reinforce but SHALL NOT be the only meaning.

Exactly one room equipment row MAY be expanded at a time. Expanding another expandable row SHALL collapse the previous row. Accordion changes SHALL remain presentation/current-selection behavior and SHALL NOT reorder the automatic room acquisition queue.

Every room equipment row, including an expanded PDU row, SHALL contain no right-side device action after the common identity/status/IP content. The absence of a row action SHALL NOT create, imply, or require a hidden/disabled placeholder or an alternate direct network path.

All authorized PDU controls SHALL remain inside expanded content and through current application intent/controller boundaries. For the modern PDU dashboard, the pre-existing generic expanded-content refresh affordance labelled `Локальный опрос` (or an equivalent legacy generic Local Refresh control) SHALL NOT be rendered. `Обновить статус` inside `Управление розетками` is the sole visible PDU Local Refresh entry point and SHALL publish only the existing exact-row `LOCAL_REFRESH` lifecycle.

#### Scenario: Another device row is expanded

- **GIVEN** one expandable equipment row is open
- **WHEN** the operator expands a second row
- **THEN** the first row collapses
- **AND** only the second row owns current expanded presentation selection
- **AND** automatic queue order is unchanged

#### Scenario: Compact row remains understandable without color

- **WHEN** a compact equipment row renders any approved connection state
- **THEN** it displays explicit status text/non-color meaning in addition to optional color
- **AND** no visible common overflow placeholder or alternate direct network path is required

#### Scenario: PDU row uses the common header without a family action

- **GIVEN** a current supported PDU row is collapsed or expanded
- **WHEN** its top-level row is rendered
- **THEN** it uses the common chevron, icon, model, status and IP anatomy
- **AND** no right-side PDU action is visible

#### Scenario: Modern expanded PDU exposes one Local Refresh entry point

- **GIVEN** the modern PDU dashboard is visible
- **WHEN** the operator inspects available refresh controls
- **THEN** the visible refresh entry point is exactly `Обновить статус`
- **AND** no generic `Локальный опрос` or header refresh affordance is rendered
- **AND** the control resolves to the existing exact-row `LOCAL_REFRESH` lifecycle

### Requirement: Existing expanded device presentations remain compatible and are not redesigned by this foundation

For this foundation, `existing`, `current`, or `reused` device-family presentation means the **current room-mode exact-row presentation/interaction surface** for that family, as bound by the room diagnostic presentation path and the unified exact-model registry/lifecycle capabilities. A standalone or legacy single-device screen SHALL NOT be selected, embedded, or treated as room capability merely because it represents the same device family. The foundation MAY add only the minimum container/reparenting/theme compatibility needed to keep the current room-mode surface reachable at supported window sizes.

Expanded Audio DSP, Matrix/IN1804, codec, and PDU content SHALL remain projections of exact per-record state through that current room-mode surface. Dedicated reviewed family changes MAY define their family-specific internal visual contract inside that exact-row surface. MIH-10 provides the approved Audio DSP family redesign and MIH-11 provides the Matrix/IN1804 family redesign. The user-approved common room visual refinement in MIH-11 supersedes only the foundation's provisional upper-card and compact-accordion geometry; it neither creates a new data model nor changes the capability or lifecycle meaning of codec and PDU presentations.

Existing **room-mode** controls SHALL remain connected through their current non-secret application intent/controller boundaries and SHALL remain enabled only when current registry/lifecycle capability state permits them. The foundation SHALL NOT promote an action, control, or signal that exists only on a standalone/single-device screen into room mode. Existing room-mode PDU mutation/reconciliation, codec auxiliary/live behavior, Audio DSP live/meter behavior, and Matrix room live/local-refresh behavior SHALL remain governed by their current corresponding lifecycle contracts.

For Matrix/IN1804 specifically, MIH-11 supersedes the foundation's temporary read-only room projection only through the exact unified model registration and the existing serialized `MUTATION -> RECONCILIATION` room lifecycle. It SHALL NOT promote standalone Matrix routing as an existing room capability, wire or embed standalone `MatrixScreen.routeRequested` as a room action, or bypass the exact-row route binding and application-owned lifecycle.

Compatibility/family presentation adaptation SHALL NOT make expanded widgets authoritative for credential selection/fallback, handlers, sessions, transports, successful credential memory, stale-operation authority, request generations, exact-row identity, accepted device state, or direct device network I/O.

#### Scenario: Existing room-mode device view opens inside the common accordion

- **GIVEN** an exact supported room row has a current room-mode expanded presentation path
- **WHEN** the operator expands that row under the new common accordion
- **THEN** the current room-mode family presentation remains reachable and bound to that exact row state
- **AND** no standalone/single-device screen is promoted merely because it has the same family
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
- **AND** no Matrix route-mutation intent or registry mutation binding is inferred from the visual capability
- **AND** standalone `MatrixScreen.routeRequested` is not wired into the room accordion

#### Scenario: MIH-11 Matrix routing replaces only the deferred read-only family limitation

- **GIVEN** an exact current `Extron IN1804` room row whose unified registration declares MIH-11 Matrix route mutation/reconciliation bindings
- **WHEN** the modern Matrix output cell produces an approved route intent
- **THEN** routing enters the exact-row serialized room mutation lifecycle
- **AND** existing Matrix room live/local-refresh authority remains unchanged outside the mutation handoff
- **AND** standalone `MatrixScreen.routeRequested` is not room authority
- **AND** no direct widget-to-handler/session path is introduced

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

The modern room Audio DSP presentation SHALL expose local controls visually associated with the currently hovered channel only. They contain a channel context/label, gain decrement `-`, current gain/value, gain increment `+`, and `Mute`; a permanent full-width selected-channel control strip is not part of the accepted dashboard. Existing selected-channel visual emphasis remains a separate local state and SHALL NOT pin this popup after pointer hover ownership is lost.

On the current change base there is no approved exact-row Audio DSP gain/mute mutation binding. Therefore:

```text
gain `-`                disabled/non-actionable
current gain/value      `—` or equivalent `Нет данных`
gain `+`                disabled/non-actionable
`Mute`                  disabled/non-actionable
```

The GUI SHALL NOT infer current gain or mute state from meter level, normalized fill, Biamp signal-source values, labels, selection state, popup history, or other local widget state. Disabled placeholders SHALL emit no application/room interaction intent, signal, worker start, handler/session acquisition, protocol command, or device request.

The popup lifetime SHALL follow the current hover/current-expanded-row contract in this change: it remains visible while the pointer is over the active scale or popup, may bridge those surfaces with a presentation-only single-shot timer, switches to another valid scale when entered, and closes when neither surface owns hover. Collapse/current-row/session-context invalidation SHALL revoke it as defined by `Audio DSP popup lifetime follows current hover and expanded-row context`.

Enabling any of these controls requires a later approved capability defining exact target identity, application-owned intent binding, mutation safety, reconciliation/readback, lifecycle/currentness, and failure semantics. The popup's local target identity SHALL never itself satisfy those requirements.

#### Scenario: Hovered channel exposes only disabled future controls

- **GIVEN** a current expanded room Audio DSP meter channel owns pointer hover
- **WHEN** its local future controls are shown
- **THEN** `-`, `+`, and `Mute` are disabled/non-actionable
- **AND** current gain/value is shown as `—` or equivalent no-data text when no authoritative field exists
- **AND** interacting with the disabled presentation starts no device I/O or mutation intent

#### Scenario: Selected channel exposes only disabled future controls

- **GIVEN** a current room Audio DSP meter channel is locally selected for visual emphasis
- **AND** its local future controls are visible only because the current hover/current-expanded-row popup contract permits them
- **WHEN** the future controls are presented for that selected channel
- **THEN** `-`, `+`, and `Mute` are disabled/non-actionable
- **AND** current gain/value is shown as `—` or equivalent no-data text when no authoritative field exists
- **AND** selection does not authorize mutation, device I/O, or keep the popup open after hover ownership is lost

#### Scenario: Local selection does not authorize or pin future controls

- **GIVEN** one Audio DSP channel remains locally selected for visual emphasis
- **WHEN** pointer hover leaves both that channel scale and the popup
- **THEN** the local controls may close
- **AND** selection neither enables those controls nor creates a mutation/network target

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

### Requirement: Expanded Matrix redesign targets the current room exact-row presentation surface

The modern Matrix presentation SHALL render inside the current room-mode exact-row presentation owned by `RoomDiagnosticTreeWidget` for every exact Extron Matrix registration approved by `device-diagnostics-and-control`, including the existing `Extron IN1804` baseline and approved IN1806, IN1808, IN1608 xi, and DTP CrossPoint profiles. XTP/XTP II are deferred and are not supported production Matrix rows in this change.

A focused presentation-only Matrix dashboard component MAY consume accepted exact-row evidence and emit safe non-secret local intents, but SHALL NOT own room identity, target-search, request generation/currentness, credentials, handler/session lifecycle, polling/live ownership, mutation delivery, reconciliation authority, profile selection, SIS syntax, or device network I/O.

The standalone `MatrixScreen` remains a separate presentation/lifecycle surface and SHALL NOT become room authority merely because more Matrix models are supported.

#### Scenario: Expanded Matrix room row uses the modern presentation
- **GIVEN** the current room session contains an expandable exact supported Extron Matrix row
- **WHEN** the operator expands that row
- **THEN** the modern Matrix presentation renders inside the exact-row room content
- **AND** room/record authority remains the current exact row
- **AND** standalone `MatrixScreen` is not required or promoted as room authority

### Requirement: Matrix dashboard follows the approved three-card field-placement hierarchy

At the foundation baseline viewport of `1440 x 900` logical pixels, expanded Matrix content SHALL render three horizontal cards in this order and SHALL retain an inspection height of at least `360` logical pixels:

```text
Общая информация -> Матрица (входы и коммутация) -> Быстрые действия
```

The Matrix card SHALL be visually dominant. Baseline content-width allocation SHALL remain within these approximate ranges:

```text
Общая информация          25%
Матрица                    53%
Быстрые действия           22%
```

The proportions MAY vary by a small implementation-tuning amount while preserving the accepted `25 / 53 / 22` hierarchy. General-information facts SHALL be top-aligned with a visually right-aligned value column and spare space below the facts. Quick-action controls SHALL remain adjacent to their heading with remaining vertical space below. Exact borders and gaps MAY use theme tokens, but order, dominant central hierarchy, readable baseline content, and absence of baseline horizontal clipping are normative.

At `1180 x 720`, controlled reflow or existing expanded-content scrolling MAY be used provided all required Matrix information/table/actions remain reachable, table semantic order is preserved, and route/currentness authority does not change. Dark/light theme switching SHALL be presentation-only and SHALL perform no Matrix device I/O.

#### Scenario: Baseline Matrix dashboard preserves hierarchy

- **GIVEN** a current connected Matrix row is expanded at `1440 x 900`
- **WHEN** its presentation is laid out
- **THEN** General information is the left narrow card
- **AND** Matrix inputs/routing is the dominant center card
- **AND** Quick actions is the right narrow card
- **AND** all three are readable without baseline horizontal clipping

### Requirement: Matrix General information preserves approved field order without fabricating evidence

The Matrix `Общая информация` card SHALL always reserve and render rows in this order:

```text
Модель
MAC-адрес
Серийный номер
Версия прошивки
Температура
```

For every exact Extron Matrix model supported by this change, a room Matrix full
refresh MAY be classified as complete and successful only when accepted current
evidence establishes an authoritative non-empty value for all five rows.

Source authority SHALL be:

- `Модель`: accepted exact Matrix identity/canonical model for the current operation;
- `MAC-адрес`: mandatory current canonical room/inventory evidence;
- `Серийный номер`: mandatory current canonical room/inventory evidence;
- `Версия прошивки`: authoritative current exact-profile SIS read;
- `Температура`: authoritative current exact-profile SIS read;

Presentation and acquisition SHALL NOT infer or synthesize a required value from
another field, model text, reference artwork, logs, a prior snapshot, widget state,
default zero, placeholder text, or a command copied speculatively from another
family. An unproven authoritative read for a required row is a blocking capability
gap for that supported profile.

`Нет данных` (or the foundation safe no-data equivalent) remains truthful only
for a failed, incomplete, stale, or otherwise non-successful current acquisition.
Such a state SHALL NOT be classified as a complete successful full refresh.
A prior accepted value SHALL clear rather than survive into a current incomplete
snapshot.

Numeric temperature `0` remains a valid value only when successful current
device evidence explicitly establishes zero.

#### Scenario: Current Matrix snapshot lacks reference-only information fields

- **GIVEN** a current Matrix acquisition lacks one or more authoritative General-information values
- **AND** canonical room/inventory evidence cannot supply MAC/serial or another mandatory current read did not establish its value
- **WHEN** the General information card renders and the acquisition is classified
- **THEN** each missing row renders truthful no-data
- **AND** the acquisition is not classified as a complete successful full refresh
- **AND** no unrelated or synthetic value is inserted to make the card look complete

#### Scenario: Failed model and temperature evidence remains no-data

- **GIVEN** current Matrix normalization has no accepted exact model evidence or no authoritative current temperature evidence
- **WHEN** the General information card renders
- **THEN** the missing field shows `Нет данных`
- **AND** local `Unknown`, stale prior evidence, or synthetic numeric zero is not rendered as device evidence
- **AND** the refresh is not classified as complete successful

#### Scenario: Real zero temperature remains visible

- **GIVEN** accepted current Matrix evidence contains temperature numeric zero from a successful authoritative device response
- **WHEN** the General information card renders
- **THEN** `Температура` renders that zero value
- **AND** it is not replaced with `Нет данных`

#### Scenario: Successful full refresh fills all five rows

- **GIVEN** an exact supported Matrix model completes its authoritative current full-refresh acquisition
- **WHEN** that refresh is accepted as complete successful
- **THEN** all five General-information rows contain authoritative values
- **AND** none renders `Нет данных`, a placeholder, or stale prior evidence

#### Scenario: Missing inventory MAC or serial blocks complete success

- **GIVEN** the current exact Matrix row lacks canonical room/inventory MAC or serial evidence
- **WHEN** a complete full refresh is attempted
- **THEN** no device fallback is guessed or sent for that field
- **AND** complete-success classification is prevented
- **AND** no guessed MAC or serial is synthesized

### Requirement: Matrix input table uses proven data-driven rows and the approved column order

The central Matrix table SHALL use this semantic order:

```text
[input ordinal] | Сигнал | HDCP | Входы | [one route column per authoritative available logical output]
```

The leading ordinal column remains compact. `Входы` displays accepted input name when supported/current evidence exists. Route columns SHALL be generated from authoritative `available_output_ids`; they SHALL NOT be hard-coded to output 1 and SHALL NOT be generated from raw physical connector count.

If authoritative output-name evidence exists for an output ID, that name SHOULD be used as the route-column heading. Otherwise the deterministic fallback SHALL be `Output <id>`; the existing single-output IN1804 compatibility presentation MAY retain its accepted `Main Output` fallback for output 1.

Rows SHALL follow a proven accepted current input topology. The presentation SHALL NOT fabricate eight rows, compress gaps in available IDs, or make an unproven ordinal actionable.

A device exposing several physical connectors that share one logical route SHALL still create one route column for that logical route. A multi-output CrossPoint creates one column per authoritative available logical output. Deferred XTP/XTP II board topology does not create production route columns in this change.

#### Scenario: Four-input accepted Matrix is not rendered as eight inputs
- **GIVEN** accepted current Matrix evidence establishes four inputs
- **WHEN** the modern table renders
- **THEN** exactly four authoritative input rows are presented in accepted order
- **AND** no additional rows are fabricated from visual reference or legacy defaults

#### Scenario: Input count is unproven
- **GIVEN** current Matrix normalization cannot establish authoritative input topology/model capability
- **WHEN** the modern table renders
- **THEN** eight rows are not fabricated
- **AND** no unproven input ordinal is actionable for routing

#### Scenario: Multi-output Matrix preserves output identity
- **GIVEN** accepted current topology exposes available outputs `[1, 2, 5, 6]`
- **WHEN** the modern table renders
- **THEN** four route columns are rendered with identities `1`, `2`, `5`, and `6`
- **AND** outputs `5` and `6` are not relabeled as `3` and `4`

#### Scenario: Duplicate physical connector does not become another route column
- **GIVEN** multiple physical output connectors share one logical route
- **WHEN** the Matrix table renders
- **THEN** exactly one route column represents that logical route

### Requirement: Matrix signal, HDCP presence, and route presentation remains meaningful without color

For each accepted input row, signal state SHALL distinguish confirmed presence, confirmed absence, and UNKNOWN. Existing compact signal indicators and their non-color semantic/tool-tip/accessibility meaning remain unchanged.

The `HDCP` column SHALL represent only normalized **current input HDCP presence/state** produced by the active approved profile. Presentation SHALL NOT decode raw SIS `1/2` values itself. It SHALL NOT display HDCP version, input authorization/configuration, or output HDCP state in the input HDCP column. Failed/malformed/unrecognized/missing input-HDCP evidence remains UNKNOWN rather than fabricated `нет`.

HDCP cells SHALL use compact centered indicators rather than `есть`, `нет`,
`да`, or `Нет данных` as their primary visible text: `PRESENT_HDCP` is a
filled green indicator; `PRESENT_NO_HDCP` and `ABSENT` are neutral empty
indicators; `UNKNOWN` is neutral and non-positive. Qt semantic data, tooltips,
and accessibility SHALL retain the four distinct canonical states. Signal
UNKNOWN SHALL likewise never render as a green positive indicator. Input-name
and HDCP cell contents SHALL be horizontally centered.

For every authoritative available logical output, route state SHALL derive only from fail-closed accepted `routes[output_id]` evidence:

```text
routes[output_id] == this input  -> positive/active semantic
known different routed input    -> neutral/not-selected semantic
explicit untied output          -> no input cell active for that output
missing/unknown route evidence  -> neutral UNKNOWN semantic
```

For existing IN1804 compatibility state, accepted `current_connection` MAY project to `routes[1]`; it remains valid only through the existing fail-closed IN1804 normalization contract. Route ACK/local click state SHALL NOT become accepted active-route authority before reconciliation.

#### Scenario: Compact Signal and HDCP remain semantically explicit
- **GIVEN** accepted signal evidence is present, absent, and UNKNOWN and accepted normalized input HDCP evidence is present, absent, and unknown for corresponding rows
- **WHEN** the Matrix table renders
- **THEN** Signal cells retain explicit non-color semantic meaning
- **AND** HDCP cells present the corresponding accepted normalized meanings
- **AND** no HDCP version token is displayed

#### Scenario: Route ACK does not optimistically recolor the table
- **GIVEN** a route mutation has received apparent send success but reconciliation is not yet accepted
- **WHEN** the Matrix table is rendered
- **THEN** the previously accepted `routes[target_output_id]` remains route-state authority
- **AND** the requested cell is not shown as authoritative `активен` solely because of the ACK

#### Scenario: One input may be active on multiple outputs
- **GIVEN** accepted routes are `{1: 3, 2: 3, 3: 6}`
- **WHEN** the Matrix table renders
- **THEN** input `3` is active in output columns `1` and `2`
- **AND** input `6` is active in output column `3`

#### Scenario: Untied output has no active input
- **GIVEN** accepted route state for output `4` is explicitly untied
- **WHEN** output `4` is rendered
- **THEN** no input cell in output `4` is presented as active

### Requirement: Matrix output cells emit only approved exact-row route intent

A non-active route cell SHALL be actionable only when the exact current expanded row is an approved supported Extron Matrix exact model/profile, has usable connected accepted state, is not stale/degraded/blocked/unconfirmed, the unified registration advertises approved Matrix mutation/reconciliation capability, the serialized room interaction lane permits mutation, and both the input ID and output ID are authoritative available IDs in the current topology.

Presentation SHALL emit only a non-secret immutable route intent containing accepted `input_id` and `output_id` plus the existing exact-row identity needed by composition. It SHALL NOT contain credentials, handler/session references, raw target-search text, raw SIS command strings, standalone screen selection, or global Matrix target state.

The currently active cell remains no-op/non-actionable. Stale, degraded, failed, blocked, non-current, unsupported, unproven-input, unavailable-output, or otherwise unauthorized cells expose no route intent.

Presentation SHALL NOT call `ExtronIN1804Handler`, any CrossPoint handler, `MatrixController.request_route`, socket/transport methods, or other device I/O directly. Composition SHALL revalidate exact-row authority and require the existing explicit operator confirmation before the mutation lifecycle begins.

#### Scenario: Operator selects another current input
- **GIVEN** a connected current exact Matrix row has one authoritative current route on output `1`
- **AND** another input is proven, authorized, and non-active for that output
- **WHEN** the operator activates that input/output cell
- **THEN** presentation emits one safe route intent containing the selected input ID and output `1`
- **AND** no Matrix device I/O occurs from the widget
- **AND** composition requires explicit confirmation before mutation lifecycle begins

#### Scenario: Current active route is clicked
- **GIVEN** input N is already authoritative as active for output O
- **WHEN** the operator clicks that exact active cell
- **THEN** no route mutation intent is submitted
- **AND** no device I/O starts

#### Scenario: Multi-output route intent preserves target output
- **GIVEN** supported CrossPoint output `7` and input `3` are current authoritative available IDs
- **WHEN** the operator activates input `3` in output `7`
- **THEN** presentation emits `input_id=3` and `output_id=7`
- **AND** it does not collapse the intent to output `1`

#### Scenario: Unavailable output exposes no route intent
- **GIVEN** a future supported multi-output profile marks output `13` unavailable
- **WHEN** the table renders
- **THEN** presentation exposes no actionable route cell for output `13`

### Requirement: Expanded room codec presentation uses one self-contained five-card dashboard contract

Every current supported room codec row SHALL render the same expanded codec dashboard after it becomes the current expanded exact row. The dashboard applies to `Huawei TE20`, `Huawei TE40`, `CloudLink Bar 310`, `CloudLink Box 310`, and `Polycom RPG 310` as current-baseline acceptance oracles while runtime model/capability authority remains the unified exact-model registration.

External screenshots or conversation history MAY be used as product-design inspiration, but they are NOT normative acceptance dependencies. Implementation and independent validation SHALL be possible from this repository-local requirement alone.

At the common `1440 x 900` logical-pixel baseline viewport, the expanded codec area SHALL present exactly five top-aligned cards in this left-to-right order:

```text
Состояние | Вызов и презентация | Аудио | Журнал вызовов | Действия
```

The target relative card weights SHALL be:

```text
Состояние              23
Вызов и презентация    17
Аудио                  18
Журнал вызовов         25
Действия               17
```

Per-card tuning of approximately `±4` percentage points MAY accommodate Qt metrics, but the same hierarchy SHALL remain visible: `Состояние` and `Журнал вызовов` are substantial, `Аудио` is compact, and `Действия` is the narrow right action card. The five cards SHALL have aligned top edges and approximately aligned bottom edges at baseline; target card height is `286-326 px`. Horizontal gaps between neighboring cards SHALL be `10-14 px`. Card internal padding SHALL be `14-18 px`. Card border/radius/color SHALL use the shared room foundation rather than a codec-only theme.

At the common minimum supported room window, controlled horizontal/vertical scrolling or deterministic reflow MAY occur, but all five cards, rows and controls SHALL remain reachable and SHALL NOT disappear merely due to width. Reflow SHALL preserve the same logical card order.

Dark theme SHALL be the baseline theme. Light theme SHALL preserve card order, relative geometry, field/control order, spacing class and semantic states using the shared theme. Theme switching, resize, hover, repaint and scrolling SHALL remain presentation-only and SHALL perform no device I/O or authority change.

The dashboard SHALL be presentation/application-intent only: it SHALL NOT own target identity, credentials, handler/session instances, request generations, retries or device I/O.

#### Common card anatomy

At baseline, each card SHALL use this common visual anatomy:

```text
header height                         34-42 px
header/section icon                   18-22 px
card title                            11-12 pt semibold equivalent
body label                             9-10 pt
body primary value                    10-11 pt
secondary/timestamp text               9-10 pt
ordinary data row height              28-34 px
required status-dot diameter           8-10 px
```

Headers SHALL place the icon before the title on one line. Required status rows defined below SHALL place their semantic indicator before/adjacent to the textual value with a stable `8-10 px` dot target. Status meaning SHALL never rely on color alone; the textual state and accessibility/non-color meaning remain required. Values and indicators SHALL not overlap adjacent controls or card boundaries at baseline.

#### Scenario: Current codec row opens at baseline size

- **GIVEN** a current connected supported codec row is expanded at `1440 x 900`
- **WHEN** its expanded presentation is built
- **THEN** the five cards appear in the required order, weight ranges, gaps and aligned baseline geometry
- **AND** the dashboard uses the shared dark-theme card/typography/control language
- **AND** no standalone `CodecScreen` widget state becomes room authority

#### Scenario: Codec dashboard renders in light theme

- **GIVEN** the codec dashboard is visible
- **WHEN** the user switches to light theme
- **THEN** the five-card geometry and field/control order remain unchanged
- **AND** theme switching starts no codec device I/O

### Requirement: Codec call-log card uses normalized newest-first order and reserves three-row preview density

The `Журнал вызовов` card SHALL render at most the first three records from the current accepted normalized newest-first automatic-preview call-log result defined by `device-diagnostics-and-control`. Presentation SHALL NOT re-sort localized timestamp/display strings or manufacture chronology.

At baseline the preview region SHALL reserve visual capacity for three compact records so card height does not change merely because one or two calls are present. Each rendered record row SHALL target `52-64 px` height and contain:

```text
direction/non-color cue        18-22 px visual target
peer/number/display identity   primary line, 10-11 pt
safe timestamp                 secondary line, 9-10 pt
row separator                  subtle shared-theme divider except after last visible row
```

Missing peer or timestamp subfields SHALL render `Нет данных` in that subfield. If zero current accepted automatic-preview records are available, the preview region SHALL display one clear `Нет данных` empty state rather than three fabricated empty records.

The card SHALL contain a visible `Развернуть` action anchored after the preview region, with target height `34-40 px` and full/near-full card-body width. Every explicit activation of `Развернуть` for an eligible current exact row SHALL start a fresh serialized exact-row call-log `AUXILIARY_READ`, even when the card already has a current accepted full automatic-preview snapshot. The accepted automatic-preview snapshot SHALL NOT be treated as the detailed-window load result and SHALL NOT suppress the fresh device read.

While that explicit acquisition is pending, the already accepted room-card preview MAY remain visible as preview-only evidence for its own acquisition epoch. It SHALL NOT be promoted to fresh detailed/statistics authority merely to avoid a loading state.

The detailed call-log window MAY open immediately in its existing loading state when the operator activates `Развернуть`, but it SHALL NOT populate authoritative call rows or usage statistics from the automatic-preview snapshot. Its authoritative detailed rows/statistics SHALL populate only from the fresh explicit acquisition result after application authority accepts that result for the same exact row/generation/currentness. If the fresh explicit acquisition becomes stale, is cancelled/superseded, or otherwise fails currentness before acceptance, it SHALL NOT populate/repopulate authoritative detailed content, publish detailed statistics, mutate replacement presentation, or emit a current-row result for a replacement context.

Expanding or collapsing sections inside one already-open detailed call-log load SHALL continue to reuse that load's already accepted records and SHALL NOT start another device request solely for the section toggle.

The card SHALL NOT own call-log network acquisition. Automatic preview authority, explicit auxiliary-read admission, expansion epochs, cancellation, LIVE handoff, duplicate suppression, stale-result/currentness authority, and serialized lane ownership are defined by `room-device-interaction-lifecycle` and `codec-call-log-usage-statistics`.

#### Scenario: More than three call records are accepted

- **GIVEN** current accepted automatic-preview call-log data contains more than three records in normalized newest-first order
- **WHEN** the preview card renders
- **THEN** exactly the first three normalized records are shown
- **AND** presentation performs no second chronology sort
- **AND** `Развернуть` remains available for a fresh explicit detailed-journal load

#### Scenario: Existing preview does not replace fresh explicit opening

- **GIVEN** current exact row/generation has an accepted full automatic-preview snapshot
- **WHEN** the operator activates `Развернуть`
- **THEN** one fresh serialized exact-row call-log `AUXILIARY_READ` is started
- **AND** the existing room-card preview MAY remain visible while that acquisition is pending
- **AND** the detailed window MAY show only its loading state before fresh acceptance
- **AND** the preview snapshot is not used as the detailed-load/statistics result
- **AND** authoritative detailed content/statistics publish only from the fresh current accepted result

#### Scenario: Fresh explicit opening becomes stale or cancelled

- **GIVEN** a fresh explicit detailed-journal acquisition has started for row/generation A
- **WHEN** A becomes stale, cancelled, or superseded before its result is accepted
- **THEN** its result does not populate or repopulate authoritative detailed content
- **AND** it publishes no detailed statistics into the replacement context
- **AND** it does not mutate the current room-card preview for another row/generation

#### Scenario: Call log has no accepted data

- **WHEN** the current exact codec has no accepted automatic-preview records
- **THEN** the preview region displays `Нет данных`
- **AND** the `Развернуть` action remains present
- **AND** activating `Развернуть` still starts the same fresh serialized exact-row call-log acquisition

### Requirement: Codec action card uses two fixed full-width actions and registry-gated behavior

The `Действия` card SHALL permanently render these actions in this exact vertical order:

```text
Обновить статус
Перезагрузить устройство
```

At baseline each action SHALL have target height `36-42 px`, occupy full or near-full card-body width, and use `10-12 px` vertical separation. `Обновить статус` SHALL use the normal/primary refresh semantic styling; `Перезагрузить устройство` SHALL use the shared disruptive/destructive semantic treatment without implying support when the exact registration marks reboot unsupported.

Their temporary enabled/disabled state SHALL obey the existing room interaction lock/eligibility matrix. Current baseline reboot network capability is unsupported for all five codecs, but the fixed reboot affordance remains present and MAY be locally clickable when no lifecycle lock applies.

`Обновить статус` SHALL be only an alias of the existing exact-row Local Refresh intent/lifecycle. It SHALL NOT create a codec-specific refresh path, second interaction lane, direct handler call or different credential authority.

`Перезагрузить устройство` SHALL resolve support from the exact unified codec-control registration before any room mutation is admitted. With current baseline `UNSUPPORTED`, clicking it while controls are otherwise eligible SHALL show a local informational dialog equivalent to `Операция не поддерживается данной моделью` and SHALL perform no device I/O. This change SHALL NOT infer reboot support from a similarly named standalone method.

If a later approved baseline provides a safe reboot binding, it SHALL require a separate explicit confirmation before entering the existing exact-row state-changing mutation/reconciliation lifecycle; command dispatch/ACK alone SHALL never be final-state authority.

#### Scenario: Refresh action is clicked

- **WHEN** the operator clicks `Обновить статус` on an eligible current codec row
- **THEN** the existing Local Refresh lifecycle is requested for that exact row
- **AND** no codec-specific refresh owner is created

#### Scenario: Current reboot affordance is activated

- **WHEN** the operator clicks `Перезагрузить устройство` for any current five-codec baseline model while controls are otherwise eligible
- **THEN** the unsupported-operation information is shown locally
- **AND** no handler/session is acquired and no reboot command is sent

### Requirement: Codec visual acceptance is measurable from repository-local checkpoints

Manual visual acceptance at `1440 x 900` in dark theme SHALL use these ten repository-local checkpoints; access to an external screenshot is unnecessary:

1. exactly five codec cards remain in the approved left-to-right order;
2. card width weights remain within the approved `23:17:18:25:17` ±4-point envelope;
3. card tops align and card heights/gaps/padding remain within the existing baseline ranges;
4. all card headers use the common icon/title anatomy and typography ranges;
5. `Состояние` and `Вызов и презентация` retain their approved permanent rows/order;
6. `Аудио` renders exactly `Микрофон (уровень) -> Громкость микрофона -> Громкость динамиков`, with no speaker LIVE meter or redundant textual `Live ...` rows, distinct live/static/mute semantics, TE40/TE50 configured MIC1 gain in dB, Huawei speaker `0..21` kept separate, and Box 310 microphone LIVE explicitly unsupported;
7. `Журнал вызовов` preserves three-row preview density/anatomy and places `Развернуть` after the preview;
8. `Действия` retains exactly two vertically stacked full-width actions in the approved order/sizing;
9. state/call cards remain dot-free with right-aligned values; call/presentation use normalized `Да`/`Нет`, and registration uses the required semantic icon/neutral unavailable state;
10. light theme preserves the same geometry/order, including the single microphone live-level slot and both configured control rows, without starting device I/O.

Checkpoints 1, 5, 6, 7, 8 and 9 are mandatory structural/semantic checkpoints. The implementation SHALL satisfy all mandatory checkpoints and at least `9/10` total checkpoints. Font rasterization, platform glyph variation and one-pixel antialiasing differences are not failures when the repository-local geometry/semantic contract is met.

#### Scenario: Independent validator has no source screenshot

- **GIVEN** an independent validator has only the repository and approved OpenSpec artifacts
- **WHEN** the codec UI is manually reviewed at the baseline viewport
- **THEN** the validator can evaluate all ten checkpoints from this specification
- **AND** no external image, prior chat or agent report is required to decide visual conformance

### Requirement: Expanded room PDU presentation uses one self-contained two-card dashboard contract

Every current supported room PDU row SHALL render the same expanded room-mode PDU dashboard after it becomes the current expanded exact row. `Aten PE8208AV` and `Extron IPL T PCS4i` are current-baseline acceptance oracles while runtime model/capability authority remains the existing exact application/PDU capability registration.

External screenshots or conversation history MAY be used as product-design inspiration, but they are NOT normative acceptance dependencies. Only the region opened by expanding a PDU row is in scope for this family change. Implementation and independent validation SHALL be possible from this repository-local contract alone.

At the common `1440 x 900` logical-pixel baseline viewport, the expanded PDU body SHALL contain exactly two top-aligned cards in this left-to-right order:

```text
Основная информация | Управление розетками
```

Their target relative width weights SHALL be `30:70`. Per-card tuning of approximately `±4` percentage points MAY accommodate Qt metrics, but the outlet-management card SHALL remain visually dominant and the information card SHALL remain a supporting card wide enough for a right-aligned value column. Horizontal gap SHALL be `10-14 px`, card internal padding `14-18 px`, and target expanded body height approximately `350-410 px`. The two cards SHALL have aligned tops and approximately aligned bottoms at baseline.

At the common minimum supported room window, deterministic reflow or controlled scrolling MAY occur, but both cards, all fixed controls and current outlet rows SHALL remain reachable. Reflow SHALL preserve the information-before-outlets logical order.

Dark theme SHALL be the baseline theme. Light theme SHALL preserve the same card order, relative geometry, table/action order, spacing class and semantic states using the shared theme. Theme switching, resize, hover, repaint and scrolling SHALL remain presentation-only and SHALL perform no PDU device I/O or authority change.

The dashboard SHALL be presentation/application-intent only and SHALL NOT own exact-row identity, credentials, handler/session instances, request generations, capability support, retries or accepted PDU state.

`Основная информация` values SHALL render as a compact right-aligned value column without the visual chrome of separate input fields. `Управление розетками` SHALL include a font-independent lightning visual icon in its card header. The icon distinguishes the control-oriented card only; rendering it performs no device I/O and creates no device authority.

#### Scenario: Current Aten row opens at baseline size

- **GIVEN** a current connected `Aten PE8208AV` room row is expanded at `1440 x 900`
- **WHEN** its expanded presentation is built
- **THEN** `Основная информация` appears to the left of the visually dominant `Управление розетками` card within the approved weight/gap/padding envelope
- **AND** the dashboard uses the shared room dark-theme card language
- **AND** no standalone PDU widget state becomes room authority

#### Scenario: PDU dashboard renders in light theme

- **GIVEN** the PDU dashboard is visible
- **WHEN** the user switches to light theme
- **THEN** two-card geometry, field/table/control order and state meaning remain unchanged
- **AND** theme switching starts no PDU device I/O

### Requirement: PDU header preserves the common no-right-action anatomy

The common room accordion chevron, device-class icon, exact model label, explicit status cue/text and IP presentation remain intact for every PDU state. The expanded PDU header SHALL NOT add Refresh, Power, kebab/overflow, or a second right-side collapse/expand affordance. The common left chevron remains the sole expand/collapse control.

#### Scenario: Expanded PDU header is rendered

- **WHEN** a supported PDU row becomes the current expanded row
- **THEN** it contains no right-side PDU action after IP
- **AND** the common left chevron remains the expand/collapse affordance
- **AND** no legacy generic `Локальный опрос` is rendered in the expanded body

### Requirement: PDU information card has exactly three fixed room-record-backed rows

`Основная информация` SHALL permanently render exactly these rows in this order:

```text
Модель
Серийный номер
MAC-адрес
```

`Модель` SHALL use the exact current row/application diagnostic model identity. `Серийный номер` SHALL use usable current exact canonical room-record `serial_number` evidence. `MAC-адрес` SHALL use usable current exact canonical room-record `mac_address` evidence. A model-neutral current PDU presentation projection MAY carry those same exact-record values, but Qt state SHALL NOT become a competing source of authority.

The fixed values SHALL remain compact, right-aligned and chrome-free; they are presentation of accepted evidence, not editable input controls.

If serial number or MAC address is absent/unusable, the fixed value SHALL render `—`. The GUI SHALL NOT hide a required row, copy another room record's metadata, query the PDU solely to fill the row, or infer values from display strings.

This dedicated PDU information card SHALL NOT add rows for IP address, firmware, switch connection, device status, input-power state, temperature, humidity, overload or other screenshot-only metadata. IP and current connection state remain available through the common accordion header rather than duplicated into this card.

#### Scenario: Canonical serial number is unavailable

- **GIVEN** the current exact PDU room record has no usable canonical `serial_number`
- **WHEN** `Основная информация` is rendered
- **THEN** the `Серийный номер` row remains in its fixed second position with value `—`
- **AND** no PDU network request is started to fill it

#### Scenario: Information card does not duplicate common header data

- **WHEN** the expanded PDU information card is rendered
- **THEN** it contains exactly `Модель`, `Серийный номер`, `MAC-адрес`
- **AND** IP/connection state remain outside that three-row card

### Requirement: PDU outlet-management card uses one fixed five-column table and fixed action anatomy

`Управление розетками` SHALL place this compact action strip in the same header row as the card title, before the outlet table, in exact left-to-right order:

```text
Обновить статус | Включить всё | Выключить всё
```

The table SHALL have exactly these visible columns in this order:

```text
Розетка | Имя розетки | Состояние | Текущая мощность | Действия
```

At baseline, target relative column weights SHALL be approximately `9:31:12:20:28`, with approximately `±3` percentage points of tuning per column where needed for platform Qt metrics. Table header target height SHALL be `32-40 px`, ordinary outlet row height `28-32 px`, and inter-control spacing in the action cell `4-6 px`.

Current outlet records SHALL be rendered in deterministic ascending numeric outlet-number order. The baseline visual acceptance fixture SHALL contain eight outlet rows. If the current exact PDU exposes more rows than fit within the approved body height, a controlled vertical scrolling region SHALL keep all rows reachable without changing their authoritative order or shrinking them below the approved density.

`Текущая мощность` is a permanent placeholder column in this change. Current approved PDU paths provide no authoritative per-outlet power evidence, so every current outlet row SHALL render `—` in this column. Rendering/refreshing the dashboard SHALL NOT start a power-specific worker, timer, handler method or device request. The GUI SHALL NOT fabricate `0 Вт`. A future reviewed change MAY populate authoritative numeric power and, when it does, the user-facing unit SHALL be `Вт`.

`Состояние` SHALL use explicit non-color text plus semantic reinforcement:

```text
confirmed ON     -> green semantic cue + `ON`
confirmed OFF    -> red semantic cue + `OFF`
unknown/unusable -> neutral cue + `—`
```

The semantic cue target SHALL be approximately `8-10 px` in diameter. Color SHALL NOT be the sole state meaning.

Every outlet `Действия` cell SHALL preserve the fixed visible control order:

```text
Вкл | Выкл | Перезапуск
```

`Вкл` SHALL use green semantic styling, `Выкл` red/destructive semantic styling, and `Перезапуск` neutral/secondary styling. Target control height SHALL be `24 px`; the two shorter power buttons SHOULD occupy approximately `54-76 px` each and `Перезапуск` approximately `92-124 px` where baseline width permits. Fixed visibility does not imply network support; support behavior is defined by `device-diagnostics-and-control` and `room-device-interaction-lifecycle`.

No bulk reboot control SHALL be rendered.

The modern expanded PDU dashboard SHALL NOT render a local `Отладка` control. This is a presentation-only visibility decision: it does not change PDU device capability, introduce a Debug network path, or alter exact-row Debug presentation required for another device family.

#### Scenario: Eight-outlet Aten data is rendered

- **GIVEN** current accepted Aten data contains outlets 1 through 8
- **WHEN** the outlet-management card renders at baseline
- **THEN** eight rows are shown in numeric ascending order
- **AND** each row has the five required columns
- **AND** every power cell is `—`
- **AND** every action cell preserves `Вкл`, `Выкл`, `Перезапуск` order

#### Scenario: Outlet state is unavailable

- **GIVEN** an outlet has no usable accepted ON/OFF state
- **WHEN** its row is rendered
- **THEN** `Состояние` uses a neutral cue plus `—`
- **AND** the GUI does not infer ON/OFF from color or an action button state

### Requirement: Fixed PDU controls remain real existing operations when supported and local-only when unsupported

The common PDU dashboard SHALL keep the visible refresh, bulk and per-outlet controls specified above, but presentation SHALL resolve network capability from the existing exact PDU application capability authority rather than from model-name substrings, button existence, handler attribute probing or another support list.

When a fixed PDU operation is supported for the exact current row and the common room lock matrix permits interaction, the visible control SHALL publish only its existing safe exact-row application intent. Supported actions SHALL remain governed by the current application-owned PDU refresh or state-changing lifecycle; the view SHALL NOT perform device I/O directly.

When a fixed visible PDU operation is unsupported for the exact current model, activating the affordance while otherwise unlocked SHALL be resolved locally before room interaction admission. The application SHALL show a non-secret informational popup equivalent to `Команда не поддерживается`, and the click SHALL perform zero LIVE invalidation, credential selection, handler/session acquisition, mutation generation, device I/O or accepted-cache change.

For current `Extron IPL T PCS4i`, the fixed per-outlet `Перезапуск` affordance therefore remains visible as part of the common dashboard but remains network-unsupported/local-only. For current `Aten PE8208AV`, individual reboot remains the already-supported network operation. This visual contract SHALL NOT add bulk reboot for either model.

Temporary enabled/disabled state during active/retiring room lifecycles SHALL obey the common lock matrix; the local unsupported exception does not bypass an active lifecycle lock.

#### Scenario: Aten reboot uses existing operation

- **GIVEN** a current connected Aten outlet row is eligible for interaction
- **WHEN** the operator activates `Перезапуск` and completes the existing confirmation flow
- **THEN** the existing exact-row PDU mutation/reconciliation path owns the network operation
- **AND** the GUI does not call the Aten handler directly

#### Scenario: PCS4i reboot affordance is local-only unsupported

- **GIVEN** a current connected PCS4i row is otherwise interaction-eligible
- **WHEN** the operator activates the visible per-outlet `Перезапуск` affordance
- **THEN** a local informational popup equivalent to `Команда не поддерживается` is shown
- **AND** no room network interaction, handler/session acquisition or PDU device I/O starts

### Requirement: PDU visual acceptance is measurable from repository-local checkpoints

Manual visual acceptance at `1440 x 900` in dark theme SHALL use these ten repository-local checkpoints; access to the external screenshot is unnecessary:

1. the expanded PDU body contains exactly two cards in `Основная информация | Управление розетками` order and approximately the approved `30:70` weight hierarchy;
2. `Основная информация` contains exactly `Модель`, `Серийный номер`, `MAC-адрес` in order with no extra PDU information rows;
3. the outlet card action strip contains exactly `Обновить статус`, `Включить всё`, `Выключить всё` in order;
4. the outlet table exposes exactly `Розетка`, `Имя розетки`, `Состояние`, `Текущая мощность`, `Действия` in order and within the approved column hierarchy;
5. an eight-outlet fixture has stable row density/order and additional rows remain reachable through controlled scrolling;
6. ON/OFF/unavailable states use the required explicit text plus green/red/neutral semantic cues and never rely on color alone;
7. every current power cell renders `—` and the placeholder column remains visibly aligned;
8. every action cell groups `Вкл`, `Выкл`, `Перезапуск` in order with green/red/neutral semantic treatment and no bulk reboot exists;
9. the current expanded PDU header has no right-side action after IP, no kebab/overflow or second right-side collapse action, and the expanded presentation contains no legacy/generic `Локальный опрос` refresh affordance;
10. `Управление розетками` has its font-independent lightning icon, `Основная информация` values are compact/right-aligned/chrome-free, no local PDU `Отладка` is visible, and light theme preserves the same card/table/control geometry, ordering and readable semantic states without device I/O.

Checkpoints 1, 2, 3, 4, 6, 8 and 9 are mandatory structural/semantic checkpoints and cannot be waived by approximate similarity. The implementation SHALL satisfy all mandatory checkpoints and at least `9/10` total checkpoints to meet the product target of approximately 90% visual correspondence. Font rasterization, standard-icon glyph variation and one-pixel antialiasing differences are not acceptance failures when these repository-local ranges/checkpoints are satisfied.

#### Scenario: Independent validator has no source screenshot

- **WHEN** an independent validator reviews the PDU dashboard using only repository artifacts
- **THEN** the ten checkpoints and detailed geometry/semantic requirements are sufficient to decide visual acceptance
- **AND** all mandatory checkpoints plus at least nine total checkpoints are required for the approximately 90% target

### Requirement: Modern codec state and call cards use reduced permanent row geometry

The `Состояние` card SHALL permanently render these rows in this exact order:

```text
Модель
MAC-адрес
Серийный номер
Версия ПО
Время работы системы
Микрофон
Камера
```

The modern room codec dashboard SHALL NOT render a `Платформа` row. Removal of that presentation slot SHALL NOT require deletion, suppression, or non-collection of existing internal `platform` evidence used by other approved diagnostics or consumers.

The `Вызов и презентация` card SHALL permanently render these rows in this exact order:

```text
Статус звонка
Презентация
Регистрация SIP/H.323
```

At baseline each ordinary row SHALL use the common `28-34 px` row height. `Версия ПО` remains in its fixed row position but is the sole firmware exception: its safe firmware value MAY contain multiple lines and its row target is `48-56 px`. That value SHALL use plain text with word wrap; it SHALL NOT be interpreted as HTML. This exception does not permit other rows to increase their height. Label and value SHALL form a stable two-part row; the label remains visually secondary to the current value and may use an approximately `42-52%` label / `48-58%` value allocation where a grid is used. Long safe values MAY elide with tooltip/accessibility text rather than increase one row enough to destroy five-card alignment. Absent firmware evidence remains `Нет данных` in the same fixed slot.

`Время работы системы` is a read-only presentation-evidence row. It SHALL consume only accepted current canonical `uptime`; presentation SHALL NOT start a new network request or polling, infer uptime from logs, widget state, model text, or localized strings, or manufacture a value. Absent, stale-unusable, failed, malformed or otherwise unavailable canonical uptime SHALL render `Нет данных` in the fixed row.

For either card, absent, stale-unusable, failed, malformed or otherwise unavailable current evidence SHALL render `Нет данных` in the corresponding slot. The shared dashboard SHALL NOT hide a required row/card, invent `Unknown`, invent numeric zero, copy another model's value, or infer semantic values from model-name/localized-string substrings.

The approved five-card visual layout uses no leading status dots in `Состояние` or `Вызов и презентация`; all values in their right column SHALL align to the right edge. `Микрофон` and `Камера` use their safe textual value. `Статус звонка` and `Презентация` render `Да` or `Нет` only from typed/structured or exact-adapter-normalized boolean evidence; unavailable evidence remains `Нет данных`.

`Регистрация SIP/H.323` SHALL use a non-text icon in the right value column: `✓` for confirmed registration and `✕` for confirmed failure. The shared GUI SHALL receive this semantic state from the same typed/structured or exact-adapter-normalized evidence and SHALL NOT parse localized display strings, model names or substrings. If registration evidence is unavailable, it SHALL render a neutral `—` icon; icon color is supplementary and never the sole meaning.

#### Scenario: State card renders the reduced permanent row set

- **WHEN** a current supported codec `Состояние` card is rendered
- **THEN** it contains exactly `Модель`, `MAC-адрес`, `Серийный номер`, `Версия ПО`, `Время работы системы`, `Микрофон`, and `Камера` in the required order
- **AND** no `Платформа` row is visible
- **AND** accepted current canonical `uptime` is rendered only in the `Время работы системы` slot
- **AND** absent canonical `uptime` renders `Нет данных` in that fixed slot
- **AND** rendering either uptime state starts zero device I/O
- **AND** internal platform evidence MAY remain available outside this presentation

#### Scenario: Call-card status has no current evidence

- **GIVEN** current call, presentation or registration evidence has no usable normalized semantic state
- **WHEN** the codec state/call cards are rendered
- **THEN** each row remains in its fixed position
- **AND** call/presentation render `Нет данных` while registration renders a neutral `—` icon
- **AND** the GUI does not infer a state from a localized fallback string

### Requirement: Codec audio card distinguishes supported live-meter evidence from unsupported capability

The `Аудио` card SHALL permanently contain, in this exact order:

```text
Микрофон (уровень)     <horizontal live level indicator or explicit unsupported/no-data state>
Громкость микрофона    [−] <accepted configured value or Нет данных> [+] [mute]
Громкость динамиков    [−] <accepted percentage or Нет данных> [+] [mute]
```

The level row is **live activity evidence**, not a configured volume/gain setting. The control rows are **static/configured/readback evidence**, not live activity. Presentation SHALL NOT overwrite one authority with the other.

At baseline, the microphone level label SHALL precede a horizontal indicator occupying the available card-body width. A visible supported meter bar SHALL use approximately `8-12 px` height. The configured control rows SHALL follow the microphone meter block with approximately `8-12 px` vertical separation. Existing button-size rules remain:

```text
minus / plus button target size       28-34 px square
mute affordance target height          28-34 px
mute affordance target width           44-64 px
numeric/no-data value region           at least 38 px, centered/aligned
inter-control gap                       4-8 px
```

The modern codec Audio card SHALL NOT render a speaker-volume horizontal meter, progress bar, scale, gauge, or second visual level indicator. Speaker volume is represented only by its control row and the accepted percentage/no-data value between `−` and `+`.

The speaker value region SHALL render `<N>%` only from current accepted `speaker_volume_percent` evidence defined by `device-diagnostics-and-control`; accepted numeric zero SHALL render `0%`. Missing, malformed, stale-unusable, or otherwise unavailable accepted percentage SHALL render `Нет данных`. Presentation SHALL NOT derive percentage by guessing a device range, parse a localized/raw display string, use widget history/defaults, or reverse-convert displayed percentage into a device mutation target.

The shared presentation SHALL consume separate native speaker volume and typed mute-state authority from `device-diagnostics-and-control`; it SHALL NOT put strings such as `Muted` into a numeric/percentage slot or treat displayed percentage as mutation authority.

The modern room live-meter support matrix is:

| Exact model | `Микрофон (уровень)` |
| --- | --- |
| `Huawei TE20` | SUPPORTED from raw `MicValueIndex` evidence normalized `0..220 -> 0..100%` |
| `Huawei TE40` | SUPPORTED from `WEB_GetCurrentAudioParam`: `max(valid MicValueIndex + valid mic<N>ValueIndex + valid micArray<N>_<NN>ValIdx + valid rcaLInValueIndex + valid rcaRInValueIndex)` evidence normalized `0..220 -> 0..100%` |
| `Huawei TE50` | SUPPORTED by exact-model reuse of the approved TE40 `WEB_GetCurrentAudioParam` contract; pending TE50 hardware acceptance |
| `CloudLink Bar 310` | SUPPORTED from approved Bar-specific microphone LIVE evidence |
| `CloudLink Box 310` | **UNSUPPORTED / DEFERRED in this change** |
| `Polycom RPG 310` | UNSUPPORTED |

For a supported meter, accepted numeric zero is observed silence/zero level and SHALL render as zero fill. If capability is supported but no compatible current sample is available, the slot SHALL render `Нет данных`; absence of a sample SHALL NOT be represented as observed zero. For an unsupported meter, the slot SHALL render `Не поддерживается` or an equivalent explicit non-color state.

Rendering any meter SHALL consume only accepted application-owned live evidence and SHALL NOT itself start a timer, poll, handler/session acquisition, credential operation, or device request.

For Huawei TE20/TE40/TE50, `get_live_audio_status` remains the live authority. TE20 uses raw `MicValueIndex` normalized from `0..220` to `0..100%` for `Микрофон (уровень)`. TE40 and exact-model TE50 use the TE40 `WEB_GetCurrentAudioParam` extractor defined by `device-diagnostics-and-control`: `max(valid MicValueIndex + valid mic<N>ValueIndex + valid micArray<N>_<NN>ValIdx + valid rcaLInValueIndex + valid rcaRInValueIndex)`, then the same normalization. Accepted initial `monitor_mic_value` uses that same current-audio extractor/normalization only until a true LIVE sample is accepted. `SpeakerValueIndex` may remain compatibility evidence but SHALL NOT create a user-visible speaker LIVE capability or meter. The Audio card SHALL NOT additionally render standalone textual `Live ...` rows.

For exact `Huawei TE40` and `Huawei TE50`, accepted static numeric `mic1Value` in wire range `0..24` SHALL be presented in the `Громкость микрофона` value region as dB using `gain_db = mic1Value - 12`. Examples: wire `24 -> +12 dB`, `21 -> +9 dB`, `18 -> +6 dB`, `12 -> 0 dB`, `0 -> -12 dB`. This configured gain is independent from live microphone evidence and microphone mute. Exact TE20 shares the device input-gain scale `-12..+12 dB` but numeric microphone adjustment remains unsupported by this application, so presentation SHALL NOT fabricate a TE20 numeric configured gain.

The Huawei TE20/TE40/TE50 RCA input-gain scale is likewise `-12..+12 dB`; this fact does not add a new RCA control in this change. For TE40 and TE50, `−` / `+` microphone controls are network-supported. Each eligible click requests exactly `-1 dB` or `+1 dB`, bounded to `-12..+12 dB`, and enters the common exact-row mutation/reconciliation lifecycle through the approved TE40 `MIC1` binding reused by exact TE50. Presentation itself never builds the vendor full-state payload.

Huawei TE20/TE40/TE50 speaker volume uses the separate native `0..21` mutation/readback scale. That native value remains application authority for safe speaker targets and reconciliation; the presentation value is the accepted `speaker_volume_percent` projection defined by `device-diagnostics-and-control`. The speaker scale SHALL NOT be treated as configured microphone/RCA gain authority and SHALL NOT be used to manufacture a TE50 microphone percentage.

For `CloudLink Box 310`, microphone LIVE is explicitly unsupported in this change. Presentation SHALL show `Не поддерживается` for `Микрофон (уровень)`, SHALL NOT display stale/historical Box meter data as current, and SHALL NOT start or imply a Box LIVE lifecycle. A future reviewed change is required to restore Box microphone LIVE.

For TE20/RPG310, no synthetic numeric microphone gain SHALL be fabricated. CloudLink microphone gain remains network-unsupported.

Microphone and speaker fixed control affordances remain subject to the common room lock matrix. A network operation marked unsupported by unified capability authority may be visible only as the approved disabled/local informational affordance and SHALL resolve before handler/session/network acquisition.

#### Scenario: CloudLink codec has current meter data

- **GIVEN** the exact current model is `CloudLink Bar 310`
- **AND** current accepted Bar live microphone evidence contains a valid numeric sample under the approved Bar parser
- **WHEN** the Audio card renders
- **THEN** `Микрофон (уровень)` renders the approved normalized fill, including zero fill for accepted numeric zero
- **AND** no presentation-owned meter request is started

#### Scenario: Supported CloudLink meter has no current sample

- **GIVEN** the exact current model is `CloudLink Bar 310`
- **AND** no compatible current accepted live microphone sample is available
- **WHEN** the Audio card renders
- **THEN** `Микрофон (уровень)` displays an unavailable state equivalent to `Нет данных`
- **AND** unavailable telemetry is not represented as numeric zero

#### Scenario: Baseline codec has no approved modern room meter capability

- **GIVEN** the exact current model is `CloudLink Box 310` or `Polycom RPG 310`
- **WHEN** the Audio card renders
- **THEN** `Микрофон (уровень)` displays `Не поддерживается` or equivalent explicit unsupported state
- **AND** rendering performs zero meter handler/session/credential/network activity
- **AND** Box 310 does not consume historical/stale meter evidence as if LIVE were supported

#### Scenario: Speaker volume has accepted percentage evidence

- **GIVEN** current exact-row accepted state contains `speaker_volume_percent = 42`
- **WHEN** the speaker control row renders
- **THEN** `42%` appears between `−` and `+`
- **AND** no speaker-volume scale/bar is rendered
- **AND** the displayed percentage is not used as independent mutation authority

#### Scenario: Speaker volume has no accepted percentage evidence

- **WHEN** current exact-row accepted state has no usable `speaker_volume_percent`
- **THEN** the speaker value region displays `Нет данных`
- **AND** the GUI does not manufacture `0%`, a prior value, or a guessed mapping

#### Scenario: Huawei speaker volume keeps native authority separate from displayed percentage

- **GIVEN** the exact current model is `Huawei TE20`, `Huawei TE40`, or `Huawei TE50`
- **AND** current accepted native speaker volume evidence is `18`
- **WHEN** the application projection and speaker control row render
- **THEN** native `18` remains speaker mutation/reconciliation authority under the `0..21` speaker contract
- **AND** presentation renders only the accepted `speaker_volume_percent` projection rather than treating raw `18` as a percentage
- **AND** the native speaker value is not reinterpreted as microphone/RCA gain or converted into a configured microphone percentage

#### Scenario: Audio operation is unsupported for the exact model

- **GIVEN** the exact registration marks the clicked microphone/speaker network operation unsupported
- **AND** no existing interaction lock currently disables the common affordance
- **WHEN** the operator activates it
- **THEN** a local informational result equivalent to `Операция не поддерживается данной моделью` is shown, or the control remains disabled
- **AND** the network capability remains unsupported
- **AND** no room network interaction is started
- **AND** current LIVE, cache and row authority remain unchanged

#### Scenario: Huawei TE live audio uses model-specific microphone evidence only

- **GIVEN** the exact current model is `Huawei TE20`, `Huawei TE40`, or `Huawei TE50`
- **AND** current accepted `get_live_audio_status` evidence contains valid raw microphone evidence
- **WHEN** the Audio card renders
- **THEN** TE20 reflects normalized `MicValueIndex` evidence and TE40/TE50 reflect the normalized approved TE40 aggregate under their own exact model identities
- **AND** no user-visible speaker live meter or duplicate textual `Live ...` row is rendered

### Requirement: Codec call-history direction cue maps typed direction to the correct visible semantic role

Every modern room codec call-history record that renders a direction cue SHALL bind the cue to normalized `CallDirection` without vendor/model-specific reversal:

```text
INCOMING -> visible text `Входящий`; existing incoming semantic cue
OUTGOING -> visible text `Исходящий`; existing outgoing semantic cue
UNKNOWN  -> neutral cue MAY remain, but no visible direction text or title
```

The concrete icon glyph or Qt asset MAY vary with the shared theme, but the semantic role SHALL be testable independently of color and SHALL NOT be swapped between `INCOMING` and `OUTGOING`. `UNKNOWN` SHALL remain the typed normalized direction; presentation SHALL NOT infer direction from localized source strings, peer formatting, call result, record position, icon color, model identity, or other GUI heuristics.

#### Scenario: Incoming record uses incoming visible role

- **GIVEN** the normalized record direction is `INCOMING`
- **WHEN** a room-preview or detailed call row renders its direction cue
- **THEN** the visible/non-color semantic role is `Входящий`
- **AND** the outgoing semantic role is not used

#### Scenario: Outgoing record uses outgoing visible role

- **GIVEN** the normalized record direction is `OUTGOING`
- **WHEN** a room-preview or detailed call row renders its direction cue
- **THEN** the visible/non-color semantic role is `Исходящий`
- **AND** the incoming semantic role is not used

#### Scenario: Unknown direction is neutral

- **GIVEN** the normalized record direction is `UNKNOWN`
- **WHEN** a room-preview call row renders
- **THEN** it renders no visible direction title, including `Направление неизвестно`, `Входящий`, or `Исходящий`
- **AND** it leaves no empty direction-text row or vertical gap
- **AND** a neutral direction icon MAY remain only when it does not imply incoming or outgoing direction
- **AND** the normalized direction remains `UNKNOWN`

### Requirement: Same room diagnostic context preserves safe user presentation state across background rebuild

The room diagnostic presentation SHALL distinguish authoritative room/session/device state from context-scoped user presentation state.

The exact current `RoomDiagnosticSessionIdentity` produced by application authority SHALL be the context key for room-level presentation restoration. A background update/re-render whose incoming identity is exactly equal to the active identity SHALL preserve safe presentation state; a different identity or explicit presentation clear SHALL discard the old state rather than migrate it into the new context.

Safe state in this change includes the equipment-tree viewport/scroll position and network-tree disclosure state. Existing Audio selected-channel visual state MAY continue under its separately approved exact-room/record/channel contract. The presentation state SHALL NOT contain or become authority for credentials, handlers/sessions, workers/controllers, request generations, accepted device evidence, exact-row network target, retry state, mutation state, or secrets.

For the equipment tree, same-context rebuild SHALL restore the operator's prior viewport as closely as the current rows permit. Implementation SHOULD preserve a visual top-level `record_id` anchor plus pixel offset with a clamped scrollbar value fallback so row-height/data changes do not force the viewport to the beginning. The visual `record_id` anchor SHALL NOT select/expand the row, create an interaction context, change automatic acquisition order, or admit device I/O.

State capture/restore, clamping, layout restoration, scrolling, and disclosure restoration SHALL be presentation-only and SHALL emit no room/device interaction intent or network work.

#### Scenario: Background update preserves equipment viewport

- **GIVEN** the operator has scrolled the equipment tree away from its initial viewport
- **AND** the authoritative room/session identity remains unchanged
- **WHEN** accepted diagnostic data causes the room presentation to rebuild
- **THEN** the equipment viewport remains at the same visual position as closely as the current rows permit
- **AND** the rebuild does not scroll to the beginning merely because data refreshed
- **AND** restoration performs no device I/O or interaction admission

#### Scenario: New room/session does not inherit old viewport

- **GIVEN** one room/session has stored local viewport/disclosure state
- **WHEN** the presentation receives a different `RoomDiagnosticSessionIdentity` or is explicitly cleared
- **THEN** the old viewport/disclosure state is discarded
- **AND** no stale callback may restore it into the new context

### Requirement: Audio DSP popup lifetime follows current hover and expanded-row context

The modern room Audio DSP local-controls popup SHALL be presentation-only and SHALL have at most one active target in the room presentation. Its safe target identity SHALL be the current room/session identity plus exact Audio `record_id` plus stable channel identity (`section` + `oid`). That target identity SHALL NOT substitute for application-owned exact-row/current interaction authority.

Popup visibility SHALL require the target room/session identity to remain current, the target `record_id` to equal the current authoritative `expanded_record_id`, the row to remain an Audio DSP presentation, and the target channel to remain present in current accepted presentation evidence.

The popup SHALL remain visible while the pointer is over either the active source level scale or the corresponding popup. A short single-shot presentation-only hide delay MAY bridge pointer travel between those surfaces. Entering another current Audio scale SHALL immediately switch the popup to the new exact channel target and invalidate any pending hide callback for the old target. Once the pointer is over neither the active source scale nor popup, the popup SHALL close even if that channel remains locally selected.

Collapse of the active Audio row, expansion/current-selection of another equipment row, room/session identity replacement, explicit presentation clear, or disappearance of the exact channel SHALL synchronously invalidate and hide the old popup context. Delayed popup callbacks SHALL be fenced by current presentation epoch/target identity so stale work cannot reopen an invalid popup or hide a newer target.

A same-context destructive re-render MAY preserve popup continuity only by carrying safe target identity/hover facts, resolving the replacement current scale after rebuild, and revalidating current pointer ownership. Disposable source-widget references SHALL NOT survive rebuild as evidence of currentness.

The popup and its timers SHALL own no credentials, handler/session, worker/controller, device request, retry, application request generation, mutation, or reconciliation state.

#### Scenario: Pointer moves from scale into its popup

- **GIVEN** a current expanded Audio DSP row and one current channel scale
- **WHEN** the pointer enters the scale and then moves into that channel's popup
- **THEN** the popup remains visible through the transition
- **AND** opening/keeping it visible performs zero device I/O

#### Scenario: Pointer moves directly to another channel scale

- **GIVEN** channel A currently owns the popup
- **WHEN** the pointer enters current channel B before A's deferred hide completes
- **THEN** the popup is rebound to B immediately
- **AND** a stale callback for A cannot hide B's popup

#### Scenario: Selected channel no longer pins popup

- **GIVEN** a channel remains locally selected for visual emphasis
- **WHEN** the pointer leaves both that channel's scale and its popup
- **THEN** the popup is allowed to close after the presentation-only bridge delay
- **AND** the selected visual cue MAY remain under the separate selection contract

#### Scenario: Collapse revokes popup context

- **GIVEN** a popup is visible for the current expanded Audio row
- **WHEN** that row is collapsed or another equipment row becomes current expanded presentation
- **THEN** the old popup is hidden and its target is invalidated
- **AND** a delayed/stale callback cannot make it visible again

#### Scenario: Same-context rebuild revalidates popup without stale widget authority

- **GIVEN** a current Audio popup target and unchanged room/session identity
- **WHEN** background data causes the expanded Audio presentation to be rebuilt
- **THEN** popup continuity is permitted only if the exact replacement channel remains current/expanded and current pointer hit-testing still owns the replacement scale or popup
- **AND** an old disposable QWidget is never sufficient evidence to preserve visibility

### Requirement: Room codec presentation consumes exact-model normalized static microphone evidence

The common dashboard SHALL consume canonical static audio evidence from the exact-model parser/normalizer path. Presentation SHALL NOT parse vendor strings or infer capability from the mere presence of a widget.

| Exact model | Static microphone source | Canonical evidence | Presentation |
| --- | --- | --- | --- |
| `Huawei TE20` | authoritative mute evidence | `microphone_muted` | mute state; no fabricated numeric gain; device input-gain scale does not create a supported numeric control |
| `Huawei TE40` | numeric `mic1Value`; independent `MicSwitch`/mute evidence | numeric `microphone_volume`; independent `microphone_muted` | transform to `-12..+12 dB`; independent mute state |
| `Huawei TE50` | approved TE40 `mic1Value`; independent `MicSwitch`/mute evidence | numeric `microphone_volume`; independent `microphone_muted` | same `-12..+12 dB` presentation as TE40; independent mute state |
| `CloudLink Bar 310` | diagnostic `mic_volume`; mute only if authoritative | numeric `microphone_volume`; optional independent mute | show accepted numeric value where present |
| `CloudLink Box 310` | existing non-LIVE diagnostic evidence only where already authoritative | canonical static fields only | may show accepted static evidence; SHALL NOT imply LIVE support |
| `Polycom RPG 310` | authoritative mute evidence | `microphone_muted` | mute state; no fabricated numeric gain |

For Huawei TE20/TE40/TE50, microphone/RCA input gain uses the confirmed device scale `-12..+12 dB` with nominal `0 dB`, while speaker volume separately uses `0..21`. These domains SHALL NOT share configured-value percentage conversion logic.

#### Scenario: TE40 has numeric MIC1 gain and independent mute evidence

- **GIVEN** accepted exact-model normalization produced numeric `microphone_volume = 21` and independent `microphone_muted = false` for TE40
- **WHEN** the dashboard renders
- **THEN** the configured value is shown as `+9 dB` rather than `Нет данных`
- **AND** mute state remains independent
- **AND** numeric zero alone does not mean muted

#### Scenario: TE50 uses the same dB configured microphone presentation

- **GIVEN** accepted exact-model normalization produced numeric `microphone_volume = 24` for TE50
- **WHEN** the dashboard renders
- **THEN** the configured value is shown as `+12 dB`
- **AND** no TE50-specific percentage exception is applied

### Requirement: Automatic codec call preview presents up to three generation-current records without explicit opening

For a call-log-capable exact codec row, application/lifecycle authority SHALL acquire the initial preview only at the boundary defined by `room-device-interaction-lifecycle`: the entire automatic room cycle is terminal, the exact row is current/expanded/connected/usable, and that exact row/generation has no terminal initial-preview attempt yet.

The presentation SHALL render at most the three newest normalized records from accepted initial-preview state. It SHALL NOT initiate the network request itself. If fewer than three calls exist, every available call is shown. If the initial attempt ends with no data/ordinary failure, a neutral `Нет данных` state may be shown.

Box 310 remains call-log-capable in this change. Its automatic preview SHALL still run under the common lifecycle; absence of Box LIVE only means no post-preview LIVE start for that exact model.

#### Scenario: Three newest calls are visible without Развернуть

- **GIVEN** the current exact row/generation has an accepted initial-preview dataset with at least three records in normalized newest-first order
- **WHEN** the call-history card renders
- **THEN** exactly the three newest records are visible inline
- **AND** the operator did not need to activate `Развернуть`

#### Scenario: Explicit detail remains fresh

- **GIVEN** an accepted three-row preview is visible
- **WHEN** the operator activates `Развернуть`
- **THEN** the detailed view starts the separate fresh explicit acquisition defined by the lifecycle/call-log specs
- **AND** preview data is not promoted to authoritative detailed/statistics state

### Requirement: Supported codec microphone LIVE meters use nominal 700 ms cadence with model-owned scheduling

For the currently supported room microphone LIVE meters only — exact `Huawei TE20`, `Huawei TE40`, `Huawei TE50`, and `CloudLink Bar 310` — application/composition SHALL use a nominal `700 ms` update cadence. This is a product-level cadence, not a shared internal scheduler algorithm or a paint-rate guarantee: rendering remains a consumer of accepted evidence and SHALL create zero new meter I/O.

For exact Huawei TE20/TE40/TE50, the existing periodic room-LIVE timer remains authoritative. Its interval SHALL be `700 ms`; it SHALL remain periodic and SHALL preserve one current sample operation at most. If it expires while a prior sample is in flight, it SHALL submit no duplicate request. If a sample completes before the next periodic tick, the next eligible request occurs at that tick, not `700 ms` after completion. Huawei SHALL NOT be converted to completion-triggered or single-shot scheduling.

For exact CloudLink Bar 310, the existing serialized single-shot owner remains authoritative. After one permitted sample cycle completes, its next single-shot sample delay SHALL be `700 ms`. Its `_in_flight` protection SHALL permit at most one request in flight, and Bar SHALL NOT be converted to Huawei-style periodic scheduling.

Each owner SHALL preserve immutable current row/generation/credential authority. Late, stale, cancelled, superseded, or retired work SHALL remain powerless under the existing lifecycle. This cadence change SHALL not alter vendor protocol command/request semantics, parser/aggregation/normalization, Bar authentication/session or terminal failure behavior, or Huawei parser/aggregation/normalization behavior.

This requirement changes neither vendor protocol command/request semantics nor the support matrix. Exact `CloudLink Box 310` remains `UNSUPPORTED / DEFERRED` with no meter timer/context/request; `Polycom RPG 310` remains unsupported. It SHALL NOT change Matrix, DMP, PDU, general refresh, call-log, authentication, or unrelated timer scheduling.

#### Scenario: Huawei periodic LIVE timer uses the 700 ms interval

- **GIVEN** a current exact `Huawei TE20`, `Huawei TE40`, or `Huawei TE50` room LIVE owner
- **WHEN** its room LIVE timer is configured
- **THEN** its interval is `700 ms`
- **AND** the timer remains periodic

#### Scenario: Huawei periodic LIVE skips an in-flight tick

- **GIVEN** a current exact Huawei room LIVE timer fires
- **AND** the prior Huawei microphone sample is still in flight
- **WHEN** the tick is processed
- **THEN** no second request is submitted

#### Scenario: Huawei fast completion waits for the next periodic tick

- **GIVEN** a current Huawei microphone sample finishes before the next periodic timer tick
- **WHEN** the owner remains current and eligible
- **THEN** the next eligible request occurs at the next `700 ms` timer tick
- **AND** it is not scheduled `700 ms` after completion

#### Scenario: Bar retains completion-triggered single-shot scheduling

- **GIVEN** one permitted current `CloudLink Bar 310` microphone sample cycle completes
- **WHEN** the Bar owner schedules its next sample
- **THEN** one single-shot sample is scheduled after `700 ms`
- **AND** Bar is not converted to a periodic Huawei-style timer

#### Scenario: Bar never overlaps microphone samples

- **GIVEN** a current Bar microphone sample is in flight
- **WHEN** its single-shot owner is considered for another submission
- **THEN** at most one Bar sample remains in flight
- **AND** no overlapping request is submitted

#### Scenario: Unsupported and unrelated timers remain outside codec LIVE cadence

- **WHEN** exact `CloudLink Box 310`, `Polycom RPG 310`, Matrix, DMP, PDU, general refresh, call-log, authentication, cleanup, application-time-update, or another unrelated timer is active
- **THEN** this requirement starts no new microphone LIVE context for unsupported codecs
- **AND** it changes no unrelated timer cadence or network behavior

### Requirement: Matrix dashboard uses compact information and routing surfaces

The room Matrix dashboard SHALL contain no separate `Быстрые действия` card,
large refresh button, reboot placeholder, replacement action card, production
`Отладка` affordance, or Matrix-specific footer/action strip. The routing-table
card SHALL occupy the released horizontal dashboard area while the information
card remains compact.

The Matrix information card SHALL NOT contain an `IP-адрес` row. It SHALL NOT
contain an embedded circular refresh control, `!`/warning button, unlabeled
action button, debug button, or trailing action/footer area below the approved
information fields. Existing room/global refresh lifecycle and currentness
authority remain outside this information card; removing these controls SHALL
NOT create a replacement Matrix-specific polling lane.

The routing-table card retains its border/background framework but SHALL hide
its SectionCard title/header completely, so its first visible content is the
horizontal table header.

#### Scenario: Information card has no IP/action footer
- **WHEN** the Matrix information card renders
- **THEN** it has no `IP-адрес` field
- **AND** it has no embedded refresh/debug/warning/action button
- **AND** its visible content ends with the approved diagnostic information rows

#### Scenario: Existing refresh lifecycle is not duplicated
- **GIVEN** room/global refresh is available through an already-approved affordance outside the Matrix information card
- **WHEN** the Matrix dashboard renders
- **THEN** that existing application lifecycle remains authoritative
- **AND** the Matrix information card adds no local refresh controller or network path

#### Scenario: Matrix action card is absent
- **WHEN** the room Matrix dashboard renders
- **THEN** `Быстрые действия`, production `Отладка`, `Обновить статус` as a large action,
  `Перезагрузить устройство`, and embedded `!`/warning actions are absent
- **AND** no replacement action/footer card or standalone-screen affordance is exposed

#### Scenario: Table begins without a card title gap
- **WHEN** the room Matrix routing card renders
- **THEN** its first visible content is the horizontal table header
- **AND** no title, icon, or former header spacing appears above that header

### Requirement: Matrix route-column headings are capability-driven

Route-column headings SHALL use authoritative output-name evidence only when the active profile proves and successfully returns it. An unproven output-name command SHALL cause deterministic fallback heading `Output <id>` rather than speculative SIS I/O or a fabricated configured name.

#### Scenario: XTP output naming is unproven
- **GIVEN** the active approved profile has no authoritative output-name read
- **WHEN** the Matrix table renders output `5`
- **THEN** the heading uses deterministic fallback `Output 5`
- **AND** presentation does not imply that an empty configured name was returned

### Requirement: Matrix route columns are equal-width and compact

The route-column count SHALL be determined only by authoritative
`available_output_ids`. Every visible route column SHALL receive the same
fixed layout width (within one pixel of rounding); no output number, first
output, or physical duplicate connector may receive individual stretch or a
legacy special width. The columns SHALL be materially narrower than the former
single-output 29% route allocation while leaving static input-information
columns readable.

#### Scenario: Multi-output columns share one width
- **GIVEN** authoritative available outputs `[1, 2, 5]`
- **WHEN** the Matrix table is laid out
- **THEN** its three route columns have equal widths within one pixel
- **AND** output `1` has no privileged 29%/stretch allocation

### Requirement: Matrix information card projects canonical row facts

The Matrix information card SHALL use the same five-field completeness and
authority contract as `Matrix General information preserves approved field order
without fabricating evidence`. The row's canonical `ip_address` remains
application/target authority but SHALL NOT be duplicated inside this card.

Canonical current room/inventory MAC and serial are mandatory prerequisites.
Their absence SHALL NOT activate a device fallback in this change. Firmware and
temperature SHALL come only from authoritative current exact-profile SIS reads. Model SHALL
come from the accepted exact Matrix identity/canonical model.

The card MAY show truthful no-data during incomplete/failed acquisition, but a
snapshot with any missing required General-information value SHALL NOT be treated
as a complete successful full refresh. Missing current evidence SHALL clear old
presentation values.

#### Scenario: Canonical inventory facts survive a device snapshot without them
- **GIVEN** an exact Matrix room row has current canonical MAC and serial values
- **AND** its accepted device snapshot does not repeat those two values
- **WHEN** the information card renders
- **THEN** it displays canonical MAC and serial values without an extra device read for those already-authoritative fields
- **AND** it does not duplicate the exact row IP inside the card
- **AND** firmware and temperature still require authoritative current device evidence

#### Scenario: Missing canonical MAC or serial keeps the refresh incomplete
- **GIVEN** the current exact Matrix row lacks canonical MAC or serial evidence
- **WHEN** a complete full refresh is attempted
- **THEN** the refresh remains incomplete
- **AND** no device fallback or fabricated presentation value is used
