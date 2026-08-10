## 1. Baseline and reproduction

- [ ] Read `RULES.md` and confirm the current remote `master`, feature-branch HEAD, PR state, and pinned OpenSpec version before implementation.
- [ ] Confirm the implementation branch is based on the approved change base and contains no unrelated changes.
- [ ] Reproduce the terminal-root-requirement archive EOF defect with the pinned repository-local OpenSpec in a disposable clean worktree or temporary repository and record the exact `git diff --check` failure.
- [ ] Confirm changing delta-file EOF alone does not remove the generated root-spec defect, so implementation targets repository-local tooling rather than feature deltas.

## 2. Archive compatibility helper

- [x] Add a tracked Node standard-library helper under `tools/` for archive preflight, archive-generated root-spec discovery, minimal EOF normalization, and post-normalization whitespace checking.
- [x] Make preflight fail before upstream archive if `openspec/specs/` contains pre-existing tracked, staged, or untracked changes.
- [x] After successful upstream archive, identify only changed/new existing `openspec/specs/**/spec.md` files as normalization targets.
- [x] Fail closed before normalization if successful upstream archive leaves any staged change under `openspec/specs/`; do not modify the staged file or Git index.
- [x] Fail closed without rewriting bytes when a selected root spec is empty or contains only whitespace.
- [x] Normalize only terminal empty/whitespace-only lines, leave non-empty-line trailing whitespace untouched, ensure exactly one terminal line terminator, and preserve observable LF/CRLF style.
- [x] Keep normalization idempotent and never modify files outside the selected archive-generated root-spec set.

## 3. Repository-local wrapper integration

- [x] Update `openspec.cmd` so only a first positional `archive` command receives preflight/postprocessing behavior.
- [x] Preserve original arguments, output, and upstream exit codes for non-archive commands.
- [x] Do not run normalization after a failed upstream archive.
- [x] After successful archive normalization, run repository-wide `git diff --check` and `git diff --cached --check`, returning non-zero if either reports a whitespace defect.
- [x] Validate every selected new untracked root spec against an empty baseline using a portable Git-compatible whitespace check without staging the real file or mutating the index.
- [x] Preserve the pinned repository-local OpenSpec executable as semantic archive authority; do not patch `node_modules` or add an npm dependency.

## 4. Regression coverage

- [x] Add focused Node tests using temporary Git repositories/fake local OpenSpec execution for wrapper/helper behavior.
- [x] Cover no terminal newline, one terminal newline, multiple blank lines, whitespace-only blank lines, internal blank-line preservation, LF, and CRLF.
- [ ] Cover changed/new root-spec scoping and prove unrelated root specs, archived change files, and non-root Markdown remain unchanged.
- [x] Cover dirty-root-spec preflight and prove upstream archive is not invoked.
- [x] Cover upstream archive failure and prove postprocessing is not invoked.
- [x] Cover a fake upstream that stages a root spec: wrapper fails before normalization, the staged file and index remain unchanged, and no focused test mutates the real index.
- [x] Cover empty selected root spec failure with bytes unchanged.
- [x] Cover whitespace-only selected root spec failure with bytes unchanged.
- [x] Cover new untracked root spec standalone whitespace validation: trailing whitespace fails without normalization removing it, while a clean new root spec passes, remains untracked, and leaves the index unchanged.
- [ ] Cover successful archive orchestration followed by clean `git diff --check`, `git diff --cached --check`, and standalone new-untracked-root validation.
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
