# diagnostic-ui-presentation Delta

## ADDED Requirements

### Requirement: Same room diagnostic context preserves safe user presentation state across background rebuild

The room diagnostic presentation SHALL distinguish authoritative room/session/device state from context-scoped user presentation state.

The exact current `RoomDiagnosticSessionIdentity` produced by application authority SHALL be the context key for room-level presentation restoration. A background update/re-render whose incoming identity is exactly equal to the active identity SHALL preserve safe presentation state; a different identity or explicit presentation clear SHALL discard the old state rather than migrate it into the new context.

Safe state in this change includes the equipment-tree viewport/scroll position and network-tree disclosure state. Existing Audio selected-channel visual state MAY continue under its separately approved exact-room/record/channel contract. The presentation state SHALL NOT contain or become authority for credentials, handlers/sessions, workers/controllers, request generations, accepted device evidence, exact-row network target, retry state, mutation state, or secrets.

For the equipment tree, same-context rebuild SHALL restore the operator's prior viewport as closely as the current rows permit. Implementation SHOULD preserve a visual top-level `record_id` anchor plus pixel offset with a clamped scrollbar value fallback so row-height/data changes do not force the viewport to the beginning. The visual `record_id` anchor SHALL NOT select/expand the row, create an interaction context, change automatic acquisition order, or admit device I/O.

State capture/restore, clamping, layout restoration, scrolling, and disclosure restoration SHALL be presentation-only and SHALL emit no room/device interaction intent or network work.

#### Scenario: Background update preserves equipment viewport

- **GIVEN** the operator has scrolled the equipment tree away from its initial viewport
- **AND** the authoritative room/session identity remains unchanged
- **WHEN** accepted diagnostic data causes the room presentation to rebuild
- **THEN** the equipment viewport remains at the same visual position as closely as the current rows permit
- **AND** the rebuild does not scroll to the beginning merely because data refreshed
- **AND** restoration performs no device I/O or interaction admission

#### Scenario: New room/session does not inherit old viewport

- **GIVEN** one room/session has stored local viewport/disclosure state
- **WHEN** the presentation receives a different `RoomDiagnosticSessionIdentity` or is explicitly cleared
- **THEN** the old viewport/disclosure state is discarded
- **AND** no stale callback may restore it into the new context

### Requirement: Audio DSP popup lifetime follows current hover and expanded-row context

The modern room Audio DSP local-controls popup SHALL be presentation-only and SHALL have at most one active target in the room presentation. Its safe target identity SHALL be the current room/session identity plus exact Audio `record_id` plus stable channel identity (`section` + `oid`). That target identity SHALL NOT substitute for application-owned exact-row/current interaction authority.

Popup visibility SHALL require the target room/session identity to remain current, the target `record_id` to equal the current authoritative `expanded_record_id`, the row to remain an Audio DSP presentation, and the target channel to remain present in current accepted presentation evidence.

The popup SHALL remain visible while the pointer is over either the active source level scale or the corresponding popup. A short single-shot presentation-only hide delay MAY bridge pointer travel between those surfaces. Entering another current Audio scale SHALL immediately switch the popup to the new exact channel target and invalidate any pending hide callback for the old target. Once the pointer is over neither the active source scale nor popup, the popup SHALL close even if that channel remains locally selected.

Collapse of the active Audio row, expansion/current-selection of another equipment row, room/session identity replacement, explicit presentation clear, or disappearance of the exact channel SHALL synchronously invalidate and hide the old popup context. Delayed popup callbacks SHALL be fenced by current presentation epoch/target identity so stale work cannot reopen an invalid popup or hide a newer target.

A same-context destructive re-render MAY preserve popup continuity only by carrying safe target identity/hover facts, resolving the replacement current scale after rebuild, and revalidating current pointer ownership. Disposable source-widget references SHALL NOT survive rebuild as evidence of currentness.

The popup and its timers SHALL own no credentials, handler/session, worker/controller, device request, retry, application request generation, mutation, or reconciliation state.

#### Scenario: Pointer moves from scale into its popup

- **GIVEN** a current expanded Audio DSP row and one current channel scale
- **WHEN** the pointer enters the scale and then moves into that channel's popup
- **THEN** the popup remains visible through the transition
- **AND** opening/keeping it visible performs zero device I/O

#### Scenario: Pointer moves directly to another channel scale

- **GIVEN** channel A currently owns the popup
- **WHEN** the pointer enters current channel B before A's deferred hide completes
- **THEN** the popup is rebound to B immediately
- **AND** a stale callback for A cannot hide B's popup

#### Scenario: Selected channel no longer pins popup

