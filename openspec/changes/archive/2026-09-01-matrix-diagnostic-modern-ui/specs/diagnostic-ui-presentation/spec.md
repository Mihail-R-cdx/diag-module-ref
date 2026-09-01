## MODIFIED Requirements

### Requirement: Diagnostic shell follows a self-contained modern room-oriented foundation contract

The desktop application SHALL present the user-visible title `Диагностический модуль` and SHALL use a card-based desktop layout with consistent semantic spacing, typography, borders, radii, standard Qt/device-class icons, and status styling. External screenshots are product-design inputs only; implementation and review SHALL be possible from this repository-local foundation contract without access to the original conversation images.

The baseline visual acceptance viewport SHALL be `1440 x 900` logical pixels. The layout SHALL remain usable at a minimum `1180 x 720` logical-pixel window; below the baseline, vertical scrolling or controlled card reflow MAY occur, but target-search, top Refresh, current selected-room cue, room/network cards, common equipment accordion, and expanded current device content SHALL remain reachable.

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

Room mode SHALL place the room-summary card and network-connections card above the equipment accordion. At baseline width the two cards SHALL have aligned tops and approximately peer weight with a width ratio between `0.9:1` and `1.1:1`; neither card SHALL collapse into a narrow sidebar while the other occupies the full row. The accepted upper-card block SHALL be about `186` logical pixels high (a tuning range of `178-194` is permitted); its visible headings SHALL be `Информация о комнате` and `Сетевые подключения (N коммутаторов)` or an equivalent current switch-count rendering.

The foundation contract itself does not define final family-specific visual geometry for Audio DSP, Matrix/IN1804, codec, or PDU expanded content; such geometry is owned only by dedicated reviewed follow-up OpenSpec changes. MIH-10 and MIH-11 are those approved follow-ups for Audio DSP and Matrix/IN1804 respectively; codec and PDU redesign remain deferred. The common shell redesign SHALL NOT make Qt widget state authoritative for target identity, credentials, request generation, handler/session ownership, or device I/O.

The accepted shell uses a transparent/common diagnostic-tree background with card-like equipment surfaces. Its compact accordion has no visible tree column header and no visible trailing common overflow/action placeholder. A hidden data-bearing or accessibility surface MAY retain cycle health, but the shell SHALL NOT insert a second visible global-cycle line between the upper cards and the accordion. Hover, repaint, resize, theme switch, reflow, and scrolling remain presentation-only and SHALL start no device I/O or change authority.

#### Scenario: Room shell is rendered at baseline size

- **WHEN** room mode has an authoritative current room at the baseline viewport
- **THEN** the titled room-summary and network cards appear side by side above the compact equipment accordion with peer visual weight
- **AND** the accepted common spacing/typography/icon scale and taller upper-card geometry are applied
- **AND** device/network authority remains outside the presentation widgets

#### Scenario: Minimum supported window remains usable

- **WHEN** the application is shown at `1180 x 720` logical pixels
- **THEN** target-search, selected-room cue when present, top Refresh, room/network cards, equipment accordion, and current expanded device content remain reachable through controlled reflow/scrolling
- **AND** no target or device authority changes merely because layout reflows

### Requirement: Room summary card derives busy indication only from typed codec call activity

The room-summary card SHALL permanently include labelled presentation slots for `Название комнаты`, `Адрес комнаты`, `Гарантия`, and `Занятость`, plus VIP. Current canonical `room_name`, `room_address`, and `room_vip` SHALL use the room metadata authority defined by `room-equipment-diagnostics`.

The confirmed product decision for this change is that real warranty data is not implemented yet. This scope decision is independent of the current schema limitation. Because canonical schema v4 contains no authoritative warranty field, the permanent row SHALL render `Гарантия: нет данных` and SHALL NOT infer warranty from unrelated inventory columns, timestamps, device data, room text, or local UI state. A future reviewed change may add an authoritative warranty source/schema mapping.

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

The titled network-connections card SHALL use a compact summary table with columns equivalent to `Коммутатор (IP)`, `Порты`, and `Подключено устройств`. Rendering, hover, and local table interaction SHALL be presentation-only and SHALL perform no device network I/O.

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

The summary row SHALL use a safe generic name equivalent to `SW (<IP>)` unless safe unique current canonical display evidence establishes a user-friendly name. The displayed ports summary and record count SHALL not be persisted as canonical data and SHALL not be used as switch identity, routing, or device-topology authority. The compact table intentionally has no visual device-child rows.

For a record-bound `Коммутатор не определён` row with a known canonical port, the `Порты` cell SHALL display that exact port and count `1` because the row is bound to one exact record.

