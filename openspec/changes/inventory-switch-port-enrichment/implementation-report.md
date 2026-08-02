# Implementation Report: inventory-switch-port-enrichment

## Baseline

- Repository: `Mihail-R-cdx/diag-module-ref`
- Branch: `agent/inventory-switch-port-enrichment`
- PR: `#23`
- Change base / `origin/master`: `6b6df6ce20740312b6fccde9670de33c1913e40f`
- Approved architecture SHA: `382e7cc990f838bbca83f1d322b101a62fcbc904`
- Starting implementation remote HEAD for this correction session: `89671b25de6aeb8853776a10cff45bf4955046d3`
- Local implementation worktree: `.worktrees/impl-inventory-switch-port-enrichment`
- Python: `C:\Users\Mih\AppData\Local\Programs\Python\Python312\python.exe` (`Python 3.12.9`)
- Node: `v20.19.0`
- npm: `10.8.2`

## Implementation Commits After Architecture Approval

- `76c5d5ae167b0be55da47b1d2a422f1ee26c7779` - `Implement inventory switch port enrichment`
- `89671b25de6aeb8853776a10cff45bf4955046d3` - `Record inventory switch enrichment publication`
- Correction commit subject: `Fix inventory switch enrichment review findings`

The correction commit containing this report is recorded by subject. The exact final published remote HEAD is recorded in the session report and PR body after push.

## Correction Session

Independent read-only review of `89671b25de6aeb8853776a10cff45bf4955046d3` returned `CHANGES REQUIRED`. This correction session addresses the three Medium findings and the Low evidence finding without expanding the approved OpenSpec contract.

Fixed findings:

- Source-side network candidate multiplicity is classified before primary-side inventory matching. Repeated identical usable candidates and conflicting distinct candidates now emit source-side issues even when the network MAC is absent from primary inventory or primary inventory has duplicate records for the MAC.
- Workbook parsing now has a controlled `WorkbookReadError` boundary for expected filesystem, ZIP, XML, and XLSX package-structure failures. Primary workbook failures use the existing safe fatal contract; network workbook failures use the structured fatal network issue. The importer does not catch arbitrary programming errors at the import boundary.
- Atomic publication regression coverage now proves candidate snapshot validation failures and output publication failures preserve previous output, avoid schema-v2 fallback, and avoid publishing invalid or partial candidate JSON.
- Evidence was refreshed to remove stale architecture-only/final-readiness wording and record the correction scope.

## Changed Files In Correction Commit

- `tools/import_equipment_inventory.py`: reorders network-source multiplicity classification, keeps primary-side ambiguity/unmatched handling independent, and adds the controlled workbook parsing boundary.
- `tests/test_inventory_switch_port_enrichment.py`: adds source/primary multiplicity review regressions, malformed XLSX package fatal regressions, valid package preservation coverage, and atomic publication failure coverage.
- `openspec/changes/inventory-switch-port-enrichment/tasks.md`: records correction-session tasks while leaving independent validation and archive tasks unchecked.
- `openspec/changes/inventory-switch-port-enrichment/implementation-report.md`: this refreshed evidence report.

Forbidden scope remained untouched: no `core/equipment_inventory.py` correction-session change, no GUI, no Qt worker, no switch diagnostics, no network operations, no production workbook, no production JSON, no Graphify, no installer, no archive, no merge, and no PR ready-for-review transition.

## New Regression Coverage

- Unmatched network MAC plus repeated identical usable candidates: emits `DUPLICATE_SWITCH_CONNECTION_SOURCE` and `NETWORK_MAC_NOT_IN_INVENTORY`; publishes schema v3; enriches no record; row order does not affect result.
- Unmatched network MAC plus conflicting distinct candidates: emits `AMBIGUOUS_SWITCH_CONNECTION` and `NETWORK_MAC_NOT_IN_INVENTORY`; publishes schema v3; enriches no record; row order does not affect result.
- Duplicate primary MAC plus repeated identical usable candidates: emits `DUPLICATE_SWITCH_CONNECTION_SOURCE` and `AMBIGUOUS_INVENTORY_MAC_FOR_SWITCH`; publishes schema v3; enriches no record; row order does not affect result.
- Duplicate primary MAC plus conflicting distinct candidates: emits `AMBIGUOUS_SWITCH_CONNECTION` and `AMBIGUOUS_INVENTORY_MAC_FOR_SWITCH`; publishes schema v3; enriches no record; row order does not affect result.
- Malformed network XLSX packages: valid ZIP without `xl/workbook.xml`, missing worksheet member, shared-string index out of range, and invalid row number all return structured fatal `NETWORK_WORKBOOK_UNREADABLE`, leave previous output unchanged, and do not fall back to schema v2.
- Valid network workbook package still publishes schema v3 with switch enrichment.
- Candidate snapshot validation failure returns fatal `CANDIDATE_SNAPSHOT_INVALID`, leaves previous output byte-for-byte unchanged, and does not call the publication writer.
- Output publication failure returns fatal `OUTPUT_PUBLICATION_FAILED`, leaves previous output byte-for-byte unchanged, and removes the temporary candidate file.

