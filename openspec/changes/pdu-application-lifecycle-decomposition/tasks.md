## 1. Reconfirm current PDU contracts

- [x] 1.1 Reconfirm the implementation branch is based on the current published `master` containing both `worker-module-decomposition` and `matrix-operation-lifecycle-decomposition`.
- [x] 1.2 Inventory all PDU-specific lifecycle state and methods still owned by `gui/main_window.py`, including context revision, operation identity, refresh dispatch, individual mutation, bulk mutation, worker binding, credential-attempt coordination, stale acceptance, busy state, and mutation reconciliation.
- [x] 1.3 Inventory `gui/screens/pdu_screen.py` parent-method coupling and distinguish view-only helpers from application orchestration responsibilities.
- [x] 1.4 Reconfirm the canonical PDU worker boundary in `core/workers/pdu.py` and compatibility exports through `core/worker.py`.
- [x] 1.5 Reconfirm `core/pdu.py` operation descriptors, capability gates, individual mutation safety policy, sequential bulk contract, stale checks, and handler factory ownership.
- [x] 1.6 Reconfirm Aten and PCS4i handler protocol/credential semantics before refactoring lifecycle ownership.
- [x] 1.7 Record the current PDU credential fallback and successful-index persistence gates so structural extraction cannot broaden them.

## 2. Add the PDU-specific controller boundary

- [x] 2.1 Add a focused PDU application controller near the GUI composition boundary, preferably `gui/pdu_controller.py` with class name `PDUController` if no stronger local naming constraint appears during implementation.
- [x] 2.2 Keep the controller PDU-specific and do not introduce a generic `OperationManager`, `DeviceController`, `RequestManager`, or shared Matrix/PDU/DMP/codec lifecycle manager.
- [x] 2.3 Define or evolve an immutable non-secret common PDU context containing PDU context generation, model, IP, and credential-context revision.
- [x] 2.4 Ensure credential values, candidate dictionaries, profile secrets, cookies, tokens, and handler/session objects never appear in public PDU context or controller signal payloads.
- [x] 2.5 Move authoritative PDU context generation/invalidation and PDU operation identity generation out of `VCSDiagnosticApp` into the controller.
- [x] 2.6 Invalidate PDU controller context on relevant model, IP, credential-context revision, screen lifecycle, and application shutdown changes.

## 3. Define independent PDU operation authority lanes

- [x] 3.1 Add a refresh lane with its own current refresh/reconciliation operation identity and expected refresh worker identity.
- [x] 3.2 Route user refresh, normal status refresh, and mutation reconciliation refresh through the refresh lane.
- [x] 3.3 Add a mutation lane with its own current mutation operation identity, mutation kind, and expected mutation worker identity.
- [x] 3.4 Route individual outlet mutation and sequential bulk mutation through the mutation lane.
- [x] 3.5 Ensure individual and bulk mutations are mutually exclusive in one current PDU context.
- [x] 3.6 Ensure starting a refresh does not replace current mutation operation identity, does not clear mutation busy state, and does not make mutation result/error/finished stale merely because refresh started.
- [x] 3.7 Ensure mutation lifecycle does not use refresh operation identity as its freshness authority and mutation completion cannot finalize or clear a newer unrelated refresh lifecycle.
- [x] 3.8 Add a state epoch, refresh submission sequence, explicit refresh-lane supersession, or equivalent mechanism so a refresh snapshot submitted before a later mutation cannot be accepted as authoritative state after that mutation starts.
- [x] 3.9 Define reconciliation as a refresh-lane operation carrying its own refresh identity, expected worker identity, and originating mutation operation identity.

## 4. Replace PDUScreen parent-method orchestration with explicit intents

