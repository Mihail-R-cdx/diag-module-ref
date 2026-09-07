## MODIFIED Requirements

### Requirement: Automatic room preview and explicit detailed journal preserve separate acquisition epochs

For a current exact room codec row, the automatic modern room `Журнал вызовов` preview SHALL remain a distinct expansion-epoch presentation result from every explicit detailed-journal load. An automatic preview attempt MAY terminate from current accepted same-row/same-generation preview evidence, from a deterministic local LIVE-priority skipped/unavailable outcome with no network acquisition, or from one admitted network-backed automatic acquisition when LIVE does not have priority.

Only an accepted normalized automatic-preview result MAY populate automatic inline preview rows. A local skipped/unavailable automatic outcome creates no accepted call-history dataset and SHALL NOT be promoted into detailed rows or usage statistics.

The existing explicit-opening freshness contract remains authoritative: every explicit `Развернуть` / detailed call-log dialog opening SHALL begin a fresh serialized exact-row read-only acquisition even when a current automatic-preview snapshot already exists or the automatic attempt completed locally without data. The automatic-preview snapshot or local skip SHALL NOT substitute for that fresh explicit acquisition.

If LIVE owns the exact row when the explicit opening is requested, LIVE SHALL retire through the existing bounded room-lifecycle handoff before the explicit `AUXILIARY_READ` acquires handler/session resources. Only the fresh explicit result accepted for the same current exact row/generation/currentness MAY populate detailed rows and usage statistics for that opening.

Expanding/collapsing sections within an already-open detailed dialog MAY reuse that explicit-load data and SHALL NOT trigger another device request. The GUI SHALL NOT create a second parser, chronology sort, vendor-specific preview cache, or separate statistics dataset.

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

#### Scenario: LIVE-priority local preview does not satisfy explicit detail

- **GIVEN** the current expansion epoch completed its automatic attempt locally as skipped/unavailable because LIVE had priority
- **WHEN** the operator explicitly opens the detailed journal
- **THEN** the local automatic outcome supplies no authoritative detailed rows or statistics
- **AND** one fresh serialized exact-row call-log `AUXILIARY_READ` is required
- **AND** LIVE retirement/cleanup occurs only for that explicit network request

### Requirement: Initial modern room call-history preview admits exactly one automatic attempt per eligible expansion epoch

When the modern room codec dashboard has an eligible exact codec expansion epoch under the existing `room-device-interaction-lifecycle` contract, the application SHALL complete exactly one automatic call-history preview attempt for that epoch. The automatic attempt is mandatory as presentation/lifecycle bookkeeping but SHALL NOT be treated as mandatory network acquisition.

The attempt SHALL first evaluate current accepted preview evidence for the same exact row/generation without acquiring network authority. If usable current preview evidence already exists, it MAY populate the inline preview and the attempt becomes terminal for that epoch.

If LIVE is active, retiring, starting/pending, or otherwise has priority to own the exact row's serialized room lane, the automatic preview SHALL NOT invalidate/retire LIVE, reserve or wait as an `AUXILIARY_READ`, acquire a handler/session, select credentials, or perform device I/O. With no usable current preview evidence, the automatic attempt SHALL complete immediately as a local skipped/unavailable result for that epoch.

Only when LIVE does not have priority MAY the automatic attempt admit one network-backed preview through the existing serialized room `AUXILIARY_READ` authority. If another **non-LIVE** lifecycle currently owns or is retiring from the lane, that admitted network preview MAY remain pending behind the existing bounded lifecycle/handoff boundary without concurrent handler/session acquisition. It SHALL NOT remain pending behind continuous/current LIVE, because LIVE-priority automatic preview terminates locally instead.

Admission/completion remains exactly-once for the eligible epoch. Duplicate Qt expansion notifications, render/rebuild, resize, repaint, hover, theme switching, or later LIVE continuation/resume SHALL NOT create another automatic attempt for the same completed epoch.

If the exact row becomes expanded before the automatic room cycle is terminal, application authority SHALL retain the current expansion epoch and SHALL complete its one automatic preview attempt after the room cycle becomes terminal when the same exact row/epoch remains current, connected/usable, and call-log capable. The pre-terminal expansion itself SHALL NOT start device I/O.

Presentation SHALL only request/observe application state; it SHALL NOT call a handler/session directly, create a second worker owner, select credentials, or bypass the room interaction lane. Any admitted network-backed preview that becomes stale, cancelled, superseded, or fails currentness before publication SHALL not update a replacement context.

#### Scenario: Post-terminal expansion admits exactly one preview

- **GIVEN** the room cycle is terminal and a connected/usable call-log-capable codec row is collapsed
- **WHEN** the row transitions to a new current expansion epoch
- **THEN** exactly one automatic preview attempt is completed for that epoch
- **AND** that attempt may finish from current accepted evidence, a local LIVE-priority skip, or one admissible serialized network read
- **AND** duplicate Qt notifications or re-rendering do not create another attempt for that epoch

#### Scenario: Busy lane delays but does not drop the admitted preview

