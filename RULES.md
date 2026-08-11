---
mode: agent
apply: apply
---

# Python Execution Rules for Agent Mode

## Git Repository

Use the repository selected for the current task. Preserve unrelated working-tree
changes, and use a separate clean worktree when the primary checkout is dirty.

If Git reports a repository-ownership error, follow the scoped
`safe.directory` fallback in the validation workflow below. It is not a required
prefix for ordinary Git commands.

### Equipment inventory runbook

For any task involving equipment inventory, the Excel importer, canonical
inventory snapshots, PDU-to-room resolution, or related-codec enrichment, agents
MUST read `docs/equipment-inventory-runbook.md` after this file and before
changing code, tests, specifications, or operational data. Current root OpenSpec
specifications remain normative if the runbook and a specification conflict.

### Graphify local project graph

Graphify is optional and is only a local navigation helper. It may help locate
candidate files, symbols, and relationships, but it is not OpenSpec authority,
validation evidence, archive evidence, merge authority, a CI requirement, or
production correctness evidence.

Generated Graphify output is disposable local state. The canonical local output
directory is `.graphify-local/`; generated output is ignored by Git, must not be
committed, and may be deleted and rebuilt at any time. Missing, failed, stale,
or absent local graph output blocks nothing in ordinary architecture,
implementation, validation, archive, post-archive checks, or merge.

Agents MUST verify all material conclusions in current source and tests.
Graph confidence remains only a navigation hint: `EXTRACTED` is a static hint,
`INFERRED` is a hypothesis, and `AMBIGUOUS` is not evidence.

Ordinary tasks MUST NOT silently run Graphify. Ordinary implementation,
validation, archive, and merge require no Graphify command, no graph refresh
checkpoint, no graph-only branch or commit, no Graphify evidence JSON, no
validation-report-only or evidence-only commit, no final graph review, no
stale-graph exception, and no `A -> S -> E -> G` publication workflow.

## Python Interpreter

Use the repository-supported Python interpreter. An explicit interpreter path
MAY be supplied by the execution environment when required.

```yaml
python_interpreter: "<environment-provided-python>"
working_directory: "."
```

## Files and Escaping

Mandatory rule: when working with files whose paths may include Cyrillic or special characters, prefer Python raw strings (`r''`) to avoid escaping issues.

Example:

```python
# Correct
with open(r'gui\screens\codec_screen.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Incorrect
with open('gui\screens\codec_screen.py', 'r', encoding='utf-8') as f:
    content = f.read()
```

Tip: if file modification through a Python helper script is needed, create a separate script and run it through the Python interpreter.

## GUI Launch Rules

Mandatory rule: launch the local GUI application as a detached process outside the sandbox. Do not run it as a blocking foreground command inside the sandbox, because timeout handling can terminate the process and close the window.

Recommended command:

```powershell
Start-Process -FilePath '<environment-provided-python>' -ArgumentList '.\main.py' -WorkingDirectory '.'
```

Notes:
- use an escalated run when launching the GUI from the agent
- prefer `Start-Process`, not direct blocking `python .\main.py`
- use this rule for manual testing of the local application window

## Validation and repository workflow

`RULES.md` is the highest authority for this repository workflow. Approved
OpenSpec artifacts are the authority for implementation. Checks and readiness
statuses are gates within workflow phases: a gate is not a separate workflow
phase and does not by itself require a new Codex session.

A Codex session SHOULD complete the entire workflow phase assigned to it unless
it encounters a real blocking finding, a remote-state change, a failed mandatory
check, or an explicit user stop condition. Checks, evidence synchronization,
readiness markers, and bookkeeping belonging to that phase SHOULD be completed
in that same session rather than delegated to new sessions.

The workflow has four phases:

1. **OpenSpec / Design.** Create the OpenSpec change and its proposal, design,
   specs, and tasks; perform architecture review; resolve architecture findings;
   and obtain the final architectural `APPROVE`. `READY FOR REVIEW`, repeated
   artifact reading, and bookkeeping are gates or work within this phase, not
   separate phases.
2. **Implementation.** Implement the approved architecture; add regression
   coverage; run focused and required full tests and strict OpenSpec validation;
   synchronize `tasks.md` and implementation evidence; run `git diff --check`
   and `git diff --cached --check` as Git checks;
   create a focused implementation commit; and push the feature branch.
   Integration proof, evidence synchronization, readiness markers, and reruns
   of implementation checks are work in this phase, not mandatory new sessions.
   A real blocker stops implementation and is reported. An implementation
   session MUST NOT issue the independent final `APPROVE`.
