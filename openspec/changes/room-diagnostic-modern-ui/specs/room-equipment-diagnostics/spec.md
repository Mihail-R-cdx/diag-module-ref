## ADDED Requirements

### Requirement: Explicit room-name selection establishes room authority without a source record

When valid current inventory room-name search yields or confirms one explicitly selected exact canonical `room_id`, the application SHALL establish room diagnostic mode directly from that room ID. Direct room-name entry SHALL NOT manufacture, infer, or promote a source equipment record.

The selected room authority SHALL be bound to the current validated inventory snapshot and current target-query revision. Before per-row credentials, reachability, handler acquisition, worker/controller submission, or device network I/O, the application SHALL verify that the selected room ID still exists in current valid inventory and remains an allowed result for the unchanged current room-name query/selection context.

A stale room selection SHALL fail closed and SHALL NOT fall back to the first room, first record, matching model, device kind, source text, or previous room generation.

#### Scenario: Direct room selection starts without source device

- **GIVEN** valid inventory search returns several room IDs for a partial name
- **AND** the operator explicitly selects exact room ID `room-305`
- **WHEN** Enter/top Refresh starts diagnostics
- **THEN** `room-305` becomes authoritative room identity
- **AND** no room record is marked as a synthetic source record

#### Scenario: Selected room becomes stale

- **GIVEN** a room was selected under inventory snapshot A
- **WHEN** current inventory snapshot B no longer contains that selected room as a valid result for the unchanged query context
- **THEN** diagnostics does not start from the stale selection
- **AND** no fallback room or record is chosen

## MODIFIED Requirements

### Requirement: Room tree preserves complete deterministic membership

A room diagnostic session SHALL include every canonical inventory record whose authoritative `room_id` equals the resolved/selected room ID. Tree construction SHALL NOT filter records by `diagnostic_model`, `device_kind`, IP availability, screen type, or diagnostic eligibility.

When room mode was entered from a unique IP source record, that exact source record SHALL appear first exactly once and every remaining room record SHALL follow in ascending canonical `record_id` order.

When room mode was entered by explicit room-name selection, there is no source record. Every room record SHALL appear in ascending canonical `record_id` order and the application SHALL NOT promote the first record, first supported model, codec, PDU, or first IP-bearing record into synthetic source authority.

Same-room IP ambiguity SHALL be computed across all room records with non-null IP, including unsupported records. A supported record whose IP is shared by any other record in the same room SHALL be diagnostically ambiguous and SHALL receive no device I/O. After room authority is established, an equal IP on a record in another room SHALL NOT by itself make a room row ambiguous.

#### Scenario: Room contains supported and unsupported equipment

- **GIVEN** one authoritative room contains supported, unsupported, missing-IP, and ordinary records
- **WHEN** the tree is built
- **THEN** every room record is present exactly once
- **AND** supportability changes diagnostic eligibility but not tree membership

#### Scenario: IP source row is ordered first

- **GIVEN** room mode was entered through a unique IP record that is not first by canonical `record_id`
- **WHEN** the room tree is built
- **THEN** that exact source record is first
- **AND** all other rows follow in canonical `record_id` order

#### Scenario: Direct room selection has canonical ordering only

- **GIVEN** room mode was entered through explicit room-name selection
- **WHEN** the tree is built
- **THEN** every room record is ordered by ascending canonical `record_id`
- **AND** no record is promoted to synthetic source authority

#### Scenario: Unsupported record makes a supported IP ambiguous

- **GIVEN** a supported room record and an unsupported room record share the same non-null IP
- **WHEN** row eligibility is calculated
- **THEN** the supported row is classified as same-room ambiguous
- **AND** it is not diagnosed
- **AND** the unsupported row remains classified as unsupported

### Requirement: Shared room metadata is source-first display evidence

Room mode SHALL present shared room display metadata once above the equipment tree. Authoritative room display evidence provided by current canonical inventory SHALL include room name, room address, and VIP state and SHALL NOT display `room_id` to the operator as room identity.

For IP-entry room mode, each display field independently SHALL use the source-record value when it is nonblank/non-null and otherwise select the first nonblank/non-null value from room records in canonical `record_id` order.

For explicit room-name entry, no source record exists. Each display field independently SHALL use the first nonblank/non-null value from room records in canonical `record_id` order.

If no usable canonical value exists, the presentation SHALL use a safe no-data value. The room session SHALL NOT compare same-room `room_name`, `room_address`, or `room_vip` values to select a majority, emit a conflict merely for differing display metadata, or replace authoritative `room_id` identity. Boolean `false` SHALL be treated as a meaningful non-null VIP value.

Warranty and occupancy are not canonical schema-v4 room fields and therefore are not room identity/display authority under this requirement. A GUI MAY reserve those labels, but it SHALL NOT derive non-authoritative values for them under this change.

#### Scenario: IP source record carries the room address

- **GIVEN** IP-entry room mode has a source record with nonblank `room_address`
- **AND** another room record has a different nonblank address
- **WHEN** the shared header is rendered
- **THEN** the source-record address is displayed
- **AND** no address conflict is raised

#### Scenario: IP source metadata is missing

- **GIVEN** IP-entry source record has null room name, address, and VIP
- **WHEN** canonical room records contain later usable values
- **THEN** each field independently uses the first usable canonical value
- **AND** `room_id` remains the only room identity authority

#### Scenario: Direct room selection uses canonical-first metadata

- **GIVEN** room mode was entered by room-name selection and has no source record
- **WHEN** canonical room records contain usable room name/address/VIP values
- **THEN** each display field independently uses the first usable value in canonical record order
- **AND** no record becomes synthetic source authority
