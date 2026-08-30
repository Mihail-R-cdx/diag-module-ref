# Change: Modernize expanded Audio DSP diagnostics

## Why

The merged and archived `room-diagnostic-modern-ui` foundation deliberately kept device-family-specific expanded content on the existing room-mode exact-row presentation surface and deferred the Audio DSP redesign to a dedicated follow-up change. Current `master` renders expanded room rows through `RoomDiagnosticTreeWidget` and `RoomReadOnlyPresentation`; Audio DSP room content is currently built by `RoomReadOnlyPresentation._build_audio()` as the `roomAudioMeasurements` presentation.

The standalone `AudioDSPScreen` is a different presentation surface. It may show the same device family and may be a secondary consumer of reusable presentation widgets, but it is not the MIH-10 acceptance target and SHALL NOT be promoted into room mode merely because it represents Audio DSP devices.

Extron DMP 64 Plus accepted room snapshots already expose exact per-channel `dbfs`, `normalized`, availability, structured outcome evidence, and Input/Output grouping. The current room-mode Audio DSP presentation reduces that evidence to a read-only table. The desired room view is a compact vertical-meter presentation that remains a projection of the existing room lifecycle rather than creating another polling/session/control path.

This change isolates that family-specific visual work from Matrix, codec, and PDU redesigns so implementation, regression review, visual acceptance, and archive evidence remain focused.

## What Changes

- Redesign the **expanded Audio DSP exact-row presentation inside `RoomDiagnosticTreeWidget`** for numeric meter-capable payloads around separate Input/source and Output/destination groups with vertical segmented meters.
- Permit extraction of a focused presentation-only Audio DSP widget for reuse, provided room mode remains the normative integration/acceptance target. Reuse by standalone `AudioDSPScreen` is optional secondary reuse only.
- Render the accepted numeric dBFS value near each meter and use semantic green/yellow/orange meter zones without replacing canonical dBFS evidence.
- Define deterministic 20-segment quantization and fixed segment-zone classification so GUI regression tests have one expected result.
- Preserve safe structured unavailable-channel diagnostic evidence (`outcome` and accepted safe `error_code` when present) separately from the numeric `— dBFS` presentation.
- Add local selected-channel presentation with a non-color selection cue. Selection SHALL survive accepted updates for the same current exact room context while the same `section` + `oid` still exists, and SHALL clear on context supersession or channel disappearance.
- Reserve the approved visual positions for gain `-`, current gain value, gain `+`, and `Mute`; on the current change base these controls are disabled presentation placeholders because no approved exact-row Audio DSP gain/mute mutation capability exists.
- Keep current non-meter Audio DSP evidence honest: existing Biamp Tesira Forte CI `signal_sources` values remain represented as safe source/value evidence and are not fabricated into dBFS meters.
- Keep dark/light theme geometry stable; theme changes affect styling only and do not restart Audio DSP acquisition or alter row authority.
- Preserve the existing room application/composition lifecycle. For DMP, room automatic acquisition remains `dmp_one_shot` and room live interaction remains `dmp_room_live`; standalone `DMPPollingController` remains separate and is not room-mode authority.

## Capabilities

### New/changed capability

- `diagnostic-ui-presentation`: adds the final family-specific expanded Audio DSP visual contract that the foundation explicitly deferred.

### Unchanged authorities

This change does not redefine or take ownership of:

- target-search or canonical room/record authority;
- equipment-row expansion semantics;
- diagnostic dispatch/model capability authority;
- room adapter/live-binding ownership (`dmp_one_shot`, `dmp_room_live`);
- standalone `DMPPollingController` ownership;
- credentials, credential fallback, or successful credential memory;
- transport retry/recovery;
- request/generation or stale-operation authority;
- worker/thread ownership or cleanup;
- device protocol parsing;
- any Audio DSP mutation capability.

## Non-Goals

- No Matrix/IN1804, codec, or PDU visual redesign.
- No new DMP or Biamp protocol commands.
- No gain or mute mutation implementation.
- No new polling timer, polling worker, handler/session lane, credential retry lane, or GUI-thread network I/O.
- No conversion of Biamp boolean/arbitrary source values into invented dBFS evidence.
- No promotion or embedding of standalone `AudioDSPScreen` as room capability.
- No change to the common accordion header, one-expanded-row rule, target-search, room/network cards, or application title.
- No persistence of theme or selected Audio channel across application restarts.

## Expected Implementation Surface

The normative implementation target is the current room-mode exact-row surface and SHALL be reconfirmed against current source before coding:

- `gui/room_diagnostic_tree.py`, specifically the Audio DSP projection currently built by `RoomReadOnlyPresentation._build_audio()`;
- an optional focused presentation-only Audio DSP widget/component extracted from that path;
- `gui/theme.py` or existing presentation tokens only where required for dark/light styling;
- focused room-accordion GUI/presentation regression tests.

`gui/screens/audio_dsp_screen.py` MAY reuse the same focused presentation widget after the room target is satisfied, but standalone rendering is secondary and is not MIH-10 acceptance authority.

Changes to `core/dmp64_plus.py`, DMP workers, room adapters/live bindings, `DMPPollingController`, handlers, credential code, dispatch, or room interaction lifecycle are not expected. If implementation discovers a real need to change those authorities, it SHALL stop and return for architecture review rather than silently expanding scope.

## Dependencies

- Base: current `master` after merged/archived `room-diagnostic-modern-ui` foundation.
- Current root `diagnostic-ui-presentation` foundation contract remains authoritative for shell geometry, themes, common accordion semantics, and exact-row room presentation ownership.
- Current dispatch registry remains authoritative for DMP room bindings: `room_adapter_key = dmp_one_shot` and `live_binding_key = dmp_room_live`.
- Existing `request-lifecycle-and-recovery` contracts remain authoritative for background execution, cancellation, stale-result suppression, credential handling, and resource cleanup.

## Validation Direction

Architecture review SHALL verify that room-mode expanded Audio DSP is the actual target and that no standalone surface is promoted into room authority. Implementation validation SHALL include focused tests through `RoomDiagnosticTreeWidget`, DMP/Biamp presentation tests, room-live lifecycle regressions, theme/foundation regressions, full offline tests, repository-local strict OpenSpec validation, `git diff --check`, `git diff --cached --check`, and manual dark/light room screenshots at the foundation baseline/minimum sizes. Independent validation and archive remain later workflow gates and are not satisfied by this proposal.
