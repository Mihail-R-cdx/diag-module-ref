# Change: equipment-page-inventory-context

## Why

Canonical equipment-inventory schema v3 already carries nullable `switch_ip_address` and `switch_port` for each device after the approved MAC-only reconciliation. The runtime loader exposes both fields through immutable `EquipmentRecord` objects, but the current root contract intentionally leaves them passive and the diagnostic GUI does not render them.

Operators need the connected switch IP address and switch port in the existing device-information section of every supported equipment page. This is inventory context, not data observed from the device itself, so its visibility must not depend on a successful handler request, worker result, transport, credential attempt, or device capability.

The codec page also violates the already approved shared room-information contract in its normal rebuild path. The application initially attaches the shared bottom room block, but `CodecScreen.update_parameters_display()` removes every widget from the codec content layout and rebuilds only codec-owned cards. During a real refresh this deletes the shell-owned room block, so codec pages lose the room address and VIP status even though the application has already resolved and published them.

## What Changes

- Display two inventory-backed rows in the existing device-information card on every registered equipment page:
  - `IP коммутатора`
  - `Порт коммутатора`
- Resolve the rows in the application/composition layer from the one unambiguous canonical inventory record for the current normalized device IP.
- Keep the two values independent: a unique partial schema-v3 connection displays the available field and `—` for the unavailable field.
- Render `—` for schema-v1/schema-v2 snapshots, null fields, unavailable inventory, no matching record, or ambiguous device IP without turning a valid device diagnostic into an error.
- Preserve switch metadata as informational presentation only. It does not authorize model dispatch, credential selection, fallback, handler acquisition, transport behavior, room resolution, related-codec selection, device control, or switch network I/O.
- Ensure codec parameter-card rebuilds preserve or restore exactly one shared room-information block at the bottom of the codec page and republish the current room address/VIP context without waiting for device network success.
- Add registry-wide and lifecycle regression coverage for every supported page, partial and unavailable inventory values, stale context rejection, repeated codec rebuilds, and the real codec refresh path.

## Impact

Affected specifications:

- `diagnostic-application-shell`
- `equipment-inventory-snapshot`

Expected implementation areas:

- `gui/main_window.py`
- `gui/equipment_pages.py`
- `gui/screens/codec_screen.py`
- `gui/screens/matrix_screen.py`
- `gui/screens/pdu_screen.py`
- `gui/screens/audio_dsp_screen.py`
- focused GUI/inventory presentation tests, including `tests/test_equipment_room_context_gui.py`

The implementation may introduce one focused pure presentation resolver/model if needed, but screens must remain rendering-only and must not query inventory themselves.

This architecture change does not modify production code, tests, root specifications, archived changes, inventory workbooks, generated deployment snapshots, importer reconciliation, schema identity, device handlers/workers/controllers, credentials, transports, or Graphify artifacts.
