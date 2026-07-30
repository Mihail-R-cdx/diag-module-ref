# Tasks: inventory-driven-diagnostic-dispatch

## 1. Review the corrected architecture baseline

- [ ] Before beginning work, read `RULES.md`.
- [ ] Read `docs/equipment-inventory-runbook.md`, this change, and current root specifications for `diagnostic-application-shell`, `equipment-inventory-snapshot`, and `pdu-room-codec-enrichment`.
- [ ] Fetch GitHub and record exact `origin/master`, remote feature-branch HEAD, PR state, Draft state, base/head, mergeability, and any commits newer than the architecture base.
- [ ] Review current `gui/main_window.py`, `gui/equipment_pages.py`, `core/room_context.py`, importer consistency mapping, and focused synthetic tests.
- [ ] Confirm the permanent model selector and `Устройство` label are removed by the approved design rather than retained or hidden.
- [ ] Confirm a supported inventory model is authoritative for its request and no ordinary manual override remains.
- [ ] Confirm every unresolved outcome opens an explicit fail-closed fallback dialog and Cancel/close performs no device-specific work or I/O.
- [ ] Confirm complete IP multiplicity is classified before filtering and no duplicate-IP path selects `records[0]` or a preferred model/kind.
- [ ] Confirm PDU enrichment uses exact accepted-PDU-model/inventory-model agreement and no longer requires `device_kind = pdu`.
- [ ] Resolve every Critical, High, and Medium architecture finding before issuing `APPROVE` or starting implementation.

## 2. Validate the published architecture HEAD before approval

- [ ] Use a clean checkout/worktree from exact `origin/agent/inventory-driven-diagnostic-dispatch`, not an older local branch.
- [ ] Record exact remote SHA, local HEAD, local/remote equality, commit subject, clean `git status --short`, and current PR state/base/head/Draft/mergeability.
- [ ] Record supported Node and npm versions and dependency restoration result when required by `RULES.md`.
- [ ] Run only repository-local OpenSpec commands:

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

- [ ] Record exact commands, exit codes, validation results, and changed-file scope in the architecture review report.
- [ ] Do not issue architecture `APPROVE` while strict validation or a mandatory repository check is unexecuted or failing.

## 3. Establish one closed application dispatch registry

- [ ] Implement one reviewable application/composition registry for all nine exact supported models, their screen keys, and their existing lifecycle routes.
- [ ] Derive or integrity-check fallback choices, `EQUIPMENT_PAGE_REGISTRY`, current `device_to_screen` replacement, and model-specific lifecycle selection against the same registry.
- [ ] Remove permanent combo-box model population and do not introduce a hidden selector as request authority.
- [ ] Reject or test duplicate model entries, missing screen registration, fallback models without lifecycle routes, dispatch entries without screens, and unknown-model default-to-codec behavior.
- [ ] Keep credentials, successful indexes, handlers, sessions, transports, cookies/tokens, and mutable workers outside registry data.
- [ ] Preserve existing Matrix, PDU, DMP, codec, and Biamp lifecycle boundaries rather than introducing an unapproved generic controller.

## 4. Remove permanent model selection from the top panel

- [ ] Remove `deviceCombo`/equivalent permanent model selector and the `Устройство` label from the connection panel.
- [ ] Remove default-first-model initialization and all use of Qt selector text as model, page, credential, retry, or freshness authority.
- [ ] Store accepted exact model and registry entry only in application-owned request context.
- [ ] Adapt existing screen/title/debug presentation to read accepted request context without reintroducing model-selection authority into widgets.
- [ ] Ensure model-independent IP editing, Refresh/Enter, password/configuration, and debug actions remain coherent.

## 5. Implement automatic inventory resolution and authoritative dispatch

- [ ] On Refresh/Enter, validate and normalize IP, create a new dispatch generation, capture immutable inventory context, and resolve before model-specific credentials, ping, handler acquisition, worker/controller submission, or network I/O.
- [ ] Call `EquipmentInventory.find_by_ip(...)` and classify inventory unavailable, zero, one, or many before inspecting record model/kind.
- [ ] For exactly one record, dispatch only when exact `diagnostic_model` exists in the closed registry.
- [ ] Route unique Aten and PCS4i records to PDU even when `device_kind = other`.
- [ ] Route TE20, TE40, Bar 310, RPG 310, IN1804, Tesira Forte CI, and DMP 64 Plus through their exact existing lifecycle entries.
- [ ] Treat a supported inventory model as authoritative for the request and expose no ordinary override path.
- [ ] Do not inspect or normalize `source_model`, manufacturer/model evidence, free-form text, kind, or handler availability at runtime.
- [ ] Do not pass inventory matches or candidate-model lists to dialogs, screens, controllers, handlers, sessions, or workers.

