## Implementation Evidence

This is implementation evidence, not an independent validation verdict. It
does not approve, archive, merge, or delete the change.

### Repository baseline and scope

- Branch: `agent/change-052-credential-fallback-chains`.
- Published baseline SHA for this correction cycle:
  `914c61a59e9b6f86bbdd91384dea4d248539f4d1`.
- The earlier `docs: document portable Node validation setup` commit and its
  agreed `RULES.md` changes remain in history. `RULES.md` was read and was not
  modified.
- No force-push, rebase, squash, amend, merge, or archive operation was used.
- The final implementation commit and post-push local/remote SHA equality are
  recorded in the session handoff because a tracked report cannot contain the
  SHA of the commit that contains the report itself.

### Worker outcome corrections

- A final worker `result` now means device acquisition and parsing completed
  successfully. Authentication and non-authentication failures use the error
  signal and are never encoded as final device-data results.
- `HuaweiTE40Worker` emits one `authentication_error` for confirmed auth
  failures and one `connection_error` for timeout, SSL, connection, parsing,
  transport, or protocol failures. Generic failures no longer emit `result`.
- TE40 stops immediately after an HTTPS authentication failure. An HTTPS
  non-authentication transport failure may fall back to HTTP with the same
  assigned credential; the HTTP auth/non-auth outcome is returned without
  replacing it with a saved earlier error.
- `PolycomRPG310Worker` retains its explicitly marked HTTPS partial update.
  Failure before the partial update emits only an error. Failure during SSH or
  later parsing emits the one partial update followed by one error and no final
  non-partial result.
- TE40 and Polycom keep the GUI-assigned `current_idx`, do not inspect another
  credential candidate, redact the complete active credential chain, and emit
  no more than one final terminal result or error. Polycom partial updates are
  non-terminal and never authorize credential caching.
- `VCSDiagnosticApp.on_device_data_received()` caches a candidate only for a
  meaningful final non-partial result. As a defensive structured boundary, a
  payload explicitly marked `_outcome: error` is routed to
  `on_device_error()` before any caching, connected state, screen success, or
  success dialog. No localized error-string matching is used.
- A partial Polycom update keeps the UI loading. A following error moves it to
  the error state without caching the credential or showing a success dialog.

### Production worker contract

The production outcome matrix covers Huawei TE20, Huawei TE40, CloudLink Bar
310, Polycom RPG 310, Extron IN1804, Aten PE8208AV, and Biamp Tesira Forte CI.
Focused tests verify that exception handlers do not emit final results and no
worker changes `current_idx` during `run()`. Existing ownership tests continue
to cover one credential per worker for TE20, Bar 310, Biamp, and Aten.

### OpenSpec artifacts

- `design.md` now defines final-success-only results, failure-only errors,
  TE40 confirmed-auth fallback behavior, Polycom partial-result semantics, and
  the structured GUI guard.
- The delta `specs/credential-source-isolation/spec.md` adds successful-result,
  failed-attempt, partial-then-failure, and confirmed-authentication scenarios.
- `tasks.md` records the independent-validation worker-outcome corrections and
  their factual implementation/test status.
- The root `openspec/specs/credential-source-isolation/spec.md` was read for
  context and was not modified manually while the change remains active.

### Test evidence

- `C:\\Users\\Mih\\AppData\\Local\\Programs\\Python\\Python312\\python.exe -m unittest tests.test_credentials tests.test_credential_propagation`
  - 24 passed; 0 failures, 0 errors, 0 skips.
- `C:\\Users\\Mih\\AppData\\Local\\Programs\\Python\\Python312\\python.exe -m unittest tests.test_credential_fallback_retry`
  - 15 passed; 0 failures, 0 errors, 0 skips.
  - Covers final-success caching, error and partial non-caching, structured
    error rejection, Polycom partial-then-error UI state, non-auth no-retry,
    all seven retry dispatch paths, and saved-index exhaustion.
- `C:\\Users\\Mih\\AppData\\Local\\Programs\\Python\\Python312\\python.exe -m unittest tests.test_credential_worker_retry_ownership`
  - 8 passed; 0 failures, 0 errors, 0 skips.
- `C:\\Users\\Mih\\AppData\\Local\\Programs\\Python\\Python312\\python.exe -m unittest tests.test_hardware_log_redaction`
  - 14 passed; 0 failures, 0 errors, 0 skips.
- `C:\\Users\\Mih\\AppData\\Local\\Programs\\Python\\Python312\\python.exe -m unittest tests.test_worker_outcomes`
  - 16 passed; 0 failures, 0 errors, 0 skips.
  - Covers TE40 success/auth/timeout/SSL/parsing and HTTPS-to-HTTP outcomes;
    Polycom full success, auth, timeout, protocol, SSH, and parsing outcomes;
    immutable indexes; same-credential fallback; full-chain redaction; and the
    seven-worker exception/result contract.
- `C:\\Users\\Mih\\AppData\\Local\\Programs\\Python\\Python312\\python.exe -m unittest discover -s tests -p "test_*.py"`
  - 141 passed; 0 failures, 0 errors, 0 skips; unittest summary `OK`.

### Node and OpenSpec evidence

- Portable Node was supplied from the repository-owned ignored `.tools`
  directory through process-local `DIAG_NODE_HOME`; it was not added to the
  system PATH or tracked files.
- `node --version`: `v20.19.0`.
- `npm --version`: `10.8.2`.
- `npm ci`: succeeded; 79 packages added, 80 audited, 0 vulnerabilities.
- `.\\openspec.cmd validate credential-fallback-chains --strict`:
  `Change 'credential-fallback-chains' is valid`.
- `.\\openspec.cmd validate --all --strict`: 7 passed, 0 failed.

### Safety and hygiene

- `git diff --check` passed.
- `credentials.local.json` is ignored, absent, and untracked; it was not read.
- `node_modules` and the portable Node runtime are untracked.
- No real credential, test-log, portable-runtime, or temporary artifact is in
  the implementation diff. Tests use synthetic values only.
- `RULES.md` and the root OpenSpec specification are unchanged.

### Failures and remaining verification

- Environment: two unfiltered full-suite invocations produced misleading
  shell-wrapper statuses while emitting a large mixture of application stdout
  and unittest stderr. A filtered rerun of the same unittest discovery command
  completed with exit 0 and the authoritative summary `Ran 141 tests` / `OK`.
- Branch/test: no final targeted, full-suite, or strict-validation failure
  remains.
- Existing TLS deprecation warnings remain unchanged and do not affect the
  required offline results.
- A new independent validation session must fetch the published branch into a
  clean detached worktree, rerun the required gates, and issue its own verdict.

### Implementation status

`READY FOR RE-VALIDATION`
