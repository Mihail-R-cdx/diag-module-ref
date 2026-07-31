# equipment-inventory-snapshot Specification

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
any other value   -> other
```

The importer SHALL NOT use substring matching, fuzzy matching, model-name guessing, manufacturer guessing, recognized diagnostic-model evidence, GUI page registration, or runtime diagnostic routing to silently override the result of this exact source-type mapping.

A known supported model whose source `Тип модели` maps to an unexpected `device_kind` MAY produce the structured non-fatal consistency issue `KNOWN_MODEL_TYPE_MISMATCH`. The expected-kind registry used by that diagnostic is importer-only consistency evidence. It SHALL NOT grant authority to change `device_kind`, suppress an exact recognized `diagnostic_model`, choose a runtime page/controller, or alter canonical schema.

For the currently reviewed PDU diagnostic models, the consistency expectations SHALL be:

```text
Aten PE8208AV          -> other
Extron IPL T PCS4i     -> other
```

These expected values reflect the authoritative source-type contract for the reviewed organization rows. Runtime PDU dispatch is independently authorized by exact canonical `diagnostic_model`; it SHALL NOT require `device_kind = pdu`.

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