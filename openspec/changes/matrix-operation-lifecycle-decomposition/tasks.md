## 1. Inventory and current contracts

- [ ] 1.1 Reconfirm branch starts from current `origin/master` after `worker-module-decomposition`.
- [ ] 1.2 Inventory Matrix imports and responsibilities in `gui/main_window.py`.
- [ ] 1.3 Inventory direct handler/session/network calls in `gui/screens/matrix_screen.py`.
- [ ] 1.4 Inventory canonical Matrix worker behavior in `core/workers/matrix.py` and facade import compatibility through `core/worker.py`.
- [ ] 1.5 Inventory `handlers/extron/in1804.py` command/session methods used by refresh, route mutation, quick refresh, and keepalive.
- [ ] 1.6 Inventory `ExtronIN1804DataParser` GUI data shape and existing Matrix rendering tests.
- [ ] 1.7 Record existing Matrix credential fallback and successful credential memory behavior before implementation.

## 2. Controller/application boundary

- [ ] 2.1 Add a Matrix-specific controller/application component with a single clear ownership reason.
- [ ] 2.2 Define immutable Matrix operation context with model, IP, operation kind, generation/request ID, expected worker/operation identity, and non-secret credential context.
- [ ] 2.3 Move Matrix persistent handler/session fields and keepalive ownership out of `VCSDiagnosticApp` into the Matrix controller or replace persistence with an explicitly justified per-operation policy.
- [ ] 2.4 Keep credential candidate resolution, fallback, and successful-index memory connected to the existing application-owned credential policy.
- [ ] 2.5 Keep the controller Matrix-specific; do not introduce shared PDU/DMP/Codec orchestration.

## 3. MatrixScreen intent boundary

- [ ] 3.1 Replace direct route handler calls in `MatrixScreen` with non-secret route intent emission/callbacks.
- [ ] 3.2 Replace direct quick status refresh handler calls in `MatrixScreen` with controller-owned refresh/status intent.
- [ ] 3.3 Remove `MatrixScreen` ownership of credential lists, credential indexes, handler objects, and session objects.
- [ ] 3.4 Preserve Matrix table rendering, selected route display, device info display, and existing visual behavior.
- [ ] 3.5 Add focused tests proving `MatrixScreen` does not perform handler/network calls directly.

## 4. Background route lifecycle

- [ ] 4.1 Add a background execution path for Matrix route mutation.
- [ ] 4.2 Ensure handler/session acquisition for route mutation happens off the Qt GUI thread.
- [ ] 4.3 Classify route mutation as state-changing and prevent blind replay after ambiguous delivery.
- [ ] 4.4 Permit credential fallback only before any possible route command send and only after structured confirmed authentication failure.
- [ ] 4.5 Emit structured route result/error/finished callbacks carrying Matrix context identity.

## 5. Refresh lifecycle

- [ ] 5.1 Keep initial Matrix refresh on the existing focused worker/background boundary.
- [ ] 5.2 Bind Matrix refresh callbacks to Matrix controller context rather than widget state.
- [ ] 5.3 Add quick/status refresh after successful route mutation as a read-only background operation.
- [ ] 5.4 Bind refresh-after-mutation to the original Matrix context and drop it if the context changes.
- [ ] 5.5 Preserve terminal/status redaction and current user-visible refresh behavior.

## 6. Session/context ownership

- [ ] 6.1 Define persistent handler reuse predicate: model, IP, credential identity/index, protocol/port, and local connected state must match.
- [ ] 6.2 Prevent cross-context session reuse after model, IP, credential change/fallback, explicit reconnect, session failure, screen destruction, or application close.
- [ ] 6.3 Serialize access to one persistent Matrix handler unless implementation proves safe concurrent use.
- [ ] 6.4 Run blocking session creation, keepalive/liveness checks, and cleanup on the owning background lane.
- [ ] 6.5 Make cleanup idempotent and stale-safe.

## 7. Stale callback coverage

- [ ] 7.1 Add tests where stale Matrix result arrives after model/IP/context change.
- [ ] 7.2 Add tests where stale Matrix error arrives after model/IP/context change.
- [ ] 7.3 Add tests where stale Matrix finished arrives while a newer Matrix operation is active.
- [ ] 7.4 Add tests where stale Matrix progress/status/terminal events cannot update the newer context.
- [ ] 7.5 Add tests where stale route follow-up refresh cannot update a newer Matrix context.
- [ ] 7.6 Add tests where stale callbacks cannot save credential memory or reset handler/session ownership for the newer context.

## 8. Regression tests

- [ ] 8.1 Add focused tests proving Matrix route mutation does not execute in the GUI thread.
- [ ] 8.2 Add focused tests proving Matrix refresh and quick/status refresh do not execute in the GUI thread.
- [ ] 8.3 Add focused tests for application-owned Matrix credential fallback and no handler/worker candidate iteration.
- [ ] 8.4 Add focused tests for no cross-context session reuse.
- [ ] 8.5 Add regression tests for existing Matrix rendering and successful route behavior.
- [ ] 8.6 Run the relevant existing Matrix, worker, credential, and GUI tests.

## 9. Validation

- [ ] 9.1 Run focused regression tests added or affected by the Matrix lifecycle extraction.
- [ ] 9.2 Run `python -m unittest discover -s tests -p "test_*.py"` unless the implementation session documents why production/tests were untouched.
- [ ] 9.3 Run `.\openspec.cmd validate matrix-operation-lifecycle-decomposition --strict`.
- [ ] 9.4 Run `.\openspec.cmd validate --all --strict`.
- [ ] 9.5 Run `git diff --check`.
- [ ] 9.6 Confirm no unrelated PDU, DMP, codec, SIP, generic credential, worker facade, or handler protocol behavior changed.
