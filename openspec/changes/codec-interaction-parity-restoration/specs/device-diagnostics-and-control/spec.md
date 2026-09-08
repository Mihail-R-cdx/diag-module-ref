## ADDED Requirements

### Requirement: Room codec interactions preserve proven pre-redesign model behavior

For Huawei TE20, Huawei TE40, CloudLink Bar 310, CloudLink Box 310, and Polycom RPG 310, the common room codec dashboard SHALL preserve supported codec interactions that were working immediately before `codec-diagnostic-modern-ui`, using `c442152077dd8aa6251f1d8be9fc98b765406dbd` as the behavioral reference unless current real-device evidence proves a referenced operation invalid or incomplete.

The application SHALL preserve current exact-row authority, currentness, typed failure, credential ownership, redaction, and background-I/O rules. The behavioral reference SHALL NOT authorize direct widget-to-handler calls, a second capability registry, blind mutation replay, or restoration of an operation that current approved capability keeps unsupported without authoritative reconciliation evidence.

Supported behavior SHALL be restored at the application/controller/session boundary rather than by making the reusable legacy `CodecScreen` room authority.

Hardware observations against `467f2cbb502f698476f047d277052bf5ccb55147` are architecture-discovery evidence. Where those observations contradict the previously approved matrix or parser assumptions, the amended requirements in this change are authoritative for the next implementation.

#### Scenario: Existing protocol operation worked before codec redesign

- **GIVEN** a supported codec operation used a model-specific handler/session path successfully before `codec-diagnostic-modern-ui`
- **AND** current handler/device evidence does not invalidate that path
- **WHEN** the same operation is initiated from the current room codec dashboard
- **THEN** the current application preserves equivalent model-specific request and authoritative readback semantics
- **AND** the new room presentation does not replace the working protocol behavior with synthetic snapshot-only behavior

#### Scenario: Hardware evidence corrects an old assumption

- **GIVEN** current real-device evidence demonstrates a supported field or behavior that the prior approved matrix classified differently
- **WHEN** this amended change is implemented
- **THEN** the amended exact-model contract is used
- **AND** the implementation does not preserve the superseded assumption merely because it existed at `c442152...` or `467f2cbb...`

#### Scenario: Old visual affordance was not a proven network capability

- **GIVEN** the legacy or current codec screen displays an affordance for an operation that lacks approved authoritative target/readback support
- **WHEN** parity is evaluated
- **THEN** the visual affordance alone does not authorize network capability
- **AND** the operation remains disabled, hidden, or clearly local-only until separately proven and approved

### Requirement: Exact-model room codec capability matrix is normative

The single exact-model application registration SHALL expose codec network capabilities that match the following matrix. Implementation SHALL NOT downgrade a `YES` capability to unsupported, change an exact range/step, or infer a new capability without an approved architecture/spec change supported by current source/device evidence.

| Exact model | Speaker adjust | Range / step | Speaker readback | Speaker mute | Mic mute | Mic gain adjust | Mic gain readback | Reboot | Call log | LIVE telemetry | Local Refresh |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `Huawei TE20` | YES | `0..21` / `1` | `get_speaker_volume` | YES, zero/restore through authoritative speaker volume | YES | NO | N/A | NO | YES | YES, room-owned `get_live_audio_status`, 2 s | YES |
| `Huawei TE40` | YES | `0..21` / `1` | `get_speaker_volume` | YES, zero/restore through authoritative speaker volume | YES | **YES**, independent numeric gain | authoritative numeric `micValue`; setter protocol MUST be verified before implementation | NO | YES | YES, room-owned `get_live_audio_status`, 2 s | YES |
| `CloudLink Bar 310` | YES | `0..15` / `1` | `get_speaker_volume` | YES, zero/restore through authoritative speaker volume | NO separate approved capability | NO | N/A | NO | YES | YES, `cloudlink_room_live` | YES |
| `CloudLink Box 310` | YES | `0..15` / `1` | `get_speaker_volume` | YES, zero/restore through authoritative speaker volume | NO separate approved capability | NO | N/A | NO | YES | YES, `cloudlink_room_live` with Box-specific `{deviceId, curVolume}` extraction | YES |
| `Polycom RPG 310` | YES | `0..100` / **`2`** | `get_speaker_volume` | YES, zero/restore through authoritative speaker volume | YES | NO | N/A | NO | YES | NO | YES |

