## ADDED Requirements

### Requirement: Room codec presentation consumes exact-model normalized audio evidence

The common room codec dashboard SHALL consume canonical audio evidence produced by the exact-model parser/normalizer path. It SHALL NOT require model-specific vendor/display-string parsing in the presentation layer and SHALL NOT treat absence of one universal numeric field as proof that all microphone evidence is unavailable.

The normalization contract is:

| Exact model | Existing authoritative source evidence | Required canonical accepted evidence | Required presentation |
| --- | --- | --- | --- |
| `Huawei TE20` | `mic_mute` / equivalent typed parser evidence | `microphone_muted: bool` when known; no fabricated numeric `microphone_volume` | show mute/unmute state; numeric microphone gain is unavailable by design |
| `Huawei TE40` | `mic_mute` / equivalent typed parser evidence | `microphone_muted: bool` when known; no fabricated numeric `microphone_volume` | show mute/unmute state; numeric microphone gain is unavailable by design |
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

#### Scenario: TE20 or TE40 has microphone mute evidence but no gain

- **GIVEN** exact model is Huawei TE20 or Huawei TE40
- **AND** authoritative mute evidence is known
- **AND** no independent numeric microphone-gain evidence exists
- **WHEN** the room snapshot is accepted and rendered
- **THEN** canonical `microphone_muted` is projected as microphone state
- **AND** the application does not fabricate numeric `microphone_volume`
- **AND** absence of numeric gain does not erase the known microphone state

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

### Requirement: Room codec presentation reflects exact-model live telemetry

CloudLink Bar 310 and Box 310 SHALL display their approved live microphone meter when a current accepted live sample is available. Huawei TE20 and TE40 SHALL display the model-specific live microphone and speaker evidence restored from their proven `get_live_audio_status` behavior. Polycom RPG 310 SHALL NOT display a fabricated live meter when no approved live-meter capability exists.

Static microphone volume/mute evidence and live microphone/audio telemetry are separate authorities: a live sample SHALL NOT silently overwrite static accepted control/readback evidence, and automatic call-log preview bookkeeping SHALL NOT clear a current live sample.

#### Scenario: CloudLink live sample arrives

- **GIVEN** current exact model is CloudLink Bar 310 or Box 310
- **AND** an accepted current live microphone sample is available
- **WHEN** the dashboard renders
- **THEN** the microphone meter reflects that sample
- **AND** unrelated automatic preview state does not clear or replace it

#### Scenario: TE20 or TE40 live audio arrives

- **GIVEN** current exact model is Huawei TE20 or Huawei TE40
- **AND** current `get_live_audio_status` evidence has been accepted
- **WHEN** the dashboard renders
- **THEN** microphone monitor presentation reflects `MicValueIndex`-derived evidence
- **AND** speaker monitor presentation reflects `SpeakerValueIndex`-derived evidence
- **AND** the dashboard does not label this proven behavior unsupported solely because it is not `cloudlink_room_live`

#### Scenario: Polycom has no approved live meter

- **GIVEN** current exact model is Polycom RPG 310
- **AND** no approved live microphone/audio capability exists
- **WHEN** the dashboard renders
- **THEN** no fabricated live level is presented as device evidence

### Requirement: Codec dashboard controls match exact-model network capability

A room codec control visually presented as enabled/actionable SHALL correspond to a `YES` exact-model network capability in the normative matrix and a current lifecycle state in which the operation can be admitted.

An operation whose matrix capability is `NO` SHALL be hidden, disabled, or unmistakably local-only before user activation. It SHALL NOT look equivalent to a normal supported network action and then fail only after room interaction admission.

#### Scenario: Visible codec action is enabled

- **WHEN** a codec dashboard action is displayed as a normal enabled network control
- **THEN** the exact current model matrix advertises that capability as `YES`
- **AND** current row/lifecycle state permits admission
- **AND** activation is not guaranteed to terminate locally as unsupported

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
