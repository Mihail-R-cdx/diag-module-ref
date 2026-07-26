# Change: Frozen Project Graph Baseline

## Why

Agents currently orient themselves by repeatedly opening broad portions of the repository. This is authoritative but expensive and can obscure impact relationships. The project needs a periodically refreshed, committed, read-only navigation map of a stable verified baseline without introducing an always-on agent integration or making generated graph data normative.

## What Changes

- Add capability `agent-project-navigation` for a committed Graphify code graph tied to one exact source commit.
- Pin the pilot generator to `graphifyy==0.9.26`; Graphify remains isolated developer tooling, not an application runtime dependency.
- Add a human-authored `.graphifyignore`, `docs/project-graph-runbook.md`, and `tools/refresh_project_graph.ps1`.
- Commit only approved generated artifacts: `graphify-out/graph.json`, `graphify-out/manifest.json`, `graphify-out/GRAPH_REPORT.md`, and project-owned `graphify-out/baseline.json`, subject to implementation-time verification of actual 0.9.26 output requirements.
- Build the initial graph with code-only, no-visualization behavior; do not index OpenSpec Markdown, real inventory, secrets, temporary worktrees, or generated graph output.
- Freeze the graph throughout active implementation and validation. Refresh only after archive and post-archive validation, in a separate graph-only commit.
- Define source authority, staleness, evidence, reproducibility, incremental-update, full-rebuild, deletion/rename, security, and failure policies.
- Add only a short Graphify policy section to `RULES.md`; detailed operation belongs in the runbook.

## Non-Goals

- No production-code or application-test changes.
- No fabricated graph output and no baseline without a real local Graphify run.
- No hooks, watch mode, MCP, Graphify-installed skills, `AGENTS.md`, `.codex/hooks.json`, or merge driver.
- No automatic install, commit, push, archive, merge, branch deletion, or force-push by the wrapper.
- No use of Graphify as architectural authority, validation evidence, workflow state, or security-contract authority.

## Impact

- New capability: `agent-project-navigation`.
- Future implementation touches repository policy/documentation/tooling and generated allowlisted graph artifacts only.
- The initial implementation requires a clean local worktree with Graphify 0.9.26 and must leave its PR Draft for independent review.
