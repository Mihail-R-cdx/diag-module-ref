# Tasks: cloudlink-310-runtime-session-corrections

## 1. Architecture baseline and scope

- [x] Base the change on exact `master` `4b958488bb34b5deae23b2201a947154add8acf8` after reading current `RULES.md`.
- [x] Record sanitized live-read evidence for modern Bar session, exact verified modern reads, meter normalization, sleep/call state, device-local time, and first-HD-AI contradiction.
- [x] Apply corrected common read architecture to exact Bar/Box while preserving distinct identity and credential/profile memory.
- [x] Preserve Box meter `WEB_GetCurrentAudioParam` and keep automatic model detection out of scope.
- [x] Resolve architecture review finding: deterministic list-of-Mapping peripheral version normalization with exact `version` field, source-order de-duplication, `; ` join, and fail-closed partial-malformed policy.
- [x] Resolve architecture review finding: modern action.cgi allowlist limited to live-verified version/MAC/mailbox; unverified audio/line/presentation/camera reads remain legacy-compatible.
- [x] Resolve architecture review finding: CloudLink microphone-gain mutation disabled before network I/O until authoritative target/readback contract exists.

## 2. OpenSpec contract corrections

- [x] Modify `cloudlink-live-microphone-metering` so Bar meter uses modern read context/X-Access-Token while Box retains model-specific source/field set.
- [x] Modify `device-diagnostics-and-control` for one handler generation with modern read plus legacy compatibility/control subcontexts under one application-selected credential.
- [x] Add runtime presentation rules for sleep, deterministic camera/microphone version lists, and built-in labels without using WebUI `--` as protocol authority.
- [x] Modify `request-lifecycle-and-recovery` for exact modern allowlist, legacy compatibility routing, modern sleep/call mappings, no first-HD-AI product authority, and fail-closed gain control.
- [x] Preserve existing `codec-call-log-usage-statistics` device-time semantic contract; implementation must comply rather than weaken it.
- [ ] On the current published architecture HEAD run:
  - [ ] `git diff --check`
  - [ ] `git diff --cached --check`
  - [ ] `.\openspec.cmd validate cloudlink-310-runtime-session-corrections --strict`
  - [ ] `.\openspec.cmd validate --all --strict`
- [ ] Record exact architecture HEAD, current `origin/master`, clean status, commands, exit codes, and exact strict-validation passed/failed counts before architectural `APPROVE`.

## 3. Implement CloudLink session boundaries

- [ ] Re-read `RULES.md`, fetch current remote state, and implement only after architectural `APPROVE` of current published change HEAD.
- [ ] Add modern login `POST /v1/login/session` -> `POST /v1/login/account` using only application-assigned credential.
- [ ] Keep modern cookies/token in memory, send `X-Access-Token`, and use body token only for approved modern action.cgi version/MAC/mailbox reads.
- [ ] Implement best-effort `DELETE /v1/login/session` teardown plus local session closure and secret-safe cleanup.
- [ ] Preserve legacy compatibility/control subcontext for existing unverified audio/line/presentation/camera reads and supported non-gain mutations.
- [ ] Bind both subcontexts to one exact model/IP/credential/generation handler unit; invalidation closes both without handler-owned credential iteration.
- [ ] Preserve exact Bar/Box identity and separate success memory.

## 4. Correct status/state normalization

- [ ] Route only exact approved modern read set through modern context; do not migrate unverified action.cgi reads.
- [ ] Normalize `state.isSleep` exactly `1 -> On`, `0 -> Off`.
- [ ] Normalize case-sensitive `state.callState` exactly `0 No Call`, `1 Calling`, `2 Connected`, `3 Disconnected`; do not reuse legacy lowercase mapper.
- [ ] Stop ordinary status publication from using legacy sleep as authority when accepted modern state exists.
- [ ] Remove first-HD-AI selection as authority for `mic_connection_status`/diagnostic `mic_volume`; add no replacement heuristic.
- [ ] Do not promote `state.camera`, `state.mic`, or `/mic/devices` fields to unapproved physical/gain semantics.
- [ ] Preserve optional-field isolation and required core identity/version gates.

## 5. Version and built-in presentation

- [ ] Require `cameraVersion`/`micVersion` field, when present, to be a list; `[]` means built-in.
- [ ] For non-empty list require every entry to be Mapping with exact non-empty string `version`; ignore `name` for presentation.
- [ ] On any malformed non-empty entry make the whole peripheral version unavailable; do not partially render valid siblings.
- [ ] Strip valid versions, remove duplicates preserving first source order, join with exact `; ` separator.
- [ ] Render built-in camera exactly `Встроенная камера` and built-in microphone exactly `Встроенный микрофон`.
- [ ] Add visible `Режим сна`, `Версия камеры`, `Версия микрофона`; do not parse vendor WebUI `--`.

