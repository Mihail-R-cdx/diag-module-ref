# device-diagnostics-and-control Specification

## Purpose
TBD - created by archiving change bootstrap-openspec-baseline. Update Purpose after archive.
## Requirements
### Requirement: Supported production device diagnostics
The application SHALL provide production GUI diagnostic paths for Huawei TE20,
Huawei TE40, CloudLink Bar 310, CloudLink Box 310, Polycom RPG 310, Extron
IN1804, Extron IN1806, Extron IN1808, Extron IN1608 xi, the approved DTP CrossPoint exact
model set; first-generation XTP CrossPoint and XTP II CrossPoint frames are
deferred and SHALL NOT remain production-supported after this remediation, Aten PE8208AV, Extron IPL T PCS4i, Biamp Tesira Forte CI,
and Extron DMP 64 Plus only where those devices are connected to the
main-window/room dispatch through exact registered diagnostic models.

Each diagnostic path SHALL obtain device data through its worker/handler path
and present parser-normalized or handler-normalized data on the corresponding
screen/room surface. Extron Matrix support SHALL resolve an approved exact
capability/profile before issuing model-specific SIS reads or mutations.

The DTP CrossPoint support in this change is limited to DTP CrossPoint 84 and
DTP CrossPoint 82/84/86/108 4K. DTP2 CrossPoint, DTP3 CrossPoint, legacy
CrossPoint 300/450/Ultra, and unnamed CrossPoint generations remain unsupported.
Unknown/unsupported Extron identities SHALL NOT inherit a nearby profile by
substring similarity.

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
- **WHEN** an operator refreshes a supported Extron Matrix exact model, Aten PE8208AV, or Extron IPL T PCS4i successfully
- **THEN** the matrix or PDU screen/room surface receives normalized routing/topology or outlet data for that exact device
- **AND** an unknown Extron Matrix generation is not promoted to a supported profile

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
The GUI SHALL expose as network-capable device controls only operations implemented by the selected device path: codec presentation, audio/microphone operations, supported SIP server actions, Extron Matrix routing to an authoritative available logical output, Aten outlet on/off/reboot actions, Aten bulk on/off actions, Extron IPL T PCS4i outlet on/off actions, and Extron IPL T PCS4i bulk on/off actions. Unsupported device actions SHALL not be reported as successful.

For a supported Extron Matrix, route intent SHALL contain explicit authoritative `input_id` and `output_id`. Single-output models remain valid with output `1`; multi-output CrossPoint models MAY expose multiple independently routable outputs. Route mutation SHALL be rejected before send when either ID is unavailable in current accepted topology.

A reviewed fixed common dashboard MAY retain a visible local-only affordance for an unsupported codec or PDU operation only when the exact unified application/PDU capability authority explicitly marks that network capability unsupported and the click is resolved locally before room interaction admission. Such an affordance SHALL NOT be represented as an available/supported device network capability, SHALL NOT invalidate LIVE, acquire a handler/session, select credentials, create a mutation generation or perform device network I/O, and SHALL only produce the approved non-secret informational result.

For codec dashboards, the existing codec-specific local-only presentation exception remains limited to the reviewed common codec affordances already approved by the codec presentation contract. For the dedicated common PDU dashboard, the exception is limited to fixed PDU controls required by `diagnostic-ui-presentation`; it does not authorize arbitrary unsupported PDU actions or direct widget-to-handler dispatch.

The existing standalone/shared `PDUScreen` contract remains unchanged by this change. When that screen renders supported outlet controls for Extron IPL T PCS4i, it SHALL expose ON and OFF only; REBOOT SHALL NOT be shown as an operator action on that surface.

PCS4i REBOOT SHALL remain unsupported as a network operation and SHALL NOT enter the state-changing room lifecycle. Separately, the fixed common room PDU dashboard MAY retain its visible per-outlet `Перезапуск` affordance as local-only unsupported presentation. That room-dashboard affordance SHALL NOT extend to, or change the supported-control rendering of, the standalone/shared `PDUScreen`. Activating the room-dashboard affordance while the common room lock matrix otherwise permits input SHALL report locally that the command is unsupported before room interaction admission, with zero LIVE invalidation, credential selection, handler/session acquisition, mutation generation, device I/O, or accepted-state mutation. No PCS4i bulk REBOOT and no general PDU bulk REBOOT control is authorized on either surface.

#### Scenario: Extron routing action
- **WHEN** an operator selects an actionable Extron Matrix input/output cell under current accepted topology
- **THEN** the application/controller asks the active approved Matrix profile to route that exact input to that exact output
- **AND** the screen/room surface schedules the approved reconciliation/status refresh

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

#### Scenario: PCS4i fixed reboot affordance remains network-unsupported
- **GIVEN** selected exact device is `Extron IPL T PCS4i`
- **AND** the fixed common room PDU dashboard, rather than `PDUScreen`, is otherwise eligible for user input
- **WHEN** the operator activates the visible per-outlet `Перезапуск` affordance
- **THEN** the application reports locally that the command is unsupported
- **AND** REBOOT remains unavailable as a PCS4i network capability
- **AND** no room interaction admission, LIVE invalidation, credential selection, handler/session acquisition, mutation generation, device I/O, or accepted-state mutation starts

#### Scenario: Unsupported SIP update
- **WHEN** a codec handler does not implement SIP server update
- **THEN** the operation reports an unsupported or failed outcome rather than claiming the setting changed

#### Scenario: Fixed codec dashboard shows unsupported affordance
- **GIVEN** the fixed room codec dashboard contains a visual control whose exact-model network capability is explicitly unsupported
- **WHEN** the operator activates that affordance while the common room lock matrix otherwise permits input
- **THEN** the application reports locally that the operation is unsupported
- **AND** the operation is not represented as a supported device capability
- **AND** no handler/session/credential/network interaction begins

#### Scenario: Fixed PDU dashboard shows unsupported affordance
- **GIVEN** the fixed common room PDU dashboard contains a visual control whose exact-model network capability is explicitly unsupported
- **WHEN** the operator activates that affordance while the common room lock matrix otherwise permits input
- **THEN** the application shows an informational result equivalent to `Команда не поддерживается`
- **AND** the operation is not represented as a supported PDU network capability
- **AND** no LIVE invalidation, credential selection, handler/session acquisition, mutation generation or PDU device I/O begins

#### Scenario: Bulk action uses supported individual capability
- **GIVEN** the selected PDU model supports individual ON and OFF operations
- **WHEN** the shared PDU screen renders bulk controls
- **THEN** bulk ON is available only from the ON capability
- **AND** bulk OFF is available only from the OFF capability
- **AND** no bulk REBOOT control is exposed

#### Scenario: Unsupported bulk action is rejected
- **GIVEN** a PDU model does not support the requested individual operation
- **WHEN** a matching bulk operation is submitted programmatically
- **THEN** application dispatch rejects it before handler acquisition
- **AND** no PDU network I/O is started

### Requirement: Model-specific interactive codec session paths

The shared interactive controller SHALL preserve the supported transports, session artifacts, and operation boundaries of Huawei TE20, Huawei TE40, Huawei TE50, CloudLink Bar 310, CloudLink Box 310, and Polycom RPG 310. A model SHALL use only its supported functions, and functions on a separate worker path SHALL remain separate unless explicitly listed.

CloudLink Bar 310 and CloudLink Box 310 SHALL continue to use the same reviewed `CloudLinkBar310Handler` implementation while retaining exact assigned application model in operation context. Shared protocol capability SHALL NOT authorize Bar/Box aliasing, credential sharing, successful-index/profile sharing, model switching during recovery, or capability promotion from one exact model to the other.

For the CloudLink 310 family, one application-selected credential SHALL bind one handler generation for the exact model/IP/credential context. That generation MAY own:

```text
modern read subcontext
legacy compatibility/control subcontext
```

The modern read subcontext SHALL be established through `POST /v1/login/session` followed by `POST /v1/login/account`, retain cookies/token in memory only, and service only operations explicitly approved for the modern context. Modern action.cgi compatibility in this change is limited to the exact live-verified read-only requests `WEB_GetVersionInfoAPI`, `WEB_GetSystemMacAddrAPI`, and `WEB_GetMailboxDataAPI`.

Existing unverified read-only action.cgi operations, including audio, line/SIP, presentation, and camera reads, SHALL remain on the existing legacy compatibility path unless a later approved change proves their modern compatibility. Existing supported state-changing action.cgi operations SHALL remain on the legacy compatibility/control path and retain their existing mutation-safety rules.

The endpoint `WEB_GetCurrentAudioParam` remains classified as a legacy-compatibility endpoint for Box 310 protocol history, but **this change SHALL NOT advertise or execute it as a Box post-cycle LIVE capability**. The exact Box 310 application registration SHALL have no post-cycle LIVE binding. A future reviewed Box LIVE restoration MAY reuse that legacy transport boundary only after its own parser/normalization contract is approved.

CloudLink microphone-gain network capability is an explicit exception: for exact Bar 310 and Box 310 it SHALL remain unavailable/disabled because authoritative target selection and reconciliation are not established. The application/controller SHALL reject that network operation before device I/O. The fixed common room codec dashboard MAY retain its `−`/`+` microphone visual affordances, but for Bar/Box those affordances SHALL resolve locally as unsupported before room interaction admission and SHALL NOT be represented as a supported network capability.

The application SHALL NOT issue gain `PUT`/`POST /v1/mediacontrol/mic/devices`, use fixed device IDs, use first-HD-AI/first-plugged selection, use `gainVolume` as authoritative reconciliation, or infer gain support from a method/widget. Re-enabling gain requires a later approved contract.

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
- **GIVEN** the exact application model is `CloudLink Box 310`
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
- **AND** shared handler ownership does not imply or create a Box post-cycle LIVE binding

#### Scenario: Unverified action.cgi read remains legacy-compatible
- **WHEN** CloudLink refresh or interactive work needs existing audio, line/SIP, presentation, camera, or another read-only action.cgi operation not live-verified on modern auth
- **THEN** this change does not migrate that operation to the modern context
- **AND** its existing legacy compatibility path remains authoritative until separately approved

#### Scenario: Box live meter remains legacy-compatible
- **GIVEN** exact model is `CloudLink Box 310`
- **WHEN** current-change room interactive capabilities are composed
- **THEN** Box 310 advertises no post-cycle LIVE binding
- **AND** room LIVE performs no `WEB_GetCurrentAudioParam` request for Box 310
- **AND** the endpoint's legacy-compatibility transport classification remains dormant protocol knowledge for a future approved Box LIVE restoration
- **AND** this change does not require or authorize modern `X-Access-Token` or modern body-token routing for that deferred endpoint

