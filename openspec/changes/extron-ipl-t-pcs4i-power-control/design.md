## Context

Aten PE8208AV is currently the only production PDU. It appears under the
power-control device category, maps to `PDUScreen`, refreshes through
`AtenPDUWorker`, and exposes `get_outlets_status()`, `get_device_info()`,
`turn_on()`, `turn_off()`, and `reboot()` from `handlers/aten/pdu.py`.
`PDUScreen` renders whichever outlet records the worker returns, so it can
display four PCS4i outlets when the PCS4i worker returns four records.

The risky precedent is outlet control. `PDUScreen.on_outlet_control()` calls
`VCSDiagnosticApp.control_pdu_outlet()`, and that method creates an
`AtenPDUHandler`, connects, and sends `on`, `off`, or `reboot` synchronously on
the Qt GUI thread. PCS4i must not copy this path, and Aten commands must be
migrated to the same background PDU command boundary without changing Aten wire
semantics.

Protocol discovery and official Extron SIS evidence now resolve the PCS4i
Telnet command contract for identity, power-state readback, ON, and OFF. The
same discovery did not identify a native PCS4i REBOOT operation. Architecture
therefore treats PCS4i REBOOT as unsupported, not as an open protocol question.

Existing root specs already establish credential ownership, request-context
isolation, structured retry authority, redacted diagnostics, and background
network work. The PCS4i design extends those rules to PDU refresh and control.

## Goals / Non-Goals

**Goals:**

- Add PCS4i as a supported production power-control PDU without changing the
  operator workflow that Aten uses.
- Keep GUI rendering generic by using `PDUScreen` and returning exactly the
  handler/worker outlet records.
- Keep Telnet status/control and HTTP outlet-name enrichment separate.
- Make optional password-only authentication explicit and bounded.
- Support both passwordless and password-protected PCS4i configurations.
- Ensure no PCS4i Telnet connect, read, command, or HTTP request runs in the Qt
  GUI thread.
- Prevent stale queued PDU refresh and command operations from acquiring
  handlers or sending network I/O after device/IP/credential context changes.
- Reject unsupported PCS4i REBOOT before handler acquisition and before any
  Telnet or HTTP network I/O.
- Prevent blind replay of PCS4i ON/OFF state-changing commands.
- Move the existing Aten outlet command path to the same asynchronous PDU
  command execution boundary and protect Aten ON/OFF/REBOOT with regression
  tests.

**Non-Goals:**

- Do not implement production code in this architectural change.
- Do not create a PCS4i-specific GUI screen.
- Do not make Aten inherit from PCS4i or PCS4i inherit from Aten.
- Do not add PCS4i REBOOT through native, composite, or fallback behavior.
- Do not define an unverified HTTP GET path for PCS4i outlet names.
- Do not create a broad transport abstraction that hides device protocols.
- Do not archive this change or merge runtime behavior.

## Decisions

### Use the existing power-control UI with model-specific capabilities

Add `"Extron IPL T PCS4i": "pdu"` to the main device-to-screen mapping and add
the device item under the existing power-control category in the combo. The
screen remains `PDUScreen`; no new screen class is introduced.

The PCS4i refresh result shape matches the current PDU screen contract:

- `device_info`: model, manufacturer, IP address, connected/status, optional
  firmware, optional description, optional part number, and optional security
  level when available;
- `outlets`: exactly four outlet records with `number`, normalized `status`,
  and `name`;
- `type`: `pdu`;
- capability metadata that lets the application/UI expose only refresh, ON, and
  OFF for PCS4i.

`PDUScreen` must render the number of returned records rather than assuming
eight Aten rows. PCS4i therefore displays four rows because the worker returns
four rows. `PDUScreen` must render controls from model-supported capabilities:
PCS4i gets ON and OFF controls only; REBOOT is not shown. Aten continues to
display its returned Aten records and ON/OFF/REBOOT controls.

Application dispatch validates the selected model supports the requested
operation before worker creation. If a PCS4i REBOOT operation is submitted
programmatically, dispatch rejects it as unsupported before handler acquisition
and before any Telnet or HTTP network I/O. This unsupported-operation gate is
separate from stale-generation validation; both gates are deterministic and run
before network I/O.

Alternative considered: build a PCS4i-specific screen. Rejected because the
operator operations and data surface are shared enough for one PDU screen, while
capabilities can be model-specific.

### Keep handler protocols separate and share only the operation contract

Create a focused PCS4i handler, expected under `handlers/extron/`, with this
device-specific surface:

- `get_outlets_status()`
- `get_device_info()`
- `turn_on(outlet_number)`
- `turn_off(outlet_number)`

