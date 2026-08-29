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

### Requirement: Source IP establishes authoritative room diagnostic context

Despite this requirement's historical source-IP name, room diagnostic context SHALL now be established only from the current validated application-owned target-search authority. Room-mode start SHALL have exactly two authoritative entry branches: a syntactically valid normalized IPv4 target resolved to one canonical source record, or a current room-name target resolved/selected to one exact canonical `room_id`. Resolution/selection SHALL occur against current validated immutable equipment inventory before room-mode model-specific credential resolution, handler acquisition, worker/controller submission, or device network I/O.

For an IP target with valid inventory, source-IP multiplicity SHALL be preserved exactly. Zero matching records SHALL fail closed as not found. More than one matching record SHALL fail closed as ambiguous. Neither outcome SHALL open manual model fallback or select a record by diagnostic model, device kind, room metadata, page type, or position. Exactly one source record with non-null canonical `room_id` SHALL establish a source-backed room diagnostic session even when that source record has null or unsupported `diagnostic_model`. Exactly one source record with null `room_id` MAY continue through the existing legacy single-device path only when its exact canonical `diagnostic_model` is registered as supported. A unique no-room record with null or unsupported model SHALL fail closed.

For a room-name target, valid current inventory is mandatory. The application SHALL use only the current exact selected/resolved `room_id` bound to the current raw-query revision and current inventory resolution. The room-name branch SHALL establish room mode with no source record and SHALL NOT promote any room equipment record into source authority. If the selected room is stale, absent from current inventory, no longer belongs to the current candidate set, or is otherwise not current for the unchanged target-search context, room start SHALL fail closed before device I/O and SHALL NOT choose another room or record.

Manual diagnostic model fallback SHALL remain available only for the existing valid-IP case where canonical inventory is unavailable, unloadable, or corrupt under the structured inventory-load contract. Valid inventory data SHALL NOT be bypassed by model guessing. Room-name targets SHALL NOT use manual diagnostic or credential fallback.

#### Scenario: Unsupported IP source still establishes its room

- **GIVEN** valid inventory contains exactly one record for the entered IP
- **AND** that record has a non-null authoritative `room_id`
- **AND** its canonical `diagnostic_model` is null or unsupported
- **WHEN** diagnostic start is requested
- **THEN** the application establishes source-backed room mode from that record and `room_id`
- **AND** the source row is represented as unsupported rather than blocking discovery of other room equipment
- **AND** no manual model fallback is opened

#### Scenario: Source IP is absent from valid inventory

- **GIVEN** valid inventory is loaded
- **WHEN** zero records match the entered normalized IP
- **THEN** diagnostic start fails closed with a safe not-found outcome
- **AND** no fallback dialog, credential resolution, handler acquisition, or device network I/O starts

#### Scenario: Source IP is globally ambiguous

- **GIVEN** valid inventory is loaded
- **WHEN** more than one record matches the entered normalized IP
- **THEN** diagnostic start fails closed as ambiguous
- **AND** no record is selected by model, room, kind, or position
- **AND** no manual fallback or device network I/O starts

#### Scenario: Supported source has no room ID

- **GIVEN** exactly one valid-inventory record matches the source IP
- **AND** `room_id` is null
- **AND** its exact canonical `diagnostic_model` is registered as supported
- **WHEN** diagnostic start is requested
- **THEN** the existing legacy single-device diagnostic path remains available
- **AND** no synthetic room identity is created

#### Scenario: Current room-name selection establishes source-less room context

- **GIVEN** valid current inventory and target-search state identify one current exact selected room ID
- **WHEN** diagnostic start is requested from that room-name context
- **THEN** that exact `room_id` establishes room mode
- **AND** no source record is required or manufactured
- **AND** no model fallback is opened

#### Scenario: Stale room-name selection cannot establish room context

- **GIVEN** a previous selected room ID is not current for the present inventory snapshot/query candidate set
- **WHEN** diagnostic start is requested
- **THEN** room context establishment fails closed before device I/O
- **AND** no first room, first record, source record, or prior room generation is substituted

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

