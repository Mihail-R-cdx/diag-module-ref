## Context

`worker-module-decomposition` is merged and the canonical PDU worker now lives in `core/workers/pdu.py`, with `core/worker.py` acting as a compatibility facade. `matrix-operation-lifecycle-decomposition` is also merged and provides the current project precedent for moving device-specific application lifecycle out of `VCSDiagnosticApp` into a focused controller near the GUI composition boundary.

The remaining architectural problem is not device protocol logic or worker module size. It is the concentration of PDU-specific application lifecycle in `gui/main_window.py` and the implicit parent-method coupling between `PDUScreen` and `VCSDiagnosticApp`.

The review of the first architecture draft identified three contract gaps closed by this revision:

1. PDU lifecycle authority must not be modeled as one global `current_operation_id` across refresh and mutation operations.
2. Sequential bulk execution must explicitly re-check currentness before every next state-changing outlet send, not only suppress stale Qt callbacks later.
3. Credential fallback and successful-index persistence must be stated as a current per-model/per-operation eligibility matrix rather than as a generic "existing gate".

## Goals

- Localize PDU refresh, individual mutation, bulk mutation, stale acceptance, operation identity, and reconciliation in one PDU-specific application component.
- Replace `PDUScreen` parent-method orchestration calls with an explicit non-secret intent boundary.
- Preserve current `core/pdu.py`, worker, and handler ownership boundaries.
- Preserve application-owned credential candidate resolution, fallback authority, successful credential index memory, and credential-context revision ownership.
- Preserve all current mutation safety, bulk sequencing, stale-context, PCS4i, threading, and redaction contracts.
- Define independent refresh and mutation authority lanes so refresh activity cannot accidentally invalidate active mutation authority and mutation activity cannot accidentally complete or supersede unrelated refresh authority.
- Prevent an older refresh snapshot from being accepted as authoritative PDU state after a later mutation has started.
- Define reconciliation as a refresh-lane operation that remains linked to the originating accepted mutation.
- Keep all PDU network work outside the Qt GUI thread.
- Keep the controller strictly PDU-specific.

## Non-Goals

Do not implement production code or tests in this architecture-creation session. Do not change user-visible PDU behavior, protocol commands, Aten or PCS4i handler transport semantics, sequential bulk ordering/delay/fail-fast/partial/no-replay semantics, PCS4i credentialless behavior, Matrix, DMP, codec, SIP, or generic request/credential architecture. Do not create a generic multi-device operation/request/controller framework and do not move PDU workers back into `core/worker.py`.

## Target Architecture

```text
PDUScreen
  -> refreshRequested()
  -> outletMutationRequested(outlet_number, operation)
  -> bulkMutationRequested(operation)

PDUController
  -> captures immutable common PDU context identity
  -> owns independent refresh and mutation authority lanes
  -> obtains credential candidates/indexes through application-owned callbacks
  -> submits existing PDU background workers
  -> accepts callbacks only through the matching lane authority
  -> coordinates current PDU mutation/busy state
  -> applies existing credential fallback gates through application-owned callbacks
  -> schedules context-bound reconciliation as a refresh-lane operation

core/workers/pdu.py
  -> performs PDU network work outside the Qt GUI thread
  -> calls a controller-supplied non-GUI currentness predicate/token contract
  -> uses one assigned credential per worker attempt

core/pdu.py
  -> preserves PDU operation/safety/bulk contracts
  -> re-checks supplied currentness before every next bulk outlet send

handlers/aten/pdu.py / handlers/extron/pcs4i.py
  -> preserve device-specific wire and transport semantics
```

The preferred class name is `PDUController` and the preferred location is near the existing `gui/matrix_controller.py`, for example `gui/pdu_controller.py`. The controller must not live in `handlers/`, `core/workers/`, or `core/worker.py`.

## Ownership Boundaries

