## Why

The existing application was developed through direct edits and has a detailed
reverse-engineered note, but it has no canonical OpenSpec baseline. Establishing
one lets future work describe and validate intentional behavior changes without
inventing a fictitious history for the code that already exists.

## What Changes

- Initialize the standard OpenSpec `spec-driven` workflow and record durable
  project context.
- Capture verified current GUI, diagnostic, control, request-lifecycle, and
  security-observability behavior as new baseline capabilities.
- Preserve `specs/vcs-diagnostic-openspec.md` as historical source material
  and identify discrepancies and debt for separate future changes.
- Do not change production code, dependencies, tests, devices, or runtime
  behavior.

## Capabilities

### New Capabilities

- `diagnostic-application-shell`: PyQt application startup, device selection,
  input validation, and stateful refresh UX.
- `device-diagnostics-and-control`: Supported device diagnostics and the
  control actions wired into the production GUI.
- `request-lifecycle-and-recovery`: Worker execution, request scoping,
  credential retry, protocol fallback, and resource cleanup.
- `secure-observability-and-validation`: Redacted diagnostic output, offline
  verification boundaries, and OpenSpec completion expectations.

### Modified Capabilities

- None.

## Impact

This change adds OpenSpec configuration, baseline specifications, and change
artifacts. `main.py`, `gui/`, `core/`, `handlers/`, `utils/`, dependencies,
and existing tests remain unchanged. After archive, `openspec/specs/` is the
normative source; the prior reverse-engineered document remains historical.
