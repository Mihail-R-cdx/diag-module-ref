# Design: Modern Audio DSP expanded presentation

## Context

`room-diagnostic-modern-ui` is already archived and merged into `master`. The merged foundation establishes the common room shell, room/network cards, one-expanded-row accordion, exact-row authority, session-only dark/light themes, and the rule that family-specific expanded content remains on the current room-mode presentation surface.

Current source has two different Audio DSP presentation paths:

1. **Room mode** — `RoomDiagnosticTreeWidget.render()` builds a `RoomReadOnlyPresentation` for each expandable exact room row. For `screen_key == "audio_dsp"`, `RoomReadOnlyPresentation._build_audio()` renders the current `roomAudioMeasurements` table. This is the MIH-10 normative integration and acceptance surface.
2. **Standalone/single-device mode** — `AudioDSPScreen` is a separate screen with its own presentation and standalone lifecycle. It is not used by the room accordion and SHALL NOT be promoted into room mode by this change. A focused presentation-only widget MAY be reused by both surfaces, but room mode remains authority for MIH-10 acceptance.

Current accepted Audio DSP data also has two different shapes:

- Extron DMP 64 Plus provides `meter_sections` with deterministic `Inputs` and `Outputs`. Available channels carry `dbfs`, `normalized`, `name`, `oid`, `available`, `outcome`, and other structured evidence. The current DMP map is six inputs (`40000-40005`) and four outputs (`60000-60003`).
- Biamp Tesira Forte CI provides `signal_sources` containing approved TTP scalar/boolean evidence and does not establish the same canonical dBFS meter contract.

DMP lifecycle ownership differs between standalone and room mode and must remain explicit:

```text
standalone DMP screen lifecycle
    -> DMPPollingController

room automatic acquisition
    -> unified registry room_adapter_key = dmp_one_shot

room live interaction
    -> unified registry live_binding_key = dmp_room_live
```

The room presentation consumes accepted exact-row state after application-owned room currentness/lifecycle checks. MIH-10 must not replace these room bindings with the standalone controller or create a second polling/session lane.

## Goals

- Produce the approved modern Audio DSP look inside the expanded room exact-row presentation.
- Make DMP Inputs and Outputs immediately scannable as vertical segmented dBFS meters.
- Preserve exact numeric evidence and existing safe structured unavailable-channel outcomes independently of color.
- Provide stable local channel selection across accepted updates for the same current exact row without turning selection into device/application authority.
- Provide future gain/mute positions without inventing mutation authority.
- Remain visually coherent in both foundation themes and at foundation baseline/minimum sizes.
- Preserve existing room adapter/live/currentness ownership and keep presentation events free of device I/O.

## Non-Goals

- No standalone `AudioDSPScreen` promotion into room mode.
- No new meter acquisition protocol, OID, poll frequency, retry, or recovery policy.
- No DMP gain/mute read or mutation command.
- No Biamp gain/mute implementation.
- No conversion of non-dBFS Biamp source values into meter levels.
- No changes to target-search, common accordion header, room/network cards, or other family-specific screens.
- No dispatch/registry or room interaction lifecycle redesign unless a separately reviewed architecture gap is discovered.

## Decision 1: The room exact-row renderer is the normative integration target

MIH-10 SHALL change the Audio DSP content rendered inside `RoomDiagnosticTreeWidget` for the current exact row. The current implementation point is `RoomReadOnlyPresentation._build_audio()` in `gui/room_diagnostic_tree.py`.

Implementation MAY extract a focused presentation-only Audio DSP widget/component and embed it from `_build_audio()`. Such extraction SHALL NOT own room identity, request generation, credentials, polling/session lifecycle, or network I/O.

If the same focused widget is later reused by `AudioDSPScreen`, that reuse is secondary. Acceptance SHALL be proved through the room accordion. A standalone screen SHALL NOT be embedded or selected as a room capability merely because it represents the same device family.

## Decision 2: Numeric meter applicability follows accepted payload shape, not model-name UI lists

The vertical meter view applies when the current accepted exact-row Audio DSP payload contains `meter_sections` whose channel records use the existing normalized meter contract: `available`, and when available numeric `dbfs` plus numeric `normalized`.