- [x] 4.1 Add an explicit non-secret refresh intent boundary from `PDUScreen` to `PDUController`.
- [x] 4.2 Route individual outlet intents through an explicit signal/callback boundary instead of `self.parent.control_pdu_outlet(...)`.
- [x] 4.3 Route bulk ON/OFF intents through an explicit signal/callback boundary instead of `self.parent.control_pdu_outlets_bulk(...)`.
- [x] 4.4 Remove PDU lifecycle dependence on `PDUScreen.refresh()` calling arbitrary parent `refresh_data()` orchestration.
- [x] 4.5 Keep confirmation dialogs, table rendering, capability rendering, and focused button/presentation helpers in `PDUScreen` where they remain view responsibilities.
- [x] 4.6 Add focused tests proving `PDUScreen` does not acquire handlers, create workers, read credential candidates/indexes, perform PDU network I/O, or decide stale-operation authority.
- [x] 4.7 Add focused tests proving PDU intent payloads contain no credential values, candidate lists, handler/session objects, cookies, tokens, or transport objects.

## 5. Move PDU refresh lifecycle into the controller

- [x] 5.1 Move PDU refresh descriptor/context creation, worker construction/submission, and PDU-specific signal binding out of `VCSDiagnosticApp` into `PDUController`.
- [x] 5.2 Keep refresh execution on the existing `PDUOperationWorker`/background boundary rather than moving handler calls into controller methods.
- [x] 5.3 Bind refresh result, error, progress, status, and finished callbacks to common PDU context, refresh-lane operation identity, and expected worker identity.
- [x] 5.4 Discard stale queued refresh operations before handler acquisition/network I/O through the existing application-owned non-GUI currentness mechanism supplied to the worker/core boundary.
- [x] 5.5 Preserve current structured refresh credential fallback behavior and candidate exhaustion without introducing string-based authentication classification.
- [x] 5.6 Preserve current final-success credential persistence gates, including PCS4i credential-used semantics.
- [x] 5.7 Add tests proving a refresh started while mutation A is active does not invalidate mutation A authority and does not clear mutation busy state.
- [x] 5.8 Add tests proving refresh completion cannot unlock mutation controls, clear mutation busy state, finalize mutation, or invalidate current mutation worker identity.
- [x] 5.9 Add tests proving refresh A submitted before mutation B cannot overwrite authoritative PDU data when A completes after B started.

## 6. Move individual outlet mutation lifecycle into the controller

- [x] 6.1 Move individual PDU mutation descriptor construction, worker submission, signal binding, and terminal handling out of `VCSDiagnosticApp`.
- [x] 6.2 Preserve the existing structured distinction between safe pre-send failure, confirmed command rejection, ambiguous/unknown outcome, and stale operation.
- [x] 6.3 Preserve the rule that state-changing mutation is never blindly replayed after the command was sent, may have been delivered, or has an ambiguous outcome.
- [x] 6.4 Permit credential fallback only through application-owned policy after structured confirmed authentication rejection and structured evidence that no state-changing send was attempted or could have been delivered.
- [x] 6.5 Preserve model-specific behavior, including PCS4i password-only/credentialless rules and existing Aten command semantics.
- [x] 6.6 Make individual mutation busy/control state authoritative in the mutation lane and scoped to immutable operation/context identity.
- [x] 6.7 Bind post-mutation reconciliation to the originating immutable PDU context and originating mutation operation identity rather than refreshing whichever device is currently selected when a callback arrives.
- [x] 6.8 Add tests proving individual mutation active followed by bulk mutation request rejects the conflicting bulk mutation before worker creation/network I/O.
- [x] 6.9 Add tests proving stale individual mutation finished cannot clear busy state owned by a newer mutation.

## 7. Move sequential bulk mutation lifecycle into the controller

