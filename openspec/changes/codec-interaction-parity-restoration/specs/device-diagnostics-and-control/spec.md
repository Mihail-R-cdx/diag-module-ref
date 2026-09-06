## ADDED Requirements

### Requirement: Room codec interactions preserve proven pre-redesign model behavior

For Huawei TE20, Huawei TE40, CloudLink Bar 310, CloudLink Box 310, and Polycom RPG 310, the common room codec dashboard SHALL preserve the behavior of supported codec interactions that were working immediately before `codec-diagnostic-modern-ui`, using `c442152077dd8aa6251f1d8be9fc98b765406dbd` as the behavioral reference unless current real-device evidence proves that a referenced operation is no longer valid.

The application SHALL preserve current exact-row authority, currentness, typed failure, credential ownership, redaction, and background-I/O rules. The behavioral reference SHALL NOT authorize direct widget-to-handler calls, a second capability registry, blind mutation replay, or restoration of an operation that current approved capability explicitly keeps unsupported without authoritative reconciliation evidence.

Supported behavior SHALL be restored at the application/controller/session boundary rather than by making the reusable legacy `CodecScreen` an authority for room interaction.

#### Scenario: Existing protocol operation worked before codec redesign

- **GIVEN** a supported codec operation used a model-specific handler/session path successfully before `codec-diagnostic-modern-ui`
- **AND** current handler/device evidence does not invalidate that path
- **WHEN** the same operation is initiated from the current room codec dashboard
- **THEN** the current application preserves equivalent model-specific request and authoritative readback semantics
- **AND** the new room presentation does not replace the working protocol behavior with synthetic snapshot-only behavior

#### Scenario: Old visual affordance was not a proven network capability

- **GIVEN** the legacy codec screen displayed an affordance for an operation that lacks authoritative target/readback support under current approved capability
- **WHEN** parity is evaluated
- **THEN** the visual affordance alone does not authorize network capability
- **AND** the operation remains disabled or locally unsupported until separately proven and approved

### Requirement: Supported codec audio mutations use targeted authoritative readback

A supported room codec audio mutation SHALL use one serialized exact-model operation owner and the smallest model-supported authoritative readback that can confirm the changed field. A full codec diagnostic refresh SHALL NOT be required solely to confirm one audio field when the same model already exposes a proven authoritative getter for that field.

Successful mutation transport/ACK SHALL remain non-authoritative. Only the readback result MAY publish the reconciled canonical field. If readback cannot confirm final state, prior accepted state SHALL remain stale/unconfirmed and current mutation safety rules SHALL apply; the application SHALL NOT blindly repeat the state-changing operation.

#### Scenario: Speaker volume adjustment succeeds

- **GIVEN** the exact codec model supports speaker-volume adjustment and authoritative speaker-volume readback
- **WHEN** the operator presses `+` or `-`
- **THEN** one exact target is computed from current authoritative evidence
- **AND** the model-specific set operation runs off the GUI thread
- **AND** the model-specific speaker-volume getter confirms final state
- **AND** the reconciled speaker field is published without requiring an unrelated full diagnostic refresh
- **AND** the room interaction lock is released after bounded cleanup

#### Scenario: Audio mutation readback fails

- **WHEN** a codec audio mutation may have been delivered but targeted authoritative readback cannot confirm final state
- **THEN** the mutation is not replayed automatically
- **AND** prior accepted state remains stale/unconfirmed
- **AND** current blocked/unconfirmed recovery rules apply

### Requirement: Exact-model codec capability and actionable presentation agree

The exact model registration SHALL remain the sole network-capability authority for codec controls. A normal actionable room-dashboard control SHALL be enabled only when that exact model advertises the corresponding supported operation and the current row/lifecycle state permits it.

A fixed visual affordance for an unsupported operation MAY remain only when it is disabled or unmistakably local-only and resolves before room interaction admission. It SHALL NOT appear equivalent to an enabled supported device action that predictably fails only after the user activates it.

CloudLink Bar 310 and Box 310 microphone gain SHALL remain network-unsupported in this change unless a separate approved contract establishes authoritative target selection and reconciliation.

#### Scenario: Unsupported reboot is rendered

- **GIVEN** the exact codec capability declares reboot unsupported
- **WHEN** the room codec dashboard is rendered
- **THEN** reboot is not presented as a normal enabled device action
- **AND** activating any retained local-only affordance performs no room network admission or device I/O

#### Scenario: CloudLink microphone gain remains unsupported

- **GIVEN** exact model is CloudLink Bar 310 or CloudLink Box 310
- **WHEN** the dashboard renders microphone gain affordances
- **THEN** they are disabled or clearly local-only
- **AND** no gain mutation is admitted by this change
