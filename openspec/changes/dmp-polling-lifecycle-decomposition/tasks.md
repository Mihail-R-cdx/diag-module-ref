## 1. Reconfirm current DMP contracts

- [ ] 1.1 Reconfirm implementation branch is based on current published `master` containing `worker-module-decomposition`, `matrix-operation-lifecycle-decomposition`, and `pdu-application-lifecycle-decomposition`.
- [ ] 1.2 Inventory all DMP-specific lifecycle state and methods still owned by `gui/main_window.py`.
- [ ] 1.3 Reconfirm `core/workers/dmp.py` is the canonical long-lived DMP worker boundary and `core/worker.py` is compatibility-only.
- [ ] 1.4 Reconfirm current DMP protocol, transaction, timeout, cancellation, recovery, and cleanup contracts before refactoring lifecycle ownership.
- [ ] 1.5 Reproduce and document the current credential-context invalidation gap: DMP credential configuration change does not invalidate an active polling context.

## 2. Add the DMP-specific polling controller

- [ ] 2.1 Add a focused application controller, preferably `gui/dmp_polling_controller.py` with class `DMPPollingController`.
- [ ] 2.2 Keep the controller DMP-specific; do not introduce a generic multi-device operation/request/controller framework.
- [ ] 2.3 Define an immutable non-secret DMP polling context with generation, model, IP, generic request identity, candidate index, credential-context revision, and attempt identity as needed.
- [ ] 2.4 Keep credential values, candidate dictionaries, cancellation tokens, worker/handler/session/transport objects, cookies, and tokens out of public context/signal payloads.
- [ ] 2.5 Move authoritative DMP generation, active context, cancellation token ownership, and expected-worker authority out of `VCSDiagnosticApp` into the controller.

## 3. Route DMP refresh and worker lifecycle through the controller

- [ ] 3.1 Move DMP worker construction, one-candidate assignment, signal binding, and `QThreadPool` submission into the controller.
- [ ] 3.2 Preserve all DMP network I/O and blocking cleanup on the existing background worker boundary.
- [ ] 3.3 Route result, error, progress, status, terminal, and finished through controller acceptance before generic shell/UI handling.
- [ ] 3.4 Preserve `refresh_extron_dmp64_plus(...)` only as a narrow compatibility delegate if existing callers/tests require it.
- [ ] 3.5 Ensure explicit repeat Refresh supersedes/cancels the old polling context and starts a fresh worker with a fresh cancellation token/session.

## 4. Make DMP context invalidation complete

- [ ] 4.1 Invalidate/cancel DMP context on model change.
- [ ] 4.2 Invalidate/cancel DMP context on IP change.
- [ ] 4.3 Invalidate/cancel DMP context when leaving or superseding the DMP diagnostic context.
- [ ] 4.4 Invalidate/cancel DMP context on DMP credential configuration change even when the candidate index remains numerically unchanged.
- [ ] 4.5 Invalidate/cancel DMP context on application shutdown.
- [ ] 4.6 Remove duplicate direct DMP cancellation wiring so one controller boundary owns invalidation.
- [ ] 4.7 Ensure GUI-side invalidation only publishes cancellation and never performs blocking SSH/channel cleanup.

## 5. Move DMP stale acceptance into the controller

- [ ] 5.1 Accept callbacks only when immutable DMP context and expected worker identity match current controller authority.
- [ ] 5.2 Suppress stale result/snapshot callbacks.
- [ ] 5.3 Suppress stale error callbacks and prevent stale errors from starting fallback.
- [ ] 5.4 Suppress stale progress/status/terminal callbacks.
- [ ] 5.5 Suppress stale finished callbacks so an old worker cannot change refresh state for a newer request.
- [ ] 5.6 Remove DMP-specific stale guards such as `_dmp_callback_is_current(...)` from generic shell callbacks after controller routing is authoritative.

## 6. Preserve application-owned credential policy

