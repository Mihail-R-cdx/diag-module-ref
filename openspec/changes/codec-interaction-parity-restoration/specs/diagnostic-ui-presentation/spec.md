## MODIFIED Requirements

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
Громкость динамиков    [−] <accepted percentage/value or Нет данных> [+] [mute]
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

The modern room live-meter support matrix is:

| Exact model | `Микрофон (уровень)` |
| --- | --- |
| `Huawei TE20` | SUPPORTED from raw `MicValueIndex` evidence normalized `0..220 -> 0..100%` |
| `Huawei TE40` | SUPPORTED from raw `MicValueIndex` evidence normalized `0..220 -> 0..100%` |
| `CloudLink Bar 310` | SUPPORTED from approved Bar-specific microphone LIVE evidence |
| `CloudLink Box 310` | **UNSUPPORTED / DEFERRED in this change** |
| `Polycom RPG 310` | UNSUPPORTED |

For a supported meter, accepted numeric zero is observed silence/zero level and SHALL render as zero fill. If capability is supported but no compatible current sample is available, the slot SHALL render `Нет данных`; absence of a sample SHALL NOT be represented as observed zero. For an unsupported meter, the slot SHALL render `Не поддерживается` or an equivalent explicit non-color state.

Rendering any meter SHALL consume only accepted application-owned live evidence and SHALL NOT itself start a timer, poll, handler/session acquisition, credential operation, or device request.

For Huawei TE20/TE40, `get_live_audio_status` remains the live authority. `MicValueIndex` is raw monitor-audio evidence normalized from `0..220` to `0..100%` for `Микрофон (уровень)`. Accepted initial `monitor_mic_value` uses the same one-shot seed normalization only until a true LIVE sample is accepted. `SpeakerValueIndex` may remain compatibility evidence but SHALL NOT create a user-visible speaker LIVE capability or meter. The Audio card SHALL NOT additionally render standalone textual `Live ...` rows.

For exact `Huawei TE40`, accepted static numeric `mic1Value` in wire range `0..21` SHALL be presented in the `Громкость микрофона` value region as dB using `gain_db = mic1Value - 12`. Examples: wire `21 -> +9 dB`, `18 -> +6 dB`, `12 -> 0 dB`, `0 -> -12 dB`. This configured gain is independent from live `MicValueIndex` and microphone mute.

For TE40, `−` / `+` are network-supported controls. Each eligible click requests exactly `-1 dB` or `+1 dB`, bounded to `-12..+9 dB`, and enters the common exact-row mutation/reconciliation lifecycle through the approved TE40 `MIC1` binding. Presentation itself never builds the vendor full-state payload.

For `CloudLink Box 310`, microphone LIVE is explicitly unsupported in this change. Presentation SHALL show `Не поддерживается` for `Микрофон (уровень)`, SHALL NOT display stale/historical Box meter data as current, and SHALL NOT start or imply a Box LIVE lifecycle. A future reviewed change is required to restore Box microphone LIVE.

For TE20/RPG310, no synthetic numeric microphone gain SHALL be fabricated. CloudLink microphone gain remains network-unsupported. Speaker percentage/value presentation SHALL continue to consume only current accepted speaker evidence and SHALL not reverse-convert display percentage into mutation authority.

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
- **AND** the displayed percentage is not used as independent mutation authority

#### Scenario: Speaker volume has no accepted percentage evidence

- **WHEN** current exact-row accepted state has no usable `speaker_volume_percent`
- **THEN** the speaker configured-value region displays `Нет данных`
- **AND** the GUI does not manufacture `0%`, a prior value, or a guessed mapping

#### Scenario: Audio operation is unsupported for the exact model

- **GIVEN** the exact registration marks the clicked microphone/speaker network operation unsupported
- **AND** no existing interaction lock currently disables the common affordance
- **WHEN** the operator activates it
- **THEN** a local informational result equivalent to `Операция не поддерживается данной моделью` is shown, or the control remains disabled
- **AND** the network capability remains unsupported
- **AND** no room network interaction is started
- **AND** current LIVE, cache and row authority remain unchanged

#### Scenario: Huawei TE live audio uses microphone evidence only

- **GIVEN** the exact current model is `Huawei TE20` or `Huawei TE40`
- **AND** current accepted `get_live_audio_status` evidence contains valid raw microphone evidence
- **WHEN** the Audio card renders
- **THEN** `Микрофон (уровень)` reflects normalized `MicValueIndex` evidence
- **AND** no user-visible speaker live meter or duplicate textual `Live ...` row is rendered

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

### Requirement: Codec visual acceptance is measurable from repository-local checkpoints

Manual visual acceptance at `1440 x 900` in dark theme SHALL use these ten repository-local checkpoints; access to an external screenshot is unnecessary:

1. exactly five codec cards remain in the approved left-to-right order;
2. card width weights remain within the approved `23:17:18:25:17` ±4-point envelope;
3. card tops align and card heights/gaps/padding remain within the existing baseline ranges;
4. all card headers use the common icon/title anatomy and typography ranges;
5. `Состояние` and `Вызов и презентация` retain their approved permanent rows/order;
6. `Аудио` renders exactly `Микрофон (уровень) -> Громкость микрофона -> Громкость динамиков`, with no speaker LIVE meter or redundant textual `Live ...` rows, distinct live/static/mute semantics, TE40 configured MIC1 gain in dB, and Box 310 microphone LIVE explicitly unsupported;
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

## ADDED Requirements

### Requirement: Room codec presentation consumes exact-model normalized static microphone evidence

The common dashboard SHALL consume canonical static audio evidence from the exact-model parser/normalizer path. Presentation SHALL NOT parse vendor strings or infer capability from the mere presence of a widget.

| Exact model | Static microphone source | Canonical evidence | Presentation |
| --- | --- | --- | --- |
| `Huawei TE20` | authoritative mute evidence | `microphone_muted` | mute state; no fabricated numeric gain |
| `Huawei TE40` | numeric `mic1Value`; independent `MicSwitch`/mute evidence | numeric `microphone_volume`; independent `microphone_muted` | transform to `-12..+9 dB`; independent mute state |
| `CloudLink Bar 310` | diagnostic `mic_volume`; mute only if authoritative | numeric `microphone_volume`; optional independent mute | show accepted numeric value where present |
| `CloudLink Box 310` | existing non-LIVE diagnostic evidence only where already authoritative | canonical static fields only | may show accepted static evidence; SHALL NOT imply LIVE support |
| `Polycom RPG 310` | authoritative mute evidence | `microphone_muted` | mute state; no fabricated numeric gain |

#### Scenario: TE40 has numeric MIC1 gain and independent mute evidence

- **GIVEN** accepted exact-model normalization produced numeric `microphone_volume = 21` and independent `microphone_muted = false` for TE40
- **WHEN** the dashboard renders
- **THEN** the configured value is shown as `+9 dB` rather than `Нет данных`
- **AND** mute state remains independent
- **AND** numeric zero alone does not mean muted

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
