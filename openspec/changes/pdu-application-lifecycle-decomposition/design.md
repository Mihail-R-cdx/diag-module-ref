## Context

`worker-module-decomposition` is merged and the canonical PDU worker now lives in
`core/workers/pdu.py`, with `core/worker.py` acting as a compatibility facade.
`matrix-operation-lifecycle-decomposition` is also merged and provides the
current project precedent for moving device-specific application lifecycle out
of `VCSDiagnosticApp` into a focused controller near the GUI composition
boundary.

The current PDU architecture already has strong protocol and worker separation:

```text
PDUScreen
  renders shared Aten/PCS4i outlet UI
  owns confirmation dialogs and local presentation state
  emits outlet_control_signal / bulk_control_signal
  local slots call parent.control_pdu_outlet(...)
  local slots call parent.control_pdu_outlets_bulk(...)
  local refresh calls parent.refresh_data()

VCSDiagnosticApp
  owns global model/IP selection
  owns credential provider and successful credential index memory
  owns PDU credential-attempt plans and fallback advancement
  owns PDU context generation/invalidation
  creates PDUOperationDescriptor values
  creates/submits PDUOperationWorker instances
  binds PDU result/error/progress/status/finished callbacks
  owns individual mutation lifecycle
  owns sequential bulk lifecycle
  owns stale callback acceptance
  owns PDU busy/mutation state coordination
  owns refresh/reconciliation after mutation

core/workers/pdu.py
  owns PDUOperationWorker background execution
  receives one immutable operation descriptor
  receives one assigned credential
  invokes core.pdu execution functions off the Qt GUI thread
  emits structured result/error/progress/status/finished signals

core/pdu.py
  owns PDU capability validation
  owns PDUOperationDescriptor
  owns handler factory dispatch
  owns safe individual mutation policy
  owns sequential bulk operation policy
  owns per-operation stale checks supplied by application lifecycle

handlers/aten/pdu.py
  owns Aten HTTPS/XML/API protocol primitives

handlers/extron/pcs4i.py
  owns PCS4i Telnet/SIS protocol and optional HTTP name enrichment
```

The remaining architectural problem is therefore not device protocol logic or
worker module size. It is the concentration of PDU-specific application
lifecycle in `gui/main_window.py` and the implicit parent-method coupling between
`PDUScreen` and `VCSDiagnosticApp`.

This change defines the architecture for extracting that lifecycle without
changing PDU semantics.

## Goals

- Reduce PDU context load so routine PDU work does not require reading most of
  `gui/main_window.py`.
- Localize PDU refresh, individual mutation, bulk mutation, stale acceptance,
  operation identity, and reconciliation in one PDU-specific application
  component.
- Replace `PDUScreen` parent-method orchestration calls with an explicit
  non-secret intent boundary.
- Preserve current `core/pdu.py`, worker, and handler ownership boundaries.
- Preserve application-owned credential candidate resolution, fallback
  authority, successful credential index memory, and credential-context
  revision ownership.
- Preserve all current mutation safety, bulk sequencing, stale-context, PCS4i,
  threading, and redaction contracts.
- Keep all PDU network work outside the Qt GUI thread.
- Keep the controller strictly PDU-specific.

## Non-Goals

- Do not implement production code in this architecture-creation session.
- Do not change tests in this architecture-creation session.
- Do not change user-visible PDU behavior.
- Do not change PDU protocol commands.
- Do not change Aten or PCS4i handler transport semantics.
- Do not change sequential bulk ordering, delay, fail-fast, partial-result, or
  no-replay semantics.
- Do not expand or relax credential fallback semantics.
- Do not change PCS4i password-only or credentialless behavior.
- Do not create a generic multi-device operation/request/controller framework.
- Do not merge Matrix, PDU, DMP, codec, or SIP lifecycle ownership.
- Do not generally decompose all remaining `VCSDiagnosticApp` responsibilities.
- Do not extract DMP lifecycle or a generic request/credential coordinator in
  this change.
- Do not move PDU workers back into `core/worker.py`.

## Target Architecture

