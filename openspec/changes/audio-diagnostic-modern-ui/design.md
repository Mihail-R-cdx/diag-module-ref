# Design: Modern Audio DSP expanded presentation

## Context

`room-diagnostic-modern-ui` is already archived and merged into `master`. Its root `diagnostic-ui-presentation` contract establishes the common room shell, room/network cards, target-search, session-only dark/light themes, one-expanded-row accordion, and the rule that family-specific expanded content remains exact-row presentation. That foundation explicitly deferred the final Audio DSP geometry to a dedicated follow-up change.

Current source establishes two different Audio DSP data shapes on the shared `AudioDSPScreen`:

1. Extron DMP 64 Plus produces `meter_sections` with deterministic `Inputs` and `Outputs` groups. Each available channel carries exact `dbfs`, `normalized`, `name`, `oid`, and availability/outcome evidence. The current DMP map is six inputs (`40000-40005`) and four outputs (`60000-60003`).
2. Biamp Tesira Forte CI produces `signal_sources` with per-source rows whose values may be booleans, numbers, or other approved TTP scalar evidence. It does not establish the same canonical dBFS meter contract.

Current DMP lifecycle ownership is already explicit: `DMPPollingController` owns generation, request/IP/credential context, stale callback acceptance, credential fallback handoff, and successful-credential commit; `ExtronDMP64PlusMeterWorker` owns the background SSH/SIS polling loop and cleanup. The presentation receives only accepted normalized snapshots. This change must not duplicate that lifecycle.

## Goals

- Produce the approved modern Audio DSP look for exact numeric DMP meter evidence.
- Make Inputs and Outputs immediately scannable as vertical segmented dBFS meters.
- Preserve exact numeric evidence and unavailable states independently of color.
- Provide a local channel-selection affordance and future gain/mute control positions without inventing mutation authority.
- Remain visually coherent in both foundation themes and at foundation baseline/minimum sizes.
- Preserve current exact-row and DMP lifecycle authority without introducing network work from presentation events.

## Non-Goals

- No new meter acquisition protocol, OID, poll frequency, retry, or recovery policy.
- No DMP gain/mute read or mutation command.
- No Biamp gain/mute implementation.
- No conversion of non-dBFS Biamp source values into meter levels.
- No changes to target-search, common accordion header, room/network cards, or other family-specific screens.
- No standalone/single-device capability promotion into room mode.

## Decision 1: Numeric meter applicability follows accepted payload shape, not model-name UI lists

The vertical meter view applies when the current exact-row accepted Audio DSP payload contains `meter_sections` with channel records that carry the existing normalized meter contract (`available`, `dbfs` and `normalized` when available). Presentation SHALL NOT keep a second model-name allowlist solely to decide whether a vertical meter is legal.

For the current baseline this is the Extron DMP 64 Plus path. If a future approved producer emits the same canonical meter-section contract, presentation may render that contract without changing device authority. Conversely, a payload containing only `signal_sources` remains on the source/value presentation path even if the device category is Audio DSP.

The GUI SHALL NOT derive a numeric dBFS value from arbitrary `signal_sources`, boolean state, raw text, or channel labels.

## Decision 2: Vertical segmented meters preserve canonical dBFS evidence

At the foundation baseline viewport (`1440 x 900` logical pixels), the expanded Audio DSP meter area SHALL present two peer section cards in one horizontal row where width permits:

```text
Inputs / sources     approximately 55-62% of meter-area width
Outputs / destinations approximately 38-45% of meter-area width
```

The wider Inputs card reflects six current input channels versus four output channels; the ratio is presentation only and is not device authority.

Each channel is represented as a vertical meter column with these baseline proportions:

```text
channel column width       56-76 px
active meter track width   18-28 px
meter track height         180-240 px
segment count              20
segment gap                2-3 px
channel-to-channel gap     8-14 px
channel label              1-2 compact lines below the meter
numeric value              directly below/adjacent to the meter, before controls
```

