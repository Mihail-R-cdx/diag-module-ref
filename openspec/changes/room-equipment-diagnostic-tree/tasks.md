## 1. Repository and architecture preparation

- [ ] 1.1 Before implementation, read `RULES.md` and `docs/equipment-inventory-runbook.md`, fetch `origin/master`, confirm the implementation branch is based on the current published architecture branch/head, and preserve unrelated work.
- [ ] 1.2 Re-read the approved `room-equipment-diagnostic-tree` proposal, design, and delta specs before changing production code or tests.
- [ ] 1.3 Confirm canonical inventory v4 remains the data authority and do not change importer/schema/recognition behavior unless a new OpenSpec change explicitly approves it.
- [ ] 1.4 Keep Graphify optional/local-only and do not create Graphify artifacts, evidence, or refresh checkpoints for this change.

## 2. Source-to-room resolution and deterministic room model

- [ ] 2.1 Add a focused room-session resolver that validates the normalized source IP against the loaded immutable inventory before model-specific diagnostic work.
- [ ] 2.2 Implement valid-inventory zero/one/many source-IP semantics: zero and many fail closed without manual model fallback; one record with non-null `room_id` enters room mode regardless of source-row supportability.
- [ ] 2.3 Preserve legacy single-device mode only for one valid-inventory source record with `room_id = null` and an exact supported canonical `diagnostic_model`.
- [ ] 2.4 Preserve manual model fallback only for inventory unavailable/unloadable/corrupt conditions; do not use fallback to repair valid inventory with missing/ambiguous/unmapped/unsupported source resolution.
- [ ] 2.5 Apply the same fail-closed valid-inventory rule to `Пароль`: a unique exact supported model may open credential configuration without diagnostics; zero/many/unmapped/unsupported results do not guess a model.
- [ ] 2.6 Build room membership from every record with the authoritative `room_id`; place the source record first and all remaining records in canonical `record_id` order.
- [ ] 2.7 Detect same-room duplicate IPs across all room records, including unsupported records, without filtering ambiguity by kind/model/page. Keep duplicate IPs in other rooms irrelevant after room authority is established.
- [ ] 2.8 Select room name, address, and VIP independently by source-record value first, then first nonblank/non-null canonical room record, with no room display conflict arbitration and no `room_id` display in the GUI.

## 3. Unified model capability registry

- [ ] 3.1 Extend the existing exact application dispatch registry rather than creating a second room-only model support list.
- [ ] 3.2 Add the one-shot adapter/view binding and any stable capability metadata required by room mode while preserving current exact `diagnostic_model` identities and existing lifecycle routes.
- [ ] 3.3 Add startup/composition validation for duplicate models, missing view bindings, missing one-shot adapter bindings, and other incomplete room-required registrations.
- [ ] 3.4 Keep runtime dispatch exact-only; do not reproduce importer token recognition or infer support from `source_model`, manufacturer text, `device_kind`, or row order.

## 4. Per-record room state and presentation projection

- [ ] 4.1 Introduce room generation/session identity containing inventory snapshot identity, normalized source IP, source record, and authoritative `room_id` without secret/session material.
- [ ] 4.2 Introduce independent `DeviceRowState` (or equivalent) for every room record with exact record/model/IP context, status, accepted cache, partial data, warnings, safe failure reason, capability binding, and row operation token/generation.
- [ ] 4.3 Make per-record state the source of truth; reusable `CodecScreen`, `PDUScreen`, `MatrixScreen`, and `AudioDSPScreen` widgets must only render accepted state and must not own hidden-row timers/sessions/workers.
- [ ] 4.4 Ensure multiple records of the same model keep independent state and that collapse/reopen/rebind reconstructs presentation from the exact row state rather than another same-model record.
- [ ] 4.5 Render one shared room header with room name/address/VIP and remove duplicated room metadata authority from tree-mode device content while preserving legacy single-device compatibility.

## 5. Unified one-shot adapter boundary

