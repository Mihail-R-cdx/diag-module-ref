# codec-call-log-usage-statistics Delta

## ADDED Requirements

### Requirement: Normalized call history carries typed direction and common duration semantics across all five codecs

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

A source value that cannot be mapped authoritatively SHALL normalize to `UNKNOWN`; it SHALL NOT be guessed as incoming or outgoing.

The visible semantic mapping SHALL be deterministic:

```text
INCOMING -> incoming semantic cue with non-color/accessibility meaning `Входящий`
OUTGOING -> outgoing semantic cue with non-color/accessibility meaning `Исходящий`
UNKNOWN  -> neutral cue with non-color/accessibility meaning `Направление неизвестно`
```

The concrete glyph or Qt asset MAY vary, but the semantic role binding SHALL NOT be swapped.

The existing machine-readable duration contract SHALL apply equally to all five models. A completed record with accepted non-negative duration SHALL expose/render that duration regardless of model. Missing or unparseable duration remains unavailable, remains visible, contributes zero to arithmetic, and follows the existing partial-calculation warning semantics. Active records remain active and follow the existing zero-usage-until-completed contract.

#### Scenario: Incoming and outgoing records normalize and render consistently

- **GIVEN** supported adapters provide authoritative vendor-specific direction evidence
- **WHEN** their records are normalized and presented
- **THEN** the application record contains `INCOMING` or `OUTGOING` as appropriate
- **AND** the visible semantic cue/accessibility role matches `Входящий` or `Исходящий` respectively
- **AND** the GUI does not swap roles through a vendor/model-specific branch

#### Scenario: Direction source is ambiguous

- **WHEN** a source record has no authoritative direction mapping
- **THEN** its normalized direction is `UNKNOWN`
- **AND** the GUI uses a neutral cue whose semantic meaning is direction unknown

#### Scenario: Huawei or CloudLink completed call has valid duration

- **GIVEN** TE20, TE40, Bar 310, or Box 310 returns a completed call with accepted non-negative duration evidence
- **WHEN** the normalized record is presented
- **THEN** its duration is rendered using the same product semantics as Polycom RPG 310
- **AND** model identity does not suppress the duration

### Requirement: Automatic room preview and explicit detailed journal preserve separate acquisition epochs

For a current exact room codec row, the automatic modern room `Журнал вызовов` preview SHALL consume only the accepted normalized result of its automatic-preview acquisition epoch.

The existing explicit-opening freshness contract remains authoritative: every explicit `Развернуть` / detailed call-log dialog opening SHALL begin a fresh serialized exact-row read-only acquisition even when a current automatic-preview snapshot already exists. The automatic-preview snapshot SHALL NOT substitute for that fresh explicit acquisition.

After the fresh explicit acquisition accepts data, the detailed dialog, its record presentation, direction/duration fields, and usage-statistics calculation SHALL consume that explicit-load accepted normalized result. Expanding/collapsing sections within the already-open detailed dialog MAY reuse that explicit-load data and SHALL NOT trigger another device request, consistent with the existing root requirement.

The GUI SHALL NOT create a second parser, second chronology sort, vendor-specific preview cache, or separate statistics dataset. The room preview and detailed dialog MAY therefore display data from different acquisition epochs while preserving identical normalization and calculation semantics.

#### Scenario: Existing preview does not replace fresh explicit acquisition

- **GIVEN** a current exact codec row already has an accepted automatic-preview snapshot
- **WHEN** the operator activates `Развернуть` or otherwise explicitly opens the detailed journal
- **THEN** a fresh serialized exact-row `AUXILIARY_READ` is started
- **AND** the automatic-preview snapshot is not treated as the detailed load result
- **AND** the detailed dialog/statistics publish only from the fresh accepted explicit acquisition

#### Scenario: Detailed dialog section toggle reuses one explicit load

- **GIVEN** one explicit detailed-journal acquisition has completed and its dialog is open
- **WHEN** the operator expands or collapses the journal section inside that dialog
- **THEN** already accepted data from that explicit load is reused
- **AND** no additional device request is started solely for the section toggle

