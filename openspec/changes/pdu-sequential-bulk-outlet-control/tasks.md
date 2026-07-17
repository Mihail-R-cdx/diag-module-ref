## 1. Architecture and Spec

- [x] Inspect current PDU implementation, PDU tests, root specs, and prior PCS4i architecture.
- [x] Create OpenSpec proposal, design, tasks, and spec deltas.
- [x] Keep this change specification-only with no production or test edits.

## 2. Implementation Tasks

- [ ] Add shared `PDUScreen` bulk buttons `Выкл всё` and `Вкл всё` under the outlet table.
- [ ] Gate bulk buttons from selected-model ON/OFF capabilities.
- [ ] Add one confirmation dialog per bulk sequence.
- [ ] Add an immutable application-owned bulk operation descriptor containing operation id, generation, model, IP address, non-secret credential context, assigned credential index when any, target ON/OFF, and ordered outlet records.
- [ ] Build the outlet sequence from current outlet records ordered by outlet number; do not hard-code outlet count.
- [ ] Implement one serial background bulk execution path, either as a dedicated worker or an extension of the existing PDU worker boundary.
- [ ] Reuse existing safe absolute ON/OFF outlet policy for each outlet sub-operation.
- [ ] Keep bulk sequencing and one-second inter-outlet delays outside the Qt GUI thread.
- [ ] Do not delay before the first outlet or after the final outlet.
- [ ] Stop fail-fast on the first terminal outlet failure.
- [ ] Return structured terminal results for full and partial completion without secrets.
- [ ] Refresh actual PDU state after full or partial terminal completion when the context is current.
- [ ] Lock bulk and individual PDU controls while a bulk sequence is active.
- [ ] Ignore stale results, errors, and completions for old PDU contexts.
- [ ] Keep credential selection and fallback in the application/composition layer.
- [ ] Prevent credential fallback/restart after the first state-changing outlet command has been sent or may have been sent.
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
- [ ] One-second inter-outlet delay.
- [ ] No delay after final outlet.
- [ ] Delay does not run on GUI thread.
- [ ] Fail-fast.
- [ ] Partial completion result.
- [ ] No rollback.
- [ ] No replay of completed outlets.
- [ ] Stale before handler acquisition.
- [ ] Stale between outlet sub-operations.
- [ ] Stale callback isolation.
- [ ] One handler/session lifecycle where the chosen architecture requires it.
- [ ] Proper cleanup.
- [ ] GUI buttons.
- [ ] Confirmation dialog.
- [ ] Bulk/individual control locking.
- [ ] No concurrent bulk sequence.
- [ ] Credential fallback before mutation.
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
