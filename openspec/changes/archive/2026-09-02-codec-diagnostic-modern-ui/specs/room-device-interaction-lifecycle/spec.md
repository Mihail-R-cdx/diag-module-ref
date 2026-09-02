# room-device-interaction-lifecycle Delta

## ADDED Requirements

### Requirement: Codec expansion performs at most one automatic call-log preview attempt per expansion epoch

After the automatic room cycle is terminal, when a current connected/usable exact codec row whose unified registration advertises the existing call-log auxiliary binding transitions from collapsed to expanded under current room authority, the application SHALL admit exactly one automatic call-log preview attempt for that new **expansion epoch** through the existing serialized room interaction lane. Admission of that automatic intent is mandatory for the eligible post-terminal expansion; later currentness, retirement, cancellation or cleanup gates MAY prevent device I/O, but the implementation SHALL NOT leave the row merely "eligible" without submitting the one automatic attempt.

An expansion epoch SHALL be application-owned non-secret presentation/lifecycle state identified by the current room generation, exact `record_id`, and a monotonically changing row-expansion token or equivalent. A new epoch begins only when that exact row transitions from collapsed to expanded under current room authority. Re-rendering, resize, theme switching, hover, repaint, duplicate Qt expansion notifications, or rebuilding the same already-expanded presentation SHALL NOT create a new epoch.

If the codec row becomes expanded before the automatic room cycle reaches terminal state, the application SHALL remember only that current expanded selection/epoch and SHALL admit its one automatic preview attempt after the cycle becomes terminal if the same exact row/epoch remains current and eligible. The pre-terminal expansion itself SHALL NOT start device I/O.

All preview network acquisition SHALL enter the existing single serialized room interaction lane as `AUXILIARY_READ` and SHALL preserve the existing auxiliary credential, lock, cleanup, degradation and supersession rules. Before preview I/O begins, any current LIVE owner for that row SHALL lose authority and retire through the existing bounded cleanup/release boundary. Preview I/O SHALL start only after that boundary and only if the same room generation, `record_id`, exact model/IP, expansion epoch and operation/currentness token remain current and eligible. After terminal preview cleanup, eligible LIVE MAY start/resume only for the still-current expanded usable row.

The automatic-attempt marker SHALL become terminal for that expansion epoch after any current terminal preview result, including:

```text
accepted success with records
accepted success with zero records
ordinary parse/business/no-data failure that does not degrade the row
typed terminal connection/session/authentication failure
```

A terminal ordinary failure SHALL therefore render `Нет данных` and complete the automatic attempt; it SHALL NOT leave the same expansion epoch eligible for an automatic retry. Re-render, theme switch, resize, repaint, hover, duplicate expansion events, LIVE resume, or another local presentation event SHALL cause zero additional automatic preview I/O for that completed epoch.

A new automatic preview attempt SHALL be admitted only after an authority boundary creates a new current eligible expansion epoch and the automatic room cycle is terminal. Such boundaries include collapse followed by explicit re-expand of that codec row, expansion of another row followed by a later re-expand, a new room generation/top full Refresh followed by a new current expansion, or target/context/credential-context invalidation followed by a new valid room context and a new current expansion. Merely returning the UI to the same visible values or rebuilding an already-expanded row does not create or admit another automatic attempt.

Collapsing the row, expanding another row, top full Refresh, target-search/context invalidation, credential-context invalidation or application shutdown SHALL immediately make active preview callbacks stale and publish cancellation/retirement where applicable. Late preview callbacks SHALL NOT update another row, reopen a child window, resume LIVE for an old context, change credential-success memory outside an accepted current operation, or become current cache authority.

An ordinary preview parse/business failure without typed connection/session loss SHALL keep the row connected. Terminal typed connection/session loss or terminal authentication failure after allowed fallback is exhausted SHALL follow the existing auxiliary degradation/recovery contract.

#### Scenario: Post-terminal codec expansion automatically admits preview

- **GIVEN** the automatic room cycle is terminal
- **AND** a current connected/usable exact codec row with the registered call-log auxiliary binding is collapsed
- **WHEN** the operator expands that codec row and creates a new current expansion epoch
- **THEN** the application admits exactly one automatic call-log preview attempt through the existing `AUXILIARY_READ` lane for that epoch
- **AND** duplicate expansion notifications, render, resize, repaint or theme switching do not admit another automatic attempt for the same epoch

#### Scenario: Codec was expanded before the room cycle finished

- **GIVEN** a codec row owns a current expansion epoch while the automatic room cycle is still running
- **WHEN** the room cycle later reaches terminal state and that exact row/epoch remains current, connected/usable and call-log capable
- **THEN** one automatic call-log preview attempt is admitted through the auxiliary lane
- **AND** the earlier expansion itself performed no device I/O before the terminal room boundary

#### Scenario: Preview business failure is one-shot for the epoch

