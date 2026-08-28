## ADDED Requirements

### Requirement: Codec call activity is normalized to typed model-neutral evidence before room aggregation

For every exact codec model whose existing diagnostic path exposes a current call-state value that is consumed by the room occupancy presentation, the application SHALL project model/protocol-specific call evidence into a model-neutral typed value before room-level aggregation:

```text
CallActivity.ACTIVE
CallActivity.INACTIVE
CallActivity.UNKNOWN
```

The typed projection SHALL be owned by the model-specific parser/adapter/application normalization boundary, not by the room GUI. The room presentation SHALL NOT classify localized labels, display strings, protocol strings, or arbitrary substrings such as `Active`, `Incoming`, `Calling`, `В звонке`, `No Call`, or similar values on its own.

`ACTIVE` means that the exact-model normalization boundary has current accepted evidence that unambiguously proves a current call according to that model's existing call-state semantics. `INACTIVE` means that current accepted exact-model evidence unambiguously proves there is no current call. Missing, stale, failed, unsupported, contradictory, or unrecognized evidence SHALL normalize to `UNKNOWN`.

When an existing parser/handler currently exposes only a string-valued call state, the exact-model normalization adapter MAY map that value to `CallActivity`, but the mapping SHALL be explicit and model-scoped, SHALL prefer structured/typed protocol evidence when available, and SHALL default unrecognized values to `UNKNOWN`. Generic substring/keyword heuristics in shared room or presentation code are forbidden.

The projection SHALL reuse already accepted diagnostic/post-cycle codec evidence. Creating `CallActivity` SHALL NOT add a new codec request, timer, worker, handler/session acquisition, credential attempt, retry lane, or mutation.

#### Scenario: Exact-model active call becomes typed ACTIVE

- **GIVEN** a supported exact codec model returns current accepted call evidence that its model-specific normalization contract recognizes as a current call
- **WHEN** application normalization publishes room-row call activity
- **THEN** it publishes `CallActivity.ACTIVE`
- **AND** no room GUI string parsing is required

#### Scenario: Exact-model no-call evidence becomes typed INACTIVE

- **GIVEN** a supported exact codec model returns current accepted call evidence that its model-specific normalization contract recognizes as no current call
- **WHEN** application normalization publishes room-row call activity
- **THEN** it publishes `CallActivity.INACTIVE`

#### Scenario: Unknown call text fails closed

- **GIVEN** a codec call-state value is missing, stale, failed, contradictory, or not explicitly recognized by that exact model's normalization mapping
- **WHEN** the application projects call activity
- **THEN** it publishes `CallActivity.UNKNOWN`
- **AND** shared room/presentation code does not infer activity from string fragments
