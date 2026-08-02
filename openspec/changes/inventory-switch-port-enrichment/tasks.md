# Tasks: inventory-switch-port-enrichment

## 1. Confirm architecture baseline

- [ ] Перед началом работы прочитай RULES.md.
- [ ] Read `docs/equipment-inventory-runbook.md`, the current root `equipment-inventory-snapshot` specification, this complete change, `core/equipment_inventory.py`, `tools/import_equipment_inventory.py`, and current inventory tests.
- [ ] Fetch `origin` and record exact `origin/master`, remote feature-branch HEAD, PR state, Draft state, base/head, mergeability, and every commit newer than the last reviewed architecture HEAD.
- [ ] Confirm the change remains architecture-only before approval and changes only files under `openspec/changes/inventory-switch-port-enrichment/`.
- [ ] Confirm the inspected network workbook contract is sheet `Устройства` with exact required headers `MAC-адрес`, `IP коммутатора`, and `Порт`.
- [ ] Confirm sheet `Изменения` and column `Корректная запись` are completely outside reconciliation authority.
- [ ] Confirm standalone GUI, Qt worker, switch diagnostics, network I/O, main diagnostic GUI display, production data, and Graphify artifacts are outside this change.

## 2. Validate and review the architecture-only change

- [ ] In a clean checkout at the exact published remote branch HEAD, run:

```powershell
git diff --check
.\openspec.cmd validate inventory-switch-port-enrichment --strict
.\openspec.cmd validate --all --strict
```

- [ ] Review proposal, design, tasks, and specification delta against current `RULES.md`, the root specification, current source/tests, the equipment-inventory runbook, and the confirmed workbook structure.
- [ ] Do not begin implementation until the exact remote architecture HEAD receives `APPROVE`.

## 3. Add explicit two-source conversion configuration

- [ ] Preserve current explicit primary source and output path behavior.
- [ ] Add an optional explicitly supplied network-workbook path to direct API and CLI/config resolution.
- [ ] Resolve every configured path to an absolute `Path` before workbook I/O.
- [ ] Preserve intentional one-source mode and schema-v2 output when no network source is configured.
- [ ] Select schema-v3 mode only when a network source is explicitly configured.
- [ ] If a configured network source is missing, unreadable, or structurally invalid, return a fatal structured result and do not silently downgrade to schema v2.
- [ ] Do not commit user-specific workbook paths.

## 4. Read the closed network source contract

- [ ] Read only sheet `Устройства` as current network state.
- [ ] Require exact headers `MAC-адрес`, `IP коммутатора`, and `Порт` for a configured network source.
- [ ] Ignore sheet `Изменения` completely.
- [ ] Ignore `Корректная запись` completely regardless of presence or value.
- [ ] Ignore all other network-workbook columns for canonical authority and reconciliation.
- [ ] Account for non-empty network source rows through a usable candidate or a structured issue.
- [ ] Keep workbook parsing inside the offline importer boundary and do not add spreadsheet dependencies to normal diagnostic runtime imports.

## 5. Normalize and reconcile switch connections

- [ ] Normalize network `MAC-адрес` with the existing canonical MAC normalizer.
- [ ] Exclude missing/invalid network MAC from joining and emit a safe structured non-fatal issue.
- [ ] Normalize `IP коммутатора` as canonical dotted-decimal IPv4 or null plus `INVALID_SWITCH_IP` for invalid non-blank input.
- [ ] Normalize `Порт` with Unicode NFC and trim; preserve case and internal text; empty becomes null.
- [ ] Treat switch port as opaque text and do not parse vendor-specific interface grammar.
- [ ] Build complete multiplicity-preserving groups for primary records and network candidates by canonical MAC.
- [ ] Enrich only when exactly one primary record and exactly one distinct normalized network connection candidate share the MAC.
- [ ] Preserve valid partial unique candidates and emit the applicable missing-field issue.
- [ ] Collapse repeated identical normalized network pairs to one distinct candidate and emit `DUPLICATE_SWITCH_CONNECTION_SOURCE`.
- [ ] For multiple distinct normalized network pairs, set both switch fields null and emit `AMBIGUOUS_SWITCH_CONNECTION`.
- [ ] For duplicate primary records sharing one MAC, enrich none and emit `AMBIGUOUS_INVENTORY_MAC_FOR_SWITCH`.
- [ ] Report network MACs absent from primary inventory as `NETWORK_MAC_NOT_IN_INVENTORY`.
- [ ] Do not emit a per-record error solely because a primary record has null MAC or no matching network row.
- [ ] Do not use device IP, room, manufacturer, model, source metadata, confidence, `Корректная запись`, or row order as join or tie-break authority.

