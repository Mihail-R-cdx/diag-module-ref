## MODIFIED Requirements

### Requirement: Existing expanded device presentations remain compatible and are not redesigned by this foundation

The `room-diagnostic-modern-ui` foundation established the **current room-mode exact-row presentation/interaction surface** as the common container for supported device families. A standalone or legacy single-device screen SHALL NOT be selected, embedded, or treated as room capability merely because it represents the same device family.

Dedicated reviewed family changes MAY replace only their family-specific expanded content inside that exact-row room surface while preserving the foundation's common accordion/header, exact-row authority, theme shell, and application-owned lifecycle boundaries. MIH-10 already provides the approved Audio DSP family redesign. MIH-11 provides the approved Matrix/IN1804 family redesign described by the requirements below. Codec and PDU family-specific redesign remain deferred to their own later OpenSpec changes.

Existing **room-mode** controls SHALL remain connected through current non-secret application intent/controller boundaries and SHALL remain enabled only when current unified-registry/lifecycle capability state permits them. A family follow-up SHALL NOT promote an action, control, signal, credential owner, handler/session owner, retry lane, or network lifecycle from a standalone/single-device screen merely because similar functionality exists there.

Existing room-mode PDU mutation/reconciliation, codec auxiliary/live behavior, Audio DSP live/meter behavior, and Matrix room live/local-refresh behavior SHALL remain governed by their current corresponding lifecycle contracts except where a later approved family change explicitly adds a capability through the same unified registry and serialized room interaction authority.

For Matrix/IN1804 specifically, the original foundation intentionally preserved a read-only room projection and deferred interactive room routing to `matrix-diagnostic-modern-ui`. MIH-11 now supersedes only that temporary Matrix family limitation: the modern exact-row Matrix presentation MAY expose output-1 route intents only through the unified exact-model registry and the existing serialized `MUTATION -> RECONCILIATION` room lifecycle. Standalone `MatrixScreen.routeRequested` SHALL NOT be wired or embedded as room authority, and no widget SHALL call a Matrix handler/session directly.

Compatibility/family presentation adaptation SHALL NOT make expanded widgets authoritative for credential selection/fallback, handlers, sessions, transports, successful credential memory, stale-operation authority, request generations, exact-row identity, accepted device state, or direct device network I/O.

#### Scenario: Existing room-mode device view opens inside the common accordion

- **GIVEN** an exact supported room row has a current approved room-mode family presentation
- **WHEN** the operator expands that row under the common accordion
- **THEN** the approved room-mode family presentation is reachable and bound to that exact row state
- **AND** no standalone/single-device screen is promoted merely because it has the same family
- **AND** no widget gains direct credential/session/network authority

#### Scenario: Existing room-mode device action preserves its application boundary

- **GIVEN** an approved current room-mode device-family action is authorized by the current unified-registry/lifecycle capability
- **WHEN** the operator invokes it from expanded presentation inside the accordion
- **THEN** the approved application intent/controller boundary is used
- **AND** presentation does not create a direct handler call or parallel network lifecycle

#### Scenario: MIH-11 Matrix routing replaces only the deferred read-only family limitation

- **GIVEN** an exact current `Extron IN1804` room row whose unified registration declares the MIH-11 Matrix route mutation/reconciliation bindings
- **WHEN** the modern Matrix output cell produces an approved route intent
- **THEN** routing enters the exact-row serialized room mutation lifecycle
- **AND** existing Matrix room live/local-refresh authority remains unchanged outside the mutation handoff
- **AND** standalone `MatrixScreen.routeRequested` is not room authority
- **AND** no direct widget-to-handler/session path is introduced

## ADDED Requirements

### Requirement: Expanded Matrix redesign targets the current room exact-row presentation surface

MIH-11 SHALL render its modern Matrix/IN1804 content inside the current room-mode exact-row presentation owned by `RoomDiagnosticTreeWidget`. On the current change base, an expandable Matrix row is projected through `RoomReadOnlyPresentation`, and `screen_key == "matrix"` is rendered by its Matrix builder.

A focused presentation-only Matrix dashboard widget/component MAY be extracted and embedded from that room path. Such a component MAY consume accepted exact-row evidence and emit safe non-secret local intents, but SHALL NOT own room identity, target-search, request generation/currentness, credentials, handler/session lifecycle, polling/live ownership, mutation delivery, reconciliation authority, or device network I/O.

The standalone `MatrixScreen` SHALL remain a separate presentation/lifecycle surface. It MAY reuse a pure presentation component later, but it SHALL NOT be selected, embedded, or promoted as room authority and is not MIH-11 room acceptance authority.

The common foundation accordion header remains unchanged. MIH-11 redesigns only the expanded Matrix family interior below that header.

#### Scenario: Expanded Matrix room row uses the modern presentation

- **GIVEN** the current room session contains an expandable exact `Extron IN1804` row
- **WHEN** the operator expands that row
- **THEN** the modern Matrix presentation renders inside the exact-row room content
- **AND** room/record authority remains the current exact row
- **AND** standalone `MatrixScreen` is not required or promoted as room authority