The PCS4i handler must not expose `reboot(outlet_number)` as a supported
operation. The shared contract is the PDU operation surface plus
model-specific capability declaration, not a shared wire transport and not an
identical command set. The Aten handler remains the owner of the Aten
HTTPS/XML/API protocol and its native REBOOT operation. The PCS4i handler owns
its Telnet command parsing and required HTTP outlet-name enrichment path.

Common code may dispatch operations to either handler through a small PDU
worker/factory boundary, but it must not force a generic Telnet/HTTP transport
abstraction across unrelated devices.

### Use confirmed PCS4i SIS commands over Telnet

PCS4i uses Telnet on port 23. Telnet is authoritative for connection,
authentication/session readiness, identity, outlet power state, ON, OFF, and
post-command readback. HTTP is not authoritative for outlet power state.

SIS notation:

- `ESC` = byte `0x1B`
- `CR` = byte `0x0D`
- `LF` = byte `0x0A`

Confirmed identity and session commands:

- model query: `1I<CR>` -> `IPL T PCS4i`
- model description query: `2I<CR>` -> `Four Switched 220v AC Receptacles with Current Threshold Sensing`
- part number query: `N<CR>` -> `60-544-09`
- firmware query: `Q<CR>` -> discovered firmware `1.16`
- security level query: `<ESC>CK<CR>` -> documented values `11` User and
  `12` Administrator; live discovery returned `12<CR><LF>`

Confirmed outlet commands for outlet `N` where `N` is 1 through 4:

- authoritative power-state readback: `<ESC>NPC<CR>`
- power-state responses: `0<CR><LF>` means OFF and `1<CR><LF>` means ON
- current/reference threshold state: `<ESC>NPS<CR>` with documented responses
  `0` clear/none, `1` standby, `2` full
- ON: `<ESC>N*1PC<CR>` with acknowledgement grammar `CpnN Ppc1<CR><LF>`
- OFF: `<ESC>N*0PC<CR>` with acknowledgement grammar `CpnN Ppc0<CR><LF>`

`PC` is the authoritative outlet ON/OFF state. `PS` is current/reference
threshold state and must never be used as a substitute for power state. Live
discovery read `PC` as `1<CR><LF>` for all four outlets and `PS` as
`0<CR><LF>` for all four outlets.

State-changing ON/OFF command acknowledgement is not the final authority.
After ON or OFF, final state is established by a separate authoritative
`<ESC>NPC<CR>` readback. Outlet numbers outside 1 through 4 are rejected before
network send.

State-changing ON/OFF commands were not executed on the discovered device
because the discovery session did not receive explicit authorization variables
for mutating live tests. That is not a protocol blocker: ON and OFF command
strings are confirmed by official protocol evidence. Production tests must
verify parser and recovery behavior with synthetic transports rather than
requiring live mutating tests.

### Support passwordless and password-protected Telnet sessions

PCS4i has two supported session modes:

- Passwordless configuration: initial bytes contain no `Password` marker, a
  verified read-only SIS probe succeeds, and zero password sends occur.
- Password-protected configuration: new session bytes contain the protocol
  marker `Password`, possibly as `Password`, `Password:`, `Password:*`, or
  `Password:**********************`.

Prompt detection is based only on the presence of `Password` in the new bytes
for the current protocol phase. It must not depend on a colon, asterisks, a
specific asterisk count, or an exact full prompt string.

Prompt detection is phase-scoped:

- initial receive phase examines only initial newly received bytes;
- post password send #1 phase examines only bytes received after send #1;
- post password send #2 phase examines only bytes received after send #2.

A `Password` occurrence in the initial receive data is never reused as a
post-send prompt. The implementation must not search one accumulated session
buffer to decide whether a repeated prompt appeared.

Session establishment:

```text
CONNECT
  |
  v
BOUNDED INITIAL SESSION OBSERVATION
  |
  +--> new bytes contain "Password" -> PASSWORD FLOW
  |
  +--> no Password marker observed
           |
           v
      VERIFIED READ-ONLY SESSION PROBE
           |
           +--> verified response -> SESSION READY WITHOUT PASSWORD
           +--> Password marker appears -> PASSWORD FLOW
           +--> timeout/disconnect/protocol failure -> CONNECTION/PROTOCOL FAILURE
```

Absence of a prompt is not proof of readiness. A passwordless ready session
must be proven by successful non-mutating protocol evidence, such as
`<ESC>CK<CR>` or a verified `PC` readback.

Password flow:

