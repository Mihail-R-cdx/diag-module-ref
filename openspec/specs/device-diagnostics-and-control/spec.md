# device-diagnostics-and-control Specification

## Purpose
TBD - created by archiving change bootstrap-openspec-baseline. Update Purpose after archive.
## Requirements
### Requirement: Supported production device diagnostics
The application SHALL provide production GUI diagnostic paths for Huawei TE20,
Huawei TE40, CloudLink Bar 310, CloudLink Box 310, Polycom RPG 310, Extron
IN1804, Aten PE8208AV, Extron IPL T PCS4i, Biamp Tesira Forte CI, and Extron
DMP 64 Plus only where those devices are connected to the main-window dispatch.
Each diagnostic path SHALL obtain device data through its worker/handler path and
present parser-normalized or handler-normalized data on the corresponding
screen.

CloudLink Bar 310 and CloudLink Box 310 SHALL remain two distinct exact
application models even though both dispatch through the reviewed shared
`cloudlink_bar_310` lifecycle. Supporting Box 310 SHALL NOT rewrite its accepted
application identity to Bar 310.

#### Scenario: Codec diagnostic refresh
- **WHEN** an operator refreshes a supported codec with a successful device response
- **THEN** the codec screen receives normalized diagnostic data including the target IP and available device status values

#### Scenario: CloudLink Box 310 diagnostic refresh
- **GIVEN** the selected exact application model is `CloudLink Box 310`
- **WHEN** its production diagnostic refresh succeeds through the shared Bar/Box lifecycle
- **THEN** the codec screen receives normalized Box 310 diagnostic data
- **AND** the accepted application model remains exactly `CloudLink Box 310`
- **AND** the operation is not represented as `CloudLink Bar 310`

#### Scenario: Matrix or PDU diagnostic refresh
- **WHEN** an operator refreshes Extron IN1804, Aten PE8208AV, or Extron IPL T PCS4i successfully
- **THEN** the matrix or PDU screen receives the parsed routing or outlet data for that device

#### Scenario: PCS4i power-control category
- **WHEN** the operator opens the device selector
- **THEN** `Extron IPL T PCS4i` is listed under the `Управление питанием` category

#### Scenario: DMP audio-DSP category
- **WHEN** the operator opens the device selector
- **THEN** `Extron DMP 64 Plus` is listed under the `Audio DSP` category next to `Biamp Tesira Forte CI`
- **AND** it routes to the Audio DSP screen path

### Requirement: Device-specific diagnostic transports
The diagnostic paths SHALL preserve their current protocol boundaries: TE20
uses its HTTP profile and optionally a ready HTTPS stack; TE40 attempts HTTPS
and falls back to HTTP; CloudLink Bar 310 and CloudLink Box 310 use the same
existing Huawei web/API session implementation and approved HTTPS:443 profile;
Polycom uses HTTPS status with SSH enrichment; Extron IN1804 uses its handler
transport sequence; Aten uses its HTTPS API path; and Extron IPL T PCS4i uses
Telnet for authoritative outlet status/control plus required HTTP outlet-name
enrichment. A protocol fallback or enrichment failure SHALL be observable in
the worker/handler outcome and SHALL not be represented as a different device.

For the closed Bar/Box 310 protocol family, transport equivalence SHALL NOT
collapse exact application identity, authorize credential sharing, or authorize
retrying one family member as the other.

#### Scenario: TE40 HTTPS fallback
- **WHEN** TE40 HTTPS diagnostic connection fails and its HTTP fallback succeeds
- **THEN** the worker returns the HTTP connection profile with the parsed diagnostic data

#### Scenario: CloudLink Box 310 uses the shared Bar transport boundary
- **GIVEN** the exact application model is `CloudLink Box 310`
- **WHEN** the diagnostic path acquires its supported transport
- **THEN** it uses the same existing Huawei web/API session implementation and HTTPS:443 profile as Bar 310
- **AND** the transport path remains bound to exact `CloudLink Box 310` operation context
- **AND** transport or authentication failure does not switch the model to `CloudLink Bar 310`

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

