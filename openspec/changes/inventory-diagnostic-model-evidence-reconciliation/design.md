# Design: Inventory diagnostic model evidence reconciliation

## Context

The approved inventory boundary remains:

```text
organization Excel workbook
    -> offline importer
    -> canonical versioned JSON snapshot
    -> runtime EquipmentInventory
    -> application-owned exact dispatch and orchestration
```

Canonical runtime records deliberately separate:

```text
source_model
    = normalized organization value from Наименование

diagnostic_model
    = exact application-supported canonical model or null
```

That separation is correct and remains unchanged. The current recognition authority is too narrow: only source `Модель` participates in the closed component registry, while `Наименование` is preserved but ignored for recognition. A reviewed production-data example proves that `Наименование` may contain unique deterministic evidence for an existing supported model when `Модель` does not produce a mapping.

Runtime consumers already require exact canonical `diagnostic_model`; therefore the correction belongs entirely inside the offline importer before snapshot publication.

## Goals

1. Use both source `Модель` and source `Наименование` as independent deterministic recognition evidence.
2. Preserve the existing closed nine-model registry and exact component-boundary semantics.
3. Accept one canonical model when the union of matches from both fields contains exactly one distinct model.
4. Preserve ambiguity when evidence within or across the two fields names multiple supported models.
5. Preserve `Наименование -> source_model` without rewriting the source value.
6. Keep manufacturer evidence optional and non-authoritative.
7. Keep runtime exact-only and unchanged.
8. Add synthetic regression coverage for reconciliation outcomes and production-like formatting without committing operational data.

## Non-goals

- Do not add a new supported canonical diagnostic model.
- Do not map `Huawei CloudLink Box 610` or any other currently unsupported model.
- Do not change the canonical JSON schema version or record fields.
- Do not infer `diagnostic_model` at runtime from `source_model` or other free-form text.
- Do not modify diagnostic dispatch, GUI, credentials, controllers, workers, handlers, transports, PDU enrichment, or related-codec status logic.
- Do not let recognized model evidence override authoritative `Тип модели -> device_kind` mapping.
- Do not add fuzzy matching, arbitrary substring matching, typo correction, transliteration, edit distance, token similarity, manufacturer guessing, or machine-learning classification.
- Do not commit production workbook rows, generated production snapshots, internal IP addresses, room IDs, equipment IDs, MAC addresses, or serial numbers.

## Decision 1: Preserve the source/canonical split

`Наименование` remains authoritative for canonical `source_model`:

```text
normalize source Наименование
    -> source_model
```

Using the same normalized value as recognition evidence does not make `source_model` a runtime authority and does not authorize rewriting it. The importer may derive `diagnostic_model` from evidence while preserving the original normalized organization value exactly.

Example:

```text
Наименование: ATEN Aten PE8208AV
Модель: blank

source_model: ATEN Aten PE8208AV
diagnostic_model: Aten PE8208AV
```

## Decision 2: Evaluate each evidence field independently

The importer applies the same existing normalization and component extraction to each field independently:

```text
source Модель
    -> normalized component set
    -> complete matching canonical-rule set

source Наименование
    -> normalized component set
    -> complete matching canonical-rule set
```

Normalization remains Unicode NFC, trim, Unicode-aware casefold, exact non-alphanumeric boundaries, exact letter/digit transitions, and the already approved `4i` mixed component behavior.

The registry remains exactly the existing nine canonical models. No field-specific aliases, manufacturer requirements, or different rule ordering are introduced.

## Decision 3: Reconcile by distinct-match union

Let:

```text
M = complete canonical match set from Модель
N = complete canonical match set from Наименование
C = M union N
```

The canonical outcome is determined only from the cardinality of `C`:

```text
|C| = 0
    -> diagnostic_model = null
    -> UNMAPPED_DIAGNOSTIC_MODEL

|C| = 1
    -> diagnostic_model = the one exact canonical model
    -> no unmapped or ambiguous model issue

|C| > 1
    -> diagnostic_model = null
    -> AMBIGUOUS_DIAGNOSTIC_MODEL
```

This policy is symmetric. `Модель` does not override `Наименование`, and `Наименование` does not override `Модель`.

## Decision 4: Reconciliation examples

### Blank model field, unique name field

```text
Модель: blank
Наименование: ATEN Aten PE8208AV
M = {}
N = {Aten PE8208AV}
C = {Aten PE8208AV}
```

Result: `Aten PE8208AV`.

