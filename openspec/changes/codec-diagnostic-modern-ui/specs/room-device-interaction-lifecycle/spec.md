# room-device-interaction-lifecycle Delta

## ADDED Requirements

### Requirement: Codec expansion starts one exact-row call-log preview through the existing auxiliary lane

After the automatic room cycle is terminal, a current expanded connected/usable exact codec row whose unified registration advertises the existing call-log auxiliary binding SHALL request one automatic call-log preview. If the codec row became expanded before the automatic cycle reached terminal state, the application SHALL remember only that current presentation selection and SHALL admit the preview once, after the cycle becomes terminal and the row is still current/eligible; the pre-terminal expansion itself SHALL NOT start device I/O.

All preview network acquisition SHALL enter the existing single serialized room interaction lane as `AUXILIARY_READ` and SHALL preserve the existing auxiliary credential, lock, cleanup, degradation and supersession rules.

Before preview I/O begins, any current LIVE owner for that row SHALL lose authority and retire through the existing bounded cleanup/release boundary. Preview I/O SHALL start only after that boundary and only if the same room generation, `record_id`, exact model/IP and row operation/currentness token remain current and eligible. After terminal preview cleanup, eligible LIVE MAY start/resume only for the still-current expanded usable row.

The application SHALL maintain at most one active/pending call-log preview acquisition for the current exact row/generation. Re-rendering the row, repeated Qt expansion notifications, theme switching, hover or resize SHALL NOT enqueue duplicate auxiliary reads. A successfully completed current preview SHALL remain the current accepted preview for that exact row/generation and SHALL NOT be refetched merely because the same expanded presentation re-renders. The accepted full normalized result MAY be retained as non-secret exact-row/generation auxiliary presentation state so the codec card can project the newest three entries.

Collapsing the row, expanding another row, top full Refresh, target-search/context invalidation, credential-context invalidation or application shutdown SHALL immediately make preview callbacks stale and publish cancellation/retirement where applicable. Late preview callbacks SHALL NOT update another row, reopen a child window, resume LIVE for an old context, change credential-success memory outside an accepted current operation, or become current cache authority.

An ordinary preview parse/business failure without typed connection/session loss SHALL keep the row connected and render preview no-data after bounded cleanup. Terminal typed connection/session loss or terminal authentication failure after allowed fallback is exhausted SHALL follow the existing auxiliary degradation/recovery contract.

#### Scenario: Codec was expanded before the room cycle finished

- **GIVEN** a codec row is the current expanded row while the automatic room cycle is still running
- **WHEN** the room cycle later reaches terminal state and that exact row remains current, connected/usable and call-log capable
- **THEN** one automatic call-log preview is admitted through the auxiliary lane
- **AND** the earlier expansion itself performed no device I/O before the terminal room boundary

#### Scenario: Codec expansion starts preview after live retirement

- **GIVEN** a terminal room has a current connected codec row with a registered call-log auxiliary binding
- **AND** LIVE currently owns that row
- **WHEN** automatic call-log preview is admitted
- **THEN** LIVE is invalidated and retired before preview handler/session acquisition
- **AND** exactly one `AUXILIARY_READ` preview may perform network I/O
- **AND** eligible LIVE may resume only after preview cleanup and currentness checks

#### Scenario: Re-render does not duplicate preview

- **GIVEN** a call-log preview is active/pending or current accepted preview data already belongs to the same exact row/generation
- **WHEN** presentation re-renders or receives another equivalent expansion notification
- **THEN** no second preview network acquisition is created solely by that presentation event

#### Scenario: Row switch makes old preview stale

- **GIVEN** row A has an active call-log preview
- **WHEN** the operator expands row B
- **THEN** A's preview loses authority and is cancelled/retired under the existing auxiliary boundary
- **AND** late A callbacks cannot update B or restart A live
- **AND** any B network lifecycle waits for the permitted A retirement boundary

### Requirement: Codec call-log acquisition result is separable from detailed-window presentation

The existing room call-log application/controller boundary SHALL separate normalized acquisition/result ownership from the side effect of showing `CallLogWindow`. A current accepted call-log result SHALL remain bound to its immutable exact row/generation context and MAY feed either the inline three-record preview, the existing detailed child window, or both without creating a second capability authority.

When `Развернуть` is requested and current accepted full preview data exists for the same exact row/generation, the application SHALL populate and open the existing detailed window from that accepted result as a local presentation action with no additional network I/O. If no such current accepted data exists, `Развернуть` SHALL request a normal fresh call-log `AUXILIARY_READ`; after a current accepted result, the application SHALL populate and open the existing detailed window.

The existing direct child-window close rule remains authoritative for an active window-owned network request: user close invalidates/cancels that request, bounded cleanup follows, late callbacks cannot reopen it, and a later explicit network opening after the cancelled request requires fresh acquisition. Accepted preview data from a distinct still-current completed preview SHALL NOT be confused with a cancelled child-window request.

#### Scenario: Detail opens from current completed preview

- **GIVEN** a completed accepted call-log preview belongs to the current exact codec row/generation
- **WHEN** the operator clicks `Развернуть`
- **THEN** the existing detailed window opens from that accepted full result
- **AND** no second auxiliary read is started solely to reproduce the same current accepted records

#### Scenario: No current preview exists

- **GIVEN** the current codec row has no accepted current call-log preview
- **WHEN** the operator clicks `Развернуть`
- **THEN** a fresh call-log acquisition enters the existing serialized auxiliary lane
- **AND** the detailed window is populated/opened only after a current accepted result