The shared interactive controller SHALL preserve the supported transports, session artifacts, and operation boundaries of Huawei TE20, Huawei TE40, CloudLink Bar 310, CloudLink Box 310, and Polycom RPG 310. A model SHALL use only its supported functions, and functions on a separate worker path SHALL remain separate unless explicitly listed.

CloudLink Bar 310 and CloudLink Box 310 SHALL continue to use the same reviewed `CloudLinkBar310Handler` implementation while retaining exact assigned application model in operation context. Shared protocol capability SHALL NOT authorize Bar/Box aliasing, credential sharing, successful-index/profile sharing, or model switching during recovery.

For the CloudLink 310 family, one application-selected credential SHALL bind one handler generation for the exact model/IP/credential context. That generation MAY own:

```text
modern read subcontext
legacy compatibility/control subcontext
```

The modern read subcontext SHALL be established through `POST /v1/login/session` followed by `POST /v1/login/account`, retain cookies/token in memory only, and service only operations explicitly approved for the modern context. Modern action.cgi compatibility in this change is limited to the exact live-verified read-only requests `WEB_GetVersionInfoAPI`, `WEB_GetSystemMacAddrAPI`, and `WEB_GetMailboxDataAPI`.

Existing unverified read-only action.cgi operations, including audio, line/SIP, presentation, and camera reads, SHALL remain on the existing legacy compatibility path unless a later approved change proves their modern compatibility. The Box-specific live-meter read `WEB_GetCurrentAudioParam` is an explicit member of that legacy compatibility path in this change and is not added to the modern action.cgi allowlist. Existing supported state-changing action.cgi operations SHALL remain on the legacy compatibility/control path and retain their existing mutation-safety rules.

CloudLink microphone-gain mutation is an explicit exception: for exact Bar 310 and Box 310 it SHALL be unavailable/disabled in this change because authoritative target selection and reconciliation are not established. The application/controller SHALL reject or disable that operation before device network I/O. It SHALL NOT issue gain `PUT`/`POST /v1/mediacontrol/mic/devices`, use fixed device IDs, use first-HD-AI/first-plugged selection, or use `gainVolume` as authoritative reconciliation. Re-enabling gain requires a later approved contract.

Both CloudLink subcontexts belong to one handler generation and assigned credential. Model/IP/credential-context/generation invalidation SHALL supersede both. Handler/worker code SHALL NOT iterate credential candidates; application/composition remains credential-selection/fallback authority.

#### Scenario: CloudLink Bar 310 reviewed read uses modern context

- **GIVEN** exact model is `CloudLink Bar 310`
- **WHEN** an operation explicitly approved for the modern read context executes
- **THEN** it uses HTTPS:443 with the application-selected credential and modern session artifacts
- **AND** the context remains exactly `CloudLink Bar 310`

#### Scenario: CloudLink Bar 310 interactive session

- **GIVEN** the interactive context model is exactly `CloudLink Bar 310` with one application-selected credential
- **WHEN** Bar 310 performs supported interactive preparation, volume, mute, presentation, call-log, or other approved read work
- **THEN** it uses one exact Bar handler generation with the approved modern-read and legacy compatibility/control subcontexts
- **AND** call-log reads use the recovered shared in-memory modern token through `X-Access-Token`
- **AND** unverified reads and supported mutations retain their approved legacy compatibility/control path
- **AND** handler recovery does not select another credential or relabel the operation as Box 310

#### Scenario: CloudLink Box 310 reviewed read uses modern context

- **GIVEN** exact model is `CloudLink Box 310`
- **WHEN** an approved common modern read executes
- **THEN** it uses the shared handler modern read context
- **AND** exact Box identity remains unchanged
- **AND** recovery does not relabel or retry as Bar 310

#### Scenario: CloudLink Box 310 interactive session

- **GIVEN** the interactive context model is exactly `CloudLink Box 310`
- **WHEN** Box 310 performs an operation supported by the shared CloudLink 310 interactive capability
- **THEN** it uses HTTPS:443 through the same `CloudLinkBar310Handler` generation and the application-selected credential
- **AND** approved common modern reads use the modern read subcontext while legacy-compatible operations retain the legacy compatibility/control subcontext
- **AND** the interactive context remains exactly `CloudLink Box 310`
- **AND** recovery does not retry or relabel the operation as `CloudLink Bar 310`

