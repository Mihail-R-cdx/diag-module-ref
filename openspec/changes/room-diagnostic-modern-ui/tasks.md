## 1. Architecture and validation

- [x] 1.1 Capture the approved product decisions: IP-or-room search, direct `room_id` authority, room/network upper cards, common accordion row, device-specific visual references, disabled future controls, dark/light toggle, and application title.
- [x] 1.2 Confirm current `master`, current `RULES.md`, inventory runbook, relevant root specs, and current GUI/inventory boundaries before authoring the change.
- [ ] 1.3 Review the architecture against current `master` and resolve all CRITICAL/HIGH/MEDIUM findings without changing production code.
- [ ] 1.4 Run repository-local architecture validation on the current published architecture HEAD:

```powershell
.\openspec.cmd validate room-diagnostic-modern-ui --strict
.\openspec.cmd validate --all --strict
git diff --check
git diff --cached --check
```

- [ ] 1.5 Record exact branch/base/HEAD and validation exit codes/counts before architectural `APPROVE`.

## 2. Target search and inventory query

- [ ] 2.1 Add an immutable room-name search projection/query to `EquipmentInventory` without changing canonical schema v4.
- [ ] 2.2 Cover Unicode NFC/trim/casefold substring matching, room-id deduplication, conflicting names inside one room ID, zero/one/many matches, and deterministic result ordering.
- [ ] 2.3 Derive deterministic room result labels from canonical display name plus first usable room address; when distinct room IDs still collide, append a neutral deterministic display-only `Вариант N` discriminator without exposing it as identity.
- [ ] 2.4 Replace permanent IP-only input composition with IP-or-room target classification while preserving the operator's raw query text.
- [ ] 2.5 Implement autocomplete/dropdown selection for multi-match room queries plus a separate visible selected-room cue; typing and selection alone must perform zero device network I/O.
- [ ] 2.6 Ensure editing the raw query clears the selected-room cue, invalidates stale selection/current room authority, and increments request/currentness generation before replacement I/O.
- [ ] 2.7 Keep valid-inventory IP zero/one/many/unmapped semantics unchanged and preserve legacy supported no-room single-device behavior.
- [ ] 2.8 Preserve unavailable-inventory IP diagnostic fallback exactly: diagnostic start automatically opens the existing fail-closed model fallback and requires a new explicit model selection + `Подключиться` confirmation.
- [ ] 2.9 Keep room-name search fail-closed when inventory is unavailable; do not invoke diagnostic or credential fallback for a room-name query.
- [ ] 2.10 Preserve `Пароль` behavior: valid inventory resolves only one exact supported IP/model; unavailable inventory may use the existing explicit credential-configuration fallback; valid-inventory zero/many/unmapped and room-name contexts do not gain fallback.

## 3. Direct room-name session composition

- [ ] 3.1 Allow room session construction with an exact selected `room_id` and no source record.
- [ ] 3.2 Preserve IP-entry source-first membership ordering; use pure canonical `record_id` ordering for direct room-name entry.
- [ ] 3.3 Preserve same-room duplicate-IP ambiguity, row eligibility, exact-model registry authority, credential planning, one-shot adapter boundaries, and strictly sequential automatic I/O.
- [ ] 3.4 Resolve shared room name/address/VIP source-first for IP entry and canonical-first for source-less room entry.
- [ ] 3.5 Verify selected room authority remains bound to current inventory snapshot/query revision and repeated Refresh uses only the room identified by the visible current-selection cue while that selection remains current.

## 4. Application shell and themes

- [ ] 4.1 Set the user-visible window title to `Диагностический модуль`.
- [ ] 4.2 Build the top toolbar/search layout using semantic components with baseline control height `44-56 px`; search + selection cue should consume roughly 45-60% of baseline toolbar width.
- [ ] 4.3 Extend central theme tokens to dark and light palettes without per-widget persistence logic.
- [ ] 4.4 Start every process in dark mode and add a sun/moon session-only theme toggle.
- [ ] 4.5 Prove theme switching does not change target context, room generation, credentials, live/session ownership, device I/O, or materially reflow geometry at a fixed window size.

## 5. Room upper presentation

