## ADDED Requirements

### Requirement: MatrixScreen intent and display boundary
`MatrixScreen` SHALL be a Matrix UI boundary that renders Matrix data and
publishes non-secret user intents. It SHALL NOT own credential candidate
selection, credential indexes, handler acquisition, persistent handler/session
state, transport lifecycle, retry policy, credential fallback, keepalive, or
direct Matrix network I/O.

Matrix route and refresh user actions SHALL cross the screen boundary as
non-secret intent or callback data. Qt signals or callbacks from
`MatrixScreen` SHALL NOT carry credential values, credential candidate lists,
handler objects, session objects, transport objects, cookies/tokens, or other
secret/session material.

#### Scenario: Route click emits intent only
- **WHEN** the operator clicks a Matrix routing cell
- **THEN** `MatrixScreen` publishes a route intent for the selected Matrix input/output context
- **AND** it does not call `ExtronIN1804Handler.set_connection()` directly
- **AND** it does not acquire or reuse a handler/session object

#### Scenario: Quick refresh is not screen-owned network I/O
- **WHEN** Matrix route status needs to be refreshed after a route action
- **THEN** `MatrixScreen` requests or receives the update through the Matrix application boundary
- **AND** it does not call `ExtronIN1804Handler.get_connections()` directly

#### Scenario: Screen does not own credentials
- **WHEN** a Matrix route or refresh intent is submitted
- **THEN** `MatrixScreen` does not read or mutate credential candidate lists or successful credential indexes
- **AND** credential ownership remains outside the screen boundary

#### Scenario: Screen signal payloads are secret-free
- **WHEN** `MatrixScreen` emits a route or refresh signal/callback
- **THEN** the payload contains no credential values, credential candidate lists, handler objects, session objects, cookies, tokens, or transport objects

#### Scenario: Rendering remains screen-owned
- **WHEN** the active Matrix controller accepts current Matrix data
- **THEN** `MatrixScreen` remains responsible for rendering the routing table, current connection, signal/HDCP indicators, and device information
