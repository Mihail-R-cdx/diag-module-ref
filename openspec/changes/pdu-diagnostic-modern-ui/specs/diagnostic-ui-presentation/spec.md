# diagnostic-ui-presentation Delta

## MODIFIED Requirements

### Requirement: Equipment rows share one non-color accordion header contract

Every room equipment record SHALL use one compact top-level row layout equivalent to:

```text
expand chevron -> device-class icon -> model label -> status cue + status text -> IP
```

At baseline size a collapsed row SHALL remain within the `38-46 px` height range, targeting about `42 px`. The device-class icon SHALL be approximately `28 x 28 px` and the chevron/icon cluster SHALL remain compact. Model text SHALL receive the largest flexible width, and status and IP SHALL remain readable without forcing the row into multiple lines under ordinary baseline content. The tree header and trailing common overflow/action placeholder are intentionally not visible.

Status SHALL remain understandable without color alone. The row SHALL retain explicit text/non-color meaning for connected, waiting, connecting, unsupported, missing-IP, ambiguous-IP, failed, connection-lost, and other approved states. Color MAY reinforce but SHALL NOT be the only meaning.

Exactly one room equipment row MAY be expanded at a time. Expanding another expandable row SHALL collapse the previous row. Accordion changes SHALL remain presentation/current-selection behavior and SHALL NOT reorder the automatic room acquisition queue.

By default, including every non-PDU equipment row and every collapsed PDU row, the top-level row SHALL contain no right-side device action. The absence of a common row action SHALL NOT create, imply, or require a hidden/disabled placeholder or an alternate direct network path.

As one narrow family-specific exception, the **current expanded PDU row only** MAY append exactly one far-right Refresh affordance after the common identity/status/IP content. This exception SHALL NOT change the common left chevron, device-class icon, exact model, explicit status or IP anatomy; the left chevron remains the sole expand/collapse control. The PDU header Refresh SHALL NOT collapse/re-expand the row, change current expanded `record_id`, infer target from displayed text, call a handler directly, own credentials/sessions, or create an independent refresh lane/generation. It SHALL publish only the existing exact-row `LOCAL_REFRESH` intent defined by `room-device-interaction-lifecycle` and SHALL obey the same eligibility, locks, currentness and stale-result rules as every other Local Refresh entry point.

All authorized device controls other than that single expanded-PDU header Refresh exception SHALL remain inside expanded content and through current application intent/controller boundaries. No non-PDU family receives a right-side row action from this exception, and a collapsed PDU row SHALL NOT retain the Refresh affordance.

For the modern PDU expanded presentation, the pre-existing generic expanded-content refresh affordance labelled `Локальный опрос` (or an equivalent legacy generic Local Refresh control) SHALL NOT be rendered in addition to the new family dashboard. Exactly two visible PDU Local Refresh entry points SHALL exist while the PDU row is expanded:

```text
far-right PDU header Refresh
`Обновить статус` inside `Управление розетками`
```

Both SHALL be aliases of the same exact-row `LOCAL_REFRESH` lifecycle. Rendering a third generic refresh entry point is prohibited.

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

#### Scenario: Collapsed PDU row uses the common header without a family action

- **GIVEN** a current supported PDU row is collapsed
- **WHEN** its top-level row is rendered
- **THEN** it uses the common chevron, icon, model, status and IP anatomy
- **AND** no right-side PDU Refresh action is visible

#### Scenario: Expanded PDU row uses the narrow header Refresh exception

- **GIVEN** a current supported PDU row is the current expanded exact row
- **WHEN** its top-level row is rendered
- **THEN** the common identity/status/IP anatomy remains intact
- **AND** exactly one far-right PDU Refresh affordance is visible
- **AND** the common left chevron remains the only expand/collapse control
- **AND** activating Refresh does not change expanded selection and can only request the existing exact-row `LOCAL_REFRESH`

#### Scenario: Modern expanded PDU exposes exactly two Local Refresh entry points

- **GIVEN** the modern PDU dashboard is visible
- **WHEN** the operator inspects available refresh controls
- **THEN** the visible refresh entry points are exactly the header Refresh and `Обновить статус`
- **AND** no generic `Локальный опрос` or other third refresh affordance is rendered
- **AND** both visible controls resolve to the same exact-row `LOCAL_REFRESH` lifecycle

## ADDED Requirements

### Requirement: Expanded room PDU presentation uses one self-contained two-card dashboard contract

Every current supported room PDU row SHALL render the same expanded room-mode PDU dashboard after it becomes the current expanded exact row. `Aten PE8208AV` and `Extron IPL T PCS4i` are current-baseline acceptance oracles while runtime model/capability authority remains the existing exact application/PDU capability registration.

External screenshots or conversation history MAY be used as product-design inspiration, but they are NOT normative acceptance dependencies. Only the region opened by expanding a PDU row is in scope for this family change. Implementation and independent validation SHALL be possible from this repository-local contract alone.

At the common `1440 x 900` logical-pixel baseline viewport, the expanded PDU body SHALL contain exactly two top-aligned cards in this left-to-right order:

```text
Основная информация | Управление розетками
```

Their target relative width weights SHALL be `22:78`. Per-card tuning of approximately `±4` percentage points MAY accommodate Qt metrics, but the outlet-management card SHALL remain visually dominant and the information card SHALL remain a narrow supporting card. Horizontal gap SHALL be `10-14 px`, card internal padding `14-18 px`, and target expanded body height approximately `350-410 px`. The two cards SHALL have aligned tops and approximately aligned bottoms at baseline.

