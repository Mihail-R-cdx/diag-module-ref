## MODIFIED Requirements

### Requirement: Current codec room-control support matrix is a fixed acceptance oracle

The unified exact-model registration SHALL remain the sole runtime capability authority. Until the TE40 microphone-gain state-changing protocol is fully discovered and approved in this change, implementation and tests SHALL prove these exact network-capability declarations:

| Exact model | speaker_adjust | speaker_mute | microphone_adjust | microphone_mute | reboot |
| --- | --- | --- | --- | --- | --- |
| `Huawei TE20` | SUPPORTED | SUPPORTED | UNSUPPORTED | SUPPORTED | UNSUPPORTED |
| `Huawei TE40` | SUPPORTED | SUPPORTED | **UNSUPPORTED pending approved numeric setter contract** | SUPPORTED | UNSUPPORTED |
| `CloudLink Bar 310` | SUPPORTED | SUPPORTED | UNSUPPORTED | UNSUPPORTED | UNSUPPORTED |
| `CloudLink Box 310` | SUPPORTED | SUPPORTED | UNSUPPORTED | UNSUPPORTED | UNSUPPORTED |
| `Polycom RPG 310` | SUPPORTED | SUPPORTED | UNSUPPORTED | SUPPORTED | UNSUPPORTED |

This table is an OpenSpec/test oracle and SHALL NOT become a second runtime registry.

TE40's current `microphone_adjust = UNSUPPORTED` status is a **temporary architecture safety state**, not a claim that the device lacks numeric microphone evidence. Hardware/source evidence establishes an independent numeric `micValue` read field, but the state-changing method/ActionID, payload, numeric range and step are not yet proven. Read-only numeric evidence MAY therefore normalize to `microphone_volume` while mutation remains fail-closed.

Before final architecture `APPROVE`, protocol discovery SHALL identify and this requirement SHALL be amended to record the exact approved TE40 microphone-adjust contract. No implementation phase may begin while this matrix still marks TE40 microphone adjustment pending discovery.

Speaker mute support for all five SHALL continue to use only the approved volume-zero/restore desired-state policy and proven exact-row/generation restore evidence; it does not imply a separate raw speaker-mute wire command.

Polycom RPG 310 speaker adjustment SHALL use range `0..100`, step `2`. TE20/TE40 speaker adjustment SHALL use `0..21`, step `1`. Bar/Box speaker adjustment SHALL use `0..15`, step `1`.

#### Scenario: Current codec registration matrix is checked

- **WHEN** composition tests inspect the five current exact codec registrations before the TE40 gain discovery gate is closed
- **THEN** every operation matches the table above
- **AND** TE40 accepted numeric `micValue` does not silently promote `microphone_adjust` to network-supported
- **AND** runtime resolution still comes from the unified registry rather than this test-oracle table

### Requirement: Codec room-control adapters reuse approved typed operations and explicitly reject unsupported operations

The room codec-control capability SHALL reuse existing approved safe codec operation/readback semantics rather than duplicate protocol command grammar in the room GUI. Each exact codec registration SHALL bind an application/core codec-control adapter, or equivalent registry-owned binding, that can answer operation support before network acquisition and construct typed desired-state/readback operations only for approved controls.

A standalone widget branch, handler attribute probe, accepted read-only field, or visually present button SHALL NOT silently promote a state-changing capability.

`Huawei TE20` and `Polycom RPG 310` remain microphone-mute models with no approved numeric microphone-adjust mutation in this change. `Huawei TE40` is different: authoritative numeric `micValue` read evidence exists and SHALL remain distinct from mute, but its numeric mutation remains unsupported until the pre-APPROVE protocol-discovery gate establishes the exact setter/range/step/readback contract. `CloudLink Bar 310` and `CloudLink Box 310` retain both microphone-adjust and separate microphone-mute mutation as unsupported under the current approved room contract.

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

#### Scenario: TE40 numeric read evidence does not yet authorize mutation

- **GIVEN** exact model is `Huawei TE40`
- **AND** authoritative diagnostic parsing provides numeric `micValue`
- **AND** the exact gain setter/range/step contract has not yet been approved in OpenSpec
- **WHEN** room codec-control capability is composed
- **THEN** `microphone_mute` remains supported
- **AND** `microphone_adjust` remains network-unsupported before room interaction admission
- **AND** numeric `micValue` may still be exposed as read-only canonical `microphone_volume`
- **AND** microphone `-` / `+` causes zero gain mutation/session/device I/O

## ADDED Requirements

### Requirement: TE40 numeric microphone value and mute evidence are independent read authorities

For exact `Huawei TE40`, static audio normalization SHALL preserve numeric microphone configuration evidence independently from mute evidence.

When the approved TE40 audio-status parser receives a finite numeric `micValue`, the accepted room snapshot SHALL publish canonical numeric `microphone_volume`. When authoritative `MicSwitch` or equivalent approved mute evidence is present, the same snapshot SHALL independently publish canonical `microphone_muted`.

A numeric value, including `0`, SHALL NOT be interpreted as mute evidence. Mute state SHALL NOT overwrite numeric gain evidence, and numeric gain evidence SHALL NOT overwrite mute state.

