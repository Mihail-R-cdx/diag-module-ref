# Final technical verification report

## Scope and verified revision

This report covers the final remediation required by independent validation of
published commit `8e5511c016c5f05af75d26c2b983ba622927639b`, which returned
`CHANGES REQUIRED`. The verified revision is `HEAD` (the commit containing
this report), tested in a clean worktree based on that published commit. No real
`credentials.local.json` was created, read, or committed; all credentials and
tokens used by tests were synthetic.

## Resolved findings

- The main-window startup contract is `950 x 950`. The prior `950 x 1000`
  geometry change was incidental to window top-alignment work: it contradicted
  the pre-existing contract test and the responsive GUI documentation, and was
  not part of the credential change. Production now restores `950 x 950`; the
  existing GUI test remains the contract and also verifies responsive layouts.
- TE-40 status subrequests, complete status collection, SIP-server update, and
  SIP-server verification no longer print raw exception text or use
  `traceback.print_exc()`. They share `_report_exception`, which redacts the
  exception and formatted traceback before stdout or the command logger.
- The shared text policy now redacts standalone `Bearer`/`Basic` values and
  key/value representations of authorization, cookies, session IDs, CSRF
  tokens, passwords, and access/API keys. This closes a discovered regression
  where an authorization value contained only in an exception was not yet in
  handler state.
- The shared key/value text policy now also recognises the exact `username`
  credential key, case-insensitively. It redacts unbound values in
  `username=value`, colon and whitespace variants, single/double quoted
  values, and uppercase/mixed-case keys without treating unrelated keys such
  as `userType`, `user_count`, or `username_status` as credentials.
- Removed two earlier dead `fix_sip_huawei_te40` definitions and their
  superseded SIP helpers. Class lookup and all call sites use the single final
  SIP flow and error handler; no alias or dynamic lookup referenced the
  deleted definitions.

## Regression coverage

`test_te40_operation_exception_and_traceback_are_redacted` creates a
`HuaweiTE40Handler` with synthetic username, password, session ID, CSRF token,
cookie, and Authorization value. It forces failures in every TE-40 status
subrequest, SIP update, and SIP verification, captures stdout and the command
logger, and asserts that none of those values cross a public boundary while
redacted diagnostic context remains present. Its exception also contains an
unbound `username` value absent from the handler credentials, session, CSRF
token, cookie jar, and explicit secret list; the captured public outputs omit
it. `test_redacts_unknown_username_key_value_from_exception_text` independently
exercises all supported `username` key/value spellings with `secrets=()` and
keeps the non-sensitive exception context. Both tests use no network or
hardware.

## Commands and actual results

- `C:\\Users\\Mih\\AppData\\Local\\Programs\\Python\\Python312\\python.exe -m unittest tests.test_redaction.RedactionTests.test_redacts_unknown_username_key_value_from_exception_text`
  passed: 1 test in 0.000 seconds.
- `C:\\Users\\Mih\\AppData\\Local\\Programs\\Python\\Python312\\python.exe -m unittest tests.test_redaction`
  passed: 8 tests in 0.061 seconds.
- `C:\\Users\\Mih\\AppData\\Local\\Programs\\Python\\Python312\\python.exe -m unittest tests.test_redaction tests.test_credential_propagation tests.test_gui_theme`
  passed: 25 tests in 0.332 seconds.
- `C:\\Users\\Mih\\AppData\\Local\\Programs\\Python\\Python312\\python.exe -m unittest discover -s tests -p 'test_*.py'`
  passed: 61 tests in 0.888 seconds.

All commands ran as one offline process per command in the clean checkout.
They made no live hardware or network calls, did not read a real local
credential file, and completed without a Qt crash or hung threads. The
different historical counts (53, 56, 59, and 85) were recorded from different
repository states and test selections; this report intentionally records only
the reproducible 61-test result from the verified revision.

## Validation and repository protection

The following commands passed in this clean checkout:

- `..\\openspec.cmd validate externalize-device-credentials --strict`
- `git diff --check`
- `git check-ignore -v credentials.local.json`
- `git ls-files -- credentials.local.json`

These checks confirm strict OpenSpec validity, no whitespace errors, that the
real local credential filename is ignored, and that no local credential file
is tracked. The active change remains unarchived. Tasks 5.2, 5.3, 6.8, 6.11,
7.2, and 7.7 remain supported; owner decisions in 7.3, 7.6, and 7.8 are not
changed by this report.

No Critical, High, or Medium finding remains from the independent validation.
The change is ready for final independent validation before archive.

## Independent final validation

Validation date: 2026-07-12 (Europe/Moscow).

