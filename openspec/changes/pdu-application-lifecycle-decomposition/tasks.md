## 1. Reconfirm current PDU contracts

- [ ] 1.1 Reconfirm the implementation branch is based on the current published `master` containing both `worker-module-decomposition` and `matrix-operation-lifecycle-decomposition`.
- [ ] 1.2 Inventory all PDU-specific lifecycle state and methods still owned by `gui/main_window.py`, including context revision, operation identity, refresh dispatch, individual mutation, bulk mutation, worker binding, credential-attempt coordination, stale acceptance, busy state, and mutation reconciliation.
- [ ] 1.3 Inventory `gui/screens/pdu_screen.py` parent-method coupling and distinguish view-only helpers from application orchestration responsibilities.
- [ ] 1.4 Reconfirm the canonical PDU worker boundary in `core/workers/pdu.py` and compatibility exports through `core/worker.py`.
- [ ] 1.5 Reconfirm `core/pdu.py` operation descriptors, capability gates, individual mutation safety policy, sequential bulk contract, stale checks, and handler factory ownership.
- [ ] 1.6 Reconfirm Aten and PCS4i handler protocol/credential semantics before refactoring lifecycle ownership.
- [ ] 1.7 Record the current PDU credential fallback and successful-index persistence gates so structural extraction cannot broaden them.

## 2. Add the PDU-specific controller boundary

- [ ] 2.1 Add a focused PDU application controller near the GUI composition boundary, preferably `gui/pdu_controller.py` with class name `PDUController` if no stronger local naming constraint appears during implementation.
- [ ] 2.2 Keep the controller PDU-specific and do not introduce a generic `OperationManager`, `DeviceController`, `RequestManager`, or shared Matrix/PDU/DMP/codec lifecycle manager.
- [ ] 2.3 Define or evolve an immutable non-secret PDU operation context containing model, IP, operation kind, PDU context generation, unique operation ID, credential-context revision, assigned credential index when applicable, outlet or bulk identity, and expected worker/background-operation identity when applicable.
- [ ] 2.4 Ensure credential values, candidate dictionaries, profile secrets, cookies, tokens, and handler/session objects never appear in public PDU context or controller signal payloads.
- [ ] 2.5 Move authoritative PDU context generation/invalidation and PDU operation identity generation out of `VCSDiagnosticApp` into the controller.
- [ ] 2.6 Invalidate PDU controller context on relevant model, IP, credential-context revision, screen lifecycle, and application shutdown changes.

## 3. Replace PDUScreen parent-method orchestration with explicit intents

- [ ] 3.1 Add an explicit non-secret refresh intent boundary from `PDUScreen` to `PDUController`.
- [ ] 3.2 Route individual outlet intents through an explicit signal/callback boundary instead of `self.parent.control_pdu_outlet(...)`.
- [ ] 3.3 Route bulk ON/OFF intents through an explicit signal/callback boundary instead of `self.parent.control_pdu_outlets_bulk(...)`.
- [ ] 3.4 Remove PDU lifecycle dependence on `PDUScreen.refresh()` calling arbitrary parent `refresh_data()` orchestration.
- [ ] 3.5 Keep confirmation dialogs, table rendering, capability rendering, and focused button/presentation helpers in `PDUScreen` where they remain view responsibilities.
- [ ] 3.6 Add focused tests proving `PDUScreen` does not acquire handlers, create workers, read credential candidates/indexes, perform PDU network I/O, or decide stale-operation authority.
- [ ] 3.7 Add focused tests proving PDU intent payloads contain no credential values, candidate lists, handler/session objects, cookies, tokens, or transport objects.

## 4. Move PDU refresh lifecycle into the controller

- [ ] 4.1 Move PDU refresh descriptor/context creation, worker construction/submission, and PDU-specific signal binding out of `VCSDiagnosticApp` into `PDUController`.
- [ ] 4.2 Keep refresh execution on the existing `PDUOperationWorker`/background boundary rather than moving handler calls into controller methods.
- [ ] 4.3 Bind refresh result, error, progress, status, and finished callbacks to immutable controller context and expected worker identity.
- [ ] 4.4 Discard stale queued refresh operations before handler acquisition/network I/O through the existing application-owned non-GUI currentness mechanism supplied to the worker/core boundary.
- [ ] 4.5 Preserve current structured refresh credential fallback behavior and candidate exhaustion without introducing string-based authentication classification.
- [ ] 4.6 Preserve current final-success credential persistence gates, including PCS4i credential-used semantics.