#### Scenario: Existing CloudLink mutation stays on legacy control path
- **WHEN** Bar 310 or Box 310 performs an already supported mutation other than microphone gain, such as Wake, presentation mutation, supported mute semantics, speaker volume, or SIP configuration
- **THEN** the operation remains on its existing legacy compatibility/control path
- **AND** modern read evidence does not authorize migration or blind replay

#### Scenario: CloudLink microphone gain is disabled
- **GIVEN** exact model is `CloudLink Bar 310` or `CloudLink Box 310`
- **WHEN** user/application requests microphone-gain mutation through any network-capable boundary
- **THEN** the operation is unavailable/disabled before device network I/O
- **AND** no gain PUT/POST, fixed-ID target, first-HD-AI selection, or gain readback is attempted
- **AND** no ambiguous mutation result can trigger alternate-method replay

#### Scenario: CloudLink fixed gain affordance is local only
- **GIVEN** the fixed common room codec dashboard is rendering Bar 310 or Box 310
- **WHEN** the operator clicks visible microphone `−` or `+` while the room lock matrix otherwise permits input
- **THEN** the application resolves the affordance locally as unsupported
- **AND** no room mutation generation, handler/session acquisition or device I/O starts
- **AND** the network capability remains unavailable/disabled

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

#### Scenario: Huawei TE50 keeps exact identity while reusing TE40 session behavior

- **GIVEN** the exact application model is `Huawei TE50`
- **WHEN** it performs a function covered by the approved TE40 contract
- **THEN** it uses the same approved TE40 transport/session behavior
- **AND** operation context, credential/profile memory, parser output, and presentation retain exact model identity `Huawei TE50`
- **AND** no loose Huawei-family or `TE*` model inference is admitted

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

### Requirement: Supported device diagnostics expose bounded room one-shot acquisition

Every exact application model already supported by the production diagnostic dispatch SHALL expose a room-compatible read-only one-shot acquisition through the application-owned model capability registry when that model is eligible for automatic room diagnostics.

The room adapter SHALL reuse the model's approved handler/controller/worker transport and parser/normalization semantics rather than reimplementing protocol logic in the room orchestrator. Existing exact model identity SHALL be preserved, including distinct `CloudLink Bar 310` and `CloudLink Box 310` application identities even where they share handler implementation.

One-shot room acquisition SHALL terminate persistent diagnostic behavior after the required authoritative snapshot is obtained. A successful automatic room acquisition SHALL NOT leave model polling, keepalive, live meters, or reusable diagnostic network sessions running after the adapter's cleanup-complete boundary.

#### Scenario: CloudLink Box room diagnostic preserves exact identity

- **GIVEN** a room row has exact canonical model `CloudLink Box 310`
- **WHEN** its one-shot adapter uses the shared CloudLink 310 handler implementation
- **THEN** the operation context and accepted row state remain exactly `CloudLink Box 310`
- **AND** it is not relabeled or retried as `CloudLink Bar 310`

#### Scenario: Continuous diagnostic path is adapted to one shot

- **WHEN** a supported model normally uses polling, keepalive, or another persistent read lifecycle
- **AND** the model is acquired by the automatic room cycle
- **THEN** the adapter accepts only the required one-shot final diagnostic snapshot
- **AND** persistent diagnostic activity is stopped/released before room cleanup completion

### Requirement: Room one-shot acquisition preserves approved model-specific usable result semantics

A room adapter SHALL preserve the distinction between authoritative primary diagnostic usability and optional enrichment completion. An explicitly approved optional-enrichment failure SHALL NOT convert already accepted authoritative primary data into terminal room failure merely because the enrichment failed. Diagnostic usability and successful-credential persistence are separate authorities; credential persistence is governed by the modified `credential-source-isolation` contract for this change.

When no authoritative final diagnostic data is available, the adapter SHALL return terminal failure rather than emitting an empty/technical-only result as successful room state. Partial/intermediate results SHALL remain explicitly non-final unless a model-specific room-one-shot contract below promotes authoritative primary data to a usable terminal outcome.

#### Scenario: Polycom optional SSH enrichment is unavailable

- **WHEN** Polycom authoritative HTTPS diagnostic status succeeds and optional SSH enrichment fails during room one-shot acquisition
- **THEN** the room adapter SHALL return usable final success with a structured warning
- **AND** the authoritative HTTPS data remains available to the exact row
- **AND** the row may be presented as `подключено` with that warning
- **AND** the optional SSH failure SHALL NOT be treated as credential-retry authority
- **AND** successful-candidate persistence is decided independently under the modified `credential-source-isolation` contract

#### Scenario: PCS4i outlet-name enrichment is unavailable

- **WHEN** PCS4i authoritative Telnet outlet status succeeds but optional HTTP outlet-name enrichment fails
- **THEN** the room adapter may return usable final success with warning and safe fallback names under the existing model contract
- **AND** the Telnet status is not represented as a failed device acquisition

#### Scenario: No usable diagnostic payload exists

- **WHEN** a model path completes without any authoritative final diagnostic payload
- **THEN** the room adapter returns terminal failure
- **AND** it does not publish a successful row containing only technical context such as IP/profile metadata

### Requirement: Automatic room PDU acquisition remains independent from related-codec enrichment

Aten PE8208AV and Extron IPL T PCS4i automatic room one-shot diagnostics SHALL return only the PDU row's own accepted diagnostic data through the room adapter boundary. The automatic room acquisition SHALL NOT invoke or publish the legacy application boundary whose semantic meaning is an accepted current **user PDU refresh** for `pdu-room-codec-enrichment`.

The related codec, when present as a canonical room record, SHALL be diagnosed only by its own room-row adapter at its deterministic queue position. PDU result data SHALL NOT become room-codec diagnostic authority.

#### Scenario: Automatic Aten room row succeeds

- **WHEN** automatic room polling obtains accepted Aten PDU status
- **THEN** the Aten row receives that PDU diagnostic state
- **AND** no related-codec enrichment starts as a side effect

#### Scenario: Automatic PCS4i room row succeeds

- **WHEN** automatic room polling obtains accepted PCS4i outlet status
- **THEN** the PCS4i row receives that PDU diagnostic state
- **AND** no related-codec enrichment starts as a side effect

### Requirement: Room diagnostic adapters do not expand supported control surface

Adding a model to the automatic room tree SHALL NOT by itself authorize new state-changing operations, transports, protocol fallbacks, credential sharing, or post-cycle live behavior. In MIH-7 room mode, existing device-specific network-backed controls SHALL remain disabled or unbound both during and after automatic room-cycle completion. Existing control capability in legacy single-device mode SHALL NOT grant room-mode target authority.

Until the separately approved `room-device-interaction-lifecycle` binds an action to the exact current room record, MIH-7 SHALL reject local Refresh, Matrix routing, PDU mutation, codec mutation, auxiliary network reads, live starts, or equivalent reused-screen network intents before handler acquisition or device network I/O. Presentation of a `подключено` row SHALL NOT by itself enable those controls.

#### Scenario: Room scan completes for a controllable device

- **WHEN** a device with existing control capabilities completes automatic room acquisition
- **THEN** MIH-7 has established diagnostic row state only
- **AND** the adapter has not sent a state-changing command
- **AND** existing device network controls remain unavailable in room mode

#### Scenario: Legacy mutation intent is invoked after room completion

- **GIVEN** a supported room row completed automatic acquisition successfully
- **WHEN** a reused legacy Matrix, PDU, codec, or equivalent state-changing intent is invoked before exact-row interaction binding exists
- **THEN** application composition rejects or disables that intent before handler acquisition
- **AND** no mutation or other device network I/O is sent

#### Scenario: Legacy auxiliary or live intent is invoked after room completion

- **GIVEN** room mode has reached a terminal clean or problem outcome
- **WHEN** a reused local Refresh, Call Log/auxiliary read, live/poll start, or equivalent network-backed view intent is invoked
- **THEN** MIH-7 keeps the intent unavailable or rejects it before network I/O
- **AND** a top-level source IP or prior single-device context is not accepted as the row target

### Requirement: Codec call activity applicability and normalization are owned by the unified exact-model registry

The same unified exact application model registration that owns diagnostic and room-interaction capability dispatch SHALL be the sole applicability authority for codec call-activity projection. An exact codec registration whose approved diagnostic snapshot exposes call-state evidence SHALL explicitly declare a call-activity normalization/projection binding equivalent to `call_activity_binding_key`; applicability SHALL NOT be inferred from whether a runtime payload happens to contain a call field and SHALL NOT be maintained in a second occupancy-specific model list.

For the current change base, the following exact codec registrations already have approved diagnostic call-state evidence and therefore SHALL each declare a bound call-activity projection:

```text
Huawei TE20
Huawei TE40
CloudLink Bar 310
CloudLink Box 310
Polycom RPG 310
```

These five exact names are a baseline acceptance/test oracle for this change, not a second runtime support table. Runtime composition SHALL continue to enumerate applicability only from the unified application model registration. Bar 310 and Box 310 MAY share one normalizer implementation when their approved evidence semantics permit it, but each exact registration SHALL explicitly declare its binding. A future exact codec model whose approved diagnostic snapshot adds call-state evidence SHALL add its call-activity binding through that same unified registration in the reviewed change that adds the evidence.

For every bound exact codec model, application/model normalization SHALL project model/protocol-specific current accepted call evidence into exactly one model-neutral typed value before room-level aggregation:

```text
CallActivity.ACTIVE
CallActivity.INACTIVE
CallActivity.UNKNOWN
```

`ACTIVE` means that the exact-model normalization boundary has current accepted evidence that unambiguously proves a current call according to that model's approved call-state semantics. `INACTIVE` means that current accepted exact-model evidence unambiguously proves there is no current call. Missing, stale, failed, unsupported, contradictory, or unrecognized evidence SHALL normalize to `UNKNOWN`.

When an existing parser/handler exposes only a string-valued call state, its exact-model normalization adapter MAY map that value to `CallActivity`, but the mapping SHALL be explicit and model-scoped, SHALL prefer structured/typed protocol evidence when available, and SHALL default unrecognized values to `UNKNOWN`. Shared room or presentation code SHALL NOT classify localized labels, display strings, protocol strings, or arbitrary substrings such as `Active`, `Incoming`, `Calling`, `В звонке`, `No Call`, or similar values.