Warranty and occupancy are not canonical schema-v4 room fields and therefore are not room identity/display authority under this requirement. Warranty SHALL NOT be derived from non-authoritative values in this change. Occupancy MAY be derived only as presentation state under the typed codec call-activity contract defined by `diagnostic-ui-presentation` and `device-diagnostics-and-control`; such derived occupancy SHALL NOT become canonical room metadata, room identity, inventory state, or booking/calendar authority.

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

#### Scenario: Derived occupancy is not room metadata authority

- **GIVEN** the room presentation receives a typed current codec call-activity projection
- **WHEN** `diagnostic-ui-presentation` derives the visible occupancy row
- **THEN** that value remains presentation-only
- **AND** it does not modify canonical room metadata, inventory identity, or booking state

### Requirement: Automatic room-cycle GUI remains responsive and non-modal

Automatic room diagnostic network work SHALL execute outside the Qt GUI thread. During an active room cycle, target-search editing, Password, and top full Refresh SHALL be unavailable and row-level network/state-changing controls SHALL remain unavailable. Accordion switching SHALL remain responsive and presentation-only.

The GUI SHALL NOT open per-device automatic progress, error, or terminal modal dialogs during the room cycle. Row status/detail and one global room status SHALL present automatic outcomes inline.

At most one row SHALL be expanded at a time. Expanding an eligible waiting row MAY show its model-specific layout with waiting placeholders but SHALL NOT start its I/O early. The cycle SHALL NOT auto-expand rows merely because they succeed or fail. In IP-entry room mode, when the source row is not expandable, the application SHALL NOT automatically select another device as a substitute. In source-less room-name mode, no row is a source substitute and automatic cycle progress SHALL NOT select or expand a row on the operator's behalf.

No dedicated room-cycle Cancel button is required. Application close during read-only automatic room work SHALL invalidate/cancel current room authority best-effort and SHALL not block the GUI waiting for remote network cleanup.

#### Scenario: Waiting row is expanded

- **WHEN** the operator expands an eligible row whose queue turn has not started
- **THEN** its view shows waiting/placeholder state
- **AND** no handler acquisition or device network I/O starts because of expansion

#### Scenario: Device fails automatically

- **WHEN** one room row fails during the automatic cycle
- **THEN** its safe failure is rendered inline
- **AND** no per-device error modal is required
- **AND** later eligible room rows continue to be processed

#### Scenario: Active room cycle locks the target-search context

- **GIVEN** a source-backed or source-less room cycle is active
- **WHEN** the operator attempts to edit the persistent target-search field or start another top full Refresh
- **THEN** target-search editing and top full Refresh remain unavailable until the active cycle reaches its terminal cleanup boundary
- **AND** no competing room target context starts device I/O

### Requirement: Full room Refresh owns global room summary and timestamp

Room-mode top full Refresh SHALL represent a complete new room diagnostic cycle. Before target re-resolution begins, it SHALL create a new room generation and invalidate/clear the previous room generation, tree/cache authority, row bindings, pending interaction authority, and accordion selection so old state cannot become current again merely because re-resolution fails.

The new generation SHALL re-resolve the current unchanged target-search context against current validated inventory before rebuilding shared room metadata and row state:

```text
IP target
    -> re-resolve the normalized current IP using the existing zero/one/many rules
    -> if one current source record with room_id exists, rebuild source-backed room mode

room-name target
    -> recompute current room-name candidates from the unchanged raw query
    -> reuse the current selected room_id only if it is still a member of the current candidate set
    -> if the unchanged query has exactly one current result, that exact room_id may be selected/current
    -> if several results exist and no prior current selection remains valid, require a new explicit selection
    -> rebuild source-less room mode with no source record
```

A stale/invalid room-name selection, an IP not-found/ambiguous result, inventory failure not covered by the existing IP fallback contract, or any other failed room re-resolution SHALL fail closed and SHALL NOT resurrect the previous room tree/cache/presentation as current authority. When re-resolution succeeds, full Refresh SHALL rebuild shared room metadata and every row state from current canonical inventory and execute the complete approved sequential room cycle. It SHALL NOT be a local per-row refresh.

While the cycle is active, the shared status SHALL indicate room equipment polling. A terminal cycle with no unsupported, missing-IP, ambiguous-IP, failed, degraded, or usable-warning rows SHALL display `Опрос завершён`. A terminal cycle containing any such problem SHALL display `Опрос завершён с проблемами`.

