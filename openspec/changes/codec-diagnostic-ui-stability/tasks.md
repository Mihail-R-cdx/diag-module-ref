# Tasks: codec-diagnostic-ui-stability

## 1. Architecture and baseline verification

- [ ] 1.1 Before implementation, read current `RULES.md` and verify current `master`, feature remote HEAD, PR state/Draft/base/head, merge state, and any commits added after change approval.
- [ ] 1.2 Re-read this change plus the current root specs for `diagnostic-ui-presentation`, `device-diagnostics-and-control`, `codec-call-log-usage-statistics`, `room-device-interaction-lifecycle`, and `cloudlink-live-microphone-metering`.
- [ ] 1.3 Confirm current source still uses one unified exact-model registration and one serialized room interaction lane; do not implement against stale report/Graphify assumptions.
- [ ] 1.4 Enumerate current accepted speaker-volume source semantics for all five codec models and encode any model-specific source-to-percent mapping outside presentation code with focused tests.

## 2. Call-history parity

- [ ] 2.1 Extend normalized call-history records with typed `INCOMING | OUTGOING | UNKNOWN` direction without parsing GUI strings.
- [ ] 2.2 Ensure all five exact model adapters preserve machine-readable completed/active state and non-negative duration when source evidence exists; missing duration stays unavailable/partial rather than becoming zero.
- [ ] 2.3 Make the modern room three-row preview, detailed journal, direction cue, duration, and usage statistics consume the same accepted normalized snapshot.
- [ ] 2.4 Route initial room call-history preview only through the existing exact-row serialized `AUXILIARY_READ` authority; do not create a presentation-owned reader or second cache.
- [ ] 2.5 Add focused parity tests for TE20, TE40, Bar 310, Box 310, and Polycom RPG 310, including incoming/outgoing/unknown, active call, completed duration, missing duration, empty history, source limitation, and stale snapshot rejection where applicable.
- [ ] 2.6 Add an explicit end-to-end `CloudLink Box 310` regression proving exact Box identity -> approved retrieval/session path -> normalization -> room preview/detailed journal -> usage statistics.

## 3. Codec dashboard presentation cleanup

- [ ] 3.1 Remove only the modern codec-dashboard `Платформа` row; do not remove `platform` from parser/handler/internal diagnostic data solely for this UI change.
- [ ] 3.2 Remove the modern codec-dashboard `Отладка` affordance while preserving approved Debug presentation for non-codec device families.
- [ ] 3.3 Remove any speaker-volume meter/scale/bar from the modern codec Audio card.
- [ ] 3.4 Preserve the required five-card order/layout and update focused structural/visual tests for the new state/audio rows.

## 4. Speaker volume percentage and mutation stability

- [ ] 4.1 Add accepted display-only `speaker_volume_percent: Optional[int]` (`0..100`) to the application/presentation projection.
- [ ] 4.2 Produce percentage from exact-model accepted volume semantics outside Qt presentation; do not infer a wire range or reverse-convert GUI percentage into a mutation target.
- [ ] 4.3 Render `<N>%` between `−` and `+` when current accepted percentage exists; render `Нет данных` when it does not.
- [ ] 4.4 Keep canonical/raw speaker volume and existing model-specific target conversion as mutation/reconciliation authority.
- [ ] 4.5 Remove any independent presentation-owned pending flag/timer that can make speaker controls hang after the authoritative room lifecycle is terminal.
- [ ] 4.6 Test supported and unsupported clicks, accepted reconciliation success, ambiguous send/result, reconciliation failure/timeout, stale completion, exact-row switching, and no blind resend.

## 5. Microphone meter semantics

- [ ] 5.1 Resolve modern room microphone-meter capability from unified registration/approved live binding, not model strings in the GUI.
- [ ] 5.2 Keep Bar 310 and Box 310 `SUPPORTED`; distinguish accepted numeric zero from missing current sample (`Нет данных`).
- [ ] 5.3 Render TE20, TE40, and Polycom RPG 310 as `Не поддерживается` for the modern room live microphone meter and prove rendering performs zero meter network I/O.
- [ ] 5.4 Preserve current CloudLink Bar/Box meter endpoints, session ownership, one-second serialization, stale rejection, and ordinary-status isolation.
- [ ] 5.5 Add exact-model focused tests for all five baseline codecs covering `SUPPORTED with data`, `SUPPORTED with zero`, `SUPPORTED with no data`, and `UNSUPPORTED` as applicable.

## 6. Codec Local Refresh stability

- [ ] 6.1 Keep `Обновить статус` as a pure alias of the existing exact-row `LOCAL_REFRESH` intent/lifecycle.
- [ ] 6.2 Remove/avoid any second codec-specific refresh owner or direct presentation-to-handler path.
- [ ] 6.3 Ensure accepted success updates the exact-row cache with no error modal.
- [ ] 6.4 Ensure accepted terminal failure follows the existing row failure contract and produces at most one non-secret user-facing error for that current operation.
- [ ] 6.5 Ensure stale/superseded/cancelled Local Refresh completion mutates no current cache and produces no current-row error modal.
- [ ] 6.6 Add regression tests for success, usable-success-with-warning where applicable, terminal typed failure, stale completion, cancellation/supersession, and GUI-thread non-blocking behavior.

## 7. Focused and full implementation validation

- [ ] 7.1 Run focused tests covering every changed source/test module and all five baseline codecs.
- [ ] 7.2 Run the full offline project test suite from the implementation branch and record fresh counts/results.
- [ ] 7.3 Run `.\openspec.cmd validate codec-diagnostic-ui-stability --strict`.
- [ ] 7.4 Run `.\openspec.cmd validate --all --strict`.
- [ ] 7.5 Run `git diff --check` and verify the implementation diff contains no Graphify output or unrelated changes.
- [ ] 7.6 Commit only the approved implementation/regression scope and push the focused feature commit when the implementation session has explicit commit/push authorization.

## 8. Independent validation

- [ ] 8.1 Validate the exact current remote feature HEAD in a separate clean detached worktree; verify local HEAD equals `origin/<feature-branch>` before tests.
- [ ] 8.2 Repeat focused tests with fresh results; do not copy implementation-session counts.
- [ ] 8.3 Repeat the full offline test suite.
- [ ] 8.4 Repeat strict change validation and `validate --all --strict` using repository-local commands only.
- [ ] 8.5 Run `git diff --check`, verify the detached worktree remains clean, and review implementation against every approved architecture requirement.
- [ ] 8.6 Because this change contains `MODIFIED Requirements`, perform the required disposable archive-applicability check against the then-current root specs outside the primary feature branch/worktree.
- [ ] 8.7 Issue independent `APPROVE`, `APPROVE WITH NON-BLOCKING NOTES`, or `CHANGES REQUIRED` according to current `RULES.md`; do not self-fix findings in the validation session.

## 9. Archive and post-archive checks

- [ ] 9.1 Archive only after independent approval and explicit archive authorization using `.\openspec.cmd archive codec-diagnostic-ui-stability --yes`.
- [ ] 9.2 Review the archive/root-spec diff, including all `MODIFIED Requirements`, for applicability to the then-current root specs.
- [ ] 9.3 Run `.\openspec.cmd validate --all --strict`, the full offline test suite, and `git diff --check` after archive.
- [ ] 9.4 Create/push a dedicated archive commit only with explicit authorization and verify remote archive HEAD after push.
- [ ] 9.5 Before merge, re-check current `master`, PR state/Draft/base/head, remote feature/archive HEAD, merge state/mergeability, and new commits. Do not merge without explicit user authorization.
