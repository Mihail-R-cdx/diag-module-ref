## ADDED Requirements

### Requirement: Approved Matrix inventory canonicalization

The offline equipment inventory converter SHALL recognize normalized model and
name evidence for `Extron IN1804`, `Extron IN1806`, `Extron IN1808`, `Extron IN1608 xi`, `Extron
DTP CrossPoint 84`, `Extron DTP CrossPoint 82 4K`, `Extron DTP CrossPoint 84
4K`, `Extron DTP CrossPoint 86 4K`, `Extron DTP CrossPoint 108 4K`, `Extron
XTP CrossPoint 1600`, `Extron XTP CrossPoint 3200`, `Extron XTP II CrossPoint
1600`, `Extron XTP II CrossPoint 3200`, and `Extron XTP II CrossPoint 6400`.
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
SHALL forbid the `4k` component; first-generation `XTP CrossPoint 1600` and
`XTP CrossPoint 3200` SHALL forbid `ii`; XTP II models SHALL require `ii`; and
`Extron IN1608 xi` SHALL require `xi`. Unrecognized, conflicting, or
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

#### Scenario: XTP generations remain distinct

- **WHEN** evidence contains an approved first-generation `XTP CrossPoint 1600` or `XTP CrossPoint 3200`
- **THEN** it does not also resolve to the corresponding XTP II model
- **WHEN** evidence contains the corresponding approved XTP II model
- **THEN** it does not also resolve to the first-generation model

#### Scenario: Cross-field Matrix disagreement fails closed

- **WHEN** model evidence identifies `Extron IN1808` and name evidence identifies `Extron IN1608 xi`
- **THEN** `diagnostic_model` remains unset
- **AND** the converter reports the existing ambiguous-diagnostic-model outcome