For the current baseline this is Extron DMP 64 Plus. Presentation SHALL NOT keep a second model-name allowlist solely to decide whether the meter view is legal. Conversely, a payload containing only `signal_sources` remains on the source/value path even if its exact model belongs to Audio DSP.

The GUI SHALL NOT derive dBFS from arbitrary `signal_sources`, boolean state, raw text, channel labels, or widget state.

## Decision 3: Vertical segmented meters preserve numeric and structured diagnostic evidence

At the accepted baseline viewport (`1440 x 900` logical pixels), the expanded Audio DSP content is a compact dashboard: a narrow General information card, a dominant central meter area, and a narrow Quick actions card. The central area presents Inputs and Outputs as peer section cards in one horizontal row where width permits; Inputs receive more width than Outputs because the accepted DMP payload has six Inputs and four Outputs.

Each channel has a compact ordinal caption above its meter and accepted numeric dBFS evidence below it. The compact captions intentionally omit the repeated words `Input` and `Output`; exact `section` + `oid` remains the selection identity. Exact pixel sizes, gaps, and card ratios are visual tuning rather than a normative contract. The fixed semantic contract is 20 segments, visible numeric evidence, deterministic order, and reachability at supported sizes.

The fixed visual scale is `-60 dBFS` through `+12 dBFS`. Accepted `dbfs` remains the visible operator-readable numeric truth. Accepted `normalized` is used only to determine meter fill and SHALL NOT replace `dbfs` as displayed evidence.

### Deterministic segment quantization

Let:

```text
n = clamp(accepted normalized, 0.0, 1.0)
segment_count = 20
filled_segments = floor(n * segment_count + 0.5)
```

`filled_segments` is therefore an integer from `0` through `20` using explicit round-half-up behavior. Implementations SHALL NOT use language/runtime banker rounding or choose a different floor/ceil policy.

Segments are indexed bottom-to-top from `0` through `19`. Each segment has a fixed scale midpoint:

```text
segment_width_db = 72 / 20 = 3.6 dB
segment_midpoint_dbfs(i) = -60 + (i + 0.5) * 3.6
```

The semantic color of a **filled** physical segment is determined from that midpoint only:

```text
midpoint < -18 dBFS         green/success zone
-18 <= midpoint < -6 dBFS   yellow/warning zone
midpoint >= -6 dBFS         orange/elevated zone
```

Unfilled segments are neutral/inactive. This fixed midpoint rule makes the `-18` and `-6` transitions deterministic even though `-18` is not aligned to a 3.6 dB segment edge. Color is presentation semantics only; numeric `dbfs` remains visible.

### Unavailable-channel evidence

When `available = false`, numeric presentation SHALL show an empty/neutral segmented track and `— dBFS`. It SHALL NOT reuse a previous numeric value or fabricate `0 dBFS`.

The redesign SHALL also preserve the current accepted **safe structured diagnostic outcome** separately from numeric evidence. If accepted channel data contains `outcome`, the room presentation SHALL retain it in a secondary status/detail line, badge, or tooltip. If an accepted safe `error_code` is present, it MAY be shown alongside the structured outcome. Raw transport payload, command echo, debug text, exception text, or newly inferred categories SHALL NOT be introduced by this presentation change.

Thus, for example, `unavailable` and `sis_protocol_error` remain distinguishable without pretending either has a numeric dBFS value.

## Decision 4: Selected channel is stable local room-presentation state

Channel selection is local presentation state only. It SHALL NOT alter room/current-record authority, acquisition order, credentials, generation/currentness, handler/session ownership, polling state, retry state, or device configuration.

Stable selection identity is:

```text
current exact room context identity
+ record_id
+ section
+ oid
```

The room presentation layer SHALL preserve the selected identity across accepted snapshot renders while all of the following remain true:

- the same exact room context/generation remains current;
- the same `record_id` remains current;
- the accepted current payload still contains the same `section` + `oid` channel.

The selected channel SHALL have an explicit non-color cue in addition to optional color, such as outline + `Выбрано`/accessible selected state.

Selection SHALL clear when:

- the exact room context/generation is superseded or cleared;
- the selected `record_id` is replaced/removed;
- the selected `section` + `oid` no longer exists in accepted current evidence.

