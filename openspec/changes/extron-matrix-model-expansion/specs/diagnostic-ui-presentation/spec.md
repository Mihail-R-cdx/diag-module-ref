## MODIFIED Requirements

### Requirement: Expanded Matrix redesign targets the current room exact-row presentation surface

The modern Matrix presentation SHALL render inside the current room-mode exact-row presentation owned by `RoomDiagnosticTreeWidget` for every exact Extron Matrix registration approved by `device-diagnostics-and-control`, including the existing `Extron IN1804` baseline and newly approved IN1808, IN1608 xi, DTP CrossPoint, XTP CrossPoint, and XTP II CrossPoint profiles.

A focused presentation-only Matrix dashboard component MAY consume accepted exact-row evidence and emit safe non-secret local intents, but SHALL NOT own room identity, target-search, request generation/currentness, credentials, handler/session lifecycle, polling/live ownership, mutation delivery, reconciliation authority, profile selection, SIS syntax, or device network I/O.

The standalone `MatrixScreen` remains a separate presentation/lifecycle surface and SHALL NOT become room authority merely because more Matrix models are supported.

#### Scenario: Expanded Matrix room row uses the modern presentation
- **GIVEN** the current room session contains an expandable exact supported Extron Matrix row
- **WHEN** the operator expands that row
- **THEN** the modern Matrix presentation renders inside the exact-row room content
- **AND** room/record authority remains the current exact row
- **AND** standalone `MatrixScreen` is not required or promoted as room authority

### Requirement: Matrix input table uses proven data-driven rows and the approved column order

The central Matrix table SHALL use this semantic order:

```text
[input ordinal] | Сигнал | HDCP | Входы | [one route column per authoritative available logical output]
```

The leading ordinal column remains compact. `Входы` displays accepted input name when supported/current evidence exists. Route columns SHALL be generated from authoritative `available_output_ids`; they SHALL NOT be hard-coded to output 1 and SHALL NOT be generated from raw physical connector count.

If authoritative output-name evidence exists for an output ID, that name SHOULD be used as the route-column heading. Otherwise the deterministic fallback SHALL be `Output <id>`; the existing single-output IN1804 compatibility presentation MAY retain its accepted `Main Output` fallback for output 1.

Rows SHALL follow a proven accepted current input topology. The presentation SHALL NOT fabricate eight rows, compress gaps in available IDs, or make an unproven ordinal actionable.

A device exposing several physical connectors that share one logical route SHALL still create one route column for that logical route. A multi-output CrossPoint creates one column per authoritative available logical output. If an installed XTP/XTP II board gap removes outputs, later output IDs retain their actual numbers.

#### Scenario: Four-input accepted Matrix is not rendered as eight inputs
- **GIVEN** accepted current Matrix evidence establishes four inputs
- **WHEN** the modern table renders
- **THEN** exactly four authoritative input rows are presented in accepted order
- **AND** no additional rows are fabricated from visual reference or legacy defaults

#### Scenario: Input count is unproven
- **GIVEN** current Matrix normalization cannot establish authoritative input topology/model capability
- **WHEN** the modern table renders
- **THEN** eight rows are not fabricated
- **AND** no unproven input ordinal is actionable for routing

#### Scenario: Multi-output Matrix preserves output identity
- **GIVEN** accepted current topology exposes available outputs `[1, 2, 5, 6]`
- **WHEN** the modern table renders
- **THEN** four route columns are rendered with identities `1`, `2`, `5`, and `6`
- **AND** outputs `5` and `6` are not relabeled as `3` and `4`

#### Scenario: Duplicate physical connector does not become another route column
- **GIVEN** multiple physical output connectors share one logical route
- **WHEN** the Matrix table renders
- **THEN** exactly one route column represents that logical route

### Requirement: Matrix signal, HDCP presence, and route presentation remains meaningful without color

For each accepted input row, signal state SHALL distinguish confirmed presence, confirmed absence, and UNKNOWN. Existing compact signal indicators and their non-color semantic/tool-tip/accessibility meaning remain unchanged.

The `HDCP` column SHALL represent only normalized **current input HDCP presence/state** produced by the active approved profile. Presentation SHALL NOT decode raw SIS `1/2` values itself. It SHALL NOT display HDCP version, input authorization/configuration, or output HDCP state in the input HDCP column. Failed/malformed/unrecognized/missing input-HDCP evidence remains UNKNOWN rather than fabricated `нет`.

For every authoritative available logical output, route state SHALL derive only from fail-closed accepted `routes[output_id]` evidence:

```text
routes[output_id] == this input  -> positive/active semantic
known different routed input    -> neutral/not-selected semantic
explicit untied output          -> no input cell active for that output
missing/unknown route evidence  -> neutral UNKNOWN semantic
```

For existing IN1804 compatibility state, accepted `current_connection` MAY project to `routes[1]`; it remains valid only through the existing fail-closed IN1804 normalization contract. Route ACK/local click state SHALL NOT become accepted active-route authority before reconciliation.

#### Scenario: Compact Signal and HDCP remain semantically explicit
- **GIVEN** accepted signal evidence is present, absent, and UNKNOWN and accepted normalized input HDCP evidence is present, absent, and unknown for corresponding rows
- **WHEN** the Matrix table renders
- **THEN** Signal cells retain explicit non-color semantic meaning
- **AND** HDCP cells present the corresponding accepted normalized meanings
- **AND** no HDCP version token is displayed

