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
- [ ] 2.2 Cover Unicode NFC/trim/casefold substring matching, room-id deduplication, duplicate room display names across distinct room IDs, conflicting names inside one room ID, zero/one/many matches, and deterministic result ordering.
- [ ] 2.3 Replace permanent IP-only input composition with IP-or-room target classification while preserving the operator's raw query text.
- [ ] 2.4 Implement autocomplete/dropdown selection for multi-match room queries; typing and selection alone must perform zero device network I/O.
- [ ] 2.5 Ensure editing the raw query invalidates stale selection/current room authority and increments request/currentness generation before any replacement I/O.
- [ ] 2.6 Keep IP zero/one/many semantics and legacy supported no-room single-device fallback behavior unchanged.
- [ ] 2.7 Keep room-name search fail-closed when inventory is unavailable; do not invoke model fallback for a room-name query.
- [ ] 2.8 Keep `Пароль` network-free and available only through a resolvable IP/model configuration context; room-name search must not choose a device model for credentials.

## 3. Direct room-name session composition

- [ ] 3.1 Allow room session construction with an exact selected `room_id` and no source record.
- [ ] 3.2 Preserve IP-entry source-first membership ordering; use pure canonical `record_id` ordering for direct room-name entry.
- [ ] 3.3 Preserve same-room duplicate-IP ambiguity, row eligibility, exact-model registry authority, credential planning, one-shot adapter boundaries, and strictly sequential automatic I/O.
- [ ] 3.4 Resolve shared room name/address/VIP source-first for IP entry and canonical-first for source-less room entry.
- [ ] 3.5 Verify the selected room remains bound to current inventory snapshot/query revision and stale autocomplete selections cannot create room authority.

## 4. Application shell and themes

- [ ] 4.1 Set the user-visible window title to `Диагностический модуль`.
- [ ] 4.2 Build the top toolbar/search layout using semantic components and preserve existing Refresh/Actions application intent boundaries.
- [ ] 4.3 Extend central theme tokens to dark and light palettes without per-widget persistence logic.
- [ ] 4.4 Start every process in dark mode and add a sun/moon session-only theme toggle.
- [ ] 4.5 Prove theme switching does not change target context, room generation, credentials, live/session ownership, or device I/O.

## 5. Room upper presentation

- [ ] 5.1 Implement the upper-left room card with room name, address, VIP, warranty, and occupancy rows.
- [ ] 5.2 Populate only current authoritative name/address/VIP. Render warranty and occupancy as `Нет данных`; do not infer values or change inventory schema in this change.
- [ ] 5.3 If a room-card refresh icon is included, wire it only as an alias of top full Refresh.
- [ ] 5.4 Implement the upper-right network-connections tree by grouping current room records using canonical `switch_ip_address`/`switch_port`.
- [ ] 5.5 Render deterministic attached-device children and a safe generic switch label when unique canonical switch-name evidence is unavailable.
- [ ] 5.6 Do not fabricate switches with zero attached canonical records. Keep `Нет подключенных устройств` as a supported presentation state only for authoritative empty switch nodes supplied by a future/other approved source.

## 6. Equipment accordion and device presentations

- [ ] 6.1 Standardize room row headers as `chevron -> class icon -> model -> status cue/text -> IP -> overflow` with non-color status cues.
- [ ] 6.2 Preserve one-expanded-row accordion behavior and exact-row presentation binding.
- [ ] 6.3 Rebuild audio DSP presentation with vertical segmented dBFS meters, selected-channel emphasis, and disabled future gain/mute controls.
- [ ] 6.4 Rebuild Matrix presentation as the approved per-input signal/HDCP/name/routing table while preserving existing routing intent/controller ownership.
- [ ] 6.5 Rebuild codec presentation into grouped state/call/audio/action cards while preserving existing supported live/call-log application boundaries.
- [ ] 6.6 Rebuild PDU presentation into grouped device/outlet/action cards while preserving existing PDU refresh/mutation/reconciliation boundaries.
- [ ] 6.7 Place reference-only future controls in their intended locations as disabled widgets with no connected network/mutation intent.
- [ ] 6.8 Keep reusable widgets presentation-only; no new widget may own credentials, handler/session objects, fallback indexes, request generation, timers, or direct network I/O.

