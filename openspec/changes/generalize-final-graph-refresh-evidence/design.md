# Design: Generalize final Graphify refresh evidence

## Context

The current final Graphify gate was designed for the one-time
`frozen-project-graph-baseline` workflow. It accepts only the historical evidence
path, historical change name, and an evidence-only delta. Those rules are valid
for that published baseline but cannot support later archived changes.

PR #16 exposed two additional constraints:

- an older feature must incorporate the repaired Graphify workflow and then be
  independently revalidated on its new published remote HEAD;
- renewed validation must still publish the complete `verification-report.md`
  required by `RULES.md` before the compact Graphify gate JSON is committed.

## Goals

1. Support strict final Graphify refresh checkpoints for ordinary archived changes.
2. Preserve the historical frozen-baseline gate as an explicit special case.
3. Keep complete independent validation evidence and deterministic graph lineage.
4. Avoid self-referential commit metadata.
5. Keep generated artifact, encoding, hash, sensitive-data, ghost-node, topology,
   and graph-only commit protections unchanged.

## Non-goals

- Do not refresh `graphify-out/` as part of this change.
- Do not weaken `RULES.md` validation evidence requirements.
- Do not introduce a general process-only allowlist.
- Do not allow arbitrary evidence or verification-report paths.
- Do not infer validation from PR text or commit messages.

## Normative ordinary-change workflow

The approved ordering is:

```text
A = archive commit for the ordinary change
M = optional merge commit incorporating an approved Graphify workflow repair
V = renewed independently validated source commit after A and any required M
R = dedicated validation-report commit
E = dedicated post-archive Graphify-evidence commit
G = graph-only commit
```

For an older blocked branch such as PR #16, the infrastructure repair MUST first
be merged to `master`, incorporated into the feature branch, and followed by
renewed independent validation. The resulting published remote commit is `V`.
Older validation remains historical evidence but cannot authorize the new source.

No repository changes are allowed after `R` except the deterministic JSON created
by `E`. There is no process-only allowlist in this version.

## Deterministic paths

For ordinary change `<change-name>`:

```text
verification report:
openspec/changes/archive/<archive-directory>/verification-report.md

Graphify evidence:
openspec/validation/<change-name>.post-archive.json
```

The JSON MUST declare the exact repository-relative archived verification-report
path. The wrapper MUST reject absolute paths, traversal, alternate extensions,
wrong change/path pairing, ignored or untracked files, missing HEAD blobs, and
working-tree bytes that differ from committed HEAD blobs after repository filters.

The historical frozen-baseline path remains valid only for its historical change.

## Exact ordinary Graphify-evidence schema

The JSON MUST contain exactly these fields:

```json
{
  "schema_version": 1,
  "change_name": "example-change",
  "archive_path": "openspec/changes/archive/YYYY-MM-DD-example-change",
  "archive_commit": "<full-sha>",
  "validated_source_commit": "<full-sha>",
  "verification_report_path": "openspec/changes/archive/YYYY-MM-DD-example-change/verification-report.md",
  "verification_report_commit": "<full-sha>",
  "openspec_all_validation": {
    "status": "pass"
  },
  "python_tests": {
    "status": "pass",
    "tests": 0,
    "failures": 0,
    "errors": 0,
    "skips": 0
  },
  "git_diff_check": {
    "status": "pass"
  },
  "repository_protection": {
    "status": "pass"
  },
  "verdict": "APPROVE"
}
```

Allowed verdicts are `APPROVE` and `APPROVE WITH NON-BLOCKING NOTES`.
Unknown or missing top-level and nested fields MUST be rejected. Stored commit
values MUST be full repository SHAs.

The JSON MUST NOT contain `evidence_commit`, `indexed_source_commit`, or any SHA
whose value depends on the commit containing the JSON. The wrapper derives:

```text
evidence_commit = SourceRoot HEAD
indexed_source_commit = SourceRoot HEAD
```

## Validation report contract

`R` MUST contain only the renewed archived `verification-report.md` declared by
`verification_report_path`. The report MUST satisfy every independent-validation
fact required by `RULES.md`, including:

