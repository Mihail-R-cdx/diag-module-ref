# Implementation Evidence

This is implementation evidence, not an independent validation verdict. It
does not approve, archive, merge, or delete the change.

## Scope

- Change: `extron-dmp64-plus-meter-diagnostics`.
- Branch: `agent/extron-dmp64-plus-meter-diagnostics`.
- Approved architecture SHA: `0e3ea1afb1a715eb461f6b11f852e6a093c2428b`.
- Implementation date: 2026-07-18.
- Hardware access: none. All normal automated tests are offline with synthetic
  DMP SSH/channel data.

## Delivered Behavior

- Added `Extron DMP 64 Plus` under `Audio DSP` and routed it to the existing
  `AudioDSPScreen`; Biamp Tesira Forte CI remains on the existing
  `signal_sources` table path.
- Added DMP meter presentation for `Inputs` and `Outputs` with six input and
  four output horizontal green meter bars.
- Added DMP physical OID map `40000-40005` and `60000-60003`; the current DMP
  meter path does not use `40100-40105`.
- Added SIS command builders, clean meter parser, dBFS conversion, linear
  `-60 dBFS .. +12 dBFS` normalization, unavailable `0*0`, `E13`, and
  malformed-payload outcomes.
- Added SSH/PTY stream framing with command echo filtering, fragmented-read
  buffering, multi-frame handling, and serialized transaction correlation.
- Added SIS-over-SSH handler on port `22023` using
  `open_session -> get_pty(term='vt100') -> invoke_shell()`.
- Added one long-lived DMP polling worker/context with one persistent SSH/SIS
  session, one outstanding transaction, sequential ten-OID snapshots, bounded
  conditional `*2` recovery, cancellation checkpoints, stale callback
  suppression, and background cleanup.
- Added timeout safety: meter-read and recovery-ack timeouts poison the current
  SIS session, stop the current cycle, prevent next-OID/next-cycle reuse, and
  emit structured transport/session failure.
- Kept DMP credential selection/fallback/cache ownership in the application
  layer. DMP fallback uses only structured `authentication_error`; timeouts,
  protocol data, malformed payloads, and auth-like message text do not advance
  credentials. The assigned credential is cached at most once after the first
  accepted complete ten-OID snapshot.
- Added explicit supported variant helper for `DMP 64 Plus C`,
  `DMP 64 Plus C AT`, `DMP 64 Plus C V`, and `DMP 64 Plus C V AT`; unknown
  substring variants are not accepted.

## Review-Finding Fixes

Independent review returned `CHANGES REQUIRED` on starting SHA
`6f4dc8a9d87d0795e95626569a84b8caa2cb8019`. This corrective implementation
pass resolves the remaining process/validation and code-quality findings
without changing the approved architecture:

- The DMP worker now calls the production handler contract directly as
  `handler.connect(self.cancellation)`. The previous broad `TypeError`
  compatibility fallback was removed so an internal `TypeError` cannot trigger
  a second connection attempt.
- DMP worker test doubles now implement `connect(cancellation=None)` where
  applicable.
- Focused regression coverage verifies that the worker passes the exact
  cancellation token into `handler.connect()` and that an internal
  `TypeError` is reported through the normal worker error path after exactly
  one `connect()` call.
- Strict OpenSpec validation was rerun in a complete repository-supported
  Node/npm environment after `npm ci`.

## Review-Finding Files Changed

- `core/worker.py`
- `tests/test_extron_dmp64_plus_meter_diagnostics.py`
- `openspec/changes/extron-dmp64-plus-meter-diagnostics/implementation-report.md`

## Production Files Changed

- `core/worker.py`

## Tests Added/Changed

- `tests/test_extron_dmp64_plus_meter_diagnostics.py`

## Automated Evidence

Runtime and dependency restoration:

```text
C:\Users\Mih\AppData\Local\Programs\Python\Python312\python.exe -> Python 3.12.9
DIAG_NODE_HOME                                                   -> not set
Node source                                                      -> portable Node v20.19.0, process-local PATH only
node --version                                                   -> v20.19.0
npm --version                                                    -> 10.8.2
npm ci                                                           -> added 79 packages, audited 80, 0 vulnerabilities
```

Focused offline tests:

```text
C:\Users\Mih\AppData\Local\Programs\Python\Python312\python.exe -m unittest discover -s tests -p "test_extron_dmp64_plus_meter_diagnostics.py"
                                                                  -> 45 passed
C:\Users\Mih\AppData\Local\Programs\Python\Python312\python.exe -m unittest tests.test_biamp_tesira_forte_ci_audio_signal_status tests.test_credential_fallback_retry tests.test_pdu_gui_composition
                                                                  -> 68 passed
```

Full offline suite:

```text
C:\Users\Mih\AppData\Local\Programs\Python\Python312\python.exe -m unittest discover -s tests -p "test_*.py"
                                                                  -> 357 passed
```

OpenSpec validation:

```text
.\openspec.cmd validate extron-dmp64-plus-meter-diagnostics --strict
                                                                  -> Change is valid
.\openspec.cmd validate --all --strict                            -> 7 passed, 0 failed
```

Corrective implementation-session validation on 2026-07-18:

```text
git fetch origin                                                  -> passed
git rev-parse HEAD                                                -> 6f4dc8a9d87d0795e95626569a84b8caa2cb8019
git rev-parse origin/agent/extron-dmp64-plus-meter-diagnostics    -> 6f4dc8a9d87d0795e95626569a84b8caa2cb8019
C:\Users\Mih\AppData\Local\Programs\Python\Python312\python.exe -m unittest discover -s tests -p "test_extron_dmp64_plus_meter_diagnostics.py"
                                                                  -> 45 passed
C:\Users\Mih\AppData\Local\Programs\Python\Python312\python.exe -m unittest tests.test_biamp_tesira_forte_ci_audio_signal_status tests.test_credential_fallback_retry tests.test_pdu_gui_composition
                                                                  -> 68 passed
C:\Users\Mih\AppData\Local\Programs\Python\Python312\python.exe -m unittest discover -s tests -p "test_*.py"
                                                                  -> 357 passed
node --version                                                    -> v20.19.0
npm --version                                                     -> 10.8.2
npm ci                                                           -> added 79 packages, audited 80, 0 vulnerabilities
.\openspec.cmd validate extron-dmp64-plus-meter-diagnostics --strict
                                                                  -> Change is valid
.\openspec.cmd validate --all --strict                            -> 7 passed, 0 failed
git diff --check                                                  -> clean
```

Git hygiene:

```text
git diff --check                                                  -> clean
```

## Known Limitations

- No live DMP hardware verification was run in this implementation session.
  The normal automated suite remains fully offline as required.

## Implementation Status

`READY FOR INDEPENDENT REVIEW`
