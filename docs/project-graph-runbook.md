# Project Graph Runbook

## Purpose

The committed Graphify output is an optional read-only navigation index for a
frozen source baseline. It helps agents find candidate files, symbols, and
relationships. It is not architecture, validation evidence, workflow state, or
a substitute for reading current source and tests.

Authority order remains:

```text
RULES.md
current root OpenSpec specs
approved active change artifacts
specialized runbooks
current source and tests
Graphify navigation index
```

## Artifacts

Human-authored files:

```text
.graphifyignore
docs/project-graph-runbook.md
tools/refresh_project_graph.ps1
RULES.md
```

Generated committed files are allowlisted to:

```text
graphify-out/graph.json
graphify-out/manifest.json
graphify-out/GRAPH_REPORT.md
graphify-out/baseline.json
```

`graphify-out/graph.html`, semantic caches, API/cost outputs, converted
documents, logs, temporary probe files, package files, virtual environments,
hooks, MCP files, skills, and Graphify platform installs must not be committed.

## Baseline Metadata

`graphify-out/baseline.json` schema version 1:

```json
{
  "schema_version": 1,
  "generator": "graphify",
  "graphify_version": "0.9.26",
  "mode": "code-only",
  "indexed_source_commit": "<full-sha>",
  "indexed_branch": "master",
  "generated_at": "<UTC ISO-8601>",
  "graph_sha256": "<sha256>",
  "ignore_file_sha256": "<sha256>",
  "node_count": 0,
  "edge_count": 0
}
```

The indexed source commit is the exact source state that Graphify processed.
The following graph artifact commit may be newer than that source commit
because `graphify-out/` is excluded from the corpus.

## Initial Build

Use the isolated pinned tool:

```powershell
uv tool install graphifyy==0.9.26
graphify --version
graphify extract --help
graphify check-update --help
graphify update --help
```

Build only from a clean intended source state:

```powershell
.\tools\refresh_project_graph.ps1 -Mode Initial
```

The wrapper verifies the exact Graphify version, clean source state,
`.graphifyignore`, JSON validity, hashes, counts, output allowlist, no HTML,
secret/inventory/path scans, no hooks/watch/MCP/skills, and project-specific
smoke queries.

## Incremental Refresh

Use incremental refresh only after a completed approved workflow checkpoint,
normally after archive and post-archive validation:

```powershell
.\tools\refresh_project_graph.ps1 -Mode Incremental
```

The wrapper runs Graphify update-check before update. A normal active feature
implementation or validation session must not silently rebuild or refresh the
graph.

## Full Rebuild

Use full rebuild when the Graphify version changes, `.graphifyignore` changes,
source roots or package boundaries change, mass rename/delete occurs, ghost
nodes appear, integrity validation fails, topology unexpectedly shrinks, a
large-change threshold is reached, or an architect explicitly requests rebuild:

```powershell
.\tools\refresh_project_graph.ps1 -Mode FullRebuild
```

Full rebuild removes only generated `graphify-out/` contents and regenerates
from the clean source state. It does not commit or push.

## ChatGPT Consumption

When using the graph through GitHub without local Graphify:

1. Read `RULES.md` and applicable OpenSpec artifacts.
2. Read `graphify-out/baseline.json`.
3. Verify `indexed_source_commit`.
4. Read compact `graphify-out/GRAPH_REPORT.md`.
5. Search targeted nodes and edges in `graphify-out/graph.json`.
6. Identify candidate files and symbols.
7. Open actual source files through GitHub.
8. Check current branch, current SHA, and branch diff separately.
9. Make findings only from source evidence.

Do not paste the full `graph.json` into chat unless a reviewer explicitly asks.

## Local Codex Use

Local agents may use `graphify query`, `graphify affected`, `graphify path`, or
plain JSON search to narrow candidate files. Changed files in the current branch
must always be read directly. A stale or absent graph does not block ordinary
development or validation; it must be reported plainly.

## Active Change Behavior

During implementation and independent validation, treat the model as:

```text
indexed baseline + current branch diff + approved change artifacts
```

Do not update graph artifacts during ordinary code changes. Refresh only at an
approved checkpoint. Documentation-only changes that do not modify indexed
code, graph policy, source roots, ignore rules, wrapper behavior, or metadata
contract do not require a refresh unless the architect says otherwise.

## Confidence

Graph confidence categories, when present, mean:

- `EXTRACTED`: statically detected relationship, not architectural approval.
- `INFERRED`: navigation hypothesis only.
- `AMBIGUOUS`: never review evidence.

If Graphify uses different field names, do not invent missing confidence data.
Map the project meaning honestly over the actual schema and document the limit.

## Security

Never index or publish real credentials, `.env`, private keys, cookies,
Session IDs, CSRF/access tokens, `equipment_inventory.local.json`, production
Excel workbooks, real inventory snapshots, secret-bearing test output,
temporary worktree paths, Git credential storage, or user-specific absolute
paths.

The wrapper scans generated outputs for Windows drive paths, UNC paths, POSIX
checkout paths, `.env`, key markers, cookie/session/token terms, inventory
local filenames, Excel paths, `.worktrees`, and graph output self-indexing. If
a scan finds a sensitive value, report only the safe finding type and artifact
path, not the matched secret.

## Smoke Queries

Smoke queries must be project-specific and confirmed against source. Current
examples include:

```text
PDUController
InteractiveSessionController
EquipmentInventory
credential fallback ownership
PDU refresh to related codec status
```

For each query, record command exit code, relevant node, existing source file,
source confirmation, and honest confidence classification.

## Reproducibility

Acceptance compares topology rather than byte-for-byte output when timestamps
or ordering may vary:

- source-file set;
- node identities;
- extracted edges, or documented non-semantic differences;
- node/edge counts;
- absence of checkout-specific absolute paths;
- portability across worktrees.

Classify differences as `semantic`, `non-semantic`, or `unexpected`.
Unexpected differences block readiness.

## Troubleshooting

If Graphify generation fails, do not fabricate artifacts and do not edit
`graph.json` manually. Keep the safe error evidence, leave the graph absent or
explicitly stale, and return `CHANGES REQUIRED` unless an architect records a
temporary stale-graph exception.

If `graphify update` leaves deleted or renamed nodes behind, use the full
rebuild policy instead of accepting ghost topology.

## Windows Notes

Run from PowerShell at repository root. If execution policy blocks the wrapper,
use a process-scoped bypass:

```powershell
powershell -ExecutionPolicy Bypass -File .\tools\refresh_project_graph.ps1 -Mode Initial
```

Do not persist user-specific tool paths in repository files. Add tool bins to
`PATH` only for the current shell when needed.

## Upgrade Policy

Changing from `graphifyy==0.9.26` requires a new semantic OpenSpec change or an
explicit architect-approved amendment, release/help review, isolated
exact-version install, mandatory full rebuild, integrity/reproducibility
reruns, and updates to this runbook and baseline metadata.
