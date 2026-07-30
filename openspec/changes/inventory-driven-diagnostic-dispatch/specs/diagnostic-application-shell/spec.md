# diagnostic-application-shell Specification

## MODIFIED Requirements

### Requirement: Device selection and refresh input validation

The main window connection panel SHALL use the IP address as its only permanent diagnostic-target input. It SHALL NOT expose a persistent device-model selector, a `deviceCombo` equivalent, or the `Устройство` label. The application/composition layer SHALL hold the accepted exact model in request context only after current inventory resolution or confirmed unresolved-inventory fallback.

A user-initiated Refresh or equivalent Enter action SHALL reject an empty or malformed IPv4 address before inventory resolution. For a valid normalized IPv4 address, the application SHALL resolve current inventory context before model-specific credential resolution, preliminary reachability validation, handler acquisition, worker/controller submission, or device network I/O.

When inventory resolves one exact supported canonical `diagnostic_model`, that model SHALL be authoritative for the current request and its registered page and existing lifecycle SHALL be assigned without offering an ordinary manual override. When inventory is unavailable or unresolved, the application SHALL automatically open a fail-closed `DeviceModelFallbackDialog` or focused equivalent. Only a new explicit model selection and `Подключиться` confirmation in that dialog MAY create the manual-fallback request context.

Preliminary reachability failure after the final exact model is assigned SHALL stop before starting the assigned device worker/controller network operation.

#### Scenario: Main panel has no persistent model selector

- **WHEN** the main diagnostic window is constructed
- **THEN** the permanent connection panel exposes the IP input and model-independent actions
- **AND** it does not expose `deviceCombo`, another persistent model selector, or the `Устройство` label
- **AND** no default or previous Qt selection acts as request-model authority

#### Scenario: Valid supported inventory-assisted refresh

- **GIVEN** a valid current inventory contains exactly one record for the normalized IP
- **AND** that record has an exact `diagnostic_model` present in the closed dispatch registry
- **WHEN** the operator starts Refresh or the equivalent Enter action
- **THEN** the exact inventory model becomes the authoritative request model
- **AND** the matching registered screen and existing model-specific lifecycle are assigned
- **AND** model-specific credentials and reachability checks use only that assigned model
- **AND** no fallback dialog or manual override is offered for that request
- **AND** the device diagnostic starts only after required checks succeed

#### Scenario: Inventory cannot assign a supported model

- **WHEN** inventory is unavailable, the IP has zero or multiple records, the one record has null `diagnostic_model`, or its exact model is not registered
- **THEN** the application selects no automatic model, page, credential chain, handler, worker, or controller
- **AND** it automatically opens the fallback dialog with a safe unresolved reason

#### Scenario: Invalid refresh input

- **WHEN** the IP field is empty or malformed
- **THEN** the application displays a controlled warning
- **AND** it does not query inventory, open the fallback dialog, resolve model-specific credentials, perform preliminary reachability validation, acquire a handler, submit a worker/controller operation, or perform device network I/O

#### Scenario: Preliminary reachability validation fails

- **GIVEN** a final exact automatic or confirmed-fallback model has been assigned for a valid IP
- **WHEN** preliminary reachability validation fails
- **THEN** the application displays the existing controlled warning
- **AND** it does not start the assigned device diagnostic worker/controller network operation

## ADDED Requirements

### Requirement: Inventory-driven diagnostic dispatch uses exact canonical diagnostic_model

The application/composition layer SHALL own inventory-driven diagnostic dispatch. For a valid normalized IP and current immutable `EquipmentInventory`, it SHALL call `find_by_ip(...)`, classify the complete returned tuple as zero, one, or many, and inspect canonical fields only when exactly one total record exists.

For one record, automatic dispatch SHALL use only its exact non-null canonical `diagnostic_model`. The application SHALL NOT derive, repair, or choose a model from `device_kind`, `source_model`, manufacturer/model evidence, substring or fuzzy matching, aliases, handler availability, source row order, registry order, prior user selection, or protocol failure.

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

Each exact model SHALL have one and only one dispatch entry. Unknown models SHALL have no default route. Fallback dialog choices, page registration, and lifecycle routing SHALL derive from or be integrity-checked against this same closed registry.

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

- **GIVEN** one inventory record has any canonical `device_kind`
- **AND** its `diagnostic_model` is null or unsupported
- **WHEN** inventory dispatch evaluates the record
- **THEN** no automatic page or lifecycle is selected
- **AND** the application does not infer a route from kind or source text

#### Scenario: Unknown exact model has no default route

