## Why

After `worker-module-decomposition` and `matrix-operation-lifecycle-decomposition`, the next major application-layer context hotspot is the PDU lifecycle still embedded in `gui/main_window.py`.

The current PDU path already has useful lower-level boundaries:

- `gui/screens/pdu_screen.py` renders the shared Aten/PCS4i UI and publishes outlet/bulk signals, but its local slots still call arbitrary parent methods such as `control_pdu_outlet(...)`, `control_pdu_outlets_bulk(...)`, and `refresh_data()`;
- `core/pdu.py` owns immutable `PDUOperationDescriptor` data, model capability gates, safe individual mutation policy, sequential bulk execution, and handler-factory dispatch;
- `core/workers/pdu.py` owns the canonical background `PDUOperationWorker` and keeps PDU network execution outside the Qt GUI thread;
- `handlers/aten/pdu.py` and `handlers/extron/pcs4i.py` remain device-specific protocol boundaries;
- `VCSDiagnosticApp` still owns PDU context generation/invalidation, refresh orchestration, individual and bulk mutation state machines, worker binding, credential-attempt coordination, stale callback suppression, busy-state coordination, and refresh/reconciliation after mutation.

This means a typical PDU lifecycle change still requires a large amount of `gui/main_window.py` context even though the PDU worker and protocol layers are already focused. It also leaves the PDU UI boundary coupled to `MainWindow` method names instead of an explicit intent/controller contract.

The change therefore defines a PDU-specific application controller boundary, preferably `PDUController`, that localizes PDU refresh and mutation lifecycle without changing existing PDU behavior, protocol commands, credential fallback, bulk sequencing, PCS4i password-only behavior, or worker/handler ownership.

## What Changes

- Define a PDU-specific application/composition controller boundary for PDU refresh, individual outlet mutation, sequential bulk mutation, immutable operation context, PDU context generation, stale callback acceptance, PDU-specific worker binding, context-scoped busy state, and mutation reconciliation.
- Define explicit independent PDU operation authority lanes: a refresh lane for user refresh/status refresh/reconciliation and a mutation lane for individual and bulk mutations. The lanes share common PDU context identity but do not use one global `current_operation_id`.
- Make `PDUScreen` an explicit PDU UI boundary that renders data/control state, owns confirmation dialogs when appropriate, and publishes non-secret refresh, individual-mutation, and bulk-mutation intents without acquiring handlers, creating workers, selecting credentials, or calling arbitrary parent orchestration methods.
- Reduce `VCSDiagnosticApp` to PDU composition responsibilities: create and wire `PDUScreen` and `PDUController`, provide global model/IP context changes, provide the existing application-owned credential callbacks/providers, route accepted controller outcomes into shell/UI state, and delegate application shutdown/invalidation.
- Preserve the existing background PDU worker boundary in `core/workers/pdu.py`; moving synchronous handler I/O into a normal controller method is explicitly not a valid implementation.
- Preserve all existing PDU safety contracts, including structured authentication-only credential fallback, no blind replay after possible state-changing delivery, one assigned credential per bulk attempt, no restart of a started bulk sequence, successful-credential commit gates, dynamic outlet identity capture, and stale-context suppression.
- Make the mid-bulk stale stop contract explicit: before every next state-changing outlet sub-operation, the bulk execution path must re-check the controller-supplied non-GUI currentness predicate and stop before the next send if it has become false.
- Preserve the current per-model/per-operation credential eligibility matrix so structural extraction cannot accidentally make Aten individual mutations newly credential-retry-eligible or credential-success-persisting.
- Preserve PCS4i password-only and credentialless semantics: no invented username, no conversion of missing credentials into ordinary authentication failure, and no successful-index persistence for an unused credential.
- Keep the controller PDU-specific. Do not introduce a universal `OperationManager`, `DeviceController`, `RequestManager`, or combined Matrix/PDU/DMP/codec controller.

## Capabilities

### Modified Capabilities

- `diagnostic-application-shell`: define `PDUScreen` as an explicit non-secret intent/display boundary rather than a parent-method orchestration client.
- `request-lifecycle-and-recovery`: move normative PDU lifecycle ownership to a PDU-specific application controller, define independent refresh and mutation authority lanes, preserve immutable context and stale suppression, define reconciliation authority, and require all PDU network/reconciliation work to remain on the existing background boundary.
- `credential-source-isolation`: clarify that `PDUController` consumes application-owned credential policy callbacks/providers, preserves the current PDU credential eligibility matrix, and does not become a second credential manager or expose secrets in public operation context.

No new root capability is introduced because this is a structural specialization of the existing application shell, request lifecycle, and credential isolation contracts.

## Impact

Future implementation is expected to add a focused controller near the GUI application composition boundary (for example `gui/pdu_controller.py`), wire explicit `PDUScreen` intents to it, move PDU-specific lifecycle state and stale acceptance out of `VCSDiagnosticApp`, and add focused regression coverage for refresh, individual mutation, bulk mutation, independent authority lanes, mid-bulk stale stops, credential delegation, context switches, stale callbacks, reconciliation, and UI locking.

This architecture-only change does not implement production code, does not change tests, does not change user-visible PDU behavior, does not alter protocol commands or handler transport semantics, does not archive the OpenSpec change, and does not merge it.
