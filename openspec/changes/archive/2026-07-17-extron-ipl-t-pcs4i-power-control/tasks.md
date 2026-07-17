## 1. Architecture and registration

- [ ] 1.1 Add `Extron IPL T PCS4i` to the power-control GUI category and map it to the existing `PDUScreen`.
- [ ] 1.2 Add a model-specific PDU capability declaration: PCS4i supports refresh, ON, and OFF; PCS4i REBOOT is unsupported.
- [ ] 1.3 Add a device-specific PCS4i handler boundary that implements refresh, `get_outlets_status()`, `get_device_info()`, `turn_on(outlet_number)`, and `turn_off(outlet_number)` without inheriting Aten protocol behavior or exposing PCS4i `reboot()`.
- [ ] 1.4 Preserve Aten PE8208AV ON, OFF, and REBOOT capabilities and Aten wire semantics.
- [ ] 1.5 Keep the exact HTTP GET path containing `xName1` through `xName4` as the only unresolved protocol evidence item if no retained capture confirms it before parser implementation.

## 2. PCS4i Telnet SIS behavior

- [ ] 2.1 Implement Telnet port 23 as authoritative PCS4i transport for session establishment, identity, outlet power status, ON, OFF, and readback.
- [ ] 2.2 Implement verified identity/session SIS commands: `1I`, `2I`, `N`, `Q`, and `<ESC>CK`.
- [ ] 2.3 Implement `<ESC>NPC<CR>` as authoritative outlet power-state readback for outlets 1..4, where `0` means OFF and `1` means ON.
- [ ] 2.4 Implement `<ESC>NPS<CR>` only as current/reference threshold state and prove it is never interpreted as outlet power state.
- [ ] 2.5 Implement ON command grammar `<ESC>N*1PC<CR>` with acknowledgement `CpnN Ppc1<CR><LF>`.
- [ ] 2.6 Implement OFF command grammar `<ESC>N*0PC<CR>` with acknowledgement `CpnN Ppc0<CR><LF>`.
- [ ] 2.7 Reject PCS4i outlet numbers outside 1..4 before any Telnet command is sent.
- [ ] 2.8 After ON or OFF, determine final authoritative state through a separate `PC` readback rather than acknowledgement alone.
- [ ] 2.9 Add offline SIS parser tests for model, firmware, security level, `PC` 0/OFF, `PC` 1/ON, `PS` non-power semantics, invalid outlet rejection, ON grammar, OFF grammar, and post-command `PC` readback.

## 3. PCS4i authentication and credentials

- [ ] 3.1 Implement optional password-only Telnet authentication with no username and no required credential before connect.
- [ ] 3.2 Implement passwordless readiness: when no new `Password` marker is observed, a verified read-only SIS probe such as `<ESC>CK<CR>` or `PC` must succeed before the session is ready.
- [ ] 3.3 Detect password prompts by the `Password` marker in new phase bytes, independent of colon, asterisks, asterisk count, or exact prompt string.
- [ ] 3.4 Scope prompt detection by phase: initial receive, post password send #1, and post password send #2; never reuse the initial buffer as a repeated prompt.
- [ ] 3.5 Send the same assigned password at most twice in one connection attempt and never send a third password.
- [ ] 3.6 Return structured `CredentialRequired` when PCS4i requests `Password` and no credential was assigned; do not return `AuthenticationError` and do not send a password.
- [ ] 3.7 Return structured `AuthenticationError` only after an actually sent assigned password is rejected by a new prompt after send #2.
- [ ] 3.8 Ensure PCS4i workers and handlers receive at most one assigned credential candidate and never advance the credential index.
- [ ] 3.9 Ensure passwordless success with an assigned but unused candidate does not cache that candidate, change successful credential index, invalidate an existing index, or trigger fallback.
- [ ] 3.10 Implement application/composition behavior that creates one credentialless PCS4i attempt when no explicit credential, explicit profile, or PCS4i device mapping exists.
- [ ] 3.11 Ensure credentialless PCS4i attempts carry assigned credential `none`, no candidate index, and no successful credential index.
- [ ] 3.12 Ensure credentialless PCS4i `Password` prompt returns `CredentialRequired`, sends no password, starts no next candidate, and surfaces a safe actionable credential-configuration error.
- [ ] 3.13 Ensure missing credentials for other authentication-required devices still block before network I/O with a safe configuration error.
- [ ] 3.14 Add authentication/composition tests for passwordless session, decorated prompt, prompt without colon, second prompt sending the same credential, third prompt forbidden, initial prompt not reused, passwordless session with assigned candidate, password required with no assigned credential, PCS4i without mapping starting credentialless, credentialless success without `Password`, credentialless `Password` -> `CredentialRequired`, credentialless success not updating credential memory, and other auth-required devices remaining blocked.

