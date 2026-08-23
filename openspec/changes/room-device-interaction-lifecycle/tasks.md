## 1. Application-owned room interaction authority

- [x] 1.1 Add a focused room interaction coordinator/state machine bound to exact `inventory snapshot + room generation + record_id + diagnostic_model + IP + operation token` context.
- [x] 1.2 Extend the existing single exact model capability/dispatch registry so the same registration owns screen/view, room one-shot adapter, live, Local Refresh, auxiliary network actions, mutations, and required cleanup/release hooks; do not create parallel supported-model tables.
- [x] 1.3 Keep authoritative interactive state/cache per record and keep reusable Qt screens presentation-only.
- [x] 1.4 Enforce one serialized room interactive network lane across mutually exclusive `LIVE / LOCAL_REFRESH / AUXILIARY_READ / MUTATION / RECONCILIATION`, including stale-before-handler/stale-before-I/O checks and cross-type exclusion while prior authority is active or retiring.

## 2. Post-cycle live lifecycle

- [x] 2.1 Start live only after terminal room-cycle completion for the latest currently expanded connected row that advertises an existing live capability from the unified model registry.
- [x] 2.2 Implement safe live handoff `invalidate -> model-owner physical cleanup/release or bounded abandonment -> start latest current target` and collapse-to-none behavior for CloudLink, Matrix, and DMP.
- [x] 2.3 Keep network-backed controls disabled during pending handoff and prove rapid A -> B -> C switching starts no stale intermediate live I/O.
- [x] 2.4 Convert terminal live/session/auth loss after approved recovery into exact-row `соединение потеряно` without blocking other room rows, and set the global bottom status to `Есть проблемы с соединением`.

## 3. Local exact-row Refresh

- [x] 3.1 Bind Local Refresh only to the current connected exact row and retire live before new read-only I/O.
- [x] 3.2 From Local Refresh acceptance through terminal cleanup, disable source IP, Password, top full Refresh, accordion switching/collapse, mutations, auxiliary actions, another Local Refresh, and every competing row network action; purely local exact-row Debug may remain available.
- [x] 3.3 Reuse approved credential planning, preliminary reachability, model diagnostic acquisition, warning semantics, and bounded cleanup.
- [x] 3.4 Atomically replace authoritative row cache only on accepted usable result.
- [x] 3.5 On terminal Local Refresh failure, stop live, block all row network/state-changing controls, preserve safe stale presentation as applicable, set global problem status, and require top full Refresh for recovery.

## 4. Auxiliary read-only operations and Debug

- [x] 4.1 Bind Call Log and all network-backed auxiliary actions to exact current row context and the single cross-type room interaction lane; allow at most one auxiliary network operation at a time.
- [x] 4.2 Stop/retire live before auxiliary I/O and resume it only after terminal cleanup when the same row remains current and usable.
- [x] 4.3 While auxiliary read is active/retiring, disable source IP, Password, Local Refresh, mutations, other auxiliary actions, and competing row network actions; keep top full Refresh available as global supersession and keep accordion switching/collapse available as an auxiliary cancellation boundary.
- [x] 4.4 Preserve application-owned structured credential fallback; ordinary parse/business failure must not become credential retry or whole-row degradation without typed connection/session authority.
- [x] 4.5 Treat both real accordion row switch/collapse and direct user close (`X`) of an active auxiliary child window as exact-request cancellation boundaries: invalidate authority, publish cancel/stop, perform bounded cleanup, reject late callbacks, resume eligible live if the same row remains current/usable, and require a fresh acquisition on reopen.
- [x] 4.6 Bind `Отладка` to exact row as pure local presentation with no network I/O or live teardown on open/close; allow it during auxiliary activity only while that exact row remains current.
- [x] 4.7 Keep top full Refresh available as mandatory global supersession during auxiliary read and prove bounded cancellation/abandonment.

## 5. State-changing commands and mandatory reconciliation

- [x] 5.1 Keep confirmation view-only; Cancel must leave live/context unchanged.
- [x] 5.2 After confirmation, lock incompatible actions, retire live, and refuse mutation send if cleanup does not complete within policy.
- [x] 5.3 Execute state-changing command once under exact-row context; preserve existing structured pre-send credential rules and never infer retry from public error strings.
- [x] 5.4 Require mandatory readback/reconciliation before terminal success; command ACK alone must not update authoritative cache.
- [x] 5.5 On failed/ambiguous/unconfirmed mutation, do not blindly replay; set exact-row interaction blocked/unconfirmed, keep prior cache stale/unconfirmed, stop live, block Local Refresh, auxiliary network actions, further mutations, and every other row network lifecycle, and require top full Refresh as the only recovery path.
- [x] 5.6 On confirmed reconciliation, atomically replace exact-row cache and restore eligible controls/live only after cleanup/currentness checks.

## 6. Top controls, context invalidation, and room summary

