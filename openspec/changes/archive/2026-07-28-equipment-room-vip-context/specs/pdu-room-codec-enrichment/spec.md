# pdu-room-codec-enrichment Delta

## ADDED Requirements

### Requirement: PDU room block emphasizes VIP state

After an accepted current PDU refresh resolves room context, the PDU page SHALL render the room VIP state as the first line above the existing room-characteristics and related-codec information.

Presentation SHALL distinguish exactly:

```text
VIP: ДА
VIP: НЕТ
VIP: НЕТ ДАННЫХ
VIP: КОНФЛИКТ ДАННЫХ
```

`VIP: ДА` SHALL receive visually prominent treatment so that it is immediately noticeable after refresh. Visual emphasis SHALL not change lifecycle, focus, accessibility, or device-control authority.

The existing PDU room and related-codec block SHALL otherwise retain its approved behavior. VIP resolution SHALL use the shared equipment room-context contract and SHALL not create a second independent room-identity algorithm.

#### Scenario: Accepted PDU refresh resolves a VIP room

- **GIVEN** a current accepted PDU refresh succeeds
- **AND** the exact PDU inventory record resolves to a room with consistent VIP=true evidence
- **WHEN** PDU enrichment presentation is rendered
- **THEN** the first room-context line is `VIP: ДА`
- **AND** it is visually prominent
- **AND** the existing room and related-codec details remain available below it

#### Scenario: VIP evidence conflicts

- **GIVEN** the PDU room contains conflicting non-null VIP evidence
- **WHEN** PDU room presentation is rendered
- **THEN** it shows `VIP: КОНФЛИКТ ДАННЫХ`
- **AND** it does not select one record's value
- **AND** accepted PDU device data and controls remain valid

### Requirement: PDU VIP presentation follows enrichment supersession

Starting a new or repeated PDU refresh, changing PDU model/IP/credential context, explicit invalidation, or shutdown SHALL clear or supersede the previously rendered VIP state at the same boundary as the existing PDU room enrichment.

A stale enrichment result SHALL NOT restore an old VIP value, room address, or related-codec presentation. VIP lookup failure SHALL remain optional contextual-diagnostic failure and SHALL NOT convert accepted PDU success into PDU failure, trigger PDU retry, or open an automatic modal connection error.

#### Scenario: Repeat refresh supersedes prior VIP state

- **GIVEN** a VIP value from an earlier accepted PDU refresh is visible
- **WHEN** a repeat refresh begins
- **THEN** the earlier VIP presentation is invalidated immediately
- **AND** only the result bound to the new refresh generation may be rendered
