# diagnostic-ui-presentation Delta

## ADDED Requirements

### Requirement: Expanded room codec presentation uses one five-card reference-aligned dashboard

Every current supported room codec row SHALL render the same expanded codec dashboard after it becomes the current expanded exact row. The dashboard SHALL apply to `Huawei TE20`, `Huawei TE40`, `CloudLink Bar 310`, `CloudLink Box 310`, and `Polycom RPG 310` as current-baseline acceptance oracles while runtime model/capability authority remains the unified exact-model registration.

At the common `1440 x 900` baseline viewport the expanded codec area SHALL present exactly five top-aligned cards in this left-to-right order:

```text
Состояние | Вызов и презентация | Аудио | Журнал вызовов | Действия
```

The target relative card weights SHALL be approximately `23:17:18:25:17`. Qt/layout tuning of roughly four percentage points per card MAY be used while preserving the same hierarchy and ensuring that `Состояние` and `Журнал вызовов` remain substantial, `Аудио` remains compact, and `Действия` remains the narrow right action card. The dashboard SHALL be recognizably consistent with the approved codec reference by card order, relative proportions, field names/order, indicators, density, control placement and visual hierarchy; acceptance target is approximately 90% correspondence rather than pixel-identical font rasterization or spacing.

Dark theme SHALL be the baseline visual-reference theme. Light theme SHALL preserve the same card order/geometry and semantic states using the shared theme. At the common minimum supported room window, controlled reflow or scrolling MAY occur, but all five cards, rows and controls SHALL remain reachable and SHALL NOT disappear merely due to width.

The dashboard SHALL be presentation/application-intent only: it SHALL NOT own target identity, credentials, handler/session instances, request generations, retries or device I/O.

#### Scenario: Current codec row opens at baseline size

- **GIVEN** a current connected supported codec row is expanded at `1440 x 900`
- **WHEN** its expanded presentation is built
- **THEN** the five cards appear in the approved order with approximately the approved relative weights
- **AND** the dashboard uses the shared dark-theme card/typography/control language
- **AND** no standalone `CodecScreen` widget state becomes room authority

#### Scenario: Codec dashboard renders in light theme

- **GIVEN** the codec dashboard is visible
- **WHEN** the user switches to light theme
- **THEN** the five-card geometry and field/control order remain unchanged
- **AND** theme switching starts no codec device I/O

### Requirement: Codec state and call cards keep permanent reference slots with truthful no-data values

The `Состояние` card SHALL permanently render these rows in this exact order:

```text
Модель
MAC-адрес
Серийный номер
Платформа
Версия ПО
Микрофон
Камера
```

The `Вызов и презентация` card SHALL permanently render these rows in this exact order:

```text
Статус звонка
Презентация
Регистрация SIP/H.323
```

For either card, absent, stale-unusable, failed, malformed or otherwise unavailable current evidence SHALL render `Нет данных` in the corresponding slot. The shared dashboard SHALL NOT hide a required row/card, invent `Unknown`, invent numeric zero, copy another model's value, or infer semantic values from model-name/localized-string substrings.

Legitimate current false/zero values SHALL remain distinguishable from missing evidence where the approved model normalization defines them. Status indicators MAY use color but SHALL preserve text/non-color/accessibility meaning.

#### Scenario: Model lacks one reference field

- **GIVEN** current accepted codec evidence has no usable `Платформа` value
- **WHEN** `Состояние` is rendered
- **THEN** the `Платформа` row remains in its fixed position
- **AND** its value is `Нет данных`
- **AND** neighboring rows are not shifted into a different model-specific layout

### Requirement: Codec audio card keeps one common control geometry and never fabricates meter or volume authority

The `Аудио` card SHALL permanently contain, in this order, a current microphone-level presentation followed by microphone and speaker controls equivalent to:

```text
Микрофон (уровень)     <horizontal level indicator>
Громкость микрофона    [−] <value> [+] [mute]
Громкость динамиков    [−] <value> [+] [mute]
```

The meter SHALL consume only existing current accepted/live codec level evidence already produced by an approved model lifecycle. This change SHALL NOT start a new meter poll, timer, handler/session acquisition or device request merely to populate the reference meter. When compatible current level evidence is unavailable, the indicator remains visibly unavailable and its value meaning is `Нет данных` rather than a fabricated zero level.

