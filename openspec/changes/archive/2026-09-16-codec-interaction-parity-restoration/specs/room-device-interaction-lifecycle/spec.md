## MODIFIED Requirements

### Requirement: Codec expansion performs at most one automatic call-log preview attempt per expansion epoch

The requirement/scenario names are preserved for archive compatibility, while network freshness is now bound to the exact current expanded record and the whole automatic-room-cycle terminal boundary.

The application SHALL admit an automatic codec call-history preview only when all of these are true:

```text
entire automatic room cycle is terminal
exact codec row is the current expanded record
row is connected / usable / not blocked
exact registration advertises call-log auxiliary capability
this record_id + room generation has no terminal initial-preview attempt
```

At that boundary, one fresh network-backed preview SHALL enter the existing single serialized room lane as `AUXILIARY_READ`. It SHALL use immutable current context containing room generation, exact `record_id`, exact diagnostic model/IP, credential context and operation/currentness token. It SHALL reach success or bounded terminal failure/cleanup **before the first LIVE start for that exact row/generation**.

The requirement does not authorize call-log I/O for collapsed/non-current rows. If no codec row is expanded when the whole room cycle becomes terminal, automatic preview remains dormant. The first later eligible codec expansion may admit that exact row/generation's one preview. If a codec row is already expanded when the cycle becomes terminal, its preview is admitted then.

When application composition binds a generation-current room session whose `expanded_record_id` already identifies a current codec row, coordinator ownership SHALL accept that application-owned expansion identity for later terminal-cycle preview admission. Binding and presentation render SHALL start zero device I/O and SHALL NOT require a synthetic Qt expansion notification. The mandatory preview remains admitted only when the ordinary whole-room terminal boundary is reached and all other eligibility conditions hold.

After the row/generation's initial attempt is terminal, later expansion epochs are presentation-only for automatic call history: accepted up-to-three-row preview state may be rendered again, or a terminal unavailable state may remain visible, but collapse/re-expand SHALL NOT produce a second automatic call-history read in the same generation.

Resize, theme switch, hover, repaint, rebuild, duplicate Qt expansion notification and LIVE continuation/resume also create zero additional automatic preview network I/O.

If another non-LIVE room lifecycle is still active/retiring when preview becomes eligible, the preview may wait behind that bounded handoff. It SHALL NOT acquire a concurrent handler/session owner. First LIVE for that exact row/generation remains behind the preview's terminal cleanup boundary.

An ordinary preview parse/business/no-data failure without typed connection/session loss SHALL keep the row connected and, after bounded cleanup, allow first LIVE if the same row remains current/eligible. Terminal typed connection/session/authentication failures retain current auxiliary degradation rules.

The old LIVE-priority local-skip outcome is removed. LIVE cannot have priority over the row's first automatic preview because first LIVE is ordered after preview cleanup.

Top full Refresh/new room generation, exact-row identity replacement, target/context invalidation or credential-context invalidation SHALL revoke any old preview authority. Late callbacks SHALL NOT update another row, emit current errors into a replacement context, start/resume stale LIVE, mutate replacement credential-success memory, or become cache authority.

Explicit `Развернуть` / detailed journal remains separate fresh auxiliary work. If LIVE is active when explicit detail is requested, LIVE retires before fresh explicit handler/session acquisition and may resume only after bounded cleanup if the same row remains current/usable/eligible. Explicit detail never resets the generation-bound automatic-preview marker.

#### Scenario: Post-terminal codec expansion automatically admits preview

- **GIVEN** the entire automatic room cycle is terminal
- **AND** a current collapsed connected/usable call-log-capable codec row has no terminal automatic-preview attempt in this room generation
- **WHEN** the operator expands that exact row
- **THEN** one fresh automatic call-history `AUXILIARY_READ` is admitted for that exact row/generation
- **AND** first LIVE waits for its terminal cleanup
- **AND** duplicate expansion notifications/re-rendering do not create another request

#### Scenario: Codec was expanded before the room cycle finished

- **GIVEN** a codec row is already the current expanded presentation while the automatic room cycle is still running
- **WHEN** the entire room cycle reaches terminal state and that exact row remains connected/usable/call-log-capable
- **THEN** one generation-bound automatic preview is admitted for that exact row
- **AND** the earlier expansion itself started no call-log device I/O before the whole-room terminal boundary
- **AND** first LIVE waits for preview terminal cleanup

#### Scenario: Session binds an initially expanded codec before terminal cycle