- **GIVEN** a channel remains locally selected for visual emphasis
- **WHEN** the pointer leaves both that channel's scale and its popup
- **THEN** the popup is allowed to close after the presentation-only bridge delay
- **AND** the selected visual cue MAY remain under the separate selection contract

#### Scenario: Collapse revokes popup context

- **GIVEN** a popup is visible for the current expanded Audio row
- **WHEN** that row is collapsed or another equipment row becomes current expanded presentation
- **THEN** the old popup is hidden and its target is invalidated
- **AND** a delayed/stale callback cannot make it visible again

#### Scenario: Same-context rebuild revalidates popup without stale widget authority

- **GIVEN** a current Audio popup target and unchanged room/session identity
- **WHEN** background data causes the expanded Audio presentation to be rebuilt
- **THEN** popup continuity is permitted only if the exact replacement channel remains current/expanded and current pointer hit-testing still owns the replacement scale or popup
- **AND** an old disposable QWidget is never sufficient evidence to preserve visibility

## MODIFIED Requirements

### Requirement: Network card preserves all available canonical connection evidence

The titled network-connections card SHALL use a compact summary tree/table with columns equivalent to `Коммутатор (IP)`, `Порты`, and `Подключено устройств`. Rendering, hover, disclosure, child-row display, and local table interaction SHALL be presentation-only and SHALL perform no device network I/O.

Canonical connection evidence SHALL be presented according to these exact cases:

```text
switch_ip_address known + switch_port known
    -> one summary row for the exact switch IP with that port in its summary

switch_ip_address known + switch_port null
    -> one summary row for the exact switch IP; its port summary may be `Нет данных`

switch_ip_address null + switch_port known
    -> do not invent or merge switch identity
    -> one record-bound `Коммутатор не определён` row with that exact port and count 1

switch_ip_address null + switch_port null
    -> that record contributes no switch/port topology evidence
```

Records with unknown switch IP but known port SHALL NOT be grouped together merely because port text matches. Each such summary row remains tied to the exact canonical record evidence so no fictitious common switch is created.

For each authoritative switch-IP row, attached canonical room-equipment records SHALL be ordered by canonical `record_id`. Its `Порты` cell SHALL collect non-null canonical `switch_port` values in that order and de-duplicate by first occurrence:

```text
zero known child ports     -> `Нет данных`
one unique known port      -> that exact port, e.g. `Gi1/0/5`
multiple unique ports      -> comma-separated exact values in deterministic child order
```

The summary row SHALL use a safe generic name equivalent to `SW (<IP>)` unless safe unique current canonical display evidence establishes a user-friendly name. The displayed ports summary and record count SHALL not be persisted as canonical data and SHALL not be used as switch identity, routing, or device-topology authority.

Each known-switch summary row SHALL be a real disclosure parent with one visual child per current canonical room-equipment record attached to that exact switch, ordered by canonical `record_id`. A child SHALL display safe current equipment identity in the first column and that exact record's canonical `switch_port` or `Нет данных` in the Ports column; the parent remains the owner of the aggregate count. Child rows are read-only presentation of existing canonical records and SHALL NOT become target/routing/topology authority or start device I/O.

User expansion/collapse of a known-switch row SHALL update presentation-local disclosure state only. That state SHALL survive background refresh/re-render while the exact `RoomDiagnosticSessionIdentity` remains unchanged and the switch row still exists. Background refresh SHALL NOT independently expand or collapse a current switch row. A different room/session identity or explicit presentation clear SHALL reset prior disclosure state rather than restore it into the new context. The default for a newly encountered known-switch row in a new presentation context SHALL be collapsed.

For a record-bound `Коммутатор не определён` row with a known canonical port, the `Порты` cell SHALL display that exact port and count `1`. Such rows SHALL remain ungrouped and need not expose disclosure children because no authoritative common switch identity exists.

If the room contains no presentable switch-IP or port evidence at all, the card SHALL show a safe empty state equivalent to `Нет данных о сетевых подключениях` rather than an invented topology.

The confirmed product decision that room switches with zero attached canonical equipment are not implemented remains unchanged. Current schema v4 cannot authoritatively establish such a switch, so implementation SHALL NOT fabricate it merely to provide an empty disclosure parent.

#### Scenario: Two room devices share a switch

- **GIVEN** two room records contain the same non-null canonical `switch_ip_address`
- **AND** their canonical ports are `Gi1/0/5` and `Gi1/0/6`
- **WHEN** the network summary renders
- **THEN** one switch summary row is shown for that IP
- **AND** its Port summary displays `Gi1/0/5, Gi1/0/6` and its device count is `2`
- **AND** expanding that row reveals exactly those two canonical equipment children in deterministic `record_id` order
- **AND** neither displayed summary nor children become canonical switch/target state

