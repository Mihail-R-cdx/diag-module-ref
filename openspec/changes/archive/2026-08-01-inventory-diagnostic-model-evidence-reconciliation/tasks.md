# Tasks: inventory-diagnostic-model-evidence-reconciliation

## 1. Confirm architecture baseline

- [ ] Перед началом работы прочитай RULES.md.
- [ ] Read `docs/equipment-inventory-runbook.md`, the current root `equipment-inventory-snapshot` specification, this complete change, `tools/import_equipment_inventory.py`, and current importer tests.
- [ ] Fetch `origin` and record exact `origin/master`, remote feature-branch HEAD, PR state, Draft state, base/head, mergeability, and every commit newer than the last reviewed architecture HEAD.
- [ ] Confirm the change remains architecture-only before approval and changes only files under `openspec/changes/inventory-diagnostic-model-evidence-reconciliation/`.
- [ ] Confirm the approved scope is only independent `Модель`/`Наименование` evidence evaluation and distinct-union reconciliation.
- [ ] Confirm standalone GUI, Qt worker, file selection, expanded run-report contract, report export, second Excel input, switch-port enrichment, runtime dispatch, credentials, controllers, workers, handlers, PDU enrichment, production inventory, and Graphify artifacts are outside this change.

## 2. Validate and review the architecture-only change

- [ ] In a clean checkout at the exact published remote branch HEAD, run:

```powershell
git diff --check
.\openspec.cmd validate inventory-diagnostic-model-evidence-reconciliation --strict
.\openspec.cmd validate --all --strict
```

- [ ] Review proposal, design, tasks, and specification delta against current `RULES.md`, the root specification, importer source/tests, and the equipment-inventory runbook.
- [ ] Do not begin implementation until the exact remote architecture HEAD receives `APPROVE`.

## 3. Implement independent evidence evaluation

- [x] Preserve normalized `Наименование -> source_model` exactly as today.
- [x] Apply the existing reviewed component normalization and extractor independently to source `Модель` and source `Наименование`.
- [x] Evaluate every closed-registry rule for each evidence field and return the complete immutable canonical-model match set for that field.
- [x] Do not prematurely collapse one field to a single mapped/unmapped/ambiguous result before cross-field reconciliation.
- [x] Form the distinct canonical union of both complete match sets.
- [x] Publish one exact canonical `diagnostic_model` only when the union contains exactly one model.
- [x] Emit only `UNMAPPED_DIAGNOSTIC_MODEL` when the union is empty.
- [x] Emit only `AMBIGUOUS_DIAGNOSTIC_MODEL` when the union contains more than one model.
- [x] Preserve ambiguity when one field is internally ambiguous even if the other field agrees with one candidate.
- [x] Keep unmapped and ambiguous outcomes non-fatal when the canonical row is otherwise representable.

## 4. Preserve authorities and boundaries

- [x] Preserve the existing closed nine-model registry unchanged.
- [x] Preserve Unicode NFC, trim, casefold, separator, letter/digit transition, and reviewed mixed `4i` component semantics for both evidence fields.
- [x] Preserve `Производитель` as optional consistency evidence only; it must not add, veto, remove, or select a model match.
- [x] Preserve exact `Тип модели -> device_kind` mapping and expected-kind consistency behavior.
- [x] Preserve canonical schema versions, exact record fields, deterministic snapshot identity, atomic publication, runtime loader behavior, and inventory query APIs.
- [x] Keep runtime exact-only: do not add recognition or fallback from `source_model`, `Модель`, `Производитель`, or other free-form evidence in diagnostic runtime code.
- [x] Do not change diagnostic GUI, dispatch, credentials, controllers, workers, handlers, transports, PDU enrichment, or related-codec status logic.
- [x] Do not add a converter GUI, PyQt import, worker thread, expanded report model, report export, second source workbook, or switch-port fields.
- [x] Keep diagnostics safe: no complete source fields, complete rows, production inventory, internal IPs, room IDs, MAC addresses, serial numbers, or unnecessary free-form evidence in normal output.

## 5. Add synthetic regression coverage

- [x] Add blank `Модель` plus recognized `Наименование` coverage.
- [x] Add recognized `Модель` plus blank `Наименование` coverage.
- [x] Add recognized `Модель` plus unmapped `Наименование` coverage.
- [x] Add both fields resolving to the same canonical model.
- [x] Add fields resolving to different canonical models and prove ambiguity.
- [x] Add internally ambiguous `Модель` plus one agreeing `Наименование`; ambiguity must remain.
- [x] Add internally ambiguous `Наименование` plus one agreeing `Модель`; ambiguity must remain.
- [x] Add one internally ambiguous field plus an unmapped field.
- [x] Add both fields unmapped.
- [x] Cover all nine existing canonical models through `Наименование` evidence.
- [x] Repeat positive separator, compact-form, optional-suffix, accent-alternative, and boundary-negative cases for `Наименование` evidence.
- [x] Prove exactly one mapped/unmapped/ambiguous outcome per row.
- [x] Prove normalized `source_model` remains unchanged.
- [x] Prove authoritative `device_kind` and known-model mismatch behavior remain unchanged.
- [x] Prove schema version, canonical record shape, and deterministic snapshot identity remain unchanged.
- [x] Use only synthetic values and ensure no production workbook or inventory data enters fixtures, reports, screenshots, or logs.

