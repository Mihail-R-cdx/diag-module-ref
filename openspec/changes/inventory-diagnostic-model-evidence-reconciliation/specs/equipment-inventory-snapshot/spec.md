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

`diagnostic_model` SHALL be populated only through the separate explicit reviewed component registry defined by this capability. The importer SHALL apply that registry independently to normalized source `Модель` evidence and normalized source `Наименование` evidence, then reconcile the complete distinct canonical match union under the explicit cardinality requirement. `Наименование` SHALL remain authoritative for canonical `source_model`; using it as importer-side recognition evidence SHALL NOT rewrite `source_model` or make free-form source text a runtime dispatch authority.

The importer SHALL NOT guess a supported `diagnostic_model` from fuzzy, approximate, similar-looking, or arbitrary substring text. The source column `Производитель` MAY be used only as importer-side consistency evidence. It SHALL NOT be required for diagnostic-model recognition, add or remove a registry match, veto a unique reconciled match, or select between multiple matching registry rules. Neither `Производитель` nor `Модель` becomes a separate canonical schema-v1 field.

The source column `SmartRoomID контроллера` MAY be used only as importer-side consistency evidence for this capability. It SHALL NOT create `controller_record_id` or another controller relation in schema v1 and SHALL NOT create a runtime controller index.

#### Scenario: Confirmed source row is mapped

- **WHEN** the importer reads a source equipment row using the confirmed organization source contract
- **THEN** each available mapped source value is normalized into its corresponding canonical field
- **AND** source-only evidence fields are not copied into schema v1 unless explicitly approved by the schema
- **AND** diagnostic-model recognition follows only the reviewed component registry over the two approved model-text evidence fields

#### Scenario: Manufacturer evidence is unavailable

- **GIVEN** a source row has no usable `Производитель` value
- **WHEN** the reconciled match union from normalized `Модель` and `Наименование` evidence contains exactly one canonical model
- **THEN** the importer publishes that exact canonical `diagnostic_model`
- **AND** missing manufacturer evidence does not veto the result

#### Scenario: Model field is blank but name field is recognized

- **GIVEN** normalized source `Модель` is blank or unmapped
- **WHEN** normalized source `Наименование` satisfies exactly one reviewed registry rule and no other rule matches either field
- **THEN** the importer publishes that rule's exact canonical `diagnostic_model`
- **AND** canonical `source_model` remains the normalized `Наименование` value

### Requirement: Наименование is the authoritative source_model value

For the confirmed organization workbook, `Наименование` SHALL map directly to canonical `source_model` after canonical text normalization. If `Наименование` is absent or blank, `source_model` SHALL be null.

When `Наименование` is present, the importer SHALL NOT silently reconstruct or overwrite `source_model` from `Производитель` plus `Модель`. `Наименование` MAY also supply importer-side diagnostic-model recognition evidence through the same closed reviewed component registry used for `Модель`, but that derived use SHALL NOT alter the canonical `source_model` value and SHALL NOT authorize runtime dispatch from `source_model`.

`Производитель` and `Модель` MAY be used for consistency diagnostics. A mismatch among `Наименование`, `Производитель`, and `Модель` SHALL NOT by itself block snapshot publication or rewrite canonical `source_model`. When approved model-text evidence yields multiple distinct supported canonical matches, the diagnostic model outcome SHALL remain ambiguous under the separate cardinality requirement.

#### Scenario: Source model evidence disagrees

- **WHEN** normalized `Наименование` does not match an expected manufacturer/model combination derived for consistency checking
- **THEN** canonical `source_model` remains the normalized `Наименование` value
- **AND** the importer may report a structured non-fatal consistency issue
- **AND** it does not silently rewrite the source value

#### Scenario: Name evidence supplies a diagnostic model

- **GIVEN** normalized `Наименование` contains one unique reviewed supported-model pattern
- **WHEN** the importer uses that value as recognition evidence
- **THEN** canonical `source_model` remains the complete normalized `Наименование` text
- **AND** canonical `diagnostic_model` may contain the exact reviewed canonical model
- **AND** runtime consumers still use only `diagnostic_model` as dispatch authority

### Requirement: Diagnostic model recognition uses deterministic reviewed components

The importer SHALL evaluate source `Модель` and source `Наименование` as two independent approved model-text evidence fields. For each field separately, it SHALL apply Unicode NFC normalization, leading/trailing trim, and Unicode-aware casefold before recognition. A blank normalized value SHALL provide no components.

Recognition SHALL use exact components rather than arbitrary substrings. Non-alphanumeric characters SHALL act as component boundaries. Letter-to-digit and digit-to-letter transitions inside one alphanumeric chunk SHALL expose exact alphabetic and decimal components so compact forms such as `TE40`, `IN1804`, `PE8208`, and `DMP64` are recognized. An immediately adjacent decimal run plus alphabetic suffix SHALL also expose the exact reviewed mixed component needed for `4i` in `PCS4i`.

Component order and repetition SHALL NOT affect rule satisfaction. Space, hyphen, underscore, dot, slash, and other non-alphanumeric separators SHALL be treated as equivalent boundaries. The importer SHALL NOT use transliteration, typo correction, edit distance, token similarity, manufacturer guessing, field-specific aliases, or undeclared aliases.

