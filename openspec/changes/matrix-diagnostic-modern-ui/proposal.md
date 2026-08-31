# Change: Modernize expanded Matrix diagnostics

## Why

The merged `room-diagnostic-modern-ui` foundation established the common room shell, target-search, room/network cards, exact-row accordion, themes, and serialized post-cycle interaction authority while deliberately deferring final Matrix/IN1804 family presentation to a dedicated change. MIH-10 then completed the Audio DSP family redesign independently. MIH-11 now applies the same split discipline to Matrix/Extron IN1804 only.

Current `master` renders the expanded room Matrix row through `RoomDiagnosticTreeWidget` -> `RoomReadOnlyPresentation._build_matrix()`. That room presentation is intentionally read-only and currently reduces the accepted Matrix snapshot to a generic information form plus a five-column routing table. The standalone `MatrixScreen` is a separate screen with a real `routeRequested` intent connected to `MatrixController`; it is not room authority and must not be embedded or promoted merely to obtain routing behavior.

The accepted Matrix visual target is a compact three-area layout inside the existing expanded room row: a narrow `Общая информация` card on the left, a dominant central `Матрица (входы и коммутация)` table, and a narrow `Быстрые действия` card on the right. Field placement and hierarchy SHALL follow that approved reference without requiring pixel-perfect reproduction or access to the original image during implementation/review. The repository-local OpenSpec contract therefore records the card order, field order, table column order, proportions, status semantics, and action boundaries explicitly.

The Matrix table must also restore real routing interaction in room mode. That does not authorize a direct widget-to-handler path. Room routing must enter the already-approved application-owned `MUTATION -> RECONCILIATION` lifecycle, remain bound to the exact expanded record, use application-selected credentials, stop/retire live ownership before sending, send the state-changing route at most once, and accept the new route as authoritative only after exact-row readback confirms it.

## What Changes

- Redesign only the **expanded Extron IN1804 exact-row presentation inside the common room accordion**.
- At the foundation baseline viewport, render Matrix content as three horizontal peer cards in this order:
  1. `Общая информация` (narrow);
  2. `Матрица (входы и коммутация)` (dominant);
  3. `Быстрые действия` (narrow).
- In `Общая информация`, reserve rows in the approved visual order: `Модель`, `MAC-адрес`, `Серийный номер`, `Версия прошивки`, `Температура`, `Время работы`.
- Do not add protocol reads merely to fill those rows. On the current change base, only fields already established by the accepted Matrix snapshot are shown as data; absent MAC/serial/firmware/uptime evidence renders `Нет данных` or the common safe no-data equivalent.
- Replace the current room Matrix table hierarchy with the reference order:
  - compact input ordinal;
  - `Сигнал`;
  - `HDCP`;
  - `Входы` (input name);
  - output column using accepted output name, falling back to `Main Output`.
- Render exactly the accepted current input count/order; the reference's example row count is not an authority and SHALL NOT hard-code eight inputs.
- Preserve non-color text/cue meaning for signal, HDCP, and route state. Sample reference values such as `2.2` are visual examples only; the GUI SHALL not invent an HDCP version absent from accepted normalized evidence.
- Make non-active output cells actionable only when the exact current Matrix row is connected, current, unblocked, and its unified registration declares the MIH-11 Matrix room mutation/reconciliation bindings.
- Clicking an actionable output-1 cell produces only a non-secret exact-row route intent. After explicit confirmation, application composition submits it through the existing serialized room mutation lifecycle; the presentation never calls `ExtronIN1804Handler` or `MatrixController` directly.
- Add exact Matrix room mutation/reconciliation bindings to the unified model registration; do not create a parallel Matrix model/capability list.
- Preserve application-owned credential selection/fallback. A structured authentication rejection proven before route delivery may advance to the next approved candidate after cleanup. Once the route send was attempted or may have been delivered, no automatic replay or credential advance is permitted.
- Treat route ACK/transport success as non-authoritative. Mandatory reconciliation reads the exact current Matrix row and must confirm `current_connection == requested input` before the accepted room cache is replaced/unblocked.
- Map `Обновить статус` in Quick actions to the existing exact-row Local Refresh intent.
- Keep `Перезагрузить устройство` as a visible disabled/non-actionable reference-layout placeholder because the current approved Extron IN1804 capability has no reboot mutation.
- If `Открыть расширенный экран` is rendered to preserve the visual hierarchy, it is a disabled/non-actionable placeholder in this change. Standalone `MatrixScreen` is not promoted into room authority and no second Matrix lifecycle is opened from it.
- Preserve dark/light theme compatibility and the foundation one-expanded-row/common-header contract.

