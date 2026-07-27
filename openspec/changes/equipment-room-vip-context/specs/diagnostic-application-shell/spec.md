# diagnostic-application-shell Delta

## ADDED Requirements

### Requirement: Equipment pages expose current room context

The diagnostic application composition layer SHALL resolve room context for the currently selected equipment from the already loaded immutable equipment inventory. Resolution SHALL use the exact current equipment IP, require exactly one total IP match, and use non-null `room_id` as the only room identity authority.

The shared room context SHALL expose safe presentation state for:

```text
room address from consistent room_name evidence
room VIP state from normative room_vip aggregation
structured missing, ambiguous, and conflict outcomes
inventory snapshot identity
current equipment model/IP/page generation
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

Every equipment page registered by the application equipment-page registry SHALL pass through the centralized equipment-page shell or equivalent shared layout boundary. That boundary SHALL render exactly one shared room-information block for every registered non-PDU page and SHALL omit that bottom block only for PDU pages, which retain their dedicated placement contract.

The registry/shell invariant, rather than a manually maintained subset of screen classes, SHALL define the complete supported non-PDU page scope. Tests SHALL enumerate every registered equipment-page entry and prove that each non-PDU registration receives the shared block while each PDU registration uses the dedicated PDU presentation.

The shared non-PDU block SHALL be placed at the bottom of the equipment page and SHALL show:

```text
Адрес: <resolved room_name or safe unavailable text>
VIP: ДА | НЕТ | НЕТ ДАННЫХ | КОНФЛИКТ ДАННЫХ
```

The block SHALL use one shared presentation model or reusable widget so normalization, lifecycle binding, and safe fallback behavior are not independently reimplemented by individual equipment screens or controllers.

The room-information block SHALL remain informational. Missing inventory, unresolved room identity, duplicate IP, address conflict, or VIP conflict SHALL be shown inline and SHALL NOT open an automatic modal connection error, disable valid equipment controls, or convert a successful device diagnostic result into failure.

#### Scenario: Registered non-PDU page displays VIP room

- **GIVEN** a non-PDU equipment page is registered through the application equipment-page registry
- **AND** its current equipment context resolves to a VIP room
- **WHEN** that page context becomes current
- **THEN** the centralized equipment-page shell renders the bottom room-information block
- **AND** the block shows the resolved address
- **AND** it shows `VIP: ДА`

#### Scenario: Registry coverage is complete

- **WHEN** the application enumerates all registered equipment pages
- **THEN** every non-PDU registration is routed through the shared room-information boundary
- **AND** no supported non-PDU page relies on manual opt-in to receive the block
- **AND** PDU registrations are identified explicitly and use the dedicated PDU placement contract

#### Scenario: Inventory is unavailable

- **GIVEN** device diagnostics can run but inventory loading failed
- **WHEN** a non-PDU equipment page becomes current
- **THEN** the room-information block shows safe unavailable state
- **AND** device diagnostics and controls retain their existing authority

### Requirement: Non-PDU room context uses one application-owned publication lifecycle

For non-PDU pages, changing the selected model, normalized IP address, page context, credential context, or accepted inventory snapshot SHALL immediately invalidate the previously published room presentation and create a new application-owned room-context generation.

After invalidation, the application SHALL resolve room context for the new current `(model, normalized_ip, snapshot_id, page_context, generation)` from the immutable inventory without waiting for, depending on, or being triggered by device network success. The pure resolver MAY run synchronously. If coordination or publication is asynchronous, the result SHALL be rendered only after all bound context values and generation still match the current application context.

Device refresh start, progress, success, failure, completion, and stale callbacks SHALL NOT be room-context publication authorities. Device results SHALL NOT independently rerun, republish, clear, or restore room context. A failed device refresh SHALL leave the independently resolved current room presentation available. Starting a device refresh for unchanged current context SHALL NOT create a second room-context authority.

#### Scenario: New IP resolves without device refresh

- **GIVEN** a registered non-PDU equipment page is current
- **WHEN** the operator selects a new model/IP context and does not start device refresh
- **THEN** old room presentation is invalidated immediately
- **AND** room context is resolved and published for the new current context from inventory alone
- **AND** no device handler acquisition or network I/O is required

#### Scenario: Device refresh fails while inventory is available

- **GIVEN** current non-PDU room context has been resolved from inventory
- **WHEN** the device network refresh fails
- **THEN** the current room address and VIP presentation remain available
- **AND** the device failure does not republish, clear, or redefine room context

#### Scenario: Old refresh completes after selected IP changes

- **GIVEN** an old device refresh is queued or in flight for one model/IP context
- **WHEN** the operator selects a different model/IP context
- **THEN** old room presentation is invalidated immediately
- **AND** a new room-context generation is resolved for the new current context
- **AND** completion of the old refresh cannot rerun or restore room context for either the old or new IP

#### Scenario: Asynchronous room result becomes stale

- **GIVEN** room-context publication is coordinated asynchronously
- **WHEN** any bound model, normalized IP, snapshot ID, page context, or generation changes before publication
- **THEN** the old room result is discarded
- **AND** it performs no GUI update
