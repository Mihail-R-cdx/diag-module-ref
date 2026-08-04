# Change: equipment-page-inventory-context

## Why

Canonical equipment-inventory schema v3 already carries nullable `switch_ip_address` and `switch_port` for each device after the approved MAC-only reconciliation. The runtime loader exposes both fields through immutable `EquipmentRecord` objects, but the current root contract treats them as non-authoritative metadata and the diagnostic GUI does not render them.

Operators need the connected switch IP address and switch port in the existing device-information section of every supported equipment page. This is inventory context, not data observed from the device itself, so its visibility must not depend on a successful handler request, worker result, transport, credential attempt, or device capability.

The codec page also violates the already approved shared room-information contract during the normal diagnostic rebuild lifecycle. The application initially attaches the shell-owned `RoomInformationBlock`. `CodecScreen.update_parameters_display()` then removes every layout widget, hides it, and schedules it for Qt deferred deletion through `deleteLater()`, including the shared room block. The diagnostic-start path already republishes room context after the rebuild, but `_ensure_shared_room_block()` sees that the pending-deletion block still has a parent and incorrectly accepts it as the current live block. The publication therefore updates an object already scheduled for deletion; when `QEvent.DeferredDelete` is processed, the room block disappears on the next event-loop turn.

## What Changes

- Rename the existing inventory requirement from `Schema-v3 switch fields are passive runtime data in this change` to `Schema-v3 switch fields are non-authoritative runtime inventory metadata`, then place the complete updated contract under the new requirement name.
- Display two inventory-backed rows in the existing device-information card on every registered equipment page:
  - `IP коммутатора`
  - `Порт коммутатора`
- Resolve the rows in the application/composition layer from the one unambiguous canonical inventory record for the current normalized device IP.
- Keep the two values independent: a unique partial schema-v3 connection displays the available field and `—` for the unavailable field.
- Render `—` for schema-v1/schema-v2 snapshots, null fields, unavailable inventory, no matching record, or ambiguous device IP without turning a valid device diagnostic into an error.
- Preserve switch metadata as informational presentation only. It does not authorize model dispatch, credential selection, fallback, handler acquisition, transport behavior, room resolution, related-codec selection, device control, or switch network I/O.
- Make codec rebuild ownership explicit: `CodecScreen.update_parameters_display()` removes and recreates only codec-owned widgets and SHALL NOT hide or schedule the shell-owned room block for deferred deletion.
- Ensure every codec rebuild leaves exactly one live shared room-information block at the bottom and republishes the current room address/VIP context without waiting for device network success.
- Add regression coverage that flushes Qt deferred-deletion events after every tested rebuild before asserting the final room-block state.
- Add registry-wide and lifecycle coverage for every supported page, partial and unavailable inventory values, stale context rejection, repeated codec rebuilds, and the real codec refresh path.

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
