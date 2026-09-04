# device-diagnostics-and-control Delta

## MODIFIED Requirements

### Requirement: Limited device control
The GUI SHALL expose as network-capable device controls only operations implemented by the selected device path: codec presentation, audio/microphone operations, supported SIP server actions, Extron routing to output 1, Aten outlet on/off/reboot actions, Aten bulk on/off actions, Extron IPL T PCS4i outlet on/off actions, and Extron IPL T PCS4i bulk on/off actions. Unsupported device actions SHALL not be reported as successful.

A reviewed fixed common dashboard MAY retain a visible local-only affordance for an unsupported codec or PDU operation only when the exact unified application/PDU capability authority explicitly marks that network capability unsupported and the click is resolved locally before room interaction admission. Such an affordance SHALL NOT be represented as an available/supported device network capability, SHALL NOT invalidate LIVE, acquire a handler/session, select credentials, create a mutation generation or perform device network I/O, and SHALL only produce the approved non-secret informational result.

For codec dashboards, the existing codec-specific local-only presentation exception remains limited to the reviewed common codec affordances already approved by the codec presentation contract. For the dedicated common PDU dashboard, the exception is limited to fixed PDU controls required by `diagnostic-ui-presentation`; it does not authorize arbitrary unsupported PDU actions or direct widget-to-handler dispatch.

The existing standalone/shared `PDUScreen` contract remains unchanged by this
change. When that screen renders supported outlet controls for Extron IPL T
PCS4i, it SHALL expose ON and OFF only; REBOOT SHALL NOT be shown as an
operator action on that surface.

PCS4i REBOOT SHALL remain unsupported as a network operation and SHALL NOT
enter the state-changing room lifecycle. Separately, the fixed common **room**
PDU dashboard MAY retain its visible per-outlet `Перезапуск` affordance as
local-only unsupported presentation. That room-dashboard affordance SHALL NOT
extend to, or change the supported-control rendering of, the standalone/shared
`PDUScreen`. Activating the room-dashboard affordance while the common room
lock matrix otherwise permits input SHALL report locally that the command is
unsupported before room interaction admission, with zero LIVE invalidation,
credential selection, handler/session acquisition, mutation generation, device
I/O, or accepted-state mutation. No PCS4i bulk REBOOT and no general PDU bulk
REBOOT control is authorized on either surface.

#### Scenario: Extron routing action
- **WHEN** an operator selects an actionable Extron input/output-1 cell with a connected handler
- **THEN** the handler is asked to route that input to output 1 and the screen schedules a status refresh

#### Scenario: Aten outlet action
- **WHEN** an operator confirms an `on`, `off`, or `reboot` action for an Aten outlet
- **THEN** the application executes the matching handler action through the background PDU command path, reports its outcome, and refreshes after success

#### Scenario: PCS4i outlet action
- **WHEN** an operator confirms an `on` or `off` action for a PCS4i outlet from 1 through 4
- **THEN** the application executes the matching PCS4i handler action through the background PDU command path and reports its outcome

#### Scenario: PCS4i reboot is not available
- **GIVEN** selected device is Extron IPL T PCS4i
- **WHEN** `PDUScreen` renders supported outlet controls
- **THEN** ON is available
- **AND** OFF is available
- **AND** REBOOT is not available to the operator

#### Scenario: PCS4i fixed reboot affordance remains network-unsupported
- **GIVEN** selected exact device is `Extron IPL T PCS4i`
- **AND** the fixed common room PDU dashboard, rather than `PDUScreen`, is otherwise eligible for user input
- **WHEN** the operator activates the visible per-outlet `Перезапуск` affordance
- **THEN** the application reports locally that the command is unsupported
- **AND** REBOOT remains unavailable as a PCS4i network capability
- **AND** no room interaction admission, LIVE invalidation, credential selection, handler/session acquisition, mutation generation, device I/O, or accepted-state mutation starts

#### Scenario: Unsupported SIP update
- **WHEN** a codec handler does not implement SIP server update
- **THEN** the operation reports an unsupported or failed outcome rather than claiming the setting changed

