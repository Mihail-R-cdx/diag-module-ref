# Design: Modern Matrix/IN1804 room presentation

## Context

MIH-9 established the common room shell and exact-row accordion. MIH-10 independently modernized Audio DSP inside that shell. MIH-11 now owns only the Matrix/Extron IN1804 expanded room presentation and the minimum room-safe route interaction needed for the approved Matrix table.

Current `master` has three distinct Matrix concerns that must remain separated:

1. **Accepted Matrix evidence**
   - `ExtronIN1804Handler.get_full_status()` collects device/routing evidence.
   - `ExtronIN1804DataParser.parse()` publishes accepted normalized Matrix data.
   - Current accepted fields include model, temperature, input/output counts and names, signal evidence, HDCP evidence, current connection, and connection protocol.

2. **Standalone Matrix lifecycle**
   - `MatrixScreen` owns standalone presentation and emits `routeRequested`.
   - `MatrixController` owns standalone Matrix background refresh/route/session/currentness.
   - This standalone screen/controller pair is not room authority.

3. **Room Matrix lifecycle**
   - `RoomDiagnosticTreeWidget` owns room presentation only.
   - `RoomReadOnlyPresentation._build_matrix()` is the current Matrix room projection.
   - unified dispatch registers exact `Extron IN1804` with `matrix_one_shot` and `matrix_room_live`, but no room mutation binding.
   - `RoomInteractionCoordinator` owns one serialized room lane including generic `MUTATION` and `RECONCILIATION` semantics.

The redesign must use these existing boundaries rather than collapse them.

## Goals

- Match the approved Matrix reference hierarchy/field placement inside the foundation accordion.
- Keep the Matrix table visually dominant and operator-readable.
- Preserve truthful accepted evidence; do not fabricate reference sample values.
- Add exact-row room routing to output 1 through existing application-owned mutation safety.
- Preserve current Matrix live/local-refresh behavior and standalone behavior.
- Keep dark/light presentation geometry stable.
- Keep GUI network I/O off the Qt GUI thread.

## Non-goals

- No redesign of the common room header/shell.
- No Audio DSP/codec/PDU redesign.
- No protocol/data expansion for MAC, serial, firmware, uptime, reboot, or HDCP-version discovery.
- No standalone Matrix screen promotion into room mode.
- No second room route lane or direct widget-to-handler call.
- No mutation retry after possible route delivery.
- No change to Matrix SIS route semantics (output 1 only).

## Decision 1: The room exact-row surface is the normative Matrix target

The modern Matrix content is rendered by the current room path under `RoomDiagnosticTreeWidget`. `MatrixScreen` remains a standalone consumer/lifecycle.

Implementation may extract a presentation-only Matrix dashboard widget, but room mode remains acceptance authority. Such a widget may consume accepted data and emit safe local intents; it cannot own credentials, handlers, sessions, request generations, currentness, or device I/O.

The common accordion header is unchanged. The visual reference's device title/status row is satisfied by the already-merged common row header. MIH-11 starts below that header.

### Consequence

`Открыть расширенный экран`, if represented for reference-layout fidelity, is not a navigation authority in MIH-11. It remains disabled/non-actionable. Enabling it later requires explicit architecture for cross-surface lifecycle/target ownership.

## Decision 2: Three-card Matrix dashboard hierarchy

At the foundation baseline viewport (`1440 x 900` logical pixels), expanded Matrix content is one horizontal dashboard with this order:

```text
+-------------------------+--------------------------------------------------+--------------------+
| Общая информация       | Матрица (входы и коммутация)                    | Быстрые действия   |
| narrow                  | dominant                                          | narrow             |
+-------------------------+--------------------------------------------------+--------------------+
```

Approximate content-width shares:

```text
General information: 24-28%
Matrix table:        50-56%
Quick actions:       18-22%
```

The central Matrix card must remain the dominant region. Exact pixel dimensions and card gaps use current foundation/theme tokens rather than duplicating a Matrix-only spacing system.

At the foundation minimum supported window (`1180 x 720`), implementation may controlled-reflow auxiliary side cards (for example two side cards above/below the table) if required, but SHALL keep the Matrix table reachable, preserve its column order, and keep the active-route/action semantics usable. No baseline horizontal clipping is acceptable.

