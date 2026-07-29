# Project Graph Runbook

## Purpose

The committed Graphify output is an optional read-only navigation index for a
frozen source baseline. It helps agents find candidate files, symbols, and
relationships. It is not architecture, validation evidence, workflow state, or
a substitute for reading current source and tests.

Authority order remains:

```text
RULES.md
approved OpenSpec
current source/tests
Git diff
runbooks
Graphify
agent reports
```

An absent, invalid, or stale graph does not block ordinary OpenSpec
architecture, implementation, independent validation, archive, post-archive
checks, or merge. Ordinary changes do not create Graphify evidence JSON,
validation-report-only commits, evidence-only commits, graph-only commits, or
stale-graph merge exceptions.

## Artifacts

Human-authored graph workflow files:

```text
.gitattributes
.graphifyignore
docs/project-graph-runbook.md
tools/refresh_project_graph.ps1
RULES.md
```

Generated committed files are allowlisted to exactly:

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

New maintenance refreshes publish schema version 2 metadata:

```json
{
  "schema_version": 2,
  "generator": "graphify",
  "graphify_version": "0.9.26",
  "mode": "code-only",
  "baseline_stage": "final",
  "indexed_source_commit": "<S>",
  "indexed_source_ref": "origin/master",
  "target_branch": "master",
  "generated_at": "<UTC ISO-8601>",
  "graph_sha256": "<sha256>",
  "ignore_file_sha256": "<sha256>",
  "gitattributes_sha256": "<sha256>",
  "indexed_source_roots": "<newline-separated repository-relative root identity>",
  "indexed_source_roots_sha256": "<sha256>",
  "package_boundary_markers": "<newline-separated repository-relative marker identity>",
  "package_boundary_markers_sha256": "<sha256>",
  "indexed_source_root_policy": "<repository-owned policy id>",
  "indexed_source_root_policy_sha256": "<sha256>",
  "package_boundary_policy": "<repository-owned policy id>",
  "package_boundary_policy_sha256": "<sha256>",
  "graph_schema_contract": "<repository-owned contract id>",
  "graph_schema_contract_sha256": "<sha256>",
  "manifest_schema_contract": "<repository-owned contract id>",
  "manifest_schema_contract_sha256": "<sha256>",
  "baseline_metadata_contract": "<repository-owned contract id>",
  "baseline_metadata_contract_sha256": "<sha256>",
  "policy_fingerprint_sha256": "<sha256>",
  "node_count": 0,
  "edge_count": 0
}
```

`indexed_source_commit` is the exact source commit `S` that Graphify processed.
The following graph artifact commit `G` is not substituted for `S` because
`graphify-out/` is excluded from the indexed corpus.

`ignore_file_sha256` and `gitattributes_sha256` are SHA-256 values of the
committed blobs at `S`, after the wrapper has verified the corresponding
working-tree files match the committed content through Git filters. They are
not raw checkout-byte hashes and do not depend on platform line-ending
configuration. `graph_sha256` is the SHA-256 of the canonical published
`graphify-out/graph.json` bytes. The four generated artifacts are canonical
UTF-8 without BOM and LF.

`indexed_source_roots` and `package_boundary_markers` are deterministic
representations of the committed tree at `S`. The source-root identity records
the sorted top-level roots for tracked files in the approved code/config
corpus. The package-boundary marker identity records the sorted
repository-relative tracked `__init__.py` marker set. Their SHA-256 values and
the composite `policy_fingerprint_sha256` must match the previous accepted
baseline for `Incremental`; otherwise use `FullRebuild`.

The repository pins exact LF checkout rules in `.gitattributes`:

```text
/.graphifyignore text eol=lf
/graphify-out/graph.json text eol=lf
/graphify-out/manifest.json text eol=lf
/graphify-out/GRAPH_REPORT.md text eol=lf
/graphify-out/baseline.json text eol=lf
```

