# Change: inventory-switch-port-enrichment

## Why

The current offline equipment-inventory importer reads one organization workbook and publishes schema-v2 canonical records. The inspected network-connection workbook contains current physical connection evidence on sheet `Устройства`: `MAC-адрес`, `IP коммутатора`, and `Порт`.

The diagnostic runtime must continue to consume only canonical JSON and must not parse Excel. To make network location available for future diagnostics without changing existing dispatch, PDU, codec, credential, or GUI behavior, the offline importer needs an explicit second-source reconciliation step and a backward-compatible schema-v3 record shape.

The join cannot use device IP, room text, manufacturer, model, source row order, or the workbook's `Корректная запись` marker. Device IP and room text are mutable or non-authoritative, and `Корректная запись` is explicitly outside the approved contract. Canonical MAC is the only approved cross-source join evidence for this change.

## What Changes

- Add an optional explicitly configured network-connection workbook to the offline importer and CLI/API configuration.
- Use only sheet `Устройства` from that workbook.
- Require exact headers `MAC-адрес`, `IP коммутатора`, and `Порт` when the second source is supplied.
- Ignore sheet `Изменения` completely.
- Ignore `Корректная запись` completely: it is not required, does not filter rows, does not create issues, and does not affect canonical output or identity.
- Normalize network `MAC-адрес` with the existing canonical MAC normalizer and reconcile it against canonical primary-workbook `mac_address`.
- Enrich only unambiguous one-primary-record/one-distinct-network-connection matches.
- Add schema-v3 nullable fields:

```text
switch_ip_address
switch_port
```

- Include both fields in deterministic schema-v3 snapshot identity.
- Keep valid schema-v1 and schema-v2 snapshots loadable, adapting absent switch fields to null.
- Keep existing one-workbook conversion supported; without a network source it continues to publish schema v2. When a network source is explicitly supplied and valid, the importer publishes schema v3. A supplied but invalid network source must fail safely rather than silently downgrade.
- Add focused synthetic regression coverage and update the equipment-inventory runbook.

## Impact

Affected specification:

- `equipment-inventory-snapshot`

Expected implementation areas:

- `core/equipment_inventory.py`
- `tools/import_equipment_inventory.py`
- `tests/test_equipment_inventory.py`
- an optional focused network-enrichment test module if clearer than extending the existing module
- `docs/equipment-inventory-runbook.md`
- change-specific implementation and validation evidence

The generated production workbook inputs and `equipment_inventory.local.json` remain deployment-local operational data outside Git.

This change does not add the standalone converter GUI, Qt worker lifecycle, file pickers, progress UI, issue-table UI, report export, persistent recent paths, automatic file watching, switch diagnostics, SNMP/SSH access, switch-port status checks, or display of switch data in the main diagnostic GUI. Those remain separate future work.

This change also does not modify diagnostic dispatch, credential selection, PDU-to-room-to-codec resolution, related-codec status, handlers, controllers, workers, transport retry, device commands, existing inventory query APIs, production credentials, or Graphify artifacts.
