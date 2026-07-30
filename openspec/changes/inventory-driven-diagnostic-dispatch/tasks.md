# Tasks: inventory-driven-diagnostic-dispatch

## 1. Review the corrected architecture baseline

- [ ] Before beginning work, read `RULES.md`.
- [ ] Read `docs/equipment-inventory-runbook.md`, this change, and current root specifications for `diagnostic-application-shell`, `equipment-inventory-snapshot`, and `pdu-room-codec-enrichment`.
- [ ] Fetch GitHub and record exact `origin/master`, remote feature-branch HEAD, PR state, Draft state, base/head, mergeability, and any commits newer than the architecture base.
- [ ] Review current `gui/main_window.py`, including every `show_password_dialog()` definition and direct `device_combo.currentText()` use, plus `gui/equipment_pages.py`, `core/room_context.py`, importer consistency mapping, credential APIs, and focused synthetic tests.
- [ ] Confirm the permanent model selector and `Устройство` label are removed rather than retained or hidden.
- [ ] Confirm a supported inventory model is authoritative for diagnostic startup and no ordinary manual override remains.
- [ ] Confirm every unresolved diagnostic outcome opens explicit fail-closed fallback and Cancel/close performs no device-specific work or I/O.
- [ ] Confirm `Пароль` has a separate model-bound credential-configuration contract, performs its own exact IP/inventory resolution, and never uses previous request/widget state as model authority.
- [ ] Confirm credential configuration performs no ping, page transition, controller/worker creation, device I/O, or automatic diagnostic start.
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

- [ ] Implement one reviewable application/composition registry for all nine exact supported models, their screen keys, and existing lifecycle routes.
- [ ] Derive or integrity-check diagnostic fallback choices, credential fallback choices, `EQUIPMENT_PAGE_REGISTRY`, current `device_to_screen` replacement, and model-specific lifecycle selection against the same registry.
- [ ] Remove permanent combo-box model population and do not introduce a hidden selector as model authority.
- [ ] Reject or test duplicate model entries, missing screen registration, fallback models without lifecycle routes, dispatch entries without screens, and unknown-model default-to-codec behavior.
- [ ] Keep credentials, successful indexes, handlers, sessions, transports, cookies/tokens, and mutable workers outside registry data.
- [ ] Preserve existing Matrix, PDU, DMP, codec, and Biamp lifecycle boundaries rather than introducing an unapproved generic controller.

## 4. Remove permanent model selection from the top panel

- [ ] Remove `deviceCombo`/equivalent permanent model selector and the `Устройство` label from the connection panel.
- [ ] Remove default-first-model initialization and all use of Qt selector text as model, page, credential, retry, or freshness authority.
- [ ] Store accepted exact models only in application-owned purpose-bound contexts.
- [ ] Adapt existing screen/title/debug presentation to read accepted diagnostic context without reintroducing widget model authority.
- [ ] Keep IP editing, Refresh/Enter, `Пароль`, and debug actions coherent.
- [ ] Preserve the permanent `Пароль` button, but route it to the new credential-configuration action rather than directly opening a model-specific credential dialog.

## 5. Implement shared exact model resolution

- [ ] Implement one application-owned side-effect-free resolution path parameterized by action purpose.
- [ ] Validate/normalize IP and call `EquipmentInventory.find_by_ip(...)` against the captured immutable inventory context.
- [ ] Classify inventory unavailable and complete zero/one/many cardinality before inspecting model/kind.
- [ ] For exactly one record, resolve only exact non-null `diagnostic_model` through the closed registry.
- [ ] Distinguish `INVENTORY_UNAVAILABLE`, `IP_NOT_FOUND`, `AMBIGUOUS_IP`, `MODEL_UNMAPPED`, `MODEL_UNSUPPORTED`, and `RESOLVED` or exact private equivalents.
- [ ] Do not inspect or normalize `source_model`, manufacturer/model evidence, free-form text, `device_kind`, handler availability, prior contexts, widget text, or registry order as model authority.
- [ ] Ensure the shared resolver itself does not read/mutate credentials, change pages, ping, acquire handlers, create/submit work, or perform device I/O.