Dark/light theme switching changes semantic styling only. At the same viewport it must not intentionally change Matrix card order, table semantics, action availability, route authority, or trigger device work.

## Decision 3: General information card uses fixed visual slots and truthful evidence

The left card rows are always rendered in this visual order:

```text
Модель
MAC-адрес
Серийный номер
Версия прошивки
Температура
Время работы
```

The presentation may use deterministic accepted-key aliases only, for example:

```text
model                         -> Модель
mac / mac_address             -> MAC-адрес
serial / serial_number        -> Серийный номер
firmware / version            -> Версия прошивки
temperature                   -> Температура
uptime                        -> Время работы
```

Aliases are presentation mapping, not source inference. If accepted evidence does not contain a field, show `Нет данных` or the foundation safe no-data equivalent.

On the architecture base, Matrix accepted evidence does not authoritatively provide MAC, serial, firmware, or uptime. MIH-11 intentionally does not issue new protocol reads to fill these slots.

Do not substitute unrelated fields such as connection protocol or switch topology merely to avoid a no-data row; the product decision is the reference field placement.

## Decision 4: Matrix table column order is normative; row count is data-driven

The central table uses exactly this semantic order:

```text
[input ordinal] | Сигнал | HDCP | Входы | [accepted output-1 name / Main Output]
```

The leading input ordinal is compact and may have an empty visual header or accessible `№` label. The input-name column is the main wide descriptive input column. The output column is also wide enough for route state/action text.

Baseline width targets are proportional rather than pixel-perfect:

```text
ordinal       7-9%
Сигнал       18-21%
HDCP         16-18%
Входы        25-29%
output       26-30%
```

Implementation may tune within those ranges to account for font metrics/theme, but SHALL preserve order and hierarchy.

Rows are created from the accepted current input count/order. The screenshot's eight visible rows are illustrative only. MIH-11 SHALL NOT hard-code eight inputs. If the accepted Matrix snapshot says 4 inputs, render 4 rows; if another supported accepted payload exposes a different count through the same exact Matrix contract, render that accepted count.

The output header uses the first accepted output name when present/non-empty; otherwise `Main Output`.

## Decision 5: Signal, HDCP, and route cells preserve non-color meaning

### Signal

Signal presentation uses accepted `signal_status` for the exact input.

Minimum safe states:

```text
has_signal true       -> positive non-color cue + text equivalent to `есть`
has_signal false      -> neutral/negative non-color cue + `нет сигнала`
missing/unknown       -> neutral cue + `Нет данных`/`не определено`
```

Color may reinforce the state but never replace the text/cue.

### HDCP

The screenshot value `2.2` is not a data authority. MIH-11 renders only accepted normalized HDCP evidence from `input_hdcp_auth` / `input_hdcp_status` (or a future approved normalized equivalent already present in the accepted snapshot).

Presentation may show a meaningful accepted version/status token when the current normalized evidence actually establishes it. Otherwise it uses an honest state/no-data label. It SHALL NOT infer HDCP 2.2 from color, route state, signal presence, output status, model name, or reference artwork.

### Route/output

For output 1:

```text
current_connection == input N -> positive non-color cue + `активен`
other current input            -> neutral cue + `не выбран`
missing/unknown route evidence -> neutral cue + `Нет данных`
```

The accepted snapshot remains route-state authority. Local click/hover state never changes `активен` before reconciliation succeeds.

## Decision 6: Matrix route is a safe exact-row intent, not widget I/O

A non-active output cell may become actionable only when all are true:

- current row is exact `Extron IN1804`;
- row is the current expanded record;
- row has usable connected accepted state;
- row is not stale/degraded/blocked/unconfirmed;
- unified exact-model registration declares the approved Matrix mutation/reconciliation bindings;
- room interaction lane says mutation is currently allowed;
- accepted input ordinal is valid for the current accepted table.

The presentation emits only a non-secret immutable intent equivalent to:

```text
MatrixRoomRouteIntent(
    output_num = 1,
    input_num = N,
)
```

It carries no credential, handler/session, screen pointer, raw target-search, initial source record, or global widget context.

The current active output cell is not actionable: selecting an already-authoritative route sends no mutation.

