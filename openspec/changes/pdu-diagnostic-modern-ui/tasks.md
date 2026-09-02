# Tasks: Modern PDU diagnostic UI

## 1. PDU presentation composition

- [ ] 1.1 Replace the current room-mode PDU expanded content with the shared two-card dashboard: `Основная информация` on the left and `Управление розетками` on the right.
- [ ] 1.2 Keep the current exact-row/application authority; do not embed or promote standalone PDU widget state into room capability ownership.
- [ ] 1.3 Render `Основная информация` with exactly `Модель`, `Серийный номер`, `MAC-адрес` in that order. Use exact current room-record/application evidence and render missing serial/MAC as `—` without adding PDU device reads.
- [ ] 1.4 Remove PDU expanded-card rows for IP, firmware, switch connection, device state, input power, temperature, humidity, overload or other screenshot-only fields.
- [ ] 1.5 When a current PDU row is expanded, add exactly one far-right local-refresh icon to its header; do not add a kebab/overflow menu or a second right-side collapse action.

## 2. Outlet table and fixed controls

- [ ] 2.1 Build `Управление розетками` with top actions in exact order: `Обновить статус`, `Включить всё`, `Выключить всё`.
- [ ] 2.2 Use exactly five table columns in order: `Розетка`, `Имя розетки`, `Состояние`, `Текущая мощность`, `Действия`.
- [ ] 2.3 Keep outlet rows in deterministic numeric ascending order and support arbitrary current outlet counts with controlled vertical scrolling; visual baseline uses eight rows.
- [ ] 2.4 Render current power as `—` for every outlet in this change. Add no worker/handler/timer/network request solely to populate power. Do not fabricate `0 Вт`.
- [ ] 2.5 Render state with explicit text plus semantic cue: ON uses green reinforcement, OFF red reinforcement, unavailable neutral `—`; never rely on color alone.
- [ ] 2.6 Render the `Действия` cell in exact order `Вкл`, `Выкл`, `Перезапуск`, with green/red/neutral semantic styling respectively.
- [ ] 2.7 Meet baseline geometry from the presentation spec: approximately `22:78` card weights, approved gaps/padding/table row ranges and five-column proportions, without hiding required controls.
- [ ] 2.8 Preserve the same geometry/order in light theme; theme switch/repaint/resize/scrolling perform no device I/O.

## 3. Refresh and mutation wiring

- [ ] 3.1 Wire the PDU header refresh icon and `Обновить статус` to the same existing exact-row `LOCAL_REFRESH` intent/lifecycle. They must share eligibility/locks and must not create parallel refresh lanes or generations.
- [ ] 3.2 Keep supported per-outlet `Вкл` / `Выкл` / `Перезапуск` on the existing PDU controller/core operation path and existing confirmation plus `MUTATION -> RECONCILIATION` lifecycle.
- [ ] 3.3 Keep `Включить всё` / `Выключить всё` on the existing application-owned bulk operation path; do not implement bulk by driving individual Qt buttons and do not add bulk reboot.
- [ ] 3.4 For fixed controls unsupported by the exact PDU model, resolve support before room interaction admission and show a local informational popup equivalent to `Команда не поддерживается` with zero LIVE invalidation, credential selection, handler/session acquisition, mutation generation or device I/O.
- [ ] 3.5 Preserve current Aten capability support: refresh, individual ON/OFF/REBOOT and bulk ON/OFF remain real existing operations.
- [ ] 3.6 Preserve current PCS4i capability support: refresh, individual ON/OFF and bulk ON/OFF remain real existing operations; fixed `Перезапуск` remains visible but local-only unsupported with zero device I/O.
- [ ] 3.7 Preserve existing stale/currentness, credential ownership, ambiguous-mutation blocking, mandatory reconciliation and GUI-thread isolation contracts.
- [ ] 3.8 Preserve removal of PDU-hosted related-codec enrichment; no PDU refresh/mutation may start a related-codec lookup/session/status/meter lifecycle.

## 4. Regression coverage