## 6. Meter, gain and call-history time

- [ ] Run Bar `GET /v1/mediacontrol/mic/current-volume` through modern read context with existing normalization unchanged.
- [ ] Preserve Box `POST action.cgi?ActionID=WEB_GetCurrentAudioParam` and exact approved closed field set.
- [ ] Disable/reject CloudLink Bar/Box microphone-gain control before network I/O; no gain PUT/POST, fixed device IDs, alternate-method fallback, or first-HD-AI reconciliation.
- [ ] Obtain codec-local time from `GET /v1/om/config/systemtime` through modern context and pass as device `reference_now`.
- [ ] Preserve explicit computer-local fallback warning only when device-local time is unavailable after allowed bounded recovery.

## 7. Regression coverage

- [ ] Cover modern login/token/header/body/logout lifecycle and secret redaction.
- [ ] Cover exact modern action.cgi allowlist and legacy routing for unverified audio/line/presentation/camera reads.
- [ ] Cover HTTP 401/403 session invalidation and prove generic HTTP-200 `success: 0` does not authorize fallback.
- [ ] Cover one application-selected credential, no handler iteration, exact Bar/Box identity and separate success memory.
- [ ] Cover Bar meter auth/zero/positive/unavailable and unchanged normalizer; Box source regression.
- [ ] Cover sleep/call enums including 2/3 legacy mismatch.
- [ ] Cover deterministic version-list normalization: empty, one valid, multiple valid, duplicates, missing field, non-list, partial malformed.
- [ ] Cover multiple HD-AI records proving no connection/gain authority.
- [ ] Cover disabled gain control and assert zero device network mutation.
- [ ] Cover codec-local time and explicit system fallback.
- [ ] Cover GUI rows/rebuild/currentness/stale suppression and unresolved manual model fallback.

## 8. Implementation validation and publication

- [ ] Run focused tests for affected handler/session/parser/worker/GUI/call-history modules.
- [ ] Run full required offline test suite and record exact counts/exit code.
- [ ] Run `.\openspec.cmd validate cloudlink-310-runtime-session-corrections --strict`.
- [ ] Run `.\openspec.cmd validate --all --strict`.
- [ ] Run `git diff --check` and `git diff --cached --check`.
- [ ] Review implementation against approved OpenSpec, including no modern migration of unverified reads and no CloudLink gain mutation.
- [ ] Create focused implementation commit and push feature branch; verify local HEAD equals remote without amend/rebase/force-push/history rewrite.
- [ ] Keep PR Draft. Implementation session MUST NOT issue independent final `APPROVE`.

## 9. Independent validation and archive applicability

- [ ] Create separate clean detached worktree from current `origin/agent/cloudlink-310-runtime-session-corrections`; prove detached HEAD equals exact current remote SHA.
- [ ] Recheck current master, PR state/Draft/base/head/remote HEAD/mergeability and inspect newer commits before verdict.
- [ ] Independently repeat focused tests, full offline suite, both strict validations, Git checks, scope/security review, and architecture conformance without fixing findings.
- [ ] Verify local/remote SHA equality again and clean validation worktree.
- [ ] Because change uses `MODIFIED Requirements`, perform disposable archive-applicability check from exact validated remote HEAD and discard disposable output without publication.
- [ ] Do not issue `READY FOR ARCHIVE` with any Critical/High/Medium finding, failed mandatory check, stale/dirty validation worktree, architecture divergence, or unproven archive applicability.

## 10. Archive and completion

- [ ] Begin only after permitting independent verdict on current published feature HEAD.
- [ ] Re-read `RULES.md`, fetch remote state, verify exact feature/master SHAs and PR state before archive.
- [ ] Archive only through `.\openspec.cmd archive cloudlink-310-runtime-session-corrections --yes`.
- [ ] Review archive/root-spec diff, especially modified CloudLink meter, diagnostics/control, and request-lifecycle requirements.
- [ ] Run `.\openspec.cmd validate --all --strict`, full offline suite, `git diff --check`, and `git diff --cached --check` after archive.
- [ ] Create/push dedicated archive commit; verify remote archive HEAD.
- [ ] Issue `READY FOR MERGE` only after post-archive checks pass on exact remote archive HEAD.
- [ ] Do not merge, close PR, or delete branch without explicit user authorization.