- **GIVEN** one inventory record has a non-null canonical `diagnostic_model` absent from the closed registry
- **WHEN** inventory dispatch evaluates the record
- **THEN** the outcome is unsupported
- **AND** the application does not default to codec, a same-kind page, or the nearest handler

### Requirement: Inventory dispatch preserves complete IP cardinality

The application SHALL classify the complete `find_by_ip(...)` result before filtering or ranking by `device_kind`, `diagnostic_model`, source text, screen support, or handler availability.

Observable automatic outcomes SHALL distinguish at least:

```text
INVENTORY_UNAVAILABLE
IP_NOT_FOUND
AMBIGUOUS_IP
MODEL_UNMAPPED
MODEL_UNSUPPORTED
RESOLVED
```

Concrete private type names are not normative, but these outcomes SHALL remain independently testable. An unresolved outcome SHALL not be treated as a device connection failure, SHALL not start automatic modal network-error presentation, and SHALL open the controlled fallback dialog.

The application SHALL NOT select `records[0]`, the first supported record, the only familiar `device_kind`, or a record favored by registry order when multiple total records share one IP.

#### Scenario: IP is absent from inventory

- **WHEN** `find_by_ip(...)` returns zero records
- **THEN** no automatic model, page, credentials, controller, handler, or worker is selected
- **AND** the application opens fallback with the safe not-found reason

#### Scenario: Duplicate IP is ambiguous before filtering

- **GIVEN** two or more total records share the normalized IP
- **WHEN** inventory dispatch evaluates that IP
- **THEN** the outcome is ambiguous
- **AND** the application does not inspect the records to select a preferred kind, model, page, or handler
- **AND** it opens fallback with the safe ambiguity reason

#### Scenario: One record has no recognized model

- **GIVEN** exactly one record matches the normalized IP
- **AND** its `diagnostic_model` is null
- **WHEN** inventory dispatch evaluates the record
- **THEN** no automatic model or page is selected
- **AND** source-model or manufacturer evidence is not reanalyzed at runtime
- **AND** fallback opens with the safe unmapped reason

#### Scenario: Inventory is unavailable

- **WHEN** no valid immutable inventory is loaded
- **THEN** the application opens controlled fallback with the safe inventory category
- **AND** it performs no model-specific work before explicit confirmation

### Requirement: Unresolved inventory uses an explicit fail-closed model fallback dialog

For every unresolved automatic outcome, the application SHALL open `DeviceModelFallbackDialog` or a focused equivalent bound to the current dispatch generation, normalized IP, and immutable inventory context.

The dialog SHALL display a safe unresolved reason and only models from the closed dispatch registry. It SHALL NOT receive or display complete inventory records, source rows, credentials, handlers, workers, sessions, transports, or secrets.

No model SHALL be accepted merely because it is first, previously chosen, or remembered. `Подключиться` SHALL remain disabled or confirmation SHALL be rejected until the operator explicitly selects one model during the current dialog interaction.

Only explicit selection plus `Подключиться` confirmation MAY create a `MANUAL_FALLBACK` request context and continue to model-specific credentials and reachability checks. Fallback selection SHALL NOT mutate or persist inventory, workbook, JSON, aliases, or canonical model memory.

Cancel and window close SHALL dismiss the start, return or retain the application in `IDLE`, and perform no model-specific credential resolution, ping, handler acquisition, worker/controller creation or submission, page lifecycle start, or device network I/O.

Fallback SHALL NOT be available as an override after a `RESOLVED` automatic outcome.

#### Scenario: Operator confirms a fallback model

- **GIVEN** automatic inventory resolution is unresolved
- **AND** the current fallback dialog is open with no accepted model
- **WHEN** the operator explicitly selects one registered model and confirms `Подключиться`
- **THEN** the application creates a current `MANUAL_FALLBACK` request context for that exact model and IP
- **AND** only then may it resolve model-specific credentials and perform reachability validation
- **AND** the inventory remains unchanged

#### Scenario: No implicit first or previous selection

- **GIVEN** fallback opens for an unresolved IP
- **WHEN** the operator has not explicitly selected a model in this dialog interaction
- **THEN** no model is accepted from item order, prior dialog state, or former main-window state
- **AND** confirmation cannot start diagnostics

#### Scenario: Operator cancels fallback

- **GIVEN** fallback is open
- **WHEN** the operator activates Cancel
- **THEN** the application returns or remains in `IDLE`
- **AND** no model-specific credentials, ping, handler, worker/controller, page lifecycle, or device I/O starts

#### Scenario: Operator closes fallback window

- **GIVEN** fallback is open
- **WHEN** the dialog is closed through the window controls
- **THEN** the result is equivalent to Cancel
- **AND** the start fails closed with zero model-specific work or device I/O

