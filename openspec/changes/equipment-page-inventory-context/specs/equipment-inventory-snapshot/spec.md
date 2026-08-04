# equipment-inventory-snapshot Delta

## MODIFIED Requirements

### Requirement: Schema-v3 switch fields are passive runtime data in this change

The runtime `EquipmentRecord` SHALL expose nullable `switch_ip_address` and `switch_port` for schema-v3 records and null-adapted values for older records.

Existing inventory indexes SHALL remain equivalent to:

```text
ip_address -> tuple[EquipmentRecord, ...]
room_id -> tuple[EquipmentRecord, ...]
(room_id, device_kind) -> tuple[EquipmentRecord, ...]
```

This capability SHALL NOT add an index or public query by switch IP or switch port.

The application/composition layer MAY read `switch_ip_address` and `switch_port` from the one unambiguous record returned through the existing current-device IP lookup solely to create non-blocking equipment-page presentation. It SHALL pass only safe scalar presentation values to registered equipment screens. Screens SHALL NOT receive or query the complete inventory, interpret lookup multiplicity, reconcile source evidence, or use switch fields as device-observation data.

Diagnostic model dispatch, credential configuration or fallback, handler acquisition, request retry, successful credential memory, room-context aggregation, PDU-room-codec enrichment, related-codec selection, device controllers, workers, handlers, parsers, transports, protocol behavior, device control, and device or switch network I/O SHALL ignore both switch fields. Switch values SHALL NOT change lookup membership or ordering, select between ambiguous records, authorize a diagnostic lifecycle, classify a device request, or become a precondition for existing diagnostics.

A unique record's two switch fields SHALL remain independent for presentation. A non-null canonical field MAY be displayed while the other field is null. Null fields, null-adapted schema-v1/schema-v2 fields, unavailable inventory, invalid current device IP, zero matching records, or multiple matching records SHALL produce unavailable display values without changing the validity or availability of existing device diagnostics.

The importer MAY extend its structured result with safe network worksheet/header context and aggregate counts needed to validate two-source conversion. Those report fields SHALL NOT enter canonical records, canonical `source_row_count`, or `snapshot_id`.

#### Scenario: Existing IP and room queries are unchanged

- **WHEN** a schema-v3 inventory is loaded
- **THEN** `find_by_ip`, `find_room_equipment`, and `find_by_room_and_kind` preserve their existing zero/one/many semantics
- **AND** switch fields do not alter membership or ordering
- **AND** no switch-IP or switch-port query is added

#### Scenario: Unique current record supplies display-only values

- **GIVEN** existing device-IP lookup returns exactly one schema-v3 record
- **WHEN** the application prepares equipment-page inventory presentation
- **THEN** it may read that record's `switch_ip_address` and `switch_port`
- **AND** it passes only safe scalar display values to the registered screen
- **AND** neither field becomes device-response or network-I/O authority

#### Scenario: Unique partial switch connection remains useful

- **GIVEN** existing device-IP lookup returns exactly one record
- **AND** exactly one switch field is non-null
- **WHEN** the application prepares equipment-page presentation
- **THEN** it preserves the non-null canonical field for display
- **AND** the null field remains unavailable
- **AND** it does not infer, reconstruct, or query the missing value

#### Scenario: Ambiguous current device is not narrowed for display

- **GIVEN** existing device-IP lookup returns multiple records
- **WHEN** one record has a matching diagnostic model, preferred device kind, or more complete switch values
- **THEN** the application displays neither record's switch connection
- **AND** it does not break ambiguity by model, kind, MAC, room, completeness, or order

#### Scenario: Older snapshots remain compatible

- **GIVEN** a valid schema-v1 or schema-v2 snapshot is loaded
- **WHEN** equipment-page switch presentation is requested
- **THEN** the loader-provided null switch fields produce unavailable display values
- **AND** the source snapshot is not rewritten or upgraded
- **AND** existing diagnostics remain available

#### Scenario: Diagnostics run with schema v3

- **GIVEN** the application loads a valid schema-v3 snapshot
- **WHEN** existing diagnostic dispatch, credential, request, room, PDU enrichment, handler, worker, controller, transport, or control workflows execute
- **THEN** their authority and lifecycle remain unchanged
- **AND** they do not inspect switch IP or port
- **AND** informational equipment-page rendering does not become a success or failure gate

#### Scenario: Device payload cannot redefine canonical switch presentation

- **GIVEN** a device handler, parser, worker, or controller produces an IP, port, interface, MAC, or connection value
- **WHEN** the result is rendered
- **THEN** that value does not replace or supplement canonical `switch_ip_address` or `switch_port`
- **AND** no switch field is added to the device-result contract by this capability

#### Scenario: No switch management is introduced

- **WHEN** switch IP or port is available for display
- **THEN** the application performs no switch reachability check, authentication, link-state query, configuration, or other switch network I/O
- **AND** it does not request or resolve switch credentials

#### Scenario: Report metadata is not canonical identity

- **WHEN** safe network-run counters or source-location context differ while canonical schema-v3 records remain identical
- **THEN** deterministic `snapshot_id` remains identical
