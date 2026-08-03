# Design: Matrix immutable credential snapshots

## Context

The current diagnostic composition path resolves the complete ordered credential chain before preliminary reachability work, freezes each candidate as `MappingProxyType(dict(candidate))`, and stores the resulting tuple in `DiagnosticCredentialSnapshot`. After reachability succeeds, the same request-scoped candidates and starting candidate index are passed to the selected device lifecycle.

For Extron IN1804, `MatrixController` receives this snapshot and stores the candidate tuple for the submitted operation. The controller then performs two concrete-type checks:

```python
if not isinstance(candidate, dict):
    return ()
```

for candidate-secret collection, and:

```python
if not isinstance(candidate, dict):
    raise RuntimeError("No credentials for Extron IN1804")
```

for handler/session acquisition.

`MappingProxyType` implements the mapping operations used by the controller, including `get()`, `values()`, iteration, and membership, but it is not a `dict`. The controller therefore loses the semantic meaning of a correctly resolved immutable candidate solely because of its container implementation.

The resulting production sequence is:

```text
JsonCredentialProvider resolves the IN1804 profile
-> application composition freezes the candidate
-> reachability snapshot carries MappingProxyType
-> MatrixController retrieves the assigned candidate
-> concrete dict check rejects it
-> handler construction and network connection never start
```

The same mismatch means `_candidate_secrets()` returns an empty tuple, so fixing only session acquisition would leave immutable candidate values outside the Matrix redaction boundary.

## Goals

1. Make the Matrix controller consume the semantic mapping contract already provided by production composition.
2. Preserve immutable request snapshots through candidate lookup, redaction, and handler construction.
3. Keep candidate selection and fallback authority in the application/composition boundary.
4. Ensure the same assigned candidate values are used for handler inputs and redaction.
5. Reject absent or invalid candidate containers before network I/O without granting credential fallback authority.
6. Add tests that reproduce the real `MappingProxyType` production shape.
7. Preserve compatibility with existing mutable dictionary candidates used by tests and explicit callers.

## Non-goals

- Do not change `JsonCredentialProvider`, `DiagnosticCredentialSnapshot`, or `_freeze_credential_candidates()`.
- Do not make credential candidates mutable.
- Do not add provider access, candidate iteration, or fallback ownership to `MatrixController`, Matrix workers, or handlers.
- Do not change IN1804 username/password prompts, port selection, SSH/Telnet negotiation, or transport fallback.
- Do not redefine structured Matrix authentication classification.
- Do not change route mutation replay or ambiguous-outcome policy.
- Do not change successful credential-index persistence gates.
- Do not expose credential values, profile names, candidate containers, or private credential identity through public operation context or signals.
- Do not modify unrelated device controllers or introduce a generic credential-container abstraction across the whole repository.

## Authority and ownership

The existing authority model remains unchanged:

```text
application/composition layer
  resolves and validates the ordered chain
  freezes the request-scoped candidate snapshot
  selects the assigned candidate index
  owns structured credential fallback and success memory

MatrixController
  receives or requests the resolved candidate sequence
  binds one assigned candidate to one operation
  uses that candidate for redaction and session construction
  reports structured operation outcomes

ExtronIN1804Handler
  receives explicit username/password inputs
  owns protocol and transport work for one assigned candidate
  does not inspect or advance candidate lists
```

This change repairs the representation contract between the first two boundaries. It does not transfer ownership.

## Assigned candidate contract

The assigned Matrix candidate SHALL be treated as a `collections.abc.Mapping`-compatible object. The controller may read fields and values through the mapping interface but SHALL NOT require the concrete object to be `dict` and SHALL NOT mutate it.

The implementation should use the runtime mapping contract consistently in:

- credential candidate provider type annotations;
- candidate-secret collection;
- session/handler acquisition;
- focused helper functions introduced to avoid divergent validation behavior.

A local immutable candidate may be passed through unchanged. There is no requirement to call `dict(candidate)` before handler construction because the handler already receives scalar constructor arguments rather than the candidate container itself.

The design intentionally avoids a mutable defensive copy as the primary boundary. A temporary private copy is permissible only if a future lower-level API demonstrably requires one, and it must not become shared candidate state or alter request identity. No such copy is required for the current IN1804 handler.

## Candidate validity

A candidate is usable for the Matrix credential boundary when it implements `Mapping`. Existing credential-schema validation remains owned by the provider/composition layer and is not duplicated in the controller.

An absent candidate, out-of-range assigned index, or non-mapping candidate remains a local credential precondition failure. It SHALL:

- stop before handler construction and network I/O;
- disclose no candidate content;
- not be converted into confirmed device credential rejection;
- not authorize advancement to another candidate;
- preserve current route mutation safety and stale-operation behavior.

This change does not require a new public error category. Implementation may preserve the existing safe Matrix precondition presentation, provided the failure remains non-secret and non-fallback-authorizing.

## Redaction continuity

The controller must derive candidate secrets from the same accepted mapping instance used for handler construction. Any non-empty assigned candidate values covered by the existing redaction policy must be present in the secret collection before:

- `redacted_callback` is attached to the handler;
- connection or protocol work may emit terminal output;
- `_safe_error` formats a failure;
- public error, status, terminal, or result signals are emitted.

Container mutability is not a redaction decision. `dict`, `MappingProxyType`, and another supported mapping implementation with equivalent values must produce equivalent redaction inputs.

This change does not broaden the public data model. `MatrixOperationHandle.creds_list` remains empty, operation context remains non-secret, and public signals/results do not carry the candidate mapping.

## Session acquisition

For a current operation with an assigned mapping candidate, session acquisition shall:

1. resolve the assigned candidate through the existing operation snapshot/provider path;
2. verify the general mapping contract;
3. derive or receive the redaction secret set from that same candidate;
4. construct `ExtronIN1804Handler` with scalar `username` and `password` values read through `candidate.get(...)`;
5. attach the existing redacted terminal callback before `connect()`;
6. connect and retain the session under the existing `MatrixSessionIdentity` rules.

The immutable container itself does not become part of public session identity. Existing model, IP, protocol/port, credential-context revision, candidate index, and connected-state rules remain authoritative.

## Snapshot and fallback semantics

Freezing a candidate changes mutability, not candidate identity or ordering. The following remain unchanged:

- the starting successful index for the exact model/IP context;
- the request-scoped remaining suffix;
- monotonic advancement after structured confirmed device rejection only;
- no wrap-around;
- the same assigned candidate across transport attempts;
- no route fallback after a possible state-changing send;
- no successful-index persistence from session acquisition alone;
- persistence only after an accepted final full Matrix refresh under current policy;
- stale operations cannot save credentials or update the active screen.

The implementation SHALL NOT re-resolve a different provider candidate merely because the submitted snapshot uses an immutable mapping implementation.

## Type annotations

Focused Matrix controller annotations should describe the accepted semantic shape rather than `Iterable[dict]`. An appropriate contract is an iterable of mappings with string keys and object values, while preserving compatibility with the Python version and typing conventions used by the repository.

Type annotation cleanup is in scope only where it documents the Matrix controller boundary. A repository-wide typing refactor is out of scope.

## Test strategy

Regression coverage must exercise the production representation, not only ordinary dictionaries.

### Controller-level coverage

Create a `MappingProxyType` candidate and prove:

- `_candidate_for_context()` returns the assigned immutable mapping;
- `_candidate_secrets()` includes its non-empty username/password values;
- `_acquire_session()` constructs the handler with those scalar values;
- `connect()` is invoked;
- `No credentials for Extron IN1804` is not raised solely because the candidate is immutable;
- the mapping is not mutated;
- ordinary `dict` candidates remain supported.

### Error and redaction coverage

Prove:

- a non-mapping candidate is rejected before handler construction and `connect()`;
- candidate values embedded in a simulated handler exception or terminal callback are redacted when the candidate is immutable;
- public result, error, terminal, status, and `MatrixOperationHandle` payloads contain no credential mapping or value;
- invalid local candidate shape does not request credential advancement.

### Production-path integration coverage

Use the same snapshot creation shape as `VCSDiagnosticApp._freeze_credential_candidates()` and exercise:

```text
resolved candidate
-> MappingProxyType request snapshot
-> Matrix full refresh submission
-> MatrixController assigned-candidate lookup
-> ExtronIN1804Handler construction/connect
```

The integration test may use focused fakes for reachability and handler I/O. It must not require a real device or local credential file and must not weaken secret-isolation assertions.

### Regression protection

Existing Matrix lifecycle tests for stale suppression, serialized access, session identity, route mutation safety, authentication classification, keepalive, cleanup, and successful credential persistence must continue to pass unchanged unless a narrow assertion update is required by the mapping annotation contract.

## Implementation boundaries

Expected production change:

```text
gui/matrix_controller.py
```

Expected focused tests:

```text
tests/test_matrix_controller.py
```

One existing request-snapshot or main-window test module may be modified only if needed for the full production-path integration case. The implementation session must identify and justify that file in its report.

Out of scope:

```text
gui/main_window.py snapshot creation semantics
core/credentials.py
handlers/extron/in1804.py
core/base_handler.py
credentials.local.json
unrelated device controllers/workers
root OpenSpec specifications before archive
archived changes
validation evidence outside the approved workflow
Graphify artifacts
```

## Validation and rollout

1. Review and approve this architecture-only change.
2. Implement the mapping contract and focused regression tests on the existing branch.
3. Run focused Matrix tests, the full offline Python suite, `git diff --check`, strict change validation, and strict all validation.
4. Publish a focused implementation commit without rewriting history.
5. Independently validate the exact remote implementation HEAD in a clean detached worktree.
6. Perform a disposable archive-applicability check because this change adds root-spec requirements.
7. Archive only after approval, review the archive/root-spec diff, repeat post-archive checks, and publish a dedicated archive commit.
8. Merge only after explicit user authorization and rechecking current remote branch HEAD and current `master`.
