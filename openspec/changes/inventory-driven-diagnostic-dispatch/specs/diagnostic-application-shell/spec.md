# diagnostic-application-shell Specification

## MODIFIED Requirements

### Requirement: Device selection and refresh input validation

The main window SHALL expose only exact device models present in the closed application diagnostic-dispatch registry as selectable manual diagnostic targets and SHALL route each target to its registered codec, matrix, PDU, or audio-DSP screen and existing lifecycle path.

A user-initiated Refresh or equivalent Enter action SHALL reject an empty or malformed IPv4 address before inventory resolution. For a valid normalized IPv4 address, the application SHALL resolve the current inventory/manual selection context before model-specific credential resolution, preliminary reachability validation, handler acquisition, worker/controller submission, or device network I/O.

When inventory dispatch resolves one exact supported canonical `diagnostic_model`, that model's registered page and lifecycle SHALL become the assigned request context. When inventory dispatch is unavailable or unresolved, the existing manual selection path SHALL remain available. Preliminary reachability failure after the final model is assigned SHALL stop before starting the assigned device worker/controller network operation.

#### Scenario: Valid supported inventory-assisted refresh

- **GIVEN** a valid current inventory contains exactly one record for the normalized IP
- **AND** that record has an exact `diagnostic_model` present in the closed dispatch registry
- **WHEN** the operator starts Refresh or the equivalent Enter action
- **THEN** the matching registered screen and existing model-specific lifecycle are assigned
- **AND** model-specific credentials and reachability checks use only that assigned model
- **AND** the device diagnostic starts only after those checks succeed

#### Scenario: Inventory cannot assign a supported model

- **WHEN** inventory is unavailable, the IP has zero or multiple records, the one record has null `diagnostic_model`, or its exact model is not registered
- **THEN** the application does not guess a model or page
- **AND** the existing manual model selector remains available for diagnostic startup

#### Scenario: Invalid refresh input

- **WHEN** the IP field is empty or malformed
- **THEN** the application displays a warning
- **AND** it does not query inventory, resolve model-specific credentials, perform preliminary reachability validation, acquire a handler, submit a worker/controller operation, or perform device network I/O

#### Scenario: Preliminary reachability validation fails

- **GIVEN** the final automatic or manual model has been assigned for a valid IP
- **WHEN** preliminary reachability validation fails
- **THEN** the application displays the existing controlled warning
- **AND** it does not start the assigned device diagnostic worker/controller network operation

## ADDED Requirements

### Requirement: Inventory-driven diagnostic dispatch uses exact canonical diagnostic_model

The application/composition layer SHALL own inventory-driven diagnostic dispatch. For a valid normalized IP and current immutable `EquipmentInventory`, it SHALL call `find_by_ip(...)`, classify the complete returned tuple as zero, one, or many, and inspect canonical fields only when exactly one total record exists.

For one record, automatic dispatch SHALL use only the record's exact non-null canonical `diagnostic_model`. The application SHALL NOT derive, repair, or choose a model from `device_kind`, `source_model`, manufacturer/model evidence, substring or fuzzy matching, aliases, handler availability, source row order, registry order, or protocol failure.

The closed dispatch registry SHALL be exactly:

| Exact canonical `diagnostic_model` | Screen key | Existing diagnostic lifecycle |
| --- | --- | --- |
| `Huawei TE20` | `codec` | Huawei TE20 refresh path |
| `Huawei TE40` | `codec` | Huawei TE40 refresh path |
| `CloudLink Bar 310` | `codec` | CloudLink Bar 310 refresh path |
| `Polycom RPG 310` | `codec` | Polycom RPG 310 refresh path |
| `Extron IN1804` | `matrix` | `MatrixController` refresh path |
| `Aten PE8208AV` | `pdu` | `PDUController` with exact Aten model context |
| `Extron IPL T PCS4i` | `pdu` | `PDUController` with exact PCS4i model context |
| `Biamp Tesira Forte CI` | `audio_dsp` | existing Biamp polling path |
| `Extron DMP 64 Plus` | `audio_dsp` | `DMPPollingController` refresh path |

Each exact model SHALL have one and only one dispatch entry. Unknown models SHALL have no default route. The implementation SHALL prevent silent drift between selectable manual models, page registration, and lifecycle routing.

The registry SHALL contain no credentials, credential candidate lists, successful indexes, handler/session/transport instances, cookies/tokens, or mutable worker state.

#### Scenario: Unique Aten record selects PDU diagnostics

- **GIVEN** exactly one inventory record matches the current IP
- **AND** its `diagnostic_model` is exactly `Aten PE8208AV`
- **AND** its `device_kind` is `other`
- **WHEN** inventory dispatch is accepted
- **THEN** the application assigns the `pdu` screen and exact Aten `PDUController` path
- **AND** `device_kind = other` does not block or alter dispatch

