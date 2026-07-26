# Design: Frozen Project Graph Baseline

## Context

Graphify can generate a local AST-derived project graph and a compact report. The project needs a committed navigation index that ChatGPT can read through GitHub and local agents can query, while preserving OpenSpec and source code as authority. The graph is therefore a periodically published snapshot of a stable source commit, not a live mirror of an active branch.

The pilot pins `graphifyy==0.9.26`. The executable remains `graphify`. Official 0.9.26 documentation exposes `graphify --version`, `graphify extract <path> --code-only`, `--no-viz`, `graphify check-update <path>`, and `graphify update <path>`. The implementation session MUST capture the exact installed `--help` output and use only syntax accepted by that pinned build.

## Authority and evidence

Authority order:

1. `RULES.md`.
2. Approved root OpenSpec specifications.
3. Current change artifacts.
4. Specialized runbooks.
5. Current source and tests.
6. Graphify output as a navigation index only.

`EXTRACTED` means a statically discovered relationship, not architectural approval. `INFERRED` is a navigation hypothesis. `AMBIGUOUS` is never evidence. Every material review conclusion MUST cite and inspect current source. Graph output alone cannot support a review finding, approval, archive, or merge.

## Decisions

### 1. Why a committed frozen baseline

A committed baseline is readable by ChatGPT through GitHub without a local CLI, reviewable as an artifact, portable between worktrees, and tied to a source SHA. Freezing it prevents generated churn and avoids presenting a moving index as authoritative during implementation.

### 2. Why Graphify does not run during an active change

An active branch intentionally diverges from the indexed source. Automatic or incremental rebuild during implementation would mix unreviewed work with the stable baseline, obscure the current diff, create unrelated generated changes, and weaken independent validation. Active work is understood as:

```text
indexed baseline + current branch diff + approved change artifacts
```

Changed files are always read directly.

### 3. Why code-only

The first pilot uses local deterministic code parsing, avoids external LLM APIs, bounds artifact size, and prevents OpenSpec prose, inventory documents, and unrelated operational data from becoming graph nodes.

### 4. Why OpenSpec Markdown is excluded

OpenSpec is already normative and structured. Mixing its Markdown into a code graph risks confusing declared architecture with implemented relationships and duplicating workflow state. Agents read OpenSpec directly.

### 5. Committed artifacts

Human-authored:

- `.graphifyignore`
- `docs/project-graph-runbook.md`
- `tools/refresh_project_graph.ps1`
- short `RULES.md` policy section

Generated allowlist:

- `graphify-out/graph.json`
- `graphify-out/manifest.json`
- `graphify-out/GRAPH_REPORT.md`
- `graphify-out/baseline.json`

The implementation MUST verify whether 0.9.26 requires any additional machine file for correct incremental operation. Nothing else may be committed without an architecture amendment.

### 6. Why HTML is not committed

`graph.html` is large, redundant for ChatGPT, unnecessary for CLI queries, and creates generated review noise. Initial and refresh runs use no-visualization behavior and the wrapper rejects committed HTML.

### 7. ChatGPT consumption without local CLI

ChatGPT reads `baseline.json`, verifies the indexed source SHA against GitHub, reads `GRAPH_REPORT.md`, searches targeted nodes and edges in `graph.json`, then opens candidate source files and checks the current branch and diff. Lack of local Graphify does not prevent this read-only path.

### 8. Staleness

A graph is current for navigation when `baseline.json` is valid, its hashes match, and `indexed_source_commit` is the intended stable source commit. It may legitimately be one commit behind the graph-only commit because graph files are excluded from the corpus. It is stale when metadata/hash/integrity checks fail, the intended baseline source has moved without refresh, or an architect explicitly marks it stale. During any active feature branch it is described as a frozen baseline rather than as a model of the branch.

### 9. Applying the current branch diff

The agent identifies files changed since `indexed_source_commit`, reads all material changed files directly, and uses the graph only for unchanged-neighborhood discovery and impact candidates. Graph results never override changed source.

### 10. Source commit boundary

```text
source commit S
→ Graphify indexes checkout exactly at S
→ graph-only commit G stores outputs
```

`baseline.json.indexed_source_commit` is full SHA `S`. Commit `G` is not in the graph and does not make the map stale because graph output is excluded from the corpus.

### 11. Incremental update

Use incremental refresh after an ordinary completed, archived, post-archive-validated change when Graphify version, ignore policy, source roots, and package boundaries are unchanged and deletion/rename integrity checks pass. The wrapper runs pinned-version `check-update` followed by `update` using syntax confirmed by local help.

### 12. Full rebuild

Full rebuild is mandatory when the Graphify version changes, `.graphifyignore` changes, source roots or package boundaries change materially, there are mass renames/deletions, ghost nodes appear, integrity checks fail, topology drops unexpectedly, the configured major-change threshold is reached, or an architect requires it. Full rebuild removes only generated output through an explicit wrapper mode and regenerates from the clean source commit.