The meter has a fixed visual scale matching the existing DMP normalized projection from `-60 dBFS` through `+12 dBFS`. The exact accepted `dbfs` value remains the operator-readable truth; meter fill is only a visualization of the accepted `normalized` value.

Twenty equal visual segments SHALL be used. Segments above the accepted level remain neutral/inactive. Filled segments use semantic zones based on the corresponding fixed visual scale position:

```text
-60 dBFS .. < -18 dBFS    success/green zone
-18 dBFS .. <  -6 dBFS    warning/yellow zone
 -6 dBFS .. +12 dBFS      elevated/orange zone
```

The zone colors are presentation semantics, not diagnostic state classifications. Numeric dBFS remains visible, so the operator is never required to infer the value from color alone. Theme-aware semantic palette tokens SHALL be used rather than one-off hard-coded colors that disappear in light mode.

An unavailable channel SHALL render an empty/neutral segmented track and a non-color value equivalent to `— dBFS`; it SHALL NOT fabricate `0 dBFS`, reuse the previous value as current, or classify the channel as failed merely because the meter value is unavailable.

## Decision 3: Channel selection is local presentation state only

A click/focus action on a meter column MAY select one current channel for visual emphasis. Selection is local UI state and SHALL NOT:

- alter room/current-record authority;
- alter automatic acquisition order;
- start or stop DMP polling;
- acquire a handler/session;
- change credentials or retry state;
- send a device command.

The selected channel SHALL have a non-color cue in addition to optional color, such as a visible outline plus a small `Выбрано`/selection marker or equivalent accessible state. Merely changing theme SHALL preserve the same local selected channel when the exact row/context remains current.

No meter channel is required to be auto-selected on row expansion. If no channel is selected, the future-control area remains in an explicit no-selection/disabled state rather than silently choosing the first channel as authority.

Selection SHALL be cleared when the exact room row/context is replaced or superseded. A continuous snapshot for the same current exact row MAY retain selection by stable channel identity (`section` + `oid`) while updating only its current meter value.

## Decision 4: Gain/mute positions are disabled future controls on this change base

The target visual design reserves an Audio DSP control strip associated with the locally selected channel. It contains, in compact order, an exact channel label/context, gain decrement `-`, current gain/value display, gain increment `+`, and `Mute`.

At baseline, the strip sits directly below the meter groups or inside the selected-channel detail band immediately adjacent to them; it is not placed in the global toolbar and is never detached from the current Audio DSP expanded row.

Current `master` does not expose an approved exact-row Audio DSP gain/mute mutation binding for this room presentation. Therefore this change SHALL implement these items only as disabled/non-actionable placeholders:

- `-` disabled;
- current gain displays `—`/`Нет данных` because no authoritative gain field exists in the accepted DMP meter snapshot;
- `+` disabled;
- `Mute` disabled and not visually represented as an actual current mute state without authoritative evidence.

The placeholders SHALL emit no application intent, signal, worker, handler call, network request, or mutation. A future change may enable them only after an approved capability defines target identity, mutation safety, reconciliation/readback, exact-row lifecycle, and registry/application binding.

This avoids a hidden mutation path while still stabilizing the future visual layout.

## Decision 5: Biamp/non-meter evidence remains a truthful fallback presentation

Current Biamp Tesira Forte CI status is read-only `signal_sources`, not the DMP meter-section contract. This change SHALL preserve that evidence as source cards/tables or an equivalent modernized scalar presentation. It MAY receive family-consistent spacing, typography, cards, and theme styling, but SHALL NOT:

- draw a vertical dBFS meter for a boolean or arbitrary scalar;
- invent Inputs/Outputs that the payload does not establish;
- invent gain or mute state;
- start a separate polling lifecycle to make the screen look like DMP.

If no numeric meter sections are available, the UI remains explicit about the type of evidence it actually has.

## Decision 6: Presentation events never create a second live lifecycle

Existing application/composition ownership remains unchanged.

The following events are presentation-only and SHALL perform zero device I/O by themselves:

- row expand/collapse;
- channel select/deselect;
- meter repaint/animation;
- dark/light theme toggle;
- resizing/reflow/scrolling;
- hover/focus over disabled controls.

