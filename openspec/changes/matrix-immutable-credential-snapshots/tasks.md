# Tasks: Matrix immutable credential snapshots

## 1. Matrix credential mapping boundary

- [ ] 1.1 Read current `RULES.md`, the approved `credential-source-isolation` and `request-lifecycle-and-recovery` root specifications, current `gui/main_window.py`, current `gui/matrix_controller.py`, and focused Matrix tests before implementation.
- [ ] 1.2 Verify the implementation branch still contains this approved architecture and record the exact current remote branch HEAD and current `origin/master` before changing code.
- [ ] 1.3 Update the Matrix controller boundary to accept assigned credential candidates through `collections.abc.Mapping` semantics rather than requiring a concrete `dict`.
- [ ] 1.4 Apply the same mapping validity contract to candidate-secret collection and handler/session acquisition so redaction and handler inputs cannot diverge by container type.
- [ ] 1.5 Preserve immutable candidates without mutating them or introducing shared mutable credential state.
- [ ] 1.6 Update focused Matrix controller type annotations from concrete dictionary iterables to the supported mapping contract without performing an unrelated repository-wide typing refactor.
- [ ] 1.7 Preserve safe rejection of absent, out-of-range, or non-mapping candidates before handler construction and network I/O.
- [ ] 1.8 Ensure local candidate-shape failure remains non-secret, does not become confirmed device credential rejection, and does not authorize credential fallback.

## 2. Preserve approved Matrix lifecycle contracts

- [ ] 2.1 Keep candidate resolution, candidate ordering, starting-index selection, fallback advancement, and successful-index persistence owned by the application/composition boundary.
- [ ] 2.2 Keep one assigned candidate per Matrix operation and the same assigned candidate across supported transport attempts.
- [ ] 2.3 Do not add provider reads, candidate iteration, index changes, wrap-around, or success persistence to `MatrixController`, Matrix workers, or handlers.
- [ ] 2.4 Preserve Matrix session identity based on model, IP, protocol/port, non-secret credential-context revision, candidate index, and connected state; do not include credential values or the candidate container.
- [ ] 2.5 Preserve stale-operation suppression before handler acquisition and all existing stale callback gates.
- [ ] 2.6 Preserve structured authentication classification and prohibit string-based `auth`, `401`, or `403` fallback authority.
- [ ] 2.7 Preserve the prohibition on route replay or credential fallback after the route command was invoked, may have been delivered, or has an ambiguous outcome.
- [ ] 2.8 Preserve successful credential persistence only after an accepted final full Matrix refresh; session acquisition, route success, quick refresh, and stale success do not create a new persistence gate.

## 3. Redaction and public boundary

- [ ] 3.1 Collect non-empty assigned candidate values through the accepted mapping interface before handler connection, terminal callback rendering, or safe error formatting.
- [ ] 3.2 Verify immutable and mutable mappings with equivalent values produce equivalent Matrix redaction inputs.
- [ ] 3.3 Keep `MatrixOperationHandle`, public Matrix context, signals, results, errors, status text, and terminal output free of credential mappings, credential values, and private profile identity.
- [ ] 3.4 Do not weaken existing redaction helpers or add plaintext diagnostic logging for the candidate container.

## 4. Regression coverage

- [ ] 4.1 Add controller coverage using `MappingProxyType({"username": ..., "password": ...})` as the assigned candidate.
- [ ] 4.2 Prove `_candidate_for_context()` returns the selected immutable mapping and that the candidate is not mutated.
- [ ] 4.3 Prove `_candidate_secrets()` includes non-empty username/password values from the immutable mapping.
- [ ] 4.4 Prove `_acquire_session()` passes the immutable candidate's scalar username/password values to `ExtronIN1804Handler` and invokes `connect()`.
- [ ] 4.5 Prove immutable mapping input does not raise `No credentials for Extron IN1804` solely because of its concrete container type.
- [ ] 4.6 Preserve positive coverage for ordinary mutable `dict` candidates.
- [ ] 4.7 Add negative coverage proving absent, out-of-range, and non-mapping candidates stop before handler construction and network I/O.
- [ ] 4.8 Add redaction coverage where immutable candidate values appear in simulated handler terminal output or an exception and are absent from every public rendering boundary.
- [ ] 4.9 Add a focused production-path integration case using the same `MappingProxyType` snapshot shape created by `VCSDiagnosticApp._freeze_credential_candidates()` through Matrix full-refresh submission and handler construction.
- [ ] 4.10 Verify the integration test requires no real device, no real credential file, and no secret value in test output.
- [ ] 4.11 Re-run existing Matrix stale suppression, serialization, session invalidation, route safety, keepalive, cleanup, authentication classification, and successful credential persistence tests.