## 6. Implement automatic inventory resolution and authoritative diagnostic dispatch

- [ ] On Refresh/Enter, validate/normalize IP, create a new `DIAGNOSTIC_START` generation, capture immutable inventory context, and run shared exact model resolution.
- [ ] For `RESOLVED`, publish one current `AUTO_INVENTORY` exact model/page/lifecycle diagnostic request context.
- [ ] Route unique Aten and PCS4i records to PDU even when `device_kind = other`.
- [ ] Route TE20, TE40, Bar 310, RPG 310, IN1804, Tesira Forte CI, and DMP 64 Plus through exact existing lifecycle entries.
- [ ] Treat supported inventory model as authoritative and expose no ordinary override path.
- [ ] Resolve model-specific credentials and perform reachability validation only after current automatic/fallback diagnostic model acceptance.
- [ ] Do not pass inventory matches or candidate-model lists to dialogs, screens, controllers, handlers, sessions, or workers.

## 7. Implement purpose-bound fail-closed DeviceModelFallbackDialog

- [ ] Support explicit immutable purposes `DIAGNOSTIC_START` and `CREDENTIAL_CONFIGURATION` or exact equivalents.
- [ ] For inventory unavailable, IP not found, duplicate IP, null model, or unsupported exact model, automatically open fallback with a safe distinct reason for the requesting purpose.
- [ ] Populate choices only from the closed registry.
- [ ] Do not preaccept the first item and do not reuse previous fallback, diagnostic, credential, screen, or widget selection.
- [ ] Disable/reject confirmation until explicit selection in the current dialog interaction.
- [ ] For diagnostic purpose, use `Подключиться` and publish one current `MANUAL_FALLBACK` diagnostic request context only after confirmation.
- [ ] For credential purpose, use `Продолжить` or equivalent non-connection confirmation and publish only a model-bound credential-configuration context.
- [ ] On Cancel/window close, fail closed and perform zero purpose-specific mutation, model-specific credential access, ping, handler acquisition, controller/worker creation/submission, page lifecycle start, automatic diagnostic start, or device I/O.
- [ ] Ensure fallback does not mutate inventory, workbook, JSON, aliases, or canonical model state.
- [ ] Do not open fallback or permit model replacement after supported automatic diagnostic resolution.

## 8. Implement model-bound credential configuration for Пароль

- [ ] Replace all `show_password_dialog()` model reads from `device_combo.currentText()` with application-owned credential-action orchestration.
- [ ] Remove the obsolete duplicate password-dialog definition and retain one focused implementation.
- [ ] On every `Пароль` activation, validate/normalize current IP and create a distinct `CREDENTIAL_CONFIGURATION` generation/binding.
- [ ] For invalid/empty IP, show controlled warning and stop without inventory query, fallback, credential dialog, credential mutation, or device I/O.
- [ ] Run shared exact model resolution without reusing `_active_request`, previous successful model, previous fallback model, current page, title, or hidden widget state.
- [ ] For `RESOLVED`, bind exactly the inventory model/IP and open only that model's credential dialog.
- [ ] For unresolved outcome, require credential-purpose fallback confirmation before opening credential dialog.
- [ ] Recheck purpose, generation, IP, inventory context, selection source, exact model, and dialog identity before opening credential dialog and before credential mutation.
- [ ] On valid credential-dialog confirmation, add/promote only the exact bound model/IP candidate under existing credential-store semantics.
- [ ] Invoke existing credential-context invalidation only for the affected model/IP as required by current safety contracts.
- [ ] Do not mark entered candidate as confirmed successful credential and do not persist a connection profile.
- [ ] Do not perform ping, page transition, handler/session acquisition, controller/worker creation/submission, device I/O, diagnostic request creation, Refresh, or automatic diagnostic start.
- [ ] On fallback Cancel/close, open no credential dialog and mutate nothing.
- [ ] On credential-dialog Cancel/close, mutate no candidate list/order, successful index, profile, inventory, or diagnostic context.
- [ ] Keep secrets out of logs, public errors, fallback payloads, bindings, and status text.

## 9. Enforce purpose-bound freshness and cross-purpose isolation

