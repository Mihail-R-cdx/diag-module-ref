## MODIFIED Requirements

### Requirement: Limited device control
The GUI SHALL expose only the control operations implemented by the selected
device path: codec presentation, audio/microphone operations, supported SIP
server actions, Extron routing to output 1, Aten outlet on/off/reboot actions,
Aten bulk on/off actions, Extron IPL T PCS4i outlet on/off actions, and Extron
IPL T PCS4i bulk on/off actions. Unsupported device actions SHALL not be
reported as successful. PCS4i REBOOT SHALL be unsupported and SHALL NOT be
exposed to the operator as an individual or bulk operation.

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

## ADDED Requirements

### Requirement: Sequential bulk PDU outlet control
The application SHALL support sequential bulk PDU outlet ON and OFF operations
for Aten PE8208AV and Extron IPL T PCS4i. A bulk operation SHALL be one
application-owned orchestration sequence composed of independent outlet
sub-operations. The sequence SHALL process the actual current outlet records
in ascending outlet-number order, SHALL start the first outlet immediately,
SHALL wait one second after each completed outlet sub-operation before
starting the next one, and SHALL NOT wait after the final outlet.

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

#### Scenario: Delay outside GUI thread
- **WHEN** a bulk operation includes slow device work and inter-outlet delays
- **THEN** the Qt event loop remains responsive
- **AND** the one-second waits are not executed in the GUI thread

#### Scenario: No delay after final outlet
- **WHEN** the last outlet sub-operation in a bulk sequence completes
- **THEN** the sequence produces its terminal result without an additional inter-outlet delay

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

#### Scenario: Refresh after completion
- **WHEN** a bulk sequence reaches full or partial terminal completion
- **THEN** the application refreshes actual PDU state for the current context
- **AND** stale completion does not refresh or unlock a newer context
