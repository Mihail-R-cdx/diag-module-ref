## ADDED Requirements

### Requirement: Approved Matrix inventory canonicalization

The offline equipment inventory converter SHALL recognize normalized model and
name evidence for `Extron IN1804`, `Extron IN1806`, `Extron IN1808`, `Extron IN1608 xi`, `Extron
DTP CrossPoint 84`, `Extron DTP CrossPoint 82 4K`, `Extron DTP CrossPoint 84
4K`, `Extron DTP CrossPoint 86 4K`, and `Extron DTP CrossPoint 108 4K`.
XTP CrossPoint and XTP II CrossPoint recognition introduced by earlier work in
this branch SHALL be retired from production dispatch because those models are
explicitly deferred from the current change scope.
It SHALL emit the exact canonical runtime dispatch model in
`diagnostic_model`, retain the original source-model text, and use `other` as
the expected-kind consistency value for these Matrix models.

The converter SHALL normalize evidence, extract components, evaluate the full
canonical match set in each model/name field, and reconcile the distinct union
across fields. Manufacturer text SHALL NOT add, remove, veto, or resolve a
model match. Match-rule ordering SHALL NOT select among multiple canonical
matches.

Rules MAY declare required and forbidden components when a positive subset is
not sufficient to represent approved exact distinctions. `DTP CrossPoint 84`
SHALL forbid the `4k` component and `Extron IN1608 xi` SHALL require `xi`.
Deferred XTP/XTP II evidence SHALL NOT resolve to a supported production
`diagnostic_model` under this change. Unrecognized, conflicting, or
multi-match evidence SHALL remain unresolved under the existing fail-closed
inventory behavior.

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
- **THEN** this change does not emit an XTP/XTP II supported production `diagnostic_model`
- **AND** runtime cannot dispatch it as a supported Matrix profile

#### Scenario: Cross-field Matrix disagreement fails closed

- **WHEN** model evidence identifies `Extron IN1808` and name evidence identifies `Extron IN1608 xi`
- **THEN** `diagnostic_model` remains unset
- **AND** the converter reports the existing ambiguous-diagnostic-model outcome


### Requirement: Complete Matrix diagnostics require canonical inventory MAC and serial

For every Matrix model remaining supported by this change, canonical `mac_address` and `serial_number` are mandatory prerequisites for complete-success Matrix diagnostics. Existing schema-v4 nullability remains unchanged repository-wide: a null Matrix MAC or serial is valid inventory data, but it cannot satisfy the Matrix complete-refresh gate.

#### Scenario: Supported Matrix row lacks serial
- **GIVEN** a supported Matrix canonical record has `serial_number = null`
- **WHEN** room Matrix diagnostics run
- **THEN** inventory loading remains valid
- **AND** Matrix full refresh cannot be classified complete-success
- **AND** no serial is guessed from model, credentials, IP, MAC or device banner