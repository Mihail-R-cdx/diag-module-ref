# device-diagnostics-and-control Specification

## Purpose
TBD - created by archiving change bootstrap-openspec-baseline. Update Purpose after archive.
## Requirements
### Requirement: Supported production device diagnostics
The application SHALL provide production GUI diagnostic paths for Huawei TE20,
Huawei TE40, CloudLink Bar 310, Polycom RPG 310, Extron IN1804, Aten
PE8208AV, Extron IPL T PCS4i, and Biamp Tesira Forte CI only where those
devices are connected to the main-window dispatch. Each diagnostic path SHALL
obtain device data through its worker/handler path and present
parser-normalized or handler-normalized data on the corresponding screen.

#### Scenario: Codec diagnostic refresh
- **WHEN** an operator refreshes a supported codec with a successful device response
- **THEN** the codec screen receives normalized diagnostic data including the target IP and available device status values

#### Scenario: Matrix or PDU diagnostic refresh
- **WHEN** an operator refreshes Extron IN1804, Aten PE8208AV, or Extron IPL T PCS4i successfully
- **THEN** the matrix or PDU screen receives the parsed routing or outlet data for that device

#### Scenario: PCS4i power-control category
- **WHEN** the operator opens the device selector
- **THEN** `Extron IPL T PCS4i` is listed under the `Управление питанием` category

### Requirement: Device-specific diagnostic transports
The diagnostic paths SHALL preserve their current protocol boundaries: TE20
uses its HTTP profile and optionally a ready HTTPS stack; TE40 attempts HTTPS
and falls back to HTTP; Bar 310 uses its Huawei web/API session; Polycom uses
HTTPS status with SSH enrichment; Extron IN1804 uses its handler transport
sequence; Aten uses its HTTPS API path; and Extron IPL T PCS4i uses Telnet for
authoritative outlet status/control plus required HTTP outlet-name enrichment.
A protocol fallback or enrichment failure SHALL be observable in the
worker/handler outcome and SHALL not be represented as a different device.

#### Scenario: TE40 HTTPS fallback
- **WHEN** TE40 HTTPS diagnostic connection fails and its HTTP fallback succeeds
- **THEN** the worker returns the HTTP connection profile with the parsed diagnostic data

#### Scenario: Polycom enrichment is unavailable
- **WHEN** Polycom HTTPS status succeeds but SSH enrichment fails
- **THEN** the available HTTPS diagnostic data remains usable and the enrichment failure is reported through the worker path

#### Scenario: PCS4i HTTP outlet names are unavailable at runtime
- **WHEN** PCS4i Telnet outlet status succeeds and the implemented HTTP outlet-name path fails at runtime
- **THEN** the worker returns the four Telnet outlet states with safe fallback outlet names
- **AND** the HTTP failure is not represented as a failed Telnet status read or a different device

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

### Requirement: Model-specific interactive codec session paths
The shared interactive controller SHALL preserve the supported transports,
session artifacts, and operation boundaries of Huawei TE20, Huawei TE40,
CloudLink Bar 310, and Polycom RPG 310. A model SHALL use only its supported
interactive functions, and functions on a separate worker path SHALL remain
separate unless explicitly listed.

#### Scenario: Huawei TE20 interactive session
- **WHEN** TE20 performs live audio, sleep/Wake, volume, mute, presentation, or call-log work
- **THEN** it uses saved-first HTTP:80 and runtime-supported HTTPS:443 candidates with one credential
- **AND** recovery replaces invalid Session ID, cookie, CSRF, and transport state as one handler unit

#### Scenario: Huawei TE40 interactive session
- **WHEN** TE40 performs live audio, sleep-related presentation preparation, volume, mute, presentation, or call-log work
- **THEN** it uses saved-first HTTPS:443 and HTTP:80 candidates with one credential
- **AND** recovery replaces invalid opener, cookie, Session ID, CSRF, and browser-session state as one handler unit

#### Scenario: CloudLink Bar 310 interactive session
- **WHEN** Bar 310 performs sleep-related presentation preparation, volume, mute/gain, presentation, or call-log work
- **THEN** it uses HTTPS:443 with one credential and one Basic-auth session, cookie, and CSRF context
- **AND** call-log reads use the recovered token through the required `X-Access-Token` header

