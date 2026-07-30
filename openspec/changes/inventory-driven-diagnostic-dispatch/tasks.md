# Tasks: inventory-driven-diagnostic-dispatch

## 1. Review and approve architecture

- [ ] Read current `RULES.md`, `docs/equipment-inventory-runbook.md`, this change, the current root `diagnostic-application-shell` and `equipment-inventory-snapshot` specifications, current inventory/runtime source, GUI dispatch source, and focused tests.
- [ ] Fetch GitHub and record exact `origin/master`, remote feature-branch HEAD, PR state, Draft state, base/head, mergeability, and any commits newer than the architecture base before review.
- [ ] Confirm dispatch authority is exact canonical `diagnostic_model`, not `device_kind`, `source_model`, manufacturer evidence, handler availability, or registry order.
- [ ] Confirm complete IP multiplicity is classified before filtering and no duplicate-IP path can select `records[0]` or a preferred kind/model.
- [ ] Confirm manual fallback/override, stale generation, ownership, credentials, PDU enrichment, room/VIP compatibility, and Aten consistency correction are explicit and testable.
- [ ] Resolve every Critical, High, and Medium architecture finding before issuing `APPROVE` and starting implementation.

## 2. Establish one closed application dispatch registry

- [ ] Implement one reviewable application/composition registry for all nine exact supported canonical models, their screen keys, and their existing lifecycle routes.
- [ ] Consolidate or derive current `device_to_screen`, selectable manual models, `EQUIPMENT_PAGE_REGISTRY`, and model-specific refresh selection sufficiently to prevent silent registry drift.
- [ ] Reject or test duplicate model entries, missing screen registration, selectable models without dispatch, dispatch entries without screens, and unknown-model default-to-codec behavior.
- [ ] Keep credentials, credential lists, successful indexes, handlers, sessions, transports, cookies/tokens, and mutable workers outside registry data.
- [ ] Preserve the existing Matrix, PDU, DMP, codec, and Biamp lifecycle boundaries rather than introducing an unapproved generic device controller.

## 3. Implement inventory-assisted resolution and dispatch

- [ ] On user Refresh/Enter, validate and normalize the IP, create a new dispatch generation, capture the immutable inventory context, and resolve before model-specific credentials, ping, handler acquisition, worker/controller submission, or network I/O.
- [ ] Call `EquipmentInventory.find_by_ip(...)` and classify the complete tuple as inventory unavailable, zero, one, or many before inspecting model/kind.
- [ ] For exactly one record, dispatch only when exact `diagnostic_model` exists in the closed registry.
- [ ] Route unique Aten and PCS4i records to the PDU page/controller even when `device_kind = other`.
- [ ] Route TE20, TE40, Bar 310, RPG 310, IN1804, Tesira Forte CI, and DMP 64 Plus through their exact existing page/lifecycle entries.
- [ ] Do not inspect or normalize `source_model`, manufacturer/model evidence, free-form text, or handler availability at runtime.
- [ ] Do not pass inventory matches or candidate-model lists to screens, controllers, handlers, sessions, or workers.

## 4. Preserve manual fallback and override

- [ ] Keep existing manual model diagnostics available when inventory is unavailable, IP is not found, IP is ambiguous, `diagnostic_model` is null, or exact model is unsupported.
- [ ] Make an explicit operator selection after accepted automatic resolution a request-context override bound to the current normalized IP and immutable inventory context.
- [ ] Make the inventory/manual discrepancy observable without exposing source rows, production inventory, or secrets.
- [ ] Ensure override chooses only an existing closed dispatch entry and does not mutate `EquipmentRecord`, `EquipmentInventory`, workbook data, or `equipment_inventory.local.json`.
- [ ] Invalidate override on IP change, inventory context change/reload, reset, or shutdown and prevent stale automatic results from overwriting it.
- [ ] Resolve credentials only after the final accepted automatic or manual model is known.

## 5. Enforce dispatch freshness and lifecycle compatibility

- [ ] Bind lookup/publication to dispatch generation, normalized IP, immutable inventory context, and selection source/override binding.
- [ ] Supersede older pending dispatch on IP change, model change, new/repeated Refresh/Enter, inventory replacement/availability change, reset, or shutdown.
- [ ] Reject stale results before credential resolution, page/controller activation, handler/worker creation, and I/O.
- [ ] Ensure stale results cannot alter combo/page, room/VIP state, credentials, successful index/profile memory, controller operations, or PDU enrichment.
- [ ] Do not create a second Matrix, PDU, DMP, codec, or audio-DSP operation-generation authority after accepted dispatch enters the existing lifecycle.
- [ ] Keep normal lookup in memory; do not reread JSON, parse Excel, or perform network I/O on the Qt GUI thread.

## 6. Correct Aten consistency expectation

- [ ] Change `EXPECTED_KIND_BY_DIAGNOSTIC_MODEL["Aten PE8208AV"]` from `pdu` to `other`.
- [ ] Preserve exact `Тип модели -> device_kind` mapping, canonical fields, schema version, snapshot identity algorithm, and model-recognition rules.
- [ ] Ensure correct Aten and PCS4i rows with `device_kind = other` do not emit `KNOWN_MODEL_TYPE_MISMATCH`.
- [ ] Ensure a genuinely conflicting Aten source type still emits the consistency issue and never rewrites `device_kind` or `diagnostic_model`.