#### Scenario: Unverified action.cgi read remains legacy-compatible

- **WHEN** CloudLink refresh or interactive work needs existing audio, line/SIP, presentation, camera, or another read-only action.cgi operation not live-verified on modern auth
- **THEN** this change does not migrate that operation to the modern context
- **AND** its existing legacy compatibility path remains authoritative until separately approved

#### Scenario: Box live meter remains legacy-compatible

- **GIVEN** exact model is `CloudLink Box 310`
- **WHEN** live metering executes `WEB_GetCurrentAudioParam`
- **THEN** the request uses the existing legacy compatibility subcontext
- **AND** this change does not require modern `X-Access-Token` or modern body-token routing for that endpoint

#### Scenario: Existing CloudLink mutation stays on legacy control path

- **WHEN** Bar 310 or Box 310 performs an already supported mutation other than microphone gain, such as Wake, presentation mutation, mute, speaker volume, or SIP configuration
- **THEN** the operation remains on its existing legacy compatibility/control path
- **AND** modern read evidence does not authorize migration or blind replay

#### Scenario: CloudLink microphone gain is disabled

- **GIVEN** exact model is `CloudLink Bar 310` or `CloudLink Box 310`
- **WHEN** user or application attempts microphone-gain mutation
- **THEN** the operation is unavailable/disabled before device network I/O
- **AND** no gain PUT/POST, fixed-ID target, first-HD-AI selection, or gain readback is attempted
- **AND** no ambiguous mutation result can trigger alternate-method replay

#### Scenario: CloudLink generation is invalidated

- **WHEN** exact model, IP, relevant credential context, or generation is superseded
- **THEN** modern-read and legacy-compatibility/control resources are invalidated/closed
- **AND** stale callbacks cannot update the replacement context

#### Scenario: Huawei TE20 interactive session

- **WHEN** TE20 performs live audio, sleep/Wake, volume, mute, presentation, or call-log work
- **THEN** it uses saved-first HTTP:80 and runtime-supported HTTPS:443 candidates with one credential
- **AND** recovery replaces invalid Session ID, cookie, CSRF, and transport state as one handler unit

#### Scenario: Huawei TE40 interactive session

- **WHEN** TE40 performs live audio, sleep-related presentation preparation, volume, mute, presentation, or call-log work
- **THEN** it uses saved-first HTTPS:443 and HTTP:80 candidates with one credential
- **AND** recovery replaces invalid opener, cookie, Session ID, CSRF, and browser-session state as one handler unit

#### Scenario: Polycom interactive controls

- **WHEN** Polycom performs volume, mute, or presentation work
- **THEN** its serialized shared handler uses HTTPS:443 login and the same credential for its lazy SSH:22 control session
- **AND** failure of either sub-session follows bounded interactive recovery

#### Scenario: Polycom call log remains separate

- **WHEN** operator loads Polycom call log
- **THEN** the existing short-lived Polycom call-log worker remains owner
- **AND** it is not routed through Huawei/shared call-log session path

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

### Requirement: Extron DMP 64 Plus Audio DSP diagnostics
The application SHALL support `Extron DMP 64 Plus` as a read-only Audio DSP
diagnostic path for these explicitly supported protocol variants:
`DMP 64 Plus C`, `DMP 64 Plus C AT`, `DMP 64 Plus C V`, and
`DMP 64 Plus C V AT`. The selectable model SHALL be `Extron DMP 64 Plus`;
implementation SHALL NOT require a serial number, a fixed IP address, a
specific DSP configuration, preconfigured Meter Groups, or one tested firmware
as dispatch identity.

The application SHALL separate the user-facing selector identity from the
explicitly supported discovered protocol variants. A discovered supported
variant SHALL be accepted without requiring dispatch to depend on the exact
selector text. A future or unknown variant SHALL NOT be considered supported
only because its model string contains `DMP 64 Plus`.

The current DMP scope SHALL be physical live input/output meter diagnostics
only. The only allowed protocol-side state change in this scope is bounded
conditional meter initialization/recovery after an unavailable `0*0` sample.

