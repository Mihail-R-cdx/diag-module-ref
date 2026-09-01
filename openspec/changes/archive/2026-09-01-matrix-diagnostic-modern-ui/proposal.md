# Change: Modernize expanded Matrix diagnostics

## Why

The merged `room-diagnostic-modern-ui` foundation established the room shell, target-search, room/network cards, exact-row accordion, themes, and serialized post-cycle interaction authority while deliberately deferring final Matrix/IN1804 family presentation. MIH-10 then completed the Audio DSP family redesign independently. During MIH-11 implementation and visual acceptance, the user also approved a presentation-only refinement of the common room shell. MIH-11 therefore owns both the Matrix/IN1804 family presentation and that common visual refinement; it does not expand lifecycle, data, security, credential, or device-I/O scope.

Current `master` renders the expanded room Matrix row through `RoomDiagnosticTreeWidget` -> `RoomReadOnlyPresentation._build_matrix()`. The standalone `MatrixScreen` is a separate screen with a real `routeRequested` intent connected to `MatrixController`; it is not room authority and must not be embedded or promoted merely to obtain routing behavior.

The accepted Matrix visual target is a compact three-area layout inside the existing expanded room row: a narrow `Общая информация` card on the left, a dominant central `Матрица (входы и коммутация)` table, and a narrow `Быстрые действия` card on the right. Field placement and hierarchy SHALL follow that approved reference without requiring pixel-perfect reproduction or access to the original image during implementation/review.

MIH-11 also makes room Matrix routing interactive. That requires the Matrix snapshot consumed by presentation and reconciliation to be truthful. Current legacy normalization can synthesize `inputs_num = 8`, can turn missing/malformed connection evidence into `current_connection = 1`, can collapse failed/unknown HDCP reads into false-like zero values, and can expose no-evidence device information as `Unknown` model or `0` temperature. Those defaults are safe only as legacy presentation conveniences; they are not acceptable current device authority. MIH-11 therefore includes a minimum fail-closed normalization correction for existing IN1804 reads, without adding new SIS commands.

## What Changes

- Apply the user-approved presentation-only common room refinement: titled peer room/network upper cards, compact switch-summary table, compact card-like equipment rows, and no separate visible cycle-status line between those cards and the accordion.
- Redesign the **expanded Extron IN1804 exact-row presentation inside the refined common room accordion**.
- At the foundation baseline viewport, render Matrix content as three horizontal peer cards in this order:
  1. `Общая информация` (narrow);
  2. `Матрица (входы и коммутация)` (dominant);
  3. `Быстрые действия` (narrow).
- In `Общая информация`, reserve rows in the approved visual order: `Модель`, `MAC-адрес`, `Серийный номер`, `Версия прошивки`, `Температура`, `Время работы`.
- Do not add protocol reads merely to fill those rows. On the current change base, absent MAC/serial/firmware/uptime evidence renders `Нет данных` or the common safe no-data equivalent. Existing model/temperature reads also become fail-closed: missing/failed model -> no-data rather than local `Unknown`; missing/failed/malformed temperature -> no-data rather than synthetic zero; a real reported numeric zero remains valid.
- Replace the current room Matrix table hierarchy with the reference order:
  - compact input ordinal;
  - `Сигнал`;
  - `HDCP`;
  - `Входы` (input name);
  - output column using accepted output name, falling back to `Main Output`.