`PDUScreen` owns rendering, model-specific capabilities, accepted busy/loading/disabled control state, local table/button presentation helpers, confirmation dialogs, and translation of operator actions into non-secret intents. It must not own credential candidates, credential indexes, credential fallback, successful credential memory, worker creation/submission, handler acquisition, handler/session objects, operation generation authority, refresh lane authority, mutation lane authority, stale-operation acceptance, PDU network I/O, or direct calls to arbitrary parent orchestration methods such as `control_pdu_outlet(...)`, `control_pdu_outlets_bulk(...)`, or `refresh_data()` for PDU lifecycle execution.

`PDUController` owns PDU-specific application lifecycle: common PDU context identity and generation; refresh lane operation authority; mutation lane operation authority; PDU refresh lifecycle; individual outlet mutation lifecycle; sequential bulk mutation lifecycle; immutable operation context capture; stale callback acceptance/rejection; worker submission and signal binding; context-scoped mutation/busy ownership; context-bound reconciliation; cleanup/invalidation on model, IP, credential-context revision, screen lifecycle, and application shutdown. It is not a protocol layer and must not become a generic device manager.

After extraction, `VCSDiagnosticApp` owns only PDU composition responsibilities: create and wire `PDUScreen` and `PDUController`, wire screen intents to controller operations, wire accepted controller outputs to `PDUScreen` and global shell state, provide current model/IP context, provide application-owned credential callbacks, provide non-secret credential-context revision, and delegate invalidation/shutdown.

`core/workers/pdu.py` remains the canonical PDU worker module. `PDUOperationWorker` continues to receive one immutable descriptor/context snapshot, receive one assigned credential for one attempt, execute refresh/individual/bulk operations through `core.pdu`, perform network I/O outside the Qt GUI thread, invoke only the controller-supplied non-GUI currentness predicate/token contract, emit structured signals and redacted public payloads, and avoid credential candidate iteration and successful-index persistence.

The worker/core execution layer must not read `device_combo`, `ip_entry`, `PDUScreen`, or other QWidget values to decide freshness. The controller owns currentness authority; execution code only calls the supplied thread-safe predicate or equivalent non-GUI token contract.

`core/pdu.py` remains the owner of `PDUOperationDescriptor` or compatible immutable context shape, model capability validation, outlet identity validation, dynamic immutable bulk outlet sequence capture, safe absolute ON/OFF mutation policy, bounded individual command reconciliation, sequential bulk execution and fail-fast semantics, handler factory dispatch, and structured stale checks supplied by application lifecycle.

`handlers/aten/pdu.py` remains the Aten protocol boundary. `handlers/extron/pcs4i.py` remains the PCS4i protocol boundary. Handlers do not read credential providers, iterate credential candidates, decide application stale context, update successful credential memory, access Qt widgets, or own cross-operation application lifecycle.

## Common PDU Context Identity

All PDU operations share a common non-secret context identity:

- PDU context generation or equivalent opaque revision;
- selected PDU model;
- IP address;
- non-secret credential-context revision.

This identity becomes stale on model change, IP change, credential-context revision change, screen/application teardown, or explicit lifecycle reset where current behavior requires it. It contains no credential values, credential dictionaries, profile secrets, cookies, Session IDs, CSRF tokens, handler objects, session objects, or transport objects.

Qt widgets may be consulted only to capture the initial public model/IP intent at submission/composition time. Once captured, later widget changes do not mutate an in-flight operation. Candidate index alone is not sufficient freshness identity because credential configuration may change while the same numeric index remains selected.

## Independent Operation Authority Lanes

The PDU controller must not use one global `current_operation_id` for all PDU operations. It owns at least two independent operation authority lanes under the same common PDU context identity.

### Refresh lane

The refresh lane owns operator-requested PDU status refresh, normal PDU status refresh, and refresh/reconciliation after accepted mutation outcomes. It has its own current refresh/reconciliation operation identity and expected refresh worker identity. Starting a new refresh-lane operation may supersede an older refresh-lane operation for the same common PDU context, but it must not replace current mutation operation identity, clear mutation busy state, or make mutation result/error/finished callbacks stale merely because the refresh started.

