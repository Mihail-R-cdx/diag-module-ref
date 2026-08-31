## ADDED Requirements

### Requirement: Expanded Audio DSP redesign targets the current room exact-row presentation surface

MIH-10 SHALL render its modern Audio DSP content inside the current room-mode exact-row presentation owned by `RoomDiagnosticTreeWidget`. On the current change base, an expandable Audio DSP row is projected through `RoomReadOnlyPresentation`, and `screen_key == "audio_dsp"` is rendered by its Audio DSP builder.

A focused presentation-only Audio DSP widget/component MAY be extracted and embedded from that room path. Such a widget SHALL NOT own room identity, request generation, credentials, polling/session lifecycle, or network I/O.

The standalone `AudioDSPScreen` SHALL NOT be selected, embedded, or promoted as a room capability merely because it represents the same device family. It MAY reuse a presentation-only widget as a secondary consumer after the room target is satisfied, but standalone rendering is not MIH-10 acceptance authority.

#### Scenario: Expanded room Audio DSP row uses the modern presentation

- **GIVEN** the current room session contains an expandable Audio DSP exact row
- **WHEN** the operator expands that row
- **THEN** the modern Audio DSP presentation is rendered inside the `RoomDiagnosticTreeWidget` exact-row content
- **AND** room/record authority remains the current exact row
- **AND** standalone `AudioDSPScreen` is not required or promoted as room authority

#### Scenario: Optional reusable widget remains presentation-only

- **GIVEN** implementation extracts a focused Audio DSP meter widget for reuse
- **WHEN** that widget is embedded in the room Audio DSP projection
- **THEN** it consumes current accepted presentation data only
- **AND** it does not create or own a worker, handler/session, credential plan, room generation, or device request

### Requirement: Expanded Audio DSP numeric meter evidence uses a deterministic vertical segmented presentation

When the current accepted exact-row Audio DSP presentation receives numeric `meter_sections` evidence, it SHALL render that evidence as separate Input/source and Output/destination groups using vertical segmented meters. Applicability SHALL follow the accepted payload contract rather than a presentation-owned model-name allowlist: a channel is numeric-meter capable only when its accepted channel evidence uses the existing meter contract with `available` and, when available, numeric `dbfs` plus numeric `normalized`.

For the current change base, Extron DMP 64 Plus provides deterministic `Inputs` and `Outputs` meter sections with six input channels and four output channels. Presentation SHALL preserve accepted section/channel order and SHALL NOT sort by value, availability, outcome, color zone, or local selection.

At the accepted baseline viewport (`1440 x 900` logical pixels), the Audio DSP content SHALL form a compact dashboard with a narrow General information card, a dominant central meter area, and a narrow Quick actions card. Inputs and Outputs SHALL appear as peer section cards in one horizontal central meter area where width permits; Inputs receive more width than Outputs because the accepted DMP payload contains six Inputs and four Outputs.

Each numeric meter channel SHALL have a compact ordinal caption above its meter and visible numeric dBFS evidence below it. The caption SHALL omit the repeated `Input` or `Output` prefix, while exact `section` + `oid` remains the channel identity. Exact pixel sizes, gaps, and card ratios are presentation tuning rather than a normative contract. Each meter SHALL have exactly 20 segments and retain deterministic order, visible numeric evidence, and supported-size reachability.

The visual scale SHALL correspond to `-60 dBFS` through `+12 dBFS`. Accepted numeric `dbfs` SHALL remain visibly operator-readable and authoritative as evidence. Accepted `normalized` SHALL be used only for meter fill.

For an available channel, presentation SHALL calculate fill deterministically as:

```text
n = clamp(accepted normalized, 0.0, 1.0)
filled_segments = floor(n * 20 + 0.5)
```

This is explicit round-half-up behavior producing an integer from `0` through `20`; language/runtime banker rounding SHALL NOT substitute for this formula.

Physical meter segments SHALL be indexed bottom-to-top from `0` through `19`. Each segment SHALL use the fixed midpoint:

```text
segment_midpoint_dbfs(i) = -60 + (i + 0.5) * 3.6
```

A filled segment SHALL use theme-aware semantic styling according to that midpoint:

```text
midpoint < -18 dBFS         green/success zone
-18 <= midpoint < -6 dBFS   yellow/warning zone
midpoint >= -6 dBFS         orange/elevated zone
```

Unfilled segments remain neutral/inactive. Color SHALL NOT replace numeric meaning.

