# Implementation Report: Frozen Project Graph Baseline

This is implementation evidence, not an independent validation verdict.

## Git and PR gate

- Repository: `Mihail-R-cdx/diag-module-ref`
- PR: `#14` (`Architecture: frozen project graph baseline`)
- PR state before implementation: open Draft, base `master`, head `agent/frozen-project-graph-baseline`
- Architecture HEAD verified before work: `6108c8529717bb0d7b92c9d98196396d26f370de`
- Implementation worktree started clean from `origin/agent/frozen-project-graph-baseline`

## Tool evidence

- `uv`: `0.11.32`
- Graphify package: `graphifyy==0.9.26`
- Graphify CLI: `graphify`
- `graphify --version`: `graphify 0.9.26`
- `graphify extract --help`, `graphify check-update --help`, and `graphify update --help` returned exit code `0`; this build prints detailed command help through `graphify --help`.
- Actual initial build syntax used by the wrapper:

```powershell
graphify extract <repo-root> --code-only --no-viz
graphify cluster-only <repo-root> --no-viz --no-label
```

`extract` produced `graph.json`, `manifest.json`, and `.graphify_analysis.json`; Graphify then instructed running `cluster-only` to generate `GRAPH_REPORT.md`. The wrapper runs that command and removes uncommitted cache/analysis/root/html/dated-backup byproducts before acceptance.

## Implemented files

- `RULES.md`: short frozen-baseline policy section.
- `.graphifyignore`: repository-specific ignore policy for graph generation.
- `docs/project-graph-runbook.md`: authority, operation, staleness, security, reproducibility, ChatGPT/Codex use, and upgrade policy.
- `tools/refresh_project_graph.ps1`: pinned explicit initial/incremental/full-rebuild wrapper.
- `graphify-out/baseline.json`
- `graphify-out/graph.json`
- `graphify-out/GRAPH_REPORT.md`
- `graphify-out/manifest.json`

No production Python code, runtime tests, or runtime dependencies were changed.

## Baseline evidence

- Indexed source commit: `e9cce86df67386b4e4c5c15cbe250bdc4d563e08`
- Graphify version: `0.9.26`
- Mode: `code-only`
- Visualization: disabled/rejected; no `graph.html` committed
- Node count: `3122`
- Edge count: `8590`
- Graph SHA-256: `3bc1e404206c14075f50ac0d52e67bdbce438b9bad90597d7a727edcb4db2b30`
- Ignore SHA-256 from generation worktree bytes: `755a9a84666cd0a4aa978a7de113d63fc4bb9afdd0f5b8979c6f6ac821249b9f`
- Generated allowlist: exactly the four approved files.
- Graphify warning: `database.json` produced zero nodes; it is a JSON data file and no required source symbol depends on it for this baseline.

## Security and integration checks

Committed graph artifacts scanned clean for:

- Windows drive paths
- UNC paths
- POSIX checkout paths
- `.env`
- private-key markers
- `equipment_inventory.local.json`
- Excel file references
- `.worktrees`
- graph output self-reference

No repository Graphify hooks, watch integration, MCP configuration, skill files, `AGENTS.md`, `.codex/hooks.json`, or Graphify merge driver were created.

Vocabulary terms such as password, token, cookie, session, and csrf appear as project source vocabulary in the code graph. The wrapper reports them as review notes rather than secret matches; no secret value was printed or committed.

## Smoke queries

Each query exited through the wrapper with exit code `0`, found graph content, and was confirmed in source:

- `PDUController` -> `gui/pdu_controller.py`, confidence `EXTRACTED`
- `InteractiveSessionController` -> `core/interactive_session.py`, confidence `EXTRACTED`
- `EquipmentInventory` -> `core/equipment_inventory.py`, confidence `EXTRACTED`
- `Credential` -> `core/credentials.py`, confidence `EXTRACTED`
- `RelatedCodec` -> `core/related_codec_status.py`, confidence `EXTRACTED`

Graph confidence summary:

- `EXTRACTED`: `7491`
- `INFERRED`: `1099`
- `AMBIGUOUS`: `0`

## Reproducibility

A disposable worktree at the same exact source commit was generated and compared.

- Source-file set: identical (`121` vs `121`)
- Node identities: identical (`3122` vs `3122`, diff `0`)
- Link identities: identical (`8590` vs `8590`, diff `0`)
- Node count: identical (`3122`)
- Edge count: identical (`8590`)
- Absolute checkout paths: absent after report sanitization
- Difference classification: non-semantic byte/hash differences only, caused by Graphify clustering ordering/report metadata and working-tree line ending differences for `.graphifyignore`; topology matched exactly.

## Incremental probe

Disposable probe in a separate worktree:

1. Added `tools/graphify_probe_sample.py` with `GraphifyProbeNode`.
2. `graphify check-update .` exit code `0`.
3. `graphify update .` exit code `0`.
4. `GraphifyProbeNode` appeared in `graph.json`.
5. Deleted the synthetic file.
6. `graphify check-update .` exit code `0`.
7. `graphify update .` exit code `0`.
8. `GraphifyProbeNode` disappeared from `graph.json`.

Observed Graphify behavior: `update` emits `graph.html` and dated backup byproducts and produced a large topology jump in the disposable probe. The wrapper removes byproducts and the runbook documents full-rebuild escalation when topology changes unexpectedly. No probe files or probe graph state are committed.
