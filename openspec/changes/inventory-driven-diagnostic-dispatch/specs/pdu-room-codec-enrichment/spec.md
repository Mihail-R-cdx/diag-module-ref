# pdu-room-codec-enrichment Specification

## MODIFIED Requirements

### Requirement: Pure authoritative PDU and room resolution

The enrichment capability SHALL resolve the accepted PDU IP through the current immutable `EquipmentInventory` revision using indexed zero/one/many semantics. It SHALL use exact canonical fields and the exact model carried by the accepted current `PDUController` context. It SHALL NOT use fuzzy matching, source-model guessing, room-name fallback, `device_kind` as PDU identity, page key, record order, or first-match selection.

The resolver SHALL require exactly one total record from `find_by_ip(accepted_pdu_ip)`. It SHALL NOT reduce duplicate-IP ambiguity by filtering records by `device_kind`, diagnostic support, or page classification.

The accepted PDU context model SHALL be exactly one of this closed set:

```text
Aten PE8208AV
Extron IPL T PCS4i
```

For the one inventory record, canonical `diagnostic_model` SHALL be non-null, SHALL be in the same closed PDU set, and SHALL exactly equal the accepted PDU context model. The resolver SHALL NOT require `device_kind == "pdu"`; a correct Aten or PCS4i record with `device_kind = other` remains eligible. After exact model agreement, the record SHALL have a non-null authoritative `room_id`.

Resolution SHALL distinguish:

```text
INVENTORY_UNAVAILABLE
PDU_NOT_FOUND
AMBIGUOUS_PDU_IP
PDU_MODEL_UNSUPPORTED
PDU_MODEL_MISMATCH
ROOM_UNRESOLVED
```

`PDU_MODEL_UNSUPPORTED` SHALL mean that the model in the accepted `PDUController` context is absent from the closed PDU set. `PDU_MODEL_MISMATCH` SHALL mean that exactly one IP record exists but its canonical `diagnostic_model` is null, outside the closed PDU set, or not exactly equal to the accepted context model.

Both model failures SHALL stop before room-codec credential resolution, handler/session construction, worker submission, or network I/O. The pure resolver SHALL perform no Qt access, credential work, handler/session construction, worker submission, or network I/O.

#### Scenario: PDU IP is absent

- **WHEN** the inventory returns zero records for the accepted PDU IP
- **THEN** resolution is `PDU_NOT_FOUND`
- **AND** no codec credential or network work starts

#### Scenario: PDU IP has duplicate assignments

- **WHEN** the inventory returns more than one total record for the accepted PDU IP
- **THEN** resolution is `AMBIGUOUS_PDU_IP`
- **AND** no record is filtered, preferred, deduplicated, or selected by kind or model

#### Scenario: One PDU and one non-PDU share the IP

- **WHEN** IP lookup returns one record whose model matches the accepted PDU context and one additional record
- **THEN** resolution remains `AMBIGUOUS_PDU_IP`
- **AND** the matching record is not selected merely because its model or page is familiar

#### Scenario: Accepted PDU model is unsupported

- **GIVEN** the accepted current PDU context carries a model outside `Aten PE8208AV` and `Extron IPL T PCS4i`
- **WHEN** enrichment resolution begins
- **THEN** resolution is `PDU_MODEL_UNSUPPORTED`
- **AND** no inventory record is treated as a PDU by `device_kind`, page key, or source text
- **AND** no related-codec credential or network work starts

#### Scenario: Exact Aten context matches an Aten inventory record of kind other

- **GIVEN** the accepted current PDU context model is exactly `Aten PE8208AV`
- **AND** exactly one inventory record matches the accepted PDU IP
- **AND** that record has `diagnostic_model = Aten PE8208AV`
- **AND** that record has `device_kind = other`
- **WHEN** enrichment resolves PDU identity
- **THEN** exact PDU model validation succeeds
- **AND** `device_kind = other` does not block room resolution

#### Scenario: Exact PCS4i context matches a PCS4i inventory record of kind other

- **GIVEN** the accepted current PDU context model is exactly `Extron IPL T PCS4i`
- **AND** exactly one inventory record matches the accepted PDU IP
- **AND** that record has `diagnostic_model = Extron IPL T PCS4i`
- **AND** that record has `device_kind = other`
- **WHEN** enrichment resolves PDU identity
- **THEN** exact PDU model validation succeeds
- **AND** room resolution may continue

#### Scenario: Inventory model differs from accepted PDU model

- **GIVEN** exactly one inventory record matches the accepted PDU IP
- **AND** the accepted context model and inventory `diagnostic_model` are different exact values
- **WHEN** enrichment resolves PDU identity
- **THEN** resolution is `PDU_MODEL_MISMATCH`
- **AND** no room-codec credential or network work starts

#### Scenario: Inventory PDU model is null or unsupported

- **GIVEN** exactly one inventory record matches the accepted PDU IP
- **AND** its canonical `diagnostic_model` is null or outside the closed PDU set
- **WHEN** enrichment resolves PDU identity
- **THEN** resolution is `PDU_MODEL_MISMATCH`
- **AND** the resolver does not guess from `device_kind`, `source_model`, or page classification
- **AND** no room-codec credential or network work starts

#### Scenario: Exact IP record is not a PDU

- **GIVEN** accepted model and the one inventory record's exact `diagnostic_model` agree in the closed PDU set
- **WHEN** the inventory record has any canonical `device_kind`, including `other` or `pdu`
- **THEN** PDU identity remains established by exact model agreement
- **AND** the resolver does not emit a kind-mismatch outcome

#### Scenario: PDU has no authoritative room ID

- **GIVEN** the accepted PDU model and one inventory record match exactly
- **WHEN** that record has `room_id = null`
- **THEN** resolution is `ROOM_UNRESOLVED`
- **AND** `room_name` is not substituted as identity

#### Scenario: Inventory is unavailable

- **WHEN** composition has no validated inventory revision
- **THEN** resolution is `INVENTORY_UNAVAILABLE`
- **AND** only the existing safe load category/message is exposed
- **AND** accepted PDU diagnostics continue to function independently