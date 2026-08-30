## ADDED Requirements

### Requirement: Expanded Audio DSP numeric meter evidence uses a vertical segmented presentation

When the current exact-row Audio DSP presentation receives accepted numeric `meter_sections` evidence, it SHALL render that evidence as separate Input/source and Output/destination meter groups using vertical segmented meters. Applicability SHALL follow the accepted payload contract rather than a second presentation-owned model-name allowlist: a channel is numeric-meter capable only when its accepted channel evidence uses the existing meter contract with `available` and, when available, numeric `dbfs` plus `normalized`.

For the current change base, Extron DMP 64 Plus provides deterministic `Inputs` and `Outputs` meter sections with six input channels and four output channels. Presentation SHALL preserve accepted section/channel order and SHALL NOT sort by current value, availability, color zone, or local selection.

At the foundation baseline viewport (`1440 x 900` logical pixels), Inputs and Outputs SHALL appear as peer section cards in one horizontal meter area where width permits, with approximate meter-area proportions:

```text
Inputs / sources           55-62%
Outputs / destinations     38-45%
```

Each numeric meter channel SHALL use these baseline visual proportions:

```text
channel column width       56-76 px
active meter track width   18-28 px
meter track height         180-240 px
segment count              20
segment gap                2-3 px
channel-to-channel gap     8-14 px
channel label              1-2 compact lines below meter
numeric dBFS               directly below/adjacent to meter before controls
```

The visual meter scale SHALL correspond to the existing normalized DMP projection from `-60 dBFS` through `+12 dBFS`. The accepted numeric `dbfs` value SHALL remain visibly operator-readable and authoritative as evidence; `normalized` SHALL be used only for meter fill. Twenty equal visual segments SHALL be rendered. Segments above the accepted level SHALL remain neutral/inactive. Filled segments SHALL use theme-aware semantic zones according to their fixed scale position:

```text
-60 dBFS .. < -18 dBFS     green/success zone
-18 dBFS .. <  -6 dBFS     yellow/warning zone
 -6 dBFS .. +12 dBFS       orange/elevated zone
```

The color zone SHALL NOT replace numeric meaning. An unavailable channel SHALL render a neutral/empty segmented track and a non-color value equivalent to `— dBFS`; presentation SHALL NOT fabricate `0 dBFS`, retain an old value as current, or classify unavailability as a different device state.

#### Scenario: Current DMP snapshot renders deterministic Input and Output meters

- **GIVEN** the current accepted exact-row Audio DSP payload contains the baseline DMP `Inputs` section with six channels and `Outputs` section with four channels
- **WHEN** the expanded Audio DSP presentation renders at the baseline viewport
- **THEN** Inputs and Outputs are shown as separate peer groups in accepted order
- **AND** each available channel renders one 20-segment vertical meter from its accepted `normalized` value
- **AND** each channel visibly shows its accepted numeric `dbfs` value
- **AND** no channel is reordered by level, availability, or color

#### Scenario: Unavailable numeric channel remains explicit

- **GIVEN** a current accepted meter channel has `available = false` and no current numeric dBFS evidence
- **WHEN** the Audio DSP meter view renders
- **THEN** its segmented track is neutral/empty
- **AND** its visible value is equivalent to `— dBFS`
- **AND** no prior channel value is reused as current
- **AND** the GUI does not fabricate `0 dBFS`

#### Scenario: Meter color never replaces numeric evidence

- **GIVEN** a current available meter value crosses one or more semantic zone boundaries
- **WHEN** the meter is rendered in either supported theme
- **THEN** filled segments use the applicable theme-aware green/yellow/orange zone styling
- **AND** the accepted numeric dBFS value remains visible
- **AND** color alone is not required to determine the meter value

### Requirement: Audio DSP channel selection is local non-authoritative presentation state

The expanded numeric Audio DSP view MAY allow the operator to select one current meter channel for visual emphasis. Channel selection SHALL be local presentation state only and SHALL NOT change room/record authority, diagnostic acquisition order, credentials, request generation, handler/session ownership, polling state, retry state, or device configuration.

Selected-channel identity SHALL be scoped to the current exact room row/context and stable channel identity (`section` plus `oid`). A selected channel SHALL have a non-color cue in addition to optional color, such as a visible outline plus a selection marker/accessibility state. No first channel SHALL be required to become implicitly selected merely because the row is expanded.

