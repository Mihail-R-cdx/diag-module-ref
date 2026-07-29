# Project Graph Runbook

## Purpose

Graphify is an optional local navigation helper. It can help a developer find
candidate files, symbols, and relationships in the current checkout, but it is
not architecture, validation evidence, archive evidence, CI state, merge
authority, or production correctness evidence.

Authority order remains:

```text
RULES.md
approved OpenSpec change artifacts
current root OpenSpec specs
current source and tests
branch diff
local Graphify output
```

Material conclusions must be verified in current source and tests.

## Tooling

Use the isolated pinned package:

```text
graphifyy==0.9.26
```

The package is not an application runtime dependency. Install it in a local tool
environment before using this helper, then verify the executable is on `PATH`:

```powershell
graphify --version
```

The repository-local wrapper verifies the actual executable version before it
starts generation.

## Standard Command

From the repository root:

```powershell
.\tools\refresh_project_graph.ps1
```

To build from an explicitly supplied local checkout:

```powershell
.\tools\refresh_project_graph.ps1 -SourceRoot <local-checkout>
```

The wrapper writes accepted output only under:

```text
.graphify-local/
```

The directory is ignored by Git and disposable. Delete and rebuild it whenever
the local graph is stale or unwanted:

```powershell
Remove-Item -Recurse -Force .\.graphify-local\
.\tools\refresh_project_graph.ps1
```

Graphify failure blocks only that local helper invocation. Ordinary
implementation, validation, archive, post-archive checks, and merge continue to
use authoritative project evidence without a Graphify command.

## Corpus And Security

The wrapper uses code-only generation, disables HTML visualization, requires no
external LLM API, and reads the repository `.graphifyignore`.

The local corpus boundary excludes credentials, local inventory, Excel files,
temporary worktrees, generated output, caches, logs, deployment-local data, and
agent/private state, including at least:

```text
.git/
.agents/
.codex/
.worktrees/
.graphify-local/
graphify-out/
node_modules/
virtual environments
__pycache__/
openspec/changes/archive/
credentials.local*.json
equipment_inventory.local.json
.env files
private keys and certificates
cookies
sessions
call records
logs
Excel files
generated/output/artifact directories
deployment-local data
temporary transfer/raw directories
```

Accepted output is scanned before the wrapper exits successfully. Output is
rejected when it contains secret-like values, excluded inventory, excluded
paths, HTML visualization, Windows drive or UNC checkout paths, or POSIX
absolute checkout paths. Secret findings are reported without printing detected
secret values.

## Confidence

When Graphify reports confidence categories, use them only as navigation
labels:

- `EXTRACTED`: static hint.
- `INFERRED`: hypothesis.
- `AMBIGUOUS`: not evidence.

If the schema omits confidence data, do not invent it. Open the source files and
verify the relationship directly.
