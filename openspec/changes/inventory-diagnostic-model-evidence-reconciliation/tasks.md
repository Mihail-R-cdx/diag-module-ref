# Tasks: inventory-diagnostic-model-evidence-reconciliation

## 1. Confirm implementation baseline

- [ ] Перед началом работы прочитай RULES.md.
- [ ] Read `docs/equipment-inventory-runbook.md`, this approved change, the current root `equipment-inventory-snapshot` specification, importer source, and focused inventory tests.
- [ ] Fetch `origin`, record exact `origin/master`, remote feature-branch HEAD, PR state/Draft/base/head/mergeability, and inspect every commit newer than the approved architecture HEAD before implementation.
- [ ] Confirm the implementation diff is limited to the importer, synthetic inventory tests, runbook, and implementation evidence required by this change.

## 2. Implement two-field model evidence evaluation

- [ ] Preserve normalized `Наименование -> source_model` exactly as today.
- [ ] Apply the existing reviewed component recognizer independently to source `Модель` and source `Наименование`.
- [ ] Return the complete matching canonical-model set for each evidence field rather than selecting the first rule.
- [ ] Combine the two match sets by distinct canonical-model union.
- [ ] Publish one exact canonical `diagnostic_model` only when the combined union contains exactly one model.
- [ ] Emit only `UNMAPPED_DIAGNOSTIC_MODEL` when the combined union is empty.
- [ ] Emit only `AMBIGUOUS_DIAGNOSTIC_MODEL` when the combined union contains more than one model.
- [ ] Keep unmapped and ambiguous outcomes non-fatal when the canonical row is otherwise representable.

## 3. Preserve authorities and runtime boundaries

- [ ] Preserve the existing closed nine-model registry unchanged.
- [ ] Preserve Unicode NFC, trim, casefold, separator, letter/digit transition, and reviewed `4i` component semantics unchanged for both evidence fields.
- [ ] Preserve `Производитель` as optional consistency evidence only; it must not add, veto, remove, or select a match.
- [ ] Preserve exact `Тип модели -> device_kind` mapping and do not infer or override kind from recognized model evidence.
- [ ] Preserve canonical schema versions, exact record fields, deterministic snapshot identity, atomic publication, runtime loader behavior, and inventory query APIs.
- [ ] Do not add runtime fallback from `source_model`; GUI, dispatch, controllers, workers, handlers, credentials, PDU enrichment, and related-codec logic remain unchanged.
- [ ] Keep diagnostics safe: no complete source rows, production inventory, secrets, internal IPs, room IDs, MAC addresses, serial numbers, or unnecessary free-form evidence in normal output.

## 4. Add synthetic regression coverage

- [ ] Add a test for blank `Модель` plus recognized `Наименование` publishing the expected canonical model.
- [ ] Add a test for recognized `Модель` plus blank or unmapped `Наименование`.
- [ ] Add a test where both fields independently resolve to the same canonical model.
- [ ] Add a test where the two fields resolve to different canonical models and the result is ambiguous.
- [ ] Add a test where one field is internally ambiguous and the other agrees with one candidate; ambiguity must remain.
- [ ] Add a test where one field is internally ambiguous and the other is unmapped.
- [ ] Add a test where both fields are unmapped.
- [ ] Cover all nine existing canonical models through `Наименование` evidence.
- [ ] Repeat positive separator/compact/optional-suffix/accent cases and boundary-negative cases for `Наименование` evidence.
- [ ] Prove that each row receives exactly one mapped, unmapped, or ambiguous model-recognition outcome.
- [ ] Prove unchanged normalized `source_model`, unchanged `device_kind`, and deterministic snapshot identity.
- [ ] Prove runtime modules do not import or invoke importer recognition helpers.
- [ ] Use only synthetic values and verify that no production workbook or inventory data appears in fixtures or diagnostics.

## 5. Update operational documentation

- [ ] Update `docs/equipment-inventory-runbook.md` to describe independent `Модель` and `Наименование` evaluation and union cardinality.
- [ ] Document that `Наименование` remains canonical `source_model` while also supplying importer-only recognition evidence.
- [ ] Document disagreement and internal ambiguity as `AMBIGUOUS_DIAGNOSTIC_MODEL`.
- [ ] Document that unsupported models, including `Huawei CloudLink Box 610`, remain unmapped under this change.
- [ ] Keep runtime exact-only and require offline regeneration of `equipment_inventory.local.json` after deployment.

## 6. Validate implementation

- [ ] Run focused inventory tests with the repository-supported Python interpreter and record exact counts:

```powershell
<python> -m unittest tests.test_equipment_inventory -v
```

- [ ] Run inventory-driven dispatch and PDU enrichment regression modules to prove runtime behavior remains unchanged:

```powershell
<python> -m unittest tests.test_inventory_diagnostic_dispatch tests.test_pdu_room_codec_enrichment -v
```

- [ ] Run the canonical full offline test suite and record exact counts:

```powershell
<python> -m unittest discover -s tests -p "test_*.py" -v
```

- [ ] Run repository-local OpenSpec validation only:

```powershell
.\openspec.cmd validate inventory-diagnostic-model-evidence-reconciliation --strict
.\openspec.cmd validate --all --strict
```

- [ ] Run repository protection checks:

```powershell
git diff --check
git status --short
git diff --stat origin/master...HEAD
git diff --name-only origin/master...HEAD
```

- [ ] Review that no GUI, runtime dispatch, controllers, workers, handlers, credentials, production workbook/snapshot, Graphify output, or unrelated files changed.

## 7. Publish implementation for independent validation

- [ ] Create a focused implementation commit and push it to `agent/inventory-diagnostic-model-evidence-reconciliation` without force-push.
- [ ] Verify local HEAD equals `origin/agent/inventory-diagnostic-model-evidence-reconciliation` after push.
- [ ] Update implementation evidence with exact branch SHA, change base, commands, exit codes, test counts, and changed-file scope.
- [ ] Do not self-issue final `APPROVE`; request independent validation from a separate clean detached worktree created from the exact published remote branch HEAD.

## 8. Independent validation and archive applicability

- [ ] Independently repeat focused inventory tests, runtime regression modules, the full offline suite, both strict OpenSpec validations, `git diff --check`, architecture correspondence, scope review, safe-data checks, and local/remote SHA equality in a clean detached worktree from `origin/agent/inventory-diagnostic-model-evidence-reconciliation`.
- [ ] The validator must not fix findings or change production code, tests, proposal, design, tasks, or specs.
- [ ] Because this change uses `MODIFIED` root requirements, perform a disposable archive-applicability check outside the feature branch: archive with `.\openspec.cmd archive inventory-diagnostic-model-evidence-reconciliation --yes` in a throwaway worktree, inspect the archive/root-spec diff against the then-current root specification, run `.\openspec.cmd validate --all --strict`, and discard the worktree without publishing archive output.
- [ ] Do not issue `READY FOR ARCHIVE` while any Critical, High, or Medium finding remains, a required check fails, the validated remote HEAD changes, the validation worktree is dirty, or archive applicability is unproven.
