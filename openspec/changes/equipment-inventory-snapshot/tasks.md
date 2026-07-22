## 1. Source contract and preparation

- [ ] 1.1 Read `RULES.md`, confirm the implementation branch is based on the current published `master`, and preserve unrelated work.
- [ ] 1.2 Inspect the real equipment workbook or a sanitized workbook/schema sample before implementing source mapping; record the exact worksheet and source-column mapping and do not guess organization-specific headers.
- [ ] 1.3 Identify authoritative source fields for equipment identity, model, IP address, room identity, room display name, and equipment type.
- [ ] 1.4 Define and document the schema-v1 `record_id` provenance rule from the inspected source contract: use a normalized authoritative unique equipment ID when available; otherwise use only an explicitly reviewed deterministic derivation from stable source identity fields. Random UUIDs, timestamps, per-import values, and row numbers/order are forbidden unless row order is explicitly authoritative in the reviewed source contract. If no stable unique identity can be defined, block source mapping until architectural review.
- [ ] 1.5 Define the source-model/type normalization mapping needed to produce canonical `device_kind` values from the schema-v1 closed vocabulary `pdu`, `video_codec`, or `other`, plus optional `diagnostic_model` values, without fabricating unsupported mappings.
- [ ] 1.6 Define synthetic fixtures covering unique lookup, duplicate IP, missing room, invalid IP, unsupported/unmapped model, multiple relevant devices in one room, duplicate authoritative/derived `record_id`, reordered source rows, and every structured runtime load-failure category.

## 2. Canonical runtime inventory model

- [ ] 2.1 Add the focused runtime inventory boundary in `core/equipment_inventory.py` or an equivalently focused reviewed location.
- [ ] 2.2 Implement immutable canonical record and snapshot representations for schema v1 with `schema_version` integer `1`, deterministic non-empty string `snapshot_id`, JSON-array `records`, the approved nullable/non-null field types, identifier normalization rules, and the closed `device_kind` vocabulary.
- [ ] 2.3 Implement deterministic application-root resolution for the default deployment-local `equipment_inventory.local.json` path while allowing tests/callers to supply an explicit path.
- [ ] 2.4 Load canonical snapshots with Python standard-library JSON support and expose a structured safe load-failure contract using `NOT_FOUND`, `UNREADABLE`, `INVALID_FORMAT`, `UNSUPPORTED_SCHEMA`, or `INVALID_SNAPSHOT`; no failed load may partially publish an `EquipmentInventory`.
- [ ] 2.5 Reject duplicate canonical `record_id` values and invalid canonical field types/values as `INVALID_SNAPSHOT` rather than silently repairing them at runtime load.
- [ ] 2.6 Ensure normal application runtime import of the inventory module does not import or require `openpyxl` or another spreadsheet library.

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
- [ ] 4.3 Generate each canonical `record_id` strictly from the reviewed source-identity rule: normalize an authoritative unique equipment ID when available, otherwise apply only the approved deterministic derivation from stable source identity fields. Do not use random/per-import identity, timestamps, or non-authoritative row position.
- [ ] 4.4 Treat duplicate normalized authoritative IDs, collisions from the approved deterministic derivation, or absence of any reviewed stable unique identity rule as fatal source-contract failures. Do not silently append suffixes or invent another identity rule during import.
- [ ] 4.5 Normalize blank values, IP addresses, room fields, source model text, `device_kind`, and optional `diagnostic_model` according to the approved source mapping and schema-v1 canonical normalization rules.
- [ ] 4.6 Account for every source row as imported or reported with a structured issue; do not silently drop rows.
- [ ] 4.7 Treat fatal workbook/schema/mapping/identity failures as snapshot-publication blockers.
- [ ] 4.8 Report non-fatal data-quality issues such as missing/invalid IP, missing room, unsupported model, duplicate IP, and multiple relevant room devices without silently correcting or deduplicating them.
- [ ] 4.9 If `openpyxl` or another spreadsheet dependency is added, keep it scoped to importer/development usage and prove normal runtime inventory loading remains independent of it.
- [ ] 4.10 Produce canonical records in deterministic ascending normalized `record_id` order and compute schema-v1 `snapshot_id` deterministically from the canonical identity content (`schema_version` plus canonical `records`), excluding optional generation metadata such as timestamps.
- [ ] 4.11 Publish the fully validated canonical snapshot atomically so any importer failure before successful publication leaves the previously published snapshot intact and never exposes partial output at the production snapshot path.

