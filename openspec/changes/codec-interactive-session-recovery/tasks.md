## 1. Shared credential and transport contracts

- [ ] 1.1 Add typed established-session and unknown-command-outcome errors without changing existing authentication semantics.
- [ ] 1.2 Add a request-scoped monotonic credential attempt plan and integrate refresh retry so only final success commits the existing model/IP successful index.
- [ ] 1.3 Extract and test model-specific codec transport ordering, including runtime-supported TE20 HTTPS, saved-profile-first selection, and deduplication.

## 2. Handler failure and command semantics

- [ ] 2.1 Normalize TE20 initial authentication, established-session invalidation, transport, protocol, command, and cleanup outcomes while preserving one-send/readback controls.
- [ ] 2.2 Normalize TE40 cookie/Session ID/CSRF and browser-session outcomes so command failures are typed instead of swallowed as empty dictionaries.
- [ ] 2.3 Normalize Bar 310 session/token and REST outcomes, preserve `X-Access-Token` call logs, and replace repeated presentation sends with one send plus readback.
- [ ] 2.4 Normalize Polycom HTTPS/SSH session outcomes while retaining same-credential lazy SSH control and the separate call-log worker.

## 3. Serialized interactive session controller

- [ ] 3.1 Implement one background serialized controller lane with operation IDs, context generations, duplicate-poll suppression, and redacted public signals.
- [ ] 3.2 Implement handler acquisition with context identity checks, saved-profile-first transport fallback, one assigned credential per handler, and final-success state commits.
- [ ] 3.3 Implement cache invalidation and a non-recursive one-cycle recovery budget for local closure, invalid session, and recoverable connection loss.
- [ ] 3.4 Implement read-only replay and state-changing readback/reconciliation descriptors, including conflict-safe relative volume and toggle behavior.
- [ ] 3.5 Implement deterministic controller shutdown that closes Huawei session artifacts and Polycom HTTPS/SSH resources on their owning lane.

## 4. CodecScreen integration

- [ ] 4.1 Replace direct `_get_or_create_volume_handler()` use with controller submission and invalidate context on model, IP, credential, and screen lifecycle changes.
- [ ] 4.2 Route TE20/TE40 live audio, sleep detection, and TE20 Wake through bounded recovery without blocking the Qt event loop or showing polling dialogs.
- [ ] 4.3 Route speaker volume, microphone mute/gain, and their follow-up reads through absolute-target and relative-intent reconciliation.
- [ ] 4.4 Route presentation control, sleep/Wake preparation, and follow-up status reads through desired-state reconciliation.
- [ ] 4.5 Route Huawei TE20, TE40, and Bar 310 call logs through the recovered shared session in background execution.
- [ ] 4.6 Preserve Polycom volume/mute/presentation behavior on the shared controller while leaving `PolycomCallLogWorker` and the diagnostic refresh worker separate.

## 5. Regression coverage

- [ ] 5.1 Add credential/transport tests proving saved profiles are first, TE20/TE40 no longer discard them, connect exceptions continue allowed transport fallback, and one credential spans all transports.
- [ ] 5.2 Add controller tests for expired-session invalidation, one reconnect, same-credential-first recovery, confirmed-auth advancement, successful index/profile commits, and no retry loop.
- [ ] 5.3 Add replay tests for read-only retry, absolute target confirmation, unknown state refusal, Wake/presentation reconciliation, and relative volume never applying twice.
- [ ] 5.4 Add offscreen `CodecScreen` tests for responsive background work, live-audio recovery, stale callback rejection, duplicate-poll suppression, model/IP/credential invalidation, and destruction cleanup.
- [ ] 5.5 Add TE20, TE40, Bar 310, and Polycom handler tests for typed session outcomes, single-send state changes, session artifact cleanup, Huawei recovered call logs, and Polycom path separation.
- [ ] 5.6 Rerun and extend credential-fallback, worker retry-ownership, worker-outcome, and four-model interactive-control regression suites.
- [ ] 5.7 Verify synthetic credentials, cookies, Session IDs, CSRF tokens, and SSH material never appear in controller, handler, GUI, terminal, dialog, or test output.

## 6. Validation and rollout evidence

- [ ] 6.1 Update implementation evidence and the architecture report if implementation discoveries change the documented model matrix or conservative classifier.
- [ ] 6.2 Run focused credential, controller, handler, `CodecScreen`, UI-state, retry-ownership, worker-outcome, and redaction tests with the repository-supported Python interpreter.
- [ ] 6.3 Run the full offline unittest suite, `openspec validate codec-interactive-session-recovery --strict`, `openspec validate --all --strict`, and Git diff/hygiene checks.
- [ ] 6.4 Perform authorized opt-in hardware QA beginning with the reproducing TE20, then record redacted TE40, Bar 310, and Polycom observations where devices are available without weakening offline acceptance.
