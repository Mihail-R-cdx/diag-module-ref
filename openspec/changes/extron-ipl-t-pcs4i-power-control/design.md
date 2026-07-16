## Context

Aten PE8208AV is currently the only production PDU. It appears under the
power-control device category, maps to `PDUScreen`, refreshes through
`AtenPDUWorker`, and exposes `get_outlets_status()`, `get_device_info()`,
`turn_on()`, `turn_off()`, and `reboot()` from `handlers/aten/pdu.py`.
`PDUScreen` renders whichever outlet records the worker returns, so it can
already display four PCS4i outlets when the handler/worker returns four records.

The risky precedent is outlet control. `PDUScreen.on_outlet_control()` calls
`VCSDiagnosticApp.control_pdu_outlet()`, and that method creates an
`AtenPDUHandler`, connects, and sends `on`, `off`, or `reboot` synchronously on
the Qt GUI thread. PCS4i must not copy this path.

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
- Make password-only authentication explicit and bounded.
- Ensure no PCS4i Telnet connect, read, command, or HTTP request runs in the Qt
  GUI thread.
- Prevent stale queued PDU operations from acquiring handlers or sending network
  I/O after device/IP/credential context changes.
- Prevent blind replay of state-changing PDU commands.
- Decide whether the existing Aten outlet command path is part of the same
  boundary fix and, if so, protect Aten with regression tests.

**Non-Goals:**

- Do not implement production code in this architectural change.
- Do not create a PCS4i-specific GUI screen.
- Do not make Aten inherit from PCS4i or PCS4i inherit from Aten.
- Do not define an unverified HTTP endpoint, HTML/XML shape, or HTTP
  authentication mechanism for PCS4i outlet names.
- Do not create a broad transport abstraction that hides device protocols.
- Do not archive this change or merge runtime behavior.

## Decisions

### Use the existing power-control UI and PDU operation surface

Add `"Extron IPL T PCS4i": "pdu"` to the main device-to-screen mapping and add
the device item under the existing power-control category in the combo. The
screen remains `PDUScreen`; no new screen class is introduced.

The PCS4i refresh result shape matches the current PDU screen contract:

- `device_info`: model, manufacturer, IP address, connected/status, and optional
  firmware fields when available;
- `outlets`: exactly four outlet records with `number`, normalized `status`,
  and `name`;
- `type`: `pdu`.

`PDUScreen` must render the number of returned records rather than assuming
eight Aten rows. PCS4i therefore displays four rows because the worker returns
four rows. Aten continues to display its returned Aten records.

Alternative considered: build a PCS4i-specific screen. Rejected because the
operator operations and data surface are the same as Aten, and a second screen
would duplicate confirmation, refresh, and outlet-action behavior.

### Keep handler protocols separate and share only the operation contract

Create a focused PCS4i handler, expected under `handlers/extron/`, with these
device-specific methods:

- `get_outlets_status()`
- `get_device_info()`
- `turn_on(outlet_number)`
- `turn_off(outlet_number)`
- `reboot(outlet_number)`

The shared contract is the PDU operation surface, not a shared wire transport.
The Aten handler remains the owner of the Aten HTTPS/XML/API protocol. The
PCS4i handler owns its Telnet command parsing and optional HTTP outlet-name
enrichment. Common code may dispatch operations to either handler through a
small PDU worker/factory boundary, but it must not force a generic Telnet/HTTP
transport abstraction across unrelated devices.

### Use Telnet as authoritative PCS4i status/control transport

Telnet is the authoritative PCS4i path for:

- connecting to the device;
- password-only authentication;
- reading the state of all four controllable outlets;
- sending ON, OFF, and REBOOT outlet commands.

The handler must return exactly four outlet records for PCS4i. It must reject
outlet numbers outside 1 through 4 before sending any device command.

The exact PCS4i Telnet command set and response grammar remain unresolved in
this design because they were not confirmed from existing code or provided
protocol documentation. Future implementation must define parser behavior only
from verified evidence: official protocol material, captured redacted device
traffic, or provided test data. The architecture intentionally fixes the
handler boundary and safety behavior without inventing command strings.

### Treat HTTP outlet names as read-only enrichment