The projection SHALL reuse already accepted diagnostic/post-cycle codec evidence. Creating or updating `CallActivity` SHALL NOT add a new codec request, timer, worker, handler/session acquisition, credential attempt, retry lane, or mutation.

For `diagnostic-ui-presentation`, a relevant call-capable room codec row SHALL mean a row whose exact unified model registration declares the required bound call-activity projection. Runtime presence or absence of a `CallActivity` field SHALL NOT decide whether a registered baseline codec participates, and presentation SHALL NOT keep a parallel model list. A relevant row with missing, stale, failed, contradictory, or unrecognized current evidence remains relevant and SHALL contribute `CallActivity.UNKNOWN` rather than disappearing from aggregation.

Application startup/composition validation SHALL fail closed when a codec registration required by this contract omits its call-activity binding or references a binding unavailable to composition. A required model SHALL NOT be silently excluded from room busy aggregation.

#### Scenario: Current baseline codec registrations all declare call activity

- **GIVEN** the current exact application registry contains `Huawei TE20`, `Huawei TE40`, `CloudLink Bar 310`, `CloudLink Box 310`, and `Polycom RPG 310`
- **WHEN** registry/composition validation runs
- **THEN** every one of those exact entries declares an available call-activity projection binding
- **AND** no occupancy-specific model support list is consulted

#### Scenario: Required call-activity binding is missing

- **GIVEN** one exact codec registration required by this contract omits its call-activity binding or names an unavailable binding
- **WHEN** application registry/composition validation runs
- **THEN** validation fails closed
- **AND** the model cannot silently disappear from room busy aggregation

#### Scenario: Bound codec remains applicable when evidence is missing

- **GIVEN** an exact room codec registration declares the required available call-activity binding
- **AND** current call evidence is missing, stale, failed, contradictory, or unrecognized
- **WHEN** room call activity is projected
- **THEN** the codec remains applicable to aggregation
- **AND** its typed contribution is `CallActivity.UNKNOWN`
- **AND** runtime field absence does not make the codec irrelevant

#### Scenario: Exact-model active call becomes typed ACTIVE

- **GIVEN** a supported exact codec model returns current accepted call evidence that its model-specific normalization contract recognizes as a current call
- **WHEN** its bound application normalization publishes room-row call activity
- **THEN** it publishes `CallActivity.ACTIVE`
- **AND** no room GUI string parsing is required

#### Scenario: Exact-model no-call evidence becomes typed INACTIVE

- **GIVEN** a supported exact codec model returns current accepted call evidence that its model-specific normalization contract recognizes as no current call
- **WHEN** its bound application normalization publishes room-row call activity
- **THEN** it publishes `CallActivity.INACTIVE`

#### Scenario: Unknown call evidence fails closed

- **GIVEN** a codec call-state value is missing, stale, failed, contradictory, or not explicitly recognized by that exact model's normalization mapping
- **WHEN** the bound application normalization projects call activity
- **THEN** it publishes `CallActivity.UNKNOWN`
- **AND** shared room/presentation code does not infer activity from string fragments

### Requirement: Extron IN1804 Matrix normalization is fail-closed for routing authority

The existing IN1804 diagnostic path SHALL continue to use its current hardware-confirmed SIS reads. Its accepted evidence remains fail-closed exactly as before. The generalized Matrix model MAY project the one accepted IN1804 route into `routes[1]`, but SHALL NOT weaken the existing `current_connection` grammar or fabricate evidence.

`inputs_num` SHALL be accepted only when current model/capability evidence positively establishes the count. Missing/failed/unusable model evidence and local sentinels such as `Unknown` remain absent/`None`. Temperature is accepted only from a successful parseable current measurement; failed/malformed evidence remains absent and a real device-reported zero remains valid.

For IN1804, `current_connection` remains an optional accepted input ordinal derived only from the successfully parsed existing `!` readback and only when exactly one valid input within the proven accepted range is identified. The generalized route map SHALL represent that same evidence as `routes[1] = current_connection`; unknown route evidence SHALL produce `routes[1] = None/UNKNOWN` according to the normalized representation and SHALL NOT substitute input 1.

The existing `!` grammar remains self-contained and fail-closed: after framing normalization one exact command-echo line MAY be removed, then exactly one recognized current-input response family is accepted: decimal input ordinal `N` or tagged `In<N> All`, with `N` inside the proven range. Extra/multiple/ambiguous/unrelated numeric payload remains UNKNOWN.

The room HDCP projection consumes normalized **input HDCP status**, not authorization/configuration or output HDCP. IN1804 raw input status remains: `2 -> True`, `1 -> False`, `0 -> False`, unusable -> `None`.

#### Scenario: Unproven Matrix input count remains unknown
- **GIVEN** the Extron IN1804 diagnostic acquisition does not obtain evidence that establishes current supported input count
- **WHEN** Matrix data is normalized
- **THEN** normalized input count is UNKNOWN/absent rather than eight by default
- **AND** unproven input ordinals are not accepted as route targets

#### Scenario: Failed model evidence remains no-data
- **GIVEN** the existing model read fails, is missing, or yields only a local `Unknown` convenience sentinel
- **WHEN** Matrix data is normalized
- **THEN** accepted model evidence is absent/`None`
- **AND** room presentation cannot treat `Unknown` as a device-reported model value

#### Scenario: Failed temperature evidence does not become zero
- **GIVEN** the existing temperature read fails, is missing, or is malformed
- **WHEN** Matrix data is normalized
- **THEN** accepted temperature evidence is absent/`None`
- **AND** numeric zero is not synthesized

#### Scenario: Device-reported zero temperature remains a real value
- **GIVEN** a successful current temperature response explicitly yields numeric zero
- **WHEN** Matrix data is normalized
- **THEN** accepted temperature is numeric zero
- **AND** it is not converted to UNKNOWN merely because its value is zero

#### Scenario: Empty connection evidence does not become Input 1
- **GIVEN** the existing connection read returns no usable route evidence
- **WHEN** Matrix data is normalized
- **THEN** `current_connection` is UNKNOWN/`None`
- **AND** `routes[1]` contains no fabricated input
- **AND** input 1 is not synthesized

#### Scenario: Untagged current-input response is accepted intentionally
- **GIVEN** proven current input range includes input N
- **AND** the existing `!` query returns exactly one untagged current-input payload containing only decimal ordinal N after normal framing removal
- **WHEN** Matrix data is normalized
- **THEN** `current_connection == N`
- **AND** `routes[1] == N`
- **AND** no unrelated digits are searched or concatenated

#### Scenario: Tagged current-input response is accepted intentionally
- **GIVEN** proven current input range includes input N
- **AND** the existing `!` query returns exactly one tagged/verbose payload `In<N> All` after normal framing removal
- **WHEN** Matrix data is normalized
- **THEN** `current_connection == N`
- **AND** `routes[1] == N`

#### Scenario: Exact command echo may precede one valid payload
- **GIVEN** the device/session echoes `!` as one exact line
- **AND** exactly one valid untagged or tagged current-input response follows
- **WHEN** Matrix data is normalized
- **THEN** only the exact echo line is discarded
- **AND** the one valid response is parsed normally

#### Scenario: Malformed or ambiguous connection evidence does not become Input 1
- **GIVEN** a connection response is successful at transport level but contains no exact recognized response, multiple payload candidates, extra payload, multiple numeric candidates, or unrelated digits
- **WHEN** Matrix data is normalized
- **THEN** `current_connection` is UNKNOWN/`None`
- **AND** `routes[1]` is not fabricated
- **AND** unrelated digits are not concatenated into route authority

#### Scenario: Out-of-range connection evidence is rejected
- **GIVEN** a proven accepted input count exists
- **AND** parsed route evidence names an input outside that range
- **WHEN** Matrix data is normalized
- **THEN** `current_connection` is UNKNOWN/`None`
- **AND** the out-of-range value cannot authorize presentation or reconciliation

#### Scenario: HDCP read failure remains unknown
- **GIVEN** the existing input HDCP-status read fails or returns malformed/unrecognized evidence
- **WHEN** the input HDCP presence projection is normalized
- **THEN** its value is UNKNOWN/`None`
- **AND** the GUI cannot present that failure as confirmed `нет`

#### Scenario: Exact HDCP status mapping is deterministic
- **GIVEN** existing IN1804 input HDCP-status evidence is respectively `2`, `1`, and `0`
- **WHEN** each value is normalized
- **THEN** the resulting `hdcp_present` values are respectively True, False, and False
- **AND** no HDCP version token is required for room presentation

### Requirement: Matrix route reconciliation cannot succeed from synthetic or unknown evidence

Any Matrix room reconciliation SHALL consume fail-closed normalized evidence. For the existing IN1804 path, all existing accepted `!` grammar and `current_connection` requirements above remain valid. For generalized multi-output Matrix profiles, mutation confirmation SHALL use accepted `routes[target_output_id]` evidence from an authoritative current read of that same logical output.

A parser/handler default, missing readback, failed read, malformed response, unknown route, unavailable input/output, unproven topology, unrelated digit sequence, or response outside the active profile's exact accepted grammar SHALL never satisfy reconciliation.

#### Scenario: Requested Input 1 is not confirmed by empty readback
- **GIVEN** output 1/input 1 was requested and route send entered reconciliation
- **WHEN** current connection readback is empty, failed, malformed, ambiguous, outside the accepted grammar, or otherwise UNKNOWN
- **THEN** reconciliation does not confirm input 1
- **AND** the room mutation remains unconfirmed according to `room-device-interaction-lifecycle`

#### Scenario: Requested input is confirmed by truthful readback
- **GIVEN** output 1/input N was requested
- **AND** current reconciliation readback establishes valid normalized route evidence equal to N for output 1
- **WHEN** reconciliation evaluates the result
- **THEN** that route evidence may satisfy the route-match condition
- **AND** final acceptance remains subject to currentness and lifecycle cleanup requirements

### Requirement: Room codec dashboard data uses one typed model-neutral presentation projection

For every current exact codec registration, the room diagnostic/application boundary SHALL expose a model-neutral codec presentation projection sufficient for the fixed dashboard slots without making raw model-specific parser text or standalone Qt widgets into shared presentation authority.

The projection SHALL distinguish usable current evidence from absence/unknown and SHALL provide safe values where current approved diagnostic evidence exists for:

```text
model
mac_address
serial_number
platform
software_version
microphone
camera
call_status
presentation_status
sip_h323_registration
microphone_level
microphone_volume
microphone_mute_state
speaker_volume
speaker_mute_state
```

`microphone_volume` and `speaker_volume` SHALL be optional comparable numeric values. `microphone_mute_state` and `speaker_mute_state` SHALL be typed states equivalent to `MUTED | UNMUTED | UNKNOWN`; they SHALL NOT share one untagged scalar slot with numeric volume. An exact-model adapter MAY derive speaker mute state from numeric zero/non-zero only where that model's approved contract defines zero as muted. Shared Qt code SHALL NOT infer mute from display strings.

A model MAY legitimately have no current evidence for one or more slots. Absence SHALL remain absence and presentation SHALL render `Нет данных`; this change SHALL NOT add protocol reads solely to make every slot non-empty.

Existing typed `CallActivity` remains the model-neutral call-activity authority where applicable. Shared room presentation SHALL prefer typed/structured normalization where one exists and SHALL NOT derive shared semantic status by substring matching localized/model-specific call strings.

#### Scenario: Current model lacks platform evidence
- **GIVEN** the exact codec diagnostic snapshot has no current approved platform evidence
- **WHEN** model-neutral codec presentation is projected
- **THEN** `platform` remains unavailable
- **AND** no parser default, model string or standalone UI label is substituted as device evidence

#### Scenario: Numeric volume and mute state remain distinct
- **GIVEN** current accepted codec evidence proves a numeric speaker volume and a mute state
- **WHEN** model-neutral projection is built
- **THEN** numeric volume remains numeric authority for relative target construction
- **AND** mute state remains typed desired-state/readback authority
- **AND** neither value overwrites or stringifies the other into one ambiguous slot

### Requirement: Current codec room-control support matrix is a fixed acceptance oracle

The unified exact-model registration SHALL remain the sole runtime capability authority. Implementation and tests SHALL prove these exact network-capability declarations:

| Exact model | speaker_adjust | speaker_mute | microphone_adjust | microphone_mute | reboot |
| --- | --- | --- | --- | --- | --- |
| `Huawei TE20` | SUPPORTED | SUPPORTED | UNSUPPORTED | SUPPORTED | UNSUPPORTED |
| `Huawei TE40` | SUPPORTED | SUPPORTED | **SUPPORTED** | SUPPORTED | UNSUPPORTED |
| `Huawei TE50` | SUPPORTED | SUPPORTED | **SUPPORTED** | SUPPORTED | UNSUPPORTED |
| `CloudLink Bar 310` | SUPPORTED | SUPPORTED | UNSUPPORTED | UNSUPPORTED | UNSUPPORTED |
| `CloudLink Box 310` | SUPPORTED | SUPPORTED | UNSUPPORTED | UNSUPPORTED | UNSUPPORTED |
| `Polycom RPG 310` | SUPPORTED | SUPPORTED | UNSUPPORTED | SUPPORTED | UNSUPPORTED |

This table is an OpenSpec/test oracle and SHALL NOT become a second runtime registry.

TE40 and exact-model TE50 numeric microphone gain are distinct from microphone mute. Their approved primary-input target is `MIC1`. User-facing configured gain range is `-12 dB .. +12 dB`, step `1 dB`; device/wire range is `0..24`, step `1`, with `gain_db = mic1Value - 12` and `mic1Value = gain_db + 12`. Huawei speaker volume is a separate control domain: TE20/TE40/TE50 speaker adjustment remains `0..21`, step `1`; that speaker range SHALL NOT be reused as the MIC1 or RCA-input gain bound.

Speaker mute support for all six exact models SHALL continue to use only the approved volume-zero/restore desired-state policy and proven exact-row/generation restore evidence; it does not imply a separate raw speaker-mute wire command.

Polycom RPG 310 speaker adjustment SHALL use range `0..100`, step `2`. TE20/TE40/TE50 speaker adjustment SHALL use `0..21`, step `1`. Bar/Box speaker adjustment SHALL use `0..15`, step `1`.

Post-cycle LIVE capability is not inferred from this mutation table; it is advertised separately by the same exact-model registration. In this change Box 310 SHALL advertise no post-cycle LIVE binding.

#### Scenario: Current codec registration matrix is checked

- **WHEN** composition tests inspect the six current exact codec registrations
- **THEN** every operation matches the table above
- **AND** TE40 and TE50 expose microphone gain and microphone mute as separate supported operations
- **AND** Box 310 does not acquire a post-cycle LIVE capability by sharing a handler with Bar 310
- **AND** runtime resolution still comes from the unified registry rather than this test-oracle table

### Requirement: Codec room-control adapters reuse approved typed operations and explicitly reject unsupported operations

The room codec-control capability SHALL reuse existing approved safe codec operation/readback semantics rather than duplicate protocol command grammar in the room GUI. Each exact codec registration SHALL bind an application/core codec-control adapter, or equivalent registry-owned binding, that can answer operation support before network acquisition and construct typed desired-state/readback operations only for approved controls.

A standalone widget branch, handler attribute probe, accepted read-only field, shared handler type, or visually present button SHALL NOT silently promote a state-changing or LIVE capability.

`Huawei TE20` and `Polycom RPG 310` remain microphone-mute models with no approved numeric microphone-adjust mutation in this change. `Huawei TE40` and exact-model `Huawei TE50` support both independent numeric microphone gain and independent microphone mute under the approved TE40 contract. `CloudLink Bar 310` and `CloudLink Box 310` retain both microphone-adjust and separate microphone-mute mutation as unsupported.

Reboot SHALL remain unsupported for the current six-codec baseline.

#### Scenario: Microphone has mute but no numeric gain contract

- **GIVEN** exact model is `Huawei TE20` or `Polycom RPG 310`
- **WHEN** its room codec-control capability is composed
- **THEN** `microphone_mute` is supported
- **AND** `microphone_adjust` is unsupported
- **AND** shared GUI code does not reinterpret mute state as a numeric gain range

#### Scenario: CloudLink microphone controls remain network-unsupported

- **GIVEN** exact model is `CloudLink Bar 310` or `CloudLink Box 310`
- **WHEN** its room codec-control capability is composed
- **THEN** `microphone_adjust` and `microphone_mute` are both unsupported for room mutation
- **AND** fixed visual affordances may use only the existing local informational path
- **AND** no accepted numeric read evidence promotes either mutation capability

#### Scenario: TE40/TE50 numeric gain and mute are independent supported operations

- **GIVEN** exact model is `Huawei TE40` or `Huawei TE50`
- **WHEN** its room codec-control capability is composed
- **THEN** `microphone_adjust` is supported only through the approved `MIC1` gain contract
- **AND** `microphone_mute` remains separately supported
- **AND** changing gain never reuses `WEB_OpenMicAPI` / `WEB_CloseMicAPI`
- **AND** numeric gain value `0` is not interpreted as mute authority

### Requirement: Codec audio mutation authority separates current numeric value, mute state and restore evidence

A supported room codec audio desired-state operation SHALL use the same exact model/IP credential and transport safety boundaries as existing codec interaction. Before sending, the adapter SHALL validate the requested absolute target against its exact model operation range/state contract. Invalid, missing or contradictory targets SHALL fail before state-changing I/O.

Room-owned speaker restore authority SHALL be scoped to the exact current room generation and record. The application/core layer MAY remember the last accepted current non-zero `speaker_volume` for that exact row as a restore target. Widget-local `last_unmuted_volume`, requested values, ACKs, defaults, minimum values, another row's value, or fabricated `1` SHALL NOT become restore authority.

For a volume-zero speaker mute model:

```text
current accepted speaker_volume > 0 + mute intent
    -> desired absolute target 0
    -> current accepted non-zero value may remain the restore target

current accepted speaker_volume == 0 + unmute intent + proven restore target
    -> desired absolute target = proven restore target

current accepted speaker_volume == 0 + unmute intent + no proven restore target
    -> local unavailable result
    -> zero mutation/network I/O
```

A newly accepted non-zero authoritative speaker value MAY replace the prior restore target for the same current row/generation. Collapse/re-render does not make widget history authoritative; new room generation/context invalidation clears old restore authority.

For TE20/TE40/Polycom microphone mute, the desired target SHALL be typed `MUTED` or `UNMUTED` and reconciliation SHALL compare the typed current microphone mute state. Numeric microphone gain SHALL not be fabricated from that state.

Readback/reconciliation SHALL compare model-neutral normalized current state with the exact desired target. A command return value, ACK, HTTP success, SSH/Telnet prompt, empty error, or user-facing string SHALL NOT by itself confirm final audio state.

For relative-button intent represented as an absolute target, retry/fallback safety SHALL follow the existing relative-as-absolute operation contract: a structured authentication rejection may advance credentials only when the operation is proven not delivered under the applicable mutation-safety gate; after possible delivery, the operation SHALL NOT be blindly repeated with another credential.

#### Scenario: Desired target is outside exact model range
- **WHEN** a codec-control adapter receives an absolute audio target outside its exact approved model range
- **THEN** the operation fails closed before handler/session acquisition or state-changing send
- **AND** authoritative row data is unchanged

#### Scenario: Speaker unmute has no restore evidence
- **GIVEN** current accepted speaker volume is zero
- **AND** the exact row/generation has no accepted non-zero restore target
- **WHEN** the operator requests speaker unmute
- **THEN** no default/minimum/`1` target is invented
- **AND** no room mutation or device I/O starts
- **AND** a safe local unavailable result is shown

#### Scenario: Send appears successful but readback differs
- **WHEN** a supported audio mutation send returns apparent success
- **AND** mandatory readback does not prove the desired normalized state
- **THEN** the operation remains unconfirmed/failed under the room mutation contract
- **AND** the desired value is not written optimistically into authoritative row state

### Requirement: Current PDU room-control support matrix is a fixed acceptance oracle

The existing exact application/PDU capability authority SHALL remain the sole runtime support/dispatch authority. For the current `master` baseline, implementation and tests SHALL nevertheless prove the following expected capabilities; this table is test/acceptance data only and SHALL NOT become a second runtime model registry or duplicated GUI support table:

| Exact model | refresh | outlet_on | outlet_off | outlet_reboot | bulk_on | bulk_off |
| --- | --- | --- | --- | --- | --- | --- |
| `Aten PE8208AV` | SUPPORTED | SUPPORTED | SUPPORTED | SUPPORTED | SUPPORTED | SUPPORTED |
| `Extron IPL T PCS4i` | SUPPORTED | SUPPORTED | SUPPORTED | UNSUPPORTED | SUPPORTED | SUPPORTED |