#### Scenario: DMP is selected as Audio DSP
- **WHEN** an operator selects `Extron DMP 64 Plus`
- **THEN** the application uses the Audio DSP diagnostic screen
- **AND** no PDU, matrix, codec, or DMP-specific top-level screen is required

#### Scenario: DMP physical channel contract
- **WHEN** a DMP meter snapshot is displayed
- **THEN** it contains an `Inputs` section with six physical channels
- **AND** it contains an `Outputs` section with four physical channels

#### Scenario: Supported discovered variant
- **WHEN** DMP session discovery reports `DMP 64 Plus C V AT`
- **THEN** the diagnostic path treats it as a supported DMP variant under the `Extron DMP 64 Plus` selector

#### Scenario: Unknown variant is not substring-supported
- **WHEN** DMP session discovery reports an unknown model string containing `DMP 64 Plus`
- **THEN** the diagnostic path does not automatically treat it as supported without an explicit supported-variant mapping

#### Scenario: DMP current scope is read-only diagnostics
- **WHEN** the DMP diagnostic path is implemented
- **THEN** gain control, mute control, routing, phantom power, presets, DSP configuration, FlexInput switching, Dante configuration, Meter Group configuration, SLM configuration, and Telnet port 23 are not exposed as current DMP behavior

### Requirement: Audio DSP screen device-specific presentation
The application SHALL reuse the existing `AudioDSPScreen` for Biamp Tesira
Forte CI and Extron DMP 64 Plus while keeping device-specific presentation
contracts explicit. Existing Biamp `signal_sources` table behavior SHALL remain
unchanged. DMP meter data SHALL render as two meter sections with horizontal
green meter bars and SHALL update all ten bars from a complete normalized DMP
snapshot rather than from independent per-channel GUI polling loops.

#### Scenario: Biamp table rendering remains available
- **WHEN** `AudioDSPScreen` receives existing Biamp `signal_sources` data
- **THEN** it renders the existing signal-source tables with current behavior

#### Scenario: DMP meter rendering
- **WHEN** `AudioDSPScreen` receives DMP meter-section data
- **THEN** it renders `Inputs` and `Outputs` as horizontal meter bars
- **AND** numeric meter text is not required as the primary display

### Requirement: Extron DMP 64 Plus SIS meter protocol
The DMP handler SHALL query physical meter values through SIS-over-SSH on TCP
port `22023` using the supported current implementation mechanism
`open_session`, `get_pty(term='vt100')`, and `invoke_shell()`. This SHALL be
treated as the supported mechanism for this implementation, not as a universal
claim about every DMP firmware.

The physical meter OIDs SHALL be inputs `40000` through `40005` for inputs 1
through 6 and outputs `60000` through `60003` for outputs 1 through 4. OIDs
`40100` through `40105` SHALL NOT be used in the current production DMP meter
path.

The read command SHALL be `ESC V<OID>AU CR`. Clean payloads `1*NNN` and
`2*NNN` SHALL be valid live samples and SHALL convert to `dBFS =
-(raw_meter / 10)`. Clean payload `0*0` SHALL mean unavailable, not
initialized, or no useful meter sample; it SHALL NOT be interpreted as
`0 dBFS`.

#### Scenario: Input physical OIDs
- **WHEN** DMP input meters are read
- **THEN** Input 1 uses OID `40000`
- **AND** Input 2 uses OID `40001`
- **AND** Input 3 uses OID `40002`
- **AND** Input 4 uses OID `40003`
- **AND** Input 5 uses OID `40004`
- **AND** Input 6 uses OID `40005`

#### Scenario: Output physical OIDs
- **WHEN** DMP output meters are read
- **THEN** Output 1 uses OID `60000`
- **AND** Output 2 uses OID `60001`
- **AND** Output 3 uses OID `60002`
- **AND** Output 4 uses OID `60003`

#### Scenario: Direct meter read command
- **WHEN** the DMP handler reads OID `40004`
- **THEN** it sends bytes equivalent to `ESC V40004AU CR`

#### Scenario: Valid meter sample conversion
- **WHEN** the clean DMP meter payload is `1*457`
- **THEN** the parser returns a valid sample of `-45.7 dBFS`

