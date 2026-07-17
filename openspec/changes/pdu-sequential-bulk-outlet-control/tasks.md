## 1. Architecture and Spec

- [x] Inspect current PDU implementation, PDU tests, root specs, and prior PCS4i architecture.
- [x] Create OpenSpec proposal, design, tasks, and spec deltas.
- [x] Keep this change specification-only with no production or test edits.

## 2. Implementation Tasks

- [ ] Add shared `PDUScreen` bulk buttons `Выкл всё` and `Вкл всё` under the outlet table.
- [ ] Gate bulk buttons from selected-model ON/OFF capabilities.
- [ ] Add one confirmation dialog per bulk sequence.
- [ ] Add an immutable application-owned bulk operation descriptor containing operation id, generation, model, IP address, non-secret credential context, assigned credential index when any, target ON/OFF, structured mutation state, and immutable ordered outlet identity sequence.
- [ ] Build the outlet identity sequence from current outlet records ordered by outlet number; do not hard-code outlet count and do not store mutable outlet dictionaries in the descriptor.
- [ ] Reject missing, malformed, unsupported, or duplicate outlet identities before any state-changing network I/O.
- [ ] Implement one serial background bulk execution path, either as a dedicated worker or an extension of the existing PDU worker boundary.
- [ ] Reuse existing safe absolute ON/OFF outlet policy for each outlet sub-operation.
- [ ] Keep bulk sequencing and one-second inter-outlet delays outside the Qt GUI thread.
- [ ] Do not delay before the first outlet or after the final outlet.
- [ ] Do not wait after terminal failure or after stale validation prevents the next outlet.
- [ ] Stop fail-fast on the first terminal outlet failure.
- [ ] Return structured terminal results for full success, partial terminal failure, stale termination before mutation, and stale termination after completed outlet sub-operations without secrets.
- [ ] Refresh actual PDU state after full or partial terminal completion when the context is current.
- [ ] Lock bulk and individual PDU controls while a bulk sequence is active, scoped to the owning PDU context generation/token.
- [ ] Ensure a new PDU context does not inherit an old context's bulk lock.
- [ ] Ignore stale results, errors, and completions for old PDU contexts.
- [ ] Keep credential selection and fallback in the application/composition layer.
- [ ] Authorize bulk credential fallback only from structured `AuthenticationError` plus structured execution metadata proving zero possible state-changing sends.
- [ ] Prevent credential fallback/restart after the first state-changing outlet command has been attempted, sent, may have been delivered, or has ambiguous outcome.
- [ ] Store a successful credential index only after full successful bulk completion; do not store it after partial, failed, or stale termination.
- [ ] Preserve Aten ON/OFF/REBOOT and PCS4i ON/OFF capabilities; do not add PCS4i REBOOT.
- [ ] Do not add orchestration-only `turn_all_on()` or `turn_all_off()` handler APIs.
- [ ] Do not merge Aten and PCS4i transport protocols.

## 3. Required Tests

- [ ] Aten bulk ON.
- [ ] Aten bulk OFF.
- [ ] PCS4i bulk ON.
- [ ] PCS4i bulk OFF.
- [ ] Dynamic outlet count.
- [ ] Strict outlet ordering by outlet number.
- [ ] Duplicate outlet identity rejected before mutation.
- [ ] Missing or malformed outlet identity rejected before mutation.
- [ ] Immutable outlet sequence capture is unaffected by later GUI outlet-record mutation.
- [ ] One-second inter-outlet delay.
- [ ] No delay after final outlet.
- [ ] No delay after terminal failure.
- [ ] No delay after stale detection before the next outlet.
- [ ] Delay does not run on GUI thread.
- [ ] Fail-fast.
- [ ] Partial completion result.
- [ ] Stale termination before mutation result.
- [ ] Stale termination after completed outlet sub-operations result.
- [ ] No rollback.
- [ ] No replay of completed outlets.
- [ ] Stale before handler acquisition.
- [ ] Stale between outlet sub-operations.
- [ ] Stale callback isolation.
- [ ] Context switch while bulk active does not inherit old lock.
- [ ] Old stale completion cannot unlock a new context's active bulk controls.
- [ ] One handler/session lifecycle where the chosen architecture requires it.
- [ ] Proper cleanup.
- [ ] GUI buttons.
- [ ] Confirmation dialog.
- [ ] Bulk/individual control locking.
- [ ] No concurrent bulk sequence.
- [ ] Credential fallback before mutation.
- [ ] Structured zero-send proof required for credential fallback.
- [ ] Empty success list is not credential retry authority.
- [ ] Authentication-looking failure after possible send does not retry credentials.
- [ ] No credential fallback/restart after mutation begins.
- [ ] Successful credential memory rules.
- [ ] PCS4i credentialless/passwordless behavior regression.
- [ ] Aten individual ON/OFF/REBOOT regression.
- [ ] PCS4i individual ON/OFF regression.
- [ ] PCS4i REBOOT remains unsupported.
- [ ] Secret redaction.
- [ ] Existing full regression suite.

## 4. Validation

- [ ] Run `.\openspec.cmd validate pdu-sequential-bulk-outlet-control --strict`.
- [ ] Run `.\openspec.cmd validate --all --strict`.
- [ ] Run `git diff --check`.
- [ ] Confirm only OpenSpec change files changed.
