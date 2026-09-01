## ADDED Requirements

### Requirement: Extron IN1804 Matrix normalization is fail-closed for routing authority

The existing Extron IN1804 diagnostic path SHALL continue to use its current SIS read commands, but normalized Matrix evidence consumed by room presentation and route reconciliation SHALL distinguish confirmed values from missing, failed, malformed, unrecognized, or out-of-range evidence.

MIH-11 SHALL NOT add a new SIS query merely to satisfy this requirement. It SHALL correct only the handling/normalization of existing Matrix model/count, device-info model/temperature, connection, and input-HDCP-status reads.

#### Input count

`inputs_num` SHALL be accepted as a positive current Matrix input count only when existing model/capability evidence positively establishes that count. A constructor default, parser fallback, visual-reference row count, prior snapshot, or other convenience value SHALL NOT establish current accepted input authority.

On the current implementation path specifically, legacy defaults equivalent to `self.inputs_num = 8` and `data.get("inputs_num", 8)` SHALL NOT be published/consumed as authoritative count when model/count evidence is unproven. Unknown count SHALL remain absent/`None`/explicitly unknown according to the chosen normalized representation.

Per-input names/status arrays created only because of an unproven fallback count SHALL NOT make those ordinals actionable for room routing.

#### Device-info model and temperature

The General-information `model` and `temperature` values SHALL also preserve no-evidence semantics from the existing reads.

A model value is accepted only when the existing model read succeeds and yields a non-empty current device value. Missing/failed/unusable model evidence and local convenience sentinels such as `Unknown` SHALL normalize to absent/`None`; they SHALL NOT be presented as if reported by the device. Model recognition for input-count capability remains the stricter exact-model/capability decision above.

A temperature value is accepted only when the existing temperature read succeeds and yields one parseable numeric current measurement. Missing, failed, malformed, or unusable temperature evidence SHALL normalize to absent/`None`; handler/parser convenience defaults such as numeric `0` SHALL NOT manufacture a temperature measurement.

A real device-reported numeric zero remains a valid temperature value when zero was actually parsed from a successful current temperature response. The normalization rule is therefore evidence-based, not `0 == unknown`.

#### Current connection

`current_connection` SHALL be an optional accepted input ordinal derived only from a successfully parsed existing `!` current-input readback. It is authoritative only when the readback identifies exactly one valid input within the proven accepted input range.

Empty, failed, malformed, unrecognized, ambiguous, or out-of-range route evidence SHALL normalize to `None`/UNKNOWN. Neither the handler nor parser SHALL substitute input 1 in those cases.

Connection parsing SHALL use the reviewed protocol response structure rather than concatenating unrelated digits into a synthetic input ordinal.

For the existing `!` query, parsing SHALL be self-contained and fail closed. After normal transport framing/CR/LF normalization, the parser MAY remove one **exact command-echo line** consisting only of `!`. It SHALL then accept exactly one recognized current-input response family and no extra payload:

```text
untagged current-input response: decimal input ordinal only, N
                                 (Extron SIS manual notation: X!])
tagged/verbose response:         In<N> All
```

`N` SHALL contain exactly one decimal input ordinal and SHALL be within the proven accepted input range. Normal protocol line termination/framing may be stripped before matching; it SHALL NOT be searched for arbitrary digits.

The parser SHALL reject as UNKNOWN any response with no recognized payload, multiple candidate payload lines, extra non-framing payload, multiple numeric candidates, partial/sub-string matches, unrelated numeric tokens, or an ordinal outside the proven accepted range. Echo-only input is UNKNOWN. This grammar applies to reconciliation as well as ordinary accepted Matrix readback.

#### Input HDCP presence

The room Matrix HDCP projection SHALL consume a dedicated normalized per-input tri-state presence value derived from the existing **input HDCP status** read, not from input HDCP authorization/configuration or output HDCP state.

The existing IN1804 input-HDCP-status values SHALL normalize exactly as follows:

```text
raw status 2 -> True   # source/sink detected and HDCP present
raw status 1 -> False  # source/sink detected and HDCP absent
raw status 0 -> False  # no source/sink detected; HDCP is not present
other / missing / failed / malformed / unrecognized -> None
```

The `0` case is confirmed absence of current HDCP, not an acquisition failure. Signal presence remains a separate column and may explain that no source is detected.

A failed or unusable HDCP read SHALL NOT be converted to false/zero merely to provide a value. HDCP version information is not required or exposed by this requirement.

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
- **AND** input 1 is not synthesized

#### Scenario: Untagged current-input response is accepted intentionally

- **GIVEN** proven current input range includes input N
- **AND** the existing `!` query returns exactly one untagged current-input payload containing only decimal ordinal N after normal framing removal
- **WHEN** Matrix data is normalized
- **THEN** `current_connection == N`
- **AND** no unrelated digits are searched or concatenated

#### Scenario: Tagged current-input response is accepted intentionally

- **GIVEN** proven current input range includes input N
- **AND** the existing `!` query returns exactly one tagged/verbose payload `In<N> All` after normal framing removal
- **WHEN** Matrix data is normalized
- **THEN** `current_connection == N`

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

- **GIVEN** existing input HDCP-status evidence is respectively `2`, `1`, and `0`
- **WHEN** each value is normalized
- **THEN** the resulting `hdcp_present` values are respectively True, False, and False
- **AND** no HDCP version token is required for room presentation

### Requirement: Matrix route reconciliation cannot succeed from synthetic or unknown evidence

Any Matrix room reconciliation SHALL consume the fail-closed normalized evidence defined above. A route mutation is confirmed only when `current_connection` is a real accepted ordinal established by current readback and equals the requested input.

A parser/handler default, missing readback, failed read, malformed response, unknown connection, unproven input count, unrelated digit sequence, or response outside the exact accepted `!` grammar SHALL never satisfy route reconciliation.

#### Scenario: Requested Input 1 is not confirmed by empty readback

- **GIVEN** output 1/input 1 was requested and route send entered reconciliation
- **WHEN** current connection readback is empty, failed, malformed, ambiguous, outside the accepted grammar, or otherwise UNKNOWN
- **THEN** reconciliation does not confirm input 1
- **AND** the room mutation remains unconfirmed according to `room-device-interaction-lifecycle`

#### Scenario: Requested input is confirmed by truthful readback

- **GIVEN** output 1/input N was requested
- **AND** current reconciliation readback matches one allowed `!` response family and establishes a valid normalized `current_connection == N`
- **WHEN** reconciliation evaluates the result
- **THEN** that route evidence may satisfy the route-match condition
- **AND** final acceptance remains subject to currentness and lifecycle cleanup requirements