#### Scenario: Resolved inventory cannot be overridden

- **GIVEN** inventory dispatch accepted one exact registered model
- **WHEN** the request proceeds
- **THEN** the automatic model remains authoritative for that request
- **AND** no fallback dialog or ordinary UI control permits replacement with another model

### Requirement: Inventory dispatch freshness is application-owned and precedes I/O

Every user-initiated diagnostic start SHALL create a distinct application dispatch generation, including repeated starts for the same IP and model.

An accepted binding SHALL include at least generation, normalized IP, immutable inventory context/revision identity, automatic outcome, selection source (`AUTO_INVENTORY` or `MANUAL_FALLBACK`), exact assigned model when present, and current fallback-dialog binding when open.

IP change, new or repeated Refresh/Enter, inventory replacement/availability change, reset, and shutdown SHALL supersede older pending lookup and fallback work immediately.

A stale lookup, dialog selection, or dialog confirmation SHALL be rejected before model-specific credential resolution, handler acquisition, worker/controller submission, and network I/O. It SHALL NOT publish a model request context, change the visible page, change room/VIP presentation, alter credentials, start a controller operation, persist successful credential/profile memory, or start PDU-related-codec enrichment.

The application MAY execute the bounded in-memory inventory query synchronously. It SHALL NOT reread JSON, parse Excel, or perform network I/O on the Qt GUI thread. If lookup is queued or asynchronous, all publication SHALL pass the same binding checks.

After accepted dispatch enters an existing device-specific lifecycle, the approved Matrix, PDU, DMP, codec, or audio-DSP authority SHALL remain sole authority for that device operation. Dispatch SHALL NOT create a second operation-generation authority.

#### Scenario: New IP supersedes an older pending lookup or dialog

- **GIVEN** an older lookup result or fallback dialog is pending for IP A
- **WHEN** the operator changes the input to IP B or starts a newer request
- **THEN** the older binding is stale
- **AND** its result or confirmation cannot publish a model, resolve credentials, acquire a handler, submit work, change pages, or perform I/O

#### Scenario: Repeat refresh creates a new dispatch generation

- **GIVEN** one dispatch for the current IP has started or completed
- **WHEN** the operator starts Refresh again
- **THEN** the application creates a distinct newer dispatch generation
- **AND** old lookup/dialog actions cannot affect the new request context

#### Scenario: Lookup remains external-I/O-free

- **WHEN** the application resolves an IP from loaded inventory
- **THEN** it uses only the immutable in-memory query
- **AND** it does not load Excel, reread deployment JSON, or perform device/network I/O on the GUI thread

### Requirement: Inventory dispatch ownership does not leak into dialogs, screens, handlers, or workers

`EquipmentInventory` SHALL return canonical records and multiplicity only. It SHALL NOT choose pages, lifecycle routes, fallback models, or UI outcomes.

The fallback dialog SHALL render safe reason/model choices and publish non-secret selection, confirmation, and cancellation intent only. It SHALL NOT query inventory, resolve credentials, acquire handlers, submit work, or perform network I/O.

Diagnostic screens SHALL render accepted state and publish existing non-secret device intents. They SHALL NOT query inventory, interpret multiplicity, infer model support, choose another screen, or start another model lifecycle.

Controllers, handlers, sessions, and workers SHALL receive one already assigned exact model/IP operation context through existing application wiring. They SHALL NOT receive the complete IP-match tuple or candidate-model list and SHALL NOT search inventory, analyze `source_model` or importer evidence, choose pages, iterate models, or switch models after authentication, transport, protocol, parser, timeout, or ambiguous-result failure.

#### Scenario: Assigned lifecycle receives one model path

- **WHEN** application dispatch accepts an automatic or confirmed-fallback model
- **THEN** the selected existing lifecycle receives only its exact model/IP and approved credential context
- **AND** no dialog, handler, or worker receives all inventory matches or alternative model candidates

#### Scenario: Device failure does not trigger model guessing

- **WHEN** the assigned path reports authentication, transport, protocol, parser, timeout, or another device failure
- **THEN** existing retry and credential policies apply only within that exact model path
- **AND** no component retries with another diagnostic model

#### Scenario: PDU enrichment remains gated by accepted PDU success

- **GIVEN** dispatch assigns Aten or PCS4i to the PDU page/controller
- **WHEN** the PDU diagnostic starts
- **THEN** related-room/codec enrichment does not start from dispatch alone
- **AND** it starts only after `PDUController` accepts a current successful user refresh under the modified exact-model enrichment contract