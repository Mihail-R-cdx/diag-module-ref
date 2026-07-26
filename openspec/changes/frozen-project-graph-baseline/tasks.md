# Tasks

## 1. Repository policy and corpus

- [ ] Re-read `RULES.md`, current root specs, `.gitignore`, and the equipment inventory runbook.
- [ ] Record approved architecture branch HEAD and work only from that exact revision in a clean worktree.
- [ ] Enumerate actual Python source/test roots and root entry points; do not invent directories.
- [ ] Add a short `RULES.md` Graphify frozen-baseline section without duplicating the runbook.
- [ ] Add `.graphifyignore` with explicit protection for graph output, worktrees, inventory, Excel, secrets, deployment-local data, caches, logs, and temporary artifacts.

## 2. Tooling and documentation

- [ ] Install `graphifyy==0.9.26` in an isolated tool environment; do not add it to application dependencies.
- [ ] Capture `graphify --version` and help for `extract`, `check-update`, and `update`.
- [ ] Implement `tools/refresh_project_graph.ps1` with explicit initial, incremental, full-rebuild, and opt-in exact-install modes.
- [ ] Ensure wrapper failures remain nonzero and no automatic commit, push, merge, archive, hook, watch, MCP, or skill installation occurs.
- [ ] Add `docs/project-graph-runbook.md` covering authority, metadata, frozen behavior, ChatGPT/Codex use, commands, staleness, security, Windows operation, troubleshooting, and upgrade policy.

## 3. Real initial baseline

- [ ] Check out a clean exact source commit and run real Graphify 0.9.26 code-only extraction with visualization disabled.
- [ ] Verify actual 0.9.26 output files and commit only the approved allowlist.
- [ ] Create `graphify-out/baseline.json` with full indexed source SHA, exact version, hashes, counts, and no local identity/path data.
- [ ] Validate graph and manifest JSON, nonzero nodes/edges, repository-relative source paths, excluded-path absence, and no self-indexing.
- [ ] Confirm no HTML, semantic caches, converted documents, cost/API outputs, logs, environments, or package files are committed.

## 4. Security and query evidence

- [ ] Run textual and structured scans for credentials, `.env`, keys, cookies, Session IDs, CSRF/access tokens, real inventory, Excel data, and user-specific absolute paths.
- [ ] Select at least five symbols/flows verified in current source, including available equivalents of `PDUController`, `InteractiveSessionController`, `EquipmentInventory`, credential-fallback ownership, and the PDU-to-related-codec path.
- [ ] For each smoke query, record exit 0, relevant node, existing source file, source confirmation, and honest confidence classification.

## 5. Reproducibility and incremental behavior

- [ ] Repeat build or compare topology on the same source commit and verify identical source-file set and node identities, with extracted-edge differences explained.
- [ ] Repeat portability checks from another clean worktree and verify no checkout-specific absolute paths.
- [ ] In a disposable probe outside the production branch, add a synthetic node/edge, run incremental update, then delete/rename it and verify correct removal or full-rebuild escalation.
- [ ] Restore the original baseline and ensure no probe artifacts are committed.
- [ ] Verify full-rebuild triggers for version/ignore/root/package changes, mass rename/delete, ghost nodes, integrity failure, unexpected topology shrink, threshold, and architect request.

## 6. Validation and publication

- [ ] Run `\.\openspec.cmd validate frozen-project-graph-baseline --strict`.
- [ ] Run `\.\openspec.cmd validate --all --strict`.
- [ ] Run `python -X faulthandler -m unittest discover -s tests -p "test_*.py"` and record the fresh count.
- [ ] Run `git diff --check` and `git status --short`.
- [ ] Confirm production code and application tests are unchanged unless a separately approved necessity is documented.
- [ ] Commit and push the focused implementation to `agent/frozen-project-graph-baseline`.
- [ ] Keep the PR Draft and report `READY FOR INDEPENDENT REVIEW`.
- [ ] Do not archive or merge.

## 7. Future refresh checkpoint

- [ ] After independent approval, archive, and post-archive validation, identify final source commit S.
- [ ] Run incremental refresh or mandatory full rebuild according to policy against exactly S.
- [ ] Commit only allowlisted graph artifacts in graph-only commit G, with `baseline.json.indexed_source_commit = S`.
- [ ] Perform lightweight graph integrity review and verify remote feature HEAD equals reviewed G before merge.
