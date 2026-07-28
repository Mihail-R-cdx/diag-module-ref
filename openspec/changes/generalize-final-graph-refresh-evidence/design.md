# Design: Generalize final Graphify refresh evidence

## Context

The current final Graphify gate was designed for the one-time
`frozen-project-graph-baseline` workflow. It accepts only:

- `openspec/validation/frozen-project-graph-baseline.post-archive.json`;
- `change_name = frozen-project-graph-baseline`;
- a source HEAD whose delta from `validated_source_commit` contains only that
  evidence file.

Those constraints are intentionally strict for the original baseline, but they
are not a reusable contract for subsequent archived changes. PR #16 demonstrates
the failure mode: its valid post-archive source includes implementation, tests,
root-spec updates, archived change artifacts, and validation evidence, so the
wrapper rejects the checkpoint before Graphify generation.

## Goals

1. Support strict final Graphify refresh checkpoints for ordinary archived OpenSpec changes.
2. Preserve the original frozen-baseline gate as a valid special case.
3. Bind every refresh to an exact clean source commit and repository-owned evidence.
4. Reject evidence that is untracked, modified, ignored, stale, unrelated, or inconsistent with Git ancestry.
5. Avoid self-referential commit metadata in committed evidence.
6. Define an implementable rollout that actually unblocks PR #16.
7. Keep generated artifact scope, encoding, hash, sensitive-data, ghost-node, and topology protections unchanged.

## Non-goals

- Do not refresh `graphify-out/` as part of this change.
- Do not merge or unblock PR #16 merely by changing documentation.
- Do not weaken independent validation requirements.
- Do not allow arbitrary evidence paths without repository policy.
- Do not infer passing validation from commit messages or PR metadata.
- Do not introduce a general post-evidence process allowlist in the first version.
- Do not make Graphify mandatory for ordinary implementation or validation sessions.

## Normative ordinary-change workflow

For an ordinary archived change, the approved order is:

```text
A = archive commit for the ordinary change
M = optional merge commit that incorporates the already approved and merged
    Graphify-infrastructure repair from origin/master
V = renewed independently validated source commit after A and, when needed, M
E = dedicated evidence-only commit
G = graph-only commit
```

The infrastructure repair MUST be merged before an older blocked feature branch
uses the generalized gate. If that feature branch incorporates the repair after
its previous validation, it MUST undergo renewed independent validation on the
new published remote HEAD. The renewed validated source commit `V` becomes the
only accepted validation boundary for the subsequent final Graphify refresh.

No cross-change post-validation allowlist is used in this version. Infrastructure
code, production code, tests, root specs, archive evidence, and application
configuration MUST NOT change between `V` and `E` except for the one deterministic
ordinary-change evidence JSON created by `E`.

## Evidence location

Ordinary changes use the deterministic repository-owned path:

```text
openspec/validation/<change-name>.post-archive.json
```

The wrapper MUST derive this path from the semantic OpenSpec change name and MUST
reject path traversal, absolute paths, alternate extensions, wrong path/change
pairing, ignored files, untracked files, and working-tree bytes that differ from
the committed `HEAD` blob after repository filters.

The historical path remains accepted only for the historical change:

```text
openspec/validation/frozen-project-graph-baseline.post-archive.json
```

## Exact ordinary-change evidence schema

The ordinary-change evidence JSON MUST contain exactly these top-level fields:

```json
{
  "schema_version": 1,
  "change_name": "example-change",
  "archive_path": "openspec/changes/archive/YYYY-MM-DD-example-change",
  "archive_commit": "<full-sha>",
  "validated_source_commit": "<full-sha>",
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

Allowed verdict values are:

```text
APPROVE
APPROVE WITH NON-BLOCKING NOTES
```

Unknown or missing top-level fields MUST be rejected. Nested check objects MUST
contain the fields shown above and MUST reject unknown fields. Every commit field
stored in evidence MUST be a full 40-character repository commit SHA.

The evidence file MUST NOT contain:

- `evidence_commit`;
- `indexed_source_commit`;
- any SHA whose value depends on the commit containing this evidence file.

Those facts are wrapper-derived:

```text
evidence_commit = SourceRoot HEAD
indexed_source_commit = SourceRoot HEAD
```

This avoids a cryptographic self-reference.

## Exact lineage contract

For an ordinary archived change, the wrapper MUST prove all of the following:

1. `archive_commit` resolves to a full commit.
2. `validated_source_commit` resolves to a full commit.
3. `archive_commit` is an ancestor of or equal to `validated_source_commit`.
4. `validated_source_commit` contains the declared `archive_path`.
5. The active path `openspec/changes/<change-name>/` is absent from
   `validated_source_commit`.
6. `validated_source_commit` is the exact source commit independently validated
   after all required prerequisite merges, including the merged Graphify repair
   when an older blocked branch needs it.
7. `SourceRoot HEAD` equals the resolved explicit `SourceRef`.
8. `SourceRoot HEAD` is the dedicated evidence commit `E`.
9. The evidence file is absent from `validated_source_commit` and present in
   `SourceRoot HEAD`.
10. The complete path delta from `validated_source_commit` to `SourceRoot HEAD`
    contains exactly:

```text
openspec/validation/<change-name>.post-archive.json
```

11. Therefore `evidence_commit`, `indexed_source_commit`, and `SourceRoot HEAD`
    are the same wrapper-derived commit for graph generation.

Any other change in `V..E` MUST fail before Graphify generation. There is no
process-only allowlist in this version.

## PR #16 prerequisite handling

The architecture selects renewed independent validation rather than a cross-change
allowlist:

1. Implement, independently validate, archive, and merge this infrastructure change.
2. Update branch `agent/equipment-room-vip-context` with the repaired `master`
   using the repository-approved non-force Git workflow.
3. Review the incorporated commits and confirm no unapproved conflict resolution
   or feature mutation.
4. Run a new independent validation of the resulting published PR #16 remote HEAD.
5. Create
   `openspec/validation/equipment-room-vip-context.post-archive.json` containing
   the new `validated_source_commit`, original feature archive path and archive
   commit, required passing checks, and verdict.
6. Commit only that JSON as evidence commit `E`.
7. Run the final Graphify refresh with `SourceRoot HEAD = SourceRef = E`.
8. Publish a Graphify-only commit `G`, then perform independent final graph review.

The older PR #16 validation report remains historical evidence but is insufficient
for the new source HEAD after the infrastructure merge.

## Historical compatibility

The original `frozen-project-graph-baseline` workflow remains governed by its
existing special-case invariants unless a separately approved migration replaces
them. Generalization MUST NOT retroactively reinterpret its published evidence,
commit ordering, or hashes.

## Wrapper structure

Refactor the current final gate into separable validation responsibilities:

- evidence path resolution;
- tracked committed-byte verification;
- exact schema validation;
- archived/active change path verification;
- Git ancestry and source binding;
- required-check and verdict verification;
- evidence-only `validated_source_commit..HEAD` delta verification;
- historical frozen-baseline compatibility.

Typed/structured failures SHOULD identify which contract failed without exposing
sensitive repository data.

## Tests

Add automated tests covering at least:

- valid historical frozen-baseline evidence;
- valid ordinary archived-change evidence with wrapper-derived evidence/indexed commit;
- rejection of `evidence_commit` or `indexed_source_commit` fields in ordinary evidence;
- exact-field rejection for unknown or missing fields;
- wrong evidence path/change-name pairing;
- untracked, ignored, modified, or missing evidence;
- malformed or partial JSON;
- failed required check or disallowed verdict;
- missing archive or still-active change;
- invalid SHA, ancestry, source-ref, or source-HEAD binding;
- evidence present in `validated_source_commit`;
- any non-evidence path in `validated_source_commit..HEAD`;
- path traversal and absolute-path rejection;
- renewed-validation flow after incorporating an approved infrastructure merge;
- no regression to artifact allowlist and final generation gate.

## Rollout

1. Approve this architecture.
2. Implement wrapper, runbook, tests, and applicable root-spec delta.
3. Independently validate the implementation on its published remote HEAD.
4. Archive and merge this infrastructure change.
5. Update PR #16 with the repaired `master`.
6. Renew independent validation of PR #16 on its new published remote HEAD.
7. Publish the deterministic evidence-only commit for PR #16.
8. Rerun its final Graphify refresh through the repaired repository-local wrapper.
9. Perform independent final graph review before merging PR #16.
