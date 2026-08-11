# pdu-room-codec-enrichment Specification

## ADDED Requirements

### Requirement: PDU related-codec enrichment may continue CloudLink live microphone metering

After exact PDU/room/related-codec resolution and successful initial related-codec status normalization, `PDURoomCodecEnrichmentController` or an equivalent focused application-owned enrichment boundary SHALL continue live microphone metering only when the exact resolved related codec is:

```text
CloudLink Bar 310
CloudLink Box 310
```

The PDU meter SHALL use the same model-specific extraction, zero/unavailable distinction, fixed display ceiling of `20`, and one-second serialized cadence defined by the `cloudlink-live-microphone-metering` capability.

The existing dedicated related-codec serialized read-only session lane SHALL remain independent from generic codec refresh and from `CodecScreen.interactive_controller`. For a supported CloudLink related codec, the initial call/presentation status operation and subsequent microphone samples SHALL use the same current dedicated related-codec session context rather than opening a second simultaneous PDU-related CloudLink session solely for the meter.

Initial status success SHALL set the existing codec diagnostic status to `SUCCESS` and publish call/presentation data under the existing contract. Live-meter availability SHALL be an independent optional presentation field and SHALL NOT change `codec_diagnostic_status`, erase accepted call/presentation values, or change accepted PDU success.

An endpoint-local unavailable/malformed meter sample on an otherwise usable session SHALL affect only the meter for that cycle and SHALL allow the next scheduled sample. A typed session/transport/authentication failure SHALL use existing bounded read-only recovery and credential policy; meter recovery SHALL NOT become an unbounded one-second reconnect/login loop and meter success SHALL NOT persist credential/profile memory.

The live meter SHALL remain bound to the exact current enrichment generation, PDU accepted-refresh identity, inventory/room/codec resolution, codec model/IP, and codec credential-context revision. PDU supersession, relevant credential change, inventory replacement, explicit invalidation, or shutdown SHALL invalidate meter authority immediately. Queued stale sample work SHALL be rejected before handler acquisition and network I/O where applicable, and stale callbacks SHALL update neither PDU presentation nor credential/profile memory.

For a resolved related codec outside the two supported CloudLink models, no live-meter loop SHALL start and existing one-shot related-codec status behavior SHALL remain unchanged.

#### Scenario: PDU resolves Bar 310

- **GIVEN** an accepted current PDU refresh resolves exactly one `CloudLink Bar 310`
- **WHEN** initial related-codec status succeeds
- **THEN** codec diagnostic status becomes `SUCCESS`
- **AND** the same dedicated related-codec session context remains current for serialized one-second microphone samples
- **AND** no second simultaneous PDU-related CloudLink session is opened solely for the meter

#### Scenario: One PDU meter sample is unavailable

- **GIVEN** accepted related-codec call/presentation status is already visible
- **WHEN** one sample has an endpoint-local unsuccessful or malformed payload while the session remains usable
- **THEN** only the microphone meter becomes unavailable for that cycle
- **AND** PDU data, codec diagnostic `SUCCESS`, call status, and presentation status remain accepted
- **AND** the next scheduled sample may run

#### Scenario: PDU resolves unsupported related codec

- **WHEN** exact related-codec resolution selects a supported VCS model other than `CloudLink Bar 310` or `CloudLink Box 310`
- **THEN** no CloudLink microphone-meter polling starts
- **AND** existing one-shot related-codec status cleanup remains authoritative

#### Scenario: Repeat PDU refresh supersedes live metering

- **GIVEN** live microphone samples are being accepted for one enrichment generation
- **WHEN** repeat PDU Refresh starts, including for the same PDU and same related codec
- **THEN** the old meter authority is invalidated immediately
- **AND** queued old sample work performs no new handler acquisition or network I/O
- **AND** old callbacks cannot restore the prior meter

### Requirement: PDU related-codec block renders the CloudLink meter as its top row

When exact current related-codec resolution selects `CloudLink Bar 310` or `CloudLink Box 310`, the existing PDU `Комната и связанный кодек` section SHALL render exactly one row labelled `Уровень микрофонов` as the top overall row in the section.

The row SHALL contain a horizontal live meter with no numeric text overlay and the same available/unavailable presentation semantics as the codec-page CloudLink meter. The existing VIP row SHALL appear immediately below it and SHALL remain the first room-context row.

Before supported related-codec resolution is established, and for resolved related codecs outside the two supported CloudLink models, the meter row SHALL be hidden. Hiding the unsupported meter SHALL NOT reorder, remove, or change the semantics of existing room/codec rows.

PDU enrichment reset/supersession SHALL immediately clear or hide the old meter at the same authoritative boundary that clears the existing related-room/codec presentation. A stale sample SHALL NOT restore a bar value after supersession.

#### Scenario: Supported CloudLink related codec is resolved

- **WHEN** current PDU enrichment resolves exact `CloudLink Box 310`
- **THEN** `Уровень микрофонов` is the first overall row in `Комната и связанный кодек`
- **AND** `VIP` is immediately below it as the first room-context row

#### Scenario: Related codec does not support the meter

