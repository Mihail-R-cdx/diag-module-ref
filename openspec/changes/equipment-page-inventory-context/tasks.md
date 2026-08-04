# Tasks: Equipment page inventory context

## 1. Confirm current authority and implementation context

- [ ] 1.1 Before implementation, read current `RULES.md` and then `docs/equipment-inventory-runbook.md`.
- [ ] 1.2 Read the approved root specifications `equipment-inventory-snapshot` and `diagnostic-application-shell`, including the renamed switch-metadata requirement and the shared non-PDU room-presentation contract.
- [ ] 1.3 Read current `core/equipment_inventory.py`, `core/room_context.py`, `gui/equipment_pages.py`, `gui/main_window.py`, all four registered equipment screens, and focused inventory/room GUI tests.
- [ ] 1.4 Fetch current `origin/master` and `origin/agent/equipment-page-inventory-context`, record both full SHAs and subjects, confirm PR base/head/Draft/mergeability, and inspect commits added after the approved architecture HEAD.
- [ ] 1.5 Confirm the implementation branch still contains the approved architecture and no newer root-spec or page-registry change conflicts with it.

## 2. Preserve the renamed inventory contract

- [ ] 2.1 Preserve the OpenSpec rename from `Schema-v3 switch fields are passive runtime data in this change` to `Schema-v3 switch fields are non-authoritative runtime inventory metadata`.
- [ ] 2.2 Keep the full updated requirement under the new header in `MODIFIED Requirements`.
- [ ] 2.3 Do not introduce any additional runtime authority for switch fields beyond application-owned, display-only equipment-page presentation.

## 3. Add application-owned switch presentation

- [ ] 3.1 Resolve switch connection presentation only from the current immutable `EquipmentInventory` and existing exact `find_by_ip()` zero/one/many semantics.
- [ ] 3.2 Publish `switch_ip_address` and `switch_port` independently so a unique partial candidate keeps its available value.
- [ ] 3.3 Render null, unavailable, invalid-IP, not-found, and ambiguous outcomes as neutral unavailable values without modal errors or diagnostic failure.
- [ ] 3.4 Do not narrow multiple records by selected model, `device_kind`, MAC, room, completeness, row order, or presentation state.
- [ ] 3.5 Keep screens rendering-only; they must not receive inventory, query records, interpret multiplicity, or decide stale-result acceptance.
- [ ] 3.6 Use an application-owned binding/generation covering exact model, normalized IP, inventory snapshot identity, and registered page context.
- [ ] 3.7 Invalidate and republish on model, IP, page, or inventory snapshot/availability change.
- [ ] 3.8 Keep publication independent of reachability, credentials, handler acquisition, worker/controller result, request success/error/completion, interactive actions, and device control.
- [ ] 3.9 Ensure device result payloads cannot overwrite canonical inventory-backed switch values.

## 4. Add rows to every registered equipment page

- [ ] 4.1 Add exactly one `IP коммутатора` row and one `Порт коммутатора` row to `CodecScreen`'s existing `Основная информация` card.
- [ ] 4.2 Add the same rows to `MatrixScreen`, `PDUScreen`, and `AudioDSPScreen` inside each existing `Информация об устройстве` card.
- [ ] 4.3 Keep PDU's dedicated room-and-related-codec section unchanged.
- [ ] 4.4 Keep the rows adjacent; do not create a standalone switch card or place them in controls, routing, outlet, or room sections.
- [ ] 4.5 Mark or render inventory-owned labels through a focused path so generic device-data clearing cannot permanently erase current values.
- [ ] 4.6 Ensure repeated activation or widget reconstruction does not duplicate either row.

## 5. Correct codec room-block ownership

