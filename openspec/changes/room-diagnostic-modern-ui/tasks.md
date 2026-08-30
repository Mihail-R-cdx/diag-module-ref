## 1. Architecture and validation

- [x] 1.1 Capture the approved foundation product decisions: IP-or-room search, direct `room_id` authority, room/network upper cards, common accordion row, reuse of current room-mode exact-row device-family presentations, disabled/non-actionable unauthorized common actions, dark/light toggle, and application title.
- [x] 1.2 Confirm current `master`, current `RULES.md`, inventory runbook, relevant root specs, and current GUI/inventory boundaries before authoring the change.
- [x] 1.3 Re-review the narrowed foundation architecture against current `master` and resolve all CRITICAL/HIGH/MEDIUM findings without changing production code. (Completed in the foundation architecture review; the resulting implementation findings were resolved before `00c0a01` and no CRITICAL/HIGH/MEDIUM findings remain.)
- [x] 1.4 Run repository-local architecture validation on the current published foundation architecture HEAD:

```powershell
.\openspec.cmd validate room-diagnostic-modern-ui --strict
.\openspec.cmd validate --all --strict
git diff --check
git diff --cached --check
```

  Evidence (2026-08-30, `46fa8b8`): change validation exit 0; all strict validation exit 0 (17 passed, 0 failed); `git diff --check` exit 0; `git diff --cached --check` exit 0.

- [x] 1.5 Record exact branch/base/HEAD and fresh validation exit codes/counts before the new architectural `APPROVE`; the previous approval from the larger scope does not carry over automatically after this scope reduction. (2026-08-30: branch `agent/room-diagnostic-modern-ui`; `origin/master` `7e9fd4720d682c232e69179df7cc825afd29bd1d`; validated HEAD `46fa8b86e8665d1764a55fdb8b4e01b54713e7f3`; focused suite exit 0, 267 tests in 37.938s; full suite exit 0, 806 tests in 95.240s; validation exit codes recorded in 1.4.)

## 2. Target search and inventory query

- [x] 2.1 Add an immutable room-name search projection/query to `EquipmentInventory` without changing canonical schema v4.
- [x] 2.2 Cover Unicode NFC/trim/casefold substring matching, room-id deduplication, conflicting names inside one room ID, zero/one/many matches, and deterministic result ordering.
- [x] 2.3 Derive deterministic room result labels from canonical display name plus first usable room address; when distinct room IDs still collide, append a neutral deterministic display-only `Вариант N` discriminator without exposing it as identity.
- [x] 2.4 Replace permanent IP-only input composition with IP-or-room target classification while preserving the operator's raw query text.
- [x] 2.5 Implement autocomplete/dropdown selection for multi-match room queries plus a separate visible selected-room cue; typing and selection alone must perform zero device network I/O.
- [x] 2.6 Ensure editing the raw query clears the selected-room cue, invalidates stale selection/current room authority, and increments request/currentness generation before replacement I/O.
- [x] 2.7 Keep valid-inventory IP zero/one/many/unmapped semantics unchanged and preserve legacy supported no-room single-device behavior.
- [x] 2.8 Preserve unavailable-inventory IP diagnostic fallback exactly: diagnostic start automatically opens the existing fail-closed model fallback and requires a new explicit model selection + `Подключиться` confirmation.
- [x] 2.9 Keep room-name search fail-closed when inventory is unavailable; do not invoke diagnostic or credential fallback for a room-name query.
- [x] 2.10 Preserve `Пароль` behavior: valid inventory resolves only one exact supported IP/model; unavailable inventory may use the existing explicit credential-configuration fallback; valid-inventory zero/many/unmapped and room-name contexts do not gain fallback.

## 3. Direct room-name session composition

