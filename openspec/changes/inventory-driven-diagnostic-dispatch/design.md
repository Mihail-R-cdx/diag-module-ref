# Design: Inventory-driven diagnostic dispatch

## Context

The approved inventory boundary is:

```text
organization Excel workbook
    -> offline importer
    -> canonical versioned JSON snapshot
    -> immutable indexed EquipmentInventory
    -> application/composition orchestration
```

The importer publishes one exact supported `diagnostic_model` or null. Runtime lookup preserves multiplicity through `find_by_ip(...)`, but the desktop shell currently takes its model from a permanent combo box and duplicates routing across:

```text
device_to_screen
EQUIPMENT_PAGE_REGISTRY
model-specific refresh if/elif chain
controller-specific delegates
```

The combo box is preselected and its Qt value participates directly in page, credential, and lifecycle choice. Both active `show_password_dialog()` definitions also read `device_combo.currentText()` and save credentials under that model key. Removing the combo without defining a replacement would leave model-specific credential configuration dependent on previous state, hidden state, or an implementation-specific guess.

The current importer consistency map also incorrectly declares `Aten PE8208AV -> pdu`. The authoritative source-type mapping is independent from diagnostic routing:

```text
Тип модели = Video Conference -> video_codec
Тип модели = БРП              -> pdu
all other values              -> other
```

Correct Aten and PCS4i source rows may therefore have `device_kind = other`. Their exact canonical `diagnostic_model` values still route to the PDU page and `PDUController`.

The approved PDU-room-codec enrichment resolver currently rejects any one PDU-IP record whose `device_kind` is not `pdu`. That gate would block enrichment after a successful automatically dispatched Aten or PCS4i refresh. Enrichment identity must instead be established by exact agreement between the accepted PDU model context and the one exact inventory record.

## Goals

1. Make IP the only permanent diagnostic-target input in the top connection panel.
2. Remove the permanent device-model selector and its `Устройство` label.
3. Automatically assign one supported diagnostic model from one exact canonical inventory record.
4. Treat a supported inventory result as authoritative for diagnostic startup; do not offer a normal manual override.
5. For unresolved inventory outcomes, require a dedicated fallback dialog with a new explicit model selection and confirmation.
6. Make fallback cancellation and window close fail closed before model-specific work.
7. Preserve complete zero/one/many lookup semantics and refuse first-match behavior.
8. Route by exact canonical `diagnostic_model`, never by `device_kind` or free-form evidence.
9. Establish one closed reviewable application-owned registry for model, page, and existing lifecycle selection.
10. Give the permanent `Пароль` action an explicit model source after selector removal.
11. Reuse the same exact inventory/fallback resolution semantics for credential configuration without starting diagnostics.
12. Keep diagnostic-start and credential-configuration generations/bindings separate so stale actions cannot cross-authorize work.
13. Preserve existing credential candidate, retry, successful-index, saved-profile, device lifecycle, rendering, room/VIP, and PDU enrichment ownership boundaries.
14. Correct the false Aten consistency expectation and make enrichment compatible with Aten/PCS4i `device_kind = other`.

## Non-goals

- Do not change the canonical inventory schema or schema version.
- Do not modify the closed importer recognition component rules.
- Do not infer a diagnostic model from `source_model`, `Производитель`, `Модель`, manufacturer strings, substrings, aliases, handler availability, or protocol behavior.
- Do not make `device_kind` a diagnostic-page, enrichment-PDU, or credential-model identifier.
- Do not filter duplicate IP records by kind or supported model before deciding cardinality.
- Do not retain a hidden or visible persistent model selector as authority.
- Do not permit manual override after a supported inventory model resolves for diagnostic startup.
- Do not reuse a previous diagnostic request model or previous fallback selection for credential configuration.
- Do not automatically start diagnostics after credentials are saved.
- Do not add inventory mutation, write-back, learning, alias persistence, or JSON rewrite from the GUI.
- Do not replace Matrix, PDU, DMP, codec, or Biamp lifecycles with one generic controller.
- Do not move inventory lookup into a screen, dialog, handler, worker, session, or transport.
- Do not change credential fallback, transport retry, successful-index persistence, or saved-profile policy.
- Do not load Excel or regenerate the snapshot at runtime.
- Do not require or update Graphify output.

