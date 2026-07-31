# Change: inventory-driven-diagnostic-dispatch

## Why

The canonical equipment inventory now carries an exact reviewed `diagnostic_model`, but the desktop application still requires the operator to choose a model from a permanent top-panel selector before refresh. The current shell also duplicates routing across `device_to_screen`, `EQUIPMENT_PAGE_REGISTRY`, and a model-specific `if/elif` refresh chain. This leaves canonical inventory disconnected from normal diagnostic startup, preserves an unnecessary model control, and permits the wrong protocol and credential chain to be selected for an IP without an explicit unresolved-inventory decision.

A user-entered IP must resolve through the immutable `EquipmentInventory`, preserve zero/one/many cardinality, and dispatch only from an exact supported canonical `diagnostic_model`. When that resolution succeeds, the inventory model is authoritative for the current diagnostic request and the normal interface must not offer an override. When inventory cannot assign one supported model, the application must open a dedicated fail-closed fallback dialog that requires a new explicit model selection and confirmation before any model-specific credential, reachability, handler, worker/controller, or device-I/O work begins.

Removing the permanent selector also removes the current model source used by the permanent `Пароль` action. Credential configuration must therefore resolve the current IP through the same exact inventory/fallback authority, but through a separate action generation that never starts diagnostics. A previous request model, previous fallback choice, hidden widget state, or first registry item must never determine which model receives credentials.

The current importer also contains one known consistency defect: `EXPECTED_KIND_BY_DIAGNOSTIC_MODEL` expects `Aten PE8208AV` to have `device_kind = pdu`. The authoritative `Тип модели` mapping classifies the actual Aten rows as `other`; exact `diagnostic_model = Aten PE8208AV` remains sufficient for PDU diagnostic dispatch.

The approved PDU-room-codec enrichment contract currently requires the accepted PDU inventory record to have `device_kind == "pdu"`. That gate is incompatible with correct Aten and PCS4i records whose canonical kind is `other`. Enrichment must instead verify the exact accepted `PDUController` model against the one exact inventory record and a closed PDU model set.

## What Changes

- Remove the permanent device-model selector and its `Устройство` label from the main connection panel. Accepted models live in application-owned action/request contexts rather than Qt selector state.
- Resolve every valid user-entered IP before model-specific diagnostic startup:

```text
normalized user IP
    -> EquipmentInventory.find_by_ip(...)
    -> preserve zero / one / many
    -> exact canonical diagnostic_model
    -> closed diagnostic dispatch registry
    -> existing page and controller/refresh lifecycle
```

- Define one closed reviewable registry for the nine currently supported canonical models:

| Canonical `diagnostic_model` | Screen | Existing diagnostic lifecycle |
| --- | --- | --- |
| `Huawei TE20` | `codec` | Huawei TE20 refresh path |
| `Huawei TE40` | `codec` | Huawei TE40 refresh path |
| `CloudLink Bar 310` | `codec` | CloudLink Bar 310 refresh path |
| `Polycom RPG 310` | `codec` | Polycom RPG 310 refresh path |
| `Extron IN1804` | `matrix` | `MatrixController` refresh path |
| `Aten PE8208AV` | `pdu` | `PDUController` using the Aten model path |
| `Extron IPL T PCS4i` | `pdu` | `PDUController` using the PCS4i model path |
| `Biamp Tesira Forte CI` | `audio_dsp` | existing Biamp polling path |
| `Extron DMP 64 Plus` | `audio_dsp` | `DMPPollingController` refresh path |

- Dispatch strictly by exact `diagnostic_model`; `device_kind` is not a page, controller, enrichment-PDU, or credential-model identifier.
- Preserve complete duplicate-IP ambiguity. Multiple records for one IP must never be filtered or ranked to select a preferred record.
- For `INVENTORY_UNAVAILABLE`, IP not found, duplicate IP, null model, or unsupported exact model, automatically open `DeviceModelFallbackDialog` with a safe reason and closed-registry models.
- Require a new explicit selection and action-specific confirmation in that dialog. No first, previous, or remembered model is implicitly accepted. Cancel or window close fails closed.
- Do not permit manual override after a supported inventory model is resolved for diagnostic startup. The inventory model is authoritative for that request.
- Keep the permanent `Пароль` action, but make it start a separate model-resolution flow:

```text
Пароль
    -> validate/normalize current IP
    -> separate credential-configuration generation
    -> same exact inventory zero/one/many resolution
    -> RESOLVED: open credential dialog for exact inventory model
    -> unresolved: explicit fail-closed model fallback
    -> confirmed model: open credential dialog for that model
```

- Credential configuration performs no ping, page transition, handler acquisition, controller/worker creation, device network I/O, or automatic diagnostic start. Cancel/close changes nothing. Saving mutates credentials only for the exact current bound model/IP according to existing credential-store semantics and does not mark a credential successful or persist a connection profile.
- Bind diagnostic resolution, credential-configuration resolution, fallback confirmation, and credential saving to their current action generation, normalized IP, and immutable inventory context. Stale work must not select or mutate credentials, change pages, submit work, or start I/O.
- Keep inventory lookup and model authority in the application/composition layer. Dialogs, screens, controllers, handlers, sessions, and workers do not search inventory, interpret multiplicity, analyze free-form model text, or receive candidate model lists.
- Modify PDU-room-codec enrichment so one exact inventory record is accepted only when its exact `diagnostic_model` equals the model carried by the accepted current `PDUController` context and both are in the closed PDU set (`Aten PE8208AV`, `Extron IPL T PCS4i`). The resolver no longer requires `device_kind = pdu`.
- Correct `EXPECTED_KIND_BY_DIAGNOSTIC_MODEL["Aten PE8208AV"]` from `pdu` to `other`, preserving the exact `Тип модели -> device_kind` mapping and canonical schema.
- Add synthetic regression coverage for dispatch cardinality, diagnostic and credential fallback confirmation/cancellation, pre-confirmation no-I/O, stale rejection, exact credential model binding, PDU enrichment model matching, room/VIP compatibility, and importer consistency.
- Update the equipment-inventory runbook after implementation.

## Impact

Affected specifications:

- `diagnostic-application-shell`
- `equipment-inventory-snapshot`
- `pdu-room-codec-enrichment`

Expected implementation areas:

- `gui/main_window.py`
- `gui/equipment_pages.py` and/or a focused application-owned dispatch module
- a focused reusable `DeviceModelFallbackDialog`
- model-bound credential-dialog orchestration and removal of direct `device_combo.currentText()` credential authority
- `core/room_context.py`
- existing Matrix, PDU, codec, Biamp, and DMP composition wiring only as required to consume the assigned exact model
- `tools/import_equipment_inventory.py`
- synthetic GUI/application, credential-flow, enrichment, and importer tests
- `docs/equipment-inventory-runbook.md`

This change does not add a canonical field, change the inventory schema version, change `Тип модели -> device_kind`, introduce runtime source-text recognition, add fuzzy matching, change credential fallback or credential-store persistence authority, move network ownership into screens/handlers/workers, commit production inventory data, require Graphify, or replace existing device-specific lifecycle controllers.
