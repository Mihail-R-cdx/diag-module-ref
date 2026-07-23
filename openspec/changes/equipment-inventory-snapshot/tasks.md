## 1. Source contract and preparation

- [x] 1.1 Read `RULES.md`, confirm the implementation branch is based on the current published `master`, and preserve unrelated work.
- [x] 1.2 Use the inspected organization workbook contract documented by this change. Do not guess worksheet semantics or introduce unreviewed aliases for confirmed source columns.
- [x] 1.3 Implement the confirmed schema-v1 source mapping exactly: `SmartRoomID -> record_id`, `ID комнаты -> room_id`, `Название комнаты -> room_name`, `Наименование -> source_model`, `IP -> ip_address`, `MAC -> mac_address`, `Серийный номер -> serial_number`, and `Тип модели -> device_kind`.
- [x] 1.4 Treat `SmartRoomID` as the only authoritative schema-v1 `record_id` source for this workbook. Missing, blank-after-normalization, or duplicate canonical `SmartRoomID` is fatal. Do not generate fallback identity from row number, IP, MAC, serial number, room, model, UUID, timestamp, or another field.
- [x] 1.5 Keep `ID комнаты` authoritative for `room_id`; keep `Название комнаты` display-only unless a future reviewed source contract explicitly changes that rule.
- [x] 1.6 Define the exact `Тип модели` mapping: exact `Video Conference -> video_codec`, exact `БРП -> pdu`, every other value -> `other`. Do not use fuzzy, substring, model-name, manufacturer, or heuristic overrides.
- [x] 1.7 Define the explicit reviewed mapping from supported source manufacturer/model evidence to optional `diagnostic_model`; do not infer a supported application model from approximate text.
- [x] 1.8 Keep `SmartRoomID контроллера` outside schema v1 and runtime indexes. It may be consumed only as importer-side consistency evidence.
- [x] 1.9 Define synthetic fixtures covering the confirmed mappings, fatal identity failures, nullable fields, room/source-model/device-kind inconsistencies, controller-reference inconsistencies, duplicate IP/MAC/serial values, multiple PDU/codecs per room, reordered rows, every runtime load-failure category, and a syntactically valid but content-mismatched `snapshot_id`.

## 2. Canonical runtime inventory model

- [x] 2.1 Add the focused runtime inventory boundary in `core/equipment_inventory.py` or an equivalently focused reviewed location.
- [x] 2.2 Implement immutable schema-v1 records with required `record_id` and `device_kind`, plus nullable `source_model`, `diagnostic_model`, `ip_address`, `mac_address`, `serial_number`, `room_id`, and `room_name`.
- [x] 2.3 Implement deterministic application-root resolution for the deployment-local `equipment_inventory.local.json` path while allowing explicit paths for tests and callers.
- [x] 2.4 Load canonical snapshots with Python standard-library JSON support and expose structured safe failures using `NOT_FOUND`, `UNREADABLE`, `INVALID_FORMAT`, `UNSUPPORTED_SCHEMA`, or `INVALID_SNAPSHOT`; no failed load may partially publish an `EquipmentInventory`.
- [x] 2.5 Reject invalid canonical field types/values and duplicate canonical `record_id` values as `INVALID_SNAPSHOT`; runtime loading must never repair them.
- [x] 2.6 Recompute schema-v1 `snapshot_id` from the actually loaded canonical `schema_version` and `records` with the exact approved canonical digest algorithm before publication; reject any declared/recomputed mismatch as `INVALID_SNAPSHOT`.
- [x] 2.7 Validate canonical `ip_address` and `mac_address` forms while preserving the approved nullable semantics for invalid source values handled by the importer.
- [x] 2.8 Ensure normal application runtime import of the inventory module does not import or require `openpyxl` or another spreadsheet library.

## 3. Indexed inventory query surface