#### Scenario: Polycom interactive controls
- **WHEN** Polycom performs volume, mute, or presentation work
- **THEN** its serialized shared handler uses HTTPS:443 login and the same credential for its lazy SSH:22 control session
- **AND** failure of either sub-session follows the bounded interactive recovery contract

#### Scenario: Polycom call log remains separate
- **WHEN** the operator loads the Polycom call log
- **THEN** the existing short-lived Polycom call-log worker remains the owner of that operation
- **AND** it is not routed through the Huawei/shared call-log session path

### Requirement: Recovered interactive feature availability
A confirmed invalid session in one shared interactive handler SHALL be recovered
through the common controller rather than through feature-specific reconnect
logic. After successful recovery, read-only functions SHALL resume according to
their replay policy and state-changing functions SHALL follow reconciliation.
An unsupported or failed operation SHALL not be reported as successful.

#### Scenario: Live audio recovers after session invalidation
- **WHEN** TE20 or TE40 live-audio polling encounters an invalid session and reconnect succeeds
- **THEN** one replay updates microphone and codec-output levels without a modal failure dialog

#### Scenario: Wake uses the recovered path
- **WHEN** TE20 Wake loses its session and reconnect succeeds
- **THEN** sleep state is read before Wake is confirmed or sent again

#### Scenario: Huawei call log uses recovered session
- **WHEN** a Huawei call-log read detects an invalid cached session
- **THEN** the shared controller reconnects once and replays that read once

#### Scenario: Bar 310 remains regression-free
- **WHEN** Bar 310 executes supported interactive operations without session failure
- **THEN** the operation uses one HTTPS profile and retains its current successful behavior

#### Scenario: Polycom controls remain regression-free
- **WHEN** Polycom executes a supported interactive control without session failure
- **THEN** it uses the existing HTTPS/SSH command semantics and sends the state-changing command no more than once

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

### Requirement: PCS4i PDU handler contract
The PCS4i handler SHALL expose a PDU-compatible operation surface consisting of
`get_outlets_status()`, `get_device_info()`, `turn_on(outlet_number)`, and
`turn_off(outlet_number)`. The PCS4i handler SHALL NOT expose a supported
`reboot(outlet_number)` operation. The handler SHALL return exactly four PCS4i
outlet records and SHALL reject outlet numbers outside 1 through 4 before
sending any command.

#### Scenario: PCS4i status shape
- **WHEN** PCS4i outlet status is read successfully
- **THEN** the handler returns four records containing outlet number, normalized status, and display name

#### Scenario: PCS4i device info shape
- **WHEN** PCS4i device information is read successfully
- **THEN** the handler returns at least model, manufacturer, IP address, and connection status fields suitable for the PDU screen

#### Scenario: PCS4i rejects invalid outlet number
- **WHEN** a caller requests PCS4i outlet 0 or outlet 5
- **THEN** the handler rejects the request before sending any Telnet command

#### Scenario: PCS4i handler has no reboot command
- **WHEN** application dispatch builds PCS4i supported operations
- **THEN** the supported PCS4i operation set excludes REBOOT

### Requirement: PCS4i authoritative Telnet protocol
PCS4i Telnet SHALL be authoritative for connection, session readiness, device
identity, outlet state reads, outlet ON, outlet OFF, and final state readback.
The handler SHALL use the confirmed SIS commands and response semantics.

For identity/session metadata, `1I<CR>` SHALL read model, `2I<CR>` SHALL read
description, `N<CR>` SHALL read part number, `Q<CR>` SHALL read firmware, and
`<ESC>CK<CR>` SHALL read session security level. For outlet `N` in 1..4,
`<ESC>NPC<CR>` SHALL be authoritative power-state readback where `0<CR><LF>`
means OFF and `1<CR><LF>` means ON. `<ESC>NPS<CR>` SHALL be treated only as
current/reference threshold state. ON SHALL send `<ESC>N*1PC<CR>` and OFF SHALL
send `<ESC>N*0PC<CR>`. Final state after ON or OFF SHALL be determined through
a separate authoritative `PC` readback, not acknowledgement alone.