#### Scenario: Unavailable sample is not 0 dBFS
- **WHEN** the clean DMP meter payload is `0*0`
- **THEN** the sample is marked unavailable
- **AND** it is not converted to `0 dBFS`

### Requirement: Extron DMP 64 Plus transport framing and PTY echo handling
DMP SSH transport handling SHALL buffer byte streams, frame logical SIS
responses, filter PTY command echo, and emit clean SIS payload frames before
meter parsing. The meter parser SHALL NOT know about PTY, count the first line
as echo, count the second line as payload, require one `recv()` per response,
or depend on line position.

#### Scenario: PTY echo before payload
- **WHEN** the sent command is `ESC V40004AU CR`
- **AND** the raw PTY stream contains an echo of `ESC V40004AU` followed by clean payload `1*1060`
- **THEN** the transport/framing layer emits only `1*1060` to the DMP meter parser

#### Scenario: Fragmented SSH reads
- **WHEN** one SIS payload arrives split across multiple SSH reads
- **THEN** the transport/framing layer reconstructs the clean payload before parsing

#### Scenario: Multiple frames in one read
- **WHEN** one SSH read contains more than one logical SIS frame
- **THEN** the transport/framing layer exposes each clean frame independently

### Requirement: Extron DMP 64 Plus serialized SIS transaction correlation
The DMP polling session SHALL have at most one outstanding SIS transaction at a
time. Because DMP polling is sequential, the next request SHALL NOT be sent
until the previous request reaches an expected terminal response, structured
timeout, or transport/session failure. Each transaction SHALL know the expected
response contract for the command it sent.

For `ESC V<OID>AU CR`, expected terminal responses are a valid meter payload
`<state>*<raw_meter>` for the current transaction, a documented SIS error such
as `E13`, timeout, or transport/session failure. PTY echo is not a response.
Unrelated or unsolicited clean frames SHALL NOT automatically complete the
current transaction and SHALL NOT become the meter value for the current OID.

For `ESC V<OID>*2AU CR`, the expected acknowledgement is `DsV<OID>*2` for the
same OID. An acknowledgement for another OID SHALL NOT complete the recovery
transaction. If the expected response is not received before the bounded
transaction timeout, the transaction SHALL end with structured timeout or
transport outcome, and leftover/unrelated frames SHALL NOT be consumed as the
next OID's meter result.

Any DMP SIS transaction timeout SHALL make the current SIS session
desynchronized and unsafe for further DMP meter polling. After a meter-read
timeout or recovery-acknowledgement timeout, the implementation SHALL NOT send
the next OID request on that SSH/SIS session, SHALL NOT continue the current
polling cycle, SHALL NOT attempt to drain/clean the stream and reuse that same
session, and SHALL NOT publish the interrupted cycle as a successful complete
snapshot. It SHALL close the SSH channel/client/session through the normal
background cleanup path and report a structured session/transport failure.

`E13` SHALL remain distinct from transaction timeout. If `E13` is received as
the terminal response for the current transaction, the response boundary is
known and the session is not considered desynchronized solely because of that
SIS protocol outcome. `0*0` SHALL also remain distinct from transaction timeout:
it is a received meter response and continues to use the existing conditional
one-shot `*2` recovery contract.

Further DMP polling after transaction timeout SHALL require a fully new
SSH/SIS session with clean stream and transaction state. Timeout SHALL NOT be
authentication failure, SHALL NOT authorize credential fallback, and SHALL NOT
change successful credential memory.

#### Scenario: Unrelated frame before expected payload
- **WHEN** a DMP meter-read transaction for OID `40004` receives an unrelated clean frame before `1*1060`
- **THEN** the unrelated frame does not complete the transaction
- **AND** `1*1060` is used as the OID `40004` meter payload when it arrives within the bounded transaction timeout

#### Scenario: Unsolicited frame before expected payload
- **WHEN** a DMP meter-read transaction receives an unsolicited clean frame before its expected meter payload
- **THEN** the unsolicited frame is ignored or routed to an optional unsolicited sink
- **AND** it is not parsed as the current OID meter value

