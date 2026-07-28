# Design: Generalize final Graphify refresh evidence

## Context

The current final Graphify gate was designed for the one-time `frozen-project-graph-baseline` workflow. It accepts only:

- `openspec/validation/frozen-project-graph-baseline.post-archive.json`;
- `change_name = frozen-project-graph-baseline`;
- a source HEAD whose delta from `validated_source_commit` contains only that evidence file.

Those constraints are intentionally strict for the original baseline, but they are not a reusable contract for subsequent archived changes. PR #16 demonstrates the failure mode: its valid post-archive source includes implementation, tests, root-spec updates, archived change artifacts, and validation evidence, so the wrapper rejects the checkpoint before Graphify generation.

## Goals

1. Support strict final Graphify refresh checkpoints for ordinary archived OpenSpec changes.
2. Preserve the original frozen-baseline gate as a valid special case.
3. Bind every refresh to an exact clean source commit and repository-owned evidence.
4. Reject evidence that is untracked, modified, ignored, stale, unrelated, or inconsistent with Git ancestry.
5. Avoid trusting prose reports, PR bodies, local-only test claims, or Graphify output as validation authority.
6. Keep generated artifact scope, encoding, hash, sensitive-data, ghost-node, and topology protections unchanged.

## Non-goals

- Do not refresh `graphify-out/` as part of this change.
- Do not merge or unblock PR #16 merely by changing documentation.
- Do not weaken independent validation requirements.
- Do not allow arbitrary evidence paths without repository policy.
- Do not infer passing validation from commit messages or PR metadata.
- Do not make Graphify mandatory for ordinary implementation or validation sessions.

## Proposed contract

### Evidence location

Ordinary changes use a deterministic repository-owned path:

```text
openspec/validation/<change-name>.post-archive.json
```

The wrapper MUST validate `<change-name>` as a semantic OpenSpec change name and MUST reject path traversal, absolute paths, alternate extensions, ignored files, untracked files, and working-tree bytes that differ from the committed HEAD blob.

The historical path remains accepted only for the historical change:

```text
openspec/validation/frozen-project-graph-baseline.post-archive.json
```

### Evidence schema

The ordinary-change evidence records at least:

```json
{
  "schema_version": 1,
  "change_name": "example-change",
  "archive_path": "openspec/changes/archive/YYYY-MM-DD-example-change",
  "archive_commit": "<full-sha>",
  "validated_source_commit": "<full-sha>",
  "evidence_commit": "<full-sha>",
  "indexed_source_commit": "<full-sha>",
  "openspec_all_validation": { "status": "pass" },
  "python_tests": { "status": "pass" },
  "git_diff_check": { "status": "pass" },
  "repository_protection": { "status": "pass" },
  "verdict": "APPROVE|APPROVE WITH NON-BLOCKING NOTES"
}
```

Exact final field names may be refined during architectural review, but the implementation MUST preserve these semantic facts.

### Lineage

For an ordinary archived change, the wrapper MUST establish:

- `archive_commit` exists and contains the archived change path;
- the active change path is absent from the selected indexed source commit;
- `validated_source_commit` is the exact independently validated implementation/source commit recorded by published validation evidence;
- `archive_commit` is a descendant of or equal to the validated implementation lineage as defined by repository workflow;
- `evidence_commit` contains the change-specific evidence and is an ancestor of or equal to `indexed_source_commit`;
- `indexed_source_commit` equals the clean source worktree HEAD and the resolved `SourceRef`;
- all four SHAs are full repository commits and their ordering is consistent with the declared workflow.

The wrapper MUST NOT require that the complete delta from `validated_source_commit` to `indexed_source_commit` contain only the evidence JSON. Instead it MUST validate the expected change-specific stages and ensure no unvalidated production/source mutation occurs after the accepted archive/evidence boundary.

### Post-evidence source mutation rule

The final architecture MUST define an explicit boundary after which only approved Graphify/process metadata may change before graph generation. Production source, tests, root specs, archived evidence, Graphify policy, or application configuration changes after that boundary MUST invalidate the refresh and require renewed independent validation or a new approved source commit.

A simple implementation may require:

```text
indexed_source_commit == evidence_commit
```

for ordinary changes. A more flexible implementation may allow a documented allowlist of process-only paths after `evidence_commit`. Any flexibility MUST be explicit, deterministic, tested, and fail closed.

### Historical compatibility

The original `frozen-project-graph-baseline` workflow remains governed by its existing special-case invariants unless a separately approved migration replaces them. Generalization MUST NOT retroactively reinterpret its published evidence or hashes.

## Wrapper structure

Refactor the current monolithic final gate into separable validation responsibilities:

- evidence path resolution;
- tracked committed-byte verification;
- schema validation;
- archived/active change path verification;
- Git ancestry and source binding;
- required-check and verdict verification;
- post-evidence mutation policy;
- historical frozen-baseline compatibility.

Typed/structured failures SHOULD identify which contract failed without exposing sensitive repository data.

## Tests

Add automated tests covering at least:

- valid historical frozen-baseline evidence;
- valid ordinary archived-change evidence;
- wrong evidence path/change-name pairing;
- untracked, ignored, modified, or missing evidence;
- malformed or partial JSON;
- failed required check or disallowed verdict;
- missing archive or still-active change;
- invalid SHA, ancestry, source-ref, or source-HEAD binding;
- production/test/spec mutation after the accepted evidence boundary;
- permitted evidence-only or explicitly allowlisted process-only boundary;
- path traversal and absolute-path rejection;
- no regression to artifact allowlist and final generation gate.

## Rollout

1. Approve this architecture.
2. Implement wrapper, runbook, tests, and any root-spec delta.
3. Independently validate the implementation on its published remote HEAD.
4. Archive and merge this infrastructure change.
5. Rebase or update PR #16 only if required by repository policy; otherwise rerun its final Graphify refresh against the repaired wrapper on a source commit whose lineage is explicitly accepted.
6. Perform independent final graph review before merging PR #16.