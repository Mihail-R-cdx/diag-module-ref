# Tasks: matrix-diagnostic-modern-ui

## 1. Architecture and current-source alignment

- [x] 1.1 Before implementation, reread current `RULES.md`, current `master`, this approved change, relevant root specs, and current Matrix room/standalone source/tests. Confirm implementation is based on the approved remote HEAD rather than an older local branch/report.
- [x] 1.2 Reconfirm the normative target is the expanded exact-row Matrix presentation inside `RoomDiagnosticTreeWidget`; standalone `MatrixScreen` remains a separate lifecycle/surface and is not promoted into room authority.
- [x] 1.3 Reconfirm current authoritative Matrix evidence fields and preserve `Нет данных` for reference-layout slots without accepted MAC/serial/firmware/uptime evidence. Do not add new SIS reads for those fields.
- [x] 1.4 Reconfirm MIH-11 explicitly includes normalization-only corrections for existing Matrix input-count, model/temperature, exact current-input response grammar, and input-HDCP-status reads; legacy defaults must not become accepted device or route authority.

## 2. Fail-closed Matrix normalization

- [x] 2.1 Remove authoritative use of legacy eight-input defaults. Publish/accept `inputs_num` only when existing model/capability evidence proves the current count; otherwise preserve UNKNOWN/absent count.
- [x] 2.2 Ensure per-input arrays produced only from an unproven fallback count cannot make those ordinals actionable for room routing.
- [x] 2.3 Normalize General-information model fail-closed: successful non-empty current model read may be accepted; failed/missing/unusable evidence and local `Unknown` convenience sentinel become `None`/absent rather than device-reported data.
- [x] 2.4 Normalize temperature fail-closed: failed/missing/malformed read becomes `None`/absent and never synthetic zero; preserve a real numeric zero only when it was actually parsed from a successful current response.
- [x] 2.5 Correct existing connection normalization so empty, failed, malformed, ambiguous, extra-payload, or out-of-range readback yields `current_connection = None`/UNKNOWN; never substitute input 1.
- [x] 2.6 Implement exact existing-`!` response grammar after normal framing: optionally strip one exact echo line `!`, then accept exactly one untagged ordinal-only response `N` or one tagged/verbose `In<N> All` response; require one in-range ordinal. Echo-only, extra payload, multiple candidates/numeric tokens, partial matches, unrelated digits, and out-of-range values remain UNKNOWN.
- [x] 2.7 Add normalized per-input tri-state `hdcp_present` (or equivalent approved representation) derived from the existing input HDCP-status read only with exact raw mapping `2 -> True`, `1 -> False`, `0 -> False`, and missing/failed/malformed/unrecognized -> `None`.
- [x] 2.8 Do not use input HDCP authorization/configuration or output HDCP state as the room HDCP-column authority. Do not add a new HDCP-version read.

## 3. Matrix presentation layout

- [x] 3.1 Build/extract a presentation-only Matrix dashboard for the room exact-row path with baseline card order: `Общая информация` -> `Матрица (входы и коммутация)` -> `Быстрые действия`.
- [x] 3.2 Render General information rows in exact order: `Модель`, `MAC-адрес`, `Серийный номер`, `Версия прошивки`, `Температура`, `Время работы`; use accepted evidence only and safe no-data presentation for missing fields. In particular, normalized model/temperature `None` is `Нет данных`, while a successfully device-reported numeric temperature zero remains `0` rather than no-data.
- [x] 3.3 Replace the current room Matrix table presentation with exact column order: compact input ordinal, `Сигнал`, `HDCP`, `Входы`, accepted output-1 name / `Main Output` fallback.
- [x] 3.4 Use only proven accepted current input count/order; add regression coverage proving the presentation neither hard-codes nor falls back to eight rows when count is unknown.
- [x] 3.5 Preserve non-color text/cue meaning for signal, HDCP presence, active route, non-selected route, and no-data states.
- [x] 3.6 Render the HDCP column strictly as `есть` / `нет` / `Нет данных` from normalized `hdcp_present`; never show `2.2`, `1.4`, any version/status token, authorization value, or output HDCP state.
- [ ] 3.7 At `1440 x 900`, keep the central Matrix card dominant with approved proportions and no baseline horizontal clipping. At `1180 x 720`, use controlled reflow/scrolling without changing semantic order or route authority.
- [ ] 3.8 Keep dark/light theme switching presentation-only and geometry-stable for equivalent viewport/layout mode.

## 4. Quick/reference actions

