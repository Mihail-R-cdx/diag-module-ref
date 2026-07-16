## 1. Architecture and registration

- [ ] 1.1 Add `Extron IPL T PCS4i` to the power-control GUI category and map it to the existing `PDUScreen`.
- [ ] 1.2 Add a device-specific PCS4i handler boundary that implements the PDU operation surface without inheriting Aten protocol behavior.
- [ ] 1.3 Confirm and document the exact PCS4i Telnet command set, response grammar, session-ready marker or read-only authentication probe, HTTP outlet-name endpoint, HTTP request/response format, and HTTP authentication/session mechanism before implementing wire parsing.
- [ ] 1.4 Block implementation completion when verified PCS4i Telnet or HTTP protocol evidence is missing; do not ship guessed commands, guessed endpoints, or permanent fallback-name behavior.

## 2. PCS4i Telnet and HTTP behavior

- [ ] 2.1 Implement password-only Telnet authentication with the bounded two-send state machine and phase-specific prompt-buffer handling.
- [ ] 2.2 Add tests for initial `Password:`, initial `Password:**********************`, split prompt chunks, success after first send, success after second send, rejection after a third new prompt, and the maximum two password sends.
- [ ] 2.3 Classify timeout, disconnect, malformed prompt flow, and unknown transport data separately from confirmed authentication rejection.
- [ ] 2.4 Confirm authentication success only from a documented session-ready prompt, another documented non-mutating ready marker, or a verified read-only outlet-status query; prove ON/OFF/REBOOT are never used as authentication probes.
- [ ] 2.5 Implement Telnet outlet status reads that return exactly four normalized outlet records for `PDUScreen`.
- [ ] 2.6 Implement the verified HTTP outlet-name loading path after Telnet status succeeds; successful HTTP names replace fallback names.
- [ ] 2.7 Fall back to `Розетка N` only for runtime HTTP connection failure, timeout, HTTP 401/403/login rejection, malformed/unsupported response, or a missing/empty name for that outlet while preserving Telnet status.

## 3. Credentials and redaction

- [ ] 3.1 Resolve PCS4i credentials through the existing application-owned `auth_mode: "password"` contract before worker submission.
- [ ] 3.2 Ensure PCS4i workers and handlers receive only one assigned credential candidate and never advance the credential index.
- [ ] 3.3 Add tests proving only structured confirmed `AuthenticationError` authorizes application-owned credential fallback.
- [ ] 3.4 Add redaction tests proving the real password is absent from logs, exceptions, terminal output, GUI messages, public diagnostics, and test output.
- [ ] 3.5 Add tests proving HTTP outlet-name failures, including HTTP 401, HTTP 403, login rejection, timeout, transport failure, and malformed response, do not advance the credential chain, independently commit a credential index, or invalidate the assigned Telnet credential; successful Telnet refresh with HTTP fallback names remains eligible for normal successful-index caching.

## 4. Background PDU lifecycle

- [ ] 4.1 Add background PCS4i refresh execution for Telnet status and required HTTP name loading; no PCS4i network I/O may run in the Qt GUI thread.
- [ ] 4.2 Add background PDU outlet command execution for PCS4i and Aten through a shared application-owned operation dispatch boundary.
- [ ] 4.3 Integrate Aten refresh, including `AtenPDUWorker` if retained, into the same application-owned PDU operation generation/stale-context mechanism.
- [ ] 4.4 Store current PDU operation context generation in the application/composition layer, not in Qt widgets.
- [ ] 4.5 Submit immutable operation descriptors for PCS4i refresh, Aten refresh, PCS4i commands, and Aten commands containing operation id, generation, model, IP, non-secret credential context, operation type, outlet number when applicable, and desired command/target when applicable.
- [ ] 4.6 Recheck captured context against the application-owned current context before handler acquisition; drop stale queued operations without handler construction, transport open, network I/O, or command send.
- [ ] 4.7 Recheck validity immediately before first network I/O when handler acquisition/preparation and I/O are separate phases.
- [ ] 4.8 Release handlers/transports in worker cleanup paths for success, failure, indeterminate, and stale-drop outcomes.
- [ ] 4.9 Ignore stale results and completions after device/IP/screen/credential context changes and prove old callbacks cannot update the new context.

