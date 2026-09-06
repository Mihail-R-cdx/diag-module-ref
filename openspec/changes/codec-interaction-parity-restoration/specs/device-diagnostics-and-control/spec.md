## ADDED Requirements

### Requirement: Room codec interactions preserve proven pre-redesign model behavior

For Huawei TE20, Huawei TE40, CloudLink Bar 310, CloudLink Box 310, and Polycom RPG 310, the common room codec dashboard SHALL preserve supported codec interactions that were working immediately before `codec-diagnostic-modern-ui`, using `c442152077dd8aa6251f1d8be9fc98b765406dbd` as the behavioral reference unless current real-device evidence proves a referenced operation invalid.

The application SHALL preserve current exact-row authority, currentness, typed failure, credential ownership, redaction, and background-I/O rules. The behavioral reference SHALL NOT authorize direct widget-to-handler calls, a second capability registry, blind mutation replay, or restoration of an operation that current approved capability keeps unsupported without authoritative reconciliation evidence.

Supported behavior SHALL be restored at the application/controller/session boundary rather than by making the reusable legacy `CodecScreen` room authority.

#### Scenario: Existing protocol operation worked before codec redesign

- **GIVEN** a supported codec operation used a model-specific handler/session path successfully before `codec-diagnostic-modern-ui`
- **AND** current handler/device evidence does not invalidate that path
- **WHEN** the same operation is initiated from the current room codec dashboard
- **THEN** the current application preserves equivalent model-specific request and authoritative readback semantics
- **AND** the new room presentation does not replace the working protocol behavior with synthetic snapshot-only behavior

#### Scenario: Old visual affordance was not a proven network capability

- **GIVEN** the legacy or current codec screen displays an affordance for an operation that lacks approved authoritative target/readback support
- **WHEN** parity is evaluated
- **THEN** the visual affordance alone does not authorize network capability
- **AND** the operation remains disabled, hidden, or clearly local-only until separately proven and approved

### Requirement: Exact-model room codec capability matrix is normative

The single exact-model application registration SHALL expose codec network capabilities that match the following matrix. Implementation SHALL NOT downgrade a `YES` capability to unsupported, change an exact range/step, or infer a new capability without an approved architecture/spec change supported by current source/device evidence.

| Exact model | Speaker adjust | Range / step | Speaker readback | Speaker mute | Mic mute | Mic gain adjust | Reboot | Call log | LIVE telemetry | Local Refresh |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `Huawei TE20` | YES | `0..21` / `1` | `get_speaker_volume` | YES, zero/restore through authoritative speaker volume | YES | NO | NO | YES | YES, room-owned `get_live_audio_status`, 2 s | YES |
| `Huawei TE40` | YES | `0..21` / `1` | `get_speaker_volume` | YES, zero/restore through authoritative speaker volume | YES | NO | NO | YES | YES, room-owned `get_live_audio_status`, 2 s | YES |
| `CloudLink Bar 310` | YES | `0..15` / `1` | `get_speaker_volume` | YES, zero/restore through authoritative speaker volume | NO separate approved capability | NO | NO | YES | YES, `cloudlink_room_live` | YES |
| `CloudLink Box 310` | YES | `0..15` / `1` | `get_speaker_volume` | YES, zero/restore through authoritative speaker volume | NO separate approved capability | NO | NO | YES | YES, `cloudlink_room_live` | YES |
| `Polycom RPG 310` | YES | `0..100` / **`2`** | `get_speaker_volume` | YES, zero/restore through authoritative speaker volume | YES | NO | NO | YES | NO | YES |

The following meanings are normative:

- `Local Refresh = YES` means the existing exact-row `room_one_shot_refresh` path using the model's registered one-shot adapter.
- `Call log = YES` means a fresh exact-row model-specific `get_call_history_snapshot`/approved Polycom call-log worker path.
- `Mic gain adjust = NO` for TE20, TE40, and Polycom because their legacy `set_microphone_volume` compatibility surface represents mute/unmute rather than independent gain; it is also `NO` for Bar/Box because the current root CloudLink contract explicitly prohibits gain mutation without authoritative target selection/readback.
- `Reboot = NO` for all five models because no pre-redesign room capability/current approved exact-model registration proves it. A visible reboot affordance SHALL NOT be treated as evidence of network capability.
- Polycom speaker step SHALL be `2`; a registry value of `1` is non-conforming.

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

#### Scenario: Speaker volume adjustment succeeds

- **GIVEN** the exact codec model supports speaker-volume adjustment and authoritative speaker-volume readback
- **WHEN** the operator presses `+` or `-`
- **THEN** one exact target is computed from current authoritative evidence using the matrix range/step
- **AND** the model-specific set operation runs off the GUI thread
- **AND** `get_speaker_volume` confirms final state
- **AND** the reconciled `speaker_volume` field is published without requiring an unrelated full diagnostic refresh
- **AND** the room interaction lock is released after bounded cleanup

#### Scenario: Speaker mute succeeds

- **GIVEN** current authoritative speaker volume is positive
- **WHEN** the operator requests speaker mute
- **THEN** the application remembers that positive authoritative value for the exact session/record
- **AND** submits target volume `0`
- **AND** confirms the final state with `get_speaker_volume`
- **WHEN** the operator requests unmute while authoritative volume is `0`
- **THEN** the remembered positive value is restored and confirmed by the same authoritative getter

#### Scenario: First unmute starts from zero without remembered positive volume

- **GIVEN** the current exact codec model supports speaker mute/unmute
- **AND** the first authoritative speaker volume observed for the exact record/session is `0`
- **AND** no remembered positive speaker volume exists for that exact record/session
- **WHEN** the operator requests speaker unmute
- **THEN** the application SHALL use fallback target `1` when `1` is inside the exact-model speaker range
- **AND** SHALL submit that target through the same serialized speaker-volume mutation path
- **AND** SHALL confirm final state with `get_speaker_volume`
- **AND** SHALL remember the confirmed positive result for subsequent mute/unmute operations
- **AND** SHALL NOT require a full codec refresh merely to choose the fallback target

#### Scenario: Audio mutation readback fails

- **WHEN** a codec audio mutation may have been delivered but targeted authoritative readback cannot confirm final state
- **THEN** the mutation is not replayed automatically
- **AND** prior accepted state remains stale/unconfirmed
- **AND** current blocked/unconfirmed recovery rules apply

### Requirement: Supported microphone mute is distinct from microphone gain

Huawei TE20, Huawei TE40, and Polycom RPG 310 SHALL expose microphone mute/unmute as the supported microphone state-changing capability. The implementation MAY use the existing compatibility method names internally, but SHALL treat the operation semantically as mute/unmute and reconcile it against authoritative mute-state readback.

CloudLink Bar 310 and Box 310 SHALL NOT infer a separate microphone-mute network capability from numeric microphone level/volume presentation evidence. CloudLink microphone gain remains unavailable under the current root contract.

#### Scenario: TE20 microphone mute is requested

- **GIVEN** exact model is `Huawei TE20`
- **WHEN** the operator requests microphone mute or unmute
- **THEN** the existing microphone mute operation is used through the serialized exact-row interaction owner
- **AND** authoritative mute-state readback confirms the result
- **AND** no numeric microphone-gain mutation is inferred

#### Scenario: CloudLink numeric microphone evidence exists

- **GIVEN** exact model is CloudLink Bar 310 or CloudLink Box 310
- **AND** diagnostic data contains an authoritative numeric microphone value
- **WHEN** capabilities are evaluated
- **THEN** that numeric read evidence does not authorize microphone gain or mute mutation
- **AND** the value may still be presented according to the normalization contract
