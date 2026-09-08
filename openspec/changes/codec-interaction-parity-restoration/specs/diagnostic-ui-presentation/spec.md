## ADDED Requirements

### Requirement: Room codec presentation consumes exact-model normalized audio evidence

The common room codec dashboard SHALL consume canonical audio evidence produced by the exact-model parser/normalizer path. It SHALL NOT require model-specific vendor/display-string parsing in the presentation layer and SHALL NOT treat absence of one universal numeric field as proof that all microphone evidence is unavailable.

The normalization contract is:

| Exact model | Existing authoritative source evidence | Required canonical accepted evidence | Required presentation |
| --- | --- | --- | --- |
| `Huawei TE20` | `mic_mute` / equivalent typed parser evidence | `microphone_muted: bool` when known; no fabricated numeric `microphone_volume` | show mute/unmute state; numeric microphone gain remains unavailable in this change |
| `Huawei TE40` | numeric `micValue` plus independent `MicSwitch` / equivalent mute evidence | `microphone_volume: number` from authoritative `micValue`; `microphone_muted: bool` independently when mute evidence is known | show numeric microphone gain and independent mute state; never collapse gain into mute semantics |
| `CloudLink Bar 310` | diagnostic audio `mic_volume`; `mic_mute` only where actually returned | `microphone_volume: number` from authoritative `mic_volume`; `microphone_muted` only from authoritative mute evidence | show numeric current microphone value when received; do not show `Нет данных` merely because the source field was named `mic_volume` |
| `CloudLink Box 310` | diagnostic audio `mic_volume`; `mic_mute` only where actually returned | `microphone_volume: number` from authoritative `mic_volume`; `microphone_muted` only from authoritative mute evidence | show numeric current microphone value when received; do not show `Нет данных` merely because the source field was named `mic_volume` |
| `Polycom RPG 310` | authoritative microphone mute evidence (`mic_mute` / normalized equivalent) | `microphone_muted: bool`; no fabricated numeric `microphone_volume` | show mute/unmute state; numeric microphone gain is unavailable by design |

For all five models, authoritative numeric speaker evidence SHALL normalize to `speaker_volume`. Percentage presentation SHALL derive only from the exact-model speaker range in the normative capability matrix; Polycom's button step remains `2` even though its displayed percentage is based on `0..100`.

#### Scenario: CloudLink parser receives microphone volume

- **GIVEN** exact model is CloudLink Bar 310 or CloudLink Box 310
- **AND** the real parser/normalizer path receives authoritative numeric `mic_volume`
- **WHEN** the room snapshot is accepted
- **THEN** it contains numeric canonical `microphone_volume`
- **AND** the common dashboard renders that value rather than `Нет данных`

#### Scenario: TE20 has microphone mute evidence but no approved gain

- **GIVEN** exact model is Huawei TE20
- **AND** authoritative mute evidence is known
- **AND** no independent approved numeric microphone-gain capability exists
- **WHEN** the room snapshot is accepted and rendered
- **THEN** canonical `microphone_muted` is projected as microphone state
- **AND** the application does not fabricate numeric `microphone_volume`
- **AND** absence of numeric gain does not erase the known microphone state

#### Scenario: TE40 has independent microphone gain and mute evidence

- **GIVEN** exact model is Huawei TE40
- **AND** authoritative audio status contains numeric `micValue`
- **AND** authoritative mute evidence is known independently
- **WHEN** the room snapshot is accepted and rendered
- **THEN** numeric `microphone_volume` is displayed as the current microphone-gain setting
- **AND** `microphone_muted` is displayed/controlled as a separate state
- **AND** a numeric value of `0` does not by itself mean muted
- **AND** the dashboard does not show `Нет данных` when authoritative `micValue` was accepted

#### Scenario: Polycom has mute evidence but no numeric microphone gain

- **GIVEN** exact model is Polycom RPG 310
- **AND** authoritative microphone mute evidence is known
- **WHEN** the dashboard renders
- **THEN** the mute state is shown
- **AND** no synthetic numeric microphone gain is displayed

### Requirement: Microphone normalization regression starts before the canonical snapshot

