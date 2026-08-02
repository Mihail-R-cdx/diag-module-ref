# Tasks: inventory-switch-port-enrichment

## 1. Confirm architecture baseline

- [x] Перед началом работы прочитай RULES.md.
- [x] Read `docs/equipment-inventory-runbook.md`, the current root `equipment-inventory-snapshot` specification, this complete change, `core/equipment_inventory.py`, `tools/import_equipment_inventory.py`, and current inventory tests.
- [x] Fetch `origin` and record exact `origin/master`, remote feature-branch HEAD, PR state, Draft state, base/head, mergeability, and every commit newer than the last reviewed architecture HEAD.
- [x] Confirm the change remains architecture-only before approval and changes only files under `openspec/changes/inventory-switch-port-enrichment/`.
- [x] Confirm the inspected network workbook contract is sheet `Устройства` with exact required headers `MAC-адрес`, `IP коммутатора`, and `Порт`.
- [x] Confirm sheet `Изменения` and column `Корректная запись` are completely outside reconciliation authority.
- [x] Confirm standalone GUI, Qt worker, switch diagnostics, network I/O, main diagnostic GUI display, production data, and Graphify artifacts are outside this change.

## 2. Validate and review the architecture-only change

- [ ] In a clean checkout at the exact published remote branch HEAD, run:

```powershell
git diff --check
.\openspec.cmd validate inventory-switch-port-enrichment --strict
.\openspec.cmd validate --all --strict
```

- [ ] Review proposal, design, tasks, and specification delta against current `RULES.md`, the root specification, current source/tests, the equipment-inventory runbook, and the confirmed workbook structure.
- [ ] Confirm the delta modifies existing requirement `Existing schema-v1 snapshots remain loadable` under its exact identity and preserves existing scenario headings.
- [ ] Confirm the delta modifies existing requirement `Structured importer diagnostics and source-row accounting` rather than creating an overlapping diagnostics contract.
- [ ] Do not begin implementation until the exact remote architecture HEAD receives `APPROVE`.

## 3. Add the exact two-source configuration contract

- [x] Preserve current explicit primary source and output path behavior.
- [x] Add exact module configuration variable `NETWORK_XLSX_PATH`.
- [x] Add exact environment variable `DIAG_INVENTORY_NETWORK_XLSX`.
- [x] Add exact CLI option `--network-source`.
- [x] Add exact direct API keyword `network_source_path`.
- [x] Preserve the exact direct API signature:

```python
import_equipment_inventory(
    source_path,
    *,
    network_source_path=None,
    output_path=None,
    generated_at=None,
)
```

- [x] Resolve every configured path to an absolute `Path` before workbook I/O.
- [x] Use priority: explicit API/CLI network source, environment variable, explicitly configured module value, then no network source.
- [x] Preserve intentional one-source mode and schema-v2 output when no network source is configured.
- [x] Select schema-v3 mode only when a network source is explicitly configured.
- [x] If a configured network source has a path/configuration, read, worksheet, or required-header failure, return a fatal structured result and do not silently downgrade to schema v2.
- [x] Do not invent equivalent public names or commit user-specific workbook paths.

## 4. Read the closed network source contract

- [x] Read only sheet `Устройства` as current network state.
- [x] Require exact headers `MAC-адрес`, `IP коммутатора`, and `Порт` for a configured network source.
- [x] Treat missing or ambiguous `Устройства` selection and missing or ambiguous required headers as fatal source-structure failures.
- [x] Ignore sheet `Изменения` completely.
- [x] Ignore `Корректная запись` completely regardless of presence or value.
- [x] Ignore all other network-workbook columns for canonical authority and reconciliation.
- [x] Account for every non-empty network source row through a usable candidate, a structured issue, or both.
- [x] Keep workbook parsing inside the offline importer boundary and do not add spreadsheet dependencies to normal diagnostic runtime imports.

## 5. Normalize and reconcile switch connections