```text
new phase bytes contain Password
  |
  +--> no assigned credential -> CredentialRequired, send zero passwords
  |
  +--> assigned credential present
          |
          v
      send assigned password #1
          |
          +--> Login Administrator/Login User or verified read-only response -> SESSION READY
          +--> new post-send bytes contain Password -> send same assigned password #2
                  |
                  +--> session-ready evidence -> SESSION READY
                  +--> new post-send bytes contain Password -> AuthenticationError
```

The second password send is a repeat of the same assigned password, not
credential fallback. One worker attempt receives at most one assigned
credential. Only the application/composition layer may decide to try another
credential candidate after a structured confirmed `AuthenticationError`.
Never send a third password in one connection attempt.

If no credential was assigned and PCS4i requests `Password`, return a structured
`CredentialRequired` outcome. This is not `AuthenticationError` because no
credential was rejected. If a credential candidate was assigned but no prompt
appears and the read-only probe succeeds, the credential was not used: do not
cache it as successful, do not update the successful credential index, do not
invalidate an existing saved index, and do not initiate credential fallback.

State-changing commands are never the first authentication/readiness probe.
Only verified read-only evidence can prove readiness before ON/OFF.

### Keep credential fallback in the application layer

PCS4i uses `auth_mode: "password"` and no username. Credential resolution stays
at the GUI/application composition boundary. A PCS4i worker receives zero or
one assigned credential for one attempt and passes only the optional password
to the handler. The handler does not read `credentials.local.json`, inspect
candidate lists, select a later credential, wrap around, or remember a
successful index.

PCS4i has a device-scoped exception to the usual "missing mapping is a
configuration error" behavior. If a PCS4i operation has an explicit credential,
explicit profile, or mapped credential chain, the application builds the normal
ordered credential plan and each worker attempt receives at most one assigned
credential. If a PCS4i operation has no explicit credential, no explicit
profile, and no device mapping, the application/composition layer creates one
credentialless attempt instead of stopping before network I/O. That descriptor
has assigned credential `none`, no candidate index, and no successful
credential index for that attempt.

The credentialless PCS4i attempt may connect, perform bounded initial
observation, see no `Password` marker, run a verified read-only SIS readiness
probe, and complete as a successful passwordless session. If that same
credentialless attempt receives a `Password` marker, it returns structured
`CredentialRequired`, sends no password, does not return `AuthenticationError`,
does not start a next credential candidate because no credential plan exists,
and surfaces a safe actionable error telling the operator to configure a
credential.

Credentialless success never creates or updates successful credential memory.
It does not create a successful credential index, does not change an existing
cached index, and does not invalidate credential memory. Likewise, if an
assigned credential candidate was passed but the device never requested
`Password`, the operation may complete as passwordless success but that
candidate was not used and its index is not saved as successful.

This credentialless composition path is scoped to protocol/device paths that
support unauthenticated/passwordless operation; in this change, that means
PCS4i only. Other authentication-required devices remain blocked before network
I/O when required credentials are absent.

Credential fallback is authorized only by a structured confirmed
`AuthenticationError`, meaning an actually sent credential was rejected by the
phase-scoped Telnet password flow. The following are not fallback authority:
timeout, disconnect, malformed Telnet response, protocol parse failure, no
`Password` prompt, passwordless success, `CredentialRequired`, HTTP failure,
HTTP 401, HTTP 403, or arbitrary text containing authentication-like words.

Secret handling is mandatory. The transmitted password never appears in stdout,
debug logs, GUI dialogs, exceptions, public error messages, test assertions, or
validation reports. Device-emitted asterisks are not themselves secret, but
session buffers must not be logged without safe redaction.

### Implement HTTP outlet-name loading as read-only enrichment

Live discovery confirmed outlet names in device-served HTML/JavaScript as:

- `xName1` -> `Receptacle 1`
- `xName2` -> `Receptacle 2`
- `xName3` -> `Receptacle 3`
- `xName4` -> `Receptacle 4`

The default live values do not prove custom names are unsupported. The
representation and four-outlet mapping are confirmed; the exact HTTP GET path
containing `xName1` through `xName4` must be confirmed from captured evidence
before production parser implementation if that exact path is not already
available. Do not guess an endpoint and do not infer a read endpoint from a page
that only demonstrated a write mechanism.

On the discovered device, `GET /` returned `200 OK` with `Content-Type:
text/html` and no `WWW-Authenticate` or `Set-Cookie`. This is evidence that
that device/configuration did not require HTTP authentication; it must not be
generalized into "PCS4i HTTP never requires authentication."

Refresh flow:

1. Establish authoritative Telnet session.
2. Read authoritative Telnet outlet state with `PC`.
3. Build exactly four normalized outlet records with fallback names.
4. Attempt the implemented read-only HTTP name-loading path after Telnet status
   is available.
5. Replace fallback names with verified non-empty `xNameN` values where
   available.
6. Preserve Telnet status and use fallback names for affected outlets when HTTP
   is unavailable, malformed, unsupported, 401/403, login-rejected, or missing
   a specific name.

HTTP errors do not erase Telnet state, do not mark the refresh as a failed
device status read, do not switch credentials, do not change the successful
credential index, and do not authorize credential fallback.

### Run PDU refresh and control outside the GUI thread

PCS4i refresh and outlet control use background workers submitted through the
same application-owned execution style as existing diagnostic workers. Aten
refresh also participates in the same application-owned PDU context-generation
contract, even if it remains implemented by `AtenPDUWorker`. No PCS4i Telnet
connect/read/write, PCS4i HTTP request, or Aten refresh/control network I/O may
run in the Qt GUI thread when covered by this PDU lifecycle.

The preferred implementation is a generic PDU operation dispatch boundary:

```text
PDUScreen
    |
    v
VCSDiagnosticApp PDU dispatch
    |
    v
background PDU refresh/control worker
    |
    +--> AtenPDUHandler
    |
    +--> ExtronIPLTPCS4iHandler
```

The lifecycle contract covers:

- PCS4i refresh;
- PCS4i ON;
- PCS4i OFF;
- Aten refresh;
- Aten ON;
- Aten OFF;
- Aten REBOOT.

The application/composition layer owns the current PDU operation context
generation. Qt widgets are not the authoritative source for background workers:
workers must not inspect `device_combo`, `ip_entry`, `PDUScreen`, or other
QWidget properties to decide whether an operation is current. The context
identity includes at least device model, IP address, non-secret credential
identity or candidate index, and generation number.

The dispatch chooses the handler by selected device model and submits immutable
operation descriptors containing operation id, generation, model, IP,
credential context, operation type, outlet number when applicable, desired
target when applicable, and a capability-validated operation. The application
layer increments or replaces the current generation when the selected PDU
context changes.

Before handler acquisition, a queued worker compares the captured descriptor
with the current application-owned context through a thread-safe, non-GUI
validity mechanism. If the operation is stale, no handler is created, no
transport is opened, no network I/O occurs, and no command is sent. If handler
construction/preparation and first network I/O are separate phases, the worker
performs a second validity check immediately before first network I/O. Results,
errors, completions, and callbacks are checked again at the application
boundary and cannot update a newer context.

Refresh workers return PDU data to `PDUScreen`; command workers return a
redacted command outcome and then schedule/trigger a refresh only when the
outcome is successful or successfully reconciled. Stale callbacks are ignored
using the existing request-context rules.

### Preserve Aten REBOOT while removing PCS4i REBOOT

This change must not remove REBOOT from Aten. The existing Aten handler remains
the owner of its native reboot operation, and Aten command dispatch continues
to support ON, OFF, and REBOOT through the migrated background command
boundary. Aten protocol semantics and wire commands remain unchanged.

PCS4i capability restrictions must not alter Aten behavior. Regression tests
must prove Aten ON/OFF/REBOOT dispatch, successful refresh-after-command,
stale-drop behavior, GUI-thread isolation, outlet rendering, and wire-protocol
unchanged behavior remain intact.

### Prevent blind replay of PCS4i ON/OFF and Aten state-changing commands

PDU control operations change power state and cannot be blindly repeated after
an ambiguous transport outcome.

For PCS4i ON/OFF, the operation records an authoritative pre-command state
`PRE_STATE` before the first send when a valid `PC` readback is available. The
target state `TARGET` is ON for `turn_on()` and OFF for `turn_off()`. The
operation has these budgets for one user action:

- initial command send: max 1;
- controlled resend: max 1;
- total state-changing sends: max 2;
- reconciliation cycles: max 1;
- reconciliation decision readback after ambiguous initial delivery: max 1;
- terminal confirmation readback after the single controlled resend: max 1;
- recursive recovery/reconciliation: 0.

The reconciliation decision readback and the terminal confirmation readback are
separate budgets. The single reconciliation decision decides whether the target
already took effect, whether one controlled absolute resend is allowed, or
whether the outcome is indeterminate. If the controlled resend is used, one
terminal confirmation `PC` readback is still required and is not a second
reconciliation cycle.

Initial PCS4i ON/OFF send outcomes:

- Authoritative device rejection -> `FAILURE`; no credential fallback, no
  resend, and no reconciliation loop.
- Delivery acknowledged -> perform terminal authoritative `PC` readback even
  though acknowledgement was received.
  - `PC == TARGET` -> `SUCCESS`.
  - `PC == PRE_STATE` -> acknowledgement alone is not success; if no controlled
    resend has been used, send the same absolute `TARGET` command once and then
    perform one terminal confirmation `PC` readback.
  - `PC` unavailable, unknown, or conflicting -> `INDETERMINATE`; no resend.
- Initial delivery ambiguous -> run the one reconciliation cycle. It may perform
  at most one reconnect/recovery only if needed for authoritative `PC`
  readback, then performs one reconciliation decision readback.
  - `PC == TARGET` -> `SUCCESS`; no resend.
  - `PC == PRE_STATE` -> one controlled absolute resend of `TARGET` is allowed,
    followed by exactly one terminal confirmation `PC` readback.
  - `PC` unavailable, unknown, or conflicting -> `INDETERMINATE`; no resend.

Controlled resend terminal confirmation:

- `PC == TARGET` -> `SUCCESS`.
- `PC == PRE_STATE` -> `FAILURE`, because authoritative readback confirms the
  requested target was not reached after the only allowed resend.
- `PC` unavailable, unknown, or conflicting -> `INDETERMINATE`.

After the terminal confirmation readback, there is no further resend, reconnect,
or reconciliation. A controlled resend acknowledgement is never enough for
success without the terminal `PC` confirmation.

There is no PCS4i REBOOT recovery policy because PCS4i REBOOT is unsupported.

For Aten ambiguous ON/OFF, the existing Aten status path provides authoritative
readback; target already reached succeeds without resend, known pre-command
state permits at most one controlled absolute resend, unavailable/unknown or
conflicting readback returns indeterminate, and a second ambiguous outcome after
controlled resend returns indeterminate. For Aten ambiguous REBOOT, automatic
resend is zero and the maximum REBOOT sends for the user operation is one.

The worker must distinguish "not sent", "sent and acknowledged", "sent with
unknown acknowledgement", "valid device rejection", and "transport/session
failure" enough for this policy to be testable.

## Risks / Trade-offs

- [Exact HTTP name read path may still be missing] -> keep the confirmed
  `xName1` through `xName4` representation normative, but block production
  parser implementation until the exact captured GET path is confirmed.
- [A generic PDU worker could grow too broad] -> share dispatch, lifecycle,
  capability validation, and operation semantics only; keep Aten and PCS4i
  protocol parsing in separate handlers.
- [Migrating Aten commands changes timing] -> preserve behavior with focused
  Aten dispatch, stale-drop, GUI-thread, reconciliation-budget, and
  normal-behavior regression tests.
- [HTTP names can fail independently] -> make the implemented HTTP path
  mandatory, but constrain failures to fallback names with no impact on Telnet
  status or credential fallback.
- [Authentication prompt parsing can misclassify decorated prompts] -> track
  transport bytes by phase and inspect only new phase bytes for each prompt
  decision.

## Migration Plan

1. Add PCS4i device registration, model-to-screen mapping, model-specific
   capability declaration, and credential resolution path for optional
   `auth_mode: "password"`.
2. Add the PCS4i handler with confirmed Telnet SIS parsing, passwordless
   readiness probing, bounded password flow, HTTP name enrichment boundary,
   outlet count enforcement, ON/OFF-only command surface, and redaction.
3. Add background PDU refresh/control workers or a small PDU operation
   dispatcher that supports PCS4i refresh, PCS4i ON/OFF, Aten refresh, and Aten
   ON/OFF/REBOOT under the application-owned PDU generation contract.
4. Route `PDUScreen` outlet actions through capability-aware asynchronous
   command submission and stale-context-safe completion handling.
5. Add offline unit tests for SIS parsing, Telnet auth phases, outlet data
   normalization, successful HTTP names, HTTP enrichment failure, credential
   ownership, lifecycle isolation, PCS4i unsupported REBOOT rejection, PCS4i
   ON/OFF safety, GUI routing, Aten refresh stale-generation behavior, and Aten
   command regressions.
6. Confirm the exact HTTP GET path containing `xName1` through `xName4` before
   production parser implementation if it is not already present in retained
   discovery evidence.
7. Run strict OpenSpec validation, focused offline tests, the full offline
   suite, and opt-in hardware QA only when authorized.

## Open Questions

- What exact HTTP GET path returns the confirmed `xName1` through `xName4`
  outlet-name representation for production parser implementation?
