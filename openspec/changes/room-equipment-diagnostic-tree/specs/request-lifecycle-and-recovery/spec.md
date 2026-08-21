## ADDED Requirements

### Requirement: Room-cycle generation isolates every per-record callback

Automatic room diagnostics SHALL have one application-owned room generation for each full room cycle and one application-owned operation token/identity for each active row attempt. Every result, partial result, warning, error, progress/status event, cleanup event, and completion accepted by the room workflow SHALL be associated with the current room generation and the exact canonical record/model/IP context that started the operation.

A superseded callback SHALL NOT change the current room header, row state/cache, expanded-view rendering, global room status, `Последнее обновление`, credential/profile memory, control state, or room-queue advancement. Background workers/controllers/adapters SHALL NOT read Qt widget state to decide currentness.

Currentness SHALL be checked before handler/session factory acquisition and before first device network I/O when those phases are separable. Queued stale work SHALL perform zero handler acquisition and zero device network I/O.

#### Scenario: Old room result arrives after full Refresh

- **GIVEN** full room Refresh created a new room generation
- **WHEN** a result or completion from the prior generation arrives
- **THEN** it is ignored
- **AND** it does not update any row, credential/profile memory, room summary, or queue state of the new generation

#### Scenario: Waiting operation becomes stale before handler acquisition

- **WHEN** a queued room operation is superseded before it begins execution
- **THEN** its currentness check fails before handler/session factory acquisition
- **AND** it performs zero device network I/O

### Requirement: Automatic room one-shot cleanup is a bounded sequencing gate

Automatic room diagnostics SHALL not start diagnostic network I/O for the next eligible record until the previous record's model-specific one-shot lifecycle has completed cleanup/release or a bounded cleanup deadline has established logical abandonment.

Cleanup/release of network resources SHALL run on the background execution lane that owns those resources. The GUI SHALL publish cancellation/invalidation as needed and SHALL NOT synchronously perform device network cleanup or wait for an unbounded remote timeout.

When cleanup exceeds the policy deadline, application composition SHALL permanently invalidate that old lifecycle, ignore all later callbacks from it, and allow the room queue to continue. Physical best-effort cleanup MAY continue in the background but SHALL NOT regain authority or block a later room generation indefinitely.

#### Scenario: Cleanup completes normally

- **GIVEN** one room row has reached terminal diagnostic outcome
- **WHEN** its model-specific cleanup completes within policy
- **THEN** the application accepts cleanup completion for that exact room/row operation
- **AND** only then may the next eligible row begin diagnostic network I/O

#### Scenario: Cleanup exceeds policy deadline

- **GIVEN** one room row has reached or attempted terminal diagnostic outcome
- **WHEN** cleanup does not complete within the bounded policy deadline
- **THEN** the old lifecycle is logically abandoned
- **AND** later callbacks cannot update application state
- **AND** the room queue may proceed to the next eligible row

### Requirement: Automatic room sequencing is serialized across model lifecycle owners

The room orchestrator SHALL own cross-device sequencing but SHALL NOT become a second owner of model-specific transport/session internals. At most one room record SHALL have active diagnostic network acquisition at a time, including when different records use different controllers/workers.

Model-specific lifecycle owners SHALL remain responsible for their own handlers, sessions, worker cancellation, and cleanup. The room orchestrator SHALL wait only for their normalized terminal/cleanup boundary and SHALL not directly close protocol resources owned by another execution lane.

#### Scenario: Different model controllers are adjacent in the queue

- **GIVEN** a Matrix row is followed by a DMP row
- **WHEN** Matrix has emitted usable diagnostic data but has not retired its automatic session
- **THEN** DMP network acquisition has not started
- **AND** the room orchestrator waits for Matrix cleanup completion or bounded abandonment rather than closing Matrix transport directly

#### Scenario: One device is slow

- **WHEN** a room row's network acquisition is slow but still within its active lifecycle policy
- **THEN** Qt GUI event processing remains responsive
- **AND** no later room row begins parallel diagnostic network I/O

### Requirement: Full-room supersession invalidates queued and in-flight read-only work

Starting a new full room Refresh, changing the top-level source IP after a completed room session, or closing the application SHALL invalidate the previous room generation before replacement room work can become authoritative.

Queued old room work SHALL be dropped before handler acquisition/I/O. In-flight old network work MAY finish physically but SHALL have no current-result authority. Application close during automatic read-only room work SHALL not require a mutation-warning confirmation and SHALL not block GUI shutdown waiting for unbounded device cleanup.

#### Scenario: Source IP is edited after room completion

- **GIVEN** a completed room session is visible
- **WHEN** the operator changes the top-level IP text
- **THEN** the old room generation is invalidated and its presentation authority is cleared
- **AND** restoring the old text alone does not reactivate the old generation

#### Scenario: Application closes during automatic room polling

- **WHEN** the application closes while a room one-shot operation is active
- **THEN** current room authority is invalidated and stop/cancel is published best-effort
- **AND** stale callbacks cannot update UI after invalidation
- **AND** the GUI does not wait indefinitely for device network cleanup
