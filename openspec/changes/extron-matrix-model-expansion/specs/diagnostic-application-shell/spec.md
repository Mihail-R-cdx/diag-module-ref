## MODIFIED Requirements

### Requirement: Matrix route and refresh actions cross the presentation boundary as non-secret intent data

Matrix presentation SHALL remain isolated from Extron handler/session ownership.

A Matrix route intent SHALL carry explicit target `input_id` and `output_id` context to the application/controller boundary. Presentation SHALL NOT construct or send SIS commands, acquire credentials, or reuse handler/session objects directly.

The application/controller layer SHALL validate the requested IDs against the current authoritative Matrix topology/capability context before creating a state-changing handler operation.

#### Scenario: Multi-output route intent is translated by controller layer

- **GIVEN** the current Matrix topology authorizes input `4` and output `2`
- **WHEN** presentation emits a route intent for `(input_id=4, output_id=2)`
- **THEN** the application/controller layer resolves the current Matrix capability/profile
- **AND** delegates the state-changing route through the existing Matrix operation lifecycle
- **AND** presentation does not know whether the resulting SIS syntax is `4*2!`, `4!`, or another approved profile command.

#### Scenario: Unavailable output is rejected before send

- **GIVEN** the current runtime topology marks output `13` unavailable because its XTP/XTP II output board slot is empty
- **WHEN** stale or malformed UI/controller state attempts a route intent targeting output `13`
- **THEN** the application/controller boundary rejects the mutation before any state-changing SIS command is sent.

### Requirement: Matrix route reconciliation targets the intended logical output

After a successful or uncertain Matrix route mutation, authoritative reconciliation SHALL query the specific logical output targeted by the intent using the active profile's read command.

The controller SHALL NOT assume output `1` for a multi-output Matrix.

#### Scenario: CrossPoint output 7 mutation is reconciled independently

- **WHEN** a route mutation targets CrossPoint output `7`
- **THEN** reconciliation reads output `7` through the approved CrossPoint route-query profile
- **AND** does not use another output's route as confirmation.

### Requirement: Matrix capability context remains current-operation scoped

Model identity, topology and capability/profile selection used for route validation and reconciliation SHALL belong to the current Matrix target/context.

A stale capability object from a previously displayed Matrix SHALL NOT authorize commands for a replacement device or room context.

#### Scenario: Matrix target changes between records

- **WHEN** the active Matrix target changes from a single-output IN1804 to a multi-output XTP device
- **THEN** old IN1804 route/topology authority is invalidated
- **AND** no route mutation is permitted until current XTP identity/topology/capability evidence is established.