- [x] 3.1 Build the IP index once at successful load as `ip_address -> tuple[EquipmentRecord, ...]` or an equivalent immutable multi-value structure.
- [x] 3.2 Build the room index once as `room_id -> tuple[EquipmentRecord, ...]`.
- [x] 3.3 Build the room/device-kind index once as `(room_id, device_kind) -> tuple[EquipmentRecord, ...]` or an equivalent indexed lookup.
- [x] 3.4 Implement ambiguity-preserving query methods equivalent to `find_by_ip`, `find_room_equipment`, and `find_by_room_and_kind`.
- [x] 3.5 Normalize and validate lookup IP input before index access; invalid input must not fall back to linear, fuzzy, or heuristic matching.
- [x] 3.6 Preserve every duplicate IP match and every same-room same-kind match in deterministic canonical order; never select an arbitrary first record as authoritative.
- [x] 3.7 Make every normal inventory lookup return a result collection containing zero, one, or many records. A valid lookup with no matching IP, no matching room, or no matching room/device-kind pair must return an empty collection rather than `None`, a connection-style error, or an inventory-layer `NOT_FOUND` state; interpretation as `NOT_FOUND`, `RESOLVED`, or `AMBIGUOUS` belongs to later application/composition orchestration.
- [x] 3.8 Do not add runtime indexes for MAC address, serial number, `SmartRoomID контроллера`, or room name without a future reviewed runtime requirement.

## 4. Offline Excel importer

- [x] 4.1 Add an offline importer under `tools/` that is not imported by normal application runtime modules.
- [x] 4.2 Apply the confirmed source-to-canonical mapping exactly and keep organization-specific source-column handling inside the importer boundary.
- [x] 4.3 Normalize `SmartRoomID` into `record_id`; a missing/blank or duplicate canonical `SmartRoomID` is a fatal source-contract issue that blocks the complete new snapshot.
- [x] 4.4 Never synthesize fallback `record_id` for this source and never repair duplicate `SmartRoomID` with suffixes, row numbers, mutable attributes, or first-match selection.
- [x] 4.5 Normalize `ID комнаты` into nullable `room_id` and `Название комнаты` into nullable `room_name`; missing room identity remains non-fatal when required record fields are valid.
- [x] 4.6 Normalize `Наименование` directly into nullable `source_model`; do not reconstruct or overwrite it from `Производитель + Модель`. Manufacturer/model columns may be used only for explicit `diagnostic_model` mapping and consistency diagnostics.
- [x] 4.7 Map exact source `Тип модели` values to the closed `device_kind` vocabulary and map every unmatched value to `other`; do not override this result from recognized model evidence.
- [x] 4.8 Normalize nullable IP, MAC, serial-number, room, and model fields according to schema v1. Invalid optional source data must remain observable without dropping an otherwise representable record.
- [x] 4.9 Distinguish importer diagnostics into at least fatal source-contract issues, non-fatal invalid-field/data-quality issues, and cross-row/source consistency issues. Emit a machine-readable issue code, class, and only minimal safe row/record references.
- [x] 4.10 Detect room consistency issues without correcting source data: same `room_id` with conflicting `room_name`, same `room_name` reused by different `room_id`, and display name present while `room_id` is missing.
- [x] 4.11 Detect optional source-model consistency issues between `Наименование`, `Производитель`, and `Модель` without rewriting canonical `source_model`.
- [x] 4.12 Detect known diagnostic-model/type inconsistencies without overriding authoritative `Тип модели`-derived `device_kind`.
- [x] 4.13 Preserve multiple PDU, multiple video codecs, duplicate IP/MAC/serial values, and other non-identity multiplicity; report relevant data-quality/consistency evidence without deleting records or choosing a winner.
- [x] 4.14 Optionally use `SmartRoomID контроллера` only for non-fatal consistency checks such as conflicting controller references within one room, missing references, or references to absent equipment IDs; do not emit a controller relation into schema v1.
- [x] 4.15 Account for every source equipment row as either a canonical record or a structured issue; no source row may disappear silently.
- [x] 4.16 Produce canonical records in deterministic ascending normalized `record_id` order and compute schema-v1 `snapshot_id` from `schema_version` plus canonical `records`, excluding generation metadata.
- [x] 4.17 Publish the fully validated snapshot atomically so any fatal import failure leaves the previous production snapshot intact and never exposes partial output.
- [x] 4.18 If `openpyxl` or another spreadsheet dependency is added, keep it scoped to importer/development usage and prove normal runtime inventory loading remains independent of it.

## 5. Local-data and observability protection

- [x] 5.1 Add the deployment-local production snapshot name to `.gitignore` and ensure real organization workbook data is not added to the repository.
- [x] 5.2 Keep tracked inventory fixtures fully synthetic and free of real organization IP addresses, room identities, equipment IDs, controller references, and other operational data.
- [x] 5.3 Ensure importer/runtime diagnostics expose only issue class, issue code, minimal row reference, safe `record_id` when available, and a short safe description; do not dump complete source rows or the complete inventory.
- [x] 5.4 Confirm canonical snapshots contain only approved schema-v1 fields and do not copy source-only evidence columns such as `Производитель`, `Модель`, or `SmartRoomID контроллера` by default.

