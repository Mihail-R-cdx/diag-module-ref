## ADDED Requirements

### Requirement: Codec call activity applicability and normalization are owned by the unified exact-model registry

The same unified exact application model registration that owns diagnostic and room-interaction capability dispatch SHALL be the sole applicability authority for codec call-activity projection. An exact codec registration whose approved diagnostic snapshot exposes call-state evidence SHALL explicitly declare a call-activity normalization/projection binding equivalent to `call_activity_binding_key`; applicability SHALL NOT be inferred from whether a runtime payload happens to contain a call field and SHALL NOT be maintained in a second occupancy-specific model list.

For the current change base, the following exact codec registrations already have approved diagnostic call-state evidence and therefore SHALL each declare a bound call-activity projection:

```text
Huawei TE20
Huawei TE40
CloudLink Bar 310
CloudLink Box 310
Polycom RPG 310
```

These five exact names are a baseline acceptance/test oracle for this change, not a second runtime support table. Runtime composition SHALL continue to enumerate applicability only from the unified application model registration. Bar 310 and Box 310 MAY share one normalizer implementation when their approved evidence semantics permit it, but each exact registration SHALL explicitly declare its binding. A future exact codec model whose approved diagnostic snapshot adds call-state evidence SHALL add its call-activity binding through that same unified registration in the reviewed change that adds the evidence.

For every bound exact codec model, application/model normalization SHALL project model/protocol-specific current accepted call evidence into exactly one model-neutral typed value before room-level aggregation:

```text
CallActivity.ACTIVE
CallActivity.INACTIVE
CallActivity.UNKNOWN
```

`ACTIVE` means that the exact-model normalization boundary has current accepted evidence that unambiguously proves a current call according to that model's approved call-state semantics. `INACTIVE` means that current accepted exact-model evidence unambiguously proves there is no current call. Missing, stale, failed, unsupported, contradictory, or unrecognized evidence SHALL normalize to `UNKNOWN`.

When an existing parser/handler exposes only a string-valued call state, its exact-model normalization adapter MAY map that value to `CallActivity`, but the mapping SHALL be explicit and model-scoped, SHALL prefer structured/typed protocol evidence when available, and SHALL default unrecognized values to `UNKNOWN`. Shared room or presentation code SHALL NOT classify localized labels, display strings, protocol strings, or arbitrary substrings such as `Active`, `Incoming`, `Calling`, `В звонке`, `No Call`, or similar values.

The projection SHALL reuse already accepted diagnostic/post-cycle codec evidence. Creating or updating `CallActivity` SHALL NOT add a new codec request, timer, worker, handler/session acquisition, credential attempt, retry lane, or mutation.

For `diagnostic-ui-presentation`, a relevant call-capable room codec row SHALL mean a row whose exact unified model registration declares the required bound call-activity projection. Runtime presence or absence of a `CallActivity` field SHALL NOT decide whether a registered baseline codec participates, and presentation SHALL NOT keep a parallel model list.

Application startup/composition validation SHALL fail closed when a codec registration required by this contract omits its call-activity binding or references a binding unavailable to composition. A required model SHALL NOT be silently excluded from room busy aggregation.

#### Scenario: Current baseline codec registrations all declare call activity

- **GIVEN** the current exact application registry contains `Huawei TE20`, `Huawei TE40`, `CloudLink Bar 310`, `CloudLink Box 310`, and `Polycom RPG 310`
- **WHEN** registry/composition validation runs
- **THEN** every one of those exact entries declares an available call-activity projection binding
- **AND** no occupancy-specific model support list is consulted

#### Scenario: Required call-activity binding is missing

- **GIVEN** one exact codec registration required by this contract omits its call-activity binding or names an unavailable binding
- **WHEN** application registry/composition validation runs
- **THEN** validation fails closed
- **AND** the model cannot silently disappear from room busy aggregation

#### Scenario: Exact-model active call becomes typed ACTIVE

- **GIVEN** a supported exact codec model returns current accepted call evidence that its model-specific normalization contract recognizes as a current call
- **WHEN** its bound application normalization publishes room-row call activity
- **THEN** it publishes `CallActivity.ACTIVE`
- **AND** no room GUI string parsing is required

#### Scenario: Exact-model no-call evidence becomes typed INACTIVE

- **GIVEN** a supported exact codec model returns current accepted call evidence that its model-specific normalization contract recognizes as no current call
- **WHEN** its bound application normalization publishes room-row call activity
- **THEN** it publishes `CallActivity.INACTIVE`

#### Scenario: Unknown call evidence fails closed

- **GIVEN** a codec call-state value is missing, stale, failed, contradictory, or not explicitly recognized by that exact model's normalization mapping
- **WHEN** the bound application normalization projects call activity
- **THEN** it publishes `CallActivity.UNKNOWN`
- **AND** shared room/presentation code does not infer activity from string fragments
