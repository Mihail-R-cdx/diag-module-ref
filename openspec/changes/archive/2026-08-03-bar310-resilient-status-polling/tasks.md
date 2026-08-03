# Tasks: bar310-resilient-status-polling

## 1. Confirm implementation baseline

- [x] Before beginning work, read `RULES.md`.
- [x] Fetch `origin` and record exact `origin/master`, `origin/agent/bar310-resilient-status-polling`, PR state, Draft state, base/head, merge state, mergeability, and remote branch HEAD.
- [x] Read this approved change, the current root `request-lifecycle-and-recovery` specification, `handlers/huawei/bar310.py`, `core/workers/codec_polling.py`, `core/workers/common.py`, `core/exceptions.py`, `core/parser.py`, and relevant existing codec lifecycle/security tests.
- [x] Review every commit newer than the approved architecture HEAD before changing implementation.
- [x] Confirm the implementation scope is limited to Bar 310 handler/parser/worker behavior, synthetic tests, and implementation evidence required by this change. Do not change failure-category names or generic classifier behavior unless current source contradicts the approved `ProtocolError`/`ParseError -> protocol_error` contract.

## 2. Implement the explicit Bar 310 polling plan and exact core gate

- [x] Replace ordinary refresh iteration over `command_map` with the exact required and optional read-only plan from `design.md`.
- [x] Make `get_version` the only required core request.
- [x] Require the outer version response to be a Mapping with `success == 1` and Mapping `data`.
- [x] Read software version only from exact key `data["softVersion"]`.
- [x] Require `softVersion` to be a string whose `strip()` result is non-empty and whose casefolded value is not `unknown`.
- [x] Set handler `model` exactly to `Huawei CloudLink Bar 310` and handler `version` exactly to stripped `softVersion`.
- [x] Do not accept another version key, `Unknown`, `N/A`, an empty string, response model text, or another manufactured default as core evidence.
- [x] Populate optional `serial_number` only from observed `data["lisence"]` and optional `mic_version` only from observed `data["micVersion"]`; omit absent values.
- [x] Exclude `get_config_default`, `get_config`, every mutation endpoint, and any future command-map-only entry from ordinary status refresh.

## 3. Implement closed endpoint field ownership and precedence

- [x] Implement focused optional collectors with the exact ownership table from `design.md`:

```text
get_mac           -> mac_address
get_audio_status  -> mic_mute, speaker_mute, speaker_volume
get_line_state    -> uptime, sip_server, sip_number, primary sip_status
get_call_status   -> call_status, fallback sip_status only
get_presentation  -> presentation
get_sleep_mode    -> sleep_mode
get_camera_status -> camera_status
HD-AI endpoint    -> mic_connection_status, mic_volume
```

- [x] For MAC, use first non-empty `system_wanMAC_addr`, then `system_lanMAC_addr`; otherwise omit the field.
- [x] Make line-state SIP authoritative. Use call `state.sip` only when line-state produced no valid `sip_status`; never overwrite line evidence and preserve line value on conflict.
- [x] Map camera only from `localInMainSource == 255 -> On` and `0 -> Off`; treat missing/unsupported values as endpoint-local `ProtocolError` and omit camera status.
- [x] For HD-AI, require Mapping data and list `deviceList`, filter Mapping entries with `groupName == "HD-AI"`, preserve source order, and select the first matching entry.
- [x] Treat a successful empty HD-AI list as observed `Микрофон не подключён` with no microphone volume.
- [x] Treat `plugStatus == 0` as disconnected with no volume.
- [x] Treat `plugStatus == 1` as connected and publish observed `gainVolume`, including numeric zero.
- [x] Treat malformed `deviceList`, unsupported/missing `plugStatus`, or connected missing/`None` gain as endpoint-local `ProtocolError` and omit both microphone fields.
- [x] Ensure endpoint failure or absence cannot delete or manufacture fields owned by another endpoint.

## 4. Preserve typed terminal failures and useful partial status

- [x] Remove the broad `except Exception: return {}` status boundary.
- [x] Propagate `AuthenticationError`, `SessionInvalidError`, and `ConnectionError` from every collection phase.
- [x] Raise `CommandError` for an unsuccessful required core response.
- [x] Raise `ProtocolError` for missing/non-Mapping core data, missing `softVersion`, `None`, non-string, empty, whitespace-only, or `Unknown` software-version evidence.
- [x] Localize only endpoint-specific optional `CommandError` and `ProtocolError` outcomes, omit their owned fields, and preserve already collected observations.
- [x] Ensure optional failures do not authorize credential fallback and do not restart the handler with another credential.
- [x] Keep optional diagnostic logs safe and redacted.

## 5. Normalize canonical status without false defaults

- [x] Add shared pure presentation normalization for `auxOpen -> Start` and `auxClose -> Stop`.
- [x] Add shared pure sleep normalization for `sleep -> On` and `unsleep -> Off`.
- [x] Reuse the same helpers in full refresh and interactive readback methods.
- [x] Omit unavailable presentation, sleep, call, SIP, audio, camera, microphone, and other optional fields rather than manufacturing `Off`, `Stop`, `No Call`, `Подключена`, `Микрофон не подключён`, zero, or another semantic state.
- [x] Preserve current canonical mappings when a successful endpoint actually reports an idle, stopped, muted, disconnected, false, or zero value.
- [x] Remove unconditional parser camera output and every parser default that turns an absent optional field into an observed state.

## 6. Enforce exact parser and worker protocol gates

- [x] Make `HuaweiBar310DataParser` require raw Mapping `model == "Huawei CloudLink Bar 310"` and a non-empty string `version` that is not `Unknown`.
- [x] Emit exact required parser fields without defaults:

