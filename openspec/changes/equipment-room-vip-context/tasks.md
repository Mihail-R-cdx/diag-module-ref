# Tasks: equipment-room-vip-context

## 1. Source contract and schema

- [x] 1.1 Use the confirmed exact workbook header `VIP оборудование` and confirmed values `ИСТИНА`, `ЛОЖЬ`, and blank without committing or exposing organization data.
- [x] 1.2 Add schema-v2 `room_vip` to the canonical equipment record and deterministic snapshot identity.
- [x] 1.3 Preserve schema-v1 runtime loading with adapted `room_vip = null`.
- [x] 1.4 Add strict validation for schema-v2 boolean-or-null VIP values and reject unapproved record fields.

## 2. Importer and local path configuration

- [x] 2.1 Map the exact `VIP оборудование` source column and implement the closed mapping for Excel booleans, exact case-insensitive `истина`/`ложь`, blank, and invalid non-blank values.
- [x] 2.2 Report structured `INVALID_ROOM_VIP` and `ROOM_VIP_CONFLICT` issues without dumping source rows.
- [x] 2.3 Apply the normative room-wide VIP aggregation table: all-null, true-plus-null, false-plus-null, and true-plus-false conflict.
- [x] 2.4 Add `SOURCE_XLSX_PATH` and `OUTPUT_JSON_PATH` as resolved absolute `Path` configuration variables.
- [x] 2.5 Support `DIAG_INVENTORY_XLSX` and `DIAG_INVENTORY_JSON` while retaining explicit CLI overrides and directly callable import functions.
- [x] 2.6 Ensure fatal import or path configuration failure leaves the previous production snapshot intact.

## 3. Shared room-context resolution

- [x] 3.1 Add a pure application-owned resolver for exact equipment-IP to room context.
- [x] 3.2 Preserve duplicate-IP ambiguity before device-kind filtering and prohibit first-match selection.
- [x] 3.3 Resolve room address and VIP only from all records sharing authoritative `room_id`.
- [x] 3.4 Implement the exact aggregation outcomes `NO_DATA`, `VIP_TRUE`, `VIP_FALSE`, and `CONFLICT`, treating null as missing rather than contradictory evidence.
- [x] 3.5 Return structured missing, ambiguous, and conflict outcomes suitable for safe inline presentation.
- [x] 3.6 Compose the existing PDU enrichment with the shared room context without weakening related-codec lifecycle or credential contracts.

## 4. GUI presentation and lifecycle

- [x] 4.1 Add one reusable room-information presentation model/widget.
- [x] 4.2 Route every registered equipment page through a centralized equipment-page shell or equivalent shared layout boundary.
- [x] 4.3 Add a prominent VIP line above the existing PDU room-characteristics block.
- [x] 4.4 Add the bottom room-information block automatically to every registered non-PDU page and exclude PDU only through explicit registry classification.
- [x] 4.5 Create one application-owned non-PDU room-context generation when model, normalized IP, page, credential, or accepted snapshot context changes.
- [x] 4.6 Resolve non-PDU room context from inventory without waiting for device refresh and keep it available when device refresh fails.
- [x] 4.7 Ensure device start/progress/result/error/finished callbacks cannot rerun, republish, clear, or restore room context.
- [x] 4.8 Bind any asynchronous room publication to `(model, normalized_ip, snapshot_id, page_context, generation)` and reject stale results.
- [x] 4.9 Ensure inventory failures never change device diagnostic success authority or open automatic modal connection errors.

## 5. Tests and documentation

- [x] 5.1 Add importer tests for Excel boolean true/false, exact case-insensitive `ИСТИНА`/`ЛОЖЬ`, blank, invalid non-blank, missing-column, all-null, true-plus-null, false-plus-null, repeated-equal, and true-plus-false conflict cases.
- [x] 5.2 Add loader and snapshot-identity tests for schema v1 compatibility and schema v2 strictness.
- [x] 5.3 Add resolver tests for exact match, missing room, no room records, duplicate IP, address conflict, all VIP aggregation outcomes, and unavailable inventory.
- [x] 5.4 Add a registry enumeration test proving every registered non-PDU page receives the shared block and every PDU registration uses dedicated placement.
- [x] 5.5 Add GUI lifecycle tests for selecting a new IP without refresh, failed device refresh with available room context, old refresh completion after IP change, visible VIP emphasis, and safe unavailable states.
- [x] 5.6 Add asynchronous publication tests that vary model, normalized IP, snapshot ID, page context, and generation before result delivery.
- [x] 5.7 Add path-resolution tests for CLI, environment, repository-safe default, and missing source configuration.
- [x] 5.8 Update `docs/equipment-inventory-runbook.md` with schema v2, exact `VIP оборудование` mapping, confirmed value normalization and aggregation, path configuration, centralized page coverage, and the non-PDU publication lifecycle.

## 6. Validation and publication

- [x] 6.1 Run focused tests for importer, inventory, resolver, PDU enrichment, page registry/shell, and equipment screens.
- [x] 6.2 Run the complete offline test suite.
- [x] 6.3 Run `./openspec.cmd validate equipment-room-vip-context --strict` using the repository-local wrapper on Windows as `.\openspec.cmd validate equipment-room-vip-context --strict`.
- [x] 6.4 Run `.\openspec.cmd validate --all --strict`.
- [x] 6.5 Run `git diff --check` and verify no workbook, production snapshot, secrets, user-specific paths, or `graphify-out/` changes are included.
- [ ] 6.6 Commit and push implementation evidence before independent validation.