The following meanings are normative:

- `Local Refresh = YES` means the existing exact-row `room_one_shot_refresh` path using the model's registered one-shot adapter.
- `Call log = YES` means the model participates in both the mandatory initial three-call preview acquisition and a fresh exact-row explicit detailed acquisition through its approved model-specific call-history path.
- `Mic gain adjust = NO` remains normative for TE20, Bar 310, Box 310, and RPG310 in this change. TE20/RPG310 keep approved mute semantics; CloudLink gain remains prohibited without authoritative target/readback proof.
- `Huawei TE40 Mic gain adjust = YES` is independent from microphone mute. Static diagnostic evidence already exposes numeric `micValue`; mute evidence is separately `MicSwitch`/equivalent. A value of `0` SHALL NOT automatically mean mute unless the independent mute field says so.
- Before implementing TE40 microphone-gain mutation, architecture/implementation evidence MUST identify the actual state-changing device method/ActionID, payload, accepted range/step, and authoritative post-write numeric readback. The implementation SHALL NOT guess a write endpoint or repurpose `WEB_OpenMicAPI` / `WEB_CloseMicAPI` as gain adjustment.
- `Reboot = NO` for all five models because no pre-redesign room capability/current approved exact-model registration proves it. A visible reboot affordance SHALL NOT be treated as evidence of network capability.
- Polycom speaker step SHALL be `2`; a registry value of `1` is non-conforming.
- Broader TE30/TE50/TE60 support is outside this amendment and SHALL NOT be inferred from TE40 capability evidence.

#### Scenario: Polycom speaker adjustment uses proven step

- **GIVEN** exact model is `Polycom RPG 310`
- **AND** authoritative speaker volume is available
- **WHEN** the operator requests one `+` or `-` adjustment
- **THEN** the target changes by exactly `2` within `0..100`
- **AND** the result is confirmed by `get_speaker_volume`

#### Scenario: TE20 or TE40 live capability is registered

- **GIVEN** exact model is `Huawei TE20` or `Huawei TE40`
- **WHEN** room interaction capabilities are resolved
- **THEN** the model advertises the approved room-owned live-audio binding
- **AND** the capability is not omitted merely because it is not `cloudlink_room_live`

#### Scenario: TE40 microphone gain is registered independently from mute

- **GIVEN** exact model is `Huawei TE40`
- **WHEN** room interaction capabilities are resolved
- **THEN** microphone gain adjustment and microphone mute are represented as distinct capabilities/intents
- **AND** numeric gain readback is based on authoritative `micValue`
- **AND** mute readback is based on authoritative `MicSwitch`/equivalent mute evidence
- **AND** a gain `+` / `-` intent is never translated into a mute/unmute command

#### Scenario: TE40 gain write protocol is not yet proven

- **GIVEN** the implementation session has not yet identified and verified the actual TE40 gain-setting protocol
- **WHEN** microphone-gain implementation is attempted
- **THEN** the implementation SHALL stop rather than invent an ActionID/payload or map numeric targets onto mute/unmute
- **AND** protocol-discovery evidence becomes a blocking implementation prerequisite

#### Scenario: Unsupported reboot is rendered

- **GIVEN** any one of the five exact codec models is current
- **WHEN** the room codec dashboard is rendered
- **THEN** reboot is not presented as a normal enabled device network action
- **AND** activating any retained local-only affordance performs no room interaction admission or device I/O

#### Scenario: CloudLink microphone gain remains unsupported

- **GIVEN** exact model is CloudLink Bar 310 or CloudLink Box 310
- **WHEN** the dashboard renders microphone gain affordances
- **THEN** they are disabled, hidden, or clearly local-only
- **AND** no gain mutation is admitted by this change

### Requirement: Supported codec audio mutations use targeted authoritative readback

A supported room codec audio mutation SHALL use one serialized exact-model operation owner and the smallest model-supported authoritative readback that can confirm the changed field. A full codec diagnostic refresh SHALL NOT be required solely to confirm one audio field when the same model already exposes a proven authoritative getter for that field.

