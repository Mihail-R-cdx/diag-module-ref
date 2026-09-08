## MODIFIED Requirements

### Requirement: Codec audio card distinguishes supported live-meter evidence from unsupported capability

The `Аудио` card SHALL permanently contain, in this exact order:

```text
Микрофон (уровень)     <horizontal live level indicator or explicit unsupported/no-data state>
Динамик (уровень)      <horizontal live level indicator or explicit unsupported/no-data state>
Громкость микрофона    [−] <accepted numeric/static value or Нет данных> [+] [mute]
Громкость динамиков    [−] <accepted percentage/value or Нет данных> [+] [mute]
```

The two level rows are **live activity evidence**, not configured volume/gain settings. The two control rows are **static/configured/readback evidence**, not live activity. Presentation SHALL NOT overwrite one authority with the other.

At baseline, each level label SHALL precede a horizontal indicator occupying the available card-body width. A visible supported meter bar SHALL use approximately `8-12 px` height. The microphone and speaker meter blocks SHALL be separated by approximately `6-10 px`; the control rows SHALL follow with approximately `8-12 px` vertical separation. Existing button-size rules remain:

```text
minus / plus button target size       28-34 px square
mute affordance target height          28-34 px
mute affordance target width           44-64 px
numeric/no-data value region           at least 38 px, centered/aligned
inter-control gap                       4-8 px
```

The modern room live-meter support matrix is:

| Exact model | `Микрофон (уровень)` | `Динамик (уровень)` |
| --- | --- | --- |
| `Huawei TE20` | SUPPORTED from accepted `MicValueIndex` live evidence | SUPPORTED from accepted `SpeakerValueIndex` live evidence |
| `Huawei TE40` | SUPPORTED from accepted `MicValueIndex` live evidence | SUPPORTED from accepted `SpeakerValueIndex` live evidence |
| `CloudLink Bar 310` | SUPPORTED from approved CloudLink microphone LIVE evidence | UNSUPPORTED |
| `CloudLink Box 310` | SUPPORTED capability; accepted sample depends on the separately approved Box live parser contract | UNSUPPORTED |
| `Polycom RPG 310` | UNSUPPORTED | UNSUPPORTED |

For a supported meter, an accepted numeric zero is observed silence/zero level and SHALL render as zero fill. If the capability is supported but no compatible current sample is available, the slot SHALL render `Нет данных`; absence of a sample SHALL NOT be represented as observed zero. For an unsupported meter, the slot SHALL render `Не поддерживается` or an equivalent explicit non-color state.

Rendering any meter SHALL consume only accepted application-owned live evidence and SHALL NOT itself start a timer, poll, handler/session acquisition, credential operation, or device request.

For Huawei TE20/TE40, `get_live_audio_status` remains the live authority. `MicValueIndex` feeds `Микрофон (уровень)` and `SpeakerValueIndex` feeds `Динамик (уровень)`. The Audio card SHALL NOT additionally render standalone textual rows named `Live микрофон` or `Live динамик` for the same evidence.

For exact `Huawei TE40`, accepted static numeric `micValue` SHALL be presented in the `Громкость микрофона` value region as canonical `microphone_volume`, independently from live `MicValueIndex` and independently from microphone mute. While the exact TE40 gain setter/range/step contract remains unapproved, the numeric value is read-only evidence: visible `−` / `+` gain affordances SHALL remain disabled or local-only before room interaction admission and SHALL perform zero gain network I/O. The microphone mute affordance may remain supported from its separate exact-model capability.

For TE20/RPG310, no synthetic numeric microphone gain SHALL be fabricated. CloudLink microphone gain remains network-unsupported. Speaker percentage/value presentation SHALL continue to consume only current accepted speaker evidence and SHALL not reverse-convert display percentage into mutation authority.

Microphone and speaker fixed control affordances remain subject to the common room lock matrix. A network operation marked unsupported by unified capability authority may be visible only as the approved disabled/local informational affordance and SHALL resolve before handler/session/network acquisition.

#### Scenario: CloudLink codec has current meter data

- **GIVEN** the exact current model is `CloudLink Bar 310` or `CloudLink Box 310`
- **AND** current accepted live microphone evidence contains a valid numeric sample under that model's approved live parser
- **WHEN** the Audio card renders
- **THEN** `Микрофон (уровень)` renders the approved normalized fill, including zero fill for accepted numeric zero
- **AND** `Динамик (уровень)` renders `Не поддерживается` for that CloudLink model
- **AND** no presentation-owned meter request is started

#### Scenario: Supported CloudLink meter has no current sample

- **GIVEN** the exact current model is `CloudLink Bar 310` or `CloudLink Box 310`
- **AND** no compatible current accepted live microphone sample is available
- **WHEN** the Audio card renders
- **THEN** `Микрофон (уровень)` displays an unavailable state equivalent to `Нет данных`
- **AND** unavailable telemetry is not represented as numeric zero

#### Scenario: Baseline codec has no approved modern room meter capability

- **GIVEN** the exact current model is `Polycom RPG 310`
- **WHEN** the Audio card renders
- **THEN** both live-level slots display `Не поддерживается` or equivalent explicit unsupported states
- **AND** rendering performs zero meter handler/session/credential/network activity

#### Scenario: Speaker volume has accepted percentage evidence

