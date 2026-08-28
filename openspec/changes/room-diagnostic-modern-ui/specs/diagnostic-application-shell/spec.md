## MODIFIED Requirements

### Requirement: Device selection and refresh input validation

The main window target panel SHALL use one permanent target-search field as its only persistent diagnostic-target editor. The field SHALL accept either a syntactically valid IPv4 address or non-empty room-name text and SHALL NOT expose a persistent device-model selector, a `deviceCombo` equivalent, or the `Устройство` label.

The application SHALL preserve the operator's raw entered search text as presentation state until the operator edits it. Inventory normalization, canonical IP, selected room ID, exact model, current room generation, or result rendering SHALL NOT replace the visible raw query text.

A user-initiated top Refresh or equivalent Enter action SHALL reject an empty/blank target before credential resolution, reachability, handler acquisition, worker/controller submission, or device network I/O. For a non-empty target, application composition SHALL classify a normalized copy as follows:

```text
valid IPv4                -> IP target
otherwise non-empty text  -> room-name target
```

Typing, autocomplete computation, or selecting a room-name suggestion SHALL perform no ping, credential resolution, handler acquisition, worker/controller submission, or device network I/O.

For an IP target with valid current inventory, source-IP lookup SHALL preserve zero/one/many multiplicity without model/kind filtering:

- zero records SHALL fail closed as not found;
- more than one record SHALL fail closed as ambiguous;
- exactly one record with non-null authoritative `room_id` SHALL establish room diagnostic mode for that whole room even if the source model is unsupported/null;
- exactly one record with `room_id = null` and an exact registered `diagnostic_model` SHALL use the existing legacy single-device path;
- exactly one no-room record with null/unsupported model SHALL fail closed.

For a room-name target, valid current inventory is mandatory. The application SHALL query the storage-independent canonical room-name search boundary and reason in distinct authoritative `room_id` results:

- zero matching room IDs SHALL produce a controlled no-match outcome;
- exactly one matching room ID MAY be selected by Enter/top Refresh directly;
- more than one matching room ID SHALL require an explicit current dropdown selection before Enter/top Refresh can start diagnostics;
- selection SHALL bind the exact current inventory snapshot and query revision and SHALL NOT rewrite the raw search text;
- a selected room ID SHALL establish room mode directly and SHALL NOT create a synthetic source device.

Editing the target-search text SHALL invalidate any prior room-name selection. A stale selection from an older query revision or inventory snapshot SHALL NOT authorize diagnostics.

Manual model fallback SHALL remain available only for the IP-target path when canonical inventory is unavailable, unloadable, or corrupt under the existing structured inventory-load contract. Room-name search with unavailable/unloadable/corrupt inventory SHALL fail closed with a safe inventory-unavailable outcome and SHALL NOT open manual model fallback or guess a room/model.

For room diagnostic mode, global preliminary reachability SHALL NOT run against one selected model before the tree exists. The room lifecycle SHALL build the authoritative room context/tree first and apply the approved per-record credential-plan and reachability gates immediately before each eligible row's model-specific acquisition. For the legacy supported no-room IP path, the existing single-device reachability gate remains.

The permanent `Пароль` capability MAY remain as an application-level action, including inside an `Действия` menu, but it SHALL remain network-free credential configuration. It SHALL be available only when the current target resolves through an IP-based exact-model configuration context. A room-name target SHALL NOT select an arbitrary room record/model for credentials and SHALL NOT start room polling.

#### Scenario: Main panel has one search field and no model selector

- **WHEN** the main diagnostic window is constructed
- **THEN** it exposes one persistent target-search field plus model-independent application actions
- **AND** it does not expose `deviceCombo`, another persistent model selector, or the `Устройство` label

#### Scenario: Raw room query remains visible

- **GIVEN** the operator types `Перег` and selects a matching room from multiple suggestions
- **WHEN** room diagnostics starts and renders results
- **THEN** the search field still displays `Перег`
- **AND** selected canonical `room_id` is stored separately as application authority

#### Scenario: Valid room device IP opens the whole room

- **GIVEN** valid inventory contains exactly one record for the entered IPv4 target
- **AND** that record has non-null `room_id`
- **WHEN** Enter/top Refresh starts diagnostics
- **THEN** the complete room session/tree is established from that room ID
- **AND** the entered IP text remains visible unchanged

#### Scenario: Room-name query has exactly one room result

- **GIVEN** valid inventory room-name search returns one distinct canonical `room_id`
- **WHEN** the operator presses Enter or top Refresh
- **THEN** that exact room is selected and room diagnostics may start
- **AND** no synthetic source record is created

#### Scenario: Room-name query has multiple room results

- **GIVEN** valid inventory room-name search returns multiple distinct canonical `room_id` values
- **WHEN** no current suggestion has been explicitly selected
- **THEN** Enter/top Refresh starts no room/device network I/O
- **AND** the operator must select one exact room result

#### Scenario: Selecting a room suggestion is network-free

- **WHEN** the operator selects one room from the autocomplete dropdown
- **THEN** application state records that exact current room candidate
- **AND** no ping, credential resolution, handler acquisition, worker submission, or device network I/O starts merely from selection

#### Scenario: Search text edit invalidates selection

- **GIVEN** a room suggestion was selected for query revision N
- **WHEN** the operator edits the search field
- **THEN** the old selection cannot authorize a later diagnostic start
- **AND** a new resolution is required for the new query revision

#### Scenario: Room-name search inventory is unavailable

- **GIVEN** the target is not a valid IPv4 address
- **WHEN** canonical inventory is unavailable, unloadable, or corrupt
- **THEN** the application reports a controlled inventory-unavailable outcome
- **AND** it does not open model fallback or perform device network I/O

#### Scenario: IP target inventory is unavailable

- **GIVEN** the target is a valid IPv4 address
- **WHEN** canonical inventory is unavailable, unloadable, or corrupt
- **THEN** the existing explicit diagnostic-purpose model fallback MAY remain available under its current fail-closed confirmation contract

#### Scenario: Password is not room-name model selection

- **GIVEN** the current target is a room-name query or room-name selection
- **WHEN** the operator requests credential configuration
- **THEN** no arbitrary room record/model is selected for `Пароль`
- **AND** no device network I/O starts

#### Scenario: Legacy supported no-room IP remains available

- **GIVEN** exactly one inventory record matches the valid IPv4 target
- **AND** `room_id = null`
- **AND** its exact canonical model is registered
- **WHEN** diagnostics starts
- **THEN** the existing legacy single-device screen/lifecycle remains available
- **AND** no synthetic room is created