- [x] Normalize network `MAC-адрес` with the existing canonical MAC normalizer.
- [x] Exclude missing/invalid network MAC from joining and emit a safe structured non-fatal issue.
- [x] Normalize `IP коммутатора` as canonical dotted-decimal IPv4 or null plus `INVALID_SWITCH_IP` for invalid non-blank input.
- [x] Normalize `Порт` with Unicode NFC and trim; preserve case and internal text; empty becomes null.
- [x] Treat switch port as opaque text and do not parse vendor-specific interface grammar.
- [x] Create a usable connection candidate only when at least one normalized switch field is non-null.
- [x] For valid MAC plus blank/empty switch IP and blank/empty port, create no candidate and emit non-fatal `EMPTY_SWITCH_CONNECTION`.
- [x] For invalid non-blank switch IP plus null port, create no candidate, retain `INVALID_SWITCH_IP`, and do not require an additional `EMPTY_SWITCH_CONNECTION`.
- [x] Ensure a no-candidate row does not create multiplicity or ambiguity with another usable row for the same MAC.
- [x] Build complete multiplicity-preserving groups for primary records and usable network candidates by canonical MAC.
- [x] Enrich only when exactly one primary record and exactly one distinct usable normalized network connection candidate share the MAC.
- [x] Preserve valid partial unique candidates and emit `MISSING_SWITCH_PORT`, `MISSING_SWITCH_IP`, or `INVALID_SWITCH_IP` as applicable.
- [x] Collapse repeated identical usable normalized pairs to one distinct candidate and emit `DUPLICATE_SWITCH_CONNECTION_SOURCE`.
- [x] For multiple distinct usable normalized pairs, set both switch fields null and emit `AMBIGUOUS_SWITCH_CONNECTION`.
- [x] For duplicate primary records sharing one MAC, enrich none and emit `AMBIGUOUS_INVENTORY_MAC_FOR_SWITCH`.
- [x] Report network MACs absent from primary inventory as `NETWORK_MAC_NOT_IN_INVENTORY`.
- [x] Do not emit a per-record error solely because a primary record has null MAC or no matching usable network row.
- [x] Do not use device IP, room, manufacturer, model, source metadata, confidence, `Корректная запись`, or row order as join or tie-break authority.

## 6. Add strict canonical schema v3

- [x] Add nullable runtime fields `switch_ip_address` and `switch_port` to `EquipmentRecord` with null defaults for older schemas.
- [x] Define schema-v3 exact record fields as schema v2 plus the two switch fields.
- [x] Validate non-null `switch_ip_address` as canonical IPv4.
- [x] Validate non-null `switch_port` as normalized non-empty canonical text.
- [x] Include both switch fields in deterministic schema-v3 snapshot identity.
- [x] Preserve schema-v1 identity and exact record validation unchanged.
- [x] Preserve schema-v2 identity and exact record validation unchanged.
- [x] Load schema v1 with `room_vip`, `switch_ip_address`, and `switch_port` adapted to null.
- [x] Load schema v2 with source `room_vip` and both switch fields adapted to null.
- [x] Load schema v3 with all fields validated and exposed.
- [x] Reject hybrid v1/v2 records containing later-version fields and reject undeclared schema versions.
- [x] Preserve canonical root `source_row_count` as the primary equipment-workbook row count in schema v3.
- [x] Keep network row counts only in `ImportResult`/report metadata and outside `snapshot_id`.

## 7. Preserve runtime and application boundaries

- [x] Preserve existing inventory indexes and public query APIs unchanged.
- [x] Do not add runtime lookup indexes by switch IP or switch port.
- [x] Do not use switch fields in diagnostic dispatch, page routing, credential selection, room context, PDU-room-codec enrichment, handlers, controllers, workers, transports, or device I/O.
- [x] Preserve all existing diagnostic-model, `device_kind`, room identity, VIP aggregation, and multiplicity contracts.
- [x] Keep network workbook handling and reconciliation out of normal application startup and runtime modules.

## 8. Preserve the exact fatal/non-fatal and reporting boundary

- [x] Preserve existing `ImportResult` and report fields.
- [x] Add safe optional network-run context and counts needed to validate schema-v3 conversion.
- [x] Keep report metadata outside canonical records, canonical `source_row_count`, and snapshot identity.
- [x] Treat exactly these network conditions as fatal: configuration/path failure, workbook unreadable, missing/ambiguous `Устройства`, missing/ambiguous required headers, candidate schema validation failure, and publication failure.
- [x] Treat row-level missing/invalid MAC, `EMPTY_SWITCH_CONNECTION`, invalid/missing switch fields, duplicate identical candidates, conflicting candidates, duplicate primary MAC, and unmatched network MAC as non-fatal.
- [x] Ensure row-level ambiguity never blocks an otherwise valid schema-v3 snapshot and never causes schema-v2 fallback.
- [x] Expose only safe issue class/code, sheet, row, and canonical record context where applicable.
- [x] Do not dump complete source rows, workbook contents, production snapshot contents, or unrelated topology.
- [x] Validate the complete candidate through the runtime loader before publication.
- [x] Preserve atomic publication and the previous valid output on every fatal primary, network, candidate-validation, or output-write failure.

## 9. Add synthetic regression coverage

