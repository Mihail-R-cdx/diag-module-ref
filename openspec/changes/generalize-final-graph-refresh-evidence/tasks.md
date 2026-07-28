# Tasks: Generalize final Graphify refresh evidence

## 1. Implement approved contracts

- [ ] 1.1 Implement deterministic JSON path `openspec/validation/<change-name>.post-archive.json`.
- [ ] 1.2 Implement exact closed JSON schema including `verification_report_path` and `verification_report_commit`.
- [ ] 1.3 Reject self-referential `evidence_commit` and `indexed_source_commit` fields.
- [ ] 1.4 Derive `evidence_commit` and `indexed_source_commit` from clean `SourceRoot HEAD` and require `SourceRef` equality.
- [ ] 1.5 Implement exact lineage `archive_commit <= V < R < E`, where `V` is validated source, `R` report commit, and `E` JSON commit.
- [ ] 1.6 Require `V..R` to contain exactly the declared archived `verification-report.md`.
- [ ] 1.7 Require `R..E` to contain exactly the deterministic JSON with no process-only allowlist.
- [ ] 1.8 Retain the historical `frozen-project-graph-baseline` compatibility path.

## 2. Wrapper implementation

- [ ] 2.1 Refactor `tools/refresh_project_graph.ps1` into path, committed-byte, exact-schema, report, archive-state, ancestry, source-binding, verdict, and exact-delta checks.
- [ ] 2.2 Verify archive path exists at `V` and active change path is absent.
- [ ] 2.3 Verify `verification_report_commit` equals `R`, the report is committed and unchanged, and it records/approves exactly `V`.
- [ ] 2.4 Verify the JSON is absent from `R`, committed at `E`, and `SourceRoot HEAD = SourceRef = E`.
- [ ] 2.5 Reject traversal, absolute paths, wrong path/change pairing, alternate extensions, untracked/ignored/modified artifacts, invalid SHAs/ancestry, stale refs, incomplete reports, and extra paths in either delta.
- [ ] 2.6 Preserve existing Graphify version, artifact allowlist, canonicalization, hash, sensitive-data, topology, ghost-node, and publication protections.

## 3. Documentation and specifications

- [ ] 3.1 Update `docs/project-graph-runbook.md` with exact `V -> R -> E -> G` workflow and command arguments.
- [ ] 3.2 Document the exact JSON schema and wrapper-derived commit facts.
- [ ] 3.3 Document all `RULES.md` facts required in renewed `verification-report.md`.
- [ ] 3.4 Document exact `V..R` report-only and `R..E` JSON-only boundaries.
- [ ] 3.5 Document that older blocked features incorporating repaired `master` require renewed independent validation.
- [ ] 3.6 Preserve historical frozen-baseline workflow without reinterpretation.
- [ ] 3.7 Update applicable root OpenSpec workflow requirements during archive.

## 4. Tests

- [ ] 4.1 Add positive coverage for historical frozen-baseline evidence.
- [ ] 4.2 Add positive coverage for ordinary `V -> R -> E -> G` lineage.
- [ ] 4.3 Add negative coverage for self-referential, unknown, missing, or malformed JSON fields.
- [ ] 4.4 Add negative coverage for wrong/missing/untracked/ignored/modified report and JSON paths.
- [ ] 4.5 Add negative coverage for report commit mismatch, report not approving `V`, and incomplete `RULES.md` validation facts.
- [ ] 4.6 Add negative coverage for any extra path in `V..R` or `R..E`.
- [ ] 4.7 Add negative coverage for invalid archive state, SHAs, ancestry, source binding, verdict, and checks.
- [ ] 4.8 Add coverage proving an older feature must be revalidated after incorporating repaired `master`.
- [ ] 4.9 Verify no regression to artifact scope, encoding, hashes, sensitive-data scans, ghost-node, topology, and publication checks.

## 5. Validation

- [ ] 5.1 Run focused Graphify workflow tests.
- [ ] 5.2 Run the full offline Python test suite.
- [ ] 5.3 Run `git diff --check`.
- [ ] 5.4 Run `.\openspec.cmd validate generalize-final-graph-refresh-evidence --strict`.
- [ ] 5.5 Run `.\openspec.cmd validate --all --strict`.
- [ ] 5.6 Publish implementation commit and obtain independent validation in a clean detached remote worktree.

## 6. Archive, merge, and PR #16 recovery

- [ ] 6.1 Archive this change only after published independent approval.
- [ ] 6.2 Run post-archive strict validation, full offline tests, and repository-protection checks.
- [ ] 6.3 Merge the infrastructure change to `master`.
- [ ] 6.4 Update `agent/equipment-room-vip-context` with repaired `master` without force-push.
- [ ] 6.5 Review incorporated commits and publish the resulting PR #16 source commit `V`.
- [ ] 6.6 Independently revalidate `V` and update the archived `verification-report.md` with all `RULES.md` evidence facts.
- [ ] 6.7 Commit only that report as `R`.
- [ ] 6.8 Create exact `equipment-room-vip-context.post-archive.json` referencing `V` and `R`, and commit only it as `E`.
- [ ] 6.9 Run PR #16 final Graphify refresh with `SourceRoot HEAD = SourceRef = E`.
- [ ] 6.10 Publish graph-only `G` and perform independent final graph review before merge.