```text
"Модель" == "Huawei CloudLink Bar 310"
"Версия ПО" is non-empty and derived from raw_data["version"]
```

- [x] Raise `ParseError` when parser core model/version evidence or required display fields are missing, different, non-string, empty, `Unknown`, or become empty after display cleanup.
- [x] Map only optional fields present in the canonical handler payload and preserve valid zero/false values.
- [x] In `HuaweiBar310Worker`, raise `ProtocolError` for empty, non-Mapping, core-less, wrong-model, unusable-version, or metadata-only raw handler payloads before technical metadata is added.
- [x] Add `ip_address` and `connection_profile` only after raw and parsed payload validation succeeds.
- [x] Route raw `ProtocolError` and parser `ParseError` through `_emit_error(..., None, error)` or an equivalent typed path so exact emitted category is `protocol_error`.
- [x] Do not use `ValueError`, a generic exception, an explicit `connection_error`, or another transport category for unusable raw/parser payloads.
- [x] Emit no result signal for an unusable payload; emit `protocol_error`, disconnect the handler, and emit `finished`.
- [x] Preserve success result, cleanup, and completion behavior for a usable partial payload.
- [x] Do not move stale-result acceptance or successful credential/profile persistence out of the application/composition layer.

## 7. Add focused synthetic regression coverage

- [x] Create `tests/test_bar310_status_polling.py` with fake responses and no production device dependency.
- [x] Cover the exact polling allowlist and prove configuration and mutation endpoints are not called.
- [x] Cover exact core source key `softVersion`, exact handler model string, and exact stripped version.
- [x] Cover missing `softVersion`, another version key only, `None`, non-string, empty, whitespace-only, and case-insensitive `Unknown`; each must raise `ProtocolError`.
- [x] Prove that parser emits exact `Модель` and non-empty derived `Версия ПО` without defaults.
- [x] Cover parser missing/wrong model, missing/non-string/empty/`Unknown` version, and version emptied by display cleanup; each must raise `ParseError`.
- [x] Cover required-core success/failure, optional command/protocol isolation, terminal session/transport propagation, and absence of any `{}` fallback.
- [x] Cover endpoint ownership so one endpoint failure cannot remove another endpoint's observations.
- [x] Cover line/call SIP agreement, call fallback when line SIP is unavailable, and line-wins conflict behavior.
- [x] Cover successful empty HD-AI list, malformed `deviceList`, `plugStatus == 0`, connected missing gain, and connected `gainVolume == 0`.
- [x] Cover unavailable camera endpoint, observed disconnected camera (`0`), observed connected camera (`255`), and unsupported camera value.
- [x] Cover omitted unavailable fields versus observed negative/zero values in both handler and parser results.
- [x] Cover presentation and sleep normalization in both polling and interactive readback.
- [x] Cover empty/non-Mapping/core-less/wrong-model/metadata-only worker payload rejection as `ProtocolError` with exact error category `protocol_error` and no result.
- [x] Cover parser `ParseError` reaching exact worker category `protocol_error` and no result.
- [x] Cover usable partial success, signal order, cleanup, and redaction.
- [x] Keep fixtures synthetic and free of real IPs, credentials, tokens, cookies, response bodies, or organization data.

## 8. Validate implementation

- [x] Run the focused tests with the repository-supported Python interpreter and record the exact result count:

```powershell
<python> -m unittest tests.test_bar310_status_polling -v
```

- [x] Run the canonical full offline test suite and record exact passed/failed counts:

```powershell
<python> -m unittest discover -s tests -p "test_*.py" -v
```

- [x] Run repository-local OpenSpec validation only:

```powershell
.\openspec.cmd validate bar310-resilient-status-polling --strict
.\openspec.cmd validate --all --strict
```

- [x] Run repository-protection and scope checks:

```powershell
git diff --check
git status --short
git diff --stat origin/master...HEAD
git diff --name-only origin/master...HEAD
```

- [x] Review that no credential file, production data, unrelated handler, GUI redesign, inventory artifact, Graphify output, generated log, or temporary test artifact changed.

## 9. Publish implementation for independent validation

- [ ] Create focused implementation commit(s) and push to `agent/bar310-resilient-status-polling` without amend, rebase, force-push, or history rewrite.
- [ ] Verify local HEAD equals `origin/agent/bar310-resilient-status-polling` after push and the PR remains Draft.
- [ ] Record implementation evidence with exact remote SHA, change base, changed-file scope, commands, exit codes, and test counts.
- [ ] Do not issue final `APPROVE`; request independent validation from a separate clean detached worktree created from the published remote branch HEAD.

## 10. Independent validation and archive applicability

- [ ] Independently repeat the focused test command, full offline test command, both strict OpenSpec validations, `git diff --check`, scope/security review, and local/remote SHA equality in a clean detached worktree from `origin/agent/bar310-resilient-status-polling`.
- [ ] Independently verify the exact core source/model/version gate, closed field ownership, SIP precedence, HD-AI/camera unavailable-versus-observed semantics, typed terminal failures, partial-status behavior, exact `protocol_error` worker rejection, cleanup, redaction, and no credential-policy regression.
- [ ] Because this change adds root-spec requirements, perform a disposable archive-applicability check outside the feature branch with the repository-local wrapper, inspect the resulting archive/root-spec diff against the then-current root specification, run `validate --all --strict`, and discard the worktree without publishing archive output.
- [ ] Do not issue `READY FOR ARCHIVE` while any Critical, High, or Medium finding remains, any required check fails, the validated remote HEAD changed, the validation worktree was dirty, or archive applicability is unproven.
