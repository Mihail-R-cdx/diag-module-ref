# device-diagnostics-and-control Delta

## REMOVED Requirements

### Requirement: Room call-log preview uses one typed newest-first chronology authority

**Reason:** The old requirement bound automatic preview and detailed presentation to one accepted result. That coupling no longer matches the approved distinct-acquisition architecture.

**Migration:** The added requirement below replaces it. It preserves the shared typed schema, parser/normalizer, chronology, newest-first, and exact-model retrieval authority while separating automatic-preview and explicit-detail acquisition/result authority.

## ADDED Requirements

### Requirement: Room call-log preview and detail share typed chronology authority across separate acquisitions

Automatic inline call-log preview and the detailed call-log window SHALL use the same application-owned normalized call-history record schema, parser/normalizer semantics, chronology rules, and exact-model retrieval authority. This change SHALL NOT create a second parser/schema solely for the three-row preview or for the fresh detailed-journal load.

Automatic preview and explicit detailed opening MAY nevertheless consume **different accepted `CallHistorySnapshot` instances (or equivalent typed normalized results)** because they are distinct acquisition epochs. The automatic-preview snapshot is authoritative only for the preview acquisition that produced it. Every explicit detailed-journal opening is a fresh serialized call-log acquisition and its detailed rows/statistics SHALL use only that explicit load's current accepted normalized result.

The normalized result for every acquisition SHALL establish chronology before presentation. Records SHALL already be ordered newest-first using typed comparable `start_at` evidence. A record with no parseable/comparable `start_at` SHALL sort after every record with proven chronology. Ordering among equal timestamps or records lacking chronology SHALL preserve deterministic normalized acceptance/source order; presentation SHALL NOT sort localized `start_display` strings lexicographically and SHALL NOT guess missing timestamps.

For an accepted automatic-preview acquisition, the room preview SHALL take the first three records of that accepted newest-first normalized result. For an accepted explicit detailed acquisition, the detailed call-log window and usage-statistics calculation SHALL consume that explicit load's normalized result under the existing call-log product contract. All five current codec call-log adapters SHALL preserve/use the same model-neutral chronology and record semantics in both acquisition types.

Because preview and detailed opening are distinct acquisition epochs, their accepted datasets MAY differ when device history changes between reads. Such difference SHALL NOT be treated as parser divergence when both snapshots were independently normalized under the same chronology/schema contract. Presentation SHALL NOT force the detailed load back to the older automatic-preview snapshot merely to make both surfaces identical.

If an acquisition/normalization cannot prove records, that acquisition's result is unavailable/empty rather than fabricated. Safe display timestamp text may remain present for a record whose typed chronology is unavailable, but that text SHALL NOT promote the record ahead of timestamped records or become sorting authority. A stale/cancelled/superseded acquisition result SHALL NOT become authority for another acquisition epoch or replacement row/context.

#### Scenario: Preview and detailed opening use one normalization authority but separate accepted snapshots

- **GIVEN** an automatic preview has accepted normalized call history for a current exact codec row
- **WHEN** the operator later explicitly opens the detailed journal and a fresh call-log acquisition is accepted
- **THEN** preview remains derived from the automatic-preview snapshot
- **AND** detailed rows/statistics derive from the fresh explicit snapshot
- **AND** both snapshots use the same application-owned record schema, exact-model normalizer, and newest-first chronology rules
- **AND** no second GUI parser or chronology implementation exists

#### Scenario: Device history changes between preview and explicit opening

- **GIVEN** device call history changes after automatic preview was accepted
- **WHEN** a later fresh explicit detailed acquisition is accepted
- **THEN** the detailed snapshot MAY contain newer or otherwise different accepted records than the preview snapshot
- **AND** the implementation does not overwrite the fresh detailed result with the older preview solely to force dataset identity
- **AND** both datasets remain comparable under the same normalized semantics

#### Scenario: Missing timestamp does not become newest

- **GIVEN** accepted normalized call records include records with typed `start_at` and one record with only unparseable/missing chronology
- **WHEN** ordering is established for either automatic preview or fresh detailed acquisition
- **THEN** all records with proven timestamps are ordered newest-first ahead of the unknown-chronology record
- **AND** no display-string sort or guessed timestamp is used

#### Scenario: Stale acquisition does not cross epochs

- **GIVEN** a preview or explicit detailed call-log acquisition loses exact row/generation/currentness before acceptance
- **WHEN** its late normalized result arrives
- **THEN** that result does not become authority for the other acquisition epoch or a replacement row/context
- **AND** no GUI cache promotes it to current call-history state

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
