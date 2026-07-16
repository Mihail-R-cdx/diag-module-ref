## 1. Architecture and registration

- [ ] 1.1 Add `Extron IPL T PCS4i` to the power-control GUI category and map it to the existing `PDUScreen`.
- [ ] 1.2 Add a device-specific PCS4i handler boundary that implements the PDU operation surface without inheriting Aten protocol behavior.
- [ ] 1.3 Confirm and document the exact PCS4i Telnet command set, response grammar, session-ready marker, and HTTP outlet-name endpoint before implementing wire parsing.

## 2. PCS4i Telnet and HTTP behavior

- [ ] 2.1 Implement password-only Telnet authentication with the bounded two-send state machine and phase-specific prompt-buffer handling.
- [ ] 2.2 Add tests for initial `Password:`, initial `Password:**********************`, split prompt chunks, success after first send, success after second send, rejection after a third new prompt, and the maximum two password sends.
- [ ] 2.3 Classify timeout, disconnect, malformed prompt flow, and unknown transport data separately from confirmed authentication rejection.
- [ ] 2.4 Implement Telnet outlet status reads that return exactly four normalized outlet records for `PDUScreen`.
- [ ] 2.5 Implement HTTP outlet-name enrichment only after Telnet status succeeds; fall back to `Розетка N` and preserve Telnet status when HTTP fails.

## 3. Credentials and redaction

- [ ] 3.1 Resolve PCS4i credentials through the existing application-owned `auth_mode: "password"` contract before worker submission.
- [ ] 3.2 Ensure PCS4i workers and handlers receive only one assigned credential candidate and never advance the credential index.
- [ ] 3.3 Add tests proving only structured confirmed `AuthenticationError` authorizes application-owned credential fallback.
- [ ] 3.4 Add redaction tests proving the real password is absent from logs, exceptions, terminal output, GUI messages, public diagnostics, and test output.

## 4. Background PDU lifecycle

- [ ] 4.1 Add background PCS4i refresh execution for Telnet status and optional HTTP names; no PCS4i network I/O may run in the Qt GUI thread.
- [ ] 4.2 Add background PDU outlet command execution for PCS4i and preferably Aten through a shared operation dispatch boundary.
- [ ] 4.3 Recheck selected model, IP, credential context, and operation generation before handler acquisition and network I/O; drop stale queued operations.
- [ ] 4.4 Release handlers/transports in worker cleanup paths for success, failure, and stale-drop outcomes.
- [ ] 4.5 Ignore stale results and completions after device/IP/screen context changes.

## 5. Command safety

- [ ] 5.1 Implement ON/OFF reconciliation after ambiguous delivery: read authoritative state, report already-achieved targets, optionally send one controlled absolute target when still at the pre-command state, and otherwise report indeterminate.
- [ ] 5.2 Implement REBOOT safety so ambiguous delivery never triggers an automatic second reboot.
- [ ] 5.3 Add command tests for ON, OFF, and REBOOT dispatch through the device-specific PCS4i handler.
- [ ] 5.4 Add tests for ambiguous ON/OFF reconciliation and ambiguous REBOOT non-replay.

## 6. GUI and regression coverage

- [ ] 6.1 Test that `Extron IPL T PCS4i` appears in the power-control category and uses `PDUScreen`.
- [ ] 6.2 Test that four returned PCS4i outlet records render as four rows with ON, OFF, and REBOOT controls.
- [ ] 6.3 Test that PCS4i refresh and outlet control do not block the GUI thread.
- [ ] 6.4 Test stale queued PCS4i refresh and command operations are dropped before network I/O.
- [ ] 6.5 If Aten commands migrate to the background PDU command worker, add Aten ON/OFF/REBOOT dispatch, GUI-thread, stale-drop, outlet-rendering, and behavior-regression tests.
- [ ] 6.6 Verify other supported device paths are not routed through the PCS4i PDU dispatch.

## 7. Validation

- [ ] 7.1 Run focused PCS4i authentication, PDU data, command safety, credential, redaction, lifecycle, and GUI tests.
- [ ] 7.2 Run relevant Aten regression tests when the Aten command path is touched.
- [ ] 7.3 Run the full offline unittest suite.
- [ ] 7.4 Run `.\openspec.cmd validate extron-ipl-t-pcs4i-power-control --strict`.
- [ ] 7.5 Run `.\openspec.cmd validate --all --strict`.
- [ ] 7.6 Run `git diff --check` and confirm no production code is included in the architecture-only change.
