## MODIFIED Requirements

### Requirement: Codec expansion performs at most one automatic call-log preview attempt per expansion epoch

After the automatic room cycle is terminal, when a current connected/usable exact codec row whose unified registration advertises the existing call-log auxiliary binding transitions from collapsed to expanded under current room authority, the application SHALL complete exactly one automatic call-log preview attempt for that new **expansion epoch**. The attempt is mandatory for the eligible post-terminal expansion, but it is presentation enrichment rather than mandatory network acquisition.

An expansion epoch SHALL be application-owned non-secret presentation/lifecycle state identified by the current room generation, exact `record_id`, and a monotonically changing row-expansion token or equivalent. A new epoch begins only when that exact row transitions from collapsed to expanded under current room authority. Re-rendering, resize, theme switching, hover, repaint, duplicate Qt expansion notifications, or rebuilding the same already-expanded presentation SHALL NOT create a new epoch.

If the codec row becomes expanded before the automatic room cycle reaches terminal state, the application SHALL remember only that current expanded selection/epoch and SHALL complete its one automatic preview attempt after the cycle becomes terminal if the same exact row/epoch remains current and eligible. The pre-terminal expansion itself SHALL NOT start device I/O.

The automatic attempt SHALL first evaluate presentation-local/current accepted preview evidence without acquiring network authority. If current same-row/same-generation authoritative call-log preview evidence is already available, it MAY populate the inline preview and the attempt becomes terminal for that epoch.

If the exact expanded codec row has current LIVE active, retiring, starting, or otherwise eligible to own the serialized room lane, automatic preview SHALL NOT invalidate/retire LIVE, acquire a handler/session, select credentials, reserve or wait as an `AUXILIARY_READ`, or perform device network I/O. If no current accepted preview evidence is available in that condition, the automatic attempt SHALL complete immediately as a local skipped/unavailable result for that expansion epoch and the inline preview MAY render `Нет данных`/neutral unavailable state. Continuous LIVE therefore cannot leave the automatic attempt indefinitely deferred or pending.

Only when no current LIVE lifecycle is active/retiring/pending and the exact row is not currently eligible to acquire LIVE ahead of presentation enrichment MAY the automatic attempt perform a network-backed preview. Such network acquisition SHALL enter the existing single serialized room interaction lane as `AUXILIARY_READ` and SHALL preserve existing auxiliary exact-row credential, lock, cleanup, degradation, cancellation and supersession rules. No second or concurrent room network owner is introduced.

The automatic-attempt marker SHALL become terminal for that expansion epoch after any of:

```text
current accepted preview evidence is used locally
local skipped/unavailable because LIVE has priority
accepted network success with records
accepted network success with zero records
ordinary network parse/business/no-data failure that does not degrade the row
typed terminal connection/session/authentication failure
```

A local skip or ordinary terminal failure SHALL complete the automatic attempt and SHALL NOT leave the same expansion epoch eligible for an automatic retry. Re-render, theme switch, resize, repaint, hover, duplicate expansion events, LIVE continuation/resume, or another local presentation event SHALL cause zero additional automatic preview network I/O for that completed epoch.

A new automatic preview attempt SHALL be admitted only after an authority boundary creates a new current eligible expansion epoch and the automatic room cycle is terminal. Such boundaries include collapse followed by explicit re-expand of that codec row, expansion of another row followed by a later re-expand, a new room generation/top full Refresh followed by a new current expansion, or target/context/credential-context invalidation followed by a new valid room context and a new current expansion. Merely returning the UI to the same visible values or rebuilding an already-expanded row does not create or admit another attempt.

Collapsing the row, expanding another row, top full Refresh, target-search/context invalidation, credential-context invalidation or application shutdown SHALL immediately make any active network-backed automatic-preview callbacks stale and publish cancellation/retirement where applicable. Late preview callbacks SHALL NOT update another row, reopen a child window, resume LIVE for an old context, change credential-success memory outside an accepted current operation, or become current cache authority.

An ordinary network-backed preview parse/business failure without typed connection/session loss SHALL keep the row connected. Terminal typed connection/session loss or terminal authentication failure after allowed fallback is exhausted SHALL follow the existing auxiliary degradation/recovery contract. A local LIVE-priority skip is not a network failure, SHALL NOT degrade the row, and SHALL NOT change credential/session state.

Explicit operator `Развернуть` / detailed `Журнал звонков` is not the automatic attempt. Every eligible explicit opening SHALL remain a fresh network-backed exact-row `AUXILIARY_READ`. If LIVE owns the row when the operator explicitly opens the journal, LIVE SHALL be invalidated and retired through the existing bounded cleanup/release boundary before explicit journal handler/session acquisition. After explicit acquisition reaches terminal cleanup, eligible LIVE SHALL resume only if the same exact row remains current and usable. Explicit opening SHALL NOT reset or create another automatic-attempt marker for the current expansion epoch.

#### Scenario: Post-terminal codec expansion completes one automatic preview attempt

- **GIVEN** the automatic room cycle is terminal
- **AND** a current connected/usable exact codec row with the registered call-log auxiliary binding is collapsed
- **WHEN** the operator expands that codec row and creates a new current expansion epoch
- **THEN** the application completes exactly one automatic call-log preview attempt for that epoch
- **AND** duplicate expansion notifications, render, resize, repaint or theme switching do not create another automatic attempt for the same epoch

#### Scenario: Codec was expanded before the room cycle finished

