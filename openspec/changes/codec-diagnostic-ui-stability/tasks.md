# Tasks: codec-diagnostic-ui-stability

## 1. Architecture and baseline verification

- [ ] 1.1 Before implementation, read current `RULES.md` and verify current `master`, feature remote HEAD, PR state/Draft/base/head, merge state, mergeability, and commits added after architectural approval.
- [x] 1.2 Re-read this change plus current root specs for `diagnostic-ui-presentation`, `device-diagnostics-and-control`, `codec-call-log-usage-statistics`, `room-device-interaction-lifecycle`, and `cloudlink-live-microphone-metering`.
- [x] 1.3 Confirm current source still uses one unified exact-model registration and one serialized room interaction lane; do not implement from stale reports or Graphify.
- [x] 1.4 Verify the current registry still declares speaker ranges `TE20/TE40 0..21`, `Bar310/Box310 0..15`, and `Polycom RPG310 0..100`. If current remote source differs, stop and return for architectural review rather than silently changing the approved percentage semantics.

## 2. Call-history parity and freshness

- [x] 2.1 Extend normalized call-history records with typed `INCOMING | OUTGOING | UNKNOWN` direction without parsing GUI strings.
- [x] 2.2 Ensure all five exact model adapters preserve machine-readable completed/active state and non-negative duration when source evidence exists; missing duration stays unavailable/partial rather than becoming zero.
- [x] 2.3 Bind visible semantic cues exactly as approved: `INCOMING -> Входящий`, `OUTGOING -> Исходящий`, `UNKNOWN -> neutral/Направление неизвестно`; add presentation-level tests proving incoming/outgoing cue roles cannot be swapped.
- [x] 2.4 Keep the modern room three-row preview on the accepted automatic-preview acquisition snapshot and common normalized record semantics; do not create a second parser, chronology sort, vendor-specific preview cache, or statistics dataset.
- [x] 2.5 For every eligible codec expansion epoch, admit exactly one automatic call-history preview intent through the existing serialized `AUXILIARY_READ` authority. Busy/retiring lane state may delay network eligibility but SHALL NOT silently drop the mandatory admitted intent; duplicate Qt expansion notifications/re-render/resize/theme changes SHALL NOT admit another intent.
- [x] 2.6 Add regressions for exactly-one automatic admission covering post-terminal expansion, pre-terminal expansion followed by terminal room cycle, busy/retiring lane, duplicate Qt expansion notifications, row switch/collapse, stale/cancelled gates, and zero concurrent preview I/O.
- [x] 2.7 Preserve the root freshness contract: every explicit `Развернуть` / detailed call-log opening starts a fresh serialized exact-row `AUXILIARY_READ` even when a current automatic-preview snapshot exists. Expanding/collapsing sections inside one already-open detailed load uses that load's accepted data without another request.
- [x] 2.8 Add focused parity tests for TE20, TE40, Bar 310, Box 310, and Polycom RPG 310, including incoming/outgoing/unknown, active call, completed duration, missing duration, empty history, source limitation, hard product cap where applicable, and stale snapshot rejection.
- [x] 2.9 Add an explicit end-to-end `CloudLink Box 310` regression proving exact Box identity -> approved retrieval/session path -> normalization -> automatic room preview -> fresh explicit detailed journal acquisition -> usage statistics.

## 3. Codec dashboard presentation cleanup

- [x] 3.1 Remove only the modern codec-dashboard `Платформа` row; do not remove `platform` from parser/handler/internal diagnostic data solely for this UI change.
- [x] 3.2 Remove the modern codec-dashboard `Отладка` affordance while preserving approved Debug presentation for other device families and internal accumulated logs.
- [x] 3.3 Remove any speaker-volume meter/scale/bar from the modern codec Audio card.
- [x] 3.4 Preserve required five-card order/layout and update focused structural/visual tests for the new state/audio rows.

## 4. Speaker-volume percentage and mutation stability

- [x] 4.1 Add accepted display-only `speaker_volume_percent: Optional[int]` (`0..100`) to application/presentation projection.
- [x] 4.2 Implement the approved application-owned conversion using exact-model registry bounds only: `scaled = 100 * (V - MIN) / (MAX - MIN)` and `percent = floor(scaled + 0.5)` when `MAX > MIN` and `MIN <= V <= MAX`; do not clamp out-of-range values.
- [x] 4.3 Add normative mapping tests for each distinct range: TE20/TE40 `0->0`, `10->48`, `21->100`; Bar/Box `0->0`, `7->47`, `15->100`; Polycom `0->0`, `42->42`, `100->100`; also cover malformed/out-of-range/stale/missing evidence -> absent percentage.
- [x] 4.4 Render `<N>%` between `−` and `+` only when current accepted percentage exists; render `Нет данных` otherwise.
- [ ] 4.5 Keep canonical/raw speaker volume and existing model-specific mutation target conversion as mutation/reconciliation authority; never reverse-convert GUI percentage into a mutation target.
- [ ] 4.6 Remove/avoid any independent presentation-owned pending flag/timer that can outlive or disagree with authoritative `MUTATION -> RECONCILIATION` lifecycle.
- [ ] 4.7 Test supported and unsupported clicks, accepted reconciliation success, ambiguous send/result, reconciliation failure/timeout, stale completion, exact-row switching, and no blind resend/optimistic accepted percentage.