## 5. Command safety

- [ ] 5.1 Enforce one initial command send maximum for each user PDU ON/OFF/REBOOT operation.
- [ ] 5.2 After acknowledged success, complete with no additional command sends; after authoritative rejection, complete failure with no credential fallback and no replay.
- [ ] 5.3 For ambiguous ON/OFF delivery, allow at most one reconciliation cycle, at most one recovery/reconnect sequence when needed for device-specific authoritative outlet-state readback, and at most one normalized authoritative outlet-state decision.
- [ ] 5.4 Report success without resend when ON/OFF readback equals the requested target.
- [ ] 5.5 Allow at most one controlled absolute ON/OFF resend when readback equals the known pre-command state; if that resend is ambiguous, report indeterminate with no further replay.
- [ ] 5.6 Report indeterminate with zero resend when ON/OFF readback is unavailable, unknown, or conflicting.
- [ ] 5.7 Implement REBOOT safety so ambiguous delivery has exactly zero automatic resend and a maximum of one REBOOT send for the user operation.
- [ ] 5.8 Add command tests for ON, OFF, and REBOOT dispatch through the device-specific PCS4i handler.
- [ ] 5.9 Add tests for the bounded reconciliation budget, second ambiguous ON/OFF outcome, ambiguous REBOOT non-replay, and no recursive recovery/reconciliation.
- [ ] 5.10 Add Aten command safety tests for ambiguous ON, ambiguous OFF, target already reached, known pre-command state permitting at most one controlled resend, unavailable/unknown/conflicting readback producing indeterminate, second ambiguous outcome after controlled resend producing indeterminate, ambiguous REBOOT never resent, reconciliation budget not exceeded, and existing Aten protocol behavior unchanged.

## 6. GUI and regression coverage

- [ ] 6.1 Test that `Extron IPL T PCS4i` appears in the power-control category and uses `PDUScreen`.
- [ ] 6.2 Test that four returned PCS4i outlet records render as four rows with ON, OFF, and REBOOT controls.
- [ ] 6.3 Test that PCS4i refresh and outlet control do not block the GUI thread.
- [ ] 6.4 Test stale queued PCS4i refresh and command operations are dropped before network I/O.
- [ ] 6.5 Test stale queued Aten refresh is dropped before handler acquisition and performs zero network I/O.
- [ ] 6.6 Test Aten refresh whose context becomes stale between handler preparation and first I/O blocks first network I/O.
- [ ] 6.7 Test in-flight old Aten refresh result/error/completion cannot update a new PDU context.
- [ ] 6.8 Test normal current Aten refresh continues to work unchanged.
- [ ] 6.9 Add Aten ON/OFF/REBOOT dispatch, successful refresh-after-command, GUI-thread, stale-drop before handler acquisition/network I/O, outlet-count/rendering, wire-protocol unchanged, and normal-success behavior regression tests.
- [ ] 6.10 Verify other supported device paths are not routed through the PCS4i PDU dispatch.

## 7. Validation

- [ ] 7.1 Run focused PCS4i authentication, PDU data, command safety, credential, redaction, lifecycle, and GUI tests.
- [ ] 7.2 Run Aten refresh stale-generation and command migration regression tests.
- [ ] 7.3 Run the full offline unittest suite.
- [ ] 7.4 Run `.\openspec.cmd validate extron-ipl-t-pcs4i-power-control --strict`.
- [ ] 7.5 Run `.\openspec.cmd validate --all --strict`.
- [ ] 7.6 Run `git diff --check` and confirm no production code is included in the architecture-only change.