Refresh callbacks are accepted only when common PDU context identity, current refresh/reconciliation operation identity, expected refresh/reconciliation worker identity, and any reconciliation origin identity all match. A refresh completion cannot unlock mutation controls, clear mutation busy state, finalize a mutation, invalidate current mutation worker identity, or decide mutation credential fallback.

### Mutation lane

The mutation lane owns individual outlet mutation and sequential bulk mutation. It has its own current mutation operation identity, mutation kind (`individual` or `bulk`), and expected mutation worker identity. Individual and bulk mutations are mutually exclusive in one current PDU context. A request for individual mutation while bulk is active, or bulk mutation while individual is active, is rejected or ignored before worker creation and before any state-changing network I/O.

Mutation callbacks are accepted only when common PDU context identity, current mutation operation identity, mutation kind, and expected mutation worker identity all match. Mutation lifecycle does not use the refresh operation identity as its freshness authority. Mutation completion cannot accidentally complete, unlock, or finalize a newer unrelated refresh-lane operation.

### Coexistence rules

Starting a refresh does not invalidate a current mutation. Starting a refresh does not clear mutation busy state. Refresh result/error/finished cannot finalize mutation state. Mutation result/error/finished cannot finalize an unrelated newer refresh. Callbacks from each family are checked against that family's lane identity, and both lane checks also require the common PDU context identity to remain current.

For `mutation A active -> refresh B starts -> refresh B finishes -> mutation A later finishes`, refresh B is judged through the refresh lane and mutation A is judged through the mutation lane. Refresh B does not make mutation A stale merely by starting or finishing. Mutation A can still be handled as the current mutation if the common context and mutation lane identity still match.

## Refresh Snapshot Ordering Relative to Mutation

A refresh snapshot whose read was submitted before a later mutation started must not later be accepted as authoritative post-mutation state.

The implementation may use a controller-owned PDU state epoch, a refresh submission sequence compared with mutation-start sequence, explicit supersession of older refresh-lane authority when mutation starts, or an equivalent simple mechanism. The required contract is:

```text
refresh A submitted
-> mutation B starts later
-> refresh A completes after B started
-> refresh A must not overwrite PDU data as authoritative newer state
```

This rule prevents stale pre-mutation state from overwriting mutation-era or post-mutation UI state. It does not mean every refresh started after mutation begins invalidates the mutation lane. A refresh submitted after mutation start is still refresh-lane authority only; it cannot clear or finalize the current mutation unless a separate current mutation callback does so.

## Reconciliation Authority

Reconciliation is a refresh-lane operation with additional immutable origin identity. It is not mutation-lane owner.

A reconciliation operation must include or be equivalent to common PDU context identity, its own refresh/reconciliation operation identity, expected reconciliation worker identity, originating mutation operation identity, originating mutation kind when needed to disambiguate, and non-secret credential-context revision/assigned candidate index when the refresh attempt uses a credential candidate.

Reconciliation may start only after the originating mutation outcome has been accepted as current by the mutation lane. A stale old mutation cannot start reconciliation. After reconciliation starts, it does not become mutation owner, does not clear mutation state on behalf of a different mutation, and does not unlock controls owned by a newer mutation.

Reconciliation callbacks must not update a new model/IP/common context, must not refresh whichever device is currently selected by widgets, and must not displace an authoritative refresh-lane operation of a newer common context. A reconciliation tied to mutation A is stale if the common context changed, if a newer refresh-lane operation superseded it, or if its originating mutation identity is no longer accepted as the source that authorized reconciliation.

## Sequential Bulk Mid-Operation Currentness

Bulk ON/OFF remains one application-owned orchestration sequence executed by the existing PDU background boundary. Before every next state-changing outlet sub-operation, including after each completed outlet and before outlet N+1 is sent, the bulk execution path must re-check the supplied thread-safe currentness/stale predicate or equivalent non-GUI token contract. If the predicate is false, outlet N+1 is not sent, no later outlet is sent, completed outlets are not replayed or rolled back, and the terminal outcome preserves the existing structured stale/partial semantics.

Stale suppression of later Qt callbacks is not sufficient. The worker/core execution path itself must stop future state-changing sends once its supplied currentness authority becomes false. This check must not read Qt widgets.

