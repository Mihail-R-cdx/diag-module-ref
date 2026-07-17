## Why

Operators need a safe way to turn every available PDU outlet on or off from the
shared PDU screen without clicking each outlet one by one. Aten PE8208AV and
Extron IPL T PCS4i already expose individual outlet ON/OFF controls through the
shared PDU path, but a bulk action needs stronger orchestration rules than a
GUI loop over individual button handlers.

The existing PDU safety contract limits state-changing sends for one user PDU
operation. This change clarifies that a bulk operation is one application-owned
orchestration sequence composed of multiple independent outlet sub-operations,
where each outlet sub-operation keeps its own existing bounded safety budget.

## What Changes

- Add sequential bulk ON and bulk OFF controls to the existing `PDUScreen`.
- Define a background application/composition-owned bulk orchestration sequence
  for Aten PE8208AV and Extron IPL T PCS4i.
- Build the outlet sequence from the actual outlet records returned for the
  current PDU, ordered by outlet number, instead of hard-coding outlet counts.
- Require one second between completed outlet sub-operations, with no delay
  before the first outlet and no extra delay after the final outlet.
- Preserve existing per-outlet absolute ON/OFF safety policy, readback,
  reconciliation, indeterminate handling, and secret redaction.
- Define fail-fast, partial-result, no-rollback, stale-context, GUI locking,
  credential ownership, and refresh-after-completion behavior.

## Impact

The change is specification-only. It prepares implementation and tests for a
future approved implementation session. Production code and tests are not
changed by this proposal.

## Non-Goals

- Do not implement production code in this change.
- Do not implement tests in this change.
- Do not archive, merge, or mark this architecture as approved.
- Do not add handler-level `turn_all_on()` or `turn_all_off()` orchestration
  commands only to support bulk UI behavior.
- Do not add PCS4i REBOOT or change existing capability semantics.
- Do not merge Aten HTTPS and PCS4i Telnet/HTTP protocols behind a common
  transport abstraction.
- Do not block the Qt GUI thread for inter-outlet delays.
- Do not run independent concurrent workers for each outlet.
- Do not roll back or replay already completed outlet sub-operations after a
  later outlet fails.
- Do not use string heuristics for credential fallback.
- Do not disclose credentials, cookies, session identifiers, CSRF tokens, or
  other secrets in results, errors, logs, dialogs, or validation evidence.