- [x] 7.1 Move bulk operation identity, descriptor creation, worker submission, retry gating, signal binding, and terminal handling out of `VCSDiagnosticApp`.
- [x] 7.2 Preserve immutable outlet-sequence capture from current records and reject missing, malformed, or duplicate outlet identities before state-changing network I/O.
- [x] 7.3 Preserve one assigned credential for the entire bulk attempt and prohibit worker/handler candidate iteration.
- [x] 7.4 Preserve sequential execution, existing inter-outlet delay, fail-fast behavior, partial terminal results, no rollback, and no replay of completed outlets.
- [x] 7.5 Preserve the rule that an empty `successful_outlets` list is not evidence that credential fallback is safe.
- [x] 7.6 Preserve the prohibition on restarting the bulk sequence with another credential after mutation began or may have begun.
- [x] 7.7 Preserve successful credential persistence only after full accepted success with a credential actually used according to the existing contract; partial, failed, ambiguous, or stale bulk outcomes must not persist success.
- [x] 7.8 Scope bulk busy/control state to the mutation lane's current operation context so stale completion cannot unlock or relock a newer context.
- [x] 7.9 Bind bulk completion/partial-result reconciliation to the originating context and suppress it after context change.
- [x] 7.10 Ensure `core/workers/pdu.py` / `core.pdu` receive thread-safe currentness authority from `PDUController` and do not read Qt widgets for bulk stale checks.
- [x] 7.11 Re-check currentness before every next state-changing outlet sub-operation and stop before the next send when the supplied predicate becomes false.
- [x] 7.12 Add deterministic mid-bulk stale test with bulk sequence `[1, 2, 3]`: outlet 1 completes, context invalidates, currentness returns false before outlet 2 send, outlet 1 send count is 1, outlet 2 and 3 send counts are 0, no credential retry occurs, no successful credential is committed, and no reconciliation for the new context starts.
- [x] 7.13 Add tests proving bulk mutation active followed by individual mutation request rejects the conflicting individual mutation before worker creation/network I/O.

## 8. Preserve application-owned credential policy

- [x] 8.1 Inject focused application-owned callbacks/providers for resolved ordered PDU candidates, valid starting index, request-scoped fallback advancement, successful-index commit, and non-secret credential-context revision.
- [x] 8.2 Keep credential provider reads, candidate resolution, successful-index storage, and fallback authority outside `PDUController`.
- [x] 8.3 Ensure the controller never infers credential fallback from `auth`, `401`, `403`, user-facing text, exception-message substrings, empty success lists, or absence of success.
- [x] 8.4 Ensure each `PDUOperationWorker` and handler receives only one assigned credential for one attempt.
- [x] 8.5 Preserve transport fallback and credential fallback as separate mechanisms using the same assigned credential across one transport-attempt sequence.
- [x] 8.6 Preserve PCS4i credentialless composition, no invented username, `CredentialRequired` semantics, and no successful-index commit for an unused credential.
- [x] 8.7 Implement the explicit credential eligibility matrix for refresh, Aten individual mutation, PCS4i individual mutation, Aten bulk, and PCS4i bulk.
- [x] 8.8 Add tests proving Aten individual authentication-looking or structured failure does not introduce new credential fallback unless the pre-change contract explicitly allowed it.
- [x] 8.9 Add tests proving successful Aten individual mutation does not newly persist credential index because of this structural extraction.
- [x] 8.10 Add tests proving PCS4i individual confirmed rejection before possible command send preserves existing application-owned fallback allowance, while possible command send prevents fallback.
- [x] 8.11 Add tests proving Aten bulk confirmed authentication failure with zero sends preserves existing bulk fallback allowance and full accepted success preserves existing successful credential persistence.
- [x] 8.12 Add tests proving PCS4i bulk full success with credential used may commit, while full passwordless or assigned-but-unused success does not commit.

## 9. Move stale/currentness authority into the controller

- [x] 9.1 Add one controller-owned common PDU context currentness predicate that includes generation, model, IP, and credential-context revision.
- [x] 9.2 Add refresh-lane currentness checks that additionally include refresh/reconciliation operation identity and expected refresh worker identity.
- [x] 9.3 Add mutation-lane currentness checks that additionally include mutation operation identity, mutation kind, and expected mutation worker identity.
- [x] 9.4 Suppress stale refresh result, error, progress/status, and finished callbacks.
- [x] 9.5 Suppress stale individual mutation result, error, progress/status, and finished callbacks.
- [x] 9.6 Suppress stale bulk result/partial-result, error, progress/status, and finished callbacks.
- [x] 9.7 Ensure stale callbacks cannot update `PDUScreen`, update outlet data, save credential memory, advance fallback, start a retry, alter current busy state, alter global refresh state, or show an old operation outcome as current.
- [x] 9.8 Ensure stale mutation completion cannot start refresh/reconciliation for a newer model/IP/context.
- [x] 9.9 Ensure stale finished from an old operation cannot unlock controls owned by a newer individual or bulk mutation.
- [x] 9.10 Ensure background currentness checks never read Qt widgets as authoritative operation state.
- [x] 9.11 Add tests proving reconciliation R originating from mutation A cannot update a new context after model/IP/credential-context/generation change.
- [x] 9.12 Add tests proving stale mutation A cannot launch reconciliation while newer mutation B is active.
- [x] 9.13 Add tests proving reconciliation does not become mutation owner and cannot clear busy state for a different mutation.

