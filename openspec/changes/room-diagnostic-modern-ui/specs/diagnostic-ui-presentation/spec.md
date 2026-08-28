## ADDED Requirements

### Requirement: Diagnostic shell follows the modern room-oriented visual hierarchy

The desktop application SHALL present the user-visible title `Диагностический модуль` and SHALL use a reference-guided card-based desktop layout with consistent semantic spacing, typography, borders, radii, icons, and status styling. Exact pixel reproduction is not required, but relative proportions and information hierarchy SHALL remain recognizably consistent with the approved visual direction.

The primary toolbar SHALL expose the single target-search field, top Refresh, application actions, and the session theme control. Room mode SHALL place the room-summary card and network-connections card above the equipment accordion at approximately equal horizontal weight under ordinary desktop window sizes.

The visual redesign SHALL NOT make Qt widget state authoritative for target identity, credentials, request generation, handler/session ownership, or device I/O.

#### Scenario: Room shell is rendered

- **WHEN** room mode has an authoritative current room
- **THEN** the room-summary and network cards appear above the equipment accordion
- **AND** device/network authority remains outside the presentation widgets

### Requirement: Room summary card has permanent room-information slots

The room-summary card SHALL permanently include presentation slots for room name, room address, VIP, warranty, and occupancy. Current canonical `room_name`, `room_address`, and `room_vip` SHALL use the room metadata authority defined by `room-equipment-diagnostics`.

Because canonical schema v4 does not contain authoritative warranty or occupancy fields, this change SHALL render `Гарантия: Нет данных` and `Занятость: Нет данных` and SHALL NOT infer those values from unrelated inventory columns, timestamps, device data, room text, or local UI state.

VIP true SHALL have a clear badge/indicator in addition to textual/accessibility meaning. VIP false/null SHALL not be rendered as VIP true.

A refresh icon inside the room card MAY be present to match the visual hierarchy, but if actionable it SHALL be only an alias of the existing top full Refresh intent.

#### Scenario: Warranty authority is absent

- **GIVEN** current schema-v4 room data is loaded
- **WHEN** the room summary renders
- **THEN** warranty and occupancy remain visible as permanent rows
- **AND** both use the safe no-data presentation rather than invented values

### Requirement: Network card is a presentation-only switch/device tree

The network-connections card SHALL use a hierarchical tree with columns equivalent to `Коммутатор (IP) / Устройства` and `Порт`. The current schema-v4 projection SHALL group room equipment using canonical `switch_ip_address` and `switch_port` fields.

Each authoritative switch node SHALL display its IP and a safe label. Attached room-equipment children SHALL be ordered deterministically by canonical `record_id`, SHALL display the existing safe device/model label, and SHALL display canonical `switch_port` or a safe no-data value.

Expanding/collapsing the network tree SHALL be local presentation only and SHALL perform no device network I/O.

A specific user-friendly switch name MAY be shown only from safe unique current canonical display evidence for that exact switch IP. Otherwise a generic `Коммутатор (<IP>)` style label SHALL be used.

The tree component SHALL support a `Нет подключенных устройств` empty child for an authoritative switch node with zero children. Current schema v4 does not prove room-level unattached switches, so implementation SHALL NOT fabricate an empty switch node when no canonical authority exists.

#### Scenario: Two room devices share a switch

- **GIVEN** two room records contain the same non-null canonical `switch_ip_address`
- **WHEN** the network tree is rendered
- **THEN** one switch parent is shown for that IP
- **AND** both attached devices appear as deterministic children with their canonical ports

#### Scenario: Missing empty-switch authority is not invented

- **GIVEN** no canonical room record/evidence establishes an unattached switch node
- **WHEN** the network card renders
- **THEN** the GUI does not fabricate a switch solely to display `Нет подключенных устройств`

### Requirement: Equipment rows share one non-color accordion header contract

Every room equipment record SHALL use one common top-level row layout equivalent to:

```text
expand chevron -> device-class icon -> model label -> status cue + status text -> IP -> overflow action
```

Status SHALL remain understandable without color alone. The row SHALL retain explicit text/non-color meaning for connected, waiting, connecting, unsupported, missing-IP, ambiguous-IP, failed, connection-lost, and other approved states.

Exactly one room equipment row MAY be expanded at a time. Expanding another expandable row SHALL collapse the previous row. Accordion changes SHALL remain presentation/current-selection behavior and SHALL NOT reorder the automatic room acquisition queue.

The overflow action SHALL expose only current application-authorized actions. When no action is authorized it SHALL be disabled or non-actionable and SHALL NOT provide an alternate direct network path.

#### Scenario: Another device row is expanded

- **GIVEN** one expandable equipment row is open
- **WHEN** the operator expands a second row
- **THEN** the first row collapses
- **AND** only the second row owns current expanded presentation selection
- **AND** automatic queue order is unchanged