At the common minimum supported room window, deterministic reflow or controlled scrolling MAY occur, but both cards, all fixed controls and current outlet rows SHALL remain reachable. Reflow SHALL preserve the information-before-outlets logical order.

Dark theme SHALL be the baseline theme. Light theme SHALL preserve the same card order, relative geometry, table/action order, spacing class and semantic states using the shared theme. Theme switching, resize, hover, repaint and scrolling SHALL remain presentation-only and SHALL perform no PDU device I/O or authority change.

The dashboard SHALL be presentation/application-intent only and SHALL NOT own exact-row identity, credentials, handler/session instances, request generations, capability support, retries or accepted PDU state.

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

### Requirement: Expanded PDU header keeps only one family-specific refresh action

The modified common accordion-header contract above governs the PDU row. The common room accordion chevron, device-class icon, exact model label, explicit status cue/text and IP presentation remain intact. For the current expanded PDU row only, the narrow exception permits exactly one far-right family-specific Refresh icon/control.

The PDU expanded header SHALL NOT add a kebab/overflow menu and SHALL NOT add a second right-side collapse/expand affordance. The common left accordion chevron remains the sole expand/collapse control. A collapsed PDU row SHALL have no right-side family action.

The family-specific Refresh icon SHALL publish only the existing exact-row Local Refresh intent described by `room-device-interaction-lifecycle`; it SHALL NOT call a handler directly, own a second refresh generation, infer target from displayed text, collapse/re-expand the row or change the current exact-row selection.

The modern PDU dashboard SHALL NOT retain the old generic expanded-content `Локальный опрос` control. Together with `Обновить статус` inside `Управление розетками`, the header Refresh forms the complete set of exactly two visible PDU Local Refresh entry points, and both are aliases of the same lifecycle.

At baseline the refresh action target SHALL be approximately `32-40 px` square and visually subordinate to the model/status identity.

#### Scenario: Expanded PDU header is rendered

- **WHEN** a supported PDU row becomes the current expanded row
- **THEN** exactly one far-right PDU Refresh action is present
- **AND** no PDU kebab/overflow action or additional right-side collapse action is present
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

`Управление розетками` SHALL place this top action strip above the outlet table in exact left-to-right order:

```text
Обновить статус | Включить всё | Выключить всё
```

The table SHALL have exactly these visible columns in this order:

```text
Розетка | Имя розетки | Состояние | Текущая мощность | Действия
```

At baseline, target relative column weights SHALL be approximately `9:24:16:18:33`, with approximately `±3` percentage points of tuning per column where needed for platform Qt metrics. Table header target height SHALL be `32-40 px`, ordinary outlet row height `36-44 px`, and inter-control spacing in the action cell `6-10 px`.

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

`Вкл` SHALL use green semantic styling, `Выкл` red/destructive semantic styling, and `Перезапуск` neutral/secondary styling. Target control height SHALL be `28-34 px`; the two shorter power buttons SHOULD occupy approximately `54-76 px` each and `Перезапуск` approximately `92-124 px` where baseline width permits. Fixed visibility does not imply network support; support behavior is defined by `device-diagnostics-and-control` and `room-device-interaction-lifecycle`.

No bulk reboot control SHALL be rendered.

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

1. the expanded PDU body contains exactly two cards in `Основная информация | Управление розетками` order and approximately the approved `22:78` weight hierarchy;
2. `Основная информация` contains exactly `Модель`, `Серийный номер`, `MAC-адрес` in order with no extra PDU information rows;
3. the outlet card action strip contains exactly `Обновить статус`, `Включить всё`, `Выключить всё` in order;
4. the outlet table exposes exactly `Розетка`, `Имя розетки`, `Состояние`, `Текущая мощность`, `Действия` in order and within the approved column hierarchy;
5. an eight-outlet fixture has stable row density/order and additional rows remain reachable through controlled scrolling;
6. ON/OFF/unavailable states use the required explicit text plus green/red/neutral semantic cues and never rely on color alone;
7. every current power cell renders `—` and the placeholder column remains visibly aligned;
8. every action cell groups `Вкл`, `Выкл`, `Перезапуск` in order with green/red/neutral semantic treatment and no bulk reboot exists;
9. the current expanded PDU header has exactly one far-right PDU Refresh action, no kebab/overflow or second right-side collapse action, and the expanded presentation contains no third legacy/generic `Локальный опрос` refresh affordance;
10. light theme preserves the same card/table/control geometry, ordering and readable semantic states without device I/O.

Checkpoints 1, 2, 3, 4, 6, 8 and 9 are mandatory structural/semantic checkpoints and cannot be waived by approximate similarity. The implementation SHALL satisfy all mandatory checkpoints and at least `9/10` total checkpoints to meet the product target of approximately 90% visual correspondence. Font rasterization, standard-icon glyph variation and one-pixel antialiasing differences are not acceptance failures when these repository-local ranges/checkpoints are satisfied.

#### Scenario: Independent validator has no source screenshot

- **WHEN** an independent validator reviews the PDU dashboard using only repository artifacts
- **THEN** the ten checkpoints and detailed geometry/semantic requirements are sufficient to decide visual acceptance
- **AND** all mandatory checkpoints plus at least nine total checkpoints are required for the approximately 90% target