#### Scenario: Parent port summary de-duplicates repeated child evidence

- **GIVEN** several canonical records under one exact switch IP contain the same non-null canonical port text
- **WHEN** the network summary renders
- **THEN** the repeated port appears once according to first canonical `record_id` occurrence
- **AND** each canonical record may still appear as its own disclosed visual child
- **AND** the summary does not replace the per-record canonical evidence

#### Scenario: Known port with missing switch IP is not lost

- **GIVEN** one room record has null `switch_ip_address` and non-null canonical `switch_port`
- **WHEN** the network card renders
- **THEN** the known port remains visible under a `Коммутатор не определён` record-bound row with count `1`
- **AND** no switch IP, shared switch identity, or fictitious disclosure group is guessed

#### Scenario: User disclosure survives same-context refresh

- **GIVEN** the operator has manually expanded or collapsed a known-switch summary row
- **AND** the current `RoomDiagnosticSessionIdentity` remains unchanged
- **WHEN** background refresh/re-render rebuilds current network evidence
- **THEN** the rebuilt current switch row restores that user disclosure state
- **AND** refresh itself does not choose the expanded/collapsed state
- **AND** restoration performs zero device I/O

#### Scenario: Empty switch state is explicitly out of current scope

- **GIVEN** the confirmed product scope defers room switches with zero attached canonical equipment
- **WHEN** no canonical room record/evidence establishes an unattached switch node
- **THEN** the GUI does not fabricate a switch solely to display an empty disclosure group
- **AND** acceptance does not require that state in this change

### Requirement: Audio DSP future gain and mute controls remain local disabled placeholders until separately authorized

The modern room Audio DSP presentation SHALL expose local controls visually associated with the currently hovered channel only. They contain a channel context/label, gain decrement `-`, current gain/value, gain increment `+`, and `Mute`; a permanent full-width selected-channel control strip is not part of the accepted dashboard. Existing selected-channel visual emphasis remains a separate local state and SHALL NOT pin this popup after pointer hover ownership is lost.

On the current change base there is no approved exact-row Audio DSP gain/mute mutation binding. Therefore:

```text
gain `-`                disabled/non-actionable
current gain/value      `—` or equivalent `Нет данных`
gain `+`                disabled/non-actionable
`Mute`                  disabled/non-actionable
```

The GUI SHALL NOT infer current gain or mute state from meter level, normalized fill, Biamp signal-source values, labels, selection state, popup history, or other local widget state. Disabled placeholders SHALL emit no application/room interaction intent, signal, worker start, handler/session acquisition, protocol command, or device request.

The popup lifetime SHALL follow the current hover/current-expanded-row contract in this change: it remains visible while the pointer is over the active scale or popup, may bridge those surfaces with a presentation-only single-shot timer, switches to another valid scale when entered, and closes when neither surface owns hover. Collapse/current-row/session-context invalidation SHALL revoke it as defined by `Audio DSP popup lifetime follows current hover and expanded-row context`.

Enabling any of these controls requires a later approved capability defining exact target identity, application-owned intent binding, mutation safety, reconciliation/readback, lifecycle/currentness, and failure semantics. The popup's local target identity SHALL never itself satisfy those requirements.

#### Scenario: Hovered channel exposes only disabled future controls

- **GIVEN** a current expanded room Audio DSP meter channel owns pointer hover
- **WHEN** its local future controls are shown
- **THEN** `-`, `+`, and `Mute` are disabled/non-actionable
- **AND** current gain/value is shown as `—` or equivalent no-data text when no authoritative field exists
- **AND** interacting with the disabled presentation starts no device I/O or mutation intent

#### Scenario: Selected channel exposes only disabled future controls

- **GIVEN** a current room Audio DSP meter channel is locally selected for visual emphasis
- **AND** its local future controls are visible only because the current hover/current-expanded-row popup contract permits them
- **WHEN** the future controls are presented for that selected channel
- **THEN** `-`, `+`, and `Mute` are disabled/non-actionable
- **AND** current gain/value is shown as `—` or equivalent no-data text when no authoritative field exists
- **AND** selection does not authorize mutation, device I/O, or keep the popup open after hover ownership is lost

#### Scenario: Local selection does not authorize or pin future controls

- **GIVEN** one Audio DSP channel remains locally selected for visual emphasis
- **WHEN** pointer hover leaves both that channel scale and the popup
- **THEN** the local controls may close
- **AND** selection neither enables those controls nor creates a mutation/network target
