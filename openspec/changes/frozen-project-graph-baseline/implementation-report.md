# Implementation Report: Frozen Project Graph Baseline Corrections

This is implementation evidence after review status `CHANGES REQUIRED`, not an
independent validation verdict.

## Git and PR gate

- Repository: `Mihail-R-cdx/diag-module-ref`
- Branch: `agent/frozen-project-graph-baseline`
- PR: `#14` (`Architecture: frozen project graph baseline`)
- PR state before corrections: open Draft, base `master`, head `agent/frozen-project-graph-baseline`
- Previous reviewed HEAD: `1798dd8d74ff85b0af891682a18d6e37f116b6f7`
- Correction start HEAD: `1798dd8d74ff85b0af891682a18d6e37f116b6f7`
- Current `origin/master` used for initial baseline: `7e83d303dd997f59987d5007fff9ea56b7d10efc`
- Worktree before changes: clean; local HEAD matched remote feature HEAD.

## Findings closed

### HIGH 1 - inaccurate `indexed_branch`

- Fixed files: `tools/refresh_project_graph.ps1`, `graphify-out/baseline.json`, generated graph artifacts.
- Fix: initial mode now requires clean `SourceRoot` at the exact current `origin/master` SHA and records metadata from that source root, not the implementation worktree.
- Evidence: corrected baseline records `indexed_source_commit = 7e83d303dd997f59987d5007fff9ea56b7d10efc` and `indexed_branch = master`.

### HIGH 2 - publishable dirty mode

- Fixed file: `tools/refresh_project_graph.ps1`.
- Fix: removed `-AllowDirty`; all publish modes require a clean source Git worktree. Synthetic probes use committed disposable source states, not uncommitted bytes.
- Evidence: source clean checks run before and after generation; failed incremental candidates do not replace accepted output.

### HIGH 3 - unsafe generated freshness advice

- Fixed files: `tools/refresh_project_graph.ps1`, `graphify-out/GRAPH_REPORT.md`.
- Fix: wrapper replaces Graphify's generated freshness section with a project-owned frozen baseline policy and fails if `graphify update . after code changes` remains.
- Evidence: committed report contains `Frozen Baseline Policy` and the full source commit; forbidden advice is absent.

### HIGH 4 - incremental integrity enforcement

- Fixed files: `tools/refresh_project_graph.ps1`, `docs/project-graph-runbook.md`.
- Fix: incremental mode records previous-to-current Git diff, compares manifest source set, node identities, link identities, counts, deleted paths, renamed paths, ghost nodes, unchanged-node retention, and topology deltas. Failed integrity is nonzero and leaves the last accepted graph intact.
- Evidence: disposable add/rename/delete probes showed Graphify 0.9.26 `update` creates large topology jumps (`+1246`, `+1242`, `+1238` nodes for one source change); wrapper rejected each with `FullRebuild` guidance and preserved/restored accepted output.

### MEDIUM 1 - substring smoke tests

- Fixed file: `tools/refresh_project_graph.ps1`.
- Fix: smoke checks parse `graph.json` and verify concrete node ids, source paths, file existence, source confirmation, edge ids/types, and actual edge confidence.
- Evidence: wrapper output lists structured evidence for `PDUController`, `InteractiveSessionController`, `EquipmentInventory`, credential fallback ownership, accepted PDU refresh to enrichment, related-codec resolver, and related-codec status operation.

### MEDIUM 2 - confidence defaulting

- Fixed files: `tools/refresh_project_graph.ps1`, this report.
- Fix: edge confidence is read from the matched graph element; missing confidence is reported as `NOT_AVAILABLE`; no default `EXTRACTED` is assigned.
- Evidence: final smoke evidence reports exact edge confidence: `EXTRACTED` for confirmed extracted edges and `INFERRED` only for the related-codec status navigation hint with separate source confirmation.

### MEDIUM 3 - secret scan

- Fixed file: `tools/refresh_project_graph.ps1`.
- Fix: scans all four committed artifacts for absolute paths, local deployment files, private keys, bearer tokens, common API-key prefixes, assignment-like credential literals, URL credentials, token/cookie/session values, token-like high-entropy values, inventory/Excel names, temporary worktrees, and graph self-indexing. Findings print only category, artifact, JSON path, and redacted fingerprint.
- Evidence: final wrapper acceptance passed the strengthened scan.

## Baseline evidence

