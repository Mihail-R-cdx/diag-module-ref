## 1. Source contract and schema-v4 preparation

- [ ] 1.1 Before implementation, read `RULES.md` and `docs/equipment-inventory-runbook.md`, confirm the implementation branch is based on the current published feature branch HEAD, and preserve unrelated work.
- [ ] 1.2 Add the exact primary source mapping `Адрес комнаты -> room_address`; do not add aliases, fuzzy header matching, or inferred address sources.
- [ ] 1.3 Make the `Адрес комнаты` header mandatory for current primary-source preflight/conversion while keeping each row value nullable. Missing or ambiguous header discovery is fatal; blank cells normalize to null.
- [ ] 1.4 Keep `ID комнаты`/`room_id` as the only room identity authority. Keep `room_name`, `room_address`, and `room_vip` as per-record display metadata only.
- [ ] 1.5 Remove importer room-display conflict authority for schema-v4 publication: differing same-room `room_name` or `room_vip` values must not produce room-display conflict issues, and no `room_address` conflict issue may be introduced.

## 2. Unified schema-v4 importer output

- [ ] 2.1 Change successful primary-only conversion to publish `schema_version = 4` rather than schema v2.
- [ ] 2.2 Change successful primary-plus-network conversion to publish `schema_version = 4` rather than schema v3.
- [ ] 2.3 Define the exact schema-v4 record shape as all historical canonical fields plus `room_vip`, `room_address`, `switch_ip_address`, and `switch_port`.
- [ ] 2.4 Ensure every schema-v4 record contains all declared v4 keys even when values are null.
- [ ] 2.5 In primary-only mode, set both switch fields to null for every record; do not omit them and do not synthesize network evidence.
- [ ] 2.6 Preserve the existing optional network-source configuration priority, exact worksheet/header contract, MAC-only reconciliation, partial-candidate semantics, ambiguity handling, and ignored network evidence.
- [ ] 2.7 Preserve fail-closed network configuration: an explicitly configured invalid/unreadable network source remains fatal and must not downgrade to primary-only publication.
- [ ] 2.8 Change combined preflight to build, identify, and validate an in-memory schema-v4 candidate without publication.
- [ ] 2.9 Keep canonical `source_row_count` as the primary workbook row count and keep network row counters/report metadata outside canonical identity.

## 3. Runtime loader and immutable record model

- [ ] 3.1 Extend the runtime immutable equipment record with nullable `room_address` without adding an address index.
- [ ] 3.2 Keep valid schema v1 loading strict and adapt successful records to `room_vip = null`, `room_address = null`, `switch_ip_address = null`, and `switch_port = null`.
- [ ] 3.3 Keep valid schema v2 loading strict and adapt successful records to source `room_vip`, `room_address = null`, and null switch fields.
- [ ] 3.4 Keep valid schema v3 loading strict and adapt successful records to source `room_vip` and switch fields with `room_address = null`.
- [ ] 3.5 Add strict schema-v4 loading with exact declared record fields and nullable validation for `room_address` and the existing v4 nullable fields.
- [ ] 3.6 Reject missing, extra, or hybrid fields in any declared supported version as `INVALID_SNAPSHOT`; do not repair malformed snapshots.
- [ ] 3.7 Keep undeclared future schema versions classified as `UNSUPPORTED_SCHEMA` and preserve the existing no-partial-publication load contract.

## 4. Deterministic identity and publication

- [ ] 4.1 Compute schema-v4 `snapshot_id` from the exact canonical payload containing only `schema_version` and sorted canonical `records`.
- [ ] 4.2 Ensure `room_address`, `room_vip`, `switch_ip_address`, and `switch_port` participate in v4 identity because they are canonical record fields.
- [ ] 4.3 Keep generation metadata, structured report metadata, and row counters outside deterministic snapshot identity.
- [ ] 4.4 Validate the complete schema-v4 candidate through the runtime loader before publication.
- [ ] 4.5 Preserve atomic output replacement: any fatal source, candidate, identity, or publication failure leaves the previous valid output intact.

## 5. Import diagnostics and room-display metadata

