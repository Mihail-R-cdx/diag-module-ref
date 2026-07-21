## Context

The DMP worker is already isolated in `core/workers/dmp.py`, but `gui/main_window.py` still owns DMP generation, cancellation, worker submission, stale callback checks, retry dispatch, and successful-credential persistence. Credential configuration changes currently invalidate Matrix and PDU contexts but not the active DMP polling context, so the implementation does not fully satisfy the existing credential-context stale-isolation contract.

The current `ExtronDMP64PlusMeterWorker` emits a structured `error` before entering its `finally` cleanup, then disconnects the handler/session, and only after cleanup emits `finished`. Therefore credential fallback must not launch candidate N+1 directly from the `error` callback or two DMP workers/sessions may overlap during cleanup.

## Goals

- Add a focused DMP-specific application controller.
- Move DMP polling lifecycle and callback authority out of generic `VCSDiagnosticApp` handlers.
- Invalidate active DMP polling on model, IP, credential-context, repeat Refresh, relevant screen lifecycle, and application shutdown changes.
- Preserve application-owned credential policy and first-complete-snapshot success persistence.
- Define a cleanup-complete handoff between failed credential attempts so DMP polling workers/sessions never overlap.
- Preserve all existing DMP protocol, worker, threading, cleanup, timeout, recovery, and redaction contracts.

## Non-Goals

Do not change meter OIDs, model discovery, SSH/SIS framing, PTY echo filtering, transaction correlation, `0*0`, bounded `*2` recovery, timeout poisoning, poll cadence, DMP handler transport behavior, `AudioDSPScreen` rendering, Biamp behavior, or unrelated Matrix/PDU/codec/SIP architecture. Do not introduce a generic multi-device controller. Do not change the existing worker signal ordering merely to implement credential fallback.

## Target Architecture

```text
VCSDiagnosticApp
  -> global input validation and generic request composition
  -> application-owned credential callbacks
  -> DMPPollingController composition and accepted-outcome routing

DMPPollingController
  -> DMP generation and credential-context revision authority
  -> immutable non-secret polling context
  -> cancellation publication and expected-worker identity
  -> worker construction/submission and signal binding
  -> stale callback acceptance, including terminal_log
  -> structured authentication-only fallback coordination
  -> pending-retry / retiring-attempt cleanup handoff
  -> first accepted complete snapshot credential-success gate

core/workers/dmp.py
  -> one assigned credential per worker/session attempt
  -> long-lived background SSH/SIS polling and cleanup
  -> error signal before finally cleanup, finished after cleanup

AudioDSPScreen
  -> renders only accepted snapshots
```

The preferred implementation is `gui/dmp_polling_controller.py` with class `DMPPollingController`.

## Ownership Boundaries

`DMPPollingController` owns DMP-specific generation, active context, cancellation token, expected worker, worker submission/binding, callback acceptance, structured authentication fallback coordination, pending-retry/retiring-attempt authority, first-success persistence gating, and invalidation/shutdown.

`VCSDiagnosticApp` retains credential provider/storage, ordered candidate resolution, saved successful index, generic request creation, global UI state/rendering helpers, and controller wiring. It must no longer own DMP-specific generation/token state, stale guards, retry dispatch, or DMP success persistence logic.

The worker and handler remain one-credential execution boundaries. They do not iterate credentials, persist indexes, inspect Qt widgets for freshness, or own application lifecycle.

## DMP Polling Context

Each attempt SHALL capture immutable non-secret identity equivalent to:

- DMP generation;
- model;
- IP address;
- generic request identifier;
- candidate index;
- credential-context revision;
- attempt/operation identity when needed.

Expected worker identity is controller-private authority. Public context SHALL NOT contain credential values, credential dictionaries, cancellation tokens, worker/handler/session/transport objects, cookies, or tokens.

Candidate index alone is not sufficient freshness identity because credential configuration may change while the numeric index remains the same.

## Invalidation and Cancellation

The controller SHALL supersede and cancel the active DMP context on:

- model change;
- IP change;
- leaving/superseding the DMP diagnostic context;
- DMP credential configuration change;
- repeat Refresh;
- application shutdown.

Invalidation SHALL publish cancellation to the old worker, replace its ordinary callback authority, and return without blocking for SSH cleanup. The worker remains responsible for handler/session cleanup on its background execution lane.

Old result, error, progress, status, `terminal_log`, and ordinary finished callbacks SHALL be ignored after supersession and SHALL NOT change the new UI/request state, credential memory, retry state, or refresh controls. A retiring-attempt `finished` used only for a previously planned credential retry is governed by the separate handoff rules below.

## Credential Flow

Credential ownership remains application/composition-owned. The controller MAY consume focused callbacks for ordered candidates, saved starting index, monotonic no-wrap advancement, successful-index commit, and attempt-plan cleanup.

Each worker receives one assigned candidate. The controller may advance only after a current structured confirmed `authentication_error`. Timeout, disconnect, SIS error, unsupported model, malformed data, cancellation, and other non-authentication failures SHALL NOT advance credentials. String matching such as `auth`, `401`, or `403` is not retry authority.

A retry SHALL use a fresh worker, fresh cancellation token, and fresh SSH/SIS session. Failed workers/sessions are never reused for the next candidate.

## Credential Attempt Cleanup Handoff

