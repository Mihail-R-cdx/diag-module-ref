## 1. Architecture and Spec

- [x] Inspect `RULES.md`, root specs, current Audio DSP UI, Biamp handler and
  worker, Extron protocol patterns, credential ownership, worker lifecycle,
  stale-context protection, and relevant tests.
- [x] Create proposal, design, tasks, and spec deltas.
- [x] Keep this change specification-only with no production or test edits.

## 2. Implementation Tasks

- [ ] Add `Extron DMP 64 Plus` under the existing `Audio DSP` selector category.
- [ ] Route `Extron DMP 64 Plus` to `AudioDSPScreen`.
- [ ] Preserve Biamp Tesira Forte CI `signal_sources` table behavior.
- [ ] Add DMP `Inputs` and `Outputs` meter-bar presentation mode.
- [ ] Render six input bars and four output bars with green horizontal fill.
- [ ] Implement physical OIDs `40000-40005` and `60000-60003`.
- [ ] Exclude `40100-40105` from the current meter path.
- [ ] Generate read command bytes `ESC V<OID>AU CR`.
- [ ] Generate bounded recovery command bytes `ESC V<OID>*2AU CR`.
- [ ] Parse `1*NNN` and `2*NNN` as valid samples.
- [ ] Treat `0*0` as unavailable, not `0 dBFS`.
- [ ] Convert raw meter values with `dBFS = -(raw_meter / 10)`.
- [ ] Normalize display with `clamp((db_value + 60) / 72, 0, 1)`.
- [ ] Separate SSH transport, stream framing, PTY echo filtering, clean SIS
  payload extraction, and DMP parsing.
- [ ] Establish DMP SIS-over-SSH on port `22023` using
  `open_session -> get_pty(term='vt100') -> invoke_shell()`.
- [ ] Use one persistent background polling context per active DMP context.
- [ ] Poll all ten OIDs sequentially and emit complete snapshots.
- [ ] Prevent overlapping DMP workers, parallel requests, and per-channel GUI
  polling loops.
- [ ] Stop/cancel polling on model change, IP change, leaving the DMP screen,
  starting a new DMP context, and application close.
- [ ] Drop queued stale work before handler acquisition/network I/O where possible.
- [ ] Ignore stale in-flight callbacks.
- [ ] Keep credential fallback in the application/composition layer.
- [ ] Save credential memory only after accepted successful DMP operation.
- [ ] Distinguish authentication, transport/session, SIS protocol, per-OID
  unavailable, malformed payload, and stale/cancelled outcomes.
- [ ] Redact credentials and SSH secret material everywhere.

## 3. Required Tests

- [ ] Device selector and Audio DSP routing.
- [ ] Biamp AudioDSPScreen regression.
- [ ] DMP Inputs/Outputs meter rendering.
- [ ] DMP OID map.
- [ ] SIS read command bytes.
- [ ] SIS recovery command bytes.
- [ ] PTY echo filtering.
- [ ] Fragmented SSH reads and multiple frames in one read.
- [ ] Clean payload parsing independent of line position.
- [ ] `1*NNN`, `2*NNN`, `0*0`, `E13`, and malformed payloads.
- [ ] dBFS conversion and scale normalization.
- [ ] Clamping below `-60` and above `+12`.
- [ ] `0 dBFS` maps to approximately `83.3%`.
- [ ] Unavailable sample does not render as maximum fill.
- [ ] One-shot `*2` recovery and no repeated recovery loop.
- [ ] Fresh session gets fresh recovery budget.
- [ ] Partial snapshot semantics.
- [ ] Transport-wide failure distinct from per-channel unavailable.
- [ ] One persistent polling session and no overlapping cycles.
- [ ] Worker cancellation and stale result suppression.
- [ ] Context switch by model, IP, screen, and app close.
- [ ] Structured authentication failure and application-owned credential fallback.
- [ ] Handler/worker does not iterate credentials.
- [ ] Secret redaction.
- [ ] No GUI-thread network I/O.
- [ ] No live DMP hardware required for normal automated tests.

## 4. Validation

- [ ] Run `.\openspec.cmd validate extron-dmp64-plus-meter-diagnostics --strict`.
- [ ] Run `.\openspec.cmd validate --all --strict`.
- [ ] Run `git diff --check`.
- [ ] Confirm only OpenSpec/specification artifacts changed.