- [x] 3.1 Allow room session construction with an exact selected `room_id` and no source record.
- [x] 3.2 Preserve IP-entry source-first membership ordering; use pure canonical `record_id` ordering for direct room-name entry.
- [x] 3.3 Preserve same-room duplicate-IP ambiguity, row eligibility, exact-model registry authority, credential planning, one-shot adapter boundaries, and strictly sequential automatic I/O.
- [x] 3.4 Resolve shared room name/address/VIP source-first for IP entry and canonical-first for source-less room entry.
- [x] 3.5 Verify selected room authority remains bound to current inventory snapshot/query revision and repeated Refresh uses only the room identified by the visible current-selection cue while that selection remains current.
- [x] 3.6 Implement the approved two-branch top full Refresh contract: IP mode re-resolves the current IP; room-name mode recomputes candidates/revalidates current selection; failed re-resolution does not resurrect the previous room tree/cache/selection.
- [x] 3.7 Preserve deterministic accordion initialization: IP mode keeps source-row behavior; source-less room-name mode starts fully collapsed; full Refresh clears old selection and reapplies the new entry-mode rule.

## 4. Application shell and themes

- [x] 4.1 Set the user-visible window title to `Диагностический модуль`.
- [x] 4.2 Build the top toolbar/search layout using semantic components with baseline control height `44-56 px`; search + selection cue should consume roughly 45-60% of baseline toolbar width.
- [x] 4.3 Extend central theme tokens to dark and light palettes without per-widget persistence logic.
- [x] 4.4 Start every process in dark mode and add a sun/moon session-only theme toggle.
- [x] 4.5 Prove theme switching does not change target context, room generation, credentials, live/session ownership, device I/O, or materially reflow the common toolbar/upper-card/equipment-row geometry at a fixed window size.
- [x] 4.6 Keep reused current room-mode device-family expanded content readable/usable in both themes as a compatibility requirement, without substituting standalone screens or redesigning family-specific layout.

## 5. Room upper presentation

- [x] 5.1 Implement the upper-left room card with room name, address, VIP, warranty, and occupancy rows.
- [x] 5.2 Keep warranty explicitly unimplemented as data in this change and render `Гарантия: Нет данных`; do not infer warranty or change inventory schema for it.
- [x] 5.3 Extend the existing unified exact `DiagnosticDispatchEntry`/application model registration (or equivalent single registry) with a call-activity normalization binding. The current baseline codec entries `Huawei TE20`, `Huawei TE40`, `CloudLink Bar 310`, `CloudLink Box 310`, and `Polycom RPG 310` SHALL each declare an available binding because their approved diagnostic snapshots expose call-state evidence. Do not introduce `OCCUPANCY_SUPPORTED_MODELS` or another parallel model list; startup/composition validation must fail closed if any required exact entry lacks its binding.
- [x] 5.4 Implement model-neutral application-owned `CallActivity.ACTIVE / INACTIVE / UNKNOWN` normalization behind those exact registry bindings. Model-specific parser/adapter normalization may use explicit exact-model mappings from existing protocol/normalized evidence, but shared room/GUI code must not parse localized/protocol strings or use substring heuristics; unrecognized/missing/stale evidence becomes `UNKNOWN`.
- [x] 5.5 Derive `Занятость` only from current non-stale typed activity already owned by exact room codec rows: any current `ACTIVE` -> `Занято`; every other case, including all `INACTIVE`, -> `Нет данных`. Do not display `Свободно` in this change and do not add an occupancy-specific network poll, worker, timer, handler/session acquisition, credential flow, or booking/calendar source.
- [x] 5.6 Add a local hover tooltip/popup on the occupancy row/value with meaning equivalent to `Занятость определяется по текущему состоянию звонка кодека.`; opening it must perform zero device I/O.
- [x] 5.7 If a room-card refresh icon is included, wire it only as an alias of top full Refresh. (N/A: the room card has no refresh icon.)
- [x] 5.8 Implement the upper-right network-connections tree with peer width to the room card at baseline (`0.9:1` to `1.1:1`).
- [x] 5.9 Preserve canonical network evidence for all states: known switch IP+known port; known switch IP+missing port; missing switch IP+known port. Unknown-switch/known-port evidence must render under a record-bound `Коммутатор не определён` branch and must not be grouped into invented switch identity.
- [x] 5.10 Populate known-switch parent `Порт` as a deterministic display summary of child attachment evidence: collect non-null child ports in canonical child order, de-duplicate by first occurrence, render zero as `Нет данных`, one as the exact port, many as comma-separated exact ports. Keep exact port/no-data on every child and never treat parent summary as canonical switch state.
- [x] 5.11 If no switch/port evidence exists, render `Нет данных о сетевых подключениях`.
- [x] 5.12 Do not implement or fabricate `Нет подключенных устройств` in this change. This is an explicit product decision; a future approved room-level switch inventory source/schema is required before unattached switches become data-driven.

