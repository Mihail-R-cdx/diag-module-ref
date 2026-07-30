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

The combo box is preselected and its Qt value participates directly in page, credential, and lifecycle choice. That behavior is incompatible with inventory-owned automatic dispatch and with fail-closed fallback: an unresolved IP could otherwise use the first or previously selected model without a new explicit decision.

The current importer consistency map also incorrectly declares `Aten PE8208AV -> pdu`. The authoritative source-type mapping is independent from diagnostic routing:

```text
Тип модели = Video Conference -> video_codec
Тип модели = БРП              -> pdu
all other values              -> other
```

Correct Aten and PCS4i source rows may therefore have `device_kind = other`. Their exact canonical `diagnostic_model` values still route to the PDU page and `PDUController`.

The approved PDU-room-codec enrichment resolver currently rejects any one PDU-IP record whose `device_kind` is not `pdu`. That gate would block enrichment after a successful automatically dispatched Aten or PCS4i refresh. Enrichment identity must instead be established by exact agreement between the accepted PDU model context and the one exact inventory record.

## Goals

1. Make IP the only permanent diagnostic target input in the top connection panel.
2. Remove the permanent device-model selector and its `Устройство` label.
3. Automatically assign one supported diagnostic model from one exact canonical inventory record.
4. Treat a supported inventory result as authoritative for the current request; do not offer a normal manual override.
5. For unresolved inventory outcomes, require a dedicated fallback dialog with a new explicit model selection and confirmation.
6. Make fallback cancellation and window close fail closed: return to `IDLE` with no model-specific credentials, reachability check, handler acquisition, worker/controller submission, or device I/O.
7. Preserve complete zero/one/many lookup semantics and refuse first-match behavior.
8. Route by exact canonical `diagnostic_model`, never by `device_kind` or free-form evidence.
9. Establish one closed reviewable application-owned registry for model, page, and existing lifecycle selection.
10. Bind automatic and manual-fallback decisions to current IP, inventory context, and dispatch generation so stale work cannot start I/O.
11. Preserve existing device-specific lifecycle, credential, retry, rendering, room/VIP, and PDU enrichment ownership boundaries.
12. Correct the false Aten consistency expectation and make PDU enrichment compatible with Aten/PCS4i `device_kind = other`.

## Non-goals

- Do not change the canonical inventory schema or schema version.
- Do not modify the closed importer recognition component rules.
- Do not infer a diagnostic model from `source_model`, `Производитель`, `Модель`, manufacturer strings, substrings, aliases, handler availability, or protocol behavior.
- Do not make `device_kind` a diagnostic-page or enrichment-PDU identifier.
- Do not filter duplicate IP records by kind or supported model before deciding cardinality.
- Do not retain a hidden or visible persistent model selector as request authority.
- Do not permit manual override after a supported inventory model resolves.
- Do not reuse a previous fallback selection without a new explicit dialog confirmation.
- Do not add inventory mutation, write-back, learning, alias persistence, or JSON rewrite from the GUI.
- Do not replace Matrix, PDU, DMP, codec, or Biamp lifecycles with one generic controller.
- Do not move inventory lookup into a screen, dialog, handler, worker, session, or transport.
- Do not change credential fallback, transport retry, successful-index persistence, or saved-profile policy.
- Do not load Excel or regenerate the snapshot at runtime.
- Do not require or update Graphify output.

## Main connection-panel UX

The permanent top panel contains the IP field and existing actions that remain relevant to a model-independent start. It does not contain:

```text
QComboBox deviceCombo
label "Устройство"
preselected model state
```

No Qt widget value is the model authority. The application publishes an immutable or equivalently stable request context only after one of two accepted paths:

```text
automatic inventory resolution -> AUTO_INVENTORY
confirmed fallback dialog      -> MANUAL_FALLBACK
```

The request context contains the exact model and registry entry needed by the existing diagnostic lifecycle. It does not alter the inventory record.

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

The fallback dialog derives its selectable models from this registry. Page registration and lifecycle routing must derive from or be integrity-checked against the same authoritative set. There is no permanent combo-model population.

Registry construction must reject or test:

- duplicate canonical model entries;
- a fallback model with no lifecycle route;
- a dispatch entry with no registered screen;
- inconsistent PDU/non-PDU page classification;
- implicit default-to-codec behavior for unknown models.

Registry data contains no credentials, successful indexes, handler/session/transport instances, cookies/tokens, or mutable worker state.

