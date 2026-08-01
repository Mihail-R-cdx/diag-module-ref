# Change: inventory-diagnostic-model-evidence-reconciliation

## Why

The current importer recognizes `diagnostic_model` only from the source `Модель` column. A reviewed production-data example contains unambiguous supported-model evidence in `Наименование` (`ATEN Aten PE8208AV`) while the generated canonical record has `diagnostic_model = null`. That prevents automatic inventory-driven dispatch and later PDU-room-codec enrichment even though the source row contains deterministic evidence for an already supported model.

Recognition must remain offline, exact, and fail-closed, but the importer needs to reconcile both available source model fields instead of discarding useful `Наименование` evidence.

## What Changes

- Keep `Наименование -> source_model` unchanged and additionally evaluate normalized `Наименование` as diagnostic-model recognition evidence.
- Continue evaluating normalized source `Модель` evidence through the existing closed nine-model component registry.
- Evaluate the two fields independently, combine the complete set of matching canonical rules, and classify the union:
  - zero distinct matches -> `diagnostic_model = null` plus `UNMAPPED_DIAGNOSTIC_MODEL`;
  - one distinct match -> publish that exact canonical model;
  - more than one distinct match -> `diagnostic_model = null` plus `AMBIGUOUS_DIAGNOSTIC_MODEL`.
- Accept a unique match from either field when the other field is blank or unmapped.
- Accept the model when both fields independently resolve to the same canonical value.
- Preserve ambiguity when one field is internally ambiguous or when the two fields resolve to different canonical values; neither field overrides the other.
- Keep `Производитель` as optional non-authoritative consistency evidence only.
- Preserve the existing component registry, exact boundaries, canonical schema, snapshot identity algorithm, `device_kind` authority, runtime loader, runtime dispatch, and PDU/codec orchestration.
- Add synthetic importer regression coverage and update the equipment-inventory runbook.

## Impact

Affected specification:

- `equipment-inventory-snapshot`

Expected implementation areas:

- `tools/import_equipment_inventory.py`
- `tests/test_equipment_inventory.py`
- `docs/equipment-inventory-runbook.md`

This change does not add a new supported canonical model. In particular, unsupported source values such as `Huawei CloudLink Box 610` remain unmapped until a separate reviewed model-support change exists. It does not modify GUI code, runtime inventory resolution, diagnostic dispatch, credentials, workers, handlers, PDU-to-room resolution, related-codec resolution, production inventory data, or Graphify artifacts.
