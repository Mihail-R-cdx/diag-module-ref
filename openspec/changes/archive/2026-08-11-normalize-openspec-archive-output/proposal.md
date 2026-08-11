# Change: normalize-openspec-archive-output

## Why

The repository requires every OpenSpec archive to pass `git diff --check`, but the pinned repository-local OpenSpec 1.6.0 archive path can emit an extra blank line at EOF when it rebuilds a root specification whose terminal requirement is modified. This was reproduced during the CloudLink Box 310 archive-applicability work: the semantic archive succeeded and strict validation passed, while the generated root-spec diff failed only with `new blank line at EOF`.

The defect belongs to repository-local OpenSpec tooling, not to each individual feature delta. Requiring every change author to hand-edit generated root specs or distort delta EOF formatting is non-deterministic and hides the real compatibility boundary.

## What Changes

- Extend the tracked `openspec.cmd` archive path with a repository-local compatibility postprocessor while preserving the pinned upstream OpenSpec command as the authority that applies deltas.
- Before an archive, fail closed if `openspec/specs/**/spec.md` already contains tracked or untracked edits, so the wrapper can distinguish archive-generated root-spec changes from pre-existing work.
- Run the pinned upstream `archive` command unchanged.
- Only after a successful upstream archive, identify root specification files created or modified by that archive and normalize only terminal blank-line excess so each affected root spec ends with exactly one line terminator.
- Preserve internal Markdown bytes, requirement/scenario semantics, and the existing LF/CRLF convention; do not clean unrelated whitespace or modify archived change artifacts.
- Run `git diff --check` after normalization and return a non-zero wrapper exit code if any whitespace defect remains.
- Preserve current passthrough behavior, arguments, output, and exit codes for non-archive OpenSpec commands.
- Add repository-local regression coverage for EOF normalization, dirty-root-spec preflight, upstream archive failure, unrelated-file isolation, LF/CRLF behavior, and wrapper passthrough.
- Document the compatibility layer in `RULES.md` without relaxing the requirement for post-archive `git diff --check`.

## Capabilities

### New Capabilities

- `openspec-archive-output-normalization`: deterministic repository-local compatibility behavior for whitespace-clean OpenSpec archive output.

### Modified Capabilities

- None.

## Impact

Expected implementation areas:

- `openspec.cmd`
- a tracked Node standard-library helper under `tools/`
- focused Node regression tests
- `RULES.md`

The change does not patch or commit `node_modules`, does not change the pinned `@fission-ai/openspec` version, does not disable or weaken `git diff --check`, does not alter OpenSpec semantic merge rules, and does not modify application production code.