# device-diagnostics-and-control Delta

## ADDED Requirements

### Requirement: Modern room codec speaker volume exposes accepted display percentage without replacing mutation authority

For exact modern room codec presentation, the application/model-neutral projection SHALL expose an optional accepted field equivalent to:

```text
speaker_volume_percent: Optional[int]
```

When present, `speaker_volume_percent` SHALL be an integer in the inclusive range `0..100` and SHALL represent current accepted exact-row speaker-volume evidence mapped by the normative application-owned conversion below. It is display-only accepted evidence and SHALL NOT become mutation authority.

The existing unified exact-model registry remains the sole source of the canonical speaker range. Current approved baseline ranges are:

```text
Huawei TE20          minimum=0   maximum=21
Huawei TE40          minimum=0   maximum=21
CloudLink Bar 310    minimum=0   maximum=15
CloudLink Box 310    minimum=0   maximum=15
Polycom RPG 310      minimum=0   maximum=100
```

For accepted numeric speaker volume `V`, registry minimum `MIN`, and registry maximum `MAX`, the application projection SHALL calculate percentage only when `MAX > MIN` and `MIN <= V <= MAX`:

```text
scaled  = 100 * (V - MIN) / (MAX - MIN)
percent = floor(scaled + 0.5)
```

This is nearest-integer rounding with half values rounded upward for this non-negative closed range. The application SHALL NOT clamp an out-of-range source value into the display range. Out-of-range, malformed, stale, or missing speaker evidence SHALL produce no accepted `speaker_volume_percent`.

The conversion SHALL live in the exact-model adapter/application projection or another application-owned normalization boundary using the existing unified registry. Presentation SHALL NOT maintain a second model-range table, infer min/max from runtime observations, parse localized strings, perform its own conversion, or use widget state/history/defaults.

Current acceptance oracles SHALL include:

```text
Huawei TE20 / TE40
  0  -> 0%
  10 -> 48%
  21 -> 100%

CloudLink Bar 310 / CloudLink Box 310
  0  -> 0%
  7  -> 47%
  15 -> 100%

Polycom RPG 310
  0   -> 0%
  42  -> 42%
  100 -> 100%
```

If current remote source changes any of these approved baseline registry bounds before implementation, implementation SHALL stop and return for architecture review rather than silently adopting a different user-visible percentage scale.

The existing canonical/model-specific speaker volume used to create safe mutation targets and reconcile final state SHALL remain separate authority. `speaker_volume_percent` SHALL NOT be reverse-converted by presentation into a wire target, SHALL NOT make a requested-but-unreconciled target final state, and SHALL NOT authorize an operation unsupported by unified capability authority.

A successful send/ACK SHALL NOT update accepted `speaker_volume_percent` by itself. The displayed accepted percentage MAY change only when current exact-row application state accepts authoritative status/reconciliation evidence under `room-device-interaction-lifecycle`.

#### Scenario: Accepted zero is authoritative zero percent

- **GIVEN** current accepted speaker volume equals exact registry minimum zero
- **WHEN** the application publishes modern room codec presentation state
- **THEN** `speaker_volume_percent` is present as `0`
- **AND** presentation can distinguish it from missing data

#### Scenario: Bar or Box maximum maps to one hundred percent

- **GIVEN** exact model is `CloudLink Bar 310` or `CloudLink Box 310`
- **AND** current accepted speaker volume is `15`
- **WHEN** application projection uses the approved `0..15` registry range
- **THEN** `speaker_volume_percent` is `100`
- **AND** it is not displayed as `15%`

#### Scenario: TE intermediate value uses approved deterministic rounding

- **GIVEN** exact model is `Huawei TE20` or `Huawei TE40`
- **AND** current accepted speaker volume is `10`
- **WHEN** application projection uses the approved `0..21` range
- **THEN** `speaker_volume_percent` is `48`

#### Scenario: Source is outside approved registry range

- **GIVEN** accepted source evidence cannot be validated inside the exact model's approved registry bounds
- **WHEN** presentation projection is built
- **THEN** `speaker_volume_percent` is absent
- **AND** no clamp, guessed range, or stale widget value is substituted

#### Scenario: Mutation request has not reconciled

- **GIVEN** an admitted speaker-volume mutation requested a new target
- **AND** authoritative reconciliation has not yet accepted final state
- **WHEN** presentation state is published
- **THEN** the requested target alone does not become accepted `speaker_volume_percent`
- **AND** prior accepted state remains prior/stale according to the room lifecycle until reconciliation resolves the operation