No first channel is implicitly selected on row expansion.

Because `RoomDiagnosticTreeWidget.render()` rebuilds child presentations, selection SHALL NOT be owned only by a disposable child widget if that would reset it on every accepted snapshot. A natural implementation is local non-authoritative state on `RoomDiagnosticTreeWidget` (or an equivalent room-presentation owner above the rebuilt child), passed into the Audio DSP child when rebuilt. This is an implementation choice, not a new application/device authority.

## Decision 5: Gain/mute positions are local disabled future controls on this change base

The room Audio DSP view exposes local controls visually associated with a hovered channel or a selected/pinned channel. They contain channel context/label, gain decrement `-`, current gain/value, gain increment `+`, and `Mute`. The accepted dashboard has no permanent full-width selected-channel control strip.

Current `master` does not expose an approved exact-row Audio DSP gain/mute mutation binding for this room presentation. Therefore:

```text
-                      disabled/non-actionable
current gain/value     — / Нет данных
+                      disabled/non-actionable
Mute                   disabled/non-actionable
```

The placeholders emit no room interaction intent, signal, worker start, handler/session acquisition, protocol command, or device request. Meter level SHALL NOT be interpreted as gain or mute state.

A later approved change may enable them only after exact target identity, application intent binding, mutation safety, reconciliation/readback, lifecycle/currentness, and failure semantics are specified.

Quick actions remain limited to already-approved existing safe local room actions. If no such action is supplied, the card shows a truthful non-actionable empty state. MIH-10 SHALL NOT add or imply a gain/mute or other device mutation action there.

## Decision 6: Biamp/non-meter evidence remains a truthful fallback presentation

Biamp Tesira Forte CI `signal_sources` are not the DMP meter-section contract. They remain source/value evidence. The room Audio DSP view MAY modernize spacing, cards, typography, and theme styling, but SHALL NOT:

- draw dBFS meters for arbitrary scalar/boolean values;
- invent Inputs/Outputs not established by the payload;
- invent gain/mute state;
- start a separate polling lifecycle to make Biamp look like DMP.

## Decision 7: Room lifecycle and standalone lifecycle remain separate

The modern Audio DSP room view consumes only accepted current exact-row data from the existing room lifecycle.

For Extron DMP 64 Plus the existing registry/application boundaries remain:

```text
automatic room acquisition -> dmp_one_shot
room live interaction       -> dmp_room_live
standalone screen lifecycle -> DMPPollingController
```

MIH-10 SHALL NOT route the room accordion through `DMPPollingController`, add a second DMP live binding, or modify the unified registry merely to render the new presentation.

The following events are presentation-only and SHALL perform zero device I/O by themselves:

- row expand/collapse;
- channel select/deselect;
- meter repaint/visual animation;
- hover/focus over meter or disabled local controls;
- dark/light theme toggle;
- resize, reflow, or scrolling.

The Audio DSP room view SHALL NOT create a polling or lifecycle `QTimer`, worker, controller, handler/session, credential plan, retry lane, or mutation lane. A focused widget MAY own a single-shot `QTimer` solely to defer hiding or repositioning its local control popup, provided it performs no device I/O, emits no room interaction intent, starts no worker/session, and does not drive acquisition, retry, or mutation.

Existing application-owned room generation/record/credential/currentness checks remain authority for accepting or rejecting room callbacks. A stale room snapshot cannot update a replacement Audio DSP view or restore stale channel selection.

Expand/collapse SHALL NOT create, leak, or duplicate room live/session ownership. Cleanup/cancellation remains on the existing room/background lifecycle and SHALL NOT move network cleanup into the Qt GUI thread.

If implementation appears to require changes to `dmp_one_shot`, `dmp_room_live`, dispatch registry, DMP protocol helpers, workers, handlers, credentials, or `DMPPollingController`, implementation SHALL stop and return for architecture review before making those changes.

## Decision 8: Theme and responsive behavior preserve geometry and evidence

The change inherits foundation baseline `1440 x 900` and minimum `1180 x 720` logical-pixel requirements.

