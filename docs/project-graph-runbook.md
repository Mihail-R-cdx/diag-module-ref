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

`graphify-out/baseline.json` schema version 2:

```json
{
  "schema_version": 2,
  "generator": "graphify",
  "graphify_version": "0.9.26",
  "mode": "code-only",
  "baseline_stage": "bootstrap",
  "indexed_source_commit": "<full-sha>",
  "indexed_source_ref": "origin/master",
  "target_branch": "master",
  "generated_at": "<UTC ISO-8601>",
  "graph_sha256": "<sha256>",
  "ignore_file_sha256": "<sha256>",
  "node_count": 0,
  "edge_count": 0
}
```

The indexed source commit is the exact source state that Graphify processed.
The following graph artifact commit may be newer than that source commit because
`graphify-out/` is excluded from the corpus. `indexed_source_ref` is the
explicit ref that resolved to the indexed source commit during generation;
`target_branch` is the eventual merge target.

`baseline_stage` has two valid values:

- `bootstrap`: pre-archive, non-final, used only to review the Graphify
  integration, wrapper, corpus filters, security checks, smoke queries, and
  reproducibility. The current bootstrap graph is not the navigation baseline
  for the next ordinary change.
- `final`: post-archive baseline built from the reviewed source commit that
  includes production/tests, archived OpenSpec state, wrapper, runbook,
  `.graphifyignore`, `RULES.md`, and any human-authored Graphify workflow
  changes. The graph-only final commit is the merge HEAD after lightweight graph
  integrity review.

## Source And Output Boundary

The wrapper separates the indexed source from the publication target:

```powershell
.\tools\refresh_project_graph.ps1 -Mode Initial -BaselineStage Bootstrap -SourceRoot <clean-source-worktree> -SourceRef origin/master -OutputRoot <implementation-worktree> -TargetBranch master
```

`SourceRoot` must be a clean Git worktree. `SourceRef` is required by contract
and must resolve, inside `SourceRoot`, to `SourceRoot` `HEAD`; the wrapper does
not infer branch identity from SHA equality. Bootstrap normally uses
`origin/master`. Final uses the explicit reviewed feature-branch source ref
after archive and post-archive validation. In final mode the source tree must
contain `tools/refresh_project_graph.ps1`, `.graphifyignore`,
`docs/project-graph-runbook.md`, and `RULES.md`.

Final mode also requires explicit repository-verifiable post-archive validation
evidence:

```powershell
-PostArchiveValidationEvidence openspec/validation/frozen-project-graph-baseline.post-archive.json
```

The evidence file is project-owned JSON in the source tree. The only approved
repository path is:

```text
openspec/validation/frozen-project-graph-baseline.post-archive.json
```

The evidence path must be inside the source tree, match this approved
repository-relative path exactly, be tracked by Git, exist in `SourceRoot`
`HEAD`, not be ignored, and hash to the same Git blob as the committed `HEAD`
blob after repository filters. Ignored, untracked, locally modified,
missing-from-`HEAD`, or wrong-path evidence is rejected before semantic checks.

It must contain:

```json
{
  "change_name": "frozen-project-graph-baseline",
  "archive_commit": "<full-sha>",
  "validated_source_commit": "<full-sha>",
  "openspec_change_validation": { "status": "pass" },
  "openspec_all_validation": { "status": "pass" },
  "python_tests": { "status": "pass" },
  "git_diff_check": { "status": "pass" }
}
```

The wrapper verifies valid JSON, `change_name`, that
`validated_source_commit` equals `SourceRoot` `HEAD`, that `archive_commit` is
an ancestor of `SourceRoot` `HEAD`, that an archived
`frozen-project-graph-baseline` artifact exists under
`openspec/changes/archive/`, that the active
`openspec/changes/frozen-project-graph-baseline/` directory is absent, and that
all required checks have `status = pass`. A pre-archive source tree, missing
evidence, or evidence that is not committed in `SourceRoot` `HEAD` fails
nonzero before Graphify generation.

The wrapper reads metadata from `SourceRoot`, stages Graphify execution in a
temporary build copy, and writes accepted artifacts only under
`OutputRoot/graphify-out/`.

The temporary build copy receives the committed `.graphifyignore` as a tooling
overlay so the source worktree remains clean. The source commit, not the output
branch commit and not the temporary copy, is recorded in `baseline.json`.

## Bootstrap Build

Use the isolated pinned tool:

```powershell
uv tool install graphifyy==0.9.26
graphify --version
graphify extract --help
graphify check-update --help
graphify update --help
```

Build only from a clean detached worktree at the current `origin/master` SHA:

```powershell
$masterSha = git rev-parse origin/master
git worktree add --detach .worktrees/graph-source-$($masterSha.Substring(0, 8)) $masterSha
.\tools\refresh_project_graph.ps1 -Mode Initial -BaselineStage Bootstrap -SourceRoot .worktrees/graph-source-$($masterSha.Substring(0, 8)) -SourceRef origin/master -OutputRoot . -TargetBranch master
```

The wrapper verifies the exact Graphify version, clean source state,
`.graphifyignore`, JSON validity, hashes, counts, output allowlist, no HTML,
frozen report policy, secret/inventory/path scans, no hooks/watch/MCP/skills,
and project-specific structured smoke queries. It builds in a temporary
directory and publishes to `graphify-out/` only after all acceptance checks pass.
Publication is a validated backup-and-restore copy: if replacement fails, the
wrapper restores the previous accepted output from backup and exits nonzero.
This is not claimed as a single-step filesystem rename guarantee.

