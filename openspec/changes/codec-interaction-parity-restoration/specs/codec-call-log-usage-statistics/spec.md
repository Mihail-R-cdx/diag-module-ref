## MODIFIED Requirements

### Requirement: Automatic room preview and explicit detailed journal preserve separate acquisition epochs

For a current exact room codec row, the automatic modern room `Журнал вызовов` preview SHALL remain a distinct presentation dataset from every explicit detailed-journal load. Under this amendment, the automatic preview dataset comes from one mandatory fresh **initial call-history acquisition** for the current room generation/exact row after the initial diagnostic becomes accepted/usable and before the first eligible LIVE start.

The initial acquisition SHALL use the approved exact-model call-history path, normalize records through the existing shared chronology contract, and publish at most the three newest records into preview-owned application state. It is mandatory network acquisition for every supported call-log-capable codec row; it SHALL NOT be replaced by a LIVE-priority local skip. If the initial acquisition reaches a terminal ordinary no-data/parse/business failure, the preview may remain empty/unavailable and LIVE may still start after bounded cleanup. Typed connection/session/authentication failures follow existing degradation rules.

Only an accepted normalized initial-preview result MAY populate automatic inline preview rows. A failed/no-data result creates no accepted call-history dataset and SHALL NOT be promoted into detailed rows or usage statistics.

The existing explicit-opening freshness contract remains authoritative: every explicit `Развернуть` / detailed call-log dialog opening SHALL begin a fresh serialized exact-row read-only acquisition even when a current three-record initial preview already exists. The initial-preview snapshot SHALL NOT substitute for that fresh explicit acquisition.

If LIVE owns the exact row when the explicit opening is requested, LIVE SHALL retire through the existing bounded room-lifecycle handoff before the explicit `AUXILIARY_READ` acquires handler/session resources. Only the fresh explicit result accepted for the same current exact row/generation/currentness MAY populate detailed rows and usage statistics for that opening.

Expanding/collapsing sections within an already-open detailed dialog MAY reuse that explicit-load data and SHALL NOT trigger another device request. The GUI SHALL NOT create a second parser, chronology sort, vendor-specific preview cache, or separate statistics dataset.

#### Scenario: Existing preview does not replace fresh explicit acquisition

- **GIVEN** a current exact codec row already has an accepted automatic initial-preview snapshot containing up to three newest calls
- **WHEN** the operator activates `Развернуть` or otherwise explicitly opens the detailed journal
- **THEN** a fresh serialized exact-row `AUXILIARY_READ` is started
- **AND** the initial-preview snapshot is not treated as the detailed load result
- **AND** the detailed dialog/statistics publish only from the fresh accepted explicit acquisition

#### Scenario: Detailed dialog section toggle reuses one explicit load

- **GIVEN** one explicit detailed-journal acquisition has completed and its dialog is open
- **WHEN** the operator expands or collapses the journal section inside that dialog
- **THEN** already accepted data from that explicit load is reused
- **AND** no additional device request is started solely for the section toggle

#### Scenario: LIVE-priority local preview does not satisfy explicit detail

- **GIVEN** the legacy architecture allowed an automatic preview to complete locally without data when LIVE had priority
- **WHEN** the amended initial-preview lifecycle is evaluated
- **THEN** that local-skip behavior is superseded and does not satisfy the mandatory initial preview acquisition
- **AND** initial call-history acquisition occurs before first LIVE start for the current generation/exact row
- **WHEN** the operator later explicitly opens the detailed journal
- **THEN** one fresh serialized exact-row call-log `AUXILIARY_READ` is still required

### Requirement: Initial modern room call-history preview admits exactly one automatic attempt per eligible expansion epoch

The requirement name is preserved for root-spec/archive compatibility, but the amended acquisition boundary is application-owned room-generation state rather than expansion-triggered network work.

For each current connected/usable exact codec row whose unified registration advertises the call-log auxiliary binding, the application SHALL admit exactly one fresh initial call-history preview **network acquisition per room generation/exact row** after the automatic room diagnostic becomes accepted/usable and before the first eligible LIVE start. The acquisition SHALL complete or reach a bounded terminal failure before LIVE is first admitted for that row/generation.

