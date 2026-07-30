# Design: Inventory diagnostic model recognition

## Context

The approved inventory boundary is:

```text
organization Excel workbook
    -> offline importer
    -> canonical versioned JSON snapshot
    -> runtime EquipmentInventory
    -> application/composition orchestration
```

The source columns `Производитель` and `Модель` are importer-only evidence. Canonical runtime records contain exact `diagnostic_model` or null and do not expose those evidence columns as new runtime fields.

The current importer performs an exact lookup by `(manufacturer.casefold(), model.casefold())`. That approach requires both fields, accepts only enumerated full strings, omits two currently supported application models, and cannot recognize safe compact or separator variants. Runtime consumers already require exact canonical model names, so recognition belongs entirely before snapshot publication.

## Goals

1. Recognize every currently supported canonical diagnostic model from deterministic reviewed evidence in the source `Модель` field.
2. Accept case, separator, and compact spelling variants without introducing fuzzy matching.
3. Preserve component boundaries so similar longer values do not match accidentally.
4. Preserve ambiguity instead of selecting the first matching rule.
5. Keep manufacturer evidence optional and non-authoritative for model recognition.
6. Preserve canonical schema, `source_model`, `device_kind`, snapshot identity, runtime lookup, and runtime dispatch boundaries.
7. Make importer outcomes fully regression-testable with synthetic data.

## Non-goals

- Do not change the GUI or remove the current model selector.
- Do not implement inventory-driven runtime device dispatch or its manual fallback dialog.
- Do not infer a model at runtime from `source_model`, `Производитель`, or `Модель`.
- Do not change canonical `device_kind` values or the exact `Тип модели` mapping.
- Do not use recognized model evidence to override `device_kind`.
- Do not introduce aliases outside the closed registry in this change.
- Do not add transliteration, typo correction, Levenshtein distance, token similarity, regular-expression guess lists, or machine-learning classification.
- Do not commit a real workbook, generated production snapshot, or source-row samples.

## Authority and evidence boundary

For diagnostic-model recognition, authority is:

```text
approved component registry
    -> normalized source Модель evidence
    -> exact canonical diagnostic_model or null
```

`Модель` is the only source field that participates in rule satisfaction. `Производитель` may continue to support non-fatal consistency diagnostics but cannot:

- be required before a model can be recognized;
- veto an otherwise unique component match;
- select between multiple matching rules;
- rewrite canonical `source_model` or `device_kind`.

`Наименование` remains authoritative for `source_model`. `Тип модели` remains authoritative for `device_kind`. Recognition changes only `diagnostic_model` and its structured importer issue.

## Recognition normalization

The importer creates recognition evidence from the source `Модель` value only:

1. Apply the existing canonical text conversion needed to obtain a non-empty string.
2. Normalize Unicode to NFC.
3. Trim leading and trailing whitespace.
4. Apply Unicode-aware `casefold()`.
5. Split evidence at non-alphanumeric separators.
6. Within alphanumeric chunks, expose exact alphabetic and decimal runs at letter-to-digit and digit-to-letter transitions.
7. For an immediately adjacent decimal run followed by an alphabetic suffix, also expose the exact combined suffix needed for reviewed mixed components, such as `4i` in `PCS4i`.

The resulting evidence is a set. Component order and repetition do not affect recognition. Space, hyphen, underscore, dot, slash, and other non-alphanumeric separators are equivalent boundaries.

Examples:

```text
TE40, TE 40, TE-40, Huawei_TE.40
    -> contains exact components te and 40

DMP64, DMP 64, Extron/DMP-64-Plus
    -> contains exact components dmp and 64

IPL T PCS4i, IPL-T-PCS-4i
    -> contains exact components ipl, pcs, and 4i
```

Boundary preservation is mandatory:

```text
LTE 40   -> does not contain alphabetic component te
TE200    -> does not contain numeric component 20
TE401    -> does not contain numeric component 40
IN18040  -> does not contain numeric component 1804
PE82080  -> does not contain numeric component 8208
DMP640   -> does not contain numeric component 64
```

The implementation may use another internal representation only if tests prove the same observable component and boundary semantics.

## Closed recognition registry

Every row is evaluated against all rules in this exact closed registry:

| Canonical `diagnostic_model` | Rule |
| --- | --- |
| `Huawei TE20` | `te` and `20` |
| `Huawei TE40` | `te` and `40` |
| `CloudLink Bar 310` | `cloudlink`, `bar`, and `310` |
| `Polycom RPG 310` | (`rpg` and `310`) or (`realpresence`, `group`, and `310`) |
| `Extron IN1804` | `in` and `1804` |
| `Aten PE8208AV` | `pe` and `8208` |
| `Extron IPL T PCS4i` | `ipl`, `pcs`, and `4i` |
| `Biamp Tesira Forte CI` | `tesira` and (`forte` or `forté`) |
| `Extron DMP 64 Plus` | `dmp` and `64` |

`AV`, `CI`, and `Plus` are deliberately optional because they are not required keys in the approved source evidence. A rule may not add an undeclared manufacturer requirement or optional tie-breaker.

The registry must be represented as reviewable data or equally explicit code. Rule order is not authority.

## Match cardinality

All rules run before an outcome is selected:

```text
zero matching rules
    -> diagnostic_model = null
    -> data-quality issue UNMAPPED_DIAGNOSTIC_MODEL

exactly one matching rule
    -> diagnostic_model = exact canonical rule value
    -> no unmapped or ambiguous model issue

more than one matching rule
    -> diagnostic_model = null
    -> data-quality issue AMBIGUOUS_DIAGNOSTIC_MODEL
```

The importer must not choose the first matching rule, use registry order, use manufacturer evidence as a tie-breaker, or emit both unmapped and ambiguous issues for one row.

A combined value such as `TE20 / TE40` is intentionally ambiguous even when another evidence column appears to prefer one model. The canonical record remains representable and publication remains allowed unless an unrelated fatal source-contract issue exists.

## Structured diagnostics

`UNMAPPED_DIAGNOSTIC_MODEL` and `AMBIGUOUS_DIAGNOSTIC_MODEL` are non-fatal data-quality issues. Each issue may include the safe source row number and canonical `record_id`; normal diagnostics must not dump the complete row, workbook, or organization inventory.

The issue result must be deterministic for equivalent normalized evidence. Missing or blank `Модель` is an unmapped outcome, not an exception and not a fatal source-structure failure when the canonical row is otherwise representable.

## Canonical snapshot and compatibility

This change does not add or remove canonical fields and does not change the generated schema version. Existing valid snapshots remain loadable under their current schema contracts.

Re-importing the same workbook after implementation may change `diagnostic_model` from null to an exact canonical value. Because `diagnostic_model` is part of canonical `records`, that expected content change produces a new deterministic `snapshot_id`. Generation metadata remains excluded from identity.

Runtime behavior remains exact-only:

```text
canonical diagnostic_model
    -> later application-owned exact dispatch
```

No runtime consumer may reproduce the component recognizer or dispatch from free-form source text.

## Implementation shape

The implementation should separate:

```text
normalize model evidence
    -> extract exact components
    -> evaluate all closed rules
    -> classify zero / one / many
    -> populate diagnostic_model and one applicable issue
```

The existing direct tuple dictionary may be replaced by a declarative rule registry and focused helper types or functions. Concrete private names are not architectural contracts.

The existing known-model/type consistency warning remains non-authoritative. This change does not require changing `device_kind`, and a type mismatch must not suppress or alter an otherwise unique diagnostic-model result.

## Regression coverage

Focused tests must cover at least:

- every canonical model in the closed registry;
- uppercase, lowercase, and mixed-case values;
- whitespace, hyphen, underscore, dot, slash, and compact forms;
- `TE20`, `TE40`, `IN1804`, `PE8208`, `DMP64`, and `PCS4i` letter/digit transitions;
- accepted optional suffix presence or absence for `AV`, `CI`, and `Plus`;
- both `Polycom RPG 310` alternatives;
- both `forte` and `forté`;
- missing and conflicting manufacturer evidence without recognition veto;
- missing or blank model evidence;
- the boundary-negative examples in this design;
- one source value that matches multiple registry rules;
- exactly one of mapped, unmapped, or ambiguous outcome per row;
- unchanged `source_model` and exact `device_kind` authority;
- deterministic snapshot identity for equivalent canonical results;
- no real organization data in fixtures or diagnostics.

## Rollout and operational documentation

Implementation updates the equipment-inventory runbook with the closed registry, component semantics, issue codes, and the requirement to regenerate the deployment-local snapshot offline. Runtime does not need a migration step beyond loading the newly generated valid snapshot.

The production workbook and generated `equipment_inventory.local.json` remain deployment-local and outside Git.
