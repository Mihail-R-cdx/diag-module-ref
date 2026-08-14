# Tasks: cloudlink-310-runtime-session-corrections

## 1. Architecture baseline and scope

- [x] Base the change on exact `master` `4b958488bb34b5deae23b2201a947154add8acf8` after reading current `RULES.md`.
- [x] Record sanitized live-read evidence for modern Bar session, exact verified modern reads, meter normalization, sleep/call state, device-local time, and first-HD-AI contradiction.
- [x] Apply corrected common read architecture to exact Bar/Box while preserving distinct identity and credential/profile memory.
- [x] Preserve Box meter `WEB_GetCurrentAudioParam` and keep automatic model detection out of scope.
- [x] Resolve architecture review finding: deterministic list-of-Mapping peripheral version normalization with exact `version` field, source-order de-duplication, `; ` join, and fail-closed partial-malformed policy.
- [x] Resolve architecture review finding: modern action.cgi allowlist limited to live-verified version/MAC/mailbox; unverified audio/line/presentation/camera reads remain legacy-compatible.
- [x] Resolve architecture review finding: CloudLink microphone-gain mutation disabled before network I/O until authoritative target/readback contract exists.
- [x] Resolve refinement finding: Box meter remains on the existing legacy compatibility subcontext and is excluded from the modern action.cgi allowlist.
- [x] Resolve refinement finding: preserve MAC WAN→LAN fallback, line-state-primary/mailbox SIP fallback precedence, and legacy camera 255/0 mapping across the MODIFIED requirement.
- [x] Resolve refinement finding: retain mailbox ownership as SIP fallback while modern `/v1/login/status` owns call status and sleep.
- [x] Resolve refinement finding: preserve presentation `auxOpen/auxClose` normalization and ordinary/interactive parity; make modern `state.isSleep` the read authority while Wake remains legacy mutation.

## 2. OpenSpec contract corrections

- [x] Modify `cloudlink-live-microphone-metering` so Bar meter uses modern read context/X-Access-Token while Box keeps `WEB_GetCurrentAudioParam`, its closed field set, and legacy compatibility context.
- [x] Reconcile the meter MODIFIED requirement with archived scenarios for shared modern Bar session reuse, typed rejection, sparse/reordered identifiers, and Box non-microphone exclusion; no meter-specific credential flow is introduced.
- [x] Reconcile the interactive-session MODIFIED requirement with archived exact Bar/Box scenarios while retaining modern-read and legacy compatibility/control subcontexts.
- [x] Reconcile the polling MODIFIED requirement with archived command-map, optional-presentation, typed session, and transport-failure scenarios.
- [x] Reconcile archived SIP, HD-AI, and camera scenarios to the approved source-precedence and no-HD-AI-authority contract.
- [x] Modify `device-diagnostics-and-control` for one handler generation with modern read plus legacy compatibility/control subcontexts under one application-selected credential, including explicit Box meter legacy routing.
- [x] Add runtime presentation rules for sleep, deterministic camera/microphone version lists, and built-in labels without using WebUI `--` as protocol authority.
- [x] Modify `request-lifecycle-and-recovery` for exact modern allowlist, Box-meter legacy exception, preserved MAC/SIP/camera/presentation semantics, modern sleep/call mappings, no first-HD-AI product authority, and fail-closed gain control.
- [x] Preserve existing `codec-call-log-usage-statistics` device-time semantic contract; implementation must comply rather than weaken it.
- [ ] On the current published architecture HEAD run:
  - [ ] `git diff --check`
  - [ ] `git diff --cached --check`
  - [ ] `.\openspec.cmd validate cloudlink-310-runtime-session-corrections --strict`
  - [ ] `.\openspec.cmd validate --all --strict`
- [ ] Record exact architecture HEAD, current `origin/master`, clean status, commands, exit codes, and exact strict-validation passed/failed counts before architectural `APPROVE`.

## 3. Implement CloudLink session boundaries

- [x] Re-read `RULES.md`, fetch current remote state, and implement only after architectural `APPROVE` of current published change HEAD.
- [x] Add modern login `/v1/login/session` -> `/v1/login/account` using only application-assigned credential.
- [x] Keep modern cookies/token in memory, send `X-Access-Token`, and use body token only for approved modern action.cgi version/MAC/mailbox reads.
- [x] Implement best-effort modern logout plus local session closure and secret-safe cleanup.
- [x] Preserve legacy compatibility/control subcontext for existing unverified audio/line/presentation/camera reads, Box meter, and supported non-gain mutations.
- [x] Bind both subcontexts to one exact model/IP/credential/generation handler unit; invalidation closes both without handler-owned credential iteration.
- [x] Preserve exact Bar/Box identity and separate success memory.

## 4. Correct status/state normalization

