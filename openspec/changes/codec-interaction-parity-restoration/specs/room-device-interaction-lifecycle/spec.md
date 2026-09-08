## MODIFIED Requirements

### Requirement: Codec expansion performs at most one automatic call-log preview attempt per expansion epoch

The requirement name and existing scenario names are preserved for root-spec/archive compatibility, but this amendment moves automatic call-history **network acquisition** from the expansion epoch to a mandatory initial room-generation boundary.

After the automatic room diagnostic for a current connected/usable exact codec row becomes accepted/usable, and before the first eligible LIVE start for that row/generation, the application SHALL admit exactly one fresh call-history preview acquisition through the existing serialized room interaction lane. This initial acquisition is mandatory network work for every call-log-capable supported codec row; LIVE eligibility SHALL NOT convert it into a local skipped/unavailable result.

An expansion epoch SHALL remain application-owned non-secret presentation state identified by the current room generation, exact `record_id`, and a monotonically changing row-expansion token or equivalent. A new expansion epoch begins only when that exact row transitions from collapsed to expanded under current room authority. Re-rendering, resize, theme switching, hover, repaint, duplicate Qt expansion notifications, or rebuilding the same already-expanded presentation SHALL NOT create a new epoch.

The expansion epoch SHALL NOT own automatic call-history network acquisition. If the current room generation already has an accepted initial preview result, expansion MAY render its up-to-three newest records from application state with zero network admission. If the initial preview is still pending because the room diagnostic/lane has not reached the applicable boundary, expansion MAY render loading/neutral state but SHALL NOT create a second request.

The mandatory initial preview acquisition SHALL run only after the room diagnostic has produced a current connected/usable exact row and SHALL reach accepted success or bounded terminal failure before first LIVE is admitted for that row/generation. If another non-LIVE lifecycle owns or is retiring from the single lane, the initial preview MAY wait behind that bounded handoff. No concurrent handler/session owner is introduced.

The initial preview acquisition SHALL use the existing exact-row auxiliary authority, credential/currentness rules, approved model-specific call-history retrieval and normalization, and bounded cleanup. Accepted records SHALL be newest-first and preview-owned state SHALL retain at most three records for inline presentation.

The initial-acquisition marker SHALL become terminal for the current room generation/exact row after any of:

```text
accepted network success with records
accepted network success with zero records
ordinary network parse/business/no-data failure that does not degrade the row
typed terminal connection/session/authentication failure
```

There is no amended terminal state `local skipped/unavailable because LIVE has priority`.

Collapse/re-expand, render/rebuild, theme switch, resize, repaint, hover, duplicate expansion events, or LIVE continuation/resume SHALL cause zero additional automatic preview network I/O for a generation whose initial-acquisition marker is terminal. A new automatic acquisition boundary requires a new current room generation/top full Refresh, a new exact row identity, or target/context invalidation followed by a new accepted room context.

Collapsing the row, expanding another row, top full Refresh, target-search/context invalidation, credential-context invalidation or application shutdown SHALL immediately make any active initial-preview callbacks stale and publish cancellation/retirement where applicable. Late callbacks SHALL NOT update another row, reopen a child window, start/resume LIVE for an old context, change credential-success memory outside an accepted current operation, or become current cache authority.

An ordinary preview parse/business failure without typed connection/session loss SHALL keep the row connected and, after bounded cleanup, SHALL not prevent first LIVE from starting if the same row remains current/eligible. Terminal typed connection/session loss or terminal authentication failure after allowed fallback is exhausted SHALL follow the existing auxiliary degradation/recovery contract.

Explicit operator `Развернуть` / detailed `Журнал звонков` is not the automatic initial acquisition. Every eligible explicit opening SHALL remain a fresh network-backed exact-row `AUXILIARY_READ`. If LIVE owns the row when the operator explicitly opens the journal, LIVE SHALL be invalidated and retired through the existing bounded cleanup/release boundary before explicit journal handler/session acquisition. After explicit acquisition reaches terminal cleanup, eligible LIVE SHALL resume only if the same exact row remains current and usable. Explicit opening SHALL NOT reset or recreate the current generation's initial-preview marker.

#### Scenario: Post-terminal codec expansion automatically admits preview

- **GIVEN** the automatic room cycle is terminal
- **AND** a current connected/usable exact codec row already completed its mandatory initial preview acquisition for this room generation
- **WHEN** the operator expands that codec row and creates a new current expansion epoch
- **THEN** the application renders the accepted up-to-three-record preview if available
- **AND** expansion itself causes zero automatic call-history network I/O
- **AND** duplicate expansion notifications, render, resize, repaint or theme switching do not create another automatic acquisition for the same generation

#### Scenario: Codec was expanded before the room cycle finished

- **GIVEN** a codec row is visually expanded while the automatic room cycle is still running
- **WHEN** the room cycle later reaches accepted/usable terminal state and that exact row remains current and call-log capable
- **THEN** one mandatory initial preview acquisition is admitted for the current room generation
- **AND** the earlier expansion itself performed no device I/O
- **AND** first eligible LIVE start waits until the preview acquisition reaches a terminal boundary