## Final Baseline Build

Do not run the final baseline build during implementation review. After
independent review approval, archive, and post-archive validation, identify the
reviewed source commit `S` on `agent/frozen-project-graph-baseline` and build
from a clean source worktree whose `HEAD` equals that explicit source ref:

```powershell
.\tools\refresh_project_graph.ps1 -Mode FullRebuild -BaselineStage Final -SourceRoot <post-archive-source-worktree> -SourceRef agent/frozen-project-graph-baseline -OutputRoot . -TargetBranch master -PostArchiveValidationEvidence openspec/validation/frozen-project-graph-baseline.post-archive.json
```

The final graph commit must contain only the allowlisted generated artifacts.
Keep the PR Draft until the final graph-only commit receives lightweight graph
integrity review.

## Incremental Refresh

Use incremental refresh only after a completed approved workflow checkpoint,
normally after archive and post-archive validation:

```powershell
.\tools\refresh_project_graph.ps1 -Mode Incremental -BaselineStage Final -SourceRef agent/frozen-project-graph-baseline -TargetBranch master -PostArchiveValidationEvidence openspec/validation/frozen-project-graph-baseline.post-archive.json
```

The wrapper runs Graphify update-check before update in a temporary build copy
seeded with the last accepted `graphify-out/`. It records the source range from
the previous `baseline.json.indexed_source_commit` to the current clean source
commit, classifies `git diff --name-status --find-renames`, and enforces:

- deleted paths must disappear from manifest and graph nodes;
- old renamed paths must not remain as ghost nodes;
- new renamed paths must appear when they are in the corpus;
- unchanged node identities must not disappear;
- node/edge deltas must fit configurable per-changed-file limits;
- failed integrity leaves the last accepted baseline intact.

Any ghost node, unverifiable rename/delete, unexpected topology shrink or jump,
or excessive source delta fails nonzero and requires `FullRebuild`. A normal
active feature implementation or validation session must not silently rebuild or
refresh the graph.

## Full Rebuild

Use full rebuild when the Graphify version changes, `.graphifyignore` changes,
source roots or package boundaries change, mass rename/delete occurs, ghost
nodes appear, integrity validation fails, topology unexpectedly shrinks, a
large-change threshold is reached, or an architect explicitly requests rebuild:

```powershell
.\tools\refresh_project_graph.ps1 -Mode FullRebuild -BaselineStage Final -SourceRef agent/frozen-project-graph-baseline -TargetBranch master -PostArchiveValidationEvidence openspec/validation/frozen-project-graph-baseline.post-archive.json
```

Full rebuild regenerates from a clean source state through the same temporary
build and validated backup-and-restore publication path. It does not commit,
push, archive, merge, or install integrations.

## ChatGPT Consumption

When using the graph through GitHub without local Graphify:

1. Read `RULES.md` and applicable OpenSpec artifacts.
2. Read `graphify-out/baseline.json`.
3. Verify `schema_version`, `baseline_stage`, `indexed_source_commit`,
   `indexed_source_ref`, and artifact hashes.
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
bootstrap baseline + current branch diff + approved change artifacts
```

Do not update graph artifacts during ordinary code changes. Bootstrap artifacts
are implementation-review evidence only and are not the next-change navigation
baseline. Refresh only at an approved checkpoint. Documentation-only changes
that do not modify indexed code, graph policy, source roots, ignore rules,
wrapper behavior, or metadata contract do not require a refresh unless the
architect says otherwise.

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

The wrapper scans all four committed artifacts: `graph.json`, `manifest.json`,
`GRAPH_REPORT.md`, and `baseline.json`. It checks Windows drive paths, UNC
paths, POSIX checkout paths, `.env` and local deployment files, private-key
blocks, bearer tokens, common API-key prefixes, assignment-like credential
literals, URL-embedded credentials, token/cookie/session values, token-like
high-entropy scalars, inventory local filenames, Excel paths, temporary
worktrees, and graph output self-indexing. Secret findings print artifact, JSON
path or safe scalar location, category, and a redacted fingerprint only.

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

For each query, record command exit code, matched node ids, source paths, edge
ids/types, actual edge confidence or `NOT_AVAILABLE`, and source confirmation.
`INFERRED` may be recorded only as a navigation hint with separate source
confirmation. `AMBIGUOUS` is not successful evidence.

## Reproducibility

Acceptance compares topology rather than byte-for-byte output when timestamps
or ordering may vary:

- source-file set;
- node identities;
- extracted edges, or documented non-semantic differences;
- node/edge counts;
- absence of checkout-specific absolute paths;
- portability across worktrees.
- committed `.graphifyignore` byte hash.

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
powershell -ExecutionPolicy Bypass -File .\tools\refresh_project_graph.ps1 -Mode Initial -BaselineStage Bootstrap -SourceRef origin/master -TargetBranch master
```

Do not persist user-specific tool paths in repository files. Add tool bins to
`PATH` only for the current shell when needed.

## Upgrade Policy

Changing from `graphifyy==0.9.26` requires a new semantic OpenSpec change or an
explicit architect-approved amendment, release/help review, isolated
exact-version install, mandatory full rebuild, integrity/reproducibility
reruns, and updates to this runbook and baseline metadata.
