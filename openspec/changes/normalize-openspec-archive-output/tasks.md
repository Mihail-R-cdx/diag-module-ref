## 1. Baseline and reproduction

- [ ] Read `RULES.md` and confirm the current remote `master`, feature-branch HEAD, PR state, and pinned OpenSpec version before implementation.
- [ ] Confirm the implementation branch is based on the approved change base and contains no unrelated changes.
- [ ] Reproduce the terminal-root-requirement archive EOF defect with the pinned repository-local OpenSpec in a disposable clean worktree or temporary repository and record the exact `git diff --check` failure.
- [ ] Confirm changing delta-file EOF alone does not remove the generated root-spec defect, so implementation targets repository-local tooling rather than feature deltas.

## 2. Archive compatibility helper

- [ ] Add a tracked Node standard-library helper under `tools/` for archive preflight, archive-generated root-spec discovery, minimal EOF normalization, and post-normalization whitespace checking.
- [ ] Make preflight fail before upstream archive if `openspec/specs/` contains pre-existing tracked, staged, or untracked changes.
- [ ] After successful upstream archive, identify only changed/new existing `openspec/specs/**/spec.md` files as normalization targets.
- [ ] Normalize only terminal empty/whitespace-only lines, leave non-empty-line trailing whitespace untouched, ensure exactly one terminal line terminator, and preserve observable LF/CRLF style.
- [ ] Keep normalization idempotent and never modify files outside the selected archive-generated root-spec set.

## 3. Repository-local wrapper integration

- [ ] Update `openspec.cmd` so only a first positional `archive` command receives preflight/postprocessing behavior.
- [ ] Preserve original arguments, output, and upstream exit codes for non-archive commands.
- [ ] Do not run normalization after a failed upstream archive.
- [ ] After successful archive normalization, run `git diff --check` and return non-zero if any whitespace defect remains.
- [ ] Preserve the pinned repository-local OpenSpec executable as semantic archive authority; do not patch `node_modules` or add an npm dependency.

## 4. Regression coverage

- [ ] Add focused Node tests using temporary Git repositories/fake local OpenSpec execution for wrapper/helper behavior.
- [ ] Cover no terminal newline, one terminal newline, multiple blank lines, whitespace-only blank lines, internal blank-line preservation, LF, and CRLF.
- [ ] Cover changed/new root-spec scoping and prove unrelated root specs, archived change files, and non-root Markdown remain unchanged.
- [ ] Cover dirty-root-spec preflight and prove upstream archive is not invoked.
- [ ] Cover upstream archive failure and prove postprocessing is not invoked.
- [ ] Cover successful archive orchestration followed by clean `git diff --check`.
- [ ] Cover non-archive passthrough and upstream exit-code preservation.
- [ ] Perform a disposable integration check against the real pinned OpenSpec reproducer and prove the formerly failing terminal-root-spec archive now passes `git diff --check`.

## 5. Workflow documentation

- [ ] Update `RULES.md` to describe the archive compatibility layer, dirty-root-spec preflight, unchanged pinned dependency authority, and the fact that post-archive `git diff --check` remains mandatory.
- [ ] Do not weaken independent validation, archive, post-archive, or merge requirements.

## 6. Implementation validation and publication

- [ ] Run the focused Node tooling tests and record exact counts/results.
- [ ] Run the full offline Python suite without copying prior counts.
- [ ] Run `./openspec.cmd validate normalize-openspec-archive-output --strict` and `./openspec.cmd validate --all --strict` using only the repository-local wrapper.
- [ ] Run `git diff --check` and review the complete implementation diff for unrelated files, package-pin changes, `node_modules`, credentials, inventory, or Graphify artifacts.
- [ ] Create a focused implementation commit and push `agent/normalize-openspec-archive-output`; confirm local/remote SHA equality.

## 7. Independent validation

- [ ] Validate the published remote HEAD in a separate clean detached worktree and confirm detached/local SHA equals current remote branch SHA.
- [ ] Re-run focused Node tests, full offline Python tests, both strict OpenSpec validations, and `git diff --check` with fresh counts.
- [ ] Independently inspect wrapper/helper scope and verify non-archive passthrough, failure propagation, root-spec isolation, and no semantic Markdown rewriting.
- [ ] Independently execute the real pinned-OpenSpec terminal-requirement reproducer and confirm archive plus post-archive `git diff --check` pass.
- [ ] Issue `APPROVE` only with no CRITICAL, HIGH, or MEDIUM findings and all required checks passing.

## 8. Archive and merge readiness

- [ ] After independent approval, archive `normalize-openspec-archive-output` only with `./openspec.cmd archive normalize-openspec-archive-output --yes`.
- [ ] Review the resulting new root capability and archived change diff; confirm the corrected wrapper does not introduce unrelated root-spec changes.
- [ ] Run `./openspec.cmd validate --all --strict`, the full offline Python suite, focused Node tooling tests, and `git diff --check` after archive.
- [ ] Create and push a dedicated archive commit and confirm current remote archive HEAD before merge.
- [ ] Merge only with explicit user authorization.