## 7. Add synthetic regression coverage

- [ ] Add importer tests for correct Aten/PCS4i `other` consistency and conflicting Aten source type.
- [ ] Add dispatch-registry integrity tests for all nine exact models, unique entries, registered screens, and no unknown default route.
- [ ] Add unique-IP tests for Aten, PCS4i, Huawei TE40, IN1804, and representative Biamp/DMP audio-DSP routes.
- [ ] Prove `device_kind = other` alone selects nothing and does not block exact Aten/PCS4i dispatch.
- [ ] Add inventory unavailable, not found, duplicate IP, null model, and unsupported exact-model fallback tests.
- [ ] Prove duplicate IP never selects the first record or filters by supported model/kind.
- [ ] Add manual override, no-persistence, override invalidation, repeat-refresh generation, and stale-result-before-I/O tests.
- [ ] Prove runtime dispatch never analyzes `source_model` and handlers/workers receive no candidate-model list.
- [ ] Preserve direct manual diagnostics, PDU room/codec enrichment gating, shared room/VIP presentation, credential/fallback policy, and GUI responsiveness.
- [ ] Use only synthetic inventory and credentials; do not add real organization data, production snapshots, or Graphify output.

## 8. Update operational documentation and evidence

- [ ] Update `docs/equipment-inventory-runbook.md` with exact `diagnostic_model` dispatch authority, closed registry, zero/one/many outcomes, manual fallback/override, stale binding, and the Aten/PCS4i `device_kind = other` distinction.
- [ ] Record implementation evidence in a change-specific verification report with exact branch SHA, change base, changed files, commands, exit codes, test counts, and known limitations.
- [ ] Keep implementation scope limited to approved application composition/registry wiring, importer correction, synthetic tests, runbook, and evidence.

## 9. Validate implementation

- [ ] Run focused tests with the repository-supported Python interpreter and record exact results:

```powershell
<python> -m unittest tests.test_equipment_inventory tests.test_inventory_diagnostic_dispatch -v
```

- [ ] Run any existing focused GUI/controller regression modules touched by implementation and record exact commands and counts.
- [ ] Run the canonical full offline test suite and record exact passed/failed counts:

```powershell
<python> -m unittest discover -s tests -p "test_*.py" -v
```

- [ ] Run repository-local OpenSpec validation only:

```powershell
.\openspec.cmd validate inventory-driven-diagnostic-dispatch --strict
.\openspec.cmd validate --all --strict
```

- [ ] Run repository protection checks:

```powershell
git diff --check
git status --short
git diff --stat origin/master...HEAD
git diff --name-only origin/master...HEAD
```

- [ ] Review that no production workbook/snapshot, credentials, Graphify output, runtime source-text recognizer, device-kind routing, handler-owned lookup, or unrelated files changed.

## 10. Publish for independent validation

- [ ] Create focused implementation commit(s) and push to `agent/inventory-driven-diagnostic-dispatch` without force-push.
- [ ] Verify local HEAD equals `origin/agent/inventory-driven-diagnostic-dispatch` after push.
- [ ] Do not self-issue final `APPROVE`; request independent validation from a separate clean detached worktree created from the exact published remote branch HEAD.

## 11. Independent validation and archive applicability

- [ ] In a clean detached worktree from `origin/agent/inventory-driven-diagnostic-dispatch`, verify local/remote SHA equality, clean status, commit subject, changed-file scope, and current PR state/base/head/Draft/mergeability.
- [ ] Independently rerun focused tests, touched GUI/controller regressions, full offline tests, both strict OpenSpec validations, `git diff --check`, registry/ownership review, and secret/inventory protection checks without copying earlier counts.
- [ ] The validator must not fix its own findings or change production code, tests, proposal, design, tasks, or specifications.
- [ ] Because this change uses `MODIFIED` root requirements, perform a disposable archive-applicability check outside the feature branch: archive with `.\openspec.cmd archive inventory-driven-diagnostic-dispatch --yes` in a throwaway worktree, inspect archive/root-spec diff against then-current root specs, run `.\openspec.cmd validate --all --strict`, and discard the worktree without publishing archive output.
- [ ] Do not issue `READY FOR ARCHIVE` while any Critical, High, or Medium finding remains, a required check fails, the validated remote HEAD changed, the worktree was dirty, or archive applicability is unproven.

## 12. Archive and merge after explicit permission

- [ ] Archive only after independent approval using repository-local `.\openspec.cmd archive inventory-driven-diagnostic-dispatch --yes`.
- [ ] Review archive/root-spec diff, run `.\openspec.cmd validate --all --strict`, full offline tests, and `git diff --check`.
- [ ] Create and push a dedicated archive commit, then recheck exact remote archive HEAD and current `master`.
- [ ] Do not merge, close the PR, remove Draft, or delete branches without the user's direct permission.