Successful mutation transport/ACK SHALL remain non-authoritative. Only the readback result MAY publish the reconciled canonical field. If readback cannot confirm final state, prior accepted state SHALL remain stale/unconfirmed and current mutation safety rules SHALL apply; the application SHALL NOT blindly repeat the state-changing operation.

Speaker mute/unmute SHALL preserve the existing root restore-authority contract: only a proven current exact-row/generation non-zero restore target may be restored. When current accepted speaker volume is `0` and no proven restore target exists, the operation remains a safe local unavailable result with zero mutation/device I/O; this change SHALL NOT invent fallback `1`, a minimum value, or another synthetic restore target.

TE40 microphone gain mutation, once its protocol is verified, SHALL follow the same targeted-reconciliation principle: compute one numeric target within the verified range/step, perform one state-changing send through the serialized owner, then read authoritative numeric `micValue`. Mute state SHALL not be inferred from that numeric readback.

#### Scenario: Speaker volume adjustment succeeds

- **GIVEN** the exact codec model supports speaker-volume adjustment and authoritative speaker-volume readback
- **WHEN** the operator presses `+` or `-`
- **THEN** one exact target is computed from current authoritative evidence using the matrix range/step
- **AND** the model-specific set operation runs off the GUI thread
- **AND** `get_speaker_volume` confirms final state
- **AND** the reconciled `speaker_volume` field is published without requiring an unrelated full diagnostic refresh
- **AND** the room interaction lock is released after bounded cleanup

#### Scenario: TE40 microphone gain adjustment succeeds

- **GIVEN** exact model is `Huawei TE40`
- **AND** the verified TE40 microphone-gain setter contract is available
- **AND** current authoritative numeric `microphone_volume` is available
- **WHEN** the operator presses microphone `+` or `-`
- **THEN** one numeric target is computed using the verified TE40 range/step
- **AND** one gain-setting mutation is submitted through the serialized exact-row owner
- **AND** authoritative numeric `micValue` readback confirms final gain
- **AND** only canonical `microphone_volume` is reconciled by that gain operation
- **AND** microphone mute state is unchanged unless separately changed by a mute intent

#### Scenario: Speaker mute succeeds

- **GIVEN** current authoritative speaker volume is positive
- **WHEN** the operator requests speaker mute
- **THEN** the application remembers that positive authoritative value for the exact session/record
- **AND** submits target volume `0`
- **AND** confirms the final state with `get_speaker_volume`
- **WHEN** the operator requests unmute while authoritative volume is `0`
- **AND** the same exact row/generation has a proven positive restore target
- **THEN** the proven positive value is restored and confirmed by the same authoritative getter

#### Scenario: Speaker unmute has no restore evidence

- **GIVEN** current accepted speaker volume is `0`
- **AND** the exact row/generation has no accepted non-zero restore target
- **WHEN** the operator requests speaker unmute
- **THEN** no default, minimum, `1`, or other synthetic target is invented
- **AND** no room mutation, handler/session acquisition, or device I/O starts
- **AND** a safe local unavailable result is shown without leaving the row or interaction lane locked

#### Scenario: Audio mutation readback fails

- **WHEN** a codec audio mutation may have been delivered but targeted authoritative readback cannot confirm final state
- **THEN** the mutation is not replayed automatically
- **AND** prior accepted state remains stale/unconfirmed
- **AND** current blocked/unconfirmed recovery rules apply

### Requirement: Supported microphone mute is distinct from microphone gain

Huawei TE20, Huawei TE40, and Polycom RPG 310 SHALL expose microphone mute/unmute as a supported microphone state-changing capability. For TE20 and RPG310, this remains the only approved microphone mutation in this change. For TE40, mute/unmute SHALL coexist with independent numeric microphone gain adjustment.

CloudLink Bar 310 and Box 310 SHALL NOT infer a separate microphone-mute network capability from numeric microphone level/volume presentation evidence. CloudLink microphone gain remains unavailable under the current root contract.

#### Scenario: TE20 microphone mute is requested