## 5. Focused implementation scope

- [ ] 5.1 Limit the expected production diff to `gui/matrix_controller.py`.
- [ ] 5.2 Limit focused test changes primarily to `tests/test_matrix_controller.py`.
- [ ] 5.3 If one existing main-window/request-snapshot test module is required for the production-path integration case, identify it explicitly and justify why controller-only coverage is insufficient.
- [ ] 5.4 Do not modify `gui/main_window.py` snapshot creation semantics, credential provider/schema code, IN1804 handler authentication or transport behavior, unrelated controllers/workers, root specs before archive, archived changes, validation evidence, or Graphify artifacts.
- [ ] 5.5 Review the final implementation diff for accidental secret values, credential fixtures resembling production secrets, or unrelated changes.

## 6. Implementation validation

- [ ] 6.1 Run focused Matrix controller tests with the repository-supported Python interpreter:

```powershell
python -m unittest tests.test_matrix_controller
```

- [ ] 6.2 Run Matrix handler security tests:

```powershell
python -m unittest tests.test_matrix_handler_security
```

- [ ] 6.3 Run any focused main-window/request-snapshot integration test module modified under task 5.3 and record its exact command and counts.
- [ ] 6.4 Run the full offline test suite and record exact passed, skipped, and failed counts:

```powershell
python -m unittest discover -s tests -p "test_*.py"
```

- [ ] 6.5 Run whitespace validation:

```powershell
git diff --check
```

- [ ] 6.6 Run repository-local strict change validation:

```powershell
.\openspec.cmd validate matrix-immutable-credential-snapshots --strict
```

- [ ] 6.7 Run repository-local strict validation of all OpenSpec artifacts:

```powershell
.\openspec.cmd validate --all --strict
```

- [ ] 6.8 Record interpreter, Node, npm, and pinned OpenSpec environment details required by `RULES.md`, exact commands, exit codes, and counts.

## 7. Publish implementation for independent validation

- [ ] 7.1 Review `git status`, complete diff, changed-file list, and `git diff --check` before committing.
- [ ] 7.2 Create focused implementation commit(s) and push to `agent/matrix-immutable-credential-snapshots` without amend, rebase, force-push, or history rewrite.
- [ ] 7.3 Verify local implementation HEAD equals `origin/agent/matrix-immutable-credential-snapshots` after push and the PR remains Draft.
- [ ] 7.4 Record the exact remote implementation SHA, change base, changed-file scope, validation commands, exit codes, and test counts.
- [ ] 7.5 Do not issue final `APPROVE`; request independent validation from a separate clean detached worktree created from the published remote branch HEAD.

## 8. Independent validation and archive applicability

- [ ] 8.1 Fetch the current remote branch, record its full SHA and subject, and create a clean detached validation worktree from `origin/agent/matrix-immutable-credential-snapshots` exactly as required by `RULES.md`.
- [ ] 8.2 Verify clean worktree status and local/remote SHA equality before tests.
- [ ] 8.3 Independently repeat focused tests, the full offline test suite, `git diff --check`, strict change validation, and strict all validation without copying prior counts.
- [ ] 8.4 Independently verify immutable mapping acceptance, handler construction/connect, redaction continuity, non-mapping rejection before I/O, ordinary dictionary compatibility, and no change to fallback, route, session, or successful-index policy.
- [ ] 8.5 Verify no credential value, candidate mapping, profile identity, session secret, or private request payload appears in public output or the diff.
- [ ] 8.6 Because this change adds root-spec requirements, perform a disposable archive-applicability check outside the feature branch using the repository-local wrapper, inspect the resulting archive/root-spec diff against the then-current root specifications, run `validate --all --strict`, and discard the worktree without publishing archive output.
- [ ] 8.7 Do not issue `READY FOR ARCHIVE` while any Critical, High, or Medium finding remains, a required check fails, the validated remote HEAD changed, the validation worktree was dirty, or archive applicability is unproven.

## 9. Archive and merge

- [ ] 9.1 Archive only after independent `APPROVE` or `APPROVE WITH NON-BLOCKING NOTES` and explicit workflow authorization.
- [ ] 9.2 Review the archive and root-spec diff to ensure only the approved added requirements are applied and existing Matrix contracts are not silently rewritten.
- [ ] 9.3 Run post-archive `git diff --check`, full offline tests, `.\openspec.cmd validate --all --strict`, and repository-protection checks.
- [ ] 9.4 Create and push a dedicated archive commit without rewriting history.
- [ ] 9.5 Before merge, recheck current `master`, PR state/Draft state, base/head, mergeability, remote archive HEAD, and new commits.
- [ ] 9.6 Do not merge, close the PR, or delete the branch without direct user authorization.
