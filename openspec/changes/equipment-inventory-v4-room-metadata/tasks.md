## 1. Source contract and schema-v4 preparation

- [x] 1.1 Before implementation, read `RULES.md` and `docs/equipment-inventory-runbook.md`, confirm the implementation branch is based on the current published feature branch HEAD, and preserve unrelated work.
- [x] 1.2 Add the exact primary source mapping `Адрес комнаты -> room_address`; do not add aliases, fuzzy header matching, or inferred address sources.
- [x] 1.3 Make the `Адрес комнаты` header mandatory for current primary-source preflight/conversion while keeping each row value nullable. Missing or ambiguous header discovery is fatal; blank cells normalize to null.
- [x] 1.4 Keep `ID комнаты`/`room_id` as the only room identity authority. Keep `room_name`, `room_address`, and `room_vip` as per-record display metadata only.
- [x] 1.5 Remove importer room-display conflict authority for schema-v4 publication: differing same-room `room_name` or `room_vip` values must not produce room-display conflict issues, and no `room_address` conflict issue may be introduced.

## 2. Unified schema-v4 importer output

- [x] 2.1 Change successful primary-only CLI/direct API conversion to publish `schema_version = 4` rather than schema v2.
- [x] 2.2 Change successful primary-plus-network CLI/direct API conversion to publish `schema_version = 4` rather than schema v3.
- [x] 2.3 Define the exact schema-v4 record shape as all historical canonical fields plus `room_vip`, `room_address`, `switch_ip_address`, and `switch_port`.
- [x] 2.4 Ensure every schema-v4 record contains all declared v4 keys even when values are null.
- [x] 2.5 In primary-only mode, set both switch fields to null for every record; do not omit them and do not synthesize network evidence.
- [x] 2.6 Preserve the existing optional network-source configuration priority, exact worksheet/header contract, MAC-only reconciliation, partial-candidate semantics, ambiguity handling, and ignored network evidence.
- [x] 2.7 Preserve fail-closed network configuration: an explicitly configured invalid/unreadable network source remains fatal and must not downgrade to primary-only publication.
- [x] 2.8 Change combined preflight to build, identify, and validate an in-memory schema-v4 candidate without publication.
- [x] 2.9 Keep canonical `source_row_count` as the primary workbook row count and keep network row counters/report metadata outside canonical identity.
- [x] 2.10 Preserve the existing CLI/direct API entry points, GUI-independent importer/domain boundary, and atomic publication semantics while changing only their current output schema to v4.

## 3. Runtime loader and immutable record model

- [x] 3.1 Extend the runtime immutable equipment record with nullable `room_address` without adding an address index.
- [x] 3.2 Keep valid schema v1 loading strict and adapt successful records to `room_vip = null`, `room_address = null`, `switch_ip_address = null`, and `switch_port = null`.
- [x] 3.3 Keep valid schema v2 loading strict and adapt successful records to source `room_vip`, `room_address = null`, and null switch fields.
- [x] 3.4 Keep valid schema v3 loading strict and adapt successful records to source `room_vip` and switch fields with `room_address = null`.
- [x] 3.5 Add strict schema-v4 loading with exact declared record fields and nullable validation for `room_address` and the existing v4 nullable fields.
- [x] 3.6 Reject missing, extra, or hybrid fields in any declared supported version as `INVALID_SNAPSHOT`; do not repair malformed snapshots.
- [x] 3.7 Keep undeclared future schema versions classified as `UNSUPPORTED_SCHEMA` and preserve the existing no-partial-publication load contract.
- [x] 3.8 Preserve switch metadata authority across schema versions: v1/v2 expose loader-adapted null switch fields, v3/v4 expose validated canonical switch fields, and no switch index, dispatch, credential, lifecycle, control, or network-I/O authority is introduced.

## 4. Deterministic identity and publication

- [x] 4.1 Compute schema-v4 `snapshot_id` from the exact canonical payload containing only `schema_version` and sorted canonical `records`.
- [x] 4.2 Ensure `room_address`, `room_vip`, `switch_ip_address`, and `switch_port` participate in v4 identity because they are canonical record fields.
- [x] 4.3 Keep generation metadata, structured report metadata, and row counters outside deterministic snapshot identity.
- [x] 4.4 Validate the complete schema-v4 candidate through the runtime loader before publication.
- [x] 4.5 Preserve atomic output replacement: any fatal source, candidate, identity, or publication failure leaves the previous valid output intact.

