## MODIFIED Requirements

### Requirement: MatrixScreen intent and display boundary
`MatrixScreen` SHALL remain a Matrix UI boundary that renders Matrix data and
publishes non-secret user intents. It SHALL NOT own credential candidate
selection, credential indexes, handler acquisition, persistent handler/session
state, transport lifecycle, retry policy, credential fallback, keepalive, exact
SIS command generation, or direct Matrix network I/O.

Matrix route and refresh user actions SHALL cross the screen boundary as
non-secret intent or callback data. A route intent SHALL identify the selected
authoritative logical `input_id` and `output_id`; for existing single-output
IN1804 this remains output `1`. Presentation SHALL NOT decide whether the
resulting command is `N!`, `N*1!`, `N*M!`, or another approved profile syntax.

Qt signals or callbacks from `MatrixScreen` SHALL NOT carry credential values,
credential candidate lists, handler objects, session objects, transport
objects, cookies/tokens, raw SIS commands, or other secret/session material.

The application/controller boundary SHALL validate intent IDs against the
current exact Matrix target's accepted topology/capability context before
creating a state-changing operation. A stale capability/profile from a replaced
target SHALL NOT authorize a route.

#### Scenario: Route click emits intent only
- **WHEN** the operator clicks an actionable Matrix routing cell
- **THEN** `MatrixScreen` publishes a route intent for the selected authoritative Matrix input/output context
- **AND** the intent contains explicit non-secret input/output identity
- **AND** it does not call `ExtronIN1804Handler.set_connection()` or another model handler directly
- **AND** it does not construct SIS command syntax
- **AND** it does not acquire or reuse a handler/session object

#### Scenario: Quick refresh is not screen-owned network I/O
- **WHEN** Matrix route status needs to be refreshed after a route action
- **THEN** `MatrixScreen` requests or receives the update through the Matrix application boundary
- **AND** it does not call `ExtronIN1804Handler.get_connections()` or another handler read directly

#### Scenario: Screen does not own credentials
- **WHEN** a Matrix route or refresh intent is submitted
- **THEN** `MatrixScreen` does not read or mutate credential candidate lists or successful credential indexes
- **AND** credential ownership remains outside the screen boundary

#### Scenario: Screen signal payloads are secret-free
- **WHEN** `MatrixScreen` emits a route or refresh signal/callback
- **THEN** the payload contains no credential values, credential candidate lists, handler objects, session objects, cookies, tokens, transport objects, or raw SIS command strings

#### Scenario: Rendering remains screen-owned
- **WHEN** the active Matrix controller accepts current Matrix data
- **THEN** `MatrixScreen` remains responsible for rendering the routing table, accepted route state, signal/HDCP indicators, and device information
- **AND** a multi-output accepted route map MAY render multiple output columns without transferring protocol authority into the screen

## ADDED Requirements

### Requirement: Matrix route reconciliation targets the intended authoritative logical output

After a successful or uncertain Matrix route mutation, reconciliation SHALL query the specific logical output targeted by the intent using the active approved profile's read command. The controller SHALL NOT assume output `1` for a multi-output Matrix.

#### Scenario: CrossPoint output 7 mutation is reconciled independently
- **WHEN** a route mutation targets approved CrossPoint output `7`
- **THEN** reconciliation reads output `7` through the active CrossPoint route-query profile
- **AND** another output's route cannot confirm the mutation

### Requirement: Matrix capability context remains current-operation scoped

Exact model/frame identity, topology and profile selection used for validation/reconciliation SHALL belong to the current Matrix target/context. Deferred XTP/XTP II evidence SHALL NOT become current production capability authority in this change.

#### Scenario: Matrix target changes to deferred XTP
- **WHEN** the active Matrix target changes from a supported IN/DTP Matrix to XTP or XTP II evidence
- **THEN** old route/topology/profile authority is invalidated
- **AND** no production Matrix handler/session, route mutation, credential attempt, or topology I/O starts for the deferred target
- **AND** historical XTP parser state cannot restore support

### Requirement: Matrix GUI preserves canonical HDCP and temperature evidence

Both standalone and room Matrix presentations SHALL consume canonical
`input_hdcp[input_id]` as their input-HDCP authority. They SHALL present
`PRESENT_HDCP` as confirmed positive, `PRESENT_NO_HDCP` and `ABSENT` as
confirmed negative, and `UNKNOWN` or missing evidence as unavailable. Input
HDCP authorization and output HDCP SHALL NOT substitute for this state.
Successful current temperature evidence SHALL reach the existing Matrix
temperature field; unavailable current evidence SHALL render its established
empty state and SHALL NOT retain an earlier value or invent `0°C`.

#### Scenario: Canonical false HDCP is not displayed as unknown

- **GIVEN** canonical input states `PRESENT_HDCP`, `PRESENT_NO_HDCP`, `ABSENT`, and `UNKNOWN`
- **WHEN** each Matrix GUI table renders them
- **THEN** the visible room cells are respectively a filled green indicator, a neutral empty indicator, a neutral empty indicator, and a neutral non-positive indicator
- **AND** Qt semantic data/tooltips distinguish confirmed `PRESENT_NO_HDCP` and `ABSENT` from unavailable `UNKNOWN` data
- **AND** signal presence remains an independent column

#### Scenario: Current temperature reaches both Matrix surfaces

- **GIVEN** an accepted Matrix snapshot with `temperature=59`
- **WHEN** standalone and room Matrix presentation render it
- **THEN** each existing temperature field displays `59°C`
- **WHEN** a later current snapshot has unavailable temperature
- **THEN** the standalone field displays its empty state