#### Scenario: Route ACK does not optimistically recolor the table
- **GIVEN** a route mutation has received apparent send success but reconciliation is not yet accepted
- **WHEN** the Matrix table is rendered
- **THEN** the previously accepted `routes[target_output_id]` remains route-state authority
- **AND** the requested cell is not shown as authoritative `активен` solely because of the ACK

#### Scenario: One input may be active on multiple outputs
- **GIVEN** accepted routes are `{1: 3, 2: 3, 3: 6}`
- **WHEN** the Matrix table renders
- **THEN** input `3` is active in output columns `1` and `2`
- **AND** input `6` is active in output column `3`

#### Scenario: Untied output has no active input
- **GIVEN** accepted route state for output `4` is explicitly untied
- **WHEN** output `4` is rendered
- **THEN** no input cell in output `4` is presented as active

### Requirement: Matrix output cells emit only approved exact-row route intent

A non-active route cell SHALL be actionable only when the exact current expanded row is an approved supported Extron Matrix exact model/profile, has usable connected accepted state, is not stale/degraded/blocked/unconfirmed, the unified registration advertises approved Matrix mutation/reconciliation capability, the serialized room interaction lane permits mutation, and both the input ID and output ID are authoritative available IDs in the current topology.

Presentation SHALL emit only a non-secret immutable route intent containing accepted `input_id` and `output_id` plus the existing exact-row identity needed by composition. It SHALL NOT contain credentials, handler/session references, raw target-search text, raw SIS command strings, standalone screen selection, or global Matrix target state.

The currently active cell remains no-op/non-actionable. Stale, degraded, failed, blocked, non-current, unsupported, unproven-input, unavailable-output, or otherwise unauthorized cells expose no route intent.

Presentation SHALL NOT call `ExtronIN1804Handler`, any CrossPoint handler, `MatrixController.request_route`, socket/transport methods, or other device I/O directly. Composition SHALL revalidate exact-row authority and require the existing explicit operator confirmation before the mutation lifecycle begins.

#### Scenario: Operator selects another current input
- **GIVEN** a connected current exact Matrix row has one authoritative current route on output `1`
- **AND** another input is proven, authorized, and non-active for that output
- **WHEN** the operator activates that input/output cell
- **THEN** presentation emits one safe route intent containing the selected input ID and output `1`
- **AND** no Matrix device I/O occurs from the widget
- **AND** composition requires explicit confirmation before mutation lifecycle begins

#### Scenario: Current active route is clicked
- **GIVEN** input N is already authoritative as active for output O
- **WHEN** the operator clicks that exact active cell
- **THEN** no route mutation intent is submitted
- **AND** no device I/O starts

#### Scenario: Multi-output route intent preserves target output
- **GIVEN** supported CrossPoint output `7` and input `3` are current authoritative available IDs
- **WHEN** the operator activates input `3` in output `7`
- **THEN** presentation emits `input_id=3` and `output_id=7`
- **AND** it does not collapse the intent to output `1`

#### Scenario: Unavailable output exposes no route intent
- **GIVEN** current XTP/XTP II topology marks output `13` unavailable because its board slot is empty
- **WHEN** the table renders
- **THEN** presentation exposes no actionable route cell for output `13`

### Requirement: Matrix Quick actions remain truthful to approved capabilities

The Matrix `Быстрые действия` card SHALL continue to contain `Обновить статус` and `Перезагрузить устройство` under the existing presentation design.

`Обновить статус` maps only to the existing exact-row Local Refresh intent and remains lifecycle-gated. It SHALL NOT create a second Matrix refresh/polling path.

`Перезагрузить устройство` remains disabled/non-actionable unless a later approved exact Matrix profile and mutation/reconciliation contract explicitly adds reboot. This model-expansion change adds no Matrix reboot capability for IN1804, IN1808, IN1608 xi, approved DTP CrossPoint, XTP CrossPoint, or XTP II CrossPoint.

`Открыть расширенный экран` remains absent from the room Matrix dashboard; standalone `MatrixScreen` stays separate.

#### Scenario: Quick Refresh uses the existing room lifecycle
- **GIVEN** the exact connected Matrix row currently permits Local Refresh
- **WHEN** the operator selects `Обновить статус`
- **THEN** existing exact-row Local Refresh intent is requested
- **AND** no parallel Matrix refresh controller/lane is created

#### Scenario: Reboot remains a disabled placeholder
- **GIVEN** the Matrix Quick actions card is visible
- **WHEN** `Перезагрузить устройство` is rendered
- **THEN** it is clearly disabled/non-actionable
- **AND** interacting with it performs no Matrix device I/O

#### Scenario: Expanded-screen affordance is absent
- **WHEN** the room Matrix dashboard renders
- **THEN** `Открыть расширенный экран` is not present
- **AND** no navigation intent to standalone `MatrixScreen` is exposed

## ADDED Requirements

### Requirement: Matrix route-column headings are capability-driven

Route-column headings SHALL use authoritative output-name evidence only when the active profile proves and successfully returns it. An unproven output-name command SHALL cause deterministic fallback heading `Output <id>` rather than speculative SIS I/O or a fabricated configured name.

#### Scenario: XTP output naming is unproven
- **GIVEN** the active XTP profile has no approved output-name read
- **WHEN** the Matrix table renders output `5`
- **THEN** the heading uses deterministic fallback `Output 5`
- **AND** presentation does not imply that an empty configured name was returned
