# Tasks: Equipment page inventory context

## 1. Confirm current authority and implementation context

- [ ] 1.1 Before implementation, read current `RULES.md` and then `docs/equipment-inventory-runbook.md` as required for inventory-related work.
- [ ] 1.2 Read the approved root specifications `equipment-inventory-snapshot` and `diagnostic-application-shell`, plus any current root requirement governing equipment-page registration and non-PDU room presentation.
- [ ] 1.3 Read current `core/equipment_inventory.py`, `core/room_context.py`, `gui/equipment_pages.py`, `gui/main_window.py`, all four registered equipment screens, and focused inventory/room GUI tests.
- [ ] 1.4 Fetch current `origin/master` and `origin/agent/equipment-page-inventory-context`, record both full SHAs and subjects, confirm PR base/head/Draft state, and inspect all commits added after the approved architecture HEAD before changing code.
- [ ] 1.5 Confirm the implementation branch still contains this approved architecture and that no newer root-spec or page-registry change conflicts with it.

## 2. Add application-owned switch presentation

- [ ] 2.1 Resolve switch connection presentation only from the current immutable `EquipmentInventory` and the existing exact `find_by_ip()` zero/one/many semantics.
- [ ] 2.2 Publish the unique record's `switch_ip_address` and `switch_port` independently so a unique partial candidate keeps its available value.
- [ ] 2.3 Render null, unavailable, invalid-IP, not-found, and ambiguous outcomes as neutral unavailable values without modal errors or device-request failure.
- [ ] 2.4 Do not narrow multiple records by selected model, `device_kind`, MAC, room, row order, or presentation state.
- [ ] 2.5 Keep screens rendering-only: they must not receive the inventory, query records, interpret multiplicity, or decide stale-result acceptance.
- [ ] 2.6 Use an application-owned context binding/generation covering exact model, normalized IP, inventory snapshot identity, and registered page context, or an equivalent complete freshness contract.
- [ ] 2.7 Invalidate and republish switch presentation on current model, IP, page, or inventory snapshot/availability changes.
- [ ] 2.8 Keep publication independent of reachability, credentials, handler acquisition, worker/controller result, device request success/error/completion, interactive actions, and device control.
- [ ] 2.9 Ensure device result payloads cannot overwrite the canonical inventory-backed switch values.

## 3. Add the rows to every registered equipment page

- [ ] 3.1 Add exactly one `IP коммутатора` row and exactly one `Порт коммутатора` row to `CodecScreen`'s existing `Основная информация` card.
- [ ] 3.2 Add the same two rows to `MatrixScreen`'s existing `Информация об устройстве` card.
- [ ] 3.3 Add the same two rows to `PDUScreen`'s existing `Информация об устройстве` card without moving or changing its dedicated room-and-related-codec section.
- [ ] 3.4 Add the same two rows to `AudioDSPScreen`'s existing `Информация об устройстве` card.
- [ ] 3.5 Keep the two rows adjacent within each information card while allowing existing page-specific row ordering and layout.
- [ ] 3.6 Do not create a standalone switch card, add switch fields to control/routing/outlet sections, or add page-specific labels or null semantics.
- [ ] 3.7 Mark or update inventory-owned values so generic device-data clearing cannot permanently erase them while current inventory context remains valid.
- [ ] 3.8 Ensure repeated screen activation or widget reconstruction does not duplicate either row.

## 4. Preserve the codec room-information block through rebuilds

- [ ] 4.1 Fix the ownership conflict where `CodecScreen.update_parameters_display()` removes the shell-owned shared room block from `param_layout`.
- [ ] 4.2 Choose and document one explicit implementation: preserve shell-owned children during codec rebuild, or safely reattach and republish through a focused shell/layout hook immediately after rebuild.
- [ ] 4.3 After every codec rebuild used by model change or diagnostic refresh, ensure exactly one shared `RoomInformationBlock` exists at the bottom of the codec page.
- [ ] 4.4 Republish the current room address, VIP state, and safe room status after rebuild without waiting for codec network success.
- [ ] 4.5 Republish current switch connection presentation into newly created codec information rows under the same current inventory binding.
- [ ] 4.6 Prevent hidden, pending-deletion, or visible duplicate room blocks after repeated rebuilds.
- [ ] 4.7 Preserve existing room-context stale-generation checks and keep codec screen code free of room lookup authority.

