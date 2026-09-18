## MODIFIED Requirements

### Requirement: Supported production device diagnostics
The application SHALL provide production GUI diagnostic paths for Huawei TE20,
Huawei TE40, CloudLink Bar 310, CloudLink Box 310, Polycom RPG 310, Extron
IN1804, Extron IN1808, Extron IN1608 xi, the approved DTP CrossPoint exact
model set, approved first-generation XTP CrossPoint frames, approved XTP II
CrossPoint frames, Aten PE8208AV, Extron IPL T PCS4i, Biamp Tesira Forte CI,
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

## ADDED Requirements

### Requirement: Matrix diagnostics use authoritative per-device capability profiles

The application SHALL collect Matrix diagnostics/control data through an approved profile selected from current exact device identity and, where required, installed-hardware evidence. A command unproven for the active profile SHALL NOT be sent merely because another Extron family supports a similar command.

For XTP/XTP II, exact frame identity/profile selection SHALL occur before profile-specific dimension/board decoding. Matrix dimensions alone SHALL NOT select the generation.

#### Scenario: Unknown model does not inherit a nearby profile
- **WHEN** an Extron device identity cannot be resolved exactly to an approved capability profile
- **THEN** the application does not silently select IN1804, IN1808, IN1608, approved-DTP, XTP, or XTP II behavior by nearest-looking substring
- **AND** unsupported diagnostics and route mutations remain unavailable

#### Scenario: Unproven diagnostic read is not guessed
- **WHEN** the selected profile has no authoritative command for a diagnostic field
- **THEN** the handler sends no speculative SIS command for that field
- **AND** normalized state represents the field as unavailable/unknown

### Requirement: Matrix routing authority is multi-output normalized state

Generalized Matrix routing authority SHALL be `routes[output_id] = input_id | untied/unknown` over authoritative logical outputs. Single-output compatibility projections MAY remain for legacy consumers, but multi-output devices SHALL NOT use one scalar current route as authority.

#### Scenario: Multiple outputs can route independently
- **GIVEN** available outputs `1`, `2`, `3`, and `4` with accepted routes `{1: 2, 2: 2, 3: 7, 4: None}`
- **WHEN** routing state is normalized
- **THEN** outputs `1` and `2` independently reference input `2`
- **AND** output `3` references input `7`
- **AND** output `4` remains explicitly untied/without a source

### Requirement: Matrix topology distinguishes logical routing from physical connectors

GUI route columns and route validation SHALL use authoritative available logical routing-output IDs, not raw physical connector count. Multiple physical connectors sharing one logical route SHALL produce one route endpoint.

#### Scenario: Duplicated physical connectors share one logical route
- **WHEN** a supported presentation switcher exposes multiple physical connectors driven by one logical main route
- **THEN** normalized topology contains one logical route output for that route
- **AND** GUI exposes one routing column rather than one per connector

### Requirement: XTP and XTP II topology is derived from exact identity plus read-only installed-hardware evidence

After exact generation/frame profile selection, XTP/XTP II SHALL combine authoritative matrix-dimension information with installed board-slot evidence to derive available logical IDs. State-changing route commands SHALL NOT be used for topology discovery. Empty slots SHALL preserve numbering gaps.

#### Scenario: Missing output board preserves logical IDs
- **GIVEN** an approved XTP/XTP II frame whose installed-board evidence shows outputs `13..16` absent and `17..20` installed
- **WHEN** topology is derived
- **THEN** outputs `13..16` are unavailable
- **AND** outputs `17..20` retain those exact IDs
- **AND** they are not compressed downward

### Requirement: Extron route commands are selected by approved profile

Approved profiles SHALL generate exact documented/hardware-confirmed route syntax: IN1804 `!` / `<I>*1!`; IN1808 `1!` / `<I>*1!`; IN1608 xi `!` / `<I>!`; approved CrossPoint `<O>!` / `<I>*<O>!` / untie `0*<O>!`.

