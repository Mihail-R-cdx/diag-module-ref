## 1. Architecture and Spec

- [x] Inspect `RULES.md`, root specs, current Audio DSP UI, Biamp handler and
  worker, Extron protocol patterns, credential ownership, worker lifecycle,
  stale-context protection, and relevant tests.
- [x] Create proposal, design, tasks, and spec deltas.
- [x] Keep this change specification-only with no production or test edits.

## 2. Implementation Tasks

- [x] Add `Extron DMP 64 Plus` under the existing `Audio DSP` selector category.
- [x] Route `Extron DMP 64 Plus` to `AudioDSPScreen`.
- [x] Preserve Biamp Tesira Forte CI `signal_sources` table behavior.
- [x] Add DMP `Inputs` and `Outputs` meter-bar presentation mode.
- [x] Render six input bars and four output bars with green horizontal fill.
- [x] Implement physical OIDs `40000-40005` and `60000-60003`.
- [x] Exclude `40100-40105` from the current meter path.
- [x] Generate read command bytes `ESC V<OID>AU CR`.
- [x] Generate bounded recovery command bytes `ESC V<OID>*2AU CR`.
- [x] Parse `1*NNN` and `2*NNN` as valid samples.
- [x] Treat `0*0` as unavailable, not `0 dBFS`.
- [x] Convert raw meter values with `dBFS = -(raw_meter / 10)`.
- [x] Normalize display with `clamp((db_value + 60) / 72, 0, 1)`.
- [x] Separate SSH transport, stream framing, PTY echo filtering, clean SIS
  payload extraction, and DMP parsing.
- [x] Establish DMP SIS-over-SSH on port `22023` using
  `open_session -> get_pty(term='vt100') -> invoke_shell()`.
- [x] Use one persistent background polling context per active DMP context.
- [x] Poll all ten OIDs sequentially and emit complete snapshots.
- [x] Prevent overlapping DMP workers, parallel requests, and per-channel GUI
  polling loops.
- [x] Enforce at most one outstanding SIS transaction per DMP polling session.
- [x] Match meter read responses to the current transaction expected response
  contract.
- [x] Match recovery acknowledgements to the same current OID.
- [x] Prevent unrelated, unsolicited, or leftover frames from shifting channel
  results.
- [x] Treat any DMP SIS transaction timeout as poisoning the current SIS
  session: abandon the current polling cycle, close SSH/channel/session
  resources, and require a later fresh session before further DMP meter
  polling.
- [x] Do not drain/clean/reuse a DMP SIS stream after transaction timeout.
- [x] Do not send the next OID or publish a successful complete snapshot after
  transaction timeout on the current session.
- [x] Stop/cancel polling on model change, IP change, leaving the DMP screen,
  starting a new DMP context, and application close.
- [x] Check cancellation before handler/session acquisition, each full polling
  cycle, each OID read, each `*2` recovery command, each recovery retry read,
  and snapshot/result emission.
- [x] Use bounded SSH/SIS transaction timeouts so cancellation never depends on
  infinite blocking `recv()`.
- [x] Close DMP SSH channel/client/session resources on the owning background
  execution lane for every terminal path.
- [x] Treat repeat Refresh for the same DMP model/IP as a new authoritative
  polling generation that cancels the previous generation.
- [x] Drop queued stale work before handler acquisition/network I/O where possible.
- [x] Ignore stale in-flight callbacks.
- [x] Keep credential fallback in the application/composition layer.
- [x] Do not treat DMP transaction timeout as credential failure, credential
  fallback authorization, or successful credential-memory evidence.
- [x] Save credential memory at most once after the first accepted complete
  ten-OID polling cycle.
- [x] Accept supported discovered variants `DMP 64 Plus C`,
  `DMP 64 Plus C AT`, `DMP 64 Plus C V`, and `DMP 64 Plus C V AT`.
- [x] Reject unknown DMP variants unless explicitly mapped to the supported
  variant set.
- [x] Distinguish authentication, transport/session, SIS protocol, per-OID
  unavailable, malformed payload, and stale/cancelled outcomes.
- [x] Redact credentials and SSH secret material everywhere.

