# Change: inventory-driven-diagnostic-dispatch

## Why

The canonical equipment inventory now carries an exact reviewed `diagnostic_model`, but the desktop application still requires the operator to choose a device model manually before refresh. The current shell also duplicates model routing across `device_to_screen`, `EQUIPMENT_PAGE_REGISTRY`, and a model-specific `if/elif` refresh chain. This leaves the canonical inventory disconnected from normal diagnostic startup and allows registry drift.

A user-entered IP should resolve through the immutable `EquipmentInventory`, preserve zero/one/many cardinality, and dispatch only from an exact supported canonical `diagnostic_model`. The existing manual selector must remain available whenever inventory cannot resolve one supported model and as an explicit request-context override. Runtime code must not analyze `source_model`, manufacturer text, importer evidence, or `device_kind` to guess a diagnostic path.

The current importer also contains one known consistency defect: `EXPECTED_KIND_BY_DIAGNOSTIC_MODEL` expects `Aten PE8208AV` to have `device_kind = pdu`. The authoritative `Тип модели` mapping classifies the actual Aten rows as `other`; the exact `diagnostic_model = Aten PE8208AV` is sufficient for PDU diagnostic dispatch. The incorrect expectation produces a false `KNOWN_MODEL_TYPE_MISMATCH` without changing the canonical record.

## What Changes

- Add application-owned inventory resolution before device-specific diagnostic startup:

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

- Dispatch strictly by exact `diagnostic_model`; `device_kind` is not a page or controller identifier and must not prefilter or override dispatch.
- Preserve duplicate-IP ambiguity. Multiple records for one IP must never select the first record, even when only one appears to have a familiar kind or model.
- Preserve the current manual model selector for inventory unavailable, IP not found, duplicate IP, null `diagnostic_model`, unsupported canonical model, and explicit user override.
- Make manual override request-context-local: it may change the diagnostic model used for the current normalized IP context, but it must not mutate the immutable inventory, rewrite JSON, persist a new canonical value, or teach the registry an alias.
- Bind every inventory-assisted selection to the current normalized IP, immutable inventory context, and application dispatch generation. Superseded lookup results must not change the selected model, screen, credentials, controller, or start network I/O.
- Keep inventory lookup and dispatch in the application/composition layer. `EquipmentInventory` returns canonical tuples only; screens, controllers, handlers, sessions, and workers do not search inventory, interpret multiplicity, analyze free-form model text, or receive a list of candidate models.
- Correct `EXPECTED_KIND_BY_DIAGNOSTIC_MODEL["Aten PE8208AV"]` from `pdu` to `other`, preserving the exact `Тип модели -> device_kind` mapping and canonical schema.
- Add synthetic regression coverage for resolution cardinality, every representative screen/controller route, manual fallback and override, stale-result rejection, no-guessing boundaries, existing manual diagnostics, room/VIP/enrichment compatibility, and the Aten consistency correction.
- Update the equipment-inventory runbook after implementation with the approved dispatch and fallback boundary.

## Impact

Affected specifications:

- `diagnostic-application-shell`
- `equipment-inventory-snapshot`

Expected implementation areas:

- `gui/main_window.py`
- `gui/equipment_pages.py` and/or a focused application-owned dispatch module
- existing Matrix, PDU, codec, and audio-DSP composition wiring only as required to consume the assigned exact model
- `tools/import_equipment_inventory.py`
- synthetic GUI/application and importer tests
- `docs/equipment-inventory-runbook.md`

This change does not add a canonical field, change the inventory schema version, change `Тип модели -> device_kind`, introduce runtime source-text recognition, add fuzzy matching, change credential fallback, move network ownership into screens, handlers, or workers, commit production inventory data, require Graphify, or replace existing device-specific lifecycle controllers.