## 5. Move individual outlet mutation lifecycle into the controller

- [ ] 5.1 Move individual PDU mutation descriptor construction, worker submission, signal binding, and terminal handling out of `VCSDiagnosticApp`.
- [ ] 5.2 Preserve the existing structured distinction between safe pre-send failure, confirmed command rejection, ambiguous/unknown outcome, and stale operation.
- [ ] 5.3 Preserve the rule that state-changing mutation is never blindly replayed after the command was sent, may have been delivered, or has an ambiguous outcome.
- [ ] 5.4 Permit credential fallback only through application-owned policy after structured confirmed authentication rejection and structured evidence that no state-changing send was attempted or could have been delivered.
- [ ] 5.5 Preserve model-specific behavior, including PCS4i password-only/credentialless rules and existing Aten command semantics.
- [ ] 5.6 Make individual mutation busy/control state authoritative in the controller and scoped to immutable operation/context identity.
- [ ] 5.7 Bind post-mutation reconciliation to the originating immutable PDU context rather than refreshing whichever device is currently selected when a callback arrives.

## 6. Move sequential bulk mutation lifecycle into the controller

- [ ] 6.1 Move bulk operation identity, descriptor creation, worker submission, retry gating, signal binding, and terminal handling out of `VCSDiagnosticApp`.
- [ ] 6.2 Preserve immutable outlet-sequence capture from current records and reject missing, malformed, or duplicate outlet identities before state-changing network I/O.
- [ ] 6.3 Preserve one assigned credential for the entire bulk attempt and prohibit worker/handler candidate iteration.
- [ ] 6.4 Preserve sequential execution, existing inter-outlet delay, fail-fast behavior, partial terminal results, no rollback, and no replay of completed outlets.
- [ ] 6.5 Preserve the rule that an empty `successful_outlets` list is not evidence that credential fallback is safe.
- [ ] 6.6 Preserve the prohibition on restarting the bulk sequence with another credential after mutation began or may have begun.
- [ ] 6.7 Preserve successful credential persistence only after full accepted success with a credential actually used according to the existing contract; partial, failed, ambiguous, or stale bulk outcomes must not persist success.
- [ ] 6.8 Scope bulk busy/control state to the controller-owned current operation context so stale completion cannot unlock or relock a newer context.
- [ ] 6.9 Bind bulk completion/partial-result reconciliation to the originating context and suppress it after context change.

## 7. Preserve application-owned credential policy

- [ ] 7.1 Inject focused application-owned callbacks/providers for resolved ordered PDU candidates, valid starting index, request-scoped fallback advancement, successful-index commit, and non-secret credential-context revision.
- [ ] 7.2 Keep credential provider reads, candidate resolution, successful-index storage, and fallback authority outside `PDUController`.
- [ ] 7.3 Ensure the controller never infers credential fallback from `auth`, `401`, `403`, user-facing text, exception-message substrings, empty success lists, or absence of success.
- [ ] 7.4 Ensure each `PDUOperationWorker` and handler receives only one assigned credential for one attempt.
- [ ] 7.5 Preserve transport fallback and credential fallback as separate mechanisms using the same assigned credential across one transport-attempt sequence.
- [ ] 7.6 Preserve PCS4i credentialless composition, no invented username, `CredentialRequired` semantics, and no successful-index commit for an unused credential.

## 8. Move stale/currentness authority into the controller

