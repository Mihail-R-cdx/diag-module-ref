# Change: Generalize final Graphify refresh evidence

## Why

The repository-local final Graphify workflow is currently hard-coded to the historical `frozen-project-graph-baseline` change and its single post-archive evidence file. That gate correctly protected the original baseline publication, but it cannot validate later archived OpenSpec changes. A normal later change necessarily has production, test, specification, archive, and validation-evidence commits between the previous frozen baseline and the new graph source commit, while the wrapper currently requires an evidence-only delta tied to `frozen-project-graph-baseline`.

This blocks the approved final Graphify refresh checkpoint for PR #16 (`equipment-room-vip-context`) before graph generation. The blocker is repository workflow policy, not graph data.

## What Changes

- Define a reusable, change-scoped post-archive validation evidence contract for later Graphify refresh checkpoints.
- Preserve the strict historical `A -> S -> E -> G` contract for `frozen-project-graph-baseline` without silently weakening it.
- Allow a later archived change to identify its archived change name, archive commit, independently validated implementation/source commit, evidence commit, intended indexed source commit, and required passing checks.
- Require repository-verifiable ancestry, clean source state, exact tracked evidence bytes, archived-change presence, active-change absence, and explicit source-commit binding.
- Replace the global evidence-only-delta assumption with a change-scoped lineage check appropriate to ordinary archived changes.
- Keep Graphify artifact allowlists, hash checks, encoding policy, sensitive-data scans, ghost-node checks, topology checks, and graph-only commit rules unchanged.
- Update the project graph runbook and wrapper tests to cover both the frozen baseline workflow and ordinary later-change refresh workflows.

## Impact

Affected areas:

- `tools/refresh_project_graph.ps1`
- `docs/project-graph-runbook.md`
- Graphify workflow tests
- repository-owned post-archive validation evidence schema/path policy
- root OpenSpec contract for project graph refresh workflow

This change does not modify application production behavior, equipment inventory behavior, or current Graphify artifacts. Graphify refresh for PR #16 remains blocked until this change is implemented, independently validated, archived, and merged.