### Requirement: Expanded device presentations preserve application intent boundaries

Expanded codec, PDU, Matrix, and audio DSP content SHALL be presentation projections of exact per-record state. Restyled widgets SHALL NOT own credential selection, credential fallback, handlers, sessions, transports, successful credential memory, stale-operation authority, request generations, or direct device network I/O.

Existing supported controls SHALL remain connected through their current non-secret application intent/controller boundaries and SHALL remain enabled only when current lifecycle/capability state permits them.

Controls included in the visual target for capabilities not currently implemented SHALL be visibly disabled. A disabled future control SHALL NOT emit a network/mutation intent, create a worker, acquire a handler/session, start a timer, or fake a successful state change.

#### Scenario: Future reboot control is shown before capability exists

- **WHEN** a reference-aligned device card includes a reboot control but no approved reboot capability exists for that model/path
- **THEN** the control is disabled
- **AND** activating/clicking it cannot perform device I/O or change authoritative state

### Requirement: Audio DSP presentation uses segmented vertical level meters

Audio DSP room presentation SHALL render input/source and output/destination level groups using vertical segmented meters with displayed dBFS values. Meter zones SHALL use semantic theme tokens equivalent to low/normal green, caution yellow, and high orange presentation without altering the underlying numeric dBFS value or meter lifecycle.

A selected channel SHALL be indicated through a border/background or another non-color-only cue. The visual layout SHALL reserve adjacent gain `+`, `-`, value, and `Mute` controls for the selected channel. These state-changing controls SHALL remain disabled unless a separately approved capability already authorizes the exact operation.

Existing DMP/live meter acquisition SHALL remain owned by the application lifecycle and SHALL NOT move polling/network I/O into the Qt GUI thread merely to animate the new meter.

#### Scenario: DMP meter value updates

- **WHEN** current application-owned live/polling state supplies a new accepted dBFS value
- **THEN** the segmented meter updates its visual segments and numeric dBFS text
- **AND** presentation does not create an additional network poll

### Requirement: Matrix presentation combines signal, HDCP, name, and routing per input

Matrix/IN1804 expanded presentation SHALL use a per-input table that combines at least input number, signal presence/state, HDCP state, input name, and current/active route indication in one row per input.

Existing Matrix route interaction SHALL remain available when current capability/lifecycle state permits it. A route action SHALL continue to cross the existing non-secret Matrix intent/application-controller boundary and SHALL NOT call the handler directly from the table widget.

Signal, HDCP, and route state SHALL have text/non-color meaning in addition to semantic icon/color cues.

#### Scenario: Operator selects a Matrix route

- **WHEN** a current Matrix row is connected and routing is authorized
- **AND** the operator selects a route in the new table presentation
- **THEN** the widget emits only the existing non-secret route intent
- **AND** handler/session/credential ownership remains outside the widget

### Requirement: Codec and PDU expanded cards use grouped diagnostic and action surfaces

Codec and PDU expanded presentation SHALL group related state into compact bordered cards/sections consistent with the approved visual hierarchy rather than one undifferentiated text form.

Codec presentation MAY include grouped general state, call/presentation state, audio/live state, call-log entry point, and actions. PDU presentation MAY include grouped general device state, outlet table/control state, and actions. Only existing production-supported actions SHALL be actionable in this change; reference-only future actions remain disabled under the future-control contract.

Existing PDU mutation/reconciliation, codec auxiliary/live behavior, and all exact-row interaction gates SHALL remain unchanged by visual restyling.

#### Scenario: Existing PDU outlet action remains real

- **GIVEN** a connected PDU room row whose current lifecycle permits an existing outlet action
- **WHEN** the operator invokes that action from the restyled PDU card
- **THEN** the existing PDU application intent/mutation lifecycle is used
- **AND** no direct handler call is introduced by the new view

### Requirement: Dark and light themes are semantic and session-only

The application SHALL support dark and light semantic themes. Every new process launch SHALL start in dark mode regardless of the theme used before the previous process exited.

A user-visible sun/moon theme control SHALL toggle the active palette for the current process only. The application SHALL NOT persist theme choice to a file, settings store, registry, environment variable, inventory, credential file, or other durable state.

Theme switching SHALL preserve layout hierarchy, readable disabled controls, focus indication, and status meaning. Theme switching SHALL be presentation-only and SHALL NOT invalidate target/room generations, change credentials, stop/restart live work, submit refresh, or perform device network I/O.

#### Scenario: Application restarts after light mode

- **GIVEN** the operator switched the running application to light mode
- **WHEN** the application is closed and started again
- **THEN** the new process starts in dark mode
- **AND** no persisted theme preference is consulted

#### Scenario: Theme changes during connected room state

- **GIVEN** a connected room session exists
- **WHEN** the operator toggles the theme
- **THEN** only visual palette/style state changes
- **AND** room authority, live/network ownership, and accepted diagnostic caches remain unchanged
