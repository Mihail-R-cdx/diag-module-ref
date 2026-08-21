## ADDED Requirements

### Requirement: Supported device diagnostics expose bounded room one-shot acquisition

Every exact application model already supported by the production diagnostic dispatch SHALL expose a room-compatible read-only one-shot acquisition through the application-owned model capability registry when that model is eligible for automatic room diagnostics.

The room adapter SHALL reuse the model's approved handler/controller/worker transport and parser/normalization semantics rather than reimplementing protocol logic in the room orchestrator. Existing exact model identity SHALL be preserved, including distinct `CloudLink Bar 310` and `CloudLink Box 310` application identities even where they share handler implementation.

One-shot room acquisition SHALL terminate persistent diagnostic behavior after the required authoritative snapshot is obtained. A successful automatic room acquisition SHALL NOT leave model polling, keepalive, live meters, or reusable diagnostic network sessions running after the adapter's cleanup-complete boundary.

#### Scenario: CloudLink Box room diagnostic preserves exact identity

- **GIVEN** a room row has exact canonical model `CloudLink Box 310`
- **WHEN** its one-shot adapter uses the shared CloudLink 310 handler implementation
- **THEN** the operation context and accepted row state remain exactly `CloudLink Box 310`
- **AND** it is not relabeled or retried as `CloudLink Bar 310`

#### Scenario: Continuous diagnostic path is adapted to one shot

- **WHEN** a supported model normally uses polling, keepalive, or another persistent read lifecycle
- **AND** the model is acquired by the automatic room cycle
- **THEN** the adapter accepts only the required one-shot final diagnostic snapshot
- **AND** persistent diagnostic activity is stopped/released before room cleanup completion

### Requirement: Room one-shot acquisition preserves approved model-specific usable result semantics

A room adapter SHALL preserve the existing distinction between authoritative primary diagnostic data and optional enrichment. When a current approved model-specific diagnostic contract defines primary data as usable despite optional enrichment failure, the adapter SHALL return usable final success with a structured safe warning rather than converting the result to total failure.

When no authoritative final diagnostic data is available, the adapter SHALL return terminal failure rather than emitting an empty/technical-only result as successful room state. Partial/intermediate results SHALL remain explicitly non-final.

#### Scenario: Polycom optional enrichment is unavailable

- **WHEN** Polycom authoritative HTTPS diagnostic status succeeds and optional SSH enrichment fails under the existing approved semantics
- **THEN** the room adapter may return usable final success with warning
- **AND** the authoritative HTTPS data remains available to the exact row
- **AND** the optional failure is not treated as credential-retry authority

#### Scenario: PCS4i outlet-name enrichment is unavailable

- **WHEN** PCS4i authoritative Telnet outlet status succeeds but optional HTTP outlet-name enrichment fails
- **THEN** the room adapter may return usable final success with warning and safe fallback names under the existing model contract
- **AND** the Telnet status is not represented as a failed device acquisition

#### Scenario: No usable diagnostic payload exists

- **WHEN** a model path completes without any authoritative final diagnostic payload
- **THEN** the room adapter returns terminal failure
- **AND** it does not publish a successful row containing only technical context such as IP/profile metadata

### Requirement: Automatic room PDU acquisition remains independent from related-codec enrichment

Aten PE8208AV and Extron IPL T PCS4i automatic room one-shot diagnostics SHALL return only the PDU row's own accepted diagnostic data through the room adapter boundary. The automatic room acquisition SHALL NOT invoke or publish the legacy application boundary whose semantic meaning is an accepted current **user PDU refresh** for `pdu-room-codec-enrichment`.

The related codec, when present as a canonical room record, SHALL be diagnosed only by its own room-row adapter at its deterministic queue position. PDU result data SHALL NOT become room-codec diagnostic authority.

#### Scenario: Automatic Aten room row succeeds

- **WHEN** automatic room polling obtains accepted Aten PDU status
- **THEN** the Aten row receives that PDU diagnostic state
- **AND** no related-codec enrichment starts as a side effect

#### Scenario: Automatic PCS4i room row succeeds

- **WHEN** automatic room polling obtains accepted PCS4i outlet status
- **THEN** the PCS4i row receives that PDU diagnostic state
- **AND** no related-codec enrichment starts as a side effect

### Requirement: Room diagnostic adapters do not expand supported control surface

Adding a model to the automatic room tree SHALL NOT by itself authorize new state-changing operations, transports, protocol fallbacks, credential sharing, or post-cycle live behavior. In MIH-7 room mode, existing device-specific network-backed controls SHALL remain disabled or unbound both during and after automatic room-cycle completion. Existing control capability in legacy single-device mode SHALL NOT grant room-mode target authority.

Until the separately approved `room-device-interaction-lifecycle` binds an action to the exact current room record, MIH-7 SHALL reject local Refresh, Matrix routing, PDU mutation, codec mutation, auxiliary network reads, live starts, or equivalent reused-screen network intents before handler acquisition or device network I/O. Presentation of a `подключено` row SHALL NOT by itself enable those controls.

#### Scenario: Room scan completes for a controllable device

- **WHEN** a device with existing control capabilities completes automatic room acquisition
- **THEN** MIH-7 has established diagnostic row state only
- **AND** the adapter has not sent a state-changing command
- **AND** existing device network controls remain unavailable in room mode

#### Scenario: Legacy mutation intent is invoked after room completion

- **GIVEN** a supported room row completed automatic acquisition successfully
- **WHEN** a reused legacy Matrix, PDU, codec, or equivalent state-changing intent is invoked before exact-row interaction binding exists
- **THEN** application composition rejects or disables that intent before handler acquisition
- **AND** no mutation or other device network I/O is sent

#### Scenario: Legacy auxiliary or live intent is invoked after room completion

- **GIVEN** room mode has reached a terminal clean or problem outcome
- **WHEN** a reused local Refresh, Call Log/auxiliary read, live/poll start, or equivalent network-backed view intent is invoked
- **THEN** MIH-7 keeps the intent unavailable or rejects it before network I/O
- **AND** a top-level source IP or prior single-device context is not accepted as the row target
