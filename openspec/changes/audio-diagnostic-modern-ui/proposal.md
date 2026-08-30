# Change: Modernize expanded Audio DSP diagnostics

## Why

The merged and archived `room-diagnostic-modern-ui` foundation deliberately kept device-family-specific expanded content on the existing room-mode presentation surface and deferred the Audio DSP redesign to a dedicated follow-up change. The current `master` now provides the common target-search, room cards, network card, exact-row accordion, dark/light session themes, and room lifecycle that this Audio DSP presentation can build on without stacking on the old foundation branch.

The current Audio DSP screen is safe but not aligned with the approved visual direction. In particular, Extron DMP 64 Plus meter snapshots already expose exact per-channel `dbfs`, `normalized`, availability, and Input/Output grouping, while the GUI currently renders those channels as horizontal progress bars and does not show the numeric dBFS value beside each meter. The desired Audio DSP view is a compact vertical-meter presentation that remains a projection of the existing application-owned diagnostic lifecycle rather than creating another polling/session/control path.

This change isolates that family-specific visual work from Matrix, codec, and PDU redesigns so implementation, regression review, visual acceptance, and archive evidence remain focused.

## What Changes

- Redesign the expanded room-mode Audio DSP presentation for numeric meter-capable payloads around separate Input/source and Output/destination groups with vertical segmented meters.
- Render the accepted numeric dBFS value near each meter and use semantic green/yellow/orange meter zones without changing, rounding away, or replacing the canonical dBFS evidence.
- Add deterministic meter geometry, spacing, channel-label hierarchy, unavailable-value treatment, and responsive behavior for the foundation baseline/minimum viewport.
- Add local selected-channel presentation with a non-color selection cue.
- Reserve the approved visual positions for gain `-`, current gain value, gain `+`, and `Mute`; on the current change base these controls are disabled presentation placeholders because no approved exact-row Audio DSP gain/mute mutation capability exists.
- Keep current non-meter Audio DSP evidence honest: existing Biamp Tesira Forte CI `signal_sources` values remain represented as their current safe source/value presentation and are not fabricated into dBFS meters.
- Keep dark/light theme geometry stable; theme changes affect styling only and do not restart Audio DSP polling or alter row authority.
- Preserve the existing application/composition-owned DMP polling, credential fallback, request generation, stale-result rejection, worker cleanup, and background-I/O contracts. Channel selection, meter animation/rendering, theme changes, and accordion presentation do not start extra device I/O.

## Capabilities

### New/changed capability

- `diagnostic-ui-presentation`: adds the final family-specific expanded Audio DSP visual contract that the foundation explicitly deferred.

### Unchanged authorities

This change does not redefine or take ownership of:

- target-search or canonical room/record authority;
- equipment-row expansion semantics;
- diagnostic dispatch/model capability authority;
- DMP polling/session acquisition;
- credentials, credential fallback, or successful credential memory;
- transport retry/recovery;
- request generation or stale-operation authority;
- worker/thread ownership or cleanup;
- device protocol parsing;
- any Audio DSP mutation capability.

## Non-Goals

- No Matrix/IN1804, codec, or PDU visual redesign.
- No new DMP or Biamp protocol commands.
- No gain or mute mutation implementation.
- No new polling timer, polling worker, handler/session lane, credential retry lane, or GUI-thread network I/O.
- No conversion of Biamp boolean/arbitrary source values into invented dBFS evidence.
- No change to the common accordion header, one-expanded-row rule, target-search, room/network cards, or application title.
- No persistence of theme or selected Audio channel across application restarts.

## Expected Implementation Surface

The likely implementation surface is intentionally narrow and SHALL be confirmed against current source before coding:

- `gui/screens/audio_dsp_screen.py`
- `gui/theme.py` or existing presentation tokens only where required for dark/light styling
- focused GUI/presentation regression tests

Changes to `core/dmp64_plus.py`, DMP workers/controllers, handlers, credential code, or room lifecycle code are not expected and require explicit architectural justification if implementation discovers a real contract gap.

## Dependencies

- Base: current `master` after merged/archived `room-diagnostic-modern-ui` foundation.
- Current root `diagnostic-ui-presentation` foundation contract remains authoritative for shell geometry, themes, common accordion semantics, and exact-row presentation ownership.
- Existing DMP lifecycle contracts in `request-lifecycle-and-recovery` remain authoritative for background polling, cancellation, stale-result suppression, credential handling, and resource cleanup.

## Validation Direction

Architecture review SHALL verify that the redesign is presentation-only and self-contained. Implementation validation SHALL include focused Audio DSP/DMP tests, theme and room-foundation regressions, full offline tests, repository-local strict OpenSpec validation, `git diff --check`, and manual dark/light screenshots at the foundation baseline/minimum sizes. Independent validation and archive remain later workflow gates and are not satisfied by this proposal.
