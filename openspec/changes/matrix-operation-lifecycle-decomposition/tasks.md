## 1. Inventory and current contracts

- [x] 1.1 Reconfirm branch starts from current `origin/master` after `worker-module-decomposition`.
- [x] 1.2 Inventory Matrix imports and responsibilities in `gui/main_window.py`.
- [x] 1.3 Inventory direct handler/session/network calls in `gui/screens/matrix_screen.py`.
- [x] 1.4 Inventory canonical Matrix worker behavior in `core/workers/matrix.py` and facade import compatibility through `core/worker.py`.
- [x] 1.5 Inventory `handlers/extron/in1804.py` command/session methods used by refresh, route mutation, quick refresh, and keepalive.
- [x] 1.6 Inventory `ExtronIN1804DataParser` GUI data shape and existing Matrix rendering tests.
- [x] 1.7 Record existing Matrix credential fallback and successful credential memory behavior before implementation.

## 2. Controller/application boundary

- [x] 2.1 Add a Matrix-specific controller/application component with a single clear ownership reason.
- [x] 2.2 Define immutable Matrix operation context with model, IP, operation kind, generation/request ID, expected worker/operation identity, non-secret credential context revision, and assigned candidate index when applicable.
- [x] 2.3 Move Matrix persistent handler/session fields and keepalive ownership out of `VCSDiagnosticApp` into the Matrix controller.
- [x] 2.4 Make MatrixController the only application-level owner of one persistent Matrix handler/session for the active Matrix context.
- [x] 2.5 Define Matrix session identity with model, IP, protocol/port, non-secret credential context revision or equivalent opaque token, and candidate index.
- [x] 2.6 Ensure candidate index alone is never sufficient for persistent session reuse.
- [x] 2.7 Keep credential candidate resolution, fallback, and successful-index memory connected to the existing application-owned credential policy.
- [x] 2.8 Keep the controller Matrix-specific; do not introduce shared PDU/DMP/Codec orchestration.

## 3. MatrixScreen intent boundary

- [x] 3.1 Replace direct route handler calls in `MatrixScreen` with non-secret route intent emission/callbacks.
- [x] 3.2 Replace direct quick status refresh handler calls in `MatrixScreen` with controller-owned refresh/status intent.
- [x] 3.3 Remove `MatrixScreen` ownership of credential lists, credential indexes, handler objects, and session objects.
- [x] 3.4 Preserve Matrix table rendering, selected route display, device info display, and existing visual behavior.
- [x] 3.5 Add focused tests proving `MatrixScreen` does not perform handler/network calls directly.

## 4. Background route lifecycle

- [x] 4.1 Add a background execution path for Matrix route mutation.
- [x] 4.2 Ensure handler/session acquisition for route mutation happens off the Qt GUI thread.
- [x] 4.3 Classify route mutation as state-changing and prevent blind replay after ambiguous delivery.
- [x] 4.4 Permit credential fallback only before any possible route command send and only after a structured authentication outcome explicitly confirms device rejection of the assigned credential.
- [x] 4.5 Emit structured route result/error/finished callbacks carrying Matrix context identity.

## 5. Structured Matrix authentication classification

- [x] 5.1 Replace text-based authentication classification in `ExtronIN1804Worker` with structured failure semantics that distinguish confirmed device credential rejection from local authentication/configuration precondition failure.
- [x] 5.2 Remove final authentication classification in `BaseExtronMatrixHandler.connect()` that searches aggregated exception strings for `auth`, `login`, `password`, `authentication`, `401`, `403`, or similar text.
- [x] 5.3 Preserve structured failure category and confirmed-rejection semantics for each Matrix transport attempt in the connection sequence.
- [x] 5.4 Keep one assigned credential candidate across all transport fallback attempts in one Matrix connection operation.
- [x] 5.5 Define conservative mixed-outcome handling: mixed or ambiguous auth/non-auth transport outcomes do not authorize credential fallback unless the final structured outcome is an unambiguous confirmed authentication rejection.
- [x] 5.6 Ensure Matrix handler and worker do not perform credential iteration, candidate advancement, wrap-around, or successful-index persistence.
- [x] 5.7 Ensure application credential fallback receives authority only from explicit structured confirmed device credential rejection semantics; `AuthenticationError` exception class alone is not sufficient authority.
- [x] 5.8 If implementation changes shared `BaseExtronMatrixHandler`, add regression coverage proving other Extron Matrix users of that base handler keep compatible non-Matrix behavior.
- [x] 5.9 Add focused tests proving that structured confirmed device credential rejection may authorize fallback only before mutation send is possible, while local authentication/configuration precondition failures, including missing username or password, do not advance credentials and application fallback checks confirmed-rejection semantics rather than only the `AuthenticationError` exception class.

## 6. Refresh lifecycle

- [x] 6.1 Keep initial Matrix refresh on the existing focused worker/background boundary.
- [x] 6.2 Bind Matrix refresh callbacks to Matrix controller context rather than widget state.
- [x] 6.3 Add quick/status refresh after successful route mutation as a read-only background operation.
- [x] 6.4 Bind refresh-after-mutation to the original Matrix context and drop it if the context changes.
- [x] 6.5 Preserve terminal/status redaction and current user-visible refresh behavior.

## 7. Session/context ownership

