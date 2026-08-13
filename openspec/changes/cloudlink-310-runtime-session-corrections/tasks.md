# Tasks: cloudlink-310-runtime-session-corrections

## 1. Architecture baseline and scope

- [x] Base the change on exact `master` `4b958488bb34b5deae23b2201a947154add8acf8` after reading current `RULES.md`.
- [x] Record the live-read evidence that established the modern Bar session, reviewed read-only endpoint compatibility, meter normalization, sleep/call-state fields, device-local time, and the first-HD-AI contradiction without persisting secrets.
- [x] Apply the corrected common read-session/read-only behavior to exact `CloudLink Bar 310` and exact `CloudLink Box 310` while preserving distinct identity and credential/profile memory.
- [x] Preserve the confirmed exceptions: Box live meter remains `WEB_GetCurrentAudioParam`; state-changing CloudLink operations remain on the existing legacy control path.
- [x] Keep automatic Bar/Box model detection, unproved camera state, and unproved microphone connection/gain semantics out of scope.

## 2. OpenSpec contract corrections

- [x] Modify `cloudlink-live-microphone-metering` so Bar metering uses the modern read context and `X-Access-Token`, while Box retains its existing model-specific meter source/field set.
- [x] Modify `device-diagnostics-and-control` so the shared Bar/Box handler owns modern read and legacy control subcontexts under one application-selected credential and exact model/IP context.
- [x] Add CloudLink runtime presentation rules for `Режим сна`, `Версия камеры`, `Версия микрофона`, `Встроенная камера`, and `Встроенный микрофон` without making GUI text protocol authority.
- [x] Modify `request-lifecycle-and-recovery` to use the modern read status plan, exact modern sleep/call mappings, conservative typed failure handling, and no first-HD-AI product authority.
- [x] Preserve the existing `codec-call-log-usage-statistics` device-time semantic contract; require implementation compliance rather than weakening that root requirement.
- [ ] Run architecture validation on the published architecture HEAD:
  - [ ] `git diff --check`
  - [ ] `git diff --cached --check`
  - [ ] `.\openspec.cmd validate cloudlink-310-runtime-session-corrections --strict`
  - [ ] `.\openspec.cmd validate --all --strict`
- [ ] Record exact architecture HEAD, current `origin/master`, clean status, commands, exit codes, and exact strict-validation passed/failed counts before architectural `APPROVE`.

## 3. Implement the modern CloudLink 310 read context

- [ ] Re-read `RULES.md`, fetch current remote state, and implement only after architectural `APPROVE` of the current published change HEAD.
- [ ] Add the modern read login sequence `POST /v1/login/session` -> `POST /v1/login/account` using only the credential assigned by the application/composition layer.
- [ ] Keep modern cookies and token in memory, send the token as `X-Access-Token`, and use the reviewed modern token body placement for read-only action.cgi requests.
- [ ] Implement best-effort `DELETE /v1/login/session` teardown plus local HTTP-session closure with secret-safe idempotent cleanup.
- [ ] Keep the existing legacy state-changing control path and establish/use it only for operations that already own that contract; do not migrate mutations to the modern context.
- [ ] Bind modern and legacy subcontexts to one exact model/IP/credential/generation handler unit so invalidation closes both without handler-owned credential iteration.
- [ ] Preserve exact Bar/Box identity and separate successful credential/profile memory.

## 4. Correct status/state normalization

- [ ] Route the reviewed common read-only version/MAC/mailbox/general-state path through the modern read context for both exact CloudLink 310 models.
- [ ] Normalize modern `state.isSleep` exactly as `1 -> On`, `0 -> Off`; omit/mark unavailable unsupported values.
- [ ] Normalize case-sensitive modern `state.callState` exactly as `0 No Call`, `1 Calling`, `2 Connected`, `3 Disconnected`; do not reuse the legacy lowercase mapper.
- [ ] Stop ordinary status publication from using the legacy sleep endpoint as authoritative when modern state is available.
- [ ] Remove first-HD-AI selection as authority for `mic_connection_status` and `mic_volume`; do not replace it with another unapproved group/order/gain heuristic.
- [ ] Do not promote `state.camera`, `state.mic`, or unproved `/mic/devices` fields to physical camera/microphone semantics.
- [ ] Preserve optional-field isolation and required core identity/version gates.

## 5. Version and built-in presentation

- [ ] Normalize successful structured `cameraVersion` evidence into usable-version, built-in-empty, or unavailable states.
- [ ] Normalize successful structured `micVersion` evidence into usable-version, built-in-empty, or unavailable states.
- [ ] Render built-in-empty camera exactly as `Встроенная камера` and built-in-empty microphone exactly as `Встроенный микрофон`.
- [ ] Render usable version evidence as the real normalized version and keep absent/malformed endpoint evidence unavailable rather than calling it built-in.
- [ ] Add visible `Режим сна`, `Версия камеры`, and `Версия микрофона` rows for exact Bar/Box contexts without parsing vendor WebUI `--` text.
- [ ] Keep built-in/version presentation separate from camera activity, physical microphone connection, mute, gain, and live signal level.