HTTP is used only to load user-defined names for the four outlets. Name loading
is not authoritative for outlet state and is not required for a successful
refresh.

The handler refresh flow is:

1. Authenticate and read outlet state through Telnet.
2. Build four normalized outlet records with safe fallback names:
   `Розетка 1`, `Розетка 2`, `Розетка 3`, and `Розетка 4`.
3. Attempt HTTP name enrichment only after Telnet status is available.
4. Replace fallback names with verified non-empty HTTP names where available.
5. If HTTP fails, times out, returns an unsupported shape, or lacks a verified
   endpoint, return the Telnet outlet status with fallback names.

HTTP errors therefore do not erase Telnet state, do not mark the refresh as a
failed device status read, and do not authorize credential fallback unless a
future verified HTTP authentication phase produces a structured authentication
failure owned by the composition layer.

The exact HTTP endpoint, response format, and authentication mechanism are
unresolved. The implementation must not guess them.

### Use password-only credentials and keep fallback in the application layer

PCS4i uses `auth_mode: "password"` and no username. Credential resolution stays
at the GUI/application composition boundary. A PCS4i worker receives exactly
one assigned credential for one attempt and passes only the password to the
handler. The handler does not read `credentials.local.json`, inspect candidate
lists, select a later credential, wrap around, or remember a successful index.

Only the application/composition layer may advance to the next credential, and
only after the worker reports a structured confirmed `AuthenticationError`.
Timeout, disconnect, malformed prompt flow, protocol parsing failure, command
failure, HTTP name-loading failure, and arbitrary text containing words like
`auth`, `password`, `401`, or `403` are not retry authority.

Successful credential index caching remains scoped to the exact device/IP
context and is committed only after final successful refresh or successful
command/reconciliation, not after partial data or failed next attempts.

### Define a bounded Telnet password state machine

PCS4i session establishment uses a finite state machine with at most two
password sends:

```text
CONNECT
  |
  v
WAIT_INITIAL_PASSWORD_PROMPT
  |
  | accepts new bytes containing:
  |   Password:
  |   Password:***************
  v
SEND_PASSWORD_ATTEMPT_1
  |
  v
READ_POST_PASSWORD_DATA_1
  |
  +--> authenticated/session ready
  |
  +--> new Password: prompt
          |
          v
      SEND_PASSWORD_ATTEMPT_2
          |
          v
      READ_POST_PASSWORD_DATA_2
          |
          +--> authenticated/session ready
          |
          +--> new Password: prompt
                  |
                  v
            AuthenticationError
```

The initial prompt buffer is consumed before the first password is sent. A line
such as `Password:**********************` in that initial buffer is still the
initial prompt and must not be counted as a second post-password prompt. After
the first send, repeated prompt detection examines only bytes received after
that send. After the second send, another new password prompt is a confirmed
authentication rejection.

Authentication success is established only from verified session-ready evidence
after a password send, such as the device prompt, a valid command response, or
another documented ready marker. A timeout waiting for the initial prompt,
disconnect after a password send, malformed prompt flow, or unknown device text
is a connection/session/protocol failure, not `AuthenticationError`.

The real password must never appear in stdout, terminal logs, GUI messages,
exceptions, public diagnostics, or test assertions. Device-emitted asterisks
are not themselves secret, but the transmitted credential is always redacted.

### Run PDU refresh and control outside the GUI thread

PCS4i refresh and outlet control use background workers submitted through the
same application-owned execution style as existing diagnostic workers. No
PCS4i Telnet connect/read/write or HTTP request may run in the Qt GUI thread.

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

The dispatch chooses the handler by selected device model and submits immutable
operation descriptors containing model, IP, credential candidate index, outlet
number, command, and request generation. The worker rechecks the generation
before handler acquisition and before network I/O. If the selected model, IP,
or credential context changed while the operation was queued, it drops the
operation without opening a transport or sending a command.

Refresh workers return PDU data to `PDUScreen`; command workers return a
redacted command outcome and then schedule/trigger a refresh only when the
outcome is successful or successfully reconciled. Stale callbacks are ignored
using the existing request-context rules.