- [x] Route only exact approved modern read set through modern context; do not migrate unverified action.cgi reads or Box meter.
- [x] Preserve MAC selection: first non-empty `system_wanMAC_addr`, then `system_lanMAC_addr`.
- [x] Preserve line-state SIP as primary and mailbox `state.sip` 1/0 as fallback only when line-state has no valid SIP observation.
- [x] Normalize `state.isSleep` exactly `1 -> On`, `0 -> Off` for ordinary status and interactive sleep readback; keep Wake on legacy mutation path.
- [x] Normalize case-sensitive `state.callState` exactly `0 No Call`, `1 Calling`, `2 Connected`, `3 Disconnected`; do not reuse legacy lowercase mapper.
- [x] Preserve legacy camera mapping `localInMainSource == 255 -> On`, `0 -> Off`; do not use `state.camera` as replacement.
- [x] Preserve presentation mapping `auxOpen -> Start`, `auxClose -> Stop` identically for ordinary status and interactive readback.
- [x] Remove first-HD-AI selection as authority for `mic_connection_status`/diagnostic `mic_volume`; add no replacement heuristic.
- [x] Do not promote `state.camera`, `state.mic`, or `/mic/devices` fields to unapproved physical/gain semantics.
- [x] Preserve optional-field isolation and required core identity/version gates.

## 5. Version and built-in presentation

- [x] Require `cameraVersion`/`micVersion` field, when present, to be a list; `[]` means built-in.
- [x] For non-empty list require every entry to be Mapping with exact non-empty string `version`; ignore `name` for presentation.
- [x] On any malformed non-empty entry make the whole peripheral version unavailable; do not partially render valid siblings.
- [x] Strip valid versions, remove duplicates preserving first source order, join with exact `; ` separator.
- [x] Render built-in camera exactly `Встроенная камера` and built-in microphone exactly `Встроенный микрофон`.
- [x] Add visible `Режим сна`, `Версия камеры`, `Версия микрофона`; do not parse vendor WebUI `--`.

## 6. Meter, gain and call-history time

- [x] Run Bar `GET /v1/mediacontrol/mic/current-volume` through modern read context with existing normalization unchanged.
- [x] Preserve Box `POST action.cgi?ActionID=WEB_GetCurrentAudioParam`, exact approved closed field set, and existing legacy compatibility subcontext.
- [x] Disable/reject CloudLink Bar/Box microphone-gain control before network I/O; no gain PUT/POST, fixed device IDs, alternate-method fallback, or first-HD-AI reconciliation.
- [x] Obtain codec-local time from `GET /v1/om/config/systemtime` through modern context and pass as device `reference_now`.
- [x] Preserve explicit computer-local fallback warning only when device-local time is unavailable after allowed bounded recovery.

## 7. Regression coverage

- [x] Cover modern login/token/header/body/logout lifecycle and secret redaction.
- [x] Cover exact modern action.cgi allowlist and legacy routing for unverified audio/line/presentation/camera reads plus Box meter.
- [x] Cover MAC WAN→LAN fallback and line-state-primary/mailbox SIP fallback precedence.
- [x] Cover legacy camera `255/0` mapping and prove `state.camera` is not canonical authority.
- [x] Cover presentation `auxOpen/auxClose` mapping and ordinary/interactive readback parity.
- [x] Cover modern sleep ordinary/interactive parity while Wake remains on legacy mutation path.
- [x] Cover HTTP 401/403 session invalidation and prove generic HTTP-200 `success: 0` does not authorize fallback.
- [x] Cover one application-selected credential, no handler iteration, exact Bar/Box identity and separate success memory.
- [x] Cover Bar meter auth/zero/positive/unavailable and unchanged normalizer; Box meter source/context regression.
- [x] Cover sleep/call enums including 2/3 legacy mismatch.
- [x] Cover deterministic version-list normalization: empty, one valid, multiple valid, duplicates, missing field, non-list, partial malformed.
- [x] Cover multiple HD-AI records proving no connection/gain authority.
- [x] Cover disabled gain control and assert zero device network mutation.
- [x] Cover codec-local time and explicit system fallback.
- [x] Cover GUI rows/rebuild/currentness/stale suppression and unresolved manual model fallback.
- [x] Resolve corrective review findings: isolate malformed optional presentation and modern sleep/call observations without swallowing terminal typed failures.
- [x] Resolve corrective review finding: classify Bar call-history HTTP/app/protocol/transport failures with their approved typed exception categories.

## 8. Implementation validation and publication

- [x] Run focused tests for affected handler/session/parser/worker/GUI/call-history modules.
- [x] Run full required offline test suite and record exact counts/exit code.
- [x] Run `.\openspec.cmd validate cloudlink-310-runtime-session-corrections --strict`.
- [x] Run `.\openspec.cmd validate --all --strict`.
- [x] Run `git diff --check` and `git diff --cached --check`.
- [x] Review implementation against approved OpenSpec, including no modern migration of unverified reads/Box meter and no CloudLink gain mutation.
- [x] Create focused implementation commit and push feature branch; verify local HEAD equals remote without amend/rebase/force-push/history rewrite.
- [x] Keep PR Draft. Implementation session MUST NOT issue independent final `APPROVE`.

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