- [ ] 5.1 Define a model-neutral one-shot adapter contract that receives immutable exact row/attempt context and one assigned credential candidate and emits partial, usable-success, usable-success-with-warning, terminal-failure, and cleanup-complete outcomes.
- [ ] 5.2 Keep handlers/workers/adapters unable to iterate credential candidates or persist successful candidate/profile state.
- [ ] 5.3 Adapt ordinary codec refresh paths to one-shot room acquisition without leaving live/poll timers or interactive session work running after row retirement.
- [ ] 5.4 Adapt Matrix acquisition so the required final snapshot is accepted and persistent keepalive/session resources are stopped/released before room row retirement.
- [ ] 5.5 Adapt DMP acquisition so the first complete authoritative snapshot is accepted, further polling is stopped, and SSH/channel resources are cleaned before retirement.
- [ ] 5.6 Adapt PDU paths for one-shot room acquisition while preserving existing protocol/status semantics and ensuring automatic room PDU acquisition does not publish the legacy accepted-user-PDU-refresh trigger for PDU->room->codec enrichment.
- [ ] 5.7 Preserve all existing model-specific transport boundaries, exact CloudLink Bar/Box identities, parser normalization, and optional-enrichment semantics behind the adapters.

## 6. Sequential room orchestrator and credential plan

- [ ] 6.1 Implement one application-owned room queue that performs at most one record's diagnostic network I/O at a time.
- [ ] 6.2 For every eligible row enforce `currentness -> ping -> credential plan -> assigned attempt -> accepted terminal outcome -> cleanup/release -> next row`.
- [ ] 6.3 Make ping failure terminal for that row before model handler/worker acquisition and continue the queue.
- [ ] 6.4 Reuse saved supported successful credential index/profile first for exact model/IP, then advance monotonically through only the remaining candidate suffix without wrap-around.
- [ ] 6.5 Advance credential candidates only after structured new-login `AuthenticationError`; do not advance for timeout, transport, TLS, protocol, parse, empty/malformed response, arbitrary text, or numeric substrings.
- [ ] 6.6 Treat missing required credentials for authenticated non-PCS4i models as a safe pre-I/O configuration failure and continue the room queue.
- [ ] 6.7 Preserve the approved PCS4i credentialless attempt when no explicit/mapped credential exists.
- [ ] 6.8 Persist successful credential index/profile only after an accepted final success; never persist from partial, failed, stale, or cleanup-degraded outcomes.

## 7. Row status, partial data, warnings, and safe failures

- [ ] 7.1 Implement pre-I/O status priority: unsupported -> `не поддерживается`; supported missing IP -> `IP не указан`; supported same-room duplicate IP -> `неоднозначный IP`; otherwise `ожидание опроса`.
- [ ] 7.2 Keep unsupported, missing-IP, and ambiguous-IP rows visible but at zero device I/O; make their network/state-changing actions unavailable. Missing/ambiguous supported rows and unsupported rows must not open an active diagnostic screen.
- [ ] 7.3 Show `Модель не определена` when an unsupported row also has null `source_model`; do not infer an alternate label from other inventory fields.
- [ ] 7.4 Transition the active eligible row through `подключение...` and only to `подключено` after accepted usable final success.
- [ ] 7.5 Preserve intermediate partial values as visible unconfirmed evidence while keeping the row in progress; partial data must not advance the queue, enable controls, or become successful cache.
- [ ] 7.6 Preserve model-specific usable final success with optional warning, including existing Polycom/PCS4i-style optional enrichment failures; cache usable fields and classify the room cycle as completed with problems.
- [ ] 7.7 If terminal failure follows partial data, retain only explicitly incomplete/unconfirmed presentation and do not cache/persist it as success.
- [ ] 7.8 Map typed/category failures to safe inline reasons; do not expose raw exception strings, credentials, tokens, cookies, secret-bearing URLs, request bodies, or authentication text heuristics.

## 8. Bounded cleanup and stale-generation isolation