- **GIVEN** exact model is `Huawei TE20`
- **WHEN** the operator requests microphone mute or unmute
- **THEN** the existing microphone mute operation is used through the serialized exact-row interaction owner
- **AND** authoritative mute-state readback confirms the result
- **AND** no numeric microphone-gain mutation is inferred

#### Scenario: TE40 microphone mute is requested

- **GIVEN** exact model is `Huawei TE40`
- **WHEN** the operator requests microphone mute or unmute
- **THEN** the approved mute operation is reconciled against authoritative `MicSwitch`/equivalent mute evidence
- **AND** current numeric `micValue` is not used to infer the mute result
- **AND** the independent gain target/value is not rewritten merely because mute state changed

#### Scenario: CloudLink numeric microphone evidence exists

- **GIVEN** exact model is CloudLink Bar 310 or CloudLink Box 310
- **AND** diagnostic data contains an authoritative numeric microphone value
- **WHEN** capabilities are evaluated
- **THEN** that numeric read evidence does not authorize microphone gain or mute mutation
- **AND** the value may still be presented according to the normalization contract

### Requirement: TE40 static microphone and camera evidence is normalized from actual device fields

For exact `Huawei TE40`, static audio normalization SHALL preserve independent numeric microphone gain and mute evidence. When `WEB_InitAudioCtrlParamsAPI`/approved audio-status parsing provides numeric `micValue`, the accepted room snapshot SHALL publish canonical numeric `microphone_volume`. When authoritative `MicSwitch`/equivalent mute evidence is present, it SHALL independently publish canonical `microphone_muted`.

TE40 camera discovery SHALL accept `WEB_GetLocalCameraList`/approved camera-list evidence containing zero, one, or many `itemList` entries. The parser SHALL NOT require at least two entries before publishing camera state. Each present entry SHALL be interpreted independently; active camera model lookup may use the existing approved port/type lookup. Empty or absent authoritative lists may produce unavailable/disconnected semantics according to the existing parser contract, but one valid returned camera SHALL never become `Нет данных` solely because a second list entry is absent.

#### Scenario: TE40 static audio contains gain and mute evidence

- **GIVEN** TE40 audio status contains numeric `micValue = 7`
- **AND** independent mute evidence says the microphone is unmuted
- **WHEN** the room snapshot is accepted
- **THEN** `microphone_volume` is numeric `7`
- **AND** `microphone_muted` is `false`
- **AND** neither value is derived from the other

#### Scenario: TE40 has exactly one returned camera entry

- **GIVEN** `WEB_GetLocalCameraList` returns an `itemList` containing exactly one valid camera record
- **WHEN** TE40 diagnostic parsing runs
- **THEN** that camera record is processed
- **AND** camera status/model evidence is published when available
- **AND** the parser does not return `Нет данных` merely because `len(itemList) < 2`

### Requirement: CloudLink Box 310 live microphone parsing follows hardware-observed record shape

For exact `CloudLink Box 310`, `WEB_GetCurrentAudioParam` live microphone evidence SHALL be parsed from the hardware-observed collection of records containing `deviceId` and `curVolume`, including when the collection is nested inside the endpoint's normal response envelope. The Box parser SHALL remain Box-specific even if a shared helper is used for numeric aggregation.

Every record with a valid non-negative numeric `curVolume` SHALL be eligible for aggregation unless separate device evidence later proves a required microphone-only filter. The accepted raw live level SHALL be the maximum valid `curVolume`. Empty/malformed collections SHALL produce unavailable live evidence. The parser SHALL NOT depend on the superseded fixed fields `mic1ValueIndex`, `mic2ValueIndex`, `micArray*_ValIdx`.

#### Scenario: Box returns multiple device-volume records

- **GIVEN** exact model is `CloudLink Box 310`
- **AND** `WEB_GetCurrentAudioParam` contains records `{deviceId: 1, curVolume: 4}`, `{deviceId: 2, curVolume: 11}`, and `{deviceId: 18, curVolume: 7}`
- **WHEN** the Box live microphone parser normalizes the response
- **THEN** the accepted raw live microphone level is `11`
- **AND** exact model identity remains Box 310 rather than a Bar alias