- [ ] 4.1 Add `tests/test_pdu_modern_ui.py` (or equivalent focused suite) covering the common two-card room PDU dashboard for Aten PE8208AV and Extron IPL T PCS4i while runtime authority remains the existing unified/exact PDU capability source.
- [ ] 4.2 Assert exact three-row information-card order and sources: model, canonical serial, canonical MAC; missing values render `—`; no extra PDU information rows are present.
- [ ] 4.3 Assert exact top-action labels/order and exact five table columns/order.
- [ ] 4.4 Assert eight-row baseline density, arbitrary-row scrolling behavior and deterministic numeric outlet ordering.
- [ ] 4.5 Assert power cells remain `—` and dashboard construction/refresh introduces no new power-specific acquisition path.
- [ ] 4.6 Assert ON/OFF explicit status text and semantic colors, plus `Вкл`/`Выкл`/`Перезапуск` action order and styling hooks.
- [ ] 4.7 Assert both PDU refresh affordances submit the same Local Refresh intent and cannot create concurrent refresh ownership.
- [ ] 4.8 Assert Aten individual ON/OFF/REBOOT and bulk ON/OFF continue through existing controller/application lifecycle and mandatory reconciliation.
- [ ] 4.9 Assert PCS4i individual ON/OFF and bulk ON/OFF remain supported, while visible `Перезапуск` produces `Команда не поддерживается` locally and causes zero PDU network I/O; no bulk reboot exists.
- [ ] 4.10 Assert programmatic unsupported operations still fail closed before handler acquisition.
- [ ] 4.11 Assert mutation ACK/request state never directly becomes accepted outlet state; only successful current reconciliation replaces cache.
- [ ] 4.12 Assert legacy PDU related-codec enrichment remains absent after redesign.
- [ ] 4.13 Assert dark/light theme parity and header contains only the PDU refresh action on the right: no kebab/overflow and no extra right collapse action.

## 5. Implementation validation and publication

- [ ] 5.1 Run focused PDU suites including at minimum `tests/test_pdu_modern_ui.py`, `tests/test_pdu_gui_composition.py`, `tests/test_pdu_controller.py`, `tests/test_pdu_operations.py`, `tests/test_aten_pdu_safety.py`, `tests/test_extron_pcs4i.py`, `tests/test_pdu_room_codec_removal.py`, `tests/test_room_interaction.py`, `tests/test_room_modern_foundation.py`, and `tests/test_gui_theme.py` as applicable to the final diff.
- [ ] 5.2 Run all other directly affected room/device/GUI regression suites discovered from the implementation diff.
- [ ] 5.3 Run the full offline test suite and report fresh counts; do not reuse historical counts.
- [ ] 5.4 Run repository-supported Node/npm checks and use only repository-local `./openspec.cmd validate pdu-diagnostic-modern-ui --strict` and `./openspec.cmd validate --all --strict`.
- [ ] 5.5 Run `git diff --check`, `git diff --cached --check`, review the complete feature diff for scope/secrets/Graphify exclusions, then create one focused implementation commit and push. Implementation session must not self-issue independent `APPROVE`.
- [ ] 5.6 Launch the GUI detached per `RULES.md`. At `1440 x 900` with an eight-outlet Aten fixture evaluate all ten repository-local PDU visual checkpoints in dark theme and confirm the same geometry/readability in light theme. All mandatory checkpoints and at least `9/10` total must pass. Screenshots remain local by default.

## 6. Independent validation / archive gates

- [ ] 6.1 Independent validator uses a separate clean detached worktree from current `origin/agent/pdu-diagnostic-modern-ui`, proves local/remote SHA equality and reruns fresh focused/full tests, strict validation and Git checks.
- [ ] 6.2 Independent validator performs a disposable archive-applicability check because this change uses a `MODIFIED Requirement` and will replace an existing root requirement on archive.
- [ ] 6.3 Archive only after an independent permitting verdict; then run post-archive `validate --all --strict`, full offline tests, Git checks and review archive/root-spec diff before dedicated archive commit/push.
- [ ] 6.4 Merge only with explicit user authorization after rechecking current remote archive HEAD and current `master`.