Bulk ON/OFF support is derived from the existing supported individual ON/OFF capability/policy rather than from a new dashboard-owned protocol command. The table SHALL NOT authorize bulk reboot.

If approved source/contracts change before implementation such that this matrix is no longer true, the OpenSpec architecture SHALL be reviewed before implementation silently changes the common dashboard behavior.

#### Scenario: Current PDU capability oracle is checked

- **WHEN** composition/regression tests inspect the two current exact PDU models
- **THEN** their current operation support matches the table above
- **AND** runtime resolution still comes from existing exact PDU capability authority rather than this acceptance table

### Requirement: PDU presentation metadata does not create new device telemetry authority

The common room PDU presentation MAY consume the exact current room record's canonical `serial_number` and `mac_address` for the fixed information card. It SHALL NOT add a PDU protocol read solely to populate those presentation values, and absence SHALL remain absence for presentation as `—`.

Per-outlet current power is not an approved current PDU diagnostic field in this change. The application/handler boundary SHALL NOT add a power polling operation solely because the fixed dashboard contains a `Текущая мощность` column. The presentation placeholder SHALL remain non-authoritative until a later reviewed capability defines a source and lifecycle.

#### Scenario: Dashboard is built with no power capability

- **GIVEN** the current exact PDU capability exposes no authoritative per-outlet power read
- **WHEN** the common PDU dashboard is rendered or locally refreshed under current approved diagnostics
- **THEN** no power-specific handler/session/device request is introduced by this change
- **AND** the presentation uses the approved `—` placeholder

### Requirement: Room call-log preview and detail share typed chronology authority across separate acquisitions

Automatic inline call-log preview and the detailed call-log window SHALL use the same application-owned normalized call-history record schema, parser/normalizer semantics, chronology rules, and exact-model retrieval authority. This change SHALL NOT create a second parser/schema solely for the three-row preview or for the fresh detailed-journal load.

Automatic preview and explicit detailed opening MAY nevertheless consume **different accepted `CallHistorySnapshot` instances (or equivalent typed normalized results)** because they are distinct acquisition epochs. The automatic-preview snapshot is authoritative only for the preview acquisition that produced it. Every explicit detailed-journal opening is a fresh serialized call-log acquisition and its detailed rows/statistics SHALL use only that explicit load's current accepted normalized result.

The normalized result for every acquisition SHALL establish chronology before presentation. Records SHALL already be ordered newest-first using typed comparable `start_at` evidence. A record with no parseable/comparable `start_at` SHALL sort after every record with proven chronology. Ordering among equal timestamps or records lacking chronology SHALL preserve deterministic normalized acceptance/source order; presentation SHALL NOT sort localized `start_display` strings lexicographically and SHALL NOT guess missing timestamps.

For an accepted automatic-preview acquisition, the room preview SHALL take the first three records of that accepted newest-first normalized result. For an accepted explicit detailed acquisition, the detailed call-log window and usage-statistics calculation SHALL consume that explicit load's normalized result under the existing call-log product contract. All five current codec call-log adapters SHALL preserve/use the same model-neutral chronology and record semantics in both acquisition types.

Because preview and detailed opening are distinct acquisition epochs, their accepted datasets MAY differ when device history changes between reads. Such difference SHALL NOT be treated as parser divergence when both snapshots were independently normalized under the same chronology/schema contract. Presentation SHALL NOT force the detailed load back to the older automatic-preview snapshot merely to make both surfaces identical.

If an acquisition/normalization cannot prove records, that acquisition's result is unavailable/empty rather than fabricated. Safe display timestamp text may remain present for a record whose typed chronology is unavailable, but that text SHALL NOT promote the record ahead of timestamped records or become sorting authority. A stale/cancelled/superseded acquisition result SHALL NOT become authority for another acquisition epoch or replacement row/context.

#### Scenario: Preview and detailed opening use one normalization authority but separate accepted snapshots

- **GIVEN** an automatic preview has accepted normalized call history for a current exact codec row
- **WHEN** the operator later explicitly opens the detailed journal and a fresh call-log acquisition is accepted
- **THEN** preview remains derived from the automatic-preview snapshot
- **AND** detailed rows/statistics derive from the fresh explicit snapshot
- **AND** both snapshots use the same application-owned record schema, exact-model normalizer, and newest-first chronology rules
- **AND** no second GUI parser or chronology implementation exists

#### Scenario: Device history changes between preview and explicit opening

- **GIVEN** device call history changes after automatic preview was accepted
- **WHEN** a later fresh explicit detailed acquisition is accepted
- **THEN** the detailed snapshot MAY contain newer or otherwise different accepted records than the preview snapshot
- **AND** the implementation does not overwrite the fresh detailed result with the older preview solely to force dataset identity
- **AND** both datasets remain comparable under the same normalized semantics

#### Scenario: Missing timestamp does not become newest

- **GIVEN** accepted normalized call records include records with typed `start_at` and one record with only unparseable/missing chronology
- **WHEN** ordering is established for either automatic preview or fresh detailed acquisition
- **THEN** all records with proven timestamps are ordered newest-first ahead of the unknown-chronology record
- **AND** no display-string sort or guessed timestamp is used

#### Scenario: Stale acquisition does not cross epochs

- **GIVEN** a preview or explicit detailed call-log acquisition loses exact row/generation/currentness before acceptance
- **WHEN** its late normalized result arrives
- **THEN** that result does not become authority for the other acquisition epoch or a replacement row/context
- **AND** no GUI cache promotes it to current call-history state

### Requirement: Modern room codec speaker volume exposes accepted display percentage without replacing mutation authority

For exact modern room codec presentation, the application/model-neutral projection SHALL expose an optional accepted field equivalent to:

```text
speaker_volume_percent: Optional[int]
```

When present, `speaker_volume_percent` SHALL be an integer in the inclusive range `0..100` and SHALL represent current accepted exact-row speaker-volume evidence mapped by the normative application-owned conversion below. It is display-only accepted evidence and SHALL NOT become mutation authority.

The existing unified exact-model registry remains the sole source of the canonical speaker range. Current approved baseline ranges are:

```text
Huawei TE20          minimum=0   maximum=21
Huawei TE40          minimum=0   maximum=21
CloudLink Bar 310    minimum=0   maximum=15
CloudLink Box 310    minimum=0   maximum=15
Polycom RPG 310      minimum=0   maximum=100
```

For accepted numeric speaker volume `V`, registry minimum `MIN`, and registry maximum `MAX`, the application projection SHALL calculate percentage only when `MAX > MIN` and `MIN <= V <= MAX`:

```text
scaled  = 100 * (V - MIN) / (MAX - MIN)
percent = floor(scaled + 0.5)
```

This is nearest-integer rounding with half values rounded upward for this non-negative closed range. The application SHALL NOT clamp an out-of-range source value into the display range. Out-of-range, malformed, stale, or missing speaker evidence SHALL produce no accepted `speaker_volume_percent`.

The conversion SHALL live in the exact-model adapter/application projection or another application-owned normalization boundary using the existing unified registry. Presentation SHALL NOT maintain a second model-range table, infer min/max from runtime observations, parse localized strings, perform its own conversion, or use widget state/history/defaults.

Current acceptance oracles SHALL include:

```text
Huawei TE20 / TE40
  0  -> 0%
  10 -> 48%
  21 -> 100%

CloudLink Bar 310 / CloudLink Box 310
  0  -> 0%
  7  -> 47%
  15 -> 100%

Polycom RPG 310
  0   -> 0%
  42  -> 42%
  100 -> 100%
```

If current remote source changes any of these approved baseline registry bounds before implementation, implementation SHALL stop and return for architecture review rather than silently adopting a different user-visible percentage scale.

The existing canonical/model-specific speaker volume used to create safe mutation targets and reconcile final state SHALL remain separate authority. `speaker_volume_percent` SHALL NOT be reverse-converted by presentation into a wire target, SHALL NOT make a requested-but-unreconciled target final state, and SHALL NOT authorize an operation unsupported by unified capability authority.

A successful send/ACK SHALL NOT update accepted `speaker_volume_percent` by itself. The displayed accepted percentage MAY change only when current exact-row application state accepts authoritative status/reconciliation evidence under `room-device-interaction-lifecycle`.

#### Scenario: Accepted zero is authoritative zero percent

- **GIVEN** current accepted speaker volume equals exact registry minimum zero
- **WHEN** the application publishes modern room codec presentation state
- **THEN** `speaker_volume_percent` is present as `0`
- **AND** presentation can distinguish it from missing data

#### Scenario: Bar or Box maximum maps to one hundred percent

- **GIVEN** exact model is `CloudLink Bar 310` or `CloudLink Box 310`
- **AND** current accepted speaker volume is `15`
- **WHEN** application projection uses the approved `0..15` registry range
- **THEN** `speaker_volume_percent` is `100`
- **AND** it is not displayed as `15%`

#### Scenario: TE intermediate value uses approved deterministic rounding

- **GIVEN** exact model is `Huawei TE20` or `Huawei TE40`
- **AND** current accepted speaker volume is `10`
- **WHEN** application projection uses the approved `0..21` range
- **THEN** `speaker_volume_percent` is `48`

#### Scenario: Source is outside approved registry range

- **GIVEN** accepted source evidence cannot be validated inside the exact model's approved registry bounds
- **WHEN** presentation projection is built
- **THEN** `speaker_volume_percent` is absent
- **AND** no clamp, guessed range, or stale widget value is substituted

#### Scenario: Mutation request has not reconciled

- **GIVEN** an admitted speaker-volume mutation requested a new target
- **AND** authoritative reconciliation has not yet accepted final state
- **WHEN** presentation state is published
- **THEN** the requested target alone does not become accepted `speaker_volume_percent`
- **AND** prior accepted state remains prior/stale according to the room lifecycle until reconciliation resolves the operation

### Requirement: Huawei TE50 is an exact-model reuse of the approved TE40 contract

`Huawei TE50` is an explicitly admitted exact application model in this change. By the product requirement's declared protocol equivalence, it SHALL reuse every approved TE40 protocol, capability, parser/normalization, presentation, call-log, Local Refresh, and currentness/cleanup contract covered by this change, including `WEB_GetCurrentAudioParam`, current-audio JSON-string decoding, explicit `MicValueIndex`/`mic<N>ValueIndex`/`micArray<N>_<NN>ValIdx`/`rcaLInValueIndex`/`rcaRInValueIndex` aggregation, `0..220 -> 0..100%` microphone LIVE normalization, MIC1 configured gain/mutation, mute, speaker, camera, and lifecycle behavior.

