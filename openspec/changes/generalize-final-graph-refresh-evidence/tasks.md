# Tasks: Generalize final Graphify refresh evidence

## 1. Architecture and contracts

- [ ] 1.1 Review and approve the reusable ordinary-change evidence schema and deterministic evidence path policy.
- [ ] 1.2 Define exact Git lineage rules for validated source, archive, evidence, and indexed source commits.
- [ ] 1.3 Define the fail-closed post-evidence mutation boundary.
- [ ] 1.4 Confirm backward compatibility for `frozen-project-graph-baseline` without weakening its published gate.

## 2. Wrapper implementation

- [ ] 2.1 Refactor `tools/refresh_project_graph.ps1` to separate evidence path, committed-byte, schema, archive-state, ancestry, verdict, and mutation-boundary checks.
- [ ] 2.2 Support deterministic change-scoped evidence under `openspec/validation/`.
- [ ] 2.3 Retain the historical frozen-baseline evidence contract as an explicit compatibility path.
- [ ] 2.4 Reject path traversal, absolute paths, wrong change/path pairing, untracked/ignored/modified evidence, invalid SHAs, invalid ancestry, stale source refs, and disallowed post-evidence mutations.
- [ ] 2.5 Preserve existing Graphify version, artifact allowlist, canonicalization, hash, sensitive-data, topology, ghost-node, and publication protections.

## 3. Documentation and specifications

- [ ] 3.1 Update `docs/project-graph-runbook.md` with the ordinary archived-change final refresh workflow.
- [ ] 3.2 Clearly separate the historical `A -> S -> E -> G` frozen-baseline workflow from later change workflows.
- [ ] 3.3 Update applicable root OpenSpec project-graph workflow requirements during archive.

## 4. Tests

- [ ] 4.1 Add positive coverage for historical frozen-baseline evidence.
- [ ] 4.2 Add positive coverage for an ordinary archived-change evidence flow.
- [ ] 4.3 Add negative coverage for malformed, missing, untracked, ignored, modified, wrong-path, and wrong-change evidence.
- [ ] 4.4 Add negative coverage for invalid archive state, SHA, ancestry, source binding, verdict, required checks, and post-evidence mutations.
- [ ] 4.5 Verify no regression to generated artifact scope, encoding, hashes, sensitive-data scans, ghost-node checks, and topology checks.

## 5. Validation

- [ ] 5.1 Run focused Graphify workflow tests.
- [ ] 5.2 Run the full offline Python test suite.
- [ ] 5.3 Run `git diff --check`.
- [ ] 5.4 Run `./openspec.cmd validate generalize-final-graph-refresh-evidence --strict` using the repository-local wrapper on the target platform syntax.
- [ ] 5.5 Run `./openspec.cmd validate --all --strict` using the repository-local wrapper on the target platform syntax.
- [ ] 5.6 Publish implementation commit and obtain independent validation evidence.

## 6. Archive and unblock

- [ ] 6.1 Archive this change only after published independent approval.
- [ ] 6.2 Run post-archive strict validation and full offline tests.
- [ ] 6.3 Merge the infrastructure change according to repository workflow.
- [ ] 6.4 Return to PR #16 and rerun its final Graphify refresh through the repaired repository-local wrapper.
- [ ] 6.5 Perform independent final graph review before PR #16 merge.