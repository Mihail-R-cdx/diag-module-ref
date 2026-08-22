## REMOVED Requirements

### Requirement: PDU lifecycle exposes accepted-refresh and supersession boundaries

**Reason:** The dedicated PDU-to-room-to-related-codec enrichment lifecycle is retired. Room context and every codec are now represented by the authoritative room session/tree, and post-cycle interaction is bound to exact room records.

**Migration:** Keep PDU refresh/mutation authority in `PDUController` for the PDU record itself. Do not emit or consume enrichment accepted-refresh/supersession events.

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
