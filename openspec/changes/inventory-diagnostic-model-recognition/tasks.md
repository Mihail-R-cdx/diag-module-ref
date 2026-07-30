# Tasks: inventory-diagnostic-model-recognition

## 1. Confirm implementation baseline

- [x] Read current `RULES.md`, `docs/equipment-inventory-runbook.md`, this approved change, the current root `equipment-inventory-snapshot` specification, importer source, and focused inventory tests.
- [x] Fetch `origin`, record exact `origin/master`, remote feature-branch HEAD, PR state/Draft/base/head, and review any commits newer than the approved architecture HEAD before implementation.
- [x] Confirm the implementation diff is limited to the importer, synthetic inventory tests, runbook, and implementation evidence required by this change.

## 2. Implement deterministic component recognition

- [x] Replace exact manufacturer/model tuple lookup with a closed reviewable registry for the nine approved canonical models.
- [x] Normalize only source `Модель` evidence with NFC, trim, and casefold and extract exact components with the approved separator and letter/digit boundary semantics.
- [x] Support the approved mixed component `4i` without allowing arbitrary substring matching.
- [x] Evaluate all registry rules and classify zero, exactly one, or multiple matches independently of registry order.
- [x] Populate exact canonical `diagnostic_model` only for one match.
- [x] Emit only `UNMAPPED_DIAGNOSTIC_MODEL` for zero matches and only `AMBIGUOUS_DIAGNOSTIC_MODEL` for multiple matches.
- [x] Keep both issues non-fatal when the canonical row is otherwise representable.

## 3. Preserve existing authorities and safety

- [x] Make `Производитель` optional consistency evidence only; missing or conflicting manufacturer evidence must not veto or disambiguate model recognition.
- [x] Preserve `Наименование -> source_model` unchanged.
- [x] Preserve exact `Тип модели -> device_kind` mapping unchanged and do not infer or override kind from the recognized model.
- [x] Preserve canonical schema versions, exact record fields, deterministic snapshot identity, atomic publication, runtime loader behavior, and inventory query APIs.
- [x] Keep importer diagnostics safe: no complete source rows, real inventory, secrets, or unnecessary free-form model evidence in normal output.

## 4. Add regression coverage

- [x] Add synthetic positive tests for all nine canonical models and every alternative rule branch.
- [x] Cover case variation, separators, compact forms, optional suffix presence or absence, `forte`/`forté`, and missing manufacturer evidence.
- [x] Add boundary-negative tests for `LTE 40`, `TE200`, `TE401`, `IN18040`, `PE82080`, and `DMP640` or equivalent values proving exact component boundaries.
- [x] Add an ambiguity test where one source `Модель` value satisfies more than one registry rule and prove that no first rule is selected.
- [x] Prove that each row receives exactly one mapped, unmapped, or ambiguous recognition outcome.
- [x] Prove unchanged `source_model`, unchanged authoritative `device_kind`, deterministic ordering/identity, and absence of real organization data.

## 5. Update operational documentation

- [x] Update `docs/equipment-inventory-runbook.md` with the closed registry, component normalization, zero/one/many outcomes, safe issue codes, and offline snapshot-regeneration instructions.
- [x] Keep runtime exact-only and explicitly prohibit runtime dispatch from `source_model`, manufacturer text, or model evidence.

## 6. Validate implementation

- [x] Run focused inventory tests with the repository-supported Python interpreter and record the exact result count:

```powershell
<python> -m unittest tests.test_equipment_inventory -v
```

- [x] Run the canonical full offline test suite and record the exact passed/failed counts:

```powershell
<python> -m unittest discover -s tests -p "test_*.py" -v
```

- [x] Run repository-local OpenSpec validation only:

```powershell
.\openspec.cmd validate inventory-diagnostic-model-recognition --strict
.\openspec.cmd validate --all --strict
```

- [x] Run repository protection checks:

```powershell
git diff --check
git status --short
git diff --stat origin/master...HEAD
git diff --name-only origin/master...HEAD
```

- [x] Review that no production workbook, generated deployment snapshot, credentials, Graphify output, GUI, handlers, runtime dispatch, or unrelated files changed.

## 7. Publish implementation for independent validation

- [ ] Create a focused implementation commit and push it to `agent/inventory-diagnostic-model-recognition` without force-push.
- [ ] Verify local HEAD equals `origin/agent/inventory-diagnostic-model-recognition` after push.
- [ ] Update implementation evidence with exact branch SHA, change base, commands, exit codes, test counts, and changed-file scope.
- [ ] Do not issue final `APPROVE`; request independent validation from a separate clean detached worktree created from the published remote branch HEAD.

## 8. Independent validation and archive applicability

- [ ] Independently repeat the focused `unittest` command, the full `unittest discover` command, both strict OpenSpec validations, `git diff --check`, scope review, secret/inventory checks, and local/remote SHA equality in a clean detached worktree from `origin/agent/inventory-diagnostic-model-recognition`.
- [ ] Because this change uses a `MODIFIED` root requirement, perform a disposable archive-applicability check outside the feature branch: archive the change with the repository-local wrapper in a throwaway worktree, inspect the resulting archive/root-spec diff against the then-current root specification, run `validate --all --strict`, and discard the worktree without publishing archive output.
- [ ] Do not issue `READY FOR ARCHIVE` while any Critical, High, or Medium finding remains, any required check fails, the validated remote HEAD changed, or archive applicability is unproven.
