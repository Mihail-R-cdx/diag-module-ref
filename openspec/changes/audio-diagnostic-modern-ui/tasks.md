# Tasks: Modern Audio DSP expanded presentation

## 1. Architecture and current-state confirmation

- [ ] 1.1 Read current `RULES.md`, current merged root OpenSpec, and confirm the change is based on current `master` after archived `room-diagnostic-modern-ui`.
- [ ] 1.2 Reconfirm the real room Audio DSP source/tests before implementation: `RoomDiagnosticTreeWidget`, `RoomReadOnlyPresentation._build_audio()`, `normalize_audio_dsp_presentation`, DMP canonical `meter_sections`, Biamp `signal_sources`, unified registry `dmp_one_shot` / `dmp_room_live`, and existing stale-result/cleanup boundaries. Treat standalone `AudioDSPScreen` / `DMPPollingController` only as a separate secondary surface/lifecycle.
- [ ] 1.3 From the repository root run only `./openspec.cmd validate audio-diagnostic-modern-ui --strict` (PowerShell: `.\openspec.cmd validate audio-diagnostic-modern-ui --strict`) and complete architecture review before production implementation.

## 2. Room Audio DSP presentation implementation

- [ ] 2.1 Refactor the Audio DSP exact-row content rendered from `RoomReadOnlyPresentation._build_audio()` (or a focused presentation-only widget embedded from that path) so accepted numeric `meter_sections` render as separate Inputs/source and Outputs/destination cards. Do not substitute or embed standalone `AudioDSPScreen` as room authority.
- [ ] 2.2 Implement the vertical 20-segment dBFS meter using accepted `normalized` only for fill and accepted `dbfs` as visible numeric truth. Use exactly `filled_segments = floor(clamp(normalized, 0, 1) * 20 + 0.5)`.
- [ ] 2.3 Classify each physical filled segment by fixed midpoint `-60 + (index + 0.5) * 3.6 dBFS`: green below `-18`, yellow from `-18` to below `-6`, orange at/above `-6`; use theme-aware tokens and keep numeric dBFS visible.
- [ ] 2.4 Render unavailable numeric evidence as a neutral/empty segmented track with `— dBFS` while preserving accepted safe structured `outcome` and accepted safe `error_code` when present in secondary presentation. Do not expose raw payload/debug text, reuse an old value, or fabricate `0 dBFS`.
- [ ] 2.5 Implement deterministic channel labels/order and local selected-channel state keyed by current exact room context + `record_id` + `section` + `oid`, with an explicit non-color selection cue.
- [ ] 2.6 Preserve valid selected-channel state across accepted same-context snapshot rebuilds while the same `section` + `oid` remains present. Clear it on context supersession/clear, record replacement/removal, or selected-channel disappearance. Do not keep this state solely in a disposable rebuilt child if that causes snapshot-to-snapshot reset.
- [ ] 2.7 Add the future selected-channel control strip with `-`, current gain/value, `+`, and `Mute` in the approved room layout. On the current base all are disabled/non-actionable, current gain is `—`/`Нет данных`, and no application/room interaction intent or network mutation is emitted.
- [ ] 2.8 Preserve current Biamp `signal_sources` as truthful source/value evidence; family-consistent visual cleanup is allowed, but do not fabricate dBFS meters, Inputs/Outputs, gain, or mute state from unsupported evidence.
- [ ] 2.9 Keep room Audio DSP content usable at foundation baseline `1440 x 900` and minimum `1180 x 720`, with controlled reflow/scrolling and consistent dark/light geometry.
- [ ] 2.10 If a focused reusable Audio DSP presentation widget is extracted, integrate it into the room exact-row path first. Optional standalone `AudioDSPScreen` reuse is secondary and must not change room authority or acceptance.

## 3. Lifecycle and authority preservation

- [ ] 3.1 Prove channel select/deselect, meter repaint/animation, hover/focus, resize/reflow, theme toggle, and pure presentation rebuilds perform no device I/O and do not start workers, timers, handlers, sessions, credential attempts, retries, or mutations.
- [ ] 3.2 Prove room DMP automatic acquisition remains `dmp_one_shot`, room live interaction remains `dmp_room_live`, and standalone `DMPPollingController` is not promoted into room mode or treated as room callback authority.
- [ ] 3.3 Prove stale/superseded room DMP callbacks cannot update a replacement Audio DSP exact row/context and cannot restore stale selected-channel state.
- [ ] 3.4 Prove row expand/collapse does not create, leak, or duplicate room DMP live/session ownership and does not alter common accordion acquisition order.
- [ ] 3.5 Prove theme changes do not restart room Audio DSP acquisition/live lifecycle, change exact-row authority, reorder channels, or clear a still-valid selection.
- [ ] 3.6 If implementation appears to require changes to `dmp_one_shot`, `dmp_room_live`, dispatch registry, DMP protocol helpers, handlers, workers, `DMPPollingController`, credentials, room lifecycle, or mutation capability, stop and return for architecture review before making those changes.