#### Scenario: Extracted Matrix widget remains presentation-only

- **GIVEN** implementation extracts a focused Matrix dashboard/table component
- **WHEN** it is embedded in room Matrix presentation
- **THEN** it consumes accepted current exact-row evidence and emits only approved non-secret presentation intents
- **AND** it owns no worker, handler/session, credential plan, room generation, transport, mutation lifecycle, or accepted device state

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

Exact pixel dimensions, border radii, and gaps MAY use current foundation/theme tokens, but the order, dominant central hierarchy, readable baseline content, and absence of baseline horizontal clipping are normative.

At the foundation minimum supported window of `1180 x 720`, implementation MAY use controlled reflow for auxiliary cards or existing expanded-content scrolling, provided all required Matrix information/table/actions remain reachable, table semantic order is preserved, and route/currentness authority does not change.

Dark/light theme switching SHALL be presentation-only. At a fixed viewport it SHALL preserve Matrix semantic order and action availability and SHALL perform no Matrix device I/O.

#### Scenario: Baseline Matrix dashboard preserves reference hierarchy

- **GIVEN** a current connected Matrix row is expanded at `1440 x 900`
- **WHEN** its presentation is laid out
- **THEN** General information is the left narrow card
- **AND** Matrix inputs/routing is the dominant center card
- **AND** Quick actions is the right narrow card
- **AND** all three are readable without baseline horizontal clipping

#### Scenario: Minimum-width layout remains usable

- **GIVEN** the same current Matrix presentation at the foundation minimum supported window
- **WHEN** auxiliary cards reflow or expanded-content scrolling is used
- **THEN** the Matrix table remains reachable with unchanged semantic column order
- **AND** route state/action meaning remains usable
- **AND** reflow triggers no device I/O

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

Each row SHALL use only accepted current exact-row evidence through deterministic presentation mapping. Accepted aliases MAY be mapped explicitly (for example `model`, `mac`/`mac_address`, `serial`/`serial_number`, `firmware`/`version`, `temperature`, `uptime`), but presentation SHALL NOT infer a value from unrelated fields, model text, reference artwork, logs, prior snapshots, or widget state.

If accepted evidence does not establish a field, the row SHALL display `Нет данных` or the foundation safe no-data equivalent. On the current change base, absence of authoritative Matrix MAC, serial, firmware, or uptime evidence is expected and SHALL NOT cause new protocol reads or parser/handler expansion under MIH-11.

Unrelated currently available fields such as connection protocol SHALL NOT replace the approved reference slots merely to avoid no-data presentation.

#### Scenario: Current Matrix snapshot lacks reference-only information fields

- **GIVEN** accepted current Matrix evidence contains model and temperature but no MAC, serial, firmware, or uptime
- **WHEN** the General information card renders
- **THEN** model and temperature render from accepted evidence
- **AND** MAC, serial, firmware, and uptime render truthful no-data values
- **AND** presentation issues no additional Matrix request to fill them

### Requirement: Matrix input table uses data-driven rows and the approved column order

The central Matrix table SHALL use this semantic order:

```text
[input ordinal] | Сигнал | HDCP | Входы | [accepted output-1 name or Main Output]
```

The leading ordinal column SHALL remain compact and MAY use an empty visual header with accessible `№` meaning. `Входы` displays the accepted input name. The output column uses the first accepted output name when present/non-empty and otherwise `Main Output`.

At baseline, approximate table-width allocation SHALL preserve this hierarchy:

```text
input ordinal    7-9%
Сигнал          18-21%
HDCP            16-18%
Входы           25-29%
output           26-30%
```

Rows SHALL follow the accepted current input count/order. MIH-11 SHALL NOT hard-code the eight rows visible in the design example. The rendered number of inputs comes from accepted current Matrix evidence; input ordinals and names SHALL remain aligned with that evidence.

#### Scenario: Four-input accepted Matrix is not rendered as eight inputs

- **GIVEN** accepted current Matrix evidence establishes four inputs
- **WHEN** the modern table renders
- **THEN** exactly four input rows are presented in accepted order
- **AND** no additional rows are fabricated from the visual reference

#### Scenario: Output header uses accepted name when available

- **GIVEN** accepted Matrix evidence provides a non-empty output-1 name
- **WHEN** the table renders
- **THEN** that accepted name labels the output column
- **AND** `Main Output` is used only as the safe presentation fallback when no accepted output name is available

### Requirement: Matrix signal, HDCP, and route presentation remains meaningful without color

For each accepted input row, signal state SHALL be derived from accepted normalized `signal_status` evidence. A confirmed present signal SHALL have a positive non-color cue and text equivalent to `есть`; confirmed absence SHALL have a distinct non-color cue/text equivalent to `нет сигнала`; missing/unknown evidence SHALL use a neutral no-data/unknown presentation. Color MAY reinforce but SHALL NOT be the only meaning.

