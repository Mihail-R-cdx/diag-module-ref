# Change: matrix-immutable-credential-snapshots

## Why

The diagnostic request composition layer resolves Extron IN1804 credentials before network I/O and freezes each request-scoped credential candidate with `MappingProxyType`. This immutable snapshot is the intended production shape after reachability validation.

`MatrixController` currently accepts only a concrete `dict` in both session acquisition and candidate-secret collection. A valid `MappingProxyType` candidate therefore fails `isinstance(candidate, dict)`, is reported as `No credentials for Extron IN1804`, and prevents `ExtronIN1804Handler` construction and connection. The same concrete-type check also excludes the assigned immutable candidate from the Matrix redaction boundary.

The defect is an integration mismatch between the approved immutable request snapshot and the Matrix application controller. It is not a missing credential profile, a device authentication failure, or a reason to change Matrix transport or credential-fallback policy.

## What Changes

- Define the assigned Matrix credential candidate as a mapping contract rather than a concrete mutable `dict` contract.
- Require Matrix session acquisition to accept mutable and immutable `collections.abc.Mapping` implementations while continuing to reject absent or non-mapping candidates before network I/O.
- Preserve the immutable request snapshot without mutating it or converting it into shared mutable credential state.
- Require Matrix redaction to collect the assigned candidate's secret values through the same mapping contract used for handler construction.
- Preserve application-owned candidate selection, monotonic credential fallback, structured authentication authority, session identity, route mutation safety, and successful-index persistence gates.
- Add production-shape regression coverage using `MappingProxyType`, including handler construction, connection start, redaction, non-mapping rejection, and ordinary `dict` compatibility.

## Impact

Affected specifications:

- `credential-source-isolation`
- `request-lifecycle-and-recovery`

Expected implementation areas:

- `gui/matrix_controller.py`
- `tests/test_matrix_controller.py`
- an existing focused main-window/request-snapshot integration test module if needed to cover the full production path

This architecture change does not modify production code, tests, root specifications, archived changes, credentials storage, IN1804 authentication protocol, transport fallback, Matrix route semantics, or Graphify artifacts.
