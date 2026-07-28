# equipment-inventory-snapshot Delta

## ADDED Requirements

### Requirement: Schema v2 carries explicit room VIP state

Newly generated canonical equipment inventory snapshots SHALL use `schema_version` exactly `2` and every schema-v2 equipment record SHALL contain exactly one additional field:

```text
room_vip
```

`room_vip` SHALL be a JSON boolean or JSON null. `true` means the source explicitly identifies the authoritative room as VIP, `false` means the source explicitly identifies it as non-VIP, and null means the source value is absent, unsupported, or unresolved.

The deterministic schema-v2 snapshot identity SHALL include `room_vip` for every record. Generation metadata SHALL remain outside snapshot identity.

#### Scenario: VIP room is published

- **WHEN** a source row contains an explicitly supported VIP value
- **THEN** the schema-v2 record contains the corresponding JSON boolean
- **AND** the boolean participates in deterministic snapshot identity

#### Scenario: VIP value is unavailable

- **WHEN** the source VIP value is blank or cannot be represented under the approved mapping
- **THEN** the canonical `room_vip` value is null
- **AND** unsupported non-blank source data produces a structured non-fatal issue

### Requirement: Existing schema-v1 snapshots remain loadable

The runtime inventory loader SHALL continue to accept valid schema-v1 snapshots. A loaded schema-v1 record SHALL expose `room_vip = null` to runtime consumers without rewriting the source file or bypassing schema-v1 snapshot identity verification.

The loader SHALL strictly validate each supported schema version against its own approved exact record fields and identity payload. It SHALL NOT accept an undeclared hybrid record containing schema-v2 fields while claiming schema version 1.

#### Scenario: Existing deployment snapshot is loaded

- **GIVEN** a valid schema-v1 snapshot created before this change
- **WHEN** the runtime loader loads it
- **THEN** the inventory is available
- **AND** every runtime record exposes unknown VIP state

#### Scenario: Hybrid snapshot is rejected

- **WHEN** a snapshot claims schema version 1 but contains `room_vip`
- **THEN** loading fails as an invalid snapshot
- **AND** no partial inventory is published

### Requirement: VIP source mapping is explicit and closed

For the confirmed deployment workbook, the exact source column `VIP оборудование` SHALL map to canonical `room_vip`.

The importer SHALL normalize only these semantic values:

```text
Excel boolean true                  -> true
Excel boolean false                 -> false
"истина"                            -> true
"ложь"                              -> false
blank                               -> null
```

Text comparison SHALL apply Unicode normalization, trim leading and trailing whitespace, and perform case-insensitive exact comparison. The confirmed workbook values are `ИСТИНА`, `ЛОЖЬ`, and blank. No other textual or numeric aliases are approved by this contract.

Any other non-blank value SHALL become null plus a structured `INVALID_ROOM_VIP` non-fatal issue. Substring, fuzzy, approximate, or locale-guessing interpretation is forbidden.

#### Scenario: Confirmed true textual VIP value is normalized

- **WHEN** the source `VIP оборудование` cell contains `ИСТИНА` with arbitrary surrounding whitespace or case
- **THEN** canonical `room_vip` is true

#### Scenario: Confirmed false textual VIP value is normalized

- **WHEN** the source `VIP оборудование` cell contains `ЛОЖЬ` with arbitrary surrounding whitespace or case
- **THEN** canonical `room_vip` is false

#### Scenario: Unsupported VIP value is preserved as unknown

- **WHEN** the source `VIP оборудование` cell contains a non-blank value outside the closed mapping
- **THEN** canonical `room_vip` is null
- **AND** the importer reports `INVALID_ROOM_VIP`
- **AND** the row is not silently dropped solely for this condition

### Requirement: Room VIP evidence uses normative room-wide aggregation

The importer and runtime room-context layer SHALL preserve equipment-record multiplicity and SHALL evaluate VIP evidence across all records sharing one non-null authoritative `room_id`. Null means absence of authoritative VIP evidence for that record. Null SHALL NOT conflict with a consistent known boolean.

The normative aggregation table is:

```text
no room records                         -> unresolved room
all room_vip values null                -> NO_DATA
one or more true, all others null/true  -> VIP_TRUE
one or more false, all others null/false-> VIP_FALSE
at least one true and at least one false-> CONFLICT
```

The importer SHALL report structured non-fatal `ROOM_VIP_CONFLICT` only when both true and false occur under the same authoritative `room_id`. It SHALL NOT report a conflict for `true + null`, `false + null`, repeated equal booleans, or all-null evidence.

Runtime room-context resolution SHALL apply the same table exactly. It SHALL expose `ДА` for `VIP_TRUE`, `НЕТ` for `VIP_FALSE`, `НЕТ ДАННЫХ` for `NO_DATA`, `КОНФЛИКТ ДАННЫХ` for `CONFLICT`, and unresolved room state when no records exist for the authoritative room lookup. It SHALL NOT select the first record or apply device-kind preference.

#### Scenario: All room VIP evidence is absent

- **WHEN** all records sharing one authoritative `room_id` contain `room_vip = null`
- **THEN** runtime VIP presentation is `НЕТ ДАННЫХ`
- **AND** no conflict is reported

#### Scenario: Known VIP evidence is mixed with null

- **WHEN** records sharing one authoritative `room_id` contain one or more true values and all remaining values are true or null
- **THEN** runtime VIP presentation is `ДА`
- **AND** null does not weaken or conflict with the known consistent value

#### Scenario: Known non-VIP evidence is mixed with null

- **WHEN** records sharing one authoritative `room_id` contain one or more false values and all remaining values are false or null
- **THEN** runtime VIP presentation is `НЕТ`
- **AND** null does not weaken or conflict with the known consistent value

#### Scenario: One room contains conflicting VIP flags

- **WHEN** records sharing one authoritative `room_id` contain at least one true and at least one false VIP value
- **THEN** all otherwise valid records remain in the snapshot
- **AND** the importer reports `ROOM_VIP_CONFLICT`
- **AND** runtime presentation is `КОНФЛИКТ ДАННЫХ`
- **AND** runtime does not claim either VIP or non-VIP authority

### Requirement: Converter paths use repository-safe absolute configuration

The offline converter SHALL expose execution-time configuration variables named `SOURCE_XLSX_PATH` and `OUTPUT_JSON_PATH`. Each configured value SHALL be a resolved absolute `Path` before workbook reading or snapshot publication begins.

Path resolution priority SHALL be:

```text
explicit command-line override
environment variable
repository-safe default where approved
configuration failure
```

The supported environment variables SHALL be `DIAG_INVENTORY_XLSX` and `DIAG_INVENTORY_JSON`. The JSON output MAY default to the repository-local deployment snapshot path. No user-specific source workbook path SHALL be committed as a default.

The direct import API SHALL continue to accept explicit source and output paths for tests and automation. A source-path configuration failure SHALL occur before candidate publication and SHALL leave any previous valid output intact.

#### Scenario: Environment paths are resolved

- **GIVEN** relative or user-expanded path text is supplied through the supported environment variables
- **WHEN** converter configuration is initialized
- **THEN** `SOURCE_XLSX_PATH` and `OUTPUT_JSON_PATH` contain absolute resolved `Path` values

#### Scenario: Source path is not configured

- **GIVEN** no CLI source override, no source environment variable, and no approved repository-safe source default
- **WHEN** the converter starts
- **THEN** it exits with a clear safe configuration error
- **AND** it does not modify the existing JSON snapshot