The existing worker signal ordering is authoritative: a failed worker may emit `error` while its SSH/SIS resources still exist; cleanup occurs in `finally`; `finished` is emitted only after that cleanup path completes. The controller SHALL preserve this ordering rather than changing worker semantics for the decomposition.

When the current attempt emits a structured confirmed `authentication_error` and application-owned policy selects a later candidate, the controller SHALL record that candidate as a pending retry associated with the exact failed attempt/context and expected worker. It SHALL NOT construct, submit, connect, or otherwise start the next DMP worker from the `error` callback.

The failed worker then becomes a retiring attempt. Its ordinary result/error/progress/status/`terminal_log` authority is exhausted, but its exact `finished` callback retains narrow retiring-attempt authority solely to confirm cleanup completion and release the already-planned retry. That `finished` callback SHALL NOT be routed as ordinary request completion, SHALL NOT alter refresh controls or current UI state, SHALL NOT persist credentials, and SHALL NOT independently choose or advance another candidate.

Only after the matching retiring worker emits `finished` may the controller create a fresh attempt context, fresh cancellation token, fresh worker, and fresh SSH/SIS session for the already-selected next candidate. At no point may two DMP polling workers or SSH/SIS sessions for consecutive credential attempts be active concurrently.

If model, IP, credential-context revision, generic request authority, DMP lifecycle generation, or application lifecycle is superseded before the retiring worker finishes, the pending retry SHALL be discarded. A stale or non-matching `finished` callback SHALL NOT launch any retry.

## Successful Credential Gate

The assigned candidate may be committed as successful only after the first accepted complete ten-OID snapshot of the current non-stale polling attempt and only when the credential was actually used under the existing worker result contract.

SSH login, model discovery, one OID, partial cycle, stale snapshot, timeout, cancellation, terminal failure, or later continuous snapshots SHALL NOT independently commit success.

The controller SHALL ensure generic `VCSDiagnosticApp` result handling cannot persist the DMP candidate a second time, for example by marking accepted DMP results as credential-policy-handled or by using an equivalent dedicated accepted-result boundary.

## Callback Acceptance

All DMP callbacks SHALL pass through the controller before generic shell rendering/state logic. Acceptance SHALL require the current immutable DMP context and expected worker identity to match. This includes `result`, `error`, `progress`, `status`, `terminal_log`, and `finished`.

`terminal_log` SHALL be bound through the DMP controller rather than directly from the worker to `on_codec_poll_terminal_log`. The controller SHALL apply the same DMP context and expected-worker freshness checks before any terminal text is rendered.

A stale callback SHALL NOT update `AudioDSPScreen`, append terminal output, alter global request/UI state, save credential success, advance fallback, start another DMP attempt, change refresh controls, or affect a newer context.

The only exception to ordinary current-context callback acceptance is the narrow retiring-attempt `finished` authority described above. It may release an already-planned retry after cleanup, but it may perform no other UI, credential, or request-completion action.

After extraction, generic shell callbacks SHALL NOT contain DMP-specific `_dmp_callback_is_current(...)` checks or DMP-specific credential fallback dispatch.

## MainWindow Reduction

Implementation should remove or reduce these DMP-specific responsibilities from `VCSDiagnosticApp`:

- `_dmp_context_revision`;
- `_dmp_cancel_token`;
- `_begin_dmp_context()`;
- direct worker-attached DMP context dictionaries;
- `_dmp_callback_is_current(...)`;
- DMP stale guards in generic callbacks;
- direct DMP `terminal_log` binding to `on_codec_poll_terminal_log`;
- DMP retry branch in generic `on_device_error(...)`;
- DMP success persistence through generic result handling;
- duplicate direct DMP cancellation wiring.

`refresh_extron_dmp64_plus(...)` MAY remain temporarily as a narrow compatibility delegate if existing callers require the name.

## Testing Strategy

Add focused coverage for repeat-refresh replacement, model/IP/credential-context invalidation, application shutdown, stale result/error/progress/status/`terminal_log`/finished suppression, old finished not altering newer refresh state, stale `terminal_log` not appending terminal output, structured auth-only fallback, pending retry not starting before failed-worker cleanup/finished, no overlapping DMP workers during fallback, stale retiring finished not launching retry, no-wrap exhaustion, non-auth no-fallback, fresh worker/session per candidate, first accepted complete snapshot committing success exactly once, later continuous snapshots not committing again, stale first snapshot not committing, one assigned credential per worker, and non-blocking GUI-side cancellation.

Run focused DMP/controller tests, the full offline suite, `git diff --check`, `./openspec.cmd validate dmp-polling-lifecycle-decomposition --strict`, and `./openspec.cmd validate --all --strict` through the repository-local wrapper.

## Risks

- **Overlapping credential attempts:** never start a pending fallback worker before the failed worker's cleanup-complete `finished` handoff.
- **Retiring finished overreach:** retiring-attempt `finished` may only release an already-planned retry and cannot act as ordinary completion.
- **Direct terminal bypass:** route `terminal_log` through controller freshness acceptance before rendering.
- **Duplicate credential handling:** prevent both controller and generic callbacks from retrying or persisting DMP credentials.
- **Credential change without invalidation:** make credential configuration change an explicit controller invalidation event.
- **GUI-thread cleanup regression:** controller only cancels; worker-owned cleanup remains background work.
- **Scope creep:** preserve DMP protocol and worker semantics unless a narrowly necessary compatibility change is required.