Regression coverage for static microphone presentation SHALL exercise the actual exact-model parser/normalizer/session path from transport-edge data into the accepted room snapshot and then into the common dashboard.

A test that manually constructs an accepted snapshot already containing `microphone_volume` or `microphone_muted` MAY supplement coverage but SHALL NOT be the sole regression evidence for this defect family.

#### Scenario: CloudLink transport-edge fake publishes old compatibility field

- **GIVEN** a deterministic transport-edge fake returns the same authoritative `mic_volume` shape consumed by the CloudLink parser
- **WHEN** the actual parser/normalizer and room acceptance path execute
- **THEN** canonical `microphone_volume` reaches the dashboard
- **AND** the test does not inject `microphone_volume` directly into the snapshot

#### Scenario: TE40 transport-edge fake publishes micValue and MicSwitch

- **GIVEN** a deterministic TE40 transport-edge fake returns the actual audio-status fields used by the handler, including numeric `micValue` and independent `MicSwitch`
- **WHEN** the actual parser/normalizer and room acceptance path execute
- **THEN** canonical numeric `microphone_volume` and independent `microphone_muted` reach the dashboard
- **AND** the test does not inject those canonical fields directly into the snapshot

### Requirement: Room codec presentation reflects exact-model live telemetry

CloudLink Bar 310 and Box 310 SHALL display their approved live microphone meter when a current accepted live sample is available. Huawei TE20 and TE40 SHALL display the model-specific live microphone and speaker evidence restored from their proven `get_live_audio_status` behavior. Polycom RPG 310 SHALL NOT display a fabricated live meter when no approved live-meter capability exists.

Static microphone gain/mute evidence and live microphone/audio telemetry are separate authorities: a live sample SHALL NOT silently overwrite static accepted control/readback evidence, and call-log preview bookkeeping SHALL NOT clear a current live sample.

For Huawei TE20/TE40, the canonical live microphone evidence derived from `MicValueIndex` SHALL feed the existing microphone-level meter presentation, and canonical live speaker evidence derived from `SpeakerValueIndex` SHALL feed a dedicated speaker-level meter. The dashboard SHALL NOT render redundant standalone textual rows named `Live микрофон` or `Live динамик` when those same live values are available to the meters.

The labels SHALL distinguish configuration/control from activity/level evidence. For TE40 in particular, `Громкость микрофона` represents the numeric gain setting derived from `micValue`, while `Микрофон (уровень)` represents live input activity derived from `MicValueIndex`. Speaker control volume and `Динамик (уровень)` are likewise distinct.

#### Scenario: CloudLink live sample arrives

- **GIVEN** current exact model is CloudLink Bar 310 or Box 310
- **AND** an accepted current live microphone sample is available
- **WHEN** the dashboard renders
- **THEN** the microphone meter reflects that sample
- **AND** unrelated call-log preview state does not clear or replace it

#### Scenario: TE20 or TE40 live audio arrives

- **GIVEN** current exact model is Huawei TE20 or Huawei TE40
- **AND** current `get_live_audio_status` evidence has been accepted
- **WHEN** the dashboard renders
- **THEN** `Микрофон (уровень)` reflects `MicValueIndex`-derived evidence
- **AND** `Динамик (уровень)` reflects `SpeakerValueIndex`-derived evidence
- **AND** the dashboard does not label this proven behavior unsupported solely because it is not `cloudlink_room_live`
- **AND** redundant textual `Live микрофон` / `Live динамик` rows are absent

#### Scenario: TE40 static gain and live microphone level coexist

- **GIVEN** TE40 has accepted static `microphone_volume = 7`
- **AND** a current live `MicValueIndex` sample is also accepted
- **WHEN** the dashboard renders
- **THEN** the numeric gain control continues to display `7`
- **AND** the microphone-level meter reflects the live sample independently
- **AND** neither presentation overwrites the other's authority

#### Scenario: Polycom has no approved live meter

- **GIVEN** current exact model is Polycom RPG 310
- **AND** no approved live microphone/audio capability exists
- **WHEN** the dashboard renders
- **THEN** no fabricated live level is presented as device evidence

