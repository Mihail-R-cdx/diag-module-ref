## MODIFIED Requirements

### Requirement: Limited device control
The GUI SHALL expose only the control operations implemented by the selected
device path: codec presentation, audio/microphone operations, supported SIP
server actions, Extron routing to output 1, Aten outlet on/off/reboot actions,
Aten bulk on/off actions, Extron IPL T PCS4i outlet on/off actions, and Extron
IPL T PCS4i bulk on/off actions. Unsupported device actions SHALL not be
reported as successful. PCS4i REBOOT SHALL be unsupported and SHALL NOT be
exposed to the operator as an individual or bulk operation.

#### Scenario: Extron routing action
- **WHEN** an operator selects an actionable Extron input/output-1 cell with a connected handler
- **THEN** the handler is asked to route that input to output 1 and the screen schedules a status refresh

#### Scenario: Aten outlet action
- **WHEN** an operator confirms an `on`, `off`, or `reboot` action for an Aten outlet
- **THEN** the application executes the matching handler action through the background PDU command path, reports its outcome, and refreshes after success

#### Scenario: PCS4i outlet action
- **WHEN** an operator confirms an `on` or `off` action for a PCS4i outlet from 1 through 4
- **THEN** the application executes the matching PCS4i handler action through the background PDU command path and reports its outcome

#### Scenario: PCS4i reboot is not available
- **GIVEN** selected device is Extron IPL T PCS4i
- **WHEN** `PDUScreen` renders supported outlet controls
- **THEN** ON is available
- **AND** OFF is available
- **AND** REBOOT is not available to the operator

#### Scenario: Unsupported SIP update
- **WHEN** a codec handler does not implement SIP server update
- **THEN** the operation reports an unsupported or failed outcome rather than claiming the setting changed

#### Scenario: Bulk action uses supported individual capability
- **GIVEN** the selected PDU model supports individual ON and OFF operations
- **WHEN** the shared PDU screen renders bulk controls
- **THEN** bulk ON is available only from the ON capability
- **AND** bulk OFF is available only from the OFF capability
- **AND** no PCS4i REBOOT or bulk REBOOT control is exposed

#### Scenario: Unsupported bulk action is rejected
- **GIVEN** a PDU model does not support the requested individual operation
- **WHEN** a matching bulk operation is submitted programmatically
- **THEN** application dispatch rejects it before handler acquisition
- **AND** no PDU network I/O is started

### Requirement: Shared PDU screen with device-specific capabilities
The application SHALL use the existing `PDUScreen` for Aten PE8208AV and
Extron IPL T PCS4i. The screen SHALL render the outlet records returned by the
active handler/worker and SHALL not hard-code the PCS4i outlet count to Aten's
eight-outlet layout. Device protocols SHALL remain in device-specific handlers.
Control rendering SHALL use selected-model capabilities rather than assuming
all PDU models expose the same operation set. The same screen SHALL render
bulk controls `Выкл всё` and `Вкл всё` under the outlet table when the selected
model supports the corresponding individual OFF or ON operation.

Bulk busy/lock state SHALL be owned by the PDU context generation or token that
started the bulk sequence. When the application activates a new PDU context,
that new context SHALL establish its own control state independently of any
superseded context. A superseded bulk operation SHALL NOT keep the new context
locked, and a stale callback from the old context SHALL NOT unlock, relock, or
otherwise change controls owned by the new context.

#### Scenario: PCS4i uses existing PDU screen
- **WHEN** an operator refreshes `Extron IPL T PCS4i`
- **THEN** the application displays the existing `PDUScreen`
- **AND** no PCS4i-specific screen is created

#### Scenario: PCS4i renders four outlets
- **WHEN** the PCS4i worker returns four outlet records
- **THEN** `PDUScreen` displays exactly four outlet rows
- **AND** each row exposes ON and OFF controls only

#### Scenario: Aten remains on the same PDU screen
- **WHEN** an operator refreshes `Aten PE8208AV`
- **THEN** the application continues to display Aten outlet data on `PDUScreen` with its existing behavior

#### Scenario: Aten capabilities are preserved
- **GIVEN** selected device is a supported Aten PDU
- **WHEN** operator controls an outlet
- **THEN** existing ON/OFF/REBOOT capabilities remain available
- **AND** PCS4i capability restrictions do not alter Aten protocol semantics

#### Scenario: Bulk controls appear on the shared PDU screen
- **WHEN** an operator refreshes a supported PDU and outlet records are shown
- **THEN** `PDUScreen` shows `Выкл всё` and `Вкл всё` below the outlet table
- **AND** no Aten-specific or PCS4i-specific bulk screen is created

#### Scenario: Bulk OFF on Aten uses returned outlet records
- **GIVEN** the Aten refresh result contains available outlet records
- **WHEN** the operator confirms `Выкл всё`
- **THEN** the application builds the bulk OFF sequence from those outlet records
- **AND** outlets are ordered by ascending outlet number
- **AND** the sequence does not assume a fixed outlet count beyond the records returned

#### Scenario: Bulk ON on PCS4i uses four returned outlets
- **GIVEN** PCS4i returns four outlet records
- **WHEN** the operator confirms `Вкл всё`
- **THEN** the application builds a four-outlet bulk ON sequence
- **AND** no eight-outlet Aten logic is applied to PCS4i

#### Scenario: One confirmation dialog per bulk operation
- **WHEN** an operator starts bulk ON or bulk OFF
- **THEN** the GUI asks for one confirmation for the whole sequence
- **AND** it does not ask for separate confirmation per outlet

