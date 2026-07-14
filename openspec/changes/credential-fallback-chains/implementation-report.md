## Implementation Evidence

This is an implementation-session record, not an independent validation
verdict. It does not approve, archive, merge, or delete the change.

### Delivered behavior

- `CredentialProvider` supports ordered candidates while existing providers
  that only implement `resolve()` remain usable.
- `JsonCredentialProvider` accepts a device mapping as either one profile name
  or a non-empty ordered list. It validates every name and referenced profile
  before returning any candidate; no fixed chain length exists.
- GUI composition converts all candidates through `as_handler_kwargs()` and
  supplies them to the existing retry state. Existing per-device/IP successful
  index handling remains in use.
- The example configuration contains a legacy string mapping and a five-entry
  synthetic fallback chain.

### Test evidence

- `C:\\Users\\Mih\\AppData\\Local\\Programs\\Python\\Python312\\python.exe -m unittest tests.test_credentials tests.test_credential_propagation`
  - 24 tests passed; no skips or failures.
- `C:\\Users\\Mih\\AppData\\Local\\Programs\\Python\\Python312\\python.exe -m unittest tests.test_credential_fallback_retry`
  - 3 tests passed; no skips or failures.
- `C:\\Users\\Mih\\AppData\\Local\\Programs\\Python\\Python312\\python.exe -m unittest discover -s tests -p "test_*.py"`
  - 105 tests passed; no skips or failures.
- `./openspec.cmd validate credential-fallback-chains --strict`
  - passed.
- `./openspec.cmd validate --all --strict`
  - 7 items passed, 0 failed.
- `git diff --check`
  - passed.
- `git check-ignore credentials.local.json`
  - confirmed ignored; the file was not created (`Test-Path` returned `False`)
    and is not tracked.

### Environment notes

`python` and `node` were not available on the default PATH. The repository
supported Python 3.12 and the supplied pinned Node 20.19.0 were used directly.
`npm ci` restored the pinned OpenSpec dependencies; `node_modules` remains
ignored, and the temporary wrapper junction was removed before Git checks.

### Remaining verification

An independent validation session must fetch the published branch, create a
clean detached worktree from its remote SHA, rerun the required checks, and
record its own verdict. No `APPROVE` is issued here.