#### Scenario: Unique PCS4i record selects PDU diagnostics

- **GIVEN** exactly one inventory record matches the current IP
- **AND** its `diagnostic_model` is exactly `Extron IPL T PCS4i`
- **AND** its `device_kind` is `other`
- **WHEN** inventory dispatch is accepted
- **THEN** the application assigns the `pdu` screen and exact PCS4i `PDUController` path

#### Scenario: Unique TE40 record selects codec diagnostics

- **GIVEN** exactly one inventory record matches the current IP
- **AND** its `diagnostic_model` is exactly `Huawei TE40`
- **WHEN** inventory dispatch is accepted
- **THEN** the application assigns the `codec` screen and Huawei TE40 refresh path

#### Scenario: Unique IN1804 record selects Matrix diagnostics

- **GIVEN** exactly one inventory record matches the current IP
- **AND** its `diagnostic_model` is exactly `Extron IN1804`
- **WHEN** inventory dispatch is accepted
- **THEN** the application assigns the `matrix` screen and `MatrixController` refresh path

#### Scenario: Device kind alone grants no route

- **GIVEN** one inventory record has `device_kind = other`
- **AND** its `diagnostic_model` is null or unsupported
- **WHEN** inventory dispatch evaluates the record
- **THEN** no automatic page or lifecycle is selected
- **AND** the application does not infer a route from kind or source text

#### Scenario: Unknown exact model has no default route

- **GIVEN** one inventory record has a non-null canonical `diagnostic_model` absent from the closed registry
- **WHEN** inventory dispatch evaluates the record
- **THEN** the outcome is unsupported
- **AND** the application does not default to the codec page, a same-kind page, or the nearest available handler

### Requirement: Inventory dispatch preserves complete IP cardinality and manual fallback

The application SHALL classify the complete `find_by_ip(...)` result before filtering or ranking by `device_kind`, `diagnostic_model`, source text, screen support, or handler availability.

Observable dispatch outcomes SHALL distinguish at least:

```text
inventory unavailable
IP not found
ambiguous duplicate IP
one record with null diagnostic_model
one record with unsupported diagnostic_model
one record with supported diagnostic_model
explicit manual override
```

Concrete private type names are not normative, but these outcomes SHALL remain independently testable. Inventory-unavailable and unresolved outcomes SHALL not be treated as device connection failure, shall not start automatic modal network-error presentation, and SHALL preserve the manual selector and existing direct manual diagnostic flow.

The application SHALL NOT select `records[0]`, the first supported record, the only familiar `device_kind`, or a record favored by registry order when multiple total records share one IP.

#### Scenario: IP is absent from inventory

- **WHEN** `find_by_ip(...)` returns zero records
- **THEN** no automatic model, page, controller, handler, or worker is selected
- **AND** the current supported manual selection remains available

#### Scenario: Duplicate IP is ambiguous before filtering

- **GIVEN** two or more total records share the normalized IP
- **WHEN** inventory dispatch evaluates that IP
- **THEN** the outcome is ambiguous
- **AND** the application does not inspect the records to select a preferred kind, supported model, page, or handler
- **AND** the current supported manual selection remains available

#### Scenario: One record has no recognized model

- **GIVEN** exactly one record matches the normalized IP
- **AND** its `diagnostic_model` is null
- **WHEN** inventory dispatch evaluates the record
- **THEN** no automatic model or page is selected
- **AND** source-model or manufacturer evidence is not reanalyzed at runtime
- **AND** manual selection remains available

#### Scenario: Inventory is unavailable

- **WHEN** no valid immutable inventory is loaded
- **THEN** the application exposes a controlled inventory-unavailable fallback
- **AND** startup and existing manual codec, Matrix, PDU, and audio-DSP diagnostics remain available

### Requirement: Manual diagnostic override remains request-context-local

After an accepted inventory-assisted selection for a normalized IP, an explicit operator selection of another registered exact model SHALL create a manual override bound to the current normalized IP, current immutable inventory context, and current application selection context.

A current override SHALL cause the next diagnostic start in that bound context to use only the explicitly selected registry entry. The application SHALL make the inventory/manual discrepancy observable without exposing full source records, production inventory, or secrets.

Manual override SHALL NOT mutate or replace an `EquipmentRecord`, change `EquipmentInventory`, write the workbook or canonical JSON, persist a new canonical model, add an alias, or affect another IP/inventory context. It SHALL be invalidated by normalized IP change, inventory replacement/reload or availability change, application reset, or shutdown.

The selector's visible text alone SHALL NOT be freshness authority. Application state SHALL distinguish an accepted automatic selection from an explicit operator override so stale automatic results cannot overwrite newer user intent.

#### Scenario: Operator overrides an accepted inventory model