## 5. Import diagnostics and room-display metadata

- [x] 5.1 Preserve per-record normalized `room_name`, `room_address`, and `room_vip` values without cross-record reconciliation.
- [x] 5.2 Remove importer diagnostics whose only meaning is conflicting non-null `room_name` values under one `room_id`.
- [x] 5.3 Remove importer `ROOM_VIP_CONFLICT` generation for differing same-room VIP values while preserving normal row-level `INVALID_ROOM_VIP` handling for unsupported source cell values.
- [x] 5.4 Do not add `ROOM_ADDRESS_CONFLICT` or another same-room address reconciliation diagnostic.
- [x] 5.5 Preserve all other approved importer issue classes, safe diagnostic boundaries, multiplicity, model recognition, authoritative identity, and source-row accounting.

## 6. Focused regression coverage

- [x] 6.1 Test exact `Адрес комнаты` mapping and canonical NFC/trim normalization.
- [x] 6.2 Test a blank room-address cell becomes `room_address = null` without making the row fatal.
- [x] 6.3 Test missing or ambiguous `Адрес комнаты` header is fatal for primary preflight/conversion and preserves a previous valid output.
- [x] 6.4 Test primary-only CLI/direct API conversion publishes schema v4 with null switch fields on every record.
- [x] 6.5 Test valid two-source CLI/direct API conversion publishes schema v4 with existing MAC-only switch enrichment semantics.
- [x] 6.6 Test an explicitly configured network-source failure does not downgrade to primary-only schema-v4 publication.
- [x] 6.7 Test combined preflight reports schema version 4, validates the candidate, and publishes no output.
- [x] 6.8 Test schema-v4 exact shape: all declared fields required as keys; extra or missing keys fail as `INVALID_SNAPSHOT`.
- [x] 6.9 Test changing only `room_address` changes deterministic schema-v4 `snapshot_id`.
- [x] 6.10 Test valid historical v1/v2/v3 snapshots remain loadable and expose `room_address = null` without rewriting the source snapshot.
- [x] 6.11 Test hybrid historical records remain invalid and an undeclared future schema remains `UNSUPPORTED_SCHEMA`.
- [x] 6.12 Test differing same-room `room_name`, `room_address`, and `room_vip` values preserve all records and do not emit importer room-display conflict issues.
- [x] 6.13 Test row-level unsupported non-blank `VIP оборудование` still produces `INVALID_ROOM_VIP`; removing room-wide conflict checks must not weaken cell-level validation.
- [x] 6.14 Test normal runtime inventory loading remains independent of `openpyxl` or any spreadsheet parser.
- [x] 6.15 Test switch presentation remains display-only for schema v4, v1/v2 null adaptation remains compatible, and diagnostic dispatch, credentials, lifecycle, control, and network I/O do not gain switch-field authority.

## 7. Documentation and implementation boundaries

- [x] 7.1 Update `docs/equipment-inventory-runbook.md` to describe schema v4 as the only newly generated format, the exact `Адрес комнаты` mapping, strict v1-v4 loader adaptation, and the removal of importer room-display conflict diagnostics.
- [x] 7.2 Keep real organization workbooks and generated `equipment_inventory.local.json` outside Git; use only synthetic fixtures in tests.
- [x] 7.3 Do not implement room-tree GUI, room-cycle orchestration, per-record diagnostic screens, related-device network I/O, live polling, device mutations, or credential-policy changes in this change.

## 8. Validation and handoff

- [x] 8.1 Run focused equipment-inventory/importer tests covering schema v4, address mapping, historical loading, identity, preflight, network enrichment, conversion entry points, and switch metadata authority.
- [x] 8.2 Run the full offline test suite with `python -m unittest discover -s tests -p "test_*.py"`.
- [x] 8.3 Run `.\openspec.cmd validate equipment-inventory-v4-room-metadata --strict`.
- [x] 8.4 Run `.\openspec.cmd validate --all --strict`.
- [x] 8.5 Run `git diff --check` and `git diff --cached --check`.
- [x] 8.6 Synchronize this task list with implementation evidence without marking independent validation or archive work complete prematurely.
- [ ] 8.7 Create and push one focused implementation commit before requesting independent validation; the implementation session must not issue its own final `APPROVE`.
- [ ] 8.8 Independent validation must use a clean detached worktree from the current remote feature HEAD and must perform a disposable archive-applicability check because this change modifies existing root requirements.