### Requirement: Automatic room codec preview displays the three newest calls after initial connection

For every supported exact codec model whose registration advertises call-log capability, the common room codec presentation SHALL expose an inline preview containing at most the three newest normalized call records acquired by the mandatory initial call-history lifecycle. The preview SHALL be ready from accepted application state after the initial acquisition reaches terminal success and SHALL NOT require the operator to press `Развернуть` merely to obtain those three records.

The presentation SHALL NOT initiate the device read itself. It only renders the accepted initial preview dataset owned by the application/lifecycle layer. Records SHALL follow the existing normalized newest-first chronology contract; when fewer than three records exist, all available records are shown. A terminal no-data/failure outcome may render a neutral unavailable/empty state, but the application SHALL have attempted the required initial acquisition before first LIVE start for that generation/current row.

#### Scenario: Initial call preview succeeds

- **GIVEN** a supported current codec completes its mandatory initial call-history acquisition with at least three normalized records
- **WHEN** the room codec card is rendered
- **THEN** the three newest records are visible inline without an explicit `Развернуть` action
- **AND** no fourth record is displayed in the inline preview

#### Scenario: Fewer than three calls exist

- **GIVEN** the initial accepted call-history dataset contains one or two records
- **WHEN** the inline preview renders
- **THEN** every available record is shown
- **AND** the presentation does not fabricate placeholder calls

#### Scenario: Explicit detail remains distinct

- **GIVEN** three initial preview rows are already visible
- **WHEN** the operator presses `Развернуть`
- **THEN** the detailed view enters its fresh explicit-acquisition lifecycle
- **AND** the three-row preview is not promoted as the fresh detailed result

### Requirement: Codec dashboard controls match exact-model network capability

A room codec control visually presented as enabled/actionable SHALL correspond to a `YES` exact-model network capability in the normative matrix and a current lifecycle state in which the operation can be admitted.

An operation whose matrix capability is `NO` SHALL be hidden, disabled, or unmistakably local-only before user activation. It SHALL NOT look equivalent to a normal supported network action and then fail only after room interaction admission.

#### Scenario: Visible codec action is enabled

- **WHEN** a codec dashboard action is displayed as a normal enabled network control
- **THEN** the exact current model matrix advertises that capability as `YES`
- **AND** current row/lifecycle state permits admission
- **AND** activation is not guaranteed to terminate locally as unsupported

#### Scenario: TE40 microphone gain controls are rendered

- **GIVEN** exact model is `Huawei TE40`
- **AND** authoritative numeric microphone gain has been accepted
- **AND** the verified gain setter protocol is implemented
- **WHEN** the dashboard renders microphone gain controls
- **THEN** `-` and `+` are normal supported network controls using the TE40 gain capability
- **AND** the current numeric gain is displayed between/with those controls rather than `Нет данных`
- **AND** microphone mute remains a separate control/state

#### Scenario: CloudLink microphone plus/minus is rendered

- **GIVEN** exact model is CloudLink Bar 310 or CloudLink Box 310
- **WHEN** the dashboard renders microphone `-` / `+`
- **THEN** they are not normal enabled network controls
- **AND** no gain mutation is admitted

#### Scenario: Reboot is rendered for a codec

- **GIVEN** any of the five exact codec models is current
- **WHEN** the dashboard renders `Перезагрузить устройство`
- **THEN** the control is hidden, disabled, or unmistakably local-only
- **AND** no reboot network I/O is admitted by this change

### Requirement: TE40 camera presentation accepts one-or-more normalized camera records

The room codec dashboard SHALL render TE40 camera evidence produced from the exact-model parser without assuming two camera records exist. A valid normalized camera result derived from exactly one returned `WEB_GetLocalCameraList.itemList` entry SHALL be presented as known camera state/model evidence rather than `Нет данных` solely because a second entry is absent.

#### Scenario: TE40 has one active camera

- **GIVEN** TE40 parsing accepts exactly one active camera record and optional resolved camera model
- **WHEN** the dashboard renders camera state
- **THEN** the accepted camera status/model is shown
- **AND** `Нет данных` is not shown merely because only one camera entry exists