## 4. HTTP outlet-name enrichment

- [ ] 4.1 Implement the real read-only HTTP name-loading path only after confirming the exact GET path whose response contains `xName1`, `xName2`, `xName3`, and `xName4`.
- [ ] 4.2 Parse `xName1` through `xName4` as outlet names mapped to outlets 1 through 4.
- [ ] 4.3 Treat the discovered no-auth `GET /` result as configuration-specific evidence only; do not require all PCS4i devices to be HTTP-auth-free.
- [ ] 4.4 Run HTTP name enrichment only after authoritative Telnet status succeeds.
- [ ] 4.5 Use fallback names per outlet only when the HTTP response is unavailable, malformed, unsupported, 401/403, login-rejected, or that outlet name is missing/empty.
- [ ] 4.6 Preserve Telnet status on HTTP failure and ensure HTTP failure never authorizes Telnet credential fallback or produces Telnet `AuthenticationError`.
- [ ] 4.7 Add HTTP tests for all names available, one name missing, malformed response, HTTP unavailable, HTTP 401/403, and verified no-auth device behavior.

## 5. Background PDU lifecycle

- [ ] 5.1 Add background PCS4i refresh execution for Telnet status and required HTTP name loading; no PCS4i network I/O may run in the Qt GUI thread.
- [ ] 5.2 Add background PDU outlet command execution for PCS4i ON/OFF and Aten ON/OFF/REBOOT through a shared application-owned operation dispatch boundary.
- [ ] 5.3 Integrate Aten refresh, including `AtenPDUWorker` if retained, into the same application-owned PDU operation generation/stale-context mechanism.
- [ ] 5.4 Store current PDU operation context generation in the application/composition layer, not in Qt widgets.
- [ ] 5.5 Submit immutable operation descriptors containing operation id, generation, model, IP, non-secret credential context, operation type, outlet number when applicable, and desired target when applicable.
- [ ] 5.6 Validate model capability before worker creation; reject PCS4i REBOOT before handler acquisition and before any Telnet or HTTP network I/O.
- [ ] 5.7 Recheck captured context before handler acquisition; drop stale queued operations without handler construction, transport open, network I/O, or command send.
- [ ] 5.8 Recheck validity immediately before first network I/O when handler acquisition/preparation and I/O are separate phases.
- [ ] 5.9 Release handlers/transports in worker cleanup paths for success, failure, indeterminate, unsupported, and stale-drop outcomes.
- [ ] 5.10 Ignore stale results and completions after device/IP/screen/credential context changes and prove old callbacks cannot update the new context.

## 6. Command safety and capabilities