#### Scenario: Wrong recovery acknowledgement
- **WHEN** recovery for OID `40004` receives `DsV40005*2`
- **THEN** that acknowledgement does not complete the OID `40004` recovery transaction
- **AND** the transaction waits for `DsV40004*2`, timeout, or transport failure

#### Scenario: Expected response timeout
- **WHEN** the expected meter payload or SIS error for the current transaction is not received before the bounded transaction timeout
- **THEN** the current SIS session is treated as unsafe for further DMP meter polling
- **AND** no next OID request is sent on that session
- **AND** the session is closed through the background cleanup path
- **AND** a random unrelated frame is not treated as success

#### Scenario: Leftover frame cannot shift channel result
- **WHEN** an untagged meter response arrives after a timed-out meter-read transaction
- **THEN** it cannot be consumed by another OID transaction on the same session
- **AND** no next OID transaction is started on that session

#### Scenario: Recovery acknowledgement timeout abandons session
- **WHEN** recovery acknowledgement `DsV40004*2` is not received before the bounded transaction timeout
- **THEN** the current SIS session is treated as unsafe for further DMP meter polling
- **AND** no recovery retry read or next OID read is sent on that session

#### Scenario: E13 is not timeout
- **WHEN** the current meter-read transaction receives `E13` as its terminal response
- **THEN** the transaction completes as a structured SIS protocol outcome
- **AND** the session is not considered desynchronized solely because `E13` was received

#### Scenario: 0*0 is not timeout
- **WHEN** the current meter-read transaction receives `0*0`
- **THEN** the transaction has received a meter response
- **AND** the existing conditional one-shot recovery contract applies

### Requirement: Extron DMP 64 Plus meter recovery budget
DMP meter recovery SHALL be conditional and bounded. After a direct read
returns `0*0`, the implementation MAY send one initialization/recovery command
`ESC V<OID>*2AU CR` for that OID, accept acknowledgement `DsV<OID>*2`, and
repeat the direct read once. The recovery budget SHALL be one initialization
attempt per concrete OID within the current polling session or recovery
episode. A newly created DMP session context SHALL receive a fresh bounded
recovery budget.

#### Scenario: One-shot recovery after 0*0
- **WHEN** direct read for OID `40000` returns `0*0`
- **THEN** one `ESC V40000*2AU CR` recovery attempt is allowed
- **AND** direct read for OID `40000` is retried once

#### Scenario: No repeated recovery loop
- **WHEN** OID `40000` already consumed its recovery attempt in the current polling session
- **AND** a later polling cycle again reads `0*0`
- **THEN** the implementation does not send another `*2` recovery command for that OID in that same session episode

#### Scenario: Fresh session has fresh budget
- **WHEN** a fully new DMP connection/session context is established
- **THEN** each physical OID has a new one-shot recovery budget

### Requirement: Extron DMP 64 Plus meter scale mapping
DMP visual meter bars SHALL use a linear dB scale from `-60 dB` through
`+12 dB`: `normalized = clamp((db_value + 60) / 72, 0, 1)`. The
implementation SHALL NOT apply additional logarithmic conversion after raw
meter conversion. Values below `-60 dBFS` SHALL render as 0% fill.
`0 dBFS` SHALL render at approximately 83.3%. An unavailable sample SHALL
render as empty/unavailable and SHALL never render as maximum level.

#### Scenario: Scale examples
- **WHEN** DMP visual scale normalization is applied
- **THEN** `-60 dBFS` maps to `0%`
- **AND** `-48 dBFS` maps to approximately `16.7%`
- **AND** `-36 dBFS` maps to approximately `33.3%`
- **AND** `-24 dBFS` maps to `50%`
- **AND** `-12 dBFS` maps to approximately `66.7%`
- **AND** `0 dBFS` maps to approximately `83.3%`
- **AND** `+12 dBFS` maps to `100%`

#### Scenario: Unavailable bar
- **WHEN** a DMP channel sample is unavailable
- **THEN** the meter bar is empty or unavailable
- **AND** it is not displayed as `100%`

### Requirement: PDU diagnostics include optional related-room codec context

After a current user PDU refresh is accepted, the existing PDU screen SHALL be able to
present optional inventory-derived room context and related VCS codec diagnostic state. The
presentation SHALL include, when available and current:

```text
room_id
room_name
codec source/display model
codec diagnostic model
codec IP address
call status
presentation/broadcast status
```

The related-room section SHALL be contextual enrichment of the accepted PDU diagnostics,
not a replacement device diagnostic request. A not-found, ambiguous, unsupported,
unavailable, authentication, transport, protocol, or stale enrichment outcome SHALL NOT
change the accepted PDU diagnostic result into failure, clear outlet records, or disable
otherwise valid PDU control capabilities.

#### Scenario: PDU and related codec both succeed

- **WHEN** a supported PDU refresh succeeds, inventory resolves one room and one supported codec, and related-codec status succeeds
- **THEN** `PDUScreen` retains the PDU device/outlet data
- **AND** it also displays current room identity plus normalized codec call and presentation status

#### Scenario: PDU succeeds but room cannot be resolved

- **WHEN** accepted PDU diagnostics succeeds and inventory resolution is not found, ambiguous, mismatched, or missing room identity
- **THEN** `PDUScreen` retains successful PDU diagnostics and controls
- **AND** the related-room section displays the safe structured resolution state

#### Scenario: PDU succeeds but related codec fails

- **WHEN** room/codec resolution succeeds but related-codec authentication, transport, protocol, or status normalization fails
- **THEN** accepted PDU diagnostics remains successful and usable
- **AND** only the related-codec section displays the diagnostic failure
- **AND** no automatic modal device-connection error is shown

### Requirement: Related-codec status reuses supported codec protocol boundaries

Automatic related-codec status SHALL use the existing supported handler and transport
boundaries for Huawei TE20, Huawei TE40, CloudLink Bar 310, CloudLink Box 310, and
Polycom RPG 310. It SHALL reuse existing status methods and parser normalization where
available and SHALL NOT invent a protocol from `source_model`, a manufacturer substring,
or an unsupported inventory record.

For exact `CloudLink Box 310`, the related-codec path SHALL reuse the existing Bar 310
call/presentation command semantics and HTTPS:443 protocol boundary while keeping exact
Box application identity, Box credential selection, and Box successful connection memory.
Protocol equivalence SHALL NOT authorize implicit Bar credential/profile reuse or model
switching.

The focused related-codec adapter SHALL expose only normalized call and presentation status
to PDU presentation. Complete raw status and model-specific session artifacts SHALL remain
inside the handler/session/adapter boundary.

#### Scenario: Huawei related codec is resolved

- **WHEN** the inventory resolves an exact supported Huawei codec model/IP
- **THEN** automatic status uses that model's existing supported handler and saved-first transport order
- **AND** normalized call and presentation status are derived through the existing parser or an equivalent focused adapter

#### Scenario: CloudLink Box 310 related codec is resolved

- **GIVEN** inventory resolution returns exact `codec_diagnostic_model = CloudLink Box 310`
- **WHEN** automatic related-codec status is requested
- **THEN** it uses the shared Bar protocol handler and existing Bar call/presentation semantics over HTTPS:443
- **AND** credentials and saved connection state are resolved for exact `CloudLink Box 310` and codec IP
- **AND** accepted presentation remains exactly `CloudLink Box 310`
- **AND** the operation is not retried or relabeled as `CloudLink Bar 310`

#### Scenario: Polycom related codec is resolved

- **WHEN** the inventory resolves exact `Polycom RPG 310`
- **THEN** automatic status uses the existing Polycom status/session protocol boundary
- **AND** it does not reuse or alter the user codec interactive session

#### Scenario: Inventory codec is unsupported

- **WHEN** a canonical `video_codec` record has no exact supported VCS `diagnostic_model`
- **THEN** the related-codec section reports unsupported
- **AND** no handler is guessed or constructed from source text

### Requirement: Related-codec diagnostics are read-only

The automatic room-codec operation SHALL be read-only. It SHALL not expose or execute
presentation control, Wake, volume, mute, SIP update, call placement, call termination, or
another state-changing codec command. Its only device purpose in this change is to obtain
status required for the PDU/room context.

#### Scenario: Related-codec status is requested