### Requirement: Initial modern room call-history preview admits exactly one automatic attempt per eligible expansion epoch

When the modern room codec dashboard has an eligible exact codec expansion epoch under the existing `room-device-interaction-lifecycle` contract, the application SHALL admit exactly one automatic call-history preview intent through the existing serialized room `AUXILIARY_READ` authority.

Admission is mandatory for the eligible epoch. Duplicate Qt expansion notifications, render/rebuild, resize, repaint, hover, or theme switching SHALL NOT admit a second automatic intent for the same expansion epoch.

If the exact row becomes expanded before the automatic room cycle is terminal, application authority SHALL retain the current expansion epoch and SHALL admit its one automatic preview intent after the room cycle becomes terminal when the same exact row/epoch remains current, connected/usable, and call-log capable. The pre-terminal expansion itself SHALL NOT start device I/O.

If another lifecycle owns or is retiring from the serialized lane when the automatic preview is admitted, the admitted preview remains pending behind the existing lifecycle/handoff boundary. It SHALL NOT be silently dropped merely because the lane is busy, and it SHALL NOT acquire handler/session resources concurrently. Later stale, cancelled, superseded, or failed-currentness/cleanup gates MAY prevent device I/O.

Presentation SHALL only request/observe application state; it SHALL NOT call a handler/session directly, create a second worker owner, select credentials, or bypass the room interaction lane.

#### Scenario: Post-terminal expansion admits exactly one preview

- **GIVEN** the room cycle is terminal and a connected/usable call-log-capable codec row is collapsed
- **WHEN** the row transitions to a new current expansion epoch
- **THEN** exactly one automatic preview intent is admitted through the serialized auxiliary lane
- **AND** duplicate Qt notifications or re-rendering do not admit another intent for that epoch

#### Scenario: Busy lane delays but does not drop the admitted preview

- **GIVEN** the current expansion epoch has admitted its mandatory automatic preview intent
- **AND** another lifecycle owns or is retiring from the serialized lane
- **WHEN** the preview is not yet network-eligible
- **THEN** the preview remains pending under application authority without concurrent handler/session acquisition
- **AND** it is not silently discarded solely because the lane is busy
- **AND** later currentness/cancellation/supersession rules may still prevent I/O

#### Scenario: Initial preview becomes stale

- **GIVEN** automatic preview is pending or in flight for row A
- **WHEN** row A loses exact current authority before publication
- **THEN** late preview data/error/completion cannot update the replacement row
- **AND** it cannot emit a current-row call-history error

### Requirement: CloudLink Box 310 is an end-to-end call-history and usage-statistics regression oracle

Implementation SHALL include an end-to-end regression for exact `CloudLink Box 310` covering application registration and approved CloudLink call-history read/session boundary through normalization into both the automatic room-preview flow and a fresh explicit detailed-journal acquisition.

The regression SHALL prove at minimum:

- exact application identity remains `CloudLink Box 310` and is not aliased to Bar 310;
- the approved existing call-history retrieval/session path is used without a second credential source or handler-owned fallback;
- normalized newest-first records reach the automatic room preview;
- explicit detailed opening performs a fresh serialized acquisition even when preview data already exists;
- accepted completed duration is visible and participates in existing usage arithmetic;
- typed direction, when authoritative source evidence exists, reaches the correct visible semantic cue role without GUI heuristics;
- current 30/90-day, source-limited, or 100-record product semantics continue to follow the existing root requirements applicable to the fixture;
- stale/superseded Box results cannot publish into a replacement row/context;
- secrets/session tokens do not appear in normalized records, public errors, or test evidence.

#### Scenario: Box 310 automatic preview and fresh detailed load remain distinct

- **GIVEN** exact `CloudLink Box 310` has accepted automatic-preview history
- **WHEN** the operator explicitly opens the detailed journal
- **THEN** Box identity remains exact
- **AND** a fresh approved call-history read/session acquisition occurs
- **AND** the detailed presentation/statistics publish from that fresh accepted result rather than the prior preview snapshot