### Requirement: Room codec controls use registry-owned exact-row state-changing lifecycle bindings

The unified exact application model registration SHALL remain the sole capability authority for codec room controls. Each current exact codec registration SHALL explicitly declare support or absence for the operations needed by the common codec dashboard:

```text
speaker_adjust
speaker_mute
microphone_adjust
microphone_mute
reboot
```

These declarations SHALL live in or be owned by the existing exact registration and SHALL NOT form a parallel model registry. Application composition SHALL fail closed if a codec operation is declared supported but its required adapter, model-safe target policy, readback/reconciliation binding, cancellation or cleanup hook is unavailable or contradictory.

A dashboard click for an explicitly unsupported operation SHALL be resolved locally before `RoomInteractionCoordinator` mutation admission: it SHALL show the approved non-secret informational result and SHALL NOT invalidate LIVE, replace an interaction generation, acquire a handler/session, select credentials or perform device network I/O. Unsupported controls SHALL not be permanently disabled solely because the model lacks that operation; however, the existing interaction lock matrix MAY temporarily disable the common controls while another room lifecycle owns interaction authority.

A supported codec state-changing operation SHALL bind to the current immutable exact-row `RoomInteractionContext` and use the existing `MUTATION -> RECONCILIATION` lifecycle. It SHALL preserve all stronger generic mutation rules: LIVE retirement before send, no send if cleanup cannot reach its permitted boundary, one state-changing delivery attempt at most under current policy, no blind replay/credential advance after possible delivery, mandatory model-appropriate readback, authoritative cache update only after confirmed reconciliation, and row network blocking until top full Refresh after ambiguous/unconfirmed outcome.

For non-disruptive codec audio controls (`speaker_adjust`, `speaker_mute`, `microphone_adjust`, `microphone_mute`), the operator's click on the explicit desired-state control SHALL constitute the explicit mutation confirmation required by the generic room mutation contract; no second confirmation dialog SHALL be inserted between the control click and lifecycle admission. For a supported `reboot`, a separate explicit confirmation dialog SHALL be required before mutation admission because reboot is disruptive. Canceling that reboot confirmation SHALL be a no-op under the existing mutation contract.

The presentation SHALL NOT call standalone `CodecScreen`, handlers or transports directly and SHALL NOT determine support from widget type, handler method presence, model substring, localized text or an independent codec model list.

#### Scenario: Unsupported codec control is local only

- **GIVEN** the exact codec registration explicitly marks the requested dashboard operation unsupported
- **AND** the common controls are not temporarily locked by another lifecycle
- **WHEN** the operator clicks its visible control
- **THEN** the application displays the unsupported-operation information locally
- **AND** no room interaction generation or network owner changes
- **AND** no handler/session is acquired and current LIVE remains eligible/unchanged

#### Scenario: Audio control click is its explicit desired-state confirmation

- **GIVEN** an eligible current codec row supports the selected audio operation
- **WHEN** the operator clicks `+`, `−` or mute with a provable desired target
- **THEN** no secondary modal confirmation is required
- **AND** the click may be admitted into the existing mutation lifecycle after normal exact-row/currentness gates

#### Scenario: Supported reboot requires confirmation

- **GIVEN** an exact codec registration has an approved supported reboot binding
- **WHEN** the operator clicks `Перезагрузить устройство`
- **THEN** the application asks for explicit confirmation before mutation admission
- **AND** Cancel performs no reboot I/O and does not replace interaction authority

#### Scenario: Declared codec control binding is unavailable

- **GIVEN** an exact codec registration declares a dashboard operation supported
- **WHEN** composition cannot resolve its required operation/readback/cleanup binding
- **THEN** startup/composition fails closed
- **AND** the GUI cannot expose that operation as a network-capable room control

### Requirement: Codec relative audio controls resolve to authoritative absolute targets before mutation

Room codec `+` and `−` controls SHALL NOT be implemented as blind relative device commands or by guessing a starting value. Before mutation admission, application/core codec-control composition SHALL use current accepted exact-row authoritative audio evidence plus the registry-bound model range/step policy to derive one valid absolute target.

If the current value, range, step or applicable operation support cannot be proven for the exact row, the click SHALL produce a safe local unavailable/unsupported informational result and SHALL perform no device I/O. A fallback default such as minimum volume, zero, another model's range, or a stale standalone-widget value SHALL NOT become mutation authority.

Mute/unmute SHALL likewise resolve to an explicit desired model-safe target, not a blind toggle. Where the existing approved model contract represents mute through volume zero/restore or a typed mute state, the codec-control adapter SHALL perform that mapping below the shared presentation and SHALL provide the model-appropriate readback needed for reconciliation.

Model-specific range/step/mute policy SHALL come from the registry-owned binding/adapter. Shared Qt presentation SHALL NOT hard-code model names to choose command semantics. Existing safe behavior, including a model-specific larger Polycom speaker step where applicable, MAY be preserved through that adapter.

#### Scenario: Volume value is unavailable

- **GIVEN** a supported codec row has no current authoritative speaker value from which a `+` target can be derived
- **WHEN** the operator clicks `+`
- **THEN** no guessed absolute target is created
- **AND** no mutation/handler/device I/O starts
- **AND** a safe informational unavailable result is shown

#### Scenario: Supported audio target reconciles

- **GIVEN** current authoritative value and registry-bound model policy produce a valid absolute target
- **WHEN** the operator requests an audio change
- **THEN** one exact-row mutation may send that desired target after currentness/live-retirement gates
- **AND** only matching accepted readback may confirm the operation and replace authoritative row audio state
