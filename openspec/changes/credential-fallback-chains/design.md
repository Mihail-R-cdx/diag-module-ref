## Context

The GUI already keeps an ordered `creds_list` and retries the next entry only
after its existing authentication-failure classification.  However, the
composition layer supplies only one resolved credential because the JSON
provider accepts only a string-valued device mapping.  The change must extend
that boundary without duplicating retries in device handlers or exposing
credential metadata in public output.

## Goals / Non-Goals

**Goals:**

- Accept a string or any-length non-empty list of profile names for a device.
- Resolve and validate every candidate before a worker can begin network I/O.
- Preserve the single-candidate provider and GUI interfaces for existing
  providers, callers, and direct test overrides.
- Feed the ordered, redacted-safe handler kwargs into the existing retry state.

**Non-Goals:**

- Change device protocols, retry classification, storage encryption, or add a
  runtime dependency.
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

### Preserve mode-specific kwargs

Candidate conversion delegates to `Credential.as_handler_kwargs()`.  Thus a
password-only candidate contains only `password`, and an unauthenticated
candidate contains no credential keys.  This avoids manufacturing fields that
could change handler contracts.

## Risks / Trade-offs

- [An invalid later profile could otherwise permit partial connection] → parse
  the entire sequence before returning it.
- [A legacy provider lacks the plural method] → provide the base-class
  one-element fallback.
- [Credential metadata could leak during retry] → display only attempt number
  and total, and test public signal/error paths with synthetic values.

## Migration Plan

1. Add plural resolution and schema validation with unit tests.
2. Pass candidate kwargs through GUI composition and cover legacy-provider and
   direct-override compatibility.
3. Verify all production paths continue to receive the existing retry fields.
4. Update the tracked example and run focused, full offline, and strict
   OpenSpec validation. Rollback is safe because string mappings and
   single-candidate APIs remain supported.

## Open Questions

- None; the current GUI retry implementation already supplies the required
  state and is intentionally reused.