- [ ] 5.1 Implement the upper-left room card with room name, address, VIP, warranty, and occupancy rows.
- [ ] 5.2 Populate only current authoritative name/address/VIP. Render warranty and occupancy as `Нет данных`; do not infer values or change inventory schema in this change.
- [ ] 5.3 If a room-card refresh icon is included, wire it only as an alias of top full Refresh.
- [ ] 5.4 Implement the upper-right network-connections tree with peer width to the room card at baseline (`0.9:1` to `1.1:1`).
- [ ] 5.5 Preserve canonical network evidence for all states: known switch IP+known port; known switch IP+missing port; missing switch IP+known port. Unknown-switch/known-port evidence must render under a record-bound `Коммутатор не определён` branch and must not be grouped into invented switch identity.
- [ ] 5.6 Define parent `Порт` cells as not-applicable (`—`); attachment port belongs only to the exact device child. If no switch/port evidence exists, render `Нет данных о сетевых подключениях`.
- [ ] 5.7 Do not implement or fabricate the product-reference `Нет подключенных устройств` state in this change. It is explicitly deferred until a future approved room-level switch inventory source/schema can prove an unattached switch.

## 6. Equipment accordion and device presentations

- [ ] 6.1 Standardize room row headers as `chevron -> class icon -> model -> status cue/text -> IP -> overflow`, baseline collapsed height `52-64 px`, with non-color status cues.
- [ ] 6.2 Preserve one-expanded-row accordion behavior and exact-row presentation binding.
- [ ] 6.3 Rebuild audio DSP presentation with vertical segmented dBFS meters approximately `16-22 px` wide and `180-240 px` tall at baseline, selected-channel emphasis, and disabled future gain/mute controls.
- [ ] 6.4 Rebuild Matrix presentation as the approved per-input signal/HDCP/name/routing table, keeping input name the widest semantic column and preserving existing routing intent/controller ownership.
- [ ] 6.5 Rebuild codec presentation into grouped state/call/audio/action cards with primary/secondary card proportions from the visual contract while preserving existing supported live/call-log application boundaries.
- [ ] 6.6 Rebuild PDU presentation into grouped device/outlet/action cards while preserving existing PDU refresh/mutation/reconciliation boundaries; outlet table may use full width below summary cards.
- [ ] 6.7 Place reference-only future controls in their intended locations as disabled widgets with no connected network/mutation intent.
- [ ] 6.8 Keep reusable widgets presentation-only; no new widget may own credentials, handler/session objects, fallback indexes, request generation, timers, or direct network I/O.

## 7. Regression coverage

- [ ] 7.1 Test raw search text remains unchanged after IP resolution, single room-name resolution, multi-result selection, diagnostics, and top Refresh.
- [ ] 7.2 Test duplicate room names across distinct room IDs produce distinguishable deterministic labels, explicit selection maps to one exact room ID, the selected-room cue remains visible, and repeated Refresh uses only that current selection.
- [ ] 7.3 Test room-name zero/one/many resolution and selection currentness with zero device I/O before Enter/top Refresh.
- [ ] 7.4 Test direct room-name entry creates no synthetic source record and uses canonical row ordering.
- [ ] 7.5 Test IP entry still opens the complete room and retains source-first ordering.
- [ ] 7.6 Regression-test unavailable-inventory IP diagnostic start automatically opens existing model fallback and that `Пароль` retains unavailable-inventory credential-configuration fallback; valid-inventory zero/many/unmapped remains no-fallback.
- [ ] 7.7 Test target-search edits supersede/retire current room interaction under existing lifecycle rules and clear selected-room presentation.
- [ ] 7.8 Test common row statuses remain understandable without color alone and one-row accordion behavior remains deterministic.
- [ ] 7.9 Test future placeholder controls are disabled and cannot emit application/network intents.
- [ ] 7.10 Test Matrix route clicks still cross only the Matrix intent boundary; restyling must not introduce direct handler calls.
- [ ] 7.11 Test audio meter restyling preserves authoritative dBFS/live data and does not move network work to the Qt GUI thread.
- [ ] 7.12 Test theme starts dark on each new application instance, is not persisted, and does not materially change geometry at a fixed baseline window.
- [ ] 7.13 Test warranty/occupancy display never derives non-authoritative values from current schema-v4 records.
- [ ] 7.14 Test network presentation retains known port when switch IP is missing, shows safe no-data for missing port when switch IP is known, never groups unknown-switch records by port, and never fabricates unattached switches.