## 3. Required Tests

- [x] Device selector and Audio DSP routing.
- [x] Biamp AudioDSPScreen regression.
- [x] DMP Inputs/Outputs meter rendering.
- [x] DMP OID map.
- [x] SIS read command bytes.
- [x] SIS recovery command bytes.
- [x] PTY echo filtering.
- [x] Fragmented SSH reads and multiple frames in one read.
- [x] Unrelated clean frame before expected meter payload.
- [x] Unsolicited frame before expected meter payload.
- [x] Recovery ack for wrong OID before correct `DsV<OID>*2`.
- [x] Expected response timeout.
- [x] Meter-read timeout abandons the current SIS session.
- [x] Recovery acknowledgement timeout abandons the current SIS session.
- [x] No next OID request is sent after transaction timeout on the same
  session.
- [x] Delayed untagged meter response after timeout cannot become another
  OID's result because the old session is not reused.
- [x] Timed-out polling cycle is not emitted as a successful complete snapshot.
- [x] Leftover/unrelated frame does not become next OID meter result.
- [x] `E13` and `0*0` remain distinct from transaction timeout.
- [x] Clean payload parsing independent of line position.
- [x] `1*NNN`, `2*NNN`, `0*0`, `E13`, and malformed payloads.
- [x] dBFS conversion and scale normalization.
- [x] Clamping below `-60` and above `+12`.
- [x] `0 dBFS` maps to approximately `83.3%`.
- [x] Unavailable sample does not render as maximum fill.
- [x] One-shot `*2` recovery and no repeated recovery loop.
- [x] Fresh session gets fresh recovery budget.
- [x] Partial snapshot semantics.
- [x] Transport-wide failure distinct from per-channel unavailable.
- [x] One persistent polling session and no overlapping cycles.
- [x] Worker cancellation and stale result suppression.
- [x] Cancellation before handler acquisition.
- [x] Cancellation between OIDs.
- [x] Cancellation before `*2`.
- [x] Cancellation during bounded wait.
- [x] No next cycle after cancellation.
- [x] SSH resources released on all DMP terminal paths.
- [x] SSH resources released after DMP transaction timeout.
- [x] Later polling after transaction timeout starts with a fresh session and
  clean transaction state.
- [x] Repeat Refresh does not leave two active authoritative polling contexts.
- [x] Application close cleans up DMP session.
- [x] Context switch by model, IP, screen, and app close.
- [x] Structured authentication failure and application-owned credential fallback.
- [x] Handler/worker does not iterate credentials.
- [x] SSH login only does not cache DMP credential.
- [x] One channel result does not cache DMP credential.
- [x] First accepted complete snapshot caches DMP credential once.
- [x] Complete snapshot with per-channel unavailable entries may cache DMP credential.
- [x] Stale complete snapshot does not cache DMP credential.
- [x] Repeated snapshots do not repeatedly alter credential memory.
- [x] Session-level failure before first accepted snapshot does not cache DMP credential.
- [x] Transaction timeout does not advance the DMP credential chain.
- [x] Timed-out DMP cycle does not cache the assigned credential.
- [x] Supported DMP variants are accepted.
- [x] Unknown DMP variant is not accepted solely by substring matching.
- [x] Secret redaction.
- [x] No GUI-thread network I/O.
- [x] No live DMP hardware required for normal automated tests.

## 4. Architecture Validation Completed

- [x] Ran `.\openspec.cmd validate extron-dmp64-plus-meter-diagnostics --strict` during architecture preparation.
- [x] Ran `.\openspec.cmd validate --all --strict` during architecture preparation.
- [x] Ran `git diff --check` during architecture preparation.
- [x] Confirmed only OpenSpec/specification artifacts changed during architecture preparation.

## 5. Implementation/Final Validation To Rerun

- [x] Run `.\openspec.cmd validate extron-dmp64-plus-meter-diagnostics --strict`.
- [x] Run `.\openspec.cmd validate --all --strict`.
- [x] Run `git diff --check`.
- [x] Confirm implementation diff is scoped to DMP production, tests, and OpenSpec/evidence artifacts.
