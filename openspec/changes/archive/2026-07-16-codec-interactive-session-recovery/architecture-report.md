# Codec interactive session recovery architecture report

## Baseline and conclusion

Analysis was performed from clean `origin/master` at merge commit
`eba8a8263e10d95a4bc89668d273f7b216900254`, after reading the archived
`credential-fallback-chains` proposal, design, tasks, delta spec, implementation
evidence, and all current root specifications.

The code-confirmed root cause is a split ownership model. Diagnostic refresh
workers use the credential and transport rules introduced by
`credential-fallback-chains`, while codec interactive features create and cache
another long-lived handler in `CodecScreen` without the same saved-profile,
credential-fallback, failure-classification, and session-recovery contract. A
single invalid cached handler is shared by nearly every reported feature, so
one session failure has the observed multi-feature blast radius.

The change is architecturally ready for implementation. Hardware-specific
session-expiry signatures remain conservative open QA items; they do not block
implementation of the typed, bounded recovery framework and must not be guessed
without redacted evidence.

## Confirmed implementation findings

1. `VCSDiagnosticApp.refresh_data()` resolves every credential candidate before
   ping/network work (`gui/main_window.py:889-914`). Model refresh methods choose
   the saved model/IP index and give one candidate to one worker
   (`gui/main_window.py:1015-1250`).
2. Refresh workers preserve the assigned credential during protocol fallback.
   TE20 loops HTTP and runtime-supported HTTPS and catches a non-auth exception
   per profile (`core/te20_worker.py:59-155`); TE40 falls back HTTPS to HTTP only
   after a non-auth failure (`core/worker.py:91-222`). A final result carries the
   successful profile, and the GUI stores index/profile for model/IP
   (`gui/main_window.py:1489-1547`).
3. Interactive code instead reads only the currently selected credential
   (`gui/screens/codec_screen.py:122-139`) and creates a handler directly. It has
   no ordered candidate loop and cannot advance credentials after confirmed
   interactive login failure.
4. `_get_or_create_volume_handler()` obtains the saved profile and then
   unconditionally clears it for TE20/TE40
   (`gui/screens/codec_screen.py:1628-1633`). Git blame traces the exception to
   the initial sanitized source import, with no later rationale or coverage.
5. A key-matching cached handler is returned immediately without even calling
   its local `is_connected()` predicate (`gui/screens/codec_screen.py:1659-1666`).
   The key proves only model/IP/credential/profile equality, not remote Session
   ID, cookie, CSRF, HTTPS login, or SSH-channel validity.
6. The transport loop calls `handler.connect()` outside a per-profile exception
   boundary (`gui/screens/codec_screen.py:1670-1691`). A raised timeout, SSL, or
   connection error therefore prevents the next supported transport attempt.
7. The same cached handler is used by presentation (`1080-1159`), speaker and
   microphone volume/mute (`1292-1524`), follow-up reads (`1526-1580`), TE20/TE40
   live audio and sleep detection (`1737-1999`), Wake (`1866-1906`), and Huawei
   call logs (`585-631`). This confirms the common failure domain.
8. Huawei call logs run synchronously through that handler in the GUI thread;
   only the Polycom call log has its own background worker
   (`gui/screens/codec_screen.py:633-717`, `core/worker.py:50-88`). The separate
   Polycom worker is not part of the shared-session regression.
9. TE20 retains `requests.Session`, Session ID, CSRF token, and an optional
   pycurl cookie jar (`handlers/huawei/te20.py:81-113, 180-254`); TE40 retains an
   opener, cookie jar, Session ID, CSRF, and cookie-session flag
   (`handlers/huawei/te40.py:52-88, 207-293`); Bar 310 retains a Basic-auth
   `requests.Session`, cookie, and CSRF token (`handlers/huawei/bar310.py:23-68`);
   Polycom retains HTTPS authentication plus lazy SSH client/channel
   (`handlers/polycom/rpg310.py:33-58, 127-200`). These artifacts can expire
   while the local cached-handler key remains unchanged.