## 5. Local-data and observability protection

- [ ] 5.1 Add the deployment-local production snapshot name to `.gitignore` and ensure real organization workbook data is not added to the repository.
- [ ] 5.2 Keep tracked inventory fixtures fully synthetic and free of real organization IP addresses, room identities, equipment IDs, and other operational data.
- [ ] 5.3 Ensure importer and runtime errors identify issue categories and minimal row/record references without dumping full source rows or the complete inventory.
- [ ] 5.4 Confirm canonical snapshots contain only approved runtime fields and do not copy all source Excel columns by default.

## 6. Focused regression coverage

- [ ] 6.1 Test valid schema-v1 JSON loading and exact structured load-failure classification for absent file (`NOT_FOUND`), unreadable file (`UNREADABLE`), invalid JSON (`INVALID_FORMAT`), unsupported schema version (`UNSUPPORTED_SCHEMA`), and invalid canonical root/records including duplicate `record_id` (`INVALID_SNAPSHOT`).
- [ ] 6.2 Test every load failure publishes no partial `EquipmentInventory` and leaves any previously published inventory instance outside the loader unchanged.
- [ ] 6.3 Test deterministic default-path resolution independent of current working directory.
- [ ] 6.4 Test unique IP lookup and zero-match lookup.
- [ ] 6.5 Test duplicate IP lookup returns every matching record and never silently chooses one.
- [ ] 6.6 Test room and room/device-kind indexes with zero, one, and multiple matches, including exact `video_codec` vocabulary use.
- [ ] 6.7 Test records with missing room, missing IP, invalid source IP, and unsupported/unmapped diagnostic model retain the approved explicit unresolved semantics.
- [ ] 6.8 Test importer row accounting and structured fatal versus non-fatal issue behavior with synthetic workbook data.
- [ ] 6.9 Test identical normalized logical source inventory produces the same `record_id` values, deterministic canonical record order, and `snapshot_id`; changed canonical content produces a different `snapshot_id`; optional generation metadata does not affect snapshot identity.
- [ ] 6.10 Test reordering source workbook rows does not change `record_id`, canonical record order, or `snapshot_id` when source row order is not part of the reviewed authoritative source contract.
- [ ] 6.11 Test duplicate normalized authoritative IDs and collisions in an approved derived-identity rule are fatal and are not repaired by arbitrary suffixes.
- [ ] 6.12 Test a failed import before complete publication preserves the previous valid production snapshot byte-for-byte and leaves no partial output exposed at the production snapshot path.
- [ ] 6.13 Test runtime inventory imports and JSON loading in an environment where the spreadsheet library is unavailable.
- [ ] 6.14 Test production local inventory paths are ignored while synthetic fixtures remain tracked.

## 7. Validation and handoff

- [ ] 7.1 Run focused inventory/importer tests.
- [ ] 7.2 Run `python -m unittest discover -s tests -p "test_*.py"`.
- [ ] 7.3 Run `.\openspec.cmd validate equipment-inventory-snapshot --strict`.
- [ ] 7.4 Run `.\openspec.cmd validate --all --strict`.
- [ ] 7.5 Run `git diff --check`.
- [ ] 7.6 Confirm the change introduces no PDU-to-room orchestration, codec network I/O, codec session reuse, credential-policy changes, or GUI behavior changes.
- [ ] 7.7 Commit and push the implementation/evidence before requesting independent validation; the implementation session must not issue its own final `APPROVE`.
