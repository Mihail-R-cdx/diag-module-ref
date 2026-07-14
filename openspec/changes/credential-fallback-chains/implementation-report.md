## Implementation Evidence

This is implementation evidence, not an independent validation verdict. It
does not approve, archive, merge, or delete the change.

### Repository baseline and scope

- Branch: `agent/change-052-credential-fallback-chains`.
- Published baseline SHA: `53d53ac2aec3c2396856e8b8e941ae1c58863cdc`.
- The baseline commit `docs: document portable Node validation setup` and its
  agreed `RULES.md` changes are preserved. `RULES.md` was not modified in this
  implementation session.
- History was not rewritten: no force-push, rebase, squash, amend, merge, or
  archive operation was used.
- The final implementation commit and post-push local/remote SHA equality are
  recorded in the session handoff because a tracked report cannot contain the
  SHA of the commit that contains the report itself.

### Retry ownership corrections

- The GUI/application composition layer is the sole credential-fallback owner.
  `on_device_error()` advances monotonically to the next larger candidate only
  after a confirmed authentication failure. A timeout, SSL, connection,
  parsing, transport, or protocol error terminates the chain.
- Error de-duplication is scoped to `worker + request_id`, so duplicate signals
  from one attempt cannot create a second retry while a worker reused by a new
  request remains valid. Existing request identity checks reject stale worker
  callbacks.
- A request beginning at a saved index tries only the remaining suffix of the
  chain. It does not wrap to earlier candidates and ends after a finite number
  of attempts with one safe authentication error when exhausted.
- `HuaweiTE20Worker` performs one credential attempt. Its existing HTTP/HTTPS
  transport fallback uses the same assigned username/password on every
  transport, does not change `current_idx`, and emits one terminal result or
  error.
- `HuaweiBar310Worker` performs one credential attempt, does not change
  `current_idx`, does not cache a successful index, and emits one terminal
  result or error.
- Focused review found the same competing retry pattern in the production
  Biamp and Aten workers. Those internal loops were also removed so the generic
  one-worker/one-credential requirement is true for every affected production
  path rather than only the two workers named in the original finding.
- Workers retain the full `creds_list` only as redaction/request context. The
  shared worker-secret collector now redacts every value in each candidate.

### OpenSpec artifacts

- `proposal.md`, `design.md`, and the delta
  `specs/credential-source-isolation/spec.md` now define one retry owner,
  credential-stable protocol fallback, one terminal worker outcome, monotonic
  saved-index exhaustion, and application-only credential-index advancement.
- `tasks.md` records the independent-validation corrections and their factual
  implementation/test completion.
- The root `openspec/specs/credential-source-isolation/spec.md` was read for
  context and was not modified manually while the change remains active.

### Test evidence

- `C:\\Users\\Mih\\AppData\\Local\\Programs\\Python\\Python312\\python.exe -m unittest tests.test_credentials tests.test_credential_propagation`
  - 24 passed; 0 failures, 0 errors, 0 skips.
- `C:\\Users\\Mih\\AppData\\Local\\Programs\\Python\\Python312\\python.exe -m unittest tests.test_credential_fallback_retry`
  - 13 passed; 0 failures, 0 errors, 0 skips.
  - Covers all seven production retry dispatch paths, chain lengths five and
    ten, saved-index suffix exhaustion, duplicate/stale callbacks,
    non-authentication termination, and success-in-the-middle behavior.
- `C:\\Users\\Mih\\AppData\\Local\\Programs\\Python\\Python312\\python.exe -m unittest tests.test_credential_worker_retry_ownership`
  - 8 passed; 0 failures, 0 errors, 0 skips.
  - Covers TE20 and Bar 310 one-credential behavior, TE20 transport fallback,
    authentication and non-authentication failures, immutable worker index,
    single terminal outcomes, full-chain redaction, and Biamp/Aten ownership.
- `C:\\Users\\Mih\\AppData\\Local\\Programs\\Python\\Python312\\python.exe -m unittest tests.test_hardware_log_redaction`
  - 14 passed; 0 failures, 0 errors, 0 skips.
- `C:\\Users\\Mih\\AppData\\Local\\Programs\\Python\\Python312\\python.exe -m unittest discover -s tests -p "test_*.py"`
  - 123 passed; 0 failures, 0 errors, 0 skips; final status `OK`.

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
- No internal credential-order or wrap-around loop remains in the affected
  production workers; `current_idx` is assigned by GUI composition and remains
  unchanged during a worker run.

### Failures and remaining verification

- Environment: the first parallel targeted-test rerun was rejected before
  test startup by a Windows sandbox ACL helper. The same commands were rerun
  sequentially and all passed.
- Branch/test: an intermediate full suite exposed one UI-state regression when
  error de-duplication was initially worker-global. It was corrected to
  `worker + request_id`; the focused 17-test UI/retry rerun and final 123-test
  suite passed. No branch/test failure remains.
- Existing TLS deprecation warnings remain unchanged and do not affect the
  required offline results.
- A new independent validation session must fetch the published branch into a
  clean detached worktree, rerun the required gates, and issue its own verdict.

### Implementation status

`READY FOR RE-VALIDATION`
