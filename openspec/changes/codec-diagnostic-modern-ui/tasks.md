# Tasks: Modern codec diagnostic UI

## 1. Architecture and capability composition

- [ ] 1.1 Extend the unified exact-model registration with one codec-control capability/binding descriptor (or equivalent registry-owned structure) for `speaker_adjust`, `speaker_mute`, `microphone_adjust`, `microphone_mute`, and `reboot`.
- [ ] 1.2 Make the five current exact codec registrations match the approved OpenSpec acceptance matrix exactly:

  | Exact model | speaker_adjust | speaker_mute | microphone_adjust | microphone_mute | reboot |
  | --- | --- | --- | --- | --- | --- |
  | Huawei TE20 | SUPPORTED | SUPPORTED | UNSUPPORTED | SUPPORTED | UNSUPPORTED |
  | Huawei TE40 | SUPPORTED | SUPPORTED | UNSUPPORTED | SUPPORTED | UNSUPPORTED |
  | CloudLink Bar 310 | SUPPORTED | SUPPORTED | UNSUPPORTED | UNSUPPORTED | UNSUPPORTED |
  | CloudLink Box 310 | SUPPORTED | SUPPORTED | UNSUPPORTED | UNSUPPORTED | UNSUPPORTED |
  | Polycom RPG 310 | SUPPORTED | SUPPORTED | UNSUPPORTED | SUPPORTED | UNSUPPORTED |

  This is test/acceptance data only; do not add a second runtime codec support table.
- [ ] 1.3 Fail closed during composition when a declared supported codec operation lacks its required adapter/readback/cleanup binding.
- [ ] 1.4 Preserve the modified unsupported-control contract: fixed codec affordance may remain visible/clickable when otherwise unlocked, but unsupported network capability resolves locally before coordinator admission with zero LIVE invalidation, handler/session/credential/network activity.
- [ ] 1.5 Preserve the modified CloudLink contract: Bar/Box microphone gain network capability remains unavailable/disabled and no gain PUT/POST/readback is introduced; visible microphone `−/+` affordances are local-only unsupported presentation.

## 2. Unified codec dashboard presentation

- [x] 2.1 Replace the room codec flat-field projection with the one shared five-card dashboard: `Состояние`, `Вызов и презентация`, `Аудио`, `Журнал вызовов`, `Действия`.
- [x] 2.2 Preserve exact `Состояние` row order: model, MAC, serial, platform, software version, microphone, camera.
- [x] 2.3 Preserve exact `Вызов и презентация` row order: call status, presentation, SIP/H.323 registration.
- [x] 2.4 Render missing/unusable values as `Нет данных`; never hide a required card/row because one model lacks the value. Use the approved dot-free, right-aligned value columns; call/presentation use normalized `Да`/`Нет`, while registration uses its semantic icon and neutral unavailable state without shared-GUI localized-string parsing.
- [x] 2.5 Implement Audio with horizontal current microphone-level indicator followed by microphone and speaker rows in the exact `− | value | + | mute` geometry and approved size ranges.
- [x] 2.6 Reuse only existing current accepted/live level evidence; do not add a meter poll solely to populate the visual slot.
- [x] 2.7 Implement Actions with two full-width vertical buttons in order: `Обновить статус`, then `Перезагрузить устройство`; refresh is existing Local Refresh alias and reboot follows current unsupported local-only path.
- [x] 2.8 Meet repository-local baseline geometry: five-card weights `23:17:18:25:17` within ±4 points, card height `286-326 px`, card gaps `10-14 px`, padding `14-18 px`, and all detailed typography/control/call-row ranges in the presentation spec.
- [ ] 2.9 At `1440 x 900` satisfy all mandatory visual checkpoints, including required indicator checkpoint 9, and at least `9/10` total repository-local checkpoints; preserve the same geometry/order in light theme. External screenshot access must not be required.

## 3. Typed room audio projection and interactions

