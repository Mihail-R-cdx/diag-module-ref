# codec-call-log-usage-statistics Delta

## ADDED Requirements

### Requirement: Normalized call history carries typed direction and one duration presentation contract across all five codecs

For the existing five supported exact models:

```text
Huawei TE20
Huawei TE40
CloudLink Bar 310
CloudLink Box 310
Polycom RPG 310
```

each accepted normalized call-history record SHALL expose direction as a typed application semantic equivalent to:

```text
INCOMING
OUTGOING
UNKNOWN
```

when source evidence permits. Vendor-specific source values SHALL be mapped inside model-specific retrieval/normalization boundaries. Presentation SHALL NOT determine direction from model name, icon color, peer-number formatting, localized strings, record position, success/failure, or other GUI heuristics.

A source value that cannot be mapped authoritatively SHALL normalize to `UNKNOWN`; it SHALL NOT be guessed as incoming or outgoing. `UNKNOWN` presentation SHALL use a neutral/non-color cue that does not falsely claim a direction.

The existing machine-readable duration contract SHALL apply equally to all five models. A completed record with accepted non-negative duration SHALL expose/render that duration regardless of model. Missing or unparseable duration remains unavailable, remains visible, contributes zero to arithmetic, and follows the existing partial-calculation warning semantics; presentation SHALL NOT special-case Polycom as the only model whose duration may be shown.

Active records remain active and follow the existing zero-usage-until-completed contract.

#### Scenario: Incoming and outgoing records from different vendors normalize consistently

- **GIVEN** two supported model adapters each provide authoritative but vendor-specific direction evidence
- **WHEN** their records are normalized
- **THEN** the application record contains typed `INCOMING` or `OUTGOING` as appropriate
- **AND** presentation uses that typed semantic rather than a vendor/model branch

#### Scenario: Direction source is ambiguous

- **WHEN** a source record has no authoritative direction mapping
- **THEN** its normalized direction is `UNKNOWN`
- **AND** the GUI does not show a false incoming/outgoing cue

#### Scenario: Huawei or CloudLink completed call has valid duration

- **GIVEN** TE20, TE40, Bar 310, or Box 310 returns a completed call with accepted non-negative duration evidence
- **WHEN** the normalized record is presented
- **THEN** its duration is rendered using the same product semantics as Polycom RPG 310
- **AND** model identity does not suppress the duration

### Requirement: One accepted call-history snapshot drives room preview, detailed journal, duration, direction, and usage statistics

For a current exact room codec row, the modern three-row `Журнал вызовов` preview, the existing detailed call-log presentation, typed direction cues, duration display, and usage-statistics calculation SHALL consume the same accepted normalized call-history snapshot/record set for that acquisition epoch.

The GUI SHALL NOT create a second call-history parser, second chronology sort, vendor-specific preview cache, or separate statistics dataset. Existing newest-first ordering, accepted-record cap, coverage rules, source-history limitation, product-cap degradation, current-time rules, and duration arithmetic remain authoritative.

If a current accepted room preview snapshot exists, expanding the detailed journal SHALL reuse that snapshot according to the existing presentation/lifecycle contract. If no accepted current snapshot exists, the explicit detailed action SHALL start only the existing serialized exact-row call-history auxiliary acquisition.

#### Scenario: Preview and detailed journal use the same epoch

- **GIVEN** a current exact row has an accepted call-history snapshot
- **WHEN** the room preview is shown and the operator opens the detailed journal without requiring a new acquisition under the existing lifecycle contract
- **THEN** both surfaces use records from the same accepted normalized snapshot
- **AND** direction/duration/statistics semantics do not diverge between surfaces

### Requirement: Initial modern room call-history preview uses existing exact-row auxiliary ownership

When the modern room codec dashboard automatically attempts to populate its call-history preview, acquisition SHALL remain owned by the existing application/composition call-history binding and the serialized room `AUXILIARY_READ` lifecycle. Presentation SHALL only request/observe application state; it SHALL NOT call a handler/session directly, create a second worker owner, select credentials, or bypass the room interaction lane.

Automatic preview SHALL be bound to the immutable exact current row/generation. If the row collapses/switches, top full Refresh supersedes the room, the exact row becomes stale, or the acquisition otherwise loses authority, late records/completion/errors SHALL NOT populate the replacement row, open/reopen a dialog, change credential/profile memory, or produce a current-row error.

If another room network lifecycle currently owns or is retiring from the serialized lane, automatic preview SHALL obey the existing handoff/eligibility policy rather than run concurrently merely to avoid an empty card.

An ordinary preview acquisition failure that does not prove terminal loss of connection/session SHALL preserve already accepted ordinary codec status according to the existing auxiliary-read contract.

#### Scenario: Initial preview is accepted for current exact row

- **GIVEN** a current connected codec row is eligible for its approved call-history auxiliary binding
- **WHEN** automatic room preview acquisition completes for the same current row/generation
- **THEN** its accepted normalized snapshot may populate the room preview and statistics
- **AND** no second call-history network owner exists

#### Scenario: Initial preview becomes stale

- **GIVEN** automatic call-history preview is in flight for row A
- **WHEN** row A loses exact current authority before publication
- **THEN** late preview data/error/completion cannot update the newly current row
- **AND** it cannot emit a current-row call-history error

### Requirement: CloudLink Box 310 is an end-to-end call-history and usage-statistics regression oracle

Implementation SHALL include an end-to-end regression for exact `CloudLink Box 310` covering the existing application registration and approved CloudLink call-history read/session boundary through normalization into the room call-history snapshot and user-visible usage-statistics semantics.

The regression SHALL prove at minimum:

- exact application identity remains `CloudLink Box 310` and is not aliased to Bar 310;
- the approved existing call-history retrieval/session path is used without introducing a second credential source or handler-owned fallback;
- normalized newest-first records reach the room preview/detailed presentation contract;
- accepted completed duration is visible and participates in existing usage arithmetic;
- typed direction, when authoritative source evidence exists, reaches presentation without GUI string heuristics;
- current 30/90-day, source-limited, or 100-record product semantics continue to follow the existing root requirements applicable to the fixture;
- stale/superseded Box results cannot publish into a replacement row/context;
- secrets/session tokens do not appear in normalized records, public errors, or test evidence.

#### Scenario: Box 310 accepted history reaches statistics

- **GIVEN** exact `CloudLink Box 310` returns an accepted call-history dataset under the approved existing read/session path
- **WHEN** the end-to-end room call-history flow completes for the same current row/generation
- **THEN** the accepted normalized records populate the modern preview/detailed flow
- **AND** applicable usage statistics are calculated under the common product contract
- **AND** exact model identity remains `CloudLink Box 310`