- [ ] Bind every diagnostic and credential action to purpose, generation, normalized IP, immutable inventory context, outcome, selection source, exact model when accepted, fallback identity, and credential-dialog identity when applicable.
- [ ] Use separate generation counters or one global serial with mandatory purpose binding and proven cross-purpose rejection.
- [ ] Supersede pending actions on IP change, inventory replacement/availability change, reset, or shutdown.
- [ ] Supersede older same-purpose action on new/repeated Refresh/Enter or `Пароль` activation.
- [ ] Do not reuse accepted diagnostic model as credential-action authority and do not let credential action replace accepted diagnostic request model.
- [ ] Reject stale lookup, fallback, credential-dialog, and diagnostic continuation before credential access/mutation, page/controller activation, handler/worker creation, and I/O.
- [ ] Ensure stale work cannot alter request model, credentials, successful index/profile memory, page, room/VIP state, controller operations, or PDU enrichment.
- [ ] Keep normal lookup in memory; do not reread JSON, parse Excel, ping, or perform external I/O on Qt GUI thread.
- [ ] Do not create a second Matrix, PDU, DMP, codec, or audio-DSP operation-generation authority after accepted diagnostic dispatch enters its lifecycle.

## 10. Make PDU room-codec enrichment use exact accepted model identity

- [ ] Change pure related-codec resolver boundary to receive exact model and IP from accepted current `PDUController` context.
- [ ] Preserve complete zero/one/many IP cardinality before model inspection.
- [ ] Accept only closed PDU set: `Aten PE8208AV` and `Extron IPL T PCS4i`.
- [ ] Require one inventory record's exact canonical `diagnostic_model` to equal accepted PDU context model.
- [ ] Remove `device_kind == "pdu"` gate and do not identify PDU by kind, page, source text, or position.
- [ ] Add `PDU_MODEL_UNSUPPORTED` and `PDU_MODEL_MISMATCH` or exact specified equivalents.
- [ ] Ensure mismatch stops before related-codec credentials, handler/session construction, work submission, and network I/O.
- [ ] Preserve accepted-PDU-success gating, room-ID authority, one-codec multiplicity, dedicated read-only codec lane, stale rejection, and enrichment independence.
- [ ] Prove credential configuration for Aten/PCS4i never starts PDU refresh or enrichment.

## 11. Correct Aten consistency expectation

- [ ] Change `EXPECTED_KIND_BY_DIAGNOSTIC_MODEL["Aten PE8208AV"]` from `pdu` to `other`.
- [ ] Preserve exact `Тип модели -> device_kind` mapping, canonical fields, schema version, snapshot identity algorithm, and recognition rules.
- [ ] Ensure correct Aten and PCS4i rows with `device_kind = other` do not emit `KNOWN_MODEL_TYPE_MISMATCH`.
- [ ] Ensure genuinely conflicting Aten source type still emits consistency issue and never rewrites canonical fields.

## 12. Add synthetic regression coverage

- [ ] Add top-panel tests proving no permanent model selector, no `Устройство` label, and no default/previous widget model authority.
- [ ] Add registry integrity tests for all nine models, unique entries, registered screens, both fallback purposes, and no unknown default route.
- [ ] Add unique-IP diagnostic routing tests for Aten, PCS4i, TE40, IN1804, and representative Biamp/DMP routes.
- [ ] Prove `device_kind` alone selects nothing and does not block exact Aten/PCS4i dispatch.
- [ ] Add diagnostic fallback tests for inventory unavailable, not found, duplicate IP, null model, unsupported model, explicit selection, confirmation, Cancel, close, and no override after resolution.
- [ ] Add credential-flow tests for valid/invalid IP, every resolution outcome, exact inventory model, purpose-bound fallback, explicit selection, fallback Cancel/close, credential dialog Cancel/close, and saving exact bound model/IP only.
- [ ] Prove `Пароль` never uses previous diagnostic request, previous fallback, current page/title, first registry item, or Qt selector state.
- [ ] Prove no credential access/mutation before model confirmation and no ping, page transition, handler, worker/controller, I/O, or automatic diagnostic start at any credential-flow stage.
- [ ] Prove credential save changes candidate configuration only, does not mark success or persist profile, and invalidates only affected credential context.
- [ ] Add cross-purpose and stale fallback/credential-dialog-before-mutation tests.
- [ ] Add PDU enrichment tests for exact Aten/PCS4i context with kind `other`, duplicate IP, unsupported accepted model, null/unsupported/different inventory model, and zero codec I/O after mismatch.
- [ ] Add importer tests for correct Aten/PCS4i `other` consistency and conflicting Aten source type.
- [ ] Prove runtime never analyzes `source_model` and handlers/workers receive no candidate-model list.
- [ ] Preserve shared room/VIP presentation, credential fallback/success policy, and GUI responsiveness.
- [ ] Use only synthetic inventory/credentials; add no real organization data, snapshots, secrets, or Graphify output.

