# diagnostic-application-shell Delta

## ADDED Requirements

### Requirement: Registered equipment pages render inventory switch connection fields

Every equipment page registered by the application equipment-page registry SHALL render exactly one inventory-backed row labelled `IP коммутатора` and exactly one inventory-backed row labelled `Порт коммутатора`.

The two rows SHALL be placed in that screen's existing device-information card. For the current registered pages, placement SHALL be:

```text
codec      -> Основная информация
matrix     -> Информация об устройстве
pdu        -> Информация об устройстве
audio_dsp  -> Информация об устройстве
```

The rows SHALL NOT be placed in a separate switch card, the shared non-PDU room block, the PDU related-room/codec section, a control section, a routing table, an outlet table, or another page-specific section.

The equipment-page registry SHALL remain the completeness authority. Tests SHALL enumerate every registered page, including PDU pages with dedicated room placement, and prove that each page receives the same two switch rows without relying on a manually maintained subset of screen classes.

Each row SHALL render the corresponding canonical inventory value for the current unique device record. Null or unavailable values SHALL render as `—`. The two fields SHALL be independent so a unique partial connection preserves the available switch IP or opaque switch-port text while the other row renders `—`.

Switch connection presentation SHALL remain informational and non-blocking. Missing inventory, invalid current IP, zero or multiple matching records, older snapshots with null-adapted switch fields, or null schema-v3 fields SHALL NOT open an automatic modal error, change the device request outcome, disable valid equipment controls, or prevent existing diagnostics.

#### Scenario: Codec page shows switch connection in existing information card

- **GIVEN** the current codec IP resolves to one schema-v3 equipment record with both switch fields
- **WHEN** the codec page becomes current
- **THEN** its existing `Основная информация` card shows `IP коммутатора` with the exact canonical switch IP
- **AND** it shows `Порт коммутатора` with the exact canonical opaque port text
- **AND** no separate switch card is created

#### Scenario: Matrix page shows switch connection in existing information card

- **GIVEN** the current Matrix IP resolves to one schema-v3 equipment record with switch connection data
- **WHEN** the Matrix page becomes current
- **THEN** its existing `Информация об устройстве` card contains both inventory-backed switch rows
- **AND** Matrix routing and device-observed information retain their existing authority

#### Scenario: PDU page is included despite dedicated room placement

- **GIVEN** the current PDU IP resolves to one schema-v3 equipment record with switch connection data
- **WHEN** the PDU page becomes current
- **THEN** its existing `Информация об устройстве` card contains both switch rows
- **AND** its dedicated `Комната и связанный кодек` section remains separate and unchanged

#### Scenario: Audio DSP page shows switch connection in existing information card

- **GIVEN** the current audio-DSP IP resolves to one schema-v3 equipment record with switch connection data
- **WHEN** the audio-DSP page becomes current
- **THEN** its existing `Информация об устройстве` card contains both inventory-backed switch rows
- **AND** meter rendering retains its existing authority

#### Scenario: Unique partial switch connection is displayed

- **GIVEN** the current device resolves to one record with exactly one non-null switch field
- **WHEN** its registered equipment page renders inventory context
- **THEN** the available canonical field is displayed exactly
- **AND** the unavailable field displays `—`
- **AND** the page does not infer or manufacture the missing value

#### Scenario: Switch connection is unavailable

- **WHEN** inventory is unavailable, the current IP is invalid, lookup returns zero or multiple records, or both canonical switch fields are null
- **THEN** both switch rows display `—`
- **AND** no automatic modal connection error is opened
- **AND** existing device diagnostics and controls remain available

#### Scenario: Registry coverage remains complete

- **WHEN** tests enumerate the application equipment-page registry
- **THEN** every current registered page exposes exactly one switch-IP row and one switch-port row in its existing information card
- **AND** repeated page activation or widget reconstruction does not duplicate either row

### Requirement: Switch connection presentation uses one application-owned inventory lifecycle

The application/composition layer SHALL own resolution, freshness, and publication of equipment-page switch connection presentation. Registered equipment screens SHALL remain rendering boundaries and SHALL NOT load or query inventory, interpret zero/one/many lookup outcomes, select an equipment record, decide stale-result acceptance, or derive switch values from device responses.

For a valid normalized current device IP, the application SHALL use the existing immutable inventory device-IP lookup. Exactly one matching record SHALL authorize display of that record's `switch_ip_address` and `switch_port` independently. Zero or multiple matching records SHALL authorize neither value. The application SHALL NOT break ambiguity by selected diagnostic model, `device_kind`, MAC, room, row order, non-null preference, or Qt presentation state.

The switch presentation SHALL be bound to current exact model, normalized IP, inventory snapshot identity or inventory-unavailable identity, registered page context, and an application-owned generation, or an equivalent complete immutable context. Changing any authoritative context SHALL invalidate prior presentation immediately. A delayed or queued publication SHALL render only when its complete binding and generation still match the current application context.

Current switch presentation SHALL be resolved and may be published without device network I/O. Preliminary reachability, credential resolution, handler acquisition, worker/controller submission, device refresh result/error/completion, interactive actions, PDU mutation, Matrix route, and audio polling SHALL NOT be switch-presentation authorities. They SHALL NOT overwrite inventory-backed values from device payloads, convert unavailable switch context into device failure, or restore an older inventory context.

