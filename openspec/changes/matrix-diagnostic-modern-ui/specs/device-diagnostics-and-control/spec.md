## ADDED Requirements

### Requirement: Extron IN1804 Matrix normalization is fail-closed for routing authority

The existing Extron IN1804 diagnostic path SHALL continue to use its current SIS read commands, but normalized Matrix evidence consumed by room presentation and route reconciliation SHALL distinguish confirmed values from missing, failed, malformed, unrecognized, or out-of-range evidence.

MIH-11 SHALL NOT add a new SIS query merely to satisfy this requirement. It SHALL correct only the handling/normalization of existing Matrix model/count, connection, and input-HDCP-status reads.

#### Input count

`inputs_num` SHALL be accepted as a positive current Matrix input count only when existing model/capability evidence positively establishes that count. A constructor default, parser fallback, visual-reference row count, prior snapshot, or other convenience value SHALL NOT establish current accepted input authority.

On the current implementation path specifically, legacy defaults equivalent to `self.inputs_num = 8` and `data.get("inputs_num", 8)` SHALL NOT be published/consumed as authoritative count when model/count evidence is unproven. Unknown count SHALL remain absent/`None`/explicitly unknown according to the chosen normalized representation.

Per-input names/status arrays created only because of an unproven fallback count SHALL NOT make those ordinals actionable for room routing.

#### Current connection

`current_connection` SHALL be an optional accepted input ordinal derived only from a successfully parsed existing connection readback. It is authoritative only when the readback identifies exactly one valid input within the proven accepted input range.

Empty, failed, malformed, unrecognized, ambiguous, or out-of-range route evidence SHALL normalize to `None`/UNKNOWN. Neither the handler nor parser SHALL substitute input 1 in those cases.

Connection parsing SHALL use the reviewed protocol response structure rather than concatenating unrelated digits into a synthetic input ordinal.

#### Input HDCP presence

The room Matrix HDCP projection SHALL consume a dedicated normalized per-input tri-state presence value derived from the existing **input HDCP status** read, not from input HDCP authorization/configuration or output HDCP state.

The normalized meaning SHALL be equivalent to:

```text
recognized current HDCP present -> True
recognized current HDCP absent  -> False
failed/missing/malformed/unrecognized -> None
```

A failed or unusable HDCP read SHALL NOT be converted to false/zero merely to provide a value. HDCP version information is not required or exposed by this requirement.

#### Scenario: Unproven Matrix input count remains unknown

- **GIVEN** the Extron IN1804 diagnostic acquisition does not obtain evidence that establishes current supported input count
- **WHEN** Matrix data is normalized
- **THEN** normalized input count is UNKNOWN/absent rather than eight by default
- **AND** unproven input ordinals are not accepted as route targets

#### Scenario: Empty connection evidence does not become Input 1

- **GIVEN** the existing connection read returns no usable route evidence
- **WHEN** Matrix data is normalized
- **THEN** `current_connection` is UNKNOWN/`None`
- **AND** input 1 is not synthesized

#### Scenario: Malformed connection evidence does not become Input 1

- **GIVEN** a connection response is successful at transport level but does not match the reviewed route-response structure or does not establish one valid input ordinal
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

#### Scenario: Confirmed HDCP presence is boolean evidence

- **GIVEN** the existing input HDCP-status read returns a recognized current-present or current-absent state
- **WHEN** it is normalized
- **THEN** the projection yields True or False respectively
- **AND** no HDCP version token is required for room presentation

### Requirement: Matrix route reconciliation cannot succeed from synthetic or unknown evidence

Any Matrix room reconciliation SHALL consume the fail-closed normalized evidence defined above. A route mutation is confirmed only when `current_connection` is a real accepted ordinal established by current readback and equals the requested input.

A parser/handler default, missing readback, failed read, malformed response, unknown connection, unproven input count, or unrelated digit sequence SHALL never satisfy route reconciliation.

#### Scenario: Requested Input 1 is not confirmed by empty readback

- **GIVEN** output 1/input 1 was requested and route send entered reconciliation
- **WHEN** current connection readback is empty, failed, malformed, or otherwise UNKNOWN
- **THEN** reconciliation does not confirm input 1
- **AND** the room mutation remains unconfirmed according to `room-device-interaction-lifecycle`

#### Scenario: Requested input is confirmed by truthful readback

- **GIVEN** output 1/input N was requested
- **AND** current reconciliation readback establishes a valid normalized `current_connection == N`
- **WHEN** reconciliation evaluates the result
- **THEN** that route evidence may satisfy the route-match condition
- **AND** final acceptance remains subject to currentness and lifecycle cleanup requirements
