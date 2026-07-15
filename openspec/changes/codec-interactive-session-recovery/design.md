## Context

`credential-fallback-chains` established the correct ownership boundary for
diagnostic refreshes: the GUI/application composition layer resolves an ordered
candidate list before network I/O, a worker receives one credential, transport
fallback keeps that credential, and only the application advances the
credential index after confirmed authentication failure.

Interactive codec work does not use that path. `CodecScreen` synchronously
selects the currently saved credential and funnels volume, mute, presentation,
live audio, sleep/Wake, and Huawei call-log calls through the historically named
`_get_or_create_volume_handler()`. That method:

- fetches but then deliberately discards the saved profile for TE20 and TE40;
- caches one handler by model, IP, credential values, and profile list;
- returns a key-matching handler without testing even its local connected flag;
- lets an exception from `connect()` escape the transport loop; and
- has no common way to classify an expired session, invalidate the cache,
  reconnect, or decide whether to replay the original operation.

The handlers compound the problem. TE20 stores a `requests.Session`, Session ID,
CSRF token, and optional pycurl cookie jar; TE40 stores an opener, cookie jar,
Session ID, CSRF token, and browser-session flag; Bar 310 stores a
`requests.Session`, cookie, and CSRF token; Polycom stores an HTTPS opener/login
flag and a lazy SSH client/channel. Several command paths convert exceptions or
invalid sessions to `{}`, `False`, `None`, or `success: 0`, so the caller loses
the distinction between authentication, established-session invalidation,
transport failure, protocol failure, and a normal command rejection.

The interactive calls also run in the Qt GUI thread today. Recovery must not
add more synchronous I/O or allow timer polling and button commands to use the
same handler concurrently.

## Goals / Non-Goals

**Goals:**

- Make one application-owned component responsible for interactive handler
  creation, credential attempt progression, transport fallback, cached-session
  lifecycle, recovery, and terminal outcome classification.
- Reuse the ordered candidates, successful index, and saved connection profile
  owned by `VCSDiagnosticApp`; do not create a second credential registry.
- Execute every operation for one cached handler serially outside the GUI
  thread and reject stale callbacks after model/IP/context changes.
- Detect local closure and device-reported session invalidation, invalidate the
  cache, and allow at most one reconnect cycle for one submitted operation.
- Separate reconnection from replay. Replay read-only operations once, and use
  read-after-reconnect reconciliation for state-changing intent.
- Preserve model-specific transports and session mechanisms for TE20, TE40,
  Bar 310, and Polycom RPG 310.
- Keep credentials, cookies, Session IDs, CSRF tokens, and derived private
  session identity out of logs, signals, dialogs, and results.

**Non-Goals:**

- Roll back or replace `credential-fallback-chains`, change the credential JSON
  schema, or move candidate iteration into a handler.
- Build an application-wide retry framework or refactor unrelated workers.
- Add persistent session storage, dependencies, or automatic hardware tests.
- Redesign the separate Polycom call-log worker or the Polycom diagnostic
  HTTPS-plus-SSH refresh worker.
- Treat every protocol error or unsuccessful command result as an expired
  session.

## Decisions

### Use one serialized application-owned interactive session controller

Add a focused controller/operation worker in `core/interactive_session.py`.
`CodecScreen` owns its lifetime but not its handler internals. The controller
runs on one dedicated background execution lane, creates and uses the cached
handler on that same lane, and serializes polling, reads, and commands. The GUI
submits immutable operation descriptors and receives redacted result/error
signals containing an operation ID and public context generation.

`CodecScreen` resolves credentials through the existing main-window
composition boundary before submitting work. The controller receives the
already validated candidates, the valid saved starting index, and the saved
profile; it never imports or reads `JsonCredentialProvider`. Candidate
advancement remains application behavior inside this controller, while every
handler receives exactly one assigned candidate.

The main window and controller will share a small request-scoped credential
attempt-plan abstraction rather than duplicate retry policy. The plan has a
starting index, a monotonic current index, and attempted indexes. It never wraps
and commits `current_credential_index` only after a successful final operation.
The existing per-device/IP maps remain the only successful-index and profile
memory. Diagnostic refreshes can adopt the same request-local cursor so an
unsuccessful next attempt is not confused with a successfully cached index.

