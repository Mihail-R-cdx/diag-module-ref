## MODIFIED Requirements

### Requirement: Automatic room preview and explicit detailed journal preserve separate acquisition epochs

For a supported exact codec row, automatic inline `Журнал вызовов` preview and every explicit detailed-journal load SHALL remain separate acquisition intents/datasets.

The automatic preview acquisition is allowed only at this exact authority boundary:

```text
entire automatic room cycle is terminal
+ exact codec row is current expanded row
+ row is connected / usable / not blocked
+ exact registration advertises call-log capability
+ this exact record_id + room generation has no terminal initial-preview attempt
```

At that boundary, the application SHALL perform one fresh serialized exact-row call-history `AUXILIARY_READ` **before the first LIVE start for that row/generation**. The request SHALL use the existing approved model-specific call-history path, exact-row credentials/currentness, shared normalization and newest-first chronology. Accepted preview-owned state SHALL contain at most the three newest normalized records.

This change does not authorize hidden/background call-log I/O for collapsed or non-current codec rows. If no codec row is expanded when the whole room cycle becomes terminal, no automatic preview request starts until an eligible codec row later becomes current/expanded. If a row is already expanded at room-cycle terminal, its mandatory initial preview starts at that terminal boundary.

After the exact row/generation has a terminal initial-preview attempt, collapse/re-expand, repaint, resize, theme switch, duplicate Qt notifications or rebuild SHALL cause zero additional automatic call-history network I/O for that same row/generation. A new top full Refresh/new room generation creates a new freshness boundary.

An accepted preview result MAY populate only inline preview-owned presentation state. An accepted success with fewer than three records publishes all available records. Accepted zero records or an ordinary parse/business/no-data failure may leave the preview empty/unavailable. Ordinary non-degrading failure reaches bounded cleanup and then permits first LIVE if the same row remains current/eligible. Typed terminal connection/session/authentication failure follows existing degradation rules.

The previous LIVE-priority local-skip behavior is removed. Because automatic preview is ordered before first LIVE, LIVE eligibility SHALL NOT convert the mandatory initial acquisition into a local skipped/unavailable result.

Every explicit `Развернуть` / detailed call-log opening remains a new fresh serialized exact-row acquisition even when a current three-record preview already exists. If LIVE is active, it retires through the existing bounded handoff before explicit handler/session acquisition. Only the fresh explicit result accepted for the same current exact row/generation/currentness may populate detailed rows and usage statistics.

Expanding/collapsing sections within an already-open detailed dialog may reuse that explicit load and SHALL NOT start another device request solely for section disclosure.

#### Scenario: Existing preview does not replace fresh explicit acquisition

- **GIVEN** a current exact codec row/generation already has an accepted automatic preview containing up to three newest calls
- **WHEN** the operator activates `Развернуть` or otherwise explicitly opens the detailed journal
- **THEN** a fresh serialized exact-row `AUXILIARY_READ` is started
- **AND** the preview snapshot is not treated as the detailed-load result
- **AND** detailed rows/statistics publish only from the fresh accepted explicit acquisition

#### Scenario: Detailed dialog section toggle reuses one explicit load

- **GIVEN** one explicit detailed-journal acquisition completed and its dialog is open
- **WHEN** the operator expands or collapses a section inside that dialog
- **THEN** already accepted data from that explicit load is reused
- **AND** no additional device request is started solely for the section toggle

#### Scenario: LIVE-priority local preview does not satisfy explicit detail

- **GIVEN** a legacy pre-amendment build could skip automatic preview because LIVE had priority
- **WHEN** the amended lifecycle is evaluated for a new room generation
- **THEN** that skip is non-conforming
- **AND** the mandatory automatic preview is attempted at the whole-room-terminal/current-expanded boundary before first LIVE
- **WHEN** the operator later explicitly opens detailed journal
- **THEN** one separate fresh exact-row acquisition is still required

### Requirement: Initial modern room call-history preview admits exactly one automatic attempt per eligible expansion epoch

The requirement name is preserved for root/archive compatibility. The amended network-admission boundary is generation + exact current expanded row after the **entire automatic room cycle is terminal**.

An expansion epoch remains presentation-owned non-secret state, but expansion alone does not imply repeated network freshness. For an exact codec row/generation:

- if the whole room cycle is not terminal, expansion starts no call-log device I/O;
- once the whole room cycle becomes terminal, an already-expanded eligible codec row admits its one generation-bound initial preview;
- if the row is collapsed at terminal time, the first later eligible expansion admits that row/generation's one initial preview;
- once that row/generation attempt is terminal, later collapse/re-expand epochs reuse accepted preview state or the terminal no-data state with zero automatic network I/O;
- switching to a different eligible codec row may admit that different record's own first generation-bound preview, after any prior lifecycle cleanup;
- a top full Refresh/new room generation makes the same row eligible for one new initial preview after the new whole-room terminal boundary.

The automatic preview SHALL acquire the same serialized `AUXILIARY_READ` authority as other network-backed auxiliary reads and SHALL remain bound to the exact current expanded record. No collapsed/non-current row may own the automatic request.

First LIVE for the same row/generation SHALL wait until the mandatory initial preview reaches accepted success or bounded terminal failure and cleanup/release. If another non-LIVE lifecycle owns or is retiring from the lane, the preview may wait behind that bounded handoff without concurrent handler/session acquisition.

The generation/record initial-attempt marker becomes terminal after:

```text
accepted success with records
accepted success with zero records
ordinary parse/business/no-data failure
typed terminal connection/session/authentication failure
```

