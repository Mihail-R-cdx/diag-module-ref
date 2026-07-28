# Tasks: Generalize final Graphify refresh evidence

## 1. Implement approved contracts

- [x] 1.1 Implement deterministic JSON path `openspec/validation/<change-name>.post-archive.json`.
- [x] 1.2 Implement exact closed JSON schema including `verification_report_path` and `verification_report_commit`.
- [x] 1.3 Reject self-referential `evidence_commit` and `indexed_source_commit` fields.
- [x] 1.4 Derive `evidence_commit` and `indexed_source_commit` from clean `SourceRoot HEAD` and require `SourceRef` equality.
- [x] 1.5 Implement exact lineage `archive_commit <= V < R < E`, where `V` is validated source, `R` report commit, and `E` JSON commit.
- [x] 1.6 Require `V..R` to contain exactly the declared archived `verification-report.md`.
- [x] 1.7 Require `R..E` to contain exactly the deterministic JSON with no process-only allowlist.
- [x] 1.8 Implement the exact single `BEGIN VALIDATION METADATA` / `END VALIDATION METADATA` block contract.
- [x] 1.9 Retain the historical `frozen-project-graph-baseline` compatibility path.

## 2. Wrapper implementation

- [x] 2.1 Refactor `tools/refresh_project_graph.ps1` into path, committed-byte, exact-JSON-schema, exact-report-metadata, archive-state, ancestry, source-binding, verdict, and exact-delta checks.
- [x] 2.2 Verify archive path exists at `V` and active change path is absent.
- [x] 2.3 Read committed bytes from `R:<verification_report_path>` rather than PR text or an uncommitted report.
- [x] 2.4 Require exactly one literal metadata block with exactly eight ordered key/value lines and exact `key: value` grammar.
- [x] 2.5 Validate branch with `git check-ref-format --branch`, full lowercase SHA equality to `V`, allowed verdict, lowercase booleans, `archive_permitted = true`, and validator code/test flags both `false`.
- [x] 2.6 Reject duplicate/conflicting markers, quoted/example blocks, blank/comment/indented lines, duplicate/unknown/missing/reordered keys, invalid types, and free-form substring fallback.
- [x] 2.7 Verify JSON verdict and metadata verdict agree and authoritative human-readable permission/change statements do not contradict metadata.
- [x] 2.8 Verify `verification_report_commit` equals `R`, the report is committed and unchanged, and `V..R` contains only that report.
- [x] 2.9 Verify the JSON is absent from `R`, committed at `E`, `R..E` contains only that JSON, and `SourceRoot HEAD = SourceRef = E`.
- [x] 2.10 Reject traversal, absolute paths, wrong path/change pairing, alternate extensions, untracked/ignored/modified artifacts, invalid SHAs/ancestry, stale refs, incomplete reports, and extra paths in either delta.
- [x] 2.11 Preserve existing Graphify version, artifact allowlist, canonicalization, hash, sensitive-data, topology, ghost-node, and publication protections.

## 3. Documentation and specifications

- [x] 3.1 Update `docs/project-graph-runbook.md` with exact `V -> R -> E -> G` workflow and command arguments.
- [x] 3.2 Document the exact JSON schema and wrapper-derived commit facts.
- [x] 3.3 Document the exact validation metadata delimiters, ordered keys, grammar, allowed values, and rejection rules.
- [x] 3.4 Document all `RULES.md` facts still required in the human-readable `verification-report.md`.
- [x] 3.5 Document exact `V..R` report-only and `R..E` JSON-only boundaries.
- [x] 3.6 Document that older blocked features incorporating repaired `master` require renewed independent validation.
- [x] 3.7 Preserve historical frozen-baseline workflow without reinterpretation.
- [x] 3.8 Update applicable root OpenSpec workflow requirements during archive.

## 4. Tests

- [x] 4.1 Add positive coverage for historical frozen-baseline evidence.
- [x] 4.2 Add positive coverage for ordinary `V -> R -> E -> G` lineage with one exact metadata block.
- [x] 4.3 Add negative coverage for self-referential, unknown, missing, or malformed JSON fields.
- [x] 4.4 Add negative coverage for wrong/missing/untracked/ignored/modified report and JSON paths.
- [x] 4.5 Add negative coverage for missing, duplicate, conflicting, quoted, malformed, or reordered metadata blocks/keys.
- [x] 4.6 Add negative coverage for invalid branch, partial/uppercase SHA, disallowed verdict, invalid boolean, denied archive permission, validator code/test mutation, and JSON/report verdict mismatch.
- [x] 4.7 Add negative coverage proving substring search cannot accept historical, quoted, example, or conflicting values.
- [x] 4.8 Add negative coverage for human-readable authoritative statements that contradict the metadata block.
- [x] 4.9 Add negative coverage for report commit mismatch and any extra path in `V..R` or `R..E`.
- [x] 4.10 Add negative coverage for invalid archive state, SHAs, ancestry, source binding, verdict, and checks.
- [x] 4.11 Add coverage proving an older feature must be revalidated after incorporating repaired `master`.
- [x] 4.12 Verify no regression to artifact scope, encoding, hashes, sensitive-data scans, ghost-node, topology, and publication checks.

## 5. Architecture validation

- [ ] 5.1 From a clean checkout of the current published architecture HEAD, run `git diff --check`.
- [ ] 5.2 Run `\.\openspec.cmd validate generalize-final-graph-refresh-evidence --strict` using the repository-local wrapper.
- [ ] 5.3 Run `\.\openspec.cmd validate --all --strict` using the repository-local wrapper.
- [ ] 5.4 Record exact architecture HEAD, commands, exit codes, and passed/failed counts before architecture approval.

## 6. Implementation validation

- [x] 6.1 Run focused Graphify workflow tests.
- [x] 6.2 Run the full offline Python test suite.
- [x] 6.3 Run `git diff --check`.
- [x] 6.4 Run `\.\openspec.cmd validate generalize-final-graph-refresh-evidence --strict`.
- [x] 6.5 Run `\.\openspec.cmd validate --all --strict`.
- [ ] 6.6 Publish implementation commit and obtain independent validation in a clean detached remote worktree.

## 7. Archive, merge, and PR #16 recovery

- [ ] 7.1 Archive this change only after published independent approval.
- [ ] 7.2 Run post-archive strict validation, full offline tests, and repository-protection checks.
- [ ] 7.3 Merge the infrastructure change to `master`.
- [ ] 7.4 Update `agent/equipment-room-vip-context` with repaired `master` without force-push.
- [ ] 7.5 Review incorporated commits and publish the resulting PR #16 source commit `V`.
- [ ] 7.6 Independently revalidate `V` and update the archived `verification-report.md` with all `RULES.md` facts and the exact metadata block.
- [ ] 7.7 Commit only that report as `R`.
- [ ] 7.8 Create exact `equipment-room-vip-context.post-archive.json` referencing `V` and `R`, and commit only it as `E`.
- [ ] 7.9 Run PR #16 final Graphify refresh with `SourceRoot HEAD = SourceRef = E`.
- [ ] 7.10 Publish graph-only `G` and perform independent final graph review before merge.