## Credential Eligibility Matrix

Structural extraction must preserve current per-model/per-operation credential behavior. It must not turn the PDU controller into a generic policy that makes every PDU operation retry-eligible or success-persisting.

| Operation family | Fallback eligibility | Successful-index persistence |
| --- | --- | --- |
| PDU refresh | Supported credential-bearing refresh may advance only after structured confirmed device credential rejection while the operation is still read-only/safe for another credential attempt. Candidate advancement remains application-owned. PCS4i `CredentialRequired`, passwordless success, assigned-but-unused password, and HTTP outlet-name enrichment 401/403/failure are not fallback authority. | Save only after accepted final successful refresh for the exact device/IP and only when the assigned credential was actually used where the protocol contract requires it. PCS4i credentialless success and assigned-but-unused password success do not persist. HTTP enrichment does not make an independent persistence decision. |
| Aten individual mutation | This structural change does not newly make Aten individual outlet mutations credential-retry-eligible unless that behavior already existed before the change. No generic retry is introduced merely because the lifecycle moved into `PDUController`. | This structural change does not newly persist successful credential index from Aten individual mutation unless that behavior already existed before the change. |
| PCS4i individual ON/OFF | Existing PCS4i fallback remains allowed only after structured confirmed Telnet credential rejection plus structured proof that no state-changing command send occurred or could have been delivered. After possible send, no fallback and no replay. | Commit only if the existing PCS4i success gate permits it and the assigned credential was actually used. Passwordless or assigned-but-unused success does not persist. Partial, failed, ambiguous, or stale outcomes do not persist. |
| Aten bulk ON/OFF | Existing bulk fallback may advance only after structured confirmed authentication rejection and structured execution state proving zero possible state-changing sends. After possible send, no restart, no replay of completed outlets, and no wrap-around. | After full accepted successful Aten bulk, a used assigned credential index may be persisted according to the existing bulk contract. Partial, failed, ambiguous, or stale bulk outcomes do not persist. |
| PCS4i bulk ON/OFF | Same bulk rule: one assigned credential for the whole attempt, fallback only on structured confirmed rejection plus zero-send safety evidence. After possible send, no restart, no completed-outlet replay, and no wrap-around. `CredentialRequired`, passwordless behavior, HTTP enrichment failure, and assigned-but-unused success are not fallback authority. | Commit only after full accepted bulk success and only when the assigned PCS4i credential was actually used. Passwordless or assigned-but-unused success does not persist. Partial, failed, ambiguous, or stale bulk outcomes do not persist. |

## Credential Ownership

Credential architecture does not move into the PDU controller. The application/composition credential boundary remains the owner of candidate sequence resolution, current successful credential index memory by device/IP, request-scoped candidate advancement policy, successful-index persistence, and credential-context revision.

`PDUController` may receive injected callbacks/providers for obtaining resolved ordered candidates, obtaining the valid starting successful credential index, advancing a request-scoped attempt only after a structured fallback-authorizing outcome, committing a successful candidate only after an approved success gate from the eligibility matrix, and obtaining the non-secret credential-context revision. These callbacks do not make the controller a second independent credential manager.

Workers and handlers continue to receive one assigned credential only. Transport fallback and credential fallback remain separate mechanisms; all transport attempts within one credential attempt use that assigned credential.

## PCS4i Preservation

PCS4i keeps the existing password-only contract: no username is invented; an assigned candidate contains only the optional password after normalization; absence of mapping may produce the existing single credentialless PCS4i attempt rather than a generic configuration/authentication failure; `CredentialRequired` is not reclassified as confirmed credential rejection; passwordless success and assigned-but-unused credentials do not create successful credential memory; HTTP outlet-name 401/403 or other enrichment failure is not credential fallback authority; PCS4i REBOOT remains unsupported.

## Busy and Control-State Coordination

The controller owns authoritative current-operation busy state and context identity for the mutation lane. `PDUScreen` renders the accepted state. A current active mutation prevents conflicting PDU mutation intents according to existing UI behavior. Context invalidation gives the new context independent control state. An old callback cannot unlock or relock the new context.

## Refresh and Reconciliation After Mutation

Existing PDU mutation reconciliation behavior is preserved but moved under the controller lifecycle. A mutation outcome may schedule or request a reconciliation refresh only when the originating mutation outcome is accepted as current by the mutation lane and existing policy requires reconciliation. The follow-up refresh is bound to the original PDU common context and originating mutation identity and receives its own refresh-lane operation identity.

The reconciliation path must not call `VCSDiagnosticApp.refresh_data()` without preserving originating context, refresh whichever device happens to be selected when an old callback arrives, reuse stale worker identity as current authority, become mutation owner, clear busy state for another mutation, update a newer model/IP/common context, or displace an authoritative refresh-lane operation for a newer common context.

## Threading Model

All PDU network operations remain outside the Qt GUI thread, including refresh, individual outlet mutation, sequential bulk mutation and inter-outlet delays, refresh/reconciliation after mutation, handler acquisition/connect, and blocking handler/session cleanup when such cleanup is part of the operation.

A controller method may capture context, validate currentness, select an assigned credential through application callbacks, and submit background work. It must not directly execute blocking handler methods on the GUI thread. Moving `handler.connect()`, `get_outlets_status()`, `turn_on()`, `turn_off()`, `reboot()`, or equivalent synchronous calls from `VCSDiagnosticApp` into a plain controller method is not a valid implementation.

## MainWindow Migration Boundary

Future implementation should remove these PDU-specific responsibilities from `VCSDiagnosticApp`: PDU context revision/generation state, PDU operation serial/identity generation, refresh-lane authority and expected refresh worker identity, mutation-lane authority/mutation kind/expected mutation worker identity, descriptor construction, refresh worker construction/submission, individual mutation worker construction/submission, bulk worker construction/submission/retry orchestration, worker signal binding, stale callback predicates, mutation/bulk busy ownership, result/error/finished handlers, and refresh-after-mutation decisions.

Generic shell responsibilities, global credential memory/policy, global model/IP selection, non-PDU request lifecycle, and unrelated device controllers remain in their existing ownership boundaries unless a separate approved change moves them.

## Risks / Trade-Offs

- The existing generic refresh lifecycle in `VCSDiagnosticApp` is shared by several device families. PDU extraction must avoid accidentally duplicating or changing generic shell behavior while making PDU callback ownership explicit.
- Independent authority lanes add a little more state, but they prevent refresh and mutation callbacks from accidentally invalidating or finalizing each other.
- Credential policy injection can become overly abstract. Prefer focused PDU callbacks matching current application-owned operations rather than creating a new generic credential framework in this change.
- A controller that merely forwards every call back into `VCSDiagnosticApp` would not reduce context load.
- A controller that absorbs `core.pdu` execution algorithms would create a new oversized boundary.

## Migration Plan

1. Add a focused PDU controller/context type near the GUI composition boundary.
2. Introduce explicit `PDUScreen` refresh, individual mutation, and bulk mutation intents and remove arbitrary parent-method orchestration calls.
3. Move common PDU context identity and invalidation into the controller.
4. Add independent refresh and mutation authority lanes.
5. Move PDU refresh lifecycle and worker binding from `VCSDiagnosticApp` into the controller while preserving application credential callbacks.
6. Move individual mutation lifecycle and context-bound busy state into the mutation lane without changing mutation safety or fallback semantics.
7. Move bulk mutation lifecycle, retry gating, mid-bulk currentness checks, and partial/full terminal handling into the mutation lane without changing `core.pdu` sequencing semantics.
8. Move PDU stale/currentness predicates and PDU context generation into the controller.
9. Bind post-mutation refresh/reconciliation to the originating immutable mutation identity as a refresh-lane operation.
10. Reduce `VCSDiagnosticApp` to PDU composition, shell-state wiring, credential callbacks, context updates, and shutdown delegation.
11. Add focused regression coverage and run the full offline suite plus strict repository-local OpenSpec validation.