- [ ] 6.1 Provide focused callbacks/providers for ordered DMP candidates, valid saved starting index, monotonic no-wrap advancement, successful-index commit, and attempt-plan cleanup as needed.
- [ ] 6.2 Keep credential provider reads and successful-index storage outside workers and handlers.
- [ ] 6.3 Allow fallback only after current structured confirmed `authentication_error`.
- [ ] 6.4 Ensure timeout, disconnect, SIS error, unsupported model, malformed data, cancellation, and other non-authentication failures do not advance credentials.
- [ ] 6.5 Do not use string heuristics such as `auth`, `401`, or `403` as fallback authority.
- [ ] 6.6 Start each fallback candidate with a fresh worker, cancellation token, and SSH/SIS session; do not reuse the failed session.
- [ ] 6.7 Remove DMP retry ownership from generic `on_device_error(...)` so only one DMP fallback authority remains.

## 7. Preserve the DMP successful-credential gate

- [ ] 7.1 Commit the assigned DMP candidate only after the first accepted complete ten-OID snapshot of the current non-stale attempt and only when the credential was actually used.
- [ ] 7.2 Do not commit after SSH login, model discovery, one OID, partial cycle, stale snapshot, cancellation, timeout, or terminal failure.
- [ ] 7.3 Ensure later continuous snapshots from the same polling session do not repeatedly persist credential success.
- [ ] 7.4 Ensure stale first complete snapshot cannot persist credential success.
- [ ] 7.5 Prevent generic `on_device_data_received(...)` from independently persisting an already controller-handled DMP candidate.

## 8. Reduce MainWindow to DMP composition responsibilities

- [ ] 8.1 Create and wire `DMPPollingController` from `VCSDiagnosticApp`.
- [ ] 8.2 Route DMP refresh dispatch to the controller after existing global input validation/generic request setup.
- [ ] 8.3 Delegate model/IP/credential-context/shutdown invalidation to the controller.
- [ ] 8.4 Remove `_dmp_context_revision`, `_dmp_cancel_token`, direct DMP context dictionaries, and direct DMP worker lifecycle ownership from `VCSDiagnosticApp` when no longer needed.
- [ ] 8.5 Remove DMP-specific retry and stale branches from generic shell callbacks.
- [ ] 8.6 Preserve unrelated codec, Matrix, PDU, SIP, Biamp, generic request, and generic credential responsibilities.

## 9. Focused regression coverage

- [ ] 9.1 Add tests for repeat Refresh replacement and fresh worker/session identity.
- [ ] 9.2 Add tests for model, IP, credential-context, and shutdown invalidation.
- [ ] 9.3 Add a regression proving credential configuration change invalidates active DMP polling even when candidate index is unchanged.
- [ ] 9.4 Add tests for stale result, error, progress, status, terminal, and finished suppression.
- [ ] 9.5 Add tests proving old finished cannot re-enable/alter controls for a newer request.
- [ ] 9.6 Add tests for structured authentication-only fallback, no-wrap exhaustion, and no fallback on non-authentication failures.
- [ ] 9.7 Add tests proving one assigned credential per worker and fresh worker/session per fallback candidate.
- [ ] 9.8 Add tests proving first accepted complete snapshot commits successful candidate exactly once.
- [ ] 9.9 Add tests proving later continuous snapshots and stale first snapshots do not persist credential success.
- [ ] 9.10 Add tests proving controller cancellation is non-blocking and worker-owned cleanup remains on the background lane.

## 10. Validation and publication

- [ ] 10.1 Run focused DMP/controller tests.
- [ ] 10.2 Run the full offline test suite.
- [ ] 10.3 Run `git diff --check`.
- [ ] 10.4 Run `./openspec.cmd validate dmp-polling-lifecycle-decomposition --strict` using the repository-local wrapper only.
- [ ] 10.5 Run `./openspec.cmd validate --all --strict` using the repository-local wrapper only.
- [ ] 10.6 Commit and push implementation before requesting independent validation.
- [ ] 10.7 Perform independent validation in a separate clean detached worktree from the exact published remote SHA according to `RULES.md`.