This read-normalization requirement does not itself authorize `microphone_adjust` mutation.

#### Scenario: TE40 static audio contains numeric value and unmuted state

- **GIVEN** TE40 audio status contains numeric `micValue = 7`
- **AND** independent authoritative mute evidence says unmuted
- **WHEN** the room snapshot is accepted
- **THEN** `microphone_volume` is numeric `7`
- **AND** `microphone_muted` is `false`
- **AND** neither value is derived from the other

#### Scenario: TE40 micValue zero is not mute authority

- **GIVEN** TE40 audio status contains numeric `micValue = 0`
- **AND** independent authoritative mute evidence says unmuted
- **WHEN** the room snapshot is accepted
- **THEN** `microphone_volume` remains numeric `0`
- **AND** `microphone_muted` remains `false`
- **AND** the application does not fabricate a muted state from the numeric value

### Requirement: TE40 microphone-gain mutation protocol is a pre-architecture-approval gate

Before this change may receive final architecture `APPROVE`, authorized protocol discovery on TE40 SHALL establish and record in OpenSpec all of:

```text
exact state-changing method / ActionID / endpoint boundary
HTTP method where applicable
non-secret payload fields and numeric target semantics
allowed numeric range
one-button adjustment step
success / acknowledgement semantics
authoritative numeric post-write readback method and field
```

The discovered contract SHALL be reviewed against root state-changing safety before `microphone_adjust` is changed to supported. The authoritative readback is expected to remain an explicit numeric device value such as `micValue`, but architecture SHALL record the actual proven path rather than infer it.

Until that amendment is published and reviewed, TE40 gain mutation remains unavailable before room interaction admission.

#### Scenario: TE40 setter has not been proven

- **GIVEN** the exact TE40 gain-set protocol has not been captured and approved
- **WHEN** an implementation or GUI path attempts numeric microphone adjustment
- **THEN** the operation remains unsupported before device I/O
- **AND** no guessed ActionID, payload, range or step is used
- **AND** `WEB_OpenMicAPI` / `WEB_CloseMicAPI` are not repurposed as gain adjustment

#### Scenario: TE40 protocol discovery is complete

- **GIVEN** authorized hardware evidence proves the exact setter, payload, range, step and numeric readback
- **WHEN** architecture is updated for final review
- **THEN** the capability matrix and mutation contract are amended with those exact values
- **AND** implementation still does not begin until the amended architecture receives a new `APPROVE`

### Requirement: TE40 camera normalization accepts zero-to-many camera records

For exact `Huawei TE40`, `WEB_GetLocalCameraList.itemList` or its approved equivalent SHALL be treated as a zero-to-many collection. The parser SHALL NOT require at least two entries before processing camera evidence.

Each present entry SHALL be interpreted independently. An active camera MAY use the existing approved port/type lookup to resolve model evidence. A valid single returned camera SHALL publish known camera status/model evidence when available and SHALL NOT become `Нет данных` solely because a second list entry is absent.

#### Scenario: TE40 returns exactly one camera record

- **GIVEN** TE40 camera-list data contains exactly one valid camera entry
- **WHEN** exact-model camera normalization runs
- **THEN** that entry is processed
- **AND** available camera state/model evidence is published
- **AND** the parser does not require `len(itemList) >= 2`

### Requirement: CloudLink Box 310 live response semantics must be proven before parser replacement

Hardware has established that `WEB_GetCurrentAudioParam` can return multiple records containing `deviceId` and numeric-looking `curVolume`, which invalidates the old fixed-field assumption based on `mic1ValueIndex`, `mic2ValueIndex`, and `micArray*_ValIdx`.

However, the observed pair shape alone does not prove that every returned record is microphone evidence. Before final architecture `APPROVE`, authorized discovery SHALL capture a redacted complete response envelope/container and establish one of:

- the relevant collection is microphone-only; or
- the collection contains mixed roles and an authoritative microphone filter/device-role mapping is required.

The final amended parser contract SHALL specify the envelope/container path, microphone record-selection rule, accepted numeric `curVolume` rules, aggregation rule, empty/malformed behavior, exact Box identity, and display normalization. Until that contract is approved, implementation SHALL NOT replace the old parser with an unproven `max(all curVolume)` algorithm.

#### Scenario: Box response contains device-volume pairs but roles are not proven

- **GIVEN** a redacted Box response contains multiple `{deviceId, curVolume}` records
- **AND** device-role semantics have not yet been established
- **WHEN** architecture evaluates live microphone aggregation
- **THEN** it does not classify every record as microphone evidence by assumption
- **AND** no normative `max(all curVolume)` rule is approved
- **AND** response-role discovery remains a blocking architecture task

#### Scenario: Box microphone collection role is proven

- **GIVEN** authorized discovery establishes the exact response container and microphone record-selection semantics
- **WHEN** architecture is amended for final review
- **THEN** only authoritative microphone `curVolume` evidence participates in aggregation
- **AND** exact application identity remains `CloudLink Box 310`
- **AND** the resulting parser rule is testable from transport-edge response data
