# Tasks: room-diagnostic-ui-presentation-stability

## 1. Architecture and baseline verification

- [x] 1.1 Read current `RULES.md` before repository conclusions.
- [x] 1.2 Verify current `master` is `fcf066b9046d78a864e957a927626981a77c2691` and that no later master commit exists at design time.
- [x] 1.3 Verify no existing `agent/room-diagnostic-ui-presentation-stability` branch and no existing PR for this change at design time.
- [x] 1.4 Read MIH-19 and MIH-14 through MIH-18 from Linear and confirm they remain one change scope.
- [x] 1.5 Re-read current root `diagnostic-ui-presentation` and `room-device-interaction-lifecycle` specs; use archived changes only for artifact format/history, not as authority.
- [x] 1.6 Inspect current room presentation, session/controller/composition boundaries, and focused room/Audio GUI tests for render, scroll, network disclosure, Audio popup, expanded row, session identity/generation, and VIP behavior.
- [x] 1.7 Architecture review this change and obtain `APPROVE` before implementation.

## 2. Presentation context state

- [ ] 2.1 Before implementation, re-check current remote `master`, feature branch/PR state if any, and commits added after architecture approval; stop for re-review if ownership/contracts materially changed.
- [ ] 2.2 Introduce a room-presentation state boundary keyed only by current application-produced `RoomDiagnosticSessionIdentity`; do not store handlers/sessions, credentials, controllers/workers, secrets, accepted device data, or network authority in it.
- [ ] 2.3 Capture/restore equipment viewport for same-identity re-render using the approved visual anchor + clamped scrollbar fallback; new identity/clear discards the prior viewport.
- [ ] 2.4 Ensure programmatic scroll/disclosure restoration is signal-safe and emits no room/device interaction intent or I/O.
- [ ] 2.5 Preserve existing Audio selected-channel local state semantics while keeping it independent from popup visibility.

## 3. Network disclosure stability

- [ ] 3.1 Keep current known-switch grouping, deterministic port de-duplication/count, unknown-switch record-bound behavior, and empty-state semantics.
- [ ] 3.2 Make each known-switch summary row a real disclosure parent with current canonical equipment children ordered by `record_id`; do not invent unattached switches or group unknown-switch records.
- [ ] 3.3 Keep network children presentation-only; they must not become routing/target/topology authority or trigger device I/O.
- [ ] 3.4 Persist user expanded/collapsed state per known-switch visual key only for the same `RoomDiagnosticSessionIdentity`; reset on new identity/clear, defaulting newly encountered switch rows to collapsed.
- [ ] 3.5 Add focused tests for expanded and collapsed persistence through same-context rebuild, reset on identity replacement, removed-switch pruning, unknown-switch non-grouping, unchanged summary evidence, and zero interaction/network signals from restoration.

## 4. Audio popup hover/current-row lifecycle

- [ ] 4.1 Lift popup lifetime coordination above disposable Audio channel widgets to one room-owned presentation coordinator (or equivalent single owner) without moving application/device authority into it.
- [ ] 4.2 Represent popup target only with safe room identity + current Audio `record_id` + `section` + `oid`; never use it as `RoomInteractionContext` or mutation authority.
- [ ] 4.3 Keep popup visible across scale -> popup pointer transfer using one presentation-only single-shot hide bridge.
- [ ] 4.4 Switch A -> B immediately when another current scale is entered and fence delayed callbacks by current popup epoch/target so A cannot hide B.
- [ ] 4.5 Remove selected/pinned-channel behavior from popup lifetime; selection remains visual-only and does not keep popup open after both hover surfaces are left.
- [ ] 4.6 Synchronously hide/invalidate on active Audio row collapse, another current expanded row, identity replacement, clear, or exact channel disappearance.
- [ ] 4.7 During same-identity destructive render, retain no old source QWidget authority; re-resolve the exact replacement scale and preserve popup only if current pointer hit-testing still owns replacement scale or room-owned popup.
- [ ] 4.8 Keep `-`, `+`, and `Mute` disabled/non-actionable and prove popup events/timers emit zero mutation/network intents.
- [ ] 4.9 Add regressions for scale->popup, popup->outside, A->B, selected-not-pinned, collapse, row switch, identity switch, channel disappearance, stale timer, same-context valid rebind, and failed rebind close.

