# Tasks

## 1. Architecture Validation

- [x] Read `RULES.md`, current `agent-project-navigation` root spec, Graphify
  runbook, wrapper, ignore/attributes policy, and frozen baseline metadata.
- [x] Confirm the branch starts from current `origin/master`.
- [x] Create architecture-only OpenSpec artifacts for
  `local-only-project-graph`.
- [x] Run `git diff --check`.
- [x] Run `.\openspec.cmd validate local-only-project-graph --strict`.
- [x] Run `.\openspec.cmd validate --all --strict`.
- [x] Commit and push only `openspec/changes/local-only-project-graph/**`.
- [x] Open a replacement Draft PR and record that PR #18 is superseded.

## 2. Implementation

- [x] Update `RULES.md` to describe Graphify as optional local-only navigation
  helper, not committed evidence or lifecycle authority.
- [x] Keep root `openspec/specs/agent-project-navigation/spec.md`
  byte-identical to `origin/master` on the implementation branch until archive.
- [x] Prove the absence of root-spec branch diff before archive with
  `git diff --exit-code origin/master -- openspec/specs/agent-project-navigation/spec.md`.
- [x] Add `.graphify-local/` to `.gitignore`.
- [x] Update `.graphifyignore` for local-output, credential, inventory, Excel,
  archive, worktree, and generated-output exclusions.
- [x] Remove or narrow `.gitattributes` rules that exist only for committed
  `graphify-out/*` byte-hash publication.

## 3. Removal Of Committed Artifacts

- [x] Remove tracked `graphify-out/graph.json`.
- [x] Remove tracked `graphify-out/manifest.json`.
- [x] Remove tracked `graphify-out/GRAPH_REPORT.md`.
- [x] Remove tracked `graphify-out/baseline.json`.
- [x] Verify no generated local graph artifact appears in the PR diff,
  validation evidence, archive, or merge checks.

## 4. Retained Wrapper And Runbook Simplification

- [x] Keep `tools/refresh_project_graph.ps1` as the repository-local developer
  interface for local Graphify generation.
- [x] Make the wrapper run against the current checkout or an explicitly
  supplied local source.
- [x] Make the wrapper write only under ignored `.graphify-local/`.
- [x] Remove publication target, graph-only commit, branch/worktree creation,
  archive lineage, OpenSpec validation evidence, Graphify evidence JSON, final
  baseline, and merge authority logic from the wrapper.
- [x] Preserve pinned `graphifyy==0.9.26`, `.graphifyignore`, local corpus
  boundaries, and secret-safe failure behavior.
- [x] Rewrite `docs/project-graph-runbook.md` as a local usage guide with one
  standard command through `tools/refresh_project_graph.ps1`, disposable
  output, and delete/rebuild guidance.

## 5. Focused Tests

- [x] Remove or replace publication/worktree/archive/commit tests for the
  retired committed workflow.
- [x] Add focused local-helper tests for the retained wrapper.
- [x] Verify output stays under ignored `.graphify-local/`.
- [x] Verify tracked files are not mutated by successful or failing local
  helper runs.
- [x] Verify excluded and sensitive paths are not indexed.
- [x] Verify the pinned version contract is used.

## 6. Full Validation

- [x] Run `npm ci` if repository-local OpenSpec dependencies are absent.
- [x] Run `git diff --check`.
- [x] Run `.\openspec.cmd validate local-only-project-graph --strict`.
- [x] Run `.\openspec.cmd validate --all --strict`.
- [x] Run the full offline Python test suite and record exact counts.
- [x] Confirm production application behavior is unchanged.
- [x] Confirm graph artifacts, credentials, inventory, validation evidence, and
  archives are not modified except for the approved removal of tracked
  `graphify-out/*`.

## 7. Disposable Archive-Applicability Test

- [ ] Before `READY FOR ARCHIVE`, create a disposable checkout from the
  candidate commit.
- [ ] Run `.\openspec.cmd archive local-only-project-graph --yes` only in the
  disposable checkout.
- [ ] Verify the archive succeeds, removes the active change, creates an
  archive directory, and applies the expected root spec changes.
- [ ] Verify the disposable archive diff contains only expected
  active/archive/root-spec changes.
- [ ] Remove the disposable checkout.

## 8. Independent Validation

- [ ] Request independent validation from the pushed remote branch.
- [ ] Ensure the validator uses a clean detached worktree from
  `origin/agent/local-only-project-graph`.
- [ ] Address only actionable findings in a later implementation session.

## 9. Archive

- [ ] Archive only after an independent verdict permits archive.
- [ ] Run strict OpenSpec validation, full Python tests, and `git diff --check`
  after archive.
- [ ] Commit and push the archive result without modifying generated local
  graph output.

## 10. Merge

- [ ] Confirm remote feature HEAD still matches the reviewed archive commit.
- [ ] Merge only after archive checks pass.
- [ ] Do not perform Graphify refresh, graph-only commit, final graph review,
  Graphify evidence, or stale-graph exception as part of merge.
