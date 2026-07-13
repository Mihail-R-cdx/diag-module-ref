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

## Historical baseline restoration

Validation date: 2026-07-13 (Europe/Moscow).

### Finding and provenance

The outstanding High finding was that the published repository did not contain
the historical `specs/vcs-diagnostic-openspec.md` document claimed by the
bootstrap proposal, design, and task 2.3. The document was located in the
available Git object history at the same path in source commit
`1b5183b3b1eb57a7529b36f445629e0fa53e9971` (`Publish sanitized diagnostic
source code`). Its source blob is `15fcc7e70de49bcc5fa0be14360ccca0e36b6e16`.

The search covered all refs, path/name history, object names, likely filename
variants, reflog/stash references, and unreachable objects. The source commit
was confirmed with `git ls-tree`; the file is a 551-line reverse-engineered
behavioral specification for the existing diagnostic application. Its sections
cover metadata and scope, inputs and outputs, UI and worker behavior,
device-specific diagnostics and controls, error handling, dependencies, and
the covered source-file inventory.

The tracked file has been restored at `specs/vcs-diagnostic-openspec.md` from
that source revision. The historical body is restored without semantic
changes. A short leading status note and normalization of 14 legacy trailing
whitespace errors are the only intentional technical changes:
it records the source commit and explicitly labels the document historical,
migration input, reference-only, and non-authoritative after root specs were
introduced. It also directs current requirements to `openspec/specs/` and
gives those specifications precedence in the event of a difference.

This treatment matches the bootstrap artifacts: proposal and design describe
the document as preserved historical source material and a cross-check, while
the OpenSpec capability specifications remain the normative baseline. It does
not claim that every production behavior was formalized, and it does not copy
later credential-isolation requirements into the historical snapshot.

### Restoration checks

- The file exists at the required path and is non-empty.
- Deterministic checks found the required `historical migration reference`
  marker and the `openspec/specs/` reference. No `TODO` or `TBD` placeholder
  was found.
- The targeted sensitive-field scan found only documented field/protocol
  terminology in the restored historical material; no credential values,
  tokens, cookies, or local credential content were introduced or reported.
- No separate Markdown-artifact test was added because the repository has no
  existing repository-artifact test harness; the deterministic checks above
  provide the requested coverage without adding a framework.

### Workflow and offline validation

The repository-local wrapper was run after `npm ci` using the existing portable
Node.js runtime. It resolved `@fission-ai/openspec` version `1.6.0`; no global
OpenSpec installation was used.

| Command | Result |
| --- | --- |
| `./openspec.cmd --help` | Passed. |
| `./openspec.cmd list` | Passed; active `bootstrap-openspec-baseline` reported as 8/9 tasks. The archived credential change was not returned as active. |
| `./openspec.cmd validate bootstrap-openspec-baseline --strict` | Passed. |
| `./openspec.cmd validate --all --strict` | Passed; 3 passed, 0 failed. |
| `python -m unittest discover -s tests -p "test_*.py"` | `python` is not on `PATH` on this host. The equivalent command with the available Python 3.12 interpreter passed 61 tests in 0.733 s. |

The offline suite made no live-hardware or application network calls, used no
real `credentials.local.json`, and completed without a Qt crash or hung
threads.

### Git protection and scope

- `git diff --check` passed with no whitespace errors.
- `git check-ignore -v credentials.local.json` confirmed the ignore rule; `git
  ls-files -- credentials.local.json` returned no tracked credential file.
- The restoration is limited to the historical reference, its task provenance,
  and this verification record. No production code, GUI, handlers, workers,
  root specs, archived credential change, wrapper, dependency version, archive,
  merge, pull request, or branch deletion was changed or performed.

The missing historical baseline specification finding is resolved by the
tracked `specs/vcs-diagnostic-openspec.md` reference document. A new independent
validation of `bootstrap-openspec-baseline` is required before archive.

## Independent final validation after blocker remediation

Validation date: 2026-07-13 (Europe/Moscow).