#### Scenario: Current cached preview evidence completes the epoch locally

- **GIVEN** current accepted initial-preview evidence already belongs to the same exact row/generation
- **WHEN** an expansion epoch renders
- **THEN** that evidence MAY populate the inline preview without room network admission
- **AND** expansion bookkeeping becomes locally complete without modifying the generation-owned initial-acquisition marker

#### Scenario: Codec expansion starts preview after live retirement

- **GIVEN** the legacy requirement name implied expansion might start preview after LIVE retirement
- **WHEN** the amended lifecycle is evaluated
- **THEN** that legacy network sequence is superseded
- **AND** mandatory automatic preview acquisition occurs before first LIVE start rather than by retiring LIVE after expansion
- **AND** expansion of a LIVE-active row causes zero automatic preview network I/O

#### Scenario: Network preview is allowed only when LIVE does not have priority

- **GIVEN** this preserved legacy scenario name is evaluated under the amended contract
- **WHEN** a new room generation reaches the initial-preview boundary
- **THEN** LIVE has not yet been admitted for that row/generation
- **AND** the mandatory initial preview may acquire the single serialized auxiliary lane after any bounded non-LIVE handoff
- **AND** LIVE priority is not used as a reason to skip the acquisition

#### Scenario: Preview business failure is one-shot for the epoch

- **GIVEN** the mandatory initial preview acquisition for the current exact row/generation ends with an ordinary parse/business/no-data failure
- **WHEN** the same presentation is rebuilt, resized, repainted, theme-switched, collapsed/re-expanded or receives duplicate expansion notifications
- **THEN** no additional automatic call-log read is admitted for that generation
- **AND** the row remains connected unless the failure separately proves typed connection/session loss
- **AND** eligible LIVE may start after bounded cleanup

#### Scenario: Local LIVE-priority skip is one-shot for the epoch

- **GIVEN** a pre-amendment build could complete automatic preview with a local LIVE-priority skip
- **WHEN** the amended implementation is evaluated for a new current room generation
- **THEN** such a skip is non-conforming
- **AND** exactly one fresh initial preview acquisition is attempted before first LIVE start
- **AND** later presentation events cause no additional automatic acquisition for that generation

#### Scenario: Collapse and re-expand creates a new attempt boundary

- **GIVEN** the current room generation already completed its mandatory initial preview acquisition
- **WHEN** the operator collapses and later re-expands the same current row
- **THEN** a new presentation expansion epoch is created
- **BUT** no new automatic call-history network acquisition is created solely by collapse/re-expand
- **AND** the existing accepted initial preview MAY be rendered again

#### Scenario: Explicit journal retires and resumes LIVE

- **GIVEN** codec LIVE is active for the current exact row
- **WHEN** the operator explicitly opens `Развернуть` / detailed `Журнал звонков`
- **THEN** LIVE is invalidated and retired before the fresh explicit `AUXILIARY_READ` acquires handler/session resources
- **AND** no concurrent network owner is introduced
- **AND** eligible LIVE resumes after explicit auxiliary cleanup only if the same row remains current and usable
- **AND** the explicit acquisition does not reset the completed initial-preview marker

#### Scenario: Row switch makes old preview stale

- **GIVEN** row/generation A has an active mandatory initial call-log preview acquisition
- **WHEN** authority switches to row/generation B
- **THEN** A's preview loses authority and is cancelled/retired under the existing auxiliary boundary
- **AND** late A callbacks cannot update B or start/resume A LIVE
- **AND** any B network lifecycle waits for the permitted A retirement boundary

### Requirement: Codec automatic preview and explicit detail retain distinct call-log acquisition authority

The existing room call-log application/controller boundary SHALL separate the mandatory initial room-generation preview from explicit detailed-journal network acquisition. Both use the same approved call-log normalization contract and exact-row/currentness authority, but they are different acquisition intents and datasets.

The initial preview SHALL be one fresh serialized call-history acquisition after initial diagnostic acceptance and before first LIVE start for each current call-log-capable row/generation. A current accepted initial-preview result SHALL remain bound to its immutable exact row/generation and MAY populate only the up-to-three-row inline preview plus other preview-owned presentation state approved for that result. It SHALL NOT become the accepted load result for a later explicit detailed-journal opening.

Every eligible explicit `Развернуть` / detailed call-log opening SHALL be treated as a new operator auxiliary intent and SHALL start one fresh serialized exact-row call-log `AUXILIARY_READ` even when a current accepted initial-preview result already exists. If LIVE owns the row, explicit detail SHALL invalidate/retire LIVE through the existing bounded cleanup boundary before handler/session acquisition. The detailed child window MAY open immediately in its loading state while the accepted room-card preview remains preview-only evidence.

Only a fresh explicit result accepted for the same current exact row/generation/currentness MAY populate authoritative detailed call rows and usage statistics for that opening. If the explicit acquisition becomes stale, cancelled, superseded, or otherwise fails currentness before acceptance, it SHALL NOT populate/repopulate authoritative detailed content, publish detailed statistics, mutate replacement presentation, or emit a current-row result for a replacement context.