- [ ] 5.1 Preserve per-record normalized `room_name`, `room_address`, and `room_vip` values without cross-record reconciliation.
- [ ] 5.2 Remove importer diagnostics whose only meaning is conflicting non-null `room_name` values under one `room_id`.
- [ ] 5.3 Remove importer `ROOM_VIP_CONFLICT` generation for differing same-room VIP values while preserving normal row-level `INVALID_ROOM_VIP` handling for unsupported source cell values.
- [ ] 5.4 Do not add `ROOM_ADDRESS_CONFLICT` or another same-room address reconciliation diagnostic.
- [ ] 5.5 Preserve all other approved importer issue classes, safe diagnostic boundaries, multiplicity, model recognition, authoritative identity, and source-row accounting.

## 6. Focused regression coverage

- [ ] 6.1 Test exact `Адрес комнаты` mapping and canonical NFC/trim normalization.
- [ ] 6.2 Test a blank room-address cell becomes `room_address = null` without making the row fatal.
- [ ] 6.3 Test missing or ambiguous `Адрес комнаты` header is fatal for primary preflight/conversion and preserves a previous valid output.
- [ ] 6.4 Test primary-only conversion publishes schema v4 with null switch fields on every record.
- [ ] 6.5 Test valid two-source conversion publishes schema v4 with existing MAC-only switch enrichment semantics.
- [ ] 6.6 Test an explicitly configured network-source failure does not downgrade to primary-only schema-v4 publication.
- [ ] 6.7 Test combined preflight reports schema version 4, validates the candidate, and publishes no output.
- [ ] 6.8 Test schema-v4 exact shape: all declared fields required as keys; extra or missing keys fail as `INVALID_SNAPSHOT`.
- [ ] 6.9 Test changing only `room_address` changes deterministic schema-v4 `snapshot_id`.
- [ ] 6.10 Test valid historical v1/v2/v3 snapshots remain loadable and expose `room_address = null` without rewriting the source snapshot.
- [ ] 6.11 Test hybrid historical records remain invalid and an undeclared future schema remains `UNSUPPORTED_SCHEMA`.
- [ ] 6.12 Test differing same-room `room_name`, `room_address`, and `room_vip` values preserve all records and do not emit importer room-display conflict issues.
- [ ] 6.13 Test row-level unsupported non-blank `VIP оборудование` still produces `INVALID_ROOM_VIP`; removing room-wide conflict checks must not weaken cell-level validation.
- [ ] 6.14 Test normal runtime inventory loading remains independent of `openpyxl` or any spreadsheet parser.

## 7. Documentation and implementation boundaries

- [ ] 7.1 Update `docs/equipment-inventory-runbook.md` to describe schema v4 as the only newly generated format, the exact `Адрес комнаты` mapping, strict v1-v4 loader adaptation, and the removal of importer room-display conflict diagnostics.
- [ ] 7.2 Keep real organization workbooks and generated `equipment_inventory.local.json` outside Git; use only synthetic fixtures in tests.
- [ ] 7.3 Do not implement room-tree GUI, room-cycle orchestration, per-record diagnostic screens, related-device network I/O, live polling, device mutations, or credential-policy changes in this change.

## 8. Validation and handoff

- [ ] 8.1 Run focused equipment-inventory/importer tests covering schema v4, address mapping, historical loading, identity, preflight, and network enrichment.
- [ ] 8.2 Run the full offline test suite with `python -m unittest discover -s tests -p "test_*.py"`.
- [ ] 8.3 Run `.\openspec.cmd validate equipment-inventory-v4-room-metadata --strict`.
- [ ] 8.4 Run `.\openspec.cmd validate --all --strict`.
- [ ] 8.5 Run `git diff --check` and `git diff --cached --check`.
- [ ] 8.6 Synchronize this task list with implementation evidence without marking independent validation or archive work complete prematurely.
- [ ] 8.7 Create and push one focused implementation commit before requesting independent validation; the implementation session must not issue its own final `APPROVE`.
- [ ] 8.8 Independent validation must use a clean detached worktree from the current remote feature HEAD and must perform a disposable archive-applicability check because this change modifies existing root requirements.
