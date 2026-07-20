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
  -> owns one persistent Matrix handler/session for the active Matrix context
  -> serializes all access to that persistent session
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
- serialized access to the one active persistent Matrix handler/session;
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
- non-secret credential context revision or equivalent opaque revision token
  that changes when credential configuration changes;
- assigned credential candidate index when applicable;
- whether the operation is read-only or state-changing.

Qt widgets may provide initial values when the user submits an intent, but
background operations must use the captured context. Later widget changes do
not mutate an in-flight context.

Staleness is defined by comparing the callback context against the controller's
current Matrix generation, model/IP, credential context revision, assigned
candidate index when relevant, and expected operation/worker identity. A
callback that fails this comparison is stale. Credential candidate index alone
is not a sufficient identity: candidate `0` can be replaced in configuration
while remaining index `0`, and the old session must then become stale without
credential values crossing public contexts.

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
advance or commit indexes only at the approved Matrix credential-success gate.

Credential fallback for Matrix is allowed only after a structured
authentication outcome whose semantics explicitly confirm that the assigned
credential was rejected by the device on a supported authentication path, and
only when safe for the operation. The `AuthenticationError` exception class
alone is not credential-fallback authority. Local authentication or credential
configuration precondition failures, including missing username, missing
password, or incomplete credential configuration, do not authorize fallback
unless the device has explicitly confirmed rejection of the assigned
credential. String heuristics such as `auth`, `401`, or `403` embedded in
generic error text do not authorize fallback.

Credential configuration changes publish a new non-secret credential context
revision or equivalent opaque token through the application-owned credential
lifecycle. The Matrix controller includes that revision in Matrix operation and
session identity. Usernames, passwords, profile names, and other secret
credential values do not appear in context identity, signals, results, logs, or
terminal output.

Matrix credential-success gates are intentionally narrow:

- an accepted, non-stale, final successful full Matrix refresh with parsed
  device data may save the assigned credential index for the model/IP context;
- session acquisition, connect, login/authentication, or persistent session
  creation alone does not save a successful credential index;
- successful route mutation does not update successful credential memory in
  this structural change;
- quick/status refresh used as route reconciliation does not introduce a new
  independent credential-memory semantic;
- stale success never updates credential memory.

## Structured Matrix Authentication Classification

Current technical debt:

- `ExtronIN1804Worker` currently maps a generic exception to
  `authentication_error` by checking whether the redacted error message
  contains `"authentication"`.
- `BaseExtronMatrixHandler.connect()` currently stores transport-attempt
  failures as strings and later searches the aggregated strings for words such
  as `auth`, `login`, or `password` before raising `AuthenticationError`.

Both legacy paths must be removed during implementation of this change. The
future Matrix lifecycle must preserve structured failure categories end to end.

The structured authentication outcome is formed at typed failure boundaries,
but the `AuthenticationError` type alone is not automatically a confirmed
credential rejection:

- authentication/configuration precondition failures such as missing username,
  missing password, incomplete credential configuration, or failure before the
  device can reject the assigned credential remain non-fallback-authorizing
  structured outcomes even if represented by `AuthenticationError`;
- a fallback-eligible authentication outcome must additionally carry or
  unambiguously express semantics that the assigned credential was actually
  rejected by the device on a supported authentication path;
- Matrix workers and Matrix background operations may translate a caught
  structured `AuthenticationError` into a fallback-eligible
  worker/application authentication category only when those confirmed
  rejection semantics are present; the exception class by itself is
  insufficient;
- handler connection, timeout, negotiation, unsupported service, malformed
  protocol, and command/protocol failures keep non-authentication categories;
- Matrix workers and background operations must not search exception text for
  `auth`, `authentication`, `login`, `password`, `401`, `403`, or similar
  strings and must not convert generic transport/protocol failures into
  authentication failures based on message text.

Transport fallback and credential fallback remain separate. A Matrix
connection operation may try multiple supported transport/profile attempts, but
every attempt uses the same assigned credential candidate. The handler does not
select another credential, the worker does not select another credential, and
transport fallback never advances the credential candidate index.

For a sequence of Matrix transport attempts, the handler or replacement
connection logic must preserve structured category and confirmed-rejection
semantics for each attempt. Conceptual shape:

```text
attempt 1 -> structured authentication_precondition, no confirmed rejection
attempt 2 -> structured confirmed_credential_rejection
attempt 3 -> structured ConnectionError
```

The final Matrix connection outcome is classified conservatively:

- confirmed authentication failure: only when structured failure semantics
  unambiguously prove the assigned credential was rejected by the device on a
  supported authentication path;
- transport/connection/protocol failure: timeout, connection refusal,
  SSH/Telnet negotiation failure, unsupported service, malformed protocol
  response, and other non-authentication failures stay non-authentication even
  when their message text contains authentication-like words;
- local authentication/configuration precondition failure: missing required
  authentication input, incomplete credential configuration, or any failure
  before confirmed device rejection remains non-fallback-authorizing;
- mixed outcomes: an ambiguous mixture of authentication and non-authentication
  transport failures does not authorize credential fallback unless the final
  structured outcome is an unambiguous confirmed authentication rejection.

The application-owned credential fallback policy may consider the next
candidate only after it receives a final structured authentication outcome that
explicitly confirms device rejection of the assigned credential. Receiving an
`AuthenticationError` exception without those semantics is not sufficient.
There is no compatibility shortcut where any error string containing `auth`,
`authentication`, `login`, `password`, `401`, or `403` authorizes credential
fallback.

## State-Changing Route Mutation Safety

Matrix route mutation is a state-changing command. A route operation must not
be blindly repeated after an ambiguous outcome.

Before the command is sent, only a structured authentication outcome that
explicitly confirms device rejection of the assigned credential during handler
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
The approved target architecture retains a persistent Matrix handler/session
and moves its application-level ownership to the Matrix controller.
Implementation sessions must not replace this with per-operation handler
ownership without a separate approved architecture change.

The Matrix controller owns one persistent Matrix session for the active Matrix
context:

- The persistent handler/session is created and managed by the Matrix
  controller.
- The handler/session does not belong to `MatrixScreen`.
- The handler/session no longer belongs directly to `VCSDiagnosticApp`.
- The persistent session identity includes model, IP address, protocol/port,
  non-secret credential context revision or equivalent opaque token, and the
  assigned candidate index.
- Credential candidate index alone is insufficient for reuse.
- A session is reusable only when the full persistent session identity and
  local connected state match the current Matrix context.
- Cross-context reuse is forbidden. Model change, IP change, credential
  configuration change, credential fallback, explicit reconnect,
  authentication/session failure, screen destruction, and application close
  invalidate the old session.
- Access to the one persistent handler is serialized. Overlapping route,
  refresh, quick/status refresh, and keepalive operations do not invoke that
  handler concurrently.
- Session acquisition, blocking liveness checks, route mutation, quick refresh,
  keepalive, and cleanup run on the owning background lane outside the Qt GUI
  thread.
- Cleanup is idempotent. A stale cleanup/finished callback cannot close,
  clear, or disconnect the active session for a newer Matrix context.

Conceptually, the reusable session identity is:

```text
MatrixSessionIdentity:
    model
    ip_address
    protocol
    port
    credential_context_revision
    candidate_index
```

The exact Python shape may differ, but the contract is fixed: the identity
contains a non-secret credential configuration revision/token in addition to
the candidate index, and it never contains username, password, or other secret
credential values.

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

Rejected. The approved target architecture retains one persistent Matrix
session owned by the Matrix controller, with serialized access and strict
context invalidation. Replacing it with per-operation handler ownership would
be a separate architecture change, not an implementation choice for this
change.

## Risks and Mitigations

- Route mutation currently runs synchronously from a screen callback.
  Mitigation: add focused tests proving route mutation and follow-up refresh
  execute on the background boundary.
- Persistent handler reuse can cross model/IP/credential contexts.
  Mitigation: immutable Matrix session identity includes model, IP, protocol,
  port, credential context revision, candidate index, and local connected
  state; candidate index alone is never enough.
- Stale route callbacks can update a newer screen or reset active lifecycle.
  Mitigation: controller-owned generation/request ID and expected operation
  identity checks for result, error, progress/status, and finished callbacks.
- Credential fallback after mutation could duplicate a state-changing route
  command. Mitigation: allow fallback only before any possible command send and
  only from structured semantics that explicitly confirm device rejection of
  the assigned credential.
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
- credential configuration change invalidates Matrix persistent session even
  when candidate index remains the same;
- credential fallback remains application-owned and requires explicit structured
  confirmed device credential rejection semantics rather than only an
  `AuthenticationError` exception class;
- local authentication/configuration precondition failures, including missing
  username or password, do not advance credential candidates;
- accepted full Matrix refresh may cache the assigned credential index;
- session acquisition, route mutation, route reconciliation, and stale success
  do not cache credential memory;
- existing Matrix rendering and route behavior remain compatible.
