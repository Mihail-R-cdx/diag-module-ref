# Change: Modernize expanded Matrix diagnostics

## Why

The merged `room-diagnostic-modern-ui` foundation established the common room shell, target-search, room/network cards, exact-row accordion, themes, and serialized post-cycle interaction authority while deliberately deferring final Matrix/IN1804 family presentation to a dedicated change. MIH-10 then completed the Audio DSP family redesign independently. MIH-11 now applies the same split discipline to Matrix/Extron IN1804 only.

Current `master` renders the expanded room Matrix row through `RoomDiagnosticTreeWidget` -> `RoomReadOnlyPresentation._build_matrix()`. The standalone `MatrixScreen` is a separate screen with a real `routeRequested` intent connected to `MatrixController`; it is not room authority and must not be embedded or promoted merely to obtain routing behavior.

The accepted Matrix visual target is a compact three-area layout inside the existing expanded room row: a narrow `Общая информация` card on the left, a dominant central `Матрица (входы и коммутация)` table, and a narrow `Быстрые действия` card on the right. Field placement and hierarchy SHALL follow that approved reference without requiring pixel-perfect reproduction or access to the original image during implementation/review.

MIH-11 also makes room Matrix routing interactive. That requires the Matrix snapshot consumed by presentation and reconciliation to be truthful. Current legacy normalization can synthesize `inputs_num = 8`, can turn missing/malformed connection evidence into `current_connection = 1`, and can collapse failed/unknown HDCP reads into false-like zero values. Those defaults are safe only as legacy presentation conveniences; they are not acceptable authority for a state-changing room route. MIH-11 therefore includes a minimum fail-closed normalization correction for existing IN1804 reads, without adding new SIS commands.

## What Changes

- Redesign only the **expanded Extron IN1804 exact-row presentation inside the common room accordion**.
- At the foundation baseline viewport, render Matrix content as three horizontal peer cards in this order:
  1. `Общая информация` (narrow);
  2. `Матрица (входы и коммутация)` (dominant);
  3. `Быстрые действия` (narrow).
- In `Общая информация`, reserve rows in the approved visual order: `Модель`, `MAC-адрес`, `Серийный номер`, `Версия прошивки`, `Температура`, `Время работы`.
- Do not add protocol reads merely to fill those rows. On the current change base, absent MAC/serial/firmware/uptime evidence renders `Нет данных` or the common safe no-data equivalent.
- Replace the current room Matrix table hierarchy with the reference order:
  - compact input ordinal;
  - `Сигнал`;
  - `HDCP`;
  - `Входы` (input name);
  - output column using accepted output name, falling back to `Main Output`.
- Render only a **proven accepted current input count/order**. The reference's example row count is not authority and SHALL NOT hard-code eight inputs. Legacy constructor/parser default `8` SHALL NOT become accepted evidence when input count/model capability is unproven.
- Correct existing Matrix normalization, without new SIS reads, so empty/malformed/unknown route evidence yields `current_connection = None`/UNKNOWN rather than input 1, and unproven input count remains unknown rather than eight.
- Normalize the per-input HDCP **presence flag** as tri-state evidence: confirmed present -> present, confirmed absent -> absent, failed/malformed/unrecognized -> unknown. The room `HDCP` column SHALL show only `есть`, `нет`, or `Нет данных`; it SHALL NOT show `2.2`, `1.4`, another version token, the HDCP authorization configuration value, or output HDCP status.
- Preserve non-color text/cue meaning for signal, HDCP presence, and route state.
- Make non-active output cells actionable only when the exact current Matrix row is connected, current, unblocked, has proven accepted input authority, and its unified registration declares the MIH-11 Matrix room mutation/reconciliation bindings.
- Clicking an actionable output-1 cell produces only a non-secret exact-row route intent. After **explicit operator confirmation**, application composition submits it through the existing serialized room mutation lifecycle; the presentation never calls `ExtronIN1804Handler` or `MatrixController` directly.
- Add exact Matrix room mutation/reconciliation bindings to the unified model registration; do not create a parallel Matrix model/capability list.
- Preserve application-owned credential selection/fallback. A structured authentication rejection proven before route delivery may advance to the next approved candidate after cleanup. Once route send was attempted or may have been delivered, no automatic replay or credential advance is permitted.
- Treat route ACK/transport success as non-authoritative. Mandatory reconciliation reads the exact current Matrix row and confirms success only when truthful normalized `current_connection == requested input`. UNKNOWN/missing/malformed readback can never confirm the mutation.
- Map `Обновить статус` in Quick actions to the existing exact-row Local Refresh intent.
- Keep `Перезагрузить устройство` as a visible disabled/non-actionable reference-layout placeholder because current approved Extron IN1804 capability has no reboot mutation.
- **Do not render `Открыть расширенный экран` at all in MIH-11.** There is no enabled control, disabled placeholder, navigation intent, or acceptance requirement for it. Standalone `MatrixScreen` remains a separate existing surface.
- Preserve dark/light theme compatibility and the foundation one-expanded-row/common-header contract.

