# Final technical verification report

## Scope and verified revision

This report covers the remediation applied after the independent validation of
`43297326d242c96b780b2fe8c7c74d5f56fc58a7` returned `CHANGES REQUIRED`.
The verified revision is `HEAD` (the commit containing this report), tested in
a clean clone created from that commit's parent. No real
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
redacted diagnostic context remains present. It uses no network or hardware.

## Commands and actual results

- `C:\\Users\\Mih\\AppData\\Local\\Programs\\Python\\Python312\\python.exe -m unittest tests.test_gui_theme tests.test_redaction`
  passed: 14 tests in 0.319 seconds.
- `C:\\Users\\Mih\\AppData\\Local\\Programs\\Python\\Python312\\python.exe -m unittest tests.test_redaction tests.test_credential_propagation tests.test_gui_theme`
  passed: 24 tests in 0.275 seconds.
- `C:\\Users\\Mih\\AppData\\Local\\Programs\\Python\\Python312\\python.exe -m unittest discover -s tests -p 'test_*.py'`
  passed: 60 tests in 0.750 seconds.

All commands ran as one offline process per command in the clean checkout.
They made no live hardware or network calls, did not read a real local
credential file, and completed without a Qt crash or hung threads. The
different historical counts (53, 56, 59, and 85) were recorded from different
repository states and test selections; this report intentionally records only
the reproducible 60-test result from the verified revision.

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
