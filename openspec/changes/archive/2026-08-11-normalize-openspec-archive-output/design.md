## Context

`openspec.cmd` is the repository authority for OpenSpec commands and currently forwards all arguments directly to the pinned `node_modules/.bin/openspec.cmd`. The pinned dependency is `@fission-ai/openspec` 1.6.0. During a real disposable archive-applicability check, upstream archive semantics applied correctly and post-archive strict validation passed, but terminal root requirements were serialized with an additional blank line at EOF. Changing the source delta EOF did not change the generated result, confirming that the compatibility defect is in archive recomposition rather than feature-spec content.

The repository must keep upstream OpenSpec responsible for semantic delta application while ensuring its tracked wrapper produces repository-compliant archive artifacts.

## Goals / Non-Goals

**Goals:**

- Make `./openspec.cmd archive <change> --yes` produce whitespace-clean root-spec output deterministically.
- Keep semantic archive behavior owned by the pinned upstream CLI.
- Normalize only root specs actually created or modified by a successful archive.
- Fail closed when pre-existing root-spec edits make archive-generated scope ambiguous.
- Preserve all non-archive wrapper behavior.
- Keep the compatibility layer idempotent if a future upstream release already emits correct EOF formatting.

**Non-Goals:**

- Patch or commit files under `node_modules`.
- Upgrade `@fission-ai/openspec` in this change.
- Ignore `blank-at-eof` or weaken `git diff --check`.
- Rewrite requirement/scenario content, headings, internal blank lines, or other whitespace defects.
- Normalize archived change artifacts or unrelated Markdown.
- Change application runtime code.

## Decisions

### 1. Keep upstream archive authoritative

`openspec.cmd` continues to invoke the pinned repository-local OpenSpec executable with the original archive arguments. The compatibility layer never applies OpenSpec deltas itself and never interprets requirement semantics.

For non-archive commands the wrapper remains a direct passthrough.

### 2. Add an archive-only preflight and postprocessor

For a first positional command of `archive`, the wrapper performs:

```text
root-spec preflight
-> pinned upstream archive
-> if upstream succeeds: fail closed if it staged any root-spec change
-> discover archive-generated root specs
-> fail closed for an empty/whitespace-only selected spec
-> minimally normalize eligible root specs
-> git diff --check
-> git diff --cached --check
-> standalone whitespace validation for each selected new untracked root spec
-> final wrapper exit code
```

The preflight fails before upstream archive if any path under `openspec/specs/` is already tracked-modified, staged-modified, or untracked. This makes the post-archive root-spec change set attributable to the archive operation. Ignored local artifacts remain irrelevant.

If upstream archive returns non-zero, the wrapper returns that failure and does not run normalization. It does not hide or repair partial upstream changes.

After a successful upstream archive and before discovery or normalization, the helper checks for staged changes under `openspec/specs/`. Any such change is unexpected upstream behavior: the wrapper fails non-zero, performs no EOF normalization, and leaves both the staged file and Git index untouched for diagnosis. The compatibility layer never stages, unstages, invokes `git add` or `git reset`, or otherwise mutates the index.

### 3. Derive the normalization set from Git after successful archive

Because root specs are clean at preflight and staged root output is rejected, files reported after archive as working-tree changes relative to `HEAD` or as newly untracked under `openspec/specs/` are archive-generated. The helper filters this set to existing files matching `openspec/specs/**/spec.md`.

Deleted paths are not rewritten. Files outside the root-spec tree and files under `openspec/changes/archive/` are never normalization targets.

### 4. Normalize EOF minimally

The helper operates on UTF-8 file bytes/text without reformatting Markdown. For each selected root spec it:

- leaves all content before the terminal blank-line region unchanged;
- removes only excess terminal empty/whitespace-only lines;
- leaves trailing spaces on a non-empty content line untouched, so `git diff --check` can still reject them;
- ensures exactly one terminal line terminator;
- preserves the file's terminal line-ending convention (`LF` or `CRLF`) when one is observable, defaulting to `LF` only when no line ending exists.

Before any rewrite, the helper verifies that the selected file contains at least one non-whitespace character. An empty or whitespace-only selected file is anomalous archive output, not an EOF-formatting case: the wrapper fails non-zero, does not rewrite that file, and leaves its bytes visible for diagnosis.

Running the helper repeatedly on already-normalized output is a no-op.

### 5. Whitespace validation remains authoritative

After normalization, the archive wrapper runs repository-wide `git diff --check` and `git diff --cached --check`; either failure causes a non-zero wrapper result. The latter checks staged whitespace anywhere in the repository, without treating staged root-spec output as supported. Each selected new untracked root spec also receives a standalone, portable Git-compatible whitespace check against an empty baseline. That check covers the complete untracked file, detects standard whitespace defects including trailing whitespace, does not stage the real file or mutate the index, and causes a non-zero wrapper result on a finding. The implementation may select a portable no-index/empty-baseline invocation, but must not use a platform-specific hardcoded null path.

Normal repository archive workflow still repeats `git diff --check`, strict validation, full tests, and archive/root-spec review as required by `RULES.md`.

### 6. Use a tracked Node standard-library helper

The helper is implemented as a tracked `.mjs` utility under `tools/` and uses only Node and Git already required by the OpenSpec workflow. No new npm dependency is added and the package pin remains unchanged.

`openspec.cmd` owns orchestration; the helper owns preflight/scope discovery/EOF normalization/post-check behavior. The helper does not alter the Git index. This avoids editing third-party installation output and survives `npm ci`.

### 7. Regression coverage includes wrapper orchestration

Focused Node tests use temporary Git repositories and a fake repository-local OpenSpec executable to exercise the tracked wrapper/helper boundary without modifying real root specs. Coverage must include:

- no newline -> exactly one newline;
- one newline -> no change;
- multiple terminal blank lines -> exactly one newline;
- whitespace-only terminal blank lines -> removed;
- LF and CRLF preservation;
- internal blank lines unchanged;
- unrelated/non-root files unchanged;
- dirty root-spec preflight prevents upstream archive execution;
- failed upstream archive does not trigger normalization;
- staged root-spec output fails closed before normalization and leaves the index unchanged;
- empty and whitespace-only selected root specs fail closed with bytes unchanged;
- successful archive normalizes only changed/new root specs and then passes both repository-wide whitespace checks;
- a new untracked root spec is checked without staging; trailing whitespace fails while a clean untracked root spec passes and remains untracked;
- non-archive commands remain passthrough and preserve the upstream exit code.

A disposable real-OpenSpec reproduction/validation is also required during implementation/independent validation to prove the original terminal-requirement EOF case is fixed with the pinned dependency.

## Risks / Trade-offs

- **A postprocessor could hide unrelated defects.** Limit it to terminal blank-line excess on archive-generated root specs, then run both repository-wide diff checks and a standalone check for new untracked root specs so other defects remain visible.
- **Upstream could unexpectedly stage root output.** Fail closed before normalization and leave the index untouched rather than trying to reconcile staged and working-tree representations.
- **An archive could create a semantically empty root spec.** Fail closed without rewriting its bytes; that is invalid output, not compatible EOF formatting.
- **Pre-existing root-spec edits could be normalized accidentally.** Fail before archive when the root-spec tree is dirty.
- **A future upstream version may fix the bug.** The normalizer is idempotent, so correct upstream output remains unchanged; dependency upgrades remain a separate reviewed change.
- **Batch argument routing can diverge from the CLI.** Only the repository-approved form with `archive` as the first command token receives compatibility behavior; all other commands retain passthrough semantics.

## Migration Plan

1. Implement the helper and archive-only wrapper orchestration without changing the dependency pin.
2. Add focused Node regression tests and reproduce the original EOF failure against the pinned upstream tool before confirming the fix.
3. Run focused tests, full Python offline tests, repository-local strict validation, and `git diff --check`.
4. Independently validate from the current remote HEAD, including a clean disposable real archive case that modifies a terminal root requirement and must finish whitespace-clean.
5. Archive this tooling change through the corrected wrapper, repeat post-archive checks, and merge only after the normal workflow permits it.

## Open Questions

None. The compatibility boundary is intentionally narrow and does not depend on an upstream release.