- **GIVEN** an automatic preview attempt for the current exact row/expansion epoch ends with an ordinary parse/business/no-data failure
- **WHEN** the same expanded presentation is rebuilt, resized, repainted, theme-switched or receives duplicate expansion notifications
- **THEN** no additional automatic call-log read is admitted for that epoch
- **AND** the row remains connected unless the failure separately proves typed connection/session loss

#### Scenario: Collapse and re-expand creates a new attempt boundary

- **GIVEN** the current codec expansion epoch already completed its automatic preview attempt
- **WHEN** the operator collapses that row and later explicitly expands it again under the same otherwise-current terminal room generation
- **THEN** the new expansion receives a new expansion epoch
- **AND** one new automatic preview attempt is admitted if the row is still current, connected/usable and call-log capable

#### Scenario: Codec expansion starts preview after live retirement

- **GIVEN** a terminal room has a current connected codec row with a registered call-log auxiliary binding
- **AND** LIVE currently owns that row
- **WHEN** the current expansion epoch's mandatory automatic call-log preview attempt is admitted
- **THEN** LIVE is invalidated and retired before preview handler/session acquisition
- **AND** exactly one `AUXILIARY_READ` preview may perform network I/O
- **AND** eligible LIVE may resume only after preview cleanup and currentness checks

#### Scenario: Row switch makes old preview stale

- **GIVEN** row A has an active call-log preview
- **WHEN** the operator expands row B
- **THEN** A's preview loses authority and is cancelled/retired under the existing auxiliary boundary
- **AND** late A callbacks cannot update B or restart A live
- **AND** any B network lifecycle waits for the permitted A retirement boundary

### Requirement: Codec call-log acquisition result and explicit detail request are separate from automatic-attempt authority

The existing room call-log application/controller boundary SHALL separate normalized acquisition/result ownership from the side effect of showing `CallLogWindow`. A current accepted call-log result SHALL remain bound to its immutable exact row/generation context and MAY feed either the inline three-record preview, the existing detailed child window, or both without creating a second capability authority.

When `Развернуть` is requested and current accepted full preview data exists for the same exact row/generation, the application SHALL populate and open the existing detailed window from that accepted result as a local presentation action with no additional network I/O.

If no current accepted data exists — including after a completed automatic preview attempt that ended in ordinary failure/no-data — `Развернуть` SHALL be treated as a new explicit operator auxiliary intent. It MAY request one normal fresh call-log `AUXILIARY_READ` through the same serialized lane; after a current accepted result, the application SHALL populate and open the existing detailed window. This explicit request SHALL NOT clear, reuse or reset the completed automatic-attempt marker for the current expansion epoch, and its completion SHALL NOT cause an automatic retry loop.

The existing direct child-window close rule remains authoritative for an active window-owned network request: user close invalidates/cancels that request, bounded cleanup follows, late callbacks cannot reopen it, and a later explicit network opening after the cancelled request requires fresh acquisition. Accepted preview data from a distinct still-current completed preview SHALL NOT be confused with a cancelled child-window request.

#### Scenario: Detail opens from current completed preview

- **GIVEN** a completed accepted call-log preview belongs to the current exact codec row/generation
- **WHEN** the operator clicks `Развернуть`
- **THEN** the existing detailed window opens from that accepted full result
- **AND** no second auxiliary read is started solely to reproduce the same current accepted records

#### Scenario: Failed automatic preview can be retried only by explicit detail intent

- **GIVEN** the current expansion epoch's automatic preview completed with an ordinary failure/no-data result
- **WHEN** no explicit call-log action occurs
- **THEN** presentation events cause zero further automatic call-log I/O
- **WHEN** the operator explicitly clicks `Развернуть`
- **THEN** one fresh call-log auxiliary acquisition may be requested through the serialized lane
- **AND** the automatic-attempt marker for that expansion epoch remains completed

### Requirement: Room codec controls use registry-owned exact-row state-changing lifecycle bindings

The unified exact application model registration SHALL remain the sole runtime capability authority for codec room controls. Each current exact codec registration SHALL explicitly declare support or absence for:

```text
speaker_adjust
speaker_mute
microphone_adjust
microphone_mute
reboot
```

The required current-baseline values are the OpenSpec test oracle defined by `device-diagnostics-and-control`; they SHALL NOT be copied into a second runtime support table. Application composition SHALL fail closed if a codec operation is declared supported but its required adapter, model-safe target policy, readback/reconciliation binding, cancellation or cleanup hook is unavailable or contradictory.

A dashboard click for an explicitly unsupported operation SHALL be resolved locally before `RoomInteractionCoordinator` mutation admission. The local affordance SHALL show the approved non-secret informational result and SHALL NOT invalidate LIVE, replace an interaction generation, acquire a handler/session, select credentials or perform device network I/O. The operation remains an unsupported **network capability** even though the fixed dashboard retains a visible local affordance. Existing active/retiring lifecycle locks MAY temporarily disable the common controls.