- [ ] 5.1 Treat `RoomInformationBlock` as shell-owned and codec information/control cards as codec-owned.
- [ ] 5.2 Change `CodecScreen.update_parameters_display()` so it removes/recreates only codec-owned widgets and never calls `hide()` or `deleteLater()` on the shell-owned room block.
- [ ] 5.3 Do not implement the normal rebuild as "delete everything and reattach later".
- [ ] 5.4 After every codec rebuild used by model change or diagnostic refresh, ensure exactly one live shared room block remains last in the codec layout.
- [ ] 5.5 Ensure `shared_room_information_block` points to that exact live object.
- [ ] 5.6 Republish current address, VIP state, safe room status, and switch values after widget reconstruction without waiting for network success.
- [ ] 5.7 Prevent hidden, detached, pending-deletion, or deleted blocks from being accepted as current.
- [ ] 5.8 Preserve room-context stale-generation checks and keep codec code free of room lookup authority.
- [ ] 5.9 Allow `_ensure_shared_room_block()` to recover only from a genuinely missing/deleted block; it must not mask normal codec ownership violations.

## 6. Preserve inventory and diagnostic boundaries

- [ ] 6.1 Do not modify workbook source mapping, MAC-only reconciliation, ambiguity handling, schema shapes, loader validation, snapshot identity, or inventory indexes.
- [ ] 6.2 Do not add a public query by switch IP or switch port.
- [ ] 6.3 Do not use switch fields for dispatch, credentials, fallback, handler acquisition, transport selection, room aggregation, PDU enrichment, related-codec selection, successful credential memory, or device control.
- [ ] 6.4 Do not add switch fields to handler, parser, worker, controller, transport, or device-response payload contracts.
- [ ] 6.5 Do not perform switch reachability, authentication, link-state queries, or any switch network I/O.
- [ ] 6.6 Preserve schema-v1/v2 support through existing null adaptation.
- [ ] 6.7 Keep inventory absence and switch-field absence non-blocking.
- [ ] 6.8 Keep operational workbooks and generated deployment snapshots outside Git.

## 7. Regression coverage

- [ ] 7.1 Add a registry-driven test proving both switch rows occur exactly once in every registered screen's existing information card.
- [ ] 7.2 Prove PDU is included while retaining its dedicated room placement.
- [ ] 7.3 Prove full, switch-IP-only, switch-port-only, both-null, schema-v1/v2, unavailable inventory, invalid IP, zero-match, and multiple-match outcomes.
- [ ] 7.4 Prove ambiguity is not narrowed by selected model or another record attribute.
- [ ] 7.5 Prove current values publish without device network I/O, survive device request errors, and cannot be overwritten by device payloads.
- [ ] 7.6 Prove model/IP/page/snapshot changes invalidate old values and stale publication cannot restore them.
- [ ] 7.7 Exercise the real codec diagnostic-start path that calls `update_parameters_display()`.
- [ ] 7.8 After every codec rebuild under test, explicitly run:

```python
QApplication.sendPostedEvents(None, QEvent.DeferredDelete)
QApplication.processEvents()
```

- [ ] 7.9 After the deferred-delete flush, prove exactly one live `RoomInformationBlock` exists, it is last in the layout, and `shared_room_information_block` points to it.
- [ ] 7.10 Prove the preserved pre-rebuild block was never scheduled for deletion; for a genuine recovery case, prove the stale block is deleted and no longer referenced.
- [ ] 7.11 Prove the live block contains current address/VIP and later publication updates only that block.
- [ ] 7.12 Prove stale/deleted blocks cannot receive subsequent publication.
- [ ] 7.13 Rebuild repeatedly and prove exactly one room block and one switch-row pair remain after each deferred-delete flush.
- [ ] 7.14 Prove codec request failure does not remove or clear current room/switch presentation.
- [ ] 7.15 Use synthetic inventory only; require no real workbook, generated production snapshot, credential file, device, or network.

## 8. Focused implementation scope and review

- [ ] 8.1 Keep production changes focused on application inventory presentation, registered page rows, and codec widget ownership.
- [ ] 8.2 Expected files are `gui/main_window.py`, `gui/equipment_pages.py`, and the four registered screen modules; justify any additional production module.
- [ ] 8.3 Keep focused tests in `tests/test_equipment_room_context_gui.py` and one directly related existing/new switch-presentation GUI module unless another file is demonstrably required.
- [ ] 8.4 Do not modify importer code, handlers, transports, credential storage, operational data, root specs before archive, archived changes, or Graphify artifacts.
- [ ] 8.5 Review the final diff for unrelated UI redesign, page-specific inventory logic, accidental workbook data, complete inventory dumps, credentials, or new network behavior.