- **GIVEN** a generation-current room session is created with `expanded_record_id` for a connected/usable call-log-capable codec row
- **AND** coordinator binding occurs before the automatic room cycle becomes terminal
- **WHEN** the session binds and presentation renders without a synthetic expansion notification
- **THEN** binding/render start zero device I/O
- **WHEN** the ordinary automatic room cycle reaches terminal state and the same row remains current/eligible
- **THEN** exactly one generation-current automatic `call_log_preview` is admitted
- **AND** no manual collapse/re-expand is required
- **AND** preview cleanup precedes first eligible LIVE

#### Scenario: Current cached preview evidence completes the epoch locally

- **GIVEN** current accepted automatic-preview evidence already belongs to the same exact row/generation and that row's generation-bound attempt is terminal
- **WHEN** a later expansion epoch renders
- **THEN** that accepted evidence MAY populate the inline preview locally
- **AND** no room network admission occurs solely for the later expansion epoch

#### Scenario: Codec expansion starts preview after live retirement

- **GIVEN** this preserved legacy scenario name previously implied automatic preview could retire LIVE after expansion
- **WHEN** the amended lifecycle is evaluated
- **THEN** that network ordering is superseded
- **AND** automatic preview occurs before first LIVE for the row/generation
- **AND** expanding a row whose LIVE already started and whose automatic attempt is terminal causes zero automatic-preview I/O

#### Scenario: Network preview is allowed only when LIVE does not have priority

- **GIVEN** the whole room cycle is terminal and the current expanded row has no terminal automatic-preview attempt
- **WHEN** the automatic preview becomes eligible
- **THEN** first LIVE has not yet acquired row authority
- **AND** preview may acquire the single serialized auxiliary lane after any bounded non-LIVE handoff
- **AND** LIVE eligibility is not a reason to skip the preview

#### Scenario: Preview business failure is one-shot for the epoch

- **GIVEN** the generation-bound automatic preview ends with ordinary parse/business/no-data failure
- **WHEN** the same row is rebuilt, repainted, theme-switched, collapsed/re-expanded or receives duplicate expansion events
- **THEN** no additional automatic call-history read is admitted for that row/generation
- **AND** the row remains connected unless typed loss was separately proven
- **AND** first/eligible LIVE may start after bounded cleanup

#### Scenario: Local LIVE-priority skip is one-shot for the epoch

- **GIVEN** a pre-amendment build could complete automatic preview with a local LIVE-priority skip
- **WHEN** a new room generation is evaluated under the amended contract
- **THEN** such a skip is non-conforming
- **AND** one fresh automatic preview is attempted at the whole-room-terminal/current-expanded boundary before first LIVE
- **AND** later presentation events cause no extra automatic acquisition after that attempt is terminal

#### Scenario: Collapse and re-expand creates a new attempt boundary

- **GIVEN** the current row/generation already has a terminal automatic-preview attempt
- **WHEN** the operator collapses and re-expands the same exact row without a top full Refresh/new generation
- **THEN** a new presentation expansion epoch may be created
- **BUT** no new automatic call-history network acquisition is admitted
- **AND** accepted preview state may be rendered again locally

#### Scenario: Explicit journal retires and resumes LIVE

- **GIVEN** codec LIVE is active for the current exact row
- **WHEN** the operator explicitly opens `Развернуть` / detailed `Журнал звонков`
- **THEN** LIVE is invalidated and retired before fresh explicit `AUXILIARY_READ` handler/session acquisition
- **AND** no concurrent network owner is introduced
- **AND** eligible LIVE resumes after explicit cleanup only if the same row remains current/usable
- **AND** the explicit acquisition does not reset the generation-bound automatic-preview marker

#### Scenario: Row switch makes old preview stale

- **GIVEN** row A has an active or pending generation-bound automatic preview
- **WHEN** the operator makes row B the current expanded row
- **THEN** A loses automatic-preview authority and is cancelled/retired under the existing auxiliary boundary
- **AND** late A callbacks cannot update B or start/resume A LIVE
- **AND** B network work waits for A's permitted retirement boundary
- **AND** B may then admit its own first generation-bound preview if otherwise eligible

### Requirement: Codec automatic preview and explicit detail retain distinct call-log acquisition authority

Automatic preview SHALL remain application-owned preview state and explicit detail SHALL remain a fresh operator-owned auxiliary acquisition.

Automatic preview uses the whole-room-terminal/current-expanded boundary above and retains at most three newest normalized records for inline presentation. It is exact-row/generation evidence only. It SHALL NOT become authoritative detailed rows/statistics for a later explicit opening.

Every eligible explicit `Развернуть` SHALL start one fresh serialized exact-row call-history `AUXILIARY_READ`. If LIVE owns the row, explicit detail retires LIVE through bounded cleanup before handler/session acquisition. Only the fresh explicit result accepted for the same current exact row/generation/currentness may populate detailed rows and usage statistics.

