# Tasks: CloudLink Box 310 codec support

## 1. Confirm implementation baseline

- [ ] Read current `RULES.md` first, then `docs/equipment-inventory-runbook.md`, this approved change, and the affected root specs before modifying code or tests.
- [ ] Fetch GitHub and record exact `origin/master`, remote feature-branch HEAD, PR state/Draft/base/head when a PR exists, and any commits newer than the approved architecture HEAD before implementation.
- [ ] Confirm the implementation diff is limited to the Box 310 model-support surface, synthetic tests, runbook updates, and implementation evidence required by this change.
- [ ] Do not modify production inventory data, credential files, validation evidence from another session, or Graphify output.

## 2. Extend deterministic inventory recognition

- [ ] Add exact canonical `CloudLink Box 310` to the closed `DIAGNOSTIC_MODEL_RULES` registry with required components `cloudlink`, `box`, and `310`.
- [ ] Add `CloudLink Box 310 -> video_codec` to importer expected-kind consistency evidence without changing authoritative `Тип модели -> device_kind` mapping.
- [ ] Preserve independent `Модель`/`Наименование` evaluation, distinct-union ambiguity semantics, safe diagnostics, and all existing model rules unchanged.
- [ ] Update `docs/equipment-inventory-runbook.md` so its closed registry includes Box 310 and still prohibits undeclared aliases/fuzzy matching.

## 3. Extend exact application dispatch and page registration

- [ ] Add exact dispatch entry `CloudLink Box 310 -> codec -> cloudlink_bar_310` while leaving the Bar 310 entry unchanged.
- [ ] Add exact `CloudLink Box 310` to the codec equipment-page registration so registry integrity validation and fallback choices include it.
- [ ] Preserve the exact accepted model in request/action contexts; do not rewrite Box 310 to Bar 310 as application identity.
- [ ] Update model-specific ordinary refresh and credential-attempt restart gates so Box 310 selects the same existing Bar refresh implementation.

## 4. Reuse the Bar protocol with distinct Box identity

- [ ] Introduce one focused closed Bar/Box identity mapping or equivalent exact helper:

```text
CloudLink Bar 310 -> Huawei CloudLink Bar 310
CloudLink Box 310 -> Huawei CloudLink Box 310
```

- [ ] Reuse `CloudLinkBar310Handler`; do not create a duplicate Box handler or duplicate command map/polling plan.
- [ ] Pass the already assigned expected handler/display identity into the shared Bar protocol path so `get_status()` publishes the correct exact product identity.
- [ ] Make `HuaweiBar310Worker` validate the expected identity for its assigned model rather than hard-code Bar-only identity.
- [ ] Make `HuaweiBar310DataParser` validate and render the expected Bar or Box identity without accepting an unexpected family member or guessing from response text.
- [ ] Preserve every existing Bar status-polling endpoint, precedence, optional-failure, typed-failure, cleanup, redaction, and success-gating contract unchanged.

## 5. Extend all existing Bar capability gates to the closed Bar/Box family

- [ ] Make codec connection-profile ordering return the existing HTTPS:443 Bar profile for Box 310.
- [ ] Make interactive-session handler acquisition support Box 310 through `CloudLinkBar310Handler` while preserving the exact Box context model.
- [ ] Extend related-codec status support so Box 310 uses the same Bar call/presentation commands and normalization and remains reported as Box 310.
- [ ] Extend the existing Bar-supported SIP-server action to Box 310 through the same handler semantics.
- [ ] Review all exact `CloudLink Bar 310` model gates in current source/tests and change only gates that express shared Bar protocol capability; leave Bar-specific identity assertions intact where identity itself is the contract.

## 6. Preserve credential and recovery boundaries