## Main connection-panel UX

The permanent top panel contains:

```text
IP field
Пароль
Обновить данные
Отладка
```

It does not contain:

```text
QComboBox deviceCombo
label "Устройство"
preselected model state
```

No Qt widget value is model authority. The `Пароль` button remains visible, but it does not read a previous request model or open a model-specific credential dialog directly. It begins a separate model-resolution action described below.

The application publishes stable action context only after exact automatic resolution or explicit current fallback confirmation.

## Closed dispatch registry

The application/composition layer owns one exact reviewable registry:

| Exact canonical model | Screen key | Existing lifecycle route |
| --- | --- | --- |
| `Huawei TE20` | `codec` | Huawei TE20 refresh route |
| `Huawei TE40` | `codec` | Huawei TE40 refresh route |
| `CloudLink Bar 310` | `codec` | CloudLink Bar 310 refresh route |
| `Polycom RPG 310` | `codec` | Polycom RPG 310 refresh route |
| `Extron IN1804` | `matrix` | `MatrixController` refresh route |
| `Aten PE8208AV` | `pdu` | `PDUController` with exact Aten model context |
| `Extron IPL T PCS4i` | `pdu` | `PDUController` with exact PCS4i model context |
| `Biamp Tesira Forte CI` | `audio_dsp` | existing Biamp polling route |
| `Extron DMP 64 Plus` | `audio_dsp` | `DMPPollingController` refresh route |

Diagnostic fallback choices and credential-configuration fallback choices derive from this registry. Page registration and lifecycle routing derive from or are integrity-checked against the same set. There is no permanent combo-model population.

Registry construction must reject or test:

- duplicate canonical model entries;
- a fallback model with no lifecycle route;
- a dispatch entry with no registered screen;
- inconsistent PDU/non-PDU page classification;
- implicit default-to-codec behavior for unknown models.

Registry data contains no credentials, successful indexes, handler/session/transport instances, cookies/tokens, or mutable worker state.

## Shared exact model resolution

The application owns one pure or equivalently side-effect-free model-resolution operation parameterized by action purpose. Inputs are:

```text
normalized IP
immutable EquipmentInventory context or structured unavailability
closed dispatch registry
```

Observable outcomes are:

```text
INVENTORY_UNAVAILABLE
IP_NOT_FOUND
AMBIGUOUS_IP
MODEL_UNMAPPED
MODEL_UNSUPPORTED
RESOLVED
```

Required authority is:

```text
current normalized IP
    -> current immutable EquipmentInventory
    -> find_by_ip(IP) returns tuple[EquipmentRecord, ...]
    -> classify zero / one / many before inspection
    -> one record's exact diagnostic_model
    -> closed dispatch registry
```

Forbidden authority includes:

```text
device_kind
source_model or importer evidence
handler availability
record or registry order
previous diagnostic request model
previous credential action model
first or remembered fallback item
Qt widget text
```

The shared resolver does not itself open a page, read credentials, mutate credentials, ping, acquire handlers, create workers/controllers, or perform device I/O. Application orchestration consumes its result according to action purpose.

## Diagnostic-start flow

Inventory resolution occurs for user-initiated Refresh or equivalent Enter after IPv4 validation.

Required ordering:

```text
1. Validate and normalize IP.
2. Create a new DIAGNOSTIC_START generation.
3. Capture IP and immutable inventory context.
4. Run shared exact model resolution.
5. RESOLVED: accept AUTO_INVENTORY request context while binding remains current.
6. Unresolved: open DeviceModelFallbackDialog with purpose DIAGNOSTIC_START.
7. Accept MANUAL_FALLBACK only after explicit selection and Подключиться confirmation.
8. Publish exact model/page/lifecycle request context.
9. Resolve model-specific credentials and perform preliminary reachability checks.
10. Start only the assigned existing lifecycle.
```

After `RESOLVED`, the exact inventory model is authoritative for that diagnostic request. The ordinary UI provides no override. Device failure does not authorize model switching.

Before automatic acceptance or fallback confirmation there is no model-specific credential access, ping, handler acquisition, worker/controller creation or submission, page lifecycle start, or device I/O.

## DeviceModelFallbackDialog

Every unresolved outcome opens a focused modal or equivalently blocking `DeviceModelFallbackDialog`. The same dialog component may serve both action purposes, but the application supplies an immutable purpose:

```text
DIAGNOSTIC_START
CREDENTIAL_CONFIGURATION
```

The dialog receives only:

```text
safe unresolved reason
closed-registry public model identifiers/labels
action purpose
action generation and non-secret binding token
```

It does not receive full inventory records, source rows, credential values, handlers, workers, sessions, or transports.

Common required behavior:

- no model is accepted because it is first, previous, or remembered;
- explicit current-interaction selection is mandatory;
- confirmation is disabled or rejected until a current selection exists;
- Cancel/window close fails closed;
- IP change, a newer same-purpose action, inventory replacement, reset, or shutdown invalidates the binding;
- stale confirmation is ignored.

Purpose-specific confirmation is:

```text
DIAGNOSTIC_START
    -> Подключиться
    -> create MANUAL_FALLBACK diagnostic request context

CREDENTIAL_CONFIGURATION
    -> Продолжить or equivalent non-connection confirmation
    -> create model-bound credential-configuration context
    -> open credential dialog only
```

The dialog never starts diagnostics or opens credential storage itself. Application composition interprets the confirmed exact model under the bound purpose.

## Model-bound credential configuration flow

The permanent `Пароль` action is model-specific and therefore must resolve model authority every time it is invoked. It never uses an existing `_active_request`, last successful model, previous fallback selection, screen state, window title, or hidden selector.

Required ordering:

```text
1. Operator presses Пароль.
2. Validate and normalize current IP.
3. Invalid/empty IP -> controlled warning; stop.
4. Create a new CREDENTIAL_CONFIGURATION generation distinct from DIAGNOSTIC_START generations.
5. Capture normalized IP and immutable inventory context.
6. Run shared exact model resolution.
7. RESOLVED -> accept exact inventory model for this credential action.
8. Unresolved -> open DeviceModelFallbackDialog with purpose CREDENTIAL_CONFIGURATION.
9. Accept fallback model only after explicit current selection and purpose-specific confirmation.
10. Recheck generation/IP/inventory/purpose binding.
11. Open credential dialog for exactly the accepted model and normalized IP.
12. On credential-dialog confirmation, recheck the same binding before any mutation.
13. Add or promote only that model's credential candidate using existing credential-store semantics.
14. Apply existing credential-context invalidation for the affected model/IP.
15. Remain in the current diagnostic UI state; do not start diagnostics.
```

The credential flow does not:

- perform ping or other reachability validation;
- change the visible diagnostic page;
- create or submit a controller/worker;
- acquire a handler/session/transport;
- perform device network I/O;
- create a diagnostic request context;
- reuse or overwrite an accepted diagnostic model;
- automatically call Refresh after saving;
- mark the entered candidate as a confirmed successful credential;
- persist a connection profile.

Credential-dialog Cancel/window close changes no credential list, index, profile, inventory, or diagnostic state. Fallback Cancel/window close opens no credential dialog and performs no credential mutation.

Saving uses the exact accepted model as the credential key and the current normalized IP wherever current credential APIs are IP-scoped. It may place the entered candidate first for the next attempt according to existing configuration behavior, but that is configuration ordering, not successful-credential evidence. No other model's credential chain is read or mutated.

