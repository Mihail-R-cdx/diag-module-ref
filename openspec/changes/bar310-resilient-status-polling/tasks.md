# Tasks: bar310-resilient-status-polling

## 1. Confirm implementation baseline

- [ ] Before beginning work, read `RULES.md`.
- [ ] Fetch `origin` and record exact `origin/master`, `origin/agent/bar310-resilient-status-polling`, PR state, Draft state, base/head, merge state, and remote branch HEAD.
- [ ] Read this approved change, the current root `request-lifecycle-and-recovery` specification, `handlers/huawei/bar310.py`, `core/workers/codec_polling.py`, `core/parser.py`, and relevant existing codec lifecycle/security tests.
- [ ] Review every commit newer than the approved architecture HEAD before changing implementation.
- [ ] Confirm the implementation scope is limited to Bar 310 handler/parser/worker behavior, synthetic tests, and implementation evidence required by this change.

## 2. Implement the explicit Bar 310 polling plan

- [ ] Replace ordinary refresh iteration over `command_map` with the exact required and optional read-only plan from `design.md`.
- [ ] Make `get_version` the required core request and require a successful object response with usable software-version evidence before creating canonical model/version fields.
- [ ] Exclude `get_config_default`, `get_config`, every mutation endpoint, and any future command-map-only entry from ordinary status refresh.
- [ ] Implement focused optional collectors for MAC, audio, line/SIP, call, presentation, sleep, camera, and HD-AI microphone state.
- [ ] Preserve valid zero and false values returned by successful endpoints.

## 3. Preserve typed terminal failures and useful partial status

- [ ] Remove the broad `except Exception: return {}` status boundary.
- [ ] Propagate `AuthenticationError`, `SessionInvalidError`, and `ConnectionError` from every collection phase.
- [ ] Raise `CommandError` for an unsuccessful required core response and `ProtocolError` for missing or malformed required core data.
- [ ] Localize only endpoint-specific optional `CommandError` and `ProtocolError` outcomes, omit their owned fields, and preserve already collected observations.
- [ ] Ensure optional failures do not authorize credential fallback and do not restart the handler with another credential.
- [ ] Keep optional diagnostic logs safe and redacted.

## 4. Normalize canonical status without false defaults

- [ ] Add shared pure presentation normalization for `auxOpen -> Start` and `auxClose -> Stop`.
- [ ] Add shared pure sleep normalization for `sleep -> On` and `unsleep -> Off`.
- [ ] Reuse the same helpers in full refresh and interactive readback methods.
- [ ] Omit unavailable presentation, sleep, call, SIP, audio, camera, microphone, and other optional fields rather than manufacturing `Off`, `Stop`, `No Call`, zero, or another semantic state.
- [ ] Preserve current canonical mappings when a successful endpoint actually reports an idle, stopped, muted, false, or zero value.

## 5. Enforce the worker/parser success gate

- [ ] Reject empty, non-mapping, and core-less raw handler payloads before technical metadata is added.
- [ ] Make `HuaweiBar310DataParser` validate core model/version evidence and map only fields present in the canonical handler payload.
- [ ] Add `ip_address` and `connection_profile` only after raw and parsed payload validation succeeds.
- [ ] Emit no result signal for an unusable payload; emit a safe error, disconnect the handler, and emit `finished`.
- [ ] Preserve success result, cleanup, and completion behavior for a usable partial payload.
- [ ] Do not move stale-result acceptance or successful credential/profile persistence out of the application/composition layer.

## 6. Add focused synthetic regression coverage

- [ ] Create `tests/test_bar310_status_polling.py` with fake responses and no production device dependency.
- [ ] Cover the exact polling allowlist and prove configuration and mutation endpoints are not called.
- [ ] Cover required-core success/failure, optional command/protocol isolation, terminal session/transport propagation, and absence of any `{}` fallback.
- [ ] Cover omitted unavailable fields versus observed negative/zero values.
- [ ] Cover presentation and sleep normalization in both polling and interactive readback.
- [ ] Cover empty/non-mapping/core-less worker payload rejection, usable partial success, signal order, cleanup, and redaction.
- [ ] Keep fixtures synthetic and free of real IPs, credentials, tokens, cookies, response bodies, or organization data.

## 7. Validate implementation

- [ ] Run the focused tests with the repository-supported Python interpreter and record the exact result count:

```powershell
<python> -m unittest tests.test_bar310_status_polling -v
```

- [ ] Run the canonical full offline test suite and record exact passed/failed counts:

```powershell
<python> -m unittest discover -s tests -p "test_*.py" -v
```

- [ ] Run repository-local OpenSpec validation only:

```powershell
.\openspec.cmd validate bar310-resilient-status-polling --strict
.\openspec.cmd validate --all --strict
```

- [ ] Run repository-protection and scope checks:

```powershell
git diff --check
git status --short
git diff --stat origin/master...HEAD
git diff --name-only origin/master...HEAD
```

- [ ] Review that no credential file, production data, unrelated handler, GUI redesign, inventory artifact, Graphify output, generated log, or temporary test artifact changed.

## 8. Publish implementation for independent validation

- [ ] Create focused implementation commit(s) and push to `agent/bar310-resilient-status-polling` without amend, rebase, force-push, or history rewrite.
- [ ] Verify local HEAD equals `origin/agent/bar310-resilient-status-polling` after push and the PR remains Draft.
- [ ] Record implementation evidence with exact remote SHA, change base, changed-file scope, commands, exit codes, and test counts.
- [ ] Do not issue final `APPROVE`; request independent validation from a separate clean detached worktree created from the published remote branch HEAD.

## 9. Independent validation and archive applicability

- [ ] Independently repeat the focused test command, full offline test command, both strict OpenSpec validations, `git diff --check`, scope/security review, and local/remote SHA equality in a clean detached worktree from `origin/agent/bar310-resilient-status-polling`.
- [ ] Independently verify typed failure preservation, optional partial-status behavior, worker no-result error path, cleanup, redaction, and no credential-policy regression.
- [ ] Because this change adds root-spec requirements, perform a disposable archive-applicability check outside the feature branch with the repository-local wrapper, inspect the resulting archive/root-spec diff against the then-current root specification, run `validate --all --strict`, and discard the worktree without publishing archive output.
- [ ] Do not issue `READY FOR ARCHIVE` while any Critical, High, or Medium finding remains, any required check fails, the validated remote HEAD changed, the validation worktree was dirty, or archive applicability is unproven.
