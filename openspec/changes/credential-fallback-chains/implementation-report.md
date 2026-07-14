## Implementation Evidence

This is an implementation-session record, not an independent validation
verdict. It does not approve, archive, merge, or delete the change.

### Baseline and delivered fixes

- Baseline branch SHA: `7534917a47102f0392b596e854f60650a7e097e6`.
- Successful credential indexes are now stored only under a device/IP key for
  IP-specific requests; a legacy device-only value is not an IP fallback.
  A new IP starts at zero, the original IP retains its own successful index,
  and an out-of-range saved index safely starts at zero.
- Refresh and command paths use the bounded device/IP helper. Partial worker
  results no longer cache a candidate as successful, and existing request-id
  checks continue to reject stale callbacks.
- `on_device_error()` redacts errors before TE20 or Extron terminal rendering.
  It passes every value in the active candidate chain as an explicit secret to
  the centralized redaction helper, covering unlabeled values as well as
  username, password, token, session, and authorization material.
- Regression coverage includes cross-IP and cross-device isolation, legacy
  device-only non-fallback behavior, invalid-index recovery, partial results,
  TE40/Extron/Aten retry dispatch, and TE20/Extron terminal, status, and dialog
  redaction with synthetic values.

### Test evidence

- `C:\\Users\\Mih\\AppData\\Local\\Programs\\Python\\Python312\\python.exe -m unittest tests.test_credentials tests.test_credential_propagation`
  - 24 passed; 0 failures, 0 errors, 0 skips.
- `C:\\Users\\Mih\\AppData\\Local\\Programs\\Python\\Python312\\python.exe -m unittest tests.test_credential_fallback_retry`
  - 8 passed; 0 failures, 0 errors, 0 skips.
- `C:\\Users\\Mih\\AppData\\Local\\Programs\\Python\\Python312\\python.exe -m unittest tests.test_hardware_log_redaction`
  - 14 passed; 0 failures, 0 errors, 0 skips.
- `C:\\Users\\Mih\\AppData\\Local\\Programs\\Python\\Python312\\python.exe -m unittest discover -s tests -p "test_*.py"`
  - 110 passed; 0 failures, 0 errors, 0 skips.
- `git diff --check`
  - passed before the final evidence update; it is rerun before commit.
- Portable Node from the repository-root `.tools` directory:
  - Node `v20.19.0`; npm `10.8.2`.
- `npm ci`
  - succeeded: 79 packages added, 80 audited, 0 vulnerabilities.
- `./openspec.cmd validate credential-fallback-chains --strict`
  - passed: `Change 'credential-fallback-chains' is valid`.
- `./openspec.cmd validate --all --strict`
  - passed: 7 items passed, 0 failed.

### Environment resolution and remaining handoff

- `python` is unavailable on PATH; the installed Python 3.12 executable above
  was used directly.
- `RULES.md` identifies the portable Node directory. It was prepended to PATH
  only for the commands above; no system PATH setting or portable runtime is
  committed.
- The implementation commit SHA and its post-push local/remote comparison are
  recorded in the session handoff after the normal commit and push.

### Remaining verification

After publication, an independent validation session must fetch the published
branch, create a clean detached worktree from its remote SHA, rerun the
required checks, and record its own verdict. No `APPROVE` is issued here.
