## Context

The GUI keeps an ordered `creds_list` and retries the next entry only after its
authentication-failure classification. The composition layer originally
supplied only one resolved credential because the JSON provider accepted only
a string-valued device mapping. After plural resolution was added, the TE20
and Bar 310 workers still iterated the same list independently, competing with
the GUI retry flow and permitting repeated or non-authentication retries. The
change must therefore extend the provider boundary while keeping credential
fallback under one owner and without exposing credential metadata in public
output.

## Goals / Non-Goals

**Goals:**

- Accept a string or any-length non-empty list of profile names for a device.
- Resolve and validate every candidate before a worker can begin network I/O.
- Preserve the single-candidate provider and GUI interfaces for existing
  providers, callers, and direct test overrides.
- Feed the ordered, redacted-safe handler kwargs into the existing retry state.
- Make one worker instance correspond to exactly one credential attempt, with
  the GUI/application composition layer as the only owner of credential index
  advancement.
- Keep protocol or transport fallback distinct from credential fallback and
  preserve the current credential across all protocol attempts.

**Non-Goals:**

- Change device protocol ordering, storage encryption, or add a runtime
  dependency.
- Create, read in workers, or commit a real local credential file.

## Decisions

### Add a plural provider contract

`CredentialProvider.resolve_candidates()` will default to a one-element
sequence containing `resolve()`.  This retains compatibility with test and
future providers that implement only `resolve()`.  `JsonCredentialProvider`
will override the plural method; its existing `resolve()` returns the first
candidate from that method.  A request-scoped plural helper applies priority:
explicit credentials, explicit profile, then device mapping.

### Validate all names and profiles atomically

The JSON provider loads the document once per plural call.  It converts a
string mapping to a one-name sequence, validates list shape and every name,
then parses every referenced profile before returning anything.  An invalid
element or profile raises the existing safe configuration error, so no partial
credential list reaches a worker.

### Reuse GUI retry state

GUI composition will add a plural conversion method using
`Credential.as_handler_kwargs()` for every candidate and make the request
store use it.  Existing worker fields (`creds_list`, current index, device and
IP context) continue to govern retry, attempt display, de-duplication, stale
callback rejection, and successful-index caching.  No handler receives a
profile name or reads JSON.

The GUI/application composition layer is the sole owner of credential
fallback. It creates a worker with the current candidate and may advance only
to the next larger index after a confirmed authentication failure. A request
that begins at a saved index does not wrap around to earlier candidates; it
terminates after the remaining suffix of the chain. This monotonic ordering
ensures every request completes after a finite number of attempts and no
candidate is attempted more than once in that request.

Each worker uses only the `username` and `password` passed for its assigned
candidate. A worker may retain `creds_list` for redacting the complete active
chain and retain `current_idx` as immutable request context, but it does not
select from the list, change the index, or cache a successful index. A worker
emits at most one terminal result or error. A confirmed authentication failure
returns one `authentication_error` to the GUI; a timeout, SSL, connection,
parsing, transport, or protocol failure returns a non-authentication error and
terminates the credential chain.

### Keep protocol fallback credential-stable

Protocol or transport fallback is local to a worker and is not credential
fallback. TE20 may try its existing HTTP/HTTPS connection profiles, but every
profile uses the worker's one assigned username/password pair. A confirmed
authentication failure ends that worker immediately and returns control to the
GUI. A non-authentication failure may move to another supported transport for
the same credential when the worker already supports that behavior, but it
never selects another credential.

TE40 follows the same ownership boundary with an explicit HTTPS-to-HTTP
transport fallback. A confirmed HTTPS authentication failure ends the worker
immediately and returns one `authentication_error`; HTTP is not attempted in
that case. A non-authentication HTTPS transport failure may fall back to HTTP
with the same assigned credential. The HTTP outcome is then authoritative: an
HTTP authentication failure returns `authentication_error`, while an HTTP
timeout, SSL, connection, parsing, transport, or protocol failure returns a
non-authentication error. A later failure never masks or replaces an earlier
confirmed authentication failure because protocol fallback does not run after
that failure.

### Separate successful results from failed attempts

A final worker `result` is a success contract: device data was obtained and
parsed successfully, and only that final non-partial result permits the GUI to
cache the assigned credential index or enter the connected state. An
authentication or non-authentication failure is emitted through the worker
`error` signal and is never encoded as a final result dictionary.

Polycom may emit an explicitly marked `_partial_update` after its HTTPS stage.
That partial payload can update the screen while the SSH stage continues, but
it does not cache the credential, enter the connected state, or show a success
dialog. If SSH, parsing, protocol, or transport work then fails, the worker
emits one redacted error and no final non-partial result; the GUI transitions
from loading to the corresponding error state. As a defensive compatibility
boundary, the GUI also rejects a result payload explicitly marked with
`_outcome: error` instead of treating it as success; no localized message
matching is used.

### Preserve mode-specific kwargs

Candidate conversion delegates to `Credential.as_handler_kwargs()`.  Thus a
password-only candidate contains only `password`, and an unauthenticated
candidate contains no credential keys.  This avoids manufacturing fields that
could change handler contracts.

### Isolate retry state and terminal errors by request context

Successful credential indexes are scoped to the exact device/IP pair whenever
an IP address is available. A device-only index remains a legacy value for
callers without an IP address, but is never used as a fallback for an
IP-specific request. Refresh and command paths treat an index outside the
current candidate sequence as zero, so a changed chain cannot cause an index
error. Existing request-id checks continue to reject stale callbacks, and a
partial result does not cache a candidate as successful.

Before TE20 or Extron error text reaches a terminal, status, or dialog, the
GUI redacts the error with every credential value in the active candidate
chain supplied as explicit secrets. This supplements the centralized
structured-text redaction for error formats that do not label their values.

## Risks / Trade-offs

- [An invalid later profile could otherwise permit partial connection] → parse
  the entire sequence before returning it.
- [A legacy provider lacks the plural method] → provide the base-class
  one-element fallback.
- [Credential metadata could leak during retry] → display only attempt number
  and total, and test public signal/error paths with synthetic values.
- [Two retry owners could repeat candidates or retry after transport errors] →
  workers perform one credential attempt and only the GUI advances the index.
- [A saved index could wrap to candidates already skipped in this request] →
  advance monotonically through only the remaining suffix of the chain.
- [A worker could encode a failed attempt as device data] → final `result`
  means successful acquisition and parsing; every failure uses `error`.
- [A Polycom partial update could be mistaken for completion] → partial
  payloads remain loading-only, and a later failure produces an error state
  without credential caching or a success dialog.

## Migration Plan

1. Add plural resolution and schema validation with unit tests.
2. Pass candidate kwargs through GUI composition and cover legacy-provider and
   direct-override compatibility.
3. Verify all production paths continue to receive the existing retry fields.
4. Remove worker-owned credential iteration from TE20 and Bar 310 and add
   worker-level retry-ownership tests.
5. Update the tracked example and run focused, full offline, and strict
   OpenSpec validation. Rollback is safe because string mappings and
   single-candidate APIs remain supported.

## Open Questions

- None; the current GUI retry implementation already supplies the required
  state and is intentionally reused.
