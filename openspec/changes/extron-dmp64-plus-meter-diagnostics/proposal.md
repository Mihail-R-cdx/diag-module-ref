## Why

Operators need read-only live meter diagnostics for the Extron DMP 64 Plus
family in the existing Audio DSP category. The current Audio DSP path supports
Biamp Tesira Forte CI signal-source tables, but it does not define DMP
physical input/output meter bars, SIS-over-SSH transport framing, bounded
meter recovery, or continuous snapshot polling.

Live evidence confirms a useful minimum scope: six physical inputs and four
physical outputs, read by direct sequential SIS meter queries over SSH port
22023. The accepted cadence is approximately one complete ten-channel snapshot
per second, with observed sequential polling around 1.07 seconds.

## What Changes

- Add `Extron DMP 64 Plus` under `Audio DSP` next to `Biamp Tesira Forte CI`.
- Reuse `AudioDSPScreen` with device-specific DMP meter-bar presentation while
  preserving Biamp table behavior.
- Define DMP SIS-over-SSH transport using the supported implementation
  mechanism `open_session -> get_pty(term='vt100') -> invoke_shell()`.
- Define stream buffering/framing and PTY echo filtering before clean SIS
  payloads reach the meter parser.
- Define physical input/output OIDs, direct meter reads, dBFS conversion,
  `-60 dB .. +12 dB` linear meter scale, unavailable samples, partial
  snapshots, and one-shot `*2` recovery after `0*0`.
- Define one long-lived background polling context with sequential snapshots,
  no overlapping workers, explicit cancellation, stale-context protection, and
  application-owned credential fallback.
- Add offline testability requirements for protocol, scale, recovery,
  lifecycle, stale handling, structured errors, and secret redaction.

## Impact

This change is specification-only. It prepares architecture and acceptance
criteria for a later implementation session. Production code and tests are not
changed by this proposal.

## Non-Goals

- Do not implement production code in this change.
- Do not add gain, mute, routing, phantom power, presets, DSP configuration,
  FlexInput switching, Dante configuration, Meter Groups, SLM, or Telnet 23.
- Do not require Meter Groups, push subscription, or DSP Configurator setup.
- Do not use numeric meter values as the required primary UI.
- Do not require cadence faster than approximately one complete snapshot per
  second.
- Do not create overlapping polling workers, ten SSH connections, ten parallel
  requests, or per-channel GUI polling loops.
- Do not move credential iteration into the DMP handler or worker.