- **WHEN** room/codec resolution succeeds
- **THEN** the application submits only the approved read-only status operation
- **AND** it does not send any codec state-changing command

#### Scenario: Status recovery is required

- **WHEN** the read-only status loses its session and bounded reconnect succeeds
- **THEN** the application may replay the read once
- **AND** no state-changing codec operation is introduced during recovery

### Requirement: CloudLink 310 runtime presentation uses proved structured evidence

For exact `CloudLink Bar 310` and exact `CloudLink Box 310`, the codec page SHALL expose visible rows:

```text
Режим сна
Версия камеры
Версия микрофона
```

Sleep SHALL normalize only:

```text
state.isSleep == 1 -> On
state.isSleep == 0 -> Off
```

Unsupported/missing/malformed sleep evidence remains unavailable and SHALL NOT become `Off`.

Peripheral version/type normalization SHALL use exact structured rules for each of `cameraVersion` and `micVersion`:

```text
field absent -> unavailable
field not a list -> malformed/unavailable
[] -> built-in
non-empty list -> every element must be a Mapping with exact non-empty string field "version"
                  ignore "name" and other fields for presentation authority
                  any malformed element makes the whole peripheral observation unavailable
                  otherwise strip versions, remove duplicate texts preserving first source order,
                  join with exact separator "; "
```

Successfully observed empty fields render exactly:

```text
cameraVersion == [] -> Встроенная камера
micVersion == []    -> Встроенный микрофон
```

A valid non-empty list renders the deterministic joined real-version text. Missing/malformed/unavailable evidence remains unavailable. The GUI SHALL NOT parse vendor WebUI `--`.

Version/type evidence SHALL NOT imply camera activity/connection, microphone physical connection, mute, gain, or live signal. `state.camera`, `state.mic`, `/v1/mediacontrol/mic/devices`, HD-AI list position, `MIC1`, `plugStatus`, and `gainVolume` receive no new user-visible physical/gain authority.

The screen remains rendering-only and SHALL NOT establish sessions, choose credentials, infer Bar versus Box, parse vendor containers, or perform blocking device I/O. Existing generation/currentness protects all new rows from stale callbacks.

CloudLink microphone-gain controls SHALL be disabled/unavailable for Bar/Box under this change; the GUI SHALL NOT expose an enabled control that can submit the prohibited gain mutation.

Model resolution remains unchanged. If inventory cannot resolve one exact supported CloudLink model, the existing purpose-bound fallback dialog remains authoritative; no network Bar/Box detector is introduced.

#### Scenario: CloudLink codec is sleeping

- **WHEN** accepted modern state reports `isSleep == 1`
- **THEN** `Режим сна` renders sleeping state
- **AND** GUI does not derive it from a legacy string/default

#### Scenario: CloudLink codec is awake

- **WHEN** accepted modern state reports `isSleep == 0`
- **THEN** `Режим сна` renders awake state
- **AND** zero is not treated as missing

#### Scenario: Camera version list is empty

- **WHEN** successful version response contains `cameraVersion == []`
- **THEN** `Версия камеры` displays `Встроенная камера`
- **AND** no camera activity/connection is inferred

#### Scenario: Microphone version list is empty

- **WHEN** successful version response contains `micVersion == []`
- **THEN** `Версия микрофона` displays `Встроенный микрофон`
- **AND** no connection/mute/gain/live-level state is inferred

#### Scenario: Multiple valid peripheral versions are present

- **WHEN** non-empty peripheral list contains valid version strings with duplicates
- **THEN** duplicate texts are removed preserving first source occurrence
- **AND** remaining texts are joined with `; `
- **AND** `name` does not affect display

#### Scenario: Non-empty peripheral list is partially malformed

- **WHEN** any entry is non-Mapping, lacks exact `version`, or has empty/non-string `version`
- **THEN** the whole peripheral-version observation is unavailable
- **AND** valid siblings are not partially rendered
- **AND** built-in fallback is not manufactured

#### Scenario: Inventory cannot resolve Bar or Box automatically

- **WHEN** existing inventory/model-resolution reaches unresolved fallback
- **THEN** operator may explicitly select `CloudLink Bar 310` or `CloudLink Box 310`
- **AND** this change performs no network model-detection probe