- [ ] 8.1 Add configurable/testable bounded cleanup policy for every automatic one-shot row lifecycle; do not make an exact timeout value a user-facing OpenSpec contract.
- [ ] 8.2 Do not start the next device before cleanup completes or the cleanup deadline produces a logical abandonment boundary.
- [ ] 8.3 On cleanup timeout, permanently remove authority from the old row lifecycle, ignore its late callbacks, and continue to the next room record instead of hanging the room cycle.
- [ ] 8.4 When cleanup times out after usable data, keep the snapshot visibly stale and mark the row degraded/`соединение потеряно`; without usable data, mark terminal failure.
- [ ] 8.5 Associate callbacks with room generation, exact record/model/IP context, and row operation token; stale callbacks must not change row/cache/global state, credential/profile memory, control locks, or queue advancement.
- [ ] 8.6 Recheck currentness before handler acquisition and before first device I/O when separable; queued stale work must perform zero handler acquisition and zero network I/O.
- [ ] 8.7 Keep background resource cleanup on the owning execution lane and keep the Qt GUI thread non-blocking.

## 9. Room-tree GUI and full-room Refresh

- [ ] 9.1 Render the complete room tree before starting sequential diagnostics; source row first, deterministic remaining order, one accordion row expanded at most.
- [ ] 9.2 During the automatic cycle disable top IP/Password/full Refresh. For the entire MIH-7 room-mode session, including after terminal room completion, keep every row network/state-changing/live/auxiliary/local-Refresh action disabled or unbound until MIH-8 provides exact-row interaction authority.
- [ ] 9.3 Keep the permanent top-level `Отладка` action disabled/unavailable for the entire MIH-7 room-mode session; do not bind it from top source IP, current reusable screen, or prior single-device state.
- [ ] 9.4 Allow a waiting eligible row to be expanded with placeholder/waiting values without causing early I/O or queue reordering.
- [ ] 9.5 Suppress automatic per-device modal error/progress/terminal windows during room polling; show progress through row status/detail and one global room status.
- [ ] 9.6 On every new room session, including top full Refresh, if the source row is supported and expandable, make it the only initially expanded row; if the source row is non-expandable, start fully collapsed. Never carry forward a previously selected secondary row or auto-select another row.
- [ ] 9.7 Do not auto-expand or change accordion selection because a row succeeds, warns, or fails.
- [ ] 9.8 Provide no separate Cancel action for the automatic room cycle. On application close, invalidate/cancel read-only room work best-effort without blocking the GUI on network cleanup.
- [ ] 9.9 Show global `Опрос оборудования помещения...` while active, `Опрос завершён` after a fully clean cycle, and `Опрос завершён с проблемами` when any row is unsupported/missing/ambiguous/failed/degraded/warned.
- [ ] 9.10 Update `Последнее обновление` at terminal completion of every full room cycle, including a cycle with no eligible network I/O.
- [ ] 9.11 Make top Refresh in room mode first invalidate and clear prior room generation/tree/cache/presentation/row bindings/accordion selection, then re-resolve the current source IP, rebuild new room state, and rerun the complete room cycle. Failed re-resolution must not restore the old room presentation.
- [ ] 9.12 Invalidate/clear the established room presentation when the top IP is edited after a completed cycle; restoring old text alone must not resurrect old room authority.

## 10. Legacy compatibility and deferred interactive boundary

- [ ] 10.1 Keep valid legacy single-device diagnostics working for a unique supported source record with no `room_id` and for explicit manual fallback when inventory is unavailable/unloadable/corrupt.
- [ ] 10.2 Keep the existing PDU-room-codec enrichment capability unchanged for its legacy user-PDU lifecycle, but prove automatic room PDU one-shot diagnostics do not start it.
- [ ] 10.3 Do not implement post-cycle live handoff, local per-device Refresh, Call Log/auxiliary network operations, state-changing commands, mutation readback/reconciliation, or post-cycle connection recovery in MIH-7; keep existing reused-screen implementations fail-closed/disabled in room mode after cycle completion rather than allowing them to use top-IP or previous single-device target authority.
- [ ] 10.4 Expose stable room session, exact per-record state/cache, capability registry, one-shot adapter, and terminal row-state contracts for the following `room-device-interaction-lifecycle` change.

## 11. Focused regression coverage