## 6. Add strict canonical schema v3

- [ ] Add nullable runtime fields `switch_ip_address` and `switch_port` to `EquipmentRecord` with null defaults for older schemas.
- [ ] Define schema-v3 exact record fields as schema v2 plus the two switch fields.
- [ ] Validate non-null `switch_ip_address` as canonical IPv4.
- [ ] Validate non-null `switch_port` as normalized non-empty canonical text.
- [ ] Include both switch fields in deterministic schema-v3 snapshot identity.
- [ ] Preserve schema-v1 identity and exact record validation unchanged.
- [ ] Preserve schema-v2 identity and exact record validation unchanged.
- [ ] Load schema v1 with `room_vip`, `switch_ip_address`, and `switch_port` adapted to null as applicable.
- [ ] Load schema v2 with both switch fields adapted to null.
- [ ] Load schema v3 with all fields validated and exposed.
- [ ] Reject hybrid v1/v2 records containing v3 fields and reject undeclared schema versions.

## 7. Preserve runtime and application boundaries

- [ ] Preserve existing inventory indexes and public query APIs unchanged.
- [ ] Do not add runtime lookup indexes by switch IP or switch port.
- [ ] Do not use switch fields in diagnostic dispatch, page routing, credential selection, room context, PDU-room-codec enrichment, handlers, controllers, workers, transports, or device I/O.
- [ ] Preserve all existing diagnostic-model, `device_kind`, room identity, VIP aggregation, and multiplicity contracts.
- [ ] Keep network workbook handling and reconciliation out of normal application startup and runtime modules.

## 8. Extend safe structured conversion reporting

- [ ] Preserve existing `ImportResult` and report fields.
- [ ] Add safe optional network-run context and counts needed to validate schema-v3 conversion.
- [ ] Keep report metadata outside snapshot identity.
- [ ] Expose only safe issue class/code, sheet, row, and canonical record context where applicable.
- [ ] Do not dump complete source rows, workbook contents, production snapshot contents, or unrelated topology.
- [ ] Validate the complete candidate through the runtime loader before publication.
- [ ] Preserve atomic publication and the previous valid output on every fatal primary, network, candidate-validation, or output-write failure.

## 9. Add synthetic regression coverage

- [ ] Prove existing one-source conversion still emits schema v2 with unchanged identity behavior.
- [ ] Prove explicit valid two-source conversion emits schema v3.
- [ ] Test exact network sheet and header requirements.
- [ ] Prove `Изменения` and `Корректная запись` have no effect.
- [ ] Test canonical MAC joins across every currently supported textual form.
- [ ] Prove no join occurs by IP, room, manufacturer, model, source order, or ignored metadata.
- [ ] Test one unique complete connection and unique partial connections.
- [ ] Test invalid/missing network MAC, switch IP, and switch port.
- [ ] Test duplicate identical network rows and conflicting distinct network rows.
- [ ] Test duplicate primary MAC and network MAC absent from primary inventory.
- [ ] Test v1/v2/v3 loader compatibility, strict hybrid rejection, and unsupported schema rejection.
- [ ] Prove schema-v3 identity changes when either switch field changes.
- [ ] Prove existing inventory indexes and public queries are unchanged.
- [ ] Run existing diagnostic dispatch, credential, room-context, and PDU enrichment regressions.
- [ ] Prove previous output survives every fatal two-source failure.
- [ ] Use only synthetic addresses, identifiers, and workbooks.