## Capabilities

### Changed capability

- `diagnostic-ui-presentation`: adds the final Matrix/IN1804 family-specific expanded visual contract and supersedes the foundation's temporary read-only Matrix room presentation for MIH-11.

### New room interaction specialization

- `room-device-interaction-lifecycle`: authorizes Extron IN1804 room routing through the existing serialized `MUTATION -> RECONCILIATION` architecture, with exact-row currentness, one-send mutation safety, structured pre-delivery credential fallback only, mandatory readback, and fail-closed ambiguous outcomes.

### Existing authorities retained

This change does not redefine or take ownership of:

- target-search, selected-room, canonical room ID, or exact `record_id` authority;
- common equipment-row header or one-expanded-row behavior;
- automatic room queue ordering;
- credential loading, credential selection/fallback policy, or successful credential memory;
- transport/authentication classification rules;
- room interaction generation/currentness and stale callback rejection;
- Matrix handler protocol implementation or SIS command syntax;
- background-thread ownership or Qt GUI-thread safety;
- standalone Matrix screen lifecycle;
- room live/local-refresh semantics except where live must retire under the already-approved mutation lock matrix.

## Product/visual decisions captured by this change

The Matrix expanded content SHALL visually correspond to the approved reference while fitting the already-merged foundation shell. The common accordion header remains foundation-owned and is not redesigned by MIH-11.

At `1440 x 900` logical pixels, the expanded Matrix content uses a horizontal three-card hierarchy with approximate content-width shares:

```text
General information      24-28%
Matrix table             50-56%
Quick actions            18-22%
```

Within the central table, the input number remains compact and the input-name/output columns receive the largest semantic width. Exact pixel values are presentation tuning; the required order/hierarchy and absence of baseline horizontal clipping are normative.

The approved general-information rows are layout slots, not permission to fabricate data. Current authoritative Matrix parsing exposes model/temperature plus routing-related evidence but not authoritative MAC, serial, firmware, or uptime. Missing values therefore remain truthful no-data presentation in MIH-11. A later reviewed diagnostic-data change may add protocol/source support without changing this visual slot order.

## Interaction boundary

Room Matrix routing SHALL use the unified exact-model registration and one application-owned room interaction lane. The intended composition shape is:

```text
current expanded Extron IN1804 record
-> presentation emits non-secret output=1/input=N intent
-> explicit operator confirmation
-> RoomInteractionCoordinator confirms MUTATION
-> unified registry matrix_room_route binding
-> background exact-context route adapter with one application-selected credential attempt
-> at most one route send
-> mutation terminal success/ACK remains non-authoritative
-> matrix_room_route_reconcile binding
-> exact-row read-only reconciliation
-> accept cache only if current_connection == requested input
```

The implementation MAY reuse existing `MatrixController` transport/session primitives through a focused room adapter or use a dedicated background room route adapter, but it SHALL NOT use global widget selection as target authority, SHALL NOT wire standalone `MatrixScreen.routeRequested` into room mode, and SHALL NOT keep a route session alive in a way that overlaps mandatory reconciliation.

If an implementation approach cannot prove physical/authoritative release between mutation transport ownership and reconciliation, it must return for architecture review rather than weakening the serialized lifecycle.

## Non-Goals

