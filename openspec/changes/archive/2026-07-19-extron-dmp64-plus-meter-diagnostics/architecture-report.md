# Architecture Self-Review

## Review Findings Resolution

- HIGH cancellation/resource release: RESOLVED.
- MEDIUM transaction correlation: RESOLVED.
- MEDIUM credential success gate: RESOLVED.
- MEDIUM family support: RESOLVED.
- MEDIUM untagged meter timeout desynchronization: RESOLVED.
- LOW tasks/validation state: RESOLVED.

## Findings

NONE remaining in this architecture self-review.

## Checklist

- Credential fallback remains in the application/composition layer.
- Network I/O remains outside the Qt GUI thread.
- DMP uses one long-lived polling context rather than overlapping workers.
- Cancellation ownership, checkpoints, bounded waits, repeat Refresh behavior,
  and resource cleanup are defined.
- Stale-context protection uses explicit non-GUI context.
- Partial snapshot semantics are defined.
- One-shot recovery budget is defined.
- Serialized SIS transaction correlation is defined.
- Any DMP SIS transaction timeout poisons the current session and abandons the
  current polling cycle.
- No next OID or next polling cycle is sent on a session after transaction
  timeout.
- Delayed untagged meter responses after timeout cannot shift channel results
  because the old session is closed rather than drained/reused.
- Wrong-OID recovery acknowledgement cannot satisfy the current recovery.
- Meter-read timeout and recovery-acknowledgement timeout share the same
  session-abandonment rule.
- `E13` and `0*0` remain distinct from transaction timeout.
- Transport framing is separate from meter parsing.
- PTY echo handling is not based on fixed line numbers.
- `0*0` is unavailable and not `0 dBFS`.
- Meter Groups and SLM remain non-goals.
- Biamp Tesira behavior is preserved.
- Scale `-60 dB .. +12 dB` is defined; `0 dBFS` maps to about `83.3%`.
- Credential success gate is the first accepted complete ten-OID polling cycle.
- Timed-out cycles do not authorize credential fallback and do not cache
  successful credential memory.
- Further polling after transaction timeout requires a fully new SSH/SIS
  session with clean stream and transaction state.
- Supported variants are explicit: `DMP 64 Plus C`, `DMP 64 Plus C AT`,
  `DMP 64 Plus C V`, and `DMP 64 Plus C V AT`.
- Unknown future variants are not substring-supported.
- Scope remains read-only diagnostics plus bounded conditional meter recovery.
