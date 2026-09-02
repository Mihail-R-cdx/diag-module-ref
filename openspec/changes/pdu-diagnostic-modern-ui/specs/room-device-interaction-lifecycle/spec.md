# room-device-interaction-lifecycle Delta

## ADDED Requirements

### Requirement: Fixed PDU dashboard reuses the existing exact-row refresh and mutation lifecycle

The dedicated common room PDU dashboard SHALL remain a presentation/application-intent surface over the existing exact-row room interaction architecture. It SHALL NOT introduce a PDU-specific interaction lane, direct widget-to-handler path, alternate credential owner, optimistic accepted-state owner, or independent request generation.

The two visible PDU refresh affordances:

```text
expanded-row far-right refresh icon
`Обновить статус`
```

SHALL be strict aliases of the same existing exact-row `LOCAL_REFRESH` intent/lifecycle. They SHALL share one eligibility state, one lock state, one current exact-row context and one operation token/generation. Accepting either refresh while another Local Refresh or incompatible room network lifecycle is active/retiring SHALL follow the existing serialized interaction policy rather than creating a concurrent PDU refresh.

A supported individual PDU action (`Вкл`, `Выкл`, or supported `Перезапуск`) and supported bulk action (`Включить всё` or `Выключить всё`) SHALL enter only the existing state-changing room path after its existing explicit confirmation boundary. Existing LIVE retirement where applicable, exact-row currentness, credential ownership, no-blind-retry policy, mutation ambiguity handling and mandatory reconciliation remain unchanged. A command ACK/request result SHALL NOT become accepted outlet state; only successful current reconciliation MAY atomically replace the exact PDU row cache.

A fixed visible PDU affordance that exact capability authority marks unsupported SHALL resolve locally before interaction-coordinator admission. Such a local unsupported click SHALL NOT invalidate LIVE, acquire credentials/handler/session, reserve the interaction lane, create a mutation/reconciliation generation, alter accepted cache or perform device network I/O. During any active/retiring lifecycle that normally disables the corresponding refresh or state-changing controls, the visible common PDU controls SHALL obey that same temporary lock; the local-only unsupported exception does not bypass lifecycle locking.

Bulk ON/OFF SHALL reuse the current application-owned bulk policy and deterministic outlet sequencing. Presentation SHALL NOT implement bulk by programmatically clicking individual Qt controls or create a parallel set of per-outlet network owners. No bulk reboot lifecycle is introduced.

PDU dashboard rendering, theme switching, hover, scrolling, resizing and power-placeholder presentation SHALL perform no network interaction.

#### Scenario: Header refresh and text refresh are one lifecycle

- **GIVEN** a current expanded connected PDU row is eligible for Local Refresh
- **WHEN** the operator activates either the header refresh icon or `Обновить статус`
- **THEN** the same existing exact-row `LOCAL_REFRESH` intent/lifecycle is requested
- **AND** neither affordance owns a separate worker/session/generation
- **AND** the other refresh affordance follows the same active/retiring lock state

#### Scenario: Supported Aten outlet mutation keeps mandatory reconciliation

- **GIVEN** a current connected Aten outlet is eligible for a supported state-changing action
- **WHEN** the operator confirms `Вкл`, `Выкл`, or `Перезапуск`
- **THEN** the existing exact-row PDU mutation path owns the send
- **AND** accepted outlet state changes only after current mandatory reconciliation succeeds
- **AND** ambiguous/failed reconciliation follows the existing blocked/unconfirmed recovery policy

#### Scenario: Unsupported fixed PDU action never enters room interaction

- **GIVEN** the fixed common PDU dashboard shows an affordance unsupported by the exact model
- **AND** no lifecycle lock currently disables that affordance
- **WHEN** the operator activates it
- **THEN** support is resolved before room interaction admission and a local unsupported information result is shown
- **AND** no lifecycle authority, handler/session, credentials, network I/O or accepted state changes

#### Scenario: Bulk operation does not use Qt buttons as execution owners

- **WHEN** an eligible current PDU row starts `Включить всё` or `Выключить всё`
- **THEN** the existing application-owned bulk PDU lifecycle owns deterministic execution/reconciliation
- **AND** the dashboard does not emulate bulk by triggering individual outlet buttons

### Requirement: Modern PDU presentation preserves exact-row and related-codec separation

All PDU dashboard refresh/mutation intents SHALL remain bound to the immutable exact current expanded PDU row context required by the root lifecycle. Model/IP/record identity SHALL NOT be reconstructed from displayed card text, outlet names, target-search contents or standalone screen state.

The modern PDU dashboard SHALL continue to present/control only that exact PDU. It SHALL NOT restore the removed PDU-hosted related-codec resolver, credential/session path, call/presentation read, microphone meter, worker or child network lane. Shared room metadata and codec diagnostics remain owned by the common room header and the codec row respectively.

#### Scenario: Modern PDU local refresh remains PDU-only

- **WHEN** either modern PDU refresh affordance completes an accepted exact-row refresh
- **THEN** only current PDU data/presentation is eligible to update
- **AND** no related-codec lookup/session/status/meter lifecycle starts
- **AND** codec data remains owned by its own exact room row