- [ ] 3.1 Replace ambiguous combined audio slots with separate model-neutral `microphone_volume`, `microphone_mute_state`, `speaker_volume`, `speaker_mute_state`; volumes are optional numeric and mute states are typed `MUTED | UNMUTED | UNKNOWN` or equivalent.
- [ ] 3.2 Route room speaker/microphone intents through application composition and the existing exact-row serialized interaction coordinator; presentation widgets must not own handlers/sessions/credentials.
- [ ] 3.3 Build supported `+ / −` only from current accepted numeric values into absolute model-valid targets using registry-bound range/step policy; do not fabricate a starting value when current evidence/range is unavailable.
- [ ] 3.4 Implement TE20/TE40/Polycom microphone mute as typed desired `MUTED`/`UNMUTED` with typed readback; do not reinterpret it as numeric microphone gain.
- [ ] 3.5 Implement supported speaker mute as absolute volume zero and unmute as restore to the last accepted current non-zero speaker volume owned by application/core for the exact room generation/record.
- [ ] 3.6 Never use `CodecScreen.last_unmuted_volume`, fallback `1`, minimum/default volume, another row's value, requested value or ACK as restore authority; if current speaker volume is zero and no accepted restore target exists, unmute shows local unavailable and performs zero network I/O.
- [ ] 3.7 Clear/remap room-owned restore authority on new room generation/context invalidation; only newly accepted current non-zero speaker readback may replace it.
- [ ] 3.8 Run every supported state-changing audio operation through `MUTATION -> RECONCILIATION`; update accepted row state only after matching confirmed readback.
- [ ] 3.9 Preserve no-replay/no-credential-advance semantics after possible delivery or ambiguous outcome, exact-row stale checks, bounded cleanup and GUI-thread isolation.

## 4. Call-log preview and chronology

- [ ] 4.1 Refactor/reuse the existing room call-log controller so acquisition/typed normalized result ownership is separable from opening `CallLogWindow`.
- [ ] 4.2 Track automatic preview authority by current room generation + exact `record_id` + expansion epoch; a new epoch begins only on a real collapsed->expanded transition, not rerender/theme/resize/repaint/duplicate Qt events. When the room cycle is already terminal, every current eligible collapsed->expanded codec transition must admit exactly one automatic preview intent through the existing `AUXILIARY_READ` lane for that epoch.
- [ ] 4.3 If codec is expanded before room-cycle terminal state, perform zero pre-terminal preview I/O and admit that epoch's one automatic attempt only after terminal state if the same exact row/epoch remains current and eligible.
- [ ] 4.4 Route the one automatic attempt through existing `AUXILIARY_READ`, retire active LIVE before preview I/O, and resume eligible LIVE only after terminal cleanup/currentness checks.
- [ ] 4.5 Mark the automatic attempt terminal for the expansion epoch after success-with-records, success-empty, ordinary parse/business/no-data failure, or typed terminal failure.
- [ ] 4.6 After an ordinary automatic preview failure, repeated render/theme/resize/repaint/hover/duplicate expansion/LIVE resume must cause zero additional automatic call-log I/O for the same epoch.
- [ ] 4.7 Allow a new automatic attempt only after an approved new expansion/context boundary: collapse+re-expand, row switch then later re-expand, new room generation/top Refresh, or new valid context after invalidation.
- [ ] 4.8 Keep accepted full call-log result exact-row/generation bound; preview takes only the first three records from the typed normalized newest-first result.
- [ ] 4.9 Use `CallHistorySnapshot` chronology contract (or exact equivalent): typed comparable `start_at` descending; missing chronology after timestamped records; deterministic stable order for equal/missing chronology; never sort localized display strings.
- [x] 4.10 Preserve safe direction/peer/timestamp presentation and `Нет данных` for missing subfields/empty preview.
- [ ] 4.11 Collapse, row switch, top Refresh, target/context/credential invalidation and shutdown must cancel/invalidate active preview authority and reject late callbacks.
- [ ] 4.12 `Развернуть` reuses current accepted full preview without I/O; if no accepted result exists, including after failed/no-data automatic preview, it may submit one explicit fresh auxiliary request without resetting the completed automatic-attempt marker.
- [ ] 4.13 Preserve existing direct child-window close cancellation and fresh explicit reopen behavior for a cancelled active request.

## 5. Regression coverage

