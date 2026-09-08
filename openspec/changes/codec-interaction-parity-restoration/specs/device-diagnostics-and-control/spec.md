## MODIFIED Requirements

### Requirement: Current codec room-control support matrix is a fixed acceptance oracle

The unified exact-model registration SHALL remain the sole runtime capability authority. With the TE40 microphone-gain protocol now discovered on authorized hardware, implementation and tests SHALL prove these exact network-capability declarations:

| Exact model | speaker_adjust | speaker_mute | microphone_adjust | microphone_mute | reboot |
| --- | --- | --- | --- | --- | --- |
| `Huawei TE20` | SUPPORTED | SUPPORTED | UNSUPPORTED | SUPPORTED | UNSUPPORTED |
| `Huawei TE40` | SUPPORTED | SUPPORTED | **SUPPORTED** | SUPPORTED | UNSUPPORTED |
| `CloudLink Bar 310` | SUPPORTED | SUPPORTED | UNSUPPORTED | UNSUPPORTED | UNSUPPORTED |
| `CloudLink Box 310` | SUPPORTED | SUPPORTED | UNSUPPORTED | UNSUPPORTED | UNSUPPORTED |
| `Polycom RPG 310` | SUPPORTED | SUPPORTED | UNSUPPORTED | SUPPORTED | UNSUPPORTED |

This table is an OpenSpec/test oracle and SHALL NOT become a second runtime registry.

TE40 numeric microphone gain is a distinct state-changing capability from microphone mute. Its approved primary-input target is `MIC1`. The user-facing configured gain range is `-12 dB .. +9 dB`, step `1 dB`; the corresponding device/wire range is `0..21`, step `1`, with deterministic mapping `gain_db = mic1Value - 12` and `mic1Value = gain_db + 12`.

Speaker mute support for all five SHALL continue to use only the approved volume-zero/restore desired-state policy and proven exact-row/generation restore evidence; it does not imply a separate raw speaker-mute wire command.

Polycom RPG 310 speaker adjustment SHALL use range `0..100`, step `2`. TE20/TE40 speaker adjustment SHALL use `0..21`, step `1`. Bar/Box speaker adjustment SHALL use `0..15`, step `1`.

#### Scenario: Current codec registration matrix is checked

- **WHEN** composition tests inspect the five current exact codec registrations
- **THEN** every operation matches the table above
- **AND** TE40 exposes microphone gain and microphone mute as separate supported operations
- **AND** runtime resolution still comes from the unified registry rather than this test-oracle table

### Requirement: Codec room-control adapters reuse approved typed operations and explicitly reject unsupported operations

The room codec-control capability SHALL reuse existing approved safe codec operation/readback semantics rather than duplicate protocol command grammar in the room GUI. Each exact codec registration SHALL bind an application/core codec-control adapter, or equivalent registry-owned binding, that can answer operation support before network acquisition and construct typed desired-state/readback operations only for approved controls.

A standalone widget branch, handler attribute probe, accepted read-only field, or visually present button SHALL NOT silently promote a state-changing capability.

`Huawei TE20` and `Polycom RPG 310` remain microphone-mute models with no approved numeric microphone-adjust mutation in this change. `Huawei TE40` supports both independent numeric microphone gain and independent microphone mute under the exact contract below. `CloudLink Bar 310` and `CloudLink Box 310` retain both microphone-adjust and separate microphone-mute mutation as unsupported under the current approved room contract.

Reboot SHALL remain unsupported for the current five-codec baseline.

#### Scenario: Microphone has mute but no numeric gain contract

- **GIVEN** exact model is `Huawei TE20` or `Polycom RPG 310`
- **WHEN** its room codec-control capability is composed
- **THEN** `microphone_mute` is supported
- **AND** `microphone_adjust` is unsupported
- **AND** shared GUI code does not reinterpret mute state as a numeric gain range

#### Scenario: CloudLink microphone controls remain network-unsupported

- **GIVEN** exact model is `CloudLink Bar 310` or `CloudLink Box 310`
- **WHEN** its room codec-control capability is composed
- **THEN** `microphone_adjust` and `microphone_mute` are both unsupported for room mutation
- **AND** fixed visual affordances may use only the existing local informational path
- **AND** no accepted numeric read evidence promotes either mutation capability

#### Scenario: TE40 numeric gain and mute are independent supported operations

