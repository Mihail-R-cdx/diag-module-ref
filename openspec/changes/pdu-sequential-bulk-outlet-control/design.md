## Context

The current production PDU path has a shared `PDUScreen` for Aten PE8208AV and
Extron IPL T PCS4i. `PDUScreen` renders the outlet records returned by the
current PDU refresh result, and model capabilities decide whether ON, OFF, and
REBOOT controls are shown. PCS4i returns four outlets and supports ON/OFF only;
Aten commonly returns eight outlets and supports ON/OFF/REBOOT.

The application/composition layer already owns PDU credential resolution,
credential fallback, operation descriptors, stale-context checks, and the
background `PDUOperationWorker` boundary. `core.pdu` owns shared PDU operation
contracts and safe absolute ON/OFF policy, while device-specific handlers own
wire primitives and authoritative readback for their protocol.

Bulk ON/OFF must not be modeled as several independent user clicks or as a GUI
loop calling `control_pdu_outlet(...)`. It needs one application-owned sequence
that remains off the Qt GUI thread and treats each outlet as an independent
safe state-changing sub-operation.

## Goals

- Add shared-screen bulk ON/OFF architecture for Aten PE8208AV and Extron IPL T
  PCS4i.
- Keep outlet count dynamic by using the actual outlet records returned for the
  current PDU path.
- Execute the sequence as one managed background operation with serial outlet
  sub-operations.
- Preserve the existing safe absolute ON/OFF policy for every outlet.
- Keep credential selection and credential fallback in the
  application/composition layer.
- Keep GUI controls responsive but locked against competing PDU mutations while
  bulk work is active.
- Return a structured terminal result suitable for full or partial completion
  messaging without secrets.

## Non-Goals

- Do not implement this architecture in production code in this change.
- Do not add bulk orchestration methods to Aten or PCS4i handlers unless a
  later implementation proves a device-native primitive is required.
- Do not introduce PCS4i REBOOT.
- Do not combine Aten and PCS4i transports.
- Do not perform inter-outlet delay in the Qt GUI thread.
- Do not make the operation transactional.

## Decisions

### Represent bulk as an application-owned orchestration sequence

The bulk operation is one application/composition-owned background sequence:

```text
PDUScreen
  -> application/composition bulk dispatch
  -> immutable bulk operation context
  -> background PDU bulk execution
      -> handler acquisition / connect
      -> outlet N safe absolute outlet operation
      -> one second delay before the next outlet
      -> terminal result
      -> disconnect / cleanup
```

The exact implementation may be a dedicated bulk worker or an extension of the
existing PDU worker boundary. The required property is that the sequence is one
managed serial background operation, not multiple concurrent per-outlet
workers and not repeated GUI submissions of individual commands.

The bulk context is immutable and includes at least operation id, generation,
model, IP address, non-secret credential context, assigned credential index
when any, bulk target (`ON` or `OFF`), and the ordered outlet sequence captured
from the current PDU data.

### Build outlet order from current records

Bulk dispatch uses the currently available outlet records for the active PDU
screen/context. It sorts by outlet number ascending. It does not assume eight
outlets for Aten or four outlets for every device except insofar as the current
handler has returned that many records.

PCS4i therefore processes four outlets when the current PCS4i refresh result
contains four records. Aten processes however many valid outlet records the
Aten path returned.

### Preserve handler boundaries

Device-specific handlers continue to own wire primitives:

- Aten owns HTTPS/API status and outlet state primitives.
- PCS4i owns Telnet/SIS status and ON/OFF primitives plus read-only HTTP outlet
  name enrichment.

The application/core orchestration layer owns outlet sequencing and delay.
Handlers are not given orchestration-only `turn_all_on()` or `turn_all_off()`
methods for this change.

### Reuse existing safe absolute ON/OFF policy per outlet

Each outlet sub-operation is a normal supported absolute ON or OFF operation
through the existing safe PDU state-changing boundary. It must preserve:

- pre-state/readback rules;
- bounded reconciliation;
- indeterminate outcome handling;
- controlled resend limits;
- final-state confirmation;
- device-specific authoritative readback.