- [ ] 8.1 Add one controller-owned currentness predicate that includes PDU generation, model, IP, operation ID, credential-context revision, assigned candidate index when applicable, and expected worker/background identity when applicable.
- [ ] 8.2 Suppress stale refresh result, error, progress/status, and finished callbacks.
- [ ] 8.3 Suppress stale individual mutation result, error, progress/status, and finished callbacks.
- [ ] 8.4 Suppress stale bulk result/partial-result, error, progress/status, and finished callbacks.
- [ ] 8.5 Ensure stale callbacks cannot update `PDUScreen`, update outlet data, save credential memory, advance fallback, start a retry, alter current busy state, alter global refresh state, or show an old operation outcome as current.
- [ ] 8.6 Ensure stale mutation completion cannot start refresh/reconciliation for a newer model/IP/context.
- [ ] 8.7 Ensure stale finished from an old operation cannot unlock controls owned by a newer individual or bulk mutation.
- [ ] 8.8 Ensure background currentness checks never read Qt widgets as authoritative operation state.

## 9. Reduce MainWindow to PDU composition responsibilities

- [ ] 9.1 Create and wire `PDUController` from `VCSDiagnosticApp` alongside `PDUScreen`.
- [ ] 9.2 Wire screen intents to controller operations and accepted controller outputs to the screen/global shell.
- [ ] 9.3 Route model/IP/credential-context changes into controller invalidation without leaving duplicate PDU generation authority in `VCSDiagnosticApp`.
- [ ] 9.4 Delegate application shutdown/invalidation to the controller while keeping blocking network cleanup off the Qt GUI thread.
- [ ] 9.5 Remove obsolete PDU-specific operation state machines, worker binding, context generation, stale callback handlers, mutation/bulk orchestration, and PDU-specific reconciliation logic from `gui/main_window.py`.
- [ ] 9.6 Preserve unrelated codec, Matrix, DMP, SIP, generic shell, and generic credential responsibilities.

## 10. Focused regression coverage

- [ ] 10.1 Add focused tests proving PDU refresh, individual mutation, bulk mutation, and reconciliation network I/O remain outside the Qt GUI thread.
- [ ] 10.2 Add tests proving stale queued PDU operations are rejected before handler acquisition/network I/O.
- [ ] 10.3 Add tests for stale refresh result/error/progress/status/finished after model, IP, or credential-context change.
- [ ] 10.4 Add tests for stale individual mutation result/error/progress/status/finished and stale reconciliation.
- [ ] 10.5 Add tests for stale bulk result/partial-result/error/progress/status/finished and stale reconciliation.
- [ ] 10.6 Add tests proving stale callbacks cannot save a credential, advance fallback, alter current busy state, unlock newer controls, or change global refresh state.
- [ ] 10.7 Add tests proving individual ambiguous post-send outcomes are not replayed and do not authorize credential fallback.
- [ ] 10.8 Add tests proving bulk mutation never restarts after possible send, never replays completed outlets, and does not treat an empty successful-outlet list as fallback authority.
- [ ] 10.9 Add tests proving successful credential memory is committed only at existing accepted PDU success gates and never from stale/partial/failed outcomes.
- [ ] 10.10 Add PCS4i regression tests for password-only candidate normalization, credentialless operation, `CredentialRequired`, unused-credential success, HTTP enrichment failure, and no invented username.
- [ ] 10.11 Add Aten regression tests proving refresh, ON/OFF/REBOOT, and bulk ON/OFF retain existing behavior.
- [ ] 10.12 Add `PDUScreen` regression tests for rendering, confirmation dialogs, dynamic outlet count, capability-driven controls, and explicit intent wiring.

## 11. Validation

- [ ] 11.1 Run focused PDU controller, PDU core/worker, GUI composition, Aten, and PCS4i regression tests.
- [ ] 11.2 Run `python -m unittest discover -s tests -p "test_*.py"`.
- [ ] 11.3 Run `.\openspec.cmd validate pdu-application-lifecycle-decomposition --strict` using only the repository-local wrapper.
- [ ] 11.4 Run `.\openspec.cmd validate --all --strict` using only the repository-local wrapper.
- [ ] 11.5 Run `git diff --check`.
- [ ] 11.6 Confirm production behavior, protocol commands, handler transport semantics, bulk sequencing semantics, credential fallback semantics, PCS4i credentialless semantics, and unrelated device lifecycles remain unchanged except for the approved structural ownership move.