## 6. Common equipment accordion foundation

- [x] 6.1 Standardize room row headers as `chevron -> 48 x 48 px class icon -> model -> status cue/text -> IP -> overflow`, baseline collapsed height `52-64 px`, with non-color status cues.
- [x] 6.2 Preserve one-expanded-row accordion behavior, exact-row presentation binding, and queue-order independence from accordion selection.
- [x] 6.3 Integrate the current **room-mode exact-row** Audio DSP, Matrix/IN1804, codec, and PDU presentation/interaction surfaces into the common accordion using only the minimum wrapper/reparenting/theme compatibility required. Do not substitute a standalone/single-device screen merely because it belongs to the same family, and do not redesign family-specific internal layout in this change.
- [x] 6.4 Preserve only application intents/capabilities already present in the current room-mode surface and declared by the unified exact-model registry/current room lifecycle. Matrix keeps its current room live/local-refresh behavior and remains read-only for routing; PDU mutation/reconciliation, codec live/auxiliary operations, and Audio DSP live/meter acquisition retain their existing room-mode gates. Do not promote standalone-only controls/signals/capabilities or give any reused widget direct handler/session/network ownership.
- [x] 6.5 Keep overflow/common actions disabled or non-actionable when the current lifecycle does not authorize an action. Do not add new screen-specific gain/mute/reboot/card/table/meter placeholder controls solely to match deferred family redesign references.
- [x] 6.6 Treat any Audio DSP segmented-meter redesign, Matrix column-layout or interactive room-routing redesign, codec grouped-card redesign, or PDU grouped-card/outlet redesign as out of scope and leave it for a later dedicated OpenSpec change.

## 7. Regression coverage

