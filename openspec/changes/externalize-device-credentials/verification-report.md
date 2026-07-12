# Intermediate verification report

## Scope

This report covers the in-progress local-JSON credential migration. It does
not include a real `credentials.local.json` file and does not disclose any
credential values.

## Results

- Strict OpenSpec validation: passed (`openspec validate
  externalize-device-credentials --strict`).
- Focused credential, propagation, redaction, hardware-log, and GUI
  composition tests: passed (35 tests).
- The required single-process offline discovery suite passed: 75 tests.
  The command used the installed Python 3.12 executable because `python` is
  not on PATH in this environment; no live hardware or local credential file
  was used.
- The prior Qt exit `0xC0000409` was traced to a GUI test that closed a window
  without processing its deferred deletion. The test now calls `deleteLater`,
  processes `QEvent.DeferredDelete`, and then processes the event queue.
- `credentials.local.json` does not exist in the worktree and Git confirms
  that the path would be ignored.

## Remaining work

OpenSpec tasks 7.3, 7.6, and 7.8 remain unchecked. Manual GUI verification
requires an opt-in interactive run; history/rotation requires incident
approval; and the future secure-provider change is deliberately deferred.