- [x] 7.1 Retain one persistent Matrix handler/session owned by MatrixController for the active Matrix context.
- [x] 7.2 Define persistent handler reuse predicate: model, IP, protocol/port, credential context revision, candidate index, and local connected state must match.
- [x] 7.3 Prevent cross-context session reuse after model, IP, credential configuration revision change, credential fallback, explicit reconnect, session failure, screen destruction, or application close.
- [x] 7.4 Serialize all access to the one persistent Matrix handler; overlapping route, refresh, quick/status refresh, and keepalive operations must not invoke it concurrently.
- [x] 7.5 Run blocking session acquisition, route mutation, refresh, keepalive/liveness checks, and cleanup on the owning background lane.
- [x] 7.6 Make cleanup idempotent and stale-safe so old cleanup cannot close the newer context's session.
- [x] 7.7 Add coverage for credential configuration changing while candidate index remains the same and invalidating the existing Matrix persistent session.

## 8. Stale callback coverage

- [x] 8.1 Add tests where stale Matrix result arrives after model/IP/context change.
- [x] 8.2 Add tests where stale Matrix error arrives after model/IP/context change.
- [x] 8.3 Add tests where stale Matrix finished arrives while a newer Matrix operation is active.
- [x] 8.4 Add tests where stale Matrix progress/status/terminal events cannot update the newer context.
- [x] 8.5 Add tests where stale route follow-up refresh cannot update a newer Matrix context.
- [x] 8.6 Add tests where stale callbacks cannot save credential memory or reset handler/session ownership for the newer context.

## 9. Regression tests

- [x] 9.1 Add focused tests proving Matrix route mutation does not execute in the GUI thread.
- [x] 9.2 Add focused tests proving Matrix refresh and quick/status refresh do not execute in the GUI thread.
- [x] 9.3 Add focused tests for application-owned Matrix credential fallback and no handler/worker candidate iteration.
- [x] 9.4 Add focused tests for no cross-context session reuse.
- [x] 9.5 Add focused tests proving full Matrix refresh success may cache the assigned credential index.
- [x] 9.6 Add focused tests proving session acquisition alone does not cache credential memory.
- [x] 9.7 Add focused tests proving successful route mutation and route reconciliation do not cache credential memory.
- [x] 9.8 Add focused tests proving stale Matrix success does not cache credential memory.
- [x] 9.9 Add focused tests proving generic connection text containing `auth`, `authentication`, `login`, `password`, `401`, or `403` does not authorize Matrix credential fallback.
- [x] 9.10 Add focused tests proving timeout, connection refusal, socket failure, SSH/Telnet negotiation failure, unsupported service, and malformed protocol response remain non-authentication Matrix outcomes.
- [x] 9.11 Add focused tests proving Matrix transport fallback keeps the same assigned credential candidate across all attempts.
- [x] 9.12 Add focused tests proving mixed Matrix transport outcomes use conservative no-credential-fallback classification unless final structured outcome is unambiguous authentication rejection.
- [x] 9.13 Add regression tests for existing Matrix rendering and successful route behavior.
- [x] 9.14 Run the relevant existing Matrix, worker, credential, and GUI tests.

## 10. Validation

- [x] 10.1 Run focused regression tests added or affected by the Matrix lifecycle extraction.
- [x] 10.2 Run `python -m unittest discover -s tests -p "test_*.py"` unless the implementation session documents why production/tests were untouched.
- [x] 10.3 Run `.\openspec.cmd validate matrix-operation-lifecycle-decomposition --strict`.
- [x] 10.4 Run `.\openspec.cmd validate --all --strict`.
- [x] 10.5 Run `git diff --check`.
- [x] 10.6 Confirm no unrelated PDU, DMP, codec, SIP, generic credential, worker facade, or handler protocol behavior changed.

## 11. Review follow-up evidence

- [x] 11.1 Serialize real persistent handler use across refresh, route, quick refresh, keepalive, and cleanup through the Matrix operation lane; covered by `test_persistent_handler_access_is_serialized_for_overlapping_operations`.
- [x] 11.2 Discard stale queued Matrix route operations before handler acquisition/network I/O; covered by `test_stale_queued_route_is_discarded_before_handler_acquisition`.
- [x] 11.3 Re-check current immutable context after waiting for the serialized lane and immediately before route send; covered by `test_route_that_becomes_stale_while_waiting_for_lane_does_not_send`.
- [x] 11.4 Use the application-owned request-scoped full-refresh credential cursor for retry candidate N+1 without persisting success early; covered by `test_matrix_full_refresh_uses_existing_attempt_plan_after_fallback`.
- [x] 11.5 Keep Matrix full-refresh fallback finite and discard the request plan after terminal exhaustion; covered by `test_matrix_full_refresh_fallback_exhaustion_discards_request_plan`.
- [x] 11.6 Dispatch controller-owned keepalive timer start/stop through the Qt owner-thread boundary while keeping the network probe in background; covered by `test_background_operation_does_not_start_keepalive_timer_directly`.
- [x] 11.7 Invalidate only the matching failed persistent session and reconnect on the next operation without letting old failures clear a newer session; covered by `test_session_failure_invalidates_matching_session_and_reconnects` and `test_old_failure_does_not_invalidate_new_matching_context_session`.
- [x] 11.8 Redact actual Matrix username/password from stdout and handler log callbacks, including echoed authentication prompts; covered by `test_telnet_authentication_does_not_print_or_log_actual_credentials`.
- [x] 11.9 Preserve stale suppression for result, error, progress, status, terminal, finished, cleanup, and route follow-up callbacks; covered by `test_stale_callbacks_are_suppressed_for_all_public_channels`.