3. **Independent validation.** A mandatory separation-of-duty handoff that
   validates the published implementation without fixing its own findings. It
   includes all required tests, strict OpenSpec validation, implementation review
   against the approved architecture, Git checks, and, when applicable, the
   disposable archive-applicability check described below.
4. **Archive + completion.** After a permitting independent verdict, archive;
   review the archive/root-spec diff; run strict all-artifact validation, full
   required offline tests, `git diff --check`, and `git diff --cached --check`;
   make and push a dedicated archive commit; confirm the current remote archive
   HEAD; and merge only if the user explicitly authorizes it. Archive,
   post-archive validation, archive commit, `READY FOR MERGE`, and merge are
   work or gates in this one completion phase, not mandatory separate sessions.

Repository readiness statuses, including `APPROVE`, `CHANGES REQUIRED`,
`READY FOR REVIEW`, `READY FOR INDEPENDENT REVALIDATION`, `READY FOR ARCHIVE`,
and `READY FOR MERGE`, are gate/state markers, not mandatory workflow phases or
mandatory new Codex sessions. Passing through a status does not by itself
require a new commit, branch, validation artifact, or Codex session.

### Independent validation checkout

Independent validation MUST run in a separate clean detached worktree created
from the current published remote branch revision. The validator MUST record the
remote branch SHA before starting and verify that the validation worktree HEAD
matches that SHA. A dirty primary worktree MUST NOT be used as validation
evidence or as the source of validation commits.

```powershell
git fetch origin
$branch = "agent/example-change" # example; use the actual branch
$remoteRef = "origin/$branch"
$sha = git rev-parse $remoteRef
git worktree add --detach ".worktrees/validation-$($sha.Substring(0, 8))" $remoteRef
```

The worktree MUST be created from `origin/<branch>`, not a local branch. The
validator MUST compare its local SHA with the remote SHA and stop or explicitly
reorient to a newer published SHA after reviewing commits if they differ.

### Git safe.directory

When Git rejects a validation worktree because of repository ownership, the
agent MAY register only the exact affected repository or worktree path as a
safe directory. The wildcard safe-directory setting MUST NOT be used.

```powershell
git config --global --add safe.directory "C:/exact/path/to/worktree"
git -c safe.directory="C:/exact/path/to/worktree" status
```

This is a fallback for an ownership problem, not a mandatory prefix for every
Git command. `safe.directory="*"` MUST NOT be configured.

### Авторизация GitHub CLI

Перед использованием `gh` при необходимости проверить авторизацию:

```powershell
gh auth status
```

При первоначальном подключении:

```powershell
gh auth login
```

Важно: в изолированной среде `gh` может не иметь доступа к пользовательскому Windows keyring и поэтому не видеть уже сохранённую авторизацию.

Если проверка `gh auth status` в изолированной среде показывает отсутствие авторизации, это не обязательно означает, что пользователь не авторизован в GitHub CLI.

В таком случае повторная проверка должна выполняться в среде с доступом к пользовательскому Windows-профилю и его credential storage.

Не следует предлагать повторный `gh auth login`, пока наличие действующей авторизации не проверено с доступом к пользовательскому профилю.




### OpenSpec execution

All repository OpenSpec operations MUST use the tracked repository-local
`openspec.cmd` wrapper. Agents MUST NOT rely on a globally installed OpenSpec
executable for validation or archive evidence.

```powershell
.\openspec.cmd --help
.\openspec.cmd list
.\openspec.cmd validate <change-name> --strict
.\openspec.cmd validate --all --strict
```

The wrapper uses the pinned repository-local dependency. `npm ci` restores it;
the OpenSpec version comes from `package.json` and its lock file. Agents MUST
NOT use `npx` with an `@latest` version. An archive requires explicit
`APPROVE` first.

For `./openspec.cmd archive <change> --yes`, the tracked wrapper performs a
repository-local compatibility check around the unchanged pinned upstream
archive command. It refuses to begin if `openspec/specs/` already has tracked,
staged, or untracked work; after a successful upstream archive it normalizes
only archive-generated root-spec terminal blank lines and fails closed on
staged root output. The compatibility layer never changes the Git index or
installed dependencies. Post-archive `git diff --check` remains mandatory;
the wrapper also runs it (and its cached counterpart) before reporting archive
success.

### Node environment

Validation MUST use the repository-supported Node version. The current
baseline is Node `20.19.0`; package metadata permits `20.19.0` or later. Node
MAY come from the system `PATH` or a portable installation supplied by the
environment. Rules and scripts MUST NOT contain a user-specific absolute Node
path.