The explicit detail acquisition SHALL NOT clear, reuse, or reset the completed initial-preview marker, and its completion SHALL NOT cause an automatic retry loop. A later explicit opening after cancellation or close SHALL start a new fresh acquisition.

The existing direct child-window close rule remains authoritative for an active explicit window-owned network request: user close invalidates/cancels that exact request, bounded cleanup follows, late callbacks cannot reopen it, and a later explicit opening starts a new fresh acquisition.

#### Scenario: Detail opens with fresh acquisition despite current preview

- **GIVEN** a completed accepted initial-preview result belongs to the current exact codec row/generation
- **WHEN** the operator clicks `Развернуть`
- **THEN** one fresh serialized exact-row call-log `AUXILIARY_READ` is admitted for the explicit opening
- **AND** the room-card preview MAY remain visible while that request is pending
- **AND** the detailed window MAY show only its loading state before fresh acceptance
- **AND** the initial-preview result is not promoted to authoritative detailed/statistics state

#### Scenario: Fresh detail result becomes authoritative only after current acceptance

- **GIVEN** one explicit detailed-journal acquisition is active for the current exact row/generation
- **WHEN** application authority accepts its fresh normalized result while that context is still current
- **THEN** that explicit result may populate the detailed window and usage statistics
- **AND** any initial-preview result remains a separate room-generation preview result

#### Scenario: Failed automatic preview can be retried only by explicit detail intent

- **GIVEN** the current generation's mandatory initial preview completed with an ordinary network failure/no-data result
- **WHEN** no explicit call-log action occurs
- **THEN** presentation events and LIVE continuation/resume cause zero further automatic call-log I/O for that generation
- **WHEN** the operator explicitly clicks `Развернуть`
- **THEN** one fresh call-log auxiliary acquisition is admitted through the serialized lane
- **AND** the initial-preview marker remains completed

#### Scenario: Explicit detail becomes stale or cancelled

- **GIVEN** a fresh explicit detailed-journal acquisition exists for row/generation A
- **WHEN** A loses authority or the child request is cancelled before result acceptance
- **THEN** its late result cannot populate authoritative detailed content or statistics
- **AND** it cannot update a replacement row/context
- **AND** the initial-preview marker is not reset or retried

#### Scenario: Reopening after explicit cancellation is fresh again

- **GIVEN** an explicit child-window request was cancelled by close or supersession
- **WHEN** the operator later explicitly opens the detailed journal again for an eligible current exact row
- **THEN** a new fresh serialized call-log acquisition is required
- **AND** neither the cancelled request nor the initial-preview result substitutes for that new explicit load

#### Scenario: Automatic LIVE-priority completion owns no auxiliary lifecycle

- **GIVEN** the pre-amendment architecture permitted automatic preview to complete locally because LIVE had priority
- **WHEN** the amended implementation starts a new room generation
- **THEN** the legacy local completion is not used
- **AND** the mandatory initial preview owns one serialized auxiliary lifecycle before first LIVE start
- **AND** after that lifecycle reaches terminal cleanup, LIVE may acquire its normal authority if still eligible

## ADDED Requirements

### Requirement: Codec interactive operations have bounded release on every terminal path

Every room codec Local Refresh, explicit call-log auxiliary read, mandatory initial call-history preview, supported audio mutation/reconciliation, and LIVE retirement SHALL reach either physical cleanup/release or the existing allowed bounded-abandonment boundary on success, typed authentication exhaustion, ordinary protocol/parse failure, transport/session loss, user cancellation, row collapse/switch, timeout, and stale supersession.

A terminal or cancelled codec operation SHALL NOT leave the room interaction lane, row controls, or top-level controls permanently locked because a callback was dropped or a session shutdown signal never arrived. Late callbacks after currentness revocation SHALL have no presentation, credential, cache, LIVE-start, or lock side effects.

#### Scenario: Codec operation fails ordinarily

- **WHEN** a current codec network operation ends with an ordinary protocol/parse/business failure that does not prove connection loss
- **THEN** bounded cleanup releases its room-lane ownership
- **AND** the UI lock matrix returns to the state permitted by the still-current row
- **AND** eligible LIVE may start/resume when current contracts allow it

#### Scenario: Cleanup signal never arrives

- **GIVEN** codec network-operation authority has been revoked
- **AND** expected physical cleanup notification does not arrive within policy timeout
- **WHEN** the bounded-abandonment boundary is reached
- **THEN** stale authority cannot keep the GUI permanently locked
- **AND** no late callback can regain currentness

#### Scenario: Local automatic preview cannot strand the lane

- **GIVEN** this preserved legacy scenario name is evaluated after the amendment
- **WHEN** a current generation completes its mandatory initial preview with success or bounded terminal failure
- **THEN** its network lifecycle reaches cleanup/release before first LIVE start
- **AND** later expansion-only rendering of accepted preview evidence owns no network lifecycle
- **AND** presentation-only rendering cannot leave row/top controls or the serialized room lane locked