Changing `.gitattributes`, `.graphifyignore`, source roots, package
boundaries, schema, or metadata policy requires `FullRebuild`.

## Maintenance Workflow

Graph refresh is a separate architect-triggered maintenance operation:

```text
S = exact stable current remote master
-> FullRebuild
-> G = graph-only commit
-> lightweight graph review
-> merge
```

Before generation:

1. Fetch current remote state.
2. Record full `origin/master` SHA as `S`.
3. Create a clean detached source worktree at `S`.
4. Create a separate clean output worktree and maintenance branch from `S`.
5. Verify both worktrees are clean and both have `HEAD = S`.
6. Verify `SourceRef` resolves to `S` in `SourceRoot`.
7. Verify `OutputRoot` has no pre-existing diff from `S`.
8. Verify `SourceRoot/.graphifyignore` matches committed `S:.graphifyignore` after repository filters.

Standard command:

```powershell
.\tools\refresh_project_graph.ps1 `
  -Mode FullRebuild `
  -SourceRoot <clean-detached-master-worktree> `
  -SourceRef origin/master `
  -OutputRoot <clean-maintenance-worktree-created-from-S> `
  -TargetBranch master
```

The wrapper stages generation outside both repository worktrees. Graphify reads
only source bytes from `SourceRoot`. Accepted artifacts are published only into
`OutputRoot`.

Immediately before publication, `OutputRoot` must still be unchanged from `S`.
After publication, output mutations must be confined to the four allowlisted
graph paths. If regenerated artifacts are byte-identical to all four artifacts
already present at `S`, do not fabricate an empty graph commit.

## Full Rebuild

`FullRebuild` is the standard maintenance mode. Use it when Graphify version,
`.graphifyignore`, `.gitattributes`, source roots, package boundaries, schema,
metadata policy, mass rename/delete, topology, or integrity conditions changed,
or whenever an architect explicitly requests a full rebuild.

The wrapper verifies:

- exact `graphifyy==0.9.26`;
- distinct clean source and output worktrees;
- source `HEAD`, `SourceRef`, and output base equality to `S`;
- source-owned `.graphifyignore` authority;
- code-only corpus and no HTML visualization;
- valid JSON, canonical UTF-8/LF, nonzero node and edge counts;
- graph/manifest schema and internal node/edge references;
- repository-relative current-corpus paths;
- rename/delete cleanup and absence of ghost nodes;
- secret, credential, inventory, Excel, checkout-path, and user-path scans;
- hashes calculated from actual source-policy and published bytes;
- safe backup-and-restore publication.

Blocking publication checks are application-agnostic. They do not require
historical paths such as `gui/pdu_controller.py`, fixed node IDs, concrete
class/function names, or controller/resolver/enrichment edges. Optional
application-specific observations may be recorded only as non-blocking
diagnostics.

## Incremental Refresh

`Incremental` is optional and constrained. It may be used only when all of the
following remain unchanged from the previous accepted baseline:

- Graphify version;
- `.graphifyignore` bytes and policy;
- `.gitattributes` encoding and line-ending policy;
- indexed source roots and package boundaries;
- graph schema and metadata contract.

The wrapper performs the same source/output boundary, publication, security, and
hash checks as a full rebuild. It also verifies deleted paths and nodes
disappear, old renamed paths do not remain as ghost nodes, new renamed paths
appear when included in the corpus, unchanged nodes are preserved, topology
deltas stay within limits, and failure leaves the previous accepted baseline
unchanged.

Policy changes, package-boundary changes, mass rename/delete, ghost nodes,
topology jumps, or integrity failures require `FullRebuild`.

## Publication Contract

The resulting tree at graph commit `G` must contain and validate all four
canonical artifacts:

```text
graphify-out/graph.json
graphify-out/manifest.json
graphify-out/GRAPH_REPORT.md
graphify-out/baseline.json
```

The complete `S..G` diff must be non-empty and may change only a non-empty
subset of those four paths. Unchanged artifacts must not be artificially
modified to force them into the diff, and no path outside the allowlist may
change.

Before merging the maintenance PR, recheck:

```powershell
git fetch origin
git rev-parse origin/master
git rev-parse origin/<maintenance-branch>
```

Remote `master` must still equal `S`, and the remote maintenance branch must
still equal reviewed `G`. If `master` advanced, stop and regenerate from the new
stable `master` SHA.

## Lightweight Review

Graph maintenance review verifies graph authority only:

- exact source SHA `S`, source ref, and clean source/output states;
- distinct worktrees and output branch created from `S`;
- source `.graphifyignore` identity against committed bytes;
- all four canonical artifacts present and valid;
- non-empty graph-only diff limited to the allowlist;
- no pre-existing or non-graph output mutations;
- JSON validity, counts, canonical bytes, hashes, relative paths, and scans;
- current-corpus source-file, node, edge, rename/delete, ghost-node, and topology integrity.

The reviewer does not treat application tests, OpenSpec validation reports,
feature verification reports, post-archive evidence JSON, or historical
application-specific smoke probes as Graphify inputs or publication authority.

A failed graph review blocks only the graph-maintenance PR. It does not
invalidate unrelated ordinary feature validation and does not block unrelated
archive, post-archive checks, or merge.

## Historical Forensics

The existing frozen baseline, archived `frozen-project-graph-baseline` change,
historical post-archive evidence JSON, and historical `A -> S -> E -> G`
ordering remain committed forensic records. They are not required or supported
for future ordinary changes.

PR #17 `generalize-final-graph-refresh-evidence` is superseded. Do not resume,
merge, rebase, or cherry-pick its workflow implementation.

## ChatGPT Consumption

When using the graph through GitHub or local files without running Graphify:

1. Read `RULES.md` and applicable OpenSpec artifacts.
2. Read `graphify-out/baseline.json`.
3. Verify `schema_version`, `baseline_stage`, `indexed_source_commit`, `indexed_source_ref`, and artifact hashes.
4. Read compact `graphify-out/GRAPH_REPORT.md`.
5. Search targeted nodes and edges in `graphify-out/graph.json`.
6. Identify candidate files and symbols.
7. Open actual source files.
8. Check current branch, current SHA, and branch diff separately.
9. Make findings only from current source evidence.

Do not paste the full `graph.json` into chat unless a reviewer explicitly asks.

## Security

Never index or publish real credentials, `.env`, private keys, cookies, session
IDs, CSRF/access tokens, `equipment_inventory.local.json`, production Excel
workbooks, real inventory snapshots, secret-bearing test output, temporary
worktree paths, Git credential storage, or user-specific absolute paths.

Secret findings should identify only artifact, JSON path or safe scalar
location, category, and a redacted fingerprint.

## Troubleshooting

If Graphify generation fails, do not fabricate artifacts and do not edit
`graph.json` manually. Keep the previous accepted baseline intact and return
the failed contract category.

If `graphify update` leaves deleted or renamed nodes behind, use
`FullRebuild` instead of accepting ghost topology.

Run from PowerShell at repository root. If execution policy blocks the wrapper,
use a process-scoped bypass:

```powershell
powershell -ExecutionPolicy Bypass -File .\tools\refresh_project_graph.ps1 `
  -Mode FullRebuild `
  -SourceRoot <clean-detached-master-worktree> `
  -SourceRef origin/master `
  -OutputRoot <clean-maintenance-worktree-created-from-S> `
  -TargetBranch master
```

Do not persist user-specific tool paths in repository files. Add tool bins to
`PATH` only for the current shell when needed.

## Upgrade Policy

Changing from `graphifyy==0.9.26` requires a new semantic OpenSpec change or an
explicit architect-approved amendment, release/help review, isolated
exact-version install, mandatory full rebuild, integrity/reproducibility reruns,
and updates to this runbook and baseline metadata.
