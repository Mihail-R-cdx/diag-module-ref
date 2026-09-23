## MODIFIED Requirements

### Requirement: Diagnostic model recognition uses deterministic reviewed components

The importer SHALL evaluate source `Модель` and source `Наименование` as two independent approved model-text evidence fields. For each field separately, it SHALL apply Unicode NFC normalization, leading/trailing trim, and Unicode-aware casefold before recognition. A blank normalized value SHALL provide no components.

Recognition SHALL use exact components rather than arbitrary substrings. Non-alphanumeric characters SHALL act as component boundaries. Letter-to-digit and digit-to-letter transitions inside one alphanumeric chunk SHALL expose exact alphabetic and decimal components so compact forms such as `TE40`, `IN1804`, `PE8208`, and `DMP64` are recognized. An immediately adjacent decimal run plus alphabetic suffix SHALL also expose the exact reviewed mixed component needed for reviewed forms such as `4i` in `PCS4i` and casefolded `4k` in DTP CrossPoint `4K` evidence.

Component order and repetition SHALL NOT affect rule satisfaction. Space, hyphen, underscore, dot, slash, and other non-alphanumeric separators SHALL be treated as equivalent boundaries. The importer SHALL NOT use transliteration, typo correction, edit distance, token similarity, manufacturer guessing, field-specific aliases, or undeclared aliases.

The same closed reviewed registry SHALL be evaluated independently against each evidence field and SHALL remain exactly:

| Canonical `diagnostic_model` | Mandatory components in either approved evidence field | Forbidden components |
| --- | --- | --- |
| `Huawei TE20` | `te` and `20` | — |
| `Huawei TE40` | `te` and `40` | — |
| `Huawei TE50` | `te` and `50` | — |
| `CloudLink Bar 310` | `cloudlink`, `bar`, and `310` | — |
| `CloudLink Box 310` | `cloudlink`, `box`, and `310` | — |
| `Polycom RPG 310` | (`rpg` and `310`) or (`realpresence`, `group`, and `310`) | — |
| `Extron IN1804` | `in` and `1804` | — |
| `Extron IN1806` | `in` and `1806` | — |
| `Extron IN1808` | `in` and `1808` | — |
| `Extron IN1608 xi` | `in`, `1608`, and `xi` | — |
| `Extron DTP CrossPoint 84` | `dtp`, `crosspoint`, and `84` | `4k` |
| `Extron DTP CrossPoint 82 4K` | `dtp`, `crosspoint`, `82`, and `4k` | — |
| `Extron DTP CrossPoint 84 4K` | `dtp`, `crosspoint`, `84`, and `4k` | — |
| `Extron DTP CrossPoint 86 4K` | `dtp`, `crosspoint`, `86`, and `4k` | — |
| `Extron DTP CrossPoint 108 4K` | `dtp`, `crosspoint`, `108`, and `4k` | — |
| `Aten PE8208AV` | `pe` and `8208` | — |
| `Extron IPL T PCS4i` | `ipl`, `pcs`, and `4i` | — |
| `Biamp Tesira Forte CI` | `tesira` and (`forte` or `forté`) | — |
| `Extron DMP 64 Plus` | `dmp` and `64` | — |

`AV`, `CI`, and `Plus` SHALL NOT be required components for their canonical rules. A rule with forbidden components SHALL match only when every mandatory component is present and every forbidden component is absent. `Extron DTP CrossPoint 84` therefore SHALL NOT match evidence containing the reviewed `4k` component, while `Extron IN1608 xi` SHALL require exact `xi` evidence. Rule order and evidence-field order SHALL NOT grant authority or priority. This requirement SHALL NOT add any canonical model outside this reviewed registry. XTP CrossPoint and XTP II CrossPoint models are explicitly absent from this production registry and SHALL remain unresolved by this requirement.

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

#### Scenario: IN1806 remains a distinct canonical inventory model

- **WHEN** normalized model or name evidence identifies `Extron IN1806`, `IN1806`, or spacing-equivalent `IN 1806`
- **THEN** `diagnostic_model` is exactly `Extron IN1806`
- **AND** it does not resolve to `Extron IN1808`

#### Scenario: Long-form IN1808 source name

- **WHEN** model or name evidence contains `Extron IN1808 IPCP SA`, `IN1808 IPCP SA`, or `Extron IN 1808 IPCP SA`
- **THEN** `diagnostic_model` is exactly `Extron IN1808`
- **AND** source-model evidence is not rewritten

#### Scenario: DTP 84 remains distinct from DTP 84 4K

- **WHEN** evidence contains `DTP CrossPoint 84`
- **THEN** it resolves only to `Extron DTP CrossPoint 84`
- **WHEN** evidence contains `DTP CrossPoint 84 4K`
- **THEN** it resolves only to `Extron DTP CrossPoint 84 4K`

#### Scenario: Deferred XTP evidence is not production-supported

- **WHEN** model/name evidence identifies first-generation XTP CrossPoint or XTP II CrossPoint
- **THEN** this requirement emits no XTP/XTP II supported production `diagnostic_model`
- **AND** separate production support requires another reviewed OpenSpec change

#### Scenario: Cross-field Matrix disagreement fails closed

- **WHEN** model evidence identifies `Extron IN1808` and name evidence identifies `Extron IN1608 xi`
- **THEN** the combined match union remains ambiguous under the existing diagnostic-model cardinality contract
- **AND** `diagnostic_model` remains unset

## ADDED Requirements

### Requirement: Complete Matrix diagnostics require canonical inventory MAC and serial

For every Matrix model remaining supported by this change, canonical `mac_address` and `serial_number` are mandatory prerequisites for complete-success Matrix diagnostics. Existing schema-v4 nullability remains unchanged repository-wide: a null Matrix MAC or serial is valid inventory data, but it cannot satisfy the Matrix complete-refresh gate.

#### Scenario: Supported Matrix row lacks serial
- **GIVEN** a supported Matrix canonical record has `serial_number = null`
- **WHEN** room Matrix diagnostics run
- **THEN** inventory loading remains valid
- **AND** Matrix full refresh cannot be classified complete-success
- **AND** no serial is guessed from model, credentials, IP, MAC or device banner
