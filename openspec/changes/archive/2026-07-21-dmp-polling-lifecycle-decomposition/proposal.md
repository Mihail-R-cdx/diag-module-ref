## Why

`worker-module-decomposition`, `matrix-operation-lifecycle-decomposition`, and `pdu-application-lifecycle-decomposition` are now merged. The next remaining application-layer context hotspot is the Extron DMP 64 Plus polling lifecycle still embedded in `gui/main_window.py`.

The current DMP path already has focused lower-level boundaries:

- `core/workers/dmp.py` owns the long-lived background polling worker and keeps SSH/SIS network I/O outside the Qt GUI thread;
- `core/dmp64_plus.py` owns DMP framing, transaction correlation, cancellation primitives, timeout behavior, recovery policy, and protocol-domain helpers;
- `handlers/extron/dmp64_plus.py` owns the device-specific SSH/SIS protocol boundary;
- `AudioDSPScreen` renders accepted Audio DSP data;
- `VCSDiagnosticApp` still owns DMP context generation, cancellation token lifetime, worker construction/submission, DMP stale callback acceptance, DMP credential fallback through generic request handling, successful-credential persistence through generic result handling, and DMP invalidation wiring.

This concentration means a DMP lifecycle change still requires a large amount of unrelated `gui/main_window.py` context. It also leaves DMP-specific freshness checks distributed across generic result, error, progress, status, and completion callbacks.

The current implementation also has a contract gap: changing credential configuration invalidates Matrix and PDU application contexts but does not invalidate the active DMP polling context. The DMP freshness predicate currently checks generation, cancellation token, worker identity, model, and IP, but not a credential-context revision. An old DMP session can therefore remain authoritative after credential configuration changes even though the root request-lifecycle contract requires DMP context isolation across credential-context changes.

The change therefore defines a DMP-specific application polling controller boundary, preferably `DMPPollingController`, that localizes DMP polling lifecycle and restores credential-context invalidation without changing DMP protocol semantics, meter polling behavior, worker ownership, authentication classification, or user-visible diagnostics.

## What Changes

- Define a DMP-specific application/composition controller boundary for DMP polling context generation, cancellation publication, worker construction/submission, DMP-specific signal binding, stale callback acceptance, structured authentication-only credential fallback, first-success credential persistence gating, and shutdown/invalidation.
- Define an immutable non-secret DMP polling context containing model, IP, DMP generation, generic request identity, assigned candidate index, non-secret credential-context revision, and operation/attempt identity as needed for exact callback acceptance.
- Make DMP credential-configuration changes invalidate the active DMP polling context even when model, IP, and numeric candidate index are unchanged.
- Ensure model change, IP change, leaving the DMP context, explicit repeat Refresh, credential-context change, and application close publish cancellation to the active DMP worker and supersede its callback authority.
- Move DMP-specific freshness checks out of generic `VCSDiagnosticApp` result/error/progress/status/finished handlers so only callbacks accepted by the DMP controller reach generic rendering/UI state paths.
- Move DMP credential fallback coordination out of the generic device-error dispatch path. The DMP controller may request candidate advancement only through application-owned credential policy callbacks after a structured confirmed authentication failure.
- Preserve one assigned credential per DMP worker/session attempt. The worker and handler do not inspect or advance credential candidates.
- Preserve no-wrap credential ordering and start from the valid saved successful candidate for the exact DMP device/IP context.
- Preserve the DMP success gate: successful credential index may be committed only once, after the first accepted complete ten-OID meter snapshot from the current non-stale polling context. SSH login, model discovery, one OID, partial cycle, stale snapshot, cancellation, timeout, or terminal failure do not commit credential success.
- Ensure subsequent accepted continuous snapshots from the same polling session do not repeatedly update successful credential memory.
- Preserve all existing DMP worker/protocol contracts, including one persistent SSH/SIS session per polling worker, sequential ten-OID polling, no pipelining, `0*0` handling, bounded `*2` recovery, poisoned-session timeout behavior, background cleanup ownership, and secret redaction.
- Keep the controller DMP-specific. Do not introduce a universal `OperationManager`, `DeviceController`, `RequestManager`, or combined Matrix/PDU/DMP/codec lifecycle manager.

## Capabilities

### Modified Capabilities

- `request-lifecycle-and-recovery`: move normative DMP polling lifecycle ownership to a DMP-specific application controller, define exact non-secret context identity and stale callback acceptance, restore credential-context invalidation, and preserve background cancellation/cleanup semantics.
- `credential-source-isolation`: clarify that the DMP controller consumes application-owned credential policy callbacks, may coordinate structured authentication-only fallback, and may request successful-index persistence only after the first accepted complete snapshot without becoming a credential provider or exposing secrets.
- `diagnostic-application-shell`: define the DMP polling controller as the application lifecycle boundary between global refresh composition and `AudioDSPScreen` rendering while reducing `VCSDiagnosticApp` to DMP composition/delegation responsibilities.

No new root capability is introduced because this is a structural specialization and contract repair within the existing application shell, request lifecycle, and credential isolation capabilities.

## Impact

Future implementation is expected to add a focused controller near the existing application controllers, for example `gui/dmp_polling_controller.py`, wire DMP refresh and lifecycle invalidation through it, remove DMP-specific generation/token/stale/retry logic from generic `VCSDiagnosticApp` callbacks, and add focused regression coverage for repeat refresh, model/IP changes, credential-context changes, stale result/error/progress/status/finished callbacks, structured authentication fallback, no-wrap candidate exhaustion, first-snapshot credential commit, repeated continuous snapshots, cancellation, and application shutdown.

This architecture-only change does not implement production code, does not change tests, does not change DMP protocol behavior, does not archive the OpenSpec change, and does not merge it.