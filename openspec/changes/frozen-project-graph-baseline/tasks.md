# Tasks

## 1. Repository policy and corpus

- [x] Re-read `RULES.md`, current root specs, `.gitignore`, and the equipment inventory runbook.
- [x] Record approved architecture branch HEAD and work only from that exact revision in a clean worktree.
- [x] Enumerate actual Python source/test roots and root entry points; do not invent directories.
- [x] Add a short `RULES.md` Graphify frozen-baseline section without duplicating the runbook.
- [x] Add `.graphifyignore` with explicit protection for graph output, worktrees, inventory, Excel, secrets, deployment-local data, caches, logs, and temporary artifacts.

## 2. Tooling and documentation

- [x] Install `graphifyy==0.9.26` in an isolated tool environment; do not add it to application dependencies.
- [x] Capture `graphify --version` and help for `extract`, `check-update`, and `update`.
- [x] Implement `tools/refresh_project_graph.ps1` with explicit initial, incremental, full-rebuild, opt-in exact-install modes, clean `SourceRoot`/`OutputRoot` separation, atomic publication, and no dirty publish mode.
- [x] Ensure wrapper failures remain nonzero and no automatic commit, push, merge, archive, hook, watch, MCP, or skill installation occurs.
- [x] Add `docs/project-graph-runbook.md` covering authority, metadata, frozen behavior, ChatGPT/Codex use, commands, staleness, security, Windows operation, troubleshooting, and upgrade policy.

## 3. Real initial baseline

- [x] Check out a clean exact `origin/master` source commit and run real Graphify 0.9.26 code-only extraction with visualization disabled.
- [x] Verify actual 0.9.26 output files and commit only the approved allowlist.
- [x] Create `graphify-out/baseline.json` with full indexed `origin/master` source SHA, exact version, hashes, counts, and no local identity/path data.
- [x] Validate graph and manifest JSON, nonzero nodes/edges, repository-relative source paths, excluded-path absence, and no self-indexing.
- [x] Confirm no HTML, semantic caches, converted documents, cost/API outputs, logs, environments, or package files are committed.

## 4. Security and query evidence

- [x] Run textual and structured scans across all committed graph artifacts for credentials, `.env`, keys, cookies, Session IDs, CSRF/access tokens, real inventory, Excel data, high-entropy token-like values, graph self-indexing, and user-specific absolute paths.
- [x] Select at least five symbols/flows verified in current source, including available equivalents of `PDUController`, `InteractiveSessionController`, `EquipmentInventory`, credential-fallback ownership, and the PDU-to-related-codec path.
- [x] For each smoke query, record exit 0, matched node ids, source paths, edge ids/types, actual edge confidence or `NOT_AVAILABLE`, and source confirmation.

## 5. Reproducibility and incremental behavior

- [x] Repeat build or compare topology on the same source commit and verify identical source-file set and node identities, with extracted-edge differences explained.
- [x] Repeat portability checks from another clean worktree and verify no checkout-specific absolute paths.
- [x] In a disposable probe outside the production branch, add a synthetic node/edge, run incremental update, then delete/rename it and verify correct removal or enforced full-rebuild escalation without replacing the accepted baseline on failure.
- [x] Restore the original baseline and ensure no probe artifacts are committed.
- [x] Verify full-rebuild triggers for version/ignore/root/package changes, mass rename/delete, ghost nodes, integrity failure, unexpected topology shrink, threshold, and architect request.

## 6. Validation and publication

- [x] Run `\.\openspec.cmd validate frozen-project-graph-baseline --strict`.
- [x] Run `\.\openspec.cmd validate --all --strict`.
- [x] Run `python -X faulthandler -m unittest discover -s tests -p "test_*.py"` and record the fresh count.
- [x] Run `git diff --check` and `git status --short`.
- [x] Confirm production code and application tests are unchanged unless a separately approved necessity is documented.
- [x] Commit and push the focused implementation to `agent/frozen-project-graph-baseline`.
- [x] Keep the PR Draft and report `READY FOR INDEPENDENT REVIEW`.
- [x] Do not archive or merge.

## 7. Future refresh checkpoint

- [ ] After independent approval, archive, and post-archive validation, identify final source commit S.
- [ ] Run incremental refresh or mandatory full rebuild according to policy against exactly S.
- [ ] Commit only allowlisted graph artifacts in graph-only commit G, with `baseline.json.indexed_source_commit = S`.
- [ ] Perform lightweight graph integrity review and verify remote feature HEAD equals reviewed G before merge.
