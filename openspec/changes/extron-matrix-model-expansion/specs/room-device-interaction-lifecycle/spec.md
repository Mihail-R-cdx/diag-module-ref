## MODIFIED Requirements

### Requirement: Matrix route intent is exact-row, confirmed, and stale-safe before device acquisition

A Matrix room route MAY start only from the exact current expanded Matrix row and SHALL carry non-secret explicit `input_id` plus `output_id` context. Existing exact-row identity/currentness, lock/admission, confirmation, credential ownership, mutation serialization, possible-send/no-replay, cleanup, stale-callback suppression, and reconciliation rules remain authoritative.

The requested input and output IDs SHALL both be present in the current accepted Matrix topology/capability context before the mutation may acquire a handler or send device I/O. Existing single-output IN1804 remains output `1`; multi-output Matrix profiles SHALL preserve the requested logical output ID through mutation and reconciliation.

A state-changing Matrix command that may have been sent SHALL NOT be replayed automatically to recover transport/session state or try another credential. Send/ACK success remains delivery evidence only and SHALL NOT become accepted route authority.

#### Scenario: Matrix route intent uses current exact row
- **GIVEN** a current exact Matrix row is expanded and current room interaction state permits routing
- **WHEN** a route intent for an authoritative current input/output pair is confirmed
- **THEN** the existing serialized room mutation lifecycle may acquire the exact current row operation context
- **AND** stale row/context state cannot authorize the mutation

#### Scenario: Stale Matrix route intent is rejected before device acquisition
- **GIVEN** a Matrix route intent was created for an older exact row/context
- **WHEN** room/record/currentness authority has been superseded before admission
- **THEN** the intent is rejected before handler/session acquisition and device I/O

#### Scenario: Unavailable Matrix output is rejected before send
- **GIVEN** current accepted Matrix topology marks output O unavailable
- **WHEN** a stale or malformed intent requests a route to output O
- **THEN** the room interaction boundary rejects the mutation before state-changing SIS send

#### Scenario: Matrix route possible-send is not replayed
- **GIVEN** a Matrix route command may have been delivered to the device
- **WHEN** transport/session response becomes ambiguous or fails after that boundary
- **THEN** the same mutation is not automatically replayed
- **AND** credential fallback does not resend the state-changing command
- **AND** final state remains unconfirmed until authoritative reconciliation

### Requirement: Matrix room route reconciliation is authoritative and output-specific

After a Matrix route mutation reaches reconciliation, accepted final route state SHALL come only from a current authoritative read of the logical output targeted by that mutation. Reconciliation SHALL compare the requested input against normalized `routes[target_output_id]` evidence from the active approved Matrix profile.

For existing IN1804, the current accepted `current_connection` evidence remains the compatibility authority for output 1 and MAY project to `routes[1]`. For a multi-output Matrix, no other output's route and no scalar fallback MAY confirm the targeted output.

Unknown, malformed, failed, stale, out-of-range, unavailable-output, unproven-topology, or otherwise non-authoritative readback SHALL NOT confirm the mutation.

#### Scenario: Matrix output-1 reconciliation remains compatible
- **GIVEN** existing IN1804 output 1/input N was delivered successfully and entered reconciliation
- **WHEN** current exact-row readback returns accepted Matrix evidence with `current_connection == N` and `routes[1] == N`
- **THEN** that current accepted route evidence may satisfy the route match
- **AND** final acceptance remains subject to currentness and cleanup requirements

#### Scenario: CrossPoint output-specific reconciliation
- **GIVEN** input N was requested for authoritative CrossPoint output O and the command entered reconciliation
- **WHEN** current accepted readback establishes `routes[O] == N`
- **THEN** that targeted-output evidence may satisfy route reconciliation
- **AND** a matching route on another output cannot confirm the mutation

#### Scenario: Unknown targeted route remains unconfirmed
- **GIVEN** a Matrix route mutation entered reconciliation
- **WHEN** current readback for the targeted output is missing, failed, malformed, stale, or UNKNOWN
- **THEN** the route mutation remains unconfirmed
- **AND** no requested route is promoted to accepted state from ACK or local UI state

### Requirement: Matrix room routing preserves existing PDU, Matrix live, and standalone lifecycle boundaries

Generalizing Matrix routing to explicit logical output IDs SHALL NOT create another room interaction lane, another Matrix LIVE owner, or a standalone-screen authority path. Existing PDU interaction lifecycles, Matrix room live/local-refresh ownership, and standalone Matrix presentation/lifecycle boundaries remain separate.

The room Matrix dashboard SHALL continue to emit non-secret intent into the existing room interaction authority; it SHALL NOT promote standalone `MatrixScreen` handler/session ownership or create a parallel CrossPoint mutation controller.

#### Scenario: Standalone route remains separate
- **WHEN** routing is performed from a standalone Matrix surface under its approved application lifecycle
- **THEN** that standalone lifecycle remains separate from room exact-row mutation authority
- **AND** room-mode support for additional Matrix profiles does not merge the two ownership paths

#### Scenario: Room Matrix route remains on serialized room lane
- **WHEN** a current room Matrix route intent is confirmed for any approved Matrix output
- **THEN** mutation and reconciliation use the existing serialized room interaction lifecycle
- **AND** no second Matrix room mutation lane is created