The room composition layer receives the intent, verifies that the published `record_id` is still the current expanded row, and shows an explicit confirmation dialog. Cancel performs no lifecycle change and no I/O. Confirm passes the safe intent to `RoomInteractionCoordinator.confirm_mutation()`.

## Decision 7: Unified registration owns Matrix room mutation capability

No parallel model list is introduced.

The exact `Extron IN1804` registration adds explicit room bindings equivalent to:

```text
mutation_binding_key       = matrix_room_route
reconciliation_binding_key = matrix_room_route_reconcile
cleanup_binding_key         = existing room cleanup authority
```

Existing bindings remain:

```text
room_adapter_key = matrix_one_shot
live_binding_key = matrix_room_live
local refresh    = room_one_shot_refresh
```

Startup/composition validation must fail closed if the Matrix registration declares the new mutation binding but composition cannot resolve mutation/reconciliation/cleanup.

Widget class checks, model substrings, a `MATRIX_MUTATION_MODELS` list, or standalone `MatrixScreen.routeRequested` are not capability authority.

## Decision 8: Matrix mutation execution uses one exact credential attempt and one send

The room mutation adapter is application-owned and background-executed. It receives:

- immutable `RoomInteractionContext`;
- validated `MatrixRoomRouteIntent`;
- exactly one application-selected credential candidate/index for that attempt.

It SHALL check currentness before acquiring a Matrix handler/session or doing route I/O.

The adapter may reuse reviewed MatrixController transport primitives or a focused Matrix room worker, provided it preserves these invariants:

- handler/worker does not choose/iterate credential candidates;
- route send uses exact model/IP/context and output 1/input N;
- route send is marked non-replay-safe;
- no Qt GUI-thread I/O;
- no persistent route owner overlaps reconciliation;
- cleanup/release is bounded and observable.

### Authentication fallback

Only structured authentication rejection proven before the route command could have been delivered may return `RoomAuthenticationRejected` (or equivalent typed pre-delivery result) and allow composition to advance to the next approved candidate after cleanup.

If authentication/transport/session failure is observed after route send was invoked or delivery is ambiguous, classify the result as ambiguous/unconfirmed. Do not advance credentials and do not replay the route. Public strings such as `auth`, `401`, `403`, empty success data, or user-facing error text never authorize fallback.

## Decision 9: Route ACK is non-authoritative; Matrix-specific reconciliation validates the requested input

A successful route send/ACK is only mutation delivery evidence. It SHALL NOT directly update `accepted_snapshot.current_connection`, table route styling, or credential success memory for the final state.

On mutation delivery success, the coordinator transitions to `RECONCILIATION`. Matrix reconciliation receives the requested route identity from the mutation result/intent and performs the existing exact-row read-only Matrix acquisition under the current reconciliation context.

A successful read is authoritative only when:

```text
accepted current_connection == requested input_num
```

If the read succeeds but reports a different/unknown connection, reconciliation fails unconfirmed. The prior accepted cache may remain visible only as stale/unconfirmed presentation, all row network actions remain blocked, live stays stopped, and top full Refresh is required, per the existing generic mutation contract.

If reconciliation confirms the route, its full accepted Matrix snapshot atomically replaces the row cache; the row may return to normal usable state and eligible live may resume after lifecycle cleanup/currentness checks.

## Decision 10: Route cleanup is model-specific but remains inside the one room lane

Current room mutation plumbing is PDU-specific in composition/controller methods. MIH-11 may generalize those names/dispatch points or add a Matrix-specific sibling, but SHALL NOT weaken the one-lane contract.

Expected conceptual ownership:

```text
RoomInteractionCoordinator
  -> mutation binding resolved from exact registry entry
      -> PDU mutation adapter OR Matrix route adapter
  -> reconciliation binding resolved from exact registry entry
      -> current PDU readback OR Matrix route readback validator
```

The existing PDU behavior must remain unchanged.

Cancellation/supersession must target the actual model-specific owner. A Matrix route adapter must not be cancelled through a PDU-only object, and PDU cancellation must not acquire Matrix resources.

## Decision 11: Quick actions are truthful

The right `Быстрые действия` card follows the approved reference layout.

### `Обновить статус`

Enabled only when existing exact-row Local Refresh is allowed. It emits the existing safe Local Refresh intent and does not create a second refresh path.

