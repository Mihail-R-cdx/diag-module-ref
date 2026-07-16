## Why

The application has one production PDU control path for Aten PE8208AV, but the
new Extron IPL T PCS4i must use a different Telnet/HTTP protocol while keeping
the same operator workflow. PCS4i also has password-only Telnet authentication,
only four controllable outlets, and a password prompt flow that can legitimately
ask for the same password twice during one session establishment attempt.

The current Aten command path performs outlet control synchronously from the Qt
GUI thread. Adding PCS4i by copying that path would introduce new blocking
network I/O in the GUI and would make state-changing commands unsafe after
ambiguous transport outcomes.

## What Changes

- Add Extron IPL T PCS4i to the existing power-control GUI category and route it
  to the existing `PDUScreen`; do not create a PCS4i-specific screen.
- Define a PCS4i handler contract compatible with the PDU operation surface:
  `get_outlets_status()`, `get_device_info()`, `turn_on(outlet_number)`,
  `turn_off(outlet_number)`, and `reboot(outlet_number)`.
- Use Telnet as the authoritative PCS4i transport for connection,
  password-only authentication, outlet state reads, and outlet control.
- Implement HTTP outlet-name loading as a required read-only enrichment path.
  Safe fallback names are allowed only as runtime degradation after the
  implemented HTTP path is attempted and fails, or for individual missing or
  empty outlet names.
- Define a bounded Telnet password state machine with at most two password
  sends and structured `AuthenticationError` only after a confirmed repeated
  password prompt following the second send.
- Keep credential fallback owned by the GUI/application composition layer using
  the existing `auth_mode: "password"` credential contract; handlers and
  workers receive only one assigned credential and never select the next one.
- Move PDU refresh and outlet control for PCS4i and Aten refresh through
  background worker paths with application-owned operation generation checks,
  stale queued operation rejection, cleanup, and redacted public outcomes.
- Migrate the existing Aten outlet command path to the same application-owned
  asynchronous PDU command execution boundary in this change, with explicit
  Aten regression coverage and unchanged Aten wire protocol semantics.
- Define transport-neutral state-changing PDU command safety for Aten and
  PCS4i ON, OFF, and REBOOT: no blind replay after ambiguous delivery, one
  bounded reconciliation cycle using device-specific authoritative outlet-state
  readback, no recursive recovery, and no automatic retry for ambiguous REBOOT.

## Capabilities

### New Capabilities

- `device-diagnostics-and-control`: Support Extron IPL T PCS4i as a four-outlet
  power-control PDU using the existing `PDUScreen` and PDU operation surface.

### Modified Capabilities

- `request-lifecycle-and-recovery`: Extend the request lifecycle to PDU refresh
  and outlet command workers, including background execution, stale-context
  rejection before network I/O, cleanup, and state-changing command safety.
- `credential-source-isolation`: Clarify password-only PCS4i credential
  ownership and structured retry authority.
- `secure-observability-and-validation`: Require PCS4i Telnet/HTTP diagnostics,
  command outcomes, and password prompt handling to redact the real password
  and other credential material.

## Impact

Future implementation is expected to touch `gui/main_window.py`,
`core/worker.py`, focused PDU command worker/controller code, a new PCS4i
handler under `handlers/extron/`, `gui/screens/pdu_screen.py` only where generic
PDU behavior needs tightening, credential resolution call sites for
password-only devices, and offline tests. It must not add a new GUI screen,
merge Aten and PCS4i wire-protocol implementations into one handler, disable
HTTP outlet-name loading as a completed end state, or depend on live hardware
for normal automated verification.