#### Scenario: Model query
- **WHEN** PCS4i handler sends `1I<CR>`
- **THEN** response `IPL T PCS4i` identifies the model

#### Scenario: Firmware query
- **WHEN** PCS4i handler sends `Q<CR>`
- **THEN** the firmware response is parsed as firmware metadata

#### Scenario: Security-level query
- **WHEN** PCS4i handler sends `<ESC>CK<CR>`
- **THEN** response `11<CR><LF>` is User level
- **AND** response `12<CR><LF>` is Administrator level

#### Scenario: PC returns OFF
- **WHEN** PCS4i outlet `PC` readback returns `0<CR><LF>`
- **THEN** the outlet status is normalized as OFF

#### Scenario: PC returns ON
- **WHEN** PCS4i outlet `PC` readback returns `1<CR><LF>`
- **THEN** the outlet status is normalized as ON

#### Scenario: PS is not power state
- **WHEN** PCS4i `PS` readback returns `0`, `1`, or `2`
- **THEN** that value is interpreted only as current/reference threshold state
- **AND** it is not used as authoritative ON/OFF status

#### Scenario: Outlet number outside range is rejected
- **WHEN** PCS4i outlet number is less than 1 or greater than 4
- **THEN** the request is rejected before Telnet network I/O

#### Scenario: ON command grammar
- **WHEN** PCS4i outlet 1 is turned ON
- **THEN** the command bytes are `<ESC>1*1PC<CR>`
- **AND** acknowledgement `Cpn1 Ppc1<CR><LF>` is accepted as command acknowledgement

#### Scenario: OFF command grammar
- **WHEN** PCS4i outlet 1 is turned OFF
- **THEN** the command bytes are `<ESC>1*0PC<CR>`
- **AND** acknowledgement `Cpn1 Ppc0<CR><LF>` is accepted as command acknowledgement

#### Scenario: Authoritative readback after state change
- **WHEN** PCS4i ON or OFF acknowledgement is received
- **THEN** final outlet state is read through a separate `<ESC>NPC<CR>` query

### Requirement: PCS4i HTTP outlet-name enrichment
HTTP SHALL be used only as read-only enrichment for the four PCS4i outlet
display names after authoritative Telnet status succeeds. The confirmed name
representation is `xName1`, `xName2`, `xName3`, and `xName4`, mapped to outlets
1 through 4. A completed implementation SHALL include a verified HTTP
name-loading GET path that actually returns these variables. If the exact path
has not been confirmed from retained evidence, production parser
implementation SHALL remain incomplete until that path is confirmed.

HTTP SHALL NOT be authoritative for outlet power state. When the implemented
HTTP request fails at runtime, returns HTTP 401/403, returns an unsupported or
malformed response, or lacks a usable non-empty name for a specific outlet, the
handler SHALL preserve Telnet outlet status and use safe fallback names for
affected outlets. The live discovered no-auth HTTP behavior SHALL be treated as
device/configuration-specific evidence, not a universal PCS4i rule.

#### Scenario: All names available
- **WHEN** HTTP name response contains usable `xName1`, `xName2`, `xName3`, and `xName4`
- **THEN** all four returned outlet names are used

#### Scenario: One name missing
- **WHEN** one `xNameN` value is missing or empty
- **THEN** fallback name is used only for that outlet
- **AND** other usable names are retained

#### Scenario: Malformed response
- **WHEN** HTTP name response is malformed
- **THEN** Telnet status is retained
- **AND** fallback names are used

#### Scenario: HTTP unavailable
- **WHEN** HTTP name loading is unavailable or times out
- **THEN** Telnet status is retained
- **AND** fallback names are used

#### Scenario: HTTP 401 or 403
- **WHEN** HTTP name loading returns HTTP 401 or HTTP 403
- **THEN** no credential fallback is authorized
- **AND** no Telnet `AuthenticationError` is produced
- **AND** Telnet status is retained

#### Scenario: Verified no-auth device
- **WHEN** the tested PCS4i configuration serves names without HTTP credentials
- **THEN** the read succeeds without HTTP credentials
- **AND** this does not require every PCS4i configuration to be no-auth

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
