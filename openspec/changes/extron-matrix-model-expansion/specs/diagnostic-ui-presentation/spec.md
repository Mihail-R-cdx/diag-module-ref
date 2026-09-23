## MODIFIED Requirements

### Requirement: Expanded Matrix redesign targets the current room exact-row presentation surface

The modern Matrix presentation SHALL render inside the current room-mode exact-row presentation owned by `RoomDiagnosticTreeWidget` for every exact Extron Matrix registration approved by `device-diagnostics-and-control`, including the existing `Extron IN1804` baseline and newly approved IN1806, IN1808, IN1608 xi, DTP CrossPoint, XTP CrossPoint, and XTP II CrossPoint profiles.

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

### Requirement: Matrix General information preserves approved field order without fabricating evidence

The Matrix `Общая информация` card SHALL always reserve and render rows in this order:

```text
Модель
MAC-адрес
Серийный номер
Версия прошивки
Температура
Время работы
```

For every exact Extron Matrix model supported by this change, a room Matrix full
refresh MAY be classified as complete and successful only when accepted current
evidence establishes an authoritative non-empty value for all six rows.

Source authority SHALL be:

- `Модель`: accepted exact Matrix identity/canonical model for the current operation;
- `MAC-адрес`: current canonical room/inventory evidence when available, otherwise an authoritative read-only device fallback owned by the selected exact Matrix profile;
- `Серийный номер`: current canonical room/inventory evidence when available, otherwise an authoritative read-only device fallback owned by the selected exact Matrix profile;
- `Версия прошивки`: authoritative current device read;
- `Температура`: authoritative current device read;
- `Время работы`: authoritative current device read.

Presentation and acquisition SHALL NOT infer or synthesize a required value from
another field, model text, reference artwork, logs, a prior snapshot, widget state,
default zero, placeholder text, or a command copied speculatively from another
family. An unproven authoritative read for a required row is a blocking capability
gap for that supported profile.

`Нет данных` (or the foundation safe no-data equivalent) remains truthful only
for a failed, incomplete, stale, or otherwise non-successful current acquisition.
Such a state SHALL NOT be classified as a complete successful full refresh.
A prior accepted value SHALL clear rather than survive into a current incomplete
snapshot.

Numeric temperature `0` remains a valid value only when successful current
device evidence explicitly establishes zero.

#### Scenario: Current Matrix snapshot lacks reference-only information fields

- **GIVEN** a current Matrix acquisition lacks one or more authoritative General-information values
- **AND** canonical room/inventory evidence cannot supply missing MAC/serial or the required device fallback/read did not establish them
- **WHEN** the General information card renders and the acquisition is classified
- **THEN** each missing row renders truthful no-data
- **AND** the acquisition is not classified as a complete successful full refresh
- **AND** no unrelated or synthetic value is inserted to make the card look complete

#### Scenario: Failed model and temperature evidence remains no-data

- **GIVEN** current Matrix normalization has no accepted exact model evidence or no authoritative current temperature evidence
- **WHEN** the General information card renders
- **THEN** the missing field shows `Нет данных`
- **AND** local `Unknown`, stale prior evidence, or synthetic numeric zero is not rendered as device evidence
- **AND** the refresh is not classified as complete successful

#### Scenario: Real zero temperature remains visible

- **GIVEN** accepted current Matrix evidence contains temperature numeric zero from a successful authoritative device response
- **WHEN** the General information card renders
- **THEN** `Температура` renders that zero value
- **AND** it is not replaced with `Нет данных`

#### Scenario: Successful full refresh fills all six rows

- **GIVEN** an exact supported Matrix model completes its authoritative current full-refresh acquisition
- **WHEN** that refresh is accepted as complete successful
- **THEN** all six General-information rows contain authoritative values
- **AND** none renders `Нет данных`, a placeholder, or stale prior evidence

#### Scenario: Missing inventory MAC or serial uses device fallback

- **GIVEN** the current exact Matrix row lacks canonical room/inventory MAC or serial evidence
- **WHEN** a complete full refresh is attempted
- **THEN** the selected exact profile uses its proven read-only device fallback for the missing required field
- **AND** failure or unproven support for that fallback prevents complete-success classification
- **AND** no guessed MAC or serial is synthesized

## REMOVED Requirements

### Requirement: Matrix Quick actions remain truthful to approved capabilities