- [x] 4.1 Wire `Обновить статус` to the existing exact-row Local Refresh intent and only enable it under existing room lifecycle authorization.
- [x] 4.2 Render `Перезагрузить устройство` as disabled/non-actionable; it must emit no application intent, worker start, handler/session acquisition, or protocol command.
- [x] 4.3 Do **not** render `Открыть расширенный экран` in MIH-11. There is no enabled control, disabled placeholder, navigation intent, or manual-acceptance requirement for it.

## 5. Safe Matrix route intent

- [x] 5.1 Add a presentation-only, non-secret exact-row Matrix route intent for output 1 and proven accepted input N. Do not pass credentials, handler/session identity, target-search text, or standalone screen state through the widget intent.
- [x] 5.2 Enable routing only for the current expanded usable connected `Extron IN1804` row when the unified registration advertises approved Matrix mutation/reconciliation capability, the room lane permits mutation, and input N is within proven accepted input authority.
- [x] 5.3 Make the currently active route cell non-actionable/no-op; local hover/click state must not alter accepted route state.
- [x] 5.4 At composition, verify the intent still belongs to the current expanded record, show explicit operator confirmation, and call `RoomInteractionCoordinator.confirm_mutation()` only after confirm. Cancel performs zero lifecycle/device I/O.

## 6. Unified registry and composition bindings

- [x] 6.1 Extend exact `Extron IN1804` unified dispatch registration with Matrix-specific room mutation and reconciliation binding keys. Do not add a parallel model list or widget/model-substring capability inference.
- [x] 6.2 Add composition resolution for Matrix mutation/reconciliation bindings while preserving existing PDU bindings and Matrix `matrix_room_live` / `matrix_one_shot` ownership.
- [x] 6.3 Ensure startup/composition validation fails closed if registry declares Matrix mutation/reconciliation capability but required binding/cancellation/cleanup implementation is unavailable.
- [x] 6.4 Ensure cancellation/supersession targets the actual Matrix mutation owner rather than PDU-only cancellation state.

## 7. Matrix mutation execution safety

- [x] 7.1 Implement a background exact-context Matrix room route adapter/controller extension that receives one `RoomInteractionContext`, one validated output-1/input-N intent, and exactly one application-selected credential candidate for the current attempt.
- [x] 7.2 Reject stale/superseded context before handler/session acquisition and before route send; no Qt GUI-thread Matrix I/O.
- [x] 7.3 Preserve application/composition credential ownership. Worker/handler must not iterate candidates.
- [x] 7.4 Permit credential advancement only after structured authentication rejection proven before route delivery and only after prior attempt cleanup/release. Do not infer fallback from text.
- [x] 7.5 Once route send is attempted or may have been delivered, send at most once for that confirmed mutation generation; no credential advance, automatic replay, read-only retry policy, or string heuristic may repeat it after ambiguous/unknown outcome.
- [x] 7.6 Mutation success/ACK remains non-authoritative and must not directly modify `accepted_snapshot.current_connection` or visible active-route state.
- [x] 7.7 Ensure Matrix mutation transport ownership is retired before mandatory reconciliation acquires conflicting device resources; if this cannot be proven, stop and return for architecture review.

## 8. Matrix-specific reconciliation

- [x] 8.1 Preserve requested input identity across mutation-to-reconciliation handoff as non-secret exact-operation evidence.
- [x] 8.2 Run reconciliation through current exact-row read-only Matrix acquisition/currentness authority; do not reuse stale standalone/global Matrix target.
- [x] 8.3 Accept reconciliation success only when fail-closed normalized current readback matches one exact accepted `!` response family and establishes `current_connection == requested input_num`.
- [x] 8.4 Explicitly prove requested Input 1 is **not** confirmed by empty, failed, malformed, ambiguous, extra-payload, out-of-range, outside-grammar, or otherwise UNKNOWN readback.
- [x] 8.5 On readback mismatch/UNKNOWN or unconfirmed final state, keep prior cache only as stale/unconfirmed presentation, block row network actions/live, and require top full Refresh according to existing room mutation contract.
- [x] 8.6 On confirmed reconciliation, atomically replace row accepted Matrix snapshot and permit normal eligible lifecycle/live only after currentness/cleanup checks.

## 9. Focused regression coverage

