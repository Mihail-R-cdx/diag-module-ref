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

Independent review returned `CHANGES REQUIRED` for six findings. This
implementation update resolves them without changing the approved architecture:

- Recovery budget is now consumed when the session attempts to send the
  state-changing `*2` command, not only after a successful ACK. SIS errors,
  timeouts, and poisoned-session paths cannot replay `*2` on the same session.
- Meter transaction matching no longer treats arbitrary `*` frames as terminal
  meter responses. It accepts structured SIS errors and narrow digit-prefixed
  meter-like candidates, so frames such as `Unrelated*Frame` cannot shift OID
  mapping.
- DMP workers now carry an application-owned context containing generation,
  model, IP, token, worker identity, and credential index. DMP result, error,
  progress, status, and finished callbacks validate that context before UI,
  credential, or fallback side effects.
- Poll cadence now treats `poll_interval` as the target period between snapshot
  cycles. A slow cycle receives no extra unconditional one-second sleep, while
  a fast cycle waits only the remaining cancelable duration.
- Production DMP connection now performs read-only identity discovery with
  `1I\r` after SSH/SIS session acquisition and rejects models outside the exact
  supported variant set before meter polling begins.
- PTY echo filtering now recognizes both literal ESC echo and the live-device
  printable `^[` representation for command-echo comparison, including
  fragmented reads.

## Review-Finding Files Changed

- `core/dmp64_plus.py`
- `handlers/extron/dmp64_plus.py`
- `core/worker.py`
- `gui/main_window.py`
- `tests/test_extron_dmp64_plus_meter_diagnostics.py`
- `openspec/changes/extron-dmp64-plus-meter-diagnostics/implementation-report.md`

## Production Files Changed

- `core/dmp64_plus.py`
- `handlers/extron/dmp64_plus.py`
- `core/worker.py`
- `gui/main_window.py`
- `gui/screens/audio_dsp_screen.py`
- `handlers/extron/__init__.py`
- `core/factory.py`
- `credentials.example.json`

## Tests Added/Changed

- `tests/test_extron_dmp64_plus_meter_diagnostics.py`
- `tests/test_release_ui_qa.py`

## Automated Evidence

Runtime and dependency restoration:

```text
C:\Users\Mih\AppData\Local\Programs\Python\Python312\python.exe -> Python 3.12.9
node --version                                                   -> v20.19.0
npm --version                                                    -> 10.8.2
npm ci                                                           -> added 79 packages, audited 80, 0 vulnerabilities
```

Focused offline tests:

```text
C:\Users\Mih\AppData\Local\Programs\Python\Python312\python.exe -m unittest discover -s tests -p "test_extron_dmp64_plus_meter_diagnostics.py"
                                                                  -> 32 passed
C:\Users\Mih\AppData\Local\Programs\Python\Python312\python.exe -m unittest tests.test_biamp_tesira_forte_ci_audio_signal_status tests.test_credential_fallback_retry tests.test_pdu_gui_composition
                                                                  -> 68 passed
```

Full offline suite:

```text
C:\Users\Mih\AppData\Local\Programs\Python\Python312\python.exe -m unittest discover -s tests -p "test_*.py"
                                                                  -> 332 passed
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
git rev-parse origin/agent/extron-dmp64-plus-meter-diagnostics    -> c6918c16a14c39433f91f649018cfd667563a251
C:\Users\Mih\AppData\Local\Programs\Python\Python312\python.exe -m unittest discover -s tests -p "test_extron_dmp64_plus_meter_diagnostics.py"
                                                                  -> 32 passed
C:\Users\Mih\AppData\Local\Programs\Python\Python312\python.exe -m unittest discover -s tests -p "test_*.py"
                                                                  -> 344 passed
git diff --check                                                  -> clean
node --version                                                    -> blocked: node not found in PATH
npm --version                                                     -> blocked: npm not found in PATH
.\openspec.cmd validate extron-dmp64-plus-meter-diagnostics --strict
                                                                  -> blocked: "node" is not recognized
```

Git hygiene:

```text
git diff --check                                                  -> clean
```

## Known Limitations

- No live DMP hardware verification was run in this implementation session.
  The normal automated suite remains fully offline as required.
- Corrective OpenSpec strict validation could not be rerun in this environment
  because Node/npm were not available through PATH or `DIAG_NODE_HOME`; the
  repository-local `openspec.cmd` failed before validation with `"node" is not
  recognized`.

## Implementation Status

`READY FOR INDEPENDENT REVIEW`
