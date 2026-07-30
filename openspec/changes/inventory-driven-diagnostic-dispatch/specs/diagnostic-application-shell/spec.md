# diagnostic-application-shell Specification

## MODIFIED Requirements

### Requirement: Device selection and refresh input validation

The main window connection panel SHALL use the IP address as its only permanent diagnostic-target input. It SHALL NOT expose a persistent device-model selector, a `deviceCombo` equivalent, or the `Устройство` label. The permanent `Пароль` action MAY remain, but it SHALL resolve its exact model through the application-owned credential-configuration flow defined by this capability and SHALL NOT read a model from Qt selector state, previous request state, or previous fallback state.

The application/composition layer SHALL hold an accepted exact model only in a current purpose-bound context after exact inventory resolution or confirmed unresolved-inventory fallback.

A user-initiated Refresh or equivalent Enter action SHALL reject an empty or malformed IPv4 address before inventory resolution. For a valid normalized IPv4 address, the application SHALL resolve current inventory context before model-specific credential resolution, preliminary reachability validation, handler acquisition, worker/controller submission, or device network I/O.

When inventory resolves one exact supported canonical `diagnostic_model`, that model SHALL be authoritative for the current diagnostic request and its registered page and existing lifecycle SHALL be assigned without offering an ordinary manual override. When inventory is unavailable or unresolved, the application SHALL automatically open a fail-closed `DeviceModelFallbackDialog` or focused equivalent. Only a new explicit model selection and `Подключиться` confirmation in a dialog bound to diagnostic-start purpose MAY create the manual-fallback diagnostic request context.

Preliminary reachability failure after the final exact diagnostic model is assigned SHALL stop before starting the assigned device worker/controller network operation.

#### Scenario: Main panel has no persistent model selector

- **WHEN** the main diagnostic window is constructed
- **THEN** the permanent connection panel exposes the IP input and model-independent actions
- **AND** it does not expose `deviceCombo`, another persistent model selector, or the `Устройство` label
- **AND** no default or previous Qt selection acts as model authority

#### Scenario: Password action has no widget model authority

- **WHEN** the main window exposes the permanent `Пароль` action
- **THEN** that action does not read a model from `deviceCombo`, current screen, window title, prior diagnostic request, prior fallback, or another Qt presentation value
- **AND** it begins the purpose-bound credential-configuration resolution flow

#### Scenario: Valid supported inventory-assisted refresh

- **GIVEN** a valid current inventory contains exactly one record for the normalized IP
- **AND** that record has an exact `diagnostic_model` present in the closed dispatch registry
- **WHEN** the operator starts Refresh or equivalent Enter action
- **THEN** the exact inventory model becomes the authoritative diagnostic request model
- **AND** the matching registered screen and existing model-specific lifecycle are assigned
- **AND** model-specific credentials and reachability checks use only that assigned model
- **AND** no fallback dialog or manual override is offered for that diagnostic request
- **AND** the device diagnostic starts only after required checks succeed

#### Scenario: Inventory cannot assign a supported diagnostic model

- **WHEN** inventory is unavailable, the IP has zero or multiple records, the one record has null `diagnostic_model`, or its exact model is not registered
- **THEN** the application selects no automatic model, page, credential chain, handler, worker, or controller
- **AND** it automatically opens diagnostic-purpose fallback with a safe unresolved reason

#### Scenario: Invalid refresh input

- **WHEN** the IP field is empty or malformed
- **THEN** the application displays a controlled warning
- **AND** it does not query inventory, open fallback, resolve model-specific credentials, perform preliminary reachability validation, acquire a handler, submit a worker/controller operation, or perform device network I/O

#### Scenario: Preliminary reachability validation fails

- **GIVEN** a final exact automatic or confirmed-fallback diagnostic model has been assigned for a valid IP
- **WHEN** preliminary reachability validation fails
- **THEN** the application displays the existing controlled warning
- **AND** it does not start the assigned device diagnostic worker/controller network operation

## ADDED Requirements

### Requirement: Inventory-driven diagnostic dispatch uses exact canonical diagnostic_model

The application/composition layer SHALL own inventory-driven diagnostic dispatch. For a valid normalized IP and current immutable `EquipmentInventory`, it SHALL call `find_by_ip(...)`, classify the complete returned tuple as zero, one, or many, and inspect canonical fields only when exactly one total record exists.

