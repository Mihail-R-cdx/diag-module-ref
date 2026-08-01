# Change: inventory-diagnostic-model-evidence-reconciliation

## Why

The current offline importer recognizes canonical `diagnostic_model` only from source `Модель` evidence. Real organization rows may contain blank or unmapped `Модель` while source `Наименование` contains exact deterministic evidence for an already supported model, for example `ATEN Aten PE8208AV`.

Because normal runtime dispatch intentionally uses only exact canonical `diagnostic_model`, those rows remain unmapped even though the importer already receives sufficient reviewed evidence. The importer needs symmetric reconciliation of the two approved model-text fields without expanding the supported-model registry, weakening exact matching, changing canonical schema, or moving free-form recognition into runtime code.

## What Changes

- Keep `Наименование -> source_model` unchanged and additionally evaluate normalized `Наименование` as importer-only diagnostic-model evidence.
- Continue evaluating normalized source `Модель` through the existing closed nine-model component registry.
- Evaluate both fields independently and obtain the complete canonical match set from each field:

```text
M = complete canonical match set from Модель
N = complete canonical match set from Наименование
C = M union N
```

- Classify the distinct union exactly:
  - zero matches -> `diagnostic_model = null` plus `UNMAPPED_DIAGNOSTIC_MODEL`;
  - one match -> publish that exact canonical model;
  - more than one match -> `diagnostic_model = null` plus `AMBIGUOUS_DIAGNOSTIC_MODEL`.
- Give neither source field priority over the other and preserve ambiguity when one field is internally ambiguous.
- Keep `Производитель` optional and non-authoritative.
- Add focused synthetic regression coverage and update the equipment-inventory runbook.

## Impact

Affected specification:

- `equipment-inventory-snapshot`

Expected implementation areas:

- `tools/import_equipment_inventory.py`
- `tests/test_equipment_inventory.py`
- `docs/equipment-inventory-runbook.md`
- change-specific implementation and validation evidence

This change does not add a supported canonical model. Unsupported values such as `Huawei CloudLink Box 610` remain unmapped until a separate reviewed model-support change exists.

This change does not add a converter GUI, Qt worker, file-selection workflow, expanded run-report contract, report export, second Excel source, switch-port enrichment, or GUI tests. Those are separate future changes.

This change also does not modify canonical schema versions or record fields, deterministic snapshot identity, authoritative `Тип модели -> device_kind` mapping, runtime inventory loading and queries, diagnostic dispatch, credentials, controllers, workers, handlers, PDU-room-codec enrichment, related-codec status, operational inventory data, or Graphify artifacts.