- validated remote branch and full SHA `V`;
- commit subject and clean worktree before/after;
- Python, Node, npm, and relevant Graphify versions;
- dependency restoration command and result;
- exact test and OpenSpec commands, counts, and outcomes;
- repository-protection checks and severity-ordered findings;
- verdict, archive/merge permissions, and whether code or tests changed.

The wrapper MUST verify that the report is tracked, committed, unchanged in the
working tree, located at the declared archived path, and records/approves exactly
`validated_source_commit = V`. Structured parsing MAY use deterministic report
markers defined by the implementation and runbook; it MUST NOT trust free-form PR
body text.

## Exact lineage contract

For an ordinary archived change the wrapper MUST prove:

1. `archive_commit`, `validated_source_commit`, and
   `verification_report_commit` resolve to full repository commits.
2. `archive_commit` is an ancestor of or equal to `V`.
3. `V` contains the declared archive path and no active change path.
4. `V` is the exact independently validated published source commit.
5. `V` is an ancestor of `R`.
6. The complete `V..R` path delta contains exactly
   `verification_report_path`.
7. The verification report is absent or differs before `R`, is committed at `R`,
   and explicitly records and approves `V`.
8. `verification_report_commit` equals `R`.
9. `R` is the direct accepted validation-evidence boundary for `E`.
10. The Graphify JSON is absent from `R` and present in `E`.
11. The complete `R..E` path delta contains exactly
    `openspec/validation/<change-name>.post-archive.json`.
12. `SourceRoot HEAD`, resolved `SourceRef`, `E`, `evidence_commit`, and
    `indexed_source_commit` are identical.

Any additional path in `V..R` or `R..E` MUST fail before Graphify generation.

## PR #16 recovery

1. Implement, independently validate, archive, and merge this infrastructure change.
2. Incorporate repaired `master` into `agent/equipment-room-vip-context` without
   force-push.
3. Review the merge and publish the resulting remote source commit `V`.
4. Independently revalidate `V` in a clean detached worktree.
5. Update the archived PR #16 `verification-report.md` and commit only that report
   as `R`.
6. Create the exact JSON containing `V`, the original feature archive commit/path,
   and `verification_report_commit = R`; commit only that JSON as `E`.
7. Run final Graphify refresh with `SourceRoot HEAD = SourceRef = E`.
8. Publish graph-only commit `G` and perform independent final graph review.

## Historical compatibility

The published `frozen-project-graph-baseline` workflow remains governed by its
existing special-case invariants unless a separately approved migration replaces
it. This change MUST NOT reinterpret its evidence, ordering, or hashes.

## Wrapper structure

Refactor the final gate into separable checks for:

- evidence and verification-report path resolution;
- committed-byte verification;
- exact JSON schema validation;
- archived/active change state;
- verification-report completeness and validated-SHA binding;
- Git ancestry and exact `V..R` and `R..E` deltas;
- source-ref and clean-HEAD binding;
- historical compatibility;
- existing graph integrity and publication protections.

Failures SHOULD identify the failed contract without exposing sensitive data or
user-specific absolute paths.

## Required tests

Add coverage for:

- valid historical frozen-baseline evidence;
- valid ordinary `V -> R -> E -> G` flow;
- exact JSON field validation and rejection of self-referential fields;
- report path/commit mismatch;
- report that does not record or approve `V`;
- additional path in `V..R`;
- additional path in `R..E`;
- malformed, missing, ignored, untracked, modified, or wrong-path artifacts;
- invalid SHAs, ancestry, archive state, source ref, verdict, or checks;
- renewed validation after incorporating repaired `master`;
- no regression to existing Graphify integrity and publication protections.

## Rollout

1. Approve this architecture.
2. Implement wrapper, runbook, tests, and applicable root-spec delta.
3. Independently validate this infrastructure implementation.
4. Archive and merge it.
5. Execute the PR #16 recovery sequence above.
6. Perform independent final graph review before PR #16 merge.