For one record, automatic dispatch SHALL use only its exact non-null canonical `diagnostic_model`. The application SHALL NOT derive, repair, or choose a model from `device_kind`, `source_model`, manufacturer/model evidence, substring or fuzzy matching, aliases, handler availability, source row order, registry order, prior user selection, prior request context, or protocol failure.

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

Each exact model SHALL have one and only one registry entry. Unknown models SHALL have no default route. Diagnostic fallback choices, credential-configuration fallback choices, page registration, and lifecycle routing SHALL derive from or be integrity-checked against this same closed registry.

The registry SHALL contain no credentials, credential candidate lists, successful indexes, handler/session/transport instances, cookies/tokens, or mutable worker state.

#### Scenario: Unique Aten record selects PDU diagnostics

- **GIVEN** exactly one inventory record matches the current IP
- **AND** its `diagnostic_model` is exactly `Aten PE8208AV`
- **AND** its `device_kind` is `other`
- **WHEN** diagnostic inventory dispatch is accepted
- **THEN** the application assigns the `pdu` screen and exact Aten `PDUController` path
- **AND** `device_kind = other` does not block or alter dispatch

#### Scenario: Unique PCS4i record selects PDU diagnostics

- **GIVEN** exactly one inventory record matches the current IP
- **AND** its `diagnostic_model` is exactly `Extron IPL T PCS4i`
- **AND** its `device_kind` is `other`
- **WHEN** diagnostic inventory dispatch is accepted
- **THEN** the application assigns the `pdu` screen and exact PCS4i `PDUController` path

#### Scenario: Unique TE40 record selects codec diagnostics

- **GIVEN** exactly one inventory record matches the current IP
- **AND** its `diagnostic_model` is exactly `Huawei TE40`
- **WHEN** diagnostic inventory dispatch is accepted
- **THEN** the application assigns the `codec` screen and Huawei TE40 refresh path

#### Scenario: Unique IN1804 record selects Matrix diagnostics

- **GIVEN** exactly one inventory record matches the current IP
- **AND** its `diagnostic_model` is exactly `Extron IN1804`
- **WHEN** diagnostic inventory dispatch is accepted
- **THEN** the application assigns the `matrix` screen and `MatrixController` refresh path

#### Scenario: Device kind alone grants no route or credential model

- **GIVEN** one inventory record has any canonical `device_kind`
- **AND** its `diagnostic_model` is null or unsupported
- **WHEN** application model resolution evaluates the record
- **THEN** no automatic page, lifecycle, or credential-model context is selected
- **AND** the application does not infer a model from kind or source text

#### Scenario: Unknown exact model has no default route

- **GIVEN** one inventory record has a non-null canonical `diagnostic_model` absent from the closed registry
- **WHEN** application model resolution evaluates the record
- **THEN** the outcome is unsupported
- **AND** the application does not default to codec, a same-kind page, the nearest handler, or a prior model

### Requirement: Application model resolution preserves complete IP cardinality

The application SHALL classify the complete `find_by_ip(...)` result before filtering or ranking by `device_kind`, `diagnostic_model`, source text, screen support, handler availability, or action purpose.

Observable outcomes SHALL distinguish at least:

```text
INVENTORY_UNAVAILABLE
IP_NOT_FOUND
AMBIGUOUS_IP
MODEL_UNMAPPED
MODEL_UNSUPPORTED
RESOLVED
```

The same exact cardinality and canonical-model interpretation SHALL be used by diagnostic startup and model-bound credential configuration. Concrete private types are not normative, but the outcomes SHALL remain independently testable.

An unresolved outcome SHALL not be treated as a device connection failure and SHALL not start automatic modal network-error presentation. The requesting action MAY open only its controlled purpose-bound fallback.

The application SHALL NOT select `records[0]`, the first supported record, the only familiar `device_kind`, or a record favored by registry order when multiple total records share one IP.

#### Scenario: IP is absent from inventory

- **WHEN** `find_by_ip(...)` returns zero records
- **THEN** no automatic model, page, credentials, controller, handler, or worker is selected
- **AND** the requesting action opens fallback with the safe not-found reason

#### Scenario: Duplicate IP is ambiguous before filtering

- **GIVEN** two or more total records share the normalized IP
- **WHEN** application model resolution evaluates that IP
- **THEN** the outcome is ambiguous
- **AND** the application does not inspect the records to select a preferred kind, model, page, credential key, or handler
- **AND** the requesting action opens fallback with the safe ambiguity reason

#### Scenario: One record has no recognized model