## 6. Focused regression coverage

- [x] 6.1 Test `SmartRoomID` is normalized and used as `record_id`.
- [x] 6.2 Test missing/blank `SmartRoomID` is fatal, creates no fallback identity, blocks publication, and preserves the previous published snapshot.
- [x] 6.3 Test duplicate normalized `SmartRoomID` is fatal, is not suffix-repaired or first-match-selected, and preserves the previous published snapshot.
- [x] 6.4 Test `ID комнаты` maps to `room_id`, `Название комнаты` maps to `room_name`, and devices sharing one `room_id` are returned by the same room index.
- [x] 6.5 Test identical `room_id` with conflicting `room_name` values preserves all canonical records and reports a non-fatal consistency issue without selecting one name as authoritative.
- [x] 6.6 Test identical `room_name` under different `room_id` values does not merge rooms or change authoritative room identity.
- [x] 6.7 Test `room_name` present with missing `ID комнаты` produces `room_id = null`, preserves the record when required fields are valid, and reports the inconsistency/data-quality condition.
- [x] 6.8 Test `Наименование` maps directly to `source_model`; manufacturer/model disagreement may be reported but does not silently rewrite `source_model`.
- [x] 6.9 Test exact `Тип модели = Video Conference` maps to `video_codec`, exact `Тип модели = БРП` maps to `pdu`, and all other values map to `other`.
- [x] 6.10 Test a recognized diagnostic model with an unexpected `Тип модели` does not silently override `device_kind` and may produce a structured consistency issue.
- [x] 6.11 Test multiple PDU or multiple video codecs in one room remain multiple indexed records with zero/one/many semantics and no implicit primary selection.
- [x] 6.12 Test inconsistent `SmartRoomID контроллера` evidence can be reported as non-fatal consistency diagnostics without adding a controller field or index to runtime schema v1.
- [x] 6.13 Test every nullable schema-v1 field may be absent without whole-row drop when `record_id` and `device_kind` remain valid.
- [x] 6.14 Test invalid source IP/MAC and missing serial number retain the approved nullable semantics and produce appropriate non-fatal diagnostics.
- [x] 6.15 Test duplicate IP/MAC/serial values preserve every record and never deduplicate or select a first match.
- [x] 6.16 Test importer diagnostics distinguish fatal source-contract, non-fatal data-quality, and consistency classes while redacting unrelated source-row data.
- [x] 6.17 Test a syntactically valid but stale/wrong declared `snapshot_id` is rejected as `INVALID_SNAPSHOT` after loader recomputation with no partial publication.
- [x] 6.18 Test deterministic canonical ordering and `snapshot_id`, including row reordering and mutable attribute changes that preserve `SmartRoomID`.
- [x] 6.19 Test valid runtime snapshot loading, every structured load-failure category, default-path resolution, and runtime operation without the spreadsheet dependency.
- [x] 6.20 Test production local inventory paths are ignored while synthetic fixtures remain tracked.
- [x] 6.21 Test `find_by_ip` explicitly for zero, one, and many matches: zero returns an empty collection, one returns exactly one record, and many returns every match in deterministic canonical order without converting an ordinary zero-match into `None`, an exception, or a connection-style error.
- [x] 6.22 Test room and room/device-kind lookups return an empty collection for zero matches and preserve one/many result collections; verify the inventory layer does not classify zero/one/many results as `NOT_FOUND`, `RESOLVED`, or `AMBIGUOUS`.

## 7. Validation and handoff

- [x] 7.1 Run focused inventory/importer tests.
- [x] 7.2 Run `python -m unittest discover -s tests -p "test_*.py"`.
- [ ] 7.3 Run `.\openspec.cmd validate equipment-inventory-snapshot --strict`.
- [ ] 7.4 Run `.\openspec.cmd validate --all --strict`.
- [x] 7.5 Run `git diff --check`.
- [x] 7.6 Confirm the implementation introduces no PDU-to-room orchestration, codec network I/O, codec session reuse, credential-policy changes, transport changes, or GUI behavior changes.
- [x] 7.7 Commit and push implementation/evidence before requesting independent validation; the implementation session must not issue its own final `APPROVE`.
