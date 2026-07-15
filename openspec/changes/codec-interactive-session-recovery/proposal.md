## Why

Codec refresh workers now preserve credential and transport fallback ownership,
but `CodecScreen` interactive operations use a separate cached-handler path that
ignores saved Huawei transport profiles and cannot recover an expired session.
One stale handler can therefore break live audio, sleep/wake, volume, mute,
presentation, and Huawei call-log operations together.

## What Changes

- Give the GUI/application composition layer one shared interactive-session
  owner that resolves the existing ordered credential candidates before network
  I/O, reuses the existing successful credential/profile state, and serializes
  handler work outside the Qt GUI thread.
- Use the saved `connection_profile` first when it is supported, then try the
  remaining model-specific transports with the same credential; remove the
  unexplained TE20/TE40 exception that currently discards the saved profile.
- Classify initial authentication failure separately from transport, protocol,
  command, and established-session invalidation so only the application layer
  may advance the credential chain.
- Invalidate stale cached handlers, perform at most one reconnect cycle per
  interactive operation, and prevent recursive or unbounded retry.
- Define operation-specific replay and reconciliation rules: read-only work may
  replay once, while state-changing commands are reconciled against device
  state before any retry and relative volume intent is never applied twice.
- Apply the recovered path to live audio, sleep detection, Wake, volume, mute,
  presentation, and Huawei call logs for TE20, TE40, Bar 310, and supported
  Polycom interactive controls without moving the separate Polycom call-log
  worker into scope.
- Add lifecycle, model-matrix, fallback, recovery, replay, redaction, and
  regression tests for all four codec models.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `request-lifecycle-and-recovery`: Define application-owned interactive
  session identity, transport selection, invalidation, bounded recovery,
  replay policy, request isolation, and cleanup.
- `credential-source-isolation`: Extend the existing ordered-candidate
  ownership contract to interactive connection and reconnect attempts without
  creating a handler-owned retry loop.
- `device-diagnostics-and-control`: Define the supported interactive path and
  recovery behavior for Huawei TE20, Huawei TE40, CloudLink Bar 310, and
  Polycom RPG 310, including the Huawei/Polycom call-log path boundary.

## Impact

The implementation will affect `gui/screens/codec_screen.py`, focused
composition/lifecycle code in `gui/main_window.py` and `core/`, the four codec
handlers where failure classification is currently lossy, and their offline
tests. It adds no credential schema, persistent store, runtime dependency, or
live-hardware requirement and does not redesign the separate Polycom call-log
worker or roll back `credential-fallback-chains`.