- Graphify version: `0.9.26`
- Source worktree: clean detached worktree at `7e83d303dd997f59987d5007fff9ea56b7d10efc`
- Indexed branch: `master`
- Mode: `code-only`
- Visualization: disabled/rejected; no `graph.html` committed
- Node count: `3106`
- Edge count: `8563`
- Graph SHA-256: `ccb423f992d3b1b147807fc177ca95e5d75c3f00fdba05045a51906383d972fe`
- Ignore SHA-256 from committed bytes: `755a9a84666cd0a4aa978a7de113d63fc4bb9afdd0f5b8979c6f6ac821249b9f`
- Generated allowlist: exactly `graphify-out/graph.json`, `graphify-out/manifest.json`, `graphify-out/GRAPH_REPORT.md`, and `graphify-out/baseline.json`.
- Graphify warning: `database.json` produced zero nodes; it is JSON data and no smoke evidence depends on it.

## Structured smoke evidence

- `PDUController`: node `gui_pdu_controller_pducontroller`, source `gui/pdu_controller.py`, type `code`, source-confirmed.
- `InteractiveSessionController`: node `core_interactive_session_interactivesessioncontroller`, source `core/interactive_session.py`, type `code`, source-confirmed.
- `EquipmentInventory`: node `core_equipment_inventory_equipmentinventory`, source `core/equipment_inventory.py`, type `code`, source-confirmed.
- `credential fallback ownership`: edge `core_interactive_session_interactivesessioncontroller_acquire_handler|calls|core_credentials_credentialattemptplan`, confidence `EXTRACTED`, source `core/interactive_session.py`, source-confirmed.
- `accepted PDU refresh to enrichment controller`: edge `gui_main_window_vcsdiagnosticapp_on_pdu_refresh_accepted_for_enrichment|calls|gui_main_window_vcsdiagnosticapp_pdu_room_codec_controller`, confidence `EXTRACTED`, source `gui/main_window.py`, source-confirmed.
- `related codec resolver navigation hint`: edge `core_room_context_roomcontextresolver_resolve_related_codec|references|core_equipment_inventory_equipmentinventory`, confidence `EXTRACTED`, source `core/room_context.py`, source-confirmed.
- `related codec status operation navigation hint`: edge `gui_pdu_room_codec_enrichment_pduroomcodecenrichmentcontroller_handler_factory|indirect_call|core_related_codec_status_relatedcodecstatusadapter_read_status`, confidence `INFERRED`, source `gui/pdu_room_codec_enrichment.py`, source-confirmed.

Confidence summary:

- `EXTRACTED`: `7464`
- `INFERRED`: `1099`
- `AMBIGUOUS`: `0`

## Reproducibility

A repeated initial build of exact `origin/master` was compared against the
previous accepted output.

- Source-file set diff: `0`
- Node identity diff: `0`
- Link identity diff: `0`
- Confidence category mismatch keys: `0`
- Counts before/after: `3106/8563` and `3106/8563`
- `.graphifyignore` byte hash before/after: `755a9a84666cd0a4aa978a7de113d63fc4bb9afdd0f5b8979c6f6ac821249b9f`
- Checkout path/probe scan: no hits.
- Byte-for-byte graph hash varies with Graphify clustering/report ordering; topology and source identities match.

## Incremental probe

Disposable source worktree started at `7e83d303dd997f59987d5007fff9ea56b7d10efc`.

1. Added committed `tools/graphify_probe_sample.py`.
2. Direct full rebuild for the disposable source confirmed node `GraphifyProbeNode` and probe file edges appear.
3. Incremental add from master baseline was rejected nonzero due unexpected topology jump `+1246` nodes for one changed source file; accepted master baseline remained intact.
4. Renamed the synthetic file and committed the disposable source change.
5. Incremental rename was rejected nonzero due unexpected topology jump `+1242` nodes for one changed source file; no failed candidate was published.
6. Deleted the synthetic file and committed the disposable source change.
7. Incremental delete was rejected nonzero due unexpected topology jump `+1238` nodes for one changed source file; no failed candidate was published.
8. Final accepted output was restored by a clean `Initial` build from exact `origin/master`.

No probe artifact is committed.

## Security and integration checks

Committed graph artifacts passed scans for Windows drive paths, UNC paths,
POSIX checkout paths, `.env`/local deployment files, private-key blocks, bearer
tokens, common API-key prefixes, assignment-like credential values, URL
credentials, token/cookie/session values, high-entropy token-like values, real
inventory local filename, Excel filenames, `.worktrees`, graph output
self-indexing, and probe paths.

No repository Graphify hooks, watch integration, MCP configuration, skill files,
`AGENTS.md`, `.codex/hooks.json`, or Graphify merge driver were created.

No production Python code, runtime tests, runtime dependencies, GUI code,
handlers, credentials/recovery behavior, real inventory, or root specs were
changed.
