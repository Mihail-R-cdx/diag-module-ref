# Corrective OpenSpec wrapper verification report

## Scope and finding addressed

Validation date: 2026-07-12 (Europe/Moscow).

The prior independent validation reported a Critical finding: a clean checkout
did not contain `openspec.cmd`, repository-local package metadata, or a usable
OpenSpec executable. The documented local workflow therefore depended on a
tool that happened to exist in the author's untracked working tree.

The root cause was that the original bootstrap recorded OpenSpec 1.6.0 as
available through a launcher, but did not track either that launcher or the
dependency metadata required to restore its executable.

This corrective implementation adds `openspec.cmd`, `package.json`, and
`package-lock.json`. `package.json` pins `@fission-ai/openspec` to `1.6.0` as
a development dependency. `npm ci` restores it reproducibly into
`node_modules`.

## Repository-local launcher

`openspec.cmd` determines its own directory with `%~dp0`, enters that directory
with `pushd`, and invokes only
`node_modules\\.bin\\openspec.cmd`. It calls that executable with `%*`, saves
`%ERRORLEVEL%`, restores the caller's directory, and returns the saved code.
It contains no credentials or absolute paths, does not modify global `PATH`,
and has no global-OpenSpec fallback. If the local executable is absent, it
prints `Install the pinned project dependencies with: npm ci` and exits with
code 1.

The change README documents the Windows sequence:

1. `npm ci`
2. `./openspec.cmd list`
3. `./openspec.cmd validate --all --strict`

It explicitly states that a global OpenSpec installation is unnecessary.

## Deterministic launcher checks

A temporary fake `node_modules\\.bin\\openspec.cmd` was used without being
committed. The root wrapper was invoked from a directory outside the repository
whose checkout path contains spaces.

| Check | Result |
| --- | --- |
| Argument forwarding | The fake executable received `validate --all --strict` unchanged. |
| Exit-code propagation | The fake executable returned 23; `openspec.cmd` returned 23. |
| Working directory and spaces | The wrapper found its local binary from outside the repository by using `%~dp0`; the checkout path contains spaces. |
| Missing dependency | With the local executable temporarily absent, the wrapper printed the documented `npm ci` guidance and returned 1. |

## Real OpenSpec workflow

Portable Node.js 20.19.0 was used only to perform validation because this host
does not expose `node`, `npm`, or `openspec` globally. It was not recorded in
the repository and no global OpenSpec installation was used. After `npm ci`,
the repository-local executable reported OpenSpec 1.6.0.

| Command | Result |
| --- | --- |
| `./openspec.cmd --help` | Passed, exit code 0. |
| `./openspec.cmd list` | Passed, exit code 0; active change: `bootstrap-openspec-baseline`. |
| `./openspec.cmd validate bootstrap-openspec-baseline --strict` | Passed, exit code 0. |
| `./openspec.cmd validate --all --strict` | Passed, exit code 0; 3 items passed and 0 failed: the active change plus `credential-source-isolation` and `repository-secret-hygiene`. |
| `python -m unittest discover -s tests -p "test_*.py"` | `python` was absent from `PATH`; the available Python 3.12 interpreter ran the equivalent command successfully: 61 tests passed in 0.887 s. |

## Clean-checkout reproduction

A separate detached worktree was created from a temporary pre-final commit
that contained the exact tracked launcher and dependency files. Its status was
empty before dependency restoration. `Get-Command openspec` found no global
command. In that worktree, `npm ci` installed 79 packages from the lockfile
with zero reported vulnerabilities; then `./openspec.cmd list` and
`./openspec.cmd validate --all --strict` both returned 0. The latter again
reported 3 passed and 0 failed. The worktree did not use `node_modules`, the
wrapper, or any other file from the original working tree.

## Git protection and scope

- `git diff --check` passed with no whitespace errors.
- `credentials.local.json` remains ignored by `.gitignore` and is not tracked.
- `node_modules/` is ignored, while `openspec.cmd` is not ignored and is
  tracked by this implementation.
- Only launcher, Node dependency metadata/lockfile, OpenSpec documentation,
  tasks, the verification report, and the necessary ignore rule were changed.
- No production code, application tests, root specs, archived credential
  change, archive operation, merge, pull request, or branch deletion was
  performed.

## Remaining finding and verdict

Critical finding for the missing repository-local OpenSpec wrapper is resolved.
The previously reported High finding for `specs/vcs-diagnostic-openspec.md`
remains open. A new independent validation is required.

The active change remains `bootstrap-openspec-baseline`; task 3.3 remains
unchecked. This implementation must not be archived or treated as an approval
of the full baseline.

RESOLVED FINDING: missing repository-local openspec.cmd
OPEN FINDING: missing specs/vcs-diagnostic-openspec.md