- **GIVEN** exactly one record matches the normalized IP
- **AND** its `diagnostic_model` is null
- **WHEN** application model resolution evaluates the record
- **THEN** no automatic model or page is selected
- **AND** source-model or manufacturer evidence is not reanalyzed at runtime
- **AND** the requesting action opens fallback with the safe unmapped reason

#### Scenario: Inventory is unavailable

- **WHEN** no valid immutable inventory is loaded
- **THEN** the requesting action opens controlled fallback with the safe inventory category
- **AND** it performs no model-specific work before explicit confirmation

### Requirement: Unresolved inventory uses an explicit purpose-bound fail-closed model fallback dialog

For every unresolved automatic outcome, the application SHALL open `DeviceModelFallbackDialog` or a focused equivalent bound to the current action purpose, action generation, normalized IP, and immutable inventory context.

Supported purposes SHALL include:

```text
DIAGNOSTIC_START
CREDENTIAL_CONFIGURATION
```

The dialog SHALL display a safe unresolved reason and only models from the closed dispatch registry. It SHALL NOT receive or display complete inventory records, source rows, credential values, handlers, workers, sessions, transports, or secrets.

No model SHALL be accepted merely because it is first, previously chosen, remembered, present in a prior request context, or visible on a diagnostic page. Confirmation SHALL remain disabled or be rejected until the operator explicitly selects one model during the current dialog interaction.

For `DIAGNOSTIC_START`, explicit selection plus `Подключиться` MAY create a `MANUAL_FALLBACK` diagnostic request context and continue to model-specific credentials and reachability checks.

For `CREDENTIAL_CONFIGURATION`, explicit selection plus `Продолжить` or equivalent non-connection confirmation MAY create a model-bound credential-configuration context and open the credential dialog only. It SHALL NOT create a diagnostic request context or start diagnostics.

Fallback selection SHALL NOT mutate or persist inventory, workbook, JSON, aliases, or canonical model memory. Cancel and window close SHALL dismiss the requesting action, return or retain controlled idle/current presentation, and perform no purpose-specific mutation or device I/O.

Fallback SHALL NOT be available as an override after a `RESOLVED` diagnostic outcome.

#### Scenario: Operator confirms diagnostic fallback

- **GIVEN** diagnostic-start resolution is unresolved
- **AND** current fallback has no accepted model
- **WHEN** the operator explicitly selects one registered model and confirms `Подключиться`
- **THEN** the application creates a current `MANUAL_FALLBACK` diagnostic request context for that exact model and IP
- **AND** only then may it resolve model-specific credentials and perform reachability validation

#### Scenario: Operator confirms credential-configuration fallback

- **GIVEN** credential-configuration resolution is unresolved
- **AND** current fallback has no accepted model
- **WHEN** the operator explicitly selects one registered model and confirms the non-connection continuation action
- **THEN** the application creates a current credential-configuration context for that exact model and IP
- **AND** it may open only that model's credential dialog
- **AND** it does not start diagnostic credentials, ping, page transition, controller/worker work, or device I/O

#### Scenario: No implicit first or previous selection

- **GIVEN** fallback opens for either purpose
- **WHEN** the operator has not explicitly selected a model in this dialog interaction
- **THEN** no model is accepted from item order, prior dialog state, former main-window state, or prior request context
- **AND** confirmation cannot continue the action

#### Scenario: Operator cancels or closes fallback

- **GIVEN** fallback is open for either purpose
- **WHEN** the operator activates Cancel or closes the window
- **THEN** the requesting action fails closed
- **AND** no model-specific credential resolution or mutation, ping, handler, worker/controller, page lifecycle, automatic diagnostic start, or device I/O occurs

#### Scenario: Resolved diagnostic inventory cannot be overridden

- **GIVEN** diagnostic dispatch accepted one exact registered model
- **WHEN** the diagnostic request proceeds
- **THEN** the automatic model remains authoritative for that request
- **AND** no fallback dialog or ordinary UI control permits replacement with another model

### Requirement: Password action configures credentials for one current exact model without device I/O

The permanent `Пароль` action SHALL be an application-owned model-bound credential-configuration action. Each activation SHALL validate and normalize the current IP and create a new `CREDENTIAL_CONFIGURATION` generation/binding distinct from diagnostic-start context.

For a valid IP, the action SHALL run the same exact inventory zero/one/many and canonical-model resolution defined by this capability. It SHALL NOT reuse `_active_request`, a previous successful model, a previous fallback model, current screen, window title, widget text, or another presentation value as model authority.