- No Audio DSP, codec, or PDU redesign.
- No changes to room/network cards, target-search, themes, title, or common accordion header geometry.
- No new Matrix polling interval or second live lane.
- No new protocol command solely for MAC, serial, firmware, uptime, HDCP-version enrichment, reboot, or expanded-screen navigation.
- No Matrix reboot implementation.
- No promotion/embedding of standalone `MatrixScreen` as room authority.
- No direct handler/session/credential ownership in table/card widgets.
- No credential selection or fallback inside Matrix handler/worker code.
- No string heuristic (`auth`, `401`, `403`, etc.) for credential advancement.
- No blind retry of a route after its send was attempted or outcome became ambiguous.
- No treating route ACK as authoritative final connection state.
- No hard-coded eight-input UI contract.

## Expected implementation surface

The normative implementation target is the current room-mode exact-row surface and SHALL be reconfirmed against current source before coding. Expected files include:

- `gui/room_diagnostic_tree.py` for Matrix presentation/view-model and the room-safe Matrix route intent signal;
- `gui/diagnostic_dispatch.py` for the exact Extron IN1804 mutation/reconciliation binding declaration;
- `gui/main_window.py` for composition-owned confirmation, Matrix room mutation binding, credential attempt ownership, and reconciliation wiring;
- a focused background Matrix room route adapter/controller extension where needed to execute one exact-context state-changing send outside the GUI thread;
- focused Matrix room presentation/lifecycle regression tests;
- `gui/theme.py` only if Matrix-specific semantic presentation tokens are required.

`gui/screens/matrix_screen.py` and `gui/matrix_controller.py` remain useful current-source references for existing standalone routing semantics. They are not automatically the implementation target. Any reuse must preserve exact room context and the single room lifecycle; standalone/global widget context SHALL NOT become room authority.

Changes to `handlers/extron/in1804.py` or `core/parser.py` are not expected for the visual/data slots described here. If implementation discovers that the accepted current evidence is insufficient for an explicitly normative value rather than merely a no-data slot, it SHALL stop and return for architecture review before adding protocol or parser scope.

## Dependencies

- Change base: current `master` after merged MIH-9 foundation and merged MIH-10 Audio DSP change.
- Change base SHA at architecture creation: `f77b74a7fca0174a303e16682f4898cce11a36ef`.
- Current root `diagnostic-ui-presentation` remains authority for shell geometry, themes, common accordion semantics, and exact-row presentation ownership.
- Current root `room-device-interaction-lifecycle` remains authority for one serialized lane, exact-row contexts, mutation locks, one-send ambiguity handling, and mandatory reconciliation.
- Current root `device-diagnostics-and-control` already recognizes Extron routing to output 1 as a supported Matrix operation; MIH-11 adds the room-safe binding/presentation rather than inventing a new SIS capability.
- Current `MatrixController`/handler behavior remains authority for standalone Matrix transport and one-send route safety where reused.

## Validation direction

Architecture review SHALL verify the visual hierarchy against this self-contained contract, not against hidden conversation context; verify that missing information-card fields remain truthful; and verify that room routing is enabled only through unified registry + serialized mutation/reconciliation authority.

Implementation validation SHALL include:

- focused Matrix room presentation tests for field order, card order, dynamic input count, output naming, non-color states, dark/light rendering, and safe no-data slots;
- focused Matrix route-intent tests proving no direct widget I/O;
- registry tests proving Extron IN1804 declares exactly the approved room mutation/reconciliation binding and no parallel model list exists;
- mutation tests for explicit confirmation, live retirement, exact-row context, pre-delivery structured auth fallback, at-most-one send, stale rejection, mandatory reconciliation, readback match/mismatch, and blocked/unconfirmed ambiguous outcomes;
- regression tests for existing standalone Matrix routing and current room live/local Refresh;
- common accordion/theme regressions;
- full offline tests;
- `./openspec.cmd`/`\.\openspec.cmd` repository-local strict validation as appropriate to platform;
- `git diff --check` and `git diff --cached --check`.

Manual visual acceptance SHALL capture the expanded Matrix room row at the foundation baseline `1440 x 900` in dark and light themes and verify the three-card hierarchy and table-field placement. These screenshots are local validation evidence only unless a later instruction explicitly requires tracked evidence.
