# Change: Local-Only Project Graph

## Why

The committed Graphify baseline proved useful as a navigation hint, but the
publication workflow became more expensive than the graph's authority warrants.
The graph is not architecture, validation evidence, production correctness
evidence, CI state, or merge authority. Remote ChatGPT and Codex sessions still
must verify current source, tests, root OpenSpec, and branch diffs directly, so
a committed generated map adds Git churn and process risk without removing the
need for source review.

The project should keep Graphify as an optional local helper for developers who
want it, while removing generated graph output from Git and from the ordinary
OpenSpec lifecycle. A local graph built from the current checkout is a better
fit because it describes the developer's actual tree and can be deleted or
rebuilt without repository ceremony.

PR #18 is superseded by this simpler direction. It must be closed without
merge and its branch retained temporarily only as forensic/reference history.
No commits or files from PR #18 are reused here. The earlier committed baseline
history, including PR #15, remains in Git history; history is not rewritten.

## What Changes

- Redefine `agent-project-navigation` so Graphify is an optional local-only
  navigation helper.
- Specify that generated graph artifacts are not repository artifacts and are
  not committed, archived, submitted as validation evidence, or required for
  merge.
- Plan removal of tracked `graphify-out/graph.json`,
  `graphify-out/manifest.json`, `graphify-out/GRAPH_REPORT.md`, and
  `graphify-out/baseline.json` during implementation.
- Choose `.graphify-local/` as the ignored local output directory.
- Keep `tools/refresh_project_graph.ps1` as a simple local developer helper
  that writes only to `.graphify-local/`, uses pinned `graphifyy==0.9.26`, and
  does not create commits, branches, worktrees, evidence, or publication
  metadata.
- Simplify the runbook into local usage guidance and simplify tests to focused
  local-helper protections.
- Remove ordinary lifecycle concepts such as graph refresh checkpoints,
  graph-only commits, validation-report-only commits, Graphify evidence JSON,
  stale-graph exceptions, and dedicated graph review.

## Non-Goals

- No production application behavior changes in this architecture stage.
- No implementation edits to `RULES.md`, root specs, docs, tools, tests,
  `.gitignore`, `.gitattributes`, `.graphifyignore`, or `graphify-out/`.
- No archive, merge, Graphify refresh, branch deletion, force-push, or PR #18
  branch modification.
- No new remote Graphify publication capability.
- No Git history rewrite; PR #15 and other historical graph commits remain as
  historical records.

## Impact

Affected specification:

- `agent-project-navigation`

Expected implementation areas after approval:

- `RULES.md`
- `openspec/specs/agent-project-navigation/spec.md`
- `docs/project-graph-runbook.md`
- `tools/refresh_project_graph.ps1`
- focused tests for the local helper
- `.gitignore`
- `.gitattributes`
- `.graphifyignore`
- removal of tracked `graphify-out/*`

Production application behavior is unchanged. The VIP change and other useful
changes already merged to `master` remain preserved because this branch starts
from current `origin/master`.