- [ ] 5.1 Cover the unified dashboard for all five exact codec registrations while proving runtime authority comes only from the unified registry.
- [ ] 5.2 Assert every current codec registration matches the exact support matrix in task 1.2; a regression that turns a required current SUPPORTED operation into UNSUPPORTED must fail.
- [ ] 5.3 Assert fixed card/field order, permanent missing-data rows, all normative baseline geometry ranges, mandatory structural checkpoints, approved dot-free status/call-value presentation (including neutral unavailable registration state), and dark/light parity.
- [ ] 5.4 Assert microphone-level unavailable behavior and that the dashboard starts no new level I/O solely for presentation.
- [ ] 5.5 Assert split numeric volume/mute-state typing; shared GUI never treats `Muted`/`Unmuted` as numeric volume or parses display strings for mutation authority.
- [ ] 5.6 Assert supported speaker `+/-`, mute and restore target construction; current zero + no accepted restore target -> informational unavailable + zero handler/session/network I/O.
- [ ] 5.7 Assert old widget-local remembered volume, fallback `1`, minimum/default and optimistic requested/ACK values cannot become room restore authority.
- [ ] 5.8 Assert TE20/TE40/Polycom microphone mute succeeds only through typed mute/readback; all five `microphone_adjust` capabilities remain unsupported.
- [ ] 5.9 Assert CloudLink Bar/Box microphone `−/+` clicks use local informational path with zero interaction/network I/O and no gain PUT/POST/readback.
- [ ] 5.10 Assert current reboot is unsupported for all five and visible affordance performs zero I/O; do not add a reboot handler merely to satisfy the dashboard.
- [ ] 5.11 Assert supported audio mutation/readback confirmation, ambiguous-outcome blocking and top-Refresh recovery.
- [ ] 5.12 Assert a terminal room followed by an eligible collapsed->expanded codec transition admits exactly one automatic `AUXILIARY_READ` preview intent for that epoch, and separately assert a codec already expanded when the cycle becomes terminal admits its one deferred automatic attempt.
- [ ] 5.13 Assert success, empty and ordinary-failure automatic preview each consume exactly one attempt per expansion epoch; specifically business failure -> repeated render/theme/resize/repaint -> zero additional automatic I/O.
- [ ] 5.14 Assert collapse+re-expand creates a new epoch that admits one new automatic attempt when still eligible; duplicate expansion notifications without collapse do not.
- [ ] 5.15 Assert preview/live handoff and stale suppression across collapse, A->B row switch, top Refresh, query/context invalidation and shutdown.
- [ ] 5.16 Assert `Развернуть` after a failed automatic attempt may execute one explicit fresh auxiliary read without causing a new automatic attempt.
- [ ] 5.17 For TE20, TE40, Bar 310, Box 310 and Polycom call-log fixtures, assert normalized newest-first chronology; include equal, malformed and missing timestamp cases and prove localized display strings are not sorting authority.
- [ ] 5.18 Assert `Обновить статус` remains the existing Local Refresh lifecycle and does not create a codec-specific refresh lane.

## 6. Implementation validation and publication

- [x] 6.1 Run focused codec room presentation/interaction/call-log tests.
- [x] 6.2 Run all affected room lifecycle, dispatch/registry, codec, GUI and stale-safety suites.
- [x] 6.3 Run the full offline test suite; record fresh counts in the implementation report/task evidence. (2026-09-02: 842 tests, OK.)
- [x] 6.4 Run `node --version`, `npm --version`, `npm ci` when dependencies require restoration, then `./openspec.cmd validate codec-diagnostic-modern-ui --strict` and `./openspec.cmd validate --all --strict` using only the repository-local wrapper.
- [x] 6.5 Run `git diff --check`, `git diff --cached --check`, and review the complete feature diff for scope/secrets/Graphify exclusions.
- [ ] 6.6 Launch the GUI detached per `RULES.md`; at `1440 x 900` evaluate the ten repository-local visual checkpoints in dark theme, explicitly verify the five mandatory status indicators and neutral unavailable states, and verify the same geometry/readability in light theme. External screenshot comparison is optional and not validation authority. Do not commit screenshots by default.
- [ ] 6.7 Create one focused implementation commit and push the feature branch. Do not self-issue independent `APPROVE`.

## 7. Independent validation / archive gates

- [ ] 7.1 Independent validator uses a clean detached worktree from current `origin/agent/codec-diagnostic-modern-ui`, proves local/remote SHA equality and reruns fresh required tests/strict validation/Git checks.
- [ ] 7.2 Independent validator performs the disposable archive-applicability check because this change uses `MODIFIED Requirements` and will modify existing root-spec requirements on archive.
- [ ] 7.3 Archive only after an independent permitting verdict; then run post-archive strict all validation, full offline tests, Git checks and review the archive/root-spec diff before the dedicated archive commit/push.
- [ ] 7.4 Merge only with explicit user authorization after rechecking current remote archive HEAD and current `master`.
