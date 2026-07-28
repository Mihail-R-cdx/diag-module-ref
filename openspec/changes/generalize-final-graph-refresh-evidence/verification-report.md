# Independent Validation Report: generalize-final-graph-refresh-evidence

Validated remote branch: `agent/generalize-final-graph-refresh-evidence`
Validated implementation commit: `d5219f8a1e33ff032eec809881d18d2145c64801`
Commit subject: `Generalize final Graphify refresh evidence`
Base branch: `master`
Base commit: `8d75d7177772967e6aa99508033fcb677157e20d`
PR: `#17`
PR state: `open`
PR draft: `true`
Validation worktree: `.worktrees/validation-generalize-final-graph-refresh-evidence-d5219f8a`

## Remote and Worktree Evidence

- `git fetch origin`: exit code 0.
- `git rev-parse origin/agent/generalize-final-graph-refresh-evidence`: `d5219f8a1e33ff032eec809881d18d2145c64801`.
- `git rev-parse origin/master`: `8d75d7177772967e6aa99508033fcb677157e20d`.
- Local validation worktree HEAD: `d5219f8a1e33ff032eec809881d18d2145c64801`.
- Local HEAD equals remote implementation HEAD: yes.
- Detached validation worktree: yes; `git branch --show-current` returned empty.
- Clean worktree before validation: yes.
- Clean tracked worktree after dependency restoration and validation commands, before this report: yes.

## RULES and Graphify Baseline

`RULES.md` was read before validation work. `graphify-out/baseline.json` was read afterward.

Baseline facts:

- `baseline_stage`: `final`
- `indexed_source_commit`: `2ad5c67b5413627cfc15fb327c0e6f856cf9b264`
- `indexed_source_ref`: `origin/agent/frozen-project-graph-baseline-final-gate-repair`
- `graphify_version`: `0.9.26`

Graphify was treated only as a frozen navigation baseline. No `graphify-out/` refresh was performed.

## Scope Review

Branch diff from `origin/master...HEAD` changes exactly these paths:

- `docs/project-graph-runbook.md`
- `openspec/changes/generalize-final-graph-refresh-evidence/.openspec.yaml`
- `openspec/changes/generalize-final-graph-refresh-evidence/design.md`
- `openspec/changes/generalize-final-graph-refresh-evidence/proposal.md`
- `openspec/changes/generalize-final-graph-refresh-evidence/specs/project-graph-refresh-workflow/spec.md`
- `openspec/changes/generalize-final-graph-refresh-evidence/tasks.md`
- `openspec/specs/project-graph-refresh-workflow/spec.md`
- `tests/test_project_graph_refresh_workflow.py`
- `tools/refresh_project_graph.ps1`

Diff stat: 9 files changed, 1851 insertions, 44 deletions.

Implementation delta after approved architecture HEAD `3770e08209335d91235be445b818a549ea0dc912` changes:

- `docs/project-graph-runbook.md`
- `openspec/changes/generalize-final-graph-refresh-evidence/tasks.md`
- `openspec/specs/project-graph-refresh-workflow/spec.md`
- `tests/test_project_graph_refresh_workflow.py`
- `tools/refresh_project_graph.ps1`

No changes were found under `graphify-out/`, `openspec/validation/`, `openspec/changes/archive/`, `core/`, `gui/`, credentials, inventory data, unrelated specs, or unrelated tests.

## Architecture and Contract Assessment

The implementation adds ordinary final Graphify refresh handling for `A -> optional M -> V -> R -> E -> G`, a deterministic ordinary evidence path, exact JSON field validation, exact metadata-block parsing, V-R and R-E path-delta checks, SourceRef/HEAD binding, historical frozen-baseline compatibility, and existing Graphify protection checks.

However, validation found blocking conformance gaps in the report-policy enforcement and structured failure coverage. The wrapper does not fully enforce the approved human-readable `verification-report.md` evidence contract, and the focused tests claim several required negative paths that are not actually present.