When resolution is `RESOLVED`, the action SHALL bind the exact inventory `diagnostic_model` and normalized IP and open the credential dialog for that model only. When resolution is unresolved, it SHALL first obtain a new explicit model through purpose-bound fail-closed fallback and only then open the credential dialog.

Before opening the credential dialog and again before credential mutation, the application SHALL verify that action purpose, generation, normalized IP, immutable inventory context, selection source, accepted exact model, and dialog identity are current.

Credential-dialog confirmation MAY add a new credential candidate or move an identical existing candidate to the configured first-attempt position according to existing application-owned credential-store semantics. The mutation SHALL affect only the accepted exact model and current normalized IP wherever existing credential APIs are IP-scoped. It MAY invoke the existing credential-context invalidation for that affected model/IP.

Credential configuration SHALL NOT:

- perform ping or another reachability check;
- change the visible diagnostic page;
- acquire a handler/session/transport;
- create or submit a worker/controller operation;
- perform device network I/O;
- create or replace a diagnostic request context;
- automatically start or refresh diagnostics after saving;
- mark the entered candidate as a confirmed successful credential;
- persist a connection profile;
- mutate another model's credential chain.

Credential-dialog Cancel or window close SHALL perform no credential mutation. Invalid/empty IP SHALL produce a controlled warning and SHALL not query inventory, open model fallback, open a credential dialog, or mutate credentials.

Secret values SHALL remain excluded from logs, public errors, status presentation, fallback payloads, and non-secret action bindings.

#### Scenario: Resolved inventory opens credentials for exact model

- **GIVEN** exactly one inventory record matches the current valid IP
- **AND** its exact `diagnostic_model` is registered
- **WHEN** the operator activates `Пароль`
- **THEN** the application opens the credential dialog for exactly that inventory model and IP
- **AND** it does not use a previous diagnostic or fallback model
- **AND** it performs no ping, page transition, device operation, or network I/O

#### Scenario: Unresolved credential action requires fallback

- **WHEN** credential-configuration resolution is inventory-unavailable, not found, ambiguous, unmapped, or unsupported
- **THEN** no credential model is chosen automatically
- **AND** purpose-bound fallback opens before the credential dialog
- **AND** no credential list is mutated before explicit fallback confirmation and credential-dialog confirmation

#### Scenario: Credential fallback is cancelled

- **GIVEN** credential-purpose fallback is open
- **WHEN** the operator cancels or closes it
- **THEN** no credential dialog opens
- **AND** no credentials, indexes, profiles, diagnostic context, page, controller, worker, or device I/O change

#### Scenario: Credential dialog is cancelled

- **GIVEN** a current exact model/IP credential dialog is open
- **WHEN** the operator cancels or closes it
- **THEN** no credential candidate, configured ordering, successful index, profile, inventory, or diagnostic context changes

#### Scenario: Credential save is model-bound but not success evidence

- **GIVEN** a current credential dialog is bound to exact model M and normalized IP A
- **WHEN** the operator confirms valid credential input
- **THEN** only M's candidate configuration for A is added/promoted under existing storage semantics
- **AND** the entered candidate is not recorded as a confirmed successful credential
- **AND** no connection profile is persisted
- **AND** diagnostics are not started automatically

#### Scenario: Stale credential dialog cannot mutate configuration

- **GIVEN** a credential fallback or credential dialog was opened under an older binding
- **WHEN** IP, inventory context, reset/shutdown, or a newer credential action supersedes it
- **THEN** later selection or confirmation is rejected before credential mutation
- **AND** no device work or I/O occurs

### Requirement: Purpose-bound model resolution freshness is application-owned and precedes work

Every user-initiated diagnostic start and every `Пароль` activation SHALL create a distinct application action generation. A shared global serial MAY be used only when action purpose is part of the binding and cross-purpose callbacks cannot be accepted.

A current binding SHALL include at least action purpose, generation, normalized IP, immutable inventory context/revision identity, resolution outcome, selection source (`AUTO_INVENTORY` or `MANUAL_FALLBACK`), exact assigned model when present, fallback-dialog identity when open, and credential-dialog identity for credential configuration.

IP change, inventory replacement/availability change, reset, and shutdown SHALL supersede all pending model-resolution/dialog work. A newer same-purpose action SHALL supersede an older action. Diagnostic and credential actions SHALL NOT reuse each other's accepted model context as authority.

