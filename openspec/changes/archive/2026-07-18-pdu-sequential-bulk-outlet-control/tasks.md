## 1. Architecture and Spec

- [x] Inspect current PDU implementation, PDU tests, root specs, and prior PCS4i architecture.
- [x] Create OpenSpec proposal, design, tasks, and spec deltas.
- [x] Keep this change specification-only with no production or test edits.

## 2. Implementation Tasks

- [x] Add shared `PDUScreen` bulk buttons `Выкл всё` and `Вкл всё` under the outlet table.
- [x] Gate bulk buttons from selected-model ON/OFF capabilities.
- [x] Add one confirmation dialog per bulk sequence.
- [x] Add an immutable application-owned bulk operation descriptor containing operation id, generation, model, IP address, non-secret credential context, assigned credential index when any, target ON/OFF, structured mutation state, and immutable ordered outlet identity sequence.
- [x] Build the outlet identity sequence from current outlet records ordered by outlet number; do not hard-code outlet count and do not store mutable outlet dictionaries in the descriptor.
- [x] Reject missing, malformed, unsupported, or duplicate outlet identities before any state-changing network I/O.
- [x] Implement one serial background bulk execution path, either as a dedicated worker or an extension of the existing PDU worker boundary.
- [x] Reuse existing safe absolute ON/OFF outlet policy for each outlet sub-operation.
- [x] Keep bulk sequencing and one-second inter-outlet delays outside the Qt GUI thread.
- [x] Do not delay before the first outlet or after the final outlet.
- [x] Do not wait after terminal failure or after stale validation prevents the next outlet.
- [x] Stop fail-fast on the first terminal outlet failure.
- [x] Return structured terminal results for full success, partial terminal failure, stale termination before mutation, and stale termination after completed outlet sub-operations without secrets.
- [x] Refresh actual PDU state after full or partial terminal completion when the context is current.
- [x] Lock bulk and individual PDU controls while a bulk sequence is active, scoped to the owning PDU context generation/token.
- [x] Ensure a new PDU context does not inherit an old context's bulk lock.
- [x] Ignore stale results, errors, and completions for old PDU contexts.
- [x] Keep credential selection and fallback in the application/composition layer.
- [x] Authorize bulk credential fallback only from structured `AuthenticationError` plus structured execution metadata proving zero possible state-changing sends.
- [x] Prevent credential fallback/restart after the first state-changing outlet command has been attempted, sent, may have been delivered, or has ambiguous outcome.
- [x] Store a successful credential index only after full successful bulk completion; do not store it after partial, failed, or stale termination.
- [x] Preserve Aten ON/OFF/REBOOT and PCS4i ON/OFF capabilities; do not add PCS4i REBOOT.
- [x] Do not add orchestration-only `turn_all_on()` or `turn_all_off()` handler APIs.
- [x] Do not merge Aten and PCS4i transport protocols.

## 3. Required Tests

- [x] Aten bulk ON.
- [x] Aten bulk OFF.
- [x] PCS4i bulk ON.
- [x] PCS4i bulk OFF.
- [x] Dynamic outlet count.
- [x] Strict outlet ordering by outlet number.
- [x] Duplicate outlet identity rejected before mutation.
- [x] Missing or malformed outlet identity rejected before mutation.
- [x] Immutable outlet sequence capture is unaffected by later GUI outlet-record mutation.
- [x] One-second inter-outlet delay.
- [x] No delay after final outlet.
- [x] No delay after terminal failure.
- [x] No delay after stale detection before the next outlet.
- [x] Delay does not run on GUI thread.
- [x] Fail-fast.
- [x] Partial completion result.
- [x] Stale termination before mutation result.
- [x] Stale termination after completed outlet sub-operations result.
- [x] No rollback.
- [x] No replay of completed outlets.
- [x] Stale before handler acquisition.
- [x] Stale between outlet sub-operations.
- [x] Stale callback isolation.
- [x] Context switch while bulk active does not inherit old lock.
- [x] Old stale completion cannot unlock a new context's active bulk controls.
- [x] One handler/session lifecycle where the chosen architecture requires it.
- [x] Proper cleanup.
- [x] GUI buttons.
- [x] Confirmation dialog.
- [x] Bulk/individual control locking.
- [x] No concurrent bulk sequence.
- [x] Credential fallback before mutation.
- [x] Structured zero-send proof required for credential fallback.
- [x] Empty success list is not credential retry authority.
- [x] Authentication-looking failure after possible send does not retry credentials.
- [x] No credential fallback/restart after mutation begins.
- [x] Successful credential memory rules.
- [x] PCS4i credentialless/passwordless behavior regression.
- [x] Aten individual ON/OFF/REBOOT regression.
- [x] PCS4i individual ON/OFF regression.
- [x] PCS4i REBOOT remains unsupported.
- [x] Secret redaction.
- [x] Existing full regression suite.

## 4. Validation

- [x] Run `.\openspec.cmd validate pdu-sequential-bulk-outlet-control --strict`.
- [x] Run `.\openspec.cmd validate --all --strict`.
- [x] Run `git diff --check`.
- [x] Confirm implementation changes are scoped to approved production code, tests, and task evidence.