## 6. Update operational documentation

- [x] Update `docs/equipment-inventory-runbook.md` so `Модель` and `Наименование` are documented as independent importer-only recognition evidence.
- [x] Document complete per-field match sets and distinct-union cardinality.
- [x] Document that `Наименование` remains canonical `source_model` and does not become runtime authority.
- [x] Document that `Производитель` remains optional non-authoritative consistency evidence.
- [x] Document that the closed registry, exact boundary matching, `device_kind`, schema, and runtime behavior remain unchanged.
- [x] Document that unsupported models, including `Huawei CloudLink Box 610`, remain unmapped.
- [x] Require offline regeneration of `equipment_inventory.local.json` after deployment.
- [x] Do not document a standalone GUI or second workbook in this change.

## 7. Validate implementation

- [x] Run focused importer tests with the repository-supported Python interpreter and record exact counts:

```powershell
<python> -m unittest tests.test_equipment_inventory -v
```

- [x] Run runtime dispatch and PDU enrichment regressions:

```powershell
<python> -m unittest tests.test_inventory_diagnostic_dispatch tests.test_pdu_room_codec_enrichment -v
```

- [x] Run the canonical full offline test suite and record exact counts:

```powershell
<python> -m unittest discover -s tests -p "test_*.py" -v
```

- [x] Run repository-local OpenSpec validation only:

```powershell
.\openspec.cmd validate inventory-diagnostic-model-evidence-reconciliation --strict
.\openspec.cmd validate --all --strict
```

- [x] Run repository-protection checks:

```powershell
git diff --check
git status --short
git diff --stat origin/master...HEAD
git diff --name-only origin/master...HEAD
```

- [x] Review that only the approved importer, focused importer tests, runbook, and change evidence changed after implementation.
- [x] Review that no converter GUI, Qt code, expanded report refactor, second workbook support, runtime code, operational data, installer output, Graphify output, or unrelated files changed.

## 8. Publish implementation for independent validation

- [ ] Create focused implementation commit(s) and push to `agent/inventory-diagnostic-model-evidence-reconciliation` without force-push.
- [ ] Verify local HEAD equals `origin/agent/inventory-diagnostic-model-evidence-reconciliation` after push.
- [ ] Update implementation evidence with exact branch SHA, change base, commands, exit codes, test counts, and changed-file scope.
- [ ] Do not self-issue final `APPROVE`; request independent validation from a separate clean detached worktree created from the exact published remote branch HEAD.

## 9. Independent validation and archive applicability

- [ ] Independently repeat focused importer tests, runtime regression modules, the full offline suite, both strict OpenSpec validations, `git diff --check`, architecture correspondence, safe-data checks, scope review, and local/remote SHA equality in a clean detached worktree from `origin/agent/inventory-diagnostic-model-evidence-reconciliation`.
- [ ] The validator must not fix findings or change production code, tests, proposal, design, tasks, or specs.
- [ ] Because this change uses `MODIFIED` root requirements, perform a disposable archive-applicability check outside the feature branch: archive with `.\openspec.cmd archive inventory-diagnostic-model-evidence-reconciliation --yes` in a throwaway worktree, inspect the archive/root-spec diff against the then-current root specification, run `.\openspec.cmd validate --all --strict`, and discard the worktree without publishing archive output.
- [ ] Do not issue `READY FOR ARCHIVE` while any Critical, High, or Medium finding remains, a required check fails, the validated remote HEAD changes, the validation worktree is dirty, or archive applicability is unproven.

## 10. Archive and post-archive checks

- [ ] Archive only after an independent verdict permits archive and only with explicit user authorization.
- [ ] Use only:

```powershell
.\openspec.cmd archive inventory-diagnostic-model-evidence-reconciliation --yes
```

- [ ] Review the archive and root-spec diff and confirm it contains only the approved two-field evidence reconciliation.
- [ ] Run post-archive checks:

```powershell
.\openspec.cmd validate --all --strict
<python> -m unittest discover -s tests -p "test_*.py" -v
git diff --check
git status --short
```

- [ ] Create and push a dedicated archive commit without force-push.
- [ ] Before any merge, recheck current `master`, exact remote archive HEAD, PR state, Draft state, base/head, mergeability, and new commits.
- [ ] Do not mark ready, merge, close the PR, or delete branches without explicit user authorization.