- **WHEN** current related-codec resolution selects another supported codec model
- **THEN** the microphone-meter row is hidden
- **AND** the existing room and related-codec presentation remains available

## MODIFIED Requirements

### Requirement: Related-codec resources have explicit lifecycle cleanup

The application SHALL invalidate and close the dedicated related-codec handler/session on terminal failure, PDU-context supersession, relevant credential change, inventory replacement, and application shutdown. Cleanup SHALL run on the execution lane that owns network/session resources and SHALL be idempotent or exactly once. The Qt GUI thread SHALL NOT block on network cleanup.

For a resolved related codec outside `CloudLink Bar 310` and `CloudLink Box 310`, terminal status success SHALL retain the existing behavior: it SHALL invalidate/close the dedicated related-codec handler/session after accepted status publication.

For exact `CloudLink Bar 310` or `CloudLink Box 310`, accepted initial related-codec status success SHALL be terminal only for the initial status operation and SHALL NOT by itself close the dedicated session while live microphone metering remains current. The same dedicated session context MAY remain active solely for the approved serialized read-only meter lifecycle. It SHALL be closed when the meter context is superseded, when a typed failure makes the session unusable after approved bounded recovery, when relevant credential or inventory context changes, when explicit PDU/enrichment invalidation occurs, or when the application shuts down.

An endpoint-local unavailable or malformed microphone sample on an otherwise usable session SHALL NOT require session teardown; the next scheduled sample may reuse the current dedicated session. This exception SHALL NOT weaken cleanup for authentication rejection, established-session invalidation, transport/session failure, stale context, or shutdown.

#### Scenario: Application closes during related-codec work

- **WHEN** application shutdown supersedes related-codec work
- **THEN** enrichment and dedicated session contexts are invalidated immediately
- **AND** resource cleanup runs on the owning lane
- **AND** later callbacks cannot update destroyed or superseded UI state

#### Scenario: Non-CloudLink status succeeds

- **WHEN** a resolved related codec outside Bar 310 and Box 310 completes accepted status successfully
- **THEN** its dedicated related-codec handler/session is cleaned up under the existing one-shot lifecycle
- **AND** no live microphone-meter work remains

#### Scenario: CloudLink status succeeds and meter continues

- **GIVEN** exact related-codec model is Bar 310 or Box 310
- **WHEN** initial related-codec status succeeds and the enrichment generation remains current
- **THEN** the dedicated session is not closed merely because initial status succeeded
- **AND** it remains available only for the approved serialized live-meter lifecycle

#### Scenario: CloudLink meter context is superseded

- **GIVEN** a CloudLink related-codec session remains open for live metering
- **WHEN** PDU context, codec credential context, inventory context, explicit invalidation, or shutdown supersedes it
- **THEN** meter authority is invalidated immediately
- **AND** session cleanup runs on the owning background lane
- **AND** no later sample can update current presentation

### Requirement: PDU room block emphasizes VIP state

After an accepted current PDU refresh resolves room context, the PDU page SHALL render the room VIP state as the first room-context line above the existing room-characteristics and related-codec information.

When current exact related-codec resolution selects `CloudLink Bar 310` or `CloudLink Box 310`, the optional `Уровень микрофонов` live-meter row SHALL be the top overall line of the `Комната и связанный кодек` section and the VIP line SHALL appear immediately below it as the first room-context line. For all other related-codec states, the hidden/absent meter SHALL leave VIP as the top visible room-context line under the existing layout.

VIP presentation SHALL distinguish exactly:

```text
VIP: ДА
VIP: НЕТ
VIP: НЕТ ДАННЫХ
VIP: КОНФЛИКТ ДАННЫХ
```

`VIP: ДА` SHALL receive visually prominent treatment so that it is immediately noticeable after refresh. Visual emphasis SHALL not change lifecycle, focus, accessibility, or device-control authority.

The existing PDU room and related-codec block SHALL otherwise retain its approved behavior. VIP resolution SHALL use the shared equipment room-context contract and SHALL not create a second independent room-identity algorithm. Live microphone metering SHALL NOT become room-identity or VIP authority.

#### Scenario: Accepted PDU refresh resolves a VIP room

- **GIVEN** a current accepted PDU refresh succeeds
- **AND** the exact PDU inventory record resolves to a room with consistent VIP=true evidence
- **WHEN** PDU enrichment presentation is rendered
- **THEN** the first room-context line is `VIP: ДА`
- **AND** it is visually prominent
- **AND** the existing room and related-codec details remain available below it

#### Scenario: VIP room has a supported CloudLink related codec

- **GIVEN** current enrichment resolves a VIP room and exact Bar 310 or Box 310 related codec
- **WHEN** the related-codec section is rendered
- **THEN** `Уровень микрофонов` is the top overall row
- **AND** `VIP: ДА` is immediately below it as the first room-context row
- **AND** VIP remains visually prominent

#### Scenario: VIP evidence conflicts

- **GIVEN** the PDU room contains conflicting non-null VIP evidence
- **WHEN** PDU room presentation is rendered
- **THEN** it shows `VIP: КОНФЛИКТ ДАННЫХ`
- **AND** it does not select one record's value
- **AND** accepted PDU device data and controls remain valid
