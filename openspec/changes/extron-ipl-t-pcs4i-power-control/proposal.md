## Why

The application has one production PDU control path for Aten PE8208AV, but the
new Extron IPL T PCS4i uses a different Telnet/HTTP protocol while keeping the
same operator workflow in the existing `PDUScreen`. Protocol discovery and
official Extron SIS evidence now confirm the PCS4i status/control commands and
also confirm the architectural decision that PCS4i REBOOT is unsupported.

PCS4i has exactly four controllable outlets. Telnet is authoritative for
session establishment, device identity, outlet ON/OFF state, outlet ON, outlet
OFF, and final state readback. HTTP is a read-only enrichment source for outlet
names only. PCS4i must support both password-protected configurations and
passwordless configurations where no `Password` prompt appears and a verified
read-only SIS probe proves the session is ready.

The current Aten command path performs outlet control synchronously from the Qt
GUI thread. Adding PCS4i by copying that path would introduce new blocking
network I/O in the GUI and would make state-changing commands unsafe after
ambiguous transport outcomes.

## What Changes

- Add Extron IPL T PCS4i to the existing power-control GUI category and route it
  to the existing `PDUScreen`; do not create a PCS4i-specific screen.
- Define a model-specific PDU capability contract: PCS4i supports refresh, ON,
  and OFF; PCS4i REBOOT is unsupported and must not be exposed to the operator.
- Keep Aten PE8208AV ON, OFF, and REBOOT capabilities and wire semantics
  unchanged.
- Use Telnet port 23 as the authoritative PCS4i transport for connection,
  optional password authentication, identity queries, outlet power-state reads,
  outlet ON, outlet OFF, and authoritative post-command readback.
- Use confirmed SIS commands for PCS4i model, description, part number,
  firmware, security level, outlet power state, current/reference threshold
  state, ON, and OFF.
- Implement HTTP outlet-name loading as a required read-only enrichment path
  using the confirmed `xName1` through `xName4` representation. If the exact
  captured GET path containing those variables is not available before
  production parser work, that path remains the only narrow evidence blocker.
- Define a bounded Telnet session state machine that detects the `Password`
  protocol marker in phase-scoped new bytes, treats credentials as optional
  until requested, sends the same assigned password at most twice, returns
  `CredentialRequired` when a prompt appears without an assigned credential, and
  returns `AuthenticationError` only after confirmed rejection of an actually
  sent credential.
- Keep credential fallback owned by the GUI/application composition layer;
  handlers and workers receive at most one assigned credential and never select
  the next one.
- Move PDU refresh and outlet control for PCS4i and Aten refresh through
  background worker paths with application-owned operation generation checks,
  stale queued operation rejection, cleanup, and redacted public outcomes.
- Migrate the existing Aten outlet command path to the same application-owned
  asynchronous PDU command execution boundary in this change, with explicit Aten
  regression coverage and unchanged Aten wire protocol semantics.
- Define PCS4i ON/OFF bounded recovery: no blind replay after ambiguous
  delivery, at most one reconciliation cycle, authoritative readback through
  Telnet `PC`, and no PCS4i REBOOT recovery because PCS4i REBOOT is unsupported.

## Capabilities

### New Capabilities

- `device-diagnostics-and-control`: Support Extron IPL T PCS4i as a four-outlet
  power-control PDU using the existing `PDUScreen`, with refresh, ON, and OFF
  only.

### Modified Capabilities

- `request-lifecycle-and-recovery`: Extend the request lifecycle to PDU refresh
  and outlet command workers, including background execution, stale-context
  rejection before network I/O, unsupported-operation rejection before handler
  acquisition, cleanup, and state-changing ON/OFF command safety.
- `credential-source-isolation`: Clarify optional password-only PCS4i credential
  ownership, phase-scoped prompt handling, `CredentialRequired`, and structured
  retry authority.
- `secure-observability-and-validation`: Require PCS4i Telnet/HTTP diagnostics,
  command outcomes, and password prompt handling to redact the real password
  and other credential material.

## Impact

Future implementation is expected to touch `gui/main_window.py`,
`core/worker.py`, focused PDU command worker/controller code, a new PCS4i
handler under `handlers/extron/`, `gui/screens/pdu_screen.py` only where generic
PDU capability rendering needs tightening, credential resolution call sites for
password-only devices, and offline tests. It must not add a new GUI screen,
merge Aten and PCS4i wire-protocol implementations into one handler, expose
PCS4i REBOOT, disable HTTP outlet-name loading as a completed end state, or
depend on live hardware for normal automated verification.
