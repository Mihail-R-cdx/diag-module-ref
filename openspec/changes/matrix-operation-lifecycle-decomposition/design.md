## Context

`worker-module-decomposition` has already moved the canonical Matrix refresh
worker to `core/workers/matrix.py` and reduced `core/worker.py` to a public
compatibility facade. The next Matrix hotspot is therefore above the worker
layer: Matrix operation lifecycle and ownership.

Current Matrix architecture:

```text
VCSDiagnosticApp
  owns global device/IP widgets
  owns credential provider, credential fallback, successful credential index
  owns generic worker binding and stale refresh callback checks
  owns Matrix persistent handler fields and keepalive timer
  starts ExtronIN1804Worker for refresh
  updates MatrixScreen from worker result

MatrixScreen
  renders routing table and device info
  reads main_window.ip_entry and main_window.device_combo on route click
  reads main_window.device_credentials and current credential index
  calls main_window.ensure_matrix_persistent_handler()
  invokes handler.set_connection() directly
  schedules a quick refresh that calls handler.get_connections() directly

core/workers/matrix.py
  owns ExtronIN1804Worker refresh polling
  creates ExtronIN1804Handler in a QRunnable
  parses via ExtronIN1804DataParser
  disconnects its handler before finished

handlers/extron/in1804.py
  owns Extron SIS/Telnet command semantics
  owns connect, disconnect, get_full_status, get_connections, set_connection
```

The general worker refresh path already carries `_active_request` identity and
ignores stale result, error, progress, status, and finished callbacks through
`_request_is_current()`. DMP has an even stricter model/IP/generation/token
guard. Matrix refresh benefits from the generic worker guard, but Matrix route
mutation, quick refresh, persistent handler acquisition/reuse, keepalive, and
refresh-after-mutation are still spread between the screen and main window.

## Goals

- Reduce Matrix context load so a typical Matrix change does not require
  reading most of `gui/main_window.py`.
- Put Matrix operation lifecycle in one Matrix-specific application component.
- Remove handler acquisition, credentials, persistent session state, retry
  policy, and direct network I/O from `MatrixScreen`.
- Preserve application-owned credential candidate selection, fallback, and
  successful credential memory.
- Keep Matrix refresh, route mutation, persistent session acquisition/reuse,
  and quick/status refresh outside the Qt GUI thread.
- Make stale Matrix result, error, progress/status, finished, and
  refresh-after-mutation callbacks unable to affect a newer Matrix context.
- Preserve existing user-visible Matrix rendering and route behavior.

## Non-Goals

- Do not implement this architecture in production code in this change.
- Do not decompose unrelated `MainWindow` responsibilities.
- Do not extract PDU, DMP, codec, SIP, or generic credential architecture.
- Do not create a universal controller or manager shared by multiple device
  families.
- Do not move Matrix worker implementation back into `core/worker.py`.
- Do not introduce blind replay for state-changing route commands.

## Target Architecture

```text
MatrixScreen
  -> routeRequested(MatrixRouteIntent)
  -> refreshRequested()

MatrixController
  -> creates immutable MatrixOperationContext
  -> resolves operation through application-owned credential policy
  -> submits refresh / route / status work to background execution
  -> owns persistent Matrix handler/session lifecycle
  -> accepts only callbacks matching active Matrix context

core/workers/matrix.py / Matrix background operation
  -> invokes ExtronIN1804Handler off the GUI thread
  -> returns structured result/error/status/finished

handlers/extron/in1804.py
  -> owns SIS/Telnet protocol and transport primitives

MatrixController
  -> emits accepted display updates and route outcomes

MatrixScreen
  -> displays Matrix data and route state
```

The exact class name may be `MatrixController` unless implementation finds a
more precise local naming convention. The controller should live near the GUI
application composition boundary, for example under `gui/` or a focused
application/controller package, not in `core/workers/`, not in the handler
package, and not in `core/worker.py`.

## Ownership Boundaries

### MatrixScreen

`MatrixScreen` owns:

- rendering the routing table, signal/HDCP indicators, selected route, and
  device information;
- translating clicks and UI actions into non-secret user intents;
- local display state such as selected row highlighting and stale-free data
  rendering after the controller accepts an update.

`MatrixScreen` must not own:

- credential lists, credential indexes, or credential fallback;
- handler acquisition, persistent session state, or transport keepalive;
- retry/fallback policy;
- direct `set_connection()`, `get_connections()`, `get_full_status()`, or any
  other network I/O;
- handler objects, session objects, or secrets in Qt signal payloads.

The intended screen boundary is a small intent interface:

- route request: model, IP or public device context reference, output number,
  and input number, without credentials or handler/session objects;
- refresh request: public Matrix context, without credentials or handler
  objects.

Implementation may capture model/IP in the controller instead of sending them
through the screen signal if that better fits current composition wiring. In
either case, widgets are not the authoritative context for background
operations after submission.

### Matrix Controller

The Matrix controller owns Matrix-specific lifecycle:

- refresh request lifecycle;
- route action lifecycle;
- background worker/background operation ownership;
- active Matrix request identity;
- immutable context capture;
- stale result, error, finished, and progress/status suppression;
- persistent handler/session creation, reuse eligibility, and cleanup;
- cleanup on model, IP, credential context, screen, and application changes;
- refresh-after-mutation scheduling and context binding;
- Matrix terminal/status messages emitted without secrets.

The controller is Matrix-specific. It must not absorb unrelated PDU, DMP,
codec, SIP, or generic credential responsibilities from `VCSDiagnosticApp`.

The controller consumes the existing application credential boundary rather
than creating a second credential manager. It may receive a resolver/callback
from `VCSDiagnosticApp` that returns ordered candidates, current successful
index, and commit/fallback operations. The application layer remains the only
owner of successful credential index memory.

### MainWindow

After extraction, `VCSDiagnosticApp` owns Matrix composition only:

- creates `MatrixScreen` and the Matrix controller;
- wires screen intents to controller methods and controller outputs to screen
  updates;
- provides global model/IP changes to the controller;
- provides the existing credential provider/policy callbacks;
- routes close/application cleanup to controller shutdown;
- keeps global refresh button and shell state in sync with accepted controller
  lifecycle events.

`VCSDiagnosticApp` should no longer carry Matrix persistent handler fields,
Matrix keepalive logic, route mutation, quick refresh, or Matrix-specific stale
state machine details directly once the implementation is complete.

### Worker

`core/workers/matrix.py` remains the canonical Matrix worker module. It owns
background Matrix refresh polling and compatible worker signal payloads. It
does not own credential fallback, successful credential memory, active request
generation, persistent session reuse policy, or GUI callback acceptance.

A future route/status background operation may reuse `ExtronIN1804Worker`,
extend the focused Matrix worker module, or introduce a focused Matrix
operation runnable. The required property is that Matrix network I/O remains
off the GUI thread and stays under the Matrix-specific lifecycle boundary.

### Handler and Parser

`handlers/extron/in1804.py` owns protocol and transport primitives:

- `connect()` / `disconnect()`;
- read commands such as `get_full_status()` and `get_connections()`;
- state-changing command `set_connection(output_num, input_num)`;
- device-specific command validation and response interpretation.

`ExtronIN1804DataParser` owns normalization of handler status into the
GUI-facing Matrix data shape. Neither handler nor parser chooses credentials,
reads provider files, advances credential indexes, checks Qt widgets for
freshness, or emits GUI signals.

## Request Context Model

A Matrix operation context should be immutable after submission and contain at
least:

- model, currently `Extron IN1804`;
- IP address;
- output number and input number for route mutation;
- operation kind: refresh, route mutation, quick/status refresh, keepalive, or
  cleanup;
- generation or request ID;
- expected worker/background-operation identity when applicable;
- assigned credential index and non-secret credential context identity when
  applicable;
- whether the operation is read-only or state-changing.

Qt widgets may provide initial values when the user submits an intent, but
background operations must use the captured context. Later widget changes do
not mutate an in-flight context.

Staleness is defined by comparing the callback context against the controller's
current Matrix generation, model/IP, assigned credential context, and expected
operation/worker identity. A callback that fails this comparison is stale.

## Stale Callback Policy

For the scenario:

1. operation A starts for device A;
2. operation A is still running;
3. user changes model/IP/context;
4. operation B starts for device B;
5. callback from operation A arrives later;

the callback from A must not:

- update Matrix data for B;
- publish old routes in the new context;
- save a successful credential for B;
- start credential fallback for B;
- reset ownership of B's worker/background operation;
- re-enable or unlock B's active operation lifecycle;
- start refresh of B;
- reuse A's handler/session for B.

This applies separately to stale result, stale error, stale finished, stale
progress/status, and stale terminal/log events. Stale callbacks may be logged
in redacted developer diagnostics, but they are not user-visible outcomes for
the active context.

## Threading Model

Matrix network I/O must not run in the Qt GUI thread. This includes:

- initial Matrix refresh;
- quick/status refresh after route mutation;
- route mutation itself;
- persistent handler/session acquisition and reconnect;
- keepalive or liveness probes;
- cleanup that performs blocking network/session close work when such cleanup
  can block.

Moving a synchronous handler call from `MatrixScreen` to a normal controller
method is not sufficient. The controller method may compose context and submit
work, but handler invocation must run on the Matrix background execution
boundary.

The existing `ExtronIN1804Worker` is already a QRunnable for refresh. Route
mutation and quick/status refresh need an equivalent background boundary and
typed callback identity.

## Credential Ownership

The existing application/composition layer owns:

- credential candidate selection;
- credential fallback decisions;
- successful credential index memory;
- redaction of public attempt and terminal messages.

The Matrix controller participates in that application boundary but does not
become an independent credential manager. It asks for the resolved candidate
sequence and reports structured outcomes that let the application-owned policy
advance or commit indexes.

Credential fallback for Matrix is allowed only after a structured confirmed
authentication failure and only when safe for the operation. String heuristics
such as `auth`, `401`, or `403` embedded in generic error text do not authorize
fallback.