This is exact-model registration reuse, not substring/family inference: `Huawei TE50` SHALL remain distinguishable from `Huawei TE40` in model resolution and operation context while reusing its approved implementation boundary. TE40 protocol evidence is hardware-backed; TE50 admission is based on declared product equivalence and requires exact-SHA TE50 hardware acceptance before that equivalence is treated as hardware-proven. `Huawei TE30` and `Huawei TE60` remain out of scope and SHALL NOT be inferred from this requirement.

#### Scenario: TE50 reuses the approved TE40 contract without widening the family

- **GIVEN** exact model resolution yields `Huawei TE50`
- **WHEN** a function covered by this change is composed
- **THEN** TE50 receives the corresponding approved TE40 behavior under exact TE50 identity
- **AND** `Huawei TE30` and `Huawei TE60` receive no capability merely from this reuse declaration
- **AND** TE50 hardware acceptance remains pending until tested on the exact implementation SHA

### Requirement: TE40 current-audio microphone LIVE aggregates hardware-backed microphone evidence

For exact `Huawei TE40`, and exact-model `Huawei TE50` through the declared TE40 reuse contract, both one-shot `WEB_GetCurrentAudioParam` evidence used to seed `monitor_mic_value` and true periodic `get_live_audio_status` evidence SHALL use the same exact-model current-audio microphone extractor. The approved TE40/TE50 microphone-level authority is `WEB_GetCurrentAudioParam`; `WEB_GetMonitorAudioParam` SHALL NOT remain a co-authority for either initial seed or true LIVE without separate hardware-backed contract evidence.

The successful current-audio response has the outer envelope `{ "success": 1, "data": "<JSON string>" }`; when `data` is a JSON string, the exact-model boundary SHALL decode it to an object before extraction. The extractor SHALL collect valid microphone candidates from present compatibility `MicValueIndex`, every present field whose name exactly matches `^mic\d+ValueIndex$`, every present field whose name exactly matches `^micArray\d+_\d+ValIdx$`, and exactly the named RCA input fields `rcaLInValueIndex` and `rcaRInValueIndex`. A valid candidate is finite numeric evidence; booleans, null, malformed values, non-numeric strings, lists, objects, `NaN`, and infinities SHALL NOT be numeric candidates. The raw microphone level for the single room meter SHALL be `max(all valid microphone candidates)`. This is an application aggregation contract derived from observed TE40 telemetry; it does not assert that Huawei documents those fields as one vendor max-meter.

If there is no valid candidate, the microphone LIVE sample is unavailable and presentation SHALL render `Нет данных`, not observed zero. A valid candidate of numeric `0` is observed zero/silence. After aggregation, the existing TE40 Huawei monitor-audio normalization SHALL map raw `0..220` to `0..100%` exactly once and clamp only the presentation result according to its existing helper. `SpeakerValueIndex` SHALL NOT participate in the microphone aggregate or create a speaker LIVE capability. No wildcard `*InValueIndex` admission is authorized: all `trs*`, `hdmi*`, `dvi*`, `dp*`, `pstnInValueIndex`, `sdi*`, unrelated inputs, and `SpeakerValueIndex` remain excluded.

The initial one-shot seed has lower authority than an accepted true LIVE sample, but both use this same extractor/aggregation contract. Exact `Huawei TE20` retains its existing `MicValueIndex`-only contract and SHALL NOT infer `micArray...` or RCA input support from this TE40/TE50 evidence.

#### Scenario: TE40 current-audio authority serves initial seed and true LIVE

- **GIVEN** exact current model is `Huawei TE40`
- **WHEN** initial microphone seed or periodic true LIVE needs microphone-level evidence
- **THEN** the exact-model source is `WEB_GetCurrentAudioParam`
- **AND** the two paths use the same extractor
- **AND** `WEB_GetMonitorAudioParam` is not a co-authority for those TE40 microphone samples

#### Scenario: TE40 current-audio JSON string is decoded before extraction

- **GIVEN** `WEB_GetCurrentAudioParam` succeeds with `data` containing a JSON string object
- **WHEN** TE40 exact-model current-audio normalization runs
- **THEN** it decodes the string before selecting microphone candidates

#### Scenario: TE40 MicValueIndex remains a valid sole microphone candidate

- **GIVEN** a TE40 current-audio payload has valid `MicValueIndex = 41` and no valid matching individual or array field
- **WHEN** exact-model microphone extraction runs
- **THEN** raw microphone level is `41`

#### Scenario: TE40 individual microphone evidence supplies a level

- **GIVEN** a TE40 current-audio payload has `mic1ValueIndex = 37` and no greater valid microphone candidate
- **WHEN** exact-model microphone extraction runs
- **THEN** raw microphone level is `37`

#### Scenario: TE40 array evidence supplies microphone level when MicValueIndex is absent

- **GIVEN** a TE40 current-audio payload lacks `MicValueIndex` and has `micArray1_01ValIdx = 17`, `micArray1_02ValIdx = 83`, and `micArray1_03ValIdx = 41`
- **WHEN** exact-model microphone extraction runs
- **THEN** raw microphone level is `83`

#### Scenario: TE40 individual microphone values aggregate by maximum

- **GIVEN** a TE40 current-audio payload has valid `mic1ValueIndex = 37` and `mic2ValueIndex = 41`
- **WHEN** exact-model microphone extraction runs
- **THEN** raw microphone level is `41`

#### Scenario: TE40 multiple microphone arrays aggregate by maximum

- **GIVEN** a TE40 current-audio payload has valid `micArray1_03ValIdx = 37` and `micArray2_02ValIdx = 83`
- **WHEN** exact-model microphone extraction runs
- **THEN** raw microphone level is `83`

#### Scenario: TE40 aggregate retains the maximum across compatibility, individual, and array evidence

- **GIVEN** a TE40 current-audio payload has `MicValueIndex = 20`, `mic1ValueIndex = 37`, and `micArray1_01ValIdx = 70`
- **WHEN** exact-model microphone extraction runs
- **THEN** raw microphone level is `70`

#### Scenario: TE40 real individual and array evidence aggregates to the observed maximum

- **GIVEN** a decoded TE40 current-audio payload has `mic1ValueIndex = 37`, `micArray1_01ValIdx = 25`, `micArray1_02ValIdx = 12`, and `micArray1_03ValIdx = 37`
- **WHEN** exact-model microphone extraction runs
- **THEN** raw microphone level is `37`
- **AND** existing `0..220 -> 0..100%` presentation normalization produces its existing rounded approximately `17%` fill

#### Scenario: TE40 malformed microphone evidence is ignored

- **GIVEN** a TE40 current-audio payload has valid `micArray1_01ValIdx = 31` alongside matching individual/array fields that are null, boolean, malformed, infinite, or non-numeric strings
- **WHEN** exact-model microphone extraction runs
- **THEN** only valid finite numeric candidates participate
- **AND** raw microphone level is `31`

#### Scenario: TE40 unrelated audio inputs are excluded

- **GIVEN** a TE40 current-audio payload has valid `MicValueIndex = 20` and greater numeric `trs*`, unrelated `rca*`, `hdmi*`, `dvi*`, `dp*`, `pstn*`, or `sdi*` fields
- **WHEN** exact-model microphone extraction runs
- **THEN** raw microphone level remains `20`

#### Scenario: TE40 has no valid microphone candidate

- **GIVEN** a TE40 current-audio payload has no valid compatibility, individual, or array candidate
- **WHEN** exact-model microphone extraction runs
- **THEN** microphone LIVE is unavailable
- **AND** presentation renders `Нет данных` rather than numeric zero

#### Scenario: TE40 observed zero remains valid microphone evidence

- **GIVEN** a TE40 current-audio payload has a valid microphone candidate of numeric `0`
- **WHEN** exact-model microphone extraction runs
- **THEN** the raw microphone level is observed numeric `0`
- **AND** the normalized meter is available at `0%`

#### Scenario: TE40 RCA inputs contribute to the microphone aggregate

- **GIVEN** a TE40 current-audio payload has valid `mic1ValueIndex = 37`, `rcaLInValueIndex = 62`, and `rcaRInValueIndex = 0`
- **WHEN** exact-model microphone extraction runs
- **THEN** raw microphone level is `62`

#### Scenario: TE40 silent RCA inputs do not override a microphone candidate

- **GIVEN** a TE40 current-audio payload has valid `mic1ValueIndex = 37`, `rcaLInValueIndex = 0`, and `rcaRInValueIndex = 0`
- **WHEN** exact-model microphone extraction runs
- **THEN** raw microphone level is `37`

#### Scenario: TE40 RCA input supplies microphone evidence when microphone fields are absent

- **GIVEN** a TE40 current-audio payload has no valid compatibility, individual, or array candidate and has valid `rcaLInValueIndex = 42`
- **WHEN** exact-model microphone extraction runs
- **THEN** raw microphone level is `42`

#### Scenario: TE40 RCA numeric zero remains valid microphone evidence

- **GIVEN** a TE40 current-audio payload has no other valid candidate and has valid `rcaLInValueIndex = 0` and `rcaRInValueIndex = 0`
- **WHEN** exact-model microphone extraction runs
- **THEN** the raw microphone level is observed numeric `0`
- **AND** the normalized meter is available at `0%`

#### Scenario: TE40 excluded high inputs do not contaminate the RCA aggregate

- **GIVEN** a TE40 current-audio payload has valid `mic1ValueIndex = 37`, invalid `rcaLInValueIndex` or `rcaRInValueIndex` evidence, and valid `trs*`, `hdmi*`, or `sdi*` input evidence of `220`
- **WHEN** exact-model microphone extraction runs
- **THEN** invalid RCA and excluded inputs do not participate
- **AND** raw microphone level remains `37`

#### Scenario: TE50 reuses the exact TE40 RCA aggregate

- **GIVEN** exact current model is `Huawei TE50` and its current-audio payload has valid `mic1ValueIndex = 37`, `rcaLInValueIndex = 62`, and `rcaRInValueIndex = 0`
- **WHEN** exact-model microphone extraction runs
- **THEN** raw microphone level is `62` under the same TE40 aggregation and normalization contract