When `available = false`, numeric presentation SHALL render an empty/neutral segmented track and a non-color value equivalent to `— dBFS`; it SHALL NOT fabricate `0 dBFS` or reuse a prior numeric value as current.

The redesign SHALL preserve current accepted safe structured diagnostic evidence separately from numeric meter value. If the accepted channel contains `outcome`, the room presentation SHALL keep that value visible through a secondary status/detail line, badge, or tooltip. If an accepted safe `error_code` is present, it MAY be shown alongside the structured outcome. Raw protocol payload, command echo, debug text, exception text, or newly inferred categories SHALL NOT be introduced by this presentation change.

#### Scenario: Current DMP snapshot renders deterministic Input and Output meters

- **GIVEN** the current accepted exact-row Audio DSP payload contains the baseline DMP `Inputs` section with six channels and `Outputs` section with four channels
- **WHEN** the expanded room Audio DSP presentation renders at the baseline viewport
- **THEN** Inputs and Outputs are shown as separate peer groups in accepted order
- **AND** each available channel renders one 20-segment vertical meter using the exact fill formula
- **AND** each channel visibly shows its accepted numeric `dbfs`
- **AND** no channel is reordered by value, availability, outcome, or color

#### Scenario: Quantization is deterministic at segment boundaries

- **GIVEN** an accepted available channel has normalized value `n`
- **WHEN** the meter determines its filled segment count
- **THEN** it uses `floor(clamp(n, 0, 1) * 20 + 0.5)` exactly
- **AND** each filled physical segment derives its semantic zone from the fixed segment midpoint
- **AND** no alternative floor, ceil, banker-rounding, or value-dependent zone algorithm is used

#### Scenario: Unavailable numeric channel preserves diagnostic outcome

- **GIVEN** a current accepted meter channel has `available = false`
- **AND** its accepted evidence contains a structured `outcome`
- **WHEN** the room Audio DSP meter view renders
- **THEN** its segmented track is neutral/empty
- **AND** its visible numeric value is equivalent to `— dBFS`
- **AND** the safe structured `outcome` remains available in secondary presentation
- **AND** an accepted safe `error_code` MAY also be shown when present
- **AND** no prior numeric value or fabricated `0 dBFS` is shown as current

### Requirement: Audio DSP channel selection is stable local non-authoritative room presentation state

The expanded numeric Audio DSP room view MAY allow the operator to select one current meter channel for visual emphasis. Channel selection SHALL be local presentation state only and SHALL NOT change room/record authority, diagnostic acquisition order, credentials, request generation/currentness, handler/session ownership, polling state, retry state, or device configuration.

Selected-channel identity SHALL be scoped by current exact room context plus `record_id` plus stable channel identity (`section` + `oid`). A selected channel SHALL have a non-color cue in addition to optional color, such as a visible outline plus a selection marker/accessibility state. No first channel SHALL become implicitly selected merely because the row is expanded.

While the same exact room context/generation and same `record_id` remain current, every accepted snapshot update SHALL preserve the selected channel if that accepted payload still contains the same `section` + `oid`. Rendering a new current meter value SHALL NOT clear that valid same-context selection.

Selection SHALL clear when the exact room context/generation is superseded or cleared, when the selected record is replaced/removed, or when accepted current evidence no longer contains the selected `section` + `oid`.

Because current room rendering may rebuild child presentation widgets, selected-channel state SHALL be owned at a room-presentation level that survives such same-context rebuilds; a disposable child widget SHALL NOT be the sole owner if that would reset valid selection on every accepted snapshot. This ownership remains non-authoritative presentation state.

#### Scenario: Operator selects a current channel

- **GIVEN** an expanded current Audio DSP row with no selected channel
- **WHEN** the operator selects one meter channel
- **THEN** that channel receives an explicit non-color selection cue
- **AND** no worker, timer, handler, session, credential attempt, retry, room interaction intent, or device command is started by selection
- **AND** room acquisition order and exact-row authority remain unchanged

#### Scenario: Same-context accepted snapshot preserves selected channel

- **GIVEN** a channel is selected for the current exact room context and record by `section` + `oid`
- **AND** a later accepted current snapshot still contains that same channel identity
- **WHEN** the room presentation rebuilds or updates its Audio DSP child
- **THEN** the meter value updates
- **AND** the same channel SHALL remain selected
- **AND** selection does not alter callback-currentness authority

#### Scenario: Supersession or channel disappearance clears selection