### Unique model field, unmapped name field

```text
Модель: TE40
Наименование: ВКС терминал
M = {Huawei TE40}
N = {}
C = {Huawei TE40}
```

Result: `Huawei TE40`.

### Both fields agree

```text
Модель: PE8208AV
Наименование: ATEN Aten PE8208AV
M = {Aten PE8208AV}
N = {Aten PE8208AV}
C = {Aten PE8208AV}
```

Result: `Aten PE8208AV`.

### Fields disagree

```text
Модель: PCS4i
Наименование: ATEN Aten PE8208AV
M = {Extron IPL T PCS4i}
N = {Aten PE8208AV}
C = {Extron IPL T PCS4i, Aten PE8208AV}
```

Result: null plus `AMBIGUOUS_DIAGNOSTIC_MODEL`.

### One field is internally ambiguous

```text
Модель: TE20 / TE40
Наименование: Huawei TE20
M = {Huawei TE20, Huawei TE40}
N = {Huawei TE20}
C = {Huawei TE20, Huawei TE40}
```

Result: null plus `AMBIGUOUS_DIAGNOSTIC_MODEL`. Unique evidence in the other field does not erase contradictory supported-model evidence.

### Neither field maps

```text
Модель: CloudLink Box 610
Наименование: Huawei CloudLink Box 610
M = {}
N = {}
C = {}
```

Result: null plus `UNMAPPED_DIAGNOSTIC_MODEL`. This change does not add Box 610 support.

## Decision 5: Keep issue cardinality stable

Each source row still receives exactly one model-recognition outcome:

- mapped;
- unmapped;
- ambiguous.

No new required issue code is introduced. Cross-field disagreement is represented by the existing `AMBIGUOUS_DIAGNOSTIC_MODEL` because more than one reviewed canonical rule matched the row's approved evidence corpus.

The importer must not emit both `UNMAPPED_DIAGNOSTIC_MODEL` and `AMBIGUOUS_DIAGNOSTIC_MODEL` for one row.

## Decision 6: Manufacturer remains consistency evidence only

`Производитель` may continue to support non-fatal consistency diagnostics. It cannot:

- be required for recognition;
- add a canonical match absent from both approved model text fields;
- veto a unique union result;
- remove a match from either field;
- select one model when the union contains multiple models;
- rewrite `source_model` or `device_kind`.

## Decision 7: Runtime remains exact-only

The runtime contract remains:

```text
canonical diagnostic_model
    -> exact application-owned dispatch
```

Runtime modules must not reproduce component extraction, inspect `source_model` as protocol authority, or compensate for old snapshots. Deployment must regenerate `equipment_inventory.local.json` with the corrected importer.

Existing valid snapshots remain loadable. A regenerated snapshot may change `diagnostic_model` values and therefore legitimately receives a new deterministic `snapshot_id`.

## Implementation shape

A compliant implementation should expose one reusable private recognition function equivalent to:

```text
recognize one evidence string
    -> frozenset of all matching canonical models
```

Row construction then performs:

```text
model_matches = recognize(Модель)
name_matches = recognize(Наименование)
combined_matches = model_matches union name_matches
classify zero / one / many
```

The current private helper names and exact internal data structures are not architectural contracts.

## Regression coverage

Focused synthetic tests must cover at least:

- blank `Модель` plus recognized `Наименование`;
- recognized `Модель` plus blank or unmapped `Наименование`;
- both fields resolving to the same model;
- fields resolving to different models;
- one internally ambiguous field plus one agreeing unique field;
- one internally ambiguous field plus an unmapped field;
- both fields unmapped;
- all nine existing canonical models through `Наименование` evidence;
- existing component separators, compact forms, optional suffix behavior, accent alternatives, and boundary-negative cases for both evidence fields;
- unchanged `source_model` bytes after canonical text normalization;
- unchanged authoritative `device_kind` mapping;
- exactly one mapped/unmapped/ambiguous outcome per row;
- deterministic snapshot identity for equivalent canonical results;
- no runtime import of recognition helpers;
- no production data in fixtures or diagnostics.

## Rollout

After implementation and validation:

1. Deploy the updated offline converter.
2. Regenerate the deployment-local `equipment_inventory.local.json` from the configured workbook.
3. Review the import report for unmapped and ambiguous records.
4. Replace the previous snapshot only through the existing atomic publication path.
5. Restart or reload the diagnostic application under the existing deployment procedure.

No runtime migration or compatibility fallback is added.