- [x] 7.1 Test raw search text remains unchanged after IP resolution, single room-name resolution, multi-result selection, diagnostics, and top Refresh.
- [x] 7.2 Test duplicate room names across distinct room IDs produce distinguishable deterministic labels, explicit selection maps to one exact room ID, the selected-room cue remains visible, and repeated Refresh uses only that current selection.
- [x] 7.3 Test room-name zero/one/many resolution and selection currentness with zero device I/O before Enter/top Refresh.
- [x] 7.4 Test direct room-name entry creates no synthetic source record and uses canonical row ordering.
- [x] 7.5 Test IP entry still opens the complete room and retains source-first ordering.
- [x] 7.6 Regression-test unavailable-inventory IP diagnostic start automatically opens existing model fallback and that `Пароль` retains unavailable-inventory credential-configuration fallback; valid-inventory zero/many/unmapped remains no-fallback.
- [x] 7.7 Test the complete target-search lock/supersession migration: active automatic room cycle disables target-search editing; editing in allowed idle/live state invalidates current room authority; active/retiring Local Refresh disables target-search editing; active/retiring `AUXILIARY_READ` disables target-search editing while top full Refresh remains the approved supersession action where specified; confirmed mutation/reconciliation keeps target-search locked; raw search/initial source IP never substitutes for the exact expanded-row target.
- [x] 7.8 Test Full Refresh for both entry modes, including stale room-name selection invalidation, no old-tree resurrection after failed re-resolution, and source-less fully-collapsed accordion reset.
- [x] 7.9 Test common row statuses remain understandable without color alone and one-row accordion behavior remains deterministic.
- [x] 7.10 Test each current room-mode supported family presentation can be opened inside the new accordion and remains bound to exact per-record state without substituting a standalone/single-device screen or gaining direct credentials/handler/session/network authority.
- [x] 7.11 Regression-test that the current room Matrix presentation remains exact-row and read-only for routing; existing Matrix room live/local-refresh lifecycle remains unchanged; foundation introduces no Matrix route-mutation intent, no registry mutation binding, and does not wire standalone `MatrixScreen.routeRequested` into the room accordion.
- [x] 7.12 Regression-test existing room-mode Audio DSP live/meter updates remain application-owned and do not move network work to the Qt GUI thread merely because the view is mounted in the new shell.
- [x] 7.13 Regression-test existing room-mode codec auxiliary/live and PDU mutation/reconciliation paths retain their approved exact-row lifecycle gates inside the new accordion.
- [x] 7.14 Test theme starts dark on each new application instance, is not persisted, does not materially change common foundation geometry at a fixed baseline window, and keeps reused room-mode family content readable/usable.
- [x] 7.15 Test warranty remains explicit `Нет данных` and is not inferred from schema-v4/device data.
- [x] 7.16 Test unified-registry call-activity coverage explicitly for all five current exact codec identities: `Huawei TE20`, `Huawei TE40`, `CloudLink Bar 310`, `CloudLink Box 310`, and `Polycom RPG 310`. For each, cover known active evidence -> `ACTIVE`, known no-call evidence -> `INACTIVE`, and missing/stale/unrecognized evidence -> `UNKNOWN`; prove a missing/unavailable required binding fails registry/composition validation and prove shared room/GUI code has no model list or string/substring classification path.
- [x] 7.17 Test occupancy projection: any current `ACTIVE` -> `Занято`; all-`INACTIVE`, `UNKNOWN`, missing, stale, or failed evidence without an `ACTIVE` -> `Нет данных`; accepted typed activity updates refresh the presentation without occupancy-specific I/O; hover explanation is local-only.
- [x] 7.18 Test network presentation retains known port when switch IP is missing, shows safe no-data for missing child port when switch IP is known, never groups unknown-switch records by port, and never fabricates unattached switches.
- [x] 7.19 Test parent port summary for zero/one/many/repeated child ports and prove it is presentation-only while child ports remain exact.
- [x] 7.20 Add a scope-guard regression/review assertion that this implementation does not introduce the deferred Audio segmented-meter layout, Matrix new column hierarchy or room route-mutation capability, codec grouped-card redesign, PDU grouped-card redesign, new screen-specific reference-only controls, or promotion of standalone/single-device controls into room mode.

## 8. Manual visual acceptance

- [x] 8.1 Launch the GUI as a detached process per `RULES.md`; use a `1440 x 900` logical-pixel baseline window in representative room mode.
- [x] 8.2 Capture local, non-committed dark-theme screenshots and verify only the foundation criteria: toolbar/search dominance, visible selected-room cue, room/network peer-card ratio, room occupancy row/tooltip, switch-parent port summary, spacing/radius scale, `52-64 px` common equipment-row density, one-row accordion behavior, and reachability/readability of reused current room-mode expanded family content. (Operator confirmed local dark-theme screenshot acceptance at 1440 x 900 on 2026-08-30; screenshot remains untracked.)
- [x] 8.3 Toggle to light mode at the same window size, capture local non-committed screenshots, and verify the same common foundation geometry/hierarchy with readable primary/secondary/disabled/focus/status states and readable/usable reused current room-mode expanded content. (Operator confirmed local light-theme screenshot acceptance at 1440 x 900 on 2026-08-30; screenshot remains untracked.)
- [x] 8.4 Do NOT evaluate deferred Audio meter geometry, Matrix column hierarchy/interactive room routing, codec grouped-card layout, or PDU grouped-card layout as acceptance criteria for this change.
- [x] 8.5 Record the manual foundation acceptance result in the implementation session report; screenshots remain local validation aids and SHALL NOT be committed unless the user explicitly requests tracked evidence. (2026-08-30: operator confirmed acceptance in the detached GUI.)

## 9. Implementation verification and publication

- [x] 9.1 Run focused tests for inventory search, room target resolution, fallback preservation, direct room/session ordering, two-branch Full Refresh, complete target-search lifecycle lock matrix, common shell/theme, common accordion integration, unified-registry call-activity binding/validation for all five baseline codecs, typed call-activity normalization, busy occupancy projection, network partial evidence/parent summary, current room-mode family-boundary compatibility, and the Matrix read-only/no-route-promotion guard.
- [x] 9.2 Run the full required offline test suite and record fresh exact counts; do not copy prior counts. (`C:\Users\Mih\AppData\Local\Programs\Python\Python312\python.exe -m unittest discover -s tests -p "test_*.py" -v`: 806 tests in 95.468s, OK.)
- [x] 9.3 Run:

```powershell
.\openspec.cmd validate room-diagnostic-modern-ui --strict
.\openspec.cmd validate --all --strict
git diff --check
git diff --cached --check
```

- [x] 9.4 Synchronize implementation evidence/tasks only with commands actually executed on the current implementation HEAD.
- [x] 9.5 Create one focused implementation commit and push `agent/room-diagnostic-modern-ui`; implementation session must not issue independent `APPROVE`.

## 10. Independent validation

- [ ] 10.1 Fetch current remote state and record current `master`, PR Draft/state/base/head, and `origin/agent/room-diagnostic-modern-ui` SHA.
- [ ] 10.2 Create a separate clean detached worktree from exact `origin/agent/room-diagnostic-modern-ui`; verify local HEAD equals recorded remote SHA and worktree is clean.
- [ ] 10.3 Independently review implementation against every approved foundation contract, with special attention to fallback preservation, selected-room visibility/currentness, source-less Full Refresh/accordion rules, complete target-search lock/supersession inheritance across automatic cycle/Local Refresh/AUXILIARY_READ/mutation, exact-row target authority, unified-registry call-activity bindings for all five baseline codecs, fail-fast missing-binding validation, exact-model typed normalization, no shared string/model-list heuristics, busy-only occupancy/no extra I/O, parent-port summary semantics, partial network evidence, no-widget network authority, current room-mode-only family reuse, Matrix read-only/no-route-promotion, and absence of deferred device-family redesign scope creep.
- [ ] 10.4 Rerun fresh focused and full offline tests, strict change/all OpenSpec validation, `git diff --check`, and `git diff --cached --check`.
- [ ] 10.5 Repeat the foundation dark/light manual visual acceptance in the independent detached worktree/environment where GUI launch is available; if GUI launch is unavailable, report that limitation rather than claiming visual acceptance. Do not score deferred family-specific redesign criteria.
- [ ] 10.6 Perform the mandatory disposable archive-applicability check because this change modifies root requirements and adds a new root capability. Do not run archive on the primary feature branch for this check.
- [ ] 10.7 Independent validator must not fix its own findings. `READY FOR ARCHIVE` is permitted only with no CRITICAL/HIGH/MEDIUM findings and all mandatory checks passing on current remote HEAD.

## 11. Archive and completion

- [ ] 11.1 Archive only after an independent permitting verdict using:

```powershell
.\openspec.cmd archive room-diagnostic-modern-ui --yes
```

- [ ] 11.2 Review archive/root-spec diff, especially replacements in `diagnostic-application-shell`, `room-equipment-diagnostics`, `room-device-interaction-lifecycle`, the inventory query addition, the added `device-diagnostics-and-control` call-activity requirement, and the new foundation-only `diagnostic-ui-presentation` root spec.
- [ ] 11.3 Run full post-archive checks:

```powershell
.\openspec.cmd validate --all --strict
# full required offline test suite
git diff --check
git diff --cached --check
```

- [ ] 11.4 Create and push a dedicated archive commit.
- [ ] 11.5 Reconfirm current remote archive HEAD and current `master` before merge. Do not merge, close the PR, or delete the branch without explicit user authorization.

## 12. Deferred follow-up changes

- [ ] 12.1 Do not create or stack device-family redesign changes on this unarchived feature branch.
- [ ] 12.2 After this foundation is archived and merged to current `master`, create separate semantic OpenSpec changes equivalent to `audio-diagnostic-modern-ui`, `matrix-diagnostic-modern-ui`, `codec-diagnostic-modern-ui`, and `pdu-diagnostic-modern-ui` as needed.
- [ ] 12.3 Each follow-up change must independently define/review its visual contract, regression coverage, manual acceptance, lifecycle safety, implementation, independent validation, archive, and merge.