## 4. Regression coverage

- [ ] 4.1 Add focused GUI tests through `RoomDiagnosticTreeWidget` proving an expanded Audio DSP exact row uses the modern room presentation rather than standalone `AudioDSPScreen`.
- [ ] 4.2 Add focused room GUI tests for current DMP six-Input/four-Output grouping, deterministic accepted order, meter geometry/20-segment count, numeric dBFS display, and exact round-half-up normalized fill.
- [ ] 4.3 Add focused tests for fixed midpoint semantic-zone assignment, including values/segments around the `-18 dBFS` and `-6 dBFS` boundaries, without color-only value meaning.
- [ ] 4.4 Add focused tests for unavailable channels showing `— dBFS` while preserving accepted structured `outcome`/safe `error_code`, with no stale numeric reuse or fabricated `0 dBFS`.
- [ ] 4.5 Add focused tests for selected-channel non-color cue, same-context persistence across room presentation rebuilds, clearing on context/record/channel invalidation, and no implicit first-channel selection.
- [ ] 4.6 Add focused tests proving `-`, gain/value, `+`, and `Mute` placeholders are disabled and emit no action/room-interaction/mutation intent.
- [ ] 4.7 Add/retain regression coverage for Biamp non-meter `signal_sources` so arbitrary scalar/boolean evidence is not turned into dBFS.
- [ ] 4.8 Re-run existing DMP protocol/worker/controller tests as regression protection, but also run room one-shot/live production lifecycle tests, `RoomDiagnosticTreeWidget`/foundation tests, and theme regressions relevant to the changed room presentation.
- [ ] 4.9 If standalone `AudioDSPScreen` reuses the focused widget, add only the secondary reuse regressions needed for that surface; standalone tests do not replace room-mode acceptance tests.
- [ ] 4.10 Run the full offline test suite; do not copy historical test counts.

## 5. Manual visual acceptance

- [ ] 5.1 With controlled fixture data, inspect the expanded DMP Audio DSP **room accordion row** at `1440 x 900` in dark theme and verify room integration, Inputs/Outputs proportions, 20-segment vertical meters, labels, numeric dBFS, structured unavailable outcome detail, selected cue, and disabled controls.
- [ ] 5.2 Repeat the same room fixture/data at `1440 x 900` in light theme and verify geometry/order/data/selection are unchanged while semantic styling remains legible.
- [ ] 5.3 During same-context accepted meter updates, verify the selected `section` + `oid` remains selected; then supersede/replace the exact room context and verify selection clears.
- [ ] 5.4 Inspect at `1180 x 720` and verify all room Audio DSP meter/outcome/control content remains reachable through approved reflow/scrolling.
- [ ] 5.5 Keep screenshots local/untracked unless a separately approved workflow explicitly requires repository evidence.

## 6. Implementation validation and publication

- [ ] 6.1 Run focused tests for all changed room Audio DSP presentation behavior.
- [ ] 6.2 Run the full offline test suite.
- [ ] 6.3 Run only repository-local OpenSpec validation: `./openspec.cmd validate audio-diagnostic-modern-ui --strict` and `./openspec.cmd validate --all --strict` (PowerShell: `.\openspec.cmd ...`).
- [ ] 6.4 Run both `git diff --check` and `git diff --cached --check`, then review the full implementation diff against the approved architecture.
- [ ] 6.5 Create a focused implementation commit and push the feature branch only after implementation checks pass; do not archive or merge.

## 7. Independent validation

- [ ] 7.1 Validate the current published remote feature HEAD from a separate clean detached worktree; prove local/remote SHA equality and clean state before/after.
- [ ] 7.2 Independently repeat focused tests, full offline tests, strict change/all OpenSpec validation, `git diff --check`, and `git diff --cached --check` without copying implementation-session counts.
- [ ] 7.3 Review implementation against this approved room Audio DSP presentation contract, including actual `RoomDiagnosticTreeWidget` integration, `dmp_one_shot` / `dmp_room_live` lifecycle separation, disabled mutation placeholders, structured unavailable outcome preservation, selected-channel persistence/clearing, Biamp honesty, responsive themes, and stale-result boundaries.
- [ ] 7.4 Perform a disposable archive-applicability check because archive will update an existing root spec; do not perform the real archive in the validation worktree.
- [ ] 7.5 Do not fix findings in the independent validation session. Any CRITICAL/HIGH/MEDIUM finding returns the change to implementation/review.

## 8. Archive and post-archive gates

- [ ] 8.1 Archive only after a permitting independent verdict using `./openspec.cmd archive audio-diagnostic-modern-ui --yes` on the designated feature branch.
- [ ] 8.2 Review archive/root-spec diff, run `./openspec.cmd validate --all --strict`, full offline tests, `git diff --check`, and `git diff --cached --check` after archive.
- [ ] 8.3 Create and push a dedicated archive commit only after post-archive checks pass.
- [ ] 8.4 Before any merge, re-check current remote archive HEAD and current `master`; merge only with explicit user authorization.
