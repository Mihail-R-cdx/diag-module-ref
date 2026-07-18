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
- [ ] Enforce at most one outstanding SIS transaction per DMP polling session.
- [ ] Match meter read responses to the current transaction expected response
  contract.
- [ ] Match recovery acknowledgements to the same current OID.
- [ ] Prevent unrelated, unsolicited, or leftover frames from shifting channel
  results.
- [ ] Treat any DMP SIS transaction timeout as poisoning the current SIS
  session: abandon the current polling cycle, close SSH/channel/session
  resources, and require a later fresh session before further DMP meter
  polling.
- [ ] Do not drain/clean/reuse a DMP SIS stream after transaction timeout.
- [ ] Do not send the next OID or publish a successful complete snapshot after
  transaction timeout on the current session.
- [ ] Stop/cancel polling on model change, IP change, leaving the DMP screen,
  starting a new DMP context, and application close.
- [ ] Check cancellation before handler/session acquisition, each full polling
  cycle, each OID read, each `*2` recovery command, each recovery retry read,
  and snapshot/result emission.
- [ ] Use bounded SSH/SIS transaction timeouts so cancellation never depends on
  infinite blocking `recv()`.
- [ ] Close DMP SSH channel/client/session resources on the owning background
  execution lane for every terminal path.
- [ ] Treat repeat Refresh for the same DMP model/IP as a new authoritative
  polling generation that cancels the previous generation.
- [ ] Drop queued stale work before handler acquisition/network I/O where possible.
- [ ] Ignore stale in-flight callbacks.
- [ ] Keep credential fallback in the application/composition layer.
- [ ] Do not treat DMP transaction timeout as credential failure, credential
  fallback authorization, or successful credential-memory evidence.
- [ ] Save credential memory at most once after the first accepted complete
  ten-OID polling cycle.
- [ ] Accept supported discovered variants `DMP 64 Plus C`,
  `DMP 64 Plus C AT`, `DMP 64 Plus C V`, and `DMP 64 Plus C V AT`.
- [ ] Reject unknown DMP variants unless explicitly mapped to the supported
  variant set.
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
- [ ] Unrelated clean frame before expected meter payload.
- [ ] Unsolicited frame before expected meter payload.
- [ ] Recovery ack for wrong OID before correct `DsV<OID>*2`.
- [ ] Expected response timeout.
- [ ] Meter-read timeout abandons the current SIS session.
- [ ] Recovery acknowledgement timeout abandons the current SIS session.
- [ ] No next OID request is sent after transaction timeout on the same
  session.
- [ ] Delayed untagged meter response after timeout cannot become another
  OID's result because the old session is not reused.
- [ ] Timed-out polling cycle is not emitted as a successful complete snapshot.
- [ ] Leftover/unrelated frame does not become next OID meter result.
- [ ] `E13` and `0*0` remain distinct from transaction timeout.
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
- [ ] Cancellation before handler acquisition.
- [ ] Cancellation between OIDs.
- [ ] Cancellation before `*2`.
- [ ] Cancellation during bounded wait.
- [ ] No next cycle after cancellation.
- [ ] SSH resources released on all DMP terminal paths.
- [ ] SSH resources released after DMP transaction timeout.
- [ ] Later polling after transaction timeout starts with a fresh session and
  clean transaction state.
- [ ] Repeat Refresh does not leave two active authoritative polling contexts.
- [ ] Application close cleans up DMP session.
- [ ] Context switch by model, IP, screen, and app close.
- [ ] Structured authentication failure and application-owned credential fallback.
- [ ] Handler/worker does not iterate credentials.
- [ ] SSH login only does not cache DMP credential.
- [ ] One channel result does not cache DMP credential.
- [ ] First accepted complete snapshot caches DMP credential once.
- [ ] Complete snapshot with per-channel unavailable entries may cache DMP credential.
- [ ] Stale complete snapshot does not cache DMP credential.
- [ ] Repeated snapshots do not repeatedly alter credential memory.
- [ ] Session-level failure before first accepted snapshot does not cache DMP credential.
- [ ] Transaction timeout does not advance the DMP credential chain.
- [ ] Timed-out DMP cycle does not cache the assigned credential.
- [ ] Supported DMP variants are accepted.
- [ ] Unknown DMP variant is not accepted solely by substring matching.
- [ ] Secret redaction.
- [ ] No GUI-thread network I/O.
- [ ] No live DMP hardware required for normal automated tests.

## 4. Architecture Validation Completed

- [x] Ran `.\openspec.cmd validate extron-dmp64-plus-meter-diagnostics --strict` during architecture preparation.
- [x] Ran `.\openspec.cmd validate --all --strict` during architecture preparation.
- [x] Ran `git diff --check` during architecture preparation.
- [x] Confirmed only OpenSpec/specification artifacts changed during architecture preparation.

## 5. Implementation/Final Validation To Rerun

- [ ] Run `.\openspec.cmd validate extron-dmp64-plus-meter-diagnostics --strict`.
- [ ] Run `.\openspec.cmd validate --all --strict`.
- [ ] Run `git diff --check`.
- [ ] Confirm only OpenSpec/specification artifacts changed.
