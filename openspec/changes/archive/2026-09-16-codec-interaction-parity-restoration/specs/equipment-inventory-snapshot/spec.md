## MODIFIED Requirements

### Requirement: Device kind uses exact authoritative source type mapping

Schema-v1 `device_kind` SHALL use the closed vocabulary:

```text
pdu
video_codec
other
```

For the confirmed organization workbook, the importer SHALL map exact normalized source `Тип модели` values as follows:

```text
Video Conference -> video_codec
БРП              -> pdu
any other value  -> other
```

The importer SHALL NOT use substring matching, fuzzy matching, model-name guessing, manufacturer guessing, recognized diagnostic-model evidence, GUI page registration, or runtime diagnostic routing to silently override the result of this exact source-type mapping.

A known supported model whose source `Тип модели` maps to an unexpected `device_kind` MAY produce the structured non-fatal consistency issue `KNOWN_MODEL_TYPE_MISMATCH`. The expected-kind registry used by that diagnostic is importer-only consistency evidence. It SHALL NOT grant authority to change `device_kind`, suppress an exact recognized `diagnostic_model`, choose a runtime page/controller, or alter canonical schema.

For the currently reviewed diagnostic models, the importer-side consistency expectations SHALL be:

```text
Huawei TE50          -> video_codec
Aten PE8208AV        -> other
Extron IPL T PCS4i   -> other
```

These expected values reflect the authoritative source-type contract for the reviewed organization rows. Runtime PDU or codec dispatch is independently authorized by exact canonical `diagnostic_model`; it SHALL NOT require an expected `device_kind` result.

#### Scenario: Video Conference type is mapped

- **WHEN** normalized `Тип модели` is exactly `Video Conference`
- **THEN** canonical `device_kind` is exactly `video_codec`

#### Scenario: БРП type is mapped

- **WHEN** normalized `Тип модели` is exactly `БРП`
- **THEN** canonical `device_kind` is exactly `pdu`

#### Scenario: Other type value is mapped safely

- **WHEN** normalized `Тип модели` is any value other than the two explicitly mapped values, including an unknown or new value
- **THEN** canonical `device_kind` is exactly `other`
- **AND** the importer does not guess a more specific kind from other text, recognized model, or diagnostic page registration

#### Scenario: Huawei TE50 has a video-codec consistency expectation

- **GIVEN** reviewed recognition yields exact `diagnostic_model = Huawei TE50`
- **WHEN** importer consistency diagnostics evaluate the expected-kind registry
- **THEN** the expected kind is exactly `video_codec`
- **AND** exact source `Тип модели` mapping remains the sole authority for canonical `device_kind`
- **AND** a mismatch is non-fatal consistency evidence and does not suppress the recognized diagnostic model

#### Scenario: Correct Aten source type has no known-model mismatch

- **GIVEN** source `Модель` evidence recognizes exact `diagnostic_model = Aten PE8208AV`
- **AND** exact source `Тип модели` mapping produces `device_kind = other`
- **WHEN** importer consistency diagnostics are evaluated
- **THEN** no `KNOWN_MODEL_TYPE_MISMATCH` is emitted for that record
- **AND** `device_kind` remains `other`

#### Scenario: Correct PCS4i source type has no known-model mismatch

- **GIVEN** source `Модель` evidence recognizes exact `diagnostic_model = Extron IPL T PCS4i`
- **AND** exact source `Тип модели` mapping produces `device_kind = other`
- **WHEN** importer consistency diagnostics are evaluated
- **THEN** no `KNOWN_MODEL_TYPE_MISMATCH` is emitted for that record
- **AND** `device_kind` remains `other`

#### Scenario: Known model conflicts with source type

- **GIVEN** source `Модель` evidence recognizes exact `diagnostic_model = Aten PE8208AV`
- **AND** exact source `Тип модели` mapping produces `device_kind = pdu` or `video_codec`
- **WHEN** importer consistency diagnostics are evaluated
- **THEN** the importer emits non-fatal `KNOWN_MODEL_TYPE_MISMATCH`
- **AND** canonical `device_kind` remains the exact authoritative source-type result
- **AND** canonical `diagnostic_model` remains `Aten PE8208AV`
- **AND** the importer does not silently rewrite either field

#### Scenario: Consistency registry has no runtime dispatch authority

- **WHEN** runtime diagnostics consume a valid canonical record
- **THEN** importer expected-kind evidence is not used to select a page, controller, handler, or fallback model
- **AND** runtime dispatch may use only the exact canonical `diagnostic_model` under the diagnostic-application-shell contract

### Requirement: Diagnostic model recognition uses deterministic reviewed components

The importer SHALL evaluate source `Модель` and source `Наименование` as two independent approved model-text evidence fields. For each field separately, it SHALL apply Unicode NFC normalization, leading/trailing trim, and Unicode-aware casefold before recognition. A blank normalized value SHALL provide no components.

