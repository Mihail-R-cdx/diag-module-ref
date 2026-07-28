# Change: equipment-room-vip-context

## Why

The organization workbook already contains a room VIP flag, but the existing Excel-to-JSON inventory conversion contract does not publish it. As a result, diagnostic equipment screens cannot show whether the resolved room is VIP.

The PDU screen already renders room characteristics after an accepted refresh, while other equipment screens do not currently render a shared room-information block. The importer also requires explicit path arguments and has no repository-safe configuration variables for the absolute workbook and JSON paths used in local operation.

## What Changes

- extend the canonical equipment inventory snapshot with nullable room VIP state;
- map the authoritative workbook column `VIP оборудование` into the canonical snapshot through explicit closed normalization of confirmed boolean, `ИСТИНА`, `ЛОЖЬ`, and blank values;
- preserve compatibility with existing schema-v1 snapshots while publishing new snapshots as schema v2;
- resolve room address and VIP state for the currently selected equipment by exact inventory IP identity without network I/O;
- add a visually prominent VIP line above the existing PDU room-characteristics block;
- add a shared room-information block at the bottom of every other equipment page, showing room address and VIP state;
- clear or supersede room context when equipment model/IP context changes so stale room data is never rendered;
- add converter configuration variables that resolve the Excel source and JSON output to absolute `Path` values without committing user-specific paths;
- retain command-line path overrides for repeatable testing and automation.

## Impact

Affected specifications:

- `equipment-inventory-snapshot`
- `diagnostic-application-shell`
- `pdu-room-codec-enrichment`

Expected implementation areas:

- `core/equipment_inventory.py`
- `tools/import_equipment_inventory.py`
- room-context resolution/presentation modules
- PDU and non-PDU GUI screens/controllers
- focused importer, inventory, resolver, lifecycle, and GUI tests
- `docs/equipment-inventory-runbook.md`

The real organization workbook and generated production snapshot remain deployment-local operational data and must not be committed. `graphify-out/` is outside this change.
