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

### Independent validation checkout

Independent validation MUST run in a separate clean detached worktree created
from the published remote branch revision. The validator MUST record the remote
branch SHA before starting and verify that the validation worktree HEAD matches
that SHA. A dirty primary worktree MUST NOT be used as validation evidence or
as the source of validation commits.

```powershell
git fetch origin
$branch = "agent/example-change" # example; use the actual branch
$remoteRef = "origin/$branch"
$sha = git rev-parse $remoteRef
git worktree add --detach ".worktrees/validation-$($sha.Substring(0, 8))" $remoteRef
```

The worktree MUST be created from `origin/<branch>`, not a local branch.
Validation commits MAY be created from that isolated worktree.

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

Every independent validation report MUST record:

- validated remote branch and full commit SHA;
- commit subject, clean worktree evidence, and local/remote SHA comparison;
- relevant tool versions and dependency-restoration command and result;
- exact OpenSpec and test commands, test counts, and results;
- repository-protection checks and findings ordered by severity;
- final verdict; archive/merge permission; and whether code or tests changed.

An older report is an assertion, not evidence. The validator MUST rerun required
commands and MUST NOT copy prior test counts. If SHAs differ, validation MUST
stop or explicitly reorient to the newer published SHA after reviewing commits.

### Validation verdicts

Allowed final verdicts are `APPROVE`, `APPROVE WITH NON-BLOCKING NOTES`, and
`CHANGES REQUIRED`. `APPROVE` requires no Critical, High, or Medium findings
and passing mandatory tests and strict validation. The non-blocking verdict
permits only Low findings. `CHANGES REQUIRED` applies to a Critical, High, or
Medium finding, a failed required check, or insufficient task evidence.

Archive is permitted only after `APPROVE` or `APPROVE WITH NON-BLOCKING NOTES`.
Validation sessions MUST NOT fix their own findings; implementation and
validation MUST be separate sessions.

### Validation commits

A validation commit MUST contain only validation evidence, normally the
change-specific `verification-report.md`. Production code, tests, specs,
proposal, design, and tasks MUST NOT change during independent validation.

The commit MUST originate in a clean isolated worktree. Before committing, run
`git status`, `git diff`, and `git diff --check`. After pushing, compare the
local SHA with the remote branch SHA. Force-push MUST NOT be used. If a
post-push fetch times out, confirmed SHA equality MUST NOT be claimed without
other evidence.

### Implementation sessions

Implementation sessions MAY modify code, tests, and change artifacts needed to
resolve approved findings. They MUST preserve unrelated changes, keep a focused
scope, add regression coverage, run targeted and full tests, run strict
OpenSpec validation, update implementation evidence, and commit and push before
requesting new independent validation. They MUST NOT issue the final `APPROVE`.

### Archive sessions

An OpenSpec change MAY be archived only after a published independent verdict
permits it. Archive MUST be followed by strict validation of all OpenSpec
artifacts, the full offline test suite, `git diff --check`, review of the
archive and root-spec diff, and a dedicated archive commit and push.

After the archive checks pass and the dedicated archive commit is pushed, the
same session MAY merge the feature branch. A separate archived-branch review or
separate merge session is NOT required unless the user or repository policy
explicitly requests one. Before merging, the session MUST confirm that the
remote feature-branch HEAD still matches the reviewed archive commit.

### Temporary artifacts

Validation worktrees, fake wrapper binaries, temporary Node installations,
`node_modules`, generated logs, and test artifacts MUST NOT be committed.
Temporary worktrees SHOULD be removed after validation or implementation.