- [x] 9.1 Input-count normalization tests: missing/unrecognized model/count does not become eight accepted inputs and unproven ordinals remain non-actionable.
- [ ] 9.2 General-info normalization tests: failed/missing model does not publish `Unknown`; failed/missing/malformed temperature becomes UNKNOWN rather than zero; a successful device-reported numeric zero remains accepted zero.
- [ ] 9.3 Current-input grammar tests: accept untagged ordinal-only `N`, tagged/verbose `In<N> All`, exact echo `!` + each accepted form; reject echo-only, extra/multiple payloads, multiple numeric candidates, unrelated numeric text, partial matches, and out-of-range ordinals.
- [x] 9.4 HDCP normalization tests: raw status `2/1/0` becomes `True/False/False`; failed/malformed/unrecognized input HDCP status becomes UNKNOWN and not false.
- [x] 9.5 Presentation tests: three-card order, General information field order, no-data slots, exact table column order, proven data-driven input count, dynamic output header, signal/HDCP-presence/route non-color states.
- [ ] 9.6 Presentation tests: HDCP never renders a version token; `Открыть расширенный экран` is absent; disabled reboot emits no intent.
- [ ] 9.7 Intent tests: active-route click no-op; eligible non-active route emits one safe intent; stale/degraded/blocked/non-current/unproven-input rows emit/accept no route mutation.
- [ ] 9.8 Confirmation tests: Cancel creates zero network work; Confirm enters the one serialized room mutation lane.
- [ ] 9.9 Registry tests: exact Extron IN1804 declares Matrix mutation/reconciliation bindings; missing binding implementation fails closed; no parallel Matrix mutation model list exists.
- [x] 9.10 Mutation tests: live retirement before send, stale pre-acquisition rejection, structured pre-delivery auth fallback, at-most-one send after command invocation, no string-based fallback/replay.
- [ ] 9.11 Reconciliation tests: ACK does not update cache; matching truthful exact-grammar readback accepts route; mismatching/UNKNOWN readback blocks/unconfirms; requested Input 1 with empty/malformed/ambiguous/outside-grammar readback is never accepted; late stale callbacks cannot update replacement context.
- [ ] 9.12 Regression tests: existing PDU mutation/reconciliation remains unchanged.
- [x] 9.13 Regression tests: existing Matrix room live/local Refresh remains unchanged.
- [x] 9.14 Regression tests: standalone MatrixScreen/MatrixController routing remains functional and separate from room exact-row authority, subject to removal of fabricated normalization defaults.
- [ ] 9.15 Regression tests: common accordion one-expanded-row rule, target-search/foundation shell, and theme toggle remain unchanged; theme/resize/hover/cell repaint causes no device I/O.

## 10. Implementation validation

- [x] 10.1 Run focused Matrix normalization/room GUI/lifecycle tests for all changed surfaces.
- [x] 10.2 Run full offline test suite from implementation branch and record fresh command/counts; do not copy prior counts.
- [x] 10.3 Run repository-local `.\openspec.cmd validate matrix-diagnostic-modern-ui --strict`.
- [x] 10.4 Run repository-local `.\openspec.cmd validate --all --strict`.
- [x] 10.5 Run `git diff --check` and `git diff --cached --check`.
- [ ] 10.6 Perform local manual visual acceptance at `1440 x 900` in dark and light themes: left General information, dominant center Matrix table, right Quick actions, exact field/column order, HDCP presence-only projection, truthful no-data/UNKNOWN states, disabled reboot, and no `Открыть расширенный экран`. Screenshots remain local evidence unless explicitly requested as tracked artifacts.
- [ ] 10.7 Create one focused implementation commit and push to feature branch only after focused/full tests and strict validation pass. Do not archive or self-approve.

## 11. Independent validation and completion gates

- [ ] 11.1 Independent validator uses a separate clean detached worktree from current `origin/agent/matrix-diagnostic-modern-ui`, proves local/remote SHA equality and clean status before/after, and independently repeats focused/full tests, strict validation, Git checks, architecture/diff review, normalization/mutation/reconciliation safety review, and visual acceptance as required.
- [ ] 11.2 Because this change adds/modifies root-spec requirements, independent validation performs a disposable archive-applicability check on a disposable worktree/branch, not on the feature branch.
- [ ] 11.3 Only after independent `APPROVE` / `READY FOR ARCHIVE`, archive with repository-local `.\openspec.cmd archive matrix-diagnostic-modern-ui --yes` in the archive/completion phase.
- [ ] 11.4 Post-archive: review archive/root-spec diff, run `.\openspec.cmd validate --all --strict`, full offline tests, `git diff --check`, `git diff --cached --check`, and create/push a dedicated archive commit.
- [ ] 11.5 Before merge, recheck current remote archive HEAD and current `master`. Do not mark PR ready, merge, close, or delete branches without explicit user authorization.
