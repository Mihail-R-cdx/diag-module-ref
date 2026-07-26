# Tasks

## 1. Implementation-review scope

- [x] Re-read `RULES.md`, current root specs, `.gitignore`, and the equipment inventory runbook.
- [x] Record branch/PR gate and work only on `agent/frozen-project-graph-baseline`.
- [x] Enumerate actual Python source/test roots and root entry points; do not invent directories.
- [x] Add a short `RULES.md` Graphify frozen-baseline section without duplicating the runbook.
- [x] Add `.graphifyignore` with explicit protection for graph output, worktrees, inventory, Excel, secrets, deployment-local data, caches, logs, and temporary artifacts.
- [x] Install `graphifyy==0.9.26` in an isolated tool environment; do not add it to application dependencies.
- [x] Capture `graphify --version` and help for `extract`, `check-update`, and `update`.
- [x] Implement `tools/refresh_project_graph.ps1` with explicit initial, incremental, full-rebuild, opt-in exact-install modes, clean `SourceRoot`/`OutputRoot` separation, required `BaselineStage`/`SourceRef`/`TargetBranch`, schema-v2 metadata, and no dirty publish mode.
- [x] Enforce final-mode workflow gate requiring project-owned post-archive validation evidence at the approved repository path, tracked Git evidence, `HEAD` blob presence, working-tree content hashing to the `HEAD` blob after repository filters, archived change presence, active change absence, archive-to-validated-source ancestry, validated-source-to-`HEAD` ancestry, evidence-only `S..E` delta, and pass statuses before Graphify generation.
- [x] Ensure wrapper failures remain nonzero and no automatic commit, push, merge, archive, hook, watch, MCP, or skill installation occurs.
- [x] Clarify publication as validated backup-and-restore copy, not a single-step filesystem rename guarantee.
- [x] Add `docs/project-graph-runbook.md` covering authority, bootstrap/final metadata, frozen behavior, ChatGPT/Codex use, commands, staleness, security, Windows operation, troubleshooting, and upgrade policy.

## 2. Bootstrap graph evidence

- [x] Check out a clean exact `origin/master` source commit and run real Graphify 0.9.26 code-only extraction with visualization disabled.
- [x] Generate current committed graph as `baseline_stage = bootstrap`, `indexed_source_ref = origin/master`, `target_branch = master`.
- [x] Verify actual 0.9.26 output files and commit only the approved allowlist.
- [x] Create `graphify-out/baseline.json` with full indexed source SHA, exact version, hashes, counts, and no local identity/path data.
- [x] Validate graph and manifest JSON, nonzero nodes/edges, repository-relative source paths, excluded-path absence, and no self-indexing.
- [x] Confirm no HTML, semantic caches, converted documents, cost/API outputs, logs, environments, or package files are committed.
- [x] Mark `GRAPH_REPORT.md` as bootstrap, pre-archive, non-final, and not the next-change navigation baseline.

## 3. Security, smoke, and reproducibility

- [x] Run textual and structured scans across all committed graph artifacts for credentials, `.env`, keys, cookies, Session IDs, CSRF/access tokens, real inventory, Excel data, high-entropy token-like values, graph self-indexing, and user-specific absolute paths.
- [x] Select at least five symbols/flows verified in current source, including available equivalents of `PDUController`, `InteractiveSessionController`, `EquipmentInventory`, credential-fallback ownership, and the PDU-to-related-codec path.
- [x] For each smoke query, record exit 0, matched node ids, source paths, edge ids/types, actual edge confidence or `NOT_AVAILABLE`, and source confirmation.
- [x] Repeat build or compare topology on the same source commit and verify identical source-file set, node identities, edge identities, counts, and committed `.graphifyignore` byte hash.
- [x] Repeat portability checks from another clean worktree and verify no checkout-specific absolute paths.
- [x] In a disposable probe outside the production branch, add/rename/delete a synthetic source file and verify incremental integrity rejection or full-rebuild escalation without replacing the accepted baseline on failure.
- [x] Restore the bootstrap baseline and ensure no probe artifacts are committed.
- [x] Verify full-rebuild triggers for version/ignore/root/package changes, mass rename/delete, ghost nodes, integrity failure, unexpected topology shrink, threshold, and architect request.
- [x] Verify disposable final-gate negative cases for missing, wrong-path, ignored, untracked, added-but-not-in-`HEAD`, modified-after-commit, invalid JSON, nonexistent validated source, validated source not ancestor of `HEAD`, archive not ancestor of validated source, failed check status, and extra `S..E` changes in production, tests, wrapper/ignore, and other files, plus a positive `A -> S -> E` fixture that passes the gate before the fake Graphify sentinel.

## 4. Implementation validation

- [x] Run `.\openspec.cmd validate frozen-project-graph-baseline --strict`.
- [x] Run `.\openspec.cmd validate --all --strict`.
- [x] Run `python -X faulthandler -m unittest discover -s tests -p "test_*.py"` and record the fresh count.
- [x] Run `git diff --check` and `git status --short`.
- [x] Confirm production code, runtime tests, runtime dependencies, GUI code, handlers, credentials/recovery behavior, real inventory, and root specs are unchanged unless separately approved.
- [x] Commit and push the focused implementation to `agent/frozen-project-graph-baseline`.
- [x] Keep the PR Draft and report `READY FOR INDEPENDENT REVIEW`.
- [x] Do not archive, build final graph, merge, delete branch, force-push, or mark Ready for review.

## 5. Post-review final baseline and merge checkpoint

- [ ] Receive independent review approval or approval with only non-blocking notes.
- [ ] Archive the OpenSpec change only after the approval verdict permits archive.
- [ ] Run post-archive strict OpenSpec validation, full Python tests, and `git diff --check`.
- [ ] Create project-owned post-archive validation evidence JSON at `openspec/validation/frozen-project-graph-baseline.post-archive.json` containing `change_name`, `archive_commit`, `validated_source_commit`, `openspec_change_validation`, `openspec_all_validation`, `python_tests`, and `git_diff_check`.
- [ ] Identify archive commit `A` and post-archive validated source commit `S`.
- [ ] Commit only the approved post-archive validation evidence JSON in evidence commit `E`, with no other `S..E` changes.
- [ ] Generate the final baseline from `E` with `baseline_stage = final`, explicit source ref, `target_branch = master`, and `-PostArchiveValidationEvidence`.
- [ ] Commit only allowlisted graph artifacts in graph-only commit `G`, with `baseline.json.indexed_source_commit = E`.
- [ ] Perform lightweight graph integrity review.
- [ ] Verify remote feature HEAD equals reviewed `G` before merge.
- [ ] Merge only after the final graph-only commit review permits it.