10. Failure categories are lost below the controller boundary. TE40
    `send_command()` catches every exception and returns `{}`
    (`handlers/huawei/te40.py:461-543`); TE20 frequently converts non-auth
    failures to `success: 0` (`handlers/huawei/te20.py:714-876`); Bar 310
    `_make_request()` converts request exceptions to normal dictionaries and
    `connect()` can classify an unsuccessful session request as authentication
    (`handlers/huawei/bar310.py:88-164, 227-316`). A caller cannot implement
    correct session recovery from these values.
11. State-changing semantics are not uniform. Most handlers send an absolute
    target then read back state, but Bar 310 presentation can resend Start more
    than once internally (`handlers/huawei/bar310.py:785-823`). Relative volume
    buttons compute an absolute target in the screen
    (`gui/screens/codec_screen.py:1292-1319`), so an ambiguous lost response must
    reconcile original and target values rather than apply another delta.
12. Existing lifecycle hooks reset the shared handler on model selection and
    application close (`gui/main_window.py:545-568, 2542-2550`), but there is no
    equivalent immediate IP/credential invalidation, no typed remote-session
    invalidation, and no shutdown contract for pending background interactive
    work because that work is currently synchronous.
13. Codec refresh fallback still calls `is_authentication_error()` and treats
    message substrings such as `auth`, `401`, `403`, localized words, and numeric
    codes as retry authority (`gui/main_window.py:875-887, 1642-1681`). This can
    advance credentials for a transport/protocol error whose text happens to
    match. The codec migration must derive retry authority from caught typed
    failures while allowing unrelated legacy device paths to retain the helper
    temporarily.

## Current connection/session path map

| Entry point | Credential owner | Transport/session owner | Success memory | Recovery today |
| --- | --- | --- | --- | --- |
| Diagnostic refresh | `VCSDiagnosticApp` ordered candidates and current worker index | One model worker; handler(s) scoped to that worker | GUI stores model/IP index and `connection_profile` after final result | Credential retry on classified auth; model-specific transport fallback |
| Huawei interactive controls/read/poll/call log | `CodecScreen` reads one current candidate | Cached handler from `_get_or_create_volume_handler()` | Reads GUI state but discards saved TE20/TE40 profile; does not commit interactive success | Caller-specific exception reset only; no common reconnect/replay |
| Polycom interactive controls | `CodecScreen` reads one current candidate | Same cached handler; HTTPS login plus lazy SSH | HTTPS profile only | Lazy SSH connect, but no common stale-session recovery/replay policy |
| Polycom call log | `CodecScreen` reads one candidate | Short-lived `PolycomCallLogWorker` and handler | None | One worker attempt; intentionally separate |
| SIP fix | Main-window composition | Separate `CodecSipFixWorker` | None | Separate command path; out of this change |

## Selected architecture

`CodecScreen` will own one application controller with a single serialized
background execution lane. The screen resolves the existing ordered candidates
and reads the existing successful index/profile before any submitted network
work. The controller owns only request-scoped progression and cached handler
lifecycle; handlers remain single-credential protocol adapters and never read
the provider or choose another candidate.

The controller uses an explicit context `(model, IP, private credential
identity, index, profile, generation)`. It reuses a handler only when that
identity and local connected state match. The actual operation is the remote
liveness probe. A confirmed invalid-session response invalidates the entire
model handler and consumes at most one reconnect cycle.

An operation's captured generation is checked twice: on callback delivery and,
normatively, when the serialized controller dequeues it immediately before
handler acquisition or network I/O. If model, IP, or credential context changed
while the operation waited, it is dropped without invoking the handler. An
already in-flight call is not assumed cancellable, so its result is ignored and
all later queued operations from that old generation are discarded before they
can produce device-side effects.

Transport ordering is saved-supported-profile first, then model defaults,
deduplicated. All transport attempts for one candidate use that candidate.
Initial login authentication failure can advance the application attempt plan;
transport failure cannot. An established-session rejection first reconnects
the same candidate and becomes credential fallback only if the new login
itself confirms authentication failure.

