## Context

The repository contains a PyQt5 diagnostic application, production handlers,
workers, parsers, offline tests, reference drivers, and a long
reverse-engineered behavior note. OpenSpec 1.6.0 is available through the
repository launcher and is configured with its standard `spec-driven` schema.
No prior OpenSpec history exists.

## Goals / Non-Goals

**Goals:**

- Make the current, verified behavior reviewable as a canonical baseline.
- Put repeatable project constraints and real validation commands in OpenSpec.
- Keep an audit trail of the bootstrap and preserve the old document.

**Non-Goals:**

- Change runtime behavior, repair defects, remove secrets from legacy code, or
  claim support merely because an experimental driver exists.
- Recreate the former role/handoff process in OpenSpec.

## Decisions

- Use four capabilities rather than one monolith: shell UX, device behavior,
  asynchronous lifecycle, and security/validation have separate review and
  change boundaries.
- Use production modules and offline tests as the evidence hierarchy; use the
  old specification only as a cross-check. This avoids making historical prose
  normative where it diverges from code.
- Treat the bootstrap as an ordinary change and archive it only after strict
  validation. Archiving applies the delta to `openspec/specs/` while preserving
  the reviewable artifacts under `openspec/changes/archive/`.
- Keep known deviations out of requirements and list them as candidates for
  explicit, scoped follow-up changes.

## Risks / Trade-offs

- [A broad baseline can accidentally promise desired behavior.] → Requirements
  describe observed code paths and label nonconforming architecture as debt.
- [Legacy text and code may drift.] → The historical notice points to the
  normative OpenSpec specs, and future work must update specs with behavior.
- [Hardware cannot be safely contacted during documentation work.] → Validate
  with the offline suite only; retain hardware tools as opt-in evidence.

## Observed mismatches and follow-up candidates

- The historical device list omits the read-only Biamp Tesira Forte CI path,
  although the current main-window dispatch, worker, and audio-DSP screen wire
  it into the production GUI. This baseline follows the code; a future change
  can reconcile historical documentation and extend device coverage tests.
- The historical note describes credential redaction as a broad guarantee, but
  the legacy `show_saved_passwords()` debug UI renders stored credentials.
  Removing or restricting that exposure is a separate security change; this
  bootstrap does not alter it or copy any credential values into new files.
- PDU outlet control constructs and uses its handler in the main-window path.
  Moving that potentially blocking operation to a worker is a separate GUI
  responsiveness change, not a claim made by this baseline.

## Migration Plan

1. Add the historical notice and project context.
2. Validate the change deltas and offline suite without modifying runtime code.
3. Archive the completed bootstrap to create `openspec/specs/`.
4. Use a new OpenSpec change for every later behavior change.

## Open Questions

None for the baseline. Security and GUI-thread deviations are deliberately
tracked as future change candidates rather than resolved in this migration.