#### Scenario: TE40 speaker evidence does not affect microphone aggregate

- **GIVEN** a TE40 current-audio payload has valid `MicValueIndex = 20` and `SpeakerValueIndex = 220`
- **WHEN** exact-model microphone extraction runs
- **THEN** raw microphone level remains `20`
- **AND** no user-visible speaker LIVE meter is created

#### Scenario: TE40 initial seed and true LIVE share one extractor

- **GIVEN** equivalent TE40 one-shot and true LIVE current-audio payloads contain matching valid compatibility, individual, and array evidence
- **WHEN** each path extracts microphone level
- **THEN** each produces the same raw aggregate and normalization result
- **AND** accepted true LIVE takes precedence over the initial seed

#### Scenario: TE20 current contract is unchanged

- **GIVEN** exact current model is `Huawei TE20`
- **WHEN** it obtains initial or LIVE microphone evidence
- **THEN** its existing `MicValueIndex`-only source and extraction contract remains unchanged
- **AND** TE40 individual/array fields and `rcaLInValueIndex`/`rcaRInValueIndex` are not promoted into TE20 evidence

### Requirement: TE40 static status publishes canonical room evidence without additional I/O

The existing TE40 initial diagnostic snapshot SHALL publish canonical `microphone_status` from rich `mic_connection_status`, canonical `camera_status` from rich `camera_connection_status`, and canonical `uptime` from the already-read `runDay`/`runHour`/`runMin` presentation value when present. These fields remain distinct from microphone mute and require no additional request or polling.

Present numeric `mic1Value` is the authoritative configured-primary-gain source for `mic_volume`. Historical `micValue` may be used only as a compatibility fallback when `mic1Value` is absent; it SHALL not override present MIC1 evidence.

#### Scenario: TE40 initial snapshot preserves rich state and MIC1 gain

- **GIVEN** the existing initial TE40 diagnostic result contains rich microphone/camera connection evidence, `mic1Value = 18`, and formatted uptime `12 дней 4 часов 37 минут`
- **WHEN** exact parser normalization completes
- **THEN** canonical microphone status, camera status, uptime, and configured microphone volume `18` are available to room presentation
- **AND** no extra status request or uptime polling starts

### Requirement: TE40 MIC1 gain and mute evidence are independent read authorities

For exact `Huawei TE40`, static audio normalization SHALL preserve numeric microphone configuration evidence independently from mute evidence.

When the approved TE40 audio-status parser receives a present finite numeric `mic1Value` in wire domain `0..24`, the accepted room snapshot SHALL publish canonical numeric `microphone_volume` from that MIC1 value. Historical `micValue` MAY be a compatibility fallback only when `mic1Value` is absent; present `mic1Value` SHALL NOT be overridden by `micValue`. When authoritative `MicSwitch` or equivalent approved mute evidence is present, the same snapshot SHALL independently publish canonical `microphone_muted`.

For presentation and typed gain intent, TE40 SHALL use `gain_db = microphone_volume - 12`. Thus wire value `24` is `+12 dB`, `21` is `+9 dB`, `18` is `+6 dB`, and `0` is `-12 dB`.

A numeric value, including `0`, SHALL NOT be interpreted as mute evidence. Mute state SHALL NOT overwrite numeric gain evidence, and numeric gain evidence SHALL NOT overwrite mute state.

#### Scenario: TE40 static audio contains MIC1 gain and unmuted state

- **GIVEN** TE40 audio status contains numeric `mic1Value = 18`
- **AND** independent authoritative mute evidence says unmuted
- **WHEN** the room snapshot is accepted
- **THEN** `microphone_volume` is numeric `18`
- **AND** the model-specific display value is `+6 dB`
- **AND** `microphone_muted` is `false`
- **AND** neither value is derived from the other

#### Scenario: TE40 MIC1 zero is not mute authority

- **GIVEN** TE40 audio status contains numeric `mic1Value = 0`
- **AND** independent authoritative mute evidence says unmuted
- **WHEN** the room snapshot is accepted
- **THEN** `microphone_volume` remains numeric `0`
- **AND** its configured gain meaning is `-12 dB`
- **AND** `microphone_muted` remains `false`
- **AND** the application does not fabricate a muted state from the numeric value

#### Scenario: Present MIC1 gain wins over historical compatibility field

- **GIVEN** TE40 audio status contains `mic1Value = 18` and `micValue = 12`
- **WHEN** the room snapshot is accepted
- **THEN** `microphone_volume` remains numeric `18`
- **AND** the model-specific display value is `+6 dB`

#### Scenario: Historical micValue is fallback only when MIC1 is absent

- **GIVEN** TE40 audio status has no `mic1Value` and contains numeric `micValue = 18`
- **WHEN** the room snapshot is accepted
- **THEN** compatibility fallback may publish numeric `microphone_volume = 18`

### Requirement: TE40 microphone-gain mutation uses fresh full-state save and reconciliation

For exact `Huawei TE40`, room `microphone_adjust` SHALL control primary `MIC1` configured input gain only. Each operator `-` / `+` intent changes configured gain by exactly `1 dB`, clamped to `-12 dB .. +12 dB`, equivalent to wire target `0..24` step `1`.

The state-changing transport boundary is:

```text
POST action.cgi?ActionID=WEB_SaveAudioMicCtrlParams
```

A previously accepted room snapshot SHALL NOT be used as full-state save authority.

After the exact MUTATION owns the serialized room interaction lane and prior LIVE has retired through bounded cleanup, the mutation SHALL first perform a **fresh full TE40 audio-control read** through `WEB_InitAudioCtrlParamsAPI` using the approved exact-row/session context. An already-approved equivalent read MAY be used only if it returns the same complete mutation-required state.

The fresh mutation-local pre-write state SHALL include all non-secret save-state fields required by the native full-state payload:

```text
micall
mic1 .. mic18
mic1Value .. mic18Value
```

If that fresh state is missing, malformed, stale, not current for the exact row/generation, or lacks any required field, the save command SHALL NOT be submitted. This is a definite pre-submit failure: it SHALL NOT set `unconfirmed_after_command` or stale-due-command merely because the fresh read failed. Existing typed auth/session/connection failure rules still apply independently.

The outgoing save payload SHALL be constructed exclusively from that fresh pre-write state plus current required secret session/CSRF material. For a MIC1 gain intent, only target `mic1Value` may differ from the fresh baseline. Non-target `micall`, `micN`, and `micNValue` fields SHALL NOT come from older cache, GUI state, guessed defaults, zeros, or another model.

The mapping is:

```text
wire mic1Value = requested gain_db + 12
requested gain_db = wire mic1Value - 12
```

A successful response such as `{"success":1,"data":""}` is acknowledgement only.

After one accepted submit, reconciliation SHALL perform a fresh full audio-control read from the same approved authority. Final success requires all of:

```text
current exact row / room generation / operation currentness still matches
MIC1 target equals requested wire value
all preserved non-target micall / micN / micNValue fields equal the fresh pre-write baseline
```

The approved canonical `microphone_volume` projection MAY confirm the MIC1 target, but target confirmation does not substitute for collateral-state comparison. If the post-write read cannot expose sufficient full state to compare the preserved fields, success SHALL NOT be declared.

Missing/malformed/mismatched/stale readback, collateral mismatch, ambiguous send outcome, or cancellation after possible send SHALL follow the root blocked/unconfirmed mutation contract; no blind replay is permitted.

Microphone mute remains a separate desired-state operation and SHALL NOT change as a side effect of gain adjustment.

#### Scenario: TE40 gain plus uses a fresh full-state baseline

- **GIVEN** exact TE40 currently has accepted room `microphone_volume = 18`
- **WHEN** the operator confirms one microphone gain `+`
- **THEN** MUTATION first retires LIVE and obtains fresh full audio-control state
- **AND** the typed target is wire `mic1Value = 19`
- **AND** the outgoing full-state save is built only from that fresh baseline
- **AND** only target `mic1Value` differs from the fresh baseline

#### Scenario: TE40 fresh pre-write state is unavailable

- **GIVEN** a TE40 gain mutation owns the lane but fresh full audio-control state cannot be obtained completely
- **WHEN** mutation preparation evaluates the save
- **THEN** `WEB_SaveAudioMicCtrlParams` is not submitted
- **AND** no command ambiguity is created solely by that pre-submit failure
- **AND** bounded cleanup releases the lane subject to independent typed session/connection failure rules

#### Scenario: TE40 gain acknowledgement is not final authority

- **GIVEN** `WEB_SaveAudioMicCtrlParams` returns a successful acknowledgement
- **WHEN** mandatory post-write full-state read is missing, malformed, stale, or target MIC1 does not equal the requested target
- **THEN** requested gain is not published as confirmed
- **AND** root blocked/unconfirmed mutation safety applies
- **AND** the command is not blindly repeated

#### Scenario: TE40 collateral microphone state changed

- **GIVEN** fresh pre-write state records non-target microphone fields
- **AND** one gain save may have been delivered
- **WHEN** post-write full-state reconciliation shows any preserved non-target `micall`, `micN`, or `micNValue` field differs from that fresh baseline
- **THEN** the MIC1 mutation is not declared fully confirmed
- **AND** the row enters root blocked/unconfirmed state
- **AND** the application does not silently accept or replay the command

#### Scenario: TE40 gain minus at lower bound is local no-op

- **GIVEN** exact TE40 has current accepted `microphone_volume = 0`, equivalent to `-12 dB`
- **WHEN** the operator requests one microphone gain `-`
- **THEN** no below-range target is constructed
- **AND** no mutation/session/device I/O is started solely for that no-op
- **AND** mute state remains unchanged

#### Scenario: TE40 gain plus at upper bound is local no-op

- **GIVEN** exact TE40 has current accepted `microphone_volume = 24`, equivalent to `+12 dB`
- **WHEN** the operator requests one microphone gain `+`
- **THEN** no above-range target is constructed
- **AND** no mutation/session/device I/O is started solely for that no-op
- **AND** mute state remains unchanged

### Requirement: TE40 camera normalization accepts zero-to-many camera records

For exact `Huawei TE40`, `WEB_GetLocalCameraList.itemList` or its approved equivalent SHALL be treated as a zero-to-many collection. The parser SHALL NOT require at least two entries before processing camera evidence.

Each present entry SHALL be interpreted independently. An active camera MAY use the existing approved port/type lookup to resolve model evidence. A valid single returned camera SHALL publish known camera status/model evidence when available and SHALL NOT become `Нет данных` solely because a second list entry is absent.

