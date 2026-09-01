# device-diagnostics-and-control Delta

## ADDED Requirements

### Requirement: Room codec dashboard data uses one model-neutral normalized presentation projection

For every current exact codec registration, the room diagnostic/application boundary SHALL expose a model-neutral codec presentation projection sufficient for the fixed dashboard slots without making raw model-specific parser text or standalone Qt widgets into shared presentation authority.

The projection SHALL distinguish usable current evidence from absence/unknown and SHALL provide safe values where current approved diagnostic evidence exists for:

```text
model
mac_address
serial_number
platform
software_version
microphone
camera
call_status
presentation_status
sip_h323_registration
microphone_level
microphone_volume_or_state
speaker_volume_or_state
```

A model MAY legitimately have no current evidence for one or more slots. Absence SHALL remain absence and presentation SHALL render `Нет данных`; this change SHALL NOT add protocol reads solely to make every slot non-empty.

Existing typed `CallActivity` remains the model-neutral call-activity authority where applicable. Shared room presentation SHALL prefer typed/structured normalization where one exists and SHALL NOT derive shared semantic status by substring matching localized/model-specific call strings.

#### Scenario: Current model lacks platform evidence

- **GIVEN** the exact codec diagnostic snapshot has no current approved platform evidence
- **WHEN** model-neutral codec presentation is projected
- **THEN** `platform` remains unavailable
- **AND** no parser default, model string or standalone UI label is substituted as device evidence

### Requirement: Codec room-control adapters reuse approved typed operations and explicitly declare unsupported operations

The room codec-control capability SHALL reuse existing approved safe codec operation/readback semantics where available rather than duplicating protocol command grammar in the room GUI. Each exact codec registration SHALL bind an application/core codec-control adapter (or equivalent existing exact-registry-owned binding) that can answer operation support before network acquisition and can construct the typed desired-state/readback operation for supported controls.

Current exact codec registrations for acceptance are:

```text
Huawei TE20
Huawei TE40
CloudLink Bar 310
CloudLink Box 310
Polycom RPG 310
```

These names SHALL be test oracles for the current baseline only; runtime SHALL iterate/resolve the unified exact-model registry rather than consult a second hard-coded control-model list.

Standalone `CodecScreen` demonstrates existing safe speaker/microphone interactive semantics but is not itself a room capability authority. A room adapter MAY reuse the same underlying application/core operation definitions only when the exact model actually supports the required method/readback contract. A standalone widget branch, handler attribute probe or visually present button SHALL NOT silently promote support.

For the current baseline, implementation SHALL preserve the proven speaker-volume desired-state behavior for all five codecs where the existing exact handlers/readbacks support it. Microphone numeric adjustment and mute support SHALL be declared independently because some current models expose microphone mute/state semantics rather than a numeric gain adjustment. A model without a proven numeric microphone-adjust contract SHALL declare `microphone_adjust` unsupported rather than reinterpret mute/state as gain. Reboot SHALL remain unsupported unless current approved source/operation contracts already establish a safe typed reboot plus reconciliation path; this change SHALL NOT invent one.

#### Scenario: Microphone has mute but no numeric gain contract

- **GIVEN** an exact codec model has an approved microphone mute/state desired-state operation but no approved numeric microphone-adjust operation
- **WHEN** its room codec-control capability is composed
- **THEN** `microphone_mute` may be supported
- **AND** `microphone_adjust` is explicitly unsupported
- **AND** shared GUI code does not reinterpret mute state as a numeric gain range

#### Scenario: No approved reboot contract exists

- **GIVEN** an exact codec registration has no current approved typed reboot operation with required safe lifecycle/readback semantics
- **WHEN** room codec-control capability is composed
- **THEN** reboot is explicitly unsupported
- **AND** no raw handler command is invented by this change

### Requirement: Codec audio mutation target and reconciliation evidence are model-safe and fail closed

A supported room codec audio desired-state operation SHALL use the same exact model/IP credential and transport safety boundaries as existing codec interaction. Before sending, the adapter SHALL validate the requested absolute target against its exact model operation range/state contract. Invalid, missing or contradictory targets SHALL fail before state-changing I/O.

Readback/reconciliation SHALL compare model-neutral normalized current state with the exact desired target. A command return value, ACK, HTTP success, SSH/Telnet prompt, empty error, or user-facing string SHALL NOT by itself confirm final audio state.

For relative-button intent represented as an absolute target, retry/fallback safety SHALL follow the existing relative-as-absolute operation contract: a structured authentication rejection may advance credentials only when the operation is proven not delivered under the applicable mutation-safety gate; after possible delivery, the operation SHALL NOT be blindly repeated with another credential.

#### Scenario: Desired target is outside exact model range

- **WHEN** a codec-control adapter receives an absolute audio target outside its exact approved model range
- **THEN** the operation fails closed before handler/session acquisition or state-changing send
- **AND** authoritative row data is unchanged

#### Scenario: Send appears successful but readback differs

- **WHEN** a supported audio mutation send returns apparent success
- **AND** mandatory readback does not prove the desired normalized state
- **THEN** the operation remains unconfirmed/failed under the room mutation contract
- **AND** the desired value is not written optimistically into authoritative row state

### Requirement: Room call-log preview reuses existing model call-log normalization for all registered codecs

Automatic inline call-log preview and the detailed call-log window SHALL consume the same application-owned normalized call-log result for the exact model. This change SHALL NOT create a second parser/schema solely for the three-row preview.

Every current exact codec registration that already declares the room call-log auxiliary binding SHALL remain eligible for the preview. Model-specific acquisition may differ, but accepted output SHALL provide deterministic record ordering and safe normalized fields sufficient for direction, peer/display identity and timestamp presentation. If the acquisition/normalization cannot prove records, the preview result is unavailable/empty rather than fabricated.

#### Scenario: Preview and detailed window receive the same accepted result

- **GIVEN** a current call-log auxiliary acquisition is accepted for an exact codec row
- **WHEN** inline preview and detailed presentation consume it
- **THEN** both derive from the same normalized full result bound to that row/generation
- **AND** the preview does not run a separate model parser or alter record meaning