## 6. Meter and call-history time

- [ ] Run Bar `GET /v1/mediacontrol/mic/current-volume` through the modern read context while leaving the existing normalization algorithm unchanged.
- [ ] Preserve Box `POST action.cgi?ActionID=WEB_GetCurrentAudioParam` and its exact approved closed microphone field set/normalization.
- [ ] Obtain CloudLink codec-local calendar time from `GET /v1/om/config/systemtime` through the modern read context and pass it to call-history normalization as device `reference_now`.
- [ ] Preserve explicit computer-local fallback warning only when reliable device-local time is unavailable after allowed bounded recovery.

## 7. Regression coverage

- [ ] Add focused tests for modern login/token/header/body/logout lifecycle and secret redaction.
- [ ] Cover HTTP 401/403 session invalidation and prove generic HTTP-200 `success: 0` does not authorize credential fallback or string-heuristic session recovery.
- [ ] Cover one application-selected credential, no handler/worker iteration, exact Bar/Box model identity, and separate credential/profile memory.
- [ ] Cover modern read-only action.cgi use while existing state-changing operations remain on the legacy control path.
- [ ] Cover Bar meter auth with raw zero/positive/unavailable samples and unchanged all-entry normalization; cover Box source and closed-field regression.
- [ ] Cover sleep and modern call-state enums, including missing/unsupported fields and the 2/3 legacy-enum mismatch regression.
- [ ] Cover multiple HD-AI records proving list order is not product authority and that no unapproved connection/gain value is manufactured.
- [ ] Cover codec-local device time and explicit system fallback.
- [ ] Cover camera/microphone version, built-in-empty, unavailable, GUI rows, reconstruction, and stale-context suppression.
- [ ] Cover unresolved inventory/manual fallback so no network Bar/Box auto-detection is introduced.

## 8. Implementation validation and publication

- [ ] Run focused tests for all affected handler/session/parser/worker/GUI/call-history modules.
- [ ] Run the full required offline test suite and record exact passed/failed counts and exit code.
- [ ] Run `.\openspec.cmd validate cloudlink-310-runtime-session-corrections --strict`.
- [ ] Run `.\openspec.cmd validate --all --strict`.
- [ ] Run `git diff --check` and `git diff --cached --check`.
- [ ] Review the implementation diff against the approved OpenSpec and confirm no production behavior was added for camera state or microphone gain/connection without an approved contract.
- [ ] Create a focused implementation commit and push `agent/cloudlink-310-runtime-session-corrections`; verify local HEAD equals current remote branch HEAD without amend, rebase, force-push, or history rewrite.
- [ ] Keep the PR Draft. The implementation session MUST NOT issue its own independent final `APPROVE`.

## 9. Independent validation and archive applicability

- [ ] Create a separate clean detached worktree from current `origin/agent/cloudlink-310-runtime-session-corrections`; record the remote SHA and prove detached HEAD equals that exact current remote SHA.
- [ ] Independently inspect current `master`, PR state/Draft/base/head/remote HEAD/mergeability and review every newer feature commit before verdict.
- [ ] Independently repeat focused tests, the full offline suite, both strict OpenSpec validations, `git diff --check`, `git diff --cached --check`, scope/security review, and all material session/meter/status/time/presentation contracts without fixing findings in the validation session.
- [ ] Verify local/remote SHA equality again after validation and confirm the validation worktree remained clean.
- [ ] Because this change uses `MODIFIED Requirements`, perform the required disposable archive-applicability check from the exact validated remote HEAD using only repository-local `openspec.cmd`; inspect the prospective archive/root-spec diff and discard disposable output/worktree without publishing it.
- [ ] Do not issue `READY FOR ARCHIVE` while any Critical, High, or Medium finding remains, any mandatory check fails, validation used a stale/dirty worktree, implementation differs from approved architecture, or archive applicability is unproven.

## 10. Archive and completion

- [ ] Begin only after a permitting independent verdict on the current published feature HEAD.
- [ ] Re-read current `RULES.md`, fetch remote state, and verify exact feature/master SHAs plus PR Draft/base/head/mergeability before archive.
- [ ] Archive only through `.\openspec.cmd archive cloudlink-310-runtime-session-corrections --yes`.
- [ ] Review the archive/root-spec diff, especially modified CloudLink meter, diagnostics/control, and request-lifecycle requirements.
- [ ] Run `.\openspec.cmd validate --all --strict`, the full offline suite, `git diff --check`, and `git diff --cached --check` after archive.
- [ ] Create and push a dedicated archive commit; verify current remote archive HEAD.
- [ ] Issue `READY FOR MERGE` only after post-archive checks pass on the exact remote archive HEAD.
- [ ] Do not merge, close the PR, or delete the branch without explicit user authorization.
