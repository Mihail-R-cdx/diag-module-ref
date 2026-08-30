# Tasks: Modern Audio DSP expanded presentation

## 1. Architecture and current-state confirmation

- [ ] 1.1 Read current `RULES.md`, current merged root OpenSpec, and confirm the change is based on current `master` after archived `room-diagnostic-modern-ui`.
- [ ] 1.2 Reconfirm current Audio DSP source/tests before implementation: `AudioDSPScreen`, DMP canonical `meter_sections`, Biamp `signal_sources`, `DMPPollingController`, DMP worker cleanup/stale-result boundaries, and current room-mode exact-row integration.
- [ ] 1.3 Run `..\..\..\openspec.cmd validate audio-diagnostic-modern-ui --strict` (or the equivalent repository-root `./openspec.cmd` invocation for the local shell) and complete architecture review before production implementation.

## 2. Audio DSP presentation implementation

- [ ] 2.1 Refactor the current expanded Audio DSP presentation so accepted numeric `meter_sections` render as separate Inputs/source and Outputs/destination cards without changing current payload authority or channel order.
- [ ] 2.2 Implement the vertical 20-segment dBFS meter component/presentation using accepted `normalized` only for fill and accepted `dbfs` as the visible numeric truth.
- [ ] 2.3 Apply the approved semantic meter zones (`green` below `-18 dBFS`, `yellow` from `-18` to below `-6 dBFS`, `orange` from `-6` through `+12 dBFS`) through theme-aware presentation tokens; keep numeric dBFS visible in both themes.
- [ ] 2.4 Render unavailable meter evidence as a neutral/empty segmented track with `— dBFS`; never reuse an old value as current or fabricate `0 dBFS`.
- [ ] 2.5 Implement deterministic channel labels/order and local selected-channel state keyed by current exact row plus `section`/`oid`, with an explicit non-color selection cue.
- [ ] 2.6 Add the future selected-channel control strip with `-`, current gain/value, `+`, and `Mute` in the approved layout. On the current change base all of these are disabled/non-actionable, current gain is `—`/`Нет данных`, and no signal/application intent/network mutation is emitted.
- [ ] 2.7 Preserve current Biamp `signal_sources` as truthful source/value evidence; family-consistent visual cleanup is allowed, but do not fabricate dBFS meters, Inputs/Outputs, gain, or mute state from unsupported evidence.
- [ ] 2.8 Keep the Audio DSP content usable at foundation baseline `1440 x 900` and minimum `1180 x 720`, with controlled reflow/scrolling and consistent dark/light geometry.

## 3. Lifecycle and authority preservation

- [ ] 3.1 Prove that channel select/deselect, meter repaint/animation, hover/focus, resize/reflow, and theme toggle perform no device I/O and do not start workers, timers, handlers, sessions, credential attempts, retries, or mutations.
- [ ] 3.2 Prove that the redesign does not introduce a second DMP live/polling lifecycle; existing application/composition generation and callback currentness remain the only acceptance authority.
- [ ] 3.3 Prove stale/superseded DMP snapshots cannot update a replacement Audio DSP row/context and cannot restore a stale selected-channel state.
- [ ] 3.4 Prove row expand/collapse does not leak or duplicate DMP polling/session ownership and does not alter common accordion acquisition order.
- [ ] 3.5 Prove theme changes do not restart the Audio DSP live lifecycle, change exact-row authority, or reorder channels.
- [ ] 3.6 If implementation appears to require changes to DMP protocol helpers, handlers, workers, `DMPPollingController`, credentials, dispatch, room lifecycle, or mutation capability, stop and return for architecture review before making those changes.

## 4. Regression coverage

- [ ] 4.1 Add focused GUI tests for current DMP six-Input/four-Output grouping, deterministic order, meter geometry/segment count, numeric dBFS display, and normalized fill.
- [ ] 4.2 Add focused GUI tests for unavailable channels and theme-aware semantic zones without color-only value meaning.
- [ ] 4.3 Add focused tests for selected-channel non-color cue, stable same-context selection, selection invalidation on context replacement, and no implicit first-channel authority requirement.
- [ ] 4.4 Add focused tests proving `-`, gain/value, `+`, and `Mute` placeholders are disabled and emit no action/mutation intent.
- [ ] 4.5 Add/retain regression coverage for Biamp non-meter `signal_sources` so arbitrary scalar/boolean evidence is not turned into dBFS.
- [ ] 4.6 Re-run existing DMP protocol/worker/controller lifecycle tests, current device-screen tests, room live production lifecycle tests, room modern foundation tests, and theme regressions relevant to the changed presentation.
- [ ] 4.7 Run the full offline test suite; do not copy historical test counts.

## 5. Manual visual acceptance

- [ ] 5.1 With controlled fixture data, inspect the expanded DMP Audio DSP row at `1440 x 900` in dark theme and verify Inputs/Outputs proportions, 20-segment vertical meters, labels, numeric dBFS, selected cue, and disabled controls.
- [ ] 5.2 Repeat the same fixture/data at `1440 x 900` in light theme and verify geometry/order/data are unchanged while semantic styling remains legible.
- [ ] 5.3 Inspect at `1180 x 720` and verify all Audio DSP meter/control content remains reachable through approved reflow/scrolling.
- [ ] 5.4 Keep screenshots local/untracked unless a separately approved workflow explicitly requires repository evidence.

## 6. Implementation validation and publication

- [ ] 6.1 Run focused tests for all changed Audio DSP presentation behavior.
- [ ] 6.2 Run the full offline test suite.
- [ ] 6.3 Run only repository-local OpenSpec validation: `./openspec.cmd validate audio-diagnostic-modern-ui --strict` and `./openspec.cmd validate --all --strict` (PowerShell: `.\openspec.cmd ...`).
- [ ] 6.4 Run `git diff --check` and review the full implementation diff against the approved architecture.
- [ ] 6.5 Create a focused implementation commit and push the feature branch only after implementation checks pass; do not archive or merge.

## 7. Independent validation

- [ ] 7.1 Validate the current published remote feature HEAD from a separate clean detached worktree; prove local/remote SHA equality and clean state before/after.
- [ ] 7.2 Independently repeat focused tests, full offline tests, strict change/all OpenSpec validation, and Git diff checks without copying implementation-session counts.
- [ ] 7.3 Review implementation against this approved Audio DSP presentation contract, including exact-row lifecycle, disabled mutation placeholders, Biamp honesty, responsive themes, and stale-result boundaries.
- [ ] 7.4 Perform a disposable archive-applicability check because archive will update an existing root spec; do not perform the real archive in the validation worktree.
- [ ] 7.5 Do not fix findings in the independent validation session. Any CRITICAL/HIGH/MEDIUM finding returns the change to implementation/review.

## 8. Archive and post-archive gates

- [ ] 8.1 Archive only after independent `APPROVE` / `READY FOR ARCHIVE` using `./openspec.cmd archive audio-diagnostic-modern-ui --yes` on the designated feature branch.
- [ ] 8.2 Review archive/root-spec diff, run `./openspec.cmd validate --all --strict`, full offline tests, and `git diff --check` after archive.
- [ ] 8.3 Create and push a dedicated archive commit only after post-archive checks pass.
- [ ] 8.4 Before any merge, re-check current remote archive HEAD and current `master`; merge only with explicit user authorization.