A stale lookup, fallback selection/confirmation, credential-dialog confirmation, or diagnostic-start continuation SHALL be rejected before model-specific credential access or mutation, handler acquisition, worker/controller submission, and network I/O. It SHALL NOT publish/replace a model request context, change the visible page, change room/VIP presentation, alter credentials, start a controller operation, persist successful credential/profile memory, or start PDU-related-codec enrichment.

The application MAY execute bounded in-memory inventory query synchronously. It SHALL NOT reread JSON, parse Excel, or perform network I/O on the Qt GUI thread. If lookup is queued or asynchronous, publication SHALL pass the same binding checks.

After accepted diagnostic dispatch enters an existing device-specific lifecycle, approved Matrix, PDU, DMP, codec, or audio-DSP authority SHALL remain sole authority for that device operation. Credential configuration SHALL not create a device operation authority.

#### Scenario: New IP supersedes older pending actions

- **GIVEN** an older diagnostic lookup, credential lookup, fallback, or credential dialog is pending for IP A
- **WHEN** the operator changes input to IP B
- **THEN** the older binding is stale
- **AND** its result or confirmation cannot publish a model, mutate credentials, acquire a handler, submit work, change pages, or perform I/O

#### Scenario: Diagnostic and credential purposes do not cross-authorize

- **GIVEN** a current accepted diagnostic request model exists
- **WHEN** the operator activates `Пароль`
- **THEN** the credential action performs its own current IP/inventory resolution
- **AND** it does not reuse the diagnostic request model as credential authority

#### Scenario: Repeat action creates a new generation

- **GIVEN** one action of a purpose has started or completed
- **WHEN** the operator repeats that action
- **THEN** the application creates a distinct newer generation
- **AND** old lookup/dialog actions cannot affect the new context

#### Scenario: Lookup remains external-I/O-free

- **WHEN** the application resolves an IP from loaded inventory for either purpose
- **THEN** it uses only immutable in-memory query
- **AND** it does not load Excel, reread deployment JSON, ping, or perform device/network I/O on the GUI thread

### Requirement: Inventory dispatch ownership does not leak into dialogs, screens, handlers, or workers

`EquipmentInventory` SHALL return canonical records and multiplicity only. It SHALL NOT choose pages, lifecycle routes, fallback models, credential models, or UI outcomes.

The fallback dialog SHALL render safe reason/model choices and publish non-secret selection, confirmation, and cancellation intent only. It SHALL NOT query inventory, read/mutate credentials, acquire handlers, submit work, or perform network I/O.

The credential dialog SHALL receive one already accepted exact public model/IP context and publish credential confirm/cancel data to application composition. It SHALL NOT choose a model, query inventory, start diagnostics, ping, acquire handlers, submit workers/controllers, or perform device network I/O.

Diagnostic screens SHALL render accepted state and publish existing non-secret device intents. They SHALL NOT query inventory, interpret multiplicity, infer model support, choose another screen, or start another model lifecycle.

Controllers, handlers, sessions, and workers SHALL receive one already assigned exact model/IP diagnostic operation context through existing application wiring. They SHALL NOT receive complete IP-match tuples or candidate-model lists and SHALL NOT search inventory, analyze `source_model` or importer evidence, choose pages, iterate models, or switch models after authentication, transport, protocol, parser, timeout, or ambiguous-result failure.

#### Scenario: Assigned diagnostic lifecycle receives one model path

- **WHEN** application dispatch accepts an automatic or confirmed-fallback diagnostic model
- **THEN** the selected existing lifecycle receives only its exact model/IP and approved credential context
- **AND** no dialog, handler, or worker receives all inventory matches or alternative model candidates

#### Scenario: Device failure does not trigger model guessing

- **WHEN** the assigned diagnostic path reports authentication, transport, protocol, parser, timeout, or another device failure
- **THEN** existing retry and credential policies apply only within that exact model path
- **AND** no component retries with another diagnostic model

#### Scenario: PDU enrichment remains gated by accepted PDU success

- **GIVEN** diagnostic dispatch assigns Aten or PCS4i to the PDU page/controller
- **WHEN** the PDU diagnostic starts
- **THEN** related-room/codec enrichment does not start from dispatch alone
- **AND** it starts only after `PDUController` accepts a current successful user refresh under the modified exact-model enrichment contract

#### Scenario: Password action cannot start PDU enrichment

- **GIVEN** credential configuration resolves Aten or PCS4i
- **WHEN** the credential dialog opens, is cancelled, or saves candidate configuration
- **THEN** no PDU refresh or related-room/codec enrichment starts