A supported codec state-changing operation SHALL bind to the current immutable exact-row `RoomInteractionContext` and use the existing `MUTATION -> RECONCILIATION` lifecycle. It SHALL preserve all stronger generic mutation rules: LIVE retirement before send, no send if cleanup cannot reach its permitted boundary, one state-changing delivery attempt at most under current policy, no blind replay/credential advance after possible delivery, mandatory model-appropriate readback, authoritative cache update only after confirmed reconciliation, and row network blocking until top full Refresh after ambiguous/unconfirmed outcome.

For non-disruptive codec audio controls, the operator's click on an explicit provable desired-state control SHALL constitute the explicit mutation confirmation required by the generic room mutation contract; no second confirmation dialog SHALL be inserted between the control click and lifecycle admission. A future supported `reboot` would require a separate explicit confirmation dialog because reboot is disruptive; current baseline reboot support is `UNSUPPORTED` for all five codecs.

The presentation SHALL NOT call standalone `CodecScreen`, handlers or transports directly and SHALL NOT determine support from widget type, handler method presence, model substring, localized text or an independent codec model list.

#### Scenario: Unsupported codec control is local only

- **GIVEN** the exact codec registration explicitly marks the requested dashboard network operation unsupported
- **AND** the common controls are not temporarily locked by another lifecycle
- **WHEN** the operator clicks its visible affordance
- **THEN** the application displays the unsupported-operation information locally
- **AND** no room interaction generation or network owner changes
- **AND** no handler/session is acquired and current LIVE remains eligible/unchanged

#### Scenario: Audio control click is its explicit desired-state confirmation

- **GIVEN** an eligible current codec row supports the selected audio operation
- **WHEN** the operator clicks `+`, `−` or mute with a provable desired target
- **THEN** no secondary modal confirmation is required
- **AND** the click may be admitted into the existing mutation lifecycle after normal exact-row/currentness gates

#### Scenario: Declared codec control binding is unavailable

- **GIVEN** an exact codec registration declares a dashboard operation supported
- **WHEN** composition cannot resolve its required operation/readback/cleanup binding
- **THEN** startup/composition fails closed
- **AND** the GUI cannot expose that operation as a network-capable room control

### Requirement: Codec relative and mute controls derive only from authoritative typed audio evidence

Room codec `+` and `−` controls SHALL NOT be implemented as blind relative device commands or by guessing a starting value. Before mutation admission, application/core codec-control composition SHALL use current accepted exact-row numeric `speaker_volume` or `microphone_volume` plus the registry-bound model range/step policy to derive one valid absolute target.

If the current numeric value, range, step or applicable operation support cannot be proven for the exact row, the click SHALL produce a safe local unavailable/unsupported informational result and SHALL perform no device I/O. A fallback default such as minimum volume, zero, another model's range, or a stale standalone-widget value SHALL NOT become mutation authority.

Mute/unmute SHALL likewise resolve to an explicit desired model-safe target, not a blind toggle. The application SHALL consume the separate typed mute-state and restore authority defined by `device-diagnostics-and-control`:

- supported TE20/TE40/Polycom microphone mute uses typed `MUTED`/`UNMUTED` readback and never numeric-gain inference;
- supported speaker mute for current codecs may map to absolute zero/restore only when current numeric volume and exact-row room-owned restore evidence prove the target;
- widget-local `last_unmuted_volume`, fallback `1`, minimum volume or requested-but-unconfirmed values SHALL NOT supply restore authority;
- when unmute cannot prove a restore target, the click remains local unavailable and starts zero mutation/network I/O.

Model-specific range/step/mute policy SHALL come from the registry-owned binding/adapter. Shared Qt presentation SHALL NOT hard-code model names to choose command semantics.

#### Scenario: Volume value is unavailable

- **GIVEN** a supported codec row has no current authoritative speaker value from which a `+` target can be derived
- **WHEN** the operator clicks `+`
- **THEN** no guessed absolute target is created
- **AND** no mutation/handler/device I/O starts
- **AND** a safe informational unavailable result is shown

#### Scenario: Speaker unmute lacks restore authority

- **GIVEN** the current exact row has accepted speaker volume zero
- **AND** no current exact-row/generation non-zero restore target is proven
- **WHEN** the operator clicks speaker unmute
- **THEN** no fallback target is fabricated
- **AND** no mutation/handler/device I/O starts

#### Scenario: Supported audio target reconciles

- **GIVEN** current authoritative audio evidence and registry-bound model policy produce a valid absolute or typed desired target
- **WHEN** the operator requests an audio change
- **THEN** one exact-row mutation may send that desired target after currentness/live-retirement gates
- **AND** only matching accepted readback may confirm the operation and replace authoritative row audio state
