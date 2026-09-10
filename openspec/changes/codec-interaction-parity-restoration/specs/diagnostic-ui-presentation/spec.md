## MODIFIED Requirements

### Requirement: Diagnostic shell follows a self-contained modern room-oriented foundation contract

The desktop application SHALL present the user-visible title `Диагностический модуль` and SHALL use a card-based desktop layout with consistent semantic spacing, typography, borders, radii, standard Qt/device-class icons, and status styling. External screenshots are product-design inputs only; implementation and review SHALL be possible from this repository-local foundation contract without access to the original conversation images.

The baseline visual acceptance viewport SHALL be `1440 x 900` logical pixels. The layout SHALL remain usable at a minimum `1180 x 720` logical-pixel window; below the baseline, vertical scrolling or controlled card reflow MAY occur, but target-search, top Refresh, current selected-room cue, room/network peer tiles, common equipment accordion, and expanded current device content SHALL remain reachable.

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

Room mode SHALL place the outer room-summary peer tile and the outer network peer tile above the equipment accordion. At baseline width the two outer tiles SHALL have aligned tops and approximately peer weight with a width ratio between `0.9:1` and `1.1:1`; neither tile SHALL collapse into a narrow sidebar while the other occupies the full row. The accepted upper-tile block SHALL be about `186` logical pixels high (a tuning range of `178-194` is permitted). The left room-summary tile SHALL have no separate visible heading `Информация о комнате`, section icon, SectionCard header, header spacer, or header chrome; its room-information body is its sole visible content. The right network tile SHALL have no separate visible heading, icon, dynamic switch-count title, header spacing, or SectionCard header; its network table/tree is its sole visible content.

The foundation contract itself does not define final family-specific visual geometry for Audio DSP, Matrix/IN1804, codec, or PDU expanded content; such geometry is owned only by dedicated reviewed follow-up OpenSpec changes. MIH-10 and MIH-11 are those approved follow-ups for Audio DSP and Matrix/IN1804 respectively; codec and PDU redesign remain deferred. The common shell redesign SHALL NOT make Qt widget state authoritative for target identity, credentials, request generation, handler/session ownership, or device I/O.

The accepted shell uses a transparent/common diagnostic-tree background with card-like equipment surfaces. Its compact accordion has no visible tree column header and no visible trailing common overflow/action placeholder. A hidden data-bearing or accessibility surface MAY retain cycle health, but the shell SHALL NOT insert a second visible global-cycle line between the upper tiles and the accordion. Hover, repaint, resize, theme switch, reflow, and scrolling remain presentation-only and SHALL start no device I/O or change authority.

#### Scenario: Room shell is rendered at baseline size

- **WHEN** room mode has an authoritative current room at the baseline viewport
- **THEN** the headerless room-summary tile and headerless network table-only tile appear side by side above the compact equipment accordion with peer visual weight
- **AND** the accepted common spacing/typography/icon scale and taller upper-tile geometry are applied
- **AND** device/network authority remains outside the presentation widgets

#### Scenario: Minimum supported window remains usable

- **WHEN** the application is shown at `1180 x 720` logical pixels
- **THEN** target-search, selected-room cue when present, top Refresh, room/network peer tiles, equipment accordion, and current expanded device content remain reachable through controlled reflow/scrolling
- **AND** no target or device authority changes merely because layout reflows

### Requirement: Network card preserves all available canonical connection evidence

The headerless right network peer tile SHALL use a compact summary tree/table with columns exactly `Коммутатор (IP)`, `Порты`, and `Подключено устройств`. It SHALL contain no separate visible `Сетевые подключения` title, dynamic `Сетевые подключения (N коммутаторов)` title, network-card icon, SectionCard header, or header spacer. The table/tree SHALL be the tile's sole visible content and fill all available area within the preserved outer peer tile; ordinary SectionCard inner padding or margins SHALL NOT reduce that table/tree area. Rendering, hover, disclosure, child-row display, and local table interaction SHALL be presentation-only and SHALL perform no device network I/O.

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

The summary row SHALL use a safe generic name equivalent to `SW (<IP>)` unless safe unique current canonical display evidence establishes a user-friendly name. The displayed ports summary and record count SHALL not be persisted as canonical data and SHALL not be used as switch identity, routing, or device-topology authority.

Each known-switch summary row SHALL be a real disclosure parent with one visual child per current canonical room-equipment record attached to that exact switch, ordered by canonical `record_id`. A child SHALL display safe current equipment identity in the first column and that exact record's canonical `switch_port` or `Нет данных` in the Ports column; the parent remains the owner of the aggregate count. Child rows are read-only presentation of existing canonical records and SHALL NOT become target/routing/topology authority or start device I/O.