The Audio DSP view consumes only current accepted row data. It SHALL NOT create another `QTimer`, polling worker, `DMPPollingController`, handler/session, credential plan, or retry lane to animate or refresh meters.

Existing DMP callbacks remain accepted/rejected by application-owned context before presentation update. A stale snapshot from an old model/IP/record/credential/request/generation cannot update the replacement row merely because a widget with the same screen type still exists.

Expand/collapse SHALL NOT leak an extra polling/session lane. If the current room lifecycle already owns a live Audio DSP lane for the exact row, the presentation may attach/detach visually without creating a duplicate. Cleanup/cancellation stays on the existing owning lifecycle.

## Decision 7: Theme and responsive behavior preserve geometry and evidence

The change inherits foundation baseline `1440 x 900` and minimum `1180 x 720` logical-pixel requirements.

At baseline, Inputs and Outputs are side by side. At narrower supported widths, controlled reflow MAY stack the two section cards vertically or allow the existing expanded-content scroll area, provided:

- every channel remains reachable;
- numeric dBFS remains readable;
- labels are not replaced solely by tooltips;
- selected-channel cue and disabled control strip remain reachable;
- reflow does not change channel identity or data authority.

Dark/light theme changes SHALL alter style tokens only. Meter dimensions, channel ordering, selected identity, dBFS values, and lifecycle state SHALL not change merely because the theme changed. The application continues to start in dark theme according to the foundation; this change adds no theme persistence.

## Ordering and identity

For current DMP snapshots, section and channel order SHALL follow accepted payload order, which is already deterministic (`Inputs` then `Outputs`, with channel OIDs in the canonical DMP meter map order). Presentation SHALL NOT sort channels by current dBFS value, availability, or color zone.

Stable selected identity uses the accepted exact-row context plus (`section`, `oid`). Channel label is presentation text and SHALL NOT substitute for OID/context authority.

## Expected source impact

The primary implementation target is `gui/screens/audio_dsp_screen.py`. Theme token additions in `gui/theme.py` or a focused reusable presentation widget are acceptable if they remain presentation-only and do not create lifecycle authority.

A change to DMP protocol helpers, workers, `DMPPollingController`, room interaction lifecycle, credentials, handlers, or dispatch is not expected. If implementation believes one is necessary, it SHALL stop and return for architecture review rather than silently expanding scope.

## Validation strategy

### Focused automated coverage

Add/adjust tests to prove at least:

- six current DMP Inputs and four Outputs render in deterministic group/order;
- meter uses accepted normalized fill and displays exact numeric `dbfs` text;
- unavailable channel shows neutral meter + `— dBFS` and never stale/current fabrication;
- semantic zone styling is theme-aware while numeric value remains visible;
- selected channel has a non-color cue;
- no implicit first-channel authority is required;
- gain `-`, value, `+`, and `Mute` placeholders are disabled and emit no mutation intent;
- Biamp `signal_sources` remain non-fabricated scalar/source presentation;
- repeated current snapshots update values without changing channel order or exact selected identity;
- stale DMP callbacks still cannot update a superseded context through existing lifecycle tests;
- theme toggle and channel selection do not start workers/network operations;
- expand/collapse does not create duplicate live polling/session ownership.

### Manual visual acceptance

From an implementation/validation build using controlled fixture data, capture local untracked screenshots for:

- `1440 x 900` dark theme with DMP meter view;
- `1440 x 900` light theme with the same data;
- `1180 x 720` supported minimum with all meter/control content reachable.

Verify proportions, Inputs/Outputs hierarchy, vertical segment readability, dBFS labels, selected cue, disabled controls, and geometry-stable theme behavior. Screenshots are validation aids and SHALL NOT become required repository artifacts unless separately approved.

### Full workflow

Implementation still requires focused tests, full offline tests, repository-local strict validation, and Git diff checks. Independent validation must use a clean detached worktree from the current published feature HEAD. Because archive will add requirements to an existing root spec, independent validation SHALL also perform a disposable archive-applicability check before `READY FOR ARCHIVE`.