The accepted result SHALL be normalized newest-first and preview-owned application state SHALL retain at most the first three records. Duplicate rendering, Qt expansion notifications, collapse/re-expand, resize, repaint, hover, theme switching, or LIVE continuation/resume SHALL NOT create another automatic preview network request in the same room generation.

A row expansion epoch remains relevant only to presentation bookkeeping: when the operator expands a row after an accepted initial preview exists, the dashboard may render the already accepted up-to-three-record preview without network admission. Expanding a row SHALL NOT be the trigger for the initial network acquisition and SHALL NOT wait for a later LIVE idle window.

If the row becomes expanded before the automatic room cycle is terminal, presentation MAY show loading/neutral state. After the same row becomes accepted/usable, the application performs its one mandatory initial preview acquisition, publishes any accepted three-record result, and only then admits first LIVE if the model is LIVE-capable.

If another **non-LIVE** lifecycle still owns or is retiring from the serialized lane at the initial-preview boundary, the initial acquisition MAY wait behind the existing bounded lifecycle/handoff boundary without concurrent handler/session acquisition. LIVE SHALL NOT start ahead of this mandatory initial preview acquisition. Currentness/cancellation/supersession rules remain authoritative.

The automatic initial-acquisition marker SHALL become terminal for the current room generation/exact row after any of:

```text
accepted network success with records
accepted network success with zero records
ordinary network parse/business/no-data failure that does not degrade the row
typed terminal connection/session/authentication failure
```

There is no LIVE-priority local-skip terminal state in the amended contract.

Top full Refresh/new room generation, target/context invalidation followed by a new accepted room generation, or a new exact row identity creates a new initial-preview acquisition boundary. Collapse/re-expand alone does not.

Presentation SHALL only request/observe application state; it SHALL NOT call a handler/session directly, create a second worker owner, select credentials, or bypass the room interaction lane. Any initial acquisition that becomes stale, cancelled, superseded, or fails currentness before publication SHALL NOT update a replacement context or authorize LIVE for an old context.

#### Scenario: Post-terminal expansion admits exactly one preview

- **GIVEN** the room cycle is terminal for a connected/usable call-log-capable codec row
- **AND** that row's current room generation already completed its mandatory initial preview acquisition
- **WHEN** the operator expands the row and creates a presentation expansion epoch
- **THEN** the accepted up-to-three-record initial preview is rendered if available
- **AND** expansion causes zero new automatic call-history network I/O
- **AND** duplicate expansion notifications or re-rendering do not create another acquisition

#### Scenario: Busy lane delays but does not drop the admitted preview

- **GIVEN** the current room generation has admitted its mandatory initial preview acquisition
- **AND** another non-LIVE lifecycle owns or is retiring from the serialized lane
- **WHEN** the preview is not yet network-eligible
- **THEN** it may remain pending under application authority without concurrent handler/session acquisition
- **AND** bounded handoff/currentness/cancellation/supersession rules determine whether it later performs I/O
- **AND** first LIVE start for that row/generation waits until this initial preview reaches a terminal boundary

#### Scenario: Initial preview becomes stale

- **GIVEN** an initial automatic preview is pending or in flight for row/generation A
- **WHEN** row/generation A loses exact current authority before publication
- **THEN** late preview data/error/completion cannot update the replacement row
- **AND** it cannot emit a current-row call-history result or start/resume LIVE for the stale context

#### Scenario: LIVE-priority initial preview completes locally

- **GIVEN** the legacy architecture permitted LIVE eligibility to turn initial preview into a local skipped/unavailable result
- **WHEN** the amended lifecycle runs for a new current room generation
- **THEN** that behavior is superseded
- **AND** one fresh initial call-history acquisition is attempted before first LIVE start
- **AND** LIVE eligibility does not cancel, skip, or replace that acquisition
- **AND** after accepted success or bounded terminal failure, LIVE may start if the same row remains current and eligible