- **GIVEN** exact model is `Huawei TE40`
- **WHEN** its room codec-control capability is composed
- **THEN** `microphone_adjust` is supported only through the approved `MIC1` gain contract
- **AND** `microphone_mute` remains separately supported
- **AND** changing gain never reuses `WEB_OpenMicAPI` / `WEB_CloseMicAPI`
- **AND** numeric gain value `0` is not interpreted as mute authority

## ADDED Requirements

### Requirement: TE40 numeric microphone value and mute evidence are independent read authorities

For exact `Huawei TE40`, static audio normalization SHALL preserve numeric microphone configuration evidence independently from mute evidence.

When the approved TE40 audio-status parser receives a finite numeric `micValue` in device/wire domain `0..21`, the accepted room snapshot SHALL publish canonical numeric `microphone_volume`. When authoritative `MicSwitch` or equivalent approved mute evidence is present, the same snapshot SHALL independently publish canonical `microphone_muted`.

For presentation and typed gain intent, TE40 SHALL use the exact-model transform `gain_db = microphone_volume - 12`. Thus wire value `21` is `+9 dB`, wire value `18` is `+6 dB`, and wire value `0` is `-12 dB`.

A numeric value, including `0`, SHALL NOT be interpreted as mute evidence. Mute state SHALL NOT overwrite numeric gain evidence, and numeric gain evidence SHALL NOT overwrite mute state.

#### Scenario: TE40 static audio contains numeric value and unmuted state

- **GIVEN** TE40 audio status contains numeric `micValue = 18`
- **AND** independent authoritative mute evidence says unmuted
- **WHEN** the room snapshot is accepted
- **THEN** `microphone_volume` is numeric `18`
- **AND** the model-specific display value is `+6 dB`
- **AND** `microphone_muted` is `false`
- **AND** neither value is derived from the other

#### Scenario: TE40 micValue zero is not mute authority

- **GIVEN** TE40 audio status contains numeric `micValue = 0`
- **AND** independent authoritative mute evidence says unmuted
- **WHEN** the room snapshot is accepted
- **THEN** `microphone_volume` remains numeric `0`
- **AND** its configured gain meaning is `-12 dB`
- **AND** `microphone_muted` remains `false`
- **AND** the application does not fabricate a muted state from the numeric value

### Requirement: TE40 microphone-gain mutation uses the proven MIC1 save/readback contract

For exact `Huawei TE40`, room `microphone_adjust` SHALL control the primary `MIC1` configured input gain only. Each operator `-` / `+` intent changes the configured gain by exactly `1 dB`, clamped to `-12 dB .. +9 dB`, equivalent to wire target `0..21` step `1`.

The state-changing transport boundary is:

```text
POST action.cgi?ActionID=WEB_SaveAudioMicCtrlParams
```

The payload SHALL be constructed from current accepted/fresh audio-control state rather than from fabricated defaults. It SHALL preserve the current non-target microphone enable/value fields (`micall`, `mic1..mic18`, `mic1Value..mic18Value` as required by the device contract) and change only the `MIC1` numeric target field `mic1Value` for a gain-adjust intent. Required session/CSRF material SHALL follow existing credential/session authority and SHALL never be logged or exposed as evidence.

The mapping SHALL be:

```text
wire mic1Value = requested gain_db + 12
requested gain_db = wire mic1Value - 12
```

A successful response such as `{"success":1,"data":""}` is acknowledgement only and SHALL NOT become authoritative final-state evidence.

After one accepted submit, the mutation lifecycle SHALL perform the approved TE40 numeric audio readback through the existing exact-model `get_audio_status` path (`WEB_InitAudioCtrlParamsAPI`) and its numeric `micValue` field. Final success requires current exact-row/generation readback to equal the requested wire target. Missing/malformed/mismatched readback, ambiguous send outcome, cancellation after possible send, or inability to complete bounded reconciliation SHALL follow the root blocked/unconfirmed mutation contract; no blind replay is permitted.

Microphone mute remains a separate desired-state operation using its approved mute evidence/path and SHALL NOT be changed as a side effect of gain adjustment.

#### Scenario: TE40 gain plus changes one dB

- **GIVEN** exact TE40 has current accepted `microphone_volume = 18`, equivalent to `+6 dB`
- **WHEN** the operator requests one microphone gain `+`
- **THEN** the typed target is `+7 dB` / wire `mic1Value = 19`
- **AND** exactly one approved save attempt is admitted after required LIVE retirement/cleanup
- **AND** unrelated `micN` / `micNValue` payload state is preserved rather than replaced with guessed defaults
- **AND** final success is published only after authoritative numeric readback confirms `micValue = 19`

