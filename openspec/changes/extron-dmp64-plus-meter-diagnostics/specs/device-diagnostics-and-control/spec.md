## MODIFIED Requirements

### Requirement: Supported production device diagnostics
The application SHALL provide production GUI diagnostic paths for Huawei TE20,
Huawei TE40, CloudLink Bar 310, Polycom RPG 310, Extron IN1804, Aten
PE8208AV, Extron IPL T PCS4i, Biamp Tesira Forte CI, and Extron DMP 64 Plus
only where those devices are connected to the main-window dispatch. Each
diagnostic path SHALL obtain device data through its worker/handler path and
present parser-normalized or handler-normalized data on the corresponding
screen.

#### Scenario: Codec diagnostic refresh
- **WHEN** an operator refreshes a supported codec with a successful device response
- **THEN** the codec screen receives normalized diagnostic data including the target IP and available device status values

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

## ADDED Requirements

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