### `Перезагрузить устройство`

Visible for layout fidelity but disabled/non-actionable because current approved IN1804 control capability does not include reboot. It emits no signal, worker, handler call, or device request.

### `Открыть расширенный экран`

If rendered above/alongside the three-card content for visual fidelity, it is disabled/non-actionable in MIH-11. It does not navigate to standalone `MatrixScreen`, start a second MatrixController, change the selected target, or perform I/O.

A later change may authorize navigation/reboot only with explicit lifecycle/capability contracts.

## Decision 12: Existing live/local refresh and standalone routing must remain regression-free

MIH-11 does not replace existing `matrix_room_live` or `matrix_one_shot` acquisition.

Before a confirmed route send, the generic room mutation contract retires current Matrix live ownership. If cleanup cannot reach the allowed boundary, no route send occurs.

After successful reconciliation, eligible Matrix room live may resume only through the existing registry binding/current exact row.

Standalone `MatrixScreen` routing remains connected to standalone `MatrixController` and keeps its current semantics. MIH-11 shall not rewire it through the room coordinator or make room exact-row behavior depend on standalone screen state.

## Failure-state table

| Event | Room Matrix result |
| --- | --- |
| Click active route | no mutation |
| Confirmation Cancel | no lifecycle change, no I/O |
| Stale/superseded route intent before mutation acquisition | reject/no I/O |
| Live cleanup timeout before send | route not sent |
| Structured auth rejection before delivery | candidate may advance after cleanup |
| Route send ACK/success | start reconciliation; cache unchanged |
| Route send ambiguous/unknown outcome | blocked/unconfirmed; no replay/fallback; full Refresh required |
| Reconciliation reads requested input | accept new full snapshot; normal lifecycle may resume |
| Reconciliation reads different/unknown input | blocked/unconfirmed; prior cache stale; full Refresh required |
| Reconciliation transport/session failure | blocked/unconfirmed/connection-loss semantics per typed failure; full Refresh required |
| Late callback from superseded context | ignored |

## Testing strategy

### Presentation

- exact three-card order at baseline;
- general-info row order and no-data behavior;
- accepted input count (4 vs 8 regression, no hard-coded eight);
- exact table column order;
- dynamic output header;
- signal text + non-color cue;
- HDCP truthfulness/no fabricated `2.2`;
- route active/non-active/no-data states;
- dark/light styling and baseline/minimum behavior;
- disabled reboot/expanded-screen placeholders;
- local Refresh action uses existing intent.

### Intent/currentness

- only non-active eligible output cell emits route intent;
- stale/non-current record emits/accepts no mutation;
- active route click is no-op;
- disabled/blocked/degraded rows produce no route intent;
- confirmation cancel performs zero device I/O.

### Registry/composition

- Extron IN1804 exact registration declares Matrix mutation/reconciliation bindings;
- binding validation fails closed if an expected implementation hook is absent;
- no parallel Matrix mutation model list.

### Mutation safety

- live retires before route owner starts;
- no handler/session acquisition before currentness/cleanup gate;
- pre-delivery typed auth rejection can advance one approved candidate at a time;
- after route send invocation, auth-like/transport failure cannot advance candidate or replay;
- at most one route send per confirmed mutation generation;
- route ACK does not update accepted route state;
- reconciliation matches requested input before accepting cache;
- mismatch/unknown blocks row and requires top full Refresh;
- stale mutation/reconciliation callbacks cannot update replacement context.

### Regression

- existing PDU mutation/reconciliation remains unchanged;
- existing Matrix room live/local Refresh remains unchanged;
- standalone Matrix route behavior remains functional;
- common accordion one-expanded-row behavior remains unchanged;
- theme toggle does not perform I/O.

## Manual visual acceptance

At `1440 x 900` in both dark and light themes, capture the expanded Matrix exact row and verify:

- left General information / center Matrix / right Quick actions hierarchy;
- field order exactly matches this design;
- central table is visually dominant;
- input number is compact;
- Signal, HDCP, input name, and output columns are readable without baseline horizontal clipping;
- route state is understandable without color alone;
- disabled placeholders are visibly disabled;
- shared foundation header/room/network regions remain unchanged.

The screenshots are local validation evidence and are not repository artifacts by default.
