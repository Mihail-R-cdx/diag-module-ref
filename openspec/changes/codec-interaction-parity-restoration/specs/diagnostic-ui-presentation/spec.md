## ADDED Requirements

### Requirement: Room codec presentation reflects exact-model live and audio evidence

The common room codec dashboard SHALL display accepted canonical audio values and live telemetry according to the exact model's approved capability rather than forcing all codecs into one synthetic field set.

CloudLink Bar 310 and Box 310 SHALL display their approved live microphone meter when a current accepted live sample is available. Huawei TE20 and TE40 SHALL display the model-specific live-audio evidence restored from their proven `get_live_audio_status` behavior. Polycom RPG 310 SHALL NOT display a fabricated live meter when no approved live-meter capability exists.

Canonical speaker/microphone values that are present in the accepted exact-model snapshot SHALL be projected into the dashboard. Missing canonical evidence SHALL display as unavailable rather than silently substituting a different field or synthetic value.

#### Scenario: CloudLink live sample arrives

- **GIVEN** current exact model is CloudLink Bar 310 or Box 310
- **AND** an accepted current live microphone sample is available
- **WHEN** the dashboard renders
- **THEN** the microphone meter reflects that sample
- **AND** unrelated automatic preview state does not clear or replace the live sample

#### Scenario: TE20 or TE40 live audio arrives

- **GIVEN** current exact model is Huawei TE20 or Huawei TE40
- **AND** current model-specific live-audio evidence has been accepted
- **WHEN** the dashboard renders
- **THEN** the microphone/speaker live-audio presentation reflects the accepted model-specific evidence
- **AND** the dashboard does not label the proven behavior unsupported solely because it is not `cloudlink_room_live`

#### Scenario: Polycom has no approved live meter

- **GIVEN** current exact model is Polycom RPG 310
- **AND** no approved live microphone-meter capability exists
- **WHEN** the dashboard renders
- **THEN** no fabricated live level is presented as device evidence

### Requirement: Codec dashboard controls do not advertise guaranteed rejection

A room codec control that is visually presented as enabled/actionable SHALL correspond to a supported exact-model network capability and a current lifecycle state in which the operation can be admitted. An operation that exact-model capability rejects SHALL be disabled, hidden, or clearly marked local-only before the user attempts it.

#### Scenario: Visible codec action is enabled

- **WHEN** a codec dashboard action is displayed as enabled
- **THEN** the exact current model registry advertises that network capability
- **AND** current row state permits admission
- **AND** activation is not guaranteed to terminate locally as `unsupported`
