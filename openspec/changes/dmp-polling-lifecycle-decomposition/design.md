## Context

The DMP worker is already isolated in `core/workers/dmp.py`, but `gui/main_window.py` still owns DMP generation, cancellation, worker submission, stale callback checks, retry dispatch, and successful-credential persistence. Credential configuration changes currently invalidate Matrix and PDU contexts but not the active DMP polling context, so the implementation does not fully satisfy the existing credential-context stale-isolation contract.

## Goals

- Add a focused DMP-specific application controller.
- Move DMP polling lifecycle and callback authority out of generic `VCSDiagnosticApp` handlers.
- Invalidate active DMP polling on model, IP, credential-context, repeat Refresh, relevant screen lifecycle, and application shutdown changes.
- Preserve application-owned credential policy and first-complete-snapshot success persistence.
- Preserve all existing DMP protocol, worker, threading, cleanup, timeout, recovery, and redaction contracts.

## Non-Goals

Do not change meter OIDs, model discovery, SSH/SIS framing, PTY echo filtering, transaction correlation, `0*0`, bounded `*2` recovery, timeout poisoning, poll cadence, DMP handler transport behavior, `AudioDSPScreen` rendering, Biamp behavior, or unrelated Matrix/PDU/codec/SIP architecture. Do not introduce a generic multi-device controller.

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
  -> stale callback acceptance
  -> structured authentication-only fallback coordination
  -> first accepted complete snapshot credential-success gate

core/workers/dmp.py
  -> one assigned credential per worker/session attempt
  -> long-lived background SSH/SIS polling and cleanup

AudioDSPScreen
  -> renders only accepted snapshots
```

The preferred implementation is `gui/dmp_polling_controller.py` with class `DMPPollingController`.

## Ownership Boundaries

`DMPPollingController` owns DMP-specific generation, active context, cancellation token, expected worker, worker submission/binding, callback acceptance, structured authentication fallback coordination, first-success persistence gating, and invalidation/shutdown.

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

Invalidation SHALL publish cancellation to the old worker, replace its callback authority, and return without blocking for SSH cleanup. The worker remains responsible for handler/session cleanup on its background execution lane.

Old result, error, progress, status, terminal, and finished callbacks SHALL be ignored after supersession and SHALL NOT change the new UI/request state, credential memory, retry state, or refresh controls.

## Credential Flow

Credential ownership remains application/composition-owned. The controller MAY consume focused callbacks for ordered candidates, saved starting index, monotonic no-wrap advancement, successful-index commit, and attempt-plan cleanup.

Each worker receives one assigned candidate. The controller may advance only after a current structured confirmed `authentication_error`. Timeout, disconnect, SIS error, unsupported model, malformed data, cancellation, and other non-authentication failures SHALL NOT advance credentials. String matching such as `auth`, `401`, or `403` is not retry authority.

A retry SHALL use a fresh worker, fresh cancellation token, and fresh SSH/SIS session. Failed workers/sessions are never reused for the next candidate.

## Successful Credential Gate

The assigned candidate may be committed as successful only after the first accepted complete ten-OID snapshot of the current non-stale polling attempt and only when the credential was actually used under the existing worker result contract.

SSH login, model discovery, one OID, partial cycle, stale snapshot, timeout, cancellation, terminal failure, or later continuous snapshots SHALL NOT independently commit success.

The controller SHALL ensure generic `VCSDiagnosticApp` result handling cannot persist the DMP candidate a second time, for example by marking accepted DMP results as credential-policy-handled or by using an equivalent dedicated accepted-result boundary.

## Callback Acceptance

All DMP callbacks SHALL pass through the controller before generic shell rendering/state logic. Acceptance SHALL require the current immutable DMP context and expected worker identity to match. This includes result, error, progress, status, terminal, and finished.

A stale callback SHALL NOT update `AudioDSPScreen`, alter global request/UI state, save credential success, advance fallback, start another DMP attempt, change refresh controls, or affect a newer context.

After extraction, generic shell callbacks SHALL NOT contain DMP-specific `_dmp_callback_is_current(...)` checks or DMP-specific credential fallback dispatch.

## MainWindow Reduction

Implementation should remove or reduce these DMP-specific responsibilities from `VCSDiagnosticApp`:

- `_dmp_context_revision`;
- `_dmp_cancel_token`;
- `_begin_dmp_context()`;
- direct worker-attached DMP context dictionaries;
- `_dmp_callback_is_current(...)`;
- DMP stale guards in generic callbacks;
- DMP retry branch in generic `on_device_error(...)`;
- DMP success persistence through generic result handling;
- duplicate direct DMP cancellation wiring.

`refresh_extron_dmp64_plus(...)` MAY remain temporarily as a narrow compatibility delegate if existing callers require the name.

## Testing Strategy

Add focused coverage for repeat-refresh replacement, model/IP/credential-context invalidation, application shutdown, stale result/error/progress/status/finished suppression, old finished not altering newer refresh state, structured auth-only fallback, no-wrap exhaustion, non-auth no-fallback, fresh worker/session per candidate, first accepted complete snapshot committing success exactly once, later continuous snapshots not committing again, stale first snapshot not committing, one assigned credential per worker, and non-blocking GUI-side cancellation.

Run focused DMP/controller tests, the full offline suite, `git diff --check`, `./openspec.cmd validate dmp-polling-lifecycle-decomposition --strict`, and `./openspec.cmd validate --all --strict` through the repository-local wrapper.

## Risks

- **Duplicate credential handling:** prevent both controller and generic callbacks from retrying or persisting DMP credentials.
- **Stale finished callback:** apply the same acceptance rule to `finished` as to data/error callbacks.
- **Credential change without invalidation:** make credential configuration change an explicit controller invalidation event.
- **GUI-thread cleanup regression:** controller only cancels; worker-owned cleanup remains background work.
- **Scope creep:** preserve DMP protocol and worker semantics unless a narrowly necessary compatibility change is required.