Alternative considered: extend `_get_or_create_volume_handler()` in place.
Rejected because it would retain blocking GUI I/O, allow timer/button
concurrency, and scatter recovery and replay decisions across each caller.

### Define explicit interactive context and cache identity

An interactive context contains:

- model and IP address;
- the fully resolved ordered credential candidates and selected index;
- a private, non-renderable identity for the assigned credential;
- ordered supported transport candidates and the chosen profile; and
- a monotonically increasing GUI context generation.

The private credential identity may compare the in-memory selected handler
kwargs or use a process-local opaque fingerprint; it MUST NOT be logged,
serialized, persisted, or emitted. The handler already holds the credential,
so no public secret-bearing cache key is needed.

A cached handler is eligible for reuse only when model, IP, assigned credential
identity, and selected transport match and its local connected predicate is
true. Local truth is only a fast rejection check: the submitted operation is
the authoritative liveness probe. A key match alone never proves that cookies,
Session ID, CSRF token, HTTPS authentication, or SSH channel remain valid.

Model change, IP change, candidate change, selected-index change, unsupported
saved profile, screen destruction, application shutdown, local disconnected
state, session-invalid outcome, or failed recovery invalidates and disconnects
the cached handler. The generation is incremented before invalidation so late
results cannot update the new screen context.

Alternative considered: perform a network health request before every command.
Rejected because it doubles normal traffic and still races with the real
operation. Typed failure from the real operation provides the liveness signal.

### Reuse saved transport profiles and keep fallback credential-stable

Use one pure model-profile ordering helper for refresh and interactive paths.
It filters the saved profile against the currently supported model/runtime
profiles, places a supported saved profile first, appends model defaults, and
deduplicates by port and SSL mode.

The interactive profile matrix is:

| Model | Supported profiles and default order | Session mechanism |
| --- | --- | --- |
| Huawei TE20 | HTTP:80, then HTTPS:443 when the TE20 HTTPS stack is ready; a supported saved profile is first | `requests.Session` and cookies for HTTP; optional pycurl cookie jar for HTTPS; Session ID and CSRF token |
| Huawei TE40 | HTTPS:443 then HTTP:80; a supported saved profile is first | urllib opener and cookie jar; Session ID plus certificate/CSRF state; browser-cookie fallback |
| CloudLink Bar 310 | HTTPS:443 only | Basic-auth `requests.Session`, session cookie, CSRF token; `X-Access-Token` for the v1 call-log endpoint |
| Polycom RPG 310 | HTTPS:443 for handler login; SSH:22 is a same-credential secondary session opened lazily by controls | HTTPS opener/cookies/login flag plus serialized SSH client/channel |

For one candidate, non-authentication connection failure or exception may move
to the next supported profile. Confirmed authentication failure stops that
transport loop immediately and asks the application attempt plan for the next
higher credential. A transport failure never advances credentials. The current
TE20/TE40 `preferred_profile = None` special case has no supporting history or
handler constraint and will be removed with regression coverage.

The successful profile and credential index are committed to the existing
model/IP maps only after the submitted operation produces a final successful or
successfully reconciled outcome. A partial result, failed command, or failed
recovery does not commit either value.

### Preserve credential-fallback-chains ownership during reconnect

Initial connection starts at the valid successful index for the exact model/IP
pair and considers only that suffix of the resolved chain. Each candidate gets
its complete transport sequence with the same assigned credential. Only a
confirmed authentication failure while establishing a new session permits the
application attempt plan to advance. No candidate is attempted twice.

An established-session 401/403 or model-specific invalid-session response is
not immediately a credential failure. The controller first invalidates the
handler and reconnects once with the same credential. If that new login returns
a confirmed authentication failure, and a later candidate remains, the same
application attempt plan may advance monotonically. This preserves the
distinction between expired session state and invalid current credentials.

