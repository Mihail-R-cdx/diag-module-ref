## MODIFIED Requirements

### Requirement: PDU lifecycle exposes accepted-refresh and supersession boundaries

PDU refresh, mutation reconciliation, presentation, and lifecycle SHALL NOT resolve or select a related codec as a PDU side effect, start a dedicated related-codec handler, session, or network lane, render duplicated room, VIP, or related-codec presentation inside the PDU screen, or host related-codec CloudLink microphone metering.

PDU-owned diagnostics, outlet/control behavior, mutation/reconciliation behavior, and room-tree PDU row rendering SHALL remain independent and supported. Room identity and display SHALL come from the authoritative room session/header. Every codec SHALL be diagnosed and interacted with only through its own exact room record under `room-device-interaction-lifecycle`.

#### Scenario: User PDU refresh is accepted

- **WHEN** a PDU refresh succeeds
- **THEN** no related-codec lookup, handler/session construction, or network I/O starts
- **AND** PDU-owned diagnostics and controls remain available

#### Scenario: Reconciliation refresh succeeds

- **WHEN** PDU mutation reconciliation succeeds
- **THEN** no related-codec enrichment starts
- **AND** PDU mutation/reconciliation authority remains unchanged

#### Scenario: New PDU refresh starts but later fails

- **WHEN** a new PDU refresh starts and later fails
- **THEN** no related-codec lookup, handler/session construction, or network I/O starts
- **AND** no prior PDU-hosted room, VIP, or codec presentation is restored

#### Scenario: Repeat Refresh uses the same PDU identity

- **WHEN** the operator starts repeat Refresh for the same PDU identity
- **THEN** no related-codec enrichment generation, handler/session, or network lane starts
- **AND** PDU-owned refresh behavior remains independent

#### Scenario: PDU row is presented

- **WHEN** a PDU row is rendered
- **THEN** it contains no duplicated room, VIP, or related-codec presentation block
- **AND** it contains no PDU-hosted related-codec CloudLink microphone meter

#### Scenario: Codec exists in the same room

- **GIVEN** a PDU and a codec belong to the same authoritative room
- **WHEN** the room is presented
- **THEN** the codec remains available only as its own exact codec row
- **AND** codec diagnostics and interaction follow `room-device-interaction-lifecycle`

#### Scenario: PDU own diagnostics and controls are used

- **WHEN** the operator uses PDU diagnostics or controls
- **THEN** PDU behavior remains supported
- **AND** the retirement contract does not remove PDU-owned functionality

## REMOVED Requirements

### Requirement: Pure authoritative PDU and room resolution

**Reason:** PDU-specific room resolution is no longer needed because room identity is resolved once by `room-equipment-diagnostics` from the top source IP.

**Migration:** Use the current room session and exact PDU row. Do not perform a second PDU-to-room lookup for related-codec enrichment.

### Requirement: Exact related-codec candidate resolution

**Reason:** The room tree contains every codec record independently; selecting exactly one related codec from a PDU context would reintroduce a competing room/codec authority.

**Migration:** Diagnose/interact with each codec only through its own exact room row.

### Requirement: Room display evidence does not replace room identity

**Reason:** Shared room display metadata is already owned by the room session/header and no longer belongs to a PDU enrichment block.

**Migration:** Use the `room-equipment-diagnostics` source-first room header contract.

### Requirement: Independent bounded related-codec status lifecycle

**Reason:** The dedicated related-codec network lane is removed. Exact codec rows now own their own room interaction lifecycle.

**Migration:** Route codec reads through the exact codec row and `room-device-interaction-lifecycle`.

### Requirement: Every enrichment generation forces dedicated session rollover

**Reason:** Enrichment generations no longer exist after removal of the related-codec lane.

**Migration:** Use room generation plus exact-row interaction generation/currentness.

### Requirement: Related-codec status normalization

**Reason:** PDU presentation no longer consumes a narrow related-codec status model.

**Migration:** Render codec state only inside the codec's own row using its existing model-specific parser/presentation contract.

### Requirement: Related-codec credential and transport policy remains application-owned

**Reason:** A PDU-specific related-codec credential/transport context is no longer created.

**Migration:** Preserve application-owned credential/transport policy on the exact codec row under the common room interaction lifecycle.

### Requirement: Composite enrichment outcome preserves PDU success

**Reason:** There is no longer a composite PDU+room+codec enrichment result.

**Migration:** PDU result authority remains only PDU result authority; codec outcomes are independent per-record room state.

### Requirement: Related-codec resources have explicit lifecycle cleanup

**Reason:** The dedicated related-codec handler/session resources are removed with the enrichment lane.

**Migration:** Exact-row live/read/control resources follow `room-device-interaction-lifecycle` cleanup.

### Requirement: PDU room block emphasizes VIP state

**Reason:** Room/VIP presentation is centralized in the shared room header and shall not be duplicated inside PDU presentation.

**Migration:** Remove the PDU `Комната и связанный кодек` room/VIP block and rely on the shared room header.

### Requirement: PDU VIP presentation follows enrichment supersession

**Reason:** PDU-local VIP enrichment state is removed.

**Migration:** Room header lifecycle follows room-session supersession/full Refresh rather than PDU refresh.

### Requirement: PDU related-codec enrichment may continue CloudLink live microphone metering

**Reason:** PDU-hosted related-codec live metering duplicates the codec row and creates an unnecessary second codec session authority.

**Migration:** CloudLink live metering runs only when the exact CloudLink room row owns current post-cycle live authority.

### Requirement: PDU related-codec block renders the CloudLink meter as its top row

**Reason:** The related-codec block is removed from the PDU screen.

**Migration:** Render the microphone meter only in the exact CloudLink codec row when that row is expanded/current.