## Environment

- Python command: `C:\Users\Mih\AppData\Local\Programs\Python\Python312\python.exe --version`
- Python version: `Python 3.12.9`
- Node source: portable local Node discovered at `C:\Users\Mih\AppData\Local\Temp\diag-node-portable\node-v20.19.0-win-x64`
- Node command: process-local `$env:Path = "$nodeHome;$env:Path"; node --version`
- Node version: `v20.19.0`
- npm version: `10.8.2`
- Dependency restoration command: `npm ci`
- Dependency restoration exit code: 0
- Packages: added 79 packages; audited 80 packages
- Vulnerabilities: 0
- Funding notice: 25 packages looking for funding
- Global `openspec` used: no
- `npx openspec` used: no

## Mandatory Commands

Command:
`& 'C:\Users\Mih\AppData\Local\Programs\Python\Python312\python.exe' -m unittest discover -s tests -p "test_project_graph_refresh_workflow.py"`

Exit code: 0
Passed: 6 unittest methods
Failed: 0
Skipped: 0
Result: OK. The 6 methods include subtests for 16 JSON schema/path cases, 20 metadata cases, and 4 lineage/path cases.

Command:
`& 'C:\Users\Mih\AppData\Local\Programs\Python\Python312\python.exe' -m unittest discover -s tests -p "test_*.py"`

Exit code: 0
Passed: 480
Failed: 0
Skipped: 0
Result: OK.

Command:
`.\openspec.cmd validate generalize-final-graph-refresh-evidence --strict`

Exit code: 0
Passed: 1 change validation
Failed: 0
Skipped: 0
Result: `Change 'generalize-final-graph-refresh-evidence' is valid`.

Command:
`.\openspec.cmd validate --all --strict`

Exit code: 0
Passed: 12
Failed: 0
Skipped: 0
Result: `Totals: 12 passed, 0 failed (12 items)`.

Command:
`git diff --check`

Exit code: 0
Passed: yes
Failed: 0
Skipped: 0
Result: no whitespace errors.

Command:
`git diff --check origin/master...HEAD`

Exit code: 0
Passed: yes
Failed: 0
Skipped: 0
Result: no whitespace errors.

Command:
`git status --short`

Exit code: 0
Passed: yes for tracked-file cleanliness before this report
Failed: 0
Skipped: 0
Result: clean tracked worktree before report creation.

## Targeted Adversarial Checks

The focused suite exercised wrapper behavior through temporary Git repositories and a fake Graphify executable, not by mocking the wrapper internals.

Confirmed by focused tests:

- JSON unknown field: rejected by `test_evidence_json_schema_and_path_fail_closed`.
- JSON with `indexed_source_commit`: rejected by `test_evidence_json_schema_and_path_fail_closed`.
- Metadata duplicate block: rejected by `test_metadata_block_failures_are_rejected_without_substring_fallback`.
- Metadata uppercase SHA in JSON commit fields: rejected by `test_evidence_json_schema_and_path_fail_closed`.
- Extra file in `V..R`: rejected by `test_lineage_report_and_working_byte_failures_are_rejected`.
- Extra file in `R..E`: rejected by `test_lineage_report_and_working_byte_failures_are_rejected`.
- Ordinary change using historical evidence path: rejected by `test_lineage_report_and_working_byte_failures_are_rejected`.
- Failure output redaction: `assertRejected` verifies rejected fixture output does not include the temporary root path and does not publish `graphify-out/baseline.json`.

Not sufficiently covered:

- malformed JSON, untracked/ignored evidence, untracked/ignored report, report commit mismatch, source-ref mismatch, dirty source worktree, invalid archive state, and several graph protection regressions are claimed in tasks but not present as focused negative cases.

## Findings

### HIGH

File: `tools/refresh_project_graph.ps1:450`

