# Tasks: Generalize final Graphify refresh evidence

## 1. Implement approved contracts

- [ ] 1.1 Implement the deterministic ordinary evidence path `openspec/validation/<change-name>.post-archive.json`.
- [ ] 1.2 Implement exact ordinary evidence schema validation, including rejection of unknown or missing top-level and nested fields.
- [ ] 1.3 Reject self-referential `evidence_commit` and `indexed_source_commit` fields in ordinary evidence.
- [ ] 1.4 Derive `evidence_commit` and `indexed_source_commit` from clean `SourceRoot HEAD` and require explicit `SourceRef` equality.
- [ ] 1.5 Implement the exact ordinary lineage ordering `archive_commit <= validated_source_commit < evidence_commit`.
- [ ] 1.6 Require `validated_source_commit..HEAD` to contain exactly the deterministic evidence JSON with no process-only allowlist.
- [ ] 1.7 Retain the historical `frozen-project-graph-baseline` contract as an explicit compatibility path.

## 2. Wrapper implementation

- [ ] 2.1 Refactor `tools/refresh_project_graph.ps1` to separate evidence path, committed-byte, exact-schema, archive-state, ancestry, source-binding, verdict, and evidence-only delta checks.
- [ ] 2.2 Verify the declared archive path exists at `validated_source_commit` and the active change path is absent.
- [ ] 2.3 Verify ordinary evidence is absent from `validated_source_commit` and present as committed bytes at `HEAD`.
- [ ] 2.4 Reject path traversal, absolute paths, wrong change/path pairing, alternate extensions, untracked/ignored/modified evidence, invalid SHAs, invalid ancestry, stale source refs, and any non-evidence path after validation.
- [ ] 2.5 Preserve existing Graphify version, artifact allowlist, canonicalization, hash, sensitive-data, topology, ghost-node, and publication protections.

## 3. Documentation and specifications

- [ ] 3.1 Update `docs/project-graph-runbook.md` with the exact ordinary archived-change evidence schema and command arguments.
- [ ] 3.2 Document that `evidence_commit` and `indexed_source_commit` are wrapper-derived and MUST NOT appear in ordinary evidence JSON.
- [ ] 3.3 Document the strict evidence-only `validated_source_commit..HEAD` boundary with no process allowlist.
- [ ] 3.4 Document that an older blocked feature incorporating the repaired `master` requires renewed independent validation before final-refresh evidence.
- [ ] 3.5 Clearly preserve the historical frozen-baseline workflow without reinterpreting its published evidence.
- [ ] 3.6 Update applicable root OpenSpec project-graph workflow requirements during archive.

## 4. Tests

- [ ] 4.1 Add positive coverage for historical frozen-baseline evidence.
- [ ] 4.2 Add positive coverage for exact ordinary archived-change evidence.
- [ ] 4.3 Add negative coverage for `evidence_commit`, `indexed_source_commit`, unknown fields, missing fields, and unknown nested fields.
- [ ] 4.4 Add negative coverage for malformed, missing, untracked, ignored, modified, wrong-path, wrong-change, and alternate-extension evidence.
- [ ] 4.5 Add negative coverage for invalid archive state, full-SHA format, ancestry, source binding, verdict, and required checks.
- [ ] 4.6 Add negative coverage for any non-evidence path in `validated_source_commit..HEAD`, including Graphify-policy or process files.
- [ ] 4.7 Add coverage proving that an older feature must be independently revalidated after incorporating the repaired wrapper.
- [ ] 4.8 Verify no regression to generated artifact scope, encoding, hashes, sensitive-data scans, ghost-node checks, and topology checks.

## 5. Validation

- [ ] 5.1 Run focused Graphify workflow tests.
- [ ] 5.2 Run the full offline Python test suite.
- [ ] 5.3 Run `git diff --check`.
- [ ] 5.4 Run `.\openspec.cmd validate generalize-final-graph-refresh-evidence --strict` using the repository-local wrapper.
- [ ] 5.5 Run `.\openspec.cmd validate --all --strict` using the repository-local wrapper.
- [ ] 5.6 Publish the implementation commit and obtain independent validation evidence from a clean detached remote worktree.

## 6. Archive, merge, and PR #16 recovery

- [ ] 6.1 Archive this change only after published independent approval.
- [ ] 6.2 Run post-archive strict validation, full offline tests, and repository-protection checks.
- [ ] 6.3 Merge the infrastructure change to `master` according to repository workflow.
- [ ] 6.4 Update branch `agent/equipment-room-vip-context` with the repaired `master` without force-push.
- [ ] 6.5 Independently review the incorporated commits and revalidate the resulting published PR #16 remote HEAD.
- [ ] 6.6 Create `openspec/validation/equipment-room-vip-context.post-archive.json` containing the renewed validated source commit and commit only that file.
- [ ] 6.7 Rerun PR #16 final Graphify refresh with `SourceRoot HEAD = SourceRef = evidence commit`.
- [ ] 6.8 Perform independent final graph review before PR #16 merge.
