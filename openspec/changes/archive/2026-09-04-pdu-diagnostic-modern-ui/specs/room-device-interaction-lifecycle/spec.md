# room-device-interaction-lifecycle Delta

## MODIFIED Requirements

### Requirement: Debug is local exact-row presentation

The current `Отладка` action in room mode SHALL be bound to the exact current expanded supported non-PDU row and SHALL display only that row's accumulated terminal/log presentation. Opening or closing Debug SHALL NOT by itself create device network I/O, stop live, select credentials, or acquire a handler/session.

When no supported expandable row is current, Debug SHALL be unavailable. Switching/collapsing the row SHALL close/invalidate the row-specific Debug presentation so logs cannot be attributed to another record. Any future Debug sub-action that performs device I/O SHALL explicitly enter an approved auxiliary-read or state-changing lifecycle; this change SHALL NOT create an arbitrary network command console.

The modern expanded PDU dashboard intentionally exposes no local `Отладка` affordance. This is a presentation-visibility exception only: it does not change PDU network capability, create an alternate Debug path, authorize hidden direct commands, or alter approved exact-row Debug controls for other device families.

#### Scenario: Debug opens while live is active

- **GIVEN** the current exact supported non-PDU row has active live
- **WHEN** the operator opens Debug
- **THEN** Debug shows that exact row's local accumulated log/terminal state
- **AND** opening Debug creates no device I/O, credential selection, or handler/session acquisition
- **AND** live continues because opening Debug creates no device I/O

#### Scenario: Modern PDU row omits local Debug

- **WHEN** a current supported PDU row is expanded in the modern dashboard
- **THEN** no local `Отладка` control is visible
- **AND** no Debug network capability or alternate lifecycle is created

#### Scenario: Non-PDU Debug remains exact-row presentation

- **GIVEN** a current expanded supported non-PDU row has approved Debug presentation
- **WHEN** the operator opens Debug
- **THEN** Debug shows that exact row's local accumulated log/terminal state
- **AND** opening it creates no device I/O, credential/session acquisition, or change to row authority

## ADDED Requirements

### Requirement: Fixed PDU dashboard reuses the existing exact-row refresh and mutation lifecycle

The dedicated common room PDU dashboard SHALL remain a presentation/application-intent surface over the existing exact-row room interaction architecture. It SHALL NOT introduce a PDU-specific interaction lane, direct widget-to-handler path, alternate credential owner, optimistic accepted-state owner, or independent request generation.

The sole visible PDU refresh control, `Обновить статус`, SHALL publish the existing exact-row `LOCAL_REFRESH` intent/lifecycle. It SHALL use the existing eligibility state, lock state, current exact-row context, operation token/generation, stale-result suppression, and serialized interaction policy. Activating it while another Local Refresh or incompatible room network lifecycle is active/retiring SHALL not create a concurrent PDU refresh.

A supported individual PDU action (`Вкл`, `Выкл`, or supported `Перезапуск`) and supported bulk action (`Включить всё` or `Выключить всё`) SHALL enter only the existing state-changing room path after its existing explicit confirmation boundary. Existing LIVE retirement where applicable, exact-row currentness, credential ownership, no-blind-retry policy, mutation ambiguity handling and mandatory reconciliation remain unchanged. A command ACK/request result SHALL NOT become accepted outlet state; only successful current reconciliation MAY atomically replace the exact PDU row cache.

A fixed visible PDU affordance that exact capability authority marks unsupported SHALL resolve locally before interaction-coordinator admission. Such a local unsupported click SHALL NOT invalidate LIVE, acquire credentials/handler/session, reserve the interaction lane, create a mutation/reconciliation generation, alter accepted cache or perform device network I/O. During any active/retiring lifecycle that normally disables the corresponding refresh or state-changing controls, the visible common PDU controls SHALL obey that same temporary lock; the local-only unsupported exception does not bypass lifecycle locking.

Bulk ON/OFF SHALL reuse the current application-owned bulk policy and deterministic outlet sequencing. Presentation SHALL NOT implement bulk by programmatically clicking individual Qt controls or create a parallel set of per-outlet network owners. No bulk reboot lifecycle is introduced.

PDU dashboard rendering, theme switching, hover, scrolling, resizing and power-placeholder presentation SHALL perform no network interaction.

#### Scenario: Sole PDU text refresh uses the existing lifecycle

- **GIVEN** a current expanded connected PDU row is eligible for Local Refresh
- **WHEN** the operator activates `Обновить статус`
- **THEN** the same existing exact-row `LOCAL_REFRESH` intent/lifecycle is requested
- **AND** the control owns no separate worker/session/generation
- **AND** it follows the existing active/retiring lock state

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

- **WHEN** the modern PDU `Обновить статус` control completes an accepted exact-row refresh
- **THEN** only current PDU data/presentation is eligible to update
- **AND** no related-codec lookup/session/status/meter lifecycle starts
- **AND** codec data remains owned by its own exact room row
