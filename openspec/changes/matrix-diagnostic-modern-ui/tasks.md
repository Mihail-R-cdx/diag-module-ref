# Tasks: matrix-diagnostic-modern-ui

## 1. Architecture and current-source alignment

- [ ] 1.1 Before implementation, reread current `RULES.md`, current `master`, this approved change, relevant root specs, and current Matrix room/standalone source/tests. Confirm implementation is based on the approved remote HEAD rather than an older local branch/report.
- [ ] 1.2 Reconfirm the normative target is the expanded exact-row Matrix presentation inside `RoomDiagnosticTreeWidget`; standalone `MatrixScreen` remains a separate lifecycle/surface and is not promoted into room authority.
- [ ] 1.3 Reconfirm current authoritative Matrix evidence fields and preserve `Нет данных` for reference-layout slots without accepted MAC/serial/firmware/uptime evidence. Do not add protocol/parser scope silently.

## 2. Matrix presentation layout

- [ ] 2.1 Build/extract a presentation-only Matrix dashboard for the room exact-row path with baseline card order: `Общая информация` -> `Матрица (входы и коммутация)` -> `Быстрые действия`.
- [ ] 2.2 Render General information rows in exact order: `Модель`, `MAC-адрес`, `Серийный номер`, `Версия прошивки`, `Температура`, `Время работы`; use accepted evidence only and safe no-data presentation for missing fields.
- [ ] 2.3 Replace the current room Matrix table presentation with exact column order: compact input ordinal, `Сигнал`, `HDCP`, `Входы`, accepted output-1 name / `Main Output` fallback.
- [ ] 2.4 Use accepted current input count/order; add regression coverage proving the presentation does not hard-code eight rows.
- [ ] 2.5 Preserve non-color text/cue meaning for signal, HDCP, active route, non-selected route, and no-data states. Do not fabricate the reference's sample `2.2` HDCP value.
- [ ] 2.6 At the `1440 x 900` baseline keep the central Matrix card dominant with the approved proportional hierarchy and no baseline horizontal clipping. At `1180 x 720`, use controlled reflow/scrolling without changing semantic order or route authority.
- [ ] 2.7 Keep dark/light theme switching presentation-only and geometry-stable for equivalent viewport/layout mode.

## 3. Quick/reference actions

- [ ] 3.1 Wire `Обновить статус` to the existing exact-row Local Refresh intent and only enable it under existing room lifecycle authorization.
- [ ] 3.2 Render `Перезагрузить устройство` as disabled/non-actionable; it must emit no application intent, worker start, handler/session acquisition, or protocol command.
- [ ] 3.3 If `Открыть расширенный экран` is rendered for reference fidelity, keep it disabled/non-actionable. Do not navigate/promote standalone `MatrixScreen` in this change.

## 4. Safe Matrix route intent

- [ ] 4.1 Add a presentation-only, non-secret exact-row Matrix route intent for output 1 and accepted input N. Do not pass credentials, handler/session identity, target-search text, or standalone screen state through the widget intent.
- [ ] 4.2 Enable routing only for the current expanded usable connected `Extron IN1804` row when the unified registration advertises the approved Matrix mutation/reconciliation capability and the room lane permits mutation.
- [ ] 4.3 Make the currently active route cell non-actionable/no-op; local hover/click state must not alter accepted route state.
- [ ] 4.4 At composition, verify the intent still belongs to the current expanded record, show explicit confirmation, and call `RoomInteractionCoordinator.confirm_mutation()` only after Yes/confirm. Cancel must perform zero lifecycle/device I/O.

## 5. Unified registry and composition bindings

- [ ] 5.1 Extend the exact `Extron IN1804` unified dispatch registration with Matrix-specific room mutation and reconciliation binding keys. Do not add a parallel model list or widget/model-substring capability inference.
- [ ] 5.2 Add composition resolution for the Matrix mutation/reconciliation bindings while preserving existing PDU bindings and existing Matrix `matrix_room_live` / `matrix_one_shot` ownership.
- [ ] 5.3 Ensure startup/composition validation fails closed if the registry declares Matrix mutation/reconciliation capability but required binding/cleanup implementation is unavailable.
- [ ] 5.4 Ensure cancellation/supersession targets the actual Matrix mutation owner rather than PDU-only cancellation state.

## 6. Matrix mutation execution safety

- [ ] 6.1 Implement a background exact-context Matrix room route adapter/controller extension that receives one `RoomInteractionContext`, one validated output-1/input-N intent, and exactly one application-selected credential candidate for the current attempt.
- [ ] 6.2 Reject stale/superseded context before handler/session acquisition and before route send; no Qt GUI-thread Matrix I/O.
- [ ] 6.3 Preserve application/composition credential ownership. Worker/handler must not iterate candidates.
- [ ] 6.4 Permit credential advancement only after structured authentication rejection proven before route delivery and only after prior attempt cleanup/release. Do not infer fallback from text.
- [ ] 6.5 Once route send is attempted or may have been delivered, send at most once for that confirmed mutation generation; no credential advance, automatic replay, read-only retry policy, or string heuristic may repeat it after ambiguous/unknown outcome.
- [ ] 6.6 Mutation success/ACK remains non-authoritative and must not directly modify `accepted_snapshot.current_connection` or visible active-route state.
- [ ] 6.7 Ensure the Matrix mutation transport owner is physically/reliably retired before mandatory reconciliation can acquire conflicting device resources; if this cannot be proven with the selected implementation approach, stop and return for architecture review.