## 7. Regression coverage

- [ ] 7.1 Test raw search text remains unchanged after IP resolution, single room-name resolution, multi-result selection, diagnostics, and top Refresh.
- [ ] 7.2 Test room-name zero/one/many resolution and selection currentness with zero device I/O before Enter/top Refresh.
- [ ] 7.3 Test direct room-name entry creates no synthetic source record and uses canonical row ordering.
- [ ] 7.4 Test IP entry still opens the complete room and retains source-first ordering.
- [ ] 7.5 Test target-search edits supersede/retire current room interaction under existing lifecycle rules.
- [ ] 7.6 Test common row statuses remain understandable without color alone and one-row accordion behavior remains deterministic.
- [ ] 7.7 Test future placeholder controls are disabled and cannot emit application/network intents.
- [ ] 7.8 Test Matrix route clicks still cross only the Matrix intent boundary; restyling must not introduce direct handler calls.
- [ ] 7.9 Test audio meter restyling preserves authoritative dBFS/live data and does not move network work to the Qt GUI thread.
- [ ] 7.10 Test theme starts dark on each new application instance and is not persisted.
- [ ] 7.11 Test warranty/occupancy display never derives non-authoritative values from current schema-v4 records.
- [ ] 7.12 Test network grouping never fabricates an unattached switch from missing evidence.

## 8. Implementation verification and publication

- [ ] 8.1 Run focused tests for inventory search, room target resolution, room session ordering, shell/theme, accordion, and all four device presentation families.
- [ ] 8.2 Run the full required offline test suite and record fresh exact counts; do not copy prior counts.
- [ ] 8.3 Run:

```powershell
.\openspec.cmd validate room-diagnostic-modern-ui --strict
.\openspec.cmd validate --all --strict
git diff --check
git diff --cached --check
```

- [ ] 8.4 Synchronize implementation evidence/tasks only with commands actually executed on the current implementation HEAD.
- [ ] 8.5 Create one focused implementation commit and push `agent/room-diagnostic-modern-ui`; implementation session must not issue independent `APPROVE`.

## 9. Independent validation

- [ ] 9.1 Fetch current remote state and record current `master`, PR Draft/state/base/head, and `origin/agent/room-diagnostic-modern-ui` SHA.
- [ ] 9.2 Create a separate clean detached worktree from exact `origin/agent/room-diagnostic-modern-ui`; verify local HEAD equals the recorded remote SHA and worktree is clean.
- [ ] 9.3 Independently review implementation against every approved contract, with special attention to no-widget network authority, search currentness, no hidden future-control I/O, and unchanged credential/mutation safety.
- [ ] 9.4 Rerun fresh focused and full offline tests, strict change/all OpenSpec validation, `git diff --check`, and `git diff --cached --check`.
- [ ] 9.5 Perform the mandatory disposable archive-applicability check because this change modifies root requirements and adds a new root capability. Do not run archive on the primary feature branch for this check.
- [ ] 9.6 Independent validator must not fix its own findings. `READY FOR ARCHIVE` is permitted only with no CRITICAL/HIGH/MEDIUM findings and all mandatory checks passing on current remote HEAD.

## 10. Archive and completion

- [ ] 10.1 Archive only after an independent permitting verdict using:

```powershell
.\openspec.cmd archive room-diagnostic-modern-ui --yes
```

- [ ] 10.2 Review archive/root-spec diff, especially replacements in `diagnostic-application-shell`, `room-equipment-diagnostics`, `room-device-interaction-lifecycle`, the inventory query addition, and the new `diagnostic-ui-presentation` root spec.
- [ ] 10.3 Run full post-archive checks:

```powershell
.\openspec.cmd validate --all --strict
# full required offline test suite
git diff --check
git diff --cached --check
```

- [ ] 10.4 Create and push a dedicated archive commit.
- [ ] 10.5 Reconfirm current remote archive HEAD and current `master` before merge. Do not merge, close the PR, or delete the branch without explicit user authorization.