The same closed reviewed registry SHALL be evaluated independently against each evidence field and SHALL remain exactly:

| Canonical `diagnostic_model` | Mandatory components in either approved evidence field |
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

`AV`, `CI`, and `Plus` SHALL NOT be required components for their canonical rules. Rule order and evidence-field order SHALL NOT grant authority or priority. This requirement SHALL NOT add any canonical model outside the existing registry.

#### Scenario: Compact TE40 evidence is recognized

- **WHEN** normalized source `Модель` or normalized source `Наименование` is `TE40`, `TE 40`, or `TE-40`
- **THEN** that field's evidence contains exact components `te` and `40`
- **AND** the `Huawei TE40` rule matches that field

#### Scenario: Optional canonical suffix is absent

- **WHEN** either normalized approved evidence field contains exact components `pe` and `8208` without `av`
- **THEN** the `Aten PE8208AV` rule matches that field
- **AND** the importer does not require the optional canonical suffix in source evidence

#### Scenario: Forte accent alternative is recognized

- **WHEN** either normalized approved evidence field contains `tesira` and exact component `forte` or `forté`
- **THEN** the `Biamp Tesira Forte CI` rule matches that field

#### Scenario: Similar longer components are rejected

- **WHEN** either normalized approved evidence field is `LTE 40`, `TE200`, `TE401`, `IN18040`, `PE82080`, or `DMP640`
- **THEN** no reviewed rule matches that field merely because a shorter key appears as a substring

#### Scenario: Unsupported model remains unmapped

- **WHEN** approved evidence contains `Huawei CloudLink Box 610` and no existing registry rule is satisfied
- **THEN** this requirement adds no new canonical model match
- **AND** separate support for that device requires another reviewed OpenSpec change

### Requirement: Diagnostic model match cardinality remains explicit

The importer SHALL evaluate every reviewed diagnostic-model rule independently against normalized source `Модель` evidence and normalized source `Наименование` evidence before selecting an outcome for a source row. Each field SHALL produce the complete set of matching canonical models. The importer SHALL form one combined set containing the distinct union of matches from both fields.

The outcome SHALL be exactly one of:

```text
zero distinct matches across both fields
    -> diagnostic_model = null
    -> one non-fatal data-quality issue UNMAPPED_DIAGNOSTIC_MODEL

exactly one distinct match across both fields
    -> diagnostic_model = that exact canonical value
    -> no UNMAPPED_DIAGNOSTIC_MODEL or AMBIGUOUS_DIAGNOSTIC_MODEL issue

more than one distinct match across both fields
    -> diagnostic_model = null
    -> one non-fatal data-quality issue AMBIGUOUS_DIAGNOSTIC_MODEL
```

The importer SHALL NOT select the first matching rule, depend on registry order, prioritize `Модель` over `Наименование`, prioritize `Наименование` over `Модель`, use `Производитель` as a tie-breaker, discard an internally ambiguous field because the other field agrees with one candidate, or emit both unmapped and ambiguous issues for the same row.

An unmapped or ambiguous model SHALL NOT by itself make an otherwise representable canonical record fatal or remove it from the candidate snapshot. Structured model-recognition issues MAY expose the safe source row number and canonical `record_id`. Normal diagnostics SHALL NOT dump either complete source field, the complete source row, workbook, production snapshot, or organization inventory.

#### Scenario: Exactly one rule matches

- **WHEN** the union of all reviewed matches from `Модель` and `Наименование` contains exactly one canonical model
- **THEN** canonical `diagnostic_model` is that exact supported model name
- **AND** no unmapped or ambiguous model issue is emitted

#### Scenario: No rule matches

- **WHEN** no reviewed rule matches normalized `Модель` or normalized `Наименование`, including when either or both fields are missing or blank
- **THEN** canonical `diagnostic_model` is null
- **AND** the importer emits `UNMAPPED_DIAGNOSTIC_MODEL`
- **AND** the row remains publishable when otherwise valid

#### Scenario: Both fields agree on one model

- **WHEN** `Модель` and `Наименование` independently match the same one canonical model and no additional rule matches either field
- **THEN** the distinct union contains one model
- **AND** canonical `diagnostic_model` is that model
- **AND** duplicate agreement does not create ambiguity

#### Scenario: Evidence fields resolve to different models

- **WHEN** normalized `Модель` matches one supported canonical model and normalized `Наименование` matches a different supported canonical model
- **THEN** canonical `diagnostic_model` is null
- **AND** the importer emits `AMBIGUOUS_DIAGNOSTIC_MODEL`
- **AND** neither evidence field overrides the other
- **AND** the row remains publishable when otherwise valid

#### Scenario: Multiple rules match

- **GIVEN** one approved evidence field satisfies more than one registry rule, such as combined `TE20 / TE40` evidence
- **WHEN** the other field is unmapped or agrees with only one of those candidates
- **THEN** the combined distinct union still contains more than one model
- **AND** canonical `diagnostic_model` is null
- **AND** the importer emits `AMBIGUOUS_DIAGNOSTIC_MODEL`
- **AND** it does not erase contradictory evidence through field priority or manufacturer evidence