## 5. Preserve inventory and diagnostic contracts

- [ ] 5.1 Do not modify primary or network workbook source mapping, MAC-only reconciliation, ambiguity handling, schema field shapes, loader validation, snapshot identity, or inventory indexes.
- [ ] 5.2 Do not add a public inventory query by switch IP or switch port.
- [ ] 5.3 Do not use switch fields for diagnostic model dispatch, credentials, fallback, handler acquisition, transport selection, room aggregation, PDU-room-codec enrichment, related-codec selection, successful credential memory, or device control.
- [ ] 5.4 Do not add switch fields to handler, parser, worker, controller, transport, or device-response payload contracts.
- [ ] 5.5 Do not perform switch reachability tests, switch authentication, link-state queries, or any switch network I/O.
- [ ] 5.6 Preserve support for schema-v1 and schema-v2 snapshots through their existing null adaptation.
- [ ] 5.7 Keep inventory absence and switch-field absence non-blocking for all existing diagnostics and controls.
- [ ] 5.8 Keep operational workbooks and generated deployment snapshots outside Git.

## 6. Regression coverage

- [ ] 6.1 Add a registry-driven test that enumerates every `EquipmentPageRegistration` and proves both switch rows occur exactly once in that screen's existing information card.
- [ ] 6.2 Prove the PDU page is included in switch-row coverage while retaining its dedicated room placement.
- [ ] 6.3 Prove a unique schema-v3 record with both fields renders both exact values on every page kind.
- [ ] 6.4 Prove switch-IP-only and switch-port-only records preserve the available value and render `—` for the other field.
- [ ] 6.5 Prove both-null, schema-v1/schema-v2, unavailable inventory, invalid IP, zero-match, and multiple-match cases render neutral unavailable values.
- [ ] 6.6 Prove ambiguity is not narrowed by current selected model or another record attribute.
- [ ] 6.7 Prove current switch values publish without device network I/O and remain after a device request error.
- [ ] 6.8 Prove model/IP/page/snapshot changes invalidate old values and stale publication cannot restore them.
- [ ] 6.9 Prove replacing a snapshot republishes values from the new exact snapshot.
- [ ] 6.10 Exercise the real codec diagnostic-start path that calls `update_parameters_display()` and prove one bottom room block still shows current address and VIP afterward.
- [ ] 6.11 Rebuild the codec page repeatedly and prove exactly one room block and one switch-row pair remain each time.
- [ ] 6.12 Prove codec request failure does not remove or clear current room and switch inventory presentation.
- [ ] 6.13 Ensure focused tests use synthetic inventory only and require no real workbook, generated production snapshot, credential file, device, or network access.

## 7. Focused implementation scope and review

- [ ] 7.1 Keep production changes focused on application inventory presentation, registered page rows, and codec rebuild ownership.
- [ ] 7.2 Expected files are `gui/main_window.py`, `gui/equipment_pages.py`, and the four registered screen modules; justify any additional production module in the implementation report.
- [ ] 7.3 Keep focused test changes in `tests/test_equipment_room_context_gui.py` and one directly related existing or new inventory-presentation GUI test module unless another file is demonstrably required.
- [ ] 7.4 Do not modify importer code, handlers, transports, credential storage, operational data, root specs before archive, archived changes, validation evidence outside the workflow, or Graphify artifacts.
- [ ] 7.5 Review the final diff for unrelated UI redesign, page-specific inventory logic, accidental workbook data, complete inventory dumps, credential values, or new device/network behavior.

## 8. Implementation validation

- [ ] 8.1 Run the focused room-context GUI tests:

```powershell
python -m unittest tests.test_equipment_room_context_gui
```