An explicit child window may open in loading state while accepted preview remains visible on the card. User close/cancellation invalidates that explicit request; late callbacks cannot reopen/update it; a later explicit opening is fresh again.

#### Scenario: Detail opens with fresh acquisition despite current preview

- **GIVEN** accepted automatic-preview rows belong to the current exact row/generation
- **WHEN** the operator clicks `Развернуть`
- **THEN** one fresh serialized exact-row call-history acquisition starts
- **AND** card preview may remain visible as preview-only evidence
- **AND** detailed rows/statistics wait for the fresh explicit result

#### Scenario: Fresh detail result becomes authoritative only after current acceptance

- **GIVEN** one explicit detailed acquisition is active for the current exact row/generation
- **WHEN** application authority accepts its normalized result while context is still current
- **THEN** that explicit result may populate detailed rows/statistics
- **AND** preview remains a separate dataset

#### Scenario: Failed automatic preview can be retried only by explicit detail intent

- **GIVEN** the row/generation's automatic preview ended with ordinary failure/no-data and is terminal
- **WHEN** no explicit journal action occurs
- **THEN** presentation events and LIVE continuation cause zero further automatic call-history I/O in that generation
- **WHEN** the operator explicitly clicks `Развернуть`
- **THEN** one fresh explicit call-history acquisition is admitted
- **AND** the automatic-preview marker remains terminal

#### Scenario: Explicit detail becomes stale or cancelled

- **GIVEN** a fresh explicit acquisition exists for row/generation A
- **WHEN** A loses authority or the child request is cancelled before acceptance
- **THEN** late result cannot populate detailed content/statistics or replacement presentation
- **AND** automatic-preview state is not reset

#### Scenario: Reopening after explicit cancellation is fresh again

- **GIVEN** an explicit child-window request was cancelled/closed/superseded
- **WHEN** the operator later opens detailed journal again for an eligible current exact row
- **THEN** a new fresh serialized call-history acquisition is required
- **AND** neither the cancelled request nor automatic preview substitutes for it

#### Scenario: Automatic LIVE-priority completion owns no auxiliary lifecycle

- **GIVEN** a legacy build allowed automatic preview to finish locally due LIVE priority
- **WHEN** the amended generation-bound preview is due
- **THEN** that legacy local completion is not used
- **AND** automatic preview owns one serialized auxiliary lifecycle before first LIVE
- **AND** after terminal cleanup, first LIVE may start if the same row remains current/eligible

## ADDED Requirements

### Requirement: Codec interactive operations have bounded release on every terminal path

Every room codec Local Refresh, explicit call-log auxiliary read, generation-bound automatic call-history preview, supported audio mutation/reconciliation, and LIVE retirement SHALL reach physical cleanup/release or the existing bounded-abandonment boundary on success, structured authentication exhaustion, ordinary protocol/parse/business failure, transport/session loss, user cancellation, row switch/collapse, timeout, and stale supersession.

If automatic-preview physical cleanup completes before its terminal callback is accepted, composition SHALL acknowledge that completed cleanup to the coordinator exactly once after terminal acceptance. It SHALL not request a second cleanup from a removed run, release before terminal acceptance, or release a structured-authentication attempt while a permitted retry owns the same context.

A terminal/cancelled operation SHALL NOT leave the room interaction lane or GUI permanently locked. Late callbacks after authority revocation have no presentation, credential, cache, LIVE-start or lock side effects.

#### Scenario: Codec operation fails ordinarily

- **WHEN** a current codec network operation ends with an ordinary non-degrading protocol/parse/business failure
- **THEN** bounded cleanup releases room-lane ownership
- **AND** controls return to the state permitted by the still-current row
- **AND** eligible LIVE may start/resume when current contracts allow

#### Scenario: Cleanup signal never arrives

- **GIVEN** codec network-operation authority has been revoked
- **AND** expected physical cleanup notification does not arrive within policy timeout
- **WHEN** bounded-abandonment boundary is reached
- **THEN** stale authority cannot keep GUI/lane permanently locked
- **AND** no late callback can regain currentness

#### Scenario: Local automatic preview cannot strand the lane

- **GIVEN** this preserved legacy scenario name is evaluated under the amended network-backed initial-preview contract
- **WHEN** the generation-bound preview reaches success or bounded terminal failure
- **THEN** cleanup/release completes before first LIVE starts
- **AND** later local rendering of accepted preview evidence owns no network lifecycle
- **AND** presentation-only rendering cannot strand the lane
