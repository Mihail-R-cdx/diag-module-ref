# Tasks: Modern codec diagnostic UI

## 1. Architecture and capability composition

- [ ] 1.1 Extend the unified exact-model registration with one codec-control capability/binding descriptor (or equivalent registry-owned structure) for `speaker_adjust`, `speaker_mute`, `microphone_adjust`, `microphone_mute`, and `reboot`.
- [ ] 1.2 Make every current exact codec registration explicitly declare each dashboard operation `SUPPORTED` or `UNSUPPORTED`; do not add a parallel codec model list.
- [ ] 1.3 Fail closed during composition when a declared supported codec operation lacks its required adapter/readback/cleanup binding.
- [ ] 1.4 Keep unsupported-operation handling local/presentation-only: active visible control -> informational dialog -> zero handler/session acquisition and zero device I/O.

## 2. Unified codec dashboard presentation

- [ ] 2.1 Replace the room codec flat-field projection with the one shared five-card dashboard: `Состояние`, `Вызов и презентация`, `Аудио`, `Журнал вызовов`, `Действия`.
- [ ] 2.2 Preserve the exact `Состояние` row order: model, MAC, serial, platform, software version, microphone, camera.
- [ ] 2.3 Preserve the exact `Вызов и презентация` row order: call status, presentation, SIP/H.323 registration.
- [ ] 2.4 Render missing/unusable model-specific values as `Нет данных`; never hide a required card/row because one model lacks the value.
- [ ] 2.5 Implement the Audio card with current microphone-level indicator plus microphone/speaker value and `− / + / mute` controls in the approved positions.
- [ ] 2.6 Reuse only existing current accepted/live level evidence; do not add a meter poll merely to populate the reference slot.
- [ ] 2.7 Implement Actions with `Обновить статус` as the existing Local Refresh alias and `Перезагрузить устройство` as registry-gated supported/unsupported intent.
- [ ] 2.8 Meet the baseline five-card order/relative weights approximately `23:17:18:25:17`, preserve shared dark/light theming, and keep all content reachable at the common minimum window.

## 3. Room audio interactions

- [ ] 3.1 Route room speaker/microphone control intents through application composition and the existing exact-row serialized interaction coordinator; presentation widgets must not own handlers/sessions/credentials.
- [ ] 3.2 Build `+ / −` from current authoritative values into absolute model-valid targets; do not fabricate a starting value when current evidence/range is unavailable.
- [ ] 3.3 Preserve model-specific existing range/step/mute semantics only through the registry-bound adapter; do not branch shared GUI behavior on model substrings.
- [ ] 3.4 Run every supported state-changing audio operation through `MUTATION -> RECONCILIATION`; update accepted row state only after confirmed readback.
- [ ] 3.5 Preserve no-replay/no-credential-advance semantics after possible delivery or ambiguous outcome, exact-row stale checks, bounded cleanup and GUI-thread isolation.

## 4. Call-log preview

- [ ] 4.1 Refactor/reuse the existing room call-log controller so acquisition/normalized result ownership is separable from opening `CallLogWindow`.
- [ ] 4.2 On expansion of an eligible current connected codec row, request at most one automatic call-log preview through the existing `AUXILIARY_READ` lane.
- [ ] 4.3 Retire active LIVE before preview I/O and resume eligible LIVE only after terminal preview cleanup/currentness checks.
- [ ] 4.4 Keep the accepted full call-log result bound to the exact row/generation; render only the three newest records in the card.
- [ ] 4.5 Render zero/unavailable preview data as `Нет данных`; preserve safe direction/peer/timestamp values for available entries.
- [ ] 4.6 Suppress duplicate preview reads caused by repeated rendering/expansion of the same current row.
- [ ] 4.7 Collapse, row switch, top Refresh and target/context invalidation must cancel/invalidate preview authority and reject late callbacks.
- [ ] 4.8 `Развернуть` opens the existing detailed call-log window from current accepted full preview data when available; otherwise it performs the existing serialized fresh auxiliary acquisition before populating the window.
- [ ] 4.9 Preserve existing direct child-window close cancellation and fresh-reopen behavior for a cancelled active request.

## 5. Regression coverage

- [ ] 5.1 Cover the unified dashboard for `Huawei TE20`, `Huawei TE40`, `CloudLink Bar 310`, `CloudLink Box 310`, and `Polycom RPG 310` as current acceptance oracles while proving runtime authority comes only from the unified registry.
- [ ] 5.2 Assert fixed card order, field order, permanent missing-data rows and `Нет данных` behavior for every codec model fixture.
- [ ] 5.3 Assert baseline card proportions/order and dark/light geometry without making screenshot pixels the runtime authority.
- [ ] 5.4 Assert microphone-level unavailable behavior and that the dashboard starts no new level I/O solely for presentation.
- [ ] 5.5 Assert every current codec registration explicitly resolves every codec-control operation to supported or unsupported and that missing declared bindings fail composition.
- [ ] 5.6 Assert unsupported audio/reboot clicks show the local information path with no handler/session/network acquisition.
- [ ] 5.7 Assert supported audio target construction, mutation/readback confirmation, ambiguous-outcome blocking and top-Refresh recovery.
- [ ] 5.8 Assert automatic call-log preview, newest-three ordering, empty state, duplicate suppression and current-row/generation binding.
- [ ] 5.9 Assert preview/live handoff and stale suppression across collapse, A->B row switch, top Refresh, query/context invalidation and application shutdown.
- [ ] 5.10 Assert `Развернуть` uses the existing detailed window and never creates a second concurrent auxiliary owner.
- [ ] 5.11 Assert `Обновить статус` remains the existing Local Refresh lifecycle and does not create a codec-specific refresh lane.

## 6. Implementation validation and publication

- [ ] 6.1 Run focused codec room presentation/interaction/call-log tests.
- [ ] 6.2 Run all affected room lifecycle, dispatch/registry, codec, GUI and stale-safety suites.
- [ ] 6.3 Run the full offline test suite; record fresh counts in the implementation report/task evidence.
- [ ] 6.4 Run `node --version`, `npm --version`, `npm ci` when dependencies require restoration, then `./openspec.cmd validate codec-diagnostic-modern-ui --strict` and `./openspec.cmd validate --all --strict` using only the repository-local wrapper.
- [ ] 6.5 Run `git diff --check`, `git diff --cached --check`, and review the complete feature diff for scope/secrets/Graphify exclusions.
- [ ] 6.6 Launch the GUI detached per `RULES.md`; at `1440 x 900` capture local dark-theme visual evidence for the expanded codec area and verify approximately 90% correspondence to the approved reference contract; verify the same geometry/readability in light theme. Do not commit screenshots by default.
- [ ] 6.7 Create one focused implementation commit and push the feature branch. Do not self-issue independent `APPROVE`.

## 7. Independent validation / archive gates

- [ ] 7.1 Independent validator uses a clean detached worktree from current `origin/agent/codec-diagnostic-modern-ui`, proves local/remote SHA equality and reruns fresh required tests/strict validation/Git checks.
- [ ] 7.2 Independent validator performs the disposable archive-applicability check because the change adds requirements to existing root specs.
- [ ] 7.3 Archive only after an independent permitting verdict; then run post-archive strict all validation, full offline tests, Git checks and review the archive/root-spec diff before the dedicated archive commit/push.
- [ ] 7.4 Merge only with explicit user authorization after rechecking current remote archive HEAD and current `master`.