## Automatic authority chain

The exact automatic authority is:

```text
current normalized user IP
    -> current immutable EquipmentInventory
    -> find_by_ip(IP) returns tuple[EquipmentRecord, ...]
    -> application classifies zero / one / many
    -> one record's exact diagnostic_model
    -> closed dispatch registry
    -> AUTO_INVENTORY request context
    -> assigned page and existing lifecycle
```

Forbidden intermediate authority includes:

```text
device_kind == pdu
source_model contains TE
manufacturer contains Huawei
handler exists for a nearby model
first supported record among duplicate IP matches
previous model selection
first fallback-dialog item
```

`EquipmentInventory` remains a data/query boundary. It returns canonical records and multiplicity; it does not return pages, controller classes, dialog choices, or user-facing outcomes.

## Dispatch trigger and ordering

Inventory resolution occurs only for a user-initiated Refresh or equivalent Enter action after IPv4 validation.

Required ordering:

```text
1. Validate and normalize the user IP.
2. Create a new application dispatch generation.
3. Capture normalized IP and current immutable inventory context.
4. Call EquipmentInventory.find_by_ip(normalized_ip), or classify inventory unavailable.
5. Classify the complete tuple as zero / one / many before inspecting model or kind.
6. For one record, resolve its exact diagnostic_model in the closed registry.
7. If supported, accept AUTO_INVENTORY only while generation/IP/inventory binding remains current.
8. If unresolved, open a generation-bound DeviceModelFallbackDialog.
9. Accept MANUAL_FALLBACK only after explicit selection and Подключиться confirmation while the dialog binding remains current.
10. Publish one assigned exact model/page/lifecycle request context.
11. Resolve model-specific credentials and perform preliminary reachability checks.
12. Start only the existing assigned model lifecycle.
```

Inventory resolution and fallback confirmation both precede model-specific credential resolution, ping, handler acquisition, worker/controller creation or submission, and network I/O.

The inventory is already loaded in memory. A bounded lookup may run synchronously on the GUI thread, but runtime must not reread JSON, parse Excel, or perform external I/O there. Any queued lookup uses the same stale checks.

## Resolution outcomes

Application code classifies the complete IP tuple before filtering:

```text
inventory unavailable
    -> INVENTORY_UNAVAILABLE
    -> open fallback dialog

zero IP records
    -> IP_NOT_FOUND
    -> open fallback dialog

more than one IP record
    -> AMBIGUOUS_IP
    -> inspect no preferred record
    -> open fallback dialog

exactly one record with diagnostic_model = null
    -> MODEL_UNMAPPED
    -> open fallback dialog

exactly one record with unknown canonical diagnostic_model
    -> MODEL_UNSUPPORTED
    -> open fallback dialog

exactly one record with registered diagnostic_model
    -> RESOLVED
    -> accept authoritative AUTO_INVENTORY context
    -> do not open fallback dialog and do not offer override
```

The UI safely distinguishes unresolved reasons without exposing complete source records or production inventory. Unresolved inventory is not a device connection failure and does not open an automatic network-error modal.

`device_kind = other` neither blocks nor grants dispatch. Aten and PCS4i resolve only through their exact registered models.

## Authoritative resolved path

After `RESOLVED`, the exact inventory model is the model of the current request. The application:

- stores it in application-owned request context;
- assigns only its registered page and lifecycle;
- resolves credentials only for that model;
- does not display a persistent model selector;
- does not expose a normal action to replace it with another model;
- does not switch models after authentication, transport, protocol, parser, timeout, or ambiguous device result.

A later Refresh for the same IP performs a new inventory resolution generation. An inventory data correction is made only through the offline inventory workflow, never through runtime override.

## DeviceModelFallbackDialog

Every unresolved inventory outcome automatically opens a dedicated modal or equivalently blocking application dialog named `DeviceModelFallbackDialog` or a focused equivalent.

The dialog receives only:

```text
safe unresolved reason
closed registry public model labels/identifiers
dispatch generation and non-secret binding token
```

It does not receive full inventory records, source rows, credentials, handlers, workers, sessions, or transports.

Required behavior:

