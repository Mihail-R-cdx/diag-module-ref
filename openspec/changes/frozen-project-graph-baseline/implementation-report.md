# Implementation Report: Frozen Project Graph Baseline Architecture Amendment

This is implementation evidence after review status `CHANGES REQUIRED -
ARCHITECTURE AMENDMENT REQUIRED`, not an independent validation verdict.

## Git and PR gate

- Repository: `Mihail-R-cdx/diag-module-ref`
- Branch: `agent/frozen-project-graph-baseline`
- PR: `#14` (`Architecture: frozen project graph baseline`)
- PR state at session start: open Draft, base `master`, head
  `agent/frozen-project-graph-baseline`
- Session start HEAD: `aab0ae74a4e8ac43b1143b8adb03c0a2e94a7f69`
- `origin/master` used for bootstrap source:
  `7e83d303dd997f59987d5007fff9ea56b7d10efc`
- Worktree before changes: clean; local branch matched remote feature HEAD.

## Architecture amendment

The previous workflow treated the first committed graph as if it were the final
baseline for future changes. That was wrong because the final baseline must be
built after independent review, archive, and post-archive validation, from a
source commit that already contains the Graphify wrapper, runbook, policy, and
archived OpenSpec state.

The workflow now has two explicit stages:

- `bootstrap`: pre-archive, non-final graph used only to review the Graphify
  integration, wrapper, corpus filters, security checks, smoke queries, and
  reproducibility.
- `final`: post-archive graph built from the reviewed source commit; it is
  committed as a graph-only commit and becomes the merge HEAD only after
  lightweight graph integrity review.

No final graph was built in this session. No archive, merge, branch deletion,
force-push, or Ready-for-review transition was performed.

## Fixes made

- Replaced ambiguous metadata schema v1 with schema v2:
  `schema_version`, `generator`, `graphify_version`, `mode`,
  `baseline_stage`, `indexed_source_commit`, `indexed_source_ref`,
  `target_branch`, `generated_at`, `graph_sha256`, `ignore_file_sha256`,
  `node_count`, and `edge_count`.
- Removed branch inference from SHA equality. The wrapper now requires
  `BaselineStage`, `SourceRef`, and `TargetBranch`, and verifies that
  `SourceRef` resolves to source `HEAD`.
- Added final-mode source checks for `tools/refresh_project_graph.ps1`,
  `.graphifyignore`, `docs/project-graph-runbook.md`, and `RULES.md`.
- Marked the current generated report as `Bootstrap Frozen Baseline Policy`,
  pre-archive, non-final, and not the navigation baseline for the next change.
- Clarified publication as validated backup-and-restore copy with restoration
  on failure; no single-step filesystem rename guarantee is claimed.
- Split tasks into implementation-review work and unchecked post-review final
  baseline/merge checkpoint work.

## Current bootstrap graph evidence

- Graphify version: `0.9.26`
- Baseline stage: `bootstrap`
- Source ref: `origin/master`
- Target branch: `master`
- Indexed source commit: `7e83d303dd997f59987d5007fff9ea56b7d10efc`
- Mode: `code-only`
- Visualization: disabled/rejected; no `graph.html` committed
- Node count: `3106`
- Edge count: `8563`
- Graph SHA-256: `b2923dd69102df258c62f0e216c12694256fe8676982f680d1ed8c0df74bc8e9`
- Ignore SHA-256: `755a9a84666cd0a4aa978a7de113d63fc4bb9afdd0f5b8979c6f6ac821249b9f`
- Generated allowlist: exactly `graphify-out/graph.json`,
  `graphify-out/manifest.json`, `graphify-out/GRAPH_REPORT.md`, and
  `graphify-out/baseline.json`.
- Graphify warning: `database.json` produced zero nodes; it is JSON data and no
  smoke evidence depends on it.

## Structured smoke evidence

- `PDUController`: node `gui_pdu_controller_pducontroller`, source
  `gui/pdu_controller.py`, type `code`, source-confirmed.
- `InteractiveSessionController`: node
  `core_interactive_session_interactivesessioncontroller`, source
  `core/interactive_session.py`, type `code`, source-confirmed.