## 9. Implementation validation

- [ ] 9.1 Run focused room-context GUI tests:

```powershell
python -m unittest tests.test_equipment_room_context_gui
```

- [ ] 9.2 Run the focused switch-presentation GUI module and directly affected codec/Matrix/PDU/audio-DSP test modules; record exact commands and counts.
- [ ] 9.3 Run the full offline suite:

```powershell
python -m unittest discover -s tests -p "test_*.py"
```

- [ ] 9.4 Run:

```powershell
git diff --check
.\openspec.cmd validate equipment-page-inventory-context --strict
.\openspec.cmd validate --all --strict
```

- [ ] 9.5 Record repository-supported Python, Node, npm, and pinned OpenSpec versions, dependency restoration, exact commands, exit codes, and test counts.

## 10. Publish implementation for independent validation

- [ ] 10.1 Review `git status`, complete diff, changed-file list, and `git diff --check` before commit.
- [ ] 10.2 Create focused implementation commit(s) and push to `agent/equipment-page-inventory-context` without amend, rebase, force-push, or history rewrite.
- [ ] 10.3 Verify local HEAD equals `origin/agent/equipment-page-inventory-context` and PR remains Draft.
- [ ] 10.4 Record exact remote implementation SHA, current change base/master, changed-file scope, commands, exit codes, and counts.
- [ ] 10.5 Do not issue final `APPROVE`; request independent validation in a separate clean detached worktree from the published remote HEAD.

## 11. Independent validation and archive applicability

- [ ] 11.1 Fetch current remote branch and `master`, record full SHAs/subjects and PR state, and inspect new commits.
- [ ] 11.2 Create a clean detached worktree from `origin/agent/equipment-page-inventory-context` as required by `RULES.md`.
- [ ] 11.3 Verify clean status and local/remote SHA equality before tests.
- [ ] 11.4 Independently repeat focused tests, affected screen tests, full suite, `git diff --check`, strict change validation, and strict all validation without copying prior counts.
- [ ] 11.5 Independently inspect registry placement, resolution, stale suppression, request independence, and the real codec rebuild after `DeferredDelete` processing.
- [ ] 11.6 Verify no switch field becomes dispatch, credential, fallback, handler, transport, room/codec selection, control, or network-I/O authority.
- [ ] 11.7 Because this change uses `RENAMED Requirements` and `MODIFIED Requirements`, perform a disposable archive-applicability check outside the feature branch using `.\openspec.cmd archive equipment-page-inventory-context --yes`; inspect archive/root-spec diff against then-current root specs, run `.\openspec.cmd validate --all --strict`, and discard the worktree without publishing archive output.
- [ ] 11.8 Do not issue `READY FOR ARCHIVE` while any Critical, High, or Medium finding remains, a check fails, remote HEAD changes, the worktree is dirty, or archive applicability is unproven.

## 12. Archive and merge

- [ ] 12.1 Archive only after independent `APPROVE` or `APPROVE WITH NON-BLOCKING NOTES` and direct workflow authorization.
- [ ] 12.2 Review the archive/root-spec diff to confirm the requirement rename, display-only switch contract, and codec ownership contract are applied exactly.
- [ ] 12.3 Run post-archive `git diff --check`, full offline tests, `.\openspec.cmd validate --all --strict`, and repository-protection checks.
- [ ] 12.4 Create and push a dedicated archive commit without amend, rebase, force-push, or history rewrite.
- [ ] 12.5 Before merge, recheck current `master`, PR state/Draft, base/head, mergeability, remote archive HEAD, and new commits.
- [ ] 12.6 Do not mark ready, merge, close, delete the branch, or rewrite history without direct user authorization.