A new accepted snapshot for the same current exact row MAY retain selected-channel identity while updating its displayed meter value. Replacing/superseding the exact row/context SHALL clear that local selection so stale UI state cannot become authority for another device or request. Theme changes MAY preserve the same local selection only while the exact row/context remains current.

#### Scenario: Operator selects a current channel

- **GIVEN** an expanded current Audio DSP row with no selected channel
- **WHEN** the operator selects one meter channel
- **THEN** that channel receives an explicit non-color selection cue
- **AND** no worker, timer, handler, session, credential attempt, retry, or device command is started by selection
- **AND** room acquisition order and exact-row authority remain unchanged

#### Scenario: Current snapshot updates a selected channel

- **GIVEN** a channel is selected for the current exact row by its section and OID
- **WHEN** another accepted current snapshot for that same exact row updates the channel level
- **THEN** the numeric/meter value updates
- **AND** the same channel MAY remain selected
- **AND** selection does not alter callback-currentness authority

#### Scenario: Superseded row cannot inherit selected channel authority

- **GIVEN** one Audio DSP row/context has a locally selected channel
- **WHEN** that exact row/context is replaced or superseded
- **THEN** the old local channel selection is cleared for the replacement context
- **AND** a stale callback cannot restore it as current selection

### Requirement: Audio DSP future gain and mute controls remain disabled placeholders until separately authorized

The modern Audio DSP presentation SHALL reserve a selected-channel control strip containing a channel context/label, gain decrement `-`, current gain/value, gain increment `+`, and `Mute`. The strip SHALL remain visually associated with the expanded Audio DSP row and selected-channel area rather than the global application toolbar.

On the current change base there is no approved exact-row Audio DSP gain/mute mutation binding for this room presentation. Therefore the control strip SHALL be presentation-only:

```text
gain `-`                disabled/non-actionable
current gain/value      `—` or equivalent `Нет данных`
gain `+`                disabled/non-actionable
`Mute`                  disabled/non-actionable
```

The GUI SHALL NOT infer current gain or mute state from DMP meter level, normalized fill, Biamp signal-source values, labels, or local widget state. Disabled placeholders SHALL emit no application mutation intent, signal, worker start, handler/session acquisition, protocol command, or device network request.

Enabling any of these controls requires a later approved capability that defines exact target identity, application-owned intent binding, mutation safety, reconciliation/readback, lifecycle/currentness, and failure semantics. This change SHALL NOT create that capability implicitly.

#### Scenario: Selected channel exposes only disabled future controls

- **GIVEN** a current Audio DSP meter channel is locally selected
- **WHEN** the future control strip is shown
- **THEN** `-`, `+`, and `Mute` are disabled/non-actionable
- **AND** current gain/value is shown as `—` or equivalent no-data text when no authoritative field exists
- **AND** interacting with the disabled presentation starts no device I/O or mutation intent

#### Scenario: Meter level is not treated as gain or mute authority

- **GIVEN** a current channel has valid dBFS meter evidence
- **WHEN** the selected-channel control strip renders
- **THEN** that meter value is not used to infer current gain
- **AND** it is not used to infer mute state
- **AND** the control placeholders remain disabled under the current approved capability set

### Requirement: Audio DSP redesign preserves application-owned live polling and stale-operation boundaries

The modern Audio DSP presentation SHALL consume only accepted current exact-row data from the existing application/composition lifecycle. It SHALL NOT create a second Audio DSP or DMP polling/session lifecycle.

The following presentation events SHALL perform zero device network I/O by themselves:

- equipment row expand/collapse;
- channel select/deselect;
- meter repaint/visual animation;
- hover/focus over meter or disabled controls;
- dark/light theme toggle;
- resize, reflow, or scrolling.

Presentation SHALL NOT create another polling `QTimer`, polling worker, `DMPPollingController`, handler/session, credential plan, retry lane, or mutation lane merely to drive the modern visual design. Existing DMP SSH/SIS work remains off the Qt GUI thread and under the current worker/controller lifecycle.

Existing application-owned generation/request/model/IP/credential/currentness checks SHALL remain the only authority for accepting DMP meter callbacks. A stale snapshot from a superseded context SHALL NOT update the replacement Audio DSP presentation, selected-channel state, credential memory, or lifecycle state.

