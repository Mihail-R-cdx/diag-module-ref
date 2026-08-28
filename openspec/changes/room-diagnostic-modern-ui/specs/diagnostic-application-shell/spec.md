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

Valid-inventory not-found, ambiguous, unmapped, and unsupported IP outcomes SHALL NOT open manual model fallback or select a target by source text, `device_kind`, page type, room display data, previous request state, or prior fallback state.

For an IP target when canonical inventory is unavailable, unloadable, or corrupt under the existing structured inventory-load contract, diagnostic start SHALL automatically open the existing fail-closed diagnostic-purpose model fallback or focused equivalent. Only a new explicit model selection and explicit `Подключиться` confirmation bound to that current diagnostic-start purpose MAY create the fallback request context. A confirmed fallback SHALL remain purpose-bound and SHALL NOT be reused implicitly by a later request or by a room-name query.

For a room-name target, valid current inventory is mandatory. The application SHALL query the storage-independent canonical room-name search boundary and reason in distinct authoritative `room_id` results:

- zero matching room IDs SHALL produce a controlled no-match outcome;
- exactly one matching room ID MAY be selected by Enter/top Refresh directly;
- more than one matching room ID SHALL require an explicit current dropdown selection before Enter/top Refresh can start diagnostics;
- each suggestion SHALL expose a deterministic non-authoritative display label sufficient to distinguish otherwise identical room names within the current result set;
- selection SHALL bind the exact current inventory snapshot and query revision and SHALL NOT rewrite the raw search text;
- a selected room ID SHALL establish room mode directly and SHALL NOT create a synthetic source device.

When an explicit room-name selection exists, the GUI SHALL expose a separate visible current-selection cue adjacent to or directly associated with the target field. That cue SHALL display the selected result's deterministic selection label without replacing `raw_query`. The cue is presentation evidence only; exact `room_id + inventory snapshot + query revision` remains application authority. Editing the target-search text SHALL clear the cue and invalidate the prior selection. A stale selection from an older query revision or inventory snapshot SHALL NOT authorize diagnostics.

Room-name search with unavailable, unloadable, or corrupt inventory SHALL fail closed with a safe inventory-unavailable outcome and SHALL NOT open diagnostic model fallback, credential fallback, or guess a room/model.

For room diagnostic mode, global preliminary reachability SHALL NOT run against one selected model before the tree exists. The room lifecycle SHALL build the authoritative room context/tree first and apply the approved per-record credential-plan and reachability gates immediately before each eligible row's model-specific acquisition. For the legacy supported no-room IP path, the existing single-device reachability gate remains.

The permanent `Пароль` capability MAY remain as an application-level action, including inside a `Действия` menu, but it SHALL remain network-free credential configuration and SHALL NOT read model authority from Qt selector state, prior requests, prior fallback state, current screen identity, or room-row presentation.

With valid inventory, exactly one IP record whose exact canonical `diagnostic_model` is registered MAY open that model's existing credential configuration, including when the record belongs to a room; it SHALL NOT start room polling. Valid-inventory zero-record, many-record, null-model, or unsupported-model outcomes SHALL report a controlled safe configuration-resolution error and SHALL NOT open manual model fallback.

For a valid IP target when inventory is unavailable, unloadable, or corrupt, `Пароль` MAY use the existing explicit credential-configuration fallback selection under its current purpose-bound confirmation contract. A room-name target SHALL NOT select an arbitrary room record/model for credentials and SHALL NOT use credential-configuration fallback.

#### Scenario: Main panel has one search field and no model selector

- **WHEN** the main diagnostic window is constructed
- **THEN** it exposes one persistent target-search field plus model-independent application actions
- **AND** it does not expose `deviceCombo`, another persistent model selector, or the `Устройство` label

#### Scenario: Raw room query remains visible with a separate selected-room cue

- **GIVEN** the operator types `Перег` and selects a matching room from multiple suggestions
- **WHEN** room diagnostics starts and renders results
- **THEN** the search field still displays `Перег`
- **AND** a separate visible cue identifies the selected room using the deterministic suggestion label
- **AND** selected canonical `room_id` is stored separately as application authority

#### Scenario: Identical room names remain visibly distinguishable

- **GIVEN** multiple distinct canonical room IDs have the same room display name
- **WHEN** the autocomplete results are shown
- **THEN** each result has a deterministic distinguishable selection label using approved room display metadata and, if still necessary, a neutral deterministic result discriminator
- **AND** selecting one result visibly identifies that same selection without exposing raw `room_id` as operator identity

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
- **AND** the visible current-selection cue identifies the selected room
- **AND** no synthetic source record is created

#### Scenario: Room-name query has multiple room results

- **GIVEN** valid inventory room-name search returns multiple distinct canonical `room_id` values
- **WHEN** no current suggestion has been explicitly selected
- **THEN** Enter/top Refresh starts no room/device network I/O
- **AND** the operator must select one exact room result

