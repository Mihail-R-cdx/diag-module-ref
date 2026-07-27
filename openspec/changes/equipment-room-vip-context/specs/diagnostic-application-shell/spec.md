# diagnostic-application-shell Delta

## ADDED Requirements

### Requirement: Equipment pages expose current room context

The diagnostic application composition layer SHALL resolve room context for the currently selected equipment from the already loaded immutable equipment inventory. Resolution SHALL use the exact current equipment IP, require exactly one total IP match, and use non-null `room_id` as the only room identity authority.

The shared room context SHALL expose safe presentation state for:

```text
room address from consistent room_name evidence
room VIP state from consistent room_vip evidence
structured missing, ambiguous, and conflict outcomes
inventory snapshot identity
current equipment model/IP context
```

The resolver SHALL NOT perform network I/O, query a device handler, use `room_name` as fallback identity, select the first record from an ambiguous result, or change device diagnostic success/failure authority.

#### Scenario: Equipment room context resolves

- **GIVEN** the current equipment IP has exactly one inventory record with authoritative room identity
- **AND** the room has consistent address and VIP evidence
- **WHEN** room context is resolved
- **THEN** the application exposes the room address and VIP state for presentation
- **AND** no device network request is performed

#### Scenario: Equipment IP is ambiguous

- **WHEN** more than one inventory record matches the current equipment IP
- **THEN** room context is ambiguous
- **AND** no matching record is selected by order or device kind
- **AND** device diagnostics remain independently usable

### Requirement: Non-PDU equipment pages render a shared room-information block

Every supported non-PDU equipment page SHALL render one shared room-information block at the bottom of the page. The block SHALL show:

```text
Адрес: <resolved room_name or safe unavailable text>
VIP: ДА | НЕТ | НЕТ ДАННЫХ | КОНФЛИКТ ДАННЫХ
```

The block SHALL use a shared presentation model or reusable widget so normalization and safe fallback behavior are not independently reimplemented by each equipment screen.

The room-information block SHALL remain informational. Missing inventory, unresolved room identity, duplicate IP, address conflict, or VIP conflict SHALL be shown inline and SHALL NOT open an automatic modal connection error, disable valid equipment controls, or convert a successful device diagnostic result into failure.

#### Scenario: Non-PDU page displays VIP room

- **GIVEN** the selected equipment resolves to a VIP room
- **WHEN** its page is displayed or refreshed
- **THEN** the bottom room-information block shows the resolved address
- **AND** it shows `VIP: ДА`

#### Scenario: Inventory is unavailable

- **GIVEN** device diagnostics can run but inventory loading failed
- **WHEN** a non-PDU equipment page is displayed
- **THEN** the room-information block shows safe unavailable state
- **AND** device diagnostics and controls retain their existing authority

### Requirement: Room presentation is bound to current equipment context

Room presentation SHALL be invalidated immediately when the selected model, IP address, credential context, page context, or accepted inventory snapshot is superseded.

A room result SHALL be rendered only when its bound equipment model/IP context and inventory snapshot still match the current application context. Stale queued or in-flight device results SHALL NOT restore prior room address or VIP state.

#### Scenario: Selected IP changes during an operation

- **GIVEN** room information for one equipment IP is visible
- **WHEN** the operator changes the selected IP before an old operation completes
- **THEN** the old room information is cleared immediately
- **AND** completion of the old operation cannot restore it
- **AND** only room context matching the new selected IP may be rendered
