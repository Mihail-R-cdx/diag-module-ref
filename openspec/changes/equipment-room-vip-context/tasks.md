# Tasks: equipment-room-vip-context

## 1. Source contract and schema

- [ ] 1.1 Reconfirm the exact workbook header `VIP` and representative source values against the deployment workbook without committing or exposing organization data.
- [ ] 1.2 Add schema-v2 `room_vip` to the canonical equipment record and deterministic snapshot identity.
- [ ] 1.3 Preserve schema-v1 runtime loading with adapted `room_vip = null`.
- [ ] 1.4 Add strict validation for schema-v2 boolean-or-null VIP values and reject unapproved record fields.

## 2. Importer and local path configuration

- [ ] 2.1 Map the exact `VIP` source column and implement closed explicit normalization.
- [ ] 2.2 Report structured `INVALID_ROOM_VIP` and `ROOM_VIP_CONFLICT` issues without dumping source rows.
- [ ] 2.3 Add `SOURCE_XLSX_PATH` and `OUTPUT_JSON_PATH` as resolved absolute `Path` configuration variables.
- [ ] 2.4 Support `DIAG_INVENTORY_XLSX` and `DIAG_INVENTORY_JSON` while retaining explicit CLI overrides and directly callable import functions.
- [ ] 2.5 Ensure fatal import or path configuration failure leaves the previous production snapshot intact.

## 3. Shared room-context resolution

- [ ] 3.1 Add a pure application-owned resolver for exact equipment-IP to room context.
- [ ] 3.2 Preserve duplicate-IP ambiguity before device-kind filtering and prohibit first-match selection.
- [ ] 3.3 Resolve room address and VIP only from records sharing authoritative `room_id`.
- [ ] 3.4 Return structured missing, ambiguous, and conflict outcomes suitable for safe inline presentation.
- [ ] 3.5 Compose the existing PDU enrichment with the shared room context without weakening related-codec lifecycle or credential contracts.

## 4. GUI presentation and lifecycle

- [ ] 4.1 Add a reusable room-information presentation model/widget.
- [ ] 4.2 Add a prominent VIP line above the existing PDU room-characteristics block.
- [ ] 4.3 Add the room-information block at the bottom of every non-PDU equipment page, showing address and VIP state.
- [ ] 4.4 Clear prior room presentation immediately when model/IP/page/credential context is superseded.
- [ ] 4.5 Reject stale room results and ensure inventory failures never change device diagnostic success authority or open automatic modal connection errors.

## 5. Tests and documentation

- [ ] 5.1 Add importer tests for true, false, blank, invalid, missing-column, and cross-row conflict cases.
- [ ] 5.2 Add loader and snapshot-identity tests for schema v1 compatibility and schema v2 strictness.
- [ ] 5.3 Add resolver tests for exact match, missing room, duplicate IP, address conflict, VIP conflict, and unavailable inventory.
- [ ] 5.4 Add GUI tests for PDU placement, non-PDU placement, visible VIP emphasis, safe unavailable states, and stale-context clearing.
- [ ] 5.5 Add path-resolution tests for CLI, environment, repository-safe default, and missing source configuration.
- [ ] 5.6 Update `docs/equipment-inventory-runbook.md` with schema v2, VIP mapping, path configuration, and shared room-context behavior.

## 6. Validation and publication

- [ ] 6.1 Run focused tests for importer, inventory, resolver, PDU enrichment, and equipment screens.
- [ ] 6.2 Run the complete offline test suite.
- [ ] 6.3 Run `./openspec.cmd validate equipment-room-vip-context --strict` using the repository-local wrapper on Windows as `.\openspec.cmd validate equipment-room-vip-context --strict`.
- [ ] 6.4 Run `.\openspec.cmd validate --all --strict`.
- [ ] 6.5 Run `git diff --check` and verify no workbook, production snapshot, secrets, user-specific paths, or `graphify-out/` changes are included.
- [ ] 6.6 Commit and push implementation evidence before independent validation.