#### Scenario: Selecting a room suggestion is network-free

- **WHEN** the operator selects one room from the autocomplete dropdown
- **THEN** application state records that exact current room candidate
- **AND** the GUI shows the corresponding current-selection cue
- **AND** no ping, credential resolution, handler acquisition, worker submission, or device network I/O starts merely from selection

#### Scenario: Search text edit invalidates selection

- **GIVEN** a room suggestion was selected for query revision N
- **WHEN** the operator edits the search field
- **THEN** the old selection and its visible selection cue are cleared
- **AND** the old selection cannot authorize a later diagnostic start
- **AND** a new resolution is required for the new query revision

#### Scenario: Repeated Refresh uses the visible current selection

- **GIVEN** a multi-match room-name query has one explicit current selection
- **AND** the raw query text has not changed
- **WHEN** top Refresh is requested again
- **THEN** the application may reuse only that same selected `room_id` if it is still a member of the current candidate set in the current inventory snapshot
- **AND** the visible selection cue continues to identify that exact selection
- **AND** otherwise the selection is invalidated and a new explicit choice is required

#### Scenario: Room-name search inventory is unavailable

- **GIVEN** the target is not a valid IPv4 address
- **WHEN** canonical inventory is unavailable, unloadable, or corrupt
- **THEN** the application reports a controlled inventory-unavailable outcome
- **AND** it does not open model fallback, credential fallback, or perform device network I/O

#### Scenario: IP target inventory is unavailable for diagnostic start

- **GIVEN** the target is a valid IPv4 address
- **WHEN** canonical inventory is unavailable, unloadable, or corrupt
- **THEN** the application automatically opens the existing fail-closed diagnostic-purpose model fallback or focused equivalent
- **AND** only a new explicit model selection and `Подключиться` confirmation may establish current diagnostic fallback authority

#### Scenario: Password resolves a supported inventory model without diagnostics

- **GIVEN** current inventory is valid
- **AND** exactly one record matches the valid IPv4 target
- **AND** its exact canonical `diagnostic_model` is registered
- **WHEN** the operator selects `Пароль`
- **THEN** credential configuration opens for that model-wide credential chain
- **AND** no ping, room cycle, handler acquisition, worker submission, or device network I/O starts

#### Scenario: Password cannot resolve a valid-inventory target

- **GIVEN** current inventory is valid
- **WHEN** IP lookup returns zero/many records or the unique record has null/unsupported `diagnostic_model`
- **THEN** the application reports a controlled safe configuration-resolution error
- **AND** it does not open manual model fallback
- **AND** it performs no device network I/O

#### Scenario: Password fallback remains available only for unavailable inventory IP context

- **GIVEN** the current target is a valid IPv4 address
- **WHEN** inventory is unavailable, unloadable, or corrupt
- **THEN** the existing explicit credential-configuration fallback selection MAY be used
- **AND** the resulting model authority is bound only to that credential-configuration purpose
- **AND** no diagnostic device I/O starts

#### Scenario: Password is not room-name model selection

- **GIVEN** the current target is a room-name query or room-name selection
- **WHEN** the operator requests credential configuration
- **THEN** no arbitrary room record/model is selected for `Пароль`
- **AND** no diagnostic or credential fallback is opened
- **AND** no device network I/O starts

#### Scenario: Legacy supported no-room IP remains available

- **GIVEN** exactly one inventory record matches the valid IPv4 target
- **AND** `room_id = null`
- **AND** its exact canonical model is registered
- **WHEN** diagnostics starts
- **THEN** the existing legacy single-device screen/lifecycle remains available
- **AND** no synthetic room is created

#### Scenario: Valid no-room unsupported IP remains fail-closed

- **GIVEN** current inventory is valid
- **AND** exactly one record matches the valid IPv4 target
- **AND** `room_id = null`
- **AND** its canonical model is null or unsupported
- **WHEN** diagnostic start is requested
- **THEN** no page, credential chain, handler, worker, controller, or manual model fallback is selected
- **AND** the application reports a safe unsupported/unmapped outcome

#### Scenario: Legacy preliminary reachability validation remains in force

- **GIVEN** a final exact legacy single-device automatic or confirmed-fallback diagnostic model has been assigned for a valid IP
- **WHEN** preliminary reachability validation fails
- **THEN** the application displays the existing controlled warning
- **AND** it does not start the assigned device diagnostic worker/controller network operation

#### Scenario: Room-row preliminary reachability validation remains in force

- **GIVEN** room mode is active and a supported eligible row reaches its queue turn
- **WHEN** that exact row fails preliminary reachability validation
- **THEN** the row receives a controlled terminal failure
- **AND** its assigned model-specific worker/controller does not start
- **AND** later eligible room rows remain eligible to run