- no model is considered selected merely because it is the first item;
- no previous or remembered model is automatically accepted;
- `Подключиться` is disabled or rejected until the operator explicitly selects one registry model;
- confirmation creates a `MANUAL_FALLBACK` request context for the current normalized IP and generation only;
- selection does not mutate `EquipmentRecord`, `EquipmentInventory`, workbook, JSON, aliases, or canonical model memory;
- Cancel and window close dismiss the unresolved start, restore/retain `IDLE`, and start no device-specific work;
- IP change, new Refresh/Enter, inventory replacement, reset, or shutdown invalidates the dialog binding;
- confirmation from a stale dialog is ignored and starts no credentials, page/lifecycle transition, handler, worker/controller, or I/O.

Fallback is available only because automatic resolution failed. It is not an override of a successful inventory decision.

## Freshness and supersession

Every start creates a distinct dispatch generation, including repeated starts for the same IP/model.

A binding includes at least:

```text
dispatch generation
normalized IP
immutable inventory context/revision identity
resolution outcome
selection source: AUTO_INVENTORY or MANUAL_FALLBACK
exact assigned model, when accepted
fallback-dialog binding, when open
```

The following immediately supersede older pending dispatch/fallback work:

- IP text change;
- a new or repeated Refresh/Enter;
- inventory replacement/reload or availability change;
- application reset or shutdown.

A stale lookup, dialog selection, or confirmation is rejected before model-specific credentials, page/controller activation, handler acquisition, worker/controller submission, and network I/O. It must not:

- publish or replace request model context;
- change the visible diagnostic page;
- clear or restore room/VIP state for a newer context;
- create or replace a controller/worker operation;
- select or advance credentials;
- persist a successful credential index or profile;
- start PDU room/codec enrichment;
- display an automatic modal connection error.

After accepted dispatch enters an existing device lifecycle, that lifecycle's approved generation authority remains sole operation authority. Dispatch does not create a second Matrix/PDU/DMP/codec/audio-DSP operation generation.

## Ownership

### Application/composition layer

Owns:

- normalized IP capture and validation;
- current immutable inventory context;
- `find_by_ip` and zero/one/many interpretation;
- closed registry lookup;
- fallback-dialog opening and confirmation acceptance;
- AUTO_INVENTORY/MANUAL_FALLBACK request context;
- dispatch generation and stale rejection;
- transition into existing credential and device lifecycle paths.

### EquipmentInventory

Owns immutable records, deterministic tuple queries, and multiplicity only. It knows nothing about pages, lifecycles, dialogs, or fallback outcomes.

### DeviceModelFallbackDialog and screens

The fallback dialog renders safe reason/model choices and publishes non-secret select/confirm/cancel intent. It does not query inventory, resolve credentials, acquire handlers, or start I/O.

Diagnostic screens render accepted device state and publish their existing non-secret device intents. They do not select models or choose another screen/controller.

### Controllers, handlers, sessions, and workers

They receive one already assigned exact model/IP operation context through existing application wiring. They do not receive the complete IP-match tuple or candidate model list and do not:

- call `find_by_ip`;
- inspect `source_model` or importer evidence;
- choose a GUI page;
- iterate diagnostic models;
- retry with another model after a device failure.

## Credential and transport compatibility

The final exact model is accepted before model-specific credential resolution. Cancelled/unconfirmed fallback performs no credential-provider access for a device model.

Existing rules remain unchanged:

- supported saved profile ordering remains model-specific;
- transport retry and credential fallback remain separate;
- credential advancement occurs only after structured authentication failure;
- strings such as `auth`, `401`, or `403` do not authorize fallback;
- successful credential index/profile persists only after accepted current complete success;
- stale or dispatch-only outcomes persist nothing.

## PDU room/related-codec compatibility

Automatic or confirmed-fallback dispatch assigns an exact PDU model to `PDUController`. Enrichment still starts only after `PDUController` accepts a current successful user refresh.

The accepted non-secret PDU context supplies at least exact model and IP to the pure resolver. Required PDU record resolution is:

```text
1. find_by_ip(accepted_pdu_ip)
2. preserve full zero/one/many cardinality
3. require exactly one total record
4. require accepted PDU model in closed set:
       Aten PE8208AV
       Extron IPL T PCS4i
5. require inventory record diagnostic_model in the same closed set
6. require inventory diagnostic_model == accepted PDU model
7. require non-null authoritative room_id
8. continue existing room -> video_codec resolution
```

The resolver does not require or inspect `device_kind == pdu`. It does not identify a PDU from page key, kind, source text, or record position.

Observable outcomes include:

```text
PDU_MODEL_UNSUPPORTED
PDU_MODEL_MISMATCH
```