#### Scenario: TE40 gain minus at lower bound is local no-op

- **GIVEN** exact TE40 has current accepted `microphone_volume = 0`, equivalent to `-12 dB`
- **WHEN** the operator requests one microphone gain `-`
- **THEN** no below-range target is constructed
- **AND** no mutation/session/device I/O is started solely for that no-op
- **AND** mute state remains unchanged

#### Scenario: TE40 gain acknowledgement is not final authority

- **GIVEN** `WEB_SaveAudioMicCtrlParams` returns a successful acknowledgement
- **WHEN** the mandatory numeric readback is missing, malformed, stale or does not equal the requested target
- **THEN** the requested gain is not published as confirmed
- **AND** root blocked/unconfirmed mutation safety applies
- **AND** the command is not blindly repeated

### Requirement: TE40 camera normalization accepts zero-to-many camera records

For exact `Huawei TE40`, `WEB_GetLocalCameraList.itemList` or its approved equivalent SHALL be treated as a zero-to-many collection. The parser SHALL NOT require at least two entries before processing camera evidence.

Each present entry SHALL be interpreted independently. An active camera MAY use the existing approved port/type lookup to resolve model evidence. A valid single returned camera SHALL publish known camera status/model evidence when available and SHALL NOT become `Нет данных` solely because a second list entry is absent.

#### Scenario: TE40 returns exactly one camera record

- **GIVEN** TE40 camera-list data contains exactly one valid camera entry
- **WHEN** exact-model camera normalization runs
- **THEN** that entry is processed
- **AND** available camera state/model evidence is published
- **AND** the parser does not require `len(itemList) >= 2`

### Requirement: CloudLink Box 310 live response semantics remain a separate discovery gate from Bar 310

The current authorized Bar 310 capture proves that Bar may return `mic1ValueIndex`, `mic2ValueIndex`, and `micArray*_ValIdx` style fields. That capture belongs to **Bar 310** and SHALL NOT be used as evidence for Box 310 parsing.

The available earlier Box 310 hardware evidence remains limited to multiple records shaped like:

```json
{"deviceId": <number>, "curVolume": <number>}
```

That pair shape is enough to reject copying Bar's fixed-field parser into Box, but it does not establish the complete Box response envelope, prove that every record is microphone evidence, define authoritative device-role filtering, or establish the display normalization range.

Before final architecture `APPROVE`, authorized Box discovery SHALL capture a redacted complete response envelope/container and establish one of:

- the relevant collection is microphone-only; or
- the collection contains mixed roles and an authoritative microphone filter/device-role mapping is required.

The final Box parser contract SHALL specify the envelope/container path, microphone record-selection rule, accepted numeric `curVolume` rules, aggregation rule, empty/malformed behavior, exact Box identity, and display normalization. Until that contract is approved, implementation SHALL NOT replace the old Box parser with either Bar's `mic*ValueIndex` schema or an unproven `max(all curVolume)` algorithm.

#### Scenario: Bar fixed-field capture is not Box evidence

- **GIVEN** an authorized Bar 310 response contains `mic1ValueIndex` / `micArray*_ValIdx` fields
- **WHEN** architecture evaluates Box 310 LIVE parsing
- **THEN** those Bar fields do not become a Box parser contract
- **AND** exact Box identity remains independent from Bar

#### Scenario: Box response contains device-volume pairs but roles are not proven

- **GIVEN** earlier Box hardware evidence contains multiple `{deviceId, curVolume}` records
- **AND** device-role semantics and full envelope have not yet been established
- **WHEN** architecture evaluates live microphone aggregation
- **THEN** it does not classify every record as microphone evidence by assumption
- **AND** no normative `max(all curVolume)` rule is approved
- **AND** response-role discovery remains a blocking architecture task

#### Scenario: Box microphone collection role is proven

- **GIVEN** authorized discovery establishes the exact Box response container and microphone record-selection semantics
- **WHEN** architecture is amended for final review
- **THEN** only authoritative microphone `curVolume` evidence participates in aggregation
- **AND** exact application identity remains `CloudLink Box 310`
- **AND** the resulting parser rule is testable from transport-edge response data