There is no `local skipped because LIVE has priority` terminal state.

Late/stale/cancelled/superseded automatic-preview callbacks SHALL NOT update another record/generation, publish a current-row error into a replacement context, start/resume LIVE for stale authority, or mutate credential-success memory outside an accepted current operation.

#### Scenario: Post-terminal expansion admits exactly one preview

- **GIVEN** the entire automatic room cycle is terminal
- **AND** a current collapsed connected/usable call-log-capable codec row has no terminal initial-preview attempt in this room generation
- **WHEN** the operator expands that exact row
- **THEN** one fresh automatic call-history acquisition is admitted for that exact row/generation
- **AND** it reaches bounded terminal cleanup before that row's first LIVE starts
- **AND** subsequent re-render/duplicate expansion notifications cause no additional automatic acquisition

#### Scenario: Busy lane delays but does not drop the admitted preview

- **GIVEN** the whole room cycle is terminal and the current expanded row has admitted its mandatory initial preview
- **AND** another non-LIVE lifecycle is still active or retiring in the serialized lane
- **WHEN** preview network acquisition is not yet eligible
- **THEN** the preview may remain pending under application authority without concurrent handler/session acquisition
- **AND** bounded handoff/currentness/cancellation rules determine whether it later performs I/O
- **AND** first LIVE waits until preview reaches its terminal cleanup boundary

#### Scenario: Initial preview becomes stale

- **GIVEN** an automatic preview is pending or in flight for row/generation A
- **WHEN** A loses exact current-expanded authority before result acceptance
- **THEN** A is cancelled/retired under the existing auxiliary boundary
- **AND** late A data/error/completion cannot update the replacement row
- **AND** it cannot start/resume A LIVE

#### Scenario: LIVE-priority initial preview completes locally

- **GIVEN** a legacy implementation could complete preview locally because LIVE was eligible
- **WHEN** the amended implementation reaches the automatic-preview boundary
- **THEN** first LIVE has not yet been admitted for that row/generation
- **AND** one fresh automatic call-history acquisition is attempted
- **AND** LIVE eligibility neither skips nor replaces it
- **AND** LIVE may start only after preview terminal cleanup if the same row remains current/eligible

### Requirement: CloudLink Box 310 is an end-to-end call-history and usage-statistics regression oracle

Implementation SHALL include an end-to-end exact `CloudLink Box 310` call-history regression that proves application registration, whole-room-terminal/current-expanded automatic-preview admission, the approved CloudLink call-history read/session boundary, normalization, up-to-three inline presentation, and a later fresh explicit detailed-journal acquisition.

The regression SHALL prove:

- exact identity remains `CloudLink Box 310`, not Bar 310;
- no automatic call-log I/O occurs while Box is collapsed/non-current;
- once the whole room cycle is terminal and Box becomes current/expanded/usable, exactly one fresh preview acquisition is made for that generation;
- first Box LIVE waits for preview terminal cleanup;
- accepted newest-first data contributes at most three inline preview rows;
- collapse/re-expand/re-render in the same generation causes zero additional automatic call-history I/O;
- explicit `Развернуть` always performs a separate fresh acquisition;
- only the fresh explicit result supplies detailed rows/statistics;
- normalized direction/duration/chronology semantics remain unchanged;
- stale/superseded results cannot publish into a replacement context;
- no secret/session material enters normalized/public evidence.

#### Scenario: Box 310 automatic preview and fresh detailed load remain distinct

- **GIVEN** the whole room cycle is terminal and exact `CloudLink Box 310` becomes the current expanded usable row for the first time in this generation
- **WHEN** automatic preview and a later explicit detailed opening are exercised
- **THEN** one fresh preview acquisition occurs before first LIVE
- **AND** at most three newest accepted records populate inline preview
- **AND** explicit detail performs a separate fresh approved call-history acquisition
- **AND** detailed rows/statistics publish from the explicit result, not the preview

## ADDED Requirements

### Requirement: Explicit codec call-log acquisition remains independent from automatic preview

For each supported exact codec model, explicit opening SHALL always start the approved fresh model-specific exact-row call-log acquisition, regardless of whether the generation-bound automatic preview succeeded, returned zero records, failed ordinarily, or never ran because the row was never current/expanded.

Automatic preview is not explicit-detail cache authority. An ordinary automatic-preview failure SHALL NOT permanently disable explicit opening or degrade an otherwise connected row unless it separately proves typed connection/session loss.

#### Scenario: Automatic preview is unavailable

- **GIVEN** the current row has no accepted preview records
- **WHEN** the operator explicitly opens the journal
- **THEN** a fresh exact-row call-log acquisition starts through the approved model-specific path
- **AND** missing preview data does not block the request

#### Scenario: Automatic preview failed earlier

- **GIVEN** a previous generation-bound automatic preview ended with an ordinary non-degrading failure
- **WHEN** the same connected exact row remains current and the operator explicitly opens the journal
- **THEN** the explicit acquisition is still available
- **AND** it is not satisfied from the failed preview attempt

#### Scenario: Automatic preview was skipped for LIVE priority

- **GIVEN** a legacy pre-amendment implementation skipped automatic preview for LIVE priority
- **WHEN** a new room generation runs under the amended contract
- **THEN** the legacy skip is not permitted at the automatic-preview boundary
- **AND** one generation-bound preview is attempted before first LIVE when the exact row is current/expanded/usable
- **AND** a later explicit opening still starts a separate fresh acquisition