`PDU_MODEL_UNSUPPORTED` applies when the accepted controller model is not in the closed PDU set. `PDU_MODEL_MISMATCH` applies when the one inventory record has null/unsupported PDU model or an exact model different from the accepted context. Both stop before codec credentials or network work.

This preserves:

```text
accepted current PDU refresh
    -> exact accepted-model/inventory-model validation
    -> room resolution
    -> one related video codec
    -> independent read-only codec status lifecycle
```

Enrichment failure remains independent from accepted PDU success. Non-PDU room/VIP presentation remains bound to current exact request model, IP, screen registration, and inventory context.

## Aten consistency correction

`EXPECTED_KIND_BY_DIAGNOSTIC_MODEL` is importer-only consistency evidence, not canonical or runtime authority.

This change corrects:

```text
Aten PE8208AV: expected kind pdu -> other
```

Required outcomes:

```text
Aten PE8208AV + source mapping to other
    -> diagnostic_model = Aten PE8208AV
    -> device_kind = other
    -> no KNOWN_MODEL_TYPE_MISMATCH

Extron IPL T PCS4i + source mapping to other
    -> diagnostic_model = Extron IPL T PCS4i
    -> device_kind = other
    -> no KNOWN_MODEL_TYPE_MISMATCH

Aten PE8208AV + source mapping to pdu or video_codec
    -> canonical fields remain source-authoritative
    -> KNOWN_MODEL_TYPE_MISMATCH remains observable
```

The correction does not change model recognition, schema, snapshot identity, or runtime lookup APIs.

## Regression coverage

Focused synthetic tests cover at least:

### UI and registry

- top panel has no `deviceCombo` and no `Устройство` label;
- all nine models have exactly one registry entry and registered screen;
- fallback choices derive from the closed registry;
- unknown model has no default route.

### Automatic dispatch

- unique Aten and PCS4i IP route to PDU despite `device_kind = other`;
- unique TE40 routes to codec;
- unique IN1804 routes to Matrix;
- representative Biamp and DMP route to distinct audio-DSP lifecycles;
- `device_kind` alone selects nothing;
- null/unsupported model selects nothing automatically;
- duplicate IP never filters or selects the first record;
- successful inventory resolution does not expose or accept manual override.

### Fallback dialog

For inventory unavailable, not found, duplicate IP, null model, and unsupported model:

- dialog opens with the correct safe reason;
- no first/previous selection is implicitly accepted;
- explicit selection plus confirmation starts only that registry model;
- Cancel and window close return/retain `IDLE`;
- before confirmation there is zero model-specific credential resolution, ping, handler acquisition, worker/controller submission, and device I/O;
- stale dialog confirmation starts nothing;
- fallback does not mutate or persist inventory.

### PDU enrichment

- accepted Aten plus exact Aten inventory record with kind `other` resolves room/codec;
- accepted PCS4i plus exact PCS4i inventory record with kind `other` resolves room/codec;
- duplicate PDU IP remains ambiguous before model inspection;
- accepted unsupported PDU model yields `PDU_MODEL_UNSUPPORTED`;
- null, unsupported, or different inventory PDU model yields `PDU_MODEL_MISMATCH`;
- no codec credential/network work follows mismatch;
- enrichment still starts only after accepted current user PDU refresh.

### Importer and compatibility

- correct Aten/PCS4i `other` rows have no mismatch;
- genuinely conflicting Aten source type emits mismatch without rewriting canonical fields;
- shared room/VIP presentation remains current;
- credentials and fallback policy remain unchanged after an assigned model exists;
- no GUI-thread JSON/Excel/network work is introduced;
- no real organization data, credentials, or Graphify output appears.

## Rollout and operational documentation

Implementation updates `docs/equipment-inventory-runbook.md` with:

- IP-only permanent connection-panel flow;
- exact `diagnostic_model` dispatch authority;
- closed model/page/lifecycle registry;
- zero/one/many outcomes;
- fail-closed `DeviceModelFallbackDialog` behavior;
- no override after successful inventory resolution;
- stale-generation requirements;
- exact accepted PDU model versus inventory model enrichment validation;
- Aten/PCS4i `device_kind = other` compatibility;
- corrected importer consistency expectation.

No runtime Excel dependency or schema migration is introduced. Existing valid snapshots remain loadable. Production workbook and `equipment_inventory.local.json` remain deployment-local and outside Git.