- [x] 6.1 Invalidate and clear current room/live/pending-start state immediately when source IP is edited during permitted post-cycle idle/live state; do not start I/O until a new Enter/top Refresh.
- [x] 6.2 Keep Password source-IP/model-wide only; Cancel and Save-without-effective-change are no-ops, while a real credential-chain change clears current room context and sessions.
- [x] 6.3 Preserve top full Refresh as the room-wide recovery action, require it to remain available during auxiliary read as global supersession, and keep it blocked during Local Refresh or confirmed mutation/reconciliation until their required terminal boundaries.
- [x] 6.4 Keep `Последнее обновление` equal to the last full room-cycle completion; post-cycle operations must not rewrite it.
- [x] 6.5 For typed post-cycle connection loss, terminal Local Refresh failure, cleanup abandonment, and failed/ambiguous/unconfirmed mutation, set the global bottom status to `Есть проблемы с соединением`; ordinary auxiliary parse/business failure without connection degradation must not set that status, and successful local actions must not erase unresolved room problems.

## 7. Remove legacy PDU related-codec enrichment

- [x] 7.1 Remove the dedicated PDU room/related-codec resolver/controller/session lane and all accepted-refresh side effects that start codec work.
- [x] 7.2 Remove duplicated PDU room/VIP/related-codec presentation and the PDU-hosted CloudLink microphone meter.
- [x] 7.3 Preserve PDU own diagnostic data, outlet/control behavior, mutation/reconciliation behavior, and room-tree PDU row rendering.
- [x] 7.4 Remove or update tests/runbook references that treat PDU enrichment as current authority; do not update legacy Graphify artifacts.

## 8. Cleanup and shutdown

- [x] 8.1 Keep all room interactive device I/O and cleanup, including mutation/reconciliation network work, off the Qt GUI thread.
- [x] 8.2 Implement bounded read-only cleanup/abandonment so stale contexts cannot hold future full Refresh forever; cleanup abandonment must set the global problem status.
- [x] 8.3 Close read-only activity without a warning dialog; invalidate generations immediately and perform best-effort background cleanup.
- [x] 8.4 Warn on application close only when a confirmed state-changing operation may have been sent; on confirmed close perform no retry or rollback.

## 9. Regression coverage

- [x] 9.1 Add focused exact-row/same-model, CloudLink/Matrix/DMP production-composition live-handoff, stale callback, and cleanup-timeout tests.
- [x] 9.2 Add cross-type serialization tests proving `LIVE / LOCAL_REFRESH / AUXILIARY_READ / MUTATION / RECONCILIATION` cannot overlap or concurrently acquire/await device network resources, including mutation no-send before cleanup and after cleanup timeout.
- [x] 9.3 Add Local Refresh lock-matrix tests for source IP, Password, top Refresh, accordion, auxiliary, mutation, repeated refresh, and pure-local Debug behavior.
- [x] 9.4 Add auxiliary lock-matrix tests proving source IP/Password/Local Refresh/mutations/other auxiliary actions are blocked while top full Refresh and accordion cancellation remain available.
- [x] 9.5 Add mutation/reconciliation tests proving failed/ambiguous/unconfirmed mutation blocks live, Local Refresh, auxiliary and further mutation until top full Refresh.
- [x] 9.6 Add registry tests proving all room interactive capability availability comes from the one exact model registration and no parallel model tables are required.
- [x] 9.7 Add room-summary tests proving agreed post-cycle degradation categories set `Есть проблемы с соединением`, while ordinary auxiliary parse/business failure does not.
- [x] 9.8 Add Call Log/auxiliary tests for direct child-window `X` cancellation, late-callback suppression, bounded cleanup, eligible live resume, and fresh acquisition on reopen; also cover Debug, source-IP/credential invalidation, per-record degradation, and exact-row currentness.
- [x] 9.9 Add removal tests proving PDU refresh no longer starts related-codec I/O/presentation while PDU own controls remain functional.
- [x] 9.10 Run affected model/controller/screen regression suites and the full offline test suite.
- [x] 9.11 Run `git diff --check` and `git diff --cached --check` before the implementation commit.

## 10. OpenSpec and workflow gates

- [x] 10.1 Run `./openspec.cmd validate room-device-interaction-lifecycle --strict` during architecture and implementation work.
- [x] 10.2 Independent architectural review approved the architecture at `ebc96586868d80af86a7178623e1d6ee100c3260` before production implementation.
- [x] 10.3 Implementation session adds focused regression coverage, runs strict validation and required tests, creates a focused commit, and pushes the feature branch without self-approving.
- [ ] 10.4 Independent validation runs in a clean detached worktree from the current published remote feature HEAD and re-runs all required checks without fixing its own findings.
- [ ] 10.5 Because this change removes requirements from `pdu-room-codec-enrichment`, independent validation performs the required disposable archive-applicability check before `READY FOR ARCHIVE`.
- [ ] 10.6 Archive only after a permitting independent verdict; then run `./openspec.cmd validate --all --strict`, full offline tests, Git diff checks, review archive/root-spec diff, create/push the dedicated archive commit, and stop before merge unless the user explicitly authorizes it.
