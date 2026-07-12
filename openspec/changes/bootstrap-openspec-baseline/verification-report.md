# Independent baseline validation report

## Scope and verified revision

Validation date: 2026-07-12 (Europe/Moscow).

This report independently validates the published revision
`92ee7ffd4906deaf5bd1c94846a3acc823e0a650` — `Archive externalize device
credentials change` — for the active OpenSpec change
`bootstrap-openspec-baseline`.

The baseline's intended scope is to introduce the OpenSpec structure and
project context, record four observed application capabilities as a
reviewable baseline, preserve the prior reverse-engineered material as
historical context, and establish a safe path for later spec-driven changes.
It must not change production behavior.

`git fetch origin` confirmed that
`origin/agent/bootstrap-openspec-baseline` resolved to the validated SHA. All
checks ran in the separate detached worktree
`.independent-final-validation`, created from that remote revision. Before
validation, `git rev-parse HEAD` returned the same SHA and `git status
--short` was empty. The implementation checkout was therefore clean and did
not depend on the dirty primary worktree.

## Evidence reviewed

- Reviewed the bootstrap proposal, design, task list, change metadata, all
  four change specs, the current root specs, and the archived
  `externalize-device-credentials` change and report.
- Reviewed `.gitignore`, `openspec/config.yaml`, the change README, the
  repository workflow text in configuration, and the relevant Git history.
- `0d15404` (`Bootstrap OpenSpec baseline`) adds OpenSpec and change artifacts
  only; its parent-to-commit name-status contains no production code or test
  changes. The credential change is a separate sequence of commits, and
  `92ee7ffd` contains only its OpenSpec archive move and root-spec creation.
- The active and archived change directories are separated correctly. The
  active directory contains only `bootstrap-openspec-baseline`; the credential
  change is under `changes/archive/2026-07-12-externalize-device-credentials`.
- The two root credential specs preserve the archived requirements; their only
  observed archive-to-root transformation is OpenSpec's generated title,
  `Purpose`, and `Requirements` headings. Their generated Purpose text remains
  a `TBD` placeholder.

## Task verification

Task 2.2 is supported by the four capability specs and task 1.2 is partially
supported by `openspec/config.yaml`, which records project context, workflow
constraints, and the intended offline test command. The historical source
material referenced by proposal and task 2.3,
`specs/vcs-diagnostic-openspec.md`, is absent from this published revision
(`Test-Path` was false and `git ls-files -- specs` returned no tracked file).

Tasks 1.1 and 3.1 cannot be verified: the repository does not track or ship
`openspec.cmd`, and no `openspec` command or repository package metadata is
available in the clean checkout. Consequently the documented OpenSpec
workflow is not runnable. Task 3.2 has partial evidence from the passing
offline suite and protection checks below, but its checkbox remains unchecked
and strict validation cannot complete. Task 3.3 remains intentionally
unchecked and was not performed in this validation session.

## Commands and actual results

| Check | Result |
| --- | --- |
| `python -m unittest discover -s tests -p "test_*.py"` | `python` was not on PATH. Python 3.12.9 at the documented installed location ran the equivalent command successfully: 61 tests passed in 0.850 s. |
| `./openspec.cmd --help` | Failed: file is absent from the clean checkout. |
| `./openspec.cmd list` | Failed: file is absent from the clean checkout. |
| `./openspec.cmd validate bootstrap-openspec-baseline --strict` | Failed: file is absent from the clean checkout. |
| `./openspec.cmd validate --all --strict` | Failed: file is absent from the clean checkout. |
| `Get-Command openspec` | No globally installed OpenSpec command was found. |
| OpenSpec validated-item count | Not available because the executable is unavailable. |
| `git diff --check` | Passed; no whitespace errors. |
| `git check-ignore -v credentials.local.json` | Passed; `.gitignore` contains the ignore rule. |
| `git ls-files -- credentials.local.json` | Passed; no real local credential file is tracked. |
| Safe OpenSpec keyword scan | Seven OpenSpec artifact files matched credential-related terms; only filenames were recorded, and review found policy/specification material rather than secret values. |

The full suite ran as one offline process in the clean checkout. It completed
without a real `credentials.local.json`, live hardware, application network
calls, a Qt crash, or hung threads. Existing SSL deprecation warnings did not
fail the suite.

## Findings

### Critical

1. `openspec.cmd` is absent from the published checkout (repository root).
   The active change's design and project configuration require a usable local
   OpenSpec workflow, and this validation explicitly requires the wrapper for
   `list`, strict `validate`, and `archive`. It existed only as an untracked
   file in the original working tree, not in the validated commit. No global
   `openspec` command or checked-in package metadata provides an alternative.
   A new clone therefore cannot perform the documented OpenSpec workflow.
   This blocks archive and blocks merge. Required action: add and document a
   portable tracked launcher (and its reproducible dependency strategy) in a
   separate corrective change, then repeat clean-checkout strict validation.

### High

1. `openspec/changes/bootstrap-openspec-baseline/tasks.md` task 2.3 and the
   proposal claim the prior reverse-engineered specification is preserved as
   historical source material, but `specs/vcs-diagnostic-openspec.md` is not
   present or tracked at the validated revision. This removes the promised
   historical cross-check and leaves the checked/claimed baseline boundary
   unsupported. It blocks archive and merge. Required action: decide whether
   to restore the historical source material or revise the change artifacts
   through an approved corrective OpenSpec change, with evidence.

2. `tasks.md` tasks 1.1 and 3.1 are not evidenced because no OpenSpec
   executable is available in a clean checkout; neither strict validation of
   the change nor strict validation of all items could run. This blocks archive
   and merge. Required action: resolve the launcher issue and record successful
   clean-checkout validation before reconsidering completion.

## Verdict

**CHANGES REQUIRED.**

Archive is **not permitted**. The branch is **not ready for merge after a
future archive** until the Critical and High findings are resolved and this
validation is repeated from a clean checkout. No production code, tests, root
specs, proposal, design, or task list were changed in this session. No archive,
merge, pull request, or branch deletion was performed.