## 8. Manual visual acceptance

- [ ] 8.1 Launch the GUI as a detached process per `RULES.md`; use a `1440 x 900` logical-pixel baseline window in representative room mode.
- [ ] 8.2 Capture local, non-committed dark-theme screenshots and verify: toolbar/search dominance, visible selected-room cue, room/network peer-card ratio, spacing/radius scale, `52-64 px` equipment-row density, grouped expanded-card hierarchy, audio-meter geometry, and Matrix column hierarchy.
- [ ] 8.3 Toggle to light mode at the same window size, capture local non-committed screenshots, and verify the same geometry/hierarchy with readable primary/secondary/disabled/focus/status states.
- [ ] 8.4 Record the manual acceptance result in the implementation session report; screenshots remain local validation aids and SHALL NOT be committed unless the user explicitly requests tracked evidence.

## 9. Implementation verification and publication

- [ ] 9.1 Run focused tests for inventory search, room target resolution, fallback preservation, room session ordering, shell/theme, network partial evidence, accordion, and all four device presentation families.
- [ ] 9.2 Run the full required offline test suite and record fresh exact counts; do not copy prior counts.
- [ ] 9.3 Run:

```powershell
.\openspec.cmd validate room-diagnostic-modern-ui --strict
.\openspec.cmd validate --all --strict
git diff --check
git diff --cached --check
```

- [ ] 9.4 Synchronize implementation evidence/tasks only with commands actually executed on the current implementation HEAD.
- [ ] 9.5 Create one focused implementation commit and push `agent/room-diagnostic-modern-ui`; implementation session must not issue independent `APPROVE`.

## 10. Independent validation

- [ ] 10.1 Fetch current remote state and record current `master`, PR Draft/state/base/head, and `origin/agent/room-diagnostic-modern-ui` SHA.
- [ ] 10.2 Create a separate clean detached worktree from exact `origin/agent/room-diagnostic-modern-ui`; verify local HEAD equals recorded remote SHA and worktree is clean.
- [ ] 10.3 Independently review implementation against every approved contract, with special attention to fallback preservation, selected-room visibility/currentness, partial network evidence, no-widget network authority, no hidden future-control I/O, and unchanged credential/mutation safety.
- [ ] 10.4 Rerun fresh focused and full offline tests, strict change/all OpenSpec validation, `git diff --check`, and `git diff --cached --check`.
- [ ] 10.5 Repeat the baseline dark/light manual visual acceptance in the independent detached worktree/environment where GUI launch is available; if GUI launch is unavailable, report that limitation rather than claiming visual acceptance.
- [ ] 10.6 Perform the mandatory disposable archive-applicability check because this change modifies root requirements and adds a new root capability. Do not run archive on the primary feature branch for this check.
- [ ] 10.7 Independent validator must not fix its own findings. `READY FOR ARCHIVE` is permitted only with no CRITICAL/HIGH/MEDIUM findings and all mandatory checks passing on current remote HEAD.

## 11. Archive and completion

- [ ] 11.1 Archive only after an independent permitting verdict using:

```powershell
.\openspec.cmd archive room-diagnostic-modern-ui --yes
```

- [ ] 11.2 Review archive/root-spec diff, especially replacements in `diagnostic-application-shell`, `room-equipment-diagnostics`, `room-device-interaction-lifecycle`, the inventory query addition, and the new `diagnostic-ui-presentation` root spec.
- [ ] 11.3 Run full post-archive checks:

```powershell
.\openspec.cmd validate --all --strict
# full required offline test suite
git diff --check
git diff --cached --check
```

- [ ] 11.4 Create and push a dedicated archive commit.
- [ ] 11.5 Reconfirm current remote archive HEAD and current `master` before merge. Do not merge, close the PR, or delete the branch without explicit user authorization.
