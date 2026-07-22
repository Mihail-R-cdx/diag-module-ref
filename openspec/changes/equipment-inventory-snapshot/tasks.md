## 1. Source contract and preparation

- [ ] 1.1 Read `RULES.md`, confirm the implementation branch is based on the current published `master`, and preserve unrelated work.
- [ ] 1.2 Inspect the real equipment workbook or a sanitized workbook/schema sample before implementing source mapping; record the exact worksheet and source-column mapping and do not guess organization-specific headers.
- [ ] 1.3 Identify authoritative source fields for equipment identity, model, IP address, room identity, room display name, and equipment type.
- [ ] 1.4 Define the source-model/type normalization mapping needed to produce canonical `device_kind` and optional `diagnostic_model` values without fabricating unsupported mappings.
- [ ] 1.5 Define synthetic fixtures covering unique lookup, duplicate IP, missing room, invalid IP, unsupported/unmapped model, and multiple relevant devices in one room.

## 2. Canonical runtime inventory model

- [ ] 2.1 Add the focused runtime inventory boundary in `core/equipment_inventory.py` or an equivalently focused reviewed location.
- [ ] 2.2 Implement immutable canonical record and snapshot representations with the approved fields and explicit `schema_version` / `snapshot_id` metadata.
- [ ] 2.3 Implement deterministic application-root resolution for the default deployment-local `equipment_inventory.local.json` path while allowing tests/callers to supply an explicit path.
- [ ] 2.4 Load canonical snapshots with Python standard-library JSON support and reject unsupported schema versions or invalid canonical shapes with structured safe errors.
- [ ] 2.5 Ensure normal application runtime import of the inventory module does not import or require `openpyxl` or another spreadsheet library.

## 3. Indexed inventory query surface

- [ ] 3.1 Build the IP index once at successful snapshot load as `ip_address -> tuple[EquipmentRecord, ...]` or an equivalent immutable multi-value structure.
- [ ] 3.2 Build the room index once as `room_id -> tuple[EquipmentRecord, ...]`.
- [ ] 3.3 Build the room/device-kind index once as `(room_id, device_kind) -> tuple[EquipmentRecord, ...]` or provide an equivalent indexed lookup without repeated full-record scans.
- [ ] 3.4 Implement ambiguity-preserving query methods equivalent to `find_by_ip`, `find_room_equipment`, and `find_by_room_and_kind`.
- [ ] 3.5 Normalize and validate lookup IP input before index access; invalid input must not fall back to a linear or fuzzy match.
- [ ] 3.6 Preserve duplicate IP matches and multiple same-room device matches in deterministic result order; never return an arbitrary first match as authoritative.

## 4. Offline Excel importer

- [ ] 4.1 Add an offline importer under `tools/` that is not imported by normal application runtime modules.
- [ ] 4.2 Use the inspected explicit workbook/sheet/column mapping to translate source rows into canonical records.
- [ ] 4.3 Normalize blank values, IP addresses, room fields, source model text, `device_kind`, and optional `diagnostic_model` according to the approved source mapping.
- [ ] 4.4 Account for every source row as imported or reported with a structured issue; do not silently drop rows.
- [ ] 4.5 Treat fatal workbook/schema/mapping failures as snapshot-publication blockers.
- [ ] 4.6 Report non-fatal data-quality issues such as missing/invalid IP, missing room, unsupported model, duplicate IP, and multiple relevant room devices without silently correcting or deduplicating them.
- [ ] 4.7 If `openpyxl` or another spreadsheet dependency is added, keep it scoped to importer/development usage and prove normal runtime inventory loading remains independent of it.
- [ ] 4.8 Write the canonical snapshot atomically so a failed import does not replace a previously valid deployment snapshot with a partial file.

## 5. Local-data and observability protection

- [ ] 5.1 Add the deployment-local production snapshot name to `.gitignore` and ensure real organization workbook data is not added to the repository.
- [ ] 5.2 Keep tracked inventory fixtures fully synthetic and free of real organization IP addresses, room identities, equipment IDs, and other operational data.
- [ ] 5.3 Ensure importer and runtime errors identify issue categories and minimal row/record references without dumping full source rows or the complete inventory.
- [ ] 5.4 Confirm canonical snapshots contain only approved runtime fields and do not copy all source Excel columns by default.

## 6. Focused regression coverage

- [ ] 6.1 Test valid canonical JSON loading, unsupported schema version rejection, malformed root/record rejection, and deterministic default-path resolution independent of current working directory.
- [ ] 6.2 Test unique IP lookup and zero-match lookup.
- [ ] 6.3 Test duplicate IP lookup returns every matching record and never silently chooses one.
- [ ] 6.4 Test room and room/device-kind indexes with zero, one, and multiple matches.
- [ ] 6.5 Test records with missing room, missing IP, invalid source IP, and unsupported/unmapped diagnostic model retain the approved explicit unresolved semantics.
- [ ] 6.6 Test importer row accounting and structured fatal versus non-fatal issue behavior with synthetic workbook data.
- [ ] 6.7 Test importer output is deterministic for the same normalized source input and produces a usable snapshot identity.
- [ ] 6.8 Test runtime inventory imports and JSON loading in an environment where the spreadsheet library is unavailable.
- [ ] 6.9 Test production local inventory paths are ignored while synthetic fixtures remain tracked.

## 7. Validation and handoff

- [ ] 7.1 Run focused inventory/importer tests.
- [ ] 7.2 Run `python -m unittest discover -s tests -p "test_*.py"`.
- [ ] 7.3 Run `.\openspec.cmd validate equipment-inventory-snapshot --strict`.
- [ ] 7.4 Run `.\openspec.cmd validate --all --strict`.
- [ ] 7.5 Run `git diff --check`.
- [ ] 7.6 Confirm the change introduces no PDU-to-room orchestration, codec network I/O, codec session reuse, credential-policy changes, or GUI behavior changes.
- [ ] 7.7 Commit and push the implementation/evidence before requesting independent validation; the implementation session must not issue its own final `APPROVE`.