Contract: `openspec/changes/generalize-final-graph-refresh-evidence/specs/project-graph-refresh-workflow/spec.md:116` requires the human-readable report to satisfy full `RULES.md` independent-validation evidence, and lines 131-135 require incomplete reports to fail before Graphify generation. `design.md:172` also requires the report to record commit subject, clean worktree evidence, Python/Node/npm/Graphify versions, dependency restoration, exact commands/counts/outcomes, repository-protection checks, findings, verdict, permissions, and validator code/test mutation facts.

Evidence: `Assert-ValidationReportMetadata` validates the metadata block and checks a short contradiction list, but it never verifies that the committed report contains the required human-readable evidence facts. The accepted positive fixture in `tests/test_project_graph_refresh_workflow.py:295` contains only a minimal title, branch/SHA/verdict/permission lines, and the metadata block; it omits Node/npm/Graphify versions, dependency restoration, exact command counts, clean worktree before/after evidence, repository-protection checks, and severity-ordered findings.

Impact: A report-only `R` commit with an exact approval metadata block but without the complete independent validation evidence required by `RULES.md` can authorize final Graphify refresh. That weakens the approved evidence boundary and can allow `E`/`G` to be created from insufficient validation evidence.

Required fix: Extend report validation to fail closed when required human-readable evidence sections/facts are absent or encode those facts in a closed machine-readable report schema that the wrapper validates. Add negative tests proving an incomplete report is rejected.

### MEDIUM

File: `tests/test_project_graph_refresh_workflow.py:454`

Contract: `openspec/changes/generalize-final-graph-refresh-evidence/tasks.md:44` through `tasks.md:53` mark required negative coverage as complete for malformed JSON, wrong/missing/untracked/ignored/modified report and JSON paths, report commit mismatch, invalid archive state, source binding, dirty worktree, renewed validation, graph protections, and related fail-closed cases.

Evidence: The focused negative cases at `tests/test_project_graph_refresh_workflow.py:454` through `tests/test_project_graph_refresh_workflow.py:525` cover 16 schema/path cases, 20 metadata cases, and 4 lineage/path cases, but do not include explicit cases for malformed JSON, untracked evidence, ignored evidence, untracked/ignored report, report commit mismatch, missing report, source-ref mismatch, dirty worktree, invalid archive state, or no-partial-publish graph protection regressions.

Impact: Required safety behavior can regress while the focused suite remains green. This is especially risky because the wrapper is a gate for repository validation and final graph publication.

Required fix: Add focused temporary-Git-repo tests for the missing negative cases and keep tasks unchecked until the cases actually exist.

### MEDIUM

File: `tools/refresh_project_graph.ps1:691`

Contract: `openspec/changes/generalize-final-graph-refresh-evidence/specs/project-graph-refresh-workflow/spec.md:231` requires rejected final Graphify inputs to identify the failed contract category without leaking sensitive data or repository contents.

Evidence: `Assert-Json` catches JSON parsing failures and exits with the untyped message `Invalid JSON.` instead of a contract category such as `[EVIDENCE_SCHEMA]`, `[EVIDENCE_BYTES]`, or `[GRAPH_INTEGRITY]`. The focused tests do not include malformed JSON despite `tasks.md:44` claiming malformed JSON coverage.

Impact: Malformed ordinary evidence does fail closed, but the failure is not structured by contract category, making automated diagnosis and evidence review weaker.

Required fix: Pass a category/subject into JSON parsing for evidence and graph artifacts, emit typed failures, and add malformed JSON tests that assert the category and redaction behavior.

## Verdict

Final verdict: `CHANGES REQUIRED`

Archive permitted: no
Merge permitted: no
Production code changed by validator: no
Tests changed by validator: no
Specs changed by validator: no
Graphify-out changed: no
Post-archive JSON created: no
Archive performed: no
PR undrafted: no
Merge performed: no
Force-push used: no
Global openspec used: no
Npx openspec used: no

No `BEGIN VALIDATION METADATA` authority block is published in this report because this validation did not approve the change.