- **GIVEN** inventory dispatch accepted one exact supported model for the current IP
- **WHEN** the operator explicitly selects a different registered model and starts diagnostics in the same current context
- **THEN** the application assigns the manually selected model's page and lifecycle for that request
- **AND** credentials are resolved only for the manual model
- **AND** the inventory remains unchanged

#### Scenario: IP change invalidates manual override

- **GIVEN** a manual override is bound to one normalized IP
- **WHEN** the IP field changes to a different normalized IP
- **THEN** the old override is no longer current
- **AND** the next diagnostic start may resolve the new IP through inventory

#### Scenario: Override never teaches runtime recognition

- **WHEN** a manual override succeeds for an inventory record with null or unsupported `diagnostic_model`
- **THEN** the application does not persist the selected model as canonical data or an alias
- **AND** a later independent context remains unresolved unless its canonical inventory data supports dispatch

### Requirement: Inventory dispatch freshness is application-owned and precedes I/O

Every user-initiated inventory-assisted diagnostic start SHALL create a distinct application dispatch generation, including repeated starts for the same IP and model.

An accepted dispatch binding SHALL include at least the generation, normalized IP, immutable inventory context/revision identity, selection source or manual-override binding, and resolved exact model when present.

IP change, explicit model change, new or repeated Refresh/Enter, inventory replacement/availability change, reset, and shutdown SHALL supersede older pending dispatch work immediately.

A stale lookup or result SHALL be rejected before model-specific credential resolution, handler acquisition, worker/controller submission, and network I/O. It SHALL NOT change the selector, visible page, room/VIP presentation, credentials, controller operation, successful credential/profile memory, or PDU-related-codec enrichment.

The application MAY execute the bounded in-memory inventory query synchronously. It SHALL NOT reread JSON, parse Excel, or perform network I/O on the Qt GUI thread. If lookup is queued or asynchronous, all publication SHALL still pass the same current-generation and binding checks.

After accepted dispatch enters an existing device-specific lifecycle, the already approved Matrix, PDU, DMP, codec, or audio-DSP controller/request authority SHALL remain the sole authority for that device operation. Dispatch SHALL NOT create a second device-operation freshness authority.

#### Scenario: New IP supersedes an older pending lookup

- **GIVEN** an older lookup/result is pending for IP A
- **WHEN** the operator changes the input to IP B or starts a newer request
- **THEN** the older dispatch generation is stale
- **AND** its result cannot alter the selected model/page, resolve credentials, acquire a handler, submit work, or perform network I/O

#### Scenario: Repeat refresh creates a new dispatch generation

- **GIVEN** one dispatch for the current IP/model has started or completed
- **WHEN** the operator starts Refresh again
- **THEN** the application creates a distinct newer dispatch generation
- **AND** callbacks or queued results from the prior generation cannot affect the new request context

#### Scenario: Lookup remains non-blocking with respect to external I/O

- **WHEN** the application resolves an IP from the loaded inventory
- **THEN** it uses only the in-memory immutable inventory query
- **AND** it does not load Excel, reread the deployment JSON, or perform device/network I/O on the GUI thread

### Requirement: Inventory dispatch ownership does not leak into screens, handlers, or workers

`EquipmentInventory` SHALL return canonical records and multiplicity only. It SHALL NOT choose GUI pages, lifecycle routes, fallback models, or manual outcomes.

Screens SHALL render accepted state and publish existing non-secret user intents. They SHALL NOT query inventory, interpret multiplicity, infer model support, choose another screen, or start device network work.

Controllers, handlers, sessions, and workers SHALL receive one already assigned exact model/IP operation context through the existing application wiring. They SHALL NOT receive the complete IP-match tuple or a list of candidate diagnostic models and SHALL NOT search inventory, analyze `source_model` or importer evidence, choose a page, iterate models, or switch models after authentication, transport, protocol, parser, timeout, or ambiguous-result failure.

#### Scenario: Handler receives one assigned model path

- **WHEN** application dispatch accepts an automatic or manual model
- **THEN** the selected existing lifecycle receives only its assigned exact model/IP and approved credential context
- **AND** no handler or worker receives all inventory matches or alternative model candidates

#### Scenario: Device failure does not trigger model guessing

- **WHEN** the assigned diagnostic path reports authentication, transport, protocol, parser, timeout, or another device failure
- **THEN** existing retry and credential policies apply only within that assigned model path
- **AND** the application, handler, and worker do not retry with another diagnostic model

#### Scenario: PDU enrichment remains gated by accepted PDU success

- **GIVEN** inventory dispatch assigns Aten or PCS4i to the PDU page/controller
- **WHEN** the PDU diagnostic starts
- **THEN** related-room/codec enrichment does not start from dispatch alone
- **AND** it starts only after `PDUController` accepts a current successful user refresh under its existing contract