- [ ] 8.2 Run the focused switch-presentation GUI test module selected or added during implementation and record its exact command and counts.
- [ ] 8.3 Run any directly affected screen test modules for codec, Matrix, PDU, and audio DSP and record exact commands and counts.
- [ ] 8.4 Run the full offline Python test suite and record exact passed, skipped, and failed counts:

```powershell
python -m unittest discover -s tests -p "test_*.py"
```

- [ ] 8.5 Run whitespace validation:

```powershell
git diff --check
```

- [ ] 8.6 Run repository-local strict change validation:

```powershell
.\openspec.cmd validate equipment-page-inventory-context --strict
```

- [ ] 8.7 Run repository-local strict validation of all OpenSpec artifacts:

```powershell
.\openspec.cmd validate --all --strict
```

- [ ] 8.8 Record the repository-supported Python, Node, npm, and pinned OpenSpec environment details required by `RULES.md`, plus exact commands, exit codes, and test counts.

## 9. Publish implementation for independent validation

- [ ] 9.1 Review `git status`, complete diff, changed-file list, and `git diff --check` before committing.
- [ ] 9.2 Create focused implementation commit(s) and push to `agent/equipment-page-inventory-context` without amend, rebase, force-push, or published-history rewrite.
- [ ] 9.3 Verify local implementation HEAD equals `origin/agent/equipment-page-inventory-context` after push and the PR remains Draft.
- [ ] 9.4 Record exact remote implementation SHA, current change base, current `master`, changed-file scope, validation commands, exit codes, and test counts.
- [ ] 9.5 Do not issue final `APPROVE`; request independent validation from a separate clean detached worktree created from the published remote branch HEAD.

## 10. Independent validation and archive applicability

- [ ] 10.1 Fetch the current remote branch and current `master`, record full SHAs/subjects and PR state, and inspect any new commits before validation.
- [ ] 10.2 Create a separate clean detached validation worktree from `origin/agent/equipment-page-inventory-context` exactly as required by `RULES.md`.
- [ ] 10.3 Verify clean worktree status and local/remote SHA equality before tests.
- [ ] 10.4 Independently repeat focused tests, affected screen tests, the full offline suite, `git diff --check`, strict change validation, and strict all validation without copying prior counts.
- [ ] 10.5 Independently inspect registry-wide row placement, unique/partial/unavailable resolution, stale suppression, device-request independence, and the real codec rebuild path.
- [ ] 10.6 Verify no switch field becomes dispatch, credential, fallback, handler, transport, room/codec selection, control, or network-I/O authority.
- [ ] 10.7 Because this change adds and modifies root-spec requirements, perform a disposable archive-applicability check outside the feature branch using `.\openspec.cmd archive equipment-page-inventory-context --yes`, inspect the resulting archive/root-spec diff against then-current root specs, run `.\openspec.cmd validate --all --strict`, and discard the worktree without publishing archive output.
- [ ] 10.8 Do not issue `READY FOR ARCHIVE` while any Critical, High, or Medium finding remains, a required check fails, the validated remote HEAD changed, the validation worktree was dirty, or archive applicability is unproven.

## 11. Archive and merge

- [ ] 11.1 Archive only after independent `APPROVE` or `APPROVE WITH NON-BLOCKING NOTES` and direct workflow authorization.
- [ ] 11.2 Review the archive/root-spec diff to ensure only the approved equipment-page display and codec rebuild contracts are applied and the remaining passive-data restrictions are preserved.
- [ ] 11.3 Run post-archive `git diff --check`, full offline tests, `.\openspec.cmd validate --all --strict`, and repository-protection checks.
- [ ] 11.4 Create and push a dedicated archive commit without amend, rebase, force-push, or history rewrite.
- [ ] 11.5 Before merge, recheck current `master`, PR state/Draft state, base/head, mergeability, remote archive HEAD, and new commits.
- [ ] 11.6 Do not mark the PR ready, merge, close it, delete the branch, or rewrite published history without direct user authorization.