- Render only a **proven accepted current input count/order**. The reference's example row count is not authority and SHALL NOT hard-code eight inputs. Legacy constructor/parser default `8` SHALL NOT become accepted evidence when input count/model capability is unproven.
- Correct existing Matrix normalization, without new SIS reads, so empty/malformed/unknown route evidence yields `current_connection = None`/UNKNOWN rather than input 1, and unproven input count remains unknown rather than eight.
- Make current-input `!` parsing explicit rather than heuristic: after normal framing and optional removal of one exact `!` echo line, accept exactly one ordinal-only untagged response or one exact `In<N> All` tagged/verbose response; require exactly one in-range ordinal; extra payload, multiple numeric candidates, unrelated digits, partial matches, echo-only, or out-of-range values are UNKNOWN.
- Normalize existing per-input HDCP status with exact tri-state semantics: raw `2 -> True`, `1 -> False`, `0 -> False`, and failed/missing/malformed/unrecognized -> `None`. The room `HDCP` column SHALL show only `есть`, `нет`, or `Нет данных`; it SHALL NOT show `2.2`, `1.4`, another version token, the HDCP authorization configuration value, or output HDCP status.
- Project Matrix Signal and route as compact filled/open indicators while retaining their non-color semantic values in tooltips, accessibility, or data roles; HDCP remains textual.
- Make non-active output cells actionable only when the exact current Matrix row is connected, current, unblocked, has proven accepted input authority, and its unified registration declares the MIH-11 Matrix room mutation/reconciliation bindings.
- Clicking an actionable output-1 cell produces only a non-secret exact-row route intent. After **explicit operator confirmation**, application composition submits it through the existing serialized room mutation lifecycle; the presentation never calls `ExtronIN1804Handler` or `MatrixController` directly.
- Add exact Matrix room mutation/reconciliation bindings to the unified model registration; do not create a parallel Matrix model/capability list.
- Preserve application-owned credential selection/fallback. A structured authentication rejection proven before route delivery may advance to the next approved candidate after cleanup. Once route send was attempted or may have been delivered, no automatic replay or credential advance is permitted.
- Treat route ACK/transport success as non-authoritative. Mandatory reconciliation reads the exact current Matrix row and confirms success only when truthful normalized `current_connection == requested input` from one exact accepted `!` response family. UNKNOWN/missing/malformed/ambiguous readback can never confirm the mutation.
- Map `Обновить статус` in Quick actions to the existing exact-row Local Refresh intent.
- Keep `Перезагрузить устройство` as a visible disabled/non-actionable reference-layout placeholder because current approved Extron IN1804 capability has no reboot mutation.
- **Do not render `Открыть расширенный экран` at all in MIH-11.** There is no enabled control, disabled placeholder, navigation intent, or acceptance requirement for it. Standalone `MatrixScreen` remains a separate existing surface.
- Preserve dark/light theme compatibility and the one-expanded-row contract.

## Capabilities

### Changed capabilities

- `diagnostic-ui-presentation`: adds the final Matrix/IN1804 expanded visual contract and reconciles the approved presentation-only common room shell with the former provisional foundation geometry.
- `device-diagnostics-and-control`: tightens existing Extron IN1804 normalization for the already-read input count, device-info model/temperature, exact current-input response grammar, route readback, and HDCP input-status evidence so missing/failed/malformed data remains UNKNOWN instead of becoming fabricated authority.

### New room interaction specialization

- `room-device-interaction-lifecycle`: authorizes Extron IN1804 room routing through the existing serialized `MUTATION -> RECONCILIATION` architecture, with exact-row currentness, one-send mutation safety, structured pre-delivery credential fallback only, mandatory truthful readback, and fail-closed ambiguous outcomes.

### Existing authorities retained

This change does not redefine or take ownership of:

- target-search, selected-room, canonical room ID, or exact `record_id` authority;
- one-expanded-row behavior;
- automatic room queue ordering;
- credential loading, credential selection/fallback policy, or successful credential memory;
- transport/authentication classification rules;
- room interaction generation/currentness and stale callback rejection;
- Matrix SIS command set or command syntax; normalization corrections use existing reads only;
- background-thread ownership or Qt GUI-thread safety;
- standalone Matrix screen lifecycle;
- room live/local-refresh semantics except where live must retire under the already-approved mutation lock matrix.

## Product/visual decisions captured by this change

The Matrix expanded content and common room shell SHALL visually correspond to the approved product decision. The accepted common shell keeps peer upper cards at a baseline height of about `186` logical pixels, labels them `Информация о комнате` and `Сетевые подключения (N коммутаторов)`, presents network evidence as a compact three-column switch summary, and uses approximately `42` logical-pixel equipment rows with `28 x 28` device-class icons. These are presentation choices only: canonical records, exact-row identity, queue order, lifecycle, credentials, and device I/O remain unchanged.