## 7. Matrix-specific reconciliation

- [ ] 7.1 Preserve the requested input identity across the mutation-to-reconciliation handoff as non-secret exact-operation evidence.
- [ ] 7.2 Run reconciliation through current exact-row read-only Matrix acquisition/currentness authority; do not reuse a stale standalone/global Matrix target.
- [ ] 7.3 Accept reconciliation success only when current accepted readback establishes `current_connection == requested input_num`.
- [ ] 7.4 On readback mismatch, unknown route, ambiguous mutation outcome, or unconfirmed final state, keep prior cache only as stale/unconfirmed presentation, block row network actions/live, and require top full Refresh according to existing room mutation contract.
- [ ] 7.5 On confirmed reconciliation, atomically replace the row's accepted Matrix snapshot and permit normal eligible lifecycle/live only after currentness/cleanup checks.

## 8. Focused regression coverage

- [ ] 8.1 Presentation tests: three-card order, General information field order, no-data slots, exact table column order, data-driven input count, dynamic output header, signal/HDCP/route non-color states.
- [ ] 8.2 Presentation tests: `2.2` is not fabricated without accepted evidence; disabled reboot/expanded-screen controls emit no intent.
- [ ] 8.3 Intent tests: active-route click no-op; eligible non-active route emits one safe intent; stale/degraded/blocked/non-current rows emit/accept no route mutation.
- [ ] 8.4 Confirmation tests: Cancel creates zero network work; Confirm enters the one serialized room mutation lane.
- [ ] 8.5 Registry tests: exact Extron IN1804 declares Matrix mutation/reconciliation bindings; missing binding implementation fails closed; no parallel Matrix mutation model list exists.
- [ ] 8.6 Mutation tests: live retirement before send, stale pre-acquisition rejection, structured pre-delivery auth fallback, at-most-one send after command invocation, no string-based fallback/replay.
- [ ] 8.7 Reconciliation tests: ACK does not update cache; matching readback accepts route; mismatching/unknown readback blocks/unconfirms; late stale mutation/reconciliation callbacks cannot update replacement context.
- [ ] 8.8 Regression tests: existing PDU mutation/reconciliation remains unchanged.
- [ ] 8.9 Regression tests: existing Matrix room live/local Refresh remains unchanged.
- [ ] 8.10 Regression tests: standalone MatrixScreen/MatrixController routing remains functional and separate from room exact-row authority.
- [ ] 8.11 Regression tests: common accordion one-expanded-row rule, target-search/foundation shell, and theme toggle remain unchanged; theme/resize/hover/cell repaint causes no device I/O.

## 9. Implementation validation

- [ ] 9.1 Run focused Matrix/room GUI/lifecycle tests for all changed surfaces.
- [ ] 9.2 Run full offline test suite from the implementation branch and record fresh command/counts in the implementation report; do not copy prior counts.
- [ ] 9.3 Run repository-local `\.\openspec.cmd validate matrix-diagnostic-modern-ui --strict`.
- [ ] 9.4 Run repository-local `\.\openspec.cmd validate --all --strict`.
- [ ] 9.5 Run `git diff --check` and `git diff --cached --check`.
- [ ] 9.6 Perform local manual visual acceptance at `1440 x 900` in dark and light themes against the self-contained OpenSpec hierarchy: left General information, dominant center Matrix table, right Quick actions, exact field/column order, readable non-color status, disabled placeholders. Screenshots remain local evidence unless explicitly requested as tracked artifacts.
- [ ] 9.7 Create one focused implementation commit and push to the feature branch only after focused/full tests and strict validation pass. Do not archive or self-approve.

## 10. Independent validation and completion gates

- [ ] 10.1 Independent validator uses a separate clean detached worktree from current `origin/agent/matrix-diagnostic-modern-ui`, proves local/remote SHA equality and clean status before/after, and independently repeats focused/full tests, strict validation, Git checks, architecture/diff review, mutation/reconciliation safety review, and visual acceptance as required.
- [ ] 10.2 Because this change modifies/adds root-spec requirements, independent validation performs a disposable archive-applicability check on a disposable worktree/branch, not on the feature branch.
- [ ] 10.3 Only after independent `APPROVE` / `READY FOR ARCHIVE`, archive with repository-local `\.\openspec.cmd archive matrix-diagnostic-modern-ui --yes` in the archive session.
- [ ] 10.4 Post-archive: review archive/root-spec diff, run `\.\openspec.cmd validate --all --strict`, full offline tests, `git diff --check`, and create/push a dedicated archive commit.
- [ ] 10.5 Before merge, recheck current remote archive HEAD and current `master`. Do not mark PR ready, merge, close, or delete branches without explicit user authorization.
