## Why

The next Matrix hotspot is not the size of `MatrixScreen` alone. The current
Matrix path spreads one lifecycle across `gui/screens/matrix_screen.py`,
`gui/main_window.py`, the focused Matrix worker, and the Extron IN1804
handler/parser:

- `MatrixScreen` renders the routing table, but route clicks also read the
  selected device/IP, select credentials through the main window, acquire a
  persistent handler, send `set_connection()`, and schedule a quick status
  refresh.
- `VCSDiagnosticApp` owns Matrix refresh worker creation, generic worker
  stale-result suppression, credential fallback, persistent handler/session
  fields, keepalive, and close-time cleanup.
- `core/workers/matrix.py` now owns the canonical Matrix refresh worker after
  `worker-module-decomposition`, while `core/worker.py` is only a compatibility
  facade.
- `handlers/extron/in1804.py` owns protocol commands and session I/O, and
  `ExtronIN1804DataParser` owns GUI-facing normalization.

This makes a typical Matrix change require reading much of `gui/main_window.py`
and `MatrixScreen`, because the user-intent boundary, background execution
boundary, persistent handler lifecycle, credential retry policy, and stale
context policy are not localized in one Matrix-specific application component.
It also leaves current route mutation and quick refresh paths able to perform
handler/network work from UI callbacks.

## What Changes

- Define a Matrix-specific application/composition controller boundary,
  tentatively `MatrixController`, for Matrix refresh, route mutation,
  request identity, background execution, persistent handler/session ownership,
  stale callback suppression, cleanup, and refresh-after-mutation behavior.
- Make `MatrixScreen` primarily a view boundary. It displays Matrix data and
  emits user intents such as refresh and route requests. It does not own
  credentials, handler acquisition, persistent session state, transport
  lifecycle, retry policy, credential fallback, or direct network I/O.
- Reduce `VCSDiagnosticApp` to Matrix composition/bootstrap responsibilities:
  create the Matrix screen/controller, provide the existing application-owned
  credential policy, route global model/IP/context changes into the Matrix
  controller, and connect controller outputs to the screen.
- Preserve existing Matrix behavior and safety contracts: rendering, refresh,
  routing, credential ownership, successful credential memory, terminal
  redaction, worker signal payloads, and cleanup remain behaviorally
  compatible.
- Keep Matrix worker implementation canonical in `core/workers/matrix.py`;
  do not move Matrix workers back into `core/worker.py`.
- Keep the change Matrix-specific. Do not introduce a generic `OperationManager`,
  `DeviceManager`, `NetworkManager`, or shared Matrix/PDU/DMP/Codec controller.

## Capabilities

### Modified Capabilities

- `diagnostic-application-shell`: define `MatrixScreen` as an intent/display
  boundary and forbid handler/session/secret ownership in that screen.
- `request-lifecycle-and-recovery`: define Matrix-specific background
  lifecycle, explicit request context, stale callback suppression, route
  mutation safety, persistent session ownership, and cleanup rules.
- `credential-source-isolation`: clarify Matrix credential fallback ownership,
  structured retry authority, and the prohibition on handler/worker credential
  iteration.

No new root capability is introduced because the Matrix lifecycle boundary is
a specialization of existing application shell, request lifecycle, and
credential-source contracts.

## Impact

Future implementation is expected to add a focused Matrix controller module,
adjust `MatrixScreen` to emit intents rather than invoking handlers, move
Matrix-specific orchestration out of `VCSDiagnosticApp`, and add focused tests
for screen boundary, background route/refresh execution, stale Matrix
callbacks, context-bound refresh after route mutation, session isolation, and
behavioral regressions.

This architecture-only change does not implement production code, does not
change runtime behavior, does not archive the OpenSpec change, and does not
merge it.