## 10. Update operational documentation

- [ ] Update `docs/equipment-inventory-runbook.md` with the optional second-source boundary and the two explicit conversion modes.
- [ ] Document exact sheet/header authority and complete ignoring of `Изменения` and `Корректная запись`.
- [ ] Document MAC-only reconciliation, multiplicity, ambiguity, partial values, and issue codes.
- [ ] Document schema-v3 fields, deterministic identity, and v1/v2 backward loading.
- [ ] Document that runtime behavior and existing queries remain unchanged.
- [ ] Document local regeneration requirements without committing production workbooks or snapshots.
- [ ] Do not document the future standalone GUI as implemented in this change.

## 11. Validate implementation

- [ ] Run focused inventory/importer tests and record exact counts:

```powershell
<python> -m unittest tests.test_equipment_inventory -v
```

- [ ] If a separate focused module is added, run it explicitly and record exact counts:

```powershell
<python> -m unittest tests.test_inventory_switch_port_enrichment -v
```

- [ ] Run runtime regression modules:

```powershell
<python> -m unittest tests.test_inventory_diagnostic_dispatch tests.test_inventory_credential_configuration tests.test_pdu_room_codec_enrichment tests.test_equipment_room_context_gui -v
```

- [ ] Run the canonical full offline suite:

```powershell
<python> -m unittest discover -s tests -p "test_*.py" -v
```

- [ ] Run repository-local OpenSpec validation only:

```powershell
.\openspec.cmd validate inventory-switch-port-enrichment --strict
.\openspec.cmd validate --all --strict
```

- [ ] Run repository-protection checks:

```powershell
git diff --check
git status --short
git diff --stat origin/master...HEAD
git diff --name-only origin/master...HEAD
```

- [ ] Review that only approved importer, loader, focused tests, runbook, and change evidence changed.
- [ ] Review that no GUI, switch network operations, production data, Graphify output, or unrelated files changed.

## 12. Publish implementation for independent validation

- [ ] Create focused implementation commit(s) and push to `agent/inventory-switch-port-enrichment` without force-push.
- [ ] Verify local HEAD equals `origin/agent/inventory-switch-port-enrichment` after push.
- [ ] Record exact change base, branch SHA, commands, exit codes, test counts, and changed-file scope.
- [ ] Do not self-issue final `APPROVE`; request independent validation in a clean detached worktree from the exact published remote HEAD.

## 13. Independent validation and archive applicability

- [ ] Independently repeat focused tests, runtime regressions, the full offline suite, both strict OpenSpec validations, `git diff --check`, architecture correspondence, safe-data checks, scope review, and local/remote SHA equality.
- [ ] The validator must not fix findings or change production code, tests, proposal, design, tasks, or specs.
- [ ] Because this change adds and modifies root requirements, perform a disposable archive-applicability check outside the feature branch with:

```powershell
.\openspec.cmd archive inventory-switch-port-enrichment --yes
```

- [ ] Inspect the disposable archive/root-spec diff, run `.\openspec.cmd validate --all --strict`, and discard the throwaway worktree without publishing archive output.
- [ ] Do not issue `READY FOR ARCHIVE` while any Critical, High, or Medium finding remains, a required check fails, the validated remote HEAD changes, the worktree is dirty, or archive applicability is unproven.

## 14. Archive and post-archive checks

- [ ] Archive only after an independent approving verdict and explicit user authorization.
- [ ] Use only:

```powershell
.\openspec.cmd archive inventory-switch-port-enrichment --yes
```

- [ ] Review the archive and root-spec diff and confirm it contains only approved second-source, reconciliation, schema-v3, loader-compatibility, and reporting contracts.
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