### Include Aten command path only as a GUI-thread boundary fix

This change may replace `control_pdu_outlet()` with the same background PDU
command worker for both Aten PE8208AV and PCS4i. If it does, the scope is only
to remove network I/O from the GUI thread and share the PDU operation dispatch;
it must not change Aten's wire protocol, outlet count, credential semantics, or
normal ON/OFF/REBOOT behavior.

Aten refresh already has `AtenPDUWorker`, but its command path is synchronous.
Moving Aten commands into the background command worker requires Aten-specific
regression tests for:

- dispatching ON, OFF, and REBOOT to `AtenPDUHandler`;
- preserving successful command refresh behavior;
- not blocking the GUI thread;
- dropping stale queued Aten commands before network I/O;
- keeping Aten outlet rendering and outlet count behavior unchanged.

If implementation discovers that migrating Aten commands would exceed the
change's risk budget, PCS4i still must use the background worker path and the
proposal/design must explicitly leave Aten's synchronous path as unchanged
debt. The preferred architecture is to migrate both through the shared PDU
command dispatch.

### Prevent blind replay of state-changing PDU commands

PDU control operations change power state and cannot be blindly repeated after
an ambiguous transport outcome.

For ON/OFF:

- if the command was definitely not sent, the worker may send it once;
- if the command was sent and acknowledgement was lost, the worker must first
  perform an authoritative Telnet readback when possible;
- if readback shows the target state, report success without resending;
- if readback shows the known pre-command state, policy may send one controlled
  absolute target command;
- if readback is unavailable or state is conflicting, report an indeterminate
  outcome and do not replay.

For REBOOT:

- if the reboot command may have reached the device, no automatic second reboot
  is allowed;
- readback may be used only to refresh/display state, not to justify automatic
  replay;
- ambiguous reboot delivery is reported as indeterminate with redacted details.

The worker must distinguish "not sent", "sent and acknowledged", "sent with
unknown acknowledgement", "valid device rejection", and "transport/session
failure" enough for this policy to be testable.

## Risks / Trade-offs

- [PCS4i wire protocol details are incomplete] -> keep the handler boundary and
  tests explicit, but leave exact Telnet commands and HTTP name endpoint
  unresolved until verified protocol evidence is available.
- [A generic PDU worker could grow too broad] -> share dispatch, lifecycle, and
  operation semantics only; keep Aten and PCS4i protocol parsing in separate
  handlers.
- [Migrating Aten commands changes timing] -> preserve behavior with focused
  Aten dispatch and UI-thread regression tests.
- [HTTP names can fail independently] -> make names optional enrichment with
  safe fallback names and no impact on Telnet status.
- [Authentication prompt parsing can misclassify the initial asterisk prompt] ->
  track transport bytes by phase and inspect only post-send bytes for repeated
  prompts.

## Migration Plan

1. Add PCS4i device registration, model-to-screen mapping, and credential
   resolution path for `auth_mode: "password"`.
2. Add the PCS4i handler with verified Telnet status/control parsing, bounded
   authentication state machine, HTTP name enrichment boundary, outlet count
   enforcement, and redaction.
3. Add background PDU refresh/control workers or a small PDU operation
   dispatcher that supports PCS4i and, preferably, Aten commands.
4. Route `PDUScreen` outlet actions through asynchronous command submission and
   stale-context-safe completion handling.
5. Add offline unit tests for Telnet auth phases, outlet data normalization,
   HTTP enrichment failure, credential ownership, lifecycle isolation,
   state-changing command safety, GUI routing, and Aten regressions if Aten
   command dispatch is migrated.
6. Run strict OpenSpec validation, focused offline tests, the full offline
   suite, and opt-in hardware QA only when authorized.

## Open Questions

- What exact PCS4i Telnet commands and response grammar read outlet states and
  execute ON, OFF, and REBOOT?
- What exact Telnet prompt or command-response marker confirms session-ready
  authentication after one or two password sends?
- What exact HTTP endpoint, response format, and authentication mechanism expose
  user-defined PCS4i outlet names?
- Does PCS4i provide an authoritative readback immediately after ambiguous
  ON/OFF delivery on all supported firmware versions?
