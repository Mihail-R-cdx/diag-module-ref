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

HDCP cells SHALL use compact centered indicators rather than `есть`, `нет`,
`да`, or `Нет данных` as their primary visible text: `PRESENT_HDCP` is a
filled green indicator; `PRESENT_NO_HDCP` and `ABSENT` are neutral empty
indicators; `UNKNOWN` is neutral and non-positive. Qt semantic data, tooltips,
and accessibility SHALL retain the four distinct canonical states. Signal
UNKNOWN SHALL likewise never render as a green positive indicator. Input-name
and HDCP cell contents SHALL be horizontally centered.

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

### Requirement: Matrix dashboard uses compact information and routing surfaces

The room Matrix dashboard SHALL contain no separate `Быстрые действия` card,
large refresh button, reboot placeholder, or replacement action card.  The
routing-table card SHALL occupy the released horizontal dashboard area while
the information card remains compact.

Local Refresh SHALL be a compact circular-arrow control in the information
card's `IP-адрес` row, beside the exact canonical row IP address.  Its stable
Qt object name, tooltip, and accessible name SHALL be `roomMatrixRefreshButton`
and `Обновить статус`, respectively.  It SHALL emit only the existing
exact-row Local Refresh intent and use exactly the same lifecycle/currentness/
interaction gating as the prior room Matrix refresh control; it SHALL NOT
create a Matrix-specific polling lane.

The routing-table card retains its border/background framework but SHALL hide
its SectionCard title/header completely, so its first visible content is the
horizontal table header.

#### Scenario: Local Refresh remains an exact-row intent
- **GIVEN** the exact connected Matrix row currently permits Local Refresh
- **WHEN** the operator activates the compact IP-row refresh control
- **THEN** exactly one existing exact-row Local Refresh intent is requested
- **AND** no parallel Matrix refresh controller/lane is created

#### Scenario: Matrix action card is absent
- **WHEN** the room Matrix dashboard renders
- **THEN** `Быстрые действия`, `Обновить статус` as a large action, and
  `Перезагрузить устройство` are absent
- **AND** no replacement action card or standalone-screen affordance is exposed

#### Scenario: Table begins without a card title gap
- **WHEN** the room Matrix routing card renders
- **THEN** its first visible content is the horizontal table header
- **AND** no title, icon, or former header spacing appears above that header

## ADDED Requirements

### Requirement: Matrix route-column headings are capability-driven

Route-column headings SHALL use authoritative output-name evidence only when the active profile proves and successfully returns it. An unproven output-name command SHALL cause deterministic fallback heading `Output <id>` rather than speculative SIS I/O or a fabricated configured name.

#### Scenario: XTP output naming is unproven
- **GIVEN** the active XTP profile has no approved output-name read
- **WHEN** the Matrix table renders output `5`
- **THEN** the heading uses deterministic fallback `Output 5`
- **AND** presentation does not imply that an empty configured name was returned

### Requirement: Matrix route columns are equal-width and compact

The route-column count SHALL be determined only by authoritative
`available_output_ids`. Every visible route column SHALL receive the same
fixed layout width (within one pixel of rounding); no output number, first
output, or physical duplicate connector may receive individual stretch or a
legacy special width. The columns SHALL be materially narrower than the former
single-output 29% route allocation while leaving static input-information
columns readable.

#### Scenario: Multi-output columns share one width
- **GIVEN** authoritative available outputs `[1, 2, 5]`
- **WHEN** the Matrix table is laid out
- **THEN** its three route columns have equal widths within one pixel
- **AND** output `1` has no privileged 29%/stretch allocation

### Requirement: Matrix information card projects canonical row facts

The Matrix information card SHALL display the exact room row's canonical
`ip_address`, `mac_address`, and `serial_number` directly from row/inventory
projection. Firmware, temperature, and uptime SHALL be shown only from current
accepted device evidence; unsupported or unproven diagnostics remain
unavailable and SHALL NOT trigger guessed SIS commands. A missing current
field SHALL clear to the established unavailable display rather than retaining
old evidence.

#### Scenario: Canonical inventory facts survive a device snapshot without them
- **GIVEN** an exact Matrix room row has canonical MAC, serial, and IP values
- **AND** its accepted device snapshot contains no MAC or serial
- **WHEN** the information card renders
- **THEN** it displays those canonical row values and the exact row IP
- **AND** it does not issue an additional device query
