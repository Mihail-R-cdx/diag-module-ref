## Why

Each device currently resolves at most one credential profile, so the GUI's
existing authentication retry mechanism cannot fall back to another approved
credential when an operator rotates or temporarily changes device access.

## What Changes

- Extend the credential-provider boundary to resolve an ordered chain of
  credentials while retaining the existing single-credential API.
- Permit a device mapping to name either one profile or a non-empty ordered
  list of profiles, and validate the complete chain before network I/O.
- Pass the resolved chain through GUI request composition to the existing
  worker retry flow without exposing profile names or credential values.
- Make the GUI/application composition layer the sole owner of credential
  fallback. Each worker instance performs one credential attempt; any
  protocol or transport fallback within that worker preserves that credential.
- Document both mapping forms and add regression coverage for unbounded
  chains, source priority, safe validation failures, and retry behavior.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `credential-source-isolation`: Extend profile selection to ordered,
  validated credential candidates while preserving source isolation and safe
  observability.

## Impact

Affected areas are `core/credentials.py`, GUI request composition and its
existing retry integration, `credentials.example.json`, focused offline tests,
and the credential-source-isolation specification. No runtime dependency or
real local credential file is added.