#### Scenario: TE40 returns exactly one camera record

- **GIVEN** TE40 camera-list data contains exactly one valid camera entry
- **WHEN** exact-model camera normalization runs
- **THEN** that entry is processed
- **AND** available camera state/model evidence is published
- **AND** the parser does not require `len(itemList) >= 2`

### Requirement: CloudLink Box 310 post-cycle microphone LIVE is deferred and unavailable in this change

Current authorized Bar 310 evidence belongs to Bar and SHALL NOT be used as a Box parser contract. Earlier Box hardware evidence is insufficient to define a complete LIVE parser. Therefore this change explicitly removes Box microphone LIVE from its implementation/acceptance scope rather than asking implementation to choose envelope, roles, aggregation, or normalization.

The unified exact-model registration for `CloudLink Box 310` SHALL advertise no post-cycle LIVE binding. Room interaction SHALL perform zero Box microphone LIVE polling, including zero `WEB_GetCurrentAudioParam` requests admitted as LIVE. Exact Box identity and all approved non-LIVE capabilities remain unchanged.

A future reviewed Box LIVE restoration change is required before this capability may become supported. That future change must establish response envelope/container, microphone record selection/device-role semantics, numeric validity, aggregation, normalization, unavailable/error semantics, lifecycle currentness, and exact Box identity.

Earlier `{deviceId, curVolume}` observations remain discovery evidence only. No `max(all curVolume)` rule is approved here. The current Bar fixed-field `mic*ValueIndex` schema is not Box evidence.

#### Scenario: Box registration has no LIVE binding

- **GIVEN** exact model is `CloudLink Box 310`
- **WHEN** unified room capabilities are composed
- **THEN** no post-cycle LIVE binding is advertised
- **AND** shared `CloudLinkBar310Handler` type does not promote Box LIVE
- **AND** no Box room LIVE request is admitted

#### Scenario: Box non-LIVE interaction remains supported where separately approved

- **GIVEN** exact model is `CloudLink Box 310`
- **WHEN** diagnostics, speaker control, call-log preview/detail, or Local Refresh use their existing approved capabilities
- **THEN** those operations remain available under their own exact-row lifecycle contracts
- **AND** absence of Box LIVE does not relabel the model as Bar 310

#### Scenario: Future Box LIVE needs a new reviewed contract

- **WHEN** a later change proposes to re-enable Box microphone LIVE
- **THEN** it cannot infer the parser from Bar fields or the earlier pair shape alone
- **AND** it must supply the complete transport-edge to normalized-meter contract before capability is advertised

### Requirement: IN1804 documented wire identities preserve the canonical profile

The Matrix identity resolver SHALL map only the documented IN1804-series `1I`
responses `IN1804`, `IN1804 DI`, `IN1804 DO`, and `IN1804 DI/DO` to the
canonical `IN1804` protocol profile and application model `Extron IN1804`.
The resolver SHALL reject unlisted aliases, suffixes, and unrelated identities;
it SHALL NOT use an IN1804 substring rule. Exact leading command echo removal
already provided by the Matrix transport MAY precede this closed resolution.

Expected-model validation SHALL compare canonical resolved profile identity.
Thus an expected `Extron IN1804` accepts a documented IN1804 wire alias, while
an actual `IN1808` identity remains a fail-closed mismatch. DTP exact identity/part-number resolution remains active; historical XTP/XTP II identity resolution is non-dispatched and does not create supported runtime authority.

#### Scenario: IN1804 DI/DO full refresh remains compatible

- **GIVEN** inventory expects `Extron IN1804`
- **AND** the device returns `IN1804 DI/DO` to `1I`
- **WHEN** the normal Matrix full-refresh path runs
- **THEN** it uses the canonical IN1804 profile
- **AND** it produces a normalized four-input, one-logical-output snapshot
- **AND** the accepted snapshot can be presented by the standalone and room Matrix surfaces

#### Scenario: Near-looking identity remains unsupported

- **WHEN** an IN-family wire identity is not one of the documented IN1804 aliases
- **THEN** it is not promoted by substring similarity

### Requirement: IN1808 aliases and legacy IN1804 HDCP remain canonical

Only documented IN1808 `1I` identities may resolve to canonical `IN1808`; all
other suffixes fail closed. The Matrix parser SHALL convert legacy IN1804
list-shaped input HDCP/auth and scalar output HDCP evidence into canonical
per-input/per-output state before GUI presentation.

#### Scenario: Legacy IN1804 HDCP evidence reaches presentation

- **WHEN** IN1804 provides list input HDCP/auth and scalar output HDCP evidence
- **THEN** the normalized snapshot retains each supported input and output value
- **AND** the GUI consumes canonical state rather than legacy shapes

### Requirement: Matrix SIS identity framing is command-specific and closed

The identity path SHALL apply exact transport command-echo removal, then only
the documented grammar for the issued identity command, then closed canonical
resolution, then canonical expected-model comparison. `1I` accepts only a bare
model identity or `Inf01*<model identity>`; `N` accepts only a bare exact part
number or `Pno<exact part number>`. `Pno` SHALL NOT be accepted as model
evidence and `Inf01*` SHALL NOT be accepted as part-number evidence.

#### Scenario: Tagged identity evidence remains command-specific

- **WHEN** `1I` returns `Pno60-1381-01` or `N` returns `Inf01*IN1808`
- **THEN** neither response resolves a Matrix profile
- **AND** the diagnostic fails closed without profile guessing

Unknown values, trailing garbage, multiple identity records, and expected-model
mismatches SHALL fail closed. DTP CP84 retains its documented `I` token and DTP 4K retains exact `N` part-number authority. Historical XTP/XTP II `N` parsing may remain only as non-dispatched evidence and SHALL NOT trigger downstream production topology discovery. The exact hardware-proven `IN1608 xi IPCP SA`
`1I` identity SHALL resolve to canonical `IN1608 xi`; other IN1608 xi aliases remain
closed unless separately approved. Exact DTP CrossPoint 108 4K part number
`60-1381-12` SHALL resolve to its existing canonical profile without enabling any
`60-1381-*` wildcard. IN1806 SHALL resolve as canonical `Extron IN1806` from exact
`IN1806` identity and exact part number `60-1663-01` where part-number evidence is used.

### Requirement: Room Matrix identity selection preserves exact diagnostic-model authority

The room one-shot Matrix path SHALL pass its exact canonical `diagnostic_model`
to the Matrix worker and then to the handler as `expected_model`. The worker
SHALL select the resulting exact profile before its first authoritative identity
read. It SHALL use model-aware connection status text; callers without an
expected model SHALL receive a neutral Matrix label rather than an IN1804 claim.

#### Scenario: DTP CrossPoint 86 4K room path starts with N

- **GIVEN** the room diagnostic model is `Extron DTP CrossPoint 86 4K`
- **WHEN** the room worker begins its handler refresh
- **THEN** the first authoritative identity command is `N`
- **AND** it is not `1I`
- **AND** the expected DTP profile is preserved through the worker/handler boundary

#### Scenario: Supported IN identity generation remains explicit

- **WHEN** the room diagnostic model is `Extron IN1608 xi` or `Extron IN1806`
- **THEN** its first authoritative identity command is `1I`
- **WHEN** evidence instead identifies deferred XTP/XTP II
- **THEN** no production Matrix identity/polling session starts for that deferred model

#### Scenario: Hardware-proven exact identities remain closed

- **WHEN** `Extron IN1608 xi` returns `IN1608 xi IPCP SA` to `1I`
- **THEN** it resolves to canonical `IN1608 xi`
- **WHEN** `Extron DTP CrossPoint 108 4K` returns `60-1381-12` to `N`
- **THEN** it resolves to canonical `DTP CrossPoint 108 4K`
- **AND** an unlisted adjacent suffix is not accepted by prefix or wildcard inference

#### Scenario: IN1806 remains distinct from IN1808

- **WHEN** the expected model is `Extron IN1806` and `1I` returns exact `IN1806`
- **THEN** the six-input IN1806 profile is selected
- **AND** inputs `7` and `8` are not fabricated from IN1808
- **AND** exact part number `60-1663-01` is consistent with the IN1806 profile

### Requirement: Hardware acquisition and GUI presentation are separate Matrix QA gates

Read-only hardware acquisition evidence SHALL NOT by itself claim presentation
success, and synthetic GUI coverage SHALL NOT claim hardware observation. The
recorded IN1804 and IN1808 evidence proves temperature, input-HDCP, signal, and
route reads only; neither device observed a positive `PRESENT_HDCP` input. The
DTP CrossPoint 86 4K wrong fallback path observed `1I` and `DTPCP86`; the
software propagation correction requires a post-fix hardware retest beginning
with `N` after authentication.

#### Scenario: Synthetic positive HDCP does not claim hardware observation

- **GIVEN** GUI regression uses a synthetic `PRESENT_HDCP` state
- **WHEN** software presentation validation passes
- **THEN** active-HDCP hardware evidence remains recorded as not exercised
- **AND** post-remediation hardware retest remains required

### Requirement: Complete Matrix full refresh requires authoritative General-information evidence

For every exact Extron Matrix model remaining in production-supported scope, a complete successful full refresh SHALL establish current authoritative model, MAC address, serial number, firmware version, and temperature.

Model authority is exact accepted device identity/canonical profile. MAC and serial are mandatory current canonical inventory evidence; this change has no device fallback for either. Firmware and temperature use only the approved exact-profile SIS commands from the design acquisition matrix.

A missing canonical MAC/serial, failed firmware/temperature read, malformed/stale evidence, or synthetic value keeps the refresh incomplete.

#### Scenario: Successful supported-Matrix refresh has complete General information
- **WHEN** a full refresh for an exact remaining supported Matrix model is accepted as complete successful
- **THEN** model, MAC, serial, firmware, and temperature are all authoritative current values
- **AND** none is missing, stale or synthetic

#### Scenario: Missing inventory identity data blocks complete success
- **GIVEN** the exact current Matrix inventory row lacks canonical MAC or serial
- **WHEN** a full refresh is attempted
- **THEN** no speculative device MAC/serial command is sent
- **AND** the refresh remains incomplete

#### Scenario: Deferred XTP does not claim supported completeness
- **WHEN** target identity resolves to first-generation XTP or XTP II
- **THEN** this change treats the profile as deferred/unsupported for production dispatch
- **AND** a partial historical handler result cannot be classified as a supported complete refresh