- **GIVEN** a codec row owns a current expansion epoch while the automatic room cycle is still running
- **WHEN** the room cycle later reaches terminal state and that exact row/epoch remains current, connected/usable and call-log capable
- **THEN** one automatic preview attempt is completed under this requirement
- **AND** the earlier expansion itself performed no device I/O before the terminal room boundary

#### Scenario: Current cached preview evidence completes the epoch locally

- **GIVEN** current accepted call-log preview evidence already belongs to the same exact row/generation
- **WHEN** the expansion epoch automatic attempt runs
- **THEN** that evidence MAY populate the inline preview without room network admission
- **AND** the automatic-attempt marker becomes terminal for that epoch

#### Scenario: LIVE-priority expansion skips automatic network preview

- **GIVEN** a terminal room has a current connected codec row with a registered call-log auxiliary binding
- **AND** LIVE is active, retiring, starting, or eligible to own that exact row's room interaction lane
- **AND** no current accepted preview evidence is available
- **WHEN** the current expansion epoch automatic preview attempt runs
- **THEN** LIVE is not invalidated or retired for automatic preview
- **AND** no automatic-preview `AUXILIARY_READ`, handler/session acquisition, credential selection, waiting network owner, or device I/O starts
- **AND** the automatic attempt completes locally as skipped/unavailable for that epoch
- **AND** LIVE remains eligible/current without starvation

#### Scenario: Network preview is allowed only when LIVE does not have priority

- **GIVEN** the current expansion epoch has no usable current preview evidence
- **AND** no current LIVE lifecycle is active, retiring, pending, or eligible to acquire the lane ahead of preview enrichment
- **WHEN** the automatic attempt performs a device read
- **THEN** exactly one network-backed preview enters the existing serialized `AUXILIARY_READ` lifecycle
- **AND** it follows existing auxiliary exact-row credential/currentness/cleanup rules
- **AND** no concurrent network owner is introduced

#### Scenario: Preview business failure is one-shot for the epoch

- **GIVEN** a network-backed automatic preview attempt for the current exact row/expansion epoch ends with an ordinary parse/business/no-data failure
- **WHEN** the same expanded presentation is rebuilt, resized, repainted, theme-switched or receives duplicate expansion notifications
- **THEN** no additional automatic call-log read is admitted for that epoch
- **AND** the row remains connected unless the failure separately proves typed connection/session loss

#### Scenario: Local LIVE-priority skip is one-shot for the epoch

- **GIVEN** the current expansion epoch completed its automatic attempt with a local LIVE-priority skip
- **WHEN** LIVE later stops/resumes or the same expanded presentation is re-rendered
- **THEN** no deferred automatic network preview is started for that completed epoch
- **AND** only a new expansion epoch or explicit journal intent can cause another acquisition decision

#### Scenario: Collapse and re-expand creates a new attempt boundary

- **GIVEN** the current codec expansion epoch already completed its automatic preview attempt
- **WHEN** the operator collapses that row and later explicitly expands it again under the same otherwise-current terminal room generation
- **THEN** the new expansion receives a new expansion epoch
- **AND** one new automatic preview attempt is completed if the row is still current, connected/usable and call-log capable

#### Scenario: Explicit journal retires and resumes LIVE

- **GIVEN** codec LIVE is active for the current exact row
- **WHEN** the operator explicitly opens `Развернуть` / detailed `Журнал звонков`
- **THEN** LIVE is invalidated and retired before the fresh explicit `AUXILIARY_READ` acquires handler/session resources
- **AND** no concurrent network owner is introduced
- **AND** eligible LIVE resumes after explicit auxiliary cleanup only if the same row remains current and usable
- **AND** the explicit acquisition does not reset the completed automatic-attempt marker

#### Scenario: Row switch makes old network preview stale

- **GIVEN** row A has an active network-backed automatic call-log preview
- **WHEN** the operator expands row B
- **THEN** A's preview loses authority and is cancelled/retired under the existing auxiliary boundary
- **AND** late A callbacks cannot update B or restart A live
- **AND** any B network lifecycle waits for the permitted A retirement boundary

## ADDED Requirements

### Requirement: Codec interactive operations have bounded release on every terminal path

Every room codec Local Refresh, explicit call-log auxiliary read, supported audio mutation/reconciliation, and LIVE retirement SHALL reach either physical cleanup/release or the existing allowed bounded-abandonment boundary on success, typed authentication exhaustion, ordinary protocol/parse failure, transport/session loss, user cancellation, row collapse/switch, timeout, and stale supersession.

A terminal or cancelled codec operation SHALL NOT leave the room interaction lane, row controls, or top-level controls permanently locked because a callback was dropped or a session shutdown signal never arrived. Late callbacks after currentness revocation SHALL have no presentation, credential, cache, or lock side effects.

#### Scenario: Codec operation fails ordinarily

- **WHEN** a current codec operation ends with an ordinary protocol/parse/business failure that does not prove connection loss
- **THEN** bounded cleanup releases its room-lane ownership
- **AND** the UI lock matrix returns to the state permitted by the still-current row
- **AND** eligible LIVE may resume when current contracts allow it

#### Scenario: Cleanup signal never arrives

- **GIVEN** codec operation authority has been revoked
- **AND** expected physical cleanup notification does not arrive within policy timeout
- **WHEN** the bounded-abandonment boundary is reached
- **THEN** stale authority cannot keep the GUI permanently locked
- **AND** no late callback can regain currentness