- **GIVEN** one Audio DSP row/context has a locally selected channel
- **WHEN** the exact room context is superseded, the record is removed/replaced, or the selected `section` + `oid` is absent from accepted current evidence
- **THEN** the old local channel selection is cleared
- **AND** a stale callback cannot restore it as current selection

### Requirement: Audio DSP future gain and mute controls remain local disabled placeholders until separately authorized

The modern room Audio DSP presentation SHALL expose local controls visually associated with a hovered channel or a selected/pinned channel. They contain a channel context/label, gain decrement `-`, current gain/value, gain increment `+`, and `Mute`; a permanent full-width selected-channel control strip is not part of the accepted dashboard.

On the current change base there is no approved exact-row Audio DSP gain/mute mutation binding. Therefore:

```text
gain `-`                disabled/non-actionable
current gain/value      `—` or equivalent `Нет данных`
gain `+`                disabled/non-actionable
`Mute`                  disabled/non-actionable
```

The GUI SHALL NOT infer current gain or mute state from meter level, normalized fill, Biamp signal-source values, labels, or local widget state. Disabled placeholders SHALL emit no application/room interaction intent, signal, worker start, handler/session acquisition, protocol command, or device request.

Enabling any of these controls requires a later approved capability defining exact target identity, application-owned intent binding, mutation safety, reconciliation/readback, lifecycle/currentness, and failure semantics.

#### Scenario: Selected channel exposes only disabled future controls

- **GIVEN** a current room Audio DSP meter channel is locally selected
- **WHEN** the local future controls are shown
- **THEN** `-`, `+`, and `Mute` are disabled/non-actionable
- **AND** current gain/value is shown as `—` or equivalent no-data text when no authoritative field exists
- **AND** interacting with the disabled presentation starts no device I/O or mutation intent

### Requirement: Audio DSP Quick actions remain truthful to existing safe room capability

The narrow Audio DSP Quick actions card SHALL contain only already-approved existing safe local room actions supplied by the current room presentation. It SHALL NOT add, imply, or enable an Audio DSP gain/mute or other device mutation capability. When no approved action is supplied, it SHALL show a truthful non-actionable empty state.

#### Scenario: Quick actions do not fabricate a capability

- **GIVEN** an expanded Audio DSP room row has no approved local action supplied to its presentation
- **WHEN** the Audio DSP dashboard renders
- **THEN** its Quick actions card shows a truthful non-actionable empty state
- **AND** no new device request, mutation intent, worker, or session is created

### Requirement: Audio DSP redesign preserves room lifecycle bindings and stale-operation boundaries

The modern Audio DSP room presentation SHALL consume only accepted current exact-row data from the existing application/composition room lifecycle and SHALL NOT create or substitute another Audio DSP/DMP polling/session lifecycle.

For Extron DMP 64 Plus, the existing lifecycle separation SHALL remain:

```text
room automatic acquisition -> `dmp_one_shot`
room live interaction       -> `dmp_room_live`
standalone screen lifecycle -> `DMPPollingController`
```

The room accordion SHALL NOT be routed through standalone `DMPPollingController`, and this change SHALL NOT add a second DMP room live binding or modify unified registry capability merely to render the new presentation.

The following presentation events SHALL perform zero device network I/O by themselves:

- equipment row expand/collapse;
- channel select/deselect;
- meter repaint/visual animation;
- hover/focus over meter or disabled controls;
- dark/light theme toggle;
- resize, reflow, or scrolling.

Presentation SHALL NOT create a polling or lifecycle `QTimer`, worker, controller, handler/session, credential plan, retry lane, or mutation lane merely to drive the modern visual design. A focused presentation widget MAY own a single-shot `QTimer` solely to defer hiding or repositioning its local controls, provided the timer performs no device I/O, emits no room interaction intent, starts no worker/session, and does not drive acquisition, retry, or mutation.

Existing application-owned room generation/record/credential/currentness checks SHALL remain authority for accepting callbacks. A stale snapshot from a superseded room context SHALL NOT update the replacement Audio DSP presentation, selected-channel state, credential memory, or lifecycle state.

Expanding/collapsing the Audio DSP row SHALL NOT create, leak, or duplicate a room live/session lane. Theme changes SHALL alter styling only and SHALL NOT restart acquisition. Cleanup/cancellation remains owned by the existing room/background lifecycle and SHALL NOT move network cleanup into the GUI thread.