## 13. Update operational documentation and evidence

- [ ] Update `docs/equipment-inventory-runbook.md` with IP-only target flow, exact model authority, closed registry, diagnostic fallback/no override, model-bound `Пароль` flow, separate purpose generation, credential fallback/cancel/no-I/O/no-auto-start behavior, stale binding, PDU accepted-model matching, and Aten/PCS4i kind distinction.
- [ ] Update safe status text that references obsolete `PDU_KIND_MISMATCH` to approved model outcomes.
- [ ] Record implementation evidence with exact branch SHA, base, changed files, commands, exit codes, test counts, and limitations.
- [ ] Keep scope limited to approved composition/registry/UI/credential orchestration, resolver correction, importer correction, synthetic tests, runbook, and evidence.

## 14. Validate implementation

- [ ] Run focused tests with repository-supported Python and record exact results:

```powershell
<python> -m unittest tests.test_equipment_inventory tests.test_inventory_diagnostic_dispatch tests.test_inventory_credential_configuration tests.test_pdu_room_codec_enrichment -v
```

- [ ] Run all existing focused GUI/controller/credential regression modules touched by implementation and record exact commands/counts.
- [ ] Run canonical full offline suite:

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

- [ ] Review that no production workbook/snapshot, credentials, Graphify output, runtime source-text recognizer, kind-owned routing, handler-owned lookup, or unrelated files changed.

## 15. Publish for independent validation

- [ ] Create focused implementation commit(s) and push to `agent/inventory-driven-diagnostic-dispatch` without force-push.
- [ ] Verify local HEAD equals `origin/agent/inventory-driven-diagnostic-dispatch` after push.
- [ ] Do not self-issue final `APPROVE`; request independent validation from separate clean detached worktree created from exact remote HEAD.

## 16. Independent validation and archive applicability

- [ ] In clean detached worktree from exact `origin/agent/inventory-driven-diagnostic-dispatch`, verify local/remote SHA equality, clean status, commit subject, scope, and current PR state/base/head/Draft/mergeability.
- [ ] Independently rerun focused tests, GUI/controller/credential regressions, full offline tests, both strict OpenSpec validations, `git diff --check`, architecture correspondence, and protection checks without copying counts.
- [ ] Validator must not fix own findings or change production code, tests, proposal, design, tasks, or specs.
- [ ] Because change uses `MODIFIED` root requirements, perform disposable archive-applicability check outside feature branch: archive with `.\openspec.cmd archive inventory-driven-diagnostic-dispatch --yes` in throwaway worktree, inspect archive/root-spec diff against current root specs, run `.\openspec.cmd validate --all --strict`, and discard worktree without publishing output.
- [ ] Do not issue `READY FOR ARCHIVE` while any Critical, High, or Medium finding remains, a check fails, validated HEAD changes, worktree is dirty, or archive applicability is unproven.

## 17. Archive and merge after explicit permission

- [ ] Archive only after independent approval using repository-local `.\openspec.cmd archive inventory-driven-diagnostic-dispatch --yes`.
- [ ] Review archive/root-spec diff, run `.\openspec.cmd validate --all --strict`, full offline tests, and `git diff --check`.
- [ ] Create/push dedicated archive commit, then recheck exact remote archive HEAD and current `master`.
- [ ] Do not merge, close PR, remove Draft, or delete branches without user's direct permission.