User expansion/collapse of a known-switch row SHALL update presentation-local disclosure state only. That state SHALL survive background refresh/re-render while the exact `RoomDiagnosticSessionIdentity` remains unchanged and the switch row still exists. Background refresh SHALL NOT independently expand or collapse a current switch row. A different room/session identity or explicit presentation clear SHALL reset prior disclosure state rather than restore it into the new context. The default for a newly encountered known-switch row in a new presentation context SHALL be collapsed.

For a record-bound `Коммутатор не определён` row with a known canonical port, the `Порты` cell SHALL display that exact port and count `1`. Such rows SHALL remain ungrouped and need not expose disclosure children because no authoritative common switch identity exists.

If the room contains no presentable switch-IP or port evidence at all, the table/tree SHALL show a safe empty state equivalent to `Нет данных о сетевых подключениях` rather than an invented topology.

The confirmed product decision that room switches with zero attached canonical equipment are not implemented remains unchanged. Current schema v4 cannot authoritatively establish such a switch, so implementation SHALL NOT fabricate it merely to provide an empty disclosure parent.

#### Scenario: Network tile renders table without a title

- **WHEN** the right network peer tile renders
- **THEN** no visible `Сетевые подключения` text, dynamic switch-count title, network-card icon, or separate header is rendered
- **AND** the network table/tree is visible
- **AND** its column headers are exactly `Коммутатор (IP)`, `Порты`, and `Подключено устройств`

#### Scenario: Network table fills the peer tile

- **WHEN** the right network peer tile renders at an accepted layout size
- **THEN** the table/tree fills its available outer-tile area
- **AND** no header spacer or ordinary SectionCard inner padding reduces that area

#### Scenario: Room summary has no separate title chrome

- **WHEN** the upper peer tiles render
- **THEN** the left room-summary tile renders no visible `Информация о комнате` text, section icon, SectionCard header, header spacer, or header chrome
- **AND** its room-information body remains visible without becoming full-bleed against the preserved outer tile border
- **AND** the right network tile does not add a separate heading

#### Scenario: Network data and disclosure semantics remain unchanged

- **GIVEN** current canonical switch evidence and same-context disclosure state exist
- **WHEN** the table-only network tile renders or re-renders
- **THEN** grouping, canonical `switch_ip_address`/`switch_port` evidence, counts, child rows, ordering, unknown-switch behavior, empty-state semantics, and disclosure restoration retain their existing contract
- **AND** no visual simplification changes topology or target authority

#### Scenario: Network tile rendering starts no I/O

- **WHEN** the table-only network tile renders, reflows, repaints, or restores disclosure state
- **THEN** it starts zero device/network I/O

#### Scenario: Two room devices share a switch

- **GIVEN** two room records contain the same non-null canonical `switch_ip_address`
- **AND** their canonical ports are `Gi1/0/5` and `Gi1/0/6`
- **WHEN** the network summary renders
- **THEN** one switch summary row is shown for that IP
- **AND** its Port summary displays `Gi1/0/5, Gi1/0/6` and its device count is `2`
- **AND** expanding that row reveals exactly those two canonical equipment children in deterministic `record_id` order
- **AND** neither displayed summary nor children become canonical switch/target state

#### Scenario: Parent port summary de-duplicates repeated child evidence

- **GIVEN** several canonical records under one exact switch IP contain the same non-null canonical port text
- **WHEN** the network summary renders
- **THEN** the repeated port appears once according to first canonical `record_id` occurrence
- **AND** each canonical record may still appear as its own disclosed visual child
- **AND** the summary does not replace the per-record canonical evidence

#### Scenario: Known port with missing switch IP is not lost

- **GIVEN** one room record has null `switch_ip_address` and non-null canonical `switch_port`
- **WHEN** the network card renders
- **THEN** the known port remains visible under a `Коммутатор не определён` record-bound row with count `1`
- **AND** no switch IP, shared switch identity, or fictitious disclosure group is guessed

#### Scenario: User disclosure survives same-context refresh

- **GIVEN** the operator has manually expanded or collapsed a known-switch summary row
- **AND** the current `RoomDiagnosticSessionIdentity` remains unchanged
- **WHEN** background refresh/re-render rebuilds current network evidence
- **THEN** the rebuilt current switch row restores that user disclosure state
- **AND** refresh itself does not choose the expanded/collapsed state
- **AND** restoration performs zero device I/O

#### Scenario: Empty switch state is explicitly out of current scope