If the room contains no presentable switch-IP or port evidence at all, the card SHALL show a safe empty state equivalent to `Нет данных о сетевых подключениях` rather than an invented topology.

The confirmed product decision for this change is that room switches with zero attached canonical equipment are not implemented now. This is an intentional scope decision, not an inference from schema v4. Current schema v4 also cannot authoritatively establish such a switch, so implementation SHALL NOT fabricate it and acceptance SHALL NOT require the `Нет подключенных устройств` runtime state. A future reviewed source/schema change is required before that state becomes data-driven.

#### Scenario: Two room devices share a switch

- **GIVEN** two room records contain the same non-null canonical `switch_ip_address`
- **AND** their canonical ports are `Gi1/0/5` and `Gi1/0/6`
- **WHEN** the network summary renders
- **THEN** one switch summary row is shown for that IP
- **AND** its Port summary displays `Gi1/0/5, Gi1/0/6` and its device count is `2`
- **AND** neither displayed summary becomes canonical switch state

#### Scenario: Parent port summary de-duplicates repeated child evidence

- **GIVEN** several canonical records under one exact switch IP contain the same non-null canonical port text
- **WHEN** the network summary renders
- **THEN** the repeated port appears once according to first canonical `record_id` occurrence
- **AND** the summary does not replace the per-record canonical evidence

#### Scenario: Known port with missing switch IP is not lost

- **GIVEN** one room record has null `switch_ip_address` and non-null canonical `switch_port`
- **WHEN** the network card renders
- **THEN** the known port remains visible under a `Коммутатор не определён` record-bound row with count `1`
- **AND** no switch IP or shared switch identity is guessed

#### Scenario: Empty switch state is explicitly out of current scope

- **GIVEN** the confirmed product scope defers room switches with zero attached canonical equipment
- **WHEN** no canonical room record/evidence establishes an unattached switch node
- **THEN** the GUI does not fabricate a switch solely to display `Нет подключенных устройств`
- **AND** acceptance does not require that state in this change

### Requirement: Equipment rows share one non-color accordion header contract

Every room equipment record SHALL use one compact top-level row layout equivalent to:

```text
expand chevron -> device-class icon -> model label -> status cue + status text -> IP
```

At baseline size a collapsed row SHALL remain within the `38-46 px` height range, targeting about `42 px`. The device-class icon SHALL be approximately `28 x 28 px` and the chevron/icon cluster SHALL remain compact. Model text SHALL receive the largest flexible width, and status and IP SHALL remain readable without forcing the row into multiple lines under ordinary baseline content. The tree header and trailing common overflow/action placeholder are intentionally not visible.

Status SHALL remain understandable without color alone. The row SHALL retain explicit text/non-color meaning for connected, waiting, connecting, unsupported, missing-IP, ambiguous-IP, failed, connection-lost, and other approved states. Color MAY reinforce but SHALL NOT be the only meaning.

Exactly one room equipment row MAY be expanded at a time. Expanding another expandable row SHALL collapse the previous row. Accordion changes SHALL remain presentation/current-selection behavior and SHALL NOT reorder the automatic room acquisition queue.

Any authorized device controls SHALL remain inside expanded content and through current application intent/controller boundaries. The absence of a common row action SHALL NOT create, imply, or require a hidden/disabled placeholder or an alternate direct network path.

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

## ADDED Requirements

### Requirement: Expanded Matrix redesign targets the current room exact-row presentation surface

MIH-11 SHALL render modern Matrix/IN1804 content inside the current room-mode exact-row presentation owned by `RoomDiagnosticTreeWidget`. A focused presentation-only Matrix dashboard component MAY consume accepted exact-row evidence and emit safe non-secret local intents, but SHALL NOT own room identity, target-search, request generation/currentness, credentials, handler/session lifecycle, polling/live ownership, mutation delivery, reconciliation authority, or device network I/O.

The standalone `MatrixScreen` SHALL remain a separate presentation/lifecycle surface. It SHALL NOT be selected, embedded, promoted, or navigated to from the MIH-11 room Matrix dashboard.

MIH-11 renders Matrix below the common accordion header. This change also owns the user-approved presentation-only refinement of the common upper cards and compact accordion header; Matrix family interior redesign remains bounded to the expanded exact-row content.

#### Scenario: Expanded Matrix room row uses the modern presentation