- [ ] Resolve credentials for exact `CloudLink Box 310`; do not silently read or copy `CloudLink Bar 310` credential candidates.
- [ ] Keep successful credential index and saved connection profile keyed by exact model/IP so Bar and Box success evidence remain independent.
- [ ] Preserve application-owned credential fallback; handler, worker, parser, and interactive controller must not switch Bar/Box model after authentication, transport, protocol, parser, timeout, or ambiguous-result failure.
- [ ] Preserve stale-operation rejection before handler acquisition/I/O and all existing read-only/state-changing recovery restrictions.

## 7. Add focused regression coverage

- [ ] Extend `tests/test_equipment_inventory.py` with synthetic Box 310 positive forms from both approved evidence fields, separator/case/compact variants, boundary negatives, and Bar/Box distinction.
- [ ] Extend `tests/test_inventory_diagnostic_dispatch.py` and registry-integrity coverage so exact Box 310 resolves to `codec` and `cloudlink_bar_310`, while unknown models still fail closed.
- [ ] Add/extend focused Bar 310 polling tests proving Box uses the shared handler semantics but validates/renders `Huawei CloudLink Box 310`, Bar still renders `Huawei CloudLink Bar 310`, and mismatched expected identity is rejected.
- [ ] Add/extend connection-profile and interactive-session tests proving Box uses HTTPS:443 and `CloudLinkBar310Handler` without becoming Bar application identity.
- [ ] Add/extend related-codec enrichment/status tests proving a room codec with exact `CloudLink Box 310` can be queried with the existing Bar call/presentation semantics.
- [ ] Add/extend SIP action coverage if the existing Bar SIP action has focused tests.
- [ ] Prove Bar and Box credential indexes/profile persistence remain distinct exact-model keys.

## 8. Validate implementation

- [ ] Run focused inventory recognition tests:

```powershell
<python> -m unittest tests.test_equipment_inventory -v
```

- [ ] Run focused diagnostic dispatch and credential-configuration tests:

```powershell
<python> -m unittest tests.test_inventory_diagnostic_dispatch -v
<python> -m unittest tests.test_inventory_credential_configuration -v
```

- [ ] Run focused Bar/Box protocol, interactive, and related-codec tests using the actual current test module names after confirming them from the repository. At minimum include the existing Bar 310 status-polling suite and affected interactive/related-codec suites.
- [ ] Run the canonical full offline test suite and record exact passed/failed counts:

```powershell
<python> -m unittest discover -s tests -p "test_*.py" -v
```

- [ ] Run repository-local OpenSpec validation only:

```powershell
.\openspec.cmd validate cloudlink-box310-codec-support --strict
.\openspec.cmd validate --all --strict
```

- [ ] Run repository protection checks:

```powershell
git diff --check
git status --short
git diff --stat origin/master...HEAD
git diff --name-only origin/master...HEAD
```

- [ ] Review the final diff for production inventory, credential material, Graphify output, unrelated refactors, or duplicated Bar/Box protocol implementation.

## 9. Publish for independent validation

- [ ] Create focused implementation commit(s) only after the required tests/checks pass.
- [ ] Push the feature branch and report local HEAD, remote HEAD, base SHA, exact test counts, strict-validation results, and changed-file list.
- [ ] Do not self-approve the implementation and do not archive the change in the implementation session.

## 10. Independent validation and archive applicability

- [ ] Validate in a separate clean detached worktree created from the current remote feature-branch HEAD.
- [ ] Confirm local detached SHA equals remote branch SHA before tests.
- [ ] Re-run focused tests, full offline tests, both strict OpenSpec validations, and `git diff --check` without copying prior counts.
- [ ] Review implementation against this approved architecture and the current root specs; do not fix findings in the independent validation session.
- [ ] Because this change contains `MODIFIED Requirements`, perform a disposable archive-applicability check against the current root specs before `READY FOR ARCHIVE`; do not perform that check on the primary feature worktree.
- [ ] Issue `READY FOR ARCHIVE` only when the current remote HEAD is cleanly validated with no CRITICAL, HIGH, or MEDIUM findings and the archive delta is applicable.