### Requirement: CloudLink Box 310 is an end-to-end call-history and usage-statistics regression oracle

Implementation SHALL include an end-to-end regression for exact `CloudLink Box 310` covering application registration, the mandatory initial room-preview acquisition, the approved CloudLink call-history read/session boundary, normalization, inline newest-three presentation, and a later fresh explicit detailed-journal acquisition.

The regression SHALL prove at minimum:

- exact application identity remains `CloudLink Box 310` and is not aliased to Bar 310;
- each new current room generation/exact Box row performs exactly one fresh initial call-history acquisition before first LIVE start;
- accepted normalized newest-first records populate at most three inline preview rows;
- row expansion/re-render causes zero additional automatic call-history network I/O for the same generation;
- explicit detailed opening always performs a fresh serialized acquisition even when three initial preview records are already present;
- normalized newest-first records from the fresh explicit load reach detailed presentation and usage calculation;
- accepted completed duration is visible and participates in existing usage arithmetic;
- typed direction, when authoritative source evidence exists, reaches the correct visible semantic cue role without GUI heuristics;
- current 30/90-day, source-limited, or 100-record product semantics continue to follow the existing root requirements applicable to the fixture;
- stale/superseded Box results cannot publish into a replacement row/context;
- secrets/session tokens do not appear in normalized records, public errors, or test evidence.

#### Scenario: Box 310 automatic preview and fresh detailed load remain distinct

- **GIVEN** exact `CloudLink Box 310` becomes a current accepted/usable room row in a new generation
- **WHEN** its automatic initial preview and a later explicit detailed-journal opening are exercised
- **THEN** Box identity remains exact
- **AND** the initial preview performs one fresh approved call-history acquisition before first LIVE start
- **AND** at most the three newest accepted records populate the inline preview
- **AND** the explicit opening performs a separate fresh approved call-history read/session acquisition
- **AND** detailed presentation/statistics publish from that fresh explicit result rather than the prior preview snapshot

## ADDED Requirements

### Requirement: Explicit codec call-log acquisition remains independent from automatic preview

For each supported exact codec model, explicitly opening the call log SHALL always start the approved fresh model-specific read-only acquisition for that exact current row, regardless of whether the mandatory initial dashboard preview succeeded with records, succeeded empty, failed ordinarily, or became stale in a previous generation.

Automatic preview is preview-owned application state and SHALL NOT become cache authority for explicit detail. The implementation SHOULD reuse the proven model-specific retrieval/normalization behavior that existed before `codec-diagnostic-modern-ui` where current device evidence confirms it remains valid.

An ordinary initial-preview failure SHALL NOT permanently disable explicit journal opening, degrade an otherwise connected row unless the failure proves typed connection/session loss, or strand the serialized room lane. An explicit journal failure SHALL follow existing typed auxiliary-failure rules and bounded cleanup.

#### Scenario: Automatic preview is unavailable

- **GIVEN** the codec dashboard has no accepted initial preview data because the mandatory acquisition completed without records or with an ordinary non-degrading failure
- **WHEN** the operator presses the explicit journal/expand action
- **THEN** a fresh exact-row call-log acquisition starts through the approved model-specific retrieval path
- **AND** missing preview data does not block the request

#### Scenario: Automatic preview failed earlier

- **GIVEN** a previous initial preview attempt failed without proving connection/session loss
- **WHEN** the same connected exact row remains current and the operator explicitly opens the journal
- **THEN** the explicit acquisition is still available
- **AND** it is not satisfied from the failed preview attempt
- **AND** its result may populate the dialog normally

#### Scenario: Automatic preview was skipped for LIVE priority

- **GIVEN** a legacy pre-amendment build skipped automatic preview because LIVE had priority
- **WHEN** the amended implementation is evaluated
- **THEN** that behavior is non-conforming for a new room generation
- **AND** the amended implementation performs one fresh initial preview acquisition before first LIVE start
- **AND** a later explicit action still starts one separate fresh serialized `AUXILIARY_READ`
