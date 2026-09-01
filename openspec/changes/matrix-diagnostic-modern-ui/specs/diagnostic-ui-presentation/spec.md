## MODIFIED Requirements

### Requirement: Diagnostic shell follows a self-contained modern room-oriented foundation contract

The desktop application SHALL retain the user-visible title `Диагностический модуль` and a card-based room-oriented layout with semantic spacing, typography, borders, radii, standard Qt/device-class icons, and status styling. This repository-local contract, rather than an external screenshot or a particular stylesheet, SHALL be sufficient for implementation and review.

The baseline viewport remains `1440 x 900` logical pixels and the minimum supported window remains `1180 x 720`. Below the baseline, controlled reflow or vertical scrolling MAY occur, but target search, top Refresh, selected-room cue, room/network cards, equipment accordion, and expanded current-device content SHALL remain reachable. Presentation widgets SHALL NOT become authority for target identity, credentials, request generation, handler/session ownership, or device I/O.

At baseline, room mode SHALL place two peer-weight cards above the equipment accordion, with aligned tops and a width ratio from `0.9:1` through `1.1:1`. The upper card block SHALL have an accepted height centered on `186` logical pixels (an implementation-tuning range of `178-194` is permitted). The left card header SHALL read `Информация о комнате`; the right header SHALL include the current switch count, equivalent to `Сетевые подключения (N коммутаторов)`. The cards SHALL remain side by side at baseline.

The accepted shell uses a transparent/common diagnostic-tree background with card-like equipment surfaces. Its compact accordion header has no visible tree column header and no visible trailing overflow placeholder. A hidden, data-bearing or accessibility surface MAY retain cycle health, but the shell SHALL NOT insert a second visible global-cycle line between the upper cards and the accordion. Hover, repaint, resize, theme switch, reflow, and scrolling remain presentation-only and SHALL start no device I/O or change authority.

#### Scenario: Accepted room shell renders at baseline size

- **WHEN** room mode has an authoritative current room at the baseline viewport
- **THEN** the titled room and network cards appear side by side above the compact equipment accordion
- **AND** the upper block uses the accepted taller card geometry
- **AND** device/network authority remains outside presentation widgets

#### Scenario: Supported smaller window remains usable

- **WHEN** the application is shown at `1180 x 720` logical pixels
- **THEN** controlled reflow or scrolling keeps the required shell and current expanded content reachable
- **AND** no target, device, credential, or request authority changes merely because layout reflows

### Requirement: Room summary card derives busy indication only from typed codec call activity

The room-summary card SHALL permanently render labelled facts for `Название комнаты`, `Адрес комнаты`, `Гарантия`, and `Занятость`, plus a clear VIP badge when canonical `room_vip` is true. `room_name`, `room_address`, and `room_vip` remain governed by the canonical room metadata authority. The accepted visual text for the unavailable warranty source is `Гарантия: нет данных`; this capitalization is presentation only and does not create a warranty field or data source.

The operator-facing `Занятость` means busy by a current VKS codec call, not physical or calendar availability. It SHALL consume only current model-neutral `CallActivity` evidence from registry-relevant call-capable codec rows. A current accepted `CallActivity.ACTIVE` renders `Занято`; all other cases, including INACTIVE, UNKNOWN, missing, stale, failed, contradictory, unrecognized, or no relevant current codec, render `Нет данных`. The GUI SHALL NOT display `Свободно`, infer occupancy from inventory/calendar/local state, maintain a second support list, parse model/localized strings, or start occupancy-specific I/O.

Registry relevance remains defined exclusively by the exact unified model registration's declared call-activity binding. A relevant row with unusable evidence contributes UNKNOWN and remains relevant. The projection updates only when the application-owned lifecycle accepts current typed evidence; rendering and the explanatory hover tooltip perform no timer, poll, worker, handler/session acquisition, credential attempt, or network request.

#### Scenario: Typed active codec call marks the room busy

- **GIVEN** a registry-relevant current room codec has accepted `CallActivity.ACTIVE`
- **WHEN** the room summary renders
- **THEN** `Занятость` displays `Занято`
- **AND** no occupancy-specific request starts

#### Scenario: Inactive or incomplete evidence does not claim availability

- **GIVEN** no registry-relevant current room codec has accepted active call activity
- **WHEN** the room summary renders
- **THEN** `Занятость` displays `Нет данных`
- **AND** the GUI does not claim `Свободно`

### Requirement: Network card preserves all available canonical connection evidence

The titled network card SHALL use a compact summary table with columns equivalent to `Коммутатор (IP)`, `Порты`, and `Подключено устройств`. Rendering, hover, and any local table interaction are presentation-only and SHALL perform no device network I/O.

For each known exact canonical `switch_ip_address`, the table SHALL render one summary row labelled equivalently to `SW (<IP>)`. Its ports cell SHALL be the deterministic, first-occurrence de-duplicated summary of non-null canonical child `switch_port` values in canonical `record_id` order (`Нет данных` if none), and its device-count cell SHALL equal the number of canonical room-equipment records with that exact switch IP. Neither summary nor count becomes canonical switch, routing, or topology authority.