- **GIVEN** current exact-row accepted state contains `speaker_volume_percent = 42`
- **WHEN** the speaker control row renders
- **THEN** `42%` appears between `−` and `+`
- **AND** that configured speaker value remains distinct from the separate `Динамик (уровень)` live meter
- **AND** the displayed percentage is not used as independent mutation authority

#### Scenario: Speaker volume has no accepted percentage evidence

- **WHEN** current exact-row accepted state has no usable `speaker_volume_percent`
- **THEN** the speaker configured-value region displays `Нет данных`
- **AND** the GUI does not manufacture `0%`, a prior value, or a guessed mapping
- **AND** any supported live speaker meter remains a separate authority

#### Scenario: Audio operation is unsupported for the exact model

- **GIVEN** the exact registration marks the clicked microphone/speaker network operation unsupported
- **AND** no existing interaction lock currently disables the common affordance
- **WHEN** the operator activates it
- **THEN** a local informational result equivalent to `Операция не поддерживается данной моделью` is shown, or the control remains disabled
- **AND** the network capability remains unsupported
- **AND** no room network interaction is started
- **AND** current LIVE, cache and row authority remain unchanged

#### Scenario: Huawei TE live audio uses both meter slots

- **GIVEN** the exact current model is `Huawei TE20` or `Huawei TE40`
- **AND** current accepted `get_live_audio_status` evidence contains valid microphone and speaker live values
- **WHEN** the Audio card renders
- **THEN** `Микрофон (уровень)` reflects `MicValueIndex`-derived evidence
- **AND** `Динамик (уровень)` reflects `SpeakerValueIndex`-derived evidence
- **AND** no duplicate textual `Live микрофон` / `Live динамик` rows are rendered

#### Scenario: TE40 static microphone value is distinct from live level

- **GIVEN** TE40 has accepted static `microphone_volume = 7`
- **AND** current live `MicValueIndex` evidence is also available
- **WHEN** the Audio card renders
- **THEN** the configured microphone value region displays `7`
- **AND** `Микрофон (уровень)` reflects only the live sample
- **AND** neither value overwrites or reclassifies the other

### Requirement: Codec visual acceptance is measurable from repository-local checkpoints

Manual visual acceptance at `1440 x 900` in dark theme SHALL use these ten repository-local checkpoints; access to an external screenshot is unnecessary:

1. exactly five codec cards remain in the approved left-to-right order;
2. card width weights remain within the approved `23:17:18:25:17` ±4-point envelope;
3. card tops align and card heights/gaps/padding remain within the existing baseline ranges;
4. all card headers use the common icon/title anatomy and typography ranges;
5. `Состояние` and `Вызов и презентация` retain their approved permanent rows/order;
6. `Аудио` renders exactly the new four-part order `Микрофон (уровень) -> Динамик (уровень) -> Громкость микрофона -> Громкость динамиков`, with two live meter slots, no redundant textual `Live ...` rows, and distinct live/static/mute semantics;
7. `Журнал вызовов` preserves three-row preview density/anatomy and places `Развернуть` after the preview;
8. `Действия` retains exactly two vertically stacked full-width actions in the approved order/sizing;
9. state/call cards remain dot-free with right-aligned values; call/presentation use normalized `Да`/`Нет`, and registration uses the required semantic icon/neutral unavailable state;
10. light theme preserves the same geometry/order, including both Audio live-meter slots, without starting device I/O.

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
| `Huawei TE40` | numeric `micValue`; independent `MicSwitch`/mute evidence | numeric `microphone_volume`; independent `microphone_muted` | show numeric configured value plus independent mute state |
| `CloudLink Bar 310` | diagnostic `mic_volume`; mute only if authoritative | numeric `microphone_volume`; optional independent mute | show accepted numeric value where present |
| `CloudLink Box 310` | diagnostic `mic_volume`; mute only if authoritative | numeric `microphone_volume`; optional independent mute | show accepted numeric value where present |
| `Polycom RPG 310` | authoritative mute evidence | `microphone_muted` | mute state; no fabricated numeric gain |

#### Scenario: TE40 has numeric micValue and independent mute evidence

- **GIVEN** accepted exact-model normalization produced numeric `microphone_volume` and independent `microphone_muted` for TE40
- **WHEN** the dashboard renders
- **THEN** the numeric configured value is not shown as `Нет данных`
- **AND** mute state remains independent
- **AND** numeric zero alone does not mean muted

### Requirement: Automatic codec call preview presents up to three generation-current records without explicit opening

For a call-log-capable exact codec row, application/lifecycle authority SHALL acquire the initial preview only at the boundary defined by `room-device-interaction-lifecycle`: the entire automatic room cycle is terminal, the exact row is current/expanded/connected/usable, and that exact row/generation has no terminal initial-preview attempt yet.

The presentation SHALL render at most the three newest normalized records from accepted initial-preview state. It SHALL NOT initiate the network request itself. If fewer than three calls exist, every available call is shown. If the initial attempt ends with no data/ordinary failure, a neutral `Нет данных` state may be shown.

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

### Requirement: TE40 camera presentation accepts one normalized camera record

A valid TE40 camera result derived from exactly one returned camera-list entry SHALL be presented as known camera state/model evidence when available. The UI SHALL NOT render `Нет данных` solely because the parser received fewer than two camera entries.

#### Scenario: TE40 has one active camera

- **GIVEN** exact-model parsing accepted one active TE40 camera record and optional model evidence
- **WHEN** the `Камера` field renders
- **THEN** that accepted evidence is shown
- **AND** absence of a second camera entry does not force `Нет данных`
