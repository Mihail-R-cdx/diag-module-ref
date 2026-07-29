# Tasks: Decouple project graph refresh

## 1. Governance and ordinary workflow

- [ ] 1.1 Update `RULES.md` so ordinary OpenSpec architecture, implementation, independent validation, archive, post-archive checks, and merge do not require Graphify refresh.
- [ ] 1.2 State explicitly that an absent or stale graph does not block ordinary validation, archive, post-archive checks, or merge and does not require a change-specific stale-graph exception.
- [ ] 1.3 Remove ordinary-change requirements for renewed validation solely for Graphify, validation-report-only commits, Graphify evidence JSON, evidence-only commits, and graph-only commits.
- [ ] 1.4 Preserve the authority order and the requirement to verify Graphify-derived hypotheses in current source and tests.
- [ ] 1.5 After architecture `APPROVE`, close PR #17 without merge and retain its branch for forensic/reference use.

## 2. Repository-local wrapper

- [ ] 2.1 Make `FullRebuild` the default graph publication mode and retain `Incremental` only as an optional mode under the approved preconditions.
- [ ] 2.2 Remove publishing mode `Initial` and caller-controlled `BaselineStage`.
- [ ] 2.3 Remove `PostArchiveValidationEvidence`, verification-report parsing, post-archive evidence JSON parsing, archive-state checks, and feature-change lineage checks.
- [ ] 2.4 Derive `indexed_source_commit` from clean `SourceRoot HEAD` and require explicit `SourceRef` to resolve to the same full SHA.
- [ ] 2.5 Publish new maintenance baselines with `baseline_stage = final`, `indexed_source_ref = origin/master`, and `target_branch = master`.
- [ ] 2.6 Preserve exact Graphify version pinning, clean source state, source/output separation, code-only corpus, output allowlist, canonical UTF-8/LF output, valid JSON, nonzero counts, and published-byte hashes.
- [ ] 2.7 Preserve secret, credential, inventory, absolute-path, user-specific path, unexpected-file, HTML, hook, watch, MCP, skill, and merge-driver rejection.
- [ ] 2.8 Preserve safe backup-and-restore publication so failed generation leaves the previous accepted baseline intact.
- [ ] 2.9 Preserve optional incremental rename/delete, ghost-node, topology, and integrity checks and force `FullRebuild` when their preconditions fail.
- [ ] 2.10 Keep `InstallExact` only if it remains a non-publishing pinned-tool helper.

## 3. Specifications and documentation

- [ ] 3.1 Reconcile root `agent-project-navigation` requirements with non-blocking stale graph behavior and separate maintenance refresh.
- [ ] 3.2 Add root `project-graph-refresh-workflow` requirements during archive.
- [ ] 3.3 Rewrite `docs/project-graph-runbook.md` around the separate `S -> G` maintenance workflow.
- [ ] 3.4 Document the exact maintenance command, source/output boundary, graph-only commit scope, and lightweight review checks.
- [ ] 3.5 Document `FullRebuild` as standard and `Incremental` as optional under unchanged version, ignore, encoding, source-root, and package-boundary policy.
- [ ] 3.6 Preserve the historical frozen baseline and `A -> S -> E -> G` only as forensic history, not a supported future workflow.

## 4. Focused workflow tests

- [ ] 4.1 Add positive coverage for `FullRebuild` from one clean exact `origin/master` source SHA without archive or evidence inputs.
- [ ] 4.2 Verify published metadata binds `baseline_stage = final`, `indexed_source_commit = S`, `indexed_source_ref = origin/master`, and `target_branch = master`.
- [ ] 4.3 Add negative coverage for dirty source, unresolved or mismatched source ref, invalid source/output boundary, invalid target, and unexpected source mutation.
- [ ] 4.4 Remove tests that treat ordinary feature `A -> V -> R -> E -> G` lineage, verification metadata blocks, or Graphify evidence JSON as supported workflow.
- [ ] 4.5 Verify the wrapper does not require or inspect archived OpenSpec changes, `verification-report.md`, or `openspec/validation/*.post-archive.json`.
- [ ] 4.6 Preserve coverage for generated artifact scope, canonical encoding, JSON validity, nonzero counts, hashes, sensitive-data/path scans, and safe publication.
- [ ] 4.7 Preserve incremental rename/delete, ghost-node, topology, and fallback-to-full-rebuild coverage.
- [ ] 4.8 Verify a failed refresh leaves the previously accepted baseline unchanged.

## 5. Implementation validation

- [ ] 5.1 Run focused Graphify workflow tests.
- [ ] 5.2 Run the full offline Python test suite.
- [ ] 5.3 Run `git diff --check`.
- [ ] 5.4 Run `.\openspec.cmd validate decouple-project-graph-refresh --strict`.
- [ ] 5.5 Run `.\openspec.cmd validate --all --strict`.
- [ ] 5.6 Verify no application production code, unrelated tests, validation evidence, archived changes, or `graphify-out/` artifacts changed.
- [ ] 5.7 Commit and push the implementation before requesting independent validation.

## 6. Independent validation, archive, and merge

- [ ] 6.1 Independently validate the current published remote implementation HEAD in a clean detached worktree.
- [ ] 6.2 Require passing focused tests, full offline tests, strict change validation, strict all validation, repository-protection checks, and `git diff --check`.
- [ ] 6.3 Archive only after `APPROVE` or `APPROVE WITH NON-BLOCKING NOTES`.
- [ ] 6.4 Run ordinary post-archive strict validation, full offline tests, archive/root-spec diff review, and repository-protection checks.
- [ ] 6.5 Merge without any Graphify refresh, evidence JSON, report-only commit, evidence-only commit, graph-only commit, or stale-graph exception.
- [ ] 6.6 Schedule a separate graph maintenance refresh later only by explicit architect decision.
