## MODIFIED Requirements

### Requirement: Room Matrix presentation renders dynamic routing outputs

The room Matrix presentation SHALL render one routing column for each authoritative `available_output_id` in the current normalized Matrix topology.

The number of routing columns SHALL NOT be hard-coded to one and SHALL NOT be derived from physical connector count.

If an authoritative output name is available for an output ID, the presentation SHOULD use that name as the column heading. Otherwise it SHALL use a deterministic fallback such as `Output <id>`.

#### Scenario: Multi-output CrossPoint renders one column per available output

- **GIVEN** normalized topology has available outputs `[1, 2, 3, 4]`
- **WHEN** the Matrix row is rendered
- **THEN** exactly four route columns are shown
- **AND** each column is bound to its corresponding logical output ID.

#### Scenario: Board gap is preserved in column identity

- **GIVEN** normalized topology has available outputs `[1, 2, 5, 6]`
- **WHEN** route columns are rendered
- **THEN** the columns retain output identities `1`, `2`, `5`, and `6`
- **AND** outputs `5` and `6` are not relabeled as `3` and `4`.

#### Scenario: Physical duplicate connector does not create duplicate route column

- **GIVEN** two physical output connectors share one logical route
- **WHEN** Matrix routing is rendered
- **THEN** only one route column is shown for that logical route.

### Requirement: Matrix routing cells project normalized output-to-input state

For each available logical output, the Matrix presentation SHALL determine the selected input from normalized `routes[output_id]` state.

A single input MAY appear selected in more than one output column.

An explicitly untied output SHALL have no selected input cell.

#### Scenario: One input feeds multiple outputs

- **GIVEN** normalized routes `{1: 3, 2: 3, 3: 6}`
- **WHEN** the table is rendered
- **THEN** input `3` is selected in output columns `1` and `2`
- **AND** input `6` is selected in output column `3`.

#### Scenario: Untied output has no active row

- **GIVEN** normalized route for output `4` is `None`
- **WHEN** output `4` is rendered
- **THEN** no input row is shown as currently selected for output `4`.

### Requirement: Matrix route intent carries explicit input and output identity

A route action emitted from the presentation SHALL identify both the target input ID and target output ID.

The presentation SHALL remain protocol-agnostic and SHALL NOT construct SIS command strings.

The currently active route cell SHALL remain a no-op/non-actionable target.

Stale, failed, blocked, unsupported, unproven-input, unavailable-output, or otherwise unauthorized cells SHALL expose no route intent.

#### Scenario: Operator selects a different route on output 3

- **GIVEN** output `3` currently routes input `2`
- **AND** input `5` and output `3` are authoritative available IDs
- **WHEN** the operator selects the cell for input `5` and output `3`
- **THEN** presentation emits a non-secret route intent containing `input_id=5` and `output_id=3`
- **AND** it does not call an Extron handler directly.

### Requirement: Matrix diagnostic columns remain capability-driven

Signal, HDCP, names and other Matrix diagnostics SHALL be projections of normalized accepted evidence for the active capability profile.

A field whose command/capability is unproven SHALL not be presented as a fabricated negative result.

#### Scenario: XTP input name command remains unproven

- **GIVEN** the active XTP profile has no proven input-name read
- **WHEN** the Matrix row is rendered
- **THEN** the input-name field follows the existing unavailable/no-data presentation behavior
- **AND** the UI does not imply that the device returned an empty configured name.

### Requirement: Existing single-output IN1804 presentation remains compatible

An existing IN1804 normalized record with one available logical output SHALL continue to render one routing column and the current accepted signal/HDCP/input-name evidence without requiring a multi-output-specific user workflow.

#### Scenario: Existing IN1804 room record

- **GIVEN** an IN1804 topology with inputs `1..4` and available output `[1]`
- **WHEN** the Matrix row is rendered after this change
- **THEN** one route column is shown
- **AND** the current input route is selected from `routes[1]`
- **AND** existing room Matrix safety/no-op behavior is preserved.