HDCP presentation SHALL use only accepted normalized HDCP evidence. The reference's sample `2.2` value SHALL NOT be fabricated. When accepted evidence establishes a meaningful HDCP version/state token, that token MAY be shown; otherwise an honest active/inactive/no-data presentation SHALL be used according to the existing normalized evidence contract. HDCP state SHALL NOT be inferred from signal presence, route state, model name, color, or reference artwork.

Output-1 route state SHALL derive only from accepted `current_connection` evidence:

```text
current_connection == this input -> non-color positive cue + `активен`
known different current input     -> neutral cue + `не выбран`
missing/unknown connection        -> neutral cue + `Нет данных`
```

Local hover/click/confirmation/ACK state SHALL NOT change the visible authoritative route to `активен` before reconciliation accepts a confirming snapshot.

#### Scenario: Reference sample HDCP version is not invented

- **GIVEN** accepted HDCP evidence for an input does not establish version `2.2`
- **WHEN** the Matrix table renders
- **THEN** it does not display fabricated `2.2`
- **AND** it renders only truthful accepted state/version/no-data meaning

#### Scenario: Route ACK does not optimistically recolor the table

- **GIVEN** a route mutation has received apparent send success but reconciliation is not yet accepted
- **WHEN** the Matrix table is rendered
- **THEN** accepted `current_connection` remains the route-state authority
- **AND** the requested row is not shown as authoritative `активен` solely because of the ACK

### Requirement: Matrix output cells emit only approved exact-row route intent

A non-active output-1 cell SHALL be actionable only when the exact current expanded row is `Extron IN1804`, has usable connected accepted state, is not stale/degraded/blocked/unconfirmed, the unified model registration advertises the approved Matrix mutation/reconciliation capability, and the serialized room interaction lane currently permits mutation.

The presentation SHALL emit only a non-secret immutable route intent equivalent to `output_num = 1` plus accepted `input_num = N`, together with the existing exact-row presentation signal identity required by composition. It SHALL NOT contain credentials, handler/session references, raw target-search text, initial source record, standalone screen selection, or global Matrix target state.

The currently active output cell SHALL be non-actionable/no-op. A stale, degraded, failed, blocked, non-current, unsupported, or otherwise unauthorized row SHALL expose no route intent.

Presentation SHALL NOT call `ExtronIN1804Handler`, `MatrixController.request_route`, socket/transport methods, or other device I/O directly. Composition must revalidate current exact-row authority and obtain explicit operator confirmation before passing the intent into `RoomInteractionCoordinator.confirm_mutation()`.

#### Scenario: Operator selects another current input

- **GIVEN** a connected current exact Matrix row has input 1 authoritative as active
- **AND** input 2 output cell is authorized and non-active
- **WHEN** the operator activates input 2's output cell
- **THEN** presentation emits one safe output-1/input-2 route intent
- **AND** no Matrix device I/O occurs from the widget
- **AND** composition requires explicit confirmation before mutation lifecycle begins

#### Scenario: Current active route is clicked

- **GIVEN** input N is already authoritative as active
- **WHEN** the operator clicks its output cell
- **THEN** no route mutation intent is submitted
- **AND** no device I/O starts

#### Scenario: Stale row cannot route

- **GIVEN** the prior Matrix row/context is stale, superseded, degraded, blocked, or no longer the current expanded row
- **WHEN** an old presentation event attempts to request routing
- **THEN** it cannot start a room mutation
- **AND** it acquires no Matrix handler/session or device network resource

### Requirement: Matrix Quick actions remain truthful to approved capabilities

The Matrix `Быстрые действия` card SHALL visually contain `Обновить статус` and `Перезагрузить устройство` in the approved reference hierarchy.

`Обновить статус` SHALL map only to the existing exact-row Local Refresh intent and SHALL be enabled only under existing room interaction authorization. It SHALL NOT create a second Matrix refresh/polling path.

`Перезагрузить устройство` SHALL be visible but disabled/non-actionable on the current change base because no approved Extron IN1804 reboot mutation capability exists. It SHALL emit no application intent, worker start, handler/session acquisition, protocol command, or device request.

If an `Открыть расширенный экран` affordance is rendered for reference-layout fidelity, it SHALL also remain disabled/non-actionable in MIH-11. It SHALL NOT navigate/promote standalone `MatrixScreen`, create a second MatrixController/session, alter room target authority, or perform device I/O.

#### Scenario: Quick Refresh uses the existing room lifecycle

- **GIVEN** the exact connected Matrix row currently permits Local Refresh
- **WHEN** the operator selects `Обновить статус`
- **THEN** the existing exact-row Local Refresh intent is requested
- **AND** no parallel Matrix refresh controller/lane is created

#### Scenario: Reboot remains a disabled placeholder

- **GIVEN** the Matrix Quick actions card is visible
- **WHEN** `Перезагрузить устройство` is rendered
- **THEN** it is clearly disabled/non-actionable
- **AND** interacting with it performs no Matrix device I/O