- `EquipmentInventory`: node `core_equipment_inventory_equipmentinventory`,
  source `core/equipment_inventory.py`, type `code`, source-confirmed.
- `credential fallback ownership`: edge
  `core_interactive_session_interactivesessioncontroller_acquire_handler|calls|core_credentials_credentialattemptplan`,
  confidence `EXTRACTED`, source `core/interactive_session.py`,
  source-confirmed.
- `accepted PDU refresh to enrichment controller`: edge
  `gui_main_window_vcsdiagnosticapp_on_pdu_refresh_accepted_for_enrichment|calls|gui_main_window_vcsdiagnosticapp_pdu_room_codec_controller`,
  confidence `EXTRACTED`, source `gui/main_window.py`, source-confirmed.
- `related codec resolver navigation hint`: edge
  `core_room_context_roomcontextresolver_resolve_related_codec|references|core_equipment_inventory_equipmentinventory`,
  confidence `EXTRACTED`, source `core/room_context.py`, source-confirmed.
- `related codec status operation navigation hint`: edge
  `gui_pdu_room_codec_enrichment_pduroomcodecenrichmentcontroller_handler_factory|indirect_call|core_related_codec_status_relatedcodecstatusadapter_read_status`,
  confidence `INFERRED`, source `gui/pdu_room_codec_enrichment.py`,
  source-confirmed.

Confidence summary: `EXTRACTED=7464`, `INFERRED=1099`, `AMBIGUOUS=0`.

## Reproducibility

A repeated bootstrap build of exact `origin/master` was compared against the
previous accepted bootstrap output.

- Source-file set diff: `0`
- Node identity diff: `0`
- Link identity diff: `0`
- Counts before/after: `3106/8563 -> 3106/8563`
- `.graphifyignore` byte hash before/after:
  `755a9a84666cd0a4aa978a7de113d63fc4bb9afdd0f5b8979c6f6ac821249b9f ->
  755a9a84666cd0a4aa978a7de113d63fc4bb9afdd0f5b8979c6f6ac821249b9f`
- Checkout path/probe scan: no committed hits.
- Byte-for-byte graph hash may vary with Graphify clustering/report ordering;
  topology and source identities match.

## Incremental probe

Disposable source worktree started at
`7e83d303dd997f59987d5007fff9ea56b7d10efc`.

1. Added committed `tools/graphify_probe_sample.py`.
2. Incremental add was rejected nonzero due unexpected topology node delta
   `+1246` for one source change; accepted bootstrap baseline remained intact.
3. Renamed the synthetic file and committed the disposable source change.
4. Incremental rename was rejected nonzero due unexpected topology node delta
   `+1246` for one source change; accepted bootstrap baseline remained intact.
5. Deleted the synthetic file and committed the disposable source change.
6. Incremental delete was rejected nonzero due unexpected topology node delta
   `+1242`; accepted bootstrap baseline remained intact.

No probe artifact is committed. Temporary source/probe worktrees were removed.

## Security and integration checks

Committed graph artifacts passed wrapper scans for Windows drive paths, UNC
paths, POSIX checkout paths, `.env`/local deployment files, private-key blocks,
bearer tokens, common API-key prefixes, assignment-like credential values, URL
credentials, token/cookie/session values, high-entropy token-like values, real
inventory local filename, Excel filenames, temporary worktrees, and graph
output self-indexing.

No repository Graphify hooks, watch integration, MCP configuration, skill files,
`AGENTS.md`, `.codex/hooks.json`, or Graphify merge driver were created.

No production Python code, runtime tests, runtime dependencies, GUI code,
handlers, credentials/recovery behavior, real inventory, or root specs were
changed.

## Fresh validation

- `graphify --version`: `graphify 0.9.26`
- `.\openspec.cmd validate frozen-project-graph-baseline --strict`: passed.
- `.\openspec.cmd validate --all --strict`: `10 passed, 0 failed`.
- `python -X faulthandler -m unittest discover -s tests -p "test_*.py"`:
  `Ran 474 tests in 40.314s`, `OK`.
- `git diff --check`: passed.
- `git status --short`: only intended implementation-review files modified
  before commit.

Implementation status: `READY FOR INDEPENDENT REVIEW` after commit, push, and
PR body update. PR must remain Draft.
