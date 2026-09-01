# diagnostic-ui-presentation Delta

## ADDED Requirements

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
header height                34-42 px
header/section icon          18-22 px
card title                   11-12 pt semibold equivalent
body label                   9-10 pt
body primary value           10-11 pt
secondary/timestamp text      9-10 pt
ordinary data row height     28-34 px
status-dot diameter           8-10 px when a dot is used
```

Headers SHALL place the icon before the title on one line. Status meaning SHALL never rely on color alone; text/accessibility meaning remains required. Values SHALL not overlap adjacent controls or card boundaries at baseline.

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

### Requirement: Codec state and call cards keep permanent slots with deterministic row geometry

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

At baseline each row SHALL use the common `28-34 px` row height. Label and value SHALL form a stable two-part row; the label remains visually secondary to the current value and may use an approximately `42-52%` label / `48-58%` value allocation where a grid is used. Long safe values MAY elide with tooltip/accessibility text rather than increase one row enough to destroy five-card alignment.

For either card, absent, stale-unusable, failed, malformed or otherwise unavailable current evidence SHALL render `Нет данных` in the corresponding slot. The shared dashboard SHALL NOT hide a required row/card, invent `Unknown`, invent numeric zero, copy another model's value, or infer semantic values from model-name/localized-string substrings.

Legitimate current false/zero values SHALL remain distinguishable from missing evidence where the approved model normalization defines them. Status indicators MAY use color but SHALL preserve text/non-color/accessibility meaning.

#### Scenario: Model lacks one field

- **GIVEN** current accepted codec evidence has no usable `Платформа` value
- **WHEN** `Состояние` is rendered
- **THEN** the `Платформа` row remains in its fixed position
- **AND** its value is `Нет данных`
- **AND** neighboring rows are not shifted into a different model-specific layout

### Requirement: Codec audio card has fixed meter and control-row geometry without fabricated authority

The `Аудио` card SHALL permanently contain, in this order:

```text
Микрофон (уровень)     <horizontal level indicator>
Громкость микрофона    [−] <value> [+] [mute]
Громкость динамиков    [−] <value> [+] [mute]
```

At baseline the microphone-level label SHALL precede a horizontal indicator occupying the available card-body width. The indicator's visible bar height SHALL be `8-12 px` with a clearly visible unavailable state. The two control rows SHALL follow with `8-12 px` vertical separation from the meter block and each other.

For each audio control row:

```text
minus / plus button target size       28-34 px square
mute affordance target height          28-34 px
mute affordance target width           44-64 px
numeric/no-data value region           at least 38 px, centered/aligned
inter-control gap                       4-8 px
```

The numeric/no-data value SHALL remain visible between decrement and increment controls. Mute SHALL remain a distinct affordance rather than replacing the numeric value. The shared presentation SHALL consume separate numeric volume and typed mute-state authority from `device-diagnostics-and-control`; it SHALL NOT put strings such as `Muted` into a numeric volume slot or treat a displayed numeric value as a generic untagged mute state.

The meter SHALL consume only existing current accepted/live codec level evidence already produced by an approved model lifecycle. This change SHALL NOT start a new meter poll, timer, handler/session acquisition or device request merely to populate the meter. When compatible current level evidence is unavailable, the indicator remains visibly unavailable and its value meaning is `Нет данных` rather than a fabricated zero level.

Microphone and speaker numeric values SHALL use current accepted authoritative values appropriate to the exact model. Missing/unusable current values render `Нет данных` while the fixed control positions remain present.

The `−`, `+` and mute visual affordances SHALL remain visibly present for every current codec model. This fixed presentation does not make the corresponding **network capability** supported. When the existing room interaction lock matrix otherwise permits input, an operation explicitly marked unsupported by unified capability authority MAY remain clickable only as the approved local-only informational affordance: it SHALL resolve before interaction admission and SHALL perform zero handler/session/credential/network activity. During an active/retiring lifecycle that locks state-changing controls, these common affordances SHALL obey that temporary lock.

Supported clicks SHALL publish only safe typed exact-row intents to application composition under `room-device-interaction-lifecycle`.

#### Scenario: Codec has no current microphone level evidence

- **WHEN** a codec row has no current compatible microphone-level evidence
- **THEN** the Audio card keeps the meter slot and shows it as unavailable/`Нет данных`
- **AND** rendering does not start a meter request to fill the slot

#### Scenario: Audio operation is unsupported for the exact model

- **GIVEN** the exact registration marks the clicked microphone/speaker network operation unsupported
- **AND** no existing interaction lock currently disables the common affordances
- **WHEN** the operator clicks its visible affordance
- **THEN** a local informational dialog equivalent to `Операция не поддерживается данной моделью` is shown
- **AND** the network capability remains unsupported
- **AND** no room network interaction is started
- **AND** current LIVE, cache and row authority remain unchanged

### Requirement: Codec call-log card uses normalized newest-first order and reserves three-row preview density

The `Журнал вызовов` card SHALL render at most the first three records from the current accepted normalized newest-first call-log result defined by `device-diagnostics-and-control`. Presentation SHALL NOT re-sort localized timestamp/display strings or manufacture chronology.

At baseline the preview region SHALL reserve visual capacity for three compact records so card height does not change merely because one or two calls are present. Each rendered record row SHALL target `52-64 px` height and contain:

```text
direction/non-color cue        18-22 px visual target
peer/number/display identity   primary line, 10-11 pt
safe timestamp                 secondary line, 9-10 pt
row separator                  subtle shared-theme divider except after last visible row
```

Missing peer or timestamp subfields SHALL render `Нет данных` in that subfield. If zero current accepted records are available, the preview region SHALL display one clear `Нет данных` empty state rather than three fabricated empty records.

The card SHALL contain a visible `Развернуть` action anchored after the preview region, with target height `34-40 px` and full/near-full card-body width. When a current accepted full preview result exists for the exact row/generation, `Развернуть` SHALL open and populate the existing detailed call-log window from that accepted result without another device read. When no current accepted preview exists, `Развернуть` SHALL use the existing serialized explicit call-log auxiliary acquisition and SHALL open/populate the detailed window only from a current accepted result.

The card SHALL NOT own call-log network acquisition. Automatic preview attempt authority, expansion epochs, cancellation, LIVE handoff, duplicate suppression and stale-result authority are defined by `room-device-interaction-lifecycle`.

#### Scenario: More than three call records are accepted

- **GIVEN** current accepted call-log data contains more than three records in normalized newest-first order
- **WHEN** the preview card renders
- **THEN** exactly the first three normalized records are shown
- **AND** presentation performs no second chronology sort
- **AND** `Развернуть` retains access to the existing detailed full-log presentation

#### Scenario: Call log has no accepted data

- **WHEN** the current exact codec has no accepted call-log preview records
- **THEN** the preview region displays `Нет данных`
- **AND** the `Развернуть` action remains present

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

Manual visual acceptance at `1440 x 900` in dark theme SHALL use the following ten repository-local checkpoints; access to any external screenshot is unnecessary:

1. exactly five cards in the required left-to-right order;
2. card width weights remain within the approved `23:17:18:25:17` ±4-point envelope;
3. card tops align and card heights/gaps/padding remain within the baseline ranges above;
4. all card headers use the common icon/title anatomy and typography ranges above;
5. `Состояние` and `Вызов и презентация` contain exactly the required permanent rows in order;
6. `Аудио` uses horizontal meter then microphone row then speaker row with the required control placement/sizing and distinct numeric/mute semantics;
7. `Журнал вызовов` reserves three-row density, uses direction + primary peer + secondary timestamp anatomy, and places `Развернуть` after the preview;
8. `Действия` uses exactly two vertically stacked full-width actions in required order/sizing;
9. ordinary labels/values/status indicators follow the shared size/density/non-color ranges above without overlap or model-specific layout collapse;
10. light theme preserves the same geometry/order and readable semantic states without device I/O.

Checkpoints 1, 5, 6, 7 and 8 are mandatory structural checkpoints and cannot be waived by approximate similarity. The implementation SHALL satisfy all mandatory structural checkpoints and at least `9/10` total checkpoints to meet the product target of approximately 90% visual correspondence. Font rasterization and one-pixel antialiasing differences are not acceptance failures when these repository-local ranges/checkpoints are satisfied.

#### Scenario: Independent validator has no source screenshot

- **GIVEN** an independent validator has only the repository and approved OpenSpec artifacts
- **WHEN** the codec UI is manually reviewed at the baseline viewport
- **THEN** the validator can evaluate all ten checkpoints from this specification
- **AND** no external image, prior chat or agent report is required to decide visual conformance