A room containing no eligible network rows SHALL still reach terminal completion, perform zero device I/O, and be classified as completed with problems.

`Последнее обновление` SHALL represent completion time of the most recent full room cycle, even when no device I/O was eligible. It SHALL NOT be changed merely by rendering cached row data.

#### Scenario: Full room cycle is clean

- **WHEN** every room row is eligible and completes with clean usable success
- **THEN** global status becomes `Опрос завершён`
- **AND** `Последнее обновление` records full-cycle completion time

#### Scenario: Room contains an unsupported record

- **WHEN** supported eligible rows complete successfully but another room record is unsupported
- **THEN** the room cycle still completes
- **AND** global status is `Опрос завершён с проблемами`

#### Scenario: Room has no eligible network rows

- **WHEN** every room row is unsupported, missing-IP, or ambiguous-IP
- **THEN** no device network I/O occurs
- **AND** the full cycle terminates as completed with problems
- **AND** `Последнее обновление` is updated

#### Scenario: Full Refresh revalidates a source-less room selection

- **GIVEN** the current room was established from room-name target-search with no source record
- **AND** the raw query is unchanged
- **WHEN** top full Refresh begins a new generation
- **THEN** current inventory candidates are recomputed before room/device I/O
- **AND** the prior selected `room_id` is reused only if it remains a current candidate
- **AND** successful re-resolution rebuilds source-less room mode without manufacturing a source record

#### Scenario: Failed source-less re-resolution does not resurrect the old room

- **GIVEN** the current room was established from a room-name selection
- **WHEN** top full Refresh cannot establish one current authoritative room for the unchanged target-search context
- **THEN** the previous room generation/tree/cache/selection remain invalidated
- **AND** no previous room record is promoted or restored as source authority
- **AND** no room device I/O starts from the stale context

### Requirement: Room accordion initial state and full-refresh reset are deterministic

Every newly established room session, including one created by top full Refresh, SHALL start from a deterministic accordion state based only on its current room-entry mode and new authoritative context.

For IP-entry room mode, if the current source row is supported and expandable under the room-row eligibility contract, that source row SHALL be the one initially expanded row. If the source row is not expandable, no row SHALL be expanded initially; the application SHALL NOT choose a secondary row automatically.

For source-less room-name entry, no source row exists and the accordion SHALL start fully collapsed. The application SHALL NOT automatically expand the first canonical row, first supported row, codec, PDU, first IP-bearing row, or any other room record merely to create an initial selection.

A new full Refresh SHALL NOT carry forward any previously expanded row or previous accordion selection. Before target re-resolution starts, the old room generation, tree/cache presentation, row bindings, and accordion selection SHALL lose authority and SHALL be cleared/reset. After successful re-resolution, the new tree SHALL apply only the current entry-mode rule above. If re-resolution fails, the previous room tree/cache/presentation/selection SHALL NOT be restored as current authority.

Automatic row success, warning, or failure during the new room cycle SHALL NOT change this user-selection state.

#### Scenario: Expandable IP source starts expanded

- **GIVEN** a new IP-entry room session is established and the source row is supported and expandable
- **WHEN** the tree is first presented
- **THEN** the source row is the only initially expanded row
- **AND** no later automatic row outcome changes expansion on the operator's behalf

#### Scenario: Non-expandable IP source starts fully collapsed

- **GIVEN** a new IP-entry room session is established and the source row is unsupported, missing-IP, or same-room ambiguous and therefore not expandable
- **WHEN** the tree is first presented
- **THEN** no room row is initially expanded
- **AND** no secondary row is selected automatically

#### Scenario: Source-less room starts fully collapsed

- **GIVEN** a new room session is established from an explicit room-name selection with no source record
- **WHEN** the tree is first presented
- **THEN** no room row is initially expanded
- **AND** no record is promoted to synthetic source or initial-selection authority

#### Scenario: Full Refresh does not preserve prior selection

- **GIVEN** any row was expanded in the previous source-backed or source-less room generation
- **WHEN** top full Refresh starts a new room generation
- **THEN** the previous selection and old room presentation lose authority before target re-resolution
- **AND** the successfully rebuilt tree uses only the new entry-mode initial-state rule
- **AND** failed re-resolution does not resurrect the previous tree or selection