The independently validated implementation is
`433023510f3384b0932385ae1399a3197fd6fe2b` — `Redact username key-value
diagnostics`. `git fetch origin`,
`git rev-parse origin/agent/bootstrap-openspec-baseline`, and
`git log -1 --format="%H%n%s" origin/agent/bootstrap-openspec-baseline`
confirmed that the remote branch resolved to that exact SHA and subject.

Validation ran in the separate clean worktree
`.independent-final-validation`, detached at that remote revision. Before
testing, `git rev-parse HEAD` returned the implementation SHA and
`git status --short` was empty; therefore local HEAD and the fetched remote
branch matched. No `AGENTS.md` was present in that checkout.

### Independent checks and results

- Reviewed the proposal, design, tasks, both change specs, and the preceding
  report as claims rather than evidence. The last implementation diff changes
  only `core/redaction.py`, this report, and `tests/test_redaction.py`.
- Reviewed `core/redaction.py`: `_SENSITIVE_TEXT_VALUE` includes the exact
  case-insensitive `username` key, accepts `:` and `=`, surrounding spaces,
  and single- or double-quoted values. Its word boundaries leave `user`,
  `userType`, `user_count`, and `username_status` outside this exact-key
  policy. A direct synthetic-value check with `secrets=()` verified all eight
  requested spellings and preserved ordinary diagnostic context.
- Reviewed `test_redacts_unknown_username_key_value_from_exception_text`:
  it supplies no username through `secrets`, exercises all eight spellings,
  removes the synthetic value, emits `<redacted>`, and keeps the non-sensitive
  message context. `test_te40_operation_exception_and_traceback_are_redacted`
  uses an unbound exception username absent from handler credential and other
  secret state; it checks stdout and `command_logger` while also covering the
  synthetic credentials, Session ID, CSRF, cookie, and Authorization value.
- Rechecked the previously closed boundaries through the passing suite and
  focused tests: TE-40 initial Session ID and CSRF handling, status exceptions,
  SIP update/verification exceptions, GUI SIP exception handling, and worker
  error/traceback boundaries. The GUI baseline test confirms `950 x 950`.
  `rg` found exactly one `fix_sip_huawei_te40` and one `on_sip_fix_error`
  definition. Those production areas were not changed after the preceding
  validation apart from the shared text-redaction update.
- `C:\\Users\\Mih\\AppData\\Local\\Programs\\Python\\Python312\\python.exe -m unittest tests.test_redaction.RedactionTests.test_redacts_unknown_username_key_value_from_exception_text`
  — passed: 1 test in 0.000 s.
- `C:\\Users\\Mih\\AppData\\Local\\Programs\\Python\\Python312\\python.exe -m unittest tests.test_redaction`
  — passed: 8 tests in 0.332 s.
- `C:\\Users\\Mih\\AppData\\Local\\Programs\\Python\\Python312\\python.exe -m unittest tests.test_redaction tests.test_credential_propagation tests.test_gui_theme`
  — passed: 25 tests in 0.374 s.
- `C:\\Users\\Mih\\AppData\\Local\\Programs\\Python\\Python312\\python.exe -m unittest discover -s tests -p 'test_*.py'`
  — passed: 61 tests in 0.881 s. This matches the committed report's expected
  full-suite count; it completed as one offline process without live hardware,
  network calls, a real `credentials.local.json`, a Qt crash, or hung threads.
- `..\\openspec.cmd validate externalize-device-credentials --strict` — passed:
  `Change 'externalize-device-credentials' is valid`.
- `git check-ignore -v credentials.local.json` identified the `.gitignore`
  rule; `git ls-files -- credentials.local.json` returned no file;
  `git diff --check` and the post-test `git status --short` were clean. A real
  credential file was neither created nor read.

Tasks 5.1, 5.2, 5.3, 6.8, 6.11, 7.2, and 7.7 are supported by the inspected
implementation and passing checks above. Tasks 7.3, 7.6, and 7.8 remain the
recorded owner decisions and are unchanged. The preceding report's username
finding, test counts, strict-validation assertion, protection assertion, and
absence of Critical/High/Medium findings agree with this independent result.

Findings: none at Critical, High, Medium, or Low severity. The test output
contains existing Python SSL deprecation warnings, but no failure, production
diff, or change-scope issue.

Verdict: **APPROVE**. Archive is permitted by this verdict, but no archive
operation was performed in this session.

The validation record commit is created immediately after this report is
written. Its SHA is necessarily emitted by Git after the commit is created
(a commit cannot contain its own hash); it is recorded in the commit and push
evidence accompanying this report. It is distinct from the validated
implementation SHA above.