When a screen reconstructs its information-row widgets, the shell MAY re-render the already accepted current inventory presentation into the new widgets. Re-rendering SHALL preserve the same current binding and SHALL NOT reclassify widget reconstruction as device or inventory authority.

#### Scenario: Switch context publishes without device success

- **GIVEN** the current model/IP/page and inventory snapshot resolve one device record
- **WHEN** that equipment context becomes current before any device request succeeds
- **THEN** the application publishes the record's switch connection presentation
- **AND** no handler, worker, controller, or switch network operation is required

#### Scenario: Ambiguous device IP is not narrowed

- **GIVEN** current inventory contains multiple records for the normalized device IP
- **WHEN** one record happens to match the selected model or has more complete switch fields
- **THEN** the application publishes neither record's switch values
- **AND** both rows remain unavailable
- **AND** model or completeness does not break ambiguity

#### Scenario: Current IP changes

- **GIVEN** switch values from one current device are visible
- **WHEN** the normalized IP context changes
- **THEN** the old values are invalidated immediately
- **AND** only a presentation resolved for the new current binding may be rendered

#### Scenario: Inventory snapshot changes

- **GIVEN** a current page displays switch values from one accepted inventory snapshot
- **WHEN** the application replaces that snapshot or inventory becomes unavailable
- **THEN** the old presentation is invalidated
- **AND** current values are resolved and published only from the new snapshot or unavailable context

#### Scenario: Stale publication is rejected

- **GIVEN** an older switch presentation was resolved for a prior model, IP, page, snapshot, or generation
- **WHEN** it reaches the rendering boundary after current context changed
- **THEN** the application rejects it
- **AND** it cannot restore old switch values

#### Scenario: Device request failure does not clear current switch context

- **GIVEN** current switch values have been accepted from inventory
- **WHEN** the device request fails, times out, or exhausts credentials
- **THEN** the current inventory-backed values remain visible
- **AND** the device failure retains its existing independent presentation

#### Scenario: Device payload cannot override inventory connection

- **GIVEN** a handler or worker result contains a similarly named IP, port, MAC, interface, or connection field
- **WHEN** the screen renders that device result
- **THEN** it does not replace `IP коммутатора` or `Порт коммутатора`
- **AND** only the application-owned canonical inventory presentation controls those rows

### Requirement: Codec page rebuild preserves shared inventory presentation boundaries

`CodecScreen` MAY reconstruct codec-owned information and control widgets when codec model context or diagnostic lifecycle requires it. That reconstruction SHALL preserve the centralized equipment-page contracts for shell-owned room presentation and application-owned switch presentation.

After every codec parameter-display rebuild used during model change, diagnostic startup, refresh, or equivalent current-page reconstruction, the codec page SHALL contain exactly one shared `RoomInformationBlock` at the bottom of its equipment-page content. The block SHALL show the current accepted room address, VIP state, and safe room status under the existing room-context lifecycle without waiting for codec network success.

The rebuild SHALL also leave exactly one `IP коммутатора` row and exactly one `Порт коммутатора` row in the codec's existing `Основная информация` card and SHALL render the current accepted switch presentation into those current row widgets.

Implementation SHALL use one explicit ownership strategy: either codec rebuild preserves shell-owned children while replacing only codec-owned widgets, or a focused shell/layout hook safely reattaches one shared block and republishes current room and switch presentation immediately after rebuilding. Initial constructor attachment alone SHALL NOT be treated as sufficient lifecycle coverage.

Repeated rebuilds SHALL NOT leave visible, hidden, pending-deletion, or otherwise live duplicate room blocks or switch rows. Codec request start, success, failure, and completion SHALL remain independent from the room and switch inventory publication authorities.

#### Scenario: Real codec refresh rebuild keeps room context

- **GIVEN** a current codec context has resolved room address and VIP state
- **WHEN** normal diagnostic startup calls the codec parameter-display rebuild
- **THEN** exactly one shared room block remains attached at the bottom of the codec page
- **AND** it shows the current address and VIP state
- **AND** no codec network success is required to restore it

#### Scenario: Real codec refresh rebuild keeps switch context

- **GIVEN** a current codec context has accepted switch IP and port presentation
- **WHEN** normal diagnostic startup reconstructs the codec information card
- **THEN** the reconstructed card contains exactly one switch row pair
- **AND** both rows show the current accepted inventory values
- **AND** device data clearing does not permanently erase them

#### Scenario: Repeated codec rebuild does not duplicate inventory widgets

- **WHEN** codec parameter display is rebuilt multiple times for current or changing codec contexts
- **THEN** the live codec page contains exactly one shared room block
- **AND** it contains exactly one `IP коммутатора` row and one `Порт коммутатора` row
- **AND** deleted or hidden stale widgets cannot receive a later publication

#### Scenario: Codec failure leaves inventory context visible

- **GIVEN** current room and switch presentation is visible after codec rebuild
- **WHEN** the codec diagnostic request fails
- **THEN** current room address, VIP state, switch IP, and switch port remain independently visible
- **AND** the codec request error does not clear or replace them
