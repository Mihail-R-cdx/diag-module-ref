# Design: Frozen Project Graph Baseline

## Context

Graphify can generate a local AST-derived project graph and a compact report.
The project needs a committed navigation index that ChatGPT can read through
GitHub and local agents can query, while preserving OpenSpec and source code as
authority. The graph is therefore a periodically published snapshot of a stable
source commit, not a live mirror of an active branch.

The pilot pins `graphifyy==0.9.26`. The executable remains `graphify`.

## Authority and evidence

Authority order:

1. `RULES.md`.
2. Approved root OpenSpec specifications.
3. Current change artifacts.
4. Specialized runbooks.
5. Current source and tests.
6. Graphify output as a navigation index only.

`EXTRACTED` means a statically discovered relationship, not architectural
approval. `INFERRED` is a navigation hypothesis. `AMBIGUOUS` is never evidence.
Every material review conclusion MUST cite and inspect current source.

## Decisions

### 1. Why a committed frozen baseline

A committed baseline is readable by ChatGPT through GitHub without a local CLI,
reviewable as an artifact, portable between worktrees, and tied to a source
SHA. Freezing it prevents generated churn and avoids presenting a moving index
as authoritative during implementation.

### 2. Why Graphify does not run during active work

An active branch intentionally diverges from the indexed source. Automatic or
incremental rebuild during implementation would mix unreviewed work with the
stable baseline, obscure the current diff, create unrelated generated changes,
and weaken independent validation. Active work is understood as:

```text
indexed baseline + current branch diff + approved change artifacts
```

Changed files are always read directly.

### 3. Bootstrap versus final baseline

The implementation review produces a `bootstrap` baseline. Bootstrap is
pre-archive and non-final: it verifies the Graphify integration, wrapper,
corpus filters, security scans, smoke queries, and reproducibility against a
stable source ref, normally `origin/master`. It is not the navigation baseline
for the next ordinary change.

The `final` baseline is produced only after independent review approval,
archive, and post-archive validation. Its source commit includes production and
test code, archived OpenSpec state, the Graphify wrapper, `.graphifyignore`,
`RULES.md`, runbook/spec/task state, and all other human-authored Graphify
workflow changes. The final graph-only commit contains only the allowlisted
generated graph artifacts and becomes the merge HEAD after lightweight graph
integrity review.

Final generation is gated by repository-verifiable evidence, not by a manual
boolean flag. The wrapper requires a project-owned post-archive validation JSON
inside the source tree at exactly
`openspec/validation/frozen-project-graph-baseline.post-archive.json` with
`change_name`, `archive_commit`, `validated_source_commit`,
`openspec_change_validation`, `openspec_all_validation`, `python_tests`, and
`git_diff_check`. The evidence must be tracked by Git, exist in the source
`HEAD` tree, not be ignored, and hash to the same Git blob as the committed
`HEAD` blob after repository filters. The archive commit and validated source
commit must be full SHAs. The archive commit must be an ancestor of the
validated source commit, the validated source commit must be an ancestor of the
source `HEAD`, and the delta from validated source commit to source `HEAD` must
contain only the approved evidence JSON, which is created by that evidence
commit. All required checks must have `status = pass`.

### 4. Source commit boundary

```text
archive commit A
-> validated source commit S
-> evidence commit E
-> Graphify indexes checkout exactly at E
-> graph-only commit G stores outputs
```

`baseline.json.indexed_source_commit` is full SHA `E`. Commit `G` is not in the
graph and does not make the map stale because graph output is excluded from the
corpus. The evidence commit `E` is allowed to differ from `S` only by
`openspec/validation/frozen-project-graph-baseline.post-archive.json`, whose
contents point back to `A` and `S`. The wrapper records the explicitly supplied
`indexed_source_ref` and `target_branch`; it does not infer `master` or
`detached` from SHA equality.

### 5. Code-only corpus

The pilot uses local deterministic code parsing, avoids external LLM APIs,
bounds artifact size, and prevents OpenSpec prose, inventory documents, and
unrelated operational data from becoming graph nodes. Markdown is excluded by
code-only mode and explicit ignore protections cover sensitive/non-code data.

### 6. Committed artifacts

Human-authored:

- `.gitattributes`
- `.graphifyignore`
- `docs/project-graph-runbook.md`
- `tools/refresh_project_graph.ps1`
- short `RULES.md` policy section

Generated allowlist:

- `graphify-out/graph.json`
- `graphify-out/manifest.json`
- `graphify-out/GRAPH_REPORT.md`
- `graphify-out/baseline.json`

Nothing else may be committed without an architecture amendment. HTML, caches,
converted documents, package files, logs, hooks, MCP files, skills, and
Graphify platform installs are excluded.

### 7. Baseline metadata

`graphify-out/baseline.json` schema version 2 contains:

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

`baseline_stage` is either `bootstrap` or `final`. `generated_at` is
informative and excluded from reproducibility identity. Counts and hashes are
derived from validated artifacts. The file contains no checkout path, username,
hostname, credentials, inventory data, ambiguous `indexed_branch`, or
`detached` placeholder.