## 5. VIP presentation regression

- [ ] 5.1 Restore plainly visible approved VIP badge/icon in `Информация о комнате` from current canonical `session.room_vip is True` only.
- [ ] 5.2 Keep false/null from rendering VIP true; do not introduce local VIP memory/inference or new metadata authority.
- [ ] 5.3 Add/strengthen focused GUI tests for true/false/null visibility and current render replacement.

## 6. Authority and lifecycle regression protection

- [ ] 6.1 Preserve `session.expanded_record_id` / application coordinator as current row authority; do not duplicate it in room presentation state.
- [ ] 6.2 Preserve application-owned credential selection/fallback, handler/session ownership, serialized network lane, typed-failure precedence, stale-result rejection, and no network I/O in the Qt GUI thread.
- [ ] 6.3 Prove scroll/disclosure/popup/VIP presentation changes alone never admit Local Refresh, auxiliary, live, mutation, reconciliation, handler/session, credential, worker, retry, or protocol activity.
- [ ] 6.4 Keep secrets absent from presentation state, logs/errors/tooltips, and test fixtures.

## 7. Focused and full implementation validation

- [ ] 7.1 Run focused room foundation/tree and Audio DSP presentation tests covering every changed source/test module.
- [ ] 7.2 Run relevant room interaction/lifecycle regression tests protecting current exact-row/network ownership.
- [ ] 7.3 Run the full offline project test suite and record fresh results.
- [ ] 7.4 Run `.\openspec.cmd validate room-diagnostic-ui-presentation-stability --strict` using repository-local tooling only.
- [ ] 7.5 Run `.\openspec.cmd validate --all --strict` using repository-local tooling only.
- [ ] 7.6 Run `git diff --check` and `git diff --cached --check`; verify no Graphify output or unrelated redesign/protocol changes.
- [ ] 7.7 After implementation, create/push the focused implementation commit only when explicitly authorized and only after implementation validation; the already-authorized design-artifact publication commit is separate.

## 8. Independent validation

- [ ] 8.1 Validate the exact current remote feature HEAD in a separate clean detached worktree and verify local HEAD equals `origin/<feature-branch>` before tests.
- [ ] 8.2 Repeat focused GUI/lifecycle tests with fresh results.
- [ ] 8.3 Repeat the full offline project test suite.
- [ ] 8.4 Repeat strict change validation and `validate --all --strict` using repository-local commands only.
- [ ] 8.5 Run Git diff checks and review implementation against every approved requirement, especially same-context vs new-context state boundaries and zero-I/O restoration.
- [ ] 8.6 Audit the modified network and Audio requirements against then-current root specs with the repository-required archive-applicability discipline where applicable.
- [ ] 8.7 Issue the independent implementation verdict according to current `RULES.md`; do not self-fix findings in the validation session.

## 9. Archive and completion

- [ ] 9.1 Archive only after permitting independent validation and explicit authorization using repository-local OpenSpec tooling.
- [ ] 9.2 Review archive/root-spec diff, especially replacement of network child-row/disclosure and Audio popup pinning semantics.
- [ ] 9.3 Run required post-archive strict validation, full offline tests, and Git checks.
- [ ] 9.4 Create/push a dedicated archive commit only with explicit authorization and verify remote archive HEAD.
- [ ] 9.5 Before merge, re-check current `master`, PR state/Draft/base/head, remote feature/archive HEAD, merge state/mergeability, and new commits; do not merge without explicit user authorization.