## Capabilities

### Changed capabilities

- `diagnostic-ui-presentation`: adds the final Matrix/IN1804 family-specific expanded visual contract and supersedes the foundation's temporary read-only Matrix room presentation for MIH-11.
- `device-diagnostics-and-control`: tightens existing Extron IN1804 normalization for the already-read input count, route readback, and HDCP input-status evidence so missing/failed/malformed data remains UNKNOWN instead of becoming fabricated routing authority.

### New room interaction specialization

- `room-device-interaction-lifecycle`: authorizes Extron IN1804 room routing through the existing serialized `MUTATION -> RECONCILIATION` architecture, with exact-row currentness, one-send mutation safety, structured pre-delivery credential fallback only, mandatory truthful readback, and fail-closed ambiguous outcomes.

### Existing authorities retained

This change does not redefine or take ownership of:

- target-search, selected-room, canonical room ID, or exact `record_id` authority;
- common equipment-row header or one-expanded-row behavior;
- automatic room queue ordering;
- credential loading, credential selection/fallback policy, or successful credential memory;
- transport/authentication classification rules;
- room interaction generation/currentness and stale callback rejection;
- Matrix SIS command set or command syntax; normalization corrections use existing reads only;
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

Within the central table, the input number remains compact and the input-name/output columns receive the largest semantic width. Exact pixel values are presentation tuning; required order/hierarchy and absence of baseline horizontal clipping are normative.

The approved general-information rows are layout slots, not permission to fabricate data. Current Matrix acquisition does not authoritatively provide MAC, serial, firmware, or uptime; those rows remain truthful no-data presentation in MIH-11. A later reviewed diagnostic-data change may add source support without changing this visual slot order.

The `HDCP` column is deliberately **not a version column**. It is a current per-input HDCP-presence projection only: `есть`, `нет`, or `Нет данных`.

## Interaction boundary

