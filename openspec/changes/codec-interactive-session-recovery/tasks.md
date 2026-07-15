## 1. Shared credential and transport contracts

- [x] 1.1 Add typed authentication, established-session, transport, protocol, command, and unknown-command-outcome boundaries, including phase-sensitive new-login versus established-session handling of HTTP 401/403.
- [x] 1.2 Add a stable structured codec failure category derived from caught typed failures; migrate codec refresh retry authority away from `is_authentication_error()` message matching while preserving the legacy helper only for unrelated device paths.
- [x] 1.3 Add a request-scoped monotonic credential attempt plan and integrate refresh retry so only final success commits the existing model/IP successful index.
- [x] 1.4 Extract and test model-specific codec transport ordering, including runtime-supported TE20 HTTPS, saved-profile-first selection, and deduplication.

## 2. Handler failure and command semantics

- [x] 2.1 Normalize TE20 initial authentication, established-session invalidation, transport, protocol, command, and cleanup outcomes while preserving one-send/readback controls.
- [x] 2.2 Normalize TE40 cookie/Session ID/CSRF and browser-session outcomes so command failures are typed instead of swallowed as empty dictionaries.
- [x] 2.3 Normalize Bar 310 session/token and REST outcomes, preserve `X-Access-Token` call logs, and replace repeated presentation sends with one send plus readback.
- [x] 2.4 Normalize Polycom HTTPS/SSH session outcomes while retaining same-credential lazy SSH control and the separate call-log worker.

## 3. Serialized interactive session controller

- [x] 3.1 Implement one background serialized controller lane with operation IDs, context generations, duplicate-poll suppression, and redacted public signals; revalidate generation/context at dequeue immediately before handler acquisition or network I/O and drop all queued work from superseded generations.
- [x] 3.2 Implement handler acquisition with context identity checks, saved-profile-first transport fallback, one assigned credential per handler, and final-success state commits.
- [x] 3.3 Implement cache invalidation and a non-recursive one-cycle recovery budget for local closure, invalid session, and recoverable connection loss.
- [x] 3.4 Implement read-only replay and state-changing readback/reconciliation descriptors, including conflict-safe relative volume and toggle behavior.
- [x] 3.5 Implement deterministic controller shutdown that closes Huawei session artifacts and Polycom HTTPS/SSH resources on their owning lane.

## 4. CodecScreen integration

- [x] 4.1 Replace direct `_get_or_create_volume_handler()` use with controller submission and invalidate context on model, IP, credential, and screen lifecycle changes.
- [x] 4.2 Route TE20/TE40 live audio, sleep detection, and TE20 Wake through bounded recovery without blocking the Qt event loop or showing polling dialogs.
- [x] 4.3 Route speaker volume, microphone mute/gain, and their follow-up reads through absolute-target and relative-intent reconciliation.
- [x] 4.4 Route presentation control, sleep/Wake preparation, and follow-up status reads through desired-state reconciliation.
- [x] 4.5 Route Huawei TE20, TE40, and Bar 310 call logs through the recovered shared session in background execution.
- [x] 4.6 Preserve Polycom volume/mute/presentation behavior on the shared controller while leaving `PolycomCallLogWorker` and the diagnostic refresh worker separate.

## 5. Regression coverage

- [x] 5.1 Add credential/transport tests proving saved profiles are first, TE20/TE40 no longer discard them, connect exceptions continue allowed transport fallback, and one credential spans all transports.
- [x] 5.2 Add codec refresh and interactive classification tests proving only a typed confirmed new-login `AuthenticationError` advances credentials; cover transport text containing `401`, established-session 401/403 invalidation, generic `success: 0`, empty/malformed responses, and arbitrary `auth` text without advancement.
- [x] 5.3 Add controller tests for expired-session invalidation, one reconnect, same-credential-first recovery, confirmed-auth advancement, successful index/profile commits, no retry loop, and dequeue-time rejection of stale read-only and state-changing operations before handler/network invocation.
- [x] 5.4 Add replay tests for read-only retry, absolute target confirmation, unknown state refusal, Wake/presentation reconciliation, and relative volume never applying twice.
- [x] 5.5 Add offscreen `CodecScreen` tests for responsive background work, live-audio recovery, stale callback rejection, duplicate-poll suppression, model/IP/credential invalidation, and destruction cleanup.
- [x] 5.6 Add TE20, TE40, Bar 310, and Polycom handler tests for typed session outcomes, single-send state changes, session artifact cleanup, Huawei recovered call logs, and Polycom path separation.
- [x] 5.7 Rerun and extend credential-fallback, worker retry-ownership, worker-outcome, and four-model interactive-control regression suites.
- [x] 5.8 Verify synthetic credentials, cookies, Session IDs, CSRF tokens, and SSH material never appear in controller, handler, GUI, terminal, dialog, or test output.

## 6. Validation and rollout evidence

- [x] 6.1 Update implementation evidence and the architecture report if implementation discoveries change the documented model matrix or conservative classifier.
- [x] 6.2 Run focused credential, controller, handler, `CodecScreen`, UI-state, retry-ownership, worker-outcome, and redaction tests with the repository-supported Python interpreter.
- [x] 6.3 Run the full offline unittest suite, `.\openspec.cmd validate codec-interactive-session-recovery --strict`, `.\openspec.cmd validate --all --strict`, and Git diff/hygiene checks using the tracked repository-local wrapper.
- [x] 6.4 Perform authorized opt-in hardware QA beginning with the reproducing TE20, then record redacted TE40, Bar 310, and Polycom observations where devices are available without weakening offline acceptance.
