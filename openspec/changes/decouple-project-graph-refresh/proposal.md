# Change: decouple-project-graph-refresh

## Why

The committed Graphify map is an optional frozen navigation aid, but the current root contract still couples a final graph refresh to the post-archive lifecycle of ordinary OpenSpec changes and allows a graph failure to become a merge checkpoint. PR #17 attempted to generalize that coupling through additional validation-report and evidence commits, but the resulting workflow is more complex than the authority of the graph justifies.

Because Graphify does not define architecture, production correctness, or validation authority, ordinary development must be able to complete against approved OpenSpec, current source, tests, and Git diff even when the committed graph is stale.

## What Changes

- Define the ordinary OpenSpec lifecycle as `Architecture -> Implementation -> Independent validation -> Archive + post-archive checks -> Merge`, with no mandatory Graphify refresh stage.
- Make an absent or stale graph explicitly non-blocking for ordinary architecture, implementation, validation, archive, post-archive checks, and merge.
- Remove ordinary-change requirements for Graphify evidence JSON, renewed validation solely for Graphify, validation-report-only commits, evidence-only commits, graph-only commits, and stale-graph merge exceptions.
- Define Graphify refresh as a separate architect-triggered maintenance workflow from one exact stable `master` source commit `S` to one graph-only commit `G` followed by lightweight graph integrity review.
- Make `FullRebuild` the standard maintenance mode and retain `Incremental` only as an optional mode under strict unchanged-policy and integrity preconditions.
- Simplify `tools/refresh_project_graph.ps1` so graph publication no longer parses OpenSpec archives, validation reports, post-archive evidence JSON, or feature-change lineage.
- Preserve version pinning, clean-source and exact-ref binding, generated-file allowlists, canonical UTF-8/LF output, JSON and count checks, published-byte hashes, repository-relative paths, and secret/inventory/path protections.
- Preserve the existing committed frozen baseline and the historical `A -> S -> E -> G` workflow as forensic history only; do not generalize it to future changes.

## Impact

Affected specifications:

- `agent-project-navigation`
- new `project-graph-refresh-workflow`

Expected implementation areas:

- `RULES.md`
- `openspec/specs/agent-project-navigation/spec.md`
- `openspec/specs/project-graph-refresh-workflow/spec.md`
- `docs/project-graph-runbook.md`
- `tools/refresh_project_graph.ps1`
- `tests/test_project_graph_refresh_workflow.py`

This architecture change does not modify application production code, application tests, validation evidence, archived changes, or `graphify-out/`. PR #17 remains superseded and must not be merged.