No worker or handler reads the candidate list, changes the index, commits a
successful index, or wraps the chain. Candidate values are passed only through
existing constructor inputs. This is an extension of the existing owner, not a
second handler-owned retry loop.

### Make failure classification observable to the controller

Add typed interactive failure boundaries in `core/exceptions.py` and normalize
the four handlers so they do not swallow recoverable failures:

- `AuthenticationError`: a confirmed failure while establishing a new session;
- `SessionInvalidError`: an established session is rejected or required
  session artifacts are no longer accepted;
- `ConnectionError`/timeout: transport cannot be established or maintained;
- `ProtocolError`/parse failure: the peer response cannot satisfy the protocol;
- `CommandError`: the device provided a valid negative command outcome; and
- `CommandOutcomeUnknownError`: a state-changing request may have reached the
  device but no authoritative response was received.

HTTP 401/403 during initial login is authentication failure; the same status
during an established operation is session invalidation. Known device codes
may be added only with redacted evidence and tests. Unknown `success: 0`, empty,
or non-JSON results are not guessed to be authentication failures. Handler
methods may perform one readback to interpret a valid command response, but may
not reconnect, advance credentials, or repeatedly send a state-changing command
after transport/session failure. In particular, Bar 310 presentation control
must stop its current internal repeated set-command loop.

Alternative considered: retain message-substring classification in callers.
Rejected because localized text and generic `success: 0` cannot reliably
separate expired session, authentication, transport, and device rejection.

### Bound recovery independently from replay

Every submitted operation owns a recovery budget initialized to one. On local
closure, `SessionInvalidError`, or a recoverable connection loss, the controller
invalidates the cache and may perform one reconnect cycle. That cycle includes
the allowed same-credential transport sequence and, only after confirmed new
login failure, monotonic remaining credential candidates. Once consumed, no
exception handler, readback, timer callback, or recursive command can reconnect
again for that operation.

The replay budget is separately at most one and is governed by the operation
descriptor. A reconnect can succeed while replay remains forbidden. A failed
operation emits one terminal redacted outcome; timer polling does not display a
modal dialog. Only one live-audio poll may be pending, so the two-second timer
cannot build an unbounded queue while the device is unavailable.

### Apply an operation-specific replay and reconciliation policy

| Operation | Semantic class | After successful reconnect |
| --- | --- | --- |
| live audio, speaker/microphone read, sleep read, presentation read, Huawei call log | Read-only | Replay once automatically. |
| set speaker volume to an absolute value | Absolute desired state | Read current value; if target is already present, report success; if an authoritative read shows the known pre-command value, set the absolute target once; otherwise report an indeterminate/conflict outcome. |
| microphone mute/unmute or Bar 310 gain | Absolute desired state derived from UI intent | Read current mute/gain; confirm target or issue the absolute target once only when current state is authoritative; never replay a toggle. |
| presentation Start/Stop | Desired state with readback | Read presentation state; confirm target or issue one Start/Stop only when the opposite state is authoritative; do not replay when state is unknown. |
| Wake | Desired awake state with readback | Read sleep state; if awake, succeed; if authoritatively still asleep, send Wake once; otherwise report unknown. |
| volume +/- button | Relative user intent converted to an absolute target | Preserve pre-command and target values. After reconnect, succeed if target is present; set the target once only if the original value is still present; if state moved elsewhere, refresh the display and do not apply the delta again. |

The controller records whether a state-changing request was definitely not
sent, received a valid negative response, or has an unknown delivery outcome.
No state-changing operation is blindly replayed. Readback itself is read-only
and consumes no additional reconnect budget; if readback loses the recovered
session, the operation terminates.

### Route all shared interactive consumers through the same contract

`CodecScreen` will submit operation descriptors for volume reads/sets, mute,
presentation reads/sets, live audio, sleep detection, Wake, and Huawei call
logs. It will update UI state only from a matching model/IP/generation result.
The existing presentation and volume follow-up timers become read-only
operations on the controller rather than direct handler calls.