- **GIVEN** the confirmed product scope defers room switches with zero attached canonical equipment
- **WHEN** no canonical room record/evidence establishes an unattached switch node
- **THEN** the GUI does not fabricate a switch solely to display an empty disclosure group
- **AND** acceptance does not require that state in this change

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
| `Huawei TE40` | SUPPORTED from `WEB_GetCurrentAudioParam`: `max(valid MicValueIndex + valid mic<N>ValueIndex + valid micArray<N>_<NN>ValIdx + valid rcaLInValueIndex + valid rcaRInValueIndex)` evidence normalized `0..220 -> 0..100%` |
| `Huawei TE50` | SUPPORTED by exact-model reuse of the approved TE40 `WEB_GetCurrentAudioParam` contract; pending TE50 hardware acceptance |
| `CloudLink Bar 310` | SUPPORTED from approved Bar-specific microphone LIVE evidence |
| `CloudLink Box 310` | **UNSUPPORTED / DEFERRED in this change** |
| `Polycom RPG 310` | UNSUPPORTED |

For a supported meter, accepted numeric zero is observed silence/zero level and SHALL render as zero fill. If capability is supported but no compatible current sample is available, the slot SHALL render `Нет данных`; absence of a sample SHALL NOT be represented as observed zero. For an unsupported meter, the slot SHALL render `Не поддерживается` or an equivalent explicit non-color state.

Rendering any meter SHALL consume only accepted application-owned live evidence and SHALL NOT itself start a timer, poll, handler/session acquisition, credential operation, or device request.

For Huawei TE20/TE40/TE50, `get_live_audio_status` remains the live authority. TE20 uses raw `MicValueIndex` normalized from `0..220` to `0..100%` for `Микрофон (уровень)`. TE40 and exact-model TE50 use the TE40 `WEB_GetCurrentAudioParam` extractor defined by `device-diagnostics-and-control`: `max(valid MicValueIndex + valid mic<N>ValueIndex + valid micArray<N>_<NN>ValIdx + valid rcaLInValueIndex + valid rcaRInValueIndex)`, then the same normalization. Accepted initial `monitor_mic_value` uses that same current-audio extractor/normalization only until a true LIVE sample is accepted. `SpeakerValueIndex` may remain compatibility evidence but SHALL NOT create a user-visible speaker LIVE capability or meter. The Audio card SHALL NOT additionally render standalone textual `Live ...` rows.

For exact `Huawei TE40` and `Huawei TE50`, accepted static numeric `mic1Value` in wire range `0..21` SHALL be presented in the `Громкость микрофона` value region as dB using `gain_db = mic1Value - 12`. Examples: wire `21 -> +9 dB`, `18 -> +6 dB`, `12 -> 0 dB`, `0 -> -12 dB`. This configured gain is independent from live microphone evidence and microphone mute.

For TE40 and TE50, `−` / `+` are network-supported controls. Each eligible click requests exactly `-1 dB` or `+1 dB`, bounded to `-12..+9 dB`, and enters the common exact-row mutation/reconciliation lifecycle through the approved TE40 `MIC1` binding reused by exact TE50. Presentation itself never builds the vendor full-state payload.

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

#### Scenario: Huawei TE live audio uses model-specific microphone evidence only

- **GIVEN** the exact current model is `Huawei TE20`, `Huawei TE40`, or `Huawei TE50`
- **AND** current accepted `get_live_audio_status` evidence contains valid raw microphone evidence
- **WHEN** the Audio card renders
- **THEN** TE20 reflects normalized `MicValueIndex` evidence and TE40/TE50 reflect the normalized approved TE40 aggregate under their own exact model identities
- **AND** no user-visible speaker live meter or duplicate textual `Live ...` row is rendered

### Requirement: Room summary card derives busy indication only from typed codec call activity

The room-summary card SHALL permanently include labelled presentation slots for `Название комнаты`, `Адрес комнаты`, `Гарантия`, and `Занятость`, plus VIP. Current canonical `room_name`, `room_address`, and `room_vip` SHALL use the room metadata authority defined by `room-equipment-diagnostics`.

The outer room-summary peer tile SHALL retain its container but render no separate `Информация о комнате` title, section icon, SectionCard header, header spacer, or header chrome. Its first visible content row SHALL be `Название комнаты`; `Адрес комнаты`, `Гарантия`, and `Занятость` SHALL follow in that order. VIP remains associated with the room-name presentation. The body MAY retain ordinary non-zero content padding and SHALL NOT be made full-bleed against the outer tile border merely because the header is absent.

The confirmed temporary product decision for this change is that the permanent warranty row SHALL always render exactly `Гарантия: Нет гарантии`. This is presentation-only placeholder text: it SHALL NOT fabricate or publish canonical warranty evidence, set a session warranty field, change the inventory schema, infer warranty from unrelated inventory columns, timestamps, device data, room text, or local UI state, or start an external lookup/device or network I/O. Future real warranty integration is tracked as Linear `MIH-28` — `Room diagnostics: заменить заглушку «Нет гарантии» реальными данными` — and requires a separately reviewed authoritative source and canonical semantics before implementation.

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