- **GIVEN** the current expansion epoch has admitted a network-backed automatic preview because LIVE does not have priority
- **AND** another non-LIVE lifecycle owns or is retiring from the serialized lane
- **WHEN** the preview is not yet network-eligible
- **THEN** the preview may remain pending under application authority without concurrent handler/session acquisition
- **AND** bounded handoff/currentness/cancellation/supersession rules determine whether it later performs I/O
- **AND** this pending rule does not apply when LIVE has priority, because that automatic attempt completes locally instead

#### Scenario: Initial preview becomes stale

- **GIVEN** a network-backed automatic preview is pending or in flight for row A
- **WHEN** row A loses exact current authority before publication
- **THEN** late preview data/error/completion cannot update the replacement row
- **AND** it cannot emit a current-row call-history error

#### Scenario: LIVE-priority initial preview completes locally

- **GIVEN** the current exact codec row is LIVE-active or LIVE-priority and has no usable current accepted preview evidence
- **WHEN** its eligible automatic preview attempt runs
- **THEN** no automatic-preview network owner or pending `AUXILIARY_READ` is created
- **AND** the attempt becomes terminal locally as skipped/unavailable for that epoch
- **AND** later LIVE continuation/resume does not trigger a deferred automatic read for the same epoch

### Requirement: CloudLink Box 310 is an end-to-end call-history and usage-statistics regression oracle

Implementation SHALL include an end-to-end regression for exact `CloudLink Box 310` covering application registration, automatic room-preview decision flow, the approved CloudLink call-history read/session boundary when network acquisition is admissible, normalization, and a fresh explicit detailed-journal acquisition.

The regression SHALL prove at minimum:

- exact application identity remains `CloudLink Box 310` and is not aliased to Bar 310;
- an eligible automatic expansion completes exactly one preview attempt without starving LIVE;
- when LIVE has priority and no current accepted preview evidence exists, the automatic attempt terminates locally with zero automatic call-history network ownership;
- when current accepted automatic-preview evidence exists, only that current same-row/same-generation evidence may populate the inline preview;
- any network-backed automatic preview used by a non-LIVE-priority fixture follows the approved existing call-history retrieval/session path without a second credential source or handler-owned fallback;
- explicit detailed opening always performs a fresh serialized acquisition even when automatic preview already completed locally or with accepted data;
- normalized newest-first records from the fresh explicit load reach detailed presentation and usage calculation;
- accepted completed duration is visible and participates in existing usage arithmetic;
- typed direction, when authoritative source evidence exists, reaches the correct visible semantic cue role without GUI heuristics;
- current 30/90-day, source-limited, or 100-record product semantics continue to follow the existing root requirements applicable to the fixture;
- stale/superseded Box results cannot publish into a replacement row/context;
- secrets/session tokens do not appear in normalized records, public errors, or test evidence.

#### Scenario: Box 310 automatic preview and fresh detailed load remain distinct

- **GIVEN** exact `CloudLink Box 310` owns a current eligible expansion epoch
- **WHEN** its automatic preview decision and a later explicit detailed-journal opening are exercised
- **THEN** Box identity remains exact
- **AND** the automatic attempt follows LIVE-priority local completion or an otherwise admissible current preview/network path without starving LIVE
- **AND** the explicit opening performs a fresh approved call-history read/session acquisition
- **AND** the detailed presentation/statistics publish from that fresh accepted explicit result rather than from a local automatic skip or prior preview snapshot

## ADDED Requirements

### Requirement: Explicit codec call-log acquisition remains independent from automatic preview

For each supported exact codec model, explicitly opening the call log SHALL always start the approved fresh model-specific read-only acquisition for that exact current row, regardless of whether automatic dashboard preview used current accepted evidence, completed locally as LIVE-priority skipped/unavailable, is empty, is stale, or previously failed.

Automatic preview is presentation enrichment and SHALL NOT become a prerequisite, cache authority, or failure gate for the explicit journal. The implementation SHOULD reuse the proven model-specific retrieval/normalization behavior that existed before `codec-diagnostic-modern-ui` where current device evidence confirms it remains valid.

A local automatic-preview skip or an ordinary automatic-preview failure SHALL NOT permanently disable explicit journal opening, degrade an otherwise connected row, or strand the serialized room lane. An explicit journal failure SHALL follow existing typed auxiliary-failure rules and bounded cleanup.

#### Scenario: Automatic preview is unavailable

- **GIVEN** the codec dashboard has no automatic preview data because the epoch completed locally or without accepted records
- **WHEN** the operator presses the explicit journal/expand action
- **THEN** a fresh exact-row call-log acquisition starts through the approved model-specific retrieval path
- **AND** missing preview data does not block the request

#### Scenario: Automatic preview failed earlier

- **GIVEN** a previous automatic preview attempt failed without proving connection/session loss
- **WHEN** the same connected exact row remains current and the operator explicitly opens the journal
- **THEN** the explicit acquisition is still available
- **AND** it is not satisfied from the failed preview attempt
- **AND** its result may populate the dialog normally

#### Scenario: Automatic preview was skipped for LIVE priority

- **GIVEN** the current expansion epoch completed its automatic preview attempt locally because LIVE had priority
- **WHEN** the operator explicitly opens the journal
- **THEN** the explicit action starts one fresh serialized `AUXILIARY_READ`
- **AND** LIVE retirement/cleanup occurs only for that explicit operator request
- **AND** the completed automatic-attempt marker is not reset