The existing safety budget applies per outlet sub-operation. A bulk operation
is one orchestration sequence made of multiple independent outlet
sub-operations. The safety budget for outlet 1 does not consume or authorize
state-changing sends for outlet 2. A later outlet failure does not repeat,
replay, or roll back already successful outlets.

### Delay outside the GUI thread

The first outlet starts immediately after the background sequence has passed
stale validation and acquired the required execution resources. After each
completed outlet sub-operation, the worker waits one second before starting
the next outlet. There is no additional wait after the final outlet.

The delay must run outside the Qt GUI thread. `time.sleep(1)` or equivalent
blocking waits in GUI callbacks are forbidden.

### Fail fast with structured partial results

If an outlet sub-operation ends with command rejection, indeterminate outcome,
connection/protocol failure, terminal authentication failure, or another
terminal failure, the sequence stops. Remaining outlets receive no commands.

Completed outlets are not repeated. Completed outlets are not rolled back.
The bulk operation is not transactional.

The terminal result contains enough non-secret structure for the GUI to report
full completion or partial completion, the outlet that stopped the sequence
when applicable, and the count/list of successfully completed outlets. The
result must not contain credentials or transport secrets.

After any terminal completion, full or partial, the application schedules a
refresh of the current PDU state if the context is still current.

### Keep credential ownership in the application layer

The application/composition layer assigns one credential for a bulk sequence
attempt. The worker and handler do not iterate credential candidates.

Credential fallback is allowed only before the first state-changing send, and
only after a structured confirmed `AuthenticationError` where retry is safe.
After the first state-changing outlet command has been sent or may have been
sent, the application must not restart the entire bulk sequence with another
credential, repeat already completed outlets, or begin again from outlet 1.

Successful credential memory is updated only after a truly successful terminal
outcome according to the existing policy. PCS4i keeps its existing rule: when a
credential was assigned but the device operated passwordless and the credential
was not used, that credential index is not saved as successful.

### Validate staleness before start and between outlets

The background sequence checks its immutable descriptor against the
application-owned current context before handler acquisition/network I/O. It
also checks before starting every next outlet sub-operation.

If the context becomes stale before the sequence starts, no handler is acquired
and no command is sent. If the context becomes stale between outlets, the next
outlet is not started. If context changes while an outlet sub-operation is in
flight, that sub-operation may complete, but the old callback cannot update the
new GUI context and the sequence does not continue to another outlet.

Workers must not read `device_combo`, `ip_entry`, `PDUScreen`, or other Qt
widgets to decide currentness.

### Lock PDU controls during active bulk execution

`PDUScreen` exposes `Выкл всё` and `Вкл всё` under the outlet table when the
selected PDU supports OFF and ON respectively. Starting either action requires
one confirmation dialog for the whole sequence.

While a bulk sequence is active, both bulk controls and individual outlet
controls are disabled for that PDU context. The screen must not submit a second
bulk operation or a concurrent individual PDU mutation through the same screen.
Controls are restored only by a terminal callback that matches the current
context.

### Preserve model capabilities

Bulk ON and bulk OFF are available only when the selected model supports the
matching individual operation. Current supported devices:

- Aten PE8208AV: ON, OFF, REBOOT.
- Extron IPL T PCS4i: ON, OFF.

Bulk control does not introduce PCS4i REBOOT and does not change Aten REBOOT.

## Risks / Trade-Offs

- A dedicated bulk worker may duplicate some `PDUOperationWorker` lifecycle
  wiring; extending the existing worker may make it broader. The implementation
  should choose the smallest boundary that keeps bulk as one serial background
  operation.
- Partial completion is expected behavior, not an exception to hide. The GUI
  must communicate it without per-outlet success/error dialogs.
- Credential fallback after mutation is intentionally restricted to avoid
  duplicate state-changing actions.

## Migration Plan

1. Extend shared PDU UI controls and composition dispatch for bulk ON/OFF.
2. Add immutable bulk descriptor/result contracts and background serial
   execution.
3. Reuse existing handler factory and safe absolute ON/OFF operation boundary
   per outlet.
4. Add stale validation before network I/O and before each next outlet.
5. Add GUI locking and one confirmation dialog per bulk sequence.
6. Add focused tests listed in `tasks.md`, then run the full regression suite.
