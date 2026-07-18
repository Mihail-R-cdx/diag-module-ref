# Architecture Self-Review

## Findings

NONE

## Checklist

- Credential fallback remains in the application/composition layer.
- Network I/O remains outside the Qt GUI thread.
- DMP uses one long-lived polling context rather than overlapping workers.
- Stop/cancellation lifecycle is defined.
- Stale-context protection uses explicit non-GUI context.
- Partial snapshot semantics are defined.
- One-shot recovery budget is defined.
- Transport framing is separate from meter parsing.
- PTY echo handling is not based on fixed line numbers.
- `0*0` is unavailable and not `0 dBFS`.
- Meter Groups and SLM remain non-goals.
- Biamp Tesira behavior is preserved.
- Scale `-60 dB .. +12 dB` is defined; `0 dBFS` maps to about `83.3%`.
- Scope remains read-only diagnostics plus bounded conditional meter recovery.