## 6. Implement fail-closed DeviceModelFallbackDialog

- [ ] For inventory unavailable, IP not found, duplicate IP, null model, or unsupported exact model, automatically open a focused `DeviceModelFallbackDialog` with a safe distinct reason.
- [ ] Populate choices only from the closed dispatch registry.
- [ ] Do not preaccept the first item and do not reuse a previous selection; require an explicit selection in the current dialog interaction.
- [ ] Disable or reject `Подключиться` until an explicit current selection exists.
- [ ] On explicit selection plus confirmation, publish one generation/IP/inventory-bound `MANUAL_FALLBACK` request context and only then resolve credentials and perform reachability validation.
- [ ] On Cancel or window close, return/retain `IDLE` and perform zero model-specific credential resolution, ping, handler acquisition, worker/controller creation/submission, page lifecycle start, or device I/O.
- [ ] Ensure fallback does not mutate `EquipmentRecord`, `EquipmentInventory`, workbook, JSON, aliases, or persistent canonical model state.
- [ ] Do not open fallback or permit model replacement after a supported automatic resolution.

## 7. Enforce dispatch and dialog freshness

- [ ] Bind lookup/publication and fallback dialog to dispatch generation, normalized IP, immutable inventory context, outcome, selection source, and exact assigned model when accepted.
- [ ] Supersede older pending lookup/dialog work on IP change, new/repeated Refresh/Enter, inventory replacement/availability change, reset, or shutdown.
- [ ] Reject stale lookup results, dialog selections, and confirmations before credentials, page/controller activation, handler/worker creation, and I/O.
- [ ] Ensure stale work cannot alter request model, page, room/VIP state, credentials, successful index/profile memory, controller operations, or PDU enrichment.
- [ ] Do not create a second Matrix, PDU, DMP, codec, or audio-DSP operation-generation authority after accepted dispatch enters its existing lifecycle.
- [ ] Keep normal lookup in memory; do not reread JSON, parse Excel, or perform network I/O on the Qt GUI thread.

## 8. Make PDU room-codec enrichment use exact accepted model identity

- [ ] Change the pure related-codec resolver boundary to receive the exact model and IP from the accepted current `PDUController` context.
- [ ] Preserve complete zero/one/many IP cardinality before any model inspection.
- [ ] Accept only the closed PDU set: `Aten PE8208AV` and `Extron IPL T PCS4i`.
- [ ] Require the one inventory record's exact canonical `diagnostic_model` to equal the accepted PDU context model.
- [ ] Remove the `device_kind == "pdu"` gate and do not identify PDU records by kind, page key, source text, or position.
- [ ] Add controlled `PDU_MODEL_UNSUPPORTED` and `PDU_MODEL_MISMATCH` outcomes or exact equivalents required by the specification.
- [ ] Ensure mismatch stops before related-codec credentials, handler/session construction, work submission, and network I/O.
- [ ] Preserve accepted-PDU-success gating, room-ID authority, one-codec multiplicity, dedicated read-only codec lane, stale rejection, and enrichment independence from PDU success.

## 9. Correct Aten consistency expectation

- [ ] Change `EXPECTED_KIND_BY_DIAGNOSTIC_MODEL["Aten PE8208AV"]` from `pdu` to `other`.
- [ ] Preserve exact `Тип модели -> device_kind` mapping, canonical fields, schema version, snapshot identity algorithm, and recognition rules.
- [ ] Ensure correct Aten and PCS4i rows with `device_kind = other` do not emit `KNOWN_MODEL_TYPE_MISMATCH`.
- [ ] Ensure a genuinely conflicting Aten source type still emits the consistency issue and never rewrites canonical fields.

## 10. Add synthetic regression coverage