## 10. Reduce MainWindow to PDU composition responsibilities

- [x] 10.1 Create and wire `PDUController` from `VCSDiagnosticApp` alongside `PDUScreen`.
- [x] 10.2 Wire screen intents to controller operations and accepted controller outputs to the screen/global shell.
- [x] 10.3 Route model/IP/credential-context changes into controller invalidation without leaving duplicate PDU generation authority in `VCSDiagnosticApp`.
- [x] 10.4 Delegate application shutdown/invalidation to the controller while keeping blocking network cleanup off the Qt GUI thread.
- [x] 10.5 Remove obsolete PDU-specific operation state machines, worker binding, context generation, stale callback handlers, mutation/bulk orchestration, and PDU-specific reconciliation logic from `gui/main_window.py`.
- [x] 10.6 Preserve unrelated codec, Matrix, DMP, SIP, generic shell, and generic credential responsibilities.

## 11. Focused regression coverage

- [x] 11.1 Add focused tests proving PDU refresh, individual mutation, bulk mutation, and reconciliation network I/O remain outside the Qt GUI thread.
- [x] 11.2 Add tests proving stale queued PDU operations are rejected before handler acquisition/network I/O.
- [x] 11.3 Add tests for stale refresh result/error/progress/status/finished after model, IP, or credential-context change.
- [x] 11.4 Add tests for stale individual mutation result/error/progress/status/finished and stale reconciliation.
- [x] 11.5 Add tests for stale bulk result/partial-result/error/progress/status/finished and stale reconciliation.
- [x] 11.6 Add tests proving stale callbacks cannot save a credential, advance fallback, alter current busy state, unlock newer controls, or change global refresh state.
- [x] 11.7 Add tests proving individual ambiguous post-send outcomes are not replayed and do not authorize credential fallback.
- [x] 11.8 Add tests proving bulk mutation never restarts after possible send, never replays completed outlets, and does not treat an empty successful-outlet list as fallback authority.
- [x] 11.9 Add tests proving successful credential memory is committed only at the explicit PDU eligibility matrix gates and never from stale/partial/failed outcomes.
- [x] 11.10 Add PCS4i regression tests for password-only candidate normalization, credentialless operation, `CredentialRequired`, unused-credential success, HTTP enrichment failure, and no invented username.
- [x] 11.11 Add Aten regression tests proving refresh, ON/OFF/REBOOT, and bulk ON/OFF retain existing behavior.
- [x] 11.12 Add `PDUScreen` regression tests for rendering, confirmation dialogs, dynamic outlet count, capability-driven controls, and explicit intent wiring.

## 12. Validation

- [x] 12.1 Run focused PDU controller, PDU core/worker, GUI composition, Aten, and PCS4i regression tests.
- [x] 12.2 Run `python -m unittest discover -s tests -p "test_*.py"`.
- [x] 12.3 Run `.\openspec.cmd validate pdu-application-lifecycle-decomposition --strict` using only the repository-local wrapper.
- [x] 12.4 Run `.\openspec.cmd validate --all --strict` using only the repository-local wrapper.
- [x] 12.5 Run `git diff --check`.
- [x] 12.6 Confirm production behavior, protocol commands, handler transport semantics, bulk sequencing semantics, credential fallback semantics, PCS4i credentialless semantics, authority lane semantics, and unrelated device lifecycles remain unchanged except for the approved structural ownership move.