- [ ] 6.1 Attempt authoritative `PRE_STATE` readback before the first PCS4i ON/OFF send, preserve it only when valid, and define `TARGET` from the requested absolute command.
- [ ] 6.2 Enforce PCS4i ON/OFF budgets: initial send max 1, controlled resend max 1, total state-changing sends max 2, reconciliation cycles max 1, reconciliation decision readback max 1, terminal confirmation readback after resend max 1, recursive recovery 0.
- [ ] 6.3 After PCS4i ON/OFF acknowledgement, always perform authoritative `PC` readback; acknowledgement alone is not terminal success.
- [ ] 6.4 If acknowledged-command `PC == TARGET`, report success; if saved `PRE_STATE` is known and `PC == PRE_STATE`, allow the single controlled absolute resend; if `PRE_STATE` is unknown and valid `PC != TARGET`, report indeterminate with no resend; if `PC` is unavailable/unknown/malformed/conflicting, report indeterminate with no resend.
- [ ] 6.5 For ambiguous PCS4i initial delivery, allow at most one reconciliation cycle with at most one reconnect/recovery if needed for `PC` readback and one reconciliation decision readback.
- [ ] 6.6 If reconciliation decision `PC == TARGET`, report success without resend; if saved `PRE_STATE` is known and `PC == PRE_STATE`, allow the single controlled absolute resend; if `PRE_STATE` is unknown and valid `PC != TARGET`, report indeterminate with no resend; if `PC` is unavailable/unknown/malformed/conflicting, report indeterminate with no resend.
- [ ] 6.7 After the controlled resend, perform exactly one terminal confirmation `PC` readback: `TARGET` -> success, `PRE_STATE` -> failure, unavailable/unknown/conflicting -> indeterminate.
- [ ] 6.8 Ensure the opposite of `TARGET` is never treated as `PRE_STATE` unless that state was captured as authoritative `PRE_STATE` before the initial send.
- [ ] 6.9 Add tests proving PCS4i REBOOT is hidden in `PDUScreen` and rejected programmatically before handler acquisition/network I/O.
- [ ] 6.10 Ensure no further resend, reconnect, or reconciliation occurs after controlled-resend terminal confirmation.
- [ ] 6.11 Add PCS4i ON/OFF tests for acknowledged mismatch with known `PRE_STATE`, unknown `PRE_STATE` reaching target, unknown `PRE_STATE` returning valid non-target state, controlled resend requiring preserved `PRE_STATE`, opposite state not implicitly being `PRE_STATE`, controlled resend confirmation, ambiguous initial delivery reaching target, ambiguous initial delivery staying at saved `PRE_STATE`, unavailable reconciliation readback, total send budget, and no success based only on resend acknowledgement.
- [ ] 6.12 Add Aten command safety tests for ambiguous ON, ambiguous OFF, target already reached, known pre-command state permitting at most one controlled resend, unavailable/unknown/conflicting readback producing indeterminate, second ambiguous outcome after controlled resend producing indeterminate, ambiguous REBOOT never resent, reconciliation budget not exceeded, and existing Aten protocol behavior unchanged.

## 7. GUI and regression coverage

- [ ] 7.1 Test that `Extron IPL T PCS4i` appears in the power-control category and uses `PDUScreen`.
- [ ] 7.2 Test that four returned PCS4i outlet records render as four rows with ON and OFF controls and without REBOOT control.
- [ ] 7.3 Test that PCS4i refresh and outlet control do not block the GUI thread.
- [ ] 7.4 Test stale queued PCS4i refresh and command operations are dropped before network I/O.
- [ ] 7.5 Test stale queued Aten refresh is dropped before handler acquisition and performs zero network I/O.
- [ ] 7.6 Test Aten refresh whose context becomes stale between handler preparation and first I/O blocks first network I/O.
- [ ] 7.7 Test in-flight old Aten refresh result/error/completion cannot update a new PDU context.
- [ ] 7.8 Test normal current Aten refresh continues to work unchanged.
- [ ] 7.9 Add Aten ON/OFF/REBOOT dispatch, successful refresh-after-command, GUI-thread, stale-drop before handler acquisition/network I/O, outlet-count/rendering, wire-protocol unchanged, and normal-success behavior regression tests.
- [ ] 7.10 Verify other supported device paths are not routed through the PCS4i PDU dispatch.

## 8. Validation

- [ ] 8.1 Run focused PCS4i authentication, SIS parser, HTTP name, PDU data, command safety, credential, redaction, lifecycle, and GUI tests.
- [ ] 8.2 Run Aten refresh stale-generation and command migration regression tests.
- [ ] 8.3 Run the full offline unittest suite.
- [ ] 8.4 Run `.\openspec.cmd validate extron-ipl-t-pcs4i-power-control --strict`.
- [ ] 8.5 Run `.\openspec.cmd validate --all --strict`.
- [ ] 8.6 Run `git diff --check` and confirm no production code or production tests are included in the architecture-only change.
