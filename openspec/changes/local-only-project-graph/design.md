# Design: Local-Only Project Graph

## Current State

`origin/master` contains capability `agent-project-navigation`, a runbook,
`.graphifyignore`, `.gitattributes` pins, a complex
`tools/refresh_project_graph.ps1`, and four committed generated files under
`graphify-out/`. The current frozen baseline is final and records
`indexed_source_commit = 2ad5c67b5413627cfc15fb327c0e6f856cf9b264`.

That model gave GitHub-readable navigation data, but it also introduced
publication metadata, archive lineage, evidence-only commits, graph-only
commits, and merge gates around data that is not authoritative. PR #17 and PR
#18 explored ways to decouple or generalize that workflow. This change
supersedes those approaches instead of extending them.

## Target Local-Only Model

Graphify becomes an optional local developer helper. It may be installed and
run locally to help find candidate files, symbols, and relationships, but all
material conclusions still come from `RULES.md`, root OpenSpec, active change
artifacts, current source, tests, and Git diff.

Generated graph output is disposable local state. It is not a repository
artifact, validation artifact, archive artifact, CI artifact, merge artifact,
or required dependency for ChatGPT/Codex work.

## Explicit Non-Goals

- Do not publish generated graph output to Git.
- Do not preserve the `A -> S -> E -> G` publication transaction.
- Do not add graph-only branches, graph-only commits, graph evidence JSON,
  validation-report-only commits, stale-graph exceptions, final graph review,
  or automatic graph refresh after archive.
- Do not make Graphify part of production runtime dependencies or CI.
- Do not rewrite history that already contains PR #15 graph artifacts.
- Do not reuse PR #18 as a base or cherry-pick from it.

## Artifact Removal Plan

Implementation removes the tracked generated artifacts:

```text
graphify-out/graph.json
graphify-out/manifest.json
graphify-out/GRAPH_REPORT.md
graphify-out/baseline.json
```

The `graphify-out/` directory may remain ignored as historical safety, but no
generated graph file should remain tracked. Historical commits and merged PR
history remain intact.

## Local Output Directory

The local output directory is:

```text
.graphify-local/
```

It must be ignored by Git. Generated local artifacts must not appear in commits,
PR diffs, OpenSpec archives, validation evidence, or merge checks. Developers
may delete this directory at any time and rebuild it from the current checkout.

## Wrapper Decision

Keep `tools/refresh_project_graph.ps1` as a small local developer helper rather
than deleting it. A wrapper still gives the project one safe command, a pinned
Graphify version, and project-specific exclusion checks. The implementation
must remove publication behavior from the wrapper.

The simplified wrapper:

- runs against the current checkout or an explicitly supplied local source;
- writes only to ignored `.graphify-local/`;
- uses pinned `graphifyy==0.9.26`;
- respects `.graphifyignore`;
- avoids credentials, real inventory, Excel files, archives, worktrees, and
  local data;
- reports failures without leaking secrets;
- never commits, pushes, branches, creates worktrees, archives, merges, reads
  OpenSpec validation reports, parses Graphify evidence JSON, verifies archive
  lineage, or publishes a frozen baseline.

If implementation finds that retaining the wrapper adds little value, the
implementation may instead remove it and document the direct local command, but
that decision must keep the same local-only and ignored-output constraints.

## Test Simplification

Implementation should not preserve large publication/worktree/archive/commit
test suites for a workflow being removed. Focused tests should cover only the
local-helper contract:

- output is written only under ignored `.graphify-local/`;
- tracked source files are not mutated;
- excluded and sensitive paths are not indexed;
- pinned Graphify version is used;
- failures do not leave tracked mutations.

If no current `tests/test_project_graph_refresh_workflow.py` exists in
`origin/master`, implementation may add a small focused test module rather than
pretending to simplify a missing file.

## Runbook Decision

`docs/project-graph-runbook.md` should become a local Graphify usage guide. It
should contain one local command, state that output is ignored and disposable,
and explain how to delete and rebuild `.graphify-local/`. It should remove
archive, validation evidence, branch, commit, final-baseline, and merge
workflow instructions.

## Git Ignore And Attributes

Implementation should add `.graphify-local/` to `.gitignore`. It should remove
or narrow `.gitattributes` rules that exist only to make committed
`graphify-out/*` byte hashes stable. `.graphifyignore` should remain a local
corpus boundary and should continue excluding credentials, inventory, Excel,
archives, generated output, worktrees, and local deployment data.

## Security Boundaries

Code-only generation is not sufficient by itself. The local helper and ignore
policy must prevent credentials, `.env`, private keys, cookies, session files,
tokens, `equipment_inventory.local.json`, production Excel workbooks, real
inventory snapshots, temporary worktrees, Git credential storage, local output,
and user-specific absolute paths from being indexed or printed in unsafe error
messages.

## OpenSpec Archive Applicability

The active delta is authored against exact requirement headers in current
`origin/master`. Root specs must not be manually edited to their post-archive
state before archive, except where an explicit OpenSpec contract allows it.
Before `READY FOR ARCHIVE`, implementation must run a disposable archive
applicability check from the candidate commit. That check must prove the
archive command applies the delta successfully in the disposable checkout and
does not archive the main feature branch.

This change avoids scenario renames inside MODIFIED requirements so the
archiver can preserve existing scenarios safely.

## Rollback Strategy

If local-only implementation is rejected, discard the active change branch
without changing `master`. If implementation lands but later proves too
limiting, a future architecture change may reintroduce a committed graph
publication model from current `master`; it must not rely on PR #18 as a base.

## Historical Treatment

- PR #15 remains historical evidence of the committed frozen baseline model.
- PR #17 remains superseded evidence-workflow exploration.
- PR #18 remains superseded decoupled committed-refresh exploration and should
  be closed without merge, retaining its branch temporarily for reference.

## Implementation And Validation Boundaries

This architecture stage creates only OpenSpec artifacts under
`openspec/changes/local-only-project-graph/`. Implementation changes are
planned but not performed here. Strict validation uses only repository-local
commands:

```powershell
git diff --check
.\openspec.cmd validate local-only-project-graph --strict
.\openspec.cmd validate --all --strict
```