Expanding/collapsing the Audio DSP row SHALL NOT leak or duplicate a live polling/session lane. Theme changes SHALL alter presentation styling only and SHALL NOT restart the live lifecycle. Cleanup/cancellation remains owned by the existing application/background lifecycle and SHALL NOT move network cleanup into the GUI thread.

#### Scenario: Theme toggle during live DMP presentation is local only

- **GIVEN** a current Audio DSP row is receiving accepted live DMP snapshots
- **WHEN** the operator switches between dark and light theme
- **THEN** meter styling changes without restarting the worker/session
- **AND** channel order, exact-row authority, accepted dBFS values, and currentness remain unchanged
- **AND** no new device I/O is started by the theme toggle

#### Scenario: Row presentation does not duplicate live polling

- **GIVEN** the existing application lifecycle owns a live Audio DSP polling context for one exact row
- **WHEN** the operator expands, collapses, or re-expands that row according to the existing room lifecycle
- **THEN** the modern presentation does not create an additional polling timer, worker, controller, handler, session, or credential plan
- **AND** cleanup remains governed by the existing lifecycle contract

#### Scenario: Stale DMP snapshot stays rejected

- **GIVEN** an old DMP polling context has been superseded by another row/model/IP/credential/request context
- **WHEN** the old context later produces a meter callback
- **THEN** that callback cannot update the current modern Audio DSP view
- **AND** it cannot restore stale selected-channel state or restart polling

### Requirement: Non-meter Audio DSP evidence is not fabricated into dBFS presentation

Audio DSP payloads that do not establish the numeric `meter_sections` contract SHALL remain truthful to their accepted evidence. In particular, current Biamp Tesira Forte CI `signal_sources` rows MAY receive family-consistent card, spacing, typography, and theme styling, but arbitrary scalar or boolean source values SHALL NOT be converted into dBFS levels, vertical numeric meters, invented Input/Output groups, gain state, or mute state.

The current safe source/value presentation MAY remain tabular/card-based. If no numeric meter sections are available, the UI SHALL clearly present the evidence it actually has rather than visually implying DMP-equivalent meter authority.

#### Scenario: Biamp boolean source value stays scalar evidence

- **GIVEN** a current Biamp Audio DSP payload contains `signal_sources` with boolean/scalar values and no numeric `meter_sections`
- **WHEN** the expanded Audio DSP presentation renders
- **THEN** those values remain source/scalar evidence
- **AND** no dBFS value or vertical numeric meter is fabricated from them
- **AND** no gain or mute state is inferred from them

### Requirement: Modern Audio DSP content remains usable in foundation themes and supported sizes

The Audio DSP redesign SHALL inherit the foundation baseline viewport of `1440 x 900` and minimum supported window of `1180 x 720` logical pixels. At baseline width the numeric Inputs and Outputs cards SHALL be side by side with the approved relative proportions. At narrower supported widths, controlled reflow MAY stack the two meter cards vertically or use the existing expanded-content scrolling, provided all current channels and the selected-channel control strip remain reachable.

Responsive behavior SHALL NOT change channel identity, order, numeric dBFS evidence, selected exact channel, or device lifecycle authority. Channel labels SHALL remain visible rather than existing solely as hover tooltips.

Dark and light themes SHALL preserve equivalent geometry, channel order, numeric evidence, disabled-control meaning, and selection meaning. Theme styling SHALL use shared/theme-aware semantic tokens. This change SHALL NOT persist the theme across application restarts and SHALL NOT change the foundation rule that the application starts in dark theme.

#### Scenario: Baseline dark and light layouts preserve evidence

- **GIVEN** the same accepted current DMP meter snapshot
- **WHEN** the expanded Audio DSP view is rendered at `1440 x 900` in dark theme and then light theme
- **THEN** Inputs/Outputs grouping, channel order, segment count, meter dimensions, numeric dBFS, disabled-control state, and selected identity remain equivalent
- **AND** only theme styling changes

#### Scenario: Minimum supported window keeps Audio DSP content reachable

- **WHEN** the application is shown at `1180 x 720` logical pixels with an expanded numeric Audio DSP row
- **THEN** controlled reflow/scrolling keeps every current meter channel, numeric value, selected cue, and disabled control strip reachable
- **AND** no channel/data authority changes because of layout reflow