For codec refresh, the worker maps a caught typed failure to a stable structured
category and the application uses that category, not message text, to advance
the attempt plan. For interactive work, the controller consumes the typed
exception directly. HTTP 401/403 is authentication failure only during a new
login; during established use it is session invalidation. Generic `success: 0`,
empty/malformed data, localized or arbitrary `auth` text, and transport errors
that merely contain `401` never authorize credential advancement. The existing
string helper may remain for unrelated devices during this minimal migration.

The existing successful-index and profile maps remain the single durable
in-process state. A request-local attempt cursor is separated from those maps,
so a failed next candidate is not mislabeled as successful. Index/profile are
committed only after final successful or successfully reconciled interactive
work.

## Session invalidation and bounded retry policy

- Invalidate on model, IP, selected credential identity, or supported-profile
  change; local disconnected state; confirmed established-session rejection;
  failed recovery; screen destruction; or application shutdown.
- Recheck generation/context at queue execution time and drop stale operations
  before handler acquisition or network I/O, including state-changing commands.
- Distinguish `AuthenticationError`, established `SessionInvalidError`,
  connection/timeout, protocol/parse, normal command rejection, and a command
  whose delivery outcome is unknown.
- Allow one reconnect cycle per submitted operation and no recursive retry.
- Permit transport fallback inside the reconnect cycle with one credential.
- Advance credentials monotonically only after confirmed new-login failure.
- Emit one redacted terminal outcome when recovery is exhausted.
- Suppress duplicate live-audio polls while one is pending.

## Replay/reconciliation policy

| Class | Operations | Policy |
| --- | --- | --- |
| Read-only | live audio, volume/mute status, sleep, presentation status, Huawei call log | Reconnect once and replay the read once. |
| Absolute desired state | speaker target, Bar microphone gain | Read after reconnect; confirm target or set it once only from an authoritative pre-command state. |
| Desired transition with readback | Wake, presentation Start/Stop | Read state first; do not resend if target is reached; send once only from an authoritative opposite state. |
| Toggle/relative intent | mute button, volume +/- | Preserve original and computed target; never resend a toggle/delta. Confirm target, set absolute target only if original remains, otherwise refresh and report conflict. |
| Unknown/no authoritative readback | any state-changing operation | Reconnect may restore the session, but the original command is not replayed; report indeterminate outcome. |

## Model matrix

| Model | Profiles | Session artifacts | Shared interactive consumers | Separate paths |
| --- | --- | --- | --- | --- |
| Huawei TE20 | HTTP:80; HTTPS:443 when runtime stack is ready; saved supported profile first | requests/pycurl cookies, Session ID, CSRF token, cookie jar | live audio, sleep, Wake, speaker, mic mute, presentation, call log | diagnostic refresh worker |
| Huawei TE40 | HTTPS:443, HTTP:80; saved supported profile first | opener/cookies, Session ID, CSRF/certificate state, browser-cookie flag | live audio, presentation sleep preparation, speaker, mic mute, presentation, call log | diagnostic refresh and SIP-fix workers |
| CloudLink Bar 310 | HTTPS:443 | Basic-auth requests session, cookie, CSRF; `X-Access-Token` for call log | presentation sleep preparation, speaker, mic gain, presentation, call log | diagnostic refresh and SIP-fix workers |
| Polycom RPG 310 | HTTPS:443 plus same-credential lazy SSH:22 controls | HTTPS opener/cookies/login flag; SSH client/channel | speaker, mic mute, presentation | diagnostic refresh, SIP fix, and call-log workers remain separate |

## Expected production file impact

- `core/exceptions.py`: typed established-session and unknown-outcome errors.
- `core/credentials.py`: shared request-scoped monotonic attempt plan.
- `core/codec_connection_profiles.py` (new): pure supported/saved-first profile ordering.
- `core/interactive_session.py` (new): serialized controller, operation
  descriptors, recovery budget, reconciliation, and redacted signals.
