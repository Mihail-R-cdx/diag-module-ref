# device-diagnostics-and-control Delta

## ADDED Requirements

### Requirement: Modern room codec speaker volume exposes accepted display percentage without replacing mutation authority

For exact modern room codec presentation, the application/model-neutral projection SHALL expose an optional accepted field equivalent to:

```text
speaker_volume_percent: Optional[int]
```

When present, `speaker_volume_percent` SHALL be an integer in the inclusive range `0..100` and SHALL represent current accepted exact-row speaker-volume evidence mapped to presentation percentage according to the exact model's proven existing source semantics. It is a display projection only.

The current baseline registrations are:

```text
Huawei TE20
Huawei TE40
CloudLink Bar 310
CloudLink Box 310
Polycom RPG 310
```

For every baseline model, any source-to-percentage transformation SHALL live in the exact-model adapter/application projection or another application-owned normalization boundary, not in Qt presentation. The mapping SHALL be explicit and regression-tested against the existing accepted source semantics for that model. Presentation SHALL NOT infer min/max from runtime observations, clamp an unknown wire scale into a percentage, parse a localized string, or use widget state/history/defaults.

Accepted exact numeric zero SHALL remain authoritative `0%`. If the current accepted snapshot has no usable speaker-volume evidence, the source semantics cannot be proven into a percentage, or the evidence is stale/malformed, `speaker_volume_percent` SHALL be absent rather than fabricated.

The existing canonical/model-specific speaker volume used to create safe mutation targets and to reconcile final state SHALL remain separate authority. `speaker_volume_percent` SHALL NOT be reverse-converted by presentation into a wire target, SHALL NOT make a requested-but-unreconciled target final state, and SHALL NOT authorize a mutation unsupported by unified capability authority.

A successful state-changing send/ACK SHALL NOT update accepted `speaker_volume_percent` by itself. The displayed accepted percentage MAY change only when current exact-row application state accepts authoritative status/reconciliation evidence under `room-device-interaction-lifecycle`.

#### Scenario: Accepted zero speaker volume is displayed as zero percent

- **GIVEN** exact-model accepted source semantics normalize current speaker volume to zero percent
- **WHEN** the application publishes the modern room projection
- **THEN** `speaker_volume_percent` is present as `0`
- **AND** presentation can distinguish it from missing data

#### Scenario: Speaker source cannot be mapped authoritatively

- **GIVEN** the current accepted exact-row snapshot does not provide speaker evidence with a proven source-to-percentage mapping
- **WHEN** the application builds the presentation projection
- **THEN** `speaker_volume_percent` is absent
- **AND** no runtime range guess, default value, or stale widget value is substituted

#### Scenario: Mutation request has not reconciled

- **GIVEN** an admitted speaker-volume mutation requested a new target
- **AND** authoritative reconciliation has not yet accepted final state
- **WHEN** presentation state is published
- **THEN** the requested target alone does not become accepted `speaker_volume_percent`
- **AND** prior accepted state remains prior/stale according to the room lifecycle until reconciliation resolves the operation