At baseline, the narrow General information card, dominant central Inputs/Outputs meter area, and narrow Quick actions card form the accepted dashboard; Inputs and Outputs are side by side inside the central area. At narrower supported widths, controlled reflow MAY place the auxiliary cards above the meter area, stack the two section cards vertically, or use existing expanded-content scrolling, provided every channel, numeric value, secondary outcome detail, selected cue, and disabled local control remains reachable.

Dark/light changes alter style tokens only. Meter dimensions, channel order, selected identity, accepted dBFS/outcome evidence, and lifecycle state SHALL not change merely because the theme changed. The application continues to start in dark theme; this change adds no theme persistence.

## Ordering and identity

Current DMP section/channel order follows accepted payload order (`Inputs`, then `Outputs`, with channel OIDs in canonical DMP order). Presentation SHALL NOT sort channels by dBFS value, availability, outcome, color zone, or selection.

Channel label is presentation text and SHALL NOT substitute for `section` + `oid` identity.

## Expected source impact

Primary/normative target:

- `gui/room_diagnostic_tree.py`, specifically `RoomReadOnlyPresentation._build_audio()` and room-presentation state needed to survive child rebuilds.

Permitted focused presentation-only extraction:

- a reusable Audio DSP meter widget/component owned by the room presentation path;
- `gui/theme.py` or existing theme tokens for semantic styling.

Optional secondary reuse:

- `gui/screens/audio_dsp_screen.py` MAY use the same reusable presentation widget, but standalone rendering is not required for MIH-10 acceptance and SHALL NOT become room authority.

Not expected without renewed architecture review:

- DMP protocol helpers;
- DMP/room workers;
- `dmp_one_shot` / `dmp_room_live` bindings;
- `DMPPollingController`;
- handlers;
- credentials;
- dispatch registry;
- room interaction lifecycle.

## Validation strategy

### Focused automated coverage

Tests SHALL prove through the room-mode surface at least:

- `RoomDiagnosticTreeWidget` expands an Audio DSP exact row into the new meter presentation rather than relying on standalone `AudioDSPScreen`;
- six current DMP Inputs and four Outputs render in deterministic accepted order;
- deterministic 20-segment fill uses `floor(clamp(normalized,0,1) * 20 + 0.5)`;
- physical segment semantic zone uses the fixed midpoint rule;
- exact numeric `dbfs` remains visible;
- unavailable channels show `— dBFS` and preserve accepted safe structured `outcome`/`error_code` detail;
- selected channel has a non-color cue;
- accepted snapshots for the same exact context/record preserve selection while the same `section` + `oid` remains present;
- context supersession, record removal, or channel disappearance clears selection;
- no implicit first-channel selection occurs;
- disabled `-`, value, `+`, `Mute` local placeholders emit no mutation/interaction intent;
- Biamp `signal_sources` remain non-fabricated scalar/source presentation;
- room DMP automatic/live lifecycle remains `dmp_one_shot` / `dmp_room_live` and standalone `DMPPollingController` is not promoted;
- stale room callbacks cannot update a superseded exact row or restore selection;
- theme toggle, channel selection, and layout events start no device I/O;
- row expand/collapse creates no duplicate live/session ownership.

Standalone `AudioDSPScreen` tests MAY be added only if implementation reuses the presentation widget there; they do not replace room-mode acceptance tests.

### Manual visual acceptance

Using controlled fixture data, inspect the **expanded Audio DSP row inside the room accordion** for:

- `1440 x 900` dark theme;
- `1440 x 900` light theme with identical data;

The user accepted the `1440 x 900` dark and light reviews. The `1180 x 720` manual visual checkpoint was explicitly cancelled; responsive runtime behavior remains automated, but this design does not claim user acceptance for that viewport.

Verify room integration, dashboard hierarchy, compact ordinal labels, segment readability, numeric dBFS, structured unavailable outcome detail, selected cue persistence during same-context accepted updates, local disabled controls, Quick actions truthfulness, and geometry-stable theme behavior. Screenshots remain local/untracked unless separately approved.

### Full workflow

Implementation requires focused tests, full offline tests, repository-local strict validation, `git diff --check`, and `git diff --cached --check`. Independent validation must use a clean detached worktree from the current published feature HEAD and repeat both Git checks. Because archive will add requirements to an existing root spec, independent validation SHALL perform the disposable archive-applicability check before `READY FOR ARCHIVE`.