- [ ] 11.1 Test source-IP zero/one/many resolution, room-mode entry for unsupported source records with valid `room_id`, fail-closed valid-inventory behavior, and legacy no-room supported-device fallback behavior.
- [ ] 11.2 Test credential-configuration resolution remains network-free and fail-closed for valid inventory zero/many/unmapped/unsupported results.
- [ ] 11.3 Test room membership/order, source-first row placement, room display source-first fallback, and absence of room-name/address/VIP conflict arbitration.
- [ ] 11.4 Test unsupported/missing-IP/same-room-duplicate-IP row precedence and prove zero device I/O for ineligible rows, including ambiguity caused by an unsupported record.
- [ ] 11.5 Test same IP in another room does not invalidate a secondary row after room authority is established, while the same IP as a top-level source remains globally ambiguous.
- [ ] 11.6 Test two same-model records maintain independent row state and widget projection/cache.
- [ ] 11.7 Test model registry validation and exact-only support authority; no runtime `source_model` recognition.
- [ ] 11.8 Test strict one-at-a-time queue ordering and prove accordion switching does not reorder or start early I/O.
- [ ] 11.9 Test each persistent model adapter retires polling/keepalive/session resources before the next room record starts.
- [ ] 11.10 Test structured-auth-only candidate fallback, saved-index suffix behavior, no wrap-around, no fallback on non-auth failures, no success persistence on partial/failure, and PCS4i credentialless exception.
- [ ] 11.11 Test usable-success-with-warning versus terminal failure and partial-followed-by-failure cache semantics.
- [ ] 11.12 Test cleanup timeout abandonment, queue continuation, stale callback suppression, and degraded stale-snapshot presentation.
- [ ] 11.13 Test no automatic room PDU one-shot starts legacy related-codec enrichment.
- [ ] 11.14 Test full-room top Refresh builds a new generation/state set and stale prior callbacks cannot update it.
- [ ] 11.15 Test automatic room polling produces no per-device modal/progress/terminal dialogs and leaves the Qt event loop responsive.
- [ ] 11.16 Test global room summary and `Последнее обновление` for clean, warning/problem, and no-eligible-I/O cycles.
- [ ] 11.17 Test clean and problem terminal room cycles leave local Refresh, Matrix route, PDU/codec mutation, live/polling, Call Log/auxiliary, and equivalent row network intents disabled or rejected before handler acquisition/network I/O.
- [ ] 11.18 Test top-level `Отладка` is unavailable in room mode and cannot display or bind mixed model/IP context from the top source IP or prior single-device state.
- [ ] 11.19 Test deterministic accordion initialization/reset: expandable source initially expanded, non-expandable source fully collapsed, automatic outcomes do not change expansion, full Refresh does not retain a prior secondary selection, and failed re-resolution does not resurrect old tree/cache/presentation.

## 12. Validation, independent review, archive, and completion

- [ ] 12.1 Run focused room/dispatch/inventory/lifecycle/controller regression tests added for this implementation.
- [ ] 12.2 Run the full offline suite with `python -m unittest discover -s tests -p "test_*.py"`.
- [ ] 12.3 Run `.\openspec.cmd validate room-equipment-diagnostic-tree --strict` using the repository-local wrapper.
- [ ] 12.4 Run `.\openspec.cmd validate --all --strict` using the repository-local wrapper.
- [ ] 12.5 Run `git diff --check` and `git diff --cached --check`.
- [ ] 12.6 Synchronize this task list with implementation evidence without prematurely marking independent validation or archive work complete.
- [ ] 12.7 Create and push a focused implementation commit before requesting independent validation; implementation must not issue its own final `APPROVE`.
- [ ] 12.8 Independent validation must use a clean detached worktree from current `origin/<feature-branch>`, confirm local/remote SHA equality, rerun required tests/strict validation/Git checks, and review implementation against approved architecture without fixing its own findings.
- [ ] 12.9 Independent validation must perform a disposable archive-applicability check because this change adds a root capability and modifies an existing root requirement.
- [ ] 12.10 Archive only after a permitting independent verdict; then review archive/root-spec delta, run `.\openspec.cmd validate --all --strict`, full offline tests, `git diff --check`, and `git diff --cached --check`, and create/push a dedicated archive commit.
- [ ] 12.11 Before merge, reconfirm current remote archive HEAD and current `master`; merge only with explicit user authorization and never force-push.