#### Scenario: IN1808 route read targets main logical output
- **WHEN** the application reads current IN1808 main route
- **THEN** it sends `1!` before transport termination
- **AND** it does not use IN1804 bare `!`

#### Scenario: IN1608 mutation uses its own profile
- **WHEN** input `5` is selected on supported IN1608 xi
- **THEN** the command before transport termination is `5!`

#### Scenario: CrossPoint mutation addresses explicit output
- **WHEN** input `3` is routed to output `7` on an approved CrossPoint profile
- **THEN** the state-changing command before transport termination is `3*7!`

### Requirement: CrossPoint output HDCP commands remain family-specific

Approved DTP CrossPoint output-HDCP reads SHALL use `WO<N>HDCP`. First-generation XTP CrossPoint output-HDCP reads SHALL use `W0<N>HDCP`, and the all-outputs query SHALL use `W0*HDCP`. XTP II output-HDCP SHALL remain unavailable/UNPROVEN until an exact official command and decoder are approved.

#### Scenario: XTP does not reuse DTP output-HDCP syntax
- **WHEN** output HDCP is read on an approved first-generation XTP frame for output `4`
- **THEN** the handler generates `W04HDCP` before transport termination
- **AND** it does not generate DTP-form `WO4HDCP`

#### Scenario: Unproven XTP II output HDCP sends nothing
- **GIVEN** the XTP II profile has no approved output-HDCP command
- **WHEN** diagnostic collection reaches optional output-HDCP data
- **THEN** no speculative DTP or first-generation XTP command is sent
- **AND** output HDCP remains unavailable/unknown

### Requirement: Input HDCP status is normalized by profile-specific semantics

The active Matrix profile SHALL normalize raw input HDCP status according to its approved family semantics. IN1804/IN1808 SHALL map `0=absent, 1=present without HDCP, 2=present with HDCP`. IN1608 xi, approved DTP, XTP and XTP II SHALL map `0=absent, 1=HDCP-compliant/present, 2=non-compliant/absent`. HDCP authorization/configuration SHALL remain distinct from actual input HDCP status.

#### Scenario: Raw value 1 differs by generation
- **WHEN** raw input HDCP value `1` is received from IN1808
- **THEN** normalized state is `PRESENT_NO_HDCP`
- **WHEN** raw input HDCP value `1` is received from approved XTP
- **THEN** normalized state is `PRESENT_HDCP`

### Requirement: Matrix route mutation preserves existing ambiguity safety

Generalizing Matrix route mutation to explicit output IDs SHALL preserve the existing state-changing possible-send boundary: after a route may have been sent it SHALL NOT be blindly replayed, and confirmed success requires authoritative targeted-output reconciliation.

#### Scenario: Possible-send CrossPoint route is not replayed
- **WHEN** a CrossPoint route command may have reached the device but its response is lost
- **THEN** the command is not automatically replayed
- **AND** UI does not claim confirmed routing until authoritative reconciliation succeeds

## ADDED Requirements

### Requirement: IN1804 documented wire identities preserve the canonical profile

The Matrix identity resolver SHALL map only the documented IN1804-series `1I`
responses `IN1804`, `IN1804 DI`, `IN1804 DO`, and `IN1804 DI/DO` to the
canonical `IN1804` protocol profile and application model `Extron IN1804`.
The resolver SHALL reject unlisted aliases, suffixes, and unrelated identities;
it SHALL NOT use an IN1804 substring rule. Exact leading command echo removal
already provided by the Matrix transport MAY precede this closed resolution.

Expected-model validation SHALL compare canonical resolved profile identity.
Thus an expected `Extron IN1804` accepts a documented IN1804 wire alias, while
an actual `IN1808` identity remains a fail-closed mismatch. DTP, XTP, and XTP
II exact identity/part-number resolution remains unchanged.

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
