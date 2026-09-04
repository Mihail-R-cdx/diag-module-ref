# diagnostic-ui-presentation Delta

## MODIFIED Requirements

### Requirement: Codec state and call cards keep permanent slots with deterministic row geometry

The `Состояние` card SHALL permanently render these rows in this exact order:

```text
Модель
MAC-адрес
Серийный номер
Версия ПО
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

For either card, absent, stale-unusable, failed, malformed or otherwise unavailable current evidence SHALL render `Нет данных` in the corresponding slot. The shared dashboard SHALL NOT hide a required row/card, invent `Unknown`, invent numeric zero, copy another model's value, or infer semantic values from model-name/localized-string substrings.

The approved five-card visual layout uses no leading status dots in `Состояние` or `Вызов и презентация`; all values in their right column SHALL align to the right edge. `Микрофон` and `Камера` use their safe textual value. `Статус звонка` and `Презентация` render `Да` or `Нет` only from typed/structured or exact-adapter-normalized boolean evidence; unavailable evidence remains `Нет данных`.

`Регистрация SIP/H.323` SHALL use a non-text icon in the right value column: `✓` for confirmed registration and `✕` for confirmed failure. The shared GUI SHALL receive this semantic state from the same typed/structured or exact-adapter-normalized evidence and SHALL NOT parse localized display strings, model names or substrings. If registration evidence is unavailable, it SHALL render a neutral `—` icon; icon color is supplementary and never the sole meaning.

#### Scenario: State card renders the reduced permanent row set

- **WHEN** a current supported codec `Состояние` card is rendered
- **THEN** it contains exactly `Модель`, `MAC-адрес`, `Серийный номер`, `Версия ПО`, `Микрофон`, and `Камера` in the required order
- **AND** no `Платформа` row is visible
- **AND** internal platform evidence MAY remain available outside this presentation

#### Scenario: Call-card status has no current evidence

- **GIVEN** current call, presentation or registration evidence has no usable normalized semantic state
- **WHEN** the codec state/call cards are rendered
- **THEN** each row remains in its fixed position
- **AND** call/presentation render `Нет данных` while registration renders a neutral `—` icon
- **AND** the GUI does not infer a state from a localized fallback string

### Requirement: Codec audio card has fixed meter and control-row geometry without fabricated authority

The `Аудио` card SHALL permanently contain, in this order:

```text
Микрофон (уровень)     <horizontal level indicator or explicit unsupported/no-data state>
Громкость микрофона    [−] <value> [+] [mute]
Громкость динамиков    [−] <accepted percentage or Нет данных> [+] [mute]
```

At baseline the microphone-level label SHALL precede a horizontal indicator occupying the available card-body width. The indicator's visible bar height SHALL be `8-12 px` when the exact model supports the approved modern room live microphone-meter capability. The two control rows SHALL follow with `8-12 px` vertical separation from the meter block and each other.

The modern codec Audio card SHALL NOT render a speaker-volume horizontal meter, progress bar, scale, gauge, or second visual level indicator. Speaker volume is represented only by its control row and the accepted percentage/no-data value between `−` and `+`.

For each audio control row:

```text
minus / plus button target size       28-34 px square
mute affordance target height          28-34 px
mute affordance target width           44-64 px
numeric/no-data value region           at least 38 px, centered/aligned
inter-control gap                       4-8 px
```

The microphone numeric/no-data value SHALL remain distinct from mute state. The speaker value region SHALL render `<N>%` only from current accepted `speaker_volume_percent` evidence defined by `device-diagnostics-and-control`; accepted numeric zero SHALL render `0%`. Missing, malformed, stale-unusable, or otherwise unavailable accepted percentage SHALL render `Нет данных`. Presentation SHALL NOT derive percentage by guessing a device range, parse a localized/raw display string, use widget history/defaults, or reverse-convert displayed percentage into a device mutation target.

The shared presentation SHALL consume separate volume and typed mute-state authority from `device-diagnostics-and-control`; it SHALL NOT put strings such as `Muted` into a numeric/percentage slot or treat a displayed numeric value as a generic untagged mute state.

Modern room microphone-meter capability SHALL be resolved from the unified exact-model application registration and existing approved live binding before runtime sample availability is interpreted. For the current five-codec baseline:

```text
Huawei TE20          -> UNSUPPORTED
Huawei TE40          -> UNSUPPORTED
CloudLink Bar 310    -> SUPPORTED
CloudLink Box 310    -> SUPPORTED
Polycom RPG 310      -> UNSUPPORTED
```

For a `SUPPORTED` Bar/Box row, the meter SHALL consume only existing current accepted/live evidence already produced by the approved CloudLink meter lifecycle. Accepted numeric zero is available observed silence. When compatible current sample evidence is unavailable, the indicator remains visibly unavailable and its value meaning is `Нет данных`; this SHALL NOT be rendered as observed zero.

For an `UNSUPPORTED` TE20/TE40/Polycom row, the permanent meter slot SHALL visibly communicate `Не поддерживается` (or an exact equivalent non-color semantic state) and SHALL NOT start a timer, poll, handler/session acquisition, credential operation, or device request. A legacy standalone method, historical polling path, similarly named handler function, or runtime field SHALL NOT by itself make the modern room meter supported.

Microphone and speaker control affordances SHALL remain visibly present for every current codec model. This fixed presentation does not make the corresponding **network capability** supported. When the existing room interaction lock matrix otherwise permits input, an operation explicitly marked unsupported by unified capability authority MAY remain clickable only as the approved local-only informational affordance: it SHALL resolve before interaction admission and SHALL perform zero handler/session/credential/network activity. During an active/retiring lifecycle that locks state-changing controls, these common affordances SHALL obey that temporary lock.

Supported clicks SHALL publish only safe typed exact-row intents to application composition under `room-device-interaction-lifecycle`. Presentation SHALL NOT own a second pending timer/flag whose lifetime can outlive or disagree with the authoritative mutation/reconciliation lifecycle.

#### Scenario: CloudLink codec has current meter data

- **GIVEN** the exact current model is `CloudLink Bar 310` or `CloudLink Box 310`
- **AND** current accepted live meter evidence contains a valid numeric sample
- **WHEN** the Audio card renders
- **THEN** the microphone meter renders the approved normalized fill, including 0 fill for accepted numeric zero
- **AND** no presentation-owned meter request is started

#### Scenario: Supported CloudLink meter has no current sample

- **GIVEN** the exact current model is `CloudLink Bar 310` or `CloudLink Box 310`
- **AND** no compatible current accepted live meter sample is available
- **WHEN** the Audio card renders
- **THEN** the meter slot displays an unavailable state equivalent to `Нет данных`
- **AND** unavailable telemetry is not represented as numeric zero

#### Scenario: Baseline codec has no approved modern room meter capability

- **GIVEN** the exact current model is `Huawei TE20`, `Huawei TE40`, or `Polycom RPG 310`
- **WHEN** the Audio card renders
- **THEN** the microphone-level slot displays `Не поддерживается` or an equivalent explicit unsupported state
- **AND** rendering performs zero meter handler/session/credential/network activity

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

#### Scenario: Audio operation is unsupported for the exact model

- **GIVEN** the exact registration marks the clicked microphone/speaker network operation unsupported
- **AND** no existing interaction lock currently disables the common affordances
- **WHEN** the operator clicks its visible affordance
- **THEN** a local informational dialog equivalent to `Операция не поддерживается данной моделью` is shown
- **AND** the network capability remains unsupported
- **AND** no room network interaction is started
- **AND** current LIVE, cache and row authority remain unchanged

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

#### Scenario: More than three automatic-preview records are accepted

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

#### Scenario: Call log has no accepted automatic-preview data

- **WHEN** the current exact codec has no accepted automatic-preview records
- **THEN** the preview region displays `Нет данных`
- **AND** the `Развернуть` action remains present
- **AND** activating `Развернуть` still starts the same fresh serialized exact-row call-log acquisition

## ADDED Requirements

### Requirement: Codec call-history direction cue maps typed direction to the correct visible semantic role

Every modern room codec call-history record that renders a direction cue SHALL bind the cue to normalized `CallDirection` without vendor/model-specific reversal:

```text
INCOMING -> incoming semantic cue; non-color/accessibility meaning `Входящий`
OUTGOING -> outgoing semantic cue; non-color/accessibility meaning `Исходящий`
UNKNOWN  -> neutral semantic cue; non-color/accessibility meaning `Направление неизвестно`
```

The concrete icon glyph or Qt asset MAY vary with the shared theme, but the semantic role SHALL be testable independently of color and SHALL NOT be swapped between `INCOMING` and `OUTGOING`. Presentation SHALL NOT infer direction from localized source strings, peer formatting, icon color, or model identity.

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
- **WHEN** the direction cue renders
- **THEN** it uses a neutral semantic role equivalent to `Направление неизвестно`
- **AND** it does not falsely claim incoming or outgoing direction
