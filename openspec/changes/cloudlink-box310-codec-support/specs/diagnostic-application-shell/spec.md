# diagnostic-application-shell Specification

## MODIFIED Requirements

### Requirement: Inventory-driven diagnostic dispatch uses exact canonical diagnostic_model

The application/composition layer SHALL own inventory-driven diagnostic dispatch. For a valid normalized IP and current immutable `EquipmentInventory`, it SHALL call `find_by_ip(...)`, classify the complete returned tuple as zero, one, or many, and inspect canonical fields only when exactly one total record exists.

For one record, automatic dispatch SHALL use only its exact non-null canonical `diagnostic_model`. The application SHALL NOT derive, repair, or choose a model from `device_kind`, `source_model`, manufacturer/model evidence, substring or fuzzy matching, aliases, handler availability, source row order, registry order, prior user selection, prior request context, or protocol failure.

The closed dispatch registry SHALL be exactly:

| Exact canonical `diagnostic_model` | Screen key | Existing diagnostic lifecycle |
| --- | --- | --- |
| `Huawei TE20` | `codec` | Huawei TE20 refresh path |
| `Huawei TE40` | `codec` | Huawei TE40 refresh path |
| `CloudLink Bar 310` | `codec` | shared CloudLink Bar/Box 310 lifecycle `cloudlink_bar_310` |
| `CloudLink Box 310` | `codec` | shared CloudLink Bar/Box 310 lifecycle `cloudlink_bar_310` |
| `Polycom RPG 310` | `codec` | Polycom RPG 310 refresh path |
| `Extron IN1804` | `matrix` | `MatrixController` refresh path |
| `Aten PE8208AV` | `pdu` | `PDUController` with exact Aten model context |
| `Extron IPL T PCS4i` | `pdu` | `PDUController` with exact PCS4i model context |
| `Biamp Tesira Forte CI` | `audio_dsp` | existing Biamp polling path |
| `Extron DMP 64 Plus` | `audio_dsp` | `DMPPollingController` refresh path |

Each exact model SHALL have one and only one registry entry. Multiple exact models MAY share one explicitly reviewed lifecycle route while retaining distinct application model identity. Unknown models SHALL have no default route. Diagnostic fallback choices, credential-configuration fallback choices, page registration, and lifecycle routing SHALL derive from or be integrity-checked against this same closed registry.

The registry SHALL contain no credentials, credential candidate lists, successful indexes, handler/session/transport instances, cookies/tokens, or mutable worker state.

#### Scenario: Unique Aten record selects PDU diagnostics

- **GIVEN** exactly one inventory record matches the current IP
- **AND** its `diagnostic_model` is exactly `Aten PE8208AV`
- **AND** its `device_kind` is `other`
- **WHEN** diagnostic inventory dispatch is accepted
- **THEN** the application assigns the `pdu` screen and exact Aten `PDUController` path
- **AND** `device_kind = other` does not block or alter dispatch

#### Scenario: Unique PCS4i record selects PDU diagnostics

- **GIVEN** exactly one inventory record matches the current IP
- **AND** its `diagnostic_model` is exactly `Extron IPL T PCS4i`
- **AND** its `device_kind` is `other`
- **WHEN** diagnostic inventory dispatch is accepted
- **THEN** the application assigns the `pdu` screen and exact PCS4i `PDUController` path

#### Scenario: Unique TE40 record selects codec diagnostics

- **GIVEN** exactly one inventory record matches the current IP
- **AND** its `diagnostic_model` is exactly `Huawei TE40`
- **WHEN** diagnostic inventory dispatch is accepted
- **THEN** the application assigns the `codec` screen and Huawei TE40 refresh path

#### Scenario: Unique CloudLink Box 310 record selects shared Bar/Box diagnostics

- **GIVEN** exactly one inventory record matches the current IP
- **AND** its `diagnostic_model` is exactly `CloudLink Box 310`
- **WHEN** diagnostic inventory dispatch is accepted
- **THEN** the application assigns the `codec` screen and lifecycle route `cloudlink_bar_310`
- **AND** the accepted application model remains exactly `CloudLink Box 310`
- **AND** the application does not rewrite the request model to `CloudLink Bar 310`

#### Scenario: Unique IN1804 record selects Matrix diagnostics

- **GIVEN** exactly one inventory record matches the current IP
- **AND** its `diagnostic_model` is exactly `Extron IN1804`
- **WHEN** diagnostic inventory dispatch is accepted
- **THEN** the application assigns the `matrix` screen and `MatrixController` refresh path

#### Scenario: Device kind alone grants no route or credential model

- **GIVEN** one inventory record has any canonical `device_kind`
- **AND** its `diagnostic_model` is null or unsupported
- **WHEN** application model resolution evaluates the record
- **THEN** no automatic page, lifecycle, or credential-model context is selected
- **AND** the application does not infer a model from kind or source text

#### Scenario: Unknown exact model has no default route

- **GIVEN** one inventory record has a non-null canonical `diagnostic_model` absent from the closed registry
- **WHEN** application model resolution evaluates the record
- **THEN** the outcome is unsupported
- **AND** the application does not default to codec, a same-kind page, the nearest handler, or a prior model
