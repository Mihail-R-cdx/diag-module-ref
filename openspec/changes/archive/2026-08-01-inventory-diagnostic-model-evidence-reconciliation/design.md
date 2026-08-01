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

That separation remains correct. The current recognition authority is too narrow because only source `Модель` participates in the reviewed registry, while `Наименование` is preserved as `source_model` but ignored as recognition evidence. A reviewed organization-row example shows that `Наименование` may contain unique deterministic evidence for an existing supported model when `Модель` is blank or unmapped.

The correction belongs entirely inside the offline importer. Runtime code continues to consume only exact canonical `diagnostic_model` and does not inspect free-form model text.

## Goals

1. Use source `Модель` and source `Наименование` as two independent deterministic recognition-evidence fields.
2. Preserve the existing closed nine-model registry and exact component-boundary semantics.
3. Produce the complete canonical match set from each evidence field before selecting an outcome.
4. Accept one canonical model only when the distinct union of both match sets contains exactly one model.
5. Preserve ambiguity when evidence within one field or across the two fields names multiple supported models.
6. Preserve `Наименование -> source_model` without rewriting the source value.
7. Preserve importer safety, canonical schema, deterministic snapshot identity, and runtime exact-only authority.

## Non-goals

- Do not add a standalone converter GUI, Qt dependency, worker thread, file chooser, progress display, issue table, or report export.
- Do not add a second Excel source or switch-port enrichment.
- Do not refactor the converter into a new expanded run-report protocol.
- Do not add a new supported canonical diagnostic model.
- Do not map `Huawei CloudLink Box 610` or any other currently unsupported model.
- Do not change canonical JSON schema versions, canonical record fields, or `snapshot_id` identity inputs.
- Do not infer `diagnostic_model` at runtime from `source_model` or other free-form text.
- Do not modify diagnostic dispatch, credentials, controllers, workers, handlers, transports, PDU enrichment, or related-codec status logic.
- Do not let recognized model evidence override authoritative `Тип модели -> device_kind` mapping.
- Do not add fuzzy matching, arbitrary substring matching, typo correction, transliteration, edit distance, token similarity, manufacturer guessing, machine-learning classification, field-specific aliases, or registry-order tie breakers.
- Do not commit production workbook rows, generated production snapshots, internal IP addresses, room IDs, equipment IDs, MAC addresses, or serial numbers.

## Decision 1: Preserve the source/canonical split

`Наименование` remains authoritative for canonical `source_model`:

```text
normalize source Наименование
    -> source_model
```

The importer may use the same normalized source value as recognition evidence, but that derived use does not rewrite `source_model` and does not make `source_model` a runtime dispatch authority.

Example:

```text
Наименование: ATEN Aten PE8208AV
Модель: blank

source_model: ATEN Aten PE8208AV
diagnostic_model: Aten PE8208AV
```

## Decision 2: Evaluate each evidence field independently

The importer applies the same existing normalization, component extraction, and closed registry to each field independently:

```text
source Модель
    -> normalized component set
    -> complete matching canonical-model set M

source Наименование
    -> normalized component set
    -> complete matching canonical-model set N
```

Normalization remains Unicode NFC, trim, Unicode-aware `casefold()`, exact non-alphanumeric boundaries, exact letter-to-digit and digit-to-letter transitions, and the already approved mixed `4i` component behavior.

The registry remains exactly:

```text
Huawei TE20
Huawei TE40
CloudLink Bar 310
Polycom RPG 310
Extron IN1804
Aten PE8208AV
Extron IPL T PCS4i
Biamp Tesira Forte CI
Extron DMP 64 Plus
```

No evidence field has its own aliases, manufacturer requirements, rule ordering, or fallback behavior.

## Decision 3: Reconcile by distinct-match union

Let:

```text
M = complete canonical match set from Модель
N = complete canonical match set from Наименование
C = M union N
```

The importer determines the row outcome only from the cardinality of `C`:

```text
|C| = 0
    -> diagnostic_model = null
    -> UNMAPPED_DIAGNOSTIC_MODEL

|C| = 1
    -> diagnostic_model = the one exact canonical model
    -> no model-recognition issue

|C| > 1
    -> diagnostic_model = null
    -> AMBIGUOUS_DIAGNOSTIC_MODEL
```

This policy is symmetric. Neither `Модель` nor `Наименование` overrides the other. `Производитель` cannot break ties, add matches, remove matches, or veto a unique reconciled result.

An internally ambiguous evidence field remains ambiguous even when the other field agrees with one of its candidates. Duplicate agreement on the same canonical model does not create ambiguity because the combined collection is a distinct set.

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

Result: null plus `AMBIGUOUS_DIAGNOSTIC_MODEL`.

### Neither field maps

```text
Модель: CloudLink Box 610
Наименование: Huawei CloudLink Box 610
M = {}
N = {}
C = {}
```

Result: null plus `UNMAPPED_DIAGNOSTIC_MODEL`.

## Decision 5: Implementation boundary

A compliant importer implementation separates rule evaluation from row-level reconciliation. Concrete private names are not contracts, but the behavior is equivalent to:

```text
evaluate_model_evidence(value)
    -> complete immutable set of matching canonical models

reconcile_model_evidence(model_value, name_value)
    -> union both complete sets
    -> classify zero, one, or many
```

The existing component extractor and closed rule registry remain shared by both evidence fields. The implementation must not call a helper that prematurely converts one field into mapped/unmapped/ambiguous and then discard that field's complete candidate set.

Row construction continues to:

- normalize `Наименование` once for canonical `source_model`;
- evaluate both approved evidence fields before assigning `diagnostic_model`;
- emit exactly one of mapped, unmapped, or ambiguous outcomes;
- preserve `source_model`, `device_kind`, and all other canonical fields independently;
- preserve non-fatal model-recognition issue semantics when the row is otherwise representable.

No runtime module, GUI module, controller, worker, handler, credential component, or PDU-codec orchestration component changes for this implementation.

## Decision 6: Safety and operational boundaries remain unchanged

Normal diagnostics may expose a safe source row and canonical `record_id`, but must not dump complete `Модель` or `Наименование` values, complete source rows, workbook content, production snapshots, or organization inventory.

The deployment workbook and generated `equipment_inventory.local.json` remain local operational data outside Git. After implementation is approved, archived, and deployed, the local snapshot must be regenerated offline so runtime receives corrected exact `diagnostic_model` values.

## Regression coverage

Focused synthetic tests must cover at least:

- blank `Модель` plus uniquely recognized `Наименование`;
- recognized `Модель` plus blank or unmapped `Наименование`;
- both fields resolving to the same canonical model;
- fields resolving to different canonical models;
- one internally ambiguous field plus one agreeing unique field;
- one internally ambiguous field plus an unmapped field;
- both fields unmapped;
- all nine existing canonical models through `Наименование` evidence;
- existing separator, compact-form, optional-suffix, accent-alternative, and boundary-negative cases for both evidence fields;
- unchanged normalized `source_model`;
- unchanged authoritative `device_kind` and expected-kind consistency behavior;
- mutually exclusive mapped/unmapped/ambiguous outcomes;
- unchanged schema version, canonical record shape, and deterministic snapshot identity;
- unchanged runtime exact-only dispatch and PDU enrichment behavior through existing regression modules.

All fixtures remain synthetic and must not contain real organization inventory.

## Rollout

1. Implement the approved importer-only reconciliation and focused tests.
2. Run focused importer tests, runtime regression tests, the full offline suite, and strict OpenSpec validation.
3. Independently validate the exact published remote branch HEAD in a clean detached worktree.
4. Perform the required disposable archive-applicability check because this change modifies root requirements.
5. Archive and perform post-archive checks only after independent approval.
6. After deployment, regenerate the local canonical inventory snapshot offline from the configured organization workbook.

A standalone operator GUI, second Excel input, switch-port enrichment, individual file tests, combined preflight, and expanded report workflow require separate future OpenSpec changes.