#### Scenario: Fixed codec dashboard shows unsupported affordance
- **GIVEN** the fixed room codec dashboard contains a visual control whose exact-model network capability is explicitly unsupported
- **WHEN** the operator activates that affordance while the common room lock matrix otherwise permits input
- **THEN** the application reports locally that the operation is unsupported
- **AND** the operation is not represented as a supported device capability
- **AND** no handler/session/credential/network interaction begins

#### Scenario: Fixed PDU dashboard shows unsupported affordance
- **GIVEN** the fixed common room PDU dashboard contains a visual control whose exact-model network capability is explicitly unsupported
- **WHEN** the operator activates that affordance while the common room lock matrix otherwise permits input
- **THEN** the application shows an informational result equivalent to `Команда не поддерживается`
- **AND** the operation is not represented as a supported PDU network capability
- **AND** no LIVE invalidation, credential selection, handler/session acquisition, mutation generation or PDU device I/O begins

#### Scenario: Bulk action uses supported individual capability
- **GIVEN** the selected PDU model supports individual ON and OFF operations
- **WHEN** the shared PDU screen renders bulk controls
- **THEN** bulk ON is available only from the ON capability
- **AND** bulk OFF is available only from the OFF capability
- **AND** no bulk REBOOT control is exposed

#### Scenario: Unsupported bulk action is rejected
- **GIVEN** a PDU model does not support the requested individual operation
- **WHEN** a matching bulk operation is submitted programmatically
- **THEN** application dispatch rejects it before handler acquisition
- **AND** no PDU network I/O is started

## ADDED Requirements

### Requirement: Current PDU room-control support matrix is a fixed acceptance oracle

The existing exact application/PDU capability authority SHALL remain the sole runtime support/dispatch authority. For the current `master` baseline, implementation and tests SHALL nevertheless prove the following expected capabilities; this table is test/acceptance data only and SHALL NOT become a second runtime model registry or duplicated GUI support table:

| Exact model | refresh | outlet_on | outlet_off | outlet_reboot | bulk_on | bulk_off |
| --- | --- | --- | --- | --- | --- | --- |
| `Aten PE8208AV` | SUPPORTED | SUPPORTED | SUPPORTED | SUPPORTED | SUPPORTED | SUPPORTED |
| `Extron IPL T PCS4i` | SUPPORTED | SUPPORTED | SUPPORTED | UNSUPPORTED | SUPPORTED | SUPPORTED |

Bulk ON/OFF support is derived from the existing supported individual ON/OFF capability/policy rather than from a new dashboard-owned protocol command. The table SHALL NOT authorize bulk reboot.

If approved source/contracts change before implementation such that this matrix is no longer true, the OpenSpec architecture SHALL be reviewed before implementation silently changes the common dashboard behavior.

#### Scenario: Current PDU capability oracle is checked

- **WHEN** composition/regression tests inspect the two current exact PDU models
- **THEN** their current operation support matches the table above
- **AND** runtime resolution still comes from existing exact PDU capability authority rather than this acceptance table

### Requirement: PDU presentation metadata does not create new device telemetry authority

The common room PDU presentation MAY consume the exact current room record's canonical `serial_number` and `mac_address` for the fixed information card. It SHALL NOT add a PDU protocol read solely to populate those presentation values, and absence SHALL remain absence for presentation as `—`.

Per-outlet current power is not an approved current PDU diagnostic field in this change. The application/handler boundary SHALL NOT add a power polling operation solely because the fixed dashboard contains a `Текущая мощность` column. The presentation placeholder SHALL remain non-authoritative until a later reviewed capability defines a source and lifecycle.

#### Scenario: Dashboard is built with no power capability

- **GIVEN** the current exact PDU capability exposes no authoritative per-outlet power read
- **WHEN** the common PDU dashboard is rendered or locally refreshed under current approved diagnostics
- **THEN** no power-specific handler/session/device request is introduced by this change
- **AND** the presentation uses the approved `—` placeholder