- **GIVEN** the current room session contains an expandable exact `Extron IN1804` row
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
Время работы
```

Each row SHALL use only accepted current exact-row evidence through deterministic presentation mapping. Presentation SHALL NOT infer a value from unrelated fields, model text, reference artwork, logs, prior snapshots, or widget state.

If accepted evidence does not establish a field, the row SHALL display `Нет данных` or the foundation safe no-data equivalent. On the current change base, absence of authoritative Matrix MAC, serial, firmware, or uptime evidence is expected and SHALL NOT cause new protocol reads under MIH-11.

For existing model/temperature reads, normalized absent/`None` is no-data. A local `Unknown` model sentinel is not display evidence. Numeric temperature `0` is displayable only when successful current device evidence actually established zero; a failed/missing/malformed read normalized to `None` SHALL display `Нет данных` rather than `0`.

#### Scenario: Current Matrix snapshot lacks reference-only information fields

- **GIVEN** accepted current Matrix evidence contains model and temperature but no MAC, serial, firmware, or uptime
- **WHEN** the General information card renders
- **THEN** model and temperature render from accepted evidence
- **AND** MAC, serial, firmware, and uptime render truthful no-data values
- **AND** presentation issues no additional Matrix request to fill them

#### Scenario: Failed model and temperature evidence remains no-data

- **GIVEN** current Matrix normalization has no accepted model evidence and no accepted temperature evidence
- **WHEN** the General information card renders
- **THEN** both `Модель` and `Температура` show `Нет данных`
- **AND** local `Unknown` or synthetic numeric zero is not rendered as device evidence

#### Scenario: Real zero temperature remains visible

- **GIVEN** accepted current Matrix evidence contains temperature numeric zero from a successful current device response
- **WHEN** the General information card renders
- **THEN** `Температура` renders that zero value
- **AND** it is not replaced with `Нет данных`

### Requirement: Matrix input table uses proven data-driven rows and the approved column order

The central Matrix table SHALL use this semantic order:

```text
[input ordinal] | Сигнал | HDCP | Входы | [accepted output-1 name or Main Output]
```

The leading ordinal column SHALL remain compact and MAY use an empty visual header with accessible `№` meaning. `Входы` displays accepted input name. The output column uses the first accepted output name when present/non-empty and otherwise `Main Output`.

At baseline, approximate table-width allocation SHALL preserve this hierarchy:

```text
input ordinal    8%
Сигнал          19%
HDCP            17%
Входы           27%
output           29%
```

Rows SHALL follow a **proven accepted current input count/order** from fail-closed Matrix normalization. MIH-11 SHALL NOT hard-code the eight rows visible in the design example and SHALL NOT accept a legacy constructor/parser default of eight as device evidence when input count/model capability is unproven.

If accepted input count is UNKNOWN, the Matrix presentation SHALL NOT fabricate eight rows and SHALL NOT expose route intents for unproven input ordinals. A no-data/unknown table state MAY be shown until current accepted evidence establishes the count.

#### Scenario: Four-input accepted Matrix is not rendered as eight inputs

- **GIVEN** accepted current Matrix evidence establishes four inputs
- **WHEN** the modern table renders
- **THEN** exactly four input rows are presented in accepted order
- **AND** no additional rows are fabricated from visual reference or legacy defaults

#### Scenario: Input count is unproven

- **GIVEN** current Matrix normalization cannot establish input count/model capability
- **WHEN** the modern table renders
- **THEN** eight rows are not fabricated
- **AND** no unproven input ordinal is actionable for routing

### Requirement: Matrix signal, HDCP presence, and route presentation remains meaningful without color

For each accepted input row, signal state SHALL distinguish confirmed presence, confirmed absence, and UNKNOWN. The accepted compact cell projects confirmed presence as a positive filled `●`, confirmed absence as a neutral/open `○`, and UNKNOWN as a neutral filled `●`. Color reinforces the positive/neutral distinction, while the accepted semantic value (`есть`, `нет сигнала`, or `Нет данных`) SHALL remain available through a tooltip, accessibility value, or data role. Visible words are not required inside Signal cells, and UNKNOWN remains fail-closed rather than false.

The `HDCP` column SHALL represent only the normalized **current input HDCP-presence flag**. Its raw existing input-HDCP-status mapping is owned by `device-diagnostics-and-control` and is deterministic (`2 -> True`, `1 -> False`, `0 -> False`, unusable evidence -> `None`). Presentation SHALL map only that normalized value:

```text
hdcp_present == True  -> non-color cue + `есть`
hdcp_present == False -> distinct non-color cue + `нет`
hdcp_present == None  -> neutral cue + `Нет данных`
```

The room `HDCP` column SHALL NOT display HDCP version (`2.2`, `1.4`, or any other version token), input HDCP authorization/configuration value, or output HDCP state. Failed, malformed, unrecognized, or missing input HDCP-status evidence SHALL remain UNKNOWN and SHALL NOT be presented as `нет`.

Output-1 route state SHALL derive only from fail-closed accepted `current_connection` evidence and use compact cells:

```text
current_connection == this input -> positive filled `●`; semantic `активен` retained
known different current input     -> neutral/open `○`; semantic `не выбран` retained
missing/unknown connection        -> neutral filled `●`; semantic `Нет данных` retained
```

The retained semantic route state SHALL be available through a tooltip, accessibility value, or data role; visible words are not required inside route cells. Local hover/click/confirmation/ACK state SHALL NOT change the visible authoritative route to `активен` before reconciliation accepts a confirming snapshot.

#### Scenario: Compact Signal and HDCP remain semantically explicit

- **GIVEN** accepted signal evidence is present, absent, and UNKNOWN and three accepted input rows respectively have normalized `hdcp_present` values True, False, and None
- **WHEN** the Matrix table renders
- **THEN** Signal cells show the accepted filled/open/neutral indicators with retained semantic values
- **AND** their HDCP cells show `есть`, `нет`, and `Нет данных` respectively
- **AND** no HDCP version token is displayed

#### Scenario: Route ACK does not optimistically recolor the table

- **GIVEN** a route mutation has received apparent send success but reconciliation is not yet accepted
- **WHEN** the Matrix table is rendered
- **THEN** accepted `current_connection` remains route-state authority
- **AND** the requested row is not shown as authoritative `активен` solely because of the ACK

### Requirement: Matrix output cells emit only approved exact-row route intent

A non-active output-1 cell SHALL be actionable only when the exact current expanded row is `Extron IN1804`, has usable connected accepted state, is not stale/degraded/blocked/unconfirmed, the unified model registration advertises approved Matrix mutation/reconciliation capability, the serialized room interaction lane currently permits mutation, and the input ordinal is within the proven accepted input authority.

Presentation SHALL emit only a non-secret immutable route intent equivalent to `output_num = 1` plus accepted `input_num = N`, together with existing exact-row presentation signal identity required by composition. It SHALL NOT contain credentials, handler/session references, raw target-search text, initial source record, standalone screen selection, or global Matrix target state.

The currently active output cell SHALL be non-actionable/no-op. A stale, degraded, failed, blocked, non-current, unsupported, unproven-input, or otherwise unauthorized row SHALL expose no route intent.

Presentation SHALL NOT call `ExtronIN1804Handler`, `MatrixController.request_route`, socket/transport methods, or other device I/O directly. Composition SHALL revalidate current exact-row authority and obtain **explicit operator confirmation** before passing the intent into `RoomInteractionCoordinator.confirm_mutation()`.

#### Scenario: Operator selects another current input

- **GIVEN** a connected current exact Matrix row has input 1 authoritative as active
- **AND** input 2 is proven, authorized, and non-active
- **WHEN** the operator activates input 2's output cell
- **THEN** presentation emits one safe output-1/input-2 route intent
- **AND** no Matrix device I/O occurs from the widget
- **AND** composition requires explicit confirmation before mutation lifecycle begins

#### Scenario: Current active route is clicked

- **GIVEN** input N is already authoritative as active
- **WHEN** the operator clicks its output cell
- **THEN** no route mutation intent is submitted
- **AND** no device I/O starts

### Requirement: Matrix Quick actions remain truthful to approved capabilities

The Matrix `Быстрые действия` card SHALL contain only `Обновить статус` and `Перезагрузить устройство` for MIH-11.

`Обновить статус` SHALL map only to existing exact-row Local Refresh intent and SHALL be enabled only under existing room interaction authorization. It SHALL NOT create a second Matrix refresh/polling path.

`Перезагрузить устройство` SHALL be visible but disabled/non-actionable because no approved Extron IN1804 reboot mutation capability exists. It SHALL emit no application intent, worker start, handler/session acquisition, protocol command, or device request.

`Открыть расширенный экран` SHALL NOT be rendered in MIH-11. There SHALL be no enabled control, disabled placeholder, navigation intent, or acceptance requirement for that affordance. Standalone `MatrixScreen` remains a separate existing surface only.

#### Scenario: Quick Refresh uses the existing room lifecycle

- **GIVEN** the exact connected Matrix row currently permits Local Refresh
- **WHEN** the operator selects `Обновить статус`
- **THEN** existing exact-row Local Refresh intent is requested
- **AND** no parallel Matrix refresh controller/lane is created

#### Scenario: Reboot remains a disabled placeholder

- **GIVEN** the Matrix Quick actions card is visible
- **WHEN** `Перезагрузить устройство` is rendered
- **THEN** it is clearly disabled/non-actionable
- **AND** interacting with it performs no Matrix device I/O

#### Scenario: Expanded-screen affordance is absent

- **WHEN** the MIH-11 Matrix room dashboard renders
- **THEN** `Открыть расширенный экран` is not present
- **AND** no navigation intent to standalone `MatrixScreen` is exposed