The Matrix `Быстрые действия` card SHALL contain only `Обновить статус` and
`Перезагрузить устройство` for MIH-11. `Обновить статус` SHALL map only to
the existing exact-row Local Refresh intent and SHALL be enabled only under
existing room interaction authorization. It SHALL NOT create a second Matrix
refresh/polling path.

`Перезагрузить устройство` SHALL be visible but disabled/non-actionable
because no approved Extron IN1804 reboot mutation capability exists. It SHALL
emit no application intent, worker start, handler/session acquisition,
protocol command, or device request. `Открыть расширенный экран` SHALL NOT be
rendered in MIH-11.

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
- **WHEN** the MIH-11 Matrix room dashboard renders
- **THEN** `Открыть расширенный экран` is not present
- **AND** no navigation intent to standalone `MatrixScreen` is exposed

## ADDED Requirements

### Requirement: Matrix dashboard uses compact information and routing surfaces

The room Matrix dashboard SHALL contain no separate `Быстрые действия` card,
large refresh button, reboot placeholder, replacement action card, production
`Отладка` affordance, or Matrix-specific footer/action strip. The routing-table
card SHALL occupy the released horizontal dashboard area while the information
card remains compact.

The Matrix information card SHALL NOT contain an `IP-адрес` row. It SHALL NOT
contain an embedded circular refresh control, `!`/warning button, unlabeled
action button, debug button, or trailing action/footer area below the approved
information fields. Existing room/global refresh lifecycle and currentness
authority remain outside this information card; removing these controls SHALL
NOT create a replacement Matrix-specific polling lane.

The routing-table card retains its border/background framework but SHALL hide
its SectionCard title/header completely, so its first visible content is the
horizontal table header.

#### Scenario: Information card has no IP/action footer
- **WHEN** the Matrix information card renders
- **THEN** it has no `IP-адрес` field
- **AND** it has no embedded refresh/debug/warning/action button
- **AND** its visible content ends with the approved diagnostic information rows

#### Scenario: Existing refresh lifecycle is not duplicated
- **GIVEN** room/global refresh is available through an already-approved affordance outside the Matrix information card
- **WHEN** the Matrix dashboard renders
- **THEN** that existing application lifecycle remains authoritative
- **AND** the Matrix information card adds no local refresh controller or network path

#### Scenario: Matrix action card is absent
- **WHEN** the room Matrix dashboard renders
- **THEN** `Быстрые действия`, production `Отладка`, `Обновить статус` as a large action,
  `Перезагрузить устройство`, and embedded `!`/warning actions are absent
- **AND** no replacement action/footer card or standalone-screen affordance is exposed

#### Scenario: Table begins without a card title gap
- **WHEN** the room Matrix routing card renders
- **THEN** its first visible content is the horizontal table header
- **AND** no title, icon, or former header spacing appears above that header

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

The Matrix information card SHALL use the same six-field completeness and
authority contract as `Matrix General information preserves approved field order
without fabricating evidence`. The row's canonical `ip_address` remains
application/target authority but SHALL NOT be duplicated inside this card.

Canonical current room/inventory MAC and serial SHALL be used when present.
Their absence SHALL activate only the selected exact profile's proven read-only
device fallback; it SHALL NOT permit a guessed value. Firmware, temperature,
and uptime SHALL come only from authoritative current device reads. Model SHALL
come from the accepted exact Matrix identity/canonical model.

The card MAY show truthful no-data during incomplete/failed acquisition, but a
snapshot with any missing required General-information value SHALL NOT be treated
as a complete successful full refresh. Missing current evidence SHALL clear old
presentation values.

#### Scenario: Canonical inventory facts survive a device snapshot without them
- **GIVEN** an exact Matrix room row has current canonical MAC and serial values
- **AND** its accepted device snapshot does not repeat those two values
- **WHEN** the information card renders
- **THEN** it displays canonical MAC and serial values without an extra device read for those already-authoritative fields
- **AND** it does not duplicate the exact row IP inside the card
- **AND** firmware, temperature, and uptime still require authoritative current device evidence

#### Scenario: Missing canonical MAC or serial requires proven device fallback
- **GIVEN** the current exact Matrix row lacks canonical MAC or serial evidence
- **WHEN** a complete full refresh is attempted
- **THEN** only the selected exact profile's proven read-only device acquisition may supply the missing value
- **AND** absent/unproven fallback leaves the refresh incomplete rather than fabricating presentation evidence
