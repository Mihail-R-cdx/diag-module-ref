## ADDED Requirements

### Requirement: PDUScreen intent and display boundary
`PDUScreen` SHALL be a PDU UI boundary that renders accepted PDU device data,
outlet records, model capabilities, and current control state, and publishes
non-secret user intents for refresh, individual outlet mutation, and sequential
bulk mutation. It SHALL NOT own credential candidate selection, credential
indexes, credential fallback, successful credential memory, worker creation or
submission, handler acquisition, request/operation generation authority, stale
operation acceptance, or direct PDU network I/O.

PDU refresh and mutation actions SHALL cross the screen boundary through an
explicit signal or callback interface. `PDUScreen` SHALL NOT depend on arbitrary
parent orchestration methods such as `control_pdu_outlet(...)`,
`control_pdu_outlets_bulk(...)`, or `refresh_data()` to execute PDU lifecycle.
The screen MAY retain local rendering helpers and confirmation dialogs that are
view responsibilities.

Qt signals or callbacks from `PDUScreen` SHALL NOT carry credential values,
credential candidate lists, credential dictionaries, handler objects, session
objects, transport objects, cookies, Session IDs, CSRF tokens, or other secret
or session material.

#### Scenario: Individual outlet action emits intent only
- **WHEN** the operator confirms an individual PDU outlet action
- **THEN** `PDUScreen` publishes the outlet number and requested non-secret operation through the explicit PDU intent boundary
- **AND** it does not acquire a handler, create a worker, select a credential candidate, or call an arbitrary parent outlet-control method

#### Scenario: Bulk action emits intent only
- **WHEN** the operator confirms bulk ON or bulk OFF
- **THEN** `PDUScreen` publishes the requested non-secret bulk operation through the explicit PDU intent boundary
- **AND** it does not build credential attempts, create workers, or call an arbitrary parent bulk-control method

#### Scenario: Refresh emits intent only
- **WHEN** the operator requests a PDU status refresh from `PDUScreen`
- **THEN** the screen publishes a refresh intent through the explicit PDU application boundary
- **AND** it does not execute PDU network I/O or directly invoke generic parent refresh orchestration as the PDU lifecycle authority

#### Scenario: Screen does not own PDU operation freshness
- **WHEN** a PDU result, error, progress/status, or completion is associated with an operation context
- **THEN** `PDUScreen` does not decide whether that operation is current from credential state, worker identity, request generation, or Qt widget values
- **AND** it renders only state or outcomes accepted by the PDU application lifecycle boundary

#### Scenario: Screen signal payloads are secret-free
- **WHEN** `PDUScreen` emits a refresh, individual mutation, or bulk mutation intent
- **THEN** the payload contains no credential values, credential candidate lists, handler/session objects, cookies, tokens, or transport objects

#### Scenario: Rendering and confirmation remain screen responsibilities
- **WHEN** the active PDU controller accepts current device data or control state
- **THEN** `PDUScreen` remains responsible for rendering device information, dynamic outlet records, capability-driven controls, and current busy/loading presentation
- **AND** implementation may keep individual and bulk confirmation dialogs in the screen without giving it application lifecycle ownership