`ignore_file_sha256` is the SHA-256 of the actual `.graphifyignore` file bytes
read by Graphify. `graph_sha256` is the SHA-256 of the actual canonical
`graphify-out/graph.json` bytes published by the wrapper. The canonical
generated artifact format is UTF-8 without BOM and LF line endings for
`graphify-out/graph.json`, `graphify-out/manifest.json`,
`graphify-out/GRAPH_REPORT.md`, and `graphify-out/baseline.json`.

The repository pins only exact graph-policy paths in `.gitattributes`:
`/.graphifyignore text eol=lf`, `/graphify-out/graph.json text eol=lf`,
`/graphify-out/manifest.json text eol=lf`,
`/graphify-out/GRAPH_REPORT.md text eol=lf`, and
`/graphify-out/baseline.json text eol=lf`. `core.autocrlf=true` Windows
checkouts and LF checkouts must produce identical bytes and hashes for these
paths. A change to `.gitattributes`, `.graphifyignore`, or generated artifact
encoding/line-ending policy is treated as graph policy drift and requires a full
rebuild rather than manual metadata editing.

### 8. Wrapper contract

`tools/refresh_project_graph.ps1`:

1. resolves and verifies repository root;
2. requires explicit `BaselineStage`, `SourceRef`, and `TargetBranch`;
3. verifies clean required source state, full source SHA, and that `SourceRef`
   resolves to source `HEAD`;
4. verifies final-mode source contains the Graphify wrapper, `.graphifyignore`,
   runbook, and `RULES.md`;
5. verifies final-mode post-archive evidence JSON uses the exact approved
   repository path, is tracked, exists in source `HEAD`, is not ignored, has
   working-tree content hashing to the committed `HEAD` blob after repository
   filters, and passes archived change existence, active change absence,
   archive-to-validated-source ancestry, validated-source-to-`HEAD` ancestry,
   evidence-only `S..E` delta, and required pass-status checks before Graphify
   generation;
6. requires Graphify exactly 0.9.26;
7. optionally installs only that exact version in an explicit install mode;
8. validates `.graphifyignore`;
9. supports explicit initial, incremental, and full-rebuild modes;
10. invokes only syntax accepted by pinned CLI help;
11. suppresses/rejects visualization output;
12. writes schema-v2 `baseline.json` after successful generation;
13. canonicalizes generated artifacts to UTF-8 without BOM and LF before JSON
    parsing, structural validation, scans, hashes, and publication;
14. computes hashes over actual canonical published bytes and node/edge counts;
15. validates JSON and relative paths;
16. scans for secrets, inventory, excluded files, and graph self-indexing;
17. runs project-specific query smoke tests;
18. checks deletion/rename and topology integrity;
19. publishes canonical artifacts by validated backup-and-restore copy after
    acceptance checks;
20. prints stage, source SHA, source ref, target branch, version, mode, hashes,
    counts, queries, and exit evidence;
21. propagates nonzero failures;
22. never edits production code/tests;
23. never commits, pushes, merges, archives, installs hooks, starts watch/MCP,
    or silently updates.

### 9. Refresh rules

Incremental refresh is allowed only after a completed approved workflow
checkpoint, normally after archive and post-archive validation, when Graphify
version, ignore policy, source roots, and package boundaries are unchanged and
deletion/rename integrity checks pass.

Full rebuild is mandatory when the Graphify version changes, `.graphifyignore`
changes, source roots or package boundaries change materially, there are mass
renames/deletions, ghost nodes appear, integrity checks fail, topology drops
unexpectedly, the configured major-change threshold is reached, or an architect
requires it.

### 10. Security

`.graphifyignore` and wrapper checks exclude at minimum `.git/`, `.worktrees/`,
`graphify-out/`, virtual environments, caches, logs, Excel files,
`equipment_inventory.local.json`, real inventory snapshots, credentials,
cookies, session material, local deployment files, and temporary artifacts.
Code-only is not treated as sufficient protection. Output receives textual and
structured secret scans.

### 11. Workflow checkpoint

```text
architecture APPROVE
-> implementation
-> bootstrap graph build for integration review
-> independent review and validation
-> archive change in commit A
-> post-archive validation on commit S
-> evidence-only commit E
-> final Graphify refresh from evidence commit E
-> final graph-only commit G
-> lightweight graph integrity review
-> merge
```

The graph-only commit contains only allowlisted Graphify output and graph
metadata. Remote feature HEAD must equal the reviewed graph commit before merge.

## Risks and mitigations

- **Generated graph mistaken for authority**: authority order and source-evidence requirement.
- **Bootstrap mistaken for final baseline**: explicit `baseline_stage`, runbook,
  report policy, and post-review task split.
- **Stale map mistaken for branch state**: source SHA, source ref, and explicit
  baseline/diff overlay.
- **Secret/inventory leakage**: layered ignore, scans, path allowlist, and review.
- **Incremental ghost nodes**: deletion/rename probes and rebuild triggers.
- **Non-reproducible output**: topology/source-set comparisons rather than byte
  equality where timestamps/order are allowed.
- **Tool drift**: exact version pin and help capture.
- **Workflow blockage**: explicit architect exception for stale graph without
  weakening production validation.