- [x] Prove existing one-source conversion still emits schema v2 with unchanged identity behavior.
- [x] Prove exact public configuration surfaces: `NETWORK_XLSX_PATH`, `DIAG_INVENTORY_NETWORK_XLSX`, `--network-source`, and `network_source_path`.
- [x] Prove explicit valid two-source conversion emits schema v3.
- [x] Test exact network sheet and header requirements, including ambiguous source structure.
- [x] Prove `Изменения` and `Корректная запись` have no effect.
- [x] Test canonical MAC joins across every currently supported textual form.
- [x] Prove no join occurs by IP, room, manufacturer, model, source order, or ignored metadata.
- [x] Test one unique complete connection and unique partial connections.
- [x] Test valid MAC with blank switch IP and blank port produces `EMPTY_SWITCH_CONNECTION` and no candidate.
- [x] Test an empty/no-candidate row does not create ambiguity with one usable row for the same MAC.
- [x] Test invalid non-blank switch IP plus blank port creates no candidate and reports `INVALID_SWITCH_IP` without requiring duplicate empty-row reporting.
- [x] Test invalid/missing network MAC, switch IP, and switch port.
- [x] Test duplicate identical usable network rows and conflicting distinct usable network rows.
- [x] Test duplicate primary MAC and network MAC absent from primary inventory.
- [x] Test the exact fatal/non-fatal table and prove row-level issues do not block schema-v3 publication.
- [x] Test v1/v2/v3 loader compatibility, preserving existing scenario identities, strict hybrid rejection, and unsupported schema rejection.
- [x] Prove schema-v3 identity changes when either switch field changes.
- [x] Prove schema-v3 `source_row_count` remains the primary-workbook count while network count stays report-only.
- [x] Prove existing inventory indexes and public queries are unchanged.
- [x] Run existing diagnostic dispatch, credential, room-context, and PDU enrichment regressions.
- [x] Prove previous output survives every fatal two-source failure.
- [x] Use only synthetic addresses, identifiers, and workbooks.

## 10. Update operational documentation

- [x] Update `docs/equipment-inventory-runbook.md` with the optional second-source boundary and the two explicit conversion modes.
- [x] Document exact public names `NETWORK_XLSX_PATH`, `DIAG_INVENTORY_NETWORK_XLSX`, `--network-source`, and `network_source_path` plus the approved direct API signature.
- [x] Document exact sheet/header authority and complete ignoring of `Изменения` and `Корректная запись`.
- [x] Document MAC-only reconciliation, candidate eligibility, `EMPTY_SWITCH_CONNECTION`, multiplicity, ambiguity, partial values, and issue codes.
- [x] Document the exact fatal/non-fatal boundary.
- [x] Document schema-v3 fields, deterministic identity, v1/v2 backward loading, and primary-only `source_row_count` semantics.
- [x] Document that runtime behavior and existing queries remain unchanged.
- [x] Document local regeneration requirements without committing production workbooks or snapshots.
- [x] Do not document the future standalone GUI as implemented in this change.

## 11. Validate implementation

- [x] Run focused inventory/importer tests and record exact counts:

```powershell
<python> -m unittest tests.test_equipment_inventory -v
```

- [x] If a separate focused module is added, run it explicitly and record exact counts:

```powershell
<python> -m unittest tests.test_inventory_switch_port_enrichment -v
```

- [x] Run runtime regression modules:

```powershell
<python> -m unittest tests.test_inventory_diagnostic_dispatch tests.test_inventory_credential_configuration tests.test_pdu_room_codec_enrichment tests.test_equipment_room_context_gui -v
```

- [x] Run the canonical full offline suite:

```powershell
<python> -m unittest discover -s tests -p "test_*.py" -v
```

- [x] Run repository-local OpenSpec validation only:

```powershell
.\openspec.cmd validate inventory-switch-port-enrichment --strict
.\openspec.cmd validate --all --strict
```

- [x] Run repository-protection checks:

```powershell
git diff --check
git status --short
git diff --stat origin/master...HEAD
git diff --name-only origin/master...HEAD
```

- [x] Review that only approved importer, loader, focused tests, runbook, and change evidence changed.
- [x] Review that no GUI, switch network operations, production data, Graphify output, or unrelated files changed.

## 12. Publish implementation for independent validation

- [x] Create focused implementation commit(s) and push to `agent/inventory-switch-port-enrichment` without force-push.
- [x] Verify local HEAD equals `origin/agent/inventory-switch-port-enrichment` after push.
- [x] Record exact change base, branch SHA, commands, exit codes, test counts, and changed-file scope.
- [x] Do not self-issue final `APPROVE`; request independent validation in a clean detached worktree from the exact published remote HEAD.

## 13. Independent validation and archive applicability

- [ ] Independently repeat focused tests, runtime regressions, the full offline suite, both strict OpenSpec validations, `git diff --check`, architecture correspondence, safe-data checks, scope review, and local/remote SHA equality.
- [ ] The validator must not fix findings or change production code, tests, proposal, design, tasks, or specs.
- [ ] Because this change adds and modifies root requirements, perform a disposable archive-applicability check outside the feature branch with:

```powershell
.\openspec.cmd archive inventory-switch-port-enrichment --yes
```

- [ ] Inspect the disposable archive/root-spec diff and confirm exact requirement/scenario identity preservation, run `.\openspec.cmd validate --all --strict`, and discard the throwaway worktree without publishing archive output.
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