#### Scenario: PDU controls are locked during active bulk sequence
- **WHEN** a bulk PDU sequence is active for the current PDU context
- **THEN** `Вкл всё` is disabled
- **AND** `Выкл всё` is disabled
- **AND** individual outlet control buttons are disabled
- **AND** the screen cannot submit a second bulk operation or a parallel individual PDU command

#### Scenario: Context switch while bulk active
- **GIVEN** Aten bulk is active and its controls are locked
- **WHEN** operator switches to a new PCS4i context
- **THEN** the new PCS4i context does not inherit the old Aten bulk lock
- **AND** old Aten callbacks cannot change the PCS4i control state

#### Scenario: Stale completion cannot unlock new active bulk
- **GIVEN** old context bulk becomes stale
- **AND** a new context starts its own bulk operation
- **WHEN** old bulk completion arrives
- **THEN** it does not unlock controls owned by the new bulk operation

## ADDED Requirements

### Requirement: Sequential bulk PDU outlet control
The application SHALL support sequential bulk PDU outlet ON and OFF operations
for Aten PE8208AV and Extron IPL T PCS4i. A bulk operation SHALL be one
application-owned orchestration sequence composed of independent outlet
sub-operations. The sequence SHALL process the actual current outlet records
in ascending outlet-number order, SHALL start the first outlet immediately,
SHALL wait one second after each completed outlet sub-operation before
starting the next one, and SHALL NOT wait after the final outlet.

Bulk dispatch SHALL capture a normalized immutable ordered outlet identity
sequence from the current outlet records before background execution starts.
The descriptor SHALL store outlet identities such as outlet numbers, not
mutable GUI/data dictionaries. Missing, malformed, or duplicate outlet
identities SHALL be rejected before any state-changing network I/O. Duplicate
outlets SHALL NOT be silently de-duplicated.

The bulk sequence SHALL run outside the Qt GUI thread. It SHALL use the
existing safe absolute PDU ON/OFF state-changing policy for each outlet
sub-operation. It SHALL stop fail-fast on the first terminal outlet failure,
SHALL leave remaining outlets untouched, SHALL NOT roll back completed outlets,
and SHALL NOT replay already completed outlets because a later outlet failed.

#### Scenario: Bulk OFF on Aten
- **GIVEN** the current Aten PDU data contains outlet records
- **WHEN** the operator confirms `Выкл всё`
- **THEN** every available Aten outlet is processed sequentially by ascending outlet number
- **AND** each outlet sub-operation requests OFF through the safe absolute outlet policy
- **AND** one second is waited between completed outlet sub-operations

#### Scenario: Bulk ON on PCS4i
- **GIVEN** the current PCS4i PDU data contains four outlet records
- **WHEN** the operator confirms `Вкл всё`
- **THEN** only those four outlets are processed sequentially
- **AND** each outlet sub-operation requests ON through the safe absolute outlet policy
- **AND** no Aten eight-outlet fallback is used

#### Scenario: Duplicate outlet number
- **GIVEN** current outlet records contain a duplicate outlet identity
- **WHEN** bulk dispatch validates the sequence
- **THEN** the bulk operation is rejected before state-changing network I/O
- **AND** no duplicate is silently removed

#### Scenario: Malformed outlet number
- **GIVEN** one outlet record has missing or invalid outlet identity
- **WHEN** bulk dispatch validates the sequence
- **THEN** the operation is rejected before state-changing network I/O

#### Scenario: Immutable capture
- **WHEN** a bulk sequence is submitted
- **THEN** later mutation of GUI outlet records does not change the captured execution sequence

#### Scenario: Delay outside GUI thread
- **WHEN** a bulk operation includes slow device work and inter-outlet delays
- **THEN** the Qt event loop remains responsive
- **AND** the one-second waits are not executed in the GUI thread

#### Scenario: No delay after final outlet
- **WHEN** the last outlet sub-operation in a bulk sequence completes
- **THEN** the sequence produces its terminal result without an additional inter-outlet delay

#### Scenario: No delay after terminal failure
- **WHEN** an outlet sub-operation fails terminally
- **THEN** the sequence stops without waiting one second for an outlet that will not start

#### Scenario: No delay before stale stop
- **WHEN** stale validation fails before the next outlet sub-operation
- **THEN** the sequence stops without waiting and without starting the next outlet

#### Scenario: Fail-fast
- **WHEN** outlet N completes with a terminal failure or indeterminate outcome
- **THEN** outlets N+1 and later receive no command
- **AND** the sequence reports partial completion when earlier outlets succeeded

#### Scenario: No rollback
- **WHEN** a later outlet sub-operation fails after earlier outlets succeeded
- **THEN** the earlier outlets are not switched back by the bulk sequence
- **AND** the bulk operation is not treated as a transaction

#### Scenario: No replay of completed outlets
- **WHEN** a later outlet sub-operation fails or is indeterminate
- **THEN** previously successful outlet sub-operations are not repeated
- **AND** their safety budgets are not reused by another outlet

#### Scenario: Partial result
- **WHEN** a bulk sequence stops after processing only part of the outlet list
- **THEN** the terminal result identifies that completion was partial
- **AND** it identifies the stopping outlet and the number of successful outlets
- **AND** it does not include credentials or transport secrets

#### Scenario: Structured terminal result categories
- **WHEN** a bulk sequence terminates
- **THEN** the result distinguishes full success, partial terminal failure, stale termination before mutation, and stale termination after completed outlet sub-operations by structured fields
- **AND** the GUI does not infer those categories from user-facing text

#### Scenario: Refresh after completion
- **WHEN** a bulk sequence reaches full or partial terminal completion
- **THEN** the application refreshes actual PDU state for the current context
- **AND** stale completion does not refresh or unlock a newer context