- `core/te20_worker.py` and `core/worker.py`: reuse profile ordering and preserve
  the validated refresh contract without broad worker refactoring.
- `core/base_handler.py`: only if a narrow common local-session predicate or
  cleanup contract is needed.
- `gui/main_window.py`: expose/commit shared request context, keep successful
  index separate from attempt cursor, and coordinate invalidation/shutdown.
- `gui/screens/codec_screen.py`: replace direct synchronous handler calls with
  typed asynchronous operations and generation-safe UI callbacks.
- `handlers/huawei/te20.py`, `handlers/huawei/te40.py`,
  `handlers/huawei/bar310.py`, `handlers/polycom/rpg310.py`: preserve protocols
  while surfacing typed session outcomes and single-send command semantics.

No credential schema, persistent storage, dependency, reference driver, or
separate Polycom call-log worker redesign is expected.

## Required test impact

- New `tests/test_interactive_session.py`: context identity, serialized work,
  saved-profile ordering, transport exception continuation, one credential,
  auth advancement, one reconnect, no recursion, state commits, and redaction.
- New focused handler recovery tests for TE20, TE40, Bar 310, and Polycom:
  session artifacts, typed invalidation, single-send controls, readback, and
  cleanup.
- Extend `tests/test_codec_screen.py`: responsive controls/call logs, duplicate
  polling suppression, live-audio recovery, Wake path, stale callback rejection,
  model/IP/credential invalidation, and screen destruction.
- Extend `tests/test_credential_fallback_retry.py`: request cursor versus
  successful index, structured codec retry authority, transport text containing
  `401`, established-session 401/403 invalidation, malformed/unstructured
  outcomes, and interactive ownership.
- Cover queued stale read-only and state-changing operations whose generation
  changes before execution; assert no handler call and no network I/O occurs.
- Re-run `tests/test_credentials.py`, `tests/test_credential_propagation.py`,
  `tests/test_credential_worker_retry_ownership.py`,
  `tests/test_worker_outcomes.py`, `tests/test_ui_states.py`, and
  `tests/test_hardware_log_redaction.py` to prove no rollback or secret leak.
- Add explicit regression scenarios for TE20/TE40 saved profile, Bar 310
  one-profile behavior, Polycom control/session behavior, and the unchanged
  separate Polycom call-log path.

## Risks, trade-offs, and open questions

- A serialized background controller is more code than a local try/except, but
  it prevents GUI blocking and concurrent use of one non-thread-safe handler.
- Handler normalization can expose latent behavior previously hidden by empty
  dictionaries; focused success and failure tests must precede GUI routing.
- Exact firmware expiry codes are not uniform. Only confirmed 401/403 and
  redacted verified signatures belong in the classifier.
- State reconciliation adds reads and latency after an exceptional failure, but
  avoids double volume deltas, toggles, Wake, or presentation commands.
- TE20 is the reproducing hardware and should be the first opt-in QA target.
  TE40, Bar 310, and Polycom require redacted observations where available.

## Planning validation evidence

Validation was rerun from the change branch worktree with the tracked
repository-local OpenSpec wrapper. No global `openspec` executable or
`npx @latest` command was used.

- Exact command: `.\openspec.cmd validate codec-interactive-session-recovery --strict`
  - Result: `Change 'codec-interactive-session-recovery' is valid` (exit code 0).
- Exact command: `.\openspec.cmd validate --all --strict`
  - Result: 7 passed, 0 failed (7 items; exit code 0).

These commands were executed again after the review-driven planning revisions.
This report is the authoritative change-artifact validation evidence; the PR
description's earlier unqualified `openspec validate ...` command text should
be replaced with the repository-local forms when the revised branch is
published. No production code was changed or executed as implementation work.

## Readiness verdict

**READY FOR IMPLEMENTATION.** The ownership boundary, transport order,
invalidation rules, one-cycle recovery budget, replay/reconciliation policy,
model matrix, production impact, and regression plan are explicit. The engineer
must keep the conservative failure classifier and record any newly discovered
hardware signature rather than broadening authentication/session matching by
message substring.