Huawei TE20 and TE40 use live-audio polling; Bar 310 does not. TE20 exposes the
dedicated Wake row; TE20, TE40, and Bar 310 may also use sleep/Wake while
preparing presentation. Huawei call logs use the recovered shared session.
Polycom volume, mute, and presentation use the serialized shared handler and
its same-credential SSH sub-session. Polycom call logs continue through the
separate short-lived `PolycomCallLogWorker`, and the separate Polycom refresh
worker remains HTTPS status plus SSH enrichment.

### Model, IP, credential, and destruction behavior

- Model change: stop polling, increment generation, cancel/ignore queued old
  operations, and disconnect the old handler before accepting the new model.
- IP change: invalidate before the next operation and wire the IP edit signal so
  the old handler is not retained as an apparently current session.
- Credential change: re-resolve before operation submission; a different
  selected candidate identity invalidates the old handler. The numeric saved
  index remains usable only when valid for the new list.
- `CodecScreen` destruction/application close: stop timers, reject new work,
  request controller shutdown, disconnect the handler and Polycom SSH resources
  on their owning lane, then stop the lane. Late callbacks are ignored.

### Security and observability boundary

Public operation context contains model, IP, operation kind, attempt ordinal,
transport label, and redacted error category only. Credential values, private
credential identity, request payloads, response bodies, cookies, Session IDs,
CSRF tokens, and Polycom session material never cross result/error/log/dialog
signals. All four handlers redact before optional diagnostic callbacks, and
tests use synthetic credentials and session artifacts.

## Risks / Trade-offs

- [A dedicated serialized lane adds lifecycle code] → keep one controller per
  `CodecScreen`, use operation/generation IDs, and cover shutdown with offscreen
  tests.
- [Handler return conventions are currently inconsistent] → introduce typed
  boundaries incrementally and add handler-level tests before routing GUI calls.
- [A device may use an undocumented session-expiry code] → classify only
  confirmed signatures; capture redacted hardware evidence and fail safely for
  unknown responses.
- [A reconnect after an ambiguous command cannot prove the first outcome] →
  reconcile with authoritative readback and never blindly replay.
- [Moving controls off the GUI thread changes timing and button behavior] →
  serialize operations, expose busy state, reject duplicate poll requests, and
  retain current follow-up delays as queued read operations.
- [Reusing a saved profile that is no longer supported could block fallback] →
  filter it through the current model/runtime capability list before ordering.
- [Polycom has two live protocol sessions] → treat the handler as one cached
  unit and serialize HTTPS/SSH use; a failed secondary session consumes the same
  bounded recovery policy.
- [Changing refresh retry cursor handling touches validated behavior] → preserve
  the existing order and tests, add request-local cursor coverage, and commit
  the successful index only on final success.

## Migration Plan

1. Add typed session/outcome errors, the pure transport-order helper, and
   request-scoped credential attempt plan with unit tests.
2. Normalize handler failure and single-send/readback behavior for the four
   models without changing successful command payloads.
3. Add the serialized interactive controller and model adapters; verify
   transport, credential, invalidation, recovery, and replay policy offline.
4. Route `CodecScreen` consumers to asynchronous operation descriptors and add
   stale-callback, timer, button, and shutdown coverage.
5. Run focused and full offline tests plus strict OpenSpec validation; then
   perform opt-in read-only and controlled command QA on TE20, followed by TE40,
   Bar 310, and Polycom where available.

Rollback removes the controller routing and typed adapter changes together;
the credential schema, saved maps, and diagnostic worker contracts remain
compatible. No session state requires migration.

## Open Questions

- Which additional redacted Huawei firmware response codes, beyond established
  HTTP/session evidence, definitively mean session invalidation rather than a
  command rejection? Unknown codes remain non-authentication failures until
  hardware evidence is recorded.
- Does each available TE20/TE40 firmware preserve the saved HTTPS/HTTP profile
  after long idle periods, and does Bar 310 report token expiry distinctly from
  a missing/incorrect `X-Access-Token`? These are hardware QA questions, not a
  reason to weaken the conservative classifier.
- Does real Polycom firmware always provide authoritative readback after a lost
  CLI response for presentation, volume, and mute? If not, the designed
  indeterminate outcome remains the safe behavior and automatic replay stays
  disabled for that case.