At `1440 x 900` logical pixels, the expanded Matrix content uses a horizontal three-card hierarchy with approximate content-width shares:

```text
General information      25%
Matrix table             53%
Quick actions            22%
```

Within the central table, the input number remains compact and the input-name/output columns receive the largest semantic width. Exact pixel values are presentation tuning; required order/hierarchy and absence of baseline horizontal clipping are normative.

The approved general-information rows are layout slots, not permission to fabricate data. Current Matrix acquisition does not authoritatively provide MAC, serial, firmware, or uptime; those rows remain truthful no-data presentation in MIH-11. Model/temperature remain existing reads, but only successful current values are accepted; local `Unknown`/synthetic `0` defaults are no-data, while a genuinely reported numeric zero remains a real temperature.

The `HDCP` column is deliberately **not a version column**. It is a current per-input HDCP-presence projection only: `есть`, `нет`, or `Нет данных`. Signal and route cells use accepted compact indicators, with semantic states retained in non-color accessible/data projections. Existing status `0` is a confirmed `нет` because no source/sink means no current HDCP; acquisition failure is separately `Нет данных`.

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

- No Audio DSP, codec, or PDU family-specific redesign.
- No target-search, title, data-model, lifecycle, security, or credential-policy change; common room changes are presentation only.
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

- `gui/room_diagnostic_tree.py` for the common room refinement, Matrix presentation/view-model, and room-safe Matrix route intent signal;
- `gui/diagnostic_dispatch.py` for exact Extron IN1804 mutation/reconciliation binding declaration;
- `gui/main_window.py` for composition-owned confirmation, Matrix room mutation binding, credential attempt ownership, and reconciliation wiring;
- `handlers/extron/in1804.py` and `core/parser.py` for **normalization-only corrections of existing reads**: remove fabricated input-count/route/model/temperature defaults, implement exact current-input response grammar, and preserve HDCP unknown vs confirmed absence with raw `2/1/0 -> True/False/False`; no new SIS commands are authorized;
- a focused background Matrix room route adapter/controller extension where needed to execute one exact-context state-changing send outside the GUI thread;
- focused Matrix room presentation/normalization/lifecycle regression tests;
- `gui/theme.py` for the common/Matrix semantic presentation tokens where required.

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

- focused Matrix normalization tests for unproven input count; model/temperature no-evidence behavior; exact untagged/tagged/echo current-input response forms; malformed/multiple-token/out-of-range connection responses; current-connection UNKNOWN; and exact HDCP raw-status mapping `2/1/0 -> True/False/False` plus unknown failures;
- explicit regression proving a requested Input 1 route cannot reconcile successfully when route readback is empty, malformed, ambiguous, failed, outside exact grammar, or unknown;
- focused Matrix room presentation tests for field order, card order, dynamic proven input count, output naming, signal/HDCP-presence/route non-color states, dark/light rendering, and safe no-data slots;
- focused Matrix route-intent tests proving no direct widget I/O;
- registry tests proving Extron IN1804 declares exactly approved room mutation/reconciliation binding and no parallel model list exists;
- mutation tests for explicit confirmation, live retirement, exact-row context, pre-delivery structured auth fallback, at-most-one send, stale rejection, mandatory reconciliation, readback match/mismatch/unknown, and blocked/unconfirmed ambiguous outcomes;
- regression tests for existing standalone Matrix routing and current room live/local Refresh;
- common accordion/theme regressions;
- full offline tests;
- repository-local `\.\openspec.cmd validate matrix-diagnostic-modern-ui --strict` and `\.\openspec.cmd validate --all --strict`;
- `git diff --check` and `git diff --cached --check`.

The user approved the current visual target during implementation/visual acceptance. This approved product decision is provenance for the reconciliation; the resulting OpenSpec is the self-contained authority and no tracked screenshot is implied. Independent validation remains required for the new reconciliation commit.