## State-Changing Route Mutation Safety

Matrix route mutation is a state-changing command. A route operation must not
be blindly repeated after an ambiguous outcome.

Before the command is sent, structured authentication failure during handler
or session acquisition may permit credential fallback. After `set_connection`
has been invoked, may have been delivered to the transport, or has an
ambiguous outcome, the controller must not retry the mutation with another
credential or replay the command automatically.

After an accepted successful route mutation, the controller schedules a
read-only refresh/status reconciliation bound to the same original Matrix
context. If the user changes model/IP/context before that refresh runs or
before its callback arrives, the refresh is stale and cannot update the new
context.

## Persistent Session Policy

The current application has a persistent Matrix handler and keepalive timer.
The target architecture keeps or removes persistence based on explicit
lifecycle rules, not because the current fields exist.

Selected policy:

- The Matrix controller owns the persistent handler/session if persistence is
  retained.
- A session is reusable only when model, IP address, assigned credential
  identity/index, protocol/port, and local connected state match the current
  Matrix context.
- Cross-context reuse is forbidden. Model change, IP change, credential
  change/fallback, explicit reconnect, authentication/session failure, screen
  destruction, and application close invalidate the old session.
- One persistent handler must not be used concurrently by overlapping refresh
  and route operations unless implementation proves the handler is thread-safe
  for that use. The conservative design is serialized Matrix handler access
  per context.
- Session creation, blocking liveness checks, route mutation, quick refresh,
  and cleanup run on the owning background lane.
- Cleanup is idempotent. A stale cleanup/finished callback cannot clear the
  active session for a newer Matrix context.

If implementation proves that the persistent session adds more risk than value,
it may replace it with per-operation handler ownership, but must preserve route
behavior, cleanup, background execution, and explicit stale guarantees. That
decision should be recorded in implementation evidence.

## Dependency Direction

Allowed direction:

```text
VCSDiagnosticApp composition
    -> MatrixController
    -> MatrixScreen intent/display API
    -> core.workers.matrix or focused Matrix background operation
    -> handlers.extron.in1804
    -> core.parser.ExtronIN1804DataParser
```

Forbidden direction:

- `MatrixScreen` importing or creating `ExtronIN1804Handler`;
- `MatrixScreen` reading credential candidates or handler/session objects;
- Matrix controller importing PDU/DMP/codec controllers for generic reuse;
- Matrix workers importing GUI modules or `core.worker`;
- handlers importing worker or GUI signal modules;
- `core/worker.py` regaining Matrix lifecycle implementation.

## Alternatives Considered

### Keep route calls in MatrixScreen

Rejected. It preserves direct GUI-thread network I/O and requires every Matrix
screen change to understand credentials, handler reuse, and session cleanup.

### Move route calls into MainWindow only

Rejected. It would reduce direct screen ownership but keep Matrix lifecycle
inside the already large `VCSDiagnosticApp`, which does not meet the
context-load objective.

### Add a generic operation manager

Rejected. PDU, DMP, codec interactive, and Matrix lifecycles have different
mutation safety, cancellation, session, and credential-success contracts. A
generic manager would hide important differences and expand scope.

### Put persistent session logic in the handler

Rejected. The handler owns protocol mechanics, not GUI/application context,
credential fallback, stale suppression, or screen lifecycle.

### Remove persistent sessions immediately

Deferred. Removing persistence may be the right implementation if analysis
shows it is safer, but the architecture decision must be made with focused
evidence. This design instead defines the required ownership and reuse rules.

## Risks and Mitigations

- Route mutation currently runs synchronously from a screen callback.
  Mitigation: add focused tests proving route mutation and follow-up refresh
  execute on the background boundary.
- Persistent handler reuse can cross model/IP/credential contexts.
  Mitigation: immutable Matrix context identity and strict reuse predicate.
- Stale route callbacks can update a newer screen or reset active lifecycle.
  Mitigation: controller-owned generation/request ID and expected operation
  identity checks for result, error, progress/status, and finished callbacks.
- Credential fallback after mutation could duplicate a state-changing route
  command. Mitigation: allow fallback only before any possible command send and
  only from structured authentication failure.
- Moving orchestration out of `MainWindow` can accidentally broaden scope.
  Mitigation: keep this controller Matrix-specific and leave PDU, DMP, codec,
  SIP, and generic credential architecture untouched.
- Screen/controller signal boundaries might leak secrets. Mitigation: only
  non-secret intent and public status/result payloads cross Qt signals.

## Acceptance Coverage

Future implementation should add focused tests for:

- `MatrixScreen` does not call handlers/network operations directly;
- route mutation does not run in the GUI thread;
- Matrix refresh and quick refresh do not run in the GUI thread;
- stale Matrix result does not update a newer context;
- stale Matrix error does not affect a newer context;
- stale Matrix finished does not reset a newer worker/lifecycle;
- route follow-up refresh remains bound to the original Matrix context;
- handler/session for device A is not reused for device B;
- credential fallback remains application-owned and structured;
- existing Matrix rendering and route behavior remain compatible.