For `switch_ip_address == null` and `switch_port != null`, the table SHALL render a separate record-bound `Коммутатор не определён` row with that exact port and device count `1`; such rows SHALL NOT be merged by matching port text. A record with both values null contributes no topology evidence. Deterministic ordering, partial-evidence visibility, and no invented switch identity remain mandatory. The compact table SHALL NOT require visual device-child rows. With no presentable evidence it SHALL show `Нет данных о сетевых подключениях` or an accepted equivalent.

#### Scenario: Two devices share a known switch

- **GIVEN** two canonical room records share one non-null switch IP and ports `Gi1/0/5` and `Gi1/0/6`
- **WHEN** the network summary renders
- **THEN** one switch row displays the deterministic port summary and count `2`
- **AND** neither displayed summary becomes canonical switch state

#### Scenario: Known port without switch identity is retained safely

- **GIVEN** a room record has null switch IP and a non-null canonical port
- **WHEN** the network summary renders
- **THEN** a separate `Коммутатор не определён` row displays that exact port and count `1`
- **AND** no shared switch identity is guessed

### Requirement: Equipment rows share one non-color accordion header contract

Every room equipment record SHALL use one compact top-level row equivalent to `chevron -> device-class icon -> model label -> status cue + status text -> IP`. At baseline, a collapsed row SHALL be approximately `42` logical pixels high (a `38-46` range is permitted), the device-class icon SHALL be approximately `28 x 28` logical pixels, and the chevron/icon cluster SHALL remain compact. The tree header and a trailing overflow/action placeholder are intentionally not visible in the accepted shell.

Model text SHALL receive flexible width while status and IP remain readable under ordinary baseline content. Status SHALL retain explicit textual/non-color meaning for connected, waiting, connecting, unsupported, missing/ambiguous IP, failed, connection-lost, and other approved states; color may reinforce only. Exactly one expandable equipment row MAY be open. Expanding another expandable row SHALL collapse the prior row without reordering automatic acquisition or changing lifecycle authority. Any authorized device controls remain inside expanded content and through current application intent/controller boundaries; absence of a common row action SHALL NOT require a hidden or disabled placeholder.

#### Scenario: Another row is expanded

- **GIVEN** one expandable equipment row is open
- **WHEN** the operator expands another expandable row
- **THEN** the first row collapses and only the second owns expanded presentation selection
- **AND** automatic acquisition order remains unchanged

#### Scenario: Compact row remains understandable without color

- **WHEN** a compact equipment row renders any approved connection state
- **THEN** it displays explicit status text/non-color meaning in addition to optional color
- **AND** no visible common overflow placeholder is required

### Requirement: Existing expanded device presentations remain compatible and are not redesigned by this foundation

The `room-diagnostic-modern-ui` foundation established the **current room-mode exact-row presentation/interaction surface** as the common container for supported device families. A standalone or legacy single-device screen SHALL NOT be selected, embedded, or treated as room capability merely because it represents the same device family.

Dedicated reviewed family changes MAY replace only their family-specific expanded content inside that exact-row room surface while preserving exact-row authority, theme semantics, and application-owned lifecycle boundaries. MIH-10 already provides the approved Audio DSP family redesign. MIH-11 provides the Matrix/IN1804 family redesign described below. The user-approved common room visual refinement in this change supersedes the foundation's provisional upper-card and compact-accordion geometry only; it neither creates a new data model nor changes the lifecycle or capability meaning of codec and PDU presentations.

Existing **room-mode** controls SHALL remain connected through current non-secret application intent/controller boundaries and SHALL remain enabled only when current unified-registry/lifecycle capability state permits them. A family follow-up SHALL NOT promote an action, signal, credential owner, handler/session owner, retry lane, or network lifecycle from a standalone/single-device screen merely because similar functionality exists there.

For Matrix/IN1804 specifically, MIH-11 supersedes the foundation's temporary read-only room projection only through the unified exact-model registry and existing serialized `MUTATION -> RECONCILIATION` room lifecycle. Standalone `MatrixScreen.routeRequested` SHALL NOT be wired or embedded as room authority, and no widget SHALL call a Matrix handler/session directly.

Compatibility/family presentation adaptation SHALL NOT make expanded widgets authoritative for credential selection/fallback, handlers, sessions, transports, successful credential memory, stale-operation authority, request generations, exact-row identity, accepted device state, or direct device network I/O.

#### Scenario: Existing room-mode device view opens inside the common accordion

- **GIVEN** an exact supported room row has a current approved room-mode family presentation
- **WHEN** the operator expands that row under the common accordion
- **THEN** the approved room-mode family presentation is reachable and bound to that exact row state
- **AND** no standalone/single-device screen is promoted merely because it has the same family
- **AND** no widget gains direct credential/session/network authority

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