Microphone and speaker values SHALL use current accepted authoritative values appropriate to the exact model. Missing/unusable current values render `Нет данных` while the reference control positions remain present.

All `−`, `+`, mute controls SHALL remain visually enabled/clickable in the common layout. Clicking a model/operation combination that unified capability authority marks unsupported SHALL show the approved local informational message and SHALL perform no handler/session acquisition or device I/O. Supported clicks SHALL publish only safe typed exact-row intents to application composition under `room-device-interaction-lifecycle`.

#### Scenario: Codec has no current microphone level evidence

- **WHEN** a codec row has no current compatible microphone-level evidence
- **THEN** the Audio card keeps the meter slot and shows it as unavailable/`Нет данных`
- **AND** rendering does not start a meter request to fill the slot

#### Scenario: Audio operation is unsupported for the exact model

- **GIVEN** the exact registration marks the clicked microphone/speaker operation unsupported
- **WHEN** the operator clicks its visible control
- **THEN** a local informational dialog equivalent to `Операция не поддерживается данной моделью` is shown
- **AND** no room network interaction is started
- **AND** current LIVE, cache and row authority remain unchanged

### Requirement: Codec call-log card previews three newest accepted records and retains the existing detailed window

The `Журнал вызовов` card SHALL render at most the three newest records from the current accepted exact-row call-log preview. For each record it SHALL present a safe direction/non-color cue, peer/number/display identity when available, and timestamp when available. Missing subfields SHALL render `Нет данных`. If no current accepted records are available, the card SHALL show `Нет данных` rather than an empty unexplained surface.

The card SHALL contain a visible `Развернуть` action. When a current accepted full preview result exists for the exact row/generation, `Развернуть` MAY open the existing detailed call-log window from that accepted result without another device read. When no current accepted preview exists, `Развернуть` SHALL use the existing serialized call-log auxiliary acquisition and populate/open the detailed window only from a current accepted result.

The card SHALL NOT own call-log network acquisition. Automatic preview acquisition, cancellation, LIVE handoff, duplicate suppression and stale-result authority are defined by `room-device-interaction-lifecycle`.

#### Scenario: More than three call records are accepted

- **GIVEN** current accepted call-log data contains more than three records
- **WHEN** the preview card renders
- **THEN** exactly the three newest records are shown in deterministic newest-first order
- **AND** `Развернуть` retains access to the existing detailed full-log presentation

#### Scenario: Call log has no accepted data

- **WHEN** the current exact codec has no accepted call-log preview records
- **THEN** the preview card displays `Нет данных`
- **AND** the `Развернуть` action remains present

### Requirement: Codec action card exposes Local Refresh and registry-gated reboot without inventing capabilities

The `Действия` card SHALL permanently render `Обновить статус` and `Перезагрузить устройство` as visually actionable controls.

`Обновить статус` SHALL be only an alias of the existing exact-row Local Refresh intent/lifecycle. It SHALL NOT create a codec-specific refresh path, second interaction lane, direct handler call or different credential authority.

`Перезагрузить устройство` SHALL resolve support from the exact unified codec-control registration before any room mutation is admitted. If no already-approved safe typed reboot binding exists for that exact model, clicking it SHALL show a local informational dialog equivalent to `Операция не поддерживается данной моделью` and SHALL perform no device I/O. Merely finding a similarly named method on a standalone widget/handler SHALL NOT establish room reboot capability.

If a reboot binding is approved and present, the action SHALL enter the existing exact-row state-changing mutation/reconciliation lifecycle and obey all command-safety/readback rules; the presentation SHALL never treat command dispatch/ACK as confirmed final device state.

#### Scenario: Refresh action is clicked

- **WHEN** the operator clicks `Обновить статус` on an eligible current codec row
- **THEN** the existing Local Refresh lifecycle is requested for that exact row
- **AND** no codec-specific refresh owner is created

#### Scenario: Reboot is not approved for the exact model

- **WHEN** the operator clicks `Перезагрузить устройство` for an exact registration without an approved reboot binding
- **THEN** the unsupported-operation information is shown locally
- **AND** no handler/session is acquired and no reboot command is sent