A credential action that resolves the same IP/model as a current diagnostic request remains a separate action. Saving may invoke the existing application-owned credential-context invalidation required for safety, but merely opening/resolving/cancelling the credential flow must not start, replace, or complete a device operation.

## Action generations and stale safety

Application composition owns separate monotonic or equivalently unique bindings for:

```text
DIAGNOSTIC_START
CREDENTIAL_CONFIGURATION
```

A common global action serial is also acceptable only if action purpose is part of the binding and cross-purpose callbacks cannot be accepted accidentally.

Every binding includes at least:

```text
action purpose
action generation
normalized IP
immutable inventory context/revision identity
resolution outcome
selection source: AUTO_INVENTORY or MANUAL_FALLBACK
exact accepted model, when any
fallback-dialog identity, when open
credential-dialog identity, for credential configuration
```

Supersession rules:

- IP text change invalidates pending diagnostic and credential-resolution/dialog bindings;
- a newer action of the same purpose invalidates the older one;
- inventory replacement/availability change, reset, or shutdown invalidates both;
- a newer diagnostic start must not accept an old credential fallback/dialog callback;
- a newer credential action must not alter an accepted diagnostic request context;
- saving credentials from a stale credential dialog is rejected before mutation.

Stale work must not publish a model context, select or mutate credentials, change pages, acquire handlers, submit work, perform I/O, persist successful memory/profile, or start PDU enrichment.

## Ownership

### Application/composition layer

Owns:

- IP validation/normalization;
- immutable inventory context;
- shared exact model resolution and zero/one/many interpretation;
- closed registry lookup;
- action-purpose generations and binding checks;
- fallback opening and confirmation acceptance;
- diagnostic request context;
- credential-configuration context;
- model-bound credential dialog orchestration and credential-store mutation callback;
- transition into existing diagnostic lifecycles only for DIAGNOSTIC_START.

### EquipmentInventory

Owns immutable records, deterministic tuple queries, and multiplicity only. It knows nothing about pages, lifecycles, dialogs, credentials, or action purposes.

### DeviceModelFallbackDialog and credential dialog

The fallback dialog renders safe reason/model choices and publishes non-secret select/confirm/cancel intent only. It does not query inventory or perform model-specific work.

The credential dialog receives one already accepted exact model/IP public context, displays secret input safely, and publishes confirm/cancel data to application composition. It does not choose a model, query inventory, start diagnostics, ping, acquire handlers, or perform device I/O.

### Diagnostic screens, controllers, handlers, sessions, and workers

They receive one already assigned exact model/IP operation context through existing diagnostic wiring. They do not receive inventory matches or candidate models, do not select models, and do not switch models after failure.

## Credential and transport compatibility

For diagnostic startup, the final model is accepted before model-specific credential resolution. Cancelled/unconfirmed fallback performs no device-model credential-provider access.

For credential configuration, the exact model is accepted before credential-list read/mutation or credential-dialog presentation. Password entry is not authentication success.

Existing rules remain unchanged:

- application/composition owns candidate chains;
- supported saved profile ordering remains model-specific;
- transport retry and credential fallback remain separate;
- credential advancement occurs only after structured authentication failure;
- strings such as `auth`, `401`, or `403` do not authorize fallback;
- successful credential index/profile persists only after accepted current complete device success;
- stale, cancelled, resolution-only, and credential-configuration-only outcomes persist no success/profile evidence;
- secrets do not appear in logs, status messages, or public errors.

## PDU room/related-codec compatibility

Automatic or confirmed diagnostic fallback assigns an exact PDU model to `PDUController`. Credential-configuration resolution never starts PDU diagnostics or enrichment.

Enrichment starts only after `PDUController` accepts a current successful user refresh. Required PDU record resolution is:

```text
1. find_by_ip(accepted_pdu_ip)
2. preserve full zero/one/many cardinality
3. require exactly one total record
4. require accepted PDU model in closed set:
       Aten PE8208AV
       Extron IPL T PCS4i
5. require inventory diagnostic_model in the same closed set
6. require inventory diagnostic_model == accepted PDU model
7. require non-null authoritative room_id
8. continue existing room -> video_codec resolution
```

The resolver does not require or inspect `device_kind == pdu`. Controlled failures are `PDU_MODEL_UNSUPPORTED` and `PDU_MODEL_MISMATCH`; both stop before related-codec credentials or network work. Enrichment failure remains independent from accepted PDU success.

## Aten consistency correction

`EXPECTED_KIND_BY_DIAGNOSTIC_MODEL` is importer-only consistency evidence, not canonical or runtime authority.

This change corrects:

```text
Aten PE8208AV: expected kind pdu -> other
```

Correct Aten/PCS4i rows mapped to `other` emit no known-model/type mismatch. A genuinely conflicting source type remains observable without rewriting canonical fields. Recognition, schema, snapshot identity, and runtime lookup APIs remain unchanged.

## Regression coverage

Focused synthetic tests cover at least:

### UI and registry

- top panel has no model selector or `Устройство` label;
- `Пароль` remains available but reads no Qt/previous model authority;
- all nine models have exactly one registry entry and registered screen;
- both fallback purposes derive choices from the registry;
- unknown model has no default route.

### Diagnostic dispatch and fallback

- representative exact models route to their existing lifecycles;
- Aten/PCS4i route to PDU despite kind `other`;
- duplicate IP never filters or first-selects;
- supported resolution exposes no override;
- every unresolved reason opens diagnostic fallback;
- explicit current selection plus `Подключиться` is required;
- Cancel/close and stale confirmation perform zero model-specific work/I/O.

### Credential configuration

For resolved and every unresolved outcome:

- pressing `Пароль` validates IP and creates a separate credential action binding;
- resolved inventory opens credentials for exactly the inventory model;
- unresolved opens purpose-bound fallback before credential dialog;
- no first/previous/request model is reused;
- fallback Cancel/close performs no credential read/mutation and no diagnostic work;
- credential-dialog Cancel/close performs no mutation;
- save affects only exact bound model/IP candidate configuration;
- save does not mark success, persist profile, ping, change page, create work, perform I/O, or auto-start diagnostics;
- stale fallback/credential-dialog confirmation cannot mutate credentials;
- direct `device_combo.currentText()` credential authority and duplicate obsolete password-dialog implementation are removed.

### PDU enrichment and importer

- exact Aten/PCS4i accepted context matches inventory model despite kind `other`;
- duplicate PDU IP remains ambiguous;
- unsupported/mismatched PDU model stops before codec work;
- correct Aten/PCS4i `other` rows have no importer mismatch;
- genuinely conflicting Aten type remains observable.

### Compatibility and protection

- shared room/VIP presentation remains current;
- existing credential fallback and success persistence rules remain unchanged;
- no GUI-thread JSON/Excel/network work is introduced;
- tests contain only synthetic inventory/credentials;
- no production data, secrets, or Graphify output is committed or exposed.

## Rollout and operational documentation

Implementation updates `docs/equipment-inventory-runbook.md` with:

- IP-only permanent target flow;
- closed exact model registry and zero/one/many outcomes;
- diagnostic fail-closed fallback and no override after resolution;
- model-bound `Пароль` flow, separate generation, unresolved fallback, no-I/O behavior, and no automatic diagnostic start;
- action freshness requirements;
- exact accepted PDU/inventory model enrichment validation;
- Aten/PCS4i kind compatibility and corrected importer expectation.

No runtime Excel dependency or schema migration is introduced. Existing valid snapshots remain loadable. Production workbook and `equipment_inventory.local.json` remain deployment-local and outside Git.