The independently validated published implementation is
`68b8ac788a153ce49b5d058ad2560810d8b7252a` — `Restore historical VCS
diagnostic specification`. After `git fetch origin`, both
`origin/agent/bootstrap-openspec-baseline` and the separate detached clean
checkout resolved to that SHA. `git status --short` was empty before this
report update; validation therefore exercised the published implementation,
not an uncommitted local diff.

### Reproduced setup and repository-local wrapper

- `package.json` and `package-lock.json` pin `@fission-ai/openspec` to
  `1.6.0`; `npm ci` completed successfully in the clean checkout, restoring
  79 packages with 0 reported vulnerabilities. The installed package metadata
  reported version `1.6.0`.
- A portable Node.js `20.19.0` runtime was placed on `PATH` only for this
  validation run. No global OpenSpec executable was used; every OpenSpec
  invocation used the repository-local `openspec.cmd` and its local
  `node_modules\\.bin\\openspec.cmd`.
- Static inspection confirms that `openspec.cmd` derives its repository
  location from `%~dp0`, uses `pushd`/`popd`, forwards `%*`, preserves the
  child exit code, and provides a clear nonzero missing-dependency error with
  no machine-specific path or global fallback.
- From a temporary directory outside the checkout, the absolute-path wrapper
  invocation `list` succeeded with exit code 0, reported only active
  `bootstrap-openspec-baseline` at 8/9 tasks, and returned the caller to its
  original directory. The checkout path contains spaces.
- A controlled, untracked fake local executable received
  `validate --all --strict` unchanged and returned 23; the wrapper returned
  23 and preserved the caller directory. The fake file was removed and is
  ignored by Git. With the executable absent, the wrapper emitted its `npm ci`
  guidance and returned 1.

### Historical document, structure, and validation evidence

- Source commit `1b5183b3b1eb57a7529b36f445629e0fa53e9971` exists and contains
  `specs/vcs-diagnostic-openspec.md` as blob
  `15fcc7e70de49bcc5fa0be14360ccca0e36b6e16`. The restored body has the same
  line count and matches that source after only trailing-whitespace
  normalization: the source had 13 trailing-whitespace lines and the restored
  file has none. The sole added content is the 13-line historical,
  non-authoritative migration-status notice that directs current requirements
  to `openspec/specs/`.
- The historical-document sensitive-field scan produced only generic field
  names and protocol/error descriptions. Manual review found no credential,
  token, cookie, or private-key value.
- `openspec.cmd --help` and `openspec.cmd list` passed. The archived
  `externalize-device-credentials` change remains under
  `openspec/changes/archive/` and is not listed as active; the two root specs
  remain available and do not conflict with the historical reference.
- `openspec.cmd validate bootstrap-openspec-baseline --strict` passed with
  exit code 0. `openspec.cmd validate --all --strict` passed with exit code 0:
  3 passed, 0 failed (`bootstrap-openspec-baseline`,
  `credential-source-isolation`, and `repository-secret-hygiene`).
- The complete offline suite, run as one process with the available Python
  3.12 interpreter, passed: 61 tests in 0.690 s. It used no real local
  credential file or live hardware; no Qt crash or hung thread occurred.
- `git diff --check` passed. `credentials.local.json` is ignored and
  untracked; `node_modules/` is ignored; `openspec.cmd`, package metadata,
  lockfile, and the historical document are tracked. No temporary validation
  artifact is tracked.

### Task reconciliation, findings, and verdict

The completed bootstrap tasks are supported by the inspected OpenSpec
configuration and artifacts, repository-local wrapper behavior, pinned clean
checkout reproduction, source provenance comparison, strict validation,
offline-suite result, root-spec/archive review, historical-document migration
boundary, and Git-protection checks above. Task 3.3 remains unchecked as
required: no archive was performed.

Findings: none at Critical, High, Medium, or Low severity.

Verdict: **APPROVE**. Archive of `bootstrap-openspec-baseline` is permitted.
The branch is ready to merge only after that archive is performed and reviewed.
This validation did not archive the change, merge a branch, create a pull
request, or delete a branch.