If implementation appears to require changes to `dmp_one_shot`, `dmp_room_live`, dispatch registry, DMP protocol helpers/workers/handlers, credentials, or `DMPPollingController`, it SHALL return for architecture review before making those changes.

#### Scenario: Room DMP lifecycle remains on registered room bindings

- **GIVEN** the exact current room row is `Extron DMP 64 Plus`
- **WHEN** automatic acquisition or an approved room live interaction supplies data for the modern Audio DSP presentation
- **THEN** automatic acquisition remains owned by `dmp_one_shot`
- **AND** room live interaction remains owned by `dmp_room_live`
- **AND** standalone `DMPPollingController` is not promoted into room authority

#### Scenario: Theme toggle during room live DMP presentation is local only

- **GIVEN** a current room Audio DSP row is receiving accepted live DMP snapshots
- **WHEN** the operator switches between dark and light theme
- **THEN** meter styling changes without restarting room acquisition/session ownership
- **AND** channel order, exact-row authority, accepted evidence, and currentness remain unchanged
- **AND** no new device I/O is started by theme toggle

#### Scenario: Stale room DMP snapshot stays rejected

- **GIVEN** an old room DMP context has been superseded by another context
- **WHEN** the old context later produces a callback
- **THEN** that callback cannot update the current modern Audio DSP view
- **AND** it cannot restore stale selected-channel state or restart acquisition

### Requirement: Non-meter Audio DSP evidence is not fabricated into dBFS presentation

Audio DSP payloads that do not establish the numeric `meter_sections` contract SHALL remain truthful to accepted evidence. Current Biamp Tesira Forte CI `signal_sources` rows MAY receive family-consistent card, spacing, typography, and theme styling, but arbitrary scalar or boolean source values SHALL NOT be converted into dBFS levels, vertical numeric meters, invented Input/Output groups, gain state, or mute state.

The safe source/value presentation MAY remain tabular/card-based. If no numeric meter sections are available, the UI SHALL clearly present the evidence it actually has rather than visually implying DMP-equivalent meter authority.

#### Scenario: Biamp boolean source value stays scalar evidence

- **GIVEN** a current Biamp Audio DSP payload contains `signal_sources` with boolean/scalar values and no numeric `meter_sections`
- **WHEN** the expanded room Audio DSP presentation renders
- **THEN** those values remain source/scalar evidence
- **AND** no dBFS value or vertical numeric meter is fabricated from them
- **AND** no gain or mute state is inferred from them

### Requirement: Modern room Audio DSP content remains usable in foundation themes and supported sizes

The Audio DSP redesign SHALL inherit the foundation baseline viewport of `1440 x 900` and minimum supported window of `1180 x 720` logical pixels. At baseline width it SHALL show the accepted dashboard hierarchy: narrow General information, dominant central Inputs/Outputs meter area, and narrow Quick actions. Inputs and Outputs cards SHALL be side by side in the central area. At narrower supported widths, controlled reflow MAY place auxiliary cards above the meter area, stack the meter cards vertically, or use existing expanded-content scrolling, provided all current channels, numeric values, secondary diagnostic outcome detail, selection cue, and disabled local controls remain reachable.

Responsive behavior SHALL NOT change channel identity, order, accepted numeric/structured evidence, selected exact channel, or device lifecycle authority. Channel labels SHALL remain visible rather than existing solely as hover tooltips.

Dark and light themes SHALL preserve equivalent geometry, channel order, evidence, disabled-control meaning, and selection meaning. Theme styling SHALL use shared/theme-aware semantic tokens. This change SHALL NOT persist theme across application restarts and SHALL NOT change the foundation rule that the application starts in dark theme.

#### Scenario: Baseline dark and light room layouts preserve evidence

- **GIVEN** the same accepted current room DMP meter snapshot
- **WHEN** the expanded Audio DSP row is rendered at `1440 x 900` in dark theme and then light theme
- **THEN** dashboard hierarchy, Inputs/Outputs grouping, compact captions, channel order, segment count, numeric dBFS, structured outcome detail, disabled-control state, and selected identity remain equivalent
- **AND** only theme styling changes

#### Scenario: Minimum supported window keeps room Audio DSP content reachable

- **WHEN** the application is shown at `1180 x 720` logical pixels with an expanded numeric Audio DSP room row
- **THEN** controlled reflow/scrolling keeps every current meter channel, numeric value, secondary diagnostic outcome, selected cue, and disabled local control reachable
- **AND** no channel/data authority changes because of layout reflow
