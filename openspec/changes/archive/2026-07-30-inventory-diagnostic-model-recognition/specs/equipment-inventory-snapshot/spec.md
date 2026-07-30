# equipment-inventory-snapshot Specification

## MODIFIED Requirements

### Requirement: Confirmed organization source-to-canonical mapping

For the inspected organization workbook, the importer SHALL use this authoritative schema-v1 mapping:

```text
SmartRoomID       -> record_id
ID комнаты        -> room_id
Название комнаты  -> room_name
Наименование      -> source_model
IP                -> ip_address
MAC               -> mac_address
Серийный номер    -> serial_number
Тип модели        -> device_kind
```

`diagnostic_model` SHALL be populated only through the separate explicit reviewed model-field component registry defined by this capability. The source `Модель` column SHALL provide recognition evidence for that registry. The importer SHALL NOT guess a supported `diagnostic_model` from fuzzy, approximate, similar-looking, or arbitrary substring text.

The source column `Производитель` MAY be used only as importer-side consistency evidence. It SHALL NOT be required for diagnostic-model recognition, veto a unique model-field match, or select between multiple matching registry rules. Neither `Производитель` nor `Модель` becomes a separate canonical schema-v1 field.

The source column `SmartRoomID контроллера` MAY be used only as importer-side consistency evidence for this capability. It SHALL NOT create `controller_record_id` or another controller relation in schema v1 and SHALL NOT create a runtime controller index.

#### Scenario: Confirmed source row is mapped

- **WHEN** the importer reads a source equipment row using the confirmed organization source contract
- **THEN** each available mapped source value is normalized into its corresponding canonical field
- **AND** source-only evidence fields are not copied into schema v1 unless explicitly approved by the schema
- **AND** diagnostic-model recognition follows only the reviewed model-field component registry

#### Scenario: Manufacturer evidence is unavailable

- **GIVEN** a source row has no usable `Производитель` value
- **WHEN** its normalized `Модель` evidence satisfies exactly one reviewed registry rule
- **THEN** the importer publishes that rule's exact canonical `diagnostic_model`
- **AND** missing manufacturer evidence does not veto the result

## ADDED Requirements

### Requirement: Diagnostic model recognition uses deterministic reviewed components

The importer SHALL normalize source `Модель` evidence using Unicode NFC normalization, leading/trailing trim, and Unicode-aware casefold before recognition. A blank normalized value SHALL provide no components.

Recognition SHALL use exact components rather than arbitrary substrings. Non-alphanumeric characters SHALL act as component boundaries. Letter-to-digit and digit-to-letter transitions inside one alphanumeric chunk SHALL expose exact alphabetic and decimal components so compact forms such as `TE40`, `IN1804`, `PE8208`, and `DMP64` are recognized. An immediately adjacent decimal run plus alphabetic suffix SHALL also expose the exact reviewed mixed component needed for `4i` in `PCS4i`.

Component order and repetition SHALL NOT affect rule satisfaction. Space, hyphen, underscore, dot, slash, and other non-alphanumeric separators SHALL be treated as equivalent boundaries. The importer SHALL NOT use transliteration, typo correction, edit distance, token similarity, manufacturer guessing, or undeclared aliases.

The closed reviewed registry SHALL be exactly:

| Canonical `diagnostic_model` | Mandatory source `Модель` components |
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

`AV`, `CI`, and `Plus` SHALL NOT be required components for their canonical rules. Rule order SHALL NOT grant authority or priority.

#### Scenario: Compact TE40 evidence is recognized

- **WHEN** normalized source `Модель` is `TE40`, `TE 40`, or `TE-40`
- **THEN** the evidence contains exact components `te` and `40`
- **AND** the `Huawei TE40` rule matches

#### Scenario: Optional canonical suffix is absent

- **WHEN** normalized source `Модель` contains exact components `pe` and `8208` without `av`
- **THEN** the `Aten PE8208AV` rule matches
- **AND** the importer does not require the optional canonical suffix in source evidence

#### Scenario: Forte accent alternative is recognized

- **WHEN** normalized source `Модель` contains `tesira` and either exact component `forte` or `forté`
- **THEN** the `Biamp Tesira Forte CI` rule matches

#### Scenario: Similar longer components are rejected

- **WHEN** normalized source `Модель` is `LTE 40`, `TE200`, `TE401`, `IN18040`, `PE82080`, or `DMP640`
- **THEN** no reviewed rule matches merely because a shorter key appears as a substring

### Requirement: Diagnostic model match cardinality remains explicit

The importer SHALL evaluate every reviewed diagnostic-model rule before selecting an outcome for a source row.

The outcome SHALL be exactly one of:

```text
zero matching rules
    -> diagnostic_model = null
    -> one non-fatal data-quality issue UNMAPPED_DIAGNOSTIC_MODEL

exactly one matching rule
    -> diagnostic_model = the rule's exact canonical value
    -> no UNMAPPED_DIAGNOSTIC_MODEL or AMBIGUOUS_DIAGNOSTIC_MODEL issue

more than one matching rule
    -> diagnostic_model = null
    -> one non-fatal data-quality issue AMBIGUOUS_DIAGNOSTIC_MODEL
```

The importer SHALL NOT select the first matching rule, depend on registry order, use `Производитель` as a tie-breaker, or emit both unmapped and ambiguous issues for the same row. An unmapped or ambiguous model SHALL NOT by itself make an otherwise representable canonical record fatal or remove it from the candidate snapshot.

Structured model-recognition issues MAY expose the safe source row number and canonical `record_id`. Normal diagnostics SHALL NOT dump the complete source row, workbook, production snapshot, or organization inventory.

#### Scenario: Exactly one rule matches

- **WHEN** one and only one reviewed rule matches normalized source `Модель` evidence
- **THEN** canonical `diagnostic_model` is that rule's exact supported model name
- **AND** no unmapped or ambiguous model issue is emitted

#### Scenario: No rule matches

- **WHEN** no reviewed rule matches normalized source `Модель` evidence, including missing or blank model evidence
- **THEN** canonical `diagnostic_model` is null
- **AND** the importer emits `UNMAPPED_DIAGNOSTIC_MODEL`
- **AND** the row remains publishable when otherwise valid

#### Scenario: Multiple rules match

- **WHEN** one source `Модель` value satisfies more than one reviewed registry rule, such as combined `TE20 / TE40` evidence
- **THEN** canonical `diagnostic_model` is null
- **AND** the importer emits `AMBIGUOUS_DIAGNOSTIC_MODEL`
- **AND** it does not select a model from rule order or manufacturer evidence
- **AND** the row remains publishable when otherwise valid