Room Matrix routing SHALL use the unified exact-model registration and one application-owned room interaction lane:

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
-> accept cache only if truthful normalized current_connection == requested input
```

The implementation MAY reuse existing `MatrixController` transport/session primitives through a focused room adapter or use a dedicated background room route adapter, but it SHALL NOT use global widget selection as target authority, SHALL NOT wire standalone `MatrixScreen.routeRequested` into room mode, and SHALL NOT keep a route session alive in a way that overlaps mandatory reconciliation.

If implementation cannot prove physical/authoritative release between mutation transport ownership and reconciliation, it must return for architecture review rather than weakening the serialized lifecycle.

## Non-Goals

- No Audio DSP, codec, or PDU redesign.
- No changes to room/network cards, target-search, themes, title, or common accordion header geometry.
- No new Matrix polling interval or second live lane.
- No new protocol command solely for MAC, serial, firmware, uptime, HDCP-version enrichment, reboot, or expanded-screen navigation.
- No HDCP version display.
- No Matrix reboot implementation.
- No `Открыть расширенный экран` affordance in the room Matrix dashboard.
- No promotion/embedding of standalone `MatrixScreen` as room authority.
- No direct handler/session/credential ownership in table/card widgets.
- No credential selection or fallback inside Matrix handler/worker code.
- No string heuristic (`auth`, `401`, `403`, etc.) for credential advancement.
- No blind retry of a route after its send was attempted or outcome became ambiguous.
- No treating route ACK or synthetic/default parser values as authoritative final connection state.
- No hard-coded eight-input UI contract.

## Expected implementation surface

The normative implementation target is the current room-mode exact-row surface and SHALL be reconfirmed against current source before coding. Expected files include:

- `gui/room_diagnostic_tree.py` for Matrix presentation/view-model and room-safe Matrix route intent signal;
- `gui/diagnostic_dispatch.py` for exact Extron IN1804 mutation/reconciliation binding declaration;
- `gui/main_window.py` for composition-owned confirmation, Matrix room mutation binding, credential attempt ownership, and reconciliation wiring;
- `handlers/extron/in1804.py` and `core/parser.py` for **normalization-only corrections of existing reads**: remove fabricated input-count/route defaults and preserve HDCP unknown vs absent; no new SIS commands are authorized;
- a focused background Matrix room route adapter/controller extension where needed to execute one exact-context state-changing send outside the GUI thread;
- focused Matrix room presentation/normalization/lifecycle regression tests;
- `gui/theme.py` only if Matrix-specific semantic presentation tokens are required.

`gui/screens/matrix_screen.py` and `gui/matrix_controller.py` remain useful current-source references for existing standalone routing semantics. They are not automatically the room implementation target. Any reuse must preserve exact room context and the single room lifecycle; standalone/global widget context SHALL NOT become room authority.

## Dependencies

- Change base: current `master` after merged MIH-9 foundation and merged MIH-10 Audio DSP change.
- Change base SHA at architecture creation: `f77b74a7fca0174a303e16682f4898cce11a36ef`.
- Current root `diagnostic-ui-presentation` remains authority for shell geometry, themes, common accordion semantics, and exact-row presentation ownership.
- Current root `room-device-interaction-lifecycle` remains authority for one serialized lane, exact-row contexts, mutation locks, one-send ambiguity handling, and mandatory reconciliation.
- Current root `device-diagnostics-and-control` remains authority for supported Extron diagnostic/control capability; MIH-11 adds fail-closed Matrix normalization without adding a new protocol read.
- Current standalone Matrix route behavior remains regression authority where compatible with the tightened normalization contract.

## Validation direction

Architecture review SHALL verify the visual hierarchy against this self-contained contract, verify truthful no-data/UNKNOWN semantics, and verify that room routing is enabled only through unified registry + serialized mutation/reconciliation authority.

Implementation validation SHALL include:

- focused Matrix normalization tests for unproven input count, empty/malformed connection response, current-connection UNKNOWN, and HDCP present/absent/unknown;
- explicit regression proving a requested Input 1 route cannot reconcile successfully when route readback is empty, malformed, failed, or unknown;
- focused Matrix room presentation tests for field order, card order, dynamic proven input count, output naming, signal/HDCP-presence/route non-color states, dark/light rendering, and safe no-data slots;
- focused Matrix route-intent tests proving no direct widget I/O;
- registry tests proving Extron IN1804 declares exactly approved room mutation/reconciliation binding and no parallel model list exists;
- mutation tests for explicit confirmation, live retirement, exact-row context, pre-delivery structured auth fallback, at-most-one send, stale rejection, mandatory reconciliation, readback match/mismatch/unknown, and blocked/unconfirmed ambiguous outcomes;
- regression tests for existing standalone Matrix routing and current room live/local Refresh;
- common accordion/theme regressions;
- full offline tests;
- repository-local `\.\openspec.cmd validate matrix-diagnostic-modern-ui --strict` and `\.\openspec.cmd validate --all --strict`;
- `git diff --check` and `git diff --cached --check`.

Manual visual acceptance SHALL capture the expanded Matrix room row at `1440 x 900` in dark and light themes and verify the three-card hierarchy, table-field placement, HDCP presence-only projection, absence of `Открыть расширенный экран`, and truthful no-data states. Screenshots are local validation evidence only unless explicitly requested as tracked evidence.