- [ ] Add top-panel tests proving no permanent model selector, no `Устройство` label, and no default/previous widget model authority.
- [ ] Add registry integrity tests for all nine exact models, unique entries, registered screens, fallback choices, and no unknown default route.
- [ ] Add unique-IP routing tests for Aten, PCS4i, TE40, IN1804, and representative Biamp/DMP routes.
- [ ] Prove `device_kind` alone selects nothing and does not block exact Aten/PCS4i dispatch.
- [ ] Add inventory unavailable, not found, duplicate IP, null model, and unsupported-model fallback-dialog tests.
- [ ] For every fallback reason, prove safe reason presentation, explicit current selection, confirmation, Cancel, and window-close behavior.
- [ ] Prove no first/previous model is implicitly accepted.
- [ ] Prove zero model-specific credential access, ping, handler acquisition, worker/controller submission, page lifecycle start, and device I/O before confirmation and after Cancel/close.
- [ ] Prove supported automatic resolution offers no fallback/override and uses only inventory model credentials/lifecycle.
- [ ] Add stale lookup and stale dialog-confirmation-before-I/O tests.
- [ ] Add PDU enrichment tests for exact Aten/PCS4i context with kind `other`, duplicate IP, unsupported accepted model, null/unsupported/different inventory model, and zero codec I/O after mismatch.
- [ ] Add importer tests for correct Aten/PCS4i `other` consistency and conflicting Aten source type.
- [ ] Prove runtime dispatch never analyzes `source_model` and handlers/workers receive no candidate-model list.
- [ ] Preserve shared room/VIP presentation, credential/fallback policy after model assignment, and GUI responsiveness.
- [ ] Use only synthetic inventory and credentials; add no real organization data, snapshots, or Graphify output.

## 11. Update operational documentation and evidence

- [ ] Update `docs/equipment-inventory-runbook.md` with IP-only top-panel flow, exact model authority, closed registry, fail-closed fallback dialog, no override after resolution, stale binding, PDU accepted-model matching, and Aten/PCS4i kind distinction.
- [ ] Update any safe status text that references obsolete `PDU_KIND_MISMATCH` to the approved model outcomes.
- [ ] Record implementation evidence with exact branch SHA, base, changed files, commands, exit codes, test counts, and limitations.
- [ ] Keep scope limited to approved composition/registry/UI wiring, resolver correction, importer correction, synthetic tests, runbook, and evidence.

## 12. Validate implementation

- [ ] Run focused tests with the repository-supported Python interpreter and record exact results:

```powershell
<python> -m unittest tests.test_equipment_inventory tests.test_inventory_diagnostic_dispatch tests.test_pdu_room_codec_enrichment -v
```

- [ ] Run all existing focused GUI/controller regression modules touched by implementation and record exact commands and counts.
- [ ] Run the canonical full offline test suite:

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

## 13. Publish for independent validation

- [ ] Create focused implementation commit(s) and push to `agent/inventory-driven-diagnostic-dispatch` without force-push.
- [ ] Verify local HEAD equals `origin/agent/inventory-driven-diagnostic-dispatch` after push.
- [ ] Do not self-issue final `APPROVE`; request independent validation from a separate clean detached worktree created from exact remote HEAD.

## 14. Independent validation and archive applicability

- [ ] In a clean detached worktree from exact `origin/agent/inventory-driven-diagnostic-dispatch`, verify local/remote SHA equality, clean status, commit subject, scope, and current PR state/base/head/Draft/mergeability.
- [ ] Independently rerun focused tests, GUI/controller regressions, full offline tests, both strict OpenSpec validations, `git diff --check`, architecture correspondence, and protection checks without copying earlier counts.
- [ ] The validator must not fix its own findings or change production code, tests, proposal, design, tasks, or specifications.
- [ ] Because this change uses `MODIFIED` root requirements, perform a disposable archive-applicability check outside the feature branch: archive with `.\openspec.cmd archive inventory-driven-diagnostic-dispatch --yes` in a throwaway worktree, inspect archive/root-spec diff against current root specs, run `.\openspec.cmd validate --all --strict`, and discard the worktree without publishing archive output.
- [ ] Do not issue `READY FOR ARCHIVE` while any Critical, High, or Medium finding remains, a check fails, validated HEAD changes, the worktree was dirty, or archive applicability is unproven.

## 15. Archive and merge after explicit permission

- [ ] Archive only after independent approval using repository-local `.\openspec.cmd archive inventory-driven-diagnostic-dispatch --yes`.
- [ ] Review archive/root-spec diff, run `.\openspec.cmd validate --all --strict`, full offline tests, and `git diff --check`.
- [ ] Create and push a dedicated archive commit, then recheck exact remote archive HEAD and current `master`.
- [ ] Do not merge, close the PR, remove Draft, or delete branches without the user's direct permission.