### 13. Inventory and secret exclusion

`.graphifyignore` and wrapper checks exclude at minimum `.git/`, `.worktrees/`, `graphify-out/`, virtual environments, caches, logs, Excel files, `equipment_inventory.local.json`, real inventory snapshots, credentials, cookies, session material, local deployment files, and temporary artifacts. Code-only is not treated as sufficient protection. Output receives textual and structured secret scans.

### 14. Absolute-path checks

All source paths in graph and manifest must be repository-relative. The wrapper scans JSON scalar strings for Windows drive-root, UNC, and POSIX checkout-root forms and fails nonzero on user-specific absolute paths. It also compares portability from a second worktree during acceptance testing.

### 15. Version upgrades

Upgrades require a new semantic OpenSpec change or explicit architect-approved amendment, review of release notes and CLI help, isolated exact-version install, mandatory full rebuild, reproducibility/integrity reruns, and update of runbook and metadata. Floating installs are forbidden.

### 16. Why hooks, watch, MCP, and skills are excluded

They create always-on mutation, persistent agent instructions, hidden rebuilds, additional attack/configuration surface, or runtime services. This integration is an explicit snapshot workflow. No `graphify install`, project/platform install, hook install, watch, MCP, `AGENTS.md`, `.agents/skills/graphify`, `.codex/hooks.json`, or Graphify merge driver is allowed.

### 17. Hint versus evidence

A graph query produces candidate files, symbols, and relationships. Review evidence begins only after inspecting the current source location and relevant tests/specs. Findings cite source, not generated graph lines alone.

### 18. Documentation-only changes

A documentation-only change that does not modify indexed code or graph policy does not require graph refresh. If `.graphifyignore`, the wrapper, runbook semantics, source-root policy, or committed graph metadata contract changes, an architect decides whether a full rebuild is required.

### 19. Graph generation failure after validated implementation

Failure does not invalidate already proven production correctness. The graph artifact step fails separately, the map is explicitly marked stale, no fabricated output is committed, and the architect decides whether to repair before merge or temporarily proceed under the exception policy.

### 20. Does an unavailable current graph block production merge?

Normally the graph-enabled workflow requires a successful graph-only refresh before merge. However, because the graph is optional navigation rather than correctness evidence, an architect MAY authorize a temporary merge with an explicit stale marker and tracked follow-up when generation is unavailable after production validation. The exception must be deliberate and recorded; agents cannot silently bypass refresh.

## Baseline metadata

`graphify-out/baseline.json` schema version 1 contains:

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

`generated_at` is informative and excluded from reproducibility identity. Counts and hashes are derived from validated artifacts. The file contains no checkout path, username, hostname, credentials, or inventory data.

## Wrapper contract

`tools/refresh_project_graph.ps1`:

1. resolves and verifies repository root;
2. verifies clean required source state and full source SHA;
3. requires Graphify exactly 0.9.26;
4. optionally installs only that exact version in an explicit install mode;
5. validates `.graphifyignore`;
6. supports explicit initial, incremental, and full-rebuild modes;
7. invokes only syntax accepted by pinned CLI help;
8. suppresses/rejects visualization output;
9. writes `baseline.json` after successful generation;
10. computes hashes and node/edge counts;
11. validates JSON and relative paths;
12. scans for secrets, inventory, excluded files, and graph self-indexing;
13. runs project-specific query smoke tests;
14. checks deletion/rename and topology integrity;
15. prints source SHA, version, mode, hashes, counts, queries, and exit evidence;
16. propagates nonzero failures;
17. never edits production code/tests;
18. never commits, pushes, merges, archives, installs hooks, starts watch/MCP, or silently updates.

## Corpus

The implementation session MUST derive the actual Python corpus from the repository tree. Expected candidates include `core/`, `gui/`, `handlers/`, `tools/`, `tests/`, and root Python entry points only when present. It MUST NOT invent absent roots. Markdown is excluded by code-only mode and explicit ignore protections cover sensitive/non-code data.

## Workflow checkpoint

```text
architecture APPROVE
→ implementation
→ independent review and validation
→ archive change
→ post-archive validation
→ Graphify refresh from final source commit
→ graph-only commit
→ lightweight graph integrity review
→ merge
```

The graph-only commit contains only allowlisted Graphify output and graph metadata. Remote feature HEAD must equal the reviewed graph commit before merge.

## Risks and mitigations

- **Generated graph mistaken for authority**: authority order and source-evidence requirement.
- **Stale map mistaken for branch state**: source SHA and explicit baseline/diff overlay.
- **Secret/inventory leakage**: layered ignore, scans, path allowlist, and review.
- **Incremental ghost nodes**: deletion/rename probes and rebuild triggers.
- **Non-reproducible output**: topology/source-set comparisons rather than byte equality where timestamps/order are allowed.
- **Tool drift**: exact version pin and help capture.
- **Workflow blockage**: explicit architect exception for stale graph without weakening production validation.
