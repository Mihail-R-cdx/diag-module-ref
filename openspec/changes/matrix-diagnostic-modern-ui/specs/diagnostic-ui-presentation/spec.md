## MODIFIED Requirements

### Requirement: Existing expanded device presentations remain compatible and are not redesigned by this foundation

The `room-diagnostic-modern-ui` foundation established the **current room-mode exact-row presentation/interaction surface** as the common container for supported device families. A standalone or legacy single-device screen SHALL NOT be selected, embedded, or treated as room capability merely because it represents the same device family.

Dedicated reviewed family changes MAY replace only their family-specific expanded content inside that exact-row room surface while preserving the foundation's common accordion/header, exact-row authority, theme shell, and application-owned lifecycle boundaries. MIH-10 already provides the approved Audio DSP family redesign. MIH-11 provides the Matrix/IN1804 family redesign described below. Codec and PDU family-specific redesign remain deferred.

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

The common foundation accordion header remains unchanged. MIH-11 redesigns only the expanded Matrix family interior below that header.

#### Scenario: Expanded Matrix room row uses the modern presentation

- **GIVEN** the current room session contains an expandable exact `Extron IN1804` row
- **WHEN** the operator expands that row
- **THEN** the modern Matrix presentation renders inside the exact-row room content
- **AND** room/record authority remains the current exact row
- **AND** standalone `MatrixScreen` is not required or promoted as room authority

### Requirement: Matrix dashboard follows the approved three-card field-placement hierarchy

At the foundation baseline viewport of `1440 x 900` logical pixels, expanded Matrix content SHALL render three horizontal cards in this order:

```text
Общая информация -> Матрица (входы и коммутация) -> Быстрые действия
```

The Matrix card SHALL be visually dominant. Baseline content-width allocation SHALL remain within these approximate ranges:

```text
Общая информация          24-28%
Матрица                    50-56%
Быстрые действия           18-22%
```

Exact pixel dimensions, border radii, and gaps MAY use foundation/theme tokens, but order, dominant central hierarchy, readable baseline content, and absence of baseline horizontal clipping are normative.

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

#### Scenario: Current Matrix snapshot lacks reference-only information fields

- **GIVEN** accepted current Matrix evidence contains model and temperature but no MAC, serial, firmware, or uptime
- **WHEN** the General information card renders
- **THEN** model and temperature render from accepted evidence
- **AND** MAC, serial, firmware, and uptime render truthful no-data values
- **AND** presentation issues no additional Matrix request to fill them

### Requirement: Matrix input table uses proven data-driven rows and the approved column order

The central Matrix table SHALL use this semantic order:

```text
[input ordinal] | Сигнал | HDCP | Входы | [accepted output-1 name or Main Output]
```

The leading ordinal column SHALL remain compact and MAY use an empty visual header with accessible `№` meaning. `Входы` displays accepted input name. The output column uses the first accepted output name when present/non-empty and otherwise `Main Output`.

At baseline, approximate table-width allocation SHALL preserve this hierarchy:

```text
input ordinal    7-9%
Сигнал          18-21%
HDCP            16-18%
Входы           25-29%
output           26-30%
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

For each accepted input row, signal state SHALL distinguish confirmed presence, confirmed absence, and unknown. A confirmed present signal SHALL use a positive non-color cue and text equivalent to `есть`; confirmed absence SHALL use text equivalent to `нет сигнала`; missing/unknown evidence SHALL use `Нет данных` or equivalent. Color MAY reinforce but SHALL NOT be the only meaning.

The `HDCP` column SHALL represent only the normalized **current input HDCP-presence flag**:

```text
hdcp_present == True  -> non-color cue + `есть`
hdcp_present == False -> distinct non-color cue + `нет`
hdcp_present == None  -> neutral cue + `Нет данных`
```

The room `HDCP` column SHALL NOT display HDCP version (`2.2`, `1.4`, or any other version token), input HDCP authorization/configuration value, or output HDCP state. Failed, malformed, unrecognized, or missing input HDCP-status evidence SHALL remain UNKNOWN and SHALL NOT be presented as `нет`.

Output-1 route state SHALL derive only from fail-closed accepted `current_connection` evidence:

```text
current_connection == this input -> non-color positive cue + `активен`
known different current input     -> neutral cue + `не выбран`
missing/unknown connection        -> neutral cue + `Нет данных`
```

Local hover/click/confirmation/ACK state SHALL NOT change the visible authoritative route to `активен` before reconciliation accepts a confirming snapshot.

#### Scenario: HDCP present/absent/unknown remains explicit

- **GIVEN** three accepted input rows respectively have normalized `hdcp_present` values True, False, and None
- **WHEN** the Matrix table renders
- **THEN** their HDCP cells show `есть`, `нет`, and `Нет данных` respectively
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