Recognition SHALL use exact components rather than arbitrary substrings. Non-alphanumeric characters SHALL act as component boundaries. Letter-to-digit and digit-to-letter transitions inside one alphanumeric chunk SHALL expose exact alphabetic and decimal components so compact forms such as `TE40`, `IN1804`, `PE8208`, and `DMP64` are recognized. An immediately adjacent decimal run plus alphabetic suffix SHALL also expose the exact reviewed mixed component needed for `4i` in `PCS4i`.

Component order and repetition SHALL NOT affect rule satisfaction. Space, hyphen, underscore, dot, slash, and other non-alphanumeric separators SHALL be treated as equivalent boundaries. The importer SHALL NOT use transliteration, typo correction, edit distance, token similarity, manufacturer guessing, field-specific aliases, or undeclared aliases.

The same closed reviewed registry SHALL be evaluated independently against each evidence field and SHALL remain exactly:

| Canonical `diagnostic_model` | Mandatory components in either approved evidence field |
| --- | --- |
| `Huawei TE20` | `te` and `20` |
| `Huawei TE40` | `te` and `40` |
| `Huawei TE50` | `te` and `50` |
| `CloudLink Bar 310` | `cloudlink`, `bar`, and `310` |
| `CloudLink Box 310` | `cloudlink`, `box`, and `310` |
| `Polycom RPG 310` | (`rpg` and `310`) or (`realpresence`, `group`, and `310`) |
| `Extron IN1804` | `in` and `1804` |
| `Aten PE8208AV` | `pe` and `8208` |
| `Extron IPL T PCS4i` | `ipl`, `pcs`, and `4i` |
| `Biamp Tesira Forte CI` | `tesira` and (`forte` or `forté`) |
| `Extron DMP 64 Plus` | `dmp` and `64` |

`AV`, `CI`, and `Plus` SHALL NOT be required components for their canonical rules. Rule order and evidence-field order SHALL NOT grant authority or priority. This requirement SHALL NOT add any canonical model outside this reviewed registry.

After deployment of this reviewed recognition-registry change, the organization workbook SHALL be converted again to regenerate deployment-local `equipment_inventory.local.json`. The workbook and generated snapshot SHALL remain outside Git, runtime SHALL continue to consume only the canonical JSON snapshot, and runtime SHALL NOT parse `.xlsx` data.

#### Scenario: Compact TE40 evidence is recognized

- **WHEN** normalized source `Модель` or normalized source `Наименование` is `TE40`, `TE 40`, or `TE-40`
- **THEN** that field's evidence contains exact components `te` and `40`
- **AND** the `Huawei TE40` rule matches that field

#### Scenario: Compact TE50 evidence is recognized

- **WHEN** normalized source `Модель` or normalized source `Наименование` is `TE50`, `TE 50`, `TE-50`, `Huawei TE50`, or `Huawei_TE.50`
- **THEN** that field's evidence contains exact components `te` and `50`
- **AND** the `Huawei TE50` rule matches that field without a new tokenization rule

#### Scenario: TE50 recognition publishes the exact canonical diagnostic model

- **GIVEN** the combined distinct match union from the two approved evidence fields contains only `Huawei TE50`
- **WHEN** the diagnostic-model cardinality contract is applied
- **THEN** canonical `diagnostic_model` is exactly `Huawei TE50`

#### Scenario: TE20, TE40, and TE50 remain distinct component rules

- **WHEN** approved evidence has exact components `te` and `40`
- **THEN** `Huawei TE40` matches and `Huawei TE50` does not match
- **WHEN** approved evidence has exact components `te` and `50`
- **THEN** `Huawei TE50` matches and `Huawei TE40` does not match
- **AND** existing `Huawei TE20` recognition remains unchanged

#### Scenario: Optional canonical suffix is absent

- **WHEN** either normalized approved evidence field contains exact components `pe` and `8208` without `av`
- **THEN** the `Aten PE8208AV` rule matches that field
- **AND** the importer does not require the optional canonical suffix in source evidence

#### Scenario: Forte accent alternative is recognized

- **WHEN** either normalized approved evidence field contains `tesira` and exact component `forte` or `forté`
- **THEN** the `Biamp Tesira Forte CI` rule matches that field

#### Scenario: Similar longer components are rejected

- **WHEN** either normalized approved evidence field is `LTE 40`, `TE200`, `TE401`, `TE500`, `TE501`, `IN18040`, `PE82080`, or `DMP640`
- **THEN** no reviewed rule matches that field merely because a shorter key appears as a substring

#### Scenario: CloudLink Box 310 evidence is recognized

- **WHEN** either normalized approved evidence field contains exact components `cloudlink`, `box`, and `310`
- **THEN** the `CloudLink Box 310` rule matches that field
- **AND** the `CloudLink Bar 310` rule does not match merely because both products share `cloudlink` and `310`

#### Scenario: Unsupported model remains unmapped

- **WHEN** approved evidence contains `Huawei CloudLink Box 610` and no existing registry rule is satisfied
- **THEN** this requirement adds no new canonical model match
- **AND** separate support for that device requires another reviewed OpenSpec change