#### Scenario: Warranty placeholder is always visible and fixed

- **WHEN** the room summary renders with any room evidence state
- **THEN** its warranty row renders exactly `Гарантия: Нет гарантии`
- **AND** it never renders `Нет данных`, `—`, or `Unknown`

#### Scenario: Warranty placeholder does not create authority or I/O

- **WHEN** the room summary renders or refreshes the warranty placeholder
- **THEN** no canonical warranty field, session warranty field, inventory-schema change, inference, lookup, device request, or network I/O is created
- **AND** room name, address, VIP, and occupancy retain their existing independent authority and behavior

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

### Requirement: Codec call-history direction cue maps typed direction to the correct visible semantic role

Every modern room codec call-history record that renders a direction cue SHALL bind the cue to normalized `CallDirection` without vendor/model-specific reversal:

```text
INCOMING -> visible text `Входящий`; existing incoming semantic cue
OUTGOING -> visible text `Исходящий`; existing outgoing semantic cue
UNKNOWN  -> neutral cue MAY remain, but no visible direction text or title
```

The concrete icon glyph or Qt asset MAY vary with the shared theme, but the semantic role SHALL be testable independently of color and SHALL NOT be swapped between `INCOMING` and `OUTGOING`. `UNKNOWN` SHALL remain the typed normalized direction; presentation SHALL NOT infer direction from localized source strings, peer formatting, call result, record position, icon color, model identity, or other GUI heuristics.

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
- **WHEN** a room-preview call row renders
- **THEN** it renders no visible direction title, including `Направление неизвестно`, `Входящий`, or `Исходящий`
- **AND** it leaves no empty direction-text row or vertical gap
- **AND** a neutral direction icon MAY remain only when it does not imply incoming or outgoing direction
- **AND** the normalized direction remains `UNKNOWN`

## ADDED Requirements

### Requirement: Room codec presentation consumes exact-model normalized static microphone evidence

The common dashboard SHALL consume canonical static audio evidence from the exact-model parser/normalizer path. Presentation SHALL NOT parse vendor strings or infer capability from the mere presence of a widget.

| Exact model | Static microphone source | Canonical evidence | Presentation |
| --- | --- | --- | --- |
| `Huawei TE20` | authoritative mute evidence | `microphone_muted` | mute state; no fabricated numeric gain |
| `Huawei TE40` | numeric `mic1Value`; independent `MicSwitch`/mute evidence | numeric `microphone_volume`; independent `microphone_muted` | transform to `-12..+9 dB`; independent mute state |
| `Huawei TE50` | approved TE40 `mic1Value`; independent `MicSwitch`/mute evidence | numeric `microphone_volume`; independent `microphone_muted` | transform to `-12..+9 dB`; independent mute state; pending TE50 hardware acceptance |
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

### Requirement: Supported codec microphone LIVE meters use a 700 ms serialized scheduling target

For the currently supported room microphone LIVE meters only — exact `Huawei TE20`, `Huawei TE40`, `Huawei TE50`, and `CloudLink Bar 310` — application/composition scheduling SHALL target `700 ms` between completed sample cycles. This is a nominal scheduling target, not a paint-rate guarantee: rendering remains a consumer of accepted evidence and SHALL create zero new meter I/O.

Each exact-model LIVE owner SHALL preserve immutable current row/generation/credential authority and SHALL permit at most one sample operation in flight. A cycle that remains in flight at its nominal next point SHALL not be overlapped; the next cycle may start only after its allowed completion boundary and a fresh currentness check. Late, stale, cancelled, superseded, or retired work SHALL remain powerless under the existing lifecycle.

This requirement changes neither vendor protocol command/request semantics nor the support matrix. Exact `CloudLink Box 310` remains `UNSUPPORTED / DEFERRED` with no meter timer/context/request; `Polycom RPG 310` remains unsupported. It SHALL NOT change Matrix, DMP, PDU, general refresh, call-log, authentication, or unrelated timer scheduling.

#### Scenario: Supported codec LIVE schedules after a short completed sample

- **GIVEN** an exact supported codec microphone LIVE sample completes while its row remains current
- **WHEN** the owner schedules the next sample
- **THEN** it targets `700 ms` after the completed cycle
- **AND** no second sample overlaps the completed or still-in-flight cycle

#### Scenario: Unsupported or unrelated timer remains outside codec LIVE cadence

- **WHEN** exact `CloudLink Box 310`, `Polycom RPG 310`, Matrix, DMP, PDU, general refresh, call-log, authentication, or another unrelated timer is active
- **THEN** this requirement starts no new microphone LIVE context for unsupported codecs
- **AND** it changes no unrelated timer cadence or network behavior