## 5. Microphone meter semantics

- [ ] 5.1 Resolve modern room microphone-meter capability from unified registration/approved live binding, not model strings in Qt presentation.
- [ ] 5.2 Keep Bar 310 and Box 310 `SUPPORTED`; distinguish accepted numeric zero from missing current sample (`Нет данных`).
- [ ] 5.3 Render TE20, TE40, and Polycom RPG 310 as `Не поддерживается` for the modern room live microphone meter and prove rendering performs zero meter network I/O.
- [ ] 5.4 Preserve current CloudLink Bar/Box meter endpoints, session ownership, one-second serialization, stale rejection, and ordinary-status isolation.
- [ ] 5.5 Add exact-model focused tests covering `SUPPORTED with data`, `SUPPORTED with zero`, `SUPPORTED with no data`, and `UNSUPPORTED` as applicable.

## 6. Codec Local Refresh investigation and correction

- [ ] 6.1 Before changing implementation, reproduce MIH-23 separately on `Huawei TE20`, `Huawei TE40`, `CloudLink Bar 310`, `CloudLink Box 310`, and `Polycom RPG 310` using current remote feature source/test baseline.
- [ ] 6.2 Record enough failing-boundary evidence to classify the defect as common lifecycle/composition vs model-specific adapter/typed-failure behavior. Do not treat duplicate callbacks, presentation code, or one model path as the root cause until this evidence exists.
- [ ] 6.3 Keep `Обновить статус` as a pure alias of the existing exact-row `LOCAL_REFRESH` intent/lifecycle and correct only the proven root-cause boundary.
- [ ] 6.4 Do not introduce a second codec-specific refresh owner, direct presentation-to-handler path, string heuristic, or duplicate current-operation error owner.
- [ ] 6.5 Ensure accepted success updates exact-row cache with no error modal; accepted terminal failure follows existing row failure contract with at most one non-secret current-operation error presentation.
- [ ] 6.6 Ensure stale/superseded/cancelled completion mutates no current cache and produces no current-row error modal; preserve stale-before-handler/I/O rejection where separable.
- [ ] 6.7 Add model-specific and common-lifecycle regression coverage according to the reproduced root cause, including success, usable-success-with-warning where applicable, terminal typed failure, stale completion, cancellation/supersession, and GUI-thread non-blocking behavior.

## 7. Focused and full implementation validation

- [x] 7.1 Run focused tests covering every changed source/test module and all five baseline codecs.
- [x] 7.2 Run the full offline project test suite from the implementation branch and record fresh counts/results.
- [x] 7.3 Run `.\openspec.cmd validate codec-diagnostic-ui-stability --strict`.
- [x] 7.4 Run `.\openspec.cmd validate --all --strict`.
- [x] 7.5 Run `git diff --check` and `git diff --cached --check`; verify diff contains no Graphify output or unrelated changes.
- [ ] 7.6 Commit only approved implementation/regression scope and push the focused feature commit when explicitly authorized.

## 8. Independent validation

- [ ] 8.1 Validate the exact current remote feature HEAD in a separate clean detached worktree; verify local HEAD equals `origin/<feature-branch>` before tests.
- [ ] 8.2 Repeat focused tests with fresh results; do not copy implementation-session counts.
- [ ] 8.3 Repeat the full offline test suite.
- [ ] 8.4 Repeat strict change validation and `validate --all --strict` using repository-local commands only.
- [ ] 8.5 Run `git diff --check` and `git diff --cached --check`, verify the detached worktree remains clean, and review implementation against every approved requirement.
- [ ] 8.6 Because this change contains `MODIFIED Requirements`, perform the required disposable archive-applicability check against then-current root specs outside the primary feature branch/worktree.
- [ ] 8.7 Issue independent `APPROVE`, `APPROVE WITH NON-BLOCKING NOTES`, or `CHANGES REQUIRED` according to current `RULES.md`; do not self-fix findings in the validation session.

## 9. Archive and post-archive checks

- [ ] 9.1 Archive only after independent approval and explicit archive authorization using `.\openspec.cmd archive codec-diagnostic-ui-stability --yes`.
- [ ] 9.2 Review archive/root-spec diff, including every `MODIFIED Requirements`, for applicability to then-current root specs.
- [ ] 9.3 Run `.\openspec.cmd validate --all --strict`, the full offline test suite, `git diff --check`, and `git diff --cached --check` after archive.
- [ ] 9.4 Create/push a dedicated archive commit only with explicit authorization and verify remote archive HEAD after push.
- [ ] 9.5 Before merge, re-check current `master`, PR state/Draft/base/head, remote feature/archive HEAD, merge state/mergeability, and new commits. Do not merge without explicit user authorization.