## Validation Commands

All commands were run from `.worktrees/impl-inventory-switch-port-enrichment`.

```powershell
& 'C:\Users\Mih\AppData\Local\Programs\Python\Python312\python.exe' --version
```

- Result: `Python 3.12.9`
- Exit code: 0

```powershell
& 'C:\Users\Mih\AppData\Local\Programs\Python\Python312\python.exe' -m py_compile core\equipment_inventory.py tools\import_equipment_inventory.py tests\test_equipment_inventory.py tests\test_inventory_switch_port_enrichment.py
```

- Result: passed
- Exit code: 0

```powershell
& 'C:\Users\Mih\AppData\Local\Programs\Python\Python312\python.exe' -m unittest tests.test_inventory_switch_port_enrichment -v
```

- Result: passed
- Exact count: 14 tests
- Exit code: 0

```powershell
& 'C:\Users\Mih\AppData\Local\Programs\Python\Python312\python.exe' -m unittest tests.test_equipment_inventory -v
```

- Result: passed
- Exact count: 25 tests
- Exit code: 0

```powershell
& 'C:\Users\Mih\AppData\Local\Programs\Python\Python312\python.exe' -m unittest tests.test_inventory_diagnostic_dispatch tests.test_inventory_credential_configuration tests.test_pdu_room_codec_enrichment tests.test_equipment_room_context_gui -v
```

- Result: passed
- Exact count: 98 tests
- Exit code: 0

```powershell
& 'C:\Users\Mih\AppData\Local\Programs\Python\Python312\python.exe' -m unittest discover -s tests -p "test_*.py" -v
```

- Result: passed
- Exact count: 609 tests
- Exit code: 0

```powershell
$nodeExe = $env:DIAG_NODE_HOME; $nodeDir = Split-Path -Parent $nodeExe; & $nodeExe --version
```

- Result: `v20.19.0`
- Exit code: 0

```powershell
$nodeExe = $env:DIAG_NODE_HOME; $nodeDir = Split-Path -Parent $nodeExe; & (Join-Path $nodeDir 'npm.cmd') --version
```

- Result: `10.8.2`
- Exit code: 0

```powershell
$nodeExe = $env:DIAG_NODE_HOME; $nodeDir = Split-Path -Parent $nodeExe; $env:Path = "$nodeDir;$env:Path"; .\openspec.cmd validate inventory-switch-port-enrichment --strict
```

- Result: passed; `Change 'inventory-switch-port-enrichment' is valid`
- Exit code: 0

```powershell
$nodeExe = $env:DIAG_NODE_HOME; $nodeDir = Split-Path -Parent $nodeExe; $env:Path = "$nodeDir;$env:Path"; .\openspec.cmd validate --all --strict
```

- Result: passed; 11 items passed, 0 failed
- Exit code: 0

```powershell
git diff --check
```

- Result: passed
- Exit code: 0

```powershell
git status --short
```

- Result before correction commit:
  - `M openspec/changes/inventory-switch-port-enrichment/implementation-report.md`
  - `M openspec/changes/inventory-switch-port-enrichment/tasks.md`
  - `M tests/test_inventory_switch_port_enrichment.py`
  - `M tools/import_equipment_inventory.py`
- Exit code: 0

```powershell
git diff --stat
```

- Result before correction commit: 4 files changed, 359 insertions(+), 98 deletions(-)
- Exit code: 0

```powershell
git diff --name-only
```

- Result before correction commit:
  - `openspec/changes/inventory-switch-port-enrichment/implementation-report.md`
  - `openspec/changes/inventory-switch-port-enrichment/tasks.md`
  - `tests/test_inventory_switch_port_enrichment.py`
  - `tools/import_equipment_inventory.py`
- Exit code: 0

## Pending Independent Work

- Independent validation was not performed in this implementation correction session.
- Archive applicability was not performed in this implementation correction session.
- The PR remains Draft unless changed by an authorized reviewer or maintainer.