```text
PDUScreen
  -> refreshRequested()
  -> outletMutationRequested(outlet_number, operation)
  -> bulkMutationRequested(operation)

PDUController
  -> captures immutable PDU operation context
  -> owns PDU context generation and operation identity
  -> obtains ordered credential candidates through application-owned callbacks
  -> obtains current successful candidate index through application-owned callback
  -> submits existing PDU background workers
  -> owns PDU-specific worker signal binding
  -> accepts only callbacks matching current context/operation identity
  -> coordinates current PDU mutation/busy state
  -> applies existing credential fallback gates through application-owned callbacks
  -> schedules context-bound refresh/reconciliation when existing policy requires it

core/workers/pdu.py
  -> performs PDU network work outside the Qt GUI thread
  -> uses one assigned credential per worker attempt
  -> returns structured outcomes

core/pdu.py
  -> preserves PDU operation/safety/bulk contracts

handlers/aten/pdu.py / handlers/extron/pcs4i.py
  -> preserve device-specific wire and transport semantics

PDUController
  -> emits accepted PDU data/state/outcomes only

PDUScreen
  -> renders accepted data and control state

VCSDiagnosticApp
  -> composition/bootstrap
  -> global model/IP selection
  -> application-owned credential policy and successful-index memory
  -> global shell UI state
  -> controller creation/wiring/invalidation/shutdown delegation
```

The preferred class name is `PDUController` and the preferred location is near
the existing `gui/matrix_controller.py`, for example `gui/pdu_controller.py`.
The controller must not live in `handlers/`, `core/workers/`, or
`core/worker.py`.

## Ownership Boundaries

### PDUScreen

`PDUScreen` owns:

- rendering device information and outlet records;
- rendering model-specific capabilities;
- rendering busy/loading/disabled control state supplied by the active PDU
  lifecycle;
- local table/button presentation helpers;
- confirmation dialogs for individual and bulk mutation when they remain a
  reasonable view responsibility;
- translating operator actions into non-secret intents.

`PDUScreen` must not own:

- credential candidates or credential indexes;
- credential fallback or successful credential memory;
- worker creation or worker submission;
- handler acquisition or handler/session objects;
- request/operation generation authority;
- stale-operation acceptance authority;
- PDU network I/O;
- direct calls to arbitrary parent orchestration methods such as
  `control_pdu_outlet(...)`, `control_pdu_outlets_bulk(...)`, or
  `refresh_data()` for PDU lifecycle execution.

The screen may keep focused local presentation helpers such as button loading
state, table rendering, and confirmation prompts. The extraction is not a
mechanical move of every UI helper into the controller.

Intent payloads contain only non-secret operation data needed by the PDU
lifecycle. They must not contain usernames, passwords, credential dictionaries,
candidate lists, cookies, tokens, handler/session objects, or transport objects.

### PDUController

`PDUController` owns PDU-specific application lifecycle:

- PDU refresh lifecycle;
- individual outlet mutation lifecycle;
- sequential bulk mutation lifecycle;
- immutable operation context capture;
- unique operation/request identity;
- PDU context generation and invalidation;
- stale callback acceptance/rejection;
- creation/submission of existing PDU workers, or a focused worker-factory
  helper owned by the same PDU boundary;
- PDU-specific worker signal binding;
- context-scoped mutation/busy ownership;
- context-bound refresh/reconciliation after mutation according to existing
  policy;
- cleanup/invalidation on model, IP, credential-context revision, screen
  lifecycle, and application shutdown.

The controller is not a protocol layer. It does not absorb `core/pdu.py` safe
mutation algorithms or device-specific handler wire logic merely to reduce file
count.

The controller is not a generic device manager. It must not acquire Matrix,
DMP, codec, SIP, or unrelated lifecycle responsibilities.

### VCSDiagnosticApp

After extraction, `VCSDiagnosticApp` owns only PDU composition responsibilities:

- create `PDUScreen` and `PDUController`;
- wire screen intents to controller operations;
- wire accepted controller outputs to `PDUScreen` and global shell UI state;
- provide current global model/IP selection to the controller through explicit
  context callbacks or update methods;
- provide application-owned credential candidate/index/fallback/commit callbacks;
- provide the non-secret credential-context revision;
- delegate PDU invalidation and application shutdown.

`VCSDiagnosticApp` should no longer directly own PDU-specific operation state
machines, PDU worker signal binding, PDU context generation, individual/bulk
mutation orchestration, PDU-specific stale callback logic, or PDU-specific
refresh-after-mutation policy.

The global shell may still own generic refresh-button and connection-state UI.
The controller may emit accepted lifecycle events that the composition layer
maps into that shell state. Stale PDU callbacks must never update global shell
state for a newer request.

### Worker Boundary

`core/workers/pdu.py` remains the canonical PDU worker module.
`PDUOperationWorker` continues to:

- receive one immutable descriptor/context snapshot;
- receive one assigned credential for one attempt;
- execute refresh, individual mutation, or bulk mutation through `core.pdu`;
- perform network I/O outside the Qt GUI thread;
- emit structured signals and redacted public payloads;
- avoid credential candidate iteration and successful-index persistence.

The controller may construct and submit the worker, but it must not replace the
background boundary with synchronous handler calls.

### Core PDU Contract

`core/pdu.py` remains the owner of shared PDU execution semantics including:

- `PDUOperationDescriptor` or its compatible evolved immutable context shape;
- model capability validation;
- outlet identity validation;
- dynamic immutable bulk outlet sequence capture;
- safe absolute ON/OFF mutation policy;
- bounded individual command reconciliation;
- sequential bulk execution and fail-fast semantics;
- handler factory dispatch;
- structured stale checks supplied by application lifecycle.

This change does not move these protocol-independent execution policies into the
GUI controller solely for locality.

### Handlers

`handlers/aten/pdu.py` remains the Aten protocol boundary.
`handlers/extron/pcs4i.py` remains the PCS4i protocol boundary.

Handlers do not:

- read credential providers;
- iterate credential candidates;
- decide application stale context;
- update successful credential memory;
- access Qt widgets;
- own cross-operation application lifecycle.

## Immutable PDU Operation Context

Every PDU operation must carry immutable, non-secret identity sufficient to
validate currentness before network work and before accepting callbacks.

The exact implementation may evolve `PDUOperationDescriptor` or add a focused
controller context type, but the effective identity must include at least:

- selected PDU model;
- IP address;
- operation kind: refresh, individual mutation, bulk mutation, or reconciliation
  refresh;
- PDU context generation or equivalent opaque context revision;
- unique operation ID;
- non-secret credential-context revision;
- assigned credential candidate index when a credential candidate participates;
- outlet number for individual mutation;
- immutable bulk operation identity including the captured outlet sequence for
  bulk mutation;
- expected worker/background-operation identity when applicable.

The public context must not contain:

- username;
- password;
- credential values or credential dictionaries;
- profile names when they reveal credential configuration;
- cookies;
- Session IDs;
- CSRF tokens;
- handler/session/transport objects.

Qt widgets may be consulted only to capture the initial public model/IP intent at
submission/composition time. Once captured, later widget changes do not mutate
an in-flight operation.

Candidate index alone is not sufficient freshness identity because credential
configuration may change while the same numeric index remains selected. The
non-secret credential-context revision must participate in currentness.

## PDU Context Generation and Invalidation

The controller owns the current PDU lifecycle generation.

The active PDU context is invalidated when relevant public or credential context
changes, including at least:

- selected model change away from or between PDU models;
- IP change;
- application-owned credential configuration revision change;
- explicit PDU lifecycle reset/reconnect where current behavior requires a new
  generation;
- screen/application destruction or shutdown.

Invalidation must detach old operation authority immediately. An old worker may
still finish physically, but its callbacks are stale and cannot mutate the new
context.

Invalidation of controller authority is not permission to perform blocking
handler/session cleanup on the Qt GUI thread. Network/session cleanup continues
through the worker/core background ownership that created the resource.

## Stale Callback Policy

For PDU operation A followed by a newer context/operation B, any callback from A
that fails the controller's currentness predicate is stale.

This policy applies separately to:

- refresh result;
- refresh error;
- refresh progress/status;
- refresh finished;
- individual mutation result;
- individual mutation error;
- individual mutation progress/status;
- individual mutation finished;
- bulk result or partial terminal result;
- bulk error;
- bulk progress/status;
- bulk finished;
- refresh/reconciliation scheduled after a mutation.

A stale callback must not:

- update the current `PDUScreen`;
- change the outlet table or device information for a newer context;
- save or clear successful credential memory;
- advance credential fallback;
- start a new credential attempt;
- start refresh for a newer model/IP;
- start mutation reconciliation for a newer context;
- set, clear, unlock, or relock busy state owned by a newer operation;
- re-enable controls belonging to a newer mutation;
- update global refresh/loading state for a newer request;
- show an old result/error dialog as the outcome of the current context.

Stale finished is specifically not authority to clear a newer operation's busy
state. Stale mutation completion is specifically not authority to refresh the
currently selected device.

## Refresh Lifecycle

PDU refresh is controller-owned application lifecycle and remains read-only.

The controller:

1. captures immutable current context;
2. obtains the ordered candidate sequence and starting index through
   application-owned credential callbacks;
3. creates one worker attempt with one assigned credential or the existing
   PCS4i credentialless attempt when applicable;
4. submits the worker to the existing background execution boundary;
5. accepts only callbacks matching the active context and worker identity;
6. requests application-owned credential advancement only after an existing
   structured fallback-authorizing authentication outcome;
7. commits successful credential memory only at the existing approved final
   success gate and only when the credential was actually used where required.

This structural change does not broaden read-only credential retry authority.
Existing structured classification and candidate exhaustion behavior remain
unchanged.

## Individual Mutation Lifecycle

Individual outlet mutation is state-changing and controller-owned.

The controller captures model, IP, outlet, operation, generation, operation ID,
credential context, assigned candidate index when any, and expected worker
identity before submission.

Existing safety distinctions remain authoritative:

- safe failure before state-changing send;
- confirmed command rejection;
- ambiguous/unknown command outcome after possible delivery;
- stale operation.

The controller must never infer safe replay or credential fallback from generic
error text, absence of success, or an authentication-looking string.

Credential fallback is permitted only when the existing structured PDU safety
contract proves both that the device rejected the assigned credential and that
no state-changing send was attempted or could have been delivered. Once mutation
was sent, may have been delivered, or has an ambiguous outcome, the operation is
not automatically replayed with the same or another credential.

The extraction must preserve current per-model behavior rather than making every
PDU mutation retry-eligible merely because a generic controller exists.

## Sequential Bulk Mutation Lifecycle

Bulk ON/OFF remains one application-owned orchestration sequence executed by the
existing PDU background boundary.

The controller owns lifecycle identity and worker orchestration but preserves
`core.pdu` bulk execution semantics:

- one immutable ordered outlet sequence captured from current records;
- one assigned credential for the whole bulk attempt;
- sequential outlet execution;
- no concurrent individual mutation for the same current PDU context;
- no restart from outlet 1 with another credential after mutation begins or may
  have begun;
- completed outlets are not replayed;
- no rollback;
- fail-fast on terminal outlet failure;
- existing inter-outlet delay semantics outside the GUI thread;
- structured full/partial/stale terminal outcomes.

An empty `successful_outlets` list is not proof that credential fallback is
safe. Fallback authority comes only from structured confirmed authentication
failure plus structured zero-send safety evidence.

Successful credential memory is updated only after full successful bulk
completion when an assigned credential was actually used according to the
existing contract. Partial, failed, ambiguous, or stale bulk outcomes do not
save successful credential memory.

## Credential Ownership

Credential architecture does not move into the PDU controller.

The application/composition credential boundary remains the owner of:

- candidate sequence resolution;
- current successful credential index memory by device/IP;
- request-scoped candidate advancement policy;
- successful-index persistence;
- credential-context revision.

`PDUController` may receive injected callbacks/providers for:

- obtaining an already resolved ordered candidate sequence;
- obtaining the valid starting successful candidate index;
- advancing a request-scoped attempt only after a structured
  fallback-authorizing outcome;
- committing a successful candidate only after an approved success gate;
- obtaining the non-secret credential-context revision.

These callbacks do not make the controller a second independent credential
manager. The controller does not read `credentials.local.json`, maintain an
independent successful-index store, wrap candidate iteration, or infer fallback
from user-facing text.

Workers and handlers continue to receive one assigned credential only.
Transport fallback and credential fallback remain separate mechanisms; all
transport attempts within one credential attempt use that assigned credential.

## PCS4i Preservation

PCS4i keeps the existing password-only contract:

- no username is invented;
- an assigned candidate contains only the optional password after normalization;
- absence of mapping may produce the existing single credentialless PCS4i
  attempt rather than a generic configuration/authentication failure;
- `CredentialRequired` because a password prompt appeared without an assigned
  password is not reclassified as confirmed credential rejection;
- passwordless success does not create successful credential memory;
- an assigned but unused credential is not saved as successful;
- HTTP outlet-name 401/403 or other enrichment failure is not credential
  fallback authority;
- PCS4i REBOOT remains unsupported.

The controller must consume these semantics from existing structured outcomes
and application credential callbacks rather than replacing them with generic
PDU assumptions.

## Busy and Control-State Coordination

The controller owns authoritative current-operation busy state and context
identity. `PDUScreen` renders the accepted state.

At minimum, the lifecycle must distinguish:

- no active PDU mutation;
- active individual mutation with its operation identity;
- active bulk mutation with its operation identity.

A current active mutation prevents conflicting PDU mutation intents according to
existing UI behavior. Context invalidation gives the new context independent
control state. An old callback cannot unlock or relock the new context.

Implementation may keep local button-loading helpers in `PDUScreen`; those
helpers must be driven only by current controller state/outcomes and must not
become stale authority themselves.

## Refresh and Reconciliation After Mutation

Existing PDU mutation reconciliation behavior is preserved but moved under the
controller lifecycle.

A mutation outcome may schedule or request a refresh only when the originating
operation context is still current and existing policy requires reconciliation.
The follow-up refresh is bound to the original PDU context and receives its own
operation identity.

The reconciliation path must not:

- call `VCSDiagnosticApp.refresh_data()` without preserving originating context;
- refresh whichever device happens to be selected when an old callback arrives;
- reuse stale worker identity as current authority.

If context changes before reconciliation starts or completes, the old
reconciliation is dropped/suppressed and cannot update the new PDU context.

## Threading Model

All PDU network operations remain outside the Qt GUI thread, including:

- refresh;
- individual outlet mutation;
- sequential bulk mutation and inter-outlet delays;
- refresh/reconciliation after mutation;
- handler acquisition/connect;
- blocking handler/session cleanup when such cleanup is part of the operation.

A controller method may capture context, validate currentness, select an assigned
credential through application callbacks, and submit background work. It must
not directly execute blocking handler methods on the GUI thread.

Moving `handler.connect()`, `get_outlets_status()`, `turn_on()`, `turn_off()`,
`reboot()`, or equivalent synchronous calls from `VCSDiagnosticApp` into a plain
controller method is not a valid implementation.

## MainWindow Migration Boundary

Future implementation should remove these PDU-specific responsibilities from
`VCSDiagnosticApp`:

- PDU context revision/generation state;
- PDU operation serial/identity generation;
- PDU-specific descriptor construction;
- PDU refresh worker construction/submission;
- PDU individual mutation worker construction/submission;
- PDU bulk worker construction/submission/retry orchestration;
- PDU-specific worker signal binding;
- PDU stale callback predicates;
- PDU mutation/bulk busy ownership;
- PDU-specific result/error/finished handlers;
- PDU-specific refresh-after-mutation decisions.

Generic shell responsibilities, global credential memory/policy, global model/IP
selection, non-PDU request lifecycle, and unrelated device controllers remain in
their existing ownership boundaries unless a separate approved change moves
them.

## Risks / Trade-Offs

- The existing generic refresh lifecycle in `VCSDiagnosticApp` is shared by
  several device families. PDU extraction must avoid accidentally duplicating or
  changing generic shell behavior while making PDU callback ownership explicit.
- Some current PDU state is split between `PDUScreen` presentation fields and
  `VCSDiagnosticApp` context fields. Implementation must establish one
  authoritative controller identity while preserving screen rendering helpers.
- Credential policy injection can become overly abstract. Prefer focused PDU
  callbacks matching current application-owned operations rather than creating a
  new generic credential framework in this change.
- A controller that merely forwards every call back into `VCSDiagnosticApp`
  would not reduce context load. The PDU-specific lifecycle state machine and
  callback acceptance must actually move to the controller.
- A controller that absorbs `core.pdu` execution algorithms would create a new
  oversized boundary. Keep execution policy in `core.pdu` and lifecycle policy
  in `PDUController`.

## Migration Plan

1. Add a focused PDU controller/context type near the GUI composition boundary.
2. Introduce explicit `PDUScreen` refresh, individual mutation, and bulk mutation
   intents and remove arbitrary parent-method orchestration calls.
3. Move PDU refresh lifecycle and worker binding from `VCSDiagnosticApp` into the
   controller while preserving application credential callbacks.
4. Move individual mutation lifecycle and context-bound busy state into the
   controller without changing mutation safety or fallback semantics.
5. Move bulk mutation lifecycle, retry gating, and partial/full terminal handling
   into the controller without changing `core.pdu` sequencing semantics.
6. Move PDU stale/currentness predicates and PDU context generation into the
   controller.
7. Bind post-mutation refresh/reconciliation to the originating immutable
   context.
8. Reduce `VCSDiagnosticApp` to PDU composition, shell-state wiring, credential
   callbacks, context updates, and shutdown delegation.
9. Add focused regression coverage and run the full offline suite plus strict
   repository-local OpenSpec validation.
