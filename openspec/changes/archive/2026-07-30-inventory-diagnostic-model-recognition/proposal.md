# Change: inventory-diagnostic-model-recognition

## Why

The offline equipment-inventory importer currently recognizes `diagnostic_model` only when the normalized pair `Производитель` plus `Модель` exactly matches a small lookup table. Real workbook values use case variations, separators, compact forms such as `TE40` and `DMP64`, optional suffixes such as `AV`, `CI`, and `Plus`, and supported models that are absent from the current table. As a result, records that contain enough deterministic model evidence are published with `diagnostic_model = null`.

The canonical snapshot must carry an exact application-supported `diagnostic_model` whenever the source `Модель` field contains one unambiguous reviewed component pattern. Recognition must remain deterministic and importer-only; runtime code must never dispatch from free-form source text.

## What Changes

- Replace exact manufacturer/model tuple lookup with a closed reviewed registry evaluated against the source `Модель` field.
- Normalize recognition evidence with Unicode NFC normalization, trim, and casefold, then extract exact lexical, numeric, and approved mixed components without fuzzy or arbitrary substring matching.
- Recognize these canonical models from mandatory component sets:

| Canonical `diagnostic_model` | Mandatory components in `Модель` |
| --- | --- |
| `Huawei TE20` | family marker `te` plus number `20` |
| `Huawei TE40` | family marker `te` plus number `40` |
| `CloudLink Bar 310` | `cloudlink` plus `bar` plus `310` |
| `Polycom RPG 310` | `rpg` plus `310`, or `realpresence` plus `group` plus `310` |
| `Extron IN1804` | family marker `in` plus number `1804` |
| `Aten PE8208AV` | `pe` plus `8208` |
| `Extron IPL T PCS4i` | `ipl` plus `pcs` plus `4i` |
| `Biamp Tesira Forte CI` | `tesira` plus `forte` or `forté` |
| `Extron DMP 64 Plus` | `dmp` plus `64` |

- Evaluate every registry rule for every row. Exactly one match publishes the corresponding canonical value; zero matches publish null plus `UNMAPPED_DIAGNOSTIC_MODEL`; multiple matches publish null plus `AMBIGUOUS_DIAGNOSTIC_MODEL`.
- Make `Производитель` optional consistency evidence only. It must not be required for recognition, veto a unique model-field match, or break an ambiguous match.
- Preserve authoritative `Наименование -> source_model` and `Тип модели -> device_kind` behavior unchanged.
- Add synthetic regression coverage for all positive forms, boundary negatives, missing or conflicting manufacturer evidence, ambiguity, and deterministic issue reporting.
- Update the equipment-inventory runbook after implementation to document the approved registry and recognition boundary.

## Impact

Affected specification:

- `equipment-inventory-snapshot`

Expected implementation areas:

- `tools/import_equipment_inventory.py`
- `tests/test_equipment_inventory.py`
- `docs/equipment-inventory-runbook.md`

This change does not modify the canonical schema version, runtime inventory query APIs, GUI model selection, device dispatch, credential selection, device handlers, `device_kind` authority, PDU-to-room resolution, related-codec resolution, production inventory data, or Graphify artifacts.