```powershell
$nodeHome = $env:DIAG_NODE_HOME
if (-not $nodeHome -or -not (Test-Path "$nodeHome\node.exe")) {
    throw "Set DIAG_NODE_HOME to the portable Node directory before OpenSpec validation."
}
$env:Path = "$nodeHome;$env:Path"
node --version
npm --version
npm ci
```

The portable Node directory MUST be added to `PATH` before `npm ci` so
post-install scripts can locate `node`. A portable Node installation and
`node_modules` MUST NOT be committed.

For a sibling clean worktree, set `DIAG_NODE_HOME` in the calling shell to the
portable Node directory owned by the primary checkout before invoking the
worktree's local wrapper. The value is process-local; do not persist it in the
system PATH and do not place a user-specific absolute path in tracked rules or
scripts. Run the version commands above before any `npm ci` or OpenSpec command
and treat a missing executable or an unsupported version as an environment
failure, not a validation result.

### Text encoding

Repository Markdown and text artifacts MUST be read and written as UTF-8.
PowerShell commands reading historical or Russian-language Markdown SHOULD
specify `-Encoding UTF8` explicitly.

```powershell
Get-Content -Path .\specs\example.md -Encoding UTF8
Set-Content -Path .\specs\example.md -Encoding UTF8 -Value $content
```

Incorrectly displayed Cyrillic MUST NOT be treated as corruption until the file
has been read again explicitly as UTF-8.

### Validation evidence

Independent validation is report-only by default. It MUST NOT create a commit
solely for a validation report, test counts, evidence publication, `READY FOR
ARCHIVE`, or recording that validation occurred. In particular, successful
independent validation MUST NOT change the feature HEAD merely to publish a
report.

When an independent validation report is produced, it MUST record:

- validated remote branch and full commit SHA;
- commit subject, clean worktree evidence, and local/remote SHA comparison;
- relevant tool versions and dependency-restoration command and result;
- exact OpenSpec and test commands, test counts, and results;
- repository-protection checks and findings ordered by severity;
- final verdict; archive/merge permission; and whether code or tests changed.

An older report is an assertion, not evidence. The validator MUST rerun required
commands and MUST NOT copy prior test counts. A tracked validation artifact is
permitted only when the user explicitly requests it and is not part of the
default workflow.

### Validation verdicts

Allowed final verdicts are `APPROVE`, `APPROVE WITH NON-BLOCKING NOTES`, and
`CHANGES REQUIRED`. `APPROVE` requires no Critical, High, or Medium findings
and passing mandatory tests and strict validation. The non-blocking verdict
permits only Low findings. `CHANGES REQUIRED` applies to a Critical, High, or
Medium finding, a failed required check, or insufficient task evidence.

Archive is permitted only after `APPROVE` or `APPROVE WITH NON-BLOCKING NOTES`.
Validation sessions MUST NOT fix their own findings; implementation and
validation MUST be separate sessions.

When a change modifies existing root specs, including `MODIFIED Requirements`,
`RENAMED Requirements`, `REMOVED Requirements`, or an equivalent root-spec
change, independent validation MUST perform the disposable archive-applicability
check. This check is inside the independent-validation phase, not a separate
workflow phase or mandatory new session.

### Implementation sessions

Implementation sessions MAY modify code, tests, and change artifacts needed to
resolve approved findings. They MUST preserve unrelated changes, keep a focused
scope, add regression coverage, run targeted and full tests, run strict
OpenSpec validation, update implementation evidence, and commit and push before
requesting new independent validation. They MUST NOT issue the final `APPROVE`.

### Archive + completion

An OpenSpec change MAY be archived only after a published independent verdict
permits it. Archive MUST be followed by strict validation of all OpenSpec
artifacts, the full offline test suite, `git diff --check`,
`git diff --cached --check`, review of the archive and root-spec diff, and a
dedicated archive commit and push.

After the archive checks pass and the dedicated archive commit is pushed, the
same session MAY merge the feature branch only with explicit user authorization.
Before merging, it MUST reconfirm that the remote feature-branch HEAD still
matches the reviewed archive commit and that `master` is current; if remote
state changed, it MUST review the new commits first. Force-push MUST NOT be
used. A separate archived-branch review or separate merge session is not
required unless the user or repository policy explicitly requests one.

### Temporary artifacts

Validation worktrees, fake wrapper binaries, temporary Node installations,
`node_modules`, generated logs, and test artifacts MUST NOT be committed.
Temporary worktrees SHOULD be